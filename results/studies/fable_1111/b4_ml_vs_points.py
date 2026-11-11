"""B4 - THE DOG'S MONEYLINE or THE POINTS - which pays more FOR THE SAME READ? (the owner's friend: the pros take
the points.) Same game, same side, two tickets: the moneyline at the close vs the closing spread at its own juice.
  1. every dog by price band (the market's own split of the two);
  2. the dogs the engine's BLIND own read likes (B3's sm.own_p read, fit on the 3 seasons before): the read 5 / 10 /
     15+ points over the no-vig price - NFL, college football, NBA 2019-26 (train 2019-22, held 2023-26);
  3. college hoops: the efficiency read's dogs (the 🔍 gap play's rows, 15+ over and ratings-backed) and the built
     spread stack's dogs (B5) 2018-25.
A flat 1u on each ticket; ROI a unit; the variance matters too - the spread ticket wins ~50%, the moneyline ~35-45%."""
import os, pickle
import lib

B = lib.B
o = lib.Out("b4")
for LG in ("nfl", "ncaaf", "nba"):
    rd = lib.cached(f"b3_reads_{LG}", lambda: {})
    fin = [g for g in B.finals(LG) if g["stype"] == "2" and g["sp"] is not None and g["season"] >= 2019]
    C = lib.Cells()
    for g in fin:
        for side, team, opp, od, won, home in B.sides(g):
            if not 100 <= od <= 350:
                continue
            spme = g["sp"] if home else -g["sp"]
            if spme <= 0:
                continue
            ml = lib.profit(won, lib.dec(od))
            a = B.ats(g, side)
            if a is None:
                continue
            bd = "+100..+150" if od <= 150 else "+151..+250" if od <= 250 else "+251..+350"
            C.add(f"1. every dog {bd}: MONEYLINE", g["season"], ml)
            C.add(f"1. every dog {bd}: POINTS", g["season"], a)
            C.add("1. every dog +100..+350: MONEYLINE", g["season"], ml)
            C.add("1. every dog +100..+350: POINTS", g["season"], a)
            if g["id"] in rd:
                own = rd[g["id"]][1] if home else 1 - rd[g["id"]][1]
                p = lib.nv(g["mlh"], g["mla"]) if home else 1 - lib.nv(g["mlh"], g["mla"])
                for cut in (0.05, 0.10, 0.15):
                    if own - p >= cut:
                        C.add(f"2. own read {int(cut*100)}+ over the price: MONEYLINE", g["season"], ml)
                        C.add(f"2. own read {int(cut*100)}+ over the price: POINTS", g["season"], a)
    o.p(f"\nB4 - {LG} dogs 2019-26 (TRAIN 2019-22, HELD 2023 / 24 / 25 / 26)")
    o.cells(C, (2019, 2022), (2023, 2024, 2025, 2026), zshow=99)

rows = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
C = lib.Cells()
for r in rows:
    if not (2018 <= r["season"] <= 2025 and r["stype"] == "2" and r.get("ml") is not None and r.get("sp") is not None):
        continue
    if not (100 <= r["ml"] <= 350 and r["sp"] > 0):
        continue
    x = r["margin"] + r["sp"]
    if x == 0:
        continue
    ml, a = lib.profit(r["won"], lib.dec(r["ml"])), lib.profit(x > 0, lib.dec(r.get("spodds") or -110))
    C.add("1. every dog +100..+350: MONEYLINE", r["season"], ml)
    C.add("1. every dog +100..+350: POINTS", r["season"], a)
    if r.get("eff") is not None and r["gn"] >= 4 and r["ogn"] >= 4:
        for cut in (0.10, 0.15):
            if r["eff"] - r["p"] >= cut and r["eff"] > 0.5:
                C.add(f"3. efficiency read {int(cut*100)}+ over, ratings-backed: MONEYLINE", r["season"], ml)
                C.add(f"3. efficiency read {int(cut*100)}+ over, ratings-backed: POINTS", r["season"], a)
o.p("\nB4 - college hoops dogs 2018-25 (TRAIN 2018-22, HELD 2023 / 24 / 25)")
o.cells(C, (2018, 2022), (2023, 2024, 2025), zshow=99)
o.save()
