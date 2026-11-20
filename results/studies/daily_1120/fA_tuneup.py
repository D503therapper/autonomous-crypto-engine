"""11/20 follow-up A (S9 + the board check's question, S1) - COLLEGE HOOPS: THE GAME AFTER A NON-D1 TUNE-UP.
A Division I team whose LAST game was against a non-D1 school (sm.ncaab_d1 - no price on that game, the ratings never
see it), tonight against a D1 team. ESPN's close at its own juice, the open as the second price (2023-26), by month,
site, the opponent's last game, the tune-up's margin and the rest; a month-matched placebo. Then S1: the built "top
scorer missed the last game" weight when the game he missed was the tune-up (box scores 2021-26)."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_game as sg  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025, 2026]
O = h.Out("fA_tuneup", TRAIN, HELD)
raw = sd.load_games("ncaab")
allf = sm.finals(raw, "ncaab")
d1 = sm.ncaab_d1(allf)
fin = sg.load("ncaab")
tl = {}
rows = []
for g in fin:
    s = g["season"]
    f = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        past = [x for x in tl.get(team, []) if x["season"] == s]
        if past:
            x = past[-1]
            o_ = x["away"] if x["home"] == team else x["home"]
            mar = (x["hs"] - x["as"]) * (1 if x["home"] == team else -1)
            f[side] = {"tune": str(o_) not in d1, "mar": mar, "days": lib.days_between(x["start"], g["start"]), "n": len(past),
                       "tunes": sum(1 for y in past if str(y["away"] if y["home"] == team else y["home"]) not in d1)}
    if g["stype"] == "2" and g["mlh"] and g["mla"] and g["hs"] != g["as"] and str(g["home"]) in d1 and str(g["away"]) in d1 \
            and "home" in f and "away" in f:
        rows.append((g, f))
    tl.setdefault(g["home"], []).append(g)
    tl.setdefault(g["away"], []).append(g)

gr = raw
pool_dog = {}
for g, f in rows:
    s, hw = g["season"], g["hs"] > g["as"]
    mth = g["start"][5:7]
    r0 = gr.get(g["id"]) or {}
    oh, oa = lib.num(r0.get("ml_home_open")), lib.num(r0.get("ml_away_open"))
    for side, o, won, op in (("home", g["mlh"], hw, oh), ("away", g["mla"], not hw, oa)):
        me, ot = f[side], f["away" if side == "home" else "home"]
        b = h.band(o)
        pr = lib.profit(won, lib.dec(o))
        at = lib.ats(g, side)
        site = "neutral" if g["neutral"] else side
        base = [f"ALL", f"ALL month {mth if mth in ('11', '12') else 'Jan+'}"]
        names = []
        if me["tune"] and not ot["tune"]:
            names.append("TUNE vs a team off a D1 game")
            names.append(f"TUNE vs D1 | month {mth if mth in ('11', '12') else 'Jan+'}")
            names.append(f"TUNE vs D1 | {site}")
            names.append(f"TUNE vs D1 | won the tune-up by {'30+' if me['mar'] >= 30 else 'under 30' if me['mar'] > 0 else 'LOST it'}")
            names.append(f"TUNE vs D1 | rest {'1-2 days' if me['days'] < 2.6 else '3-4' if me['days'] < 4.6 else '5+'}")
            names.append(f"TUNE vs D1 | the opponent {'won' if ot['mar'] > 0 else 'lost'} its D1 game")
            names.append(f"TUNE vs D1 | games in {'1-3' if me['n'] <= 3 else '4-8' if me['n'] <= 8 else '9+'}")
        if me["tune"] and ot["tune"]:
            names.append("BOTH off a tune-up")
        if not me["tune"] and ot["tune"]:
            names.append("MIRROR: off a D1 game vs a team off a tune-up")
        for nm in base + names:
            if b:
                O.add(f"{nm} | {b}", s, pr, o)
            if at is not None:
                O.add(f"{nm} | ats", s, at)
            if o >= 100:
                O.add(f"{nm} | any dog", s, pr, o)
            if o <= -101:
                O.add(f"{nm} | any fav", s, pr, o)
            if b == "dog" and op and 100 <= op <= 350:
                O.add(f"{nm} | dog AT THE OPEN", s, lib.profit(won, lib.dec(op)), op)
        if b == "dog":
            pool_dog.setdefault((mth, int(o // 50)), []).append(pr)
            if me["tune"] and not ot["tune"]:
                pool_dog.setdefault("cell", []).append((mth, int(o // 50), pr))
O.p(f"college hoops D1-vs-D1 priced regular-season games with both teams' last game on file: {len(rows)}")
O.show(minn=25)
# the month + price matched placebo (dogs)
cell = pool_dog.pop("cell")
got = sum(p for _, _, p in cell) / len(cell)
rnd = random.Random(11)
hit = 0
for _ in range(2000):
    tot = sum(rnd.choice(pool_dog[(m, b)]) for m, b, _ in cell)
    hit += tot / len(cell) >= got
O.p(f"MONTH + PRICE matched placebo, the tune-up dog ({len(cell)} bets, {got*100:+.1f}%): {hit} of 2000 random same-month same-price dogs did as well")
for a, b_ in (("TUNE vs a team off a D1 game | ats", "ALL month 11 | ats"), ("TUNE vs a team off a D1 game | dog", "ALL month 11 | dog"),
              ("TUNE vs a team off a D1 game | fav", "ALL | fav"), ("MIRROR: off a D1 game vs a team off a tune-up | ats", "ALL | ats"),
              ("MIRROR: off a D1 game vs a team off a tune-up | fav", "ALL | fav")):
    v, p = O.c[a], O.c[b_]
    O.placebo(a, b_, fade=sum(x[1] for x in v) / len(v) < sum(x[1] for x in p) / len(p))

# ---- S1: the top scorer who missed the last game - when that game was the tune-up (box scores 2021-26)
O.p("")
O.p("S1 - THE TOP SCORER MISSED THE LAST GAME (sports_ncaab_roster.top_out, the live rule): the game he missed a tune-up or a D1 game")
import sports_ncaab_roster as nr  # noqa: E402
P = h.Out("fA_topout", (2021, 2023), [2024, 2025, 2026])
n = 0
for g, f in rows:
    if g["season"] < 2021:
        continue
    hw = g["hs"] > g["as"]
    for side, o, won in (("home", g["mlh"], hw), ("away", g["mla"], not hw)):
        other = "away" if side == "home" else "home"
        try:
            to = nr.top_out(raw, g[other], g["start"])
            mine = nr.top_out(raw, g[side], g["start"])
        except Exception:  # noqa: BLE001
            continue
        if to is None:
            continue
        n += 1
        at = lib.ats(g, side)
        b = h.band(o)
        pr = lib.profit(won, lib.dec(o))
        nm = ["ALL"]
        if to["out"] and not (mine and mine["out"]):
            nm.append("ACROSS a top scorer who missed the last game")
            nm.append("ACROSS ... the game he missed was " + ("a non-D1 TUNE-UP" if f[other]["tune"] else "a D1 game"))
        for k in nm:
            if at is not None:
                P.add(f"{k} | ats", g["season"], at)
            if b:
                P.add(f"{k} | {b}", g["season"], pr, o)
P.lines = O.lines
P.p(f"sides with a known answer: {n}; TRAIN 2021-23 / HELD 2024-26")
P.show(minn=20)
for a in ("ACROSS ... the game he missed was a non-D1 TUNE-UP | ats", "ACROSS ... the game he missed was a D1 game | ats"):
    if a in P.c:
        v, p = P.c[a], P.c["ALL | ats"]
        P.placebo(a, "ALL | ats", fade=sum(x[1] for x in v) / len(v) < sum(x[1] for x in p) / len(p))
O.save()
