"""S4b - THE TWO TOTALS CELLS THAT HELD IN s4, PULLED APART (five checks):
 (A) COLLEGE HOOPS AT ALTITUDE (venue 1,220 m+ = 4,000 ft): the OVER +7.5% on 1,639 (train 3/5, held 3/3), the under
     -16.5% (0/5, 0/3). Is it one school? the visitor from low ground (the mechanism) vs two mountain teams? by
     month / conference / total size / spread; the margin of the miss; and a PRICE-FREE second check on every game
     2016-26 incl. the unpriced ones: points at altitude vs both teams' own season scoring (for + against) elsewhere.
 (B) NBA APRIL: the OVER +5.5% on 806 (3/4, 3/3), the under -14.6% (0/4, 0/3) - tanking / resting. By the last 2 weeks,
     big spread, the bad team's record, and the over in late March as the dose check."""
from collections import defaultdict

import lib

out = lib.Out("s4b_altitude_april")
ALT = 1220


def ou(rows, side="over"):
    if side == "over":
        return [(r["season"], lib.ats_pl(r["pts"] - r["total"], r["over_odds"])) for r in rows]
    return [(r["season"], lib.ats_pl(r["total"] - r["pts"], r["under_odds"])) for r in rows]


S = lib.nc_sides()
G = [x for x in S if x["side"] == "home" and x["season"] >= 2016]
# each team's home elevation (most common venue elevation of its non-neutral home games, per season)
he = defaultdict(lambda: defaultdict(int))
for g in G:
    if not g["neutral"] and g.get("elev") is not None:
        he[g["team"]][round(g["elev"])] += 1
home_elev = {t: max(c, key=c.get) for t, c in he.items()}
P = [g for g in G if g["stype"] == "2" and g["season"] >= 2018 and g.get("total")]
A = [g for g in P if (g.get("elev") or 0) >= ALT]
out.h("(A) COLLEGE AT ALTITUDE - who / when / how")
out.bets("all altitude games OVER", ou(A))
miss = sorted(g["pts"] - g["total"] for g in A)
out.note(f"   mean miss {sum(miss)/len(miss):+.2f} pts, median {miss[len(miss)//2]:+.1f} (all games: "
         f"{sum(g['pts']-g['total'] for g in P)/len(P):+.2f})")
by = defaultdict(list)
for g in A:
    by[g["name"]].append(g)
out.note("   by home school (n, over ROI): " + "; ".join(
    f"{k} {len(v)} {sum(lib.ats_pl(g['pts']-g['total'], g['over_odds']) for g in v)/len(v)*100:+.0f}%"
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1]))))
lo_vis = [g for g in A if home_elev.get(g["opp"], 0) < 600]
hi_vis = [g for g in A if home_elev.get(g["opp"], 0) >= 1000]
out.bets("visitor from LOW ground (<600 m) OVER", ou(lo_vis))
out.bets("visitor also a mountain team (1,000 m+) OVER", ou(hi_vis))
out.bets("neutral-site altitude games OVER", ou([g for g in A if g["neutral"]]))
out.bets("conference games OVER", ou([g for g in A if g["same_conf"]]))
out.bets("non-conference OVER", ou([g for g in A if not g["same_conf"]]))
out.bets("Nov-Dec OVER", ou([g for g in A if g["month"] in (11, 12)]))
out.bets("Jan-Mar OVER", ou([g for g in A if g["month"] in (1, 2, 3)]))
out.bets("total under 140 OVER", ou([g for g in A if g["total"] < 140]))
out.bets("total 140+ OVER", ou([g for g in A if g["total"] >= 140]))
out.bets("spread under 8 OVER", ou([g for g in A if g.get("sp") is not None and abs(g["sp"]) < 8]))
out.bets("spread 8+ OVER", ou([g for g in A if g.get("sp") is not None and abs(g["sp"]) >= 8]))
out.bets("1,500 m+ (5,000 ft) OVER", ou([g for g in A if g["elev"] >= 1500]))
out.bets("1,220-1,499 m OVER", ou([g for g in A if g["elev"] < 1500]))
out.bets("dose: 900-1,219 m OVER", ou([g for g in P if 900 <= (g.get("elev") or 0) < ALT]))
out.bets("dose: 600-899 m OVER", ou([g for g in P if 600 <= (g.get("elev") or 0) < 900]))
out.bets("mountain team on the ROAD at low ground (<600 m) OVER", ou([g for g in P if (g.get("elev") or 0) < 600 and home_elev.get(g["opp"], 0) >= ALT]))
out.bets("postseason at altitude (stype 3) OVER",
         ou([g for g in G if g["stype"] == "3" and (g.get("elev") or 0) >= ALT and g.get("total")]))
# 1st-half / 2nd-half split of the extra points (where do they come from?)
h = [g for g in A if g.get("h1pts") is not None]
hl = [g for g in P if g.get("h1pts") is not None and (g.get("elev") or 0) < 600]
if h and hl:
    r1 = sum(g["h1pts"] / g["total"] for g in h) / len(h)
    r2 = sum(g["h1pts"] / g["total"] for g in hl) / len(hl)
    s1 = sum((g["pts"] - g["h1pts"]) / g["total"] for g in h) / len(h)
    s2 = sum((g["pts"] - g["h1pts"]) / g["total"] for g in hl) / len(hl)
    out.note(f"   1st-half pts / total: altitude {r1:.3f} vs low ground {r2:.3f}; 2nd half {s1:.3f} vs {s2:.3f} (the 2nd half = tired legs)")

out.h("(A2) PRICE-FREE CHECK, every final 2016-26 incl. unpriced: points vs both teams' own season scoring")
# expected pts = (home team's avg pts-for + away team's avg pts-against + away avg for + home avg against)/2,
# season averages from games at venues under 600 m only (no altitude in the baseline), leave-this-game-out not needed
# (altitude games are excluded from the baseline).
pf = defaultdict(lambda: [0, 0, 0])   # (season, team) -> [pts for, pts against, n]
side_rows = [x for x in S if x["stype"] == "2" and x["season"] >= 2016]
gelev = {g["id"]: g.get("elev") for g in G}
for x in side_rows:
    e = gelev.get(x["id"])
    if e is None or e >= 600:
        continue
    pts_for = (x["pts"] + x["margin"]) / 2
    a = pf[(x["season"], x["team"])]
    a[0] += pts_for; a[1] += x["pts"] - pts_for; a[2] += 1
res = defaultdict(list)
for g in G:
    if g["stype"] != "2" or g.get("elev") is None:
        continue
    h_, a_ = pf.get((g["season"], g["team"])), pf.get((g["season"], g["opp"]))
    if not h_ or not a_ or h_[2] < 8 or a_[2] < 8:
        continue
    exp = (h_[0] / h_[2] + a_[1] / a_[2] + a_[0] / a_[2] + h_[1] / h_[2]) / 2
    band = "altitude 1220+" if g["elev"] >= ALT else ("900-1219" if g["elev"] >= 900 else ("600-899" if g["elev"] >= 600 else "low <600"))
    res[(band, g["season"])].append(g["pts"] - exp)
for band in ("low <600", "600-899", "900-1219", "altitude 1220+"):
    vals = [v for (b, s), vs in res.items() if b == band for v in vs]
    per = " ".join(f"{str(s)[2:]}:{sum(vs)/len(vs):+.1f}" for (b, s), vs in sorted(res.items()) if b == band)
    out.note(f"   {band:16s} n {len(vals):6d} pts vs expected {sum(vals)/len(vals):+.2f}  | {per}")

out.h("(B) NBA APRIL OVERS")
out.train, out.held = (2018, 2019, 2020, 2021, 2022), (2023, 2024, 2025)
NB = [g for g in lib.nba_games() if g.get("total") and g["season"] >= 2018]
for g in NB:
    g["over_odds"], g["under_odds"] = g["over_o"], g["under_o"]
rec = defaultdict(lambda: [0, 0])
for g in NB:
    for side, won in (("home", g["margin"] > 0), ("away", g["margin"] < 0)):
        r = rec[(g["season"], g[side])]
        g[side + "_wp"] = r[0] / r[1] if r[1] >= 20 else None
        r[0] += won; r[1] += 1
    g["md"] = g["start"][5:10]
Ap = [g for g in NB if g["start"][5:7] == "04"]
out.bets("April OVER", ou(Ap))
miss = [g["pts"] - g["total"] for g in Ap]
out.note(f"   mean miss {sum(miss)/len(miss):+.2f} (all NBA {sum(g['pts']-g['total'] for g in NB)/len(NB):+.2f})")
out.bets("Apr 1-7 OVER", ou([g for g in Ap if g["md"] <= "04-07"]))
out.bets("Apr 8+ OVER (last ~10 days)", ou([g for g in Ap if g["md"] > "04-07"]))
out.bets("dose: Mar 15-31 OVER", ou([g for g in NB if "03-15" <= g["md"] <= "03-31"]))
out.bets("dose: Mar 1-14 OVER", ou([g for g in NB if "03-01" <= g["md"] <= "03-14"]))
out.bets("April, a sub-.400 team in it OVER", ou([g for g in Ap if min(g["home_wp"] or 1, g["away_wp"] or 1) < 0.4]))
out.bets("April, both .400+ OVER", ou([g for g in Ap if min(g["home_wp"] or 1, g["away_wp"] or 1) >= 0.4]))
out.bets("April, both .550+ (playoff teams) OVER", ou([g for g in Ap if min(g["home_wp"] or 0, g["away_wp"] or 0) >= 0.55]))
out.bets("April spread 8+ OVER", ou([g for g in Ap if g.get("sp") is not None and abs(g["sp"]) >= 8]))
out.bets("April spread under 8 OVER", ou([g for g in Ap if g.get("sp") is not None and abs(g["sp"]) < 8]))
out.bets("April 1H points vs half the total: (count)", [], count=False)
h = [g for g in Ap if g.get("h1pts") is not None]
if h:
    out.note(f"   April: 1st half {sum(g['h1pts'] - g['total']/2 for g in h)/len(h):+.2f} vs half the total, "
             f"2nd half {sum(g['pts'] - g['h1pts'] - g['total']/2 for g in h)/len(h):+.2f}")
out.save()
