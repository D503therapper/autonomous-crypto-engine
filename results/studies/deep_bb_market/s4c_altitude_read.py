"""S4c - THE ALTITUDE OVER INSIDE A WHOLE TOTALS READ (the owner's rule: never one factor). A plain pre-game points read
for every college hoops game, no look-ahead: both teams' running season scoring (points for / against, THIS season,
games before tonight, 5+ each) -> expected total = (home for + away against + away for + home against) / 2, then the
venue: the altitude bump (+ALT_BUMP pts at 1,220 m+, fit on TRAIN 2018-22 only) and a mountain team visiting low
ground (-MTN_ROAD pts, fit on train). The read's gap = expected - the closing total.
Questions: (1) does the plain read (no venue) add anything to the closing total anywhere? (2) at altitude, does the
over get better as the read's gap grows (the read weighs it, the altitude is part of the picture), or is altitude all
of it? (3) the mirror: the mountain team at low ground - the UNDER."""
from collections import defaultdict

import lib

out = lib.Out("s4c_altitude_read")
ALT = 1220
S = [x for x in lib.nc_sides() if x["season"] >= 2016 and x["stype"] in ("2", "3")]
G = {x["id"]: x for x in S if x["side"] == "home"}
he = defaultdict(lambda: defaultdict(int))
for g in G.values():
    if not g["neutral"] and g.get("elev") is not None:
        he[g["team"]][round(g["elev"])] += 1
home_elev = {t: max(c, key=c.get) for t, c in he.items()}
run = defaultdict(lambda: [0.0, 0.0, 0])
rows = []
for g in sorted(G.values(), key=lambda g: (g["start"], g["id"])):
    s = g["season"]
    h, a = run[(s, g["team"])], run[(s, g["opp"])]
    if g.get("total") and g["stype"] == "2" and h[2] >= 5 and a[2] >= 5 and g.get("elev") is not None:
        exp = (h[0] / h[2] + a[1] / a[2] + a[0] / a[2] + h[1] / h[2]) / 2
        rows.append({"g": g, "season": s, "exp": exp, "total": g["total"], "pts": g["pts"],
                     "alt": g["elev"] >= ALT and not g["neutral"],
                     "mtn_road": g["elev"] < 600 and home_elev.get(g["opp"], 0) >= ALT and not g["neutral"],
                     "over_odds": g["over_odds"], "under_odds": g["under_odds"]})
    hp = (g["pts"] + g["margin"]) / 2
    h[0] += hp; h[1] += g["pts"] - hp; h[2] += 1
    a[0] += g["pts"] - hp; a[1] += hp; a[2] += 1

tr = [r for r in rows if r["season"] in lib.TRAIN]
base = [r for r in tr if not r["alt"] and not r["mtn_road"]]
off = sum(r["pts"] - r["exp"] for r in base) / len(base)
ALT_BUMP = sum(r["pts"] - r["exp"] for r in tr if r["alt"]) / sum(1 for r in tr if r["alt"]) - off
MTN_ROAD = off - sum(r["pts"] - r["exp"] for r in tr if r["mtn_road"]) / sum(1 for r in tr if r["mtn_road"])
out.note(f"train fit: the plain read runs {off:+.2f} vs the result on ordinary games; altitude bump {ALT_BUMP:+.2f}; "
         f"mountain team at low ground {-MTN_ROAD:+.2f}")
for r in rows:
    r["read"] = r["exp"] + off + (ALT_BUMP if r["alt"] else 0) - (MTN_ROAD if r["mtn_road"] else 0)
    r["gap"] = r["read"] - r["total"]


def ov(rs):
    return [(r["season"], lib.ats_pl(r["pts"] - r["total"], r["over_odds"])) for r in rs]


def un(rs):
    return [(r["season"], lib.ats_pl(r["total"] - r["pts"], r["under_odds"])) for r in rs]


out.h("(1) the plain read on ORDINARY games (no venue term): over / under by its gap to the close")
O = [r for r in rows if not r["alt"] and not r["mtn_road"]]
for lo, hi in ((4, 99), (2, 4), (-2, 2), (-4, -2), (-99, -4)):
    sel = [r for r in O if lo <= r["gap"] < hi]
    out.bets(f"ordinary, read gap {lo}..{hi} OVER", ov(sel))
    out.bets(f"ordinary, read gap {lo}..{hi} UNDER", un(sel))
out.h("(2) AT ALTITUDE (home floor 1,220 m+): the over by the whole read's gap")
A = [r for r in rows if r["alt"]]
out.bets("altitude, every game OVER", ov(A))
for lo, hi in ((6, 99), (3, 6), (0, 3), (-99, 0)):
    out.bets(f"altitude, read gap {lo}..{hi} OVER", ov([r for r in A if lo <= r["gap"] < hi]))
out.bets("altitude, read gap 0+ (the read agrees) OVER", ov([r for r in A if r["gap"] >= 0]))
out.bets("altitude, read gap 2+ OVER", ov([r for r in A if r["gap"] >= 2]))
out.h("(3) THE MIRROR: a mountain team at low ground (<600 m) - the UNDER")
M = [r for r in rows if r["mtn_road"]]
out.bets("mountain team at low ground, every game UNDER", un(M))
for lo, hi in ((-99, -3), (-3, 0), (0, 99)):
    out.bets(f"mountain at low ground, read gap {lo}..{hi} UNDER", un([r for r in M if lo <= r["gap"] < hi]))
out.bets("mountain at low ground, read gap <=0 (read agrees) UNDER", un([r for r in M if r["gap"] <= 0]))

out.h("(4) THE BUILT SPOT'S CELL (read gap 2+, both teams 5+ games): W-L, and the neighbours (robustness, not a choice)")
for thr in (1.0, 2.0, 3.0):
    sel = [r for r in A if r["gap"] >= thr]
    w = sum(r["pts"] > r["total"] for r in sel)
    l_ = sum(r["pts"] < r["total"] for r in sel)
    out.bets(f"altitude, read gap {thr}+ OVER  ({w}-{l_}, {w / (w + l_):.1%})", ov(sel))
sel = [r for r in A if r["gap"] >= 2.0 and r["g"]["month"] in (11, 12)]
out.bets("altitude, read gap 2+ Nov-Dec OVER", ov(sel))
sel = [r for r in A if r["gap"] >= 2.0 and r["g"]["month"] in (1, 2, 3)]
out.bets("altitude, read gap 2+ Jan-Mar OVER", ov(sel))
out.note(f"constants for the live spot: read = both teams' season scoring average {off + ALT_BUMP:+.2f} (the plain read's "
         f"offset {off:+.2f} + the altitude bump {ALT_BUMP:+.2f})")
out.save()
