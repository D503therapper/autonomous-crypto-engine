"""S8 - THE NBA LEDGER (the football R1 / college hoops slot ledgers' NBA twin - never done): every NBA unit play the
board makes, on BOTH replay boards (sizing_1114/lib.py - R1 the 10/30 funnel rows through the 11/11 board builder,
R2 the 11/12 deep program's rows on TODAY's code, 2023-10 -> 2026-11), cut by kind, home / road, the price, the dog
score, the month, the favorite / the dog on a back-to-back, the team's games in. A leak has to show on BOTH boards
in BOTH halves (train to 2025-06-30 / held out after) and beat a placebo.
S10 - the two open NBA leads re-read on the wider pool (every NBA dog the boards' rows hold, not only the posted
floor): the floor-shaped dog (dog score 0+, +100..+199, named reason, not fighting) with the favorite on a
back-to-back; home vs road."""
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "sizing_1114"))
import lib as L  # noqa: E402
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)
import sports_data as sd  # noqa: E402


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


PREV, NG, GAME = {}, {}, {}
os.chdir(REPO)
gs = [g for g in sd.load_games("nba").values() if g.get("start") and (g.get("stype") or "2") in ("2", "3")]
gs.sort(key=lambda g: g["start"])
last, cnt = {}, defaultdict(int)
for g in gs:
    t = _t(g["start"])
    y = t.year if t.month >= 9 else t.year - 1
    d0 = (t - timedelta(hours=8)).strftime("%Y-%m-%d")
    for side, other in (("home", "away"), ("away", "home")):
        GAME[(d0, g.get(f"{side}_name"), g.get(f"{other}_name"))] = (g["id"], side)
    for side in ("home", "away"):
        tm = g[side]
        PREV[(g["id"], side)] = (t - last[tm]).total_seconds() / 3600 if tm in last else None
        NG[(g["id"], side)] = cnt[(tm, y)]
    for side in ("home", "away"):
        last[g[side]] = t
        cnt[(g[side], y)] += 1


def feat(r):
    if r.get("gid"):
        gid, side = r["gid"], r["side"]
    else:
        gid, side = GAME.get((r["date"], r["team"], r["opp"]), (None, None))
    if "home" not in r:
        r["home"] = side == "home"
    o = "away" if side == "home" else "home"
    me, op = PREV.get((gid, side)), PREV.get((gid, o))
    return dict(b2b=me is not None and me <= 30, ob2b=op is not None and op <= 30, ng=NG.get((gid, side)))


BO = L.boards()
for nm in ("R1", "R2"):
    board, by = BO[nm]
    print(f"\n================ {nm} ================")
    P = [(d, r, u, k) for d, ps in board.items() for r, u, k in ps if r["league"] == "nba"]
    for x in P:
        x[1].update(feat(x[1]))
    kinds = sorted({k for _, _, _, k in P})
    rs = lambda f: [(d, r, u) for d, r, u, k in P if f(r, k)]      # noqa: E731
    L.line("every NBA unit play", rs(lambda r, k: True), units=True)
    L.line("every NBA unit play (flat)", rs(lambda r, k: True))
    for k0 in kinds:
        L.line(f"kind {k0}", rs(lambda r, k: k == k0))
    D = lambda r, k: r["odds"] >= 100          # noqa: E731
    F = lambda r, k: r["odds"] < 100           # noqa: E731
    L.line("dogs", rs(D))
    L.line("favorites", rs(F))
    print(" -- venue")
    L.line("dog, home", rs(lambda r, k: D(r, k) and r["home"]))
    L.line("dog, road", rs(lambda r, k: D(r, k) and not r["home"]))
    L.line("favorite, home", rs(lambda r, k: F(r, k) and r["home"]))
    L.line("favorite, road", rs(lambda r, k: F(r, k) and not r["home"]))
    print(" -- price")
    for lo, hi in ((100, 130), (131, 160), (161, 199), (200, 350)):
        L.line(f"dog +{lo}..+{hi}", rs(lambda r, k: lo <= r["odds"] <= hi))
    for lo, hi in ((-150, -131), (-130, -101)):
        L.line(f"favorite {lo}..{hi}", rs(lambda r, k: lo <= r["odds"] <= hi))
    print(" -- dog score (dogs)")
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        L.line(f"dog score {lo}..{hi}", rs(lambda r, k: D(r, k) and r.get("dog_score") is not None and lo <= r["dog_score"] < hi))
    print(" -- rest")
    L.line("dog, the favorite on a b2b", rs(lambda r, k: D(r, k) and r["ob2b"] and not r["b2b"]))
    L.line("dog, itself on a b2b", rs(lambda r, k: D(r, k) and r["b2b"] and not r["ob2b"]))
    L.line("dog, neither / both", rs(lambda r, k: D(r, k) and r["b2b"] == r["ob2b"]))
    L.line("favorite, the dog on a b2b", rs(lambda r, k: F(r, k) and r["ob2b"] and not r["b2b"]))
    L.line("favorite, itself on a b2b", rs(lambda r, k: F(r, k) and r["b2b"] and not r["ob2b"]))
    print(" -- month / games in")
    for mm, lab in ((("10", "11"), "Oct-Nov"), (("12",), "Dec"), (("01",), "Jan"), (("02",), "Feb"), (("03", "04"), "Mar-Apr")):
        L.line(f"dog, {lab}", rs(lambda r, k: D(r, k) and r["date"][5:7] in mm))
    L.line("dog, team games 0-9", rs(lambda r, k: D(r, k) and (r["ng"] or 0) < 10))
    L.line("dog, team games 10-40", rs(lambda r, k: D(r, k) and 10 <= (r["ng"] or 0) <= 40))
    L.line("dog, team games 41+", rs(lambda r, k: D(r, k) and (r["ng"] or 0) > 40))
    print(" -- the dog kinds by venue")
    for k0 in kinds:
        a = rs(lambda r, k: k == k0 and D(r, k) and r["home"])
        b = rs(lambda r, k: k == k0 and D(r, k) and not r["home"])
        if a or b:
            L.line(f"{k0} dog, home", a)
            L.line(f"{k0} dog, road", b)
    dogs = rs(D)
    for lab, f in (("home dogs", lambda r, k: D(r, k) and r["home"]), ("road dogs", lambda r, k: D(r, k) and not r["home"]),
                   ("dogs, fav on a b2b", lambda r, k: D(r, k) and r["ob2b"] and not r["b2b"]),
                   ("dogs +161..+199", lambda r, k: 161 <= r["odds"] <= 199)):
        print(f"   placebo {lab}: {L.placebo(rs(f), dogs)} of 2000 random board NBA dogs did as well")
    # ---- S10: the wider pool - every NBA dog row of the day's candidates, floor-shaped
    print(" -- S10: the WIDER pool (every NBA moneyline dog row, floor-shaped: dog score 0+, +100..+199, a reason, not fighting / trap)")
    W = []
    for d, v in by.items():
        for r in v:
            if r.get("league") != "nba" or r.get("market") != "ml" or r.get("result") not in ("won", "lost"):
                continue
            if not 100 <= r["odds"] <= 199 or r.get("dog_score") is None or r["dog_score"] < 0:
                continue
            if r.get("trap") or r.get("fighting") or not (r.get("n_reasons2") or r.get("n_reasons")):
                continue
            r.update(feat(r))
            W.append((d, r, 0.5))
    L.line("floor-shaped NBA dogs (all)", W)
    a = [x for x in W if x[1]["ob2b"] and not x[1]["b2b"]]
    L.line("  the favorite on a b2b, the dog rested", a)
    print(f"     placebo: {L.placebo(a, W)} of 2000")
    L.line("  the dog on a b2b, the favorite rested", [x for x in W if x[1]["b2b"] and not x[1]["ob2b"]])
    L.line("  home", [x for x in W if x[1]["home"]])
    L.line("  road", [x for x in W if not x[1]["home"]])
    L.line("  dog score 0-2", [x for x in W if x[1]["dog_score"] < 2])
    L.line("  dog score 2-4", [x for x in W if 2 <= x[1]["dog_score"] < 4])
    L.line("  dog score 4+", [x for x in W if x[1]["dog_score"] >= 4])
    A = []
    for d, v in by.items():
        for r in v:
            if r.get("league") == "nba" and r.get("market") == "ml" and r.get("result") in ("won", "lost") and 100 <= r["odds"] <= 350:
                r.update(feat(r))
                A.append((d, r, 0.5))
    L.line("EVERY NBA dog row +100..+350", A)
    L.line("  the favorite on a b2b, the dog rested", [x for x in A if x[1]["ob2b"] and not x[1]["b2b"]])
    L.line("  home", [x for x in A if x[1]["home"]])
    L.line("  road", [x for x in A if not x[1]["home"]])
    for lo, hi in ((-99, -4), (-4, -2), (-2, 0), (0, 2), (2, 4), (4, 99)):
        L.line(f"  dog score {lo}..{hi}", [x for x in A if x[1].get("dog_score") is not None and lo <= x[1]["dog_score"] < hi])
