"""S2 / S10 - COLLEGE HOOPS, the first weeks (game files at the close; the ESPN open 2023-26 as the second price).
  S2 THE EARLY OVERREACTION: a team in its games 2-6 of the season whose LAST game missed or beat its closing spread
     by 15+ points (cover margin = margin + its spread) - does the market overreact to one early game? Also the team
     that LOST last time as a 10+ point favorite, and the team that WON last time as a 10+ point dog.
  S10 HOME FROM A NEUTRAL-SITE EVENT: Nov-Dec, the team's last 1+ games were at neutral sites (multi-team events) and
     tonight it is at home (not neutral) / on the road - the first game back. (The 11/3 MTE study read the games
     INSIDE the event; this is the game after.)
Train 2018-22 seasons, held out 2023 / 2024 / 2025 apart (2026 = this week, too few)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

fin = [g for g in lib.finals("ncaab") if g["stype"] == "2"]
byid = {g["id"]: g for g in fin}
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
tl = lib.team_log(allf)
C = lib.Cells()


def cover(g, team):
    """team's cover margin at the close (margin + its spread), or None."""
    if g is None or g.get("sp") is None:
        return None
    m = lib.margin_g(g, team)
    return m + (g["sp"] if g["home"] == team else -g["sp"])


def spread_of(g, team):
    return g["sp"] if g["home"] == team else -g["sp"]


for g in fin:
    if g["season"] < 2018:
        continue
    mo = int(g["start"][5:7])
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
        tags = []
        if 1 <= len(prev) <= 5 and mo in (11, 12):
            pg = byid.get(prev[-1]["id"])
            cm = cover(pg, team)
            if cm is not None:
                if cm <= -15:
                    tags.append("S2 games 2-6, last game MISSED the spread by 15+")
                elif cm >= 15:
                    tags.append("S2 games 2-6, last game BEAT the spread by 15+")
                else:
                    tags.append("S2 games 2-6, last game within 15 (control)")
                sp = spread_of(pg, team)
                if sp <= -10 and not lib.won_g(pg, team):
                    tags.append("S2 games 2-6, LOST last as a 10+ fav")
                if sp >= 10 and lib.won_g(pg, team):
                    tags.append("S2 games 2-6, WON last as a 10+ dog")
        if prev and mo in (11, 12) and not g["neutral"]:
            if prev[-1]["neutral"] and lib.days_between(prev[-1]["start"], g["start"]) <= 10:
                n_neu = 0
                for x in reversed(prev):
                    if not x["neutral"]:
                        break
                    n_neu += 1
                where = "HOME" if home else "ROAD"
                tags.append(f"S10 first game back from a neutral site, {where}")
                if n_neu >= 2:
                    tags.append(f"S10 first game back after 2+ neutral games, {where}")
            elif not prev[-1]["neutral"]:
                tags.append(f"S10 control (last game not neutral), {'HOME' if home else 'ROAD'}")
        for t in tags:
            s = g["season"]
            for tag, price in (("close", o), ("open", g["oh"] if side == "home" else g["oa"])):
                if not price:
                    continue
                band = "dog" if lib.dog_band(price) else "fav" if lib.fav_band(price) else None
                if band:
                    C.add(f"{t} | {tag} ML {band}", s, lib.profit(won, lib.dec(price)))
            C.add(f"{t} | close ATS", s, lib.ats(g, side))
C.dump("s2s10", "COLLEGE HOOPS - early overreaction (S2) and home from a neutral event (S10)", (2018, 2022), [2023, 2024, 2025])
