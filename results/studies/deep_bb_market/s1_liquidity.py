"""S1 - LIQUIDITY: is the college hoops market softer in thin games (low-major, late night, no 1st-half line / no
public splits = small handle) than in power-conference games?

Game-level (one row per game, the home side's view). Buckets:
  tier: P = a power team in it, M = best team mid (A-10 / WCC / MWC / AAC anchors), L = both low-major (or non-D1)
  liquidity proxies: has a 1st-half line (books bother to hang a derivative), Action Network splits on file (2024+),
  tip hour ET (late = 22:00+), weekday (Mon-Thu) vs weekend.
Measures (closing prices unless said):
  spread MAE |margin + spread|, the spread SLOPE (actual home margin regressed on the closing expected margin -spread:
  1.0 = fair; > 1 = the books shade big numbers toward 0, favorites under-priced; < 1 = the reverse),
  favorite ATS / dog ATS ROI, home ATS, over ROI, favorite / dog ML ROI;
  OPEN (2023-25, ESPN's ML open): mean |close no-vig - open no-vig|, log loss of the open and the close vs the result
  (how much the market learns open -> close = how soft the open is), and the hindsight bet: the side the line moved
  to, bought at the open (what an early bettor who KNEW the move would make - an upper bound for an opening-line play)."""
import math
from collections import defaultdict

import lib

out = lib.Out("s1_liquidity")
rows = [x for x in lib.nc_sides() if x["side"] == "home" and x["stype"] == "2" and x["season"] >= 2018]
RANK = {"power": 3, "mid": 2, "low": 1, "none": 0}


def tier(x):
    m = max(RANK.get(x["tier"], 0), RANK.get(x["otier"], 0))
    return {3: "P", 2: "M"}.get(m, "L")


for x in rows:
    x["gt"] = tier(x)
    x["late"] = x["et"] >= 22
    from datetime import datetime
    x["wd"] = datetime.strptime(x["start"][:10], "%Y-%m-%d").weekday()


def slope(pairs):
    n = len(pairs)
    if n < 30:
        return None
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    sxx = sum((a - mx) ** 2 for a, _ in pairs)
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    return sxy / sxx if sxx else None


def ll(p, y):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def describe(label, rs):
    sp = [x for x in rs if x.get("sp") is not None and x["sp"] != 0]
    if len(sp) < 50:
        out.note(f"{label:34s} n {len(sp)}")
        return
    mae = sum(abs(x["margin"] + x["sp"]) for x in sp) / len(sp)
    sl = slope([(-x["sp"], x["margin"]) for x in sp])
    big = [x for x in sp if abs(x["sp"]) >= 10]
    slb = slope([(-x["sp"], x["margin"]) for x in big]) if len(big) > 50 else None

    def roi(bets):
        b = [p for p in bets if p is not None]
        return (sum(b) / len(b) * 100, len(b)) if b else (0, 0)
    fav = roi([lib.ats_pl((x["margin"] + x["sp"]) * (1 if x["sp"] < 0 else -1),
                          x["spodds"] if x["sp"] < 0 else -110) for x in sp])
    home = roi([lib.ats_pl(x["margin"] + x["sp"], x["spodds"]) for x in sp])
    tot = [x for x in rs if x.get("total")]
    ov = roi([lib.ats_pl(x["pts"] - x["total"], x["over_odds"]) for x in tot])
    tbias = sum(x["pts"] - x["total"] for x in tot) / len(tot) if tot else 0
    ml = [x for x in rs if x.get("ml")]
    fml = roi([lib.ml_pl(x["ml"], x["won"]) if x["ml"] < 0 else lib.ml_pl(x["oml"], not x["won"]) for x in ml])
    dml = roi([lib.ml_pl(x["ml"], x["won"]) if x["ml"] > 0 else lib.ml_pl(x["oml"], not x["won"]) for x in ml
               if max(x["ml"], x["oml"]) <= 350])
    h1 = sum(1 for x in rs if x["has_h1"]) / len(rs) * 100
    s = (f"{label:34s} n{len(sp):6d} MAE {mae:5.2f} slope {sl:5.3f}" + (f" (10+: {slb:5.3f})" if slb else " (10+:  -   )")
         + f" | favATS {fav[0]:+5.1f}% homeATS {home[0]:+5.1f}% | over {ov[0]:+5.1f}% bias {tbias:+.2f} | favML {fml[0]:+5.1f}%"
         f" dogML(<=+350) {dml[0]:+5.1f}% | 1H line {h1:3.0f}%")
    op = [x for x in rs if x.get("po") is not None and x.get("p") is not None]
    if len(op) > 100:
        mv = sum(abs(x["p"] - x["po"]) for x in op) / len(op)
        llo = sum(ll(x["po"], x["won"]) for x in op) / len(op)
        llc = sum(ll(x["p"], x["won"]) for x in op) / len(op)
        hind = []
        for x in op:
            d = x["p"] - x["po"]
            if abs(d) < 0.02:
                continue
            if d > 0:
                hind.append(lib.ml_pl(x["mlo"], x["won"]))
            else:
                ao = x.get("_amlo")
                hind.append(None)
        s += f" || OPEN n{len(op)} |move| {mv*100:4.2f}pt LLopen {llo:.4f} LLclose {llc:.4f} gain {1000*(llo-llc):+.1f}m"
    out.note(s)


out.h("BY GAME TIER x ERA (train 2018-22 / held 2023-25)")
for era, ss in (("train", lib.TRAIN), ("held", lib.HELD)):
    for t in ("P", "M", "L"):
        describe(f"{era} {t}", [x for x in rows if x["season"] in ss and x["gt"] == t])
out.h("TIER x CONFERENCE GAME (held)")
for t in ("P", "M", "L"):
    for c in (True, False):
        describe(f"held {t} conf={c}", [x for x in rows if x["season"] in lib.HELD and x["gt"] == t and x["same_conf"] == c])
out.h("LIQUIDITY PROXIES (held)")
H = [x for x in rows if x["season"] in lib.HELD]
describe("held 1H line hung", [x for x in H if x["has_h1"]])
describe("held NO 1H line", [x for x in H if not x["has_h1"]])
describe("held late tip 22:00+ ET", [x for x in H if x["late"]])
describe("held tip before 22:00 ET", [x for x in H if not x["late"]])
describe("held Mon-Thu", [x for x in H if x["wd"] <= 3])
describe("held Fri-Sun", [x for x in H if x["wd"] >= 4])
describe("held L late", [x for x in H if x["late"] and x["gt"] == "L"])
describe("held Nov-Dec", [x for x in H if x["month"] in (11, 12)])
describe("held Jan-Mar", [x for x in H if x["month"] in (1, 2, 3)])
describe("held L Nov-Dec", [x for x in H if x["month"] in (11, 12) and x["gt"] == "L"])
describe("held P Nov-Dec", [x for x in H if x["month"] in (11, 12) and x["gt"] == "P"])
out.h("TRAIN SAME PROXIES")
T = [x for x in rows if x["season"] in lib.TRAIN]
describe("train 1H line hung", [x for x in T if x["has_h1"]])
describe("train NO 1H line", [x for x in T if not x["has_h1"]])
describe("train late tip", [x for x in T if x["late"]])
describe("train early tip", [x for x in T if not x["late"]])

# ATS by tier x side, graded per season (the money cells)
out.h("ATS / ML CELLS BY TIER (graded per season)")
sides = [x for x in lib.nc_sides() if x["stype"] == "2" and x["season"] >= 2018]
gt = {x["id"]: x["gt"] for x in rows}
for t in ("P", "M", "L"):
    S = [x for x in sides if gt.get(x["id"]) == t and x.get("sp") is not None]
    out.bets(f"{t} favorite ATS", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in S if x["sp"] < 0])
    out.bets(f"{t} dog ATS", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in S if x["sp"] > 0])
    out.bets(f"{t} big fav 10+ ATS", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in S if x["sp"] <= -10])
    out.bets(f"{t} big dog 10+ ATS", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in S if x["sp"] >= 10])
    out.bets(f"{t} home ATS", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in S if x["side"] == "home" and not x["neutral"]])
    M = [x for x in sides if gt.get(x["id"]) == t and x.get("ml")]
    out.bets(f"{t} fav ML -101..-150", [(x["season"], lib.ml_pl(x["ml"], x["won"])) for x in M if -150 <= x["ml"] <= -101])
    out.bets(f"{t} fav ML -151..-300", [(x["season"], lib.ml_pl(x["ml"], x["won"])) for x in M if -300 <= x["ml"] < -150])
    out.bets(f"{t} dog ML +100..+200", [(x["season"], lib.ml_pl(x["ml"], x["won"])) for x in M if 100 <= x["ml"] <= 200])
out.save()
