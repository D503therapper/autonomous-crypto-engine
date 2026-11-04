"""s4 - THE RIVALRY GAME ITSELF, COLLEGE FOOTBALL (the game AFTER a rivalry game died 11/1; Thanksgiving-weekend
home sides 10/31). A rivalry = the two teams met in each of the 3 seasons before, within 10 days of the same calendar
date; the game sits in the last 16 days of the regular season (Nov 15 - Dec 1), FBS vs FBS, regular season. Cells:
the rivalry dog +100..+350 / the favorite / ATS by spread size (the big favorite laying 14+ - 'throw out the
records'), the home dog, the dog with the much worse record (3+ wins fewer), vs every other late-November game.
Prices: the close + the paid first FAIR number. Train 2018-22, held 2023 / 2024 / 2025."""
import lib
import sports_data as sd
import sports_players as sp
from datetime import datetime

C = lib.Cells()
fin = lib.finals("ncaaf")
allf = [g for g in lib.all_finals("ncaaf") if g["stype"] == "2"]
games = sd.load_games("ncaaf")
tl = lib.team_log(allf)
met = {}
for g in allf:
    met.setdefault((g["season"], frozenset((g["home"], g["away"]))), []).append(g["start"][:10])


def doy(d):
    return datetime.strptime(d, "%Y-%m-%d").timetuple().tm_yday


def rivalry(g):
    pr = frozenset((g["home"], g["away"]))
    d0 = doy(g["start"][:10])
    for s in (g["season"] - 1, g["season"] - 2, g["season"] - 3):
        ds = met.get((s, pr))
        if not ds or not any(abs(doy(d) - d0) <= 10 for d in ds):
            return False
    return True


fbs_cache = {}
for g in fin:
    if g["stype"] != "2" or g["season"] < 2018 or not ("11-15" <= g["start"][5:10] <= "12-01"):
        continue
    s = g["season"]
    key = g["start"][:7]
    if key not in fbs_cache:
        fbs_cache[key] = sp.fbs_set(games, g["start"]) or set()
    fbs = fbs_cache[key]
    if g["home"] not in fbs or g["away"] not in fbs:
        continue
    riv = rivalry(g)
    tag = "RIVALRY" if riv else "other late-Nov"
    recs = {}
    for t in (g["home"], g["away"]):
        prev = [p for p in lib.before(tl, t, g["start"]) if p["season"] == s]
        recs[t] = sum(1 for p in prev if lib.won_g(p, t))
    sp_h = g["sp"]
    for side, team, opp, o, won, home in lib.sides(g):
        a = lib.ats(g, side)
        p = lib.profit(won, lib.dec(o))
        lay = None
        if sp_h is not None:
            my_sp = sp_h if side == "home" else -sp_h
            lay = "lay 14+" if my_sp <= -14 else "lay 7-13.5" if my_sp <= -7 else "lay 0.5-6.5" if my_sp < 0 else "getting pts"
        C.add(f"{tag} ATS any", s, a)
        if lay:
            C.add(f"{tag} ATS {lay}", s, a)
        if lib.dog_band(o):
            C.add(f"{tag} dog +100..+350", s, p)
            C.add(f"{tag} dog +100..+350 {'home' if home else 'road'}", s, p)
            if recs[team] <= recs[opp] - 3:
                C.add(f"{tag} dog +100..+350, 3+ wins fewer", s, p)
            if home and not g["neutral"]:
                C.add(f"{tag} home dog ATS", s, a)
        if lib.fav_band(o):
            C.add(f"{tag} fav -101..-150", s, p)
        if -300 <= o <= -151:
            C.add(f"{tag} fav -151..-300", s, p)
        if riv and home and not g["neutral"]:
            C.add("RIVALRY home side ATS", s, a)
    if riv:
        C.add("RIVALRY over", s, lib.tot_profit(g, True))
        C.add("RIVALRY under", s, lib.tot_profit(g, False))
    else:
        C.add("other late-Nov under", s, lib.tot_profit(g, False))

C.dump("s4", "s4 COLLEGE FOOTBALL RIVALRY GAMES (met each of the 3 seasons before within 10 days of the date; Nov 15 - Dec 1, FBS vs FBS) - "
       "train 2018-22, held 2023 / 2024 / 2025", (2018, 2022), [2023, 2024, 2025])
