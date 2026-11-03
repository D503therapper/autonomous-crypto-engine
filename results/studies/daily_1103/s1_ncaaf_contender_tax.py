"""Study 1 (11/3): COLLEGE FOOTBALL - THE CONTENDER TAX IN NOVEMBER. The playoff race is the November story: do the
books (and the public) lean on the top teams too hard late? A plain walk-forward Elo (margin-aware, a third regressed
each season, FBS games only) names the top 12 / top 25 BEFORE each game. Cells: the top-12 / 13-25 team as a favorite
in November (ATS, the moneyline -101..-300), the dog across it (+100..+350), by spread size, by home / road, and the same
in Sept-Oct as the comparison. Closing prices 2016-26 + the paid history's FIRST FAIR number (2020+).
Train 2016-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
fin = lib.finals("ncaaf")
allf = lib.all_finals("ncaaf")
fbs = set()
for g in fin:
    fbs.add(g["home"]); fbs.add(g["away"])
# FBS only for the ratings: a team with 6+ priced games in a season
cnt = {}
for g in fin:
    for t in (g["home"], g["away"]):
        cnt[(g["season"], t)] = cnt.get((g["season"], t), 0) + 1
rated = [g for g in allf if cnt.get((g["season"], g["home"]), 0) >= 6 and cnt.get((g["season"], g["away"]), 0) >= 6]
elo = lib.elo_walk(rated, k=25, hfa=60)
xby = {x["id"]: x for x in lib.load_football("ncaaf")}

daily = elo.pop("_daily")      # (season, date) -> every rated team's rating at the start of that day, high to low


def rank_of(rating, season, date):
    """1 + the number of rated teams above this rating on that day (the day's standings, post-game ratings)."""
    lst = daily.get((season, date))
    if not lst:
        return 999
    return 1 + sum(1 for v in lst if v > rating)


C = lib.Cells()
for g in fin:
    if g["id"] not in elo or g["season"] < 2016:
        continue
    rh, ra = elo[g["id"]]
    ranks = {g["home"]: rank_of(rh, g["season"], g["start"][:10]), g["away"]: rank_of(ra, g["season"], g["start"][:10])}
    if int(g["start"][5:7]) in (8, 9) and sum(1 for x in daily.get((g["season"], g["start"][:10]), [])) < 100:
        continue                                             # the first days of a season: no standings yet
    month = int(g["start"][5:7])
    when = "NOV" if month == 11 else "SEP-OCT" if month in (9, 10) else None
    if not when:
        continue
    for side, team, opp, o, won, is_home in lib.sides(g):
        rk, ork = ranks.get(team, 999), ranks.get(opp, 999)
        tier = "top12" if rk <= 12 else "13-25" if rk <= 25 else None
        otier = "top12" if ork <= 12 else "13-25" if ork <= 25 else None
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        if tier and o < 0:
            C.add(f"{when} | fav | {tier} | ATS", g["season"], a)
            if -300 <= o <= -101:
                C.add(f"{when} | fav | {tier} | ML -101..-300", g["season"], p)
            if -150 <= o <= -101:
                C.add(f"{when} | fav | {tier} | ML -101..-150", g["season"], p)
            C.add(f"{when} | fav | {tier} | {'home' if is_home else 'road'} | ATS", g["season"], a)
            if g["sp"] is not None:
                lay = -g["sp"] if is_home else g["sp"]
                band = "lay 1-7" if lay < 7.5 else "lay 7.5-14" if lay < 14.5 else "lay 14.5+"
                C.add(f"{when} | fav | {tier} | {band} | ATS", g["season"], a)
            if otier:
                C.add(f"{when} | fav | {tier} vs ranked | ATS", g["season"], a)
        if otier and o >= 100 and lib.dog_band(o):
            C.add(f"{when} | dog vs {otier} | ML +100..+350", g["season"], p)
            C.add(f"{when} | dog vs {otier} | ATS", g["season"], a)
            e = lib.early_price(xby, g["id"], side)
            if e:
                C.add(f"{when} | dog vs {otier} | ML +100..+350 | FIRST FAIR", g["season"], lib.profit(won, e[1]))
        if tier is None and otier is None and o < 0:
            C.add(f"{when} | fav | unranked vs unranked | ATS", g["season"], a)
            if -300 <= o <= -101:
                C.add(f"{when} | fav | unranked vs unranked | ML -101..-300", g["season"], p)
C.dump("s1", "COLLEGE FOOTBALL: THE CONTENDER (Elo top 12 / 13-25) AS A FAVORITE IN NOVEMBER vs SEPT-OCT (close; "
       "train 2016-22, held 2023-26)", TRAIN, HELD)
