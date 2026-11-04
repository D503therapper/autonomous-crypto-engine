"""s2 - NFL DECEMBER: THE TEAM WITH NOTHING TO PLAY FOR vs THE TEAM IN THE RACE (+ the final regular-season week).
From Dec 1 (regular season), a team's record before tonight: DONE = .300 or worse after 10+ games (out of the race
in all but name), RACE = .500+, MID = between. Cells: the done team as a dog / favorite / ATS, by the opponent's
state; the race team across; the final week of the regular season (the last 4 nights of regular-season games each
season - the resting / clinched week) vs the other December weeks. Prices: the close + the paid first FAIR number.
Train 2016-21, held out 2022 / 2023 / 2024 / 2025."""
import lib

C = lib.Cells()
fin = lib.finals("nfl")
allf = [g for g in lib.all_finals("nfl") if g["stype"] == "2"]
tl = lib.team_log(allf)
xby = {g["id"]: g for g in lib.load_football("nfl")}
last_night = {}
for g in allf:
    last_night[g["season"]] = max(last_night.get(g["season"], ""), g["start"][:10])


def state(team, start, season):
    prev = [p for p in lib.before(tl, team, start) if p["season"] == season]
    if len(prev) < 10:
        return None
    w = sum(1 for p in prev if lib.won_g(p, team)) / len(prev)
    return "done" if w <= 0.3 else "race" if w >= 0.5 else "mid"


for g in fin:
    if g["stype"] != "2" or g["start"][5:7] not in ("12", "01"):
        continue
    s = g["season"]
    final_week = lib.days_between(g["start"][:10] + "T00:00Z", last_night[s] + "T00:00Z") <= 4
    wk = "FINAL WEEK" if final_week else "Dec-Jan other"
    for side, team, opp, o, won, home in lib.sides(g):
        st, so = state(team, g["start"], s), state(opp, g["start"], s)
        if not st or not so:
            continue
        a = lib.ats(g, side)
        ff = lib.early_price(xby, g["id"], side)
        p = lib.profit(won, lib.dec(o))
        for cut in (f"{st} vs {so}", f"{st} vs any", f"{wk} {st} vs {so}", f"{wk} any"):
            C.add(f"{cut} ATS", s, a)
            C.add(f"{cut} side ML any", s, p)
            if lib.dog_band(o):
                C.add(f"{cut} dog +100..+350", s, p)
                if ff:
                    C.add(f"{cut} dog +100..+350 FIRST FAIR", s, lib.profit(won, ff[1]))
            if lib.fav_band(o):
                C.add(f"{cut} fav -101..-150", s, p)
            if -300 <= o <= -151:
                C.add(f"{cut} fav -151..-300", s, p)
        if home:
            C.add(f"{wk} home side ATS", s, a)
            if lib.dog_band(o):
                C.add(f"{wk} home dog +100..+350", s, p)

C.dump("s2", "s2 NFL DECEMBER: done (.300-) / race (.500+) / mid teams, 10+ games in; FINAL WEEK = the last 4 nights of the regular season - "
       "train 2016-21, held 2022 / 2023 / 2024 / 2025", (2016, 2021), [2022, 2023, 2024, 2025])
