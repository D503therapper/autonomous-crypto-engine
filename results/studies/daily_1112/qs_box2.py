"""11/12 DAILY - TWO MORE QUICK NEW STUDIES FROM THE TEAM BOX (2021-26; never run: "fast break" 0 / "4th down" only an
NFL coach study in the findings file):
  Q5 NBA: THE RUNNING TEAM ON TIRED LEGS - a team's share of its points from fast breaks this season (10+ games), top /
     bottom fifth; tonight on the 2nd night of a back-to-back (its last game 1 day ago) vs not
  Q6 COLLEGE FOOTBALL: THE AGGRESSIVE COACH - 4th-down tries a game this season (4+ games), top / bottom third, as a dog
     and as a favorite; and the matchup (the side that goes for it more than its opponent by 1+ a game)
States from finished games strictly before tonight; prices the game file's close at its own juice; TRAIN 2021-23,
HELD 2024 / 2025 / 2026 (2026 = this season to 11/10). ~40 cells: ~2 would clear |z| 2 by luck.
Usage: python results/studies/daily_1112/qs_box2.py > results/studies/daily_1112/qs_box2_out.txt"""
import importlib.util, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fl1111", os.path.join(os.path.dirname(HERE), "fable_1111", "lib.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
B = L.B
TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]


def num(x):
    try:
        return float(str(x).replace("%", ""))
    except (TypeError, ValueError):
        return None


def quant(vals, q):
    v = sorted(vals)
    return v[int(q * (len(v) - 1))]


def rows_for(lg, update, state, ready):
    fin = [g for g in B.finals(lg) if g["season"] >= 2021 and g["stype"] == "2"]
    box = L.teambox(lg)
    acc = defaultdict(lambda: defaultdict(float))
    last = {}
    out = []
    for g in fin:
        tb = box.get(g["id"]) or {}
        for side, team, opp, odds, won, home in B.sides(g):
            a, ao = acc[(g["season"], team)], acc[(g["season"], opp)]
            if ready(a) and ready(ao):
                out.append({"season": g["season"], "x": state(a), "xo": state(ao), "odds": odds, "won": won,
                            "ats": B.ats(g, side), "b2b": bool(last.get(team)) and B.days_between(last[team], g["start"]) <= 1.3,
                            "ob2b": bool(last.get(opp)) and B.days_between(last[opp], g["start"]) <= 1.3})
        for side, team, opp, odds, won, home in B.sides(g):
            if tb.get(team):
                update(acc[(g["season"], team)], tb[team], g, side)
            last[team] = g["start"]
    return out


def cells_out(name, rows, groups):
    cells = B.Cells()
    for r in rows:
        d = B.dec(r["odds"])
        for gname, ok in groups(r):
            if not ok:
                continue
            if -150 <= r["odds"] <= -101:
                cells.add(f"{name} {gname} fav -150..-101", r["season"], B.profit(r["won"], d))
            if 100 <= r["odds"] <= 350:
                cells.add(f"{name} {gname} dog +100..+350", r["season"], B.profit(r["won"], d))
            if r["ats"] is not None:
                cells.add(f"{name} {gname} ATS", r["season"], r["ats"])
    for k, v in sorted(cells.c.items()):
        print(B.fmt(k, B.summ(v, TRAIN, HELD)))


# Q5 NBA fast breaks ------------------------------------------------------------------------------------------------
def fb_upd(a, st, g, side):
    f = num(st.get("fastBreakPoints"))
    pts = g["hs"] if side == "home" else g["as"]
    if f is not None and pts:
        a["fb"] += f
        a["pts"] += pts
        a["n"] += 1


nba = rows_for("nba", fb_upd, lambda a: a["fb"] / a["pts"], lambda a: a["n"] >= 10)
tr = [r["x"] for r in nba if TRAIN[0] <= r["season"] <= TRAIN[1]]
lo, hi = quant(tr, 0.2), quant(tr, 0.8)
print(f"== Q5 NBA fast-break share: {len(nba)} sides; bottom fifth <= {lo:.3f}, top fifth >= {hi:.3f}")
cells_out("Q5", nba, lambda r: (("BASE all", True), ("BASE on a b2b", r["b2b"]),
                                ("RUNNER (top 5th)", r["x"] >= hi), ("RUNNER on a b2b", r["x"] >= hi and r["b2b"]),
                                ("RUNNER on a b2b vs rested", r["x"] >= hi and r["b2b"] and not r["ob2b"]),
                                ("SLOW (bottom 5th) on a b2b", r["x"] <= lo and r["b2b"]),
                                ("vs a RUNNER on a b2b", r["xo"] >= hi and r["ob2b"])))


# Q6 college football 4th-down aggression ---------------------------------------------------------------------------
def fd_upd(a, st, g, side):
    p = L.pair(st.get("fourthDownEff"))
    if p:
        a["tries"] += p[1]
        a["n"] += 1


cf = rows_for("ncaaf", fd_upd, lambda a: a["tries"] / a["n"], lambda a: a["n"] >= 4)
tr = [r["x"] for r in cf if TRAIN[0] <= r["season"] <= TRAIN[1]]
lo, hi = quant(tr, 1 / 3), quant(tr, 2 / 3)
print(f"\n== Q6 college football 4th-down tries a game: {len(cf)} sides; bottom third <= {lo:.2f}, top third >= {hi:.2f}")
cells_out("Q6", cf, lambda r: (("BASE all", True), ("AGGRESSIVE (top 3rd)", r["x"] >= hi), ("TIMID (bottom 3rd)", r["x"] <= lo),
                               ("goes for it 1+ more a game than the opponent", r["x"] - r["xo"] >= 1.0),
                               ("goes for it 1+ less a game", r["x"] - r["xo"] <= -1.0)))
