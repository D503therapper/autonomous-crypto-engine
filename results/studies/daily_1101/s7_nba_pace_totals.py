"""Study 7 (11/1): NBA TOTALS vs THE PACE MATCHUP (the owner's example list; "an NBA totals read (never built)" was a
10/29 NEXT). From our box scores, every team-game's possessions = FGA - offensive rebounds + turnovers + 0.44 x FTA
(the standard estimate). Each team's season-to-date pace (both teams' possessions a game, averaged) and points per 100
possessions scored / allowed - 10+ games in, games before tonight only. The matchup's expected total = the two paces
averaged x the two offense-vs-defense matchups ((A's offense + B's defense)/2 + (B's offense + A's defense)/2), home
edge left out (it moves the side, not the total). Bet the OVER when the expected total sits 3 / 5 / 8+ over the closing
total, the UNDER when it sits that far under - at the closing total and its juice. Second cut: the pace MISMATCH (a top-
third pace team vs a bottom-third one) and both fast / both slow, against every game. Train 2018-22, held out 2023 /
2024 / 2025 / 2026 apart."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2022), (2023, 2024, 2025, 2026)


def nba_poss(st, r):
    try:
        fgm, fga = (int(x) for x in st["fieldGoalsMade-fieldGoalsAttempted"].split("-"))
        ftm, fta = (int(x) for x in st["freeThrowsMade-freeThrowsAttempted"].split("-"))
        return (fga, int(st.get("offensiveRebounds") or 0), int(st.get("turnovers") or 0), fta)
    except (KeyError, ValueError, AttributeError):
        return None


bx = lib.boxes("nba", nba_poss)
team_poss = {}                                    # (gid, team) -> possessions
for gid, teams in bx.items():
    for t, pl in teams.items():
        fga = sum(v[0] for v in pl.values())
        orb = sum(v[1] for v in pl.values())
        to = sum(v[2] for v in pl.values())
        fta = sum(v[3] for v in pl.values())
        if fga > 50:
            team_poss[(gid, t)] = fga - orb + to + 0.44 * fta

hist = defaultdict(list)                          # (season, team) -> [(start, pace, ppp_for, ppp_against)]
fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
C = lib.Cells()
rows = []
for g in fin:
    s = g["season"]
    st = {}
    for t in (g["home"], g["away"]):
        h = hist[(s, t)]
        if len(h) >= 10:
            n = len(h)
            st[t] = (sum(x[1] for x in h) / n, sum(x[2] for x in h) / n, sum(x[3] for x in h) / n)
    ph, pa = team_poss.get((g["id"], g["home"])), team_poss.get((g["id"], g["away"]))
    if len(st) == 2 and g["total"]:
        A, B = st[g["home"]], st[g["away"]]
        pace = (A[0] + B[0]) / 2
        exp = pace * ((A[1] + B[2]) / 2 + (B[1] + A[2]) / 2)
        rows.append((g, s, exp - g["total"], A[0], B[0]))
    if ph and pa:
        p = (ph + pa) / 2
        hist[(s, g["home"])].append((g["start"], p, g["hs"] / ph, g["as"] / pa))
        hist[(s, g["away"])].append((g["start"], p, g["as"] / pa, g["hs"] / ph))

# pace thirds within each season, from tonight's teams' season-to-date paces (cut points from all rows of the season)
by_s = defaultdict(list)
for g, s, gap, pA, pB in rows:
    by_s[s] += [pA, pB]
cuts = {s: (sorted(v)[len(v) // 3], sorted(v)[2 * len(v) // 3]) for s, v in by_s.items()}
for g, s, gap, pA, pB in rows:
    o, u = lib.tot_profit(g, True), lib.tot_profit(g, False)
    C.add("OVER | every game", s, o)
    C.add("UNDER | every game", s, u)
    for k in (3, 5, 8):
        if gap >= k:
            C.add(f"OVER | expected {k}+ over the total", s, o)
        if gap <= -k:
            C.add(f"UNDER | expected {k}+ under the total", s, u)
    lo, hi = cuts[s]
    fa, fb = (pA >= hi) - (pA <= lo), (pB >= hi) - (pB <= lo)
    kind = "pace MISMATCH (fast vs slow)" if fa * fb == -1 else "both FAST" if fa == fb == 1 else \
        "both SLOW" if fa == fb == -1 else None
    if kind:
        C.add(f"OVER | {kind}", s, o)
        C.add(f"UNDER | {kind}", s, u)
    md = g["start"][5:7]
    if md in ("10", "11", "12"):
        for k in (5,):
            if gap >= k:
                C.add(f"OVER | expected {k}+ over the total | Oct-Dec", s, o)
            if gap <= -k:
                C.add(f"UNDER | expected {k}+ under the total | Oct-Dec", s, u)

C.dump("s7", f"NBA TOTALS vs THE PACE MATCHUP (closing total + juice; {len(rows)} games with 10+ games of pace for both; "
       "train 2018-22, held 2023-26)", TR, HE)
