"""S7. COLLEGE HOOPS SPREADS BEYOND THE STACK.
1. The live 1/2u spread-stack rule re-read (b5's stack, rebuilt here the same way) - by the number and the juice, so
   the play carries a price limit that the data backs.
2. The next layers, each alone and on top of the stack: ALTITUDE (the totals study: games at 4,600 ft+ score more -
   does the home team cover?), TEMPO mismatches (possessions from the team box), the TRAVEL cells (miles, time zones,
   the 3rd+ straight road game).
The 11/3 (B) side table (every D1 game, both sides; the closing spread at its own juice). Stack / tempo need the team
box: 2021-25, TRAIN 2021-22, HELD 2023-25. Altitude / travel: 2016-25, TRAIN 2016-21, HELD 2022-25.
   python s7_hoops.py"""
import os, pickle, statistics, sys
from collections import defaultdict
import lib2 as L
sys.path.insert(0, os.path.join(L.ROOT, "results", "studies", "fable_1111"))
import lib as FL                      # noqa: E402  (teambox)
import sports_data as sd              # noqa: E402
import sports_ncaab_box as nb         # noqa: E402

o = L.Out("s7")
rows = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
rows = [r for r in rows if 2016 <= r["season"] <= 2025 and r["stype"] == "2"]
rows.sort(key=lambda r: (r["start"], r["id"]))
GF = sd.load_games("ncaab")
box = nb.load_box()
tb = FL.teambox("ncaab")
byg = defaultdict(list)
order = []
for r in rows:
    if r["id"] not in byg:
        order.append(r["id"])
    byg[r["id"]].append(r)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def poss(t):
    try:
        fga = float(t["fieldGoalsMade-fieldGoalsAttempted"].split("-")[1])
        fta = float(t["freeThrowsMade-freeThrowsAttempted"].split("-")[1])
        return fga - float(t["offensiveRebounds"]) + float(t["totalTurnovers"]) + 0.475 * fta
    except (KeyError, ValueError, IndexError, TypeError):
        return None


st = defaultdict(lambda: {"m3": 0, "a3": 0, "om3": 0, "oa3": 0, "cm": [], "rb": [], "nb": 0, "pace": [], "home_elev": []})
feat = {}
for gid in order:
    pr = byg[gid]
    if len(pr) != 2:
        continue
    for r in pr:
        s = st[(r["season"], r["team"])]
        f = {"tp": None, "cm": None, "rb": None, "pace": None}
        if s["nb"] >= 5 and s["a3"] >= 60 and s["oa3"] >= 60:
            f["tp"] = s["m3"] / s["a3"] - s["om3"] / s["oa3"]
        if len(s["cm"]) >= 10:
            f["cm"] = statistics.mean(s["cm"])
        if len(s["rb"]) >= 5:
            f["rb"] = statistics.mean(s["rb"])
        if len(s["pace"]) >= 5:
            f["pace"] = statistics.mean(s["pace"])
        feat[(gid, r["team"])] = f
    b = box.get(gid)
    t = tb.get(gid) or {}
    pp = [poss(t.get(r["team"]) or {}) for r in pr]
    for r in pr:
        s = st[(r["season"], r["team"])]
        if r.get("sp") is not None:
            s["cm"].append(r["margin"] + r["sp"])
        if b and r["team"] in b and r["opp"] in b:
            s["nb"] += 1
            s["m3"] += b[r["team"]]["tpm"]; s["a3"] += b[r["team"]]["tpa"]
            s["om3"] += b[r["opp"]]["tpm"]; s["oa3"] += b[r["opp"]]["tpa"]
        try:
            s["rb"].append(float(t[r["team"]]["totalRebounds"]) - float(t[r["opp"]]["totalRebounds"]))
        except (KeyError, ValueError, TypeError):
            pass
        if pp[0] is not None and pp[1] is not None:
            s["pace"].append((pp[0] + pp[1]) / 2)

# each team's usual home floor elevation (the median of its home games - known from the schedule)
home_elev = defaultdict(list)
for gid in order:
    for r in byg[gid]:
        if r["venue"] == "home":
            e = fnum((GF.get(gid) or {}).get("elev"))
            if e is not None:
                home_elev[r["team"]].append(e)
HE = {t: statistics.median(v) for t, v in home_elev.items() if len(v) >= 5}


def atsp(r):
    x = r["margin"] + r["sp"]
    return None if x == 0 else ((L.dec(r.get("spodds") or -110) - 1) if x > 0 else -1.0)


def stack(gid, r, q):
    me, th = feat[(gid, r["team"])], feat[(gid, q["team"])]
    w = 0.0
    if me["tp"] is not None and me["tp"] >= 0.05:
        w -= 0.02
    if th["tp"] is not None and th["tp"] >= 0.05:
        w += 0.02
    if me["cm"] is not None and th["cm"] is not None:
        g = me["cm"] - th["cm"]
        w += -0.03 if g >= 3 else (0.03 if g <= -3 else 0)
    if me["rb"] is not None and th["rb"] is not None:
        rg = me["rb"] - th["rb"]
        w += 0.02 if rg >= 6 else (-0.02 if rg <= -6 else 0)
    if r["nd"] and r["venue"] == "away" and r.get("rank25"):
        w -= 0.03
    if r["nd"] and r["venue"] == "home" and r.get("orank25"):
        w += 0.03
    if r.get("top_out"):
        w -= 0.03
    if r.get("o_top_out"):
        w += 0.03
    return round(w, 3)


T1, T2, T3 = defaultdict(list), defaultdict(list), defaultdict(list)
for gid in order:
    pr = byg[gid]
    if len(pr) != 2 or pr[0].get("sp") is None:
        continue
    elev = fnum((GF.get(gid) or {}).get("elev"))
    for r, q in ((pr[0], pr[1]), (pr[1], pr[0])):
        a = atsp(r)
        if a is None:
            continue
        s = r["season"]
        od = r.get("spodds") or -110
        sp = r["sp"]
        home, away = r["venue"] == "home", r["venue"] == "away"

        # ---- 2016-25: altitude / travel ----
        def add2(k):
            T2[k].append((s, a))
        add2("base: every spread side")
        if elev is not None and home:
            if elev >= 1400:
                add2("ALTITUDE: home team on a 4,600 ft+ floor")
                ve = HE.get(q["team"])
                if ve is not None and ve < 900:
                    add2("   ... the visitor's own floor is under 3,000 ft")
                if ve is not None and ve >= 1200:
                    add2("   ... the visitor is a mountain team too")
                add2("   ... home favorite" if sp < 0 else "   ... home dog")
                add2("   ... Nov-Dec" if r["nd"] else "   ... Jan-Mar")
                if elev >= 1800:
                    add2("   ... 5,900 ft+ (Wyoming / Air Force / Colorado / N Arizona ...)")
            elif 1200 <= elev < 1400:
                add2("ALTITUDE: home team at 3,900-4,600 ft")
        if away:
            mi, tz, trip = r.get("miles") or 0, r.get("tzd") or 0, r.get("trip") or 0
            if mi >= 1000:
                add2("TRAVEL: road team 1,000+ miles from its last stop")
            if mi >= 1500:
                add2("TRAVEL: road team 1,500+ miles")
                add2("   ... 1,500+ as a dog" if sp > 0 else "   ... 1,500+ as a favorite")
            if tz >= 2:
                add2("TRAVEL: road team 2+ time zones EAST of its last stop")
            if tz <= -2:
                add2("TRAVEL: road team 2+ time zones WEST of its last stop")
            if trip >= 3:
                add2("TRAVEL: the 3rd+ straight road game")
                if not r["nd"]:
                    add2("   ... 3rd+ straight road game, Jan-Mar")
        if home and (q.get("miles") or 0) >= 1500 and (q.get("trip") or 0) >= 2:
            add2("home vs a team 1,500+ miles in, 2nd+ road stop")
        # ---- 2021-25: stack / tempo ----
        if s < 2021:
            continue

        def add1(k):
            T1[k].append((s, a))
        w = stack(gid, r, q)
        me, th = feat[(gid, r["team"])], feat[(gid, q["team"])]
        add1("base: every spread side 2021-25")
        if w >= 0.05:
            add1("STACK +0.05 or more (the live 1/2u rule)")
            add1("   stack: priced -112 or cheaper" if od >= -112 else "   stack: priced worse than -112")
            if od < -120:
                add1("   stack: priced worse than -120")
            a_ = abs(sp)
            add1(f"   stack: the number {'0-3' if a_ <= 3 else ('3.5-7' if a_ <= 7 else ('7.5-12' if a_ <= 12 else '12.5+'))} ({'dog' if sp > 0 else 'fav'})")
            if elev is not None and elev >= 1400:
                add1("   stack side in a game at 4,600 ft+ (" + ("home" if home else "visitor") + ")")
            if away and (r.get("miles") or 0) >= 1000:
                add1("   stack side is a road team 1,000+ miles in")
            if home and (q.get("miles") or 0) >= 1000:
                add1("   stack side at home vs a 1,000+ mile traveler")
        if w >= 0.06:
            add1("STACK +0.06 or more")
        if me["pace"] is not None and th["pace"] is not None:
            d = me["pace"] - th["pace"]
            for cut in (4, 7):
                if d >= cut:
                    add1(f"TEMPO: the faster team by {cut}+ possessions")
                    if cut == 4:
                        add1("   ... faster, as a favorite" if sp < 0 else "   ... faster, as a dog")
                        add1("   ... faster, at home" if home else "   ... faster, away / neutral")
                if d <= -cut:
                    add1(f"TEMPO: the slower team by {cut}+ possessions")
                    if cut == 4:
                        add1("   ... slower, as a favorite" if sp < 0 else "   ... slower, as a dog")
            if w >= 0.03 and d <= -4:
                add1("STACK +0.03+ AND the slower team by 4+")
            if w >= 0.03 and d >= 4:
                add1("STACK +0.03+ AND the faster team by 4+")
        if w >= 0.03 and home and elev is not None and elev >= 1400:
            add1("STACK +0.03+ AND at home at 4,600 ft+")
        # ---- the tempo fade as a NEW stack weight: the favorite 4+ possessions faster -0.02, the dog across it +0.02 ----
        if me["pace"] is not None and th["pace"] is not None:
            d = me["pace"] - th["pace"]
            tw = (-0.02 if (d >= 4 and sp < 0) else 0.0) + (0.02 if (d <= -4 and sp > 0) else 0.0)
            w2 = round(w + tw, 3)
            if tw < 0:
                T3["the favorite 4+ possessions faster (the fade side)"].append((s, a))
            if tw > 0:
                T3["the dog across a favorite 4+ faster"].append((s, a))
                for lo_, hi_ in ((0.5, 3), (3.5, 7), (7.5, 12), (12.5, 60)):
                    if lo_ <= sp <= hi_:
                        T3[f"   ... getting {lo_:g}-{hi_:g}"].append((s, a))
                T3["   ... at home" if home else "   ... away / neutral"].append((s, a))
                T3["   ... Nov-Dec" if r["nd"] else "   ... Jan-Mar"].append((s, a))
            for cut in (0.05, 0.06):
                if w2 >= cut:
                    T3[f"NEW STACK (with tempo) +{cut:.2f} or more"].append((s, a))
                if w2 >= cut and w < cut:
                    T3[f"   rows the tempo weight LIFTS to +{cut:.2f}"].append((s, a))
                if w >= cut and w2 < cut:
                    T3[f"   rows the tempo weight DROPS under +{cut:.2f}"].append((s, a))
                if w >= cut and w2 >= cut:
                    T3[f"   rows in both at +{cut:.2f}"].append((s, a))
            if w >= 0.05 and tw < 0:
                T3["old stack +0.05+ on a 4+ faster favorite"].append((s, a))
            if w >= 0.03 and tw > 0:
                T3["old stack +0.03+ on a dog across a 4+ faster favorite"].append((s, a))
            if w <= -0.03 and tw > 0:
                T3["old stack -0.03 or worse on a dog across a 4+ faster favorite"].append((s, a))
            if w == 0 and tw > 0:
                T3["old stack 0 on a dog across a 4+ faster favorite"].append((s, a))


def dump(T, split, title):
    o(f"\n== {title} ==")
    for k in T:
        r = T[k]
        if len(r) < 40:
            continue
        tr = [(s, p) for s, p in r if s <= split]
        he = [(s, p) for s, p in r if s > split]
        ut, uh = L.by_season(tr), L.by_season(he)
        o(f"   {k[:58]:58s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% ({ut[0]}/{ut[1]}) | HELD {L.st([p for _, p in he])} ({uh[0]}/{uh[1]} up: {uh[2]})")
    o(f"   cells: {len(T)}")


dump(T1, 2022, "THE STACK + TEMPO (2021-25; train 2021-22, held 2023-25)")
dump(T2, 2021, "ALTITUDE + TRAVEL (2016-25; train 2016-21, held 2022-25)")
dump(T3, 2022, "THE TEMPO FADE AS A STACK WEIGHT (2021-25; train 2021-22, held 2023-25)")
o.save()
