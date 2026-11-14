"""11/14 STUDY 8b - THE LEAGUE OPENER HOME FAVORITE, deeper: against its base (every league home favorite), without
the built rusty-home-side cell (7+ days off vs a visitor on 4 or less), by the spread, the month, the rest; the placebo
(random league home favorites, same seasons); the side across; and the .300+ non-league record favorite the same way."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import tlib

G = [g for g in tlib.build() if g["stype"] == "2" and g["season"] >= 2018 and g["conf"] and not g["neu"] and g["sp"] is not None]
cg = {}
for g in sorted(tlib.build(), key=lambda g: g["start"]):
    pass
# league games played before each game (both teams) - recount in order
from collections import defaultdict
n = defaultdict(int)
rows = []
for g in sorted((x for x in tlib.build() if x["stype"] == "2"), key=lambda g: g["start"]):
    s = g["season"]
    h0, a0 = n[(g["home"], s)], n[(g["away"], s)]
    if g["conf"]:
        n[(g["home"], s)] += 1
        n[(g["away"], s)] += 1
    if g["season"] < 2018 or not g["conf"] or g["neu"] or g["sp"] is None:
        continue
    for side in ("home", "away"):
        sp = g["sp"] if side == "home" else -g["sp"]
        spo = (g["spo_h"] if side == "home" else g["spo_a"]) or -110
        mar = g["margin"] if side == "home" else -g["margin"]
        cov = mar + sp
        pnl = 0.0 if cov == 0 else ((L.dec(spo) - 1) if cov > 0 else -1.0)
        rows.append({"season": s, "month": g["month"], "side": side, "sp": sp, "win": cov > 0, "pnl": pnl,
                     "mine": h0 if side == "home" else a0, "theirs": a0 if side == "home" else h0,
                     "rest": g["rh"] if side == "home" else g["ra"], "orest": g["ra"] if side == "home" else g["rh"]})
HF = [r for r in rows if r["side"] == "home" and r["sp"] < 0]
AD = [r for r in rows if r["side"] == "away" and r["sp"] > 0]
rusty = lambda r: r["rest"] is not None and r["orest"] is not None and r["rest"] >= 7 and r["orest"] <= 4
L.rec("BASE every league home favorite ATS", HF)
op = [r for r in HF if r["mine"] == 0]
L.rec("opener home favorite (its 1st league game)", op, HF)
L.rec("opener home favorite, both teams' 1st", [r for r in op if r["theirs"] == 0], HF)
L.rec("opener home favorite, NOT the rusty cell", [r for r in op if not rusty(r)], HF)
L.rec("opener home favorite, the rusty cell", [r for r in op if rusty(r)], HF)
L.rec("2nd league game, home favorite", [r for r in HF if r["mine"] == 1], HF)
L.rec("3rd-4th league game, home favorite", [r for r in HF if r["mine"] in (2, 3)], HF)
for lab, f in (("laying 0.5-5", lambda r: r["sp"] >= -5), ("laying 5.5-10", lambda r: -10 <= r["sp"] < -5), ("laying 10.5+", lambda r: r["sp"] < -10)):
    L.rec(f"opener home favorite {lab}", [r for r in op if f(r)], HF)
for m in ("11", "12", "01"):
    L.rec(f"opener home favorite, month {m}", [r for r in op if r["month"] == m], HF)
for lab, f in (("rest 0-3", lambda r: r["rest"] is not None and r["rest"] < 3.5), ("rest 4-6", lambda r: r["rest"] is not None and 3.5 <= r["rest"] < 6.5), ("rest 7+", lambda r: r["rest"] is not None and r["rest"] >= 6.5)):
    L.rec(f"opener home favorite, {lab}", [r for r in op if f(r)], HF)
L.rec("BASE every league road dog ATS", AD)
L.rec("the road dog across an opener home favorite", [r for r in AD if r["theirs"] == 0], AD)
print(f"cells read: {L.CELLS[0]}")
