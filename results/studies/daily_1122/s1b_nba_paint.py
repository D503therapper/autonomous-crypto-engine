"""11/22 daily studies S1b - THE NBA PAINT DEFENSE, the second look S1 asked for (s_hoops.py nba: the team whose
opponents score the biggest share of their points in the paint ATS -9.8% on 1,798, every season down; the dog that
shuts the paint +8.8% on 827). The five checks' second read, fixed before the run:
  (a) LEAGUE-RELATIVE - the top / bottom fifth by a team's rank among the league's CURRENT values that night (the
      fixed 2021-23 cut points drift: the paint's share of scoring fell as threes rose) - the form a live rule needs
  (b) the dose (the top tenth), the side ACROSS (the bet a weight would make), the absolute paint points allowed
  (c) is it three-point luck by another name? (a team whose opponents miss threes shows a high paint share): the
      cell split by the opponents' 3P% to date (the league's bottom third = "lucky from three")
  (d) a second price: ESPN's open (2023-26) and the paid morning look (2020-23 seasons)
python results/studies/daily_1122/s1b_nba_paint.py"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_hoops  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]
MIN = 10


def main():
    O = h.Out("s1b_nba_paint", TRAIN, HELD)
    O.p("S1b - NBA PAINT DEFENSE, LEAGUE-RELATIVE (rank among the league's current values; 10+ box games; 20+ teams read)")
    tb = s_hoops.teambox("nba")
    fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nba") if g["season"] >= 2021 and g["stype"] == "2"]
    try:
        mo = lib.nba_morning()
    except Exception as e:                                   # noqa: BLE001
        O.p(f"(no paid morning look: {str(e)[:80]})")
        mo = {}
    # walk every season in order: each team's running sums BEFORE each game
    run = defaultdict(lambda: defaultdict(float))            # (season, team) -> sums
    state = {}                                               # (gid, team) -> (paint_def share, abs paint allowed, opp 3P%, n)
    latest = defaultdict(dict)                               # season -> team -> (share, abs, o3)
    rank = {}                                                # (gid, team) -> (pct of share, pct of abs, pct of o3) among the league now
    for g in allf:
        s = g["season"]
        for t in (g["home"], g["away"]):
            r = run[(s, t)]
            if r["n"] >= MIN:
                v = (r["o_paint"] / max(1.0, r["o_pts"]), r["o_paint"] / r["n"], r["o_3m"] / max(1.0, r["o_3a"]), r["paint"] / max(1.0, r["pts"]))
                state[(g["id"], t)] = v
                latest[s][t] = v
        vals = latest[s]
        if len(vals) >= 20:
            for t in (g["home"], g["away"]):
                if (g["id"], t) in state:
                    me = state[(g["id"], t)]
                    rank[(g["id"], t)] = tuple(sum(1 for x in vals.values() if x[i] < me[i]) / (len(vals) - 1) for i in range(4))
        a, b = (tb.get(g["id"]) or {}).get(str(g["home"])), (tb.get(g["id"]) or {}).get(str(g["away"]))
        if not a or not b:
            continue
        for t, me, th, pts, opts in ((g["home"], a, b, g["hs"], g["as"]), (g["away"], b, a, g["as"], g["hs"])):
            pp, op = lib.num(me.get("pointsInPaint")), lib.num(th.get("pointsInPaint"))
            try:
                m3, a3 = (float(x) for x in str(th.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted")).split("-"))
            except ValueError:
                continue
            if pp is None or op is None:
                continue
            r = run[(s, t)]
            r["n"] += 1
            r["paint"] += pp
            r["o_paint"] += op
            r["pts"] += pts
            r["o_pts"] += opts
            r["o_3m"] += m3
            r["o_3a"] += a3
    n_read = sum(1 for g in fin if (g["id"], g["home"]) in rank and (g["id"], g["away"]) in rank)
    O.p(f"priced games with both teams ranked: {n_read}")
    for g in fin:
        if (g["id"], g["home"]) not in rank or (g["id"], g["away"]) not in rank:
            continue
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            other = "away" if side == "home" else "home"
            rk, ro = rank[(g["id"], team)], rank[(g["id"], opp)]
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(g, side)
            dog, fav = 100 <= o <= 350, -150 <= o <= -101

            def put(tag, sp=True):
                if sp:
                    O.add(f"{tag}: ATS", s, at)
                if dog:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                    if o <= 199:
                        O.add(f"{tag}: dog +100..+199", s, pr, o)
                if fav:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
                if o < -150:
                    O.add(f"{tag}: fav past -150", s, pr, o)
            put("BASE")
            soft, shut = rk[0] >= 0.8, rk[0] <= 0.2
            if soft:
                put("SOFT PAINT (top fifth of the league in the paint's share of opp points)")
                put("SOFT top tenth" if rk[0] >= 0.9 else "SOFT 80th-90th")
                put("SOFT + opponents cold from three (bottom third 3P% against)" if rk[2] <= 0.333 else "SOFT + opponents NOT cold from three")
                put("SOFT + the opponent scores in the paint (top 40%)" if ro[3] >= 0.6 else "SOFT + the opponent is not a paint team")
                put("SOFT at home" if side == "home" else "SOFT on the road")
            if shut:
                put("SHUTS THE PAINT (bottom fifth)")
                put("SHUT bottom tenth" if rk[0] <= 0.1 else "SHUT 10th-20th")
                put("SHUT + opponents hot from three (top third 3P% against)" if rk[2] >= 0.667 else "SHUT + opponents NOT hot from three")
            if 0.2 < rk[0] < 0.8:
                put("MIDDLE three fifths")
            if ro[0] >= 0.8 and not soft:
                put("ACROSS a soft-paint team (we are not one)")
            if ro[0] >= 0.8 and shut:
                put("SHUTS THE PAINT vs a SOFT-PAINT team")
            if ro[0] <= 0.2 and not shut:
                put("ACROSS a paint-shutting team (we are not one)")
            if rk[1] >= 0.8:
                put("ABS: top fifth paint points allowed a game")
            if rk[1] <= 0.2:
                put("ABS: bottom fifth paint points allowed a game")
            if rk[2] <= 0.2:
                put("CONTROL: opponents coldest fifth from three (the 3-point luck read alone)")
            # second prices
            if s >= 2023 and g["oh"] and g["oa"]:
                oo = g["oh"] if side == "home" else g["oa"]
                po = lib.profit(won, lib.dec(oo))
                for nm, c in (("SOFT PAINT", soft), ("SHUTS THE PAINT", shut), ("ACROSS a soft-paint team", ro[0] >= 0.8 and not soft), ("BASE", True)):
                    if c and 100 <= oo <= 350:
                        O.add(f"OPEN (ESPN 2023-26) {nm}: dog +100..+350", s, po, oo)
                    if c and -150 <= oo <= -101:
                        O.add(f"OPEN (ESPN 2023-26) {nm}: small fav -150..-101", s, po, oo)
            m = lib.morning_side(mo, g["id"], side) if mo else None
            if m:
                om, dm, _ = m
                pm = lib.profit(won, dm)
                x = mo.get(g["id"]) or {}
                am = None
                if x.get("pt") is not None:
                    mg = (g["hs"] - g["as"] + x["pt"]) if side == "home" else -(g["hs"] - g["as"] + x["pt"])
                    am = None if mg == 0 else lib.profit(mg > 0, lib.dec(-110))
                for nm, c in (("SOFT PAINT", soft), ("SHUTS THE PAINT", shut), ("ACROSS a soft-paint team", ro[0] >= 0.8 and not soft), ("BASE", True)):
                    if not c:
                        continue
                    O.add(f"MORNING (paid) {nm}: ATS at the morning number", s, am)
                    if 100 <= om <= 350:
                        O.add(f"MORNING (paid) {nm}: dog +100..+350", s, pm, om)
                    if -150 <= om <= -101:
                        O.add(f"MORNING (paid) {nm}: small fav -150..-101", s, pm, om)
    O.show()
    O.p("")
    for a, b, fd in (("SOFT PAINT (top fifth of the league in the paint's share of opp points): ATS", "BASE: ATS", True),
                     ("SOFT PAINT (top fifth of the league in the paint's share of opp points): small fav -150..-101", "BASE: small fav -150..-101", True),
                     ("SOFT PAINT (top fifth of the league in the paint's share of opp points): dog +100..+350", "BASE: dog +100..+350", True),
                     ("SHUTS THE PAINT (bottom fifth): dog +100..+350", "BASE: dog +100..+350", False),
                     ("SHUTS THE PAINT (bottom fifth): dog +100..+199", "BASE: dog +100..+199", False),
                     ("SHUTS THE PAINT (bottom fifth): ATS", "BASE: ATS", False),
                     ("ACROSS a soft-paint team (we are not one): dog +100..+350", "BASE: dog +100..+350", False),
                     ("ACROSS a soft-paint team (we are not one): ATS", "BASE: ATS", False),
                     ("SHUTS THE PAINT vs a SOFT-PAINT team: ATS", "BASE: ATS", False),
                     ("CONTROL: opponents coldest fifth from three (the 3-point luck read alone): ATS", "BASE: ATS", True)):
        O.placebo(a, b, fade=fd)
    O.save()


if __name__ == "__main__":
    main()
