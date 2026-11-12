"""11/12 studies 5, 6, 7, 10 (schedule facts; ESPN's close 2018-26; TRAIN 2018-21, HELD 2022 / 2023 / 2024 / 2025):
S5 the long layoff, DEEPER than the 10/31 lead (which read the rusty side ATS and its small favorite): the TOTAL, the
   first half, the dose, both teams rusty, the venue, the game AFTER the rusty game;
S6 buy games: a power-conference home favorite laying 10+ vs a low-major on a road swing (spread + total);
S7 the bounce-back after losing at home as a favorite: the next game, by venue and the size of the upset;
S10 late-season motivation beyond the built race dog: senior night, playing out the string, the clinched leader,
   the conference tournament bye, the teams with nothing left.
Every input is the schedule / the standings / the last game's result and closing price - all known before tip."""
from collections import defaultdict
import lib

R = lib.build()
TR, HE = (2018, 2021), (2022, 2023, 2024, 2025)
c5, c6, c7, c10 = (lib.Cells(f"s{i}", TR, HE) for i in (5, 6, 7, 10))
tab = defaultdict(dict)        # (season, conf key) -> {team: [w, l]}


def half_cover(g, side):
    """The 1st-half margin against 0.55 x the closing spread (the 11/3 fit; no 1H lines on file for history) -
    +1 / -1 a game, a rate not a bet."""
    if g["sp"] is None or not g["lsh"] or not g["lsa"]:
        return None
    m = g["lsh"][0] - g["lsa"][0] + 0.55 * g["sp"]
    if side == "A":
        m = -m
    return None if m == 0 else (1.0 if m > 0 else -1.0)


for g in R:
    if g["season"] < 2018:
        continue
    s, mon, d = g["season"], g["day"].month, g["day"]
    H, A = g["H"], g["A"]
    ov, un = lib.tot_p(g, True), lib.tot_p(g, False)
    reg = g["stype"] == "2"
    # conference standings at tip
    lead = {}
    for side, f in (("H", H), ("A", A)):
        t = g["home"] if side == "H" else g["away"]
        if f["ck"] is not None:
            tb = tab[(s, f["ck"])]
            tb.setdefault(t, [0, 0])
            best = max(w - l for w, l in tb.values())
            second = sorted((w - l for w, l in tb.values()), reverse=True)[1] if len(tb) > 1 else best
            f["gb"] = (best - (tb[t][0] - tb[t][1])) / 2
            f["cushion"] = (tb[t][0] - tb[t][1] - second) / 2 if tb[t][0] - tb[t][1] == best else None
            f["cg"] = tb[t][0] + tb[t][1]
            f["cpct"] = tb[t][0] / f["cg"] if f["cg"] else None
    if g["mlh"] and reg:
        for side, f, o in lib.both(g):
            if "rest" not in f or "rest" not in o:
                continue
            od, sp = lib.odds(g, side), lib.spread(g, side)
            bd = lib.band(od)
            ml, at = lib.ml_p(g, side), lib.ats_p(g, side)
            v = lib.ven(g, side)
            # ---------------- S5: the layoff ----------------
            if f["n"] >= 4 and o["n"] >= 4:
                c5.add("BASE ATS", g, at)
                rusty = f["rest"] >= 7 and o["rest"] <= 4
                if rusty:
                    dose = "7-9" if f["rest"] <= 9 else "10-13" if f["rest"] <= 13 else "14+"
                    win = "Dec 10-31" if (mon == 12 and d.day >= 10) else "Jan 1-10" if (mon == 1 and d.day <= 10) else "other"
                    c5.add("RUSTY (7+ off vs a team in rhythm) ATS", g, at)
                    c5.add(f"RUSTY ATS, off {dose} days", g, at)
                    c5.add(f"RUSTY ATS, {win}", g, at)
                    c5.add(f"RUSTY ATS, ven {v}", g, at)
                    c5.add(f"RUSTY ATS, {'favorite' if (sp or 0) < 0 else 'dog'}", g, at)
                    c5.add("RUSTY 1st half vs 0.55 x the spread (+1 / -1)", g, half_cover(g, side))
                    c5.add(f"RUSTY 1st half, ven {v}", g, half_cover(g, side))
                    c5.add("RUSTY game: OVER", g, ov)
                    c5.add("RUSTY game: UNDER", g, un)
                    c5.add(f"RUSTY game, off {dose} days: UNDER", g, un)
                    c5.add(f"RUSTY game, off {dose} days: OVER", g, ov)
                    if bd:
                        c5.add(f"RUSTY {bd} ML", g, ml)
                        c5.add(f"RUSTY {bd} ML at the OPEN", g, lib.ml_open_p(g, side))
                    if bd == "sfav":
                        c5.add(f"RUSTY small fav ML, ven {v}", g, ml)
                        c5.add(f"RUSTY small fav ML, {win}", g, ml)
                    if g["lsh"] and g["lsa"] and g["total"] is not None:
                        h1 = g["lsh"][0] + g["lsa"][0]
                        c5.add("RUSTY game: 1st-half points minus 0.47 x the total", g, h1 - 0.47 * g["total"])
                # the game AFTER the rusty game (2nd game back), opponent in rhythm
                L = f["last"]
                if f["rest"] <= 4 and o["rest"] <= 6 and f["n"] >= 5:
                    pass
                if f["rest"] >= 7 and o["rest"] >= 7 and side == "H":
                    c5.add("BOTH teams off 7+: OVER", g, ov)
                    c5.add("BOTH teams off 7+: UNDER", g, un)
                    c5.add("BOTH teams off 7+: home side ATS", g, at)
                    if g["lsh"] and g["lsa"] and g["total"] is not None:
                        c5.add("BOTH off 7+: 1st-half points minus 0.47 x the total", g, g["lsh"][0] + g["lsa"][0] - 0.47 * g["total"])
                if side == "H" and g["lsh"] and g["lsa"] and g["total"] is not None and f["rest"] <= 4 and o["rest"] <= 4:
                    c5.add("BASE (both in rhythm): 1st-half points minus 0.47 x the total", g, g["lsh"][0] + g["lsa"][0] - 0.47 * g["total"])
                if side == "H" and f["rest"] <= 4 and o["rest"] <= 4:
                    c5.add("BASE (both in rhythm): UNDER", g, un)
                    c5.add("BASE (both in rhythm): OVER", g, ov)
            # ---------------- S6: buy games ----------------
            if (side == "H" and not g["neutral"] and not g["conf"] and f["tier"] in ("power", "mid") and o["tier"] == "low"
                    and sp is not None and sp <= -10 and mon in (11, 12)):
                tr = "power" if f["tier"] == "power" else "mid-major"
                trip = "2+ road games in the last 7 days" if o["road7"] >= 2 else "1 road game in the last 7" if o["road7"] == 1 else "fresh"
                run = "3rd+ straight road game" if o["road_run"] >= 2 else "2nd straight" if o["road_run"] == 1 else "first road game of the swing"
                big = "10-15.5" if sp > -16 else "16-21.5" if sp > -22 else "22+"
                da = lib.ats_p(g, "A")
                c6.add(f"BUY GAME ({tr} host laying 10+): the favorite ATS", g, at)
                c6.add(f"BUY GAME ({tr} host): the dog ATS", g, da)
                c6.add(f"BUY GAME ({tr} host): OVER", g, ov)
                c6.add(f"BUY GAME ({tr} host): UNDER", g, un)
                c6.add(f"BUY GAME, visitor {trip}: the favorite ATS", g, at)
                c6.add(f"BUY GAME, visitor {trip}: the dog ATS", g, da)
                c6.add(f"BUY GAME, visitor {trip}: OVER", g, ov)
                c6.add(f"BUY GAME, visitor {trip}: UNDER", g, un)
                c6.add(f"BUY GAME, visitor's {run}: the favorite ATS", g, at)
                c6.add(f"BUY GAME, visitor's {run}: OVER", g, ov)
                c6.add(f"BUY GAME, visitor's {run}: UNDER", g, un)
                c6.add(f"BUY GAME, laying {big}: the favorite ATS", g, at)
                c6.add(f"BUY GAME, laying {big}: OVER", g, ov)
                c6.add(f"BUY GAME, laying {big}: UNDER", g, un)
                if o["road7"] >= 2:
                    c6.add(f"BUY GAME, visitor 2+ road in 7, laying {big}: the favorite ATS", g, at)
                    c6.add(f"BUY GAME, visitor 2+ road in 7, {'visitor on 1-2 days rest' if o['rest'] <= 2 else 'visitor rested 3+'}: the favorite ATS", g, at)
                    c6.add("BUY GAME, visitor 2+ road in 7: favorite 1st half vs 0.55 x the spread (+1 / -1)", g, half_cover(g, side))
                c6.add(f"BUY GAME, the host {'played 2 nights ago or less' if f['rest'] <= 2 else 'rested 3+'}: the favorite ATS", g, at)
                nxt = "host off a loss" if not f["last"]["won"] else "host off a win"
                c6.add(f"BUY GAME, {nxt}: the favorite ATS", g, at)
            # ---------------- S7: the bounce-back ----------------
            L = f["last"]
            if L["ven"] == "H" and not L["won"] and L["ml"] is not None and L["ml"] < 0 and f["rest"] <= 10:
                up = "a -300+ favorite" if L["ml"] <= -300 else "a -151..-299 favorite" if L["ml"] < -150 else "a -101..-150 favorite"
                c7.add("BASE ATS", g, None)
                c7.add("LOST AT HOME AS A FAVORITE, next game: ATS", g, at)
                c7.add(f"...as {up}: ATS", g, at)
                c7.add(f"...next game ven {v}: ATS", g, at)
                c7.add(f"...as {up}, next ven {v}: ATS", g, at)
                c7.add(f"...lost by {'10+' if L['m'] <= -10 else '1-9'}: ATS", g, at)
                c7.add(f"...{'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'}: ATS", g, at)
                c7.add(f"...next game {'on 1-2 days rest' if f['rest'] <= 2 else 'on 3+ days'}: ATS", g, at)
                if bd:
                    c7.add(f"...next game as {bd}: ML", g, ml)
                    c7.add(f"...next game as {bd}: ML at the OPEN", g, lib.ml_open_p(g, side))
                    c7.add(f"...as {up}, next as {bd}: ML", g, ml)
                    c7.add(f"...next ven {v} as {bd}: ML", g, ml)
                c7.add("...the side ACROSS: ATS", g, lib.ats_p(g, lib.other(side)))
                c7.add("...next game: OVER", g, ov)
                c7.add("...next game: UNDER", g, un)
            if bd:
                c7.add(f"BASE {bd} ML", g, ml)
            # the mirror: WON on the road as a dog last game (the upset winner's next game) - 11/4 lead, left alone
            # ---------------- S10: motivation ----------------
            if mon in (2, 3) and g["conf"] and "gb" in f and "gb" in o and f["cg"] >= 8 and o["cg"] >= 8:
                late = (mon == 3) or d.day >= 15
                c10.add("BASE Feb-Mar conference ATS", g, at)
                if bd:
                    c10.add(f"BASE Feb-Mar conference {bd} ML", g, ml)
                # senior night: the last regular-season home game
                if side == "H" and g["last_home"] and not g["neutral"]:
                    c10.add("SENIOR NIGHT (last home game): home ATS", g, at)
                    c10.add(f"SENIOR NIGHT: home ATS, home {'.500+ in the league' if f['cpct'] >= 0.5 else 'under .500'}", g, at)
                    c10.add(f"SENIOR NIGHT: home ATS, {'favorite' if sp is not None and sp < 0 else 'dog'}", g, at)
                    if bd:
                        c10.add(f"SENIOR NIGHT: home {bd} ML", g, ml)
                    c10.add("SENIOR NIGHT: OVER", g, ov)
                    c10.add("SENIOR NIGHT: UNDER", g, un)
                    if o["gb"] <= 1:
                        c10.add("SENIOR NIGHT vs a contender (within a game of first): home ATS", g, at)
                # playing out the string: .300 or worse in the league from Feb 15, not a neutral floor
                if late and not g["neutral"]:
                    if f["cpct"] <= 0.30:
                        c10.add("STRING (league .300 or worse, Feb 15+): ATS", g, at)
                        c10.add(f"STRING: ATS ven {v}", g, at)
                        c10.add(f"STRING vs a {'.600+' if o['cpct'] >= 0.6 else '.300 or worse too' if o['cpct'] <= 0.30 else 'middle'} team: ATS", g, at)
                        if side == "H":
                            c10.add("STRING team at home: OVER", g, ov)
                            c10.add("STRING team at home: UNDER", g, un)
                        if f["cpct"] <= 0.30 and o["cpct"] <= 0.30 and side == "H":
                            c10.add("BOTH teams .300 or worse, Feb 15+: OVER", g, ov)
                            c10.add("BOTH teams .300 or worse, Feb 15+: UNDER", g, un)
                    # the leader with a cushion (clinched or close to it)
                    if f.get("cushion") is not None and f["cushion"] >= 2:
                        c10.add("CUSHION (first by 2+ games, Feb 15+): ATS", g, at)
                        c10.add(f"CUSHION: ATS ven {v}", g, at)
                        c10.add(f"CUSHION by {'3+' if f['cushion'] >= 3 else '2-2.5'}: ATS", g, at)
                        if bd:
                            c10.add(f"CUSHION: {bd} ML", g, ml)
                        if sp is not None and sp <= -8:
                            c10.add("CUSHION laying 8+: ATS", g, at)
                    # the team that still needs it: within a game of first, vs a team 4+ back
                    if f["gb"] <= 1 and f.get("cushion") in (None, 0, 0.5, 1) and o["gb"] >= 4:
                        c10.add("IN THE RACE (within a game) vs a team 4+ back: ATS", g, at)
                        c10.add(f"IN THE RACE vs 4+ back, ven {v}: ATS", g, at)
                        if sp is not None and sp <= -8:
                            c10.add("IN THE RACE vs 4+ back, laying 8+: ATS", g, at)
                        if bd == "sfav":
                            c10.add("IN THE RACE vs 4+ back, small fav: ML", g, ml)
                    # both in the race
                    if f["gb"] <= 1 and o["gb"] <= 1 and side == "H":
                        c10.add("BOTH within a game of first: OVER", g, ov)
                        c10.add("BOTH within a game of first: UNDER", g, un)
                        c10.add("BOTH within a game of first: home ATS", g, at)
                # the conference tournament (a neutral March league game)
                if mon == 3 and g["neutral"]:
                    c10.add("CONF TOURNEY: ATS base", g, at)
                    if f["rest"] >= 3 and o["rest"] == 1:
                        c10.add("CONF TOURNEY: the team off a bye vs one that played yesterday: ATS", g, at)
                        c10.add("CONF TOURNEY: bye vs played yesterday: 1st half vs 0.55 x the spread (+1 / -1)", g, half_cover(g, side))
                        if bd:
                            c10.add(f"CONF TOURNEY: bye team {bd} ML", g, ml)
                        c10.add("CONF TOURNEY: bye vs played yesterday: OVER", g, ov)
                        c10.add("CONF TOURNEY: bye vs played yesterday: UNDER", g, un)
                    if f["rest"] == 1 and o["rest"] == 1 and side == "H":
                        c10.add("CONF TOURNEY: both played yesterday: UNDER", g, un)
                        c10.add("CONF TOURNEY: both played yesterday: OVER", g, ov)
                    if f["cpct"] >= 0.75:
                        c10.add("CONF TOURNEY: a .750+ league team (safe) ATS", g, at)
                        if sp is not None and sp <= -8:
                            c10.add("CONF TOURNEY: a .750+ league team laying 8+ ATS", g, at)
                    if f["cpct"] <= 0.40:
                        c10.add("CONF TOURNEY: a .400-or-worse league team (must win it) ATS", g, at)
                        if bd == "dog":
                            c10.add("CONF TOURNEY: a .400-or-worse team dog ML", g, ml)
                    if f["cpct"] <= 0.40 and f["rest"] == 1 and f["last"]["won"]:
                        c10.add("CONF TOURNEY: a .400-or-worse team that won yesterday ATS", g, at)
    # after the game: the standings
    if g["conf"] and reg and H["ck"] is not None:
        tb = tab[(s, H["ck"])]
        hw = g["hs"] > g["as"]
        tb.setdefault(g["home"], [0, 0])[0 if hw else 1] += 1
        tb.setdefault(g["away"], [0, 0])[1 if hw else 0] += 1
for c, t in ((c5, "S5 - THE LONG LAYOFF, DEEPER"), (c6, "S6 - BUY GAMES"), (c7, "S7 - THE BOUNCE-BACK AFTER A HOME LOSS AS A FAVORITE"),
             (c10, "S10 - LATE-SEASON MOTIVATION")):
    print("\n=====", t)
    c.lines.append(t + "  (TRAIN 2018-21 | HELD 2022-25; profit a unit at the close)")
    c.dump()
