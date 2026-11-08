"""11/8 S1 - THE HOCKEY DOG 2u ON A THIN EDGE (today's Jets +124 at 2u, own read 45.4% vs 44.6% needed).
Since 10/31 (SIZING_1031_FROM) a hockey / football Dog is sized by its PRICE: 2u at +100..+150, ½u past it, thin or not.
(a) LIVE: every posted Dog in picks.json, hockey apart, split by the own read's edge per dollar (sports.thin_edge):
    'own under' (edge_own <= 0), 'thin' (0..3%), 'real' (3%+).
(b) THE REPLAY: the 10/30 sizing study's rows (results/studies/sizing_1030/board.py - the funnel 2023-26, closing prices),
    the Dog of the Day in hockey at +100..+150, by the same edge split, and the edge in finer bands (0-1 / 1-2 / 2-3 / 3-6 / 6+).
Read-only; no sizing change (the owner's call)."""
import json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

out = []
P = print


def pr(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    P(s)


def band(e):
    if e is None:
        return "no read"
    return "own under (<=0)" if e <= 0 else "thin (0-3%)" if e < 0.03 else "real (3%+)"


pk = json.load(open("data/sports/picks.json"))
pr("== (a) LIVE Dogs (picks.json) - date league team odds units result edge_own thin?")
cells = defaultdict(lambda: [0, 0, 0.0, 0.0])
for x in pk:
    if x.get("kind") != "dog":
        continue
    l = x["legs"][0]
    e = l.get("edge_own")
    res = x.get("status")
    u = x.get("units") or 0
    pnl = x.get("pnl")
    pr(f"  {x['date']} {l.get('league'):5s} {l.get('team'):16s} {l.get('odds'):+5d} {u!s:4s} {res:6s} edge_own {e if e is None else round(e, 3)!s:7s} {'THIN' if sports.thin_edge(l) else 'real'}  pnl {pnl}")
    if res not in ("won", "lost"):
        continue
    lg = "nhl" if l.get("league") == "nhl" else "other"
    for k in (f"{lg} {band(e)}", f"{lg} all", f"{lg} {'+100..+150' if l['odds'] <= 150 else '+151..+350'} {'thin/under' if sports.thin_edge(l) else 'real'}",
              f"{lg} since 10/31 {'thin' if sports.thin_edge(l) else 'real'}" if x["date"] >= "2026-10-31" else None):
        if not k:
            continue
        c = cells[k]
        c[0 if res == "won" else 1] += 1
        c[2] += (l.get("dec") or sports._dec(l["odds"])) - 1 if res == "won" else -1     # flat 1u
        c[3] += u * (((l.get("dec") or sports._dec(l["odds"])) - 1) if res == "won" else -1)
for k in sorted(cells):
    w, lo, flat, pnl = cells[k]
    pr(f"  {k:40s} {w}-{lo}  flat {flat:+.2f}u ({100 * flat / (w + lo):+.1f}%)  as sized {pnl:+.2f}u")

# (b) the replay
os.environ.setdefault("FUNNEL", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030")
sys.path.insert(0, os.path.join(ROOT, "results/studies/sizing_1030"))
import board  # noqa: E402

pr("\n== (b) THE REPLAY (10/30 funnel rows, closing prices; train 2023-24/2024-25, held 2025-26, live 10/13-10/29), the Dog of the Day")


def st(ps):
    if not ps:
        return "n=0".ljust(26)
    w = sum(r["result"] == "won" for r in ps)
    l = sum(r["result"] == "lost" for r in ps)
    net = sum(board.pnl(r, 1) for r in ps)
    return f"{w}-{l} {100 * net / len(ps):+6.1f}% ({len(ps)})".ljust(26)


def won_vs(ps):
    if not ps:
        return ""
    w = sum(r["result"] == "won" for r in ps) / len(ps)
    pri = sum(1 / r["dec"] for r in ps) / len(ps)
    own = [board.own_p(r) for r in ps if board.own_p(r) is not None]
    return f"won {100 * w:.1f}% vs priced {100 * pri:.1f}% (own read {100 * sum(own) / len(own):.1f}%)" if own else ""


def show(name, ps):
    by = defaultdict(list)
    for r in ps:
        by[board.half(r["date"])].append(r)
    seas = defaultdict(list)
    for r in ps:
        seas[board.season(r["date"])].append(r)
    s = " ".join(f"{k}:{100 * sum(board.pnl(r, 1) for r in v) / len(v):+.0f}%({len(v)})" for k, v in sorted(seas.items()))
    pr(f"  {name:44s} train {st(by['train'])} held {st(by['held'])} live {st(by['live'])} ALL {st(ps)} | {s}")
    pr(f"  {'':44s} {won_vs(ps)}")


dogs = [r for d, r, k, u in board.PLAYS if k == "dog"]
for lgname, lgs in (("hockey", ("nhl",)), ("football", ("nfl", "ncaaf")), ("hockey + football", ("nhl", "nfl", "ncaaf"))):
    pr(f"-- {lgname}")
    d = [r for r in dogs if r["league"] in lgs]
    short = [r for r in d if r["odds"] <= 150]
    show("+100..+150 all (today 2u)", short)
    for lo, hi, nm in ((-9, 0.0, "own under (<=0)"), (0.0, 0.03, "thin 0-3%"), (0.03, 9, "real 3%+")):
        show(f"+100..+150 {nm}", [r for r in short if r.get("edge_own") is not None and lo < r["edge_own"] <= hi
                                     or (nm.startswith("own") and r.get("edge_own") is not None and r["edge_own"] <= 0 and lo == -9)])
    if lgname == "hockey":
        for lo, hi in ((0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.06), (0.06, 9)):
            show(f"+100..+150 own edge {lo:.2f}-{hi:.2f}", [r for r in short if r.get("edge_own") is not None and lo < r["edge_own"] <= hi])
        # the own read over the no-vig market (points) - another cut of 'thin'
        for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 99)):
            show(f"+100..+150 own over no-vig {lo}..{hi} pts", [r for r in short if board.gap(r) is not None and lo < board.gap(r) <= hi])
    show("+151..+350 all (today ½u)", [r for r in d if r["odds"] > 150])

# the money: 2u everywhere vs 1u on the thin short hockey Dog vs ½u
pr("\n== (c) SIZE SCHEDULES on the hockey +100..+150 Dogs (units won, train / held / live / all)")
h = [r for r in dogs if r["league"] == "nhl" and r["odds"] <= 150]
for nm, f in (("today: 2u thin or not", lambda r: 2.0), ("thin 1u / real 2u", lambda r: 1.0 if (r.get("edge_own") or 0) < 0.03 else 2.0),
              ("thin ½u / real 2u (the pre-10/31 rule)", lambda r: 0.5 if (r.get("edge_own") or 0) < 0.03 else 2.0)):
    t = defaultdict(float)
    for r in h:
        t[board.half(r["date"])] += board.pnl(r, f(r))
    pr(f"  {nm:44s} train {t['train']:+.1f}u held {t['held']:+.1f}u live {t['live']:+.1f}u ALL {sum(t.values()):+.1f}u")
open(os.path.join(HERE, "s1_out.txt"), "w").write("\n".join(out) + "\n")
