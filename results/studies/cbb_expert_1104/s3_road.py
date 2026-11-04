"""S3 - ROAD TEAMS ON A ROLL + PER-TEAM HOME COURT (the owner, 11/4: "home court advantage, away teams that come in and
upset and are playing really good"): road dogs with recent road wins / road cover margin, teams that play better away,
road dogs vs home favorites with a weak home record this season; the per-TEAM home edge (its home cover margin minus
its away cover margin) - does it persist within a season, and does the market price it? Prices 2018-26: train
2018-22, held 2023-25 (the games file carries it all - no box needed)."""
import math
import statistics
from collections import defaultdict
import lib

rows = lib.regular(lib.build())
pr = [x for x in rows if x.get("ml")]
out = lib.Out("s3", train=lib.TRAIN_PRICE)
out.h("the table: every priced regular-season side 2018-26")
lib.three("base", pr, out)

out.h("A. ROAD DOGS BY THEIR ROAD RECORD THIS SEASON (true road games only, 3+)")
road = [x for x in pr if x["venue"] == "away" and x["road_w"] + x["road_l"] >= 3]


def rw(x):
    return x["road_w"] / (x["road_w"] + x["road_l"])


for lo, hi, nm in ((0, 0.25, "<.250"), (0.25, 0.5, ".250-.499"), (0.5, 0.75, ".500-.749"), (0.75, 1.01, ".750+")):
    lib.three(f"road side, road record {nm}", [x for x in road if lo <= rw(x) < hi], out)
lib.three("road side, road record .750+ (5+ road games)", [x for x in road if rw(x) >= 0.75 and x["road_w"] + x["road_l"] >= 5], out)
lib.three("road side, road record .500+ in Nov-Dec", [x for x in road if rw(x) >= 0.5 and lib.month(x) in ("11", "12")], out)
lib.three("road side, road record .500+ in Jan-Mar", [x for x in road if rw(x) >= 0.5 and lib.month(x) in ("01", "02", "03")], out)
lib.three("road side, won its last 2 road games (road_cm 3+ games)", [x for x in road if x.get("road_cm") is not None and x["streak"] >= 2], out)

out.h("B. ROAD COVER MARGIN this season (3+ road games) - covering on the road vs not")
rc = [x for x in pr if x["venue"] == "away" and x.get("road_cm") is not None]
for lo, hi, nm in ((-99, -6, "-6-"), (-6, -2, "-6..-2"), (-2, 2, "flat"), (2, 6, "+2..6"), (6, 99, "+6+")):
    lib.three(f"road side, road cover margin {nm}", [x for x in rc if lo <= x["road_cm"] < hi], out)
lib.three("road side, road cm +6+, home cm under 0 (plays BETTER away)", [x for x in rc if x["road_cm"] >= 6 and x.get("home_cm") is not None and x["home_cm"] < 0], out)
lib.three("road side, away_cm - home_cm 6+ (better away, 3+ each)", [x for x in rc if x.get("home_edge") is not None and x["home_edge"] <= -6], out)
lib.three("road side, home_cm - away_cm 6+ (a home-floor team on the road)", [x for x in rc if x.get("home_edge") is not None and x["home_edge"] >= 6], out)

out.h("C. THE HOME TEAM'S OWN HOME RECORD / HOME COVER MARGIN (the road dog across a weak host)")
hw = [x for x in pr if x["venue"] == "away" and x["ohome_w"] + x["ohome_l"] >= 3]
for lo, hi, nm in ((0, 0.5, "under .500"), (0.5, 0.8, ".500-.799"), (0.8, 1.01, ".800+")):
    lib.three(f"road side vs a host with a home record {nm}", [x for x in hw if lo <= x["ohome_w"] / (x["ohome_w"] + x["ohome_l"]) < hi], out)
hc = [x for x in pr if x["venue"] == "away" and x.get("ohome_cm") is not None]
for lo, hi, nm in ((-99, -6, "-6-"), (-6, -2, "-6..-2"), (-2, 2, "flat"), (2, 6, "+2..6"), (6, 99, "+6+")):
    lib.three(f"road side vs a host whose home cover margin is {nm}", [x for x in hc if lo <= x["ohome_cm"] < hi], out)
lib.three("road side: my road cm +3 AND their home cm -3 (the owner's spot)", [x for x in hc if (x.get("road_cm") or 0) >= 3 and x["ohome_cm"] <= -3], out)
lib.three("road side: my road record .500+ AND their home record under .500", [x for x in hw if x["road_w"] + x["road_l"] >= 3 and rw(x) >= 0.5 and x["ohome_w"] / (x["ohome_w"] + x["ohome_l"]) < 0.5], out)

out.h("D. PER-TEAM HOME EDGE: does a team's own home margin over its lines persist within a season?")
# first-half vs second-half home cover margin by team-season (home games only, 5+ each half)
by = defaultdict(list)
for x in rows:
    if x["venue"] == "home" and x.get("sp") is not None:
        by[(x["season"], x["team"])].append(x["margin"] + x["sp"])
a1, a2 = [], []
for k, v in by.items():
    if len(v) >= 10:
        h = len(v) // 2
        a1.append(sum(v[:h]) / h)
        a2.append(sum(v[h:]) / (len(v) - h))
if len(a1) > 10:
    m1, m2 = statistics.mean(a1), statistics.mean(a2)
    cov = sum((p - m1) * (q - m2) for p, q in zip(a1, a2)) / len(a1)
    r = cov / (statistics.pstdev(a1) * statistics.pstdev(a2))
    out.note(f"home cover margin, first half of the season vs the second, {len(a1)} team-seasons: corr {r:+.3f}")
# the same for the home EDGE (home cm - away cm) measured at mid-season vs the home cover margin after
by2 = defaultdict(list)
for x in rows:
    if x.get("sp") is not None and x["venue"] in ("home", "away"):
        by2[(x["season"], x["team"])].append((x["venue"], x["margin"] + x["sp"]))
e1, e2 = [], []
for k, v in by2.items():
    if len(v) >= 16:
        h = len(v) // 2
        fh, fa = [c for ven, c in v[:h] if ven == "home"], [c for ven, c in v[:h] if ven == "away"]
        sh = [c for ven, c in v[h:] if ven == "home"]
        if len(fh) >= 3 and len(fa) >= 3 and len(sh) >= 3:
            e1.append(sum(fh) / len(fh) - sum(fa) / len(fa))
            e2.append(sum(sh) / len(sh))
if len(e1) > 10:
    m1, m2 = statistics.mean(e1), statistics.mean(e2)
    cov = sum((p - q0) * (q - m2) for p, q0, q in [(p, m1, q) for p, q in zip(e1, e2)]) / len(e1)
    r = cov / (statistics.pstdev(e1) * statistics.pstdev(e2))
    out.note(f"the first-half home EDGE (home cm - away cm) vs the second-half home cover margin, {len(e1)} team-seasons: corr {r:+.3f}")
    # does the market price it? the second-half home sides by the first-half edge
hs = [x for x in pr if x["venue"] == "home" and x.get("home_edge") is not None and x["nhome"] >= 5 and x["naway"] >= 5]
for lo, hi, nm in ((-99, -8, "-8-"), (-8, -3, "-8..-3"), (-3, 3, "flat"), (3, 8, "+3..8"), (8, 99, "+8+")):
    lib.three(f"home side, its home edge so far {nm} (5+ each)", [x for x in hs if lo <= x["home_edge"] < hi], out)
lib.three("home side, home edge +8+, games 15+", [x for x in hs if x["home_edge"] >= 8 and x["gn"] >= 15], out)
lib.three("home side, home edge -8-, games 15+", [x for x in hs if x["home_edge"] <= -8 and x["gn"] >= 15], out)
rs = [x for x in pr if x["venue"] == "away" and x.get("ohome_edge") is not None]
lib.three("road side vs a host with home edge +8+", [x for x in rs if x["ohome_edge"] >= 8], out)
lib.three("road side vs a host with home edge -8- (no home floor)", [x for x in rs if x["ohome_edge"] <= -8], out)
lib.three("road side: I play better away (edge -6-) vs a host with no floor (-6-)", [x for x in rs if x["ohome_edge"] <= -6 and (x.get("home_edge") if x.get("home_edge") is not None else 0) <= -6], out)
out.save()
