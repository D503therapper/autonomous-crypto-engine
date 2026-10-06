"""🎓 THE CAPPER BENCHMARK - Dr. Bob (Bob Stoll) (the owner, 10/2: "use him as a prime example ... we don't copy his picks,
but we weigh his picks and his leans. And we compare"). Step 1: a record. Every free Lean on his public NFL analysis page
(drbobsports.com/nfl-analysis - he's NFL only this year, no college), logged the FIRST time we see it with the number
and price he gave, then graded against the final score next to ours on the same game: did he beat the line, and when we
were on the same game, who was right. Leans only count once and are never edited after the fact.
His own record (his site): Free Analysis Leans 1101-913-38 all-time in college; NFL Best Bets 57.5% since 2016 (paid -
never seen here). Report only: nothing here touches a pick or the engine's read until it's been studied.

Writes data/sports/capper_drbob.json. Fetched on GitHub's servers (Claude's sandbox can't reach the site) - one plain
public page request per run, nothing that gets around a block."""
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

import sports_data as sd

URL = "https://drbobsports.com/nfl-analysis/"
PATH = os.path.join(sd.DATA, "capper_drbob.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
EVERY_H = 3                                                     # read his page at most every 3 hours
KICK = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\w{3}) (\d{1,2}) ")
SIDE = re.compile(r"^(?P<who>[A-Za-z .'&]+?)\s*\((?P<line>[+-]\d+(?:\.5)?|pk|PK)(?:/[+-]?\d+(?:\.5)?)?(?:\s+(?P<px>[+-]\d{3}))?\)")
TOT = re.compile(r"^(?P<who>Over|Under)\s*\(?(?P<line>\d+(?:\.5)?)(?:\s+(?P<px>[+-]\d{3}))?\)?", re.I)
RATE = re.compile(r"ratings favor (?:the )?(?P<who>[A-Za-z .'&]+?) by (?:just |only )?(?P<pts>\d+(?:\.\d)?) point")
SKIP = {"ny", "la", "the", "new", "york", "los", "angeles", "bay", "city", "san", "st", "louis", "las", "vegas", "green",
        "tampa", "kansas", "england"}


def fetch(url=URL):
    import importlib.util
    spec = importlib.util.spec_from_file_location("fp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "fetch_pages.py"))
    fp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fp)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return fp.text_of(r.read().decode("utf-8", "replace"))


def _team(short, away, home):
    """'NY GIANTS' / 'Cleveland' / 'CINCINNATI' -> 'away' or 'home' by the full names in the game's header."""
    w = {x for x in re.findall(r"[a-z0-9]+", short.lower()) if x not in SKIP} or set(re.findall(r"[a-z0-9]+", short.lower()))
    hits = [s for s, full in (("away", away), ("home", home)) if w & set(re.findall(r"[a-z0-9]+", full.lower()))]
    return hits[0] if len(hits) == 1 else None


def parse(lines, year):
    """[{away, home, date, leans: [{side: away/home/over/under, line, price}], rating: (side, pts) or None}] from his page."""
    games = []
    for i, x in enumerate(lines):
        if x != "@" or i == 0 or i + 2 >= len(lines):
            continue
        m = KICK.match(lines[i + 2])
        if not m:
            continue
        try:
            d = datetime.strptime(f"{m.group(2)} {m.group(3)} {year}", "%b %d %Y").date()
        except ValueError:
            continue
        games.append({"away": lines[i - 1], "home": lines[i + 1], "date": d.isoformat(), "at": i, "leans": [], "rating": None})
    for n, g in enumerate(games):
        end = games[n + 1]["at"] - 1 if n + 1 < len(games) else len(lines)
        for x in lines[g["at"]:end]:
            if re.match(r"^Lean\s*[–-]", x):
                for part in re.split(r"\s+[–-]\s+", x)[1:]:
                    t, s = TOT.match(part), SIDE.match(part)
                    if t:
                        g["leans"].append({"side": t.group("who").lower(), "line": float(t.group("line")),
                                           "price": int(t.group("px")) if t.group("px") else None})
                        break      # (10/6: 'Over (51.5) – CINCINNATI (-2.5) vs Jacksonville' - after a total the rest
                        #           is the matchup he's writing about, not a side lean; his side leans say 'over')
                    elif s and _team(s.group("who"), g["away"], g["home"]):
                        ln = s.group("line")
                        g["leans"].append({"side": _team(s.group("who"), g["away"], g["home"]),
                                           "line": 0.0 if ln.lower() == "pk" else float(ln),
                                           "price": int(s.group("px")) if s.group("px") else None})
            r = RATE.search(x)
            if r and g["rating"] is None and _team(r.group("who"), g["away"], g["home"]):
                g["rating"] = [_team(r.group("who"), g["away"], g["home"]), float(r.group("pts"))]
        del g["at"]
    return games


def _ours(games, bob):
    """Our NFL game for one of his: same two teams (his 'Cleveland Browns' = our 'Browns'), kickoff within a day."""
    last = lambda full: full.split()[-1].lower()                                # noqa: E731
    for g in games.values():
        if g.get("league") != "nfl" or not g.get("start"):
            continue
        if (g.get("home_name") or "").lower() == last(bob["home"]) and (g.get("away_name") or "").lower() == last(bob["away"]):
            st = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(sd.PT_)   # (Pacific, DST-safe)
            if abs((st.date() - datetime.fromisoformat(bob["date"]).date()).days) <= 1:
                return g
    return None


def grade(lean, g):
    """won / lost / push against his own number, None until final."""
    if not g or g.get("status") != "final" or g.get("home_score", "") == "" or g.get("away_score", "") == "":
        return None
    h, a = float(g["home_score"]), float(g["away_score"])
    if lean["side"] in ("over", "under"):
        d = (h + a - lean["line"]) * (1 if lean["side"] == "over" else -1)
    else:
        d = (h - a if lean["side"] == "home" else a - h) + lean["line"]
    return "won" if d > 0 else "lost" if d < 0 else "push"


def update(st, page, games, picks, now):
    """Log new leans (first sight only), then grade every open one and line it up against our pick on that game."""
    stamp = now.strftime("%Y-%m-%dT%H:%MZ")
    for b in page:
        for ln in b["leans"]:
            key = f"{b['date']}|{b['away']}|{b['home']}|{ln['side']}"
            if key not in st["leans"]:
                st["leans"][key] = {**ln, "date": b["date"], "away": b["away"], "home": b["home"], "seen": stamp,
                                    "rating": b["rating"], "result": None}
    ours = {}
    for pk in picks or []:
        for leg in pk.get("legs") or []:
            if (leg.get("league") == "nfl" and pk.get("kind") not in ("parlay", "ladder")):
                ours.setdefault(leg.get("game_id"), []).append((pk, leg))
    for row in st["leans"].values():
        g = _ours(games, row)
        if not g:
            continue
        if row["result"] is None:
            row["result"] = grade(row, g)
        if row["side"] in ("home", "away"):
            mine = [(pk, leg) for pk, leg in ours.get(g["id"], []) if leg.get("market") in ("ml", "spread", None)]
            if mine:
                pk, leg = mine[0]
                row["us"] = {"kind": pk.get("kind"), "lean": bool(pk.get("lean")), "side": leg.get("side"),
                             "same": leg.get("side") == row["side"], "status": pk.get("status")}
    rec = lambda rows: {k: sum(r["result"] == k for r in rows) for k in ("won", "lost", "push")}  # noqa: E731
    rows = list(st["leans"].values())
    st["record"] = {"all": rec(rows), "sides": rec([r for r in rows if r["side"] in ("home", "away")]),
                    "totals": rec([r for r in rows if r["side"] in ("over", "under")]),
                    "with_us": rec([r for r in rows if (r.get("us") or {}).get("same")]),
                    "against_us": rec([r for r in rows if r.get("us") and not r["us"]["same"]])}
    st["checked"] = stamp
    return st


def load(path=None):
    try:
        st = json.load(open(path or PATH))
    except (OSError, ValueError):
        st = {}
    st.setdefault("leans", {})
    return st


def run(games, picks, now=None, path=None, page=None):
    """Hourly from sports.run; reads his page at most every EVERY_H hours (page= for tests). Never blocks the board."""
    now = now or datetime.now(timezone.utc)
    st = load(path)
    due = not st.get("read") or now - datetime.strptime(st["read"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc) \
        >= timedelta(hours=EVERY_H)
    if page is None and due:
        try:
            page = parse(fetch(), now.year)
            st["read"] = now.strftime("%Y-%m-%dT%H:%MZ")
        except Exception as e:                               # noqa: BLE001 - his site down never stops anything
            print(f"capper page not read: {str(e)[:80]}")
    update(st, page or [], games, picks, now)
    with open(path or PATH, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    return st
