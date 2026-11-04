"""s9 - THE UNTESTED FAVORITE vs THE BATTLE-TESTED DOG, COLLEGE HOOPS (schedule strength as a transition, never
studied: a walk-forward Elo, 2016-26 finals). Each team's last 4 opponents: WEAK = Elo under 1490 at that game (the bottom quarter of the margin Elo) (or
a team the files barely know - under 10 games last season and under 3 so far: the non-D1 tune-up), STRONG = 1690+ (the top quarter).
UNTESTED = all 4 weak; TESTED = 2+ strong. Cells: the dog +100..+350 by (dog tested / fav untested) and each alone,
the favorite -101..-200 across, ATS; Nov-Dec and Jan-Mar apart; the gauntlet (3+ strong in a row) side.
Train 2018-22, held out 2023 / 2024 / 2025 / 2026."""
import lib

C = lib.Cells()
fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
elo = lib.elo_walk(allf)
tl = lib.team_log(allf)
gp = {}
for g in allf:
    for t in (g["home"], g["away"]):
        gp[(g["season"], t)] = gp.get((g["season"], t), 0) + 1


def opp_class(team, p):
    """The class of team's opponent in its earlier game p."""
    opp = p["away"] if p["home"] == team else p["home"]
    e = elo[p["id"]][1 if p["home"] == team else 0]
    known = gp.get((p["season"] - 1, opp), 0) >= 10 or len([x for x in lib.before(tl, opp, p["start"]) if x["season"] == p["season"]]) >= 3
    if not known or e < 1490:
        return "weak"
    return "strong" if e >= 1690 else "mid"


vals = [elo[g["id"]][0] for g in allf if g["season"] == 2024]
vals.sort()
print("Elo quantiles 2024 (10/25/50/75/90):", [round(vals[int(len(vals) * q)]) for q in (0.1, 0.25, 0.5, 0.75, 0.9)])

for g in fin:
    if g["stype"] != "2" or g["season"] < 2018:
        continue
    s = g["season"]
    month = "Nov-Dec" if g["start"][5:7] in ("11", "12") else "Jan-Mar"
    cls = {}
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [p for p in lib.before(tl, team, g["start"], 4) if p["season"] == s]
        if len(prev) < 4:
            cls[side] = None
            continue
        c = [opp_class(team, p) for p in prev]
        cls[side] = ("untested" if all(x == "weak" for x in c) else "tested" if sum(1 for x in c if x == "strong") >= 2 else "mid",
                     all(x == "strong" for x in c[-3:]))
    for side, team, opp, o, won, home in lib.sides(g):
        me, ot = cls[side], cls["away" if side == "home" else "home"]
        if not me or not ot:
            continue
        p = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        cuts = [f"{me[0]} vs {ot[0]}", f"{me[0]} vs any"]
        if me[1]:
            cuts.append("gauntlet (3 strong in a row) side")
        if ot[1]:
            cuts.append("ACROSS a gauntlet side")
        for cut in cuts:
            for mm in (month, "all"):
                C.add(f"{cut} {mm} ATS", s, a)
                if lib.dog_band(o):
                    C.add(f"{cut} {mm} dog +100..+350", s, p)
                if -200 <= o <= -101:
                    C.add(f"{cut} {mm} fav -101..-200", s, p)

C.dump("s9", "s9 COLLEGE HOOPS UNTESTED FAVORITE (last 4 opponents weak) vs BATTLE-TESTED DOG (2+ of last 4 strong) - "
       "train 2018-22, held 2023 / 2024 / 2025 / 2026", (2018, 2022), [2023, 2024, 2025, 2026])
