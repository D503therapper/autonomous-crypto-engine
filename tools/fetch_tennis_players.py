"""🎾 Tennis player bios from ESPN (for the age + experience factors): date of birth, plus height, handedness and
turned-pro year when ESPN has them, for every player id in data/sports/tennis/matches.csv (ids are per tour: ATP 2980
is not WTA 2980).

Saved to data/sports/tennis/players.json keyed "tour:id". The most recently active players go first; the run stops at
its time budget and the next run carries on (players already saved are skipped - resumable). Polite: a small thread
pool, a pause between calls, retries with backoff. A player ESPN says doesn't exist (404 on both endpoints) is saved
as {"none": true} so he isn't asked for again.
Endpoints: site.web.api.espn.com common/v3 athlete first, sports.core.api.espn.com v2 athlete as the fallback."""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

MATCHES = os.path.join("data", "sports", "tennis", "matches.csv")
OUT = os.path.join("data", "sports", "tennis", "players.json")
V3 = "https://site.web.api.espn.com/apis/common/v3/sports/tennis/{tour}/athletes/{id}"
CORE = "https://sports.core.api.espn.com/v2/sports/tennis/leagues/{tour}/athletes/{id}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36", "Accept": "application/json"}
THREADS, PAUSE_S, TRIES = 4, 0.25, 3
SAVE_EVERY = 50
ERRS = []


# ---------------------------------------------------------------- parsing (both payload shapes)
def _date(x):
    """'1987-05-22T07:00Z' / '1987-05-22' / '5/22/1987' / '22/05/1987' (day > 12) -> '1987-05-22'; None if not a date."""
    s = str(x or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
        if not m:
            return None
        a, b, y = map(int, m.groups())
        mo, d = (b, a) if a > 12 else (a, b)             # ESPN's displayDOB is month/day/year
    try:
        return datetime(y, mo, d).strftime("%Y-%m-%d") if 1940 <= y <= 2020 else None
    except ValueError:
        return None


def _height_cm(a):
    """Height in cm from displayHeight ("6' 2\"", "1.88 m", "188 cm") or height (inches when < 100, else cm)."""
    s = str(a.get("displayHeight") or "")
    m = re.match(r"^\s*(\d)'\s*(\d{1,2})", s)
    if m:
        return round((int(m.group(1)) * 12 + int(m.group(2))) * 2.54)
    m = re.match(r"^\s*(\d\.\d{1,2})\s*m\b", s)
    if m:
        return round(float(m.group(1)) * 100)
    m = re.match(r"^\s*(\d{3})\s*cm", s)
    if m:
        return int(m.group(1))
    try:
        h = float(a.get("height"))
    except (TypeError, ValueError):
        return None
    if h <= 0:
        return None
    return round(h * 2.54) if h < 100 else round(h)


def _hand(a):
    h = a.get("hand") or a.get("plays") or a.get("handedness")
    if isinstance(h, dict):
        h = h.get("abbreviation") or h.get("displayValue") or h.get("type") or ""
    h = str(h or "").strip().lower()
    return "L" if h.startswith("l") else "R" if h.startswith("r") else None


def _pro(a):
    for k in ("turnedPro", "turnedProYear", "proYear", "debutYear"):
        v = a.get(k)
        if isinstance(v, dict):
            v = v.get("year") or v.get("value") or v.get("displayValue")
        m = re.search(r"(19[6-9]\d|20[0-2]\d)", str(v or ""))
        if m:
            return int(m.group(1))
    for k in ("displayExperience", "experience", "bio"):          # "Turned Pro: 2005" in a text field
        v = a.get(k)
        if isinstance(v, dict):
            v = json.dumps(v)
        m = re.search(r"turned\s*pro\D{0,5}(19[6-9]\d|20[0-2]\d)", str(v or ""), re.I)
        if m:
            return int(m.group(1))
    return None


def parse_athlete(payload):
    """Either payload shape (v3: {"athlete": {...}}; core v2: the athlete itself) -> {name, dob, height_cm, hand,
    pro, stats} with only the fields ESPN had; None when it's not an athlete. 'stats' lists the stat names ESPN sent
    (if any) - kept so we can see whether serve stats are ever there for free."""
    if not isinstance(payload, dict):
        return None
    a = payload.get("athlete") if isinstance(payload.get("athlete"), dict) else payload
    if not a.get("id") and not a.get("displayName") and not a.get("fullName"):
        return None
    out = {"name": a.get("displayName") or a.get("fullName") or ""}
    dob = _date(a.get("dateOfBirth") or a.get("birthDate") or a.get("dob")) or _date(a.get("displayDOB"))
    if dob:
        out["dob"] = dob
    h, hand, pro = _height_cm(a), _hand(a), _pro(a)
    if h and 140 <= h <= 230:
        out["height_cm"] = h
    if hand:
        out["hand"] = hand
    if pro:
        out["pro"] = pro
    names = []
    for blk in (payload.get("statsSummary"), a.get("statsSummary"), a.get("statistics"), payload.get("statistics")):
        if isinstance(blk, dict):
            names += [str(s.get("name") or s.get("displayName")) for s in blk.get("statistics") or [] if isinstance(s, dict)]
    if names:
        out["stats"] = sorted(set(names))[:40]
    return out


# ---------------------------------------------------------------- fetching
def _get(url):
    """(status, json or None): retries with backoff; 404 = the player isn't there."""
    for i in range(TRIES):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return 200, json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            ERRS.append(f"{url}: {e.code}")
            if e.code in (401, 403):
                return e.code, None                      # blocked: retrying won't help
        except Exception as e:                           # noqa: BLE001
            ERRS.append(f"{url}: {str(e)[:80]}")
        time.sleep(1.5 * (i + 1))
    return None, None


def fetch(tour, pid):
    """(key, bio | {"none": True} | None = try again next run)."""
    key = f"{tour}:{pid}"
    time.sleep(PAUSE_S)
    s1, j1 = _get(V3.format(tour=tour, id=pid))
    bio = parse_athlete(j1) if j1 else None
    if bio and bio.get("dob"):
        return key, bio
    s2, j2 = _get(CORE.format(tour=tour, id=pid))
    bio2 = parse_athlete(j2) if j2 else None
    if bio2:
        return key, {**bio2, **(bio or {}), **{k: v for k, v in bio2.items() if k == "dob"}}
    if bio:
        return key, bio
    if s1 == 404 and s2 == 404:
        return key, {"none": True}
    return key, None


def players_by_recency(path=MATCHES):
    """[(tour, id)] of every player in the history, the most recently active first."""
    last = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            t = (r.get("tour") or "atp").lower()
            for pid in (r.get("p1"), r.get("p2")):
                if pid:
                    k = (t, str(pid))
                    last[k] = max(last.get(k, ""), r.get("start") or "")
    return [k for k, _ in sorted(last.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)]


def load(path=OUT):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(data, path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, indent=0, sort_keys=True)
    os.replace(path + ".tmp", path)


def main(budget_s=20 * 60):
    t0 = time.time()
    data = load()
    todo = [(t, p) for t, p in players_by_recency() if f"{t}:{p}" not in data]
    print(f"{len(data)} players on file, {len(todo)} to fetch (newest-active first)", flush=True)
    added = found = 0
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def job(tp):
        return fetch(*tp) if time.time() - t0 < budget_s else (f"{tp[0]}:{tp[1]}", None)
    with ThreadPoolExecutor(THREADS) as ex:
        for i, (key, bio) in enumerate(ex.map(job, todo), 1):
            if bio is not None:
                data[key] = {**bio, "fetched": stamp}
                added += 1
                found += bool(bio.get("dob"))
            if i % SAVE_EVERY == 0:
                save(data)                                 # saved as it goes - a slow run never loses what it got
                print(f"{time.strftime('%H:%M:%S')} {i}/{len(todo)} checked, {added} added ({found} with a birth date)",
                      flush=True)
    save(data)
    remaining = sum(1 for t, p in players_by_recency() if f"{t}:{p}" not in data)
    print(f"{added} added this run ({found} with a birth date), {remaining} still to fetch, {len(ERRS)} errors", flush=True)
    for e in ERRS[:10]:
        print("  ", e)
    if os.environ.get("GITHUB_OUTPUT"):                    # the workflow runs again right away while it's adding
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"added={added}\nremaining={remaining}\n")
    return added, remaining


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20 * 60)
