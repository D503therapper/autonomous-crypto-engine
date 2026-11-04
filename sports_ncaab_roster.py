"""🏀 COLLEGE HOOPS ROSTERS FROM THE BOX SCORES (the owner, 11/3: "We are missing something. Dig deep ... figure out the
edge out of the basketball"). The 11/3 DEEP study (results/studies/deep_cbb_roster/, SPORTS_FINDINGS "11/3 - DEEP:
COLLEGE HOOPS ROSTERS") read every college hoops box score 2021-26 (data/sports/roster/ncaab_<season>.csv.gz - every
player every game, ESPN's athlete id survives a transfer) against ESPN's close and open. What held, and lives here:

  top_out - THE TOP SCORER MISSED THE LAST GAME (BUILT as weights in sports.py - sports.mark_ncaab_top_out):
      the team's leader in points a game this season (3+ games played, 20+ minutes a game, the team 3+ box games in)
      is NOT in the box of the team's last game. Known before tip, and the market under-prices it: the team falls
      short of its close by 0.94 points (z -3.35) / 4.3 win-% points (z -4.04), every season 2022-25 (-1.03 / -0.88 /
      -1.11 / -0.76 pts); the flagged dog -20.5% on 617 vs -5.7% for the other dogs (train 2022-23 -26.0%, held out
      2024 -26.2% / 2025 -8.2%), at ESPN's OPEN -20.7% vs -7.9%; the flagged side ATS -10.8% on 1,521 vs -4.4% (0 of
      2 train / 0 of 2 held out at or over the base). Worse inside every existing college hoops flag (the skid, 'lost /
      won', the favorite lost its last) - new information, not those weights again. Only the TOP scorer: the 2nd scorer
      missing is nothing (+5.0 / +4.0 over the base).
  tin_m - TRANSFER STRENGTH (a LEAD, tracked only - sports_leads): last season's points the team's D1 transfers
      scored elsewhere, each x his old team's average margin / 10, over this team's own last-season points.

No box on file for the last game (or fewer than 3 box games) = UNKNOWN = no flag, never a guess."""
import csv
import gzip
import json
import os

import sports_data as sd

DIR = os.path.join(sd.DATA, "roster")
TOP_MIN_GAMES = 3            # the top scorer: 3+ games played this season...
TOP_MIN_MPG = 20             # ...at 20+ minutes a game (the study's 'star' - a bench gunner in 3 games isn't one)
TEAM_MIN_BOX = 3             # the team needs 3+ box games this season before the flag can fire
_CACHE = {}                  # season -> (mtime, {team: [(start, gid, {pid: (min, pts, name)})]})


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def team_boxes(season):
    """{team id: [(start, gid, {pid: (minutes, points, name)})] oldest first} for one college hoops season (cached on
    the file's mtime - the rosters job adds games every 3 hours)."""
    path = os.path.join(DIR, f"ncaab_{season}.csv.gz")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _CACHE.get(season)
    if hit and hit[0] == mt:
        return hit[1]
    by = {}
    try:
        with gzip.open(path, "rt", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    st = json.loads(r.get("stats") or "{}")
                except ValueError:
                    continue
                d = by.setdefault(r["team"], {}).setdefault(r["gid"], (r["start"], {}))
                d[1][r["pid"]] = (_num(st.get("minutes")), _num(st.get("points")), r.get("player") or "?")
    except (OSError, EOFError, ValueError):
        return {}
    out = {t: sorted((s, gid, ps) for gid, (s, ps) in d.items()) for t, d in by.items()}
    _CACHE[season] = (mt, out)
    return out


_IDX = {}                    # (id(games), len(games)) -> {team: [(start, gid)] sorted} - one pass a run


def _finals(games):
    key = (id(games), len(games or {}))
    if key not in _IDX:
        _IDX.clear()
        by = {}
        for gid, g in (games or {}).items():
            if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final":
                continue
            if str(g.get("stype") or "2") not in sd.REAL or not str(g.get("id") or gid).startswith("ncaab"):
                continue
            s = str(g.get("start") or "")
            for t in (g.get("home"), g.get("away")):
                by.setdefault(str(t), []).append((s, g.get("id") or gid))
        for v in by.values():
            v.sort()
        _IDX[key] = by
    return _IDX[key]


def _last_final(games, team, start):
    """The team's last finished real college hoops game this season before `start` (from the games file), or None."""
    lo = f"{season_of(start)}-07-01"
    best = None
    for s, gid in _finals(games).get(str(team)) or []:
        if lo <= s < start:
            best = (s, gid)
    return best


def top_scorer(boxes, before):
    """(pid, name, points a game) of the team's leader in points a game in `boxes` before `before`, or None."""
    gp = {}
    for s, _, ps in boxes:
        if s >= before:
            break
        for pid, (m, pts, name) in ps.items():
            if m > 0:
                g = gp.setdefault(pid, [0, 0.0, 0.0, name])
                g[0] += 1
                g[1] += pts
                g[2] += m
    cand = [(g[1] / g[0], pid, g[3]) for pid, g in gp.items() if g[0] >= TOP_MIN_GAMES and g[2] / g[0] >= TOP_MIN_MPG]
    if not cand:
        return None
    ppg, pid, name = max(cand)
    return pid, name, round(ppg, 1)


def top_out(games, team, start):
    """None (unknown) or {"out": bool, "name": .., "ppg": ..}: did the team's top scorer miss its last game?"""
    start = str(start or "")
    if len(start) < 10:
        return None
    try:
        boxes = team_boxes(season_of(start)).get(str(team)) or []
    except Exception:                                        # noqa: BLE001
        return None
    before = [b for b in boxes if b[0] < start]
    if len(before) < TEAM_MIN_BOX:
        return None
    last = _last_final(games, team, start)
    if not last:
        return None
    lastbox = next((ps for s, gid, ps in before if gid == last[1]), None)
    if lastbox is None:                                      # the last game's box isn't on file yet: unknown
        return None
    top = top_scorer(before, start)
    if not top:
        return None
    pid, name, ppg = top
    m = (lastbox.get(pid) or (0, 0, ""))[0]
    return {"out": m <= 0, "name": name, "ppg": ppg}


# ---------------- the transfer-strength LEAD (tracked only) ----------------
TIN_M_CUT = 0.03             # the top third of the 2022-25 seasons (games 6-10: 0.026 / 0.014 / 0.031 / 0.039)
TIN_GAMES = (6, 10)          # the team's games 6-10
_LAST = {}                   # season -> ({pid: {team: points}}, {team: points}, {team: avg margin})


def _last_season(games, season):
    if season in _LAST:
        return _LAST[season]
    pp, tp = {}, {}
    for t, lst in team_boxes(season).items():
        for _, _, ps in lst:
            for pid, (m, pts, _) in ps.items():
                if m > 0:
                    pp.setdefault(pid, {}).setdefault(t, 0.0)
                    pp[pid][t] += pts
                    tp[t] = tp.get(t, 0.0) + pts
    marg = {}
    for g in (games or {}).values():
        if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final":
            continue
        s = str(g.get("start") or "")
        if len(s) < 10 or season_of(s) != season:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        marg.setdefault(str(g["home"]), []).append(hs - as_)
        marg.setdefault(str(g["away"]), []).append(as_ - hs)
    out = (pp, tp, {t: sum(v) / len(v) for t, v in marg.items()})
    _LAST[season] = out
    return out


def tin_m(games, team, start):
    """Transfer strength before tonight (None = unknown): the men in this season's boxes so far who scored for ANOTHER
    D1 team last season - their points there x that team's average margin / 10 - over this team's last-season points."""
    start = str(start or "")
    if len(start) < 10:
        return None
    s = season_of(start)
    team = str(team)
    roster = set()
    for st, _, ps in team_boxes(s).get(team) or []:
        if st >= start:
            break
        roster |= {p for p, v in ps.items() if v[0] > 0}
    pp, tp, marg = _last_season(games, s - 1)
    if not roster or not tp.get(team):
        return None
    v = sum(pts * marg.get(ot, 0.0) / 10 for pid in roster for ot, pts in (pp.get(pid) or {}).items() if ot != team)
    return v / tp[team]


# ---------------- 11/3 FABLE second opinion: rebounding from the box scores (BUILT as weights) ----------------
REB_MIN_GAMES = 5            # a team's rebound margin counts after 5 box games (both teams' boxes on the same game)
_REB = {}                    # season -> (mtime, {team: [(start, gid, margin)] oldest first})


def team_rebounds(season):
    """{team id: [(start, gid, rebound margin)]} this college hoops season - the team's rebounds minus the opponent's
    in every game whose box holds BOTH teams (cached on the file's mtime)."""
    path = os.path.join(DIR, f"ncaab_{season}.csv.gz")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _REB.get(season)
    if hit and hit[0] == mt:
        return hit[1]
    by = {}                                                  # gid -> {team: (start, rebounds)}
    try:
        with gzip.open(path, "rt", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    st = json.loads(r.get("stats") or "{}")
                except ValueError:
                    continue
                d = by.setdefault(r["gid"], {})
                s, reb = d.get(r["team"], (r["start"], 0.0))
                d[r["team"]] = (s, reb + _num(st.get("rebounds")))
    except (OSError, EOFError, ValueError):
        return {}
    out = {}
    for gid, teams in by.items():
        if len(teams) != 2:
            continue
        (ta, (sa, ra)), (tb, (sb, rb)) = teams.items()
        out.setdefault(ta, []).append((sa, gid, ra - rb))
        out.setdefault(tb, []).append((sb, gid, rb - ra))
    out = {t: sorted(v) for t, v in out.items()}
    _REB[season] = (mt, out)
    return out


def reb_margin(team, start):
    """The team's average rebound margin a game this season before `start` (REB_MIN_GAMES+ box games), else None."""
    start = str(start or "")
    if len(start) < 10:
        return None
    try:
        rows = [m for s, _, m in (team_rebounds(season_of(start)).get(str(team)) or []) if s < start]
    except Exception:                                        # noqa: BLE001
        return None
    if len(rows) < REB_MIN_GAMES:
        return None
    return round(sum(rows) / len(rows), 2)


# ---------------- 11/3 KNOWLEDGE (A): availability in-season + the roster mix late (BUILT as weights) ----------------
REG_TOP = 7                  # the team's REGULARS: its top 7 by minutes a game this season before tonight...
REG_MIN_MPG = 15             # ...at 15+ a game
LONG_OUT_GAMES = 4           # a regular missing the last 4+ games running (the 11/3 KNOWLEDGE (A) study 2: the dog with
#                              one -15.0% on 847 vs -8.2% for other dogs, 0 of 2 train / 0 of 3 held out up, ESPN's open
#                              -21.8%; Jan-Mar -13.8% on 826; the 2-3 game absence -6.2% = the base - the market prices
#                              the fresh news and then STOPS adjusting as the absence runs on). Never the top scorer -
#                              he's the built 11/3 DEEP top_out weight. A -2 on the dog's study points (sports.dog_spots).
LONG_OUT_MIN_BOX = 5         # the team needs 5+ box games this season before the flag can fire
TIN_HEAVY = 0.28             # 11/3 KNOWLEDGE (A) study 3: the top third of teams by this season's minutes played by D1
NEW_HEAVY = 0.26             # transfers (0.27-0.28 in 2022-25) / by newcomers with no earlier D1 box (0.25-0.29).
#                              Feb-Mar: the transfer-heavy side ATS -7.3% (Feb) / -6.5% (Mar) on 3,979 vs -4.4%, the
#                              60%+-new roster -8.8% on 3,519 (0 of 1 train / 0 of 3 held up); the freshman-heavy side
#                              vs an experienced team +2.6% on 1,236 and the experienced team across it -11.4% (0 of 4
#                              seasons up) - the young team is the one still improving in February. Spread-rank
#                              weights ±0.02 (sports.ncaab_roster_spread_w), never a gate.
PAST_SEASONS = 4             # a newcomer = no minutes in any of the last 4 seasons' boxes
_PIDS = {}                   # season -> (mtime, {pid with minutes})


def regulars(boxes, before):
    """[(pid, name, minutes a game, games)] - the team's top REG_TOP men by minutes a game before `before`."""
    gp = {}
    for s, _, ps in boxes:
        if s >= before:
            break
        for pid, (m, pts, name) in ps.items():
            if m > 0:
                g = gp.setdefault(pid, [0, 0.0, name])
                g[0] += 1
                g[1] += m
    n = sum(1 for s, _, _ in boxes if s < before)
    cand = sorted(((g[1] / n, pid, g[2], g[0], g[1]) for pid, g in gp.items() if n and g[1] / n >= REG_MIN_MPG), reverse=True)
    return [(pid, name, round(mins / games, 1), games) for _, pid, name, games, mins in cand[:REG_TOP]]   # (minutes a
    #                                                                       game PLAYED on the card; ranked over team games)


def long_out(games, team, start):
    """None (unknown) or {"n": how many regulars (not the top scorer) have missed the last LONG_OUT_GAMES+ games,
    "who": [(name, minutes a game, games missed)]} - from this season's box scores, known before tip."""
    start = str(start or "")
    if len(start) < 10:
        return None
    try:
        boxes = team_boxes(season_of(start)).get(str(team)) or []
    except Exception:                                        # noqa: BLE001
        return None
    before = [b for b in boxes if b[0] < start]
    if len(before) < LONG_OUT_MIN_BOX:
        return None
    last = _last_final(games, team, start)
    if not last or not any(gid == last[1] for _, gid, _ in before):
        return None                                          # (the last game's box isn't on file yet: unknown)
    top = top_scorer(before, start)
    who = []
    for pid, name, mpg, _ in regulars(before, start):
        if top and pid == top[0]:
            continue
        run = 0
        for _, _, ps in reversed(before):
            if (ps.get(pid) or (0, 0, ""))[0] > 0:
                break
            run += 1
        if run >= LONG_OUT_GAMES:
            who.append((name, mpg, run))
    return {"n": len(who), "who": who}


def _pids(season):
    """{pid} with minutes in that season's boxes (cached on the file's mtime)."""
    path = os.path.join(DIR, f"ncaab_{season}.csv.gz")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return set()
    hit = _PIDS.get(season)
    if hit and hit[0] == mt:
        return hit[1]
    out = set()
    for lst in team_boxes(season).values():
        for _, _, ps in lst:
            out.update(p for p, v in ps.items() if v[0] > 0)
    _PIDS[season] = (mt, out)
    return out


def roster_mix(games, team, start):
    """None (unknown) or {"n": box games, "tin": the share of the team's minutes so far by D1 TRANSFERS (men who
    scored for another D1 team last season), "new": the share by NEWCOMERS (no minutes in any of the last
    PAST_SEASONS seasons' boxes)}."""
    start = str(start or "")
    if len(start) < 10:
        return None
    s = season_of(start)
    try:
        boxes = [b for b in (team_boxes(s).get(str(team)) or []) if b[0] < start]
    except Exception:                                        # noqa: BLE001
        return None
    if len(boxes) < TEAM_MIN_BOX:
        return None
    pp, _, _ = _last_season(games, s - 1)
    old = set()
    for k in range(1, PAST_SEASONS + 1):
        old |= _pids(s - k)
    if not old:
        return None                                          # (no earlier box on file at all: nothing to compare to)
    tot = tin = new = 0.0
    for _, _, ps in boxes:
        for pid, (m, _, _) in ps.items():
            if m <= 0:
                continue
            tot += m
            lp = pp.get(pid) or {}
            if any(ot != str(team) for ot in lp):
                tin += m
            elif pid not in old:
                new += m
    if not tot:
        return None
    return {"n": len(boxes), "tin": round(tin / tot, 3), "new": round(new / tot, 3)}


CUT_MIN_TEAMS = 100          # the season's own top-third cuts need 100+ teams with a roster read; else the fixed ones
CUT_MIN_BOX = 10             # ...each with 10+ box games (the study's rows), so the thin non-D1 rosters don't set the cut
_CUTS = {}                   # (season, day) -> (tin cut, new cut, teams)


def roster_cuts(games, start):
    """(transfer-heavy cut, freshman-heavy cut, teams read): the top third of this season's D1 teams on each share as
    of `start` (the study ranked WITHIN the season - the portal era moves the whole distribution year to year); the
    fixed TIN_HEAVY / NEW_HEAVY when fewer than CUT_MIN_TEAMS teams have a read. Cached per day."""
    start = str(start or "")
    if len(start) < 10:
        return TIN_HEAVY, NEW_HEAVY, 0
    key = (season_of(start), start[:10])
    if key in _CUTS:
        return _CUTS[key]
    tins, news = [], []
    try:
        for team in list(team_boxes(key[0]).keys()):
            m = roster_mix(games, team, start)
            if m and m["n"] >= CUT_MIN_BOX:                  # (D1 teams well into the season, as the study's rows were)
                tins.append(m["tin"])
                news.append(m["new"])
    except Exception:                                        # noqa: BLE001
        return TIN_HEAVY, NEW_HEAVY, 0
    if len(tins) < CUT_MIN_TEAMS:
        out = (TIN_HEAVY, NEW_HEAVY, len(tins))
    else:
        tins.sort()
        news.sort()
        out = (round(tins[int(len(tins) * 2 / 3)], 3), round(news[int(len(news) * 2 / 3)], 3), len(tins))
    _CUTS.clear()
    _CUTS[key] = out
    return out
