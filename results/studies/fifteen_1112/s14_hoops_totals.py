"""S14 - COLLEGE HOOPS TOTALS BEYOND ALTITUDE (the owner, 11/12: "My brother's engine's been killing the overs and
unders in the college basketball ... We need to get on that level"). The close 2018-26 at its own juice, train to 2021 /
blind 2022 on. Altitude floors (1,400 m+) are LEFT OUT of every cell here unless it says so - that play is built.

A. OUR PROJECTION vs THE BOOK (his engine's 60% watch: "projection 12+ points off the book"): two honest reads -
   (1) PLAIN: both teams' season scoring for / against (5+ finals each);
   (2) RATED: a walk-forward offence / defence points rating a team (updated after every final, last season carried
       in at half weight, a home edge and a league level learned as it goes; the step size picked on 2016-21 only).
   The gap to the closing total, by size, both ways.
B. NEW ROSTERS / EARLY SEASON: last season's scoring vs the November total; a team whose first games ran far from last
   season's pace; a new team profile (the total far from last season's read).
C. LOW-MAJOR CONFERENCE TOTALS (the cbb10 table's leagues and tiers).
D. BOTH TEAMS OUT OF IT FROM FEB 15 (the 11/12 watch) - re-read, plus the overall-record version.
E. OTHER NEW CUTS: a mountain team down at sea level, tip time, rest, the third game in three days, the juice lean,
   big spread x total, the second half of a home-and-home."""
import importlib.util, os, sys
from collections import defaultdict

import lib as L

_s = importlib.util.spec_from_file_location("cbb", os.path.join(L.ROOT, "results", "studies", "cbb10_1112", "lib.py"))
C = importlib.util.module_from_spec(_s)
_s.loader.exec_module(C)

T = L.table("ncaab")
cb = {g["id"]: g for g in C.build()}
G = [g for g in T if L.reg(g)]
ov = lambda rows, sh=0.0: [(g["season"], L.tot(g, "over", sh)) for g in rows]      # noqa: E731
un = lambda rows, sh=0.0: [(g["season"], L.tot(g, "under", sh)) for g in rows]     # noqa: E731
hi_floor = {}
acc = defaultdict(list)
for g in T:
    if not g["neutral"] and g["elev"] is not None:
        acc[g["home"]].append(g["elev"])
for t, v in acc.items():
    v.sort()
    hi_floor[t] = v[len(v) // 2]


def low(g):
    return g["neutral"] or (g["elev"] or 0) < 1400


def both(rows, name):
    a = L.cell(name + " OVER", ov(rows))
    b = L.cell(name + " UNDER", un(rows))
    return a, b


# ---------------------------------------------------------------- the rated read (walk-forward)
def rated(k, tune_to=None):
    """-> {id: projected total}, and the squared error on games to tune_to (for picking k on the train seasons)."""
    off, de = defaultdict(float), defaultdict(float)
    mu, hfa, nmu = 70.0, 1.5, 0
    cur = None
    out, se, n = {}, 0.0, 0
    for g in T:
        s = g["season"]
        if s != cur:
            cur = s
            for t in list(off):
                off[t] *= 0.5
                de[t] *= 0.5
        h, a = g["home"], g["away"]
        hf = 0.0 if g["neutral"] else hfa
        ph = mu + off[h] + de[a] + hf
        pa = mu + off[a] + de[h] - hf
        if g["H"]["n"] >= 3 and g["A"]["n"] >= 3:
            out[g["id"]] = ph + pa
            if tune_to and s <= tune_to and s >= 2016:
                se += (g["hs"] + g["as"] - ph - pa) ** 2
                n += 1
        eh, ea = g["hs"] - ph, g["as"] - pa
        # overtime points are not a team's level: scale an overtime game back to regulation
        reg = 40.0
        if g["lsh"] and len(g["lsh"]) > 2:
            f = reg / (reg + 5 * (len(g["lsh"]) - 2))
            eh, ea = g["hs"] * f - ph, g["as"] * f - pa
        off[h] += k * eh
        de[a] += k * eh
        off[a] += k * ea
        de[h] += k * ea
        nmu += 1
        mu += (eh + ea) / 2 / min(nmu, 4000)
        if not g["neutral"]:
            hfa += ((eh - ea) / 2) / 4000
    return out, (se / n if n else 0.0)


print("=" * 30, "A. OUR PROJECTION vs THE BOOK")
best = None
for k in (0.06, 0.10, 0.14, 0.18):
    _, mse = rated(k, tune_to=2021)
    print(f"  step {k}: error on 2016-21 finals {mse ** 0.5:.2f}")
    if best is None or mse < best[1]:
        best = (k, mse)
R2, _ = rated(best[0])
print(f"  picked {best[0]} on the train seasons")


def plain(g):
    h, a = g["H"], g["A"]
    if h["n"] < 5 or a["n"] < 5:
        return None
    return (h["pf"] + a["pa"] + a["pf"] + h["pa"]) / 2


P = [g for g in G if g["tot"] is not None and low(g)]
import math  # noqa: E402
for nm, fn in (("plain", plain), ("rated", lambda g: R2.get(g["id"]))):
    rs = [(g, fn(g)) for g in P]
    rs = [(g, r) for g, r in rs if r is not None]
    for lab, sel in (("train", lambda g: g["season"] <= 2021), ("blind", lambda g: g["season"] > 2021)):
        x = [(g, r) for g, r in rs if sel(g)]
        e1 = math.sqrt(sum((g["hs"] + g["as"] - r) ** 2 for g, r in x) / len(x))
        e2 = math.sqrt(sum((g["hs"] + g["as"] - g["tot"]) ** 2 for g, r in x) / len(x))
        b1 = sum(r - g["tot"] for g, r in x) / len(x)
        print(f"  {nm} read, {lab}: misses the final by {e1:.2f} (RMSE) - the closing total by {e2:.2f}; the read sits "
              f"{b1:+.2f} from the total on average ({len(x)} games)")
    bias = sum(r - g["tot"] for g, r in rs if g["season"] <= 2021) / max(1, sum(1 for g, r in rs if g["season"] <= 2021))
    print(f"  ({nm}: the gap below is read - total - {bias:+.2f}, the train-season lean taken out)")
    for lo, hi in ((12, 99), (9, 12), (6, 9), (3, 6), (0, 3)):
        L.cell(f"{nm} read {lo}..{hi} OVER the total -> the over", ov([g for g, r in rs if lo <= r - g["tot"] - bias < hi]))
        L.cell(f"{nm} read {lo}..{hi} UNDER the total -> the under", un([g for g, r in rs if lo <= -(r - g["tot"] - bias) < hi]))
    L.cell(f"{nm} read 12+ off either way -> its side",
           [(g["season"], L.tot(g, "over" if r - g["tot"] - bias > 0 else "under")) for g, r in rs if abs(r - g["tot"] - bias) >= 12])
    L.cell(f"{nm} read 8+ off either way -> its side",
           [(g["season"], L.tot(g, "over" if r - g["tot"] - bias > 0 else "under")) for g, r in rs if abs(r - g["tot"] - bias) >= 8])
    L.cell(f"{nm} read 12+ off, Nov-Dec", [(g["season"], L.tot(g, "over" if r - g["tot"] - bias > 0 else "under"))
                                            for g, r in rs if abs(r - g["tot"] - bias) >= 12 and g["start"][5:7] in ("11", "12")])
    L.cell(f"{nm} read 12+ off, Jan-Mar", [(g["season"], L.tot(g, "over" if r - g["tot"] - bias > 0 else "under"))
                                            for g, r in rs if abs(r - g["tot"] - bias) >= 12 and g["start"][5:7] in ("01", "02", "03")])
# both reads agree
bp = sum(plain(g) - g["tot"] for g in P if plain(g) is not None and g["season"] <= 2021) / sum(1 for g in P if plain(g) is not None and g["season"] <= 2021)
br = sum(R2[g["id"]] - g["tot"] for g in P if g["id"] in R2 and g["season"] <= 2021) / sum(1 for g in P if g["id"] in R2 and g["season"] <= 2021)
ag = [(g, plain(g) - g["tot"] - bp, R2[g["id"]] - g["tot"] - br) for g in P if plain(g) is not None and g["id"] in R2]
for k in (5, 8, 10):
    L.cell(f"BOTH reads {k}+ over the total -> the over", ov([g for g, a, b_ in ag if a >= k and b_ >= k]))
    L.cell(f"BOTH reads {k}+ under the total -> the under", un([g for g, a, b_ in ag if a <= -k and b_ <= -k]))
# with altitude: does the projection add to the built play?
A = [g for g in G if g["tot"] is not None and not g["neutral"] and (g["elev"] or 0) >= 1400 and g["id"] in R2]
L.cell("ALTITUDE floors: rated read 3+ over the total -> over", ov([g for g in A if R2[g["id"]] - g["tot"] - br >= 3]))
L.cell("ALTITUDE floors: rated read within 3 -> over", ov([g for g in A if abs(R2[g["id"]] - g["tot"] - br) < 3]))
L.cell("ALTITUDE floors: rated read 3+ under -> over", ov([g for g in A if R2[g["id"]] - g["tot"] - br <= -3]))

# ---------------------------------------------------------------- B
print("\n" + "=" * 30, "B. NEW ROSTERS / EARLY SEASON (low ground)")
E_ = [g for g in P if g["start"][5:7] == "11"]
both(E_, "every November game")
both([g for g in E_ if g["H"]["n"] <= 1 and g["A"]["n"] <= 1], "both teams' first or second game")


def prev_read(g):
    h, a = g["H"].get("prev"), g["A"].get("prev")
    if not h or not a or h["n"] < 15 or a["n"] < 15:
        return None
    return (h["pf"] + a["pa"] + a["pf"] + h["pa"]) / 2


pr = [(g, prev_read(g)) for g in E_ if g["H"]["n"] < 5 and g["A"]["n"] < 5]
pr = [(g, r) for g, r in pr if r is not None]
bb = sum(r - g["tot"] for g, r in pr if g["season"] <= 2021) / max(1, sum(1 for g, r in pr if g["season"] <= 2021))
print(f"  last season's read sits {bb:+.2f} from the November total on the train seasons (taken out below); {len(pr)} games")
for lo, hi in ((8, 99), (4, 8), (0, 4)):
    L.cell(f"total {lo}..{hi} OVER last season's read -> the over (the book sees a faster team)", ov([g for g, r in pr if lo <= g["tot"] - r + bb < hi]))
    L.cell(f"total {lo}..{hi} OVER last season's read -> the under", un([g for g, r in pr if lo <= g["tot"] - r + bb < hi]))
    L.cell(f"total {lo}..{hi} UNDER last season's read -> the under", un([g for g, r in pr if lo <= -(g["tot"] - r + bb) < hi]))
    L.cell(f"total {lo}..{hi} UNDER last season's read -> the over", ov([g for g, r in pr if lo <= -(g["tot"] - r + bb) < hi]))
# a team whose first games ran far from last season's scoring (2-4 games in)
ch = []
for g in P:
    for side in ("H", "A"):
        f = g[side]
        pv = f.get("prev")
        if 2 <= f["n"] <= 4 and pv and pv["n"] >= 15:
            ch.append((g, (f["pf"] + f["pa"]) - (pv["pf"] + pv["pa"])))
for lo, hi in ((15, 99), (8, 15)):
    L.cell(f"a team's games run {lo}..{hi} points OVER last season's (2-4 games in) -> over", ov([g for g, d in ch if lo <= d < hi]))
    L.cell(f"   -> under", un([g for g, d in ch if lo <= d < hi]))
    L.cell(f"a team's games run {lo}..{hi} points UNDER last season's (2-4 games in) -> under", un([g for g, d in ch if lo <= -d < hi]))
    L.cell(f"   -> over", ov([g for g, d in ch if lo <= -d < hi]))
# early-season totals running over / under (the team's games vs the total so far)
for lo, hi in ((6, 99), (3, 6)):
    L.cell(f"Nov-Dec: both teams' games {lo}..{hi}+ OVER their totals so far (2+ priced) -> over",
           ov([g for g in P if g["start"][5:7] in ("11", "12") and all((g[s].get("tmn") or 0) >= 2 and lo <= g[s]["tm"] < hi for s in "HA")]))
    L.cell(f"Nov-Dec: both teams' games {lo}..{hi}+ UNDER their totals so far -> under",
           un([g for g in P if g["start"][5:7] in ("11", "12") and all((g[s].get("tmn") or 0) >= 2 and lo <= -g[s]["tm"] < hi for s in "HA")]))

# ---------------------------------------------------------------- C
print("\n" + "=" * 30, "C. LOW-MAJOR CONFERENCE TOTALS (low ground)")
J = [(g, cb[g["id"]]) for g in P if g["id"] in cb]
for tier in ("low", "mid", "power"):
    rows = [g for g, c in J if c["conf"] and c["H"].get("tier") == tier]
    both(rows, f"{tier} conference games")
LM = [(g, c) for g, c in J if c["conf"] and c["H"].get("tier") == "low"]
for lo, hi in ((0, 130), (130, 138), (138, 146), (146, 154), (154, 999)):
    both([g for g, c in LM if lo <= g["tot"] < hi], f"low-major conference, total {lo}..{hi}")
for mm in ("12", "01", "02", "03"):
    both([g for g, c in LM if g["start"][5:7] == mm], f"low-major conference, month {mm}")
both([g for g, c in LM if g["day"].weekday() in (0, 1, 2, 3)], "low-major conference, Mon-Thu")
both([g for g, c in LM if g["day"].weekday() in (5, 6)], "low-major conference, the weekend")
both([g for g, c in LM if g["A"].get("rest") == 2 and g["H"].get("rest") == 2], "low-major, both on the Thu-Sat turnaround (2 days)")
both([g for g, c in LM if c["meet"]], "low-major conference, the rematch")
both([g for g, c in LM if c["meet"] and c["meet"][-1]["total"] is not None and c["meet"][-1]["pts"] - c["meet"][-1]["total"] >= 10],
     "low-major rematch, the first meeting went 10+ over")
both([g for g, c in LM if c["meet"] and c["meet"][-1]["total"] is not None and c["meet"][-1]["pts"] - c["meet"][-1]["total"] <= -10],
     "low-major rematch, the first meeting went 10+ under")
lr = [(g, plain(g)) for g, c in LM]
lr = [(g, r) for g, r in lr if r is not None]
for k in (6, 9):
    L.cell(f"low-major conference, plain read {k}+ over -> over", ov([g for g, r in lr if r - g["tot"] - bp >= k]))
    L.cell(f"low-major conference, plain read {k}+ under -> under", un([g for g, r in lr if r - g["tot"] - bp <= -k]))
NC = [(g, c) for g, c in J if not c["conf"] and c["H"].get("tier") == "low" and c["A"].get("tier") == "low"]
both([g for g, c in NC], "low-major vs low-major, non-conference")

# ---------------------------------------------------------------- D
print("\n" + "=" * 30, "D. BOTH TEAMS OUT OF IT (from Feb 15, low ground)")


def lg_pct(f):
    n = f.get("cw", 0) + f.get("cl", 0)
    return f["cw"] / n if n >= 8 else None


late = [(g, c) for g, c in J if c["conf"] and (g["start"][5:10] >= "02-15" and g["start"][5:7] in ("02", "03"))]
for cut in (0.25, 0.30, 0.35, 0.40):
    both([g for g, c in late if all(lg_pct(c[s]) is not None and lg_pct(c[s]) <= cut for s in "HA")],
         f"both {cut:.2f} or worse in the league")
both([g for g, c in late if all(lg_pct(c[s]) is not None and lg_pct(c[s]) >= 0.70 for s in "HA")], "both .700+ in the league")
early = [(g, c) for g, c in J if c["conf"] and "02-01" <= g["start"][5:10] < "02-15"]
both([g for g, c in early if all(lg_pct(c[s]) is not None and lg_pct(c[s]) <= 0.30 for s in "HA")],
     "the same pair Feb 1-14 (the flip the 11/12 study saw)")
jan = [(g, c) for g, c in J if c["conf"] and g["start"][5:7] == "01"]
both([g for g, c in jan if all(lg_pct(c[s]) is not None and lg_pct(c[s]) <= 0.30 for s in "HA")], "the same pair in January")
both([g for g in P if g["start"][5:10] >= "02-15" and g["start"][5:7] in ("02", "03")
      and all(g[s]["n"] >= 20 and g[s]["w"] / g[s]["n"] <= 0.30 for s in "HA")], "both .300 or worse OVERALL from Feb 15")
x = [g for g, c in late if all(lg_pct(c[s]) is not None and lg_pct(c[s]) <= 0.30 for s in "HA")]
pool = [L.tot(g, "over") for g, c in late]
pp = [L.tot(g, "over") for g in x]
pp = [p for p in pp if p is not None]
print(f"   placebo: random {len(pp)} late-season conference overs as good: {L.placebo(pool, len(pp), sum(pp) / len(pp))} of 2000")

# ---------------------------------------------------------------- E
print("\n" + "=" * 30, "E. OTHER NEW CUTS (low ground)")
both([g for g in P if not g["neutral"] and hi_floor.get(g["away"], 0) >= 1400 and (g["elev"] or 0) < 600],
     "a 4,600 ft+ team DOWN at a floor under 2,000 ft")
both([g for g in P if not g["neutral"] and hi_floor.get(g["away"], 0) >= 1400 and (g["elev"] or 0) < 600 and g["A"]["n"] >= 5
      and g["start"][5:7] in ("01", "02", "03")], "   ... Jan-Mar")
both([g for g in P if not g["neutral"] and hi_floor.get(g["home"], 0) < 600 and 900 <= (g["elev"] or 0) < 1400], "floors 3,000-4,600 ft")


def local_hour(g):
    hh = int(g["start"][11:13]) + int(g["start"][14:16]) / 60 + (g["tzo"] if g["tzo"] is not None else -5)
    return hh % 24


both([g for g in P if g["tzo"] is not None and local_hour(g) < 12.5], "a tip before 12:30 local")
both([g for g in P if g["tzo"] is not None and local_hour(g) < 12.5 and not g["neutral"]], "   ... on a home floor")
both([g for g in P if g["tzo"] is not None and local_hour(g) >= 21], "a tip 9 PM local or later")
both([g for g in P if g["H"].get("rest") == 1 and g["A"].get("rest") == 1], "both teams played yesterday")
both([g for g in P if g["H"].get("g4", 0) >= 2 and g["A"].get("g4", 0) >= 2], "both on a 3rd game in 4 days")
both([g for g in P if g["H"].get("rest", 0) >= 8 and g["A"].get("rest", 0) >= 8], "both off 8+ days")
both([g for g in P if (g["H"].get("last") or {}).get("ot") or (g["A"].get("last") or {}).get("ot")], "a team off an overtime game")
# the juice lean
both([g for g in P if g["ovo"] and g["uno"] and g["ovo"] <= -115 and g["uno"] >= -105], "the OVER is the juiced side (-115 / -105 or more)")
both([g for g in P if g["ovo"] and g["uno"] and g["uno"] <= -115 and g["ovo"] >= -105], "the UNDER is the juiced side")
# spread x total
for slo, shi in ((0, 3.5), (4, 9.5), (10, 16.5), (17, 60)):
    for tlo, thi in ((0, 135), (135, 150), (150, 999)):
        both([g for g in P if g["sp"] is not None and slo <= abs(g["sp"]) <= shi and tlo <= g["tot"] < thi],
             f"spread {slo}-{shi}, total {tlo}-{thi}")
L.done()
