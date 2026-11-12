"""11/12 DEEP PROGRAM - C: THREE NEW COLLEGE HOOPS ANGLES (the cbb10 walk-forward table: every finished game 2016-26,
closes 2018-26 at their own juice; TRAIN 2018-21 / HELD 2022-25; cells named before looking).
NOT re-run: the rematch as a SIDE (11/12 s9: the home team that covered by 15+ in game 1 ATS -13.2%, the side across
only reaches even; 11/3 (B) revenge) - the second meeting has been cut as a side twice; the roster / returning-
production reads (11/3 DEEP + KNOWLEDGE (A)); the public on the spread (11/11 S5: the 65%+ side -4.3%, fading it -3.8%).
  C3  THE HOME FLOOR IN LEAGUE PLAY vs OUTSIDE IT: the home side's spread and moneyline, conference games against
      non-conference, by month, by price - is home court priced differently once league play starts?
  C5  LAST SEASON'S TEAM vs THIS SEASON'S NUMBER (the carryover): in a team's first games, where last season's scoring
      margins say one thing and the closing spread another - which is right, and for how many games?
  C6  THE BIG NAMES: sixteen programs the public bets on name (fixed here before looking) - as favorites against the
      spread, by venue / month / size, and as moneyline dogs.
Usage: python results/studies/deep_1112/c1_hoops_new.py > results/studies/deep_1112/c1_hoops_new.out"""
import os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cbb10_1112"))
import lib as C          # noqa: E402

T = [g for g in C.build() if g["season"] >= 2018 and g["stype"] == "2"]
K = C.Cells("c1_hoops_new", (2018, 2021), (2022, 2023, 2024, 2025))
mon = lambda g: "Nov-Dec" if g["start"][5:7] in ("11", "12") else "Jan-Mar"      # noqa: E731
# ---------------- C3
for g in T:
    if g["neutral"] or g["sp"] is None:
        continue
    lab = "league game" if g["conf"] else "non-league"
    for side in "HA":
        v = "home" if side == "H" else "road"
        sp = C.spread(g, side)
        K.add(f"C3 {lab}: {v} ATS", g, C.ats_p(g, side))
        K.add(f"C3 {lab} {mon(g)}: {v} ATS", g, C.ats_p(g, side))
        if sp is not None:
            b = "laying 0.5-4" if -4 <= sp < 0 else "laying 4.5-9.5" if -9.5 <= sp < -4 else "laying 10+" if sp <= -10 else \
                "getting 0.5-4" if 0 < sp <= 4 else "getting 4.5-9.5" if 4 < sp <= 9.5 else "getting 10+" if sp >= 10 else None
            if b:
                K.add(f"C3 {lab}: {v} {b} ATS", g, C.ats_p(g, side))
        bd = C.band(C.odds(g, side))
        if bd in ("dog", "sfav"):
            K.add(f"C3 {lab}: {v} ML {'dog +100..+350' if bd == 'dog' else 'favorite -150..-101'}", g, C.ml_p(g, side))
            K.add(f"C3 {lab} {mon(g)}: {v} ML {'dog +100..+350' if bd == 'dog' else 'favorite -150..-101'}", g, C.ml_p(g, side))
    # the first league home games (January: the market still on non-league form?)
    if g["conf"] and g["H"]["cw"] + g["H"]["cl"] <= 2:
        K.add("C3 league game, the home team's first 3 league games: home ATS", g, C.ats_p(g, "H"))
    if g["conf"] and g["H"]["cw"] + g["H"]["cl"] >= 10:
        K.add("C3 league game, the home team 10+ league games in: home ATS", g, C.ats_p(g, "H"))
# ---------------- C5: last season's margins
prev = {}
acc = defaultdict(lambda: [0, 0.0])
for g in C.build():
    if g["stype"] == "2":
        for t, m in ((g["home"], g["hs"] - g["as"]), (g["away"], g["as"] - g["hs"])):
            a = acc[(g["season"], t)]
            a[0] += 1
            a[1] += m
for (s, t), (n, m) in acc.items():
    if n >= 20:
        prev[(s, t)] = m / n
for g in T:
    if g["sp"] is None:
        continue
    ph, pa = prev.get((g["season"] - 1, g["home"])), prev.get((g["season"] - 1, g["away"]))
    if ph is None or pa is None:
        continue
    n = min(g["H"]["n"], g["A"]["n"])
    win = "games 1-3" if n <= 2 else "games 4-7" if n <= 6 else "games 8-12" if n <= 11 else None
    if not win:
        continue
    gap = (ph - pa) * 0.6 + (0 if g["neutral"] else 3.2) + g["sp"]         # > 0: last season likes the home side more than the number
    for lo, hi in ((4, 7), (7, 11), (11, 99)):
        if lo <= abs(gap) < hi:
            side = "H" if gap > 0 else "A"
            K.add(f"C5 {win}: last season's team {lo}-{hi if hi < 99 else '+'} over the number: ITS side ATS", g, C.ats_p(g, side))
            K.add(f"C5 {win}: last season's team {lo}-{hi if hi < 99 else '+'} over the number: the side ACROSS ATS", g, C.ats_p(g, C.other(side)))
    if abs(gap) >= 7:
        side = "H" if gap > 0 else "A"
        bd = C.band(C.odds(g, side))
        if bd == "dog":
            K.add(f"C5 {win}: last season's team 7+ over the number: its ML as a dog +100..+350", g, C.ml_p(g, side))
        bo = C.band(C.odds(g, C.other(side)))
        if bo == "dog":
            K.add(f"C5 {win}: last season's team 7+ over the number: the dog ACROSS +100..+350", g, C.ml_p(g, C.other(side)))
# ---------------- C6: the big names
BIG = {"Duke", "Kansas", "Kentucky", "North Carolina", "UCLA", "Indiana", "Michigan St", "Arizona", "Gonzaga", "UConn",
       "Villanova", "Louisville", "Syracuse", "Michigan", "Texas", "Ohio State"}
seen = set()
for g in T:
    for side, nm, on in (("H", g["hn"], g["an"]), ("A", g["an"], g["hn"])):
        if nm not in BIG or on in BIG:
            continue
        seen.add(nm)
        sp = C.spread(g, side)
        v = "neutral" if g["neutral"] else ("home" if side == "H" else "road")
        if sp is not None and sp < 0:
            K.add("C6 a big name laying points: ATS", g, C.ats_p(g, side))
            K.add("C6 a big name laying points: the side ACROSS ATS", g, C.ats_p(g, C.other(side)))
            K.add(f"C6 a big name laying points, {v}: ATS", g, C.ats_p(g, side))
            K.add(f"C6 a big name laying points, {mon(g)}: ATS", g, C.ats_p(g, side))
            K.add(f"C6 a big name laying {'10+' if sp <= -10 else '5-9.5' if sp <= -5 else 'under 5'}: ATS", g, C.ats_p(g, side))
            K.add(f"C6 a big name laying points, {'league game' if g['conf'] else 'non-league'}: ATS", g, C.ats_p(g, side))
            if v == "road" and g["conf"]:
                K.add("C6 a big name laying points on the road in league play: the home dog ATS", g, C.ats_p(g, C.other(side)))
        if sp is not None and sp > 0:
            K.add("C6 a big name GETTING points: ATS", g, C.ats_p(g, side))
        bd = C.band(C.odds(g, side))
        if bd == "sfav":
            K.add("C6 a big name ML favorite -150..-101", g, C.ml_p(g, side))
            K.add("C6 the dog ACROSS a big name at -150..-101", g, C.ml_p(g, C.other(side)))
        if bd == "dog":
            K.add("C6 a big name ML dog +100..+350", g, C.ml_p(g, side))
K.p(f"big names found in the files: {sorted(seen)}")
K.dump()
