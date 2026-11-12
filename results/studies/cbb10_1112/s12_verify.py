"""11/12 - the cells as WIRED, re-read once more with the overlap checks:
W1 the dog losing the turnover matchup by .05+ a possession (sports.NCAAB_TO_MATCH) - outside the other built box fades;
W2 the home side off 7+ days vs a visitor that played within 4 (sports.NCAAB_RUST_*) - outside the hot-ATS fade;
W3 the conference leader with a 1+ game cushion on the road in Feb-Mar (a LEAD) - is it just the built hot-ATS fade?"""
from collections import defaultdict
import lib

R = lib.build()
V = lib.Cells("s12", (2018, 2021), (2022, 2023, 2024, 2025))
tab = defaultdict(dict)
base_ats, cell_ats = [], []
for g in R:
    if g["season"] < 2018:
        continue
    s, mon, d = g["season"], g["day"].month, g["day"]
    H, A = g["H"], g["A"]
    for side, f in (("H", H), ("A", A)):
        t = g["home"] if side == "H" else g["away"]
        if f["ck"] is not None:
            tb = tab[(s, f["ck"])]
            tb.setdefault(t, [0, 0])
            ds = sorted((w - l for w, l in tb.values()), reverse=True)
            f["cushion"] = (tb[t][0] - tb[t][1] - (ds[1] if len(ds) > 1 else ds[0])) / 2 if tb[t][0] - tb[t][1] == ds[0] else None
            f["cg"] = tb[t][0] + tb[t][1]
    if g["mlh"] and g["stype"] == "2":
        for side, f, o in lib.both(g):
            if "rest" not in f or "rest" not in o:
                continue
            od, sp = lib.odds(g, side), lib.spread(g, side)
            bd = lib.band(od)
            ml, at = lib.ml_p(g, side), lib.ats_p(g, side)
            v = lib.ven(g, side)
            hot = (f.get("cm") is not None and o.get("cm") is not None and f.get("cmn", 0) >= 10 and o.get("cmn", 0) >= 10
                   and f["cm"] - o["cm"] >= 3)
            # W2
            if f["n"] >= 4 and o["n"] >= 4 and f["rest"] >= 7 and o["rest"] <= 4 and v == "H":
                V.add("W2 the rusty home side: ATS", g, at)
                V.add(f"W2 the rusty home side, {'hot-ATS (the built fade)' if hot else 'not hot-ATS'}: ATS", g, at)
                V.add("W2 the visitor across: ATS", g, lib.ats_p(g, "A"))
                V.add(f"W2 the rusty home side, month {mon:02d}: ATS", g, at)
                V.add(f"W2 the rusty home side, {f['tier'] or 'no league'}: ATS", g, at)
            if f["n"] >= 4 and o["n"] >= 4 and f["rest"] >= 7 and o["rest"] <= 4 and v == "A":
                V.add("W2 control - the rusty ROAD side: ATS", g, at)
            # W3
            if mon in (2, 3) and g["conf"] and not g["neutral"] and f.get("cg", 0) >= 8 and o.get("cg", 0) >= 8:
                if v == "A" and at is not None:
                    base_ats.append(at)
                cu = f.get("cushion")
                if cu is not None and cu >= 1:
                    V.add(f"W3 the leader with a 1+ cushion, ven {v}: ATS", g, at)
                    if v == "A":
                        cell_ats.append(at) if at is not None else None
                        V.add(f"W3 on the road, {'hot-ATS (the built fade)' if hot else 'not hot-ATS'}: ATS", g, at)
                        V.add(f"W3 on the road, {f['tier']} league: ATS", g, at)
                        V.add(f"W3 on the road, {'February' if mon == 2 else 'March'}: ATS", g, at)
                        V.add("W3 on the road: the home side across ATS", g, lib.ats_p(g, "H"))
                        V.add(f"W3 on the road, {'laying 6+' if (sp or 0) <= -6 else 'laying under 6' if (sp or 0) < 0 else 'a dog'}: ATS", g, at)
                        if bd:
                            V.add(f"W3 on the road: {bd} ML", g, ml)
                if cu is not None and cu < 1 and v == "A":
                    V.add("W3 control - the leader by under a game, on the road: ATS", g, at)
                if cu is None and v == "A" and f.get("cg"):
                    V.add("W3 control - every other road team in Feb-Mar league play: ATS", g, at)
            # W1 outside the other box fades
            if s >= 2021 and bd == "dog" and lib.both(g, 5):
                b, ob = f["bx"], o["bx"]
                net = (b["o_tor"] - b["tor"]) - (ob["o_tor"] - ob["tor"])
                if net <= -0.05:
                    V.add("W1 the dog losing the turnover matchup by .05+: ML", g, ml)
                    V.add(f"W1, {'lucky from three too' if b['tp'] - 0.34 >= 0.03 else 'not hot from three'}: ML", g, ml)
                    V.add(f"W1, the dog's games {'5-12' if f['n'] <= 12 else '13+'}: ML", g, ml)
                    V.add(f"W1, {f['tier'] or 'no league'} dog: ML", g, ml)
                    V.add(f"W1, {'conference' if g['conf'] else 'non-conference'}: ML", g, ml)
    hw = g["hs"] > g["as"]
    if g["conf"] and g["stype"] == "2" and H["ck"] is not None:
        tb = tab[(s, H["ck"])]
        tb.setdefault(g["home"], [0, 0])[0 if hw else 1] += 1
        tb.setdefault(g["away"], [0, 0])[1 if hw else 0] += 1
k = lib.placebo(cell_ats, base_ats)
V.lines.append(f"PLACEBO W3: {len(cell_ats)} road leaders with a 1+ cushion at {sum(cell_ats)/len(cell_ats)*100:+.1f}% vs "
               f"{sum(base_ats)/len(base_ats)*100:+.1f}% for every Feb-Mar league road side ({len(base_ats)}) - a random draw "
               f"landed as far away {k} of 2,000 times")
print(V.lines[-1])
V.dump()
