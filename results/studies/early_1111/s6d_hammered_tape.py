"""S6d - THE HAMMERED SPOT, LIVE SHAPE vs STUDIED SHAPE. The spot was studied on the paid history's looks (the first
fair look = Tuesday, the money's move by Thursday: two days of betting on a settled number). Live it reads the move
from the FIRST number on our tape after the fair moment - the Saturday-night / Sunday opener - and 5 of the 6 live
hammered plays posted inside 24 hours of that opener. On our own tape this season (every football dog): the dog whose
no-vig % rose 4+ points from the first fresh number, read (a) inside the first 24 hours and (b) 24-72 hours after -
what the price did from there to the close, and the ROI betting it then. Plus the paid history's own cell again."""
from datetime import timedelta

import base
import elib as E

out = E.Tee("s6d_hammered_tape_out.txt")
se = E.se
tape = E.line_tape()
allg = {}
for lg in ("nfl", "ncaaf"):
    allg.update(E.games(lg))
sched = se._schedule(allg)
res = {"inside 24h of the first fresh number": [], "24-72h after it": []}
res3 = {"inside 24h of the first fresh number": [], "24-72h after it": []}
for gid, g in allg.items():
    if g.get("status") != "final" or gid not in tape or not "2026-10-03" <= g["start"][:10] <= "2026-11-11":
        continue
    try:
        hw = float(g["home_score"]) > float(g["away_score"])
    except (KeyError, ValueError, TypeError):
        continue
    rd = se.ready(sched, g)
    if not rd:
        continue
    start = E.t(g["start"])
    tp = [(E.t(x[0]), x[1], x[2]) for x in tape[gid] if E.t(x[0]) < start]
    post = [x for x in tp if x[0] >= rd]
    if not post or (start - post[0][0]).total_seconds() < 3 * 86400:
        continue
    f = post[0]
    close = tp[-1]
    for s in (1, 2):
        p0 = E.nv(f[s], f[3 - s])
        done = set()
        for x in post[1:]:
            h = (x[0] - f[0]).total_seconds() / 3600
            if h > 72 or (start - x[0]).total_seconds() < 86400:
                break
            px = E.nv(x[s], x[3 - s])
            if not 100 <= x[s] <= 350:
                continue
            k = "inside 24h of the first fresh number" if h <= 24 else "24-72h after it"
            won = hw == (s == 1)
            row = ((E.nv(close[s], close[3 - s]) - px) * 100, (E.dec(x[s]) - 1) if won else -1.0, g["league"])
            if (px - p0) * 100 >= 4 and ("h", k) not in done and not any(d[0] == "h" for d in done):
                res[k].append(row)
                done.add(("h", k))
            if 2 <= (px - p0) * 100 < 4 and not any(d[0] == "m" for d in done) and not any(d[0] == "h" for d in done):
                res3[k].append(row)
                done.add(("m", k))
out("OUR TAPE, 10/3-11/11 (the first time the dog's price is 4+ points better than the first fresh number, +100..+350 then)")
for k, v in res.items():
    out(f"  hammered 4+ {k:38s} n {len(v):3d} | still to come by the close {E.mean(a for a, _, _ in v):+5.2f} pts "
        f"(t {E.tstat([a for a, _, _ in v]):+4.1f}; beat the close {sum(1 for a, _, _ in v if a > 0.25)}, worse {sum(1 for a, _, _ in v if a < -0.25)}) | "
        f"ROI {E.roi([b for _, b, _ in v])}")
for k, v in res3.items():
    out(f"  moved 2-4   {k:38s} n {len(v):3d} | still to come by the close {E.mean(a for a, _, _ in v):+5.2f} pts "
        f"(t {E.tstat([a for a, _, _ in v]):+4.1f}) | ROI {E.roi([b for _, b, _ in v])}")

out("\nTHE PAID HISTORY (the second early look vs the first fair number, ~2 days apart; dog +100..+350 at the second look)")
for lg in ("nfl", "ncaaf", "both"):
    v = []
    for l2 in (("nfl", "ncaaf") if lg == "both" else (lg,)):
        for r in base.build(l2):
            ff = base.first_fair(r)
            if not ff:
                continue
            later = [k for k in base.early_looks(r) if k[0] < ff[0]]
            if later and 100 <= later[0][2] <= 350 and (later[0][3] - ff[3]) * 100 >= 4:
                v.append((r, later[0], ff))
    pl = [(E.dec(k[2]) - 1) if r["won"] else -1.0 for r, k, ff in v]
    fw = [(r["close_p"] - k[3]) * 100 for r, k, ff in v]
    gap = [ff[0] - k[0] for r, k, ff in v]
    bys = {}
    for (r, k, ff), p in zip(v, pl):
        bys.setdefault(r["season"], []).append(p)
    out(f"  {lg:5s} hammered 4+ over {E.mean(gap):.1f} days: {E.roi(pl)} | still to come {E.mean(fw):+.2f} (t {E.tstat(fw):+.1f}) | "
        f"z vs the price {E.zwin([(r['won'], k[3]) for r, k, ff in v]):+.2f} | "
        + "  ".join(f"{s} {sum(1 for x in p if x > 0)}-{sum(1 for x in p if x < 0)}" for s, p in sorted(bys.items())))
