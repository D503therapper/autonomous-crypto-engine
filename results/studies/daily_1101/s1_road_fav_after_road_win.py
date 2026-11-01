"""Study 1 (11/1): THE ROAD FAVORITE AFTER A ROAD WIN (the owner's example list). A favorite on the road whose LAST game
(same season, regular season) was also a road WIN - the "they just won there, they'll win here" price. NFL first, then
the same cut in college football, the NBA and the NHL as second checks. Compared against every road favorite in the
same band, and split by how the last game went (road win / road loss / home win / home loss). The dog across from it
too (the home dog). Closing moneyline; NFL / college also at the FIRST FAIR early number (paid odds history, median
book) and ATS. Train = the old seasons, each newer season held out apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

SPLIT = {"nfl": ((2018, 2023), (2024, 2025, 2026)), "ncaaf": ((2018, 2023), (2024, 2025, 2026)),
         "nba": ((2018, 2022), (2023, 2024, 2025, 2026)), "nhl": ((2018, 2022), (2023, 2024, 2025, 2026))}
C = lib.Cells()
for lg, (TR, HE) in SPLIT.items():
    fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
    tl = lib.team_log([g for g in lib.all_finals(lg) if g["stype"] == "2"])
    xby = {x["id"]: x for x in lib.load_football(lg)} if lg in ("nfl", "ncaaf") else {}
    for g in fin:
        if g["neutral"]:
            continue
        s = g["season"]
        for side, team, opp, o, won, home in lib.sides(g):
            if home or o > -101:
                continue                          # road favorites only
            band = "-101..-150" if o >= -150 else "-151..-300" if o >= -300 else None
            if not band:
                continue
            last = lib.before(tl, team, g["start"], 1)
            if not last or last[0]["season"] != s:
                continue
            L = last[0]
            how = ("road" if L["away"] == team else "home") + (" win" if lib.won_g(L, team) else " loss")
            pr = lib.profit(won, lib.dec(o))
            oside = "home"
            dog_o = g["mlh"]
            dpr = lib.profit(not won, lib.dec(dog_o))
            for tag in ("every road fav", "last game: " + how):
                C.add(f"{lg} | road fav {band} | {tag}", s, pr)
                C.add(f"{lg} | home dog across ({band} fav) | {tag}", s, dpr)
                a = lib.ats(g, side)
                C.add(f"{lg} | ATS road fav {band} | {tag}", s, a)
                if xby:
                    e = lib.early_price(xby, g["id"], side)
                    if e and e[0] < -100:
                        C.add(f"{lg} | road fav {band} | {tag} | FIRST FAIR", s, lib.profit(won, e[1]))
            if how == "road win" and lg in ("nfl", "ncaaf", "nba", "nhl"):
                # dose: won the last road game by 14+ (football) / 10+ (NBA) / 2+ (NHL)
                big = {"nfl": 14, "ncaaf": 14, "nba": 10, "nhl": 2}[lg]
                tag2 = "road win by %d+" % big if lib.margin_g(L, team) >= big else "road win by less"
                C.add(f"{lg} | road fav {band} | last game: {tag2}", s, pr)
                # two straight road wins
                l2 = lib.before(tl, team, g["start"], 2)
                if len(l2) == 2 and l2[0]["season"] == s and l2[0]["away"] == team and lib.won_g(l2[0], team):
                    C.add(f"{lg} | road fav {band} | last 2: both road wins", s, pr)

C.dump("s1", "ROAD FAVORITE AFTER A ROAD WIN (closing ML unless FIRST FAIR / ATS; NFL/college train 2018-23, "
       "NBA/NHL train 2018-22; HELD = each later season)", lambda k: SPLIT[k.split(" |")[0]])
