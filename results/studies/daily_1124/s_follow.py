"""11/24 daily studies - THE CONTROLS before a weight, for the three cells s_today.py left standing:
  S2b  NHL: the home side whose HOME margin lags its ROAD margin (bottom fifth home-minus-road split) - dog -18.3% on
       441, small favorite -9.7% on 541. The dose, which half carries it (a poor home margin or a rich road one),
       the road side across, the home-heavy home side against a team that travels, the price, ESPN's open (2023-26),
       the paid morning (2021-23), rest
  S1b  NBA: the home-heavy team (top fifth split) as a ROAD dog (-13.6% on 638; -25.6% on 307 with a winning margin)
       - the dose, the price, the favorite across, the open / the paid morning (2020-23)
  S9b  COLLEGE HOOPS: the DEEP team (bottom fifth share of minutes on its top 5) on the second day of a back-to-back,
       ATS -27.4% on 276 - the dose, neutral / not, the month, favorite / dog, the side across, the 11/1 consolation
       cell apart (off a 15+ loss), the same team on its FIRST day, and a second definition of depth
Placebos are PRICE-MATCHED (the same number of sides out of each 50-cent price bin of the pool).
python results/studies/daily_1124/s_follow.py [nhl nba s9]"""
import bisect
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
from core import ranked, LT, LH, BT, BH  # noqa: E402


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


def split_reads(lg, since=2018, cap=None):
    cap = cap or (6.0 if lg == "nhl" else 30.0)
    allf = [g for g in lib.all_finals(lg) if g["season"] >= since and g["stype"] == "2"]

    def counters(g, t, o):
        home = g["home"] == t
        m = max(-cap, min(cap, (g["hs"] - g["as"]) * (1 if home else -1)))
        nb = g.get("neutral")
        return {"h_n": 0.0 if (not home or nb) else 1.0, "h_m": m if (home and not nb) else 0.0,
                "r_n": 0.0 if (home or nb) else 1.0, "r_m": m if (not home and not nb) else 0.0, "m": m}

    def feats(s, n):
        if s["h_n"] < 6 or s["r_n"] < 6:
            return None
        return {"split": s["h_m"] / s["h_n"] - s["r_m"] / s["r_n"], "hm": s["h_m"] / s["h_n"], "rm": s["r_m"] / s["r_n"],
                "all": s["m"] / n}
    rk = ranked(allf, counters, feats, 15)
    last = {}
    rest = {}
    for g in allf:
        for t in (g["home"], g["away"]):
            if (g["season"], t) in last:
                rest[(g["id"], t)] = lib.days_between(last[(g["season"], t)], g["start"])
            last[(g["season"], t)] = g["start"]
    return rk, rest


def q5(p):
    return min(4, int(p * 5))


Q = ["bottom fifth", "20-40", "40-60", "60-80", "top fifth"]


def ml_cells(O, tag, s, o, pr):
    if -200 <= o <= 350:
        O.add(f"{tag}: any price -200..+350", s, pr, o)
    if 100 <= o <= 350:
        O.add(f"{tag}: dog +100..+350", s, pr, o)
    if -150 <= o <= -101:
        O.add(f"{tag}: small fav -150..-101", s, pr, o)
    if -200 <= o <= -101:
        O.add(f"{tag}: fav -200..-101", s, pr, o)


def nhl():
    rk, rest = split_reads("nhl")
    fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2018 and not g.get("neutral")]
    mo = lib.nhl_morning()
    O = h.Out("s2b_nhl_split_controls", LT, LH)
    O.p("S2b - NHL: THE HOME SIDE WHOSE HOME MARGIN LAGS ITS ROAD MARGIN - the controls (2018-26; train 2018-21 / held 2022-26)")
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if not a or not b:
            continue
        s = g["season"]
        hw = g["hs"] > g["as"]
        oh, oa = g["mlh"], g["mla"]
        ph, pa = lib.profit(hw, lib.dec(oh)), lib.profit(not hw, lib.dec(oa))
        ml_cells(O, "POOL home side", s, oh, ph)
        ml_cells(O, "POOL road side", s, oa, pa)
        ml_cells(O, f"DOSE home side, its split {Q[q5(a['split'][1])]}", s, oh, ph)
        ml_cells(O, f"DOSE road side, its split {Q[q5(b['split'][1])]}", s, oa, pa)
        bad = a["split"][1] <= 0.2
        if bad:
            ml_cells(O, "HOME side, bottom fifth split", s, oh, ph)
            ml_cells(O, "ROAD side ACROSS a bottom fifth split home team", s, oa, pa)
            ml_cells(O, "HOME side, bottom fifth split, " + ("its HOME margin under the league middle" if a["hm"][1] < 0.5 else "its home margin over the league middle"), s, oh, ph)
            ml_cells(O, "HOME side, bottom fifth split, " + ("a winning margin overall" if a["all"][1] >= 0.5 else "outscored overall"), s, oh, ph)
            r = rest.get((g["id"], g["home"]))
            if r is not None:
                ml_cells(O, "HOME side, bottom fifth split, " + ("on a back-to-back" if r <= 1.3 else "not on a back-to-back"), s, oh, ph)
            if g["oh"]:
                ml_cells(O, "HOME side, bottom fifth split - at ESPN's OPEN", s, g["oh"], lib.profit(hw, lib.dec(g["oh"])))
            m = lib.morning_side(mo, g["id"], "home")
            if m:
                ml_cells(O, "HOME side, bottom fifth split - at the paid MORNING", s, m[0], lib.profit(hw, m[1]))
        if g["oh"]:
            ml_cells(O, "POOL home side - at ESPN's OPEN", s, g["oh"], lib.profit(hw, lib.dec(g["oh"])))
        m = lib.morning_side(mo, g["id"], "home")
        if m:
            ml_cells(O, "POOL home side - at the paid MORNING", s, m[0], lib.profit(hw, m[1]))
        if a["hm"][1] <= 0.2:
            ml_cells(O, "PART home side, bottom fifth HOME margin alone", s, oh, ph)
        if a["rm"][1] >= 0.8:
            ml_cells(O, "PART home side, top fifth ROAD margin alone", s, oh, ph)
        if a["split"][1] >= 0.8 and b["split"][1] <= 0.2:
            ml_cells(O, "HOME-HEAVY home side vs a bottom fifth split road team", s, oh, ph)
            ml_cells(O, "ROAD side, bottom fifth split, AT a home-heavy team", s, oa, pa)
        if b["split"][1] >= 0.8:
            ml_cells(O, "ROAD side, top fifth split (home-heavy on the road)", s, oa, pa)
        if b["split"][1] <= 0.2:
            ml_cells(O, "ROAD side, bottom fifth split (travels well, on the road)", s, oa, pa)
    O.show()
    O.p("")
    for band in ("any price -200..+350", "dog +100..+350", "small fav -150..-101", "fav -200..-101"):
        matched(O, f"HOME side, bottom fifth split: {band}", f"POOL home side: {band}")
        matched(O, f"ROAD side ACROSS a bottom fifth split home team: {band}", f"POOL road side: {band}", fade=False)
        matched(O, f"HOME-HEAVY home side vs a bottom fifth split road team: {band}", f"POOL home side: {band}", fade=False)
        matched(O, f"HOME side, bottom fifth split - at ESPN's OPEN: {band}", f"POOL home side - at ESPN's OPEN: {band}")
        matched(O, f"HOME side, bottom fifth split - at the paid MORNING: {band}", f"POOL home side - at the paid MORNING: {band}")
        matched(O, f"PART home side, bottom fifth HOME margin alone: {band}", f"POOL home side: {band}")
        matched(O, f"PART home side, top fifth ROAD margin alone: {band}", f"POOL home side: {band}")
    O.save()


def nba():
    rk, rest = split_reads("nba")
    fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["season"] >= 2018 and not g.get("neutral")]
    mo = lib.nba_morning()
    O = h.Out("s1b_nba_split_controls", LT, LH)
    O.p("S1b - NBA: THE HOME-HEAVY TEAM ON THE ROAD - the controls (2018-26; train 2018-21 / held 2022-26)")
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if not a or not b:
            continue
        s = g["season"]
        hw = g["hs"] > g["as"]
        oh, oa = g["mlh"], g["mla"]
        ph, pa = lib.profit(hw, lib.dec(oh)), lib.profit(not hw, lib.dec(oa))
        ml_cells(O, "POOL home side", s, oh, ph)
        ml_cells(O, "POOL road side", s, oa, pa)
        ml_cells(O, f"DOSE road side, its split {Q[q5(b['split'][1])]}", s, oa, pa)
        ml_cells(O, f"DOSE home side, its split {Q[q5(a['split'][1])]}", s, oh, ph)
        if b["split"][1] >= 0.8:
            ml_cells(O, "ROAD side, top fifth split", s, oa, pa)
            ml_cells(O, "HOME side ACROSS a home-heavy road team", s, oh, ph)
            ml_cells(O, "ROAD side, top fifth split, " + ("a winning margin overall" if b["all"][1] >= 0.5 else "outscored overall"), s, oa, pa)
            ml_cells(O, "ROAD side, top fifth split, " + ("its ROAD margin under the league middle" if b["rm"][1] < 0.5 else "its road margin over the league middle"), s, oa, pa)
            r = rest.get((g["id"], g["away"]))
            if r is not None:
                ml_cells(O, "ROAD side, top fifth split, " + ("on a back-to-back" if r <= 1.3 else "not on a back-to-back"), s, oa, pa)
            if g["oa"]:
                ml_cells(O, "ROAD side, top fifth split - at ESPN's OPEN", s, g["oa"], lib.profit(not hw, lib.dec(g["oa"])))
            m = lib.morning_side(mo, g["id"], "away")
            if m:
                ml_cells(O, "ROAD side, top fifth split - at the paid MORNING", s, m[0], lib.profit(not hw, m[1]))
        if g["oa"]:
            ml_cells(O, "POOL road side - at ESPN's OPEN", s, g["oa"], lib.profit(not hw, lib.dec(g["oa"])))
        m = lib.morning_side(mo, g["id"], "away")
        if m:
            ml_cells(O, "POOL road side - at the paid MORNING", s, m[0], lib.profit(not hw, m[1]))
        if b["rm"][1] <= 0.2:
            ml_cells(O, "PART road side, bottom fifth ROAD margin alone", s, oa, pa)
        if b["hm"][1] >= 0.8:
            ml_cells(O, "PART road side, top fifth HOME margin alone", s, oa, pa)
        if a["split"][1] <= 0.2:
            ml_cells(O, "HOME side, bottom fifth split", s, oh, ph)
        if a["split"][1] >= 0.8:
            ml_cells(O, "HOME side, top fifth split", s, oh, ph)
    O.show()
    O.p("")
    for band in ("any price -200..+350", "dog +100..+350", "small fav -150..-101", "fav -200..-101"):
        matched(O, f"ROAD side, top fifth split: {band}", f"POOL road side: {band}")
        matched(O, f"ROAD side, top fifth split, a winning margin overall: {band}", f"POOL road side: {band}")
        matched(O, f"HOME side ACROSS a home-heavy road team: {band}", f"POOL home side: {band}", fade=False)
        matched(O, f"ROAD side, top fifth split - at ESPN's OPEN: {band}", f"POOL road side - at ESPN's OPEN: {band}")
        matched(O, f"ROAD side, top fifth split - at the paid MORNING: {band}", f"POOL road side - at the paid MORNING: {band}")
        matched(O, f"PART road side, bottom fifth ROAD margin alone: {band}", f"POOL road side: {band}")
    O.save()


def depth_reads():
    """{(gid, team): (top-5 share of the team's minutes so far, its league place that night, days since its last
    game, that game's margin, men at 10+ minutes a team game, that count's league place, boxed games)}, the priced finals."""
    fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2021]
    bx = lib.box_rows("ncaab")
    mins = defaultdict(lambda: defaultdict(float))
    gms = defaultdict(int)
    prev = {}                                            # (season, team) -> (start, margin) of its last game
    read, latest, latest8 = {}, defaultdict(dict), defaultdict(dict)
    for g in allf:
        s = g["season"]
        cur, cur8 = {}, {}
        for t in (g["home"], g["away"]):
            key = (s, t)
            tot = mins[key]
            if gms[key] >= 4 and sum(tot.values()) > 0:
                tv = sum(tot.values())
                cur[t] = sum(sorted(tot.values(), reverse=True)[:5]) / tv
                cur8[t] = sum(1 for v in tot.values() if v / gms[key] >= 10.0)     # men at 10+ minutes a team game
                latest[s][t], latest8[s][t] = cur[t], cur8[t]
        vals = latest[s]
        if len(vals) >= 100:
            srt, srt8 = sorted(vals.values()), sorted(latest8[s].values())
            for t, v in cur.items():
                pv = prev.get((s, t))
                read[(g["id"], t)] = (v, bisect.bisect_left(srt, v) / (len(srt) - 1),
                                      lib.days_between(pv[0], g["start"]) if pv else 99.0, pv[1] if pv else None,
                                      cur8[t], bisect.bisect_right(srt8, cur8[t]) / len(srt8), gms[(s, t)])
        for t in (g["home"], g["away"]):
            rows = (bx.get(g["id"]) or {}).get(str(t)) or []
            got = False
            for r in rows:
                m = lib.num(r["st"].get("minutes"))
                if m:
                    mins[(s, t)][r["pid"]] += m
                    got = True
            if got:
                gms[(s, t)] += 1
            prev[(s, t)] = (g["start"], (g["hs"] - g["as"]) * (1 if g["home"] == t else -1))
    return read, fin


def s9():
    read, fin = depth_reads()
    O = h.Out("s9b_ncaab_depth_controls", BT, BH)
    O.p("S9b - COLLEGE HOOPS: THE DEEP TEAM ON THE SECOND DAY - the controls (the player box 2021-26; train 2021-23 / held 2024-26)")
    for g in fin:
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = read.get((g["id"], team)), read.get((g["id"], opp))
            at = lib.ats(g, side)
            pr = lib.profit(won, lib.dec(o))
            if not me:
                continue
            b2b = me[2] <= 1.3
            mon = "Nov-Dec" if g["start"][5:7] in ("11", "12") else "Jan-Mar"
            if b2b:
                O.add("POOL any team on the second day: ATS", s, at)
                O.add(f"DOSE second day, top-5 share {Q[q5(me[1])]}: ATS", s, at)
                O.add(f"DOSE second day, men at 10+ minutes: {'10+' if me[4] >= 10 else '9' if me[4] == 9 else '8' if me[4] == 8 else '7 or fewer'}: ATS", s, at)
                if 100 <= o <= 350:
                    O.add("POOL any team on the second day: dog +100..+350", s, pr, o)
            if th and th[2] <= 1.3 and th[1] <= 0.2:
                O.add("ACROSS a deep team on its second day: ATS", s, at)
                if 100 <= o <= 350:
                    O.add("ACROSS a deep team on its second day: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add("ACROSS a deep team on its second day: small fav -150..-101", s, pr, o)
                if not b2b:
                    O.add("ACROSS a deep team on its second day, we are rested: ATS", s, at)
                else:
                    O.add("ACROSS a deep team on its second day, our second day too: ATS", s, at)
            if me[1] <= 0.2:
                if not b2b and g["neutral"] and mon == "Nov-Dec":
                    O.add("CONTROL deep team, neutral floor Nov-Dec, NOT on the second day: ATS", s, at)
                if 1.3 < me[2] <= 2.3:
                    O.add("CONTROL deep team, one day off: ATS", s, at)
                if b2b:
                    O.add("DEEP second day: ATS", s, at)
                    O.add(f"DEEP second day, {'neutral floor' if g['neutral'] else 'home' if side == 'home' else 'road'}: ATS", s, at)
                    O.add(f"DEEP second day, {mon}: ATS", s, at)
                    sp = g["sp"] if side == "home" else (-g["sp"] if g["sp"] is not None else None)
                    if sp is not None:
                        O.add(f"DEEP second day, {'laying points' if sp < 0 else 'getting points'}: ATS", s, at)
                        O.add(f"DEEP second day, the number {'inside 6' if abs(sp) < 6 else '6 or more'}: ATS", s, at)
                    if me[3] is not None:
                        O.add(f"DEEP second day, {'off a 15+ loss (the 11/1 cell)' if me[3] <= -15 else 'off a win' if me[3] > 0 else 'off a loss under 15'}: ATS", s, at)
                    O.add(f"DEEP second day, {'4-7 boxed games' if me[6] <= 7 else '8+ boxed games'}: ATS", s, at)
                    if th:
                        O.add(f"DEEP second day, the other side {'on its second day too' if th[2] <= 1.3 else 'rested'}: ATS", s, at)
                    if 100 <= o <= 350:
                        O.add("DEEP second day: dog +100..+350", s, pr, o)
                    if -400 <= o <= -101:
                        O.add("DEEP second day: fav -400..-101", s, pr, o)
                    O.add("DEEP second day: the game's UNDER", s, lib.tot_profit(g, False))
            if b2b and me[5] >= 0.8:
                O.add("DEEP by the count (top fifth men at 10+ minutes), second day: ATS", s, at)
            if b2b and me[1] > 0.2:
                O.add("NOT deep, second day: ATS", s, at)
    O.show()
    O.p("")
    O.placebo("DEEP second day: ATS", "POOL any team on the second day: ATS", fade=True)
    O.placebo("ACROSS a deep team on its second day: ATS", "POOL any team on the second day: ATS", fade=False)
    matched(O, "DEEP second day: dog +100..+350", "POOL any team on the second day: dog +100..+350")
    O.save()


if __name__ == "__main__":
    for a in sys.argv[1:] or ("nhl", "nba", "s9"):
        {"nhl": nhl, "nba": nba, "s9": s9}[a]()
