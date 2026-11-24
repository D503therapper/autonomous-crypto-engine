"""Every matchup category's two halves (ours / theirs, in spreads) for the unit cards of one day - what the case
builder ranks. python results/studies/cards_1124/halves.py 2026-11-24"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.getcwd())
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cards_1122"))
import h                                                    # noqa: E402
from h import games, picks, elo, v24                        # noqa: E402
import sports                                               # noqa: E402
import sports_card_sell as cs                               # noqa: E402

day = sys.argv[1] if len(sys.argv) > 1 else "2026-11-24"
cs.CASE_MIN, cs.CASE_HALF, cs.CASE_MAX = -99, -99, 99        # (show every category)
for pk in picks:
    if pk["date"] != day or pk.get("lean"):
        continue
    for leg in pk["legs"]:
        lg = leg["league"]
        if lg not in cs.CASE_BASE or leg["game_id"] not in games:
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            sports.sync_sides([leg], games, "dry run")
        g = games[leg["game_id"]]
        tid, oid = g[leg["side"]], g["away" if leg["side"] == "home" else "home"]
        start = v24._t(g["start"])
        fin = [x for x in h.sm.finals(games, lg) if v24._t(x["start"]) < start]
        if lg == "ncaab":
            v24._d1_set(fin)
        gu = v24._real(v24._season(v24._team_games(fin, tid), start), tid, lg)
        gt = v24._real(v24._season(v24._team_games(fin, oid), start), oid, lg)
        e = elo.get(lg)
        print(f"\n{leg['team']} vs {leg['opp']}: schedules {cs.sched(gu, tid, e):.0f} / {cs.sched(gt, oid, e):.0f}"
              f" (fair to compare: {lg not in v24.SCHEDULE_FAIR or cs.fair_cmp(gu, gt, tid, oid, e)})")
        pu, pt = cs.profile(lg, gu, tid), cs.profile(lg, gt, oid)
        if not pu or not pt:
            print("   not enough box scores")
            continue
        for k, sz, ways in cs.case_edges(lg, leg["team"], leg["opp"], pu, pt, "d1" if lg == "ncaab" else ""):
            print(f"   {k:9s} {sz:+.2f}  {ways[0]}")
