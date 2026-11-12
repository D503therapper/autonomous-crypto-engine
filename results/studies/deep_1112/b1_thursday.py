"""11/12 DEEP PROGRAM - B1: THURSDAY / SHORT-WEEK NFL GAMES - sides, spreads, totals (nflverse's schedule file: every
NFL close 1999-2026 - results/studies/spreads2_1111/nfl.py). TRAIN 1999-2014 / BLIND 2015-26, the close at its juice
(-110 when the file has none), a push = 0. Cells named before looking. NOT re-run: the road team on a short week ATS
(-6.4% on 299, 11/11 S5), primetime totals as a whole (over -15.7% / under +6.9%, 11/12 s13), division unders.
A 'short Thursday' = a Thursday game with both teams on 4 days or less (not the season opener, which is a full week).
Usage: python results/studies/deep_1112/b1_thursday.py > results/studies/deep_1112/b1_thursday.out"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "spreads2_1111"))
import nfl as N          # noqa: E402

G = N.games(reg_only=True)
CELLS = [0]


def ats(g, side):
    r = g["m"] + g["hl"] if side == "H" else -(g["m"] + g["hl"])
    o = g["hso"] if side == "H" else g["aso"]
    if o is None or abs(o) < 100 or abs(o) > 150:
        o = -110
    return 0.0 if r == 0 else (N.dec(o) - 1 if r > 0 else -1.0)


def ml(g, side):
    o = g["hml"] if side == "H" else g["aml"]
    if o is None or g["m"] == 0:
        return None
    return N.dec(o) - 1 if (g["m"] > 0) == (side == "H") else -1.0


def tot(g, side):
    if g["total"] is None or g["pts"] == g["total"]:
        return 0.0 if g["total"] is not None else None
    return (100 / 110) if (g["pts"] > g["total"]) == (side == "over") else -1.0


def cell(name, rows):
    """rows = [(season, profit)]"""
    CELLS[0] += 1
    rows = [(s, p) for s, p in rows if p is not None]
    tr = [p for s, p in rows if s <= 2014]
    bl = [p for s, p in rows if s >= 2015]
    r3 = [p for s, p in rows if s >= 2023]
    up, ns, _ = N.by_season([(s, p) for s, p in rows if s >= 2015])
    print(f"  {name:66s} {N.st([p for _, p in rows])} | 99-14 {N.roi(tr):+6.1f}% ({len(tr):4d}) | 15-26 {N.roi(bl):+6.1f}% ({len(bl):4d}) {up}/{ns} up | 23-26 {N.roi(r3):+6.1f}% ({len(r3)})")


def fav(g):
    return "H" if g["hl"] < 0 else "A" if g["hl"] > 0 else None


thu = [g for g in G if g["wd"] == "Thursday"]
short = [g for g in thu if (g["hrest"] or 9) <= 4 and (g["arest"] or 9) <= 4]
tg = [g for g in thu if g["date"][5:7] == "11" and 22 <= int(g["date"][8:]) <= 28]
print(f"regular-season games {len(G)}; Thursday {len(thu)}; short Thursday (both on 4 days) {len(short)}; Thanksgiving {len(tg)}")
other = lambda s: "A" if s == "H" else "H"      # noqa: E731
for nm, S in (("SHORT THURSDAY", short), ("SHORT THURSDAY, not Thanksgiving", [g for g in short if g not in tg]), ("EVERY THURSDAY", thu)):
    print(f"\n== {nm} ({len(S)} games)")
    print(" -- the spread")
    cell("home side ATS", [(g["season"], ats(g, "H")) for g in S])
    cell("road side ATS", [(g["season"], ats(g, "A")) for g in S])
    cell("favorite ATS", [(g["season"], ats(g, fav(g))) for g in S if fav(g)])
    cell("dog ATS", [(g["season"], ats(g, other(fav(g)))) for g in S if fav(g)])
    cell("home favorite ATS", [(g["season"], ats(g, "H")) for g in S if g["hl"] < 0])
    cell("home favorite laying 1-3 ATS", [(g["season"], ats(g, "H")) for g in S if -3 <= g["hl"] <= -1])
    cell("home favorite laying 3.5-6.5 ATS", [(g["season"], ats(g, "H")) for g in S if -6.5 <= g["hl"] <= -3.5])
    cell("home favorite laying 7+ ATS", [(g["season"], ats(g, "H")) for g in S if g["hl"] <= -7])
    cell("home dog ATS", [(g["season"], ats(g, "H")) for g in S if g["hl"] > 0])
    cell("road favorite ATS", [(g["season"], ats(g, "A")) for g in S if g["hl"] > 0])
    cell("division game: home ATS", [(g["season"], ats(g, "H")) for g in S if g["div"]])
    cell("division game: home favorite ATS", [(g["season"], ats(g, "H")) for g in S if g["div"] and g["hl"] < 0])
    cell("division game: home favorite laying 1-3 ATS", [(g["season"], ats(g, "H")) for g in S if g["div"] and -3 <= g["hl"] <= -1])
    cell("division game: dog ATS", [(g["season"], ats(g, other(fav(g)))) for g in S if g["div"] and fav(g)])
    cell("not a division game: home ATS", [(g["season"], ats(g, "H")) for g in S if not g["div"]])
    print(" -- the moneyline (nflverse's closing moneyline)")
    cell("home ML", [(g["season"], ml(g, "H")) for g in S])
    cell("favorite ML -101..-150", [(g["season"], ml(g, fav(g))) for g in S if fav(g) and -150 <= ((g["hml"] if fav(g) == "H" else g["aml"]) or 0) <= -101])
    cell("home favorite ML -101..-150", [(g["season"], ml(g, "H")) for g in S if -150 <= (g["hml"] or 0) <= -101])
    cell("division home favorite ML -101..-150", [(g["season"], ml(g, "H")) for g in S if g["div"] and -150 <= (g["hml"] or 0) <= -101])
    cell("home favorite ML -151..-250", [(g["season"], ml(g, "H")) for g in S if -250 <= (g["hml"] or 0) <= -151])
    cell("dog ML +100..+350", [(g["season"], ml(g, other(fav(g)))) for g in S if fav(g) and 100 <= ((g["aml"] if fav(g) == "H" else g["hml"]) or 0) <= 350])
    cell("road dog ML +100..+199", [(g["season"], ml(g, "A")) for g in S if 100 <= (g["aml"] or 0) <= 199])
    cell("home dog ML +100..+350", [(g["season"], ml(g, "H")) for g in S if 100 <= (g["hml"] or 0) <= 350])
    print(" -- the total")
    cell("over", [(g["season"], tot(g, "over")) for g in S])
    cell("under", [(g["season"], tot(g, "under")) for g in S])
    cell("under, total 42 or less", [(g["season"], tot(g, "under")) for g in S if g["total"] and g["total"] <= 42])
    cell("under, total 42.5-46.5", [(g["season"], tot(g, "under")) for g in S if g["total"] and 42.5 <= g["total"] <= 46.5])
    cell("under, total 47+", [(g["season"], tot(g, "under")) for g in S if g["total"] and g["total"] >= 47])
    cell("division game: under", [(g["season"], tot(g, "under")) for g in S if g["div"]])
    cell("division game, total 42 or less: under", [(g["season"], tot(g, "under")) for g in S if g["div"] and g["total"] and g["total"] <= 42])
    cell("outdoors, November on: under", [(g["season"], tot(g, "under")) for g in S if g["roof"] in ("outdoors", "open") and g["date"][5:7] in ("11", "12", "01")])
    cell("wind 12+ mph (the game-day reading - not a bet): under", [(g["season"], tot(g, "under")) for g in S if (g["wind"] or 0) >= 12])
print("\n== THE WEEK AFTER A THURSDAY GAME (the mini-bye: 9+ days of rest against a team on a normal week)")
mb = [(g, s) for g in G for s in ("H", "A") if 9 <= ((g["hrest"] if s == "H" else g["arest"]) or 0) <= 11 and ((g["arest"] if s == "H" else g["hrest"]) or 0) in (6, 7, 8)]
cell("the rested side ATS", [(g["season"], ats(g, s)) for g, s in mb])
cell("the rested side ATS, at home", [(g["season"], ats(g, s)) for g, s in mb if s == "H"])
cell("the rested side ATS, on the road", [(g["season"], ats(g, s)) for g, s in mb if s == "A"])
cell("the rested side as a dog, ATS", [(g["season"], ats(g, s)) for g, s in mb if fav(g) and fav(g) != s])
cell("the rested side as a favorite, ATS", [(g["season"], ats(g, s)) for g, s in mb if fav(g) == s])
cell("the rested side ML, dog +100..+350", [(g["season"], ml(g, s)) for g, s in mb if 100 <= ((g["hml"] if s == "H" else g["aml"]) or 0) <= 350])
print("\n== SHORT WEEKS THAT AREN'T THURSDAY (a Monday-night team playing the next Sunday / Saturday: 5-6 days vs 7+)")
sw = [(g, s) for g in G for s in ("H", "A") if g["wd"] != "Thursday" and ((g["hrest"] if s == "H" else g["arest"]) or 9) <= 6 and ((g["arest"] if s == "H" else g["hrest"]) or 0) >= 7]
cell("the short side ATS", [(g["season"], ats(g, s)) for g, s in sw])
cell("the short side ATS, at home", [(g["season"], ats(g, s)) for g, s in sw if s == "H"])
cell("the short side ATS, as a favorite", [(g["season"], ats(g, s)) for g, s in sw if fav(g) == s])
cell("the short side ATS, as a dog", [(g["season"], ats(g, s)) for g, s in sw if fav(g) and fav(g) != s])
cell("those games: under", [(g["season"], tot(g, "under")) for g, s in sw])
print("\n== TONIGHT'S SHAPE (11/12: a division home favorite laying 1-3 on a short Thursday, total 41, cold and windy)")
ton = [g for g in short if g["div"] and -3 <= g["hl"] <= -1]
cell("home ATS", [(g["season"], ats(g, "H")) for g in ton])
cell("home ML", [(g["season"], ml(g, "H")) for g in ton])
cell("under", [(g["season"], tot(g, "under")) for g in ton])
ton2 = [g for g in short if g["total"] and g["total"] <= 42 and g["roof"] in ("outdoors", "open")]
cell("short Thursday outdoors, total 42 or less: under", [(g["season"], tot(g, "under")) for g in ton2])
cell("short Thursday outdoors, total 42 or less: home ATS", [(g["season"], ats(g, "H")) for g in ton2])
print(f"\ncells: {CELLS[0]} (about {CELLS[0] // 20} would clear |z| 2 by luck)")
