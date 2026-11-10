"""S5 / S10 - NHL: THE TOP GOAL SCORER'S RUN, and TOP-HEAVY SCORING (never studied: the NHL work read goalies, shots,
puck luck, periods, rest - never a skater's own goal run or how the goals are spread; checked against every
'Not re-run' list).
From the box scores (forwards + defensemen, 2021-26), this season before tonight, 10+ team games:
  S5 the team's top goal scorer (most goals, 5+ of them) - COLD = no goal in his last 6+ games played (he dressed),
     HOT = a goal in each of his last 3+ games; the side and the side across it.
  S10 TOP-HEAVY = its top 2 goal scorers hold 40%+ of its skater goals (DEEP = under 25%).
Cells: favorite -101..-250 / dog +100..+350 at the close, ESPN's open as the second price (2023-26), and the paid
NHL morning look (2021-23) where it exists. TRAIN 2021-22, HELD 2023 / 2024 / 2025 apart, 2026 live."""
from collections import Counter, defaultdict

import lib

TRAIN, HELD = (2021, 2022), [2023, 2024, 2025, 2026]
C = lib.Cells()
mo = lib.nhl_morning()


def add_side(tag, g, side, o, won, s):
    p = lib.profit(won, lib.dec(o))
    if -250 <= o <= -101:
        C.add(f"{tag} | fav -101..-250", s, p)
    if 100 <= o <= 350:
        C.add(f"{tag} | dog +100..+350", s, p)
    oo = g["oh"] if side == "home" else g["oa"]
    if oo:
        if -250 <= oo <= -101:
            C.add(f"{tag} | fav OPEN", s, lib.profit(won, lib.dec(oo)))
        if 100 <= oo <= 350:
            C.add(f"{tag} | dog OPEN", s, lib.profit(won, lib.dec(oo)))
    m = lib.morning_side(mo, g["id"], side)
    if m:
        if -250 <= m[0] <= -101:
            C.add(f"{tag} | fav MORNING", s, lib.profit(won, m[1]))
        if 100 <= m[0] <= 350:
            C.add(f"{tag} | dog MORNING", s, lib.profit(won, m[1]))


def bare(x):
    return str(x).split(":")[-1]


rows = lib.box_rows("nhl")
goals = {}                        # (gid, team) -> {pid: goals} for skaters who dressed
for gid, tm in rows.items():
    for t, rs in tm.items():
        d = {}
        for r in rs:
            if r["group"] in ("forwards", "defenses"):
                v = lib.num(r["st"].get("goals"))
                if v is not None:
                    d[r["pid"]] = int(v)
        if d:
            goals[(bare(gid), bare(t))] = d
fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2021]
tl = lib.team_log([g for g in lib.all_finals("nhl") if g["stype"] == "2"])
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
        logs = [goals.get((bare(x["id"]), bare(team))) for x in prev]
        logs = [x for x in logs if x]
        if len(logs) < 10:
            continue
        tot = Counter()
        for d in logs:
            tot.update(d)
        s = g["season"]
        oside = "away" if side == "home" else "home"
        oo = g["mla"] if side == "home" else g["mlh"]
        all_g = sum(tot.values())
        top = tot.most_common(2)
        # S10 top-heavy
        if all_g >= 20 and len(top) == 2:
            share = (top[0][1] + top[1][1]) / all_g
            lab = "TOP-HEAVY (top 2 = 40%+ of goals)" if share >= 0.40 else "DEEP (top 2 under 25%)" \
                if share < 0.25 else "middle (25-40%)"
            add_side(f"S10 {lab}", g, side, o, won, s)
            add_side(f"S10x facing {lab}", g, oside, oo, not won, s)
        # S5 the top scorer's run
        star, n = top[0]
        if n < 5:
            continue
        played = [d[star] for d in logs if star in d]
        cold = 0
        for v in reversed(played):
            if v:
                break
            cold += 1
        hot = 0
        for v in reversed(played):
            if not v:
                break
            hot += 1
        if cold >= 6:
            add_side("S5 top scorer COLD (no goal in his last 6+)", g, side, o, won, s)
            add_side("S5x facing a top scorer gone cold 6+", g, oside, oo, not won, s)
            if cold >= 9:
                add_side("S5 top scorer COLD 9+", g, side, o, won, s)
        elif hot >= 3:
            add_side("S5 top scorer HOT (a goal in 3+ straight)", g, side, o, won, s)
            add_side("S5x facing a top scorer hot 3+", g, oside, oo, not won, s)
        else:
            add_side("S5 control: the top scorer neither", g, side, o, won, s)
C.dump("s5_s10", "S5 / S10 NHL - the top goal scorer's run / top-heavy scoring; close + ESPN open + the paid morning; "
       "TRAIN 2021-22", TRAIN, HELD)
