"""Study 8 (11/3): NBA - THE EARLY-SEASON SAMPLE-SIZE TRAP: record vs margin. A 7-2 team that has outscored people by a
point a game is a .500 team the standings call a contender; the NHL version is BUILT (sports.pyth_luck, +2 for the dog
whose record sits under its goals). The NBA has never been cut this way. Games 6-20 (and 21-40 as the comparison):
this season's win % minus the margin-implied win % (Pythagorean, exponent 14) - LUCKY (+0.15 or more) / UNLUCKY (-0.15
or less). Cells: the lucky team as a favorite (fade), the unlucky team as a dog (buy), the gap between the two teams,
ATS. Closing prices 2016-26 + the paid 2020-23 MORNING look. Train 2016-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
EXP = 14.0
fin = lib.finals("nba")
allf = lib.all_finals("nba")
tl = lib.team_log(allf)
mo = lib.nba_morning()


def luck(team, g):
    rows = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
    n = len(rows)
    if n < 5:
        return None
    pf = sum(x["hs"] if x["home"] == team else x["as"] for x in rows)
    pa = sum(x["as"] if x["home"] == team else x["hs"] for x in rows)
    w = sum(1 for x in rows if lib.won_g(x, team)) / n
    exp = pf ** EXP / (pf ** EXP + pa ** EXP) if pf and pa else 0.5
    return n, w - exp, (pf - pa) / n


C = lib.Cells()
for g in fin:
    for side, team, opp, o, won, is_home in lib.sides(g):
        L, OL = luck(team, g), luck(opp, g)
        if not L or not OL:
            continue
        n, gap, mpg = L
        on, ogap, ompg = OL
        win = "6-20" if n + 1 <= 20 else "21-40" if n + 1 <= 40 else None
        if not win:
            continue
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        tags = []
        if gap >= 0.15:
            tags.append("LUCKY (record 15+ pts over its margin)")
        if gap <= -0.15:
            tags.append("UNLUCKY (record 15+ pts under its margin)")
        if gap - ogap >= 0.2:
            tags.append("luck gap +0.2 over the opponent")
        if gap - ogap <= -0.2:
            tags.append("luck gap -0.2 under the opponent")
        if gap >= 0.15 and ogap <= -0.15:
            tags.append("LUCKY vs UNLUCKY")
        for tg in tags:
            C.add(f"games {win} | {tg} | ATS", g["season"], a)
            if -200 <= o <= -101:
                C.add(f"games {win} | {tg} | fav ML -101..-200", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and -200 <= m[0] <= -101:
                    C.add(f"games {win} | {tg} | fav ML | MORNING", g["season"], lib.profit(won, m[1]))
            if lib.dog_band(o):
                C.add(f"games {win} | {tg} | dog ML +100..+350", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"games {win} | {tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
        # the base for the window
        C.add(f"games {win} | base | ATS", g["season"], a)
        if lib.dog_band(o):
            C.add(f"games {win} | base | dog ML +100..+350", g["season"], p)
        if -200 <= o <= -101:
            C.add(f"games {win} | base | fav ML -101..-200", g["season"], p)
C.dump("s8", "NBA: RECORD vs MARGIN (the lucky / unlucky team by Pythagorean, games 6-20 vs 21-40; close + the paid "
       "2020-23 morning; train 2016-22, held 2023-26)", TRAIN, HELD)
