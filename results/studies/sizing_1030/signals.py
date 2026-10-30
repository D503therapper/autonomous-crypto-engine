"""10/30 SIZING, step 1: what separates the unit plays that win MORE vs the price? Every board unit play (board.py),
flat 1u, by kind and sport, split by every candidate sizing signal - the own read over the price (edge_own, per $1), the
weighed read over the price (w_edge), the own read over the no-vig market (gap, points), the dog score, the price band.
A signal can carry a bigger size only where its top cell beats the rest in BOTH train (2023-25) and held out (2025-27).
Usage: python signals.py > signals.out"""
from collections import defaultdict

from board import PLAYS, half, pnl, gap, w_edge, season


def st(ps):
    if not ps:
        return "      n=0          "
    w = sum(r["result"] == "won" for _, r, _, _ in ps)
    l = sum(r["result"] == "lost" for _, r, _, _ in ps)
    net = sum(pnl(r, 1) for _, r, _, _ in ps)
    return f"{w:4d}-{l:<4d}{100 * net / len(ps):+6.1f}%"


def line(name, ps):
    t = [p for p in ps if half(p[0]) == "train"]
    h = [p for p in ps if half(p[0]) == "held"]
    lv = [p for p in ps if half(p[0]) == "live"]
    a = [p for p in ps if half(p[0]) != "live"]
    print(f"   {name:34s} train {st(t)} | held {st(h)} | all {st(a)} | live {st(lv)}")


def cut(f, edges):
    def g(p):
        v = f(p[1])
        if v is None:
            return "none"
        for lo, hi in edges:
            if lo <= v < hi:
                return f"{lo}..{hi}"
        return "out"
    return g


SIG = {
    "edge_own": (lambda r: None if r.get("edge_own") is None else 100 * r["edge_own"], ((-99, 0), (0, 3), (3, 6), (6, 10), (10, 15), (15, 99))),
    "w_edge": (lambda r: None if w_edge(r) is None else 100 * w_edge(r), ((-99, 0), (0, 3), (3, 6), (6, 10), (10, 99))),
    "gap": (gap, ((-99, 0), (0, 2), (2, 4), (4, 7), (7, 99))),
    "dog_score": (lambda r: r.get("dog_score"), ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99))),
    "odds": (lambda r: r["odds"], ((-150, -135), (-135, -120), (-120, -100), (100, 130), (130, 160), (160, 200), (200, 351))),
    "p (blend)": (lambda r: 100 * r["p"], ((0, 40), (40, 50), (50, 56), (56, 60), (60, 65), (65, 100))),
}


def table(name, ps, sigs=SIG):
    print(f"\n== {name}")
    line("ALL", ps)
    seas = defaultdict(list)
    for p in ps:
        seas[season(p[0])].append(p)
    for s in sorted(seas):
        line(f"season {s}", seas[s])
    for sg, (f, edges) in sigs.items():
        groups = defaultdict(list)
        g = cut(f, edges)
        for p in ps:
            groups[g(p)].append(p)
        if len(groups) <= 1 and "none" in groups:
            continue
        for k in [f"{lo}..{hi}" for lo, hi in edges] + ["none", "out"]:
            if groups.get(k):
                line(f"{sg} {k}", groups[k])


if __name__ == "__main__":
    by = defaultdict(list)
    for p in PLAYS:
        by[p[2]].append(p)
    print("UNIT PLAYS by kind (today's rules), flat 1u")
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        line(k, v)
    print("\nDogs of the Day by sport")
    for lg in ("nhl", "ncaaf", "nfl", "nba", "ncaab"):
        line(f"dog {lg}", [p for p in by["dog"] if p[1]["league"] == lg])
    print("\nLocks by sport")
    for lg in ("ncaab", "nhl", "mlb", "ncaaf", "nfl", "nba"):
        line(f"lock {lg}", [p for p in by["lock"] if p[1]["league"] == lg])
    print("\nLocks by today's size")
    for u in (1.0, 2.0, 3.0):
        line(f"lock {u}u", [p for p in by["lock"] if p[3] == u])
    for k in ("lock", "backup", "play", "dog", "dogplay", "nbafav", "nbafloor", "floor", "floorfb"):
        table(k, by[k])
    for lg in ("nhl", "ncaaf", "nba", "ncaab"):
        table(f"dog {lg}", [p for p in by["dog"] if p[1]["league"] == lg])
    table("all dogs on the board (dog + dogplay + floor + nbafloor + floorfb)",
          [p for p in PLAYS if p[1]["odds"] >= 100])
    table("all favorites on the board (lock + backup + play + nbafav)", [p for p in PLAYS if p[1]["odds"] < 100])
