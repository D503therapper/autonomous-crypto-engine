"""11/21 daily studies S7-S10 - four reads never set against a price (ESPN's close at its own juice, regular season, a
team's games THIS season before tonight - no look-ahead; train 2018-21 / held out 2022-26 each season apart):
  S7  NHL: THE PUCK LINE'S PRICE AS A SHAPE READ - the favorite's no-vig chance to win by 2+ (its -1.5 price) against
      what its moneyline says it should be (a line fit on EARLIER seasons only); the fifth of games where the books
      price a bigger / a smaller margin than the moneyline implies -> the dog, the favorite, the total
  S8  THE HOME TEAM THAT'S BEEN BLOWN OUT IN ITS OWN BUILDING (the card's line): 2+ home losses by 3+ goals (NHL) /
      15+ points (NBA, college hoops) in its last 10 home games (5+ home games) -> the visiting dog, the home favorite
  S9  WINS AGAINST WHAT THE PRICES EXPECTED: wins minus the closing no-vig chances over the last 10 priced games
      (football: the last 5) - +2.0 or better (football +1.5) / -2.0 or worse -> dog, small favorite, spread
  S10 NBA: THE STARTERS' NET AGAINST THE SCOREBOARD - the starters' average plus-minus over the last 10 games minus
      the team's average margin: +3 or more (the starters win their minutes, the bench gives it back) / -3 or less
Cells fixed before the run. python results/studies/daily_1121/s_pro.py [s7 s8 s9 s10]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025, 2026]


def s7():
    O = h.Out("s7_nhl_puck_line_shape", TRAIN, HELD)
    O.p("S7 - NHL THE PUCK LINE'S PRICE AGAINST THE MONEYLINE (the fit and the cut points from EARLIER seasons only)")
    fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["sp"] in (-1.5, 1.5) and g["spho"] and g["spao"]]
    rows = []
    for g in fin:
        fav = "home" if g["sp"] < 0 else "away"
        if (g["mlh"] < g["mla"]) != (fav == "home"):          # the puck-line favorite must be the moneyline favorite
            continue
        p = lib.nv(g["mlh"], g["mla"])
        p = p if fav == "home" else 1 - p
        fo, do = (g["spho"], g["spao"]) if fav == "home" else (g["spao"], g["spho"])
        if fo == 0 or do == 0:
            continue
        q = (1 / lib.dec(fo)) / (1 / lib.dec(fo) + 1 / lib.dec(do))
        rows.append((g, fav, p, q))
    seasons = sorted({g["season"] for g, *_ in rows})
    O.p(f"games {len(rows)}; seasons {seasons}")
    for s in seasons[1:]:
        past = [(p, q) for g, _, p, q in rows if g["season"] < s]
        n = len(past)
        mp, mq = sum(p for p, _ in past) / n, sum(q for _, q in past) / n
        b = sum((p - mp) * (q - mq) for p, q in past) / sum((p - mp) ** 2 for p, _ in past)
        a = mq - b * mp
        res = sorted(q - (a + b * p) for p, q in past)
        lo, hi = res[int(0.2 * n)], res[int(0.8 * n)]
        O.p(f"  season {s}: q = {a:+.3f} + {b:.3f} p on {n}; fifths at {lo:+.4f} / {hi:+.4f}")
        for g, fav, p, q in rows:
            if g["season"] != s:
                continue
            r = q - (a + b * p)
            tag = "BIG-margin shape (top fifth)" if r >= hi else "SMALL-margin shape (bottom fifth)" if r <= lo else "middle"
            dog = "away" if fav == "home" else "home"
            hw = g["hs"] > g["as"]
            fo, do = (g["mlh"], g["mla"]) if fav == "home" else (g["mla"], g["mlh"])
            fw = hw == (fav == "home")
            fp, dp = lib.profit(fw, lib.dec(fo)), lib.profit(not fw, lib.dec(do))
            O.add(f"{tag}: the favorite (any price)", s, fp, fo)
            if -150 <= fo <= -101:
                O.add(f"{tag}: the favorite -150..-101", s, fp, fo)
            if 100 <= do <= 350:
                O.add(f"{tag}: the dog +100..+350", s, dp, do)
                if do <= 150:
                    O.add(f"{tag}: the dog +100..+150", s, dp, do)
            O.add(f"{tag}: the over", s, lib.tot_profit(g, True))
            O.add(f"{tag}: the under", s, lib.tot_profit(g, False))
            O.add(f"{tag}: the favorite -1.5", s, lib.ats(g, fav))
            O.add(f"{tag}: the dog +1.5", s, lib.ats(g, dog))
    O.show()
    for t in ("BIG-margin shape (top fifth)", "SMALL-margin shape (bottom fifth)"):
        for k in ("the dog +100..+350", "the favorite -150..-101", "the over", "the under"):
            O.placebo(f"{t}: {k}", f"middle: {k}")
            O.placebo(f"{t}: {k}", f"middle: {k}", fade=True)
    O.save()


BLOW = {"nhl": 3, "nba": 15, "ncaab": 15}


def s8():
    for lg in ("nhl", "nba", "ncaab"):
        O = h.Out(f"s8_home_blowouts_{lg}", TRAIN, HELD)
        O.p(f"S8 - {lg.upper()} THE HOME TEAM BLOWN OUT IN ITS OWN BUILDING (2+ home losses by {BLOW[lg]}+ in its last 10 home games)")
        fin = [g for g in lib.finals(lg) if g["stype"] == "2" and not g["neutral"]]
        allf = lib.all_finals(lg)
        tl = lib.team_log(allf)
        for g in fin:
            hg = [x for x in lib.before(tl, g["home"], g["start"]) if x["season"] == g["season"] and x["home"] == g["home"]
                  and not x["neutral"]][-10:]
            if len(hg) < 5:
                continue
            n = sum(1 for x in hg if x["as"] - x["hs"] >= BLOW[lg])
            tag = "2+ home blowout losses" if n >= 2 else "none" if n == 0 else "one"
            s = g["season"]
            hw = g["hs"] > g["as"]
            hp, ap = lib.profit(hw, lib.dec(g["mlh"])), lib.profit(not hw, lib.dec(g["mla"]))
            if 100 <= g["mla"] <= 350:
                O.add(f"{tag}: the visiting dog +100..+350", s, ap, g["mla"])
                if g["mla"] <= 150:
                    O.add(f"{tag}: the visiting dog +100..+150", s, ap, g["mla"])
            if -150 <= g["mlh"] <= -101:
                O.add(f"{tag}: the home favorite -150..-101", s, hp, g["mlh"])
            if g["mlh"] < -150:
                O.add(f"{tag}: the home favorite past -150", s, hp, g["mlh"])
            if 100 <= g["mlh"] <= 350:
                O.add(f"{tag}: the home dog +100..+350", s, hp, g["mlh"])
            if lg != "nhl":
                O.add(f"{tag}: the visitor's spread", s, lib.ats(g, "away"))
                if g["mlh"] < 0:
                    O.add(f"{tag}: the visitor's spread, home team favored", s, lib.ats(g, "away"))
        O.show()
        for k in ("the visiting dog +100..+350", "the home favorite -150..-101", "the home dog +100..+350"):
            O.placebo(f"2+ home blowout losses: {k}", f"none: {k}")
            O.placebo(f"2+ home blowout losses: {k}", f"none: {k}", fade=True)
        O.save()


def s9():
    for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
        O = h.Out(f"s9_vs_prices_{lg}", TRAIN, HELD)
        nb, cut = (5, 1.5) if lg in ("nfl", "ncaaf") else (10, 2.0)
        O.p(f"S9 - {lg.upper()} WINS AGAINST WHAT THE PRICES EXPECTED (last {nb} priced games this season; +/-{cut})")
        fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
        tl = lib.team_log(fin)

        def surplus(t, g):
            ps = [x for x in lib.before(tl, t, g["start"]) if x["season"] == g["season"]][-nb:]
            if len(ps) < nb:
                return None
            tot = 0.0
            for x in ps:
                p = lib.nv(x["mlh"], x["mla"])
                tot += (1.0 if lib.won_g(x, t) else 0.0) - (p if x["home"] == t else 1 - p)
            return tot
        for g in fin:
            sv = {"home": surplus(g["home"], g), "away": surplus(g["away"], g)}
            for side, team, opp, o, won, _ in lib.sides(g):
                v, ov = sv[side], sv["away" if side == "home" else "home"]
                if v is None:
                    continue
                pr = lib.profit(won, lib.dec(o))
                b = h.band(o)
                s = g["season"]
                a = lib.ats(g, side)
                if b:
                    O.add(f"base {b}", s, pr, o)
                O.add("base ats", s, a)
                tag = "BEAT its prices" if v >= cut else "UNDER its prices" if v <= -cut else None
                if not tag:
                    continue
                if b:
                    O.add(f"{tag} {b}", s, pr, o)
                O.add(f"{tag} ats", s, a)
                if ov is not None and ((v >= cut and ov <= -cut) or (v <= -cut and ov >= cut)):
                    O.add(f"{tag} vs the opposite ats", s, a)
                    if b:
                        O.add(f"{tag} vs the opposite {b}", s, pr, o)
        res = O.show()
        for k in list(res):
            if not k.startswith("base") and res[k] and res[k]["all"]["n"] >= 80:
                pool = "base ats" if k.endswith("ats") else f"base {k.rsplit(' ', 1)[1]}"
                O.placebo(k, pool, fade=res[k]["all"]["roi"] < res[pool]["all"]["roi"])
        O.save()


def s10():
    O = h.Out("s10_nba_starters_net", TRAIN, HELD)
    O.p("S10 - NBA THE STARTERS' NET AGAINST THE SCOREBOARD (starters' average plus-minus minus the team margin, last 10)")
    br = lib.box_rows("nba")
    fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
    allf = lib.all_finals("nba")
    tl = lib.team_log(allf)

    def game_val(x, t):
        rows = (br.get(x["id"]) or {}).get(str(t)) or []
        st = [lib.num(r["st"].get("plusMinus")) for r in rows if str(r.get("starter")) in ("1", "True", "true")]
        st = [v for v in st if v is not None]
        if len(st) != 5:
            return None
        return sum(st) / 5 - lib.margin_g(x, t)

    def read(t, g):
        ps = [x for x in lib.before(tl, t, g["start"]) if x["season"] == g["season"]][-10:]
        if len(ps) < 10:
            return None
        vs = [game_val(x, t) for x in ps]
        vs = [v for v in vs if v is not None]
        return sum(vs) / len(vs) if len(vs) >= 8 else None
    n_ok = 0
    for g in fin:
        rv = {"home": read(g["home"], g), "away": read(g["away"], g)}
        for side, team, opp, o, won, _ in lib.sides(g):
            v, ov = rv[side], rv["away" if side == "home" else "home"]
            if v is None:
                continue
            n_ok += 1
            pr = lib.profit(won, lib.dec(o))
            b = h.band(o)
            s = g["season"]
            a = lib.ats(g, side)
            if b:
                O.add(f"base {b}", s, pr, o)
            O.add("base ats", s, a)
            tag = "STARTERS +3 over the scoreboard" if v >= 3 else "STARTERS 3+ under the scoreboard" if v <= -3 else None
            if not tag:
                continue
            if b:
                O.add(f"{tag} {b}", s, pr, o)
            O.add(f"{tag} ats", s, a)
            if ov is not None and ((v >= 3 and ov <= -3) or (v <= -3 and ov >= 3)):
                O.add(f"{tag} vs the opposite ats", s, a)
    O.p(f"sides with a read: {n_ok}")
    res = O.show()
    for k in list(res):
        if not k.startswith("base") and res[k] and res[k]["all"]["n"] >= 80:
            pool = "base ats" if k.endswith("ats") else f"base {k.rsplit(' ', 1)[1]}"
            O.placebo(k, pool, fade=res[k]["all"]["roi"] < res[pool]["all"]["roi"])
    O.save()


if __name__ == "__main__":
    which = sys.argv[1:] or ["s7", "s8", "s9", "s10"]
    for w in which:
        {"s7": s7, "s8": s8, "s9": s9, "s10": s10}[w]()
