"""Study 3 (11/1): THE SOFT-SCHEDULE STREAK, NFL + college football. A team on a 3+ game win streak whose last 3
opponents were all BAD (under .400 in their games before they met, 3+ games in; in college an FCS opponent counts as
bad) now facing a WINNING team (.500+). Does the market buy the streak more than the schedule earned? And the mirror:
a team that LOST its last 3, all to WINNING teams (a brutal stretch), now facing a team that is not .500+ - is the
losing streak over-sold? Records come only from games finished before each game (no look-ahead). Every cell next to
the same team-state with a normal schedule (3 straight wins / losses NOT all vs bad / good teams). Closing moneyline,
the FIRST FAIR early number (paid odds history, median book) and ATS. Train 2018-23, held out 2024 / 2025 / 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import sports_players as spl  # noqa: E402

TR, HE = (2018, 2023), (2024, 2025, 2026)
C = lib.Cells()
for lg in ("nfl", "ncaaf"):
    games = lib.sd.load_games(lg)
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    tl = lib.team_log(allf)
    xby = {x["id"]: x for x in lib.load_football(lg)}
    fbs_cache = {}

    def fbs(start):
        k = start[:7]
        if k not in fbs_cache:
            fbs_cache[k] = spl.fbs_set(games, start) if lg == "ncaaf" else None
        return fbs_cache[k]

    def rec(team, start, s):
        b = [x for x in lib.before(tl, team, start) if x["season"] == s]
        if len(b) < 3:
            return None
        return sum(lib.won_g(x, team) for x in b) / len(b)

    def bad(opp, start, s):
        if lg == "ncaaf":
            f = fbs(start)
            if f is not None and opp not in f:
                return True
        r = rec(opp, start, s)
        return r is not None and r < 0.4

    def good(opp, start, s):
        r = rec(opp, start, s)
        return r is not None and r >= 0.5

    for g in lib.finals(lg):
        if g["stype"] != "2":
            continue
        s = g["season"]
        for side, team, opp, o, won, home in lib.sides(g):
            l3 = [x for x in lib.before(tl, team, g["start"], 3) if x["season"] == s]
            if len(l3) < 3:
                continue
            res = [lib.won_g(x, team) for x in l3]
            opps = [(x["away"] if x["home"] == team else x["home"], x["start"]) for x in l3]
            tags = []
            if all(res) and good(opp, g["start"], s):
                soft = all(bad(op, st, s) for op, st in opps)
                tags.append("won 3 straight vs bad teams, now vs a winning team" if soft
                            else "won 3 straight (normal schedule), now vs a winning team")
            if not any(res):
                r_opp = rec(opp, g["start"], s)
                if r_opp is not None and r_opp < 0.5:
                    hard = all(good(op, st, s) for op, st in opps)
                    tags.append("lost 3 straight to winning teams, now vs a losing team" if hard
                                else "lost 3 straight (normal schedule), now vs a losing team")
            if not tags:
                continue
            pr = lib.profit(won, lib.dec(o))
            e = lib.early_price(xby, g["id"], side)
            band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else \
                "fav -151..-400" if -400 <= o < -150 else None
            for t in tags:
                if band:
                    C.add(f"{lg} | {band} | {t}", s, pr)
                    if e and ((band[0] == "d" and 100 <= e[0] <= 350) or (band[0] == "f" and -400 <= e[0] <= -101)):
                        C.add(f"{lg} | {band} | {t} | FIRST FAIR", s, lib.profit(won, e[1]))
                C.add(f"{lg} | ATS | {t}", s, lib.ats(g, side))

C.dump("s3", "SOFT-SCHEDULE STREAK, NFL + college (closing ML unless FIRST FAIR; train 2018-23, held 2024/25/26)",
       TR, HE)
