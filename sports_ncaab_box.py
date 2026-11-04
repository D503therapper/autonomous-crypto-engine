"""🏀 COLLEGE HOOPS TEAM IDENTITY FROM THE FULL TEAM BOX (the owner, 11/3: "If the engine is knowledgeable on the teams
... there's no reason why we should be complete losers"). The 11/3 KNOWLEDGE (A) study 4 (results/studies/
cbb_knowledge_a/s4_identity.py, SPORTS_FINDINGS "11/3 - FABLE: COLLEGE HOOPS KNOWLEDGE (A)") read the full team box
scores on disk (data/sports/teamstats/ncaab*.jsonl - turnovers, free throws, threes, rebounds; 2021-22 .. now) season
to date, walk-forward, both teams 5+ box games, against ESPN's close and open. What held, and lives here:

  identity(games, team, start) -> None (unknown: under TEAM_MIN_GAMES box games) or
      {"n": box games before `start`, "tom": turnover margin a game (forced minus committed),
       "off": points per 100 possessions over the D1 average so far this season, "def": allowed per 100 over it}
  TURNOVER-PRONE (tom <= TOM_PRONE, the bottom third): a -101..-150 moneyline favorite that coughs it up lost -9.7% on
      1,314 (train 2021-22 0 of 2 up, held out 2023-25 0 of 3; the open -7.2%; the bottom sixth -13.2%, home / away,
      Nov-Dec / Jan-Mar, both price halves all down) vs -4.2% for every small favorite - BUILT as a -2 weight on the
      favorite's read (sports.weigh_ncaab_to_fav). The dog across sits at the vig (+1.8%) - a nudge, never a trigger.
  OFFENSE-FIRST (off >= OFF_HI, the top third, and def > DEF_GOOD - not in the best defensive third): the dog in
      Jan-Mar -15.1% on 1,283 (0 of 2 / 0 of 3, the open -17.6%) vs -8.9% - but the dose is odd (a middling defense
      -18.7%, the worst third -9.0%) and Nov-Dec flips (+4.7%): a tracker LEAD only (sports_leads).
Points come from the games file (the team box carries no score); possessions = FGA - OREB + TO + 0.475 FTA."""
import glob
import json
import os

import sports_data as sd

TEAM_MIN_GAMES = 5           # a team's identity counts after 5 box games (the study's floor)
LEAGUE_MIN_GAMES = 100       # ...and once the season's D1 average stands on 100+ boxed games
TOM_PRONE = -0.5             # turnover margin a game at or under this = the bottom third (2021-25: -0.62 .. -0.44)
OFF_HI = 5.5                 # offense 5.5+ points per 100 possessions over the D1 average = the top third (5.2-5.7)
DEF_GOOD = -4.8              # defense allowing 4.8+ under the average = the best third (-5.0 .. -4.8)
OFF_LO = -0.5                # offense at or under 0.5 below the average = the bottom third (-0.77 .. -0.43). The 11/3
#                              KNOWLEDGE (A) dog view (s7): the DEFENSE-FIRST dog (def <= DEF_GOOD, off < OFF_HI) vs a
#                              bottom-third offense +14.0% on 313 (train 1 of 2 up, held out 3 of 3, the open +13.3%) -
#                              the one college hoops dog cell that paid; a tracker LEAD (sports_leads), z 1.9 only
_BOX = {}                    # stamp -> {gid: {team: dict(to, poss)}}
DATA = None                  # the data folder (None = sports_data.DATA; the tests point it at a temp folder)


def _split(s):
    a, b = str(s).split("-")
    return int(a), int(b)


def load_box(data=None):
    """{game id: {team id: dict(to, poss)}} from every team box on disk (cached on the files' sizes)."""
    data = data or DATA or sd.DATA
    files = [os.path.join(data, "teamstats", "ncaab.jsonl")] + sorted(glob.glob(os.path.join(data, "teamstats", "ncaab", "*.jsonl")))
    stamp = tuple((f, os.path.getsize(f)) for f in files if os.path.exists(f))
    if _BOX.get("stamp") == stamp:
        return _BOX["box"]
    out = {}
    for fn in files:
        try:
            fh = open(fn)
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    tm = {}
                    for tid, t in d["teams"].items():
                        fgm, fga = _split(t["fieldGoalsMade-fieldGoalsAttempted"])
                        ftm, fta = _split(t["freeThrowsMade-freeThrowsAttempted"])
                        oreb = int(t["offensiveRebounds"])
                        to = int(t.get("totalTurnovers") or t.get("turnovers") or 0)
                        tm[str(tid)] = dict(to=to, poss=fga - oreb + to + 0.475 * fta)
                    if len(tm) == 2:
                        out[str(d["gid"])] = tm
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue
    _BOX.clear()
    _BOX["stamp"], _BOX["box"] = stamp, out
    return out


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


_SEASON = {}                 # (season, len(box), len(games)) -> ({team: [(start, gid, line)]}, league sums by start)


def _season_lines(games, season):
    """Per team, its boxed finals this season in start order with (points, possessions, allowed, their possessions,
    turnovers, forced); and the league's running totals in the same order (for the D1 average before a date)."""
    box = load_box()
    key = (season, len(box), len(games or {}))
    hit = _SEASON.get(key)
    if hit:
        return hit
    rows = []
    for gid, g in (games or {}).items():
        if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final":
            continue
        s = str(g.get("start") or "")
        if len(s) < 10 or season_of(s) != season or str(g.get("stype") or "2") not in sd.REAL:
            continue
        b = box.get(str(g.get("id") or gid))
        if not b:
            continue
        h, a = str(g.get("home")), str(g.get("away"))
        if h not in b or a not in b:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append((s, str(g.get("id") or gid), h, a, hs, as_, b[h], b[a]))
    rows.sort()
    by, league = {}, []
    tp = tposs = 0.0
    for s, gid, h, a, hs, as_, bh, ba in rows:
        by.setdefault(h, []).append((s, gid, hs, bh["poss"], as_, ba["poss"], bh["to"], ba["to"]))
        by.setdefault(a, []).append((s, gid, as_, ba["poss"], hs, bh["poss"], ba["to"], bh["to"]))
        tp += hs + as_
        tposs += bh["poss"] + ba["poss"]
        league.append((s, tp, tposs, len(league) + 1))
    out = (by, league)
    _SEASON.clear()
    _SEASON[key] = out
    return out


def identity(games, team, start):
    """None (unknown) or {"n", "tom", "off", "def"} for the team before `start` (this season's boxed finals)."""
    start = str(start or "")
    if len(start) < 10:
        return None
    try:
        by, league = _season_lines(games, season_of(start))
    except Exception:                                        # noqa: BLE001
        return None
    mine = [r for r in by.get(str(team)) or [] if r[0] < start]
    if len(mine) < TEAM_MIN_GAMES:
        return None
    lg = None
    for s, tp, tposs, n in league:
        if s >= start:
            break
        lg = (tp, tposs, n)
    if not lg or lg[2] < LEAGUE_MIN_GAMES or not lg[1]:
        return None
    pts = sum(r[2] for r in mine)
    poss = sum(r[3] for r in mine)
    opts = sum(r[4] for r in mine)
    oposs = sum(r[5] for r in mine)
    if not poss or not oposs:
        return None
    avg = 100 * lg[0] / lg[1]
    return {"n": len(mine), "tom": round(sum(r[7] - r[6] for r in mine) / len(mine), 2),
            "off": round(100 * pts / poss - avg, 2), "def": round(100 * opts / oposs - avg, 2)}
