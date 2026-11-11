"""B5 (also college hoops question A) - A COLLEGE HOOPS SPREAD PLAY FROM THE BUILT ATS FADES?
Every college hoops study since 11/3 found the same thing: the moneyline dog is the worst market on the board, and
the edges that hold out of sample are ATS FADES (lucky from three z -8, the hot-ATS side z -6.6, the glass, the top-25
road team Nov-Dec, the top scorer out). A fade moves a spread rank a few points - the question the owner asked on
11/11 is whether, ADDED UP, they make a spread side that clears -110 (52.4%).
1. THE THREE-POINT GAP (new cut - 11/9 read one team's NET; this is MY net minus THEIRS): the side across.
2. THE STACK: the built spread weights exactly as sports.py carries them (3P luck -/+0.02, hot-ATS gap -/+0.03, the
   glass +/-0.02, the ranked road team Nov-Dec -/+0.03, the top scorer out -0.03), summed per side minus the other
   side's; ATS by the stack's size.
3. WALK-FORWARD: a ridge on the cover margin over the same inputs, each season fit only on the seasons before it.
Box seasons 2021-25 (the team box starts 2021): TRAIN 2021-22, HELD 2023 / 2024 / 2025 apart. Graded at the closing
spread and its own juice. Caveat said up front: the weights' DIRECTIONS were found on these same seasons (each one
held out on 2023-25 in its own study); the stack's size cut is chosen on train and read on held."""
import os, pickle, statistics
from collections import defaultdict
import lib
import sports_ncaab_box as nb

o = lib.Out("b5")
rows = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
rows = [r for r in rows if 2021 <= r["season"] <= 2025 and r["stype"] == "2"]
rows.sort(key=lambda r: (r["start"], r["id"]))
box = nb.load_box()
tb = lib.teambox("ncaab")
TR, HE = (2021, 2022), (2023, 2024, 2025)

st = defaultdict(lambda: {"n": 0, "m3": 0, "a3": 0, "om3": 0, "oa3": 0, "cm": [], "rb": [], "nb": 0})
feat = {}
byg = defaultdict(list)
for r in rows:
    byg[r["id"]].append(r)
order = []
seen = set()
for r in rows:
    if r["id"] not in seen:
        seen.add(r["id"])
        order.append(r["id"])
for gid in order:
    pr = byg[gid]
    if len(pr) != 2:
        continue
    for r in pr:
        s = st[(r["season"], r["team"])]
        f = {"tp": None, "cm": None, "rb": None}
        if s["nb"] >= 5 and s["a3"] >= 60 and s["oa3"] >= 60:
            f["tp"] = s["m3"] / s["a3"] - s["om3"] / s["oa3"]
        if len(s["cm"]) >= 10:
            f["cm"] = statistics.mean(s["cm"])
        if len(s["rb"]) >= 5:
            f["rb"] = statistics.mean(s["rb"])
        feat[(gid, r["team"])] = f
    b = box.get(gid)
    t = tb.get(gid) or {}
    for r in pr:
        s = st[(r["season"], r["team"])]
        if r.get("sp") is not None:
            s["cm"].append(r["margin"] + r["sp"])
        if b and r["team"] in b and r["opp"] in b:
            s["nb"] += 1
            s["m3"] += b[r["team"]]["tpm"]; s["a3"] += b[r["team"]]["tpa"]
            s["om3"] += b[r["opp"]]["tpm"]; s["oa3"] += b[r["opp"]]["tpa"]
        try:
            s["rb"].append(float(t[r["team"]]["totalRebounds"]) - float(t[r["opp"]]["totalRebounds"]))
        except (KeyError, ValueError, TypeError):
            pass


def atsp(r):
    x = r["margin"] + r["sp"]
    return None if x == 0 else lib.profit(x > 0, lib.dec(r.get("spodds") or -110))


C1, C2, C3 = lib.Cells(), lib.Cells(), lib.Cells()
data = []                                           # (season, x vector, cover margin, row)
for gid in order:
    pr = byg[gid]
    if len(pr) != 2 or pr[0].get("sp") is None:
        continue
    for r, q in ((pr[0], pr[1]), (pr[1], pr[0])):
        a = atsp(r)
        s = r["season"]
        me, th = feat[(gid, r["team"])], feat[(gid, q["team"])]
        C1.add("BASE every spread side", s, a)
        w, parts = 0.0, 0
        d3 = None
        if me["tp"] is not None and th["tp"] is not None:
            d3 = me["tp"] - th["tp"]
            for cut in (0.05, 0.08, 0.12):
                if d3 <= -cut:
                    C1.add(f"KEY 3P gap: the side {int(cut*100)}+ pts LESS lucky than the opponent", s, a)
                    C1.add(f"3P gap -{int(cut*100)}: {'home' if r['venue']=='home' else 'road/neutral'}", s, a)
                    C1.add(f"3P gap -{int(cut*100)}: {'dog' if r['sp'] > 0 else 'fav'}", s, a)
                    C1.add(f"3P gap -{int(cut*100)}: {'Nov-Dec' if r['nd'] else 'Jan-Mar'}", s, a)
                if d3 >= cut:
                    C1.add(f"3P gap: the side {int(cut*100)}+ pts MORE lucky (the fade)", s, a)
        if me["tp"] is not None and me["tp"] >= 0.05:
            w -= 0.02; parts += 1
        if th["tp"] is not None and th["tp"] >= 0.05:
            w += 0.02; parts += 1
        g = None
        if me["cm"] is not None and th["cm"] is not None:
            g = me["cm"] - th["cm"]
            if g >= 3:
                w -= 0.03; parts += 1
            elif g <= -3:
                w += 0.03; parts += 1
        rg = None
        if me["rb"] is not None and th["rb"] is not None:
            rg = me["rb"] - th["rb"]
            if rg >= 6:
                w += 0.02; parts += 1
            elif rg <= -6:
                w -= 0.02; parts += 1
        rr = 0
        if r["nd"] and r["venue"] == "away" and r.get("rank25"):
            w -= 0.03; parts += 1; rr = -1
        if r["nd"] and r["venue"] == "home" and r.get("orank25"):
            w += 0.03; parts += 1; rr = 1
        to = 0
        if r.get("top_out"):
            w -= 0.03; parts += 1; to -= 1
        if r.get("o_top_out"):
            w += 0.03; parts += 1; to += 1
        w = round(w, 3)
        for cut in (0.03, 0.04, 0.05, 0.06, 0.08):
            if w >= cut:
                C2.add(f"KEY STACK +{cut:.2f} or more", s, a)
                C2.add(f"STACK +{cut:.2f}+: {'dog' if r['sp'] > 0 else 'fav'}", s, a)
                C2.add(f"STACK +{cut:.2f}+: {'home' if r['venue']=='home' else 'road/neutral'}", s, a)
                C2.add(f"STACK +{cut:.2f}+: {'Nov-Dec' if r['nd'] else 'Jan-Mar'}", s, a)
                if r["venue"] == "home" and r["sp"] < -12:
                    C2.add(f"STACK +{cut:.2f}+: a 12+ home favorite (the guard)", s, a)
                else:
                    C2.add(f"KEY STACK +{cut:.2f}+, never a 12+ home favorite", s, a)
            if w <= -cut:
                C2.add(f"STACK -{cut:.2f} or worse (the fade side)", s, a)
        if w >= 0.05:
            C2.add(f"STACK +0.05+: {parts} weights firing", s, a)
            # the second market: the same side's MONEYLINE at the close and at ESPN's open (2023-25)
            if r.get("ml") is not None and -250 <= r["ml"] <= 350:
                C2.add("2ND CHECK stack +0.05+ on the MONEYLINE (-250..+350), close", s, lib.profit(r["won"], lib.dec(r["ml"])))
                C2.add(f"2ND CHECK stack +0.05+ ML close, {'dog' if r['ml'] > 0 else 'fav'}", s, lib.profit(r["won"], lib.dec(r["ml"])))
                if r.get("mlo") is not None and -250 <= r["mlo"] <= 350:
                    C2.add("2ND CHECK stack +0.05+ on the MONEYLINE, ESPN's OPEN", s, lib.profit(r["won"], lib.dec(r["mlo"])))
        # the live code's one-sided form (no 'across' half for the top scorer out / the three-point luck)
        w1 = w - (0.02 if th["tp"] is not None and th["tp"] >= 0.05 else 0) - (0.03 if r.get("o_top_out") else 0)
        if round(w1, 3) >= 0.05:
            C2.add("ONE-SIDED (today's rank weights only) +0.05+", s, a)
        if w >= 0.05 and round(w1, 3) < 0.05:
            C2.add("KEY the ACROSS half makes it +0.05+ (new rows)", s, a)
        if th["tp"] is not None and th["tp"] >= 0.05 and not (me["tp"] is not None and me["tp"] >= 0.05):
            C2.add("KEY ACROSS a side lucky from three (NET +5+), me not", s, a)
        if r.get("o_top_out") and not r.get("top_out"):
            C2.add("KEY ACROSS a side whose top scorer missed its last game", s, a)
        if d3 is not None and g is not None and rg is not None:
            data.append((s, [1.0, d3 * 100, max(-10, min(10, g)), max(-12, min(12, rg)), rr, to,
                             1.0 if r["venue"] == "home" else (-1.0 if r["venue"] == "away" else 0.0)],
                         r["margin"] + r["sp"], a))

o.p(f"B5 - THE COLLEGE HOOPS SPREAD STACK: {len(order)} games 2021-25; TRAIN 2021-22, HELD 2023/24/25")
o.p("\n1. THE THREE-POINT GAP (my NET minus theirs)")
o.cells(C1, TR, HE, minn=30, zshow=99)
o.p("\n2. THE STACK (the built spread weights summed, my side minus theirs)")
o.cells(C2, TR, HE, minn=30, zshow=99)
o.p("\n3. WALK-FORWARD ridge on the cover margin (each season on the seasons before it)")
import numpy as np
for hs in (2023, 2024, 2025):
    tr = [d for d in data if d[0] < hs]
    te = [d for d in data if d[0] == hs]
    b = lib.ridge([d[1] for d in tr], [d[2] for d in tr], 50.0)
    if hs == 2023:
        o.p("   weights (const, 3P gap per pt, hot-ATS gap per pt, rebound gap per board, ranked road, top out, home):",
            " ".join(f"{x:+.3f}" for x in b))
    for d in te:
        e = float(np.dot(b, d[1]))
        for lo, hi, nm in ((1.5, 99, "+1.5 or more"), (1.0, 1.5, "+1.0..+1.5"), (0.5, 1.0, "+0.5..+1.0"), (-0.5, 0.5, "-0.5..+0.5"),
                           (-1.0, -0.5, "-1.0..-0.5"), (-99, -1.0, "-1.0 or worse")):
            if lo <= e < hi:
                C3.add(f"KEY predicted edge {nm} pts", d[0], d[3])
        if e >= 1.0:
            C3.add("KEY predicted edge +1.0 or more", d[0], d[3])
o.cells(C3, (2023, 2023), (2024, 2025), zshow=99)
o.p(f"\ncells: {len(C1.c) + len(C2.c) + len(C3.c)}")
o.save()
