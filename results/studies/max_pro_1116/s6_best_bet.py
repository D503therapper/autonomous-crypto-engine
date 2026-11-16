"""11/16 MAX PLAY HUNT - S6: A DAILY BEST BET. Across a day's unit plays on the two replay boards (pros + everything the
board carries), is there a ranking whose #1 wins clearly more than the day's other plays and more than a random pick?
The 11/14 study tried eleven hand-named rankings - none beat a random eligible play. Here:
  (A) a FITTED ranking: a ridge logistic on the train half (to 2025-06-30) - the kind, the league, the price, the dog
      score, the own-read margin, the read margin, home, the reasons, the drift - its #1 a day on the HELD-OUT half
      against 2,000 random one-a-day picks; and its top 10% / 5% of all plays (pick-your-spots, not one a day);
  (B) the count of things agreeing on a play (own read over the price, the read its units ride on over the price, the
      dog gate, 2+ named reasons, the money coming to it, a price in -150..+150) - the confluence dose on every unit play;
  (C) the one cell S2-S4 found, as a ranking: the hockey Dog at a score of 8+ first.
Usage: python results/studies/max_pro_1116/s6_best_bet.py > results/studies/max_pro_1116/s6_best_bet.out"""
import json
import math
import os
import random
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(STUD))
sys.path.insert(0, os.path.join(STUD, "sizing_1114"))
import lib as L  # noqa: E402

KINDS = ["dog", "lock", "nbafav", "dogplay", "nbafloor", "floor", "play"]
LGS = ["nhl", "nba", "nfl", "mlb", "ncaab", "ncaaf"]


def feats(r, k):
    om = L.own_margin(r)
    f = [1.0, 1 / r["dec"], 1.0 if r["odds"] >= 100 else 0.0, (r.get("dog_score") or 0.0) / 10, 1.0 if (r.get("dog_score") or 0) >= 8 else 0.0,
         (om or 0.0) / 10, max(-10, min(10, L.read_margin(r, k))) / 10, 1.0 if r["home"] else 0.0,
         min(3, r.get("n_reasons2") or 0) / 3, (r.get("drift") or 0.0) * 10, 1.0 if r.get("thin") else 0.0]
    f += [1.0 if k == x else 0.0 for x in KINDS]
    f += [1.0 if r["league"] == x else 0.0 for x in LGS]
    return f


def fit(X, y, lam=5.0, it=400):
    w = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + lam * w
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1])
        w -= np.linalg.solve(H, g)
    return w


def st(rs):
    n = len(rs)
    if not n:
        return "n    0"
    w = sum(r["result"] == "won" for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:4d} {w:3d}-{n - w:<4d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(L.flat(r) for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


for name, (bd, by) in L.boards().items():
    plays = [(d, r, u, k) for d in sorted(bd) for r, u, k in bd[d] if r["result"] in ("won", "lost") and L.half(d) != "live"]
    tr = [p for p in plays if L.half(p[0]) == "train"]
    he = [p for p in plays if L.half(p[0]) == "held"]
    print(f"\n================ BOARD {name}: {len(tr)} train / {len(he)} held-out unit plays ================")
    print(f"  every unit play, flat: train {st([p[1] for p in tr])} | held {st([p[1] for p in he])}")
    X = np.array([feats(r, k) for d, r, u, k in tr])
    y = np.array([1.0 if r["result"] == "won" else 0.0 for d, r, u, k in tr])
    w = fit(X, y)

    def ev(r, k):
        p = 1 / (1 + math.exp(-float(np.array(feats(r, k)) @ w)))
        return p * r["dec"] - 1
    print(" (A) THE FITTED RANKING (ridge logistic on the train half; rank = its win chance x the price)")
    for nm, part in (("train (in sample)", tr), ("HELD OUT", he)):
        days = defaultdict(list)
        for d, r, u, k in part:
            days[d].append((ev(r, k), r, k))
        multi = {d: v for d, v in days.items() if len(v) >= 2}
        top = [max(v, key=lambda x: x[0])[1] for v in multi.values()]
        rest = [x[1] for v in multi.values() for x in v if x[1] is not max(v, key=lambda z: z[0])[1]]
        rnd = random.Random(7)
        tgt = sum(L.flat(r) for r in top)
        hit = sum(1 for _ in range(2000) if sum(L.flat(rnd.choice(v)[1]) for v in multi.values()) >= tgt)
        print(f"    {nm}: days with 2+ unit plays {len(multi)} | the model's #1 {st(top)} | the day's other plays {st(rest)} | a random one a day did as well {hit} of 2,000")
        sc = sorted(((ev(r, k), r) for d, r, u, k in part), key=lambda x: -x[0])
        for frac in (0.05, 0.10, 0.25):
            n = max(1, int(len(sc) * frac))
            sel = [r for _, r in sc[:n]]
            ps = [L.flat(r) for _, r in sc]
            t2 = sum(L.flat(r) for r in sel)
            h2 = sum(1 for _ in range(2000) if sum(rnd.sample(ps, n)) >= t2)
            print(f"       its top {int(frac * 100):2d}% of all plays {st(sel)} | placebo {h2} of 2,000")
    print(" (B) THE COUNT OF THINGS AGREEING on a unit play")

    def agree(r, k):
        om = L.own_margin(r)
        return ((om is not None and om > 0) + L.beats(r, k) + bool(r.get("dog_gate")) + ((r.get("n_reasons2") or 0) >= 2)
                + ((r.get("drift") or 0) <= -0.02) + (-150 <= r["odds"] <= 150))
    for c in range(0, 7):
        a = [r for d, r, u, k in tr if agree(r, k) == c]
        b = [r for d, r, u, k in he if agree(r, k) == c]
        print(f"    count == {c}: train {st(a)} | held {st(b)}")
    for c in (4, 5):
        a = [r for d, r, u, k in tr if agree(r, k) >= c]
        b = [r for d, r, u, k in he if agree(r, k) >= c]
        print(f"    count >= {c}: train {st(a)} | held {st(b)}")
    print(" (C) THE HOCKEY DOG AT 8+ against the day's other unit plays (days it fires)")
    for nm, part in (("train", tr), ("held", he)):
        days = defaultdict(list)
        for d, r, u, k in part:
            days[d].append((r, k))
        fire = {d: v for d, v in days.items() if any(k == "dog" and r["league"] == "nhl" and (r.get("dog_score") or 0) >= 8 for r, k in v)}
        top = [r for v in fire.values() for r, k in v if k == "dog" and r["league"] == "nhl" and (r.get("dog_score") or 0) >= 8]
        rest = [r for v in fire.values() for r, k in v if not (k == "dog" and r["league"] == "nhl" and (r.get("dog_score") or 0) >= 8)]
        print(f"    {nm}: days {len(fire)} | the 8+ hockey Dog {st(top)} | the same days' other unit plays {st(rest)}")
    print("  every kind (held out), for scale: " + " | ".join(f"{k} {st([r for d, r, u, kk in he if kk == k])[7:]}" for k in KINDS))

print("\n================ LIVE - the NBA Dog of the Day and the gated NBA dogs (the 2020-26 replays say +47% on 51 / 14-8 / 11-8) ================")
pk = json.load(open(os.path.join(ROOT, "data/sports/picks.json")))
for lg in ("nba", "nhl", "nfl"):
    x = []
    for q in pk:
        g = (q.get("legs") or [{}])[0]
        if g.get("league") == lg and q.get("kind") == "dog" and q.get("status") in ("won", "lost") and not q.get("pulled"):
            x.append(dict(dec=q["dec"], result=q["status"], odds=q["american"]))
    print(f"  live {lg} Dogs of the Day: {st(x)}")
