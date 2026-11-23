"""11/23 - THE BUG FIX'S SECOND CHECK: the other box reads the college hoops dog read stands on, with the non-D1
tune-ups in (as built) and out - the three-point NET (sports_ncaab_box.three_net: -1 on the dog, -2 on the -101..-250
favorite's read, -0.02 on the spread rank) and the shooting form (cold_shoot Jan-Mar / hot from three on the road, -1
each on the dog read). ESPN's close, D1-vs-D1 regular season, 2021-26 (train 2021-23 / held 2024-26).
python results/studies/daily_1123/s0b_three_net_d1.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_ncaab_box as nb  # noqa: E402

G = sd.load_games("ncaab")
fin = sm.finals(G, "ncaab")
D1 = sm.ncaab_d1(fin)
O = h.Out("s0b_three_net_d1", (2021, 2023), [2024, 2025, 2026])
O.p("S0b - THE THREE-POINT NET AND THE SHOOTING FORM ON D1 GAMES ONLY (2021-26; train 2021-23 / held 2024-26)")


def net(t, st, d1):
    by = nb._season_lines(G, nb.season_of(st), d1)[0]
    rows = [r for r in by.get(str(t)) or [] if r[0] < st]
    if len(rows) < nb.TP_NET_GAMES:
        return None
    tpm = sum(r[8]["tpm"] for r in rows)
    tpa = sum(r[8]["tpa"] for r in rows)
    otpm = sum(r[9]["tpm"] for r in rows)
    otpa = sum(r[9]["tpa"] for r in rows)
    if tpa < nb.TP_NET_TPA or otpa < nb.TP_NET_TPA:
        return None
    return tpm / tpa - otpm / otpa


def shoot(t, st, d1):
    by = nb._season_lines(G, nb.season_of(st), d1)[0]
    mine = [r[8] for r in by.get(str(t)) or [] if r[0] < st]
    if len(mine) < nb.SHOOT_LAST:
        return None

    def agg(ls):
        fgm = sum(b["fgm"] for b in ls)
        fga = sum(b["fga"] for b in ls)
        tpm = sum(b["tpm"] for b in ls)
        tpa = sum(b["tpa"] for b in ls)
        if not fga or not tpa or fga == tpa:
            return None
        return ((fgm + 0.5 * tpm) / fga, tpm / tpa, (fgm - tpm) / (fga - tpa))
    s_, l_ = agg(mine), agg(mine[-nb.SHOOT_LAST:])
    if not s_ or not l_:
        return None
    return {"cold": l_[0] - s_[0] <= nb.EFG_COLD, "hot_deep": l_[1] - s_[1] >= nb.TP_HOT and l_[2] - s_[2] < nb.TWO_NOT}


for g in fin:
    st = g["start"]
    s = lib.season(st)
    if s < 2021 or str(g.get("stype") or "2") != "2" or g["home"] not in D1 or g["away"] not in D1:
        continue
    mlh, mla = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, TypeError, ValueError):
        continue
    late = st[5:7] in ("01", "02", "03")
    neutral = str(g.get("neutral")) == "1"
    for side, t, od in (("home", g["home"], mlh), ("away", g["away"], mla)):
        na, nd = net(t, st, False), net(t, st, True)
        sa, sdd = shoot(t, st, False), shoot(t, st, True)
        a = lib.ats({"hs": hs, "as": as_, "sp": lib.num(g.get("spread_home")), "spho": lib.num(g.get("spread_home_odds")),
                     "spao": lib.num(g.get("spread_away_odds"))}, side) if g.get("spread_home") not in (None, "") else None
        pr = None
        if od and mlh and mla and hs != as_:
            pr = lib.profit((hs > as_) == (side == "home"), lib.dec(od))
        dog = pr is not None and 100 <= od <= 350
        fav = pr is not None and -250 <= od <= -101
        la, ld = na is not None and na >= nb.TP_NET_LUCKY - 1e-9, nd is not None and nd >= nb.TP_NET_LUCKY - 1e-9
        for nm, grp, val in (("lucky-from-three DOG", dog, pr), ("lucky-from-three FAVORITE -101..-250", fav, pr),
                             ("lucky-from-three SPREAD side", a is not None, a)):
            if not grp:
                continue
            O.add(f"{nm} | base", s, val)
            if la:
                O.add(f"{nm} | AS BUILT", s, val)
            if ld:
                O.add(f"{nm} | D1 GAMES ONLY", s, val)
            if la and not ld:
                O.add(f"{nm} | DROPPED by the re-cut", s, val)
            if ld and not la:
                O.add(f"{nm} | ADDED by the re-cut", s, val)
        for nm, grp, key in (("cold-shooting dog Jan-Mar", dog and late, "cold"),
                             ("hot-from-three road dog", dog and side == "away" and not neutral, "hot_deep")):
            if not grp:
                continue
            ca, cd = bool(sa and sa[key]), bool(sdd and sdd[key])
            O.add(f"{nm} | base", s, pr)
            if ca:
                O.add(f"{nm} | AS BUILT", s, pr)
            if cd:
                O.add(f"{nm} | D1 GAMES ONLY", s, pr)
            if ca and not cd:
                O.add(f"{nm} | DROPPED by the re-cut", s, pr)
            if cd and not ca:
                O.add(f"{nm} | ADDED by the re-cut", s, pr)
O.show()
O.save()
