"""Study 5 (11/1): NHL - THE FAVORITE'S NEXT GAME (look-ahead / letdown). The NBA has a built -2 on a dog whose
favorite's next game (within 2 days) is a SOFT one (10/28: the favorite coasts... no - the market over-prices it); never
checked in hockey. For an NHL favorite: its NEXT scheduled game (from the schedule - known in advance) within 2 days is
SOFT (an opponent under .400 by wins, 10+ games in) or TOUGH (.600+), or a back-to-back next night at all. Bet the
favorite (-101..-150 / -151..-250) and the dog across (+100..+350) at the close. Second check: the same cut by Elo-free
points-per-game and the NBA's own definition re-run on NBA games (that weight is built - only to compare sizes).
Train 2018-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2022), (2023, 2024, 2025, 2026)
C = lib.Cells()
for lg in ("nhl", "nba"):
    sched = defaultdict(list)                   # team -> [(start, opp)] every regular-season game on the schedule
    for g in lib.sd.load_games(lg).values():
        if g.get("league") != lg or str(g.get("stype") or "2") != "2" or not g.get("start"):
            continue
        sched[g["home"]].append((g["start"], g["away"]))
        sched[g["away"]].append((g["start"], g["home"]))
    for t in sched:
        sched[t].sort()
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    tl = lib.team_log(allf)

    def wpct(team, start, s):
        b = [x for x in lib.before(tl, team, start) if x["season"] == s]
        if len(b) < 10:
            return None
        return sum(lib.won_g(x, team) for x in b) / len(b)

    def nxt(team, start):
        for st, op in sched[team]:
            if st > start:
                return st, op
        return None

    for g in lib.finals(lg):
        if g["stype"] != "2":
            continue
        s = g["season"]
        for side, team, opp, o, won, home in lib.sides(g):
            if o > -101 or o < -250:
                continue
            n = nxt(team, g["start"])
            if not n:
                continue
            gap = lib.days_between(g["start"], n[0])
            tags = []
            if gap <= 2.6:
                wp = wpct(n[1], g["start"], s)          # the next opponent's record as of TODAY (no look-ahead)
                if wp is not None:
                    tags.append("next game in 2 days is SOFT (opp < .400)" if wp < 0.4 else
                                "next game in 2 days is TOUGH (opp .600+)" if wp >= 0.6 else
                                "next game in 2 days is a middling team")
                if gap <= 1.4:
                    tags.append("plays again tomorrow (b2b next)")
            else:
                tags.append("next game 3+ days away")
            fband = "fav -101..-150" if o >= -150 else "fav -151..-250"
            dog_o = g["mla"] if home else g["mlh"]
            for t in ["all"] + tags:
                C.add(f"{lg} | {fband} | {t}", s, lib.profit(won, lib.dec(o)))
                if lib.dog_band(dog_o):
                    C.add(f"{lg} | dog across a {fband} | {t}", s, lib.profit(not won, lib.dec(dog_o)))

C.dump("s5", "THE FAVORITE'S NEXT GAME, NHL (+ the NBA's built cut for size), closing ML; train 2018-22, held 2023-26",
       TR, HE)
