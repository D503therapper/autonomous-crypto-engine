"""S2 (college hoops) / S9 (NBA) - THE OPPONENTS' FREE-THROW LUCK, and S6 (NBA) - THE NBA SIDE LUCKY FROM THREE.
Never studied: the 11/4 knowledge study read FT% STREAKS (own, as a dog) and the free-throw RATE; the 11/9 build read the
college hoops 3P NET (own minus opponents' 3P%) - S6 is its NBA twin (the NBA has full box scores 2016-26; the 10/?
NBA threes study predicted one night's makes, never the season's luck vs the price).
A defense has almost no say in the free throws its opponents make - a team whose opponents have shot a low FT% against
it has a points margin flattered by luck (and the reverse). OPP FT% = its opponents' made / attempted free throws this
season before tonight, as the gap to the PRIOR season's league average (no look-ahead).
NBA 3P NET = own 3P% minus its opponents' 3P%, season to date (10+ games, the 11/9 build's shape at the NBA's spread).
Cells: favorite -101..-250 / dog +100..+350 at the close, ATS at the close, ESPN's open as the second price.
NBA: TRAIN 2016-22 (box 2016-26), HELD 2023 / 2024 / 2025, 2026 live. College hoops: TRAIN 2021-22, HELD 2023-25."""
import sys
from collections import defaultdict

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "nba"
fin = lib.finals(LG)
allf = [g for g in lib.all_finals(LG) if g["stype"] == "2"]


def split(s):
    try:
        a, b = str(s).split("-")
        return int(a), int(b)
    except (ValueError, AttributeError):
        return None


if LG == "ncaab":
    import sports_ncaab_box as nb
    raw = nb.load_box()
    BOX = {gid: {t: (v["ftm"], v["fta"], v["tpm"], v["tpa"]) for t, v in tm.items()} for gid, tm in raw.items()}
    TRAIN, HELD, MIN_G = (2021, 2022), (2023, 2024, 2025, 2026), 5
else:
    rows = lib.box_rows("nba")
    BOX = {}
    for gid, tm in rows.items():
        d = {}
        for t, rs in tm.items():
            ftm = fta = tpm = tpa = 0
            for r in rs:
                ft = split(r["st"].get("freeThrowsMade-freeThrowsAttempted"))
                tp = split(r["st"].get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
                if ft:
                    ftm += ft[0]
                    fta += ft[1]
                if tp:
                    tpm += tp[0]
                    tpa += tp[1]
            if fta + tpa > 0:
                d[t] = (ftm, fta, tpm, tpa)
        if len(d) == 2:
            BOX[gid] = d
    TRAIN, HELD, MIN_G = (2016, 2022), (2023, 2024, 2025, 2026), 10

run = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0, 0, 0])   # games, own ftm, fta, opp ftm, fta, own tpm, tpa, opp tpm, tpa
pre = {}
lg_ft = defaultdict(lambda: [0, 0])
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    b = BOX.get(g["id"])
    if not b or g["home"] not in b or g["away"] not in b:
        continue
    for side, opp in (("home", "away"), ("away", "home")):
        r = run[(g["season"], g[side])]
        me, th = b[g[side]], b[g[opp]]
        r[0] += 1
        r[1] += me[0]; r[2] += me[1]; r[3] += th[0]; r[4] += th[1]
        r[5] += me[2]; r[6] += me[3]; r[7] += th[2]; r[8] += th[3]
    lg_ft[g["season"]][0] += b[g["home"]][0] + b[g["away"]][0]
    lg_ft[g["season"]][1] += b[g["home"]][1] + b[g["away"]][1]
avg = {s: v[0] / v[1] for s, v in lg_ft.items() if v[1]}
print(LG, "league FT% by season:", {s: round(v, 3) for s, v in sorted(avg.items())})
FT_CUT = (0.03, 0.05)
TP_CUT = (0.02, 0.035) if LG == "nba" else (0.05, 0.08)

cells = lib.Cells()
for g in fin:
    if g["stype"] != "2" or g["season"] < TRAIN[0]:
        continue
    base = avg.get(g["season"] - 1) or avg.get(g["season"])
    if base is None:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        p = pre.get((g["id"], side))
        if not p or p[0] < MIN_G:
            continue
        n, ftm, fta, oftm, ofta, tpm, tpa, otpm, otpa = p
        s = g["season"]
        labs = []
        if ofta >= (60 if LG == "ncaab" else 150):
            d = oftm / ofta - base                    # opponents' FT% vs the league (negative = lucky defense)
            if d <= -FT_CUT[1]:
                labs.append(f"OPP FT% {FT_CUT[1]*100:.0f}+ pts under the league (lucky D)")
            if d <= -FT_CUT[0]:
                labs.append(f"OPP FT% {FT_CUT[0]*100:.0f}+ under (lucky D)")
            if d >= FT_CUT[0]:
                labs.append(f"OPP FT% {FT_CUT[0]*100:.0f}+ over (unlucky D)")
            if d >= FT_CUT[1]:
                labs.append(f"OPP FT% {FT_CUT[1]*100:.0f}+ over (unlucky D)")
            if abs(d) < 0.01:
                labs.append("OPP FT% within 1 (control)")
        if LG == "nba" and tpa >= 200 and otpa >= 200:
            net = tpm / tpa - otpm / otpa
            if net >= TP_CUT[0]:
                labs.append(f"3P NET +{TP_CUT[0]*100:.1f}+ (lucky)")
            if net >= TP_CUT[1]:
                labs.append(f"3P NET +{TP_CUT[1]*100:.1f}+ (lucky)")
            if net <= -TP_CUT[0]:
                labs.append(f"3P NET -{TP_CUT[0]*100:.1f} or worse (unlucky)")
            if abs(net) < 0.01:
                labs.append("3P NET within 1 (control)")
        stage = "games 3-5" if LG == "ncaab" and n <= 4 else None
        pl = lib.profit(won, lib.dec(o))
        oo = g["oh"] if home else g["oa"]
        a = lib.ats(g, side)
        for lab in labs:
            for pre_ in ([""] + ([f"{stage} | "] if stage else [])):
                if -250 <= o <= -101:
                    cells.add(f"{pre_}{lab} | FAV ML", s, pl)
                    if oo and -250 <= oo <= -101:
                        cells.add(f"{pre_}{lab} | FAV ML open", s, lib.profit(won, lib.dec(oo)))
                if lib.dog_band(o):
                    cells.add(f"{pre_}{lab} | DOG ML", s, pl)
                    if oo and lib.dog_band(oo):
                        cells.add(f"{pre_}{lab} | DOG ML open", s, lib.profit(won, lib.dec(oo)))
                cells.add(f"{pre_}{lab} | ATS", s, a)
tag = "s2_ncaab" if LG == "ncaab" else "s6_s9_nba"
cells.dump(tag, f"{tag} - opponents' FT% vs the prior season's league average / the NBA 3P NET; {MIN_G}+ boxed games; "
           f"close / ATS / ESPN open", TRAIN, HELD)
