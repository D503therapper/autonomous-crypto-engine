"""11/17 daily studies S2, S4-S10 - the game files at ESPN's close (its own juice), regular season, every fact known
before tip. Train = the seasons through 2021, held out 2022 / 2023 / 2024 / 2025 apart, now = 2026.
S2  NBA THE SPLIT MOVE (paid 2020-23 game-day morning -> the close): the moneyline and the spread moved different ways.
S4  NBA STRENGTH OF SCHEDULE SO FAR (games 5-30): the record built on soft / tough opponents (their win % to date).
S5  NHL STRENGTH OF SCHEDULE SO FAR (games 5-30).
S6  FOOTBALL STRENGTH OF SCHEDULE SO FAR (NFL games 4-14, college games 4-12; opponents with 3+ games on file).
S7  EVERY LEAGUE: THE IN-SEASON COACHING CHANGE (data/sports/coach_changes.json - games 1-3 after the change).
S8  COLLEGE HOOPS: THE LONG NOVEMBER-DECEMBER HOMESTAND (the home side's 4th+ straight true home game).
S9  COLLEGE HOOPS: RECORD vs POINTS (Pythagorean luck, exponent 11.5, 5+ games) - the NHL / NBA / football twins exist.
S10 THE POPULAR-TEAM TAX (NBA / NHL / NFL): a list fixed BEFORE looking - do the most-bet brands cost money?"""
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402

TRAIN, HELD = (2000, 2021), [2022, 2023, 2024, 2025, 2026]
WHICH = set(sys.argv[1:]) or {"s2", "s4", "s5", "s6", "s7", "s8", "s9", "s10"}


def band(o):
    if o is None:
        return None
    if 100 <= o <= 350:
        return "dog"
    if -150 <= o <= -101:
        return "fav"
    return None


def reg(fin):
    return [g for g in fin if g["stype"] == "2"]


def ml_prof(g, side):
    o = g["mlh"] if side == "home" else g["mla"]
    won = (g["hs"] > g["as"]) == (side == "home")
    return o, lib.profit(won, lib.dec(o))


def walk(lg):
    """Yield (g priced, state before it) in order: state = {team: {'w','l','pf','pa','opps':[...],'venues':[...]}} per
    season - updated AFTER each game is yielded (nothing from tonight)."""
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    priced = {g["id"]: g for g in reg(lib.finals(lg))}
    st = {}
    for g in allf:
        s = g["season"]
        for t in (g["home"], g["away"]):
            if (s, t) not in st:
                st[(s, t)] = {"w": 0, "l": 0, "pf": 0.0, "pa": 0.0, "opps": [], "ven": []}
        if g["id"] in priced:
            yield priced[g["id"]], st
        hw = g["hs"] > g["as"]
        for t, o, me, them, home in ((g["home"], g["away"], g["hs"], g["as"], True), (g["away"], g["home"], g["as"], g["hs"], False)):
            r = st[(s, t)]
            won = (me > them)
            r["w" if won else "l"] += 1 if me != them else 0
            r["pf"] += me
            r["pa"] += them
            r["opps"].append(o)
            r["ven"].append("N" if g["neutral"] else ("H" if home else "A"))
        del hw


def wp(r):
    n = r["w"] + r["l"]
    return r["w"] / n if n else None


# ---------------------------------------------------------------- S2 NBA SPLIT MOVE
if "s2" in WHICH:
    o = Out("s2_nba_split_move", (2020, 2021), [2022])
    mo = lib.nba_morning()
    n = 0
    for g in reg(lib.finals("nba")):
        m = mo.get(g["id"])
        if not m or m.get("p") is None or m.get("pt") is None or g["sp"] is None:
            continue
        n += 1
        pc = lib.nv(g["mlh"], g["mla"])
        ml_mv = (pc - m["p"]) * 100                    # + = ML money to home, morning -> close
        sp_mv = m["pt"] - g["sp"]                      # + = home laid more at the close
        for side in ("home", "away"):
            mlm = ml_mv if side == "home" else -ml_mv
            spm = sp_mv if side == "home" else -sp_mv
            od, pr = ml_prof(g, side)
            b = band(od)
            at = lib.ats(g, side)
            kind = None
            if mlm >= 1.5 and spm <= -0.5:
                kind = "ML money TO it, the number AWAY"
            elif mlm <= -1.5 and spm >= 0.5:
                kind = "ML money AWAY, the number TO it"
            elif mlm >= 1.5 and spm >= 0.5:
                kind = "both TO it"
            elif mlm >= 1.5 and abs(spm) < 0.5:
                kind = "ML to it, the number still"
            if kind:
                if b:
                    o.add(f"{b} {kind} ML @close", g["season"], pr)
                o.add(f"all {kind} ATS @close", g["season"], at)
            if b:
                o.add(f"{b} ALL ML @close", g["season"], pr)
            o.add("all ALL ATS @close", g["season"], at)
    o.p(f"NBA games with a paid morning ML + spread and a close: {n} (train 2020-21 / held 2022 = the 2022-23 season)")
    o.show()
    for k in list(o.c):
        if "AWAY" in k and "ALL" not in k:
            base = ("all ALL ATS @close" if "ATS" in k else ("dog ALL ML @close" if k.startswith("dog") else "fav ALL ML @close"))
            o.placebo(k, base)
            o.placebo(k, base, fade=True)
    o.save()

# ---------------------------------------------------------------- S4 / S5 SOS (NBA, NHL)
for lg, tag in (("nba", "s4"), ("nhl", "s5")):
    if tag not in WHICH:
        continue
    o = Out(f"{tag}_{lg}_strength_of_schedule", TRAIN, HELD)
    for g, st in walk(lg):
        s = g["season"]
        for side, t, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            r = st[(s, t)]
            n = r["w"] + r["l"]
            if not 5 <= n <= 30:
                continue
            ow = [wp(st[(s, x)]) for x in r["opps"] if wp(st[(s, x)]) is not None]
            if len(ow) < 5:
                continue
            sos = sum(ow) / len(ow)
            me = wp(r)
            od, pr = ml_prof(g, side)
            b = band(od)
            at = lib.ats(g, side) if lg == "nba" else None
            soft = "soft (opps < .450)" if sos < 0.45 else ("tough (opps > .550)" if sos > 0.55 else "middle")
            rec = "good (.600+)" if me >= 0.6 else ("bad (.400-)" if me <= 0.4 else "mid")
            for nm in (f"{soft}", f"{soft} & {rec}"):
                if b:
                    o.add(f"{b} {nm} ML", s, pr)
                if at is not None:
                    o.add(f"ATS {nm}", s, at)
            if b:
                o.add(f"{b} ALL ML", s, pr)
            if at is not None:
                o.add("ATS ALL", s, at)
            # the gap: my schedule's toughness vs the opponent's
            ro = st[(s, opp)]
            ow2 = [wp(st[(s, x)]) for x in ro["opps"] if wp(st[(s, x)]) is not None]
            if len(ow2) >= 5:
                gap = sos - sum(ow2) / len(ow2)
                gb = "my schedule .040+ TOUGHER" if gap >= 0.04 else ("my schedule .040+ SOFTER" if gap <= -0.04 else None)
                if gb:
                    if b:
                        o.add(f"{b} {gb} ML", s, pr)
                    if at is not None:
                        o.add(f"ATS {gb}", s, at)
    o.show(minn=40)
    for k in ("dog tough (opps > .550) & bad (.400-) ML", "fav soft (opps < .450) & good (.600+) ML",
              "dog my schedule .040+ TOUGHER ML", "fav my schedule .040+ SOFTER ML",
              "ATS my schedule .040+ TOUGHER", "ATS soft (opps < .450) & good (.600+)"):
        if k in o.c:
            base = "ATS ALL" if k.startswith("ATS") else (k.split()[0] + " ALL ML")
            o.placebo(k, base)
            o.placebo(k, base, fade=True)
    o.save()

# ---------------------------------------------------------------- S6 FOOTBALL SOS
if "s6" in WHICH:
    o = Out("s6_football_strength_of_schedule", TRAIN, HELD)
    for lg, lo, hi in (("nfl", 4, 14), ("ncaaf", 4, 12)):
        for g, st in walk(lg):
            s = g["season"]
            for side, t, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
                r = st[(s, t)]
                n = r["w"] + r["l"]
                if not lo <= n <= hi:
                    continue
                ow = [wp(st[(s, x)]) for x in r["opps"] if (st[(s, x)]["w"] + st[(s, x)]["l"]) >= 3]
                if len(ow) < max(3, n - 1):          # every opponent seen (college: no FCS team we hold half of)
                    continue
                sos = sum(ow) / len(ow)
                ro = st[(s, opp)]
                ow2 = [wp(st[(s, x)]) for x in ro["opps"] if (st[(s, x)]["w"] + st[(s, x)]["l"]) >= 3]
                if len(ow2) < max(3, ro["w"] + ro["l"] - 1):
                    continue
                gap = sos - sum(ow2) / len(ow2)
                me = wp(r)
                od, pr = ml_prof(g, side)
                b = band(od)
                at = lib.ats(g, side)
                gb = ("my schedule .080+ TOUGHER" if gap >= 0.08 else ("my schedule .080+ SOFTER" if gap <= -0.08 else "close"))
                rec = "good (.700+)" if me >= 0.7 else ("bad (.300-)" if me <= 0.3 else "mid")
                for nm in (gb, f"{gb} & {rec}"):
                    if b:
                        o.add(f"{lg} {b} {nm} ML", s, pr)
                    o.add(f"{lg} ATS {nm}", s, at)
                if b:
                    o.add(f"{lg} {b} ALL ML", s, pr)
                o.add(f"{lg} ATS ALL", s, at)
    o.show(minn=40)
    for k in ("nfl dog my schedule .080+ TOUGHER ML", "ncaaf dog my schedule .080+ TOUGHER ML", "nfl ATS my schedule .080+ TOUGHER",
              "ncaaf ATS my schedule .080+ TOUGHER", "ncaaf fav my schedule .080+ SOFTER ML", "nfl fav my schedule .080+ SOFTER ML"):
        if k in o.c:
            lg = k.split()[0]
            base = f"{lg} ATS ALL" if " ATS " in k else f"{lg} {k.split()[1]} ALL ML"
            o.placebo(k, base)
            o.placebo(k, base, fade=True)
    o.save()

# ---------------------------------------------------------------- S7 IN-SEASON COACHING CHANGE
if "s7" in WHICH:
    o = Out("s7_coach_change", TRAIN, HELD)
    ch = json.load(open(os.path.join(lib.sd.DATA, "coach_changes.json")))
    for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
        allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
        tl = lib.team_log(allf)
        priced = {g["id"]: g for g in reg(lib.finals(lg))}
        used = 0
        for c in ch:
            if c["league"] != lg:
                continue
            t, d = str(c["team"]), c["date"]
            before = [x for x in tl.get(t, []) if x["start"][:10] <= d]
            after = [x for x in tl.get(t, []) if x["start"][:10] > d]
            if not before or not after:
                continue
            if lib.days_between(before[-1]["start"], d + "T12:00Z") > 12 or lib.days_between(d + "T12:00Z", after[0]["start"]) > 12:
                continue                                  # an off-season hire, not an in-season change
            if before[-1]["season"] != after[0]["season"]:
                continue
            used += 1
            for k, x in enumerate(after[:3]):
                g = priced.get(x["id"])
                if not g:
                    continue
                side = "home" if g["home"] == t else "away"
                for who, sd_ in (("the changed team", side), ("the team across", "away" if side == "home" else "home")):
                    od, pr = ml_prof(g, sd_)
                    b = band(od)
                    at = lib.ats(g, sd_)
                    kk = "game 1" if k == 0 else "games 2-3"
                    it = "interim" if c["interim"] else "new hire"
                    for nm in (f"{who} {kk}", f"{who} games 1-3", f"{who} games 1-3 {it}", f"{who} games 1-3 [{lg}]"):
                        o.add(f"ATS {nm}", g["season"], at)
                        if b:
                            o.add(f"{b} ML {nm}", g["season"], pr)
                    if b:
                        o.add(f"{b} ML {who} games 1-3 any price band", g["season"], pr)
        o.p(f"{lg}: {used} in-season changes with games on both sides")
    o.show()
    o.save()

# ---------------------------------------------------------------- S8 / S9 COLLEGE HOOPS
if "s8" in WHICH or "s9" in WHICH:
    o8 = Out("s8_ncaab_long_homestand", TRAIN, HELD)
    o9 = Out("s9_ncaab_record_vs_points", TRAIN, HELD)
    for g, st in walk("ncaab"):
        s = g["season"]
        mth = int(g["start"][5:7])
        for side, t in (("home", g["home"]), ("away", g["away"])):
            r = st[(s, t)]
            od, pr = ml_prof(g, side)
            b = band(od)
            at = lib.ats(g, side)
            # S8: the home side's run of straight TRUE home games, tonight included
            if side == "home" and not g["neutral"] and mth in (11, 12):
                run = 1
                for v in reversed(r["ven"]):
                    if v != "H":
                        break
                    run += 1
                rb = "home game 1-3 in a row" if run <= 3 else ("home game 4-5 in a row" if run <= 5 else "home game 6+ in a row")
                ro = st[(s, g["away"])]
                opp_road = sum(1 for v in ro["ven"][-3:] if v == "A")
                for nm in (rb, f"{rb} & the visitor's 3rd+ straight road game" if opp_road == 3 and len(ro["ven"]) >= 3 else None):
                    if not nm:
                        continue
                    o8.add(f"home ATS {nm}", s, at)
                    if b:
                        o8.add(f"home {b} ML {nm}", s, pr)
                    oa = lib.ats(g, "away")
                    o8.add(f"visitor ATS {nm}", s, oa)
                    odv, prv = ml_prof(g, "away")
                    if band(odv):
                        o8.add(f"visitor {band(odv)} ML {nm}", s, prv)
            # S9: record vs points
            n = r["w"] + r["l"]
            if n >= 5 and r["pf"] + r["pa"] > 0 and mth in (11, 12, 1, 2):
                pe = r["pf"] ** 11.5 / (r["pf"] ** 11.5 + r["pa"] ** 11.5)
                luck = wp(r) - pe
                lb = "lucky (+.150)" if luck >= 0.15 else ("unlucky (-.150)" if luck <= -0.15 else ("lucky .075-.150" if luck >= 0.075 else ("unlucky .075-.150" if luck <= -0.075 else "even")))
                o9.add(f"ATS {lb}", s, at)
                if b:
                    o9.add(f"{b} ML {lb}", s, pr)
                o9.add("ATS ALL", s, at)
                if b:
                    o9.add(f"{b} ML ALL", s, pr)
    if "s8" in WHICH:
        o8.show(minn=40)
        o8.save()
    if "s9" in WHICH:
        o9.show()
        for k in ("ATS lucky (+.150)", "ATS unlucky (-.150)", "fav ML lucky (+.150)", "dog ML unlucky (-.150)"):
            if k in o9.c:
                base = "ATS ALL" if k.startswith("ATS") else k.split()[0] + " ML ALL"
                o9.placebo(k, base)
                o9.placebo(k, base, fade=True)
        o9.save()

# ---------------------------------------------------------------- S10 THE POPULAR-TEAM TAX
if "s10" in WHICH:
    POP = {"nba": {"Lakers", "Warriors", "Celtics", "Knicks", "Heat", "Bulls"},
           "nhl": {"Maple Leafs", "Canadiens", "Rangers", "Bruins", "Penguins", "Blackhawks", "Oilers"},
           "nfl": {"Cowboys", "Packers", "Steelers", "Chiefs", "49ers", "Patriots", "Eagles"}}
    o = Out("s10_popular_team_tax", TRAIN, HELD)
    for lg in ("nba", "nhl", "nfl"):
        byteam = defaultdict(lambda: defaultdict(list))
        for g in reg(lib.finals(lg)):
            for side, nm in (("home", g["hn"]), ("away", g["an"])):
                od, pr = ml_prof(g, side)
                b = band(od) or ("big fav" if od < -150 else ("long dog" if od > 350 else None))
                at = lib.ats(g, side)
                pop = nm in POP[lg]
                tag = "POPULAR" if pop else "the rest"
                if b:
                    o.add(f"{lg} {tag} {b} ML", g["season"], pr)
                    byteam[nm][b].append(pr)
                o.add(f"{lg} {tag} ATS", g["season"], at)
                if at is not None:
                    byteam[nm]["ATS"].append(at)
                # the popular team AWAY from home vs a non-popular home team (the road crowd + the tickets)
                if pop and side == "away" and g["hn"] not in POP[lg]:
                    o.add(f"{lg} POPULAR on the road vs the rest ATS", g["season"], at)
                    if band(od):
                        o.add(f"{lg} POPULAR on the road vs the rest {band(od)} ML", g["season"], pr)
                if not pop and (g["hn"] if side == "away" else g["an"]) in POP[lg] and (g["an"] if side == "away" else g["hn"]) not in POP[lg]:
                    o.add(f"{lg} the rest AGAINST a popular team ATS", g["season"], at)
                    if band(od):
                        o.add(f"{lg} the rest AGAINST a popular team {band(od)} ML", g["season"], pr)
        # placebo: random same-size team sets, their pooled ATS / fav ROI
        teams = [t for t in byteam if len(byteam[t]["ATS"]) >= 50]
        k = len([t for t in teams if t in POP[lg]])
        for key in ("ATS", "fav", "dog"):
            got = [x for t in teams if t in POP[lg] for x in byteam[t][key]]
            if not got:
                continue
            g0 = sum(got) / len(got)
            rnd = random.Random(11)
            worse = 0
            for _ in range(2000):
                pick = rnd.sample(teams, k)
                v = [x for t in pick for x in byteam[t][key]]
                if v and sum(v) / len(v) <= g0:
                    worse += 1
            o.p(f"  placebo {lg} POPULAR {key}: {g0*100:+.1f}% on {len(got)}; {worse} of 2000 random {k}-team sets did as badly")
    o.show()
    o.save()
