"""Study 3 (11/3): FOOTBALL IN NOVEMBER - THE TEMPERATURE SHOCK. The 10/15 / 10/10 weather studies graded ABSOLUTE
cold, wind and rain (sides dead; the dome team in the cold too few). New cut: the CHANGE - a team whose last game was
25F+ warmer than tonight's outdoor game (the game file's wx_temp, Open-Meteo's day reading - after the fact, the close
only had a forecast) vs an opponent that already played in the cold; and each team's FIRST game under 40F of the season.
Sides (ML dog / fav, ATS) and the UNDER. NFL + college (outdoor only), October-December. Closing prices; the paid
history's first fair number for the dogs. Train 2016-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
C = lib.Cells()
for lg in ("nfl", "ncaaf"):
    games = lib.sd.load_games(lg)
    fin = lib.finals(lg)
    allf = lib.all_finals(lg)
    tl = lib.team_log(allf)
    xby = {x["id"]: x for x in lib.load_football(lg)}

    def temp(gid):
        g = games.get(gid) or {}
        if str(g.get("indoor")) == "1":
            return 70.0                      # a dome: the body played at room temperature
        return lib.num(g.get("wx_temp"))

    for g in fin:
        raw = games.get(g["id"]) or {}
        if str(raw.get("indoor")) == "1" or int(g["start"][5:7]) not in (10, 11, 12):
            continue
        t_now = lib.num(raw.get("wx_temp"))
        if t_now is None:
            continue
        info = {}
        for side, team in (("home", g["home"]), ("away", g["away"])):
            prev = lib.before(tl, team, g["start"], 1)
            if not prev or prev[0]["season"] != g["season"]:
                info[side] = None
                continue
            t_prev = temp(prev[0]["id"])
            season_prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
            cold_before = any((temp(x["id"]) or 99) < 40 for x in season_prev)
            info[side] = {"drop": (t_prev - t_now) if t_prev is not None else None,
                          "first_cold": t_now < 40 and not cold_before}
        for side, team, opp, o, won, is_home in lib.sides(g):
            me, ot = info.get(side), info.get("away" if side == "home" else "home")
            if not me or not ot:
                continue
            d = lib.dec(o)
            p = lib.profit(won, d)
            a = lib.ats(g, side)
            shock = me["drop"] is not None and me["drop"] >= 25
            oshock = ot["drop"] is not None and ot["drop"] >= 25
            tags = []
            if shock and not oshock:
                tags.append("shock (25F+ colder than last game), opp not")
            if ot["drop"] is not None and oshock and not shock:
                tags.append("vs a shocked team")
            if me["first_cold"] and not ot["first_cold"]:
                tags.append("first sub-40F game of the season, opp had one")
            if ot["first_cold"] and not me["first_cold"]:
                tags.append("vs a team in its first sub-40F game")
            if shock and t_now < 40:
                tags.append("shock AND under 40F")
            for tg in tags:
                C.add(f"{lg} | {tg} | ATS", g["season"], a)
                if lib.dog_band(o):
                    C.add(f"{lg} | {tg} | dog ML +100..+350", g["season"], p)
                    e = lib.early_price(xby, g["id"], side)
                    if e:
                        C.add(f"{lg} | {tg} | dog ML | FIRST FAIR", g["season"], lib.profit(won, e[1]))
                if -200 <= o <= -101:
                    C.add(f"{lg} | {tg} | fav ML -101..-200", g["season"], p)
        # the total: either team shocked / the first cold game
        anyshock = any(x and x["drop"] is not None and x["drop"] >= 25 for x in info.values())
        anyfirst = any(x and x["first_cold"] for x in info.values())
        if anyshock:
            C.add(f"{lg} | UNDER | a team 25F+ colder than its last game", g["season"], lib.tot_profit(g, False))
        if anyfirst:
            C.add(f"{lg} | UNDER | a team's first sub-40F game", g["season"], lib.tot_profit(g, False))
        if t_now < 40:
            C.add(f"{lg} | UNDER | any game under 40F (base)", g["season"], lib.tot_profit(g, False))
C.dump("s3", "FOOTBALL: THE TEMPERATURE SHOCK (outdoor Oct-Dec; the team 25F+ colder than its last game / its first "
       "sub-40F game; close; train 2016-22, held 2023-26)", TRAIN, HELD)
