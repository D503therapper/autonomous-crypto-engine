"""11/18 daily studies S1-S10 - ten NEW angles on the sports in season. Every fact is known before the game (the
team's games so far this season, the line scores of games already played); prices: ESPN's close at its own juice
(the game files), the paid football history's first FAIR look (tools/early_football_study.ready_at / fair - no
look-ahead), the paid NBA (2020-23) / NHL (2021-23) game-day MORNING looks as the second price. Regular season only.
Train = the seasons through 2021 (paid football: 2020-22), each newer season held out apart, 2026 = now.
S1  NHL: THE OT-PRONE TEAM - the share of its games this season that went past regulation (10+ games).
S2  THE CLOSING HOLD (NBA / NHL / college hoops; football at the close as the second check): the books' overround at
    the close, by the league-season's own fifths - dogs / favorites in a wide-hold vs a tight-hold market.
S3  NBA / COLLEGE HOOPS: THE GAME AFTER A 1-2 POINT GAME (the heartbreak loss / the lucky win) - the NFL / college
    football heartbreak is dead (10/16); basketball never run.
S4  NHL / NBA: THE SEASON GAMES-PLAYED GAP (games 10+) - the favorite that has played 2-3+ more games than the dog.
S5  NHL / NBA: THE VENUE SPLIT - a road favorite with a losing ROAD record but a winning record; a home dog with a
    winning HOME record but a losing record.
S6  FOOTBALL (paid first fair look): THE SEASON'S EXTREME PRICE - the biggest dog / the shortest favorite a team has
    been all season, the first time a team is a dog.
S7  NBA / NHL / COLLEGE HOOPS: THE SEASON'S EXTREME PRICE at the close (S6's twin; the paid mornings as the 2nd price).
S8  COLLEGE HOOPS: THE IN-STATE GAME, Nov-Dec, a true home floor (the home state = where a team plays most home games).
S9  NHL / NBA: THE PRO LETDOWN - the favorite off a win over a .650+ team; the BOUNCE - off a loss to a .350- team.
S10 FOOTBALL: THE SHUTOUT - the team shut out last game / the team that pitched one (paid first fair look + the close).
"""
import os
import pickle
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

TRAIN, HELD = (2000, 2021), [2022, 2023, 2024, 2025, 2026]
FTRAIN, FHELD = (2020, 2022), [2023, 2024, 2025, 2026]
WHICH = set(sys.argv[1:]) or {f"s{i}" for i in range(1, 11)}
REGP = {"nhl": 3, "nba": 4, "ncaab": 2, "nfl": 4, "ncaaf": 4}


def band(o):
    if o is None:
        return None
    if 100 <= o <= 350:
        return "dog"
    if -150 <= o <= -101:
        return "fav"
    return None


def allg(lg):
    """Every finished regular-season game, in order, with the line scores, the venue state and the close (cached)."""
    cache = os.path.join(lib.CACHE, f"_allg_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = []
    for g in sm.finals(sd.load_games(lg), lg):
        if str(g.get("stype") or "2") != "2":
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        out.append({"id": g["id"], "start": g["start"], "season": lib.season(g["start"]), "home": g["home"],
                    "away": g["away"], "hs": hs, "as": as_, "neutral": str(g.get("neutral")) == "1",
                    "state": g.get("state") or "", "nper": len([x for x in str(g.get("ls_home") or "").split(",") if x != ""]),
                    "mlh": lib.num(g.get("ml_home")), "mla": lib.num(g.get("ml_away"))})
    out.sort(key=lambda x: x["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def walk(lg):
    """Yield (priced final g, st) - st[(season, team)] = the team's season so far BEFORE g (updated after the yield)."""
    priced = {g["id"]: g for g in lib.finals(lg) if g["stype"] == "2"}
    st = {}
    for g in allg(lg):
        s = g["season"]
        for t in (g["home"], g["away"]):
            st.setdefault((s, t), {"w": 0, "l": 0, "hw": 0, "hl": 0, "rw": 0, "rl": 0, "gp": 0, "ot": 0, "close": 0,
                                   "last": None, "prices": []})
        if g["id"] in priced:
            yield priced[g["id"]], g, st
        ot = g["nper"] > REGP[lg]
        for t, o, me, them, home in ((g["home"], g["away"], g["hs"], g["as"], True),
                                     (g["away"], g["home"], g["as"], g["hs"], False)):
            r, ro = st[(s, t)], st[(s, o)]
            won = me > them
            ow = (ro["w"] / (ro["w"] + ro["l"])) if (ro["w"] + ro["l"]) >= 8 else None
            r["last"] = {"margin": me - them, "opp_wp": ow, "ot": ot, "pts": me, "opp_pts": them, "home": home}
            if me == them:
                continue
            r["w" if won else "l"] += 1
            r["gp"] += 1
            if not g["neutral"]:
                k = ("h" if home else "r") + ("w" if won else "l")
                r[k] += 1
            r["ot"] += ot
            r["close"] += abs(me - them) <= 1
            mo = g["mlh"] if home else g["mla"]
            if mo:
                r["prices"].append(mo)


def ml(g, side):
    o = g["mlh"] if side == "home" else g["mla"]
    return o, lib.profit((g["hs"] > g["as"]) == (side == "home"), lib.dec(o))


def wp(r):
    n = r["w"] + r["l"]
    return r["w"] / n if n else None


def sides(g):
    return (("home", g["home"], g["away"]), ("away", g["away"], g["home"]))


def at_price(won, o):
    return lib.profit(won, lib.dec(o)) if o else None


def placebos(o, pairs):
    for k, base, fade in pairs:
        if k in o.c and base in o.c:
            o.placebo(k, base, fade=fade)


# ------------------------------------------------------------------------------------------------- S1 NHL OT-PRONE
if "s1" in WHICH:
    o = Out("s1_nhl_ot_prone", TRAIN, HELD)
    mo = lib.nhl_morning()
    for g, raw, st in walk("nhl"):
        s = g["season"]
        for side, t, opp in sides(g):
            r, ro = st[(s, t)], st[(s, opp)]
            if r["gp"] < 10 or ro["gp"] < 10:
                continue
            od, pr = ml(g, side)
            b = band(od)
            if not b:
                continue
            sh, osh = r["ot"] / r["gp"], ro["ot"] / ro["gp"]
            cs = r["close"] / r["gp"]                          # one-goal games incl. OT
            o.add(f"{b} ALL ML", s, pr)
            cut = "OT share 30%+" if sh >= 0.30 else ("OT share under 15%" if sh < 0.15 else "OT share 15-30%")
            o.add(f"{b} {cut} ML", s, pr)
            ocut = "opp OT share 30%+" if osh >= 0.30 else ("opp OT share under 15%" if osh < 0.15 else "opp 15-30%")
            o.add(f"{b} {ocut} ML", s, pr)
            if sh >= 0.30 and osh >= 0.30:
                o.add(f"{b} BOTH OT share 30%+ ML", s, pr)
            o.add(f"{b} one-goal share {'50%+' if cs >= 0.5 else ('under 35%' if cs < 0.35 else '35-50%')} ML", s, pr)
            m = mo.get(g["id"])
            if m:
                d = m["dh"] if side == "home" else m["da"]
                won = (g["hs"] > g["as"]) == (side == "home")
                o.add(f"{b} ALL @morning", s, lib.profit(won, d))
                o.add(f"{b} {cut} @morning", s, lib.profit(won, d))
                if sh >= 0.30 and osh >= 0.30:
                    o.add(f"{b} BOTH OT share 30%+ @morning", s, lib.profit(won, d))
    o.show(minn=30)
    placebos(o, [("dog OT share 30%+ ML", "dog ALL ML", False), ("dog OT share 30%+ ML", "dog ALL ML", True),
                 ("dog BOTH OT share 30%+ ML", "dog ALL ML", False), ("dog one-goal share 50%+ ML", "dog ALL ML", False),
                 ("fav OT share 30%+ ML", "fav ALL ML", True), ("dog opp OT share 30%+ ML", "dog ALL ML", False)])
    o.save()

# ------------------------------------------------------------------------------------------------- S2 CLOSING HOLD
if "s2" in WHICH:
    o = Out("s2_closing_hold", TRAIN, HELD)
    for lg in ("nba", "nhl", "ncaab", "nfl", "ncaaf"):
        fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
        by = defaultdict(list)
        for g in fin:
            g["_hold"] = 1 / lib.dec(g["mlh"]) + 1 / lib.dec(g["mla"]) - 1
            if 0 < g["_hold"] < 0.15:
                by[g["season"]].append(g["_hold"])
        cuts = {s: statistics.quantiles(v, n=5) for s, v in by.items() if len(v) >= 50}
        for g in fin:
            q = cuts.get(g["season"])
            if not q or not 0 < g["_hold"] < 0.15:
                continue
            fifth = "top fifth (wide)" if g["_hold"] >= q[3] else ("bottom fifth (tight)" if g["_hold"] <= q[0] else "middle")
            for side, t, opp in sides(g):
                od, pr = ml(g, side)
                b = band(od)
                if not b:
                    continue
                o.add(f"{lg} {b} ALL ML", g["season"], pr)
                o.add(f"{lg} {b} {fifth} ML", g["season"], pr)
                if lg in ("nba", "ncaab"):
                    a = lib.ats(g, side)
                    o.add(f"{lg} ATS ALL {b}-side", g["season"], a)
                    o.add(f"{lg} ATS {fifth} {b}-side", g["season"], a)
    o.show(minn=40)
    for lg in ("nba", "nhl", "ncaab", "nfl", "ncaaf"):
        for b in ("dog", "fav"):
            for f in ("top fifth (wide)", "bottom fifth (tight)"):
                placebos(o, [(f"{lg} {b} {f} ML", f"{lg} {b} ALL ML", False), (f"{lg} {b} {f} ML", f"{lg} {b} ALL ML", True)])
    o.save()

# ------------------------------------------------------------------------------------------------- S3 1-2 POINT GAMES
if "s3" in WHICH:
    o = Out("s3_hoops_one_two_point_game", TRAIN, HELD)
    for lg in ("nba", "ncaab"):
        for g, raw, st in walk(lg):
            s = g["season"]
            for side, t, opp in sides(g):
                r = st[(s, t)]
                if r["gp"] < 3 or not r["last"]:
                    continue
                od, pr = ml(g, side)
                b = band(od)
                a = lib.ats(g, side)
                m = r["last"]["margin"]
                kind = ("off a 1-2 pt LOSS" if -2 <= m <= -1 else "off a 1-2 pt WIN" if 1 <= m <= 2 else
                        "off a 15+ loss" if m <= -15 else "other")
                if r["last"]["ot"]:
                    kind = "off an OT game" if kind == "other" else kind + " (OT)"
                if b:
                    o.add(f"{lg} {b} ALL ML", s, pr)
                    o.add(f"{lg} {b} {kind} ML", s, pr)
                o.add(f"{lg} ATS ALL", s, a)
                o.add(f"{lg} ATS {kind}", s, a)
                ro = st[(s, opp)]
                if ro["last"] and -2 <= ro["last"]["margin"] <= -1 and b:
                    o.add(f"{lg} {b} vs a team off a 1-2 pt LOSS ML", s, pr)
                if ro["last"] and 1 <= ro["last"]["margin"] <= 2 and b:
                    o.add(f"{lg} {b} vs a team off a 1-2 pt WIN ML", s, pr)
    o.show(minn=40)
    for lg in ("nba", "ncaab"):
        placebos(o, [(f"{lg} dog off a 1-2 pt LOSS ML", f"{lg} dog ALL ML", False), (f"{lg} dog off a 1-2 pt LOSS ML", f"{lg} dog ALL ML", True),
                     (f"{lg} fav off a 1-2 pt WIN ML", f"{lg} fav ALL ML", True), (f"{lg} ATS off a 1-2 pt LOSS", f"{lg} ATS ALL", False),
                     (f"{lg} ATS off a 1-2 pt LOSS", f"{lg} ATS ALL", True), (f"{lg} ATS off a 1-2 pt WIN", f"{lg} ATS ALL", True),
                     (f"{lg} dog vs a team off a 1-2 pt WIN ML", f"{lg} dog ALL ML", False)])
    o.save()

# ------------------------------------------------------------------------------------------------- S4 GAMES-PLAYED GAP
if "s4" in WHICH:
    o = Out("s4_games_played_gap", TRAIN, HELD)
    for lg in ("nhl", "nba"):
        for g, raw, st in walk(lg):
            s = g["season"]
            for side, t, opp in sides(g):
                r, ro = st[(s, t)], st[(s, opp)]
                if r["gp"] < 10 or ro["gp"] < 10:
                    continue
                od, pr = ml(g, side)
                b = band(od)
                if not b:
                    continue
                gap = r["gp"] - ro["gp"]                     # + = I've played more
                cut = ("played 3+ MORE" if gap >= 3 else "played 2 more" if gap == 2 else "played 3+ FEWER" if gap <= -3
                       else "played 2 fewer" if gap == -2 else "within 1")
                o.add(f"{lg} {b} ALL ML", s, pr)
                o.add(f"{lg} {b} {cut} ML", s, pr)
                if lg == "nba":
                    o.add(f"{lg} ATS {cut}", s, lib.ats(g, side))
                    o.add(f"{lg} ATS ALL", s, lib.ats(g, side))
                if r["gp"] <= 30:
                    o.add(f"{lg} {b} games 10-30 {cut} ML", s, pr)
                    o.add(f"{lg} {b} games 10-30 ALL ML", s, pr)
    o.show(minn=40)
    for lg in ("nhl", "nba"):
        placebos(o, [(f"{lg} dog played 3+ FEWER ML", f"{lg} dog ALL ML", False), (f"{lg} dog played 3+ FEWER ML", f"{lg} dog ALL ML", True),
                     (f"{lg} dog played 3+ MORE ML", f"{lg} dog ALL ML", True), (f"{lg} dog played 3+ MORE ML", f"{lg} dog ALL ML", False),
                     (f"{lg} fav played 3+ MORE ML", f"{lg} fav ALL ML", True)])
    o.save()

# ------------------------------------------------------------------------------------------------- S5 VENUE SPLIT
if "s5" in WHICH:
    o = Out("s5_venue_split", TRAIN, HELD)
    for lg in ("nhl", "nba"):
        for g, raw, st in walk(lg):
            if g["neutral"]:
                continue
            s = g["season"]
            for side, t, opp in sides(g):
                r = st[(s, t)]
                if r["gp"] < 10:
                    continue
                od, pr = ml(g, side)
                b = band(od)
                if not b:
                    continue
                me = wp(r)
                vw, vl = (r["hw"], r["hl"]) if side == "home" else (r["rw"], r["rl"])
                if vw + vl < 5:
                    continue
                vp = vw / (vw + vl)
                d = vp - me
                o.add(f"{lg} {b} {side} ALL ML", s, pr)
                cut = "venue .200+ BETTER" if d >= 0.2 else ("venue .200+ WORSE" if d <= -0.2 else "venue close")
                o.add(f"{lg} {b} {side} {cut} ML", s, pr)
                if side == "away" and b == "fav" and vp < 0.4 and me >= 0.55:
                    o.add(f"{lg} fav away LOSING road record, winning overall ML", s, pr)
                if side == "home" and b == "dog" and vp >= 0.6 and me < 0.45:
                    o.add(f"{lg} dog home WINNING home record, losing overall ML", s, pr)
                if side == "away" and b == "dog" and vp >= 0.6 and me < 0.5:
                    o.add(f"{lg} dog away WINNING road record, under .500 overall ML", s, pr)
    o.show(minn=30)
    for lg in ("nhl", "nba"):
        placebos(o, [(f"{lg} fav away LOSING road record, winning overall ML", f"{lg} fav away ALL ML", True),
                     (f"{lg} fav away LOSING road record, winning overall ML", f"{lg} fav away ALL ML", False),
                     (f"{lg} dog home WINNING home record, losing overall ML", f"{lg} dog home ALL ML", False),
                     (f"{lg} dog home venue .200+ BETTER ML", f"{lg} dog home ALL ML", False),
                     (f"{lg} dog away venue .200+ BETTER ML", f"{lg} dog away ALL ML", False),
                     (f"{lg} dog away venue .200+ WORSE ML", f"{lg} dog away ALL ML", True),
                     (f"{lg} dog away WINNING road record, under .500 overall ML", f"{lg} dog away ALL ML", False)])
    o.save()


# ------------------------------------------------------------------------------------------------- S6 / S10 FOOTBALL
def football_rows(lg):
    """(g from the paid history, raw final, st before it, first fair {side: (american, decimal)})."""
    xby = {x["id"]: x for x in lib.load_football(lg)}
    for g, raw, st in walk(lg):
        x = xby.get(g["id"])
        ff = None
        if x and lib.first_fair(x["ml"]):
            h, a, _ = lib.ml_med(lib.first_fair(x["ml"])[1])
            ff = {"home": (lib.american(h), h), "away": (lib.american(a), a)}
        yield g, raw, st, ff


if "s6" in WHICH:
    o = Out("s6_football_extreme_price", FTRAIN, FHELD)
    for lg in ("nfl", "ncaaf"):
        for g, raw, st, ff in football_rows(lg):
            s = g["season"]
            if s < 2020:
                continue
            for side, t, opp in sides(g):
                r = st[(s, t)]
                if len(r["prices"]) < 3:
                    continue
                won = (g["hs"] > g["as"]) == (side == "home")
                oc, pc = ml(g, side)
                kinds = []
                for where, (od, pr) in (("first fair", ff[side] if ff else (None, None)), ("close", (oc, pc))):
                    if od is None:
                        continue
                    pr = lib.profit(won, ff[side][1]) if where == "first fair" else pr
                    b = band(od)
                    if not b:
                        continue
                    mx, mn = max(r["prices"]), min(r["prices"])
                    allfav = all(p < 0 for p in r["prices"])
                    o.add(f"{lg} {b} ALL @{where}", s, pr)
                    if b == "dog" and allfav:
                        o.add(f"{lg} dog FIRST TIME A DOG this season @{where}", s, pr)
                    if b == "dog" and mx > 0 and od >= mx + 30:
                        o.add(f"{lg} dog its BIGGEST dog price by 30c+ @{where}", s, pr)
                    if b == "dog" and mx > 0 and od < mx - 100:
                        o.add(f"{lg} dog 100c+ SHORTER than its biggest @{where}", s, pr)
                    if b == "fav" and mn < 0 and od < mn:
                        o.add(f"{lg} fav its SHORTEST fav price yet @{where}", s, pr)
                    if b == "fav" and all(p > 0 for p in r["prices"]):
                        o.add(f"{lg} fav FIRST TIME A FAVORITE this season @{where}", s, pr)
    o.show(minn=25)
    for lg in ("nfl", "ncaaf"):
        for w in ("first fair", "close"):
            placebos(o, [(f"{lg} dog FIRST TIME A DOG this season @{w}", f"{lg} dog ALL @{w}", False),
                         (f"{lg} dog FIRST TIME A DOG this season @{w}", f"{lg} dog ALL @{w}", True),
                         (f"{lg} dog its BIGGEST dog price by 30c+ @{w}", f"{lg} dog ALL @{w}", False),
                         (f"{lg} dog its BIGGEST dog price by 30c+ @{w}", f"{lg} dog ALL @{w}", True),
                         (f"{lg} fav FIRST TIME A FAVORITE this season @{w}", f"{lg} fav ALL @{w}", True),
                         (f"{lg} fav FIRST TIME A FAVORITE this season @{w}", f"{lg} fav ALL @{w}", False)])
    o.save()

if "s10" in WHICH:
    o = Out("s10_football_shutout", FTRAIN, FHELD)
    for lg in ("nfl", "ncaaf"):
        for g, raw, st, ff in football_rows(lg):
            s = g["season"]
            if s < 2020:
                continue
            for side, t, opp in sides(g):
                r, ro = st[(s, t)], st[(s, opp)]
                if not r["last"] or not ro["last"]:
                    continue
                won = (g["hs"] > g["as"]) == (side == "home")
                oc, pc = ml(g, side)
                kind = ("SHUT OUT last game" if r["last"]["pts"] == 0 else
                        "PITCHED a shutout last game" if r["last"]["opp_pts"] == 0 else None)
                okind = ("vs a team shut out last game" if ro["last"]["pts"] == 0 else
                         "vs a team that pitched a shutout" if ro["last"]["opp_pts"] == 0 else None)
                for where, od, pr in (("first fair", ff[side][0] if ff else None, lib.profit(won, ff[side][1]) if ff else None),
                                      ("close", oc, pc)):
                    b = band(od)
                    if not b:
                        continue
                    o.add(f"{lg} {b} ALL @{where}", s, pr)
                    if kind:
                        o.add(f"{lg} {b} {kind} @{where}", s, pr)
                    if okind:
                        o.add(f"{lg} {b} {okind} @{where}", s, pr)
                a = lib.ats(g, side)
                o.add(f"{lg} ATS ALL", s, a)
                if kind:
                    o.add(f"{lg} ATS {kind}", s, a)
    o.show(minn=20)
    for lg in ("nfl", "ncaaf"):
        for w in ("first fair", "close"):
            placebos(o, [(f"{lg} dog SHUT OUT last game @{w}", f"{lg} dog ALL @{w}", False),
                         (f"{lg} dog SHUT OUT last game @{w}", f"{lg} dog ALL @{w}", True),
                         (f"{lg} fav PITCHED a shutout last game @{w}", f"{lg} fav ALL @{w}", True),
                         (f"{lg} dog vs a team that pitched a shutout @{w}", f"{lg} dog ALL @{w}", False)])
    o.save()

# ------------------------------------------------------------------------------------------------- S7 HOOPS / HOCKEY EXTREME PRICE
if "s7" in WHICH:
    o = Out("s7_extreme_price_close", TRAIN, HELD)
    morn = {"nba": lib.nba_morning(), "nhl": lib.nhl_morning()}
    for lg in ("nba", "nhl", "ncaab"):
        for g, raw, st in walk(lg):
            s = g["season"]
            for side, t, opp in sides(g):
                r = st[(s, t)]
                if len(r["prices"]) < 5:
                    continue
                od, pr = ml(g, side)
                b = band(od)
                if not b:
                    continue
                won = (g["hs"] > g["as"]) == (side == "home")
                mx, mn = max(r["prices"]), min(r["prices"])
                cells = [f"{lg} {b} ALL"]
                if b == "dog" and all(p < 0 for p in r["prices"]):
                    cells.append(f"{lg} dog FIRST TIME A DOG")
                if b == "dog" and mx > 0 and od >= mx + 30:
                    cells.append(f"{lg} dog BIGGEST dog price by 30c+")
                if b == "fav" and all(p > 0 for p in r["prices"]):
                    cells.append(f"{lg} fav FIRST TIME A FAVORITE")
                if b == "fav" and mn < 0 and od < mn:
                    cells.append(f"{lg} fav SHORTEST fav price yet")
                m = morn.get(lg, {}).get(g["id"])
                for c in cells:
                    o.add(c + " ML", s, pr)
                    if m and m.get("dh"):
                        o.add(c + " @morning", s, lib.profit(won, m["dh"] if side == "home" else m["da"]))
    o.show(minn=30)
    for lg in ("nba", "nhl", "ncaab"):
        placebos(o, [(f"{lg} dog FIRST TIME A DOG ML", f"{lg} dog ALL ML", False), (f"{lg} dog FIRST TIME A DOG ML", f"{lg} dog ALL ML", True),
                     (f"{lg} dog BIGGEST dog price by 30c+ ML", f"{lg} dog ALL ML", False),
                     (f"{lg} dog BIGGEST dog price by 30c+ ML", f"{lg} dog ALL ML", True),
                     (f"{lg} fav FIRST TIME A FAVORITE ML", f"{lg} fav ALL ML", True),
                     (f"{lg} fav FIRST TIME A FAVORITE ML", f"{lg} fav ALL ML", False)])
    o.save()

# ------------------------------------------------------------------------------------------------- S8 IN-STATE
if "s8" in WHICH:
    o = Out("s8_ncaab_in_state", TRAIN, HELD)
    hs_ = defaultdict(Counter)
    for g in allg("ncaab"):
        if not g["neutral"] and g["state"]:
            hs_[g["home"]][g["state"]] += 1
    home_state = {t: c.most_common(1)[0][0] for t, c in hs_.items() if sum(c.values()) >= 10}
    for g in lib.finals("ncaab"):
        if g["stype"] != "2" or g["neutral"] or g["start"][5:7] not in ("11", "12"):
            continue
        a, h = home_state.get(g["away"]), home_state.get(g["home"])
        if not a or not h:
            continue
        ins = "IN-STATE" if a == h else "out-of-state"
        for side, t, opp in sides(g):
            od, pr = ml(g, side)
            b = band(od)
            at = lib.ats(g, side)
            if b:
                o.add(f"{b} {side} ALL ML", g["season"], pr)
                o.add(f"{b} {side} {ins} ML", g["season"], pr)
            o.add(f"ATS {side} ALL", g["season"], at)
            o.add(f"ATS {side} {ins}", g["season"], at)
            if g["sp"] is not None:
                dogside = (g["sp"] > 0) == (side == "home")
                if g["sp"] != 0:
                    o.add(f"ATS {'dog' if dogside else 'fav'} {side} {ins}", g["season"], at)
                    o.add(f"ATS {'dog' if dogside else 'fav'} {side} ALL", g["season"], at)
        tp = lib.tot_profit(g, False)
        o.add(f"UNDER {ins}", g["season"], tp)
        o.add("UNDER ALL", g["season"], tp)
    o.show(minn=40)
    placebos(o, [("dog home IN-STATE ML", "dog home ALL ML", False), ("dog home IN-STATE ML", "dog home ALL ML", True),
                 ("dog away IN-STATE ML", "dog away ALL ML", False), ("dog away IN-STATE ML", "dog away ALL ML", True),
                 ("ATS dog away IN-STATE", "ATS dog away ALL", False), ("ATS dog away IN-STATE", "ATS dog away ALL", True),
                 ("ATS dog home IN-STATE", "ATS dog home ALL", False), ("ATS dog home IN-STATE", "ATS dog home ALL", True),
                 ("UNDER IN-STATE", "UNDER ALL", False), ("UNDER IN-STATE", "UNDER ALL", True)])
    o.save()

# ------------------------------------------------------------------------------------------------- S9 PRO LETDOWN / BOUNCE
if "s9" in WHICH:
    o = Out("s9_pro_letdown_bounce", TRAIN, HELD)
    morn = {"nba": lib.nba_morning(), "nhl": lib.nhl_morning()}
    for lg in ("nhl", "nba"):
        for g, raw, st in walk(lg):
            s = g["season"]
            for side, t, opp in sides(g):
                r = st[(s, t)]
                if r["gp"] < 8 or not r["last"] or r["last"]["opp_wp"] is None:
                    continue
                od, pr = ml(g, side)
                b = band(od)
                if not b:
                    continue
                won = (g["hs"] > g["as"]) == (side == "home")
                L = r["last"]
                kind = ("off a WIN over a .650+ team" if L["margin"] > 0 and L["opp_wp"] >= 0.65 else
                        "off a LOSS to a .350- team" if L["margin"] < 0 and L["opp_wp"] <= 0.35 else
                        "off a LOSS to a .650+ team" if L["margin"] < 0 and L["opp_wp"] >= 0.65 else
                        "off a WIN over a .350- team" if L["margin"] > 0 and L["opp_wp"] <= 0.35 else "other")
                m = morn[lg].get(g["id"])
                for c in (f"{lg} {b} ALL", f"{lg} {b} {kind}"):
                    o.add(c + " ML", s, pr)
                    if m and m.get("dh"):
                        o.add(c + " @morning", s, lib.profit(won, m["dh"] if side == "home" else m["da"]))
                if lg == "nba":
                    o.add(f"{lg} ATS ALL", s, lib.ats(g, side))
                    o.add(f"{lg} ATS {kind}", s, lib.ats(g, side))
    o.show(minn=30)
    for lg in ("nhl", "nba"):
        placebos(o, [(f"{lg} fav off a WIN over a .650+ team ML", f"{lg} fav ALL ML", True),
                     (f"{lg} fav off a WIN over a .650+ team ML", f"{lg} fav ALL ML", False),
                     (f"{lg} fav off a LOSS to a .350- team ML", f"{lg} fav ALL ML", False),
                     (f"{lg} fav off a LOSS to a .350- team ML", f"{lg} fav ALL ML", True),
                     (f"{lg} dog off a WIN over a .650+ team ML", f"{lg} dog ALL ML", True),
                     (f"{lg} dog off a WIN over a .650+ team ML", f"{lg} dog ALL ML", False),
                     (f"{lg} dog off a LOSS to a .350- team ML", f"{lg} dog ALL ML", False),
                     (f"{lg} dog off a LOSS to a .650+ team ML", f"{lg} dog ALL ML", False)])
    o.save()
