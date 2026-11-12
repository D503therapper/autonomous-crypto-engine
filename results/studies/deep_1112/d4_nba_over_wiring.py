"""11/12 DEEP PROGRAM - D4: THE NEW NBA OVER (3+ of the six top-minutes men sit), ITS WIRING AGAINST REAL BOX SCORES.
The live rule (sports_nba_out.team_minutes: each team's three men with the most minutes this season, by NAME, both
teams 10+ box games) is walked through two finished seasons game by game with only the box rows before each tip, and
'out tonight' read from the box score itself (no minutes) - the fact the injury report gives before the tip. Set
against the study's own table (fifteen_1112/box.py: the same men by player ID):
  - do the two pick the same men and flag the same games?
  - does the live rule's set of games reproduce the study's over record at the close?
Then THIS season: every team's top three as the live code names them today, and whether both are past 10 games.
Usage: python results/studies/deep_1112/d4_nba_over_wiring.py > results/studies/deep_1112/d4_nba_over_wiring.out"""
import json, os, sys
from collections import defaultdict
import dlib as D
import lib as L

os.chdir(D.ROOT)
sys.path.insert(0, D.ROOT)
import sports_nba_out as no     # noqa: E402
import sports_roster as R       # noqa: E402

rows = R.load("nba")
slim = []
mins_tonight = defaultdict(lambda: defaultdict(dict))        # gid -> team -> {name: minutes}
pid_tonight = defaultdict(lambda: defaultdict(dict))
for r in rows:
    try:
        m = float(json.loads(r.get("stats") or "{}").get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    slim.append({"start": r["start"], "team": r["team"], "gid": r["gid"], "player": r["player"], "stats": json.dumps({"minutes": m})})
    mins_tonight[r["gid"]][r["team"]][r["player"]] = m
    pid_tonight[r["gid"]][r["team"]][r["pid"]] = m
by_season = defaultdict(list)
for r in slim:
    by_season[no._season(r["start"])].append(r)
T = {g["id"]: g for g in L.table("nba")}
import box as B                 # noqa: E402  (fifteen_1112/box.py)
B.nba_stars(list(T.values()))
for season in (2024, 2025):
    games = sorted((g for g in T.values() if g["season"] == season and L.reg(g) and g["id"] in mins_tonight), key=lambda g: g["start"])
    live_set, study_set, same_men, checked, bets_live, bets_study = set(), set(), 0, 0, [], []
    for i, g in enumerate(games):
        tm = no.team_minutes(by_season[season], season, g["start"])
        n_out, ok = 0, True
        for t in (g["home"], g["away"]):
            info = tm.get(str(t))
            if not info or info["games"] < no.MIN_GAMES:
                ok = False
                break
            n_out += sum(1 for name, _, _ in info["top"] if mins_tonight[g["id"]][t].get(name, 0) <= 0)
        st_n = (g["H"].get("n_out"), g["A"].get("n_out"))
        if ok and None not in st_n:
            checked += 1
            same_men += (n_out == st_n[0] + st_n[1])
        if ok and n_out >= no.NEED_OUT:
            live_set.add(g["id"])
            bets_live.append((season, L.tot(g, "over")))
        if None not in st_n and st_n[0] + st_n[1] >= 3:
            study_set.add(g["id"])
            bets_study.append((season, L.tot(g, "over")))
    print(f"== {season}-{str(season + 1)[2:]}: {len(games)} regular-season games with a box score; both teams 10+ games in under BOTH rules: {checked}; "
          f"the count of top-minutes men out agrees in {same_men} ({100 * same_men / max(1, checked):.1f}%)")
    print(f"   games with 3+ of the six out - live rule {len(live_set)}, the study's table {len(study_set)}, both {len(live_set & study_set)}, live only {len(live_set - study_set)}, study only {len(study_set - live_set)}")
    L.cell("   the over at the close, the LIVE rule's games", bets_live, train_to=2099)
    L.cell("   the over at the close, the STUDY's games", bets_study, train_to=2099)
print("\n== THIS SEASON, as the live code sees it today")
now = "2026-11-12T23:00Z"
tm = no.team_minutes(by_season[2026], 2026, now)
names = {}
for g in T.values():
    names[g["home"]], names[g["away"]] = g["hn"], g["an"]
ready = sum(1 for t, v in tm.items() if v["games"] >= no.MIN_GAMES)
print(f"   teams with a box this season: {len(tm)}; at {no.MIN_GAMES}+ games: {ready}; fewest games: {min(v['games'] for v in tm.values())}")
for t, v in sorted(tm.items(), key=lambda kv: names.get(kv[0], kv[0])):
    print(f"   {names.get(t, t):14s} {v['games']:2d} games | " + ", ".join(f"{p} {mpg:.0f} min" for p, mpg, _ in v["top"]))
L.done()
