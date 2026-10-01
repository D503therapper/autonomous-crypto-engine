"""COACHING CHANGES (the owner, 9/30: "you need to get all the data"): every in-season firing / interim coach, with
dates, from Wikipedia's season pages ("2023-24 NBA season" -> Coaching changes) through Wikipedia's own public API
(no key, a plain User-Agent that says who we are - Wikipedia's rule). ESPN only lists one coach per season.
Runs in GitHub Actions (coaches.yml - this sandbox can't reach it). Saves the raw sections to
data/sports/coach_changes_raw.json; sports_coach_changes.parse() turns them into firings."""
import json
import os
import re
import time
import urllib.parse
import urllib.request

import sports_data as sd

RAW = os.path.join(sd.DATA, "coach_changes_raw.json")
PARSED = os.path.join(sd.DATA, "coach_changes.json")      # the mid-season changes (parse()), saved each run
API = "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page={page}"
UA = "D503-sports-engine/1.0 (https://github.com/D503therapper/autonomous-crypto-engine; coaching study)"


def pages(season):
    """Wikipedia page titles for a season (the year it starts)."""
    nxt = str(season + 1)[2:]
    return {"nfl": f"{season} NFL season", "nba": f"{season}–{nxt} NBA season", "nhl": f"{season}–{nxt} NHL season",
            "mlb": f"{season} Major League Baseball season", "ncaaf": f"{season} NCAA Division I FBS football season",
            "ncaab": f"{season}–{nxt} NCAA Division I men's basketball season"}


def fetch(page):
    req = urllib.request.Request(API.format(page=urllib.parse.quote(page)), headers={"User-Agent": UA})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return ((json.load(r).get("parse") or {}).get("wikitext") or {}).get("*") or ""
        except Exception as e:                               # noqa: BLE001
            if i == 2:
                print(f"   {page}: {str(e)[:80]}")
                return ""
            time.sleep(2)


def coaching_sections(text):
    """The wikitext of every section whose heading mentions coach / manager changes (its subsections included)."""
    out, cur, level = [], [], 0                          # level: the heading depth of the section we're keeping
    for line in text.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if m:
            d = len(m.group(1))
            if level and d > level:                      # a subsection ("=== In-season ==="): keep going
                cur.append(line)
                continue
            if cur:
                out.append("\n".join(cur))
            cur, level = ([line], d) if re.search(r"coach|manager", m.group(2), re.I) else ([], 0)
        elif level:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def run(seasons=range(2015, 2027)):
    try:
        with open(RAW) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        raw = {}
    for season in seasons:
        for lg, page in pages(season).items():
            key = f"{lg}:{season}"
            if raw.get(key, {}).get("sections"):
                continue
            secs = coaching_sections(fetch(page))
            raw[key] = {"page": page, "sections": secs}
            print(f"{key}: {page} - {len(secs)} coaching section(s), {sum(len(s) for s in secs)} chars", flush=True)
            time.sleep(0.5)                                  # (gentle on Wikipedia)
    with open(RAW, "w") as f:
        json.dump(raw, f)
    try:
        with open(PARSED, "w") as f:
            json.dump(parse(sd.load_games(), raw), f, indent=0)
    except Exception as e:                                   # noqa: BLE001
        print(f"parse failed: {str(e)[:80]}")


# THE FIRING STUDY (9/30, 153 mid-season coaching changes 2016-26, closing prices): a DOG that just fired its coach
# keeps losing in football and hoops - rest of the season NFL -28%, college football -30%, NBA -10.7%, college hoops
# -18.4% (every dog about -4% to -7%): the market prices a bounce that doesn't come. Hockey is the opposite: after a
# change the team beats its price (dogs rest of season -0.6% vs -5.4%; games 4-10 +7.6% dogs / +4.5% favorites).
FADE_AFTER = ("nfl", "ncaaf", "nba", "ncaab")
BUMP_AFTER = ("nhl",)


def recent(now_iso, path=None, days=120):
    """{(league, team id): date of its mid-season coaching change} - changes within the last `days`."""
    try:
        with open(path or PARSED) as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return {}
    lo = _minus(now_iso[:10], days)
    return {(r["league"], str(r["team"])): r["date"] for r in rows if lo <= r["date"] <= now_iso[:10]}


MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                       "September", "October", "November", "December"), 1)}
EVENT = re.compile(r"\b(fired|dismissed|relieved|resign|stepped down|step down|parted ways|terminated|let go|"
                   r"interim|retire)", re.I)


def _clean(t):
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    return re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)


PLANNED = re.compile(r"will (step down|retire|resign|not return|leave)|at the (end|conclusion) of the season|"
                     r"following the season|after the season(?!'s| opener)", re.I)
DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                  r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?")


def events(raw):
    """Every dated coaching change: [(league, 'YYYY-MM-DD', its text)] - from a table row OR a bullet ('On January 23,
    2024, the Milwaukee Bucks fired head coach Adrian Griffin...' / '| Michigan State || Mel Tucker || September 27,
    2023 || Fired'). A date without a year gets the season's (fall months = the season's first year)."""
    out = []
    for key, v in raw.items():
        lg, season = key.split(":")[0], int(key.split(":")[1])
        for sec in v.get("sections") or []:
            text = _clean(sec)
            chunks = re.split(r"\n\|-[^\n]*|\n(?=\*)", text)      # table rows / bullets
            for ch in chunks:
                flat = " ".join(ch.split())
                if not EVENT.search(flat) or re.search(r"general manager|\bGM\b|president of", flat, re.I):
                    continue                             # (baseball's GM changes aren't coaching changes)
                m = DATE.search(flat)                    # the FIRST date in a row is the change itself (later ones:
                if m:                                    # 'named full-time on November 15', a hiring...)
                    mon = MONTHS[m.group(1)]
                    yr = int(m.group(3)) if m.group(3) else (season if lg == "mlb" or mon >= 7 else season + 1)
                    out.append((lg, f"{yr}-{mon:02d}-{int(m.group(2)):02d}", flat[:400]))
    return out


def parse(games, raw=None):
    """Mid-season coaching changes: [{league, team, date, interim, text}] - a dated change for a team that played
    real games both before AND after it that season (so it's truly in-season)."""
    import sports_model as sm
    if raw is None:
        with open(RAW) as f:
            raw = json.load(f)
    names = {}
    starts = {}
    for g in games.values():
        lg = g.get("league")
        if g.get("status") != "final" or (g.get("stype") or "2") != "2":
            continue                                     # (regular season only: a change after the last game isn't
            #                                              in-season, even with playoff games to come)
        for side in ("home", "away"):
            names.setdefault(lg, {})[g[side]] = g.get(side + "_name") or ""
            starts.setdefault((lg, g[side]), []).append(g["start"][:10])
    out, seen = [], set()
    for lg, day, text in events(raw):
        if PLANNED.search(text):
            continue                                     # 'will step down after the season': he coached the rest of it
        head = text[:220]
        if text[:1] in "|!":                             # a table row: the team is its FIRST cell (other teams get
            cells = [c.strip() for c in re.split(r"\|\|?|!!?", text) if c.strip() and "=" not in c]   # mentioned
            head = cells[0] if cells else head                                                         # in its notes)
        best = None
        college = lg in ("ncaaf", "ncaab")
        for tid, nm in (names.get(lg) or {}).items():
            pat = re.escape(nm)
            if college:                                  # 'Illinois' must not match 'Northern Illinois' / 'Illinois
                pat = "".join(rf"(?<![A-Z][a-z]{{{n}}}\s)" for n in range(1, 14)) + pat + \
                      r"(?!\s(?:State|St\b|Tech|A&M|A&T|Upstate|Christian|Southern|Atlantic|International|[A-Z]{2,}))"
                #                                  (10/1 audit: 'Charleston Southern' read as 'Southern', 'USC
                #                                   Upstate' as 'USC', 'North Carolina A&T' as 'North Carolina')
            if nm and re.search(r"\b" + pat + r"\b", head) and (best is None or len(nm) > len(best[1])):
                best = (tid, nm)                         # (the longest team name that fits: 'Miami (OH)' over 'Miami')
        if not best:
            continue
        ss = sorted(starts.get((lg, best[0]), []))
        before = [x for x in ss if x < day and x >= _minus(day, 120)]
        after = [x for x in ss if x > day and x <= _plus(day, 120)]
        near = before and after and before[-1] >= _minus(day, 16) and after[0] <= _plus(day, 16)
        if near and len(before) >= 3 and len(after) >= 3 and (lg, best[0], day) not in seen:   # (playing on both
            #                                                    sides within ~2 weeks: truly mid-season, not June)
            seen.add((lg, best[0], day))
            out.append({"league": lg, "team": best[0], "name": best[1], "date": day,
                        "interim": bool(re.search(r"interim", text, re.I)), "text": head})
    yearless = {(r["league"], r["team"], r["date"]) for r in out}
    out = [r for r in out if (r["league"], r["team"], f"{int(r['date'][:4]) - 1}{r['date'][4:]}") not in yearless]
    #   (10/1 audit: next season's page repeats last season's firing with no year - Staley's 12/15/2023 firing came
    #    back as a 12/15/2024 one. The same team, the same day a year later: the repeat.)
    out.sort(key=lambda r: (r["league"], r["team"], r["date"]))
    keep = [r for i, r in enumerate(out) if not (i and out[i - 1]["league"] == r["league"] and out[i - 1]["team"] == r["team"]
                                                 and r["date"] <= _plus(out[i - 1]["date"], 14))]   # (one change, twice)
    return sorted(keep, key=lambda r: (r["league"], r["date"]))


# NEW HEAD COACHES (10/1, the owner's Belichick-at-UNC point - every college football hire with its "Previous
# position" on Wikipedia's season pages (2022-26 seasons; older pages don't list it, so a vet like Mack Brown would
# read as a first-timer - left out), closing prices, the coach's FIRST season): a FIRST-TIME head coach's team as a
# +200 or bigger dog: +200..+399 -40.0% (56) vs -6.7% for every such dog, +400 and up -71.7% (81) vs -26.3% - worse
# every full season 2022-25. They get overmatched. (+100..+199: fine, +7.9%.) A coach who's run a program before:
# about even (dogs +3.1%). NFL looks the other way (retreads -14.4% as dogs) but only 21 hires - not used.
FIRST_TIMER_DOG = {"ncaaf": 200}
PREV_HEAD = re.compile(r"head coach", re.I)
NOT_HEAD = re.compile(r"(associate|assistant|interim|co-)\s*head", re.I)


def _cells(row):
    return [_clean(c).strip() for c in re.split(r"\|\||\n\||\n!|!!", row.strip().lstrip("|"))]


def hires(raw=None, leagues=("ncaaf",)):
    """Every permanent head-coach hire: [{league, team (its name), season (the coach's first), coach, first_time}]."""
    if raw is None:
        with open(RAW) as f:
            raw = json.load(f)
    rows = []
    for key, v in sorted(raw.items()):
        lg, page = key.split(":")[0], int(key.split(":")[1])
        for sec in v.get("sections") or []:
            for tb in re.findall(r"\{\|.*?\n\|\}", sec, re.S):
                hdr = [_clean(h).strip().lower() for h in re.findall(r"^!\s*(?:[^|\n]*\|)?\s*([^\n]+)$", tb, re.M)]
                rep = [i for i, h in enumerate(hdr) if ("replacement" in h and "interim" not in h) or "incoming coach" in h]
                if not rep or "position" in hdr or any("gm" in h or "general manager" in h for h in hdr):
                    continue
                prev = next((i for i, h in enumerate(hdr) if "previous" in h), None)
                date = next((i for i, h in enumerate(hdr) if h == "date"), None)
                for r in tb.split("\n|-")[1:]:
                    c = _cells(r)
                    if len(c) <= rep[0] or not c[0] or c[0].startswith("!"):
                        continue
                    rows.append((lg, page, c, rep[0], prev, date))
    left = {}                                            # coach -> the first page he LEFT a (non-interim) head job on
    for lg, page, c, ri, pi, di in rows:
        if len(c) > 1 and "interim" not in c[1].lower():
            nm = re.sub(r"\s*\(.*?\)", "", c[1]).strip()
            left[nm] = min(left.get(nm, page), page)
    out, seen = [], set()
    for lg, page, c, ri, pi, di in rows:
        if lg not in leagues:
            continue
        rep = c[ri]
        if not rep or ("interim" in rep.lower() and "permanent" not in rep.lower()):
            continue
        coach = re.sub(r"\s*\(.*", "", rep).strip()
        m = DATE.search(c[di]) if di is not None and di < len(c) else None
        season = page + 1
        if m and m.group(3):
            season = int(m.group(3)) + (1 if MONTHS[m.group(1)] >= 8 else 0)
        prev = c[pi] if pi is not None and pi < len(c) else ""
        been = (bool(PREV_HEAD.search(prev)) and not NOT_HEAD.search(prev)) or left.get(coach, 9999) <= page
        team = re.sub(r"\s*\(.*?\)", "", c[0]).strip()
        if (lg, team, season) not in seen:
            seen.add((lg, team, season))
            out.append({"league": lg, "team": team, "season": season, "coach": coach, "first_time": not been})
    return out


def _norm(n):
    return re.sub(r"\bState\b", "St", re.sub(r"\bCentral\b", "C", n)).replace(".", "").strip()


def first_timers(games, now_iso, raw=None):
    """{(league, team id)} - teams in a first-time head coach's FIRST season (this season)."""
    season = int(now_iso[:4]) - (1 if int(now_iso[5:7]) < 6 else 0)
    ids = {}
    for g in games.values():
        lg = g.get("league")
        if lg in FIRST_TIMER_DOG:
            for side in ("home", "away"):
                if g.get(side + "_name"):
                    ids.setdefault((lg, _norm(g[side + "_name"])), str(g[side]))
    try:
        rows = hires(raw, tuple(FIRST_TIMER_DOG))
    except (OSError, ValueError):
        return set()
    return {(r["league"], ids[(r["league"], _norm(r["team"]))]) for r in rows
            if r["first_time"] and r["season"] == season and (r["league"], _norm(r["team"])) in ids}


def _minus(day, n):
    from datetime import datetime, timedelta
    return (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=n)).strftime("%Y-%m-%d")


def _plus(day, n):
    from datetime import datetime, timedelta
    return (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=n)).strftime("%Y-%m-%d")


if __name__ == "__main__":
    run()
