"""11/23 daily studies - THE CONTROLS before a weight, for the three cells s_today.py left standing:
  S4b  NHL: the dog in the bottom fifth of takeaways-minus-giveaways in its ROAD games (-18.1% on 890, both halves)
       - is it the built out-shot read (shots-on-net share, last 10) by another name? the dose, home / road, the
       price, off a back-to-back, the favorite across, ESPN's open (2023-26) and the paid morning (2021-23)
  S6b  NHL: the team that gave up 40+ shots last game, playing again within 2 days (-22.0% on 360 as a dog) - a
       back-to-back apart from one night off, the out-shot team apart, the open / the morning
  S7b  NBA: a top-2 minutes man played 40+ in the team's last game (dog -15.7% on 812, both halves) - overtime, the
       days between, the dose (36-39 as a control), short-handed, the record, home / road, the price, the favorite
       across, the paid morning (2020-23) and ESPN's open
Placebos are PRICE-MATCHED (the same number of dogs out of each 50-cent price bin of the pool).
python results/studies/daily_1123/s_follow.py [nhl nba]"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_today as T  # noqa: E402


def matched(O, name, pool_name, n=2000, seed=11, fade=True):
    rs, pool = O.c.get(name, []), O.c.get(pool_name, [])
    if not rs:
        return
    bins = defaultdict(list)
    for _, p, o in pool:
        bins[int(o // 50)].append(p)
    need = defaultdict(int)
    for _, _, o in rs:
        need[int(o // 50)] += 1
    got = sum(p for _, p, _ in rs) / len(rs)
    rnd = random.Random(seed)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for b, k in need.items():
            tot += sum(rnd.sample(bins[b], k)) if len(bins[b]) >= k else sum(rnd.choices(bins[b], k=k))
        m = tot / len(rs)
        hit += (m <= got) if fade else (m >= got)
    O.p(f"  PRICE-MATCHED placebo {name}: {hit} of {n} random same-price sets did as {'badly' if fade else 'well'} (cell {got*100:+.1f}% on {len(rs)})")


def nhl():
    tb = T.teambox("nhl")
    fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021 and g["stype"] == "2"]
    mo = lib.nhl_morning()
    last, prev = {}, {}
    for g in allf:
        for t in (g["home"], g["away"]):
            if (g["season"], t) in prev:
                last[(g["id"], t)] = prev[(g["season"], t)] + (g["start"],)
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            b = (tb.get(g["id"]) or {}).get(str(o))
            sa = lib.num((b or {}).get("shotsTotal"))
            prev[(g["season"], t)] = (sa, g["start"], lib.won_g(g, t))

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        v = [lib.num(a.get(k)) for k in ("giveaways", "takeaways", "shotsTotal")] + [lib.num(b.get(k)) for k in ("giveaways", "takeaways", "shotsTotal")]
        if None in v:
            return None
        road = 1.0 if g["away"] == t else 0.0
        return {"gv": v[0], "tk": v[1], "sf": v[2], "sa": v[5], "r_n": road, "r_net": road * (v[1] - v[0]), "r_gv": road * v[0],
                "r_tk": road * v[1], "h_net": (1 - road) * (v[1] - v[0])}

    def feats(s, n):
        if s["r_n"] < 4 or n - s["r_n"] < 4:
            return None
        return {"rnet": s["r_net"] / s["r_n"], "net": (s["tk"] - s["gv"]) / n, "rgv": s["r_gv"] / s["r_n"], "rtk": s["r_tk"] / s["r_n"],
                "hnet": s["h_net"] / (n - s["r_n"])}

    def c10(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        sf, sa = lib.num(a.get("shotsTotal")), lib.num(b.get("shotsTotal"))
        if sf is None or sa is None:
            return None
        return {"sf": sf, "sa": sa}
    rk = T.ranked(allf, counters, feats, 10)
    rk10 = T.ranked(allf, c10, lambda s, n: {"ss": s["sf"] / (s["sf"] + s["sa"])}, 10, window=10)
    O = h.Out("s4b_s6b_nhl_controls", T.BT, T.BH)
    O.p("S4b / S6b - NHL: THE CONTROLS (moneylines at ESPN's close unless said; team box 2021-26; train 2021-23 / held 2024-26)")
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        sa_, sb_ = rk10.get((g["id"], g["home"])), rk10.get((g["id"], g["away"]))
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            ms, ts = (sa_, sb_) if side == "home" else (sb_, sa_)
            pr = lib.profit(won, lib.dec(o))
            lv = last.get((g["id"], team))
            days = lib.days_between(lv[1], lv[3]) if lv else None
            b2b = days is not None and days <= 1.3
            shelled = bool(lv and lv[0] is not None and lv[0] >= 40)
            dog = 100 <= o <= 350
            if dog:
                O.add("BASE dog +100..+350", s, pr, o)
            if -200 <= o <= -101:
                O.add("BASE favorite -200..-101", s, pr, o)
            op = g["oh"] if side == "home" else g["oa"]
            m = lib.morning_side(mo, g["id"], side)
            # ---- S4b
            if me and th:
                p = me["rnet"][1]
                low = p <= 0.2
                if dog:
                    O.add("S4 BASE dog (both teams read)", s, pr, o)
                    band = "bottom tenth" if p <= 0.1 else "10-20" if p <= 0.2 else "20-40" if p <= 0.4 else "40-60" if p <= 0.6 else "60-80" if p <= 0.8 else "top fifth"
                    O.add(f"S4 dose: road takeaway net, league place {band}", s, pr, o)
                    if me["rgv"][1] >= 0.8:
                        O.add("S4 parts: TOP fifth road GIVEAWAYS alone", s, pr, o)
                    if me["rtk"][1] <= 0.2:
                        O.add("S4 parts: BOTTOM fifth road TAKEAWAYS alone", s, pr, o)
                    if me["hnet"][1] <= 0.2:
                        O.add("S4 control: BOTTOM fifth takeaway net in HOME games only (the home scorer's count)", s, pr, o)
                    if ms and ms["ss"][1] <= 0.2:
                        O.add("S4 control: the built read alone - BOTTOM fifth shots-on-net share, last 10", s, pr, o)
                if low and dog:
                    O.add("S4 LOW dog (bottom fifth road takeaway net)", s, pr, o)
                    O.add("S4 LOW dog: " + ("home" if side == "home" else "road"), s, pr, o)
                    O.add("S4 LOW dog: " + ("+100..+150" if o <= 150 else "+151..+350"), s, pr, o)
                    O.add("S4 LOW dog: " + ("on a back-to-back" if b2b else "not on a back-to-back"), s, pr, o)
                    if ms:
                        O.add("S4 LOW dog: " + ("ALSO out-shot (bottom fifth shot share, the built read)" if ms["ss"][1] <= 0.2 else
                                                 "NOT out-shot (shot share above the bottom fifth)"), s, pr, o)
                        if ms["ss"][1] >= 0.5:
                            O.add("S4 LOW dog: shot share in the league's top half", s, pr, o)
                    O.add("S4 LOW dog: " + ("Oct-Dec" if g["start"][5:7] in ("10", "11", "12") else "Jan-Apr"), s, pr, o)
                    if th["rnet"][1] >= 0.8:
                        O.add("S4 LOW dog vs a TOP fifth road takeaway net team", s, pr, o)
                    if op and 100 <= op <= 350:
                        O.add("S4 LOW dog at ESPN's OPEN (2023-26)", s, lib.profit(won, lib.dec(op)), op)
                    if m and 100 <= m[0] <= 350:
                        O.add("S4 LOW dog at the paid MORNING price (2021-23)", s, lib.profit(won, m[1]), m[0])
                if dog and op and 100 <= op <= 350:
                    O.add("S4 BASE dog at ESPN's OPEN", s, lib.profit(won, lib.dec(op)), op)
                if dog and m and 100 <= m[0] <= 350:
                    O.add("S4 BASE dog at the paid MORNING price", s, lib.profit(won, m[1]), m[0])
                if th["rnet"][1] <= 0.2 and me["rnet"][1] > 0.2 and -200 <= o <= -101:
                    O.add("S4 the favorite -200..-101 ACROSS a LOW team", s, pr, o)
                if low and -150 <= o <= -101:
                    O.add("S4 LOW small favorite -150..-101", s, pr, o)
                if me["rnet"][1] >= 0.8 and dog:
                    O.add("S4 HIGH dog (top fifth road takeaway net)", s, pr, o)
            # ---- S6b
            if shelled and days is not None and days <= 2.2:
                if dog:
                    O.add("S6 SHELLED dog (40+ shots against last game, within 2 days)", s, pr, o)
                    O.add("S6 SHELLED dog: " + ("on a back-to-back" if b2b else "one night off"), s, pr, o)
                    if ms:
                        O.add("S6 SHELLED dog: " + ("out-shot team (bottom fifth shot share)" if ms["ss"][1] <= 0.2 else "NOT an out-shot team"), s, pr, o)
                    if me:
                        O.add("S6 SHELLED dog: " + ("LOW road takeaway net too" if me["rnet"][1] <= 0.2 else "not LOW"), s, pr, o)
                    O.add("S6 SHELLED dog: " + ("home" if side == "home" else "road"), s, pr, o)
                    if op and 100 <= op <= 350:
                        O.add("S6 SHELLED dog at ESPN's OPEN", s, lib.profit(won, lib.dec(op)), op)
                    if m and 100 <= m[0] <= 350:
                        O.add("S6 SHELLED dog at the paid MORNING price", s, lib.profit(won, m[1]), m[0])
                if -200 <= o <= -101:
                    O.add("S6 SHELLED favorite -200..-101", s, pr, o)
            if dog and lv and lv[0] is not None and days is not None and days <= 2.2:
                sa = lv[0]
                O.add(f"S6 dose: shots against last game {'under 25' if sa < 25 else '25-29' if sa < 30 else '30-34' if sa < 35 else '35-39' if sa < 40 else '40-44' if sa < 45 else '45+'} (within 2 days)", s, pr, o)
    O.show()
    O.p("")
    for nm in ("S4 LOW dog (bottom fifth road takeaway net)", "S4 LOW dog: NOT out-shot (shot share above the bottom fifth)",
               "S4 LOW dog: not on a back-to-back", "S4 control: the built read alone - BOTTOM fifth shots-on-net share, last 10",
               "S4 control: BOTTOM fifth takeaway net in HOME games only (the home scorer's count)",
               "S6 SHELLED dog (40+ shots against last game, within 2 days)", "S6 SHELLED dog: one night off", "S6 SHELLED dog: NOT an out-shot team"):
        matched(O, nm, "BASE dog +100..+350")
    matched(O, "S4 LOW dog at ESPN's OPEN (2023-26)", "S4 BASE dog at ESPN's OPEN")
    matched(O, "S4 LOW dog at the paid MORNING price (2021-23)", "S4 BASE dog at the paid MORNING price")
    matched(O, "S4 the favorite -200..-101 ACROSS a LOW team", "BASE favorite -200..-101", fade=False)
    O.save()


def nba():
    fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["season"] >= 2018]
    allf = [g for g in lib.all_finals("nba") if g["season"] >= 2018]
    lsby = {g["id"]: g for g in lib.finals("nba")}
    bx = lib.box_rows("nba")
    mo = lib.nba_morning()
    mins = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    prev, flag, rec = {}, {}, defaultdict(lambda: [0, 0])
    for g in allf:
        for t in (g["home"], g["away"]):
            key = (g["season"], t)
            tot = mins[key]
            reg = sorted((p for p, v in tot.items() if v[1] >= 10), key=lambda p: -tot[p][0] / tot[p][1])
            if len(reg) >= 5 and key in prev and g["stype"] == "2":
                pst, lm, pg = prev[key]
                top2 = reg[:2]
                mx = max(lm.get(p, 0) for p in top2)
                x = lsby.get(pg["id"])
                ot = bool(x and (lib.quarters(x.get("ls_h")) or []) and len(lib.quarters(x.get("ls_h")) or []) > 4)
                flag[(g["id"], t)] = {"mx": mx, "days": lib.days_between(pst, g["start"]), "ot": ot,
                                      "won": lib.won_g(pg, t), "margin": abs(pg["hs"] - pg["as"]),
                                      "short": sum(1 for p in reg[:5] if lm.get(p, 0) == 0),
                                      "wp": rec[key][0] / max(1, rec[key][0] + rec[key][1]),
                                      "avg": max(tot[p][0] / tot[p][1] for p in top2)}
        for t in (g["home"], g["away"]):
            rows = (bx.get(g["id"]) or {}).get(str(t)) or []
            lm = {}
            for r in rows:
                m = lib.num(r["st"].get("minutes"))
                if m:
                    lm[r["pid"]] = m
                    v = mins[(g["season"], t)][r["pid"]]
                    v[0] += m
                    v[1] += 1
            if lm:
                prev[(g["season"], t)] = (g["start"], lm, g)
            else:
                prev.pop((g["season"], t), None)
            rec[(g["season"], t)][0 if lib.won_g(g, t) else 1] += 1
    O = h.Out("s7b_nba_40_minutes_controls", T.LT, T.LH)
    O.p("S7b - NBA THE STAR'S 40-MINUTE NIGHT: THE CONTROLS (moneylines at ESPN's close unless said; 2018-26; train 2018-21 / held 2022-26)")
    for g in fin:
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = flag.get((g["id"], team)), flag.get((g["id"], opp))
            if not me:
                continue
            pr = lib.profit(won, lib.dec(o))
            dog = 100 <= o <= 350
            op = g["oh"] if side == "home" else g["oa"]
            m = lib.morning_side(mo, g["id"], side)
            if dog:
                O.add("BASE dog +100..+350", s, pr, o)
                mx = me["mx"]
                O.add(f"dose: the top-2 men's most minutes last game {'did not play' if mx == 0 else 'under 30' if mx < 30 else '30-35' if mx < 36 else '36-39' if mx < 40 else '40-41' if mx < 42 else '42-44' if mx < 45 else '45+'}", s, pr, o)
                if op and 100 <= op <= 350:
                    O.add("BASE dog at ESPN's OPEN", s, lib.profit(won, lib.dec(op)), op)
                if m and 100 <= m[0] <= 350:
                    O.add("BASE dog at the paid MORNING price", s, lib.profit(won, m[1]), m[0])
            if -200 <= o <= -101:
                O.add("BASE favorite -200..-101", s, pr, o)
            hot = me["mx"] >= 40
            if hot and dog:
                nm = "40+ dog"
                O.add(nm, s, pr, o)
                O.add(f"{nm}: last game went to OVERTIME" if me["ot"] else f"{nm}: last game ended in regulation", s, pr, o)
                d = me["days"]
                O.add(f"{nm}: " + ("back-to-back" if d <= 1.3 else "two nights ago" if d <= 2.3 else "3+ days ago"), s, pr, o)
                O.add(f"{nm}: " + ("WON that game" if me["won"] else "LOST that game"), s, pr, o)
                O.add(f"{nm}: " + ("that game within 5 points" if me["margin"] <= 5 else "that game by 6+"), s, pr, o)
                O.add(f"{nm}: " + ("a top-5 minutes man sat that game (short-handed)" if me["short"] >= 1 else "all top-5 minutes men played that game"), s, pr, o)
                O.add(f"{nm}: " + ("a .500+ team" if me["wp"] >= 0.5 else "a team under .500"), s, pr, o)
                O.add(f"{nm}: " + ("home" if side == "home" else "road"), s, pr, o)
                O.add(f"{nm}: " + ("+100..+150" if o <= 150 else "+151..+220" if o <= 220 else "+221..+350"), s, pr, o)
                O.add(f"{nm}: " + ("his usual is 36+ a game" if me["avg"] >= 36 else "his usual is under 36 a game"), s, pr, o)
                O.add(f"{nm}: " + ("Oct-Dec" if g["start"][5:7] in ("10", "11", "12") else "Jan-Apr"), s, pr, o)
                if op and 100 <= op <= 350:
                    O.add("40+ dog at ESPN's OPEN (2023-26)", s, lib.profit(won, lib.dec(op)), op)
                if m and 100 <= m[0] <= 350:
                    O.add("40+ dog at the paid MORNING price (2020-23)", s, lib.profit(won, m[1]), m[0])
                if not me["ot"] and d > 1.3:
                    O.add("40+ dog: regulation game, NOT a back-to-back", s, pr, o)
            if hot and -150 <= o <= -101:
                O.add("40+ small favorite -150..-101", s, pr, o)
                O.add("40+ small favorite: " + ("last game went to OVERTIME" if me["ot"] else "regulation"), s, pr, o)
            if hot and o < -150:
                O.add("40+ favorite past -150", s, pr, o)
            if th and th["mx"] >= 40 and not hot and -200 <= o <= -101:
                O.add("the favorite -200..-101 ACROSS a 40+ team", s, pr, o)
            if me["ot"] and me["mx"] < 40 and dog:
                O.add("control: dog off an OVERTIME game, no top-2 man at 40+", s, pr, o)
            if not hot and me["margin"] <= 5 and dog:
                O.add("control: dog off a game within 5 points, no top-2 man at 40+", s, pr, o)
    O.show()
    O.p("")
    for nm in ("40+ dog", "40+ dog: last game ended in regulation", "40+ dog: regulation game, NOT a back-to-back", "40+ dog: two nights ago",
               "40+ dog: all top-5 minutes men played that game", "control: dog off an OVERTIME game, no top-2 man at 40+",
               "control: dog off a game within 5 points, no top-2 man at 40+"):
        matched(O, nm, "BASE dog +100..+350")
    matched(O, "40+ dog at ESPN's OPEN (2023-26)", "BASE dog at ESPN's OPEN")
    matched(O, "40+ dog at the paid MORNING price (2020-23)", "BASE dog at the paid MORNING price")
    matched(O, "the favorite -200..-101 ACROSS a 40+ team", "BASE favorite -200..-101", fade=False)
    matched(O, "40+ small favorite -150..-101", "BASE favorite -200..-101")
    O.save()


if __name__ == "__main__":
    for a in sys.argv[1:] or ("nhl", "nba"):
        nhl() if a == "nhl" else nba()
