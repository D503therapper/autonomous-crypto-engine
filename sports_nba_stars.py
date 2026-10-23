"""🌟 NBA STAR POWER (the owner, 10/23 - the 76ers +155 at the Knicks, won 106-100: "look at the squad - Jaylen Brown,
Maxey, Edgecombe, Embiid, LeBron James ... anyone can look at that and say that line don't make no sense. The engine
needs to know that too").

What a human sees that the box scores don't: reputation. This module reads data/sports/nba_stars.json - All-Star
selections, All-NBA teams, MVP top-5, the All-Rookie first team by season, the top-10 picks by draft - and gives every
player a STAR VALUE for a season from the seasons BEFORE it only (never this season's honors - they come in February /
May; a prior All-Star is a fact the night the season opens):

    All-NBA first team 4 / second or third 3 / an All-Star 2 (+1 for an MVP top-5 finish), the best of the last three
    seasons, worth 1 / 0.7 / 0.5 by how long ago; a top-5 pick in his first three seasons 1 (a top-10 pick 0.5);
    the All-Rookie first team last season 1.5.

A team's STAR SCORE = the sum over the men on the floor tonight; a "star" = value 2+ (an All-Star within three seasons).
The data: the seasons marked "claude-knowledge" were compiled from Claude's own knowledge (tools/nba_stars_compiled.py);
the nba_stars workflow (tools/nba_stars_fetch.py) replaces them from Basketball-Reference when it runs. No file = no
star read anywhere (never a fact we can't see).

The 10/23 study (SPORTS_FINDINGS 10/23 "star power"): WHETHER this read beats the price is what the study answers - the
engine only weighs what validates (the owner's rule: a weight, never a trigger)."""
import json
import os
import re

import sports_data as sd

PATH = os.path.join(sd.DATA, "nba_stars.json")
ALL_NBA_1, ALL_NBA_23, ALL_STAR, MVP_BONUS = 4.0, 3.0, 2.0, 1.0
DECAY = (1.0, 0.7, 0.5)         # this season's honors come later; last season 1, two ago 0.7, three ago 0.5
TOP5_PICK, TOP10_PICK = 1.0, 0.5
PICK_SEASONS = 3                # a top pick carries his draft slot for his first three seasons
ALL_ROOKIE, ALL_ROOKIE_SEASONS = 1.5, 2
STAR = 2.0                      # a "star" on a card = value 2+ (an All-Star within three seasons)


def _nm(x):
    return " ".join(re.sub(r"[^a-z ]", "", str(x or "").lower().replace(" jr", "").replace(" iii", "")
                           .replace(" ii", "")).split())


_CACHE = {}


def load(path=PATH):
    """The star file -> {"honors": {name: {end_year: (points, label)}}, "picks": {name: (draft year, slot)},
    "rookie": {name: end_year}, "seasons": [end years held]} or None when there's no file."""
    if path in _CACHE:
        return _CACHE[path]
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        _CACHE[path] = None
        return None
    honors, rookie = {}, {}
    for y, s in (raw.get("seasons") or {}).items():
        try:
            y = int(y)
        except ValueError:
            continue
        pts = {}
        for t, names in (s.get("all_nba") or {}).items():
            for n in names or []:
                pts[_nm(n)] = (ALL_NBA_1 if str(t) == "1" else ALL_NBA_23, f"All-NBA {y}")
        for n in s.get("all_star") or []:
            pts.setdefault(_nm(n), (ALL_STAR, f"{y} All-Star"))
        for n in s.get("mvp_top5") or []:
            k = _nm(n)
            p, lab = pts.get(k, (ALL_STAR, f"{y} All-Star"))
            pts[k] = (p + MVP_BONUS, lab + ", top-5 MVP")
        for n in s.get("all_rookie_1") or []:
            rookie.setdefault(_nm(n), y)
        for k, v in pts.items():
            honors.setdefault(k, {})[y] = v
    picks = {}
    for d, names in (raw.get("draft") or {}).items():
        try:
            d = int(d)
        except ValueError:
            continue
        for i, n in enumerate(names or []):
            picks.setdefault(_nm(n), (d, i + 1))
    out = {"honors": honors, "picks": picks, "rookie": rookie,
           "seasons": sorted(int(y) for y in (raw.get("seasons") or {}) if str(y).isdigit()),
           "sources": {str(y): (s or {}).get("source", "") for y, s in (raw.get("seasons") or {}).items()}}
    _CACHE[path] = out
    return out


def value(name, season, data=None):
    """A player's star value for a season (its START year: 2026 = 2026-27) from the honors of the seasons before it
    -> (points, label) - (0, "") for nobody we know."""
    data = data if data is not None else load()
    if not data:
        return 0.0, ""
    k = _nm(name)
    best, lab = 0.0, ""
    for i, w in enumerate(DECAY):
        y = season - i                                   # end year = start year (last season ended in `season`)
        p, l = (data["honors"].get(k) or {}).get(y, (0.0, ""))
        if p * w > best:
            best, lab = p * w, l
    pk = data["picks"].get(k)
    if pk and 0 <= season - pk[0] < PICK_SEASONS:
        pts = TOP5_PICK if pk[1] <= 5 else TOP10_PICK
        if pts > best:
            best, lab = pts, f"the #{pk[1]} pick in {pk[0]}"
    ry = data["rookie"].get(k)
    if ry is not None and 0 <= season - ry < ALL_ROOKIE_SEASONS and ALL_ROOKIE > best:
        best, lab = ALL_ROOKIE, f"All-Rookie first team {ry}"
    return round(best, 2), lab


def team(names, season, data=None):
    """The men on the floor -> {"score": the sum, "stars": [(name, value, label)] for the value-2+ men, best first,
    "n": how many}."""
    data = data if data is not None else load()
    vals = []
    for n in names or []:
        v, lab = value(n, season, data)
        if v > 0:
            vals.append((n, v, lab))
    vals.sort(key=lambda x: -x[1])
    stars = [x for x in vals if x[1] >= STAR]
    return {"score": round(sum(v for _, v, _ in vals), 2), "stars": stars, "n": len(stars)}


def covered(season, data=None):
    """Do we hold honors for the season before this one? (no = no star read - never a fact we can't see)"""
    data = data if data is not None else load()
    return bool(data) and season in set(data["seasons"])


def verified(season, data=None):
    """Were last season's honors READ from the source (Basketball-Reference, source 'bbref') - not the list compiled
    from Claude's memory? Only verified honors go on a card (the owner: never a fact we can't fully see)."""
    data = data if data is not None else load()
    return covered(season, data) and data["sources"].get(str(season)) == "bbref"


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


def card_line(g, side, cur, data=None):
    """🌟 The card's star-power FACT line for an NBA side (info, never a weight - the 10/23 study: the close prices
    the stars): "🌟 76ers: LeBron James (All-NBA 2026) and Joel Embiid (2026 All-Star) are in the lineup tonight ·
    Paul George is out." Quiet unless the saved rosters are there AND last season's honors were fetched from the
    source (never the compiled list). "" = nothing to say."""
    data = data if data is not None else load()
    if not cur or not data:
        return ""
    tid = str(g[side])
    teams = cur.get("teams") or {}
    if tid not in teams:
        return ""
    season = season_of(g["start"])
    if not verified(season, data):
        return ""
    out = {_nm(x) for x in ((cur.get("flags") or {}).get(tid) or {}).get("out") or []}
    names = [p.get("name") for p in teams[tid] if p.get("name")]
    on = team([n for n in names if _nm(n) not in out], season, data)
    sat = team([n for n in names if _nm(n) in out], season, data)["stars"]
    parts = []
    if on["n"]:
        # the stars BY NAME, never a count (10/23, the owner: "1 star on the floor tonight - Jayson Tatum ... that sounds
        # bad" - a count reads like a weakness; and the 2025 / 2026 All-Star lists are the final's box only)
        named = [f"{n} ({lab})" for n, _, lab in on["stars"][:4]]
        parts.append((named[0] if len(named) == 1 else ", ".join(named[:-1]) + " and " + named[-1])
                     + (" is" if len(named) == 1 else " are") + " in the lineup tonight")
    if sat:
        parts.append(", ".join(n for n, _, _ in sat[:2]) + (" is out" if len(sat) == 1 else " are out"))
    return f"🌟 {g[side + '_name']}: {' · '.join(parts)}." if parts else ""
