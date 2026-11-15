"""S9b - THE 🏀 NBA 'MAIN GUYS SIT' OVER (the ½u play) AGAINST THE LEAGUE'S RUN. S9 found the NBA total lags an
UNDER run: after the league's last 100 priced games ran 1.5+ points under their totals, every over -10.9% on 1,549
(both halves) - and this season is in one. Does the over play still win there?  The play's rows rebuilt exactly as
the 11/12 study's live rule (fifteen_1112/s10b_nba_out_over.py: the top three by minutes so far this season a team, 10+ games,
3+ of the six with no minutes tonight, both teams' scoring no more than 3 under the total, the over no worse than
-115), then cut by the league's rolling miss (points - closing total, the last 100 priced regular-season games before
the day). TRAIN to 2021 / BLIND 2022 on (that study's split)."""
import json
import os
import statistics
import sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fifteen_1112"))
import lib as L  # noqa: E402
import box as B  # noqa: E402

mins = defaultdict(dict)
for row in B.R.load("nba"):
    try:
        m = float(json.loads(row["stats"]).get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m
nba = L.table("nba")
tot_m = defaultdict(lambda: defaultdict(float))
gp = defaultdict(int)
for g in nba:
    bx = mins.get(g["id"])
    for side, t in (("H", g["home"]), ("A", g["away"])):
        k = (g["season"], t)
        g[side]["o15"] = None
        if bx and t in bx and gp[k] >= 10:
            top = [p for p, _ in sorted(tot_m[k].items(), key=lambda kv: -kv[1])[:3]]
            g[side]["o15"] = sum(1 for p in top if bx[t].get(p, 0) <= 0)
        if bx and t in bx:
            for p, m in bx[t].items():
                tot_m[k][p] += m
            gp[k] += 1
del mins
# the league's rolling miss before each day
roll, buf, cur = deque(maxlen=100), [], None
for g in nba:
    d = g["start"][:10]
    if d != cur:
        roll.extend(buf)
        buf, cur = [], d
    g["run"] = statistics.mean(roll) if len(roll) == 100 else None
    if L.reg(g) and g["tot"] is not None:
        buf.append(g["hs"] + g["as"] - g["tot"])
ov = lambda rows, sh=0.0: [(g["season"], L.tot(g, "over", sh)) for g in rows]     # noqa: E731
un = lambda rows: [(g["season"], L.tot(g, "under")) for g in rows]               # noqa: E731
rd = lambda g: (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"]   # noqa: E731
N = [g for g in nba if L.reg(g) and g["tot"] is not None and g["H"].get("o15") is not None and g["A"].get("o15") is not None
     and g["run"] is not None]
R_ = [g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and rd(g) > -3 and (g["ovo"] or -110) >= -115]
base = L.cell("every NBA over (both teams 10+ games in)", ov(N))
x = L.cell("THE PLAY -> OVER", ov(R_))
BANDS = (("3+ under", -99, -3), ("1.5..3 under", -3, -1.5), ("0..1.5 under", -1.5, 0), ("0..1.5 over", 0, 1.5), ("1.5+ over", 1.5, 99))
print("\nTHE PLAY by the league's last-100 run")
for nm, lo, hi in BANDS:
    L.cell(f"  the play, run {nm}", ov([g for g in R_ if lo <= g["run"] < hi]))
    L.cell(f"     (every over, run {nm})", ov([g for g in N if lo <= g["run"] < hi]))
a = [g for g in R_ if g["run"] <= -1.5]
b = [g for g in R_ if g["run"] > -1.5]
ra = L.cell("THE PLAY, the league running 1.5+ UNDER", ov(a))
L.cell("   .. its mirror (the under)", un(a))
L.cell("THE PLAY, the rest", ov(b))
L.cell("THE PLAY, the league running 1+ under", ov([g for g in R_ if g["run"] <= -1]))
L.cell("THE PLAY, the league running 2+ under", ov([g for g in R_ if g["run"] <= -2]))
L.cell("THE PLAY, the league running under at all", ov([g for g in R_ if g["run"] < 0]))
L.cell("THE PLAY, the league running over", ov([g for g in R_ if g["run"] >= 0]))
L.cell("   the play, run 1.5+ under, before March 15", ov([g for g in a if not (g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04"))]))
L.cell("   the play, run 1.5+ under, 4+ out", ov([g for g in a if g["H"]["o15"] + g["A"]["o15"] >= 4]))
L.cell("   the play, run 1.5+ under, read 0+ over the total", ov([g for g in a if rd(g) >= 0]))
L.cell("   the play, run 1.5+ under, read -3..0", ov([g for g in a if rd(g) < 0]))
ps = [p for _, p in ra["bets"]]
pool = [p for _, p in x["bets"]]
if ps:
    print(f"placebo: a random {len(ps)} of the play's own rows as bad as its under-run rows: "
          f"{sum(1 for _ in range(1)) and L.placebo([-q for q in pool], len(ps), -sum(ps) / len(ps))} of 2000")
# the window is not tuned: 60 / 150
for W in (60, 150):
    roll, buf, cur = deque(maxlen=W), [], None
    for g in nba:
        d = g["start"][:10]
        if d != cur:
            roll.extend(buf)
            buf, cur = [], d
        g["run2"] = statistics.mean(roll) if len(roll) == W else None
        if L.reg(g) and g["tot"] is not None:
            buf.append(g["hs"] + g["as"] - g["tot"])
    L.cell(f"window {W}: the play, run 1.5+ under", ov([g for g in R_ if g["run2"] is not None and g["run2"] <= -1.5]))
    L.cell(f"window {W}: the play, the rest", ov([g for g in R_ if g["run2"] is not None and g["run2"] > -1.5]))
    L.cell(f"window {W}: every over, run 1.5+ under", ov([g for g in N if g["run2"] is not None and g["run2"] <= -1.5]))
last = [g for g in nba if g["run"] is not None][-1]
print(f"\nthe league's run before {last['start'][:10]}: {last['run']:+.2f}")
L.done()
