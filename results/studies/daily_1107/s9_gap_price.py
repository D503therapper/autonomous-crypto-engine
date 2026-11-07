"""11/7 S9 - the 🔍 college football gap play by PRICE (the live 4-8: the +100..+150 plays 2-6, the +151..+350 2-2).
The rule as wired (FBS v FBS, Elo + home edge backing the dog, raw read 15+ over the no-vig close), split +100..+150 /
+151..+250 / +251..+350, at the close and the first fair number, with the calibration (won vs read vs no-vig)."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

rows = json.load(open(os.path.join(lib.CACHE, "_gap1107_rows.json")))
xby = {x["id"]: x for x in lib.load_football("ncaaf")}
C = lib.Cells()
CAL = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
for r in rows:
    if r["fbs"] != 2 or not 100 <= r["odds"] <= 350 or r["elo"] < 0 or r["own"] - r["nv"] < 0.15:
        continue
    s = r["season"]
    band = "+100..+150" if r["odds"] <= 150 else "+151..+250" if r["odds"] <= 250 else "+251..+350"
    ep = lib.early_price(xby, r["gid"], r["side"])
    for k in sorted({f"S9 rule {band}", f"S9 rule {'+100..+150' if r['odds'] <= 150 else '+151..+350'}"}):
        C.add(k, s, lib.profit(r["won"], r["dec"]))
        C.add(k + " FIRST FAIR (at its own price)", s, lib.profit(r["won"], ep[1]) if ep and 100 <= ep[0] <= 350 else None)
        x = CAL[k]
        x[0] += 1; x[1] += r["won"]; x[2] += r["own"]; x[3] += r["nv"]
    gn = min(r["gno"] or 99, r["ogno"] or 99)
    C.add(f"S9 rule {'+100..+150' if r['odds'] <= 150 else '+151..+350'}, games {'1-3' if gn <= 3 else '4+'}", s,
          lib.profit(r["won"], r["dec"]))
C.dump("s9", "11/7 S9 the gap play by price (FBS, close unless FIRST FAIR; TRAIN 2018-22 / held 2023-26)", (2018, 2022),
       [2023, 2024, 2025, 2026])
lines = ["\nCALIBRATION:"]
for k in sorted(CAL):
    n, w, o, v = CAL[k]
    lines.append(f"{k:30s} n {n:4d} won {w/n:6.1%} read {o/n:6.1%} no-vig {v/n:6.1%} truth {((w - v) / (o - v)):+.2f} of the way")
print("\n".join(lines))
open(os.path.join(lib.OUT, "s9_out.txt"), "a").write("\n".join(lines) + "\n")
