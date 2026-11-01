"""Study 4 (11/1): COLLEGE FOOTBALL - A TEAM OFF A BYE vs A TEAM OFF A RIVALRY GAME (the owner's example list). The
rested team (12+ days since its last game, not its opener) meets a team whose LAST game was a rivalry game. Rivalry
(no rivalry field in the data): the two teams met in each of the 3 seasons before, every time within 8 days of the same
calendar date - the fixed annual games (trophy games, protected rivals), never a one-off. Built only from earlier
seasons' schedules (no look-ahead). Cells: the bye team / the hangover team at the close (dog +100..+350, favorite
-101..-150 / -151..-400), the FIRST FAIR early number (paid odds history) and ATS - each against the plain bye
team (opponent off a normal game) and the plain hangover team (no bye across). Train 2018-23, held 2024 / 2025 / 2026."""
import os, sys
from collections import defaultdict
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2023), (2024, 2025, 2026)
allf = [g for g in lib.all_finals("ncaaf") if g["stype"] == "2"]
tl = lib.team_log(allf)
pair_dates = defaultdict(list)              # frozenset(pair) -> [(season, day of year)]
for g in allf:
    d = date.fromisoformat(g["start"][:10])
    pair_dates[frozenset((g["home"], g["away"]))].append((g["season"], d.timetuple().tm_yday))


def rivalry(a, b, s, doy):
    ds = dict(pair_dates[frozenset((a, b))])
    for k in (s - 1, s - 2, s - 3):
        if k == 2020 and k not in ds:       # the covid season broke many series - skip it, look one further back
            continue
        if k not in ds or abs(ds[k] - doy) > 8:
            return False
    return True


xby = {x["id"]: x for x in lib.load_football("ncaaf")}
C = lib.Cells()
n_riv = 0
for g in lib.finals("ncaaf"):
    if g["stype"] != "2":
        continue
    s = g["season"]
    st = {}
    for t in (g["home"], g["away"]):
        last = lib.before(tl, t, g["start"], 1)
        if not last or last[0]["season"] != s:
            st[t] = None
            continue
        L = last[0]
        rest = lib.days_between(L["start"], g["start"])
        lo = L["away"] if L["home"] == t else L["home"]
        doy = date.fromisoformat(L["start"][:10]).timetuple().tm_yday
        st[t] = {"bye": rest >= 12, "riv": rivalry(t, lo, s, doy), "won": lib.won_g(L, t)}
    if st[g["home"]] is None or st[g["away"]] is None:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        me, op = st[team], st[opp]
        tags = []
        if me["bye"] and op["riv"] and not op["bye"]:
            tags.append("BYE team vs a team off a rivalry game")
            tags.append("BYE team vs a team off a rivalry " + ("WIN" if op["won"] else "LOSS"))
        elif me["bye"] and not op["bye"]:
            tags.append("bye team vs a team off a normal game")
        if me["riv"] and not me["bye"]:
            if op["bye"]:
                tags.append("HANGOVER team (off a rivalry game) vs a bye team")
            else:
                tags.append("hangover team (off a rivalry game), no bye across")
        if not tags:
            continue
        pr = lib.profit(won, lib.dec(o))
        e = lib.early_price(xby, g["id"], side)
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else \
            "fav -151..-400" if -400 <= o < -150 else None
        for t in tags:
            C.add(f"ML any -400..+350 | {t}", s, pr if -400 <= o <= 350 else None)
            if band:
                C.add(f"{band} | {t}", s, pr)
                if e and ((band[0] == "d" and 100 <= e[0] <= 350) or (band[0] == "f" and -400 <= e[0] <= -101)):
                    C.add(f"{band} | {t} | FIRST FAIR", s, lib.profit(won, e[1]))
            C.add(f"ATS | {t}", s, lib.ats(g, side))

C.dump("s4", "COLLEGE: OFF A BYE vs OFF A RIVALRY GAME (closing ML unless FIRST FAIR; train 2018-23, held 2024/25/26)",
       TR, HE)
