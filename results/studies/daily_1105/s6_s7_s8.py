"""S6 / S7 / S8 - three untested angles (game files at the close, the open 2023-26 where on file; box rows from
data/sports/players/<lg>.csv).
  S6 PLAYOFF PAYBACK (NBA / NHL / NFL): the first regular-season meeting the season AFTER a playoff elimination -
     the ELIMINATED team's side (ML dog / fav, ATS where a spread exists). Elimination = the last playoff game between
     the two that postseason (the series' last game / the one NFL game) - its loser.
  S7 THE GOALIE vs HIS OLD TEAM (NHL): tonight's starter started 20+ games for tonight's OPPONENT in earlier seasons
     (box rows - one goalie row a team-game) - his side ML.
  S8 COLLEGE QB MONSTER GAME: the team's QB threw for 400+ yards or 5+ TDs in its LAST game (box rows) - the side
     tonight ATS / ML at the close and the paid history's first fair number, and the side across it.
Train = the old seasons, held out = 2023 / 2024 / 2025 / 2026 apart."""
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

# ---------------- S6
C6 = lib.Cells()
for lg in ("nba", "nhl", "nfl"):
    fin_all = lib.finals(lg)
    elim = {}                                                # (season, loser, winner) from the last playoff game
    last_po = {}
    for g in fin_all:
        if g["stype"] != "3":
            continue
        key = (g["season"], frozenset((g["home"], g["away"])))
        last_po[key] = g
    for (s, pair), g in last_po.items():
        hw = g["hs"] > g["as"]
        loser, winner = (g["away"], g["home"]) if hw else (g["home"], g["away"])
        elim[(s + 1, loser, winner)] = True
    seen = set()
    for g in fin_all:
        if g["stype"] != "2":
            continue
        for side, team, opp, o, won, home in lib.sides(g):
            if (g["season"], team, opp) in elim and (g["season"], team, opp) not in seen:
                seen.add((g["season"], team, opp))
                s = g["season"]
                band = "dog" if lib.dog_band(o) else "fav" if lib.fav_band(o, -300, -101) else None
                if band:
                    C6.add(f"S6 {lg} eliminated team, 1st meeting next season | ML {band}", s, lib.profit(won, lib.dec(o)))
                    C6.add(f"S6 ALL eliminated team, 1st meeting next season | ML {band}", s, lib.profit(won, lib.dec(o)))
                C6.add(f"S6 {lg} eliminated team | ATS", s, lib.ats(g, side))
                C6.add(f"S6 ALL eliminated team | ATS", s, lib.ats(g, side))
                C6.add(f"S6 ALL eliminated team | ML any", s, lib.profit(won, lib.dec(o)))
C6.dump("s6", "S6 PLAYOFF PAYBACK (train to 2022, held 2023-26)", (2016, 2022), [2023, 2024, 2025, 2026])

# ---------------- S7
rows = list(csv.DictReader(open("data/sports/players/nhl.csv")))
act = {(r["gid"], r["team"]): r["player"] for r in rows}
start_of = {r["gid"]: r["start"] for r in rows}
hist = {}                                                    # goalie -> Counter((season, team) starts)
order = sorted(rows, key=lambda r: r["start"])
C7 = lib.Cells()
fin = {g["id"]: g for g in lib.finals("nhl") if g["stype"] == "2"}
done = set()
for r in order:
    gid = r["gid"]
    if gid in fin and gid not in done:
        done.add(gid)
        g = fin[gid]
        for side, team, opp, o, won, home in lib.sides(g):
            me = act.get((gid, team))
            if not me:
                continue
            h = hist.get(me, Counter())
            old = sum(n for (s, t), n in h.items() if t == opp and s < g["season"])
            now_with_opp = h.get((g["season"], opp), 0)
            if old >= 20 and now_with_opp == 0:
                s = g["season"]
                for tag, price in (("close", o), ("open", g["oh"] if side == "home" else g["oa"])):
                    if not price:
                        continue
                    band = "dog" if lib.dog_band(price) else "fav" if lib.fav_band(price, -250, -101) else None
                    if band:
                        C7.add(f"S7 goalie vs his old team (20+ starts there) | {tag} ML {band}", s,
                               lib.profit(won, lib.dec(price)))
                    C7.add(f"S7 goalie vs his old team | {tag} ML any", s, lib.profit(won, lib.dec(price)))
    for gid2 in ():
        pass
    hist.setdefault(r["player"], Counter())[(lib.season(r["start"]), r["team"])] += 1
C7.dump("s7", "S7 THE GOALIE vs HIS OLD TEAM (NHL; train 2016-22, held 2023-26)", (2016, 2022), [2023, 2024, 2025, 2026])

# ---------------- S8
qb = {}
for r in csv.DictReader(open("data/sports/players/ncaaf.csv")):
    qb[(r["gid"], r["team"])] = (float(r["yds"] or 0), float(r["td"] or 0))
allf = lib.all_finals("ncaaf")
tl = lib.team_log(allf)
xby = {x["id"]: x for x in lib.load_football("ncaaf")}
C8 = lib.Cells()
for g in lib.finals("ncaaf"):
    if g["stype"] != "2" or g["season"] < 2017:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"], 1) if x["season"] == g["season"]]
        oprev = [x for x in lib.before(tl, opp, g["start"], 1) if x["season"] == g["season"]]
        if not prev:
            continue
        y, td = qb.get((prev[-1]["id"], team), (None, None))
        if y is None:
            continue
        tags = []
        if y >= 400 or td >= 5:
            tags.append("S8 QB 400+ yds or 5+ TD last game")
        elif y >= 300 or td >= 4:
            tags.append("S8 QB 300-399 / 4 TD last game")
        else:
            tags.append("S8 control (under 300, under 4 TD)")
        if oprev:
            oy, otd = qb.get((oprev[-1]["id"], opp), (None, None))
            if oy is not None and (oy >= 400 or otd >= 5) and not (y >= 400 or td >= 5):
                tags.append("S8 FACING a team whose QB went 400+ / 5+ TD")
        for t in tags:
            s = g["season"]
            band = "dog" if lib.dog_band(o) else "fav" if lib.fav_band(o, -300, -101) else None
            if band:
                C8.add(f"{t} | close ML {band}", s, lib.profit(won, lib.dec(o)))
            C8.add(f"{t} | close ATS", s, lib.ats(g, side))
            ep = lib.early_price(xby, g["id"], side)
            if ep:
                b2 = "dog" if lib.dog_band(ep[0]) else "fav" if lib.fav_band(ep[0], -300, -101) else None
                if b2:
                    C8.add(f"{t} | first-fair ML {b2}", s, lib.profit(won, ep[1]))
C8.dump("s8", "S8 COLLEGE QB MONSTER GAME (train 2017-22, held 2023-26)", (2017, 2022), [2023, 2024, 2025, 2026])
