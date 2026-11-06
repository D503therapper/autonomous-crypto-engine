"""S5 - COLLEGE HOOPS: THE FIRST TRUE ROAD GAME after a home-only start (2+ home games, no road / neutral game yet this
season), split game 3 (inside the built early road dog's games 1-3) vs game 4+ (outside it - the new part).
S6 - COLLEGE HOOPS: THE FIRST GAME vs A D1 TEAM after non-D1 openers only (1+ games vs non-D1 schools, no D1 game yet) -
the market has nothing but last season and the tune-ups (the 11/4 South Dakota audit's question, at the game after).
Nov-Dec regular season 2018-26 at the CLOSE (game files) and ESPN's OPEN (2023-26); dogs +100..+350, favorites -101..-150,
ATS at the closing spread. Controls: the same game numbers, a team that already played on the road / already met a D1
team. Train 2018-22, held out 2023 / 2024 / 2025 / 2026 apart. Only the schedule (known before tip)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_data as sd  # noqa: E402

allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
tl = lib.team_log(allf)
d1 = sm.ncaab_d1(sm.finals(sd.load_games("ncaab"), "ncaab"))
fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2018 and g["start"][5:7] in ("11", "12")]
C = lib.Cells()
for g in fin:
    for side, team, opp, o_close, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
        n = len(prev)
        s = g["season"]
        o_open = g["oh"] if side == "home" else g["oa"]
        a = lib.ats(g, side)
        cells = []
        # S5
        road = not g["neutral"] and not home
        if road and n >= 2:
            home_only = all((x["home"] == team and not x["neutral"]) for x in prev)
            been_away = any(x["home"] != team or x["neutral"] for x in prev)
            gn = "game 3" if n == 2 else "games 4-6" if n <= 5 else "game 7+"
            if home_only:
                cells.append(f"S5 FIRST road game after {n if n < 4 else '4+'} home ({gn})")
                cells.append(f"S5 FIRST road game, home-only start ({gn})")
                cells.append("S5 FIRST road game, home-only start (game 4+)" if n >= 3 else None)
            elif been_away:
                cells.append(f"S5 control: road, already away ({gn})")
                cells.append("S5 control: road, already away (game 4+)" if n >= 3 else None)
        # S6
        if team in d1 and opp in d1 and n >= 1:
            nd = sum(1 for x in prev if (x["away"] if x["home"] == team else x["home"]) not in d1)
            dd = n - nd
            if nd >= 1 and dd == 0:
                cells.append(f"S6 FIRST D1 game after {nd if nd < 3 else '3+'} non-D1 only")
                cells.append("S6 FIRST D1 game after non-D1 only")
                cells.append(f"S6 FIRST D1 game after non-D1 only ({'home' if home and not g['neutral'] else 'road' if not g['neutral'] else 'neutral'})")
            elif n <= 3 and dd >= 1:
                cells.append("S6 control: games 2-4, already met a D1 team")
            # the OPPONENT of such a team
            oprev = [x for x in lib.before(tl, opp, g["start"]) if x["season"] == g["season"]]
            ond = sum(1 for x in oprev if (x["away"] if x["home"] == opp else x["home"]) not in d1)
            if oprev and ond >= 1 and ond == len(oprev):
                cells.append("S6 FACING a team in its first D1 game (non-D1 only before)")
        for c in cells:
            if not c:
                continue
            if lib.dog_band(o_close):
                C.add(f"{c} | close dog", s, lib.profit(won, lib.dec(o_close)))
            if lib.fav_band(o_close):
                C.add(f"{c} | close fav", s, lib.profit(won, lib.dec(o_close)))
            if o_open and s >= 2023 and lib.dog_band(o_open):
                C.add(f"{c} | OPEN dog", s, lib.profit(won, lib.dec(o_open)))
            if a is not None:
                C.add(f"{c} | ATS", s, a)
C.dump("s5_s6", "S5 / S6 COLLEGE HOOPS: the first road game after a home-only start; the first D1 game after non-D1 openers",
       (2018, 2022), [2023, 2024, 2025, 2026])
