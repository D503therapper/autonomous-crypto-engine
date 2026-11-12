"""11/12 DEEP PROGRAM - C3 follow-up: THE NON-LEAGUE ROAD FAVORITE ON THE SPREAD (c1's strongest cells: a road team
laying points outside its league - 0.5-4 -14.1%, 4.5-9.5 -7.3%, 10+ -20.9%). One cell, the checks: both halves, every
season, the month, the size, the tier, the control (the same road favorite INSIDE its league), the home dog across, a
placebo, and what is left after the two built fades that overlap (the top-25 road team in Nov-Dec is not in this
table - so the overlap is read by price: the big road favorite is the ranked team).
Usage: python results/studies/deep_1112/c1b_road_fav.py > results/studies/deep_1112/c1b_road_fav.out"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cbb10_1112"))
import lib as C          # noqa: E402

T = [g for g in C.build() if g["season"] >= 2018 and g["stype"] == "2" and not g["neutral"] and g["sp"] is not None]
K = C.Cells("c1b_road_fav", (2018, 2021), (2022, 2023, 2024, 2025))
nd = lambda g: g["start"][5:7] in ("11", "12")      # noqa: E731
pool, mine = [], []
for g in T:
    rf = g["sp"] > 0                                  # the road team lays the points
    p_road, p_home = C.ats_p(g, "A"), C.ats_p(g, "H")
    if nd(g) and p_road is not None:
        pool.append(p_road)
    if not rf:
        continue
    lab = "non-league" if not g["conf"] else "league"
    K.add(f"{lab} road favorite ATS, every month", g, p_road)
    if nd(g):
        K.add(f"{lab} road favorite ATS, Nov-Dec", g, p_road)
        K.add(f"{lab}: the HOME DOG across ATS, Nov-Dec", g, p_home)
    else:
        K.add(f"{lab} road favorite ATS, Jan-Mar", g, p_road)
    if not g["conf"] and nd(g):
        if p_road is not None:
            mine.append(p_road)
        K.add(f"non-league Nov-Dec road favorite laying {'0.5-4' if g['sp'] <= 4 else '4.5-9.5' if g['sp'] <= 9.5 else '10+'}: ATS", g, p_road)
        K.add(f"non-league Nov-Dec road favorite, home team tier {g['H']['tier']}: ATS", g, p_road)
        K.add(f"non-league Nov-Dec road favorite, {'both 4+ games in' if min(g['H']['n'], g['A']['n']) >= 4 else 'games 1-4'}: ATS", g, p_road)
        K.add(f"non-league Nov-Dec road favorite, {'November' if g['start'][5:7] == '11' else 'December'}: ATS", g, p_road)
        bd = C.band(C.odds(g, "H"))
        if bd == "dog":
            K.add("non-league Nov-Dec: the home dog's MONEYLINE +100..+350", g, C.ml_p(g, "H"))
        if C.band(C.odds(g, "A")) == "sfav":
            K.add("non-league Nov-Dec: the road favorite's moneyline -150..-101 (the built 11/3 fade's cell)", g, C.ml_p(g, "A"))
        if g["sp"] > 4:
            K.add("non-league Nov-Dec road favorite laying 4.5+ (past the built small-favorite fade): ATS", g, p_road)
            K.add("non-league Nov-Dec: the home dog getting 4.5+ ATS", g, p_home)
tgt = sum(mine) / len(mine)
rnd = random.Random(1112)
hits = sum(1 for _ in range(2000) if sum(rnd.sample(pool, len(mine))) / len(mine) <= tgt)
K.p(f"PLACEBO: a random {len(mine)} Nov-Dec road sides did as badly as the cell ({100 * tgt:+.1f}%) {hits} of 2,000 times (the pool {100 * sum(pool) / len(pool):+.1f}%)")
K.dump()
