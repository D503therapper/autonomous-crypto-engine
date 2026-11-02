"""S7 - THE BUILT DEFINITION, the canonical numbers (what sports.ncaab_top_out computes live):
the team's TOP SCORER = its leader in points a game in this season's box scores before tonight (3+ games played, 20+
minutes a game, the team 3+ box games in); he MISSED THE LAST GAME = not in (or 0 minutes in) the box of the team's
last game before tonight - and that box must be on file (no box = unknown = no flag). Regular season, 2022-25 at
ESPN's close (+ the 2023-25 open); train 2022-23, held out 2024 / 2025. Cells: the flagged side's dog / favorite / ATS,
and the side ACROSS from it; each vs the base (neither side flagged)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_ats, profit_open  # noqa: E402
from lib import load_box  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["stype"] == "2" and x["season"] >= 2022]
box, _, _ = load_box()
order = defaultdict(list)
for x in tb:
    order[(x["season"], x["team"])].append(x)
for (s, t), xs in order.items():
    xs.sort(key=lambda x: x["start"])
    for i, x in enumerate(xs):
        st = x["f"].get("stars")
        x["top_out"] = None
        if st and i:
            b = (box.get(xs[i - 1]["id"]) or {}).get(t)
            if b is not None:
                x["top_out"] = st[0] not in b or b[st[0]][0] <= 0
idx = {(x["id"], x["team"]): x for x in tb}
for x in tb:
    o = idx.get((x["id"], x["opp"]))
    x["o_top_out"] = o["top_out"] if o else None
out = []


def P(s):
    print(s)
    out.append(s)


dog = lambda x: x.get("ml") is not None and 100 <= x["ml"] <= 350
fav = lambda x: x.get("ml") is not None and -250 <= x["ml"] <= -101
me = lambda x: x["top_out"] is True and x["o_top_out"] is not True
op = lambda x: x["o_top_out"] is True and x["top_out"] is not True
base = lambda x: x["top_out"] is False and x["o_top_out"] is False
P(f"flagged sides: {sum(1 for x in tb if x['top_out'])} of {sum(1 for x in tb if x['top_out'] is not None)} with a known last box")
for lab, sel in (("FLAGGED dog +100..+350", lambda x: me(x) and dog(x)), ("   base dog", lambda x: base(x) and dog(x)),
                 ("FLAGGED fav -101..-250", lambda x: me(x) and fav(x)), ("   base fav", lambda x: base(x) and fav(x)),
                 ("ACROSS: fav -101..-250 vs a flagged dog", lambda x: op(x) and fav(x)),
                 ("ACROSS: dog +100..+350 vs a flagged fav", lambda x: op(x) and dog(x))):
    cell(lab, [x for x in tb if sel(x)], profit_ml, out)
for lab, sel in (("FLAGGED dog @OPEN", lambda x: me(x) and x.get("mlo") and 100 <= x["mlo"] <= 350),
                 ("   base dog @OPEN", lambda x: base(x) and x.get("mlo") and 100 <= x["mlo"] <= 350),
                 ("FLAGGED fav @OPEN", lambda x: me(x) and x.get("mlo") and -250 <= x["mlo"] <= -101),
                 ("   base fav @OPEN", lambda x: base(x) and x.get("mlo") and -250 <= x["mlo"] <= -101)):
    cell(lab, [x for x in tb if sel(x)], profit_open, out)
for lab, sel in (("FLAGGED side ATS", me), ("   base ATS", base), ("ACROSS side ATS", op)):
    cell(lab, [x for x in tb if sel(x)], profit_ats, out)
P("--- bet-free: flagged minus base, (margin + close spread) pts and (won - no-vig close) win %, by season")
for s in (2022, 2023, 2024, 2025):
    a = [x for x in tb if x["season"] == s and me(x)]
    b = [x for x in tb if x["season"] == s and base(x)]
    ra = np.mean([x["margin"] + x["sp"] for x in a if x.get("sp") is not None]) - np.mean([x["margin"] + x["sp"] for x in b if x.get("sp") is not None])
    rm = (np.mean([x["won"] - x["p"] for x in a if x.get("p") is not None]) - np.mean([x["won"] - x["p"] for x in b if x.get("p") is not None])) * 100
    P(f"  {s}: {ra:+.2f} pts, {rm:+.1f}% (n{len(a)})")
a = [x for x in tb if me(x)]
v = np.array([x["margin"] + x["sp"] for x in a if x.get("sp") is not None])
w = np.array([(x["won"] - x["p"]) * 100 for x in a if x.get("p") is not None])
P(f"  ALL: {v.mean():+.2f} pts (z {v.mean() / (v.std() / np.sqrt(len(v))):+.2f}), {w.mean():+.2f}% (z {w.mean() / (w.std() / np.sqrt(len(w))):+.2f})")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s7_out.txt"), "w").write("\n".join(out) + "\n")
