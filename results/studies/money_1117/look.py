"""11/17 MOST MONEY - a look at the board days with NO unit play on the rig (mlib.board): which months, how many games.
Usage: python results/studies/money_1117/look.py > results/studies/money_1117/look.out"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
R = M.D.r3()
games = defaultdict(set)
lgs = defaultdict(set)
for r in R:
    games[r["date"]].add(r["gid"])
    lgs[r["date"]].add(r["league"])
has = {r["date"] for r in P}
no = [d for d in DAYS if d not in has]
print(f"{len(DAYS)} board days, {len(no)} with no unit play ({100 * len(no) / len(DAYS):.1f}%)")
print("by month (no-play days / board days):")
m_all, m_no = Counter(d[5:7] for d in DAYS), Counter(d[5:7] for d in no)
print("  " + "  ".join(f"{m}: {m_no[m]}/{m_all[m]}" for m in sorted(m_all)))
b = Counter(min(len(games[d]), 10) for d in no)
print("no-play days by the games with a moneyline that day (10 = 10+): " + ", ".join(f"{k}: {v}" for k, v in sorted(b.items())))
big = [d for d in DAYS if len(games[d]) >= 4]
print(f"days with 4+ priced games: {len(big)}, a unit play on {100 * sum(d in has for d in big) / len(big):.1f}%")
big = [d for d in DAYS if len(games[d]) >= 8]
print(f"days with 8+ priced games: {len(big)}, a unit play on {100 * sum(d in has for d in big) / len(big):.1f}%")
print("no-play days by the sports on the slate: " + ", ".join(f"{'+'.join(sorted(k))}: {v}" for k, v in Counter(frozenset(lgs[d]) for d in no).most_common(8)))
n = Counter(len([r for r in P if r["date"] == d]) for d in DAYS)
print("unit plays a day: " + ", ".join(f"{k}: {v}" for k, v in sorted(n.items())))
