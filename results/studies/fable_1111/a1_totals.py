"""A1 + A2 - COLLEGE HOOPS TOTALS (never cut: the 11/3 studies read the efficiency model's total (dead), altitude
(built), early totals and March overs; nothing read how the market CHASES a team's over / under record, the pace
PAIR, or three-point luck on the total).
A1 - THE OVER / UNDER CHASE: each team's average (points scored by both - the closing total) over its earlier priced
     games this season (5+), the PAIR = the two teams' mean; plus the last game alone (both went over by 15+).
A2 - PACE PAIR + SHOOTING LUCK ON THE TOTAL (team box 2021-26, 5+ boxed games): both teams fast / slow (possessions
     a game vs the season's running D1 median), the mismatch; SCORING LUCK = (own 3P% + the opponents' 3P%) over
     the D1 average, both teams - games that ran high on threes both ways (the 11/9 3P luck read the NET on sides).
Graded at the closing total and its real juice. A1: TRAIN 2018-22, HELD 2023 / 2024 / 2025; A2: TRAIN 2021-22."""
import statistics
from collections import defaultdict
import lib
import sports_ncaab_box as nb

B = lib.B
o = lib.Out("a1")
fin = [g for g in B.finals("ncaab") if g["stype"] == "2"]
box = nb.load_box()

run = defaultdict(list)                          # (season, team) -> [total - closing total]
runb = defaultdict(lambda: [0, 0.0, 0, 0, 0, 0])  # boxed games, possessions, 3pm, 3pa, opp 3pm, opp 3pa
poss_all = defaultdict(list)                     # season -> every team-game possessions so far
A1, A2 = lib.Cells(), lib.Cells()
nA1 = nA2 = 0
for g in fin:
    s = g["season"]
    pre = {sd: list(run[(s, g[sd])]) for sd in ("home", "away")}
    preb = {sd: tuple(runb[(s, g[sd])]) for sd in ("home", "away")}
    tot = g["hs"] + g["as"]
    month = int(g["start"][5:7])
    ph = "Nov-Dec" if month in (11, 12) else "Jan-Mar"
    if g["total"] is not None:
        po, pu = B.tot_profit(g, True), B.tot_profit(g, False)
        A1.add("BASE every over", s, po)
        A1.add("BASE every under", s, pu)
        if all(len(pre[x]) >= 5 for x in pre):
            nA1 += 1
            mh, ma = statistics.mean(pre["home"]), statistics.mean(pre["away"])
            pr = (mh + ma) / 2
            for cut in (3, 5, 7):
                if pr >= cut:
                    A1.add(f"PAIR over its totals by {cut}+ -> UNDER", s, pu)
                    A1.add(f"PAIR over its totals by {cut}+ -> over", s, po)
                    A1.add(f"PAIR over by {cut}+ -> UNDER, {ph}", s, pu)
                if pr <= -cut:
                    A1.add(f"PAIR under its totals by {cut}+ -> OVER", s, po)
                    A1.add(f"PAIR under its totals by {cut}+ -> under", s, pu)
                    A1.add(f"PAIR under by {cut}+ -> OVER, {ph}", s, po)
            if mh >= 5 and ma >= 5:
                A1.add("BOTH teams over by 5+ -> UNDER", s, pu)
            if mh <= -5 and ma <= -5:
                A1.add("BOTH teams under by 5+ -> OVER", s, po)
            if (mh >= 5 and ma <= -5) or (mh <= -5 and ma >= 5):
                A1.add("an over team vs an under team -> over", s, po)
            l5 = (statistics.mean(pre["home"][-5:]) + statistics.mean(pre["away"][-5:])) / 2
            if l5 >= 8:
                A1.add("PAIR last 5 over by 8+ -> UNDER", s, pu)
            if l5 <= -8:
                A1.add("PAIR last 5 under by 8+ -> OVER", s, po)
        if all(len(pre[x]) >= 1 for x in pre):
            lh, la = pre["home"][-1], pre["away"][-1]
            if lh >= 15 and la >= 15:
                A1.add("both went OVER by 15+ last game -> UNDER", s, pu)
            if lh <= -15 and la <= -15:
                A1.add("both stayed UNDER by 15+ last game -> OVER", s, po)
        # ---- A2 ----
        if s >= 2021 and all(preb[x][0] >= 5 and preb[x][3] >= 60 and preb[x][5] >= 60 for x in preb) and len(poss_all[s]) >= 600:
            nA2 += 1
            med = statistics.median(poss_all[s])
            sdv = statistics.pstdev(poss_all[s])
            ph_, pa_ = preb["home"][1] / preb["home"][0], preb["away"][1] / preb["away"][0]
            fast = lambda x: x >= med + 2.5
            slow = lambda x: x <= med - 2.5
            if fast(ph_) and fast(pa_):
                A2.add("PACE both fast (+2.5 poss) -> over", s, po)
                A2.add("PACE both fast (+2.5 poss) -> under", s, pu)
            if slow(ph_) and slow(pa_):
                A2.add("PACE both slow (-2.5 poss) -> under", s, pu)
                A2.add("PACE both slow (-2.5 poss) -> over", s, po)
            if (fast(ph_) and slow(pa_)) or (slow(ph_) and fast(pa_)):
                A2.add("PACE fast vs slow -> under", s, pu)
                A2.add("PACE fast vs slow -> over", s, po)
            d1 = 0.34
            lk = []
            for x in ("home", "away"):
                n, _, m3, a3, om3, oa3 = preb[x]
                lk.append((m3 / a3 - d1) + (om3 / oa3 - d1))
            L = (lk[0] + lk[1]) / 2
            for cut in (0.03, 0.05):
                if L >= cut:
                    A2.add(f"3P HOT both ways (pair +{cut:.2f}) -> UNDER", s, pu)
                    A2.add(f"3P HOT both ways (pair +{cut:.2f}) -> over", s, po)
                    A2.add(f"3P HOT both ways (pair +{cut:.2f}) -> UNDER, {ph}", s, pu)
                if L <= -cut:
                    A2.add(f"3P COLD both ways (pair -{cut:.2f}) -> OVER", s, po)
                    A2.add(f"3P COLD both ways (pair -{cut:.2f}) -> under", s, pu)
                    A2.add(f"3P COLD both ways (pair -{cut:.2f}) -> OVER, {ph}", s, po)
    if g["total"] is not None:
        for sd in ("home", "away"):
            run[(s, g[sd])].append(tot - g["total"])
    b = box.get(g["id"])
    if b and g["home"] in b and g["away"] in b:
        for sd, op in (("home", "away"), ("away", "home")):
            r = runb[(s, g[sd])]
            me, them = b[g[sd]], b[g[op]]
            r[0] += 1
            r[1] += (me["poss"] + them["poss"]) / 2
            r[2] += me["tpm"]; r[3] += me["tpa"]; r[4] += them["tpm"]; r[5] += them["tpa"]
        poss_all[s].append((b[g["home"]]["poss"] + b[g["away"]]["poss"]) / 2)

o.p(f"A1 - THE OVER / UNDER CHASE: {nA1} priced games with 5+ priced games each; TRAIN 2018-22, HELD 2023/24/25, 2026 live")
o.cells(A1, (2018, 2022), (2023, 2024, 2025, 2026))
o.p(f"\nA2 - PACE PAIR + 3P LUCK ON THE TOTAL: {nA2} games (team box 2021-26); TRAIN 2021-22, HELD 2023/24/25, 2026 live")
o.cells(A2, (2021, 2022), (2023, 2024, 2025, 2026))
o.p(f"\ncells: {len(A1.c)} + {len(A2.c)}")
o.save()
