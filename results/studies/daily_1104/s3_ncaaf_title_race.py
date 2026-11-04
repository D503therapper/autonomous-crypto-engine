"""s3 - THE CONFERENCE TITLE RACE, COLLEGE FOOTBALL IN NOVEMBER. Conferences inferred from the schedule
(lib.football_conferences - FBS pairs that met this season and in one of the two before, label propagation), the
conference standings before each game (conference losses). From Nov 1: ALIVE = conference losses within 1 of the
conference's best, OUT = 3+ more than the best, MID = between. Cells: the alive team as a dog / favorite / ATS by the
opponent's state, the out team the same, the title showdown (both alive), conference games only, FBS vs FBS.
Prices: the close + the paid first FAIR number. Train 2018-22, held out 2023 / 2024 / 2025 (2026 is in November now)."""
import lib
import sports_data as sd
import sports_players as sp

C = lib.Cells()
fin = lib.finals("ncaaf")
allf = [g for g in lib.all_finals("ncaaf") if g["stype"] == "2"]
xby = {g["id"]: g for g in lib.load_football("ncaaf")}
games = sd.load_games("ncaaf")
conf_by, stand = {}, {}
sizes = {}
for s in range(2018, 2027):
    fbs = sp.fbs_set(games, f"{s}-10-01") or set()
    conf_by[s] = lib.football_conferences(allf, s, fbs)
    sizes[s] = len(set(conf_by[s].values()))
print("conferences found by season:", sizes)

# walk the season: conference records before each game
rec = {}
by_id = {}
for g in sorted(allf, key=lambda x: x["start"]):
    s = g["season"]
    cf = conf_by.get(s, {})
    ch, ca = cf.get(g["home"]), cf.get(g["away"])
    by_id[g["id"]] = (dict(rec.get((s, g["home"]), {"w": 0, "l": 0})), dict(rec.get((s, g["away"]), {"w": 0, "l": 0})),
                      ch is not None and ch == ca)
    if ch is not None and ch == ca:
        hw = g["hs"] > g["as"]
        for t, w in ((g["home"], hw), (g["away"], not hw)):
            r = rec.setdefault((s, t), {"w": 0, "l": 0})
            r["w" if w else "l"] += 1
# the conference's best loss count before each date: computed from rec snapshots per day
best_by_day = {}
rec2 = {}
day = None
for g in sorted(allf, key=lambda x: x["start"]):
    s = g["season"]
    cf = conf_by.get(s, {})
    d = g["start"][:10]
    if d != day:
        day = d
        best = {}
        for (ss, t), r in rec2.items():
            if ss == s and t in cf:
                k = cf[t]
                best[k] = min(best.get(k, 99), r["l"])
        best_by_day[(s, d)] = best
    ch, ca = cf.get(g["home"]), cf.get(g["away"])
    if ch is not None and ch == ca:
        hw = g["hs"] > g["as"]
        for t, w in ((g["home"], hw), (g["away"], not hw)):
            r = rec2.setdefault((s, t), {"w": 0, "l": 0})
            r["w" if w else "l"] += 1


def state(s, d, team, r):
    cf = conf_by.get(s, {})
    if team not in cf:
        return None
    b = best_by_day.get((s, d), {}).get(cf[team])
    if b is None or (r["w"] + r["l"]) < 4:
        return None
    gap = r["l"] - b
    return "alive" if gap <= 1 else "out" if gap >= 3 else "mid"


for g in fin:
    if g["stype"] != "2" or g["start"][5:7] not in ("11", "12") or g["start"][5:10] > "12-02":
        continue
    s = g["season"]
    if s < 2018:
        continue
    rh, ra, same = by_id.get(g["id"], (None, None, False))
    if not same:
        continue
    d = g["start"][:10]
    for side, team, opp, o, won, home in lib.sides(g):
        st = state(s, d, team, rh if side == "home" else ra)
        so = state(s, d, opp, ra if side == "home" else rh)
        if not st or not so:
            continue
        a = lib.ats(g, side)
        ff = lib.early_price(xby, g["id"], side)
        p = lib.profit(won, lib.dec(o))
        for cut in (f"{st} vs {so}", f"{st} vs any"):
            C.add(f"{cut} ATS", s, a)
            C.add(f"{cut} side ML any", s, p)
            if lib.dog_band(o):
                C.add(f"{cut} dog +100..+350", s, p)
                if ff:
                    C.add(f"{cut} dog +100..+350 FIRST FAIR", s, lib.profit(won, ff[1]))
            if lib.fav_band(o):
                C.add(f"{cut} fav -101..-150", s, p)
                if ff:
                    C.add(f"{cut} fav -101..-150 FIRST FAIR", s, lib.profit(won, ff[1]))
            if -300 <= o <= -151:
                C.add(f"{cut} fav -151..-300", s, p)
        if home and st == "alive":
            C.add("alive HOME side ATS", s, a)
    C.add("base conf game ATS (home)", s, lib.ats(g, "home"))

C.dump("s3", "s3 COLLEGE FOOTBALL CONFERENCE TITLE RACE, Nov 1 - Dec 2 conference games (alive = conf losses within 1 of the best; out = 3+ more) - "
       "train 2018-22, held 2023 / 2024 / 2025 / 2026", (2018, 2022), [2023, 2024, 2025, 2026])
