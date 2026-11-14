"""11/14 daily studies - NBA (S6-S10). Prices: ESPN's close at its own juice (regular season 2016-26: moneyline,
spread, total); the paid NBA history 2020-23 (the 'open' = the earliest fair look 20h+ before tip, the 'morning' = the
game-day 15:00Z look) for S10. Train 2016-21 / held 2022 / 2023 / 2024 / 2025 apart / now 2026.
S6 NBA EARLY SEASON - LAST SEASON vs THIS START (team games 1-15; 16-30 the dose): the team that was bad last season and
   starts hot (and the reverse) - does the price lag the new team, or over-chase it?
S7 NBA EARLY-SEASON TOTALS (both teams' game counts; 1-5 / 6-10 / 11-15 / 16+) and the league's own over run to date
   (this season's games so far: points minus the closing total) - does the market's total lag a new scoring year?
S8 NBA THE WHISTLE THE TEAMS BRING (the college study's NBA twin; free-throw attempts per game, own + allowed, season to
   date 10+ games, against the league to date) - on the total.
S9 NBA THE THREE-HEAVY DOG (its share of shots from three, season to date 10+ games, against the league to date; the
   variance idea: a dog that lives by the three swings more games) - moneyline and spread.
S10 NBA LINE SHAPE (paid 2020-23): open -> morning -> close on the spread and the moneyline - moved one way and came
   back / kept going; bet at the CLOSE."""
import importlib.util
import os
import pickle
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402

C = lib.CACHE
TR, HE = (2016, 2021), [2022, 2023, 2024, 2025, 2026]
fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("nba") if g["stype"] == "2"]
BOX = pickle.load(open(os.path.join(C, "nba_team.pkl"), "rb"))

# per team, per season: running lists (built walking forward; every read uses games strictly before)
hist = defaultdict(list)          # (team, season) -> [(start, won, gid, opp)]
for g in allf:
    for t, o, won in ((g["home"], g["away"], g["hs"] > g["as"]), (g["away"], g["home"], g["as"] > g["hs"])):
        hist[(t, g["season"])].append((g["start"], won, g["id"], o))


def before(t, s, start):
    return [x for x in hist[(t, s)] if x[0] < start]


def last_wp(t, s):
    lst = hist.get((t, s - 1), [])
    return sum(1 for x in lst if x[1]) / len(lst) if len(lst) >= 40 else None


def s6():
    o = h.Out("s6_nba_last_season_vs_start", TR, HE)
    o.p("S6 NBA EARLY SEASON: LAST SEASON vs THIS START (records before tip; moneyline + spread at the close)")
    for g in fin:
        for side, t, opp, odds, won, home in lib.sides(g):
            pr = lib.profit(won, lib.dec(odds))
            at = lib.ats(g, side)
            b = before(t, g["season"], g["start"])
            n = len(b)
            lw = last_wp(t, g["season"])
            bd = h.band(odds)
            if bd:
                o.add(f"BASE {bd}", g["season"], pr, odds)
            o.add("BASE ats", g["season"], at)
            if lw is None or n < 5 or n > 30:
                continue
            cw = sum(1 for x in b if x[1]) / n
            stage = "g6-15" if n < 15 else "g16-30"
            o.add(f"BASE ats {stage}", g["season"], at)
            if bd:
                o.add(f"BASE {bd} {stage}", g["season"], pr, odds)
            for nm, ok in (("bad last year (<.400), hot start (.600+)", lw < .4 and cw >= .6),
                           ("good last year (.600+), cold start (.400-)", lw >= .6 and cw <= .4),
                           ("start beats last year by .250+", cw - lw >= .25),
                           ("start trails last year by .250+", lw - cw >= .25)):
                if not ok:
                    continue
                o.add(f"S6 {stage} {nm} ATS", g["season"], at)
                if bd:
                    o.add(f"S6 {stage} {nm} {bd}", g["season"], pr, odds)
    o.show()
    for c in list(o.c):
        if c.startswith("S6 g6-15") and len(o.c[c]) >= 60:
            pool = "BASE ats g6-15" if c.endswith("ATS") else ("BASE dog g6-15" if c.endswith("dog") else "BASE fav g6-15")
            o.placebo(c, pool, fade=sum(p for _, p, _ in o.c[c]) < 0)
    o.save()


def s7_s8():
    o = h.Out("s7_s8_nba_totals", TR, HE)
    o.p("S7 / S8 NBA TOTALS: THE EARLY SEASON, THE LEAGUE'S OVER RUN, THE WHISTLE (over / under at the closing total)")
    run = defaultdict(list)            # season -> [(points - total)] of the season's games so far
    ft = defaultdict(lambda: [0, 0, 0])   # (team, season) -> [games, fta, fta allowed]
    lg = defaultdict(lambda: [0, 0])      # season -> [team-games, fta]
    day_buf = []
    cur_day = None
    for g in fin:
        if g["start"][:10] != cur_day:     # the day's games enter the running numbers only after the day
            for x in day_buf:
                x()
            day_buf, cur_day = [], g["start"][:10]
        s = g["season"]
        nh = len(before(g["home"], s, g["start"]))
        na = len(before(g["away"], s, g["start"]))
        mn = min(nh, na)
        stg = "g0-4" if mn < 5 else "g5-9" if mn < 10 else "g10-14" if mn < 15 else "g15+"
        r = run[s]
        lgo = statistics.mean(r) if len(r) >= 30 else None
        # the whistle: both teams' fta + allowed, against the league per team-game to date
        fh, fa, L = ft[(g["home"], s)], ft[(g["away"], s)], lg[s]
        wh = None
        if fh[0] >= 10 and fa[0] >= 10 and L[0] >= 200:
            lgf = L[1] / L[0]
            exp = (fh[1] / fh[0] + fa[2] / fa[0]) / 2 + (fa[1] / fa[0] + fh[2] / fh[0]) / 2
            wh = exp - 2 * lgf
        for over in (True, False):
            k = "over" if over else "under"
            pr = lib.tot_profit(g, over)
            o.add(f"BASE {k}", s, pr)
            o.add(f"S7 {k} stage {stg}", s, pr)
            if lgo is not None and mn < 15:
                if lgo >= 3:
                    o.add(f"S7 {k} early (g<15), league ran OVER by 3+ so far", s, pr)
                elif lgo <= -3:
                    o.add(f"S7 {k} early (g<15), league ran UNDER by 3+ so far", s, pr)
            if lgo is not None:
                if lgo >= 3:
                    o.add(f"S7 {k} any stage, league ran OVER by 3+ so far", s, pr)
                elif lgo <= -3:
                    o.add(f"S7 {k} any stage, league ran UNDER by 3+ so far", s, pr)
            if wh is not None:
                wb = "+6+" if wh >= 6 else "+3..6" if wh >= 3 else "-3..3" if wh > -3 else "-6..-3" if wh > -6 else "-6-"
                o.add(f"S8 {k} whistle {wb} FTA vs league", s, pr)
        if g["total"] is not None:
            def push(s=s, v=g["hs"] + g["as"] - g["total"]):
                run[s].append(v)
            day_buf.append(push)
        bx = BOX.get(g["id"], {})
        if g["home"] in bx and g["away"] in bx:
            def addft(s=s, g=g, bx=bx):
                for t, o_ in ((g["home"], g["away"]), (g["away"], g["home"])):
                    x = ft[(t, s)]
                    x[0] += 1
                    x[1] += bx[t]["fta"]
                    x[2] += bx[o_]["fta"]
                    lg[s][0] += 1
                    lg[s][1] += bx[t]["fta"]
            day_buf.append(addft)
    o.show()
    for c in list(o.c):
        if c.startswith(("S7", "S8")) and len(o.c[c]) >= 100:
            k = "BASE over" if " over " in c else "BASE under"
            o.placebo(c, k, fade=sum(p for _, p, _ in o.c[c]) < 0)
    o.save()


def s9():
    o = h.Out("s9_nba_three_heavy_dog", TR, HE)
    o.p("S9 NBA THE THREE-HEAVY DOG (3PA share of FGA season to date, 10+ games, minus the league's to date)")
    sh = defaultdict(lambda: [0, 0, 0])   # (team, season) -> [games, fga, tpa]
    lg = defaultdict(lambda: [0, 0])
    day_buf, cur_day = [], None
    for g in fin:
        if g["start"][:10] != cur_day:
            for x in day_buf:
                x()
            day_buf, cur_day = [], g["start"][:10]
        s = g["season"]
        L = lg[s]
        lsh = L[1] / L[0] if L[0] >= 2000 else None
        rel = {}
        for t in (g["home"], g["away"]):
            x = sh[(t, s)]
            rel[t] = (x[2] / x[1] - lsh) if (x[0] >= 10 and lsh) else None
        for side, t, opp, odds, won, home in lib.sides(g):
            pr = lib.profit(won, lib.dec(odds))
            at = lib.ats(g, side)
            line = g["sp"] if side == "home" else (-g["sp"] if g["sp"] is not None else None)
            bd = h.band(odds)
            if bd == "dog":
                o.add("BASE dog", s, pr, odds)
            if line is not None and line > 0:
                o.add("BASE spread dog ATS", s, at)
            if rel[t] is None or rel[opp] is None:
                continue
            r = rel[t] * 100
            rb = "+6+" if r >= 6 else "+3..6" if r >= 3 else "-3..3" if r > -3 else "-6..-3" if r > -6 else "-6-"
            gap = (rel[t] - rel[opp]) * 100
            if bd == "dog":
                o.add(f"S9 dog 3PA share {rb} pts vs league", s, pr, odds)
                if gap >= 6:
                    o.add("S9 dog shoots 6+ pts more of its shots from three than the favorite", s, pr, odds)
                if gap <= -6:
                    o.add("S9 dog shoots 6+ pts FEWER from three than the favorite", s, pr, odds)
                if odds >= 200 and r >= 3:
                    o.add("S9 long dog (+200..+350) 3PA share +3+", s, pr, odds)
            if line is not None and line > 0:
                o.add(f"S9 spread dog ATS 3PA share {rb}", s, at)
                if gap >= 6:
                    o.add("S9 spread dog ATS 6+ pts more from three than the fav", s, at)
        bx = BOX.get(g["id"], {})
        if g["home"] in bx and g["away"] in bx:
            def add(s=s, g=g, bx=bx):
                for t in (g["home"], g["away"]):
                    x = sh[(t, s)]
                    x[0] += 1
                    x[1] += bx[t]["fga"]
                    x[2] += bx[t]["tpa"]
                    lg[s][0] += bx[t]["fga"]
                    lg[s][1] += bx[t]["tpa"]
            day_buf.append(add)
    o.show()
    for c in list(o.c):
        if c.startswith("S9") and len(o.c[c]) >= 100:
            pool = "BASE spread dog ATS" if "ATS" in c else "BASE dog"
            o.placebo(c, pool, fade=sum(p for _, p, _ in o.c[c]) < 0)
    o.save()


def s10():
    o = h.Out("s10_nba_line_shape", (2020, 2021), [2022])
    o.p("S10 NBA LINE SHAPE (paid 2020-23: open = the earliest look 20h+ before tip (fair or not - the bet is at the close), morning = the game-day 15:00Z"
        " look; bet at ESPN's close; train 2020-21 + 2021-22 / held 2022-23)")
    spec = importlib.util.spec_from_file_location("nbaodds", os.path.join(lib.ROOT, "results/studies/nba_odds_1102/lib.py"))
    m = importlib.util.module_from_spec(spec)
    here = os.getcwd()
    spec.loader.exec_module(m)
    os.chdir(here)
    m.OUT = C
    games = m.load_games()
    lk = m.looks(games)
    prev = m.prev_tips(games)
    n = 0
    for g in fin:
        if g["id"] not in lk:
            continue
        # the shape needs no FAIR open (we bet at the close, after every look): the earliest look 20h+ before tip
        ml_l, sp_l = lk[g["id"]].get("ml", []), lk[g["id"]].get("sp", [])
        op = next((c for c in ml_l if c["h_before"] >= 20), None)
        mo = next((c for c in reversed(ml_l) if c["h_before"] < 20), None)
        sop = next((c for c in sp_l if c["h_before"] >= 20), None)
        smo = next((c for c in reversed(sp_l) if c["h_before"] < 20), None)
        pc = lib.nv(g["mlh"], g["mla"])
        n += 1
        for side, t, opp, odds, won, home in lib.sides(g):
            sg = 1 if side == "home" else -1
            pr = lib.profit(won, lib.dec(odds))
            at = lib.ats(g, side)
            bd = h.band(odds)
            if op and mo and bd:
                m1, m2 = sg * (mo["p"] - op["p"]) * 100, sg * (pc - mo["p"]) * 100
                o.add(f"BASE ml {bd}", g["season"], pr, odds)
                for nm, ok in (("moved TO it, then gave back", m1 >= 2 and m2 <= -1.5),
                               ("moved TO it, kept going", m1 >= 2 and m2 >= 1.5),
                               ("moved AWAY, then came back", m1 <= -2 and m2 >= 1.5),
                               ("moved AWAY, kept going", m1 <= -2 and m2 <= -1.5),
                               ("flat to morning, game-day move TO it 2+", abs(m1) < 1 and m2 >= 2),
                               ("flat to morning, game-day move AWAY 2+", abs(m1) < 1 and m2 <= -2)):
                    if ok:
                        o.add(f"S10 ml {bd} {nm}", g["season"], pr, odds)
            if sop and smo and g["sp"] is not None and at is not None:
                # points toward the side: the side's line getting SMALLER (fewer points / more laid) = money to it
                s1 = -sg * (smo["pt"] - sop["pt"])
                s2 = -sg * (g["sp"] - smo["pt"])
                o.add("BASE ats", g["season"], at)
                for nm, ok in (("moved TO it 1+, then gave back 1+", s1 >= 1 and s2 <= -1),
                               ("moved TO it 1+, kept going 1+", s1 >= 1 and s2 >= 1),
                               ("moved AWAY 1+, then came back 1+", s1 <= -1 and s2 >= 1),
                               ("moved AWAY 1+, kept going 1+", s1 <= -1 and s2 <= -1),
                               ("flat to morning, game-day move TO it 1.5+", abs(s1) < .5 and s2 >= 1.5),
                               ("flat to morning, game-day move AWAY 1.5+", abs(s1) < .5 and s2 <= -1.5)):
                    if ok:
                        o.add(f"S10 ats {nm}", g["season"], at)
    o.p(f"games in the paid history: {n}")
    o.show()
    for c in list(o.c):
        if c.startswith("S10") and len(o.c[c]) >= 60:
            pool = "BASE ats" if c.startswith("S10 ats") else ("BASE ml dog" if " dog " in c else "BASE ml fav")
            o.placebo(c, pool, fade=sum(p for _, p, _ in o.c[c]) < 0)
    o.save()


if __name__ == "__main__":
    which = sys.argv[1:] or ["s6", "s7", "s9", "s10"]
    for w, f in (("s6", s6), ("s7", s7_s8), ("s9", s9), ("s10", s10)):
        if w in which:
            f()
