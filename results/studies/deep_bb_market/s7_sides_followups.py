"""S7 - SIDE follow-ups the owner asked for by name (spreads, underdogs, slight favorites), at the close:
 (a) ALTITUDE SIDES: does the sides market miss altitude like the totals market does? the home team at 1,220 m+ vs a
     low-ground visitor (ML -101..-250 favorite / +100..+350 dog, ATS), the mountain team on the road at low ground.
 (b) BIG SPREAD DOGS by tier x phase (the s1 vig split: big favorites -6..-8% ATS, big dogs -1..-2%): any cell over?
 (c) SLIGHT FAVORITES -101..-150 by tier x home / away x phase (the 11/3 (B) weight covers away Nov-Dec)."""
from collections import defaultdict

import lib

out = lib.Out("s7_sides_followups")
ALT = 1220
S = [x for x in lib.nc_sides() if x["stype"] == "2" and x["season"] >= 2016]
he = defaultdict(lambda: defaultdict(int))
for x in S:
    if x["side"] == "home" and not x["neutral"] and x.get("elev") is not None:
        he[x["team"]][round(x["elev"])] += 1
home_elev = {t: max(c, key=c.get) for t, c in he.items()}
S = [x for x in S if x["season"] >= 2018]
for x in S:
    x["gt"] = "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L")
    x["ph"] = "NovDec" if x["month"] in (11, 12) else "JanMar"


def ml(rs):
    return [(x["season"], lib.ml_pl(x["ml"], x["won"])) for x in rs if x.get("ml")]


def ats(rs):
    return [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in rs if x.get("sp") is not None]


out.h("(a) ALTITUDE SIDES")
H = [x for x in S if not x["neutral"] and (x.get("elev") or 0) >= ALT and x["side"] == "home" and home_elev.get(x["opp"], 0) < 600]
out.bets("altitude home vs low visitor, fav -101..-250 ML", ml([x for x in H if x.get("ml") and -250 <= x["ml"] <= -101]))
out.bets("altitude home vs low visitor, dog +100..+350 ML", ml([x for x in H if x.get("ml") and 100 <= x["ml"] <= 350]))
out.bets("altitude home vs low visitor ATS", ats(H))
out.bets("altitude home vs low visitor ATS, 2nd half of season", ats([x for x in H if x["ph"] == "JanMar"]))
R = [x for x in S if not x["neutral"] and (x.get("elev") or 0) < 600 and x["side"] == "away" and home_elev.get(x["team"], 0) >= ALT]
out.bets("mountain team on the road at low ground ATS", ats(R))
out.bets("mountain team on the road at low ground, dog ML", ml([x for x in R if x.get("ml") and 100 <= x["ml"] <= 350]))
out.bets("mountain team on the road at low ground, fav ML", ml([x for x in R if x.get("ml") and -250 <= x["ml"] <= -101]))
out.h("(b) BIG SPREAD DOGS (ATS) by tier x phase")
for lo, hi in ((10, 14.5), (15, 19.5), (20, 99)):
    for t in "PML":
        for ph in ("NovDec", "JanMar"):
            out.bets(f"dog +{lo}..{hi} tier {t} {ph}", ats([x for x in S if x.get("sp") is not None and lo <= x["sp"] <= hi
                                                              and x["gt"] == t and x["ph"] == ph]))
out.h("(c) SLIGHT FAVORITES -101..-150 ML by tier x venue x phase")
for t in "PML":
    for v in ("home", "away", "neutral"):
        for ph in ("NovDec", "JanMar"):
            sel = [x for x in S if x.get("ml") and -150 <= x["ml"] <= -101 and x["gt"] == t and x["ph"] == ph
                   and (x["venue"] == v)]
            out.bets(f"slight fav {t} {v} {ph}", ml(sel))
out.save()
