"""11/7 S5-S8 (never studied - checked against the 'Not re-run' lists):
S5 NBA - the game after a 20+ point HOME loss (embarrassed at home): the side as a favorite / dog, ATS; dose 15+ / 25+.
S6 NBA / NHL - last season's FINALISTS (the two teams in the last postseason game) in games 1-25 of the next season.
S7 NHL - the game after a 4+ goal HOME loss (the S5 shape in hockey).
S8 COLLEGE HOOPS - the game after an OVERTIME game, Nov-Dec (early-season legs), the side as favorite / dog, ATS.
Prices: the game files' close; ESPN's open (2023-26) the second price. TRAIN 2016-22 (hoops 2018-22) / held 2023-26."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


def periods(x):
    try:
        return len([p for p in str(x or "").split(",") if p.strip() != ""])
    except Exception:  # noqa: BLE001
        return 0


C = lib.Cells()


def add_side(tag, g, side, o, won, s):
    p = lib.profit(won, lib.dec(o))
    if -250 <= o <= -101:
        C.add(f"{tag} fav -101..-250", s, p)
    if 100 <= o <= 350:
        C.add(f"{tag} dog +100..+350", s, p)
    C.add(f"{tag} ATS", s, lib.ats(g, side))
    oo = g["oh"] if side == "home" else g["oa"]
    if oo:
        if -250 <= oo <= -101:
            C.add(f"{tag} fav -101..-250 OPEN", s, lib.profit(won, lib.dec(oo)))
        if 100 <= oo <= 350:
            C.add(f"{tag} dog +100..+350 OPEN", s, lib.profit(won, lib.dec(oo)))


for lg, big, tag in (("nba", (15, 20, 25), "S5 NBA"), ("nhl", (3, 4, 5), "S7 NHL")):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
    tl = lib.team_log(lib.all_finals(lg))
    for g in fin:
        for side, team, opp, o, won, home in lib.sides(g):
            prev = lib.before(tl, team, g["start"], 1)
            if not prev or prev[0]["season"] != g["season"] or prev[0]["stype"] != "2":
                continue
            lg_ = prev[0]
            m = lib.margin_g(lg_, team)
            at_home = lg_["home"] == team and not lg_["neutral"]
            base = "control (any other last game)"
            for b in big:
                if m <= -b:
                    k = f"{tag} off a {b}+ {'HOME' if at_home else 'road'} loss"
                    add_side(k, g, side, o, won, g["season"])
            if not m <= -big[0]:
                add_side(f"{tag} {base}", g, side, o, won, g["season"])
            if m <= -big[1] and at_home:
                add_side(f"{tag} off a {big[1]}+ HOME loss, tonight {'home' if home else 'road'}", g, side, o, won, g["season"])

# S6 finalists
for lg in ("nba", "nhl"):
    allf = lib.all_finals(lg)
    post = {}
    for g in allf:
        if g["stype"] == "3":
            post.setdefault(g["season"], []).append(g)
    final_teams = {s: {gs[-1]["home"], gs[-1]["away"]} for s, gs in post.items() if gs}
    tl = lib.team_log(allf)
    for g in lib.finals(lg):
        if g["stype"] != "2":
            continue
        for side, team, opp, o, won, home in lib.sides(g):
            ft = final_teams.get(g["season"] - 1)
            if not ft:
                continue
            n = len([x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"] and x["stype"] == "2"])
            if n >= 25:
                continue
            if team in ft:
                add_side(f"S6 {lg.upper()} last season's finalist, games 1-25", g, side, o, won, g["season"])
            elif opp in ft:
                add_side(f"S6 {lg.upper()} facing last season's finalist, games 1-25", g, side, o, won, g["season"])

# S8 college hoops after overtime, Nov-Dec
fin = [g for g in lib.finals("ncaab") if g["stype"] == "2"]
allf = lib.finals("ncaab")
byid = {g["id"]: g for g in allf}
tl = lib.team_log(lib.all_finals("ncaab"))
for g in fin:
    mo = int(g["start"][5:7])
    if mo not in (11, 12):
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        prev = lib.before(tl, team, g["start"], 1)
        if not prev or prev[0]["season"] != g["season"]:
            continue
        pg = byid.get(prev[0]["id"])
        if not pg:
            continue
        npd = max(periods(pg["ls_h"]), periods(pg["ls_a"]))
        if npd == 0:
            continue
        days = lib.days_between(prev[0]["start"], g["start"])
        ot = npd > 2
        w = lib.won_g(prev[0], team)
        k = "S8 NCAAB Nov-Dec off an OT game" if ot else "S8 NCAAB Nov-Dec control (last game regulation)"
        add_side(k, g, side, o, won, g["season"])
        if ot:
            add_side(f"S8 NCAAB off OT, {'won' if w else 'lost'} it", g, side, o, won, g["season"])
            add_side(f"S8 NCAAB off OT, {'1 day later' if days < 1.6 else '2+ days later'}", g, side, o, won, g["season"])
            if npd >= 4:
                add_side("S8 NCAAB off 2+ OT", g, side, o, won, g["season"])


def split(k):
    return ((2018, 2022), [2023, 2024, 2025, 2026]) if "NCAAB" in k else ((2016, 2022), [2023, 2024, 2025, 2026])


C.dump("s5_s8", "11/7 S5-S8 (close unless OPEN; TRAIN 2016-22, college hoops 2018-22 / held 2023-26)", split)
