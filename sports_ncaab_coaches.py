"""🏀 COLLEGE HOOPS COACHES (the owner, 11/3: "If the engine is knowledgeable on the teams, the injuries, the players,
the new players, the coaches ... there's no reason why we should be complete losers"). ESPN's per-season coach list
(data/sports/coaches.json) is bad history for college hoops - today's coach copied back through every season (the 10/1
audit) - so the engine had NO college hoops coach knowledge. This rebuilds it from what's on disk, no network:
  - Wikipedia's season pages' "Coaching changes" tables (data/sports/coach_changes_raw.json, "ncaab:<season>" - the
    coaches.yml job pulls them with a plain request): Team | Former | Interim | New | Reason, every change during or
    after that season since 2015-16 (27-68 a season), with the dates and "after N seasons" in the reason text;
  - ESPN's CURRENT coach list (coaches.json, the newest season - right for today, wrong for the past).
Walking the changes forward from 2015-16 gives each D1 team's head coach by season: name, his first season with the
team (tenure), whether he's NEW this season, a mid-season change (the interim from its date), and whether the hire
reads as a FIRST-TIME head coach (the reason text: "assistant" / "associate head coach" vs "head coach at X" - a hint).
Saved to data/sports/ncaab_coaches.json: {team id: {season (the start year): {...}}} by build(); state() reads one
team's season for the live board. A team never in a change table since 2015 keeps its current coach all the way back
(since 2015 or earlier - tenure a lower bound, "since": null).
What the 11/3 KNOWLEDGE (A) study found on it: results/studies/cbb_knowledge_a/s1_coaches.py, SPORTS_FINDINGS."""
import json
import os
import re

import sports_data as sd

RAW = os.path.join(sd.DATA, "coach_changes_raw.json")
ESPN = os.path.join(sd.DATA, "coaches.json")
PATH = os.path.join(sd.DATA, "ncaab_coaches.json")
FIRST = 2015                                   # the first season page on file (2015-16)
MONTHS = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                           "September", "October", "November", "December"))}
DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})"
                  r"(?:,\s*(\d{4}))?")
LINK = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")
REF = re.compile(r"<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->", re.S)
TEMPL = re.compile(r"\{\{[^{}]*\}\}")
# ESPN's short names where the plain normalizer can't bridge Wikipedia's display name (normalized -> candidates,
# tried in order against our games file's names)
ALIAS = {"abilene christian": ["abilene chrstn"], "arkansas pine bluff": ["ar pine bluff"], "bethune cookman": ["bethune"],
         "cs bakersfield": ["bakersfield"], "cs northridge": ["csu northridge"], "california baptist": ["ca baptist", "cal baptist"],
         "charleston southern": ["charleston so"], "coastal carolina": ["coastal", "coastal car"],
         "george washington": ["g washington"], "georgia southern": ["ga southern"], "houston christian": ["hou christian", "houston baptist"],
         "houston baptist": ["hou christian", "houston baptist"], "jacksonville st": ["jax state", "jacksonville st"],
         "louisiana monroe": ["ul monroe", "la monroe"], "loyola": ["loyola chicago"], "loyola marymount": ["loyola mrymnt", "lmu"],
         "maryland eastern shore": ["md eastern", "umes"], "middle tennessee": ["middle tenn", "mid tennessee"],
         "mississippi valley st": ["miss valley st"], "mount st mary's": ["mount st marys", "mt st mary"],
         "new orleans": ["new orleans", "lsu n orleans"], "northwestern st": ["n'western st", "nwestern st"],
         "south carolina st": ["sc state", "s carolina st"], "south dakota st": ["s dakota st"], "north dakota st": ["n dakota st"],
         "se missouri st": ["se missouri"], "southeast missouri st": ["se missouri"], "st francis brooklyn": ["st francis bkn", "st francis (bkn)", "st francis ny"],
         "stephen f austin": ["sf austin"], "texas a&m corpus christi": ["texas a&m cc"], "texas rio grande valley": ["ut rio grande", "utrgv"],
         "ut rio grande valley": ["ut rio grande"], "utrgv": ["ut rio grande"], "uc santa barbara": ["santa barbara", "ucsb"],
         "usc upstate": ["sc upstate"], "western kentucky": ["western ky", "w kentucky"], "uconn": ["connecticut", "uconn"],
         "ole miss": ["mississippi", "ole miss"], "pitt": ["pittsburgh", "pitt"], "umass": ["massachusetts", "umass"],
         "lsu": ["louisiana st", "lsu"], "byu": ["brigham young", "byu"], "unlv": ["nevada las vegas", "unlv"],
         "utep": ["texas el paso", "utep"], "utsa": ["texas san antonio", "utsa"], "vcu": ["virginia commonwealth", "vcu"],
         "ucf": ["central florida", "ucf"], "usc": ["southern california", "usc"], "nc st": ["north carolina st", "nc state"],
         "unc": ["north carolina", "unc"], "fiu": ["florida international", "fiu"], "fau": ["florida atlantic", "fau"],
         "little rock": ["arkansas little rock", "little rock"], "siu edwardsville": ["siue", "siu edwardsville"],
         "ut martin": ["tennessee martin", "ut martin"], "umass lowell": ["massachusetts lowell", "umass lowell"],
         "uncg": ["unc greensboro"], "uncw": ["unc wilmington"], "mcneese": ["mcneese st", "mcneese"],
         "nicholls": ["nicholls st", "nicholls"], "sam houston": ["sam houston st", "sam houston"], "seattle u": ["seattle"],
         "st francis (pa)": ["st francis pa"], "saint francis": ["st francis pa"], "miami (fl)": ["miami"], "miami (oh)": ["miami oh"],
         "texas a&m commerce": ["east texas a&m", "texas a&m commerce"], "app st": ["app state", "appalachian st"],
         "appalachian st": ["app state", "appalachian st"], "southern mississippi": ["southern miss"], "hawaii": ["hawai'i", "hawaii"],
         "nebraska omaha": ["omaha"], "purdue fort wayne": ["purdue fort wayne", "fort wayne"], "fort wayne": ["purdue fort wayne"],
         "ipfw": ["purdue fort wayne", "fort wayne"], "detroit": ["detroit mercy"], "grambling st": ["grambling"],
         "prairie view a&m": ["prairie view"], "college of charleston": ["charleston"], "the citadel": ["the citadel", "citadel"],
         "citadel": ["the citadel", "citadel"], "st joseph's": ["saint joseph's", "st joseph's"], "st peter's": ["saint peter's", "st peter's"],
         "st mary's": ["saint mary's", "st mary's"], "st louis": ["saint louis", "st louis"], "mt st mary's": ["mount st marys", "mt st mary"],
         "st thomas (mn)": ["st thomas", "st thomas mn"], "queens (nc)": ["queens university", "queens"], "dixie st": ["utah tech"],
         "tarleton": ["tarleton st"], "central connecticut st": ["c connecticut", "central connecticut"],
         "southeastern louisiana": ["se louisiana"], "south carolina upstate": ["sc upstate"], "fgcu": ["florida gulf coast"],
         "nj tech": ["njit"], "fdu": ["fairleigh dickinson"], "wisconsin green bay": ["green bay"],
         "wisconsin milwaukee": ["milwaukee"], "louisiana lafayette": ["louisiana"], "ualbany": ["albany"],
         "southern university": ["southern"], "nc a&t": ["north carolina a&t", "nc a&t"], "nc central": ["north carolina central", "nc central"],
         "cal st east bay": ["cs east bay"], "cal": ["california"], "cal st long beach": ["long beach st"], "san josé st": ["san jose st"],
         "liu brooklyn": ["liu", "long island"], "long island": ["liu", "long island"], "liu": ["long island", "liu"],
         "albany": ["ualbany", "albany"], "appalachian st": ["app state", "appalachian st"], "cal st bakersfield": ["bakersfield"],
         "cal st northridge": ["csu northridge"], "east tennessee st": ["etsu", "east tennessee st"],
         "fairleigh dickinson": ["fdu", "fairleigh dickinson"], "florida atlantic": ["fau", "florida atlantic"],
         "florida gulf coast": ["fgcu", "florida gulf coast"], "iupui": ["iu indy", "iupui"], "massachusetts": ["umass", "massachusetts"],
         "mcneese st": ["mcneese", "mcneese st"], "middle tennessee": ["mtsu", "middle tenn", "middle tennessee"],
         "nicholls st": ["nicholls", "nicholls st"], "north carolina a&t": ["nc a&t", "north carolina a&t"], "pittsburgh": ["pitt", "pittsburgh"],
         "san jose st": ["san josé st", "san jose st"], "seattle": ["seattle u", "seattle"], "south carolina st": ["sc state", "south carolina st"],
         "tennessee martin": ["ut martin", "tennessee martin"], "texas arlington": ["ut arlington", "texas arlington"],
         "umkc": ["kansas city", "umkc"], "kansas city": ["kansas city", "umkc"], "loyola marymount": ["lmu", "loyola marymount"]}
WORDS = {"eastern": "e", "northern": "n", "western": "w", "central": "c", "southern": "s", "southeast": "se",
         "southeastern": "se", "northwestern": "n'western", "northeastern": "ne", "southwestern": "sw"}


def _clean(t):
    t = REF.sub("", str(t))
    t = TEMPL.sub("", t)
    t = LINK.sub(lambda m: (m.group(2) if m.group(2) is not None else m.group(1)), t)
    t = re.sub(r"'''?|<br\s*/?>|</?small>|<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm(n):
    """A team name the way both ESPN and Wikipedia spell it, near enough to match."""
    n = _clean(n).lower().replace("’", "'").replace("–", "-")
    n = re.sub(r"\s*\((men's )?basketball\)", "", n)
    n = re.sub(r"\bstate\b", "st", n)
    n = re.sub(r"\bsaint\b", "st", n)
    n = re.sub(r"\bst\.", "st", n)
    n = re.sub(r"\buniversity of\b", "", n)
    n = re.sub(r"[.]", "", n)
    n = re.sub(r"\s*-\s*", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def match(name, ids):
    """The ESPN team id for a Wikipedia team name (None when nothing on file fits)."""
    n = norm(name)
    if n in ids:
        return ids[n]
    for cand in ALIAS.get(n, []):
        if norm(cand) in ids:
            return ids[norm(cand)]
    w = n.split()
    if w and w[0] in WORDS:                               # 'Eastern Illinois' -> 'E Illinois'
        alt = " ".join([WORDS[w[0]]] + w[1:])
        if alt in ids:
            return ids[alt]
    return None


def _cells(row):
    """The cells of one wikitable row (each on its own '|' line, or '||' inline)."""
    out = []
    for part in re.split(r"\n\|(?!-)|\|\|", "\n" + row.strip())[1:]:       # (an EMPTY cell stays a cell - it keeps
        p = part.strip()                                                   #  the columns lined up)
        if p.startswith("-"):
            continue
        span = 1
        if "=" in p.split("|")[0] and "[[" not in p.split("|")[0]:        # a style attribute before the cell
            m = re.search(r"colspan\s*=\s*\"?(\d)", p.split("|")[0])       # (an interim made permanent spans the
            span = int(m.group(1)) if m else 1                            #  Interim + New columns - one cell, twice)
            p = p.split("|", 1)[1] if "|" in p else p
        out.extend([p] * span)
    return out


def _name(cell):
    """A coach's display name from a cell ('{{n/a}}' / '' -> None)."""
    c = _clean(cell)
    c = re.sub(r"\s*\(.*?\)", "", c).strip(" ,;")
    if not c or c.lower() in ("n/a", "none", "—", "-", "vacant", "tba", "tbd"):
        return None
    return c


def _first_time(reason, new):
    """The hire reads as a FIRST-TIME head coach: the sentence naming him says 'assistant' / 'associate head coach'
    and not 'head coach' of some program. A hint from the prose, not a record."""
    if not new:
        return None
    last = new.split()[-1]
    sents = [s for s in re.split(r"(?<=[.!?])\s+", reason) if last in s]
    txt = " ".join(sents) or reason
    assistant = re.search(r"\b(assistant|associate head)\b", txt, re.I)
    head = re.search(r"\bhead coach\b", re.sub(r"(assistant|associate|interim)\s+head coach", "", txt, flags=re.I), re.I)
    if assistant and not head:
        return True
    if head:
        return False
    return None


def changes(raw=None):
    """Every college hoops coaching change on file: [{season (the page's start year), team (Wikipedia's name), former,
    interim, new, date (the first date in the reason - the departure), midseason (that date falls Nov 1 - Mar 20 of
    the page season), first_time, reason}]."""
    if raw is None:
        with open(RAW) as f:
            raw = json.load(f)
    out = []
    for key, v in sorted(raw.items()):
        if not key.startswith("ncaab:"):
            continue
        page = int(key.split(":")[1])
        for sec in v.get("sections") or []:
            if "oaching changes" not in sec[:80]:
                continue
            for tb in re.findall(r"\{\|.*?\n\|\}", sec, re.S):
                hdr = [re.sub(r"<.*?>", " ", h).strip().lower() for h in re.findall(r"^!\s*([^\n]+)$", tb, re.M)]
                if not hdr or "team" not in hdr[0] or not any("new" in h for h in hdr):
                    continue
                for row in tb.split("\n|-")[1:]:
                    c = _cells(row)
                    if len(c) < 4:
                        continue
                    team = _name(c[0])
                    if not team:
                        continue
                    former, interim, new = _name(c[1]), _name(c[2]), _name(c[3]) if len(c) > 3 else None
                    reason = _clean(c[4]) if len(c) > 4 else ""
                    m = DATE.search(reason)
                    date = None
                    if m:
                        mo, dd = MONTHS[m.group(1)], int(m.group(2))
                        yr = int(m.group(3)) if m.group(3) else (page if mo >= 7 else page + 1)
                        date = f"{yr:04d}-{mo:02d}-{dd:02d}"
                    mid = bool(date) and bool(interim) and (f"{page}-11-01" <= date <= f"{page + 1}-03-10")
                    out.append({"season": page, "team": team, "former": former, "interim": interim, "new": new,
                                "date": date, "midseason": mid, "first_time": _first_time(reason, new),
                                "reason": reason[:300]})
    return out


def espn_current(espn=None):
    """{team id: coach name} from ESPN's newest college hoops season (right for today)."""
    if espn is None:
        try:
            with open(ESPN) as f:
                espn = json.load(f)
        except (OSError, ValueError):
            return {}, None
    seasons = (espn.get("ncaab") or {})
    if not seasons:
        return {}, None
    best = max(seasons, key=int)
    return {t: cs[0]["name"] for t, cs in seasons[best].items() if cs and cs[0].get("name")}, int(best) - 1


def team_ids(games):
    """{normalized name: team id} from our games file (college hoops only)."""
    out = {}
    for g in games.values():
        if g.get("league") != "ncaab":
            continue
        for side in ("home", "away"):
            if g.get(side + "_name") and g.get(side):
                out.setdefault(norm(g[side + "_name"]), str(g[side]))
    return out


def build(games=None, raw=None, espn=None, last_season=None, path=PATH):
    """The coach table {team id: {season: {coach, since, new, interim, mid (date), first_time}}} for seasons FIRST ..
    last_season (the current one), saved to `path` (None = don't save). Returns (table, report)."""
    if games is None:
        games = sd.load_games()
    ids = team_ids(games)
    cur, cur_season = espn_current(espn)
    last_season = last_season or cur_season or FIRST
    ch = changes(raw)
    by = {}
    unmatched = set()
    for c in ch:
        tid = match(c["team"], ids)
        if not tid:
            unmatched.add(c["team"])
            continue
        by.setdefault(tid, []).append(c)
    table = {}
    agree = disagree = 0
    for tid in set(by) | set(cur):
        evs = sorted(by.get(tid, []), key=lambda c: c["season"])
        now = cur.get(tid)
        # the coach going INTO season FIRST: the 'former' of the first change, else today's coach (no change since)
        coach = evs[0]["former"] if evs else now
        since = None                                     # (unknown - he was there before our first page)
        first_time = None
        rows = {}
        for s in range(FIRST, last_season + 1):
            ev = next((e for e in evs if e["season"] == s), None)
            row = {"coach": coach, "since": since, "new": since == s, "first_time": first_time if since == s else None,
                   "interim": False, "mid": None}
            if ev and ev["midseason"]:                   # a change during this season: the interim from that date
                row["mid"] = ev["date"]
                row["interim_coach"] = ev["interim"] or ev["new"]
            rows[s] = row
            if ev:                                       # next season's coach
                nxt = ev["new"] or ev["interim"]
                if nxt and nxt != coach:
                    coach, since, first_time = nxt, s + 1, ev["first_time"]
                elif not nxt:
                    coach, since, first_time = None, None, None
        if now and coach:
            if _same(now, coach):
                agree += 1
            else:
                disagree += 1
                rows[last_season]["coach_espn"] = now
        elif now and not coach:
            rows[last_season]["coach"] = now
        table[tid] = {str(s): r for s, r in rows.items()}
    report = {"changes": len(ch), "unmatched_teams": sorted(unmatched), "teams": len(table),
              "espn_agrees": agree, "espn_disagrees": disagree, "last_season": last_season}
    if path:
        with open(path, "w") as f:
            json.dump({"_why": "college hoops head coach by season (the start year), rebuilt from Wikipedia's "
                               "coaching-change tables + ESPN's current list - sports_ncaab_coaches.build()",
                       "_report": report, "teams": table}, f, separators=(",", ":"))
    return table, report


def _same(a, b):
    """The same man: the last name agrees ('Trey Johnson' / 'Trey Johnson III')."""
    def last(n):
        w = [x for x in _clean(n).replace(",", "").split() if x.lower().strip(".") not in ("jr", "sr", "ii", "iii", "iv")]
        return w[-1].lower() if w else ""
    return last(a) == last(b) or _clean(a).lower() == _clean(b).lower()


_LOADED = {}


def load(path=None):
    """The saved coach table {team id: {season: row}} ({} when there is none) - read once per file change."""
    path = path or PATH
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _LOADED.get(path)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        with open(path) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    table = d.get("teams") or {}
    _LOADED[path] = (mt, table)
    return table


def state(team, start, table=None):
    """The team's coach row for the season of `start` (+ 'tenure': seasons with the team incl. this one, None when
    he was there before our first page), or None when the team / season isn't on file."""
    if table is None:
        table = load()
    start = str(start or "")
    if len(start) < 7:
        return None
    y, m = int(start[:4]), int(start[5:7])
    s = y if m >= 7 else y - 1
    row = (table.get(str(team)) or {}).get(str(s))
    if not row or not row.get("coach"):
        return None
    out = dict(row)
    out["season"] = s
    out["tenure"] = (s - row["since"] + 1) if row.get("since") else None
    out["tenure_min"] = out["tenure"] if out["tenure"] else (s - FIRST + 1)
    return out


if __name__ == "__main__":
    _, rep = build()
    print({k: v for k, v in rep.items() if k != "unmatched_teams"}, "unmatched:", rep["unmatched_teams"])
