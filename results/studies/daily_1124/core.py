"""11/24 daily studies - the shared cell machinery (copied from daily_1123/s_today.py: teambox / ranked / cells / hi / lo)."""
import glob
import json
import os
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

BT, BH = (2021, 2023), [2024, 2025, 2026]            # the box seasons
LT, LH = (2018, 2021), [2022, 2023, 2024, 2025, 2026]  # the line-score seasons


def teambox(lg):
    out = {}
    for f in [os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")] + sorted(glob.glob(os.path.join(sd.DATA, "teamstats", lg, "*.jsonl"))):
        if not os.path.exists(f):
            continue
        for ln in open(f):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            out[r["gid"]] = r["teams"]
    return out


def ranked(allf, counters, feats, minn, window=None, minteams=20):
    """{(gid, team): {feat: (value, league pct)}} - each team's features from its earlier games this season (the last
    `window` when given), ranked among every team's current value that night."""
    hist = defaultdict(lambda: deque(maxlen=window))
    latest = defaultdict(dict)
    out = {}
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            rows = hist[(s, t)]
            if len(rows) >= minn:
                sums = defaultdict(float)
                for r in rows:
                    for k, v in r.items():
                        sums[k] += v
                f = feats(sums, len(rows))
                if f:
                    cur[t] = f
                    latest[s][t] = f
        vals = latest[s]
        if len(vals) >= minteams:
            for t, f in cur.items():
                out[(g["id"], t)] = {k: (f[k], sum(1 for x in vals.values() if x[k] < f[k]) / (len(vals) - 1)) for k in f}
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            c = counters(g, t, o)
            if c:
                hist[(s, t)].append(c)
    return out


def cells(O, fin, rk, flags, totals=(), need_both=True):
    """flags(me, them, side, g) -> [tags]; every tag gets ATS / dog / small fav / fav past -150 cells + the BASE."""
    n = 0
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if need_both and (not a or not b):
            continue
        n += 1
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(g, side)
            for tag in ["BASE"] + list(flags(me, th, side, g)):
                O.add(f"{tag}: ATS", s, at)
                if 100 <= o <= 350:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
                if o < -150:
                    O.add(f"{tag}: fav past -150", s, pr, o)
        for name, cond in [("BASE every game", lambda x, y: True)] + list(totals):
            if cond(a, b):
                O.add(f"TOTAL {name}: over", s, lib.tot_profit(g, True))
                O.add(f"TOTAL {name}: under", s, lib.tot_profit(g, False))
    O.p(f"priced games read: {n}")
    res = O.show()
    O.p("")
    for k, r in res.items():
        if k.startswith("BASE") or k.startswith("TOTAL BASE") or not r or r["all"]["n"] < 100 or not r["train"] or not r["held_all"]:
            continue
        kind = k.rsplit(": ", 1)[1]
        base = ("TOTAL BASE every game: " if k.startswith("TOTAL") else "BASE: ") + kind
        b = res.get(base)
        if not b:
            continue
        d = r["all"]["roi"] - b["all"]["roi"]
        if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
            O.placebo(k, base, fade=d < 0)
    O.p(f"cells: {len(res)}")
    O.save()


def hi(x, k, q=0.8):
    return x[k][1] >= q


def lo(x, k, q=0.2):
    return x[k][1] <= q


