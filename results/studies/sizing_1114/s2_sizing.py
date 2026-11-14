"""11/14 - SIZING: WHERE CAN WE BET MORE? (the owner, 11/13: "we should have had 2 units on the Predators today. Instead, we
have a weak-ass half unit" + "run [studies] on the sizing ... improve the engine and make it more profitable").
The 10/30 bar, unchanged: a bigger size only on a cell that won MORE vs its price than the rest of its kind (the smaller
size) in BOTH halves (train to 2025-06-30 / held out after) on BOTH replay boards (R1 the 10/30 rows, R2 today's code -
lib.py), and beat a placebo (the same number of plays of its kind drawn at random 2,000 times: 100 or fewer as good).
Cells NAMED BEFORE LOOKING (the brief): (a) the floor's hockey dogs - dog score, the favorite on a back-to-back, our goalie
hot (last 3 starts .930+ - the box score's starter, so a slight look-ahead in the replay: the morning page is right ~77%),
the price; (b) the Dog of the Day's 2u band - a 3u cell with more data (dog score 8+ / 10+, the own read over, +130..+150,
the favorite on a b2b, a hot goalie); (c) the own read over the price by a lot vs a little, every kind; (d) every kind's
size by price band and own read (the Lock, value plays, the NBA floor, the NBA favorite play, the runner-up dog).
Usage: python results/studies/sizing_1114/s2_sizing.py > results/studies/sizing_1114/s2_sizing.out"""
import csv
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, REPO)
import sports_data as sd  # noqa: E402


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------- the schedule facts: back-to-backs, the goalie's last 3
GAME = {}           # (league, pt date, team name, opp name) -> (game, team side)
PREV = {}           # (league, game id, side) -> hours since that team's last game
for lg in ("nhl", "nba"):
    gs = [g for g in sd.load_games(lg).values() if g.get("start") and (g.get("stype") or "2") in ("2", "3")]
    gs.sort(key=lambda g: g["start"])
    last = {}
    for g in gs:
        t = _t(g["start"])
        d = (t - timedelta(hours=8)).strftime("%Y-%m-%d")
        for side, other in (("home", "away"), ("away", "home")):
            tm = g[side]
            PREV[(lg, g["id"], side)] = (t - last[tm]).total_seconds() / 3600 if tm in last else None
            GAME[(lg, d, g[f"{side}_name"], g[f"{other}_name"])] = (g, side)
        for side in ("home", "away"):
            last[g[side]] = t

START = defaultdict(dict)    # (gid, team id) -> (player, sa, ga) the starter (the most shots)
for r in csv.DictReader(open(os.path.join(REPO, "data", "sports", "players", "nhl.csv"))):
    if r.get("role", "G") != "G":
        continue
    try:
        sa, ga = float(r["sa"] or 0), float(r["ga"] or 0)
    except ValueError:
        continue
    k = (r["gid"], r["team"])
    if k not in START or sa > START[k][1]:
        START[k] = (r["player"], sa, ga, r["start"])
G_HIST = defaultdict(list)   # player -> [(start, sa, ga)]
for (gid, tm), (pl, sa, ga, st) in START.items():
    G_HIST[pl].append((st, sa, ga))
for v in G_HIST.values():
    v.sort()


def g_last3(gid, team_id):
    s = START.get((gid, team_id))
    if not s:
        return None
    h = [x for x in G_HIST[s[0]] if x[0] < s[3]][-3:]
    if len(h) < 3:
        return None
    sa = sum(x[1] for x in h)
    return None if sa < 40 else 1 - sum(x[2] for x in h) / sa


def facts(r):
    if "_f" in r:
        return r["_f"]
    f = {}
    hit = GAME.get((r["league"], r["date"], r["team"], r["opp"]))
    if hit:
        g, side = hit
        other = "away" if side == "home" else "home"
        me, op = PREV.get((r["league"], g["id"], side)), PREV.get((r["league"], g["id"], other))
        f["b2b_me"] = me is not None and me <= 30
        f["b2b_opp"] = op is not None and op <= 30
        if r["league"] == "nhl":
            f["g_me"] = g_last3(g["id"], g[side])
            f["g_opp"] = g_last3(g["id"], g[other])
    r["_f"] = f
    return f


def opp_b2b(r):
    f = facts(r)
    return bool(f.get("b2b_opp")) and not f.get("b2b_me")


def g_hot(r):
    v = facts(r).get("g_me")
    return v is not None and v >= 0.930


def om(r):
    m = L.own_margin(r)
    return -99 if m is None else m


def ds(r):
    return -99 if r.get("dog_score") is None else r["dog_score"]


# ---------------------------------------------------------------- the test
VERDICT = []


def test(name, kind_sel, cell_sel, boards):
    """cell vs the rest of its kind, flat, by half, both boards; the placebo inside the kind."""
    ok_all = True
    print(f"\n  >> {name}")
    for bn, (board, _by) in boards.items():
        kind = [(d, r, u) for d in board for r, u, k in board[d] if kind_sel(r, u, k)]
        cell = [(d, r, u) for d, r, u in kind if cell_sel(r, u)]
        rest = [(d, r, u) for d, r, u in kind if not cell_sel(r, u)]
        c = L.line(f"{bn} the cell", cell)
        o = L.line(f"{bn} the rest of its kind", rest)
        pb = L.placebo(cell, kind)
        print(f"     {bn} placebo: a random {c['all']['n'] - c['live']['n']} of its kind did as well {pb if pb is not None else '-'} of 2,000")
        win = (c["train"]["n"] >= 8 and c["held"]["n"] >= 8 and c["train"]["roi"] > o["train"]["roi"] and c["held"]["roi"] > o["held"]["roi"]
               and pb is not None and pb <= 100)
        ok_all = ok_all and win
    VERDICT.append((name, ok_all))
    print(f"     => {'EARNS A BIGGER SIZE (both boards, both halves, placebo)' if ok_all else 'no'}")
    return ok_all


BOARDS = L.boards()
for bn, (board, _by) in BOARDS.items():
    for d in board:
        for r, u, k in board[d]:
            facts(r)
    hk = [(r, u, k) for d in board for r, u, k in board[d] if r["league"] == "nhl"]
    print(f"{bn}: hockey unit plays {len(hk)}, with a b2b fact {sum(1 for r, u, k in hk if 'b2b_me' in r['_f'])}, "
          f"with our goalie's last 3 {sum(1 for r, u, k in hk if r['_f'].get('g_me') is not None)}")

print("\n" + "=" * 30, "(0) WHAT EACH KIND EARNS NOW (flat 1u, and at its own size) - both boards")
for bn, (board, _by) in BOARDS.items():
    print(f"-- {bn}")
    for kk in ("lock", "backup", "dog", "nbafav", "dogplay", "play", "nbafloor", "floor", "floorfb", "solo"):
        rs = [(d, r, u) for d in board for r, u, k in board[d] if k == kk]
        if rs:
            L.line(f"{kk}", rs)
            L.line(f"{kk} at its size", rs, units=True)
    for lg in ("nhl", "nba", "mlb", "ncaab", "nfl", "ncaaf"):
        rs = [(d, r, u) for d in board for r, u, k in board[d] if k == "dog" and r["league"] == lg]
        if rs:
            L.line(f"Dog of the Day, {lg}", rs)

print("\n" + "=" * 30, "(A) THE FLOOR'S HOCKEY DOGS (½u today) - the Predators question")
FH = lambda r, u, k: k in ("floor", "floorfb") and r["league"] == "nhl"   # noqa: E731
for bn, (board, _by) in BOARDS.items():
    rs = [(d, r, u) for d in board for r, u, k in board[d] if FH(r, u, k)]
    print(f"-- {bn}: the floor's hockey dogs, by the facts")
    L.line("all", rs)
    for lo, hi in ((-99, -3), (-3, 0), (0, 3), (3, 6), (6, 99)):
        L.line(f"dog score {lo}..{hi}", [x for x in rs if lo <= ds(x[1]) < hi])
    L.line("the favorite on a b2b (we're rested)", [x for x in rs if opp_b2b(x[1])])
    L.line("we're on a b2b", [x for x in rs if facts(x[1]).get("b2b_me")])
    L.line("our goalie hot (last 3 .930+)", [x for x in rs if g_hot(x[1])])
    L.line("our goalie not hot", [x for x in rs if facts(x[1]).get("g_me") is not None and not g_hot(x[1])])
    L.line("+100..+150", [x for x in rs if x[1]["odds"] <= 150])
    L.line("+151..+350", [x for x in rs if x[1]["odds"] > 150])
    L.line("own read within 2 of the price", [x for x in rs if om(x[1]) >= -2])
    L.line("own read 2+ under the price", [x for x in rs if om(x[1]) < -2])
    L.line("the fallback (the day had no other unit play)", [(d, r, u) for d in board for r, u, k in board[d] if k == "floorfb" and r["league"] == "nhl"])
    L.line("PREDATORS-TYPE: score under 0, goalie hot", [x for x in rs if ds(x[1]) < 0 and g_hot(x[1])])
for name, sel in (("dog score 3+", lambda r, u: ds(r) >= 3), ("dog score 0+", lambda r, u: ds(r) >= 0),
                  ("the favorite on a b2b, we're rested", lambda r, u: opp_b2b(r)),
                  ("our goalie hot (last 3 .930+)", lambda r, u: g_hot(r)),
                  ("+100..+150", lambda r, u: r["odds"] <= 150),
                  ("own read within 2 of the price", lambda r, u: om(r) >= -2),
                  ("dog score 0+ AND +100..+150", lambda r, u: ds(r) >= 0 and r["odds"] <= 150),
                  ("the favorite on a b2b AND +100..+150", lambda r, u: opp_b2b(r) and r["odds"] <= 150),
                  ("goalie hot AND score under 0 (the Predators)", lambda r, u: g_hot(r) and ds(r) < 0)):
    test(f"(a) floor hockey dog at 1u+: {name}", FH, sel, BOARDS)

print("\n" + "=" * 30, "(B) THE DOG OF THE DAY'S 2u BAND - is there a 3u cell now?")
D2 = lambda r, u, k: k == "dog" and u == 2.0   # noqa: E731
for name, sel in (("dog score 8+", lambda r, u: ds(r) >= 8), ("dog score 10+", lambda r, u: ds(r) >= 10),
                  ("own read 1+ over the price", lambda r, u: om(r) >= 1), ("own read 2+ over the price", lambda r, u: om(r) >= 2),
                  ("+130..+150", lambda r, u: r["odds"] >= 130), ("+100..+129", lambda r, u: r["odds"] < 130),
                  ("the favorite on a b2b, we're rested", lambda r, u: opp_b2b(r)), ("our goalie hot", lambda r, u: g_hot(r)),
                  ("hockey", lambda r, u: r["league"] == "nhl"), ("at home", lambda r, u: r["home"]),
                  ("its read 8+ points over the price", lambda r, u: L.read_margin(r, "dog") >= 8)):
    test(f"(b) the 2u Dog at 3u: {name}", D2, sel, BOARDS)
print("-- and the ½u long Dog (+151..+350): any cell worth 1u+?")
DL = lambda r, u, k: k == "dog" and r["odds"] > 150 and r["league"] != "nba"   # noqa: E731
for name, sel in (("dog score 8+", lambda r, u: ds(r) >= 8), ("own read 2+ over", lambda r, u: om(r) >= 2),
                  ("+151..+199", lambda r, u: r["odds"] < 200), ("the favorite on a b2b", lambda r, u: opp_b2b(r))):
    test(f"(b) the long Dog at 1u+: {name}", DL, sel, BOARDS)

print("\n" + "=" * 30, "(C) THE OWN READ OVER THE PRICE BY A LOT vs A LITTLE (points of win chance)")
for bn, (board, _by) in BOARDS.items():
    print(f"-- {bn}")
    for grp, gsel in (("favorites", lambda r, k: r["odds"] < 0), ("dogs", lambda r, k: r["odds"] > 0)):
        rs = [(d, r, u) for d in board for r, u, k in board[d] if gsel(r, k)]
        for lo, hi in ((-99, -3), (-3, 0), (0, 1), (1, 3), (3, 5), (5, 8), (8, 99)):
            L.line(f"{grp}: own read {lo}..{hi} over", [x for x in rs if lo <= om(x[1]) < hi])
    rs = [(d, r, u) for d in board for r, u, k in board[d]]
    for lo, hi in ((-99, 0), (0, 2), (2, 5), (5, 10), (10, 99)):
        L.line(f"every play: its OWN units' read {lo}..{hi} over", [x for x in rs if lo <= L.read_margin(x[1], "dog") < hi])
ALL = lambda r, u, k: True   # noqa: E731
FAV = lambda r, u, k: r["odds"] < 0   # noqa: E731
DOG = lambda r, u, k: r["odds"] > 0   # noqa: E731
for name, ks, sel in (("every unit play, own read 3+ over", ALL, lambda r, u: om(r) >= 3),
                      ("every unit play, own read 5+ over", ALL, lambda r, u: om(r) >= 5),
                      ("favorites, own read 3+ over", FAV, lambda r, u: om(r) >= 3),
                      ("dogs, own read 3+ over", DOG, lambda r, u: om(r) >= 3),
                      ("dogs, own read 0+ over (not under the price)", DOG, lambda r, u: om(r) >= 0)):
    test(f"(c) {name}", ks, sel, BOARDS)

print("\n" + "=" * 30, "(D) EVERY OTHER KIND - a bigger size anywhere?")
for name, ks, sel in (
        ("the Lock (2u/1u): price -135..-101", lambda r, u, k: k == "lock", lambda r, u: r["odds"] > -135),
        ("the Lock: own read 3+ over the price", lambda r, u, k: k == "lock", lambda r, u: om(r) >= 3),
        ("the Lock: hockey", lambda r, u, k: k == "lock", lambda r, u: r["league"] == "nhl"),
        ("value plays (½u): own read 3+ over", lambda r, u, k: k == "play", lambda r, u: om(r) >= 3),
        ("value plays (½u): -135..-101", lambda r, u, k: k == "play", lambda r, u: r["odds"] > -135),
        ("value plays (½u): hockey", lambda r, u, k: k == "play", lambda r, u: r["league"] == "nhl"),
        ("the NBA floor (½u): +100..+150", lambda r, u, k: k == "nbafloor", lambda r, u: r["odds"] <= 150),
        ("the NBA floor (½u): dog score 3+", lambda r, u, k: k == "nbafloor", lambda r, u: ds(r) >= 3),
        ("the NBA floor (½u): the favorite on a b2b", lambda r, u, k: k == "nbafloor", lambda r, u: opp_b2b(r)),
        ("the NBA favorite play (1u): own read 3+ over", lambda r, u, k: k == "nbafav", lambda r, u: om(r) >= 3),
        ("the NBA favorite play (1u): -130..-101", lambda r, u, k: k == "nbafav", lambda r, u: r["odds"] > -130),
        ("the runner-up dog (½u): +100..+150", lambda r, u, k: k == "dogplay", lambda r, u: r["odds"] <= 150),
        ("the runner-up dog (½u): dog score 8+", lambda r, u, k: k == "dogplay", lambda r, u: ds(r) >= 8),
        ("the general floor (½u, every league): +100..+150", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u: r["odds"] <= 150),
        ("the general floor (½u): dog score 3+", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u: ds(r) >= 3)):
    test(f"(d) {name}", ks, sel, BOARDS)

print("\n" + "=" * 30, "VERDICTS")
for n, ok in VERDICT:
    print(f"  {'EARNED' if ok else 'no    '}  {n}")
