"""The live efficiency read on the next college hoops slate on file (offline, today's games files): every priced game's
model margin vs the spread, and which slight favorites the -3 filter would flag. Usage: python today.py [YYYY-MM-DD]"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_cbb_eff as ce  # noqa: E402
import sports_data as sd  # noqa: E402

games = sd.load_games()
day = sys.argv[1] if len(sys.argv) > 1 else None
pre = [g for g in games.values() if g["league"] == "ncaab" and g["status"] == "pre" and g.get("ml_home")]
if day:
    pre = [g for g in pre if g["start"][:10] == day]
else:
    first = min(ce.night_of(g["start"]) for g in pre)
    pre = [g for g in pre if ce.night_of(g["start"]) == first]
t = time.time()
reads = ce.read_many(games, [g["id"] for g in pre])
print(f"{len(pre)} priced games, read in {time.time() - t:.1f}s (all leagues' games in memory: {len(games)})")
flag = 0
for g in sorted(pre, key=lambda x: x["start"]):
    r = reads.get(g["id"])
    if not r:
        continue
    mk = sd.no_vig(int(float(g["ml_home"])), int(float(g["ml_away"])))
    note = ""
    for side, odds, p, m in (("home", int(float(g["ml_home"])), r["p_home"], mk),
                             ("away", int(float(g["ml_away"])), 1 - r["p_home"], 1 - mk)):
        if -150 <= odds <= -101 and p - m <= -0.03:
            note = f"  <- FILTER: {g[side + '_name']} {odds} (ratings {p:.0%} vs price {m:.0%})"
            flag += 1
    print(f"{g['start'][:16]} {g['away_name']:>18} @ {g['home_name']:<18} spread {g.get('spread_home') or '-':>6} "
          f"model {-r['margin']:+6.1f}{note}")
print(f"flagged slight favorites: {flag}")
