"""11/20 daily study S6 - NHL: HOW HARD THE BACK-TO-BACK TEAM WAS WORKED LAST NIGHT (skater ice time, box scores 2021-26).
The Ducks 3u of 11/19 was the rested dog against a favorite on the second night; the built spot reads "played last
night" and nothing about the night itself. Cells (fixed before the run): the b2b team's top pair of defensemen averaged
25:00+ last night (heavy) / under 23:00 (light); last night went past regulation; last night was a 3+ goal game either
way (the bench got minutes). The b2b team's own moneyline and the RESTED side across it, at ESPN's close.
S10 rides here too: the rested team's own load - its 4th game in 6 nights is a tracker lead already (10/30), so the
new cut is the REST the rested side really had: 1 night off vs 2+ nights off against the b2b team."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_game as sg  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]
O = h.Out("s6_nhl_ice_load", TRAIN, HELD)


def toi(st, r):
    t = str(st.get("timeOnIce") or "")
    if ":" not in t or r.get("pos") == "G":
        return None
    m, s = t.split(":")[:2]
    try:
        return (r.get("pos") or "", int(m) + int(s) / 60)
    except ValueError:
        return None


box = lib.boxes("nhl", toi)
fin = sg.load("nhl")
tl = {}
for g in fin:
    s = g["season"]
    f = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        past = tl.get(team, [])
        if not past:
            continue
        x = past[-1]
        days = lib.days_between(x["start"], g["start"])
        d = {"days": days}
        if days < 1.3:
            ps = (box.get(x["id"]) or {}).get(team) or {}
            dm = sorted((v[1] for v in ps.values() if v[0] == "D"), reverse=True)
            if len(dm) >= 4:
                d["pair"] = (dm[0] + dm[1]) / 2
            d["ot"] = len(x["lh"]) > 3
            d["rout"] = abs(x["hs"] - x["as"]) >= 3
        f[side] = d
    if g["stype"] == "2" and g["season"] >= 2021 and g["mlh"] and g["mla"] and g["hs"] != g["as"] and len(f) == 2:
        hw = g["hs"] > g["as"]
        for side, o, won in (("home", g["mlh"], hw), ("away", g["mla"], not hw)):
            me, ot = f[side], f["away" if side == "home" else "home"]
            b = h.band(o)
            if not b:
                continue
            pr = lib.profit(won, lib.dec(o))
            names = ["ALL"]
            if ot["days"] < 1.3 and me["days"] >= 1.3:               # the rested side across a b2b team
                names.append("RESTED vs b2b")
                names.append("RESTED vs b2b | I had " + ("1 night off" if me["days"] < 2.3 else "2+ nights off"))
                if "pair" in ot:
                    names.append("RESTED vs b2b | their top D pair " + ("25:00+ last night" if ot["pair"] >= 25 else "under 23:00" if ot["pair"] < 23 else "23-25"))
                names.append("RESTED vs b2b | their game last night " + ("went past regulation" if ot.get("ot") else "ended in 60"))
                names.append("RESTED vs b2b | their game last night " + ("a 3+ goal game" if ot.get("rout") else "inside 2"))
            if me["days"] < 1.3 and ot["days"] >= 1.3:               # the b2b team itself
                names.append("ON the b2b")
                if "pair" in me:
                    names.append("ON the b2b | my top D pair " + ("25:00+ last night" if me["pair"] >= 25 else "under 23:00" if me["pair"] < 23 else "23-25"))
                names.append("ON the b2b | last night " + ("went past regulation" if me.get("ot") else "ended in 60"))
            for nm in names:
                O.add(f"{nm} | {b}", s, pr, o)
    tl.setdefault(g["home"], []).append(g)
    tl.setdefault(g["away"], []).append(g)
O.p("NHL 2021-26, ESPN's close; TRAIN 2021-23 / HELD 2024-26")
O.show(minn=20)
for k in sorted(O.c):
    nm, bd = k.rsplit(" | ", 1)
    if nm.count("|") and len(O.c[k]) >= 60:
        pool = nm.split(" | ")[0] + " | " + bd
        v, p = O.c[k], O.c[pool]
        O.placebo(k, pool, fade=sum(x[1] for x in v) / len(v) < sum(x[1] for x in p) / len(p))
O.save()
