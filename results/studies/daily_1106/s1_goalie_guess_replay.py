"""S1 - NHL: THE MORNING GOALIE GUESS, THE REPLAY CHECK (11/5 study 3's next step). When no starter is confirmed /
likely (sports_goalies), the engine weighs the team's LAST starter (sports_players.starter_for -> last_starter). The
11/5 study found 'the #1 (most starts in the last 10 this season) on a rested night, the OTHER goalie on the 2nd night of
a back-to-back' names tonight's starter far more often. Here: does that better guess make the engine's GOALIE INPUTS
better - the key edge (sports_players.key_edges: score() over his last 5 starts this season, edge_units) and the
'hotter goalie' form (sports_form.goalie_form / hot_side) - vs the close, held out, and on the dog pools those inputs
feed (the 'hotter goalie' named reason: key edge 0.4+ for the dog; the hot-goalie side)?

Guesses per side (box scores 2016-26, regular season, priced games; nothing from tonight):
  LAST   = the last starter (today's fallback)
  RULE   = sports_players.projected_starter (the wired rule: the #1 on rest - a tie goes to the last starter; on a b2b
           the most-used OTHER goalie of the last 10, else the last starter)
  ACTUAL = who really started (the oracle - what the model was trained on: key_edges uses the real starters on finals)
Train 2016-22 seasons, held out 2023 / 2024 / 2025 / 2026 apart."""
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import sports_players as sp  # noqa: E402
import sports_form as sf  # noqa: E402

rows = [r for r in sp.load()["nhl"] if r.get("role") == "G"]
act = {(r["gid"], r["team"]): r["player"] for r in rows}
by_player = defaultdict(list)
for r in rows:
    by_player[r["player"]].append(r)
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]


def key_score(name, start):
    lo = sp.recent_floor("nhl", start)
    st = [r for r in by_player.get(name, []) if lo <= r["start"] < start][-sp.RECENT["G"]:]
    return sp.score("G", st)


def form(name, start):
    return sf.goalie_form(by_player.get(name, []), name, start)


C = lib.Cells()
acc = defaultdict(lambda: [0, 0])
pairs = defaultdict(list)   # method -> [(season, y, p_close, p_open, edge)]
diff_n = defaultdict(int)
for g in fin:
    names = {}
    for side in ("home", "away"):
        team = g[side]
        a = act.get((g["id"], team))
        if not a:
            names = None
            break
        trows = [r for r in by_team[team] if r["start"] < g["start"]]
        last = sp.last_starter(trows, team, g["start"])
        rule = sp.projected_starter(trows, team, g["start"])
        if not last or not rule:
            names = None
            break
        names[side] = {"LAST": last, "RULE": rule, "ACTUAL": a}
        era = "2023-26" if g["season"] >= 2023 else "2016-22"
        acc[("LAST", era)][0] += last == a
        acc[("RULE", era)][0] += rule == a
        acc[("LAST", era)][1] += 1
        acc[("RULE", era)][1] += 1
        diff_n[era] += last != rule
    if not names:
        continue
    pc = lib.nv(lib.dec(g["mlh"]), lib.dec(g["mla"])) if False else (1 / lib.dec(g["mlh"])) / (1 / lib.dec(g["mlh"]) + 1 / lib.dec(g["mla"]))
    po = None
    if g["oh"] and g["oa"]:
        po = (1 / lib.dec(g["oh"])) / (1 / lib.dec(g["oh"]) + 1 / lib.dec(g["oa"]))
    y = 1 if g["hs"] > g["as"] else 0
    for m in ("LAST", "RULE", "ACTUAL"):
        e = sp.edge_units("G", key_score(names["home"][m], g["start"]), key_score(names["away"][m], g["start"]))
        pairs[m].append((g["season"], y, pc, po, e))
        fh, fa = form(names["home"][m], g["start"]), form(names["away"][m], g["start"])
        hot = sf.hot_side("nhl", None if fh is None or fa is None else fh - fa)
        for side, o_close, o_open, won in (("home", g["mlh"], g["oh"], y == 1), ("away", g["mla"], g["oa"], y == 0)):
            s_ = 1 if side == "home" else -1
            if lib.dog_band(o_close):
                if e * s_ >= 0.4:
                    C.add(f"close dog 'hotter goalie' (key edge 0.4+ for the dog) {m}", g["season"], lib.profit(won, lib.dec(o_close)))
                if e * s_ <= -0.4:
                    C.add(f"close dog facing the hotter goalie (key edge 0.4+ against) {m}", g["season"], lib.profit(won, lib.dec(o_close)))
                if hot == side:
                    C.add(f"close dog with the hot goalie (hot_side) {m}", g["season"], lib.profit(won, lib.dec(o_close)))
            if o_open and lib.dog_band(o_open) and g["season"] >= 2023:
                if e * s_ >= 0.4:
                    C.add(f"OPEN dog 'hotter goalie' {m}", g["season"], lib.profit(won, lib.dec(o_open)))
                if hot == side:
                    C.add(f"OPEN dog with the hot goalie (hot_side) {m}", g["season"], lib.profit(won, lib.dec(o_open)))


def ll(y, p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def logit(p):
    return math.log(p / (1 - p))


def fit_b(data, col):
    """one-weight logistic on top of the market: p = sigmoid(logit(market) + b * edge), b by a grid (train only)."""
    best = None
    for b in [i / 100 for i in range(-30, 31)]:
        s = sum(ll(y, 1 / (1 + math.exp(-(logit(m) + b * e)))) for _, y, m, _, e in data if m)
        if best is None or s < best[1]:
            best = (b, s)
    return best[0]


lines = ["(a) WHO STARTS - the share each guess names right (every side of a priced regular-season game with box scores)"]
for era in ("2016-22", "2023-26"):
    for m in ("LAST", "RULE"):
        a = acc[(m, era)]
        lines.append(f"  {era} {m:5s} {a[0]}/{a[1]} = {a[0]/a[1]*100:.1f}%")
    lines.append(f"  {era} sides where RULE != LAST: {diff_n[era]}")
lines.append("(b) THE KEY EDGE vs THE REAL STARTERS' edge: correlation, and the edge's value OVER THE MARKET (one weight on top of "
             "the no-vig close, fit on 2016-22, log loss held out in millis per game - lower = better; + = the edge helps)")
act_e = {(i): x[4] for i, x in enumerate(pairs["ACTUAL"])}
for m in ("LAST", "RULE", "ACTUAL"):
    xs = [x[4] for x in pairs[m]]
    ys = [x[4] for x in pairs["ACTUAL"]]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    r = cov / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    tr = [x for x in pairs[m] if x[0] <= 2022]
    b = fit_b(tr, 3)
    out = [f"  {m:6s} corr with the real starters' edge {r:+.3f}  b(train) {b:+.2f}"]
    for lab, sel in (("held 2023-26", lambda s: s >= 2023), ("2023", lambda s: s == 2023), ("2024", lambda s: s == 2024),
                     ("2025", lambda s: s == 2025), ("2026", lambda s: s == 2026)):
        hd = [x for x in pairs[m] if sel(x[0])]
        base = sum(ll(y, mk) for _, y, mk, _, e in hd)
        mod = sum(ll(y, 1 / (1 + math.exp(-(logit(mk) + b * e)))) for _, y, mk, _, e in hd)
        out.append(f"{lab} {1000 * (base - mod) / max(1, len(hd)):+.2f}m (n {len(hd)})")
    hd = [x for x in pairs[m] if x[0] >= 2023 and x[3]]
    base = sum(ll(y, po) for _, y, _, po, e in hd)
    mod = sum(ll(y, 1 / (1 + math.exp(-(logit(po) + b * e)))) for _, y, _, po, e in hd)
    out.append(f"| at ESPN's OPEN 2023-26 {1000 * (base - mod) / max(1, len(hd)):+.2f}m (n {len(hd)})")
    lines.append("  ".join(out))
txt = "\n".join(lines)
print(txt)
open(os.path.join(HERE, "s1_acc_out.txt"), "w").write(txt + "\n")
C.dump("s1", "(c) THE DOG POOLS THE GOALIE INPUTS FEED - by guess (dogs +100..+350)", (2016, 2022), [2023, 2024, 2025, 2026])
