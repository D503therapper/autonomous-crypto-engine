"""11/12 DEEP PROGRAM - shared helpers. Read-only on the repo.
FUNNEL rows: the 10/30 funnel replay (results/studies/thin_1029/funnel_replay.py - 1,097 board days 2023-10 -> 2026-10 +
the live stretch; every moneyline candidate with the reads the live board stamps: p (the blended win %), edge_own (the
own read), w_p (the weighed read), raw_own (the raw ratings read), p_market (no-vig close), the result). 54 MB, never
committed: FUNNEL=<folder with fA-fD.jsonl + fLive.jsonl>.
TABLES: the 11/12 fifteen-studies walk-forward table a league (results/studies/fifteen_1112/lib.py)."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FUNNEL = os.environ.get("FUNNEL") or ("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/"
                                       "scratchpad/funnel1030")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fifteen_1112"))
CELLS = [0]


def funnel(live=False):
    rows, seen = [], set()
    for f in ("fA", "fB", "fC", "fD") + (("fLive",) if live else ()):
        p = os.path.join(FUNNEL, f + ".jsonl")
        for ln in open(p):
            r = json.loads(ln)
            if r.get("result") not in ("won", "lost"):
                continue
            k = (r["date"], r["league"], r["team"], r["opp"], r["side"])
            if k in seen:
                continue
            seen.add(k)
            r["y"] = 1.0 if r["result"] == "won" else 0.0
            r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
            r["half"] = "train" if r["date"] <= "2025-06-30" else "held"
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            rows.append(r)
    return rows


def dec(o):
    o = o or -110
    return 1 + (o / 100 if o > 0 else 100 / -o)


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def fit_offset(X, y, off, lam=1e-6, iters=50):
    """Logistic regression with a fixed offset; returns (w, se)."""
    d = len(X[0])
    w = [0.0] * d
    H = None
    for _ in range(iters):
        g = [lam * w[j] for j in range(d)]
        H = [[lam if i == j else 0.0 for j in range(d)] for i in range(d)]
        for x, t, o in zip(X, y, off):
            p = sig(o + sum(a * b for a, b in zip(w, x)))
            r, s = p - t, p * (1 - p)
            for i in range(d):
                g[i] += r * x[i]
                for j in range(d):
                    H[i][j] += s * x[i] * x[j]
        step = solve(H, g)
        w = [a - b for a, b in zip(w, step)]
        if max(abs(v) for v in step) < 1e-8:
            break
    inv = invert(H)
    return w, [math.sqrt(max(0.0, inv[i][i])) for i in range(d)]


def solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            continue
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def invert(A):
    n = len(A)
    cols = [solve(A, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def ll(ps, ys):
    return -sum(y * math.log(min(max(p, 1e-6), 1 - 1e-6)) + (1 - y) * math.log(min(max(1 - p, 1e-6), 1 - 1e-6)) for p, y in zip(ps, ys)) / max(1, len(ys))


def bet(rs, price=lambda r: r["dec"], win=lambda r: r["y"]):
    """rs -> (n, wins, roi %, z of the mean profit)"""
    pr = [(price(r) - 1) if win(r) == 1 else (-1.0 if win(r) == 0 else 0.0) for r in rs]
    n = len(pr)
    if not n:
        return 0, 0, 0.0, 0.0
    m = sum(pr) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in pr) / max(1, n - 1))
    return n, sum(win(r) == 1 for r in rs), 100 * m, (m / (sd / math.sqrt(n)) if sd else 0.0)


def cell(name, rs, split=lambda r: r["half"], seas=lambda r: r["season"], price=lambda r: r["dec"], win=lambda r: r["y"], out=True):
    """One printed cell: all / train / held, seasons up, z."""
    CELLS[0] += 1
    n, w, roi, z = bet(rs, price, win)
    tr = bet([r for r in rs if split(r) == "train"], price, win)
    he = bet([r for r in rs if split(r) != "train"], price, win)
    ss = {}
    for r in rs:
        ss.setdefault(seas(r), []).append(r)
    ups = sum(bet(v, price, win)[2] > 0 for v in ss.values())
    if out:
        print(f"  {name:58s} n {n:5d} {w:5d}-{n - w:<5d} {roi:+6.1f}% z {z:+5.2f} | train {tr[2]:+6.1f}% ({tr[0]:4d}) | held {he[2]:+6.1f}% ({he[0]:4d}) | seasons up {ups}/{len(ss)}")
    return dict(n=n, w=w, roi=roi, z=z, train=tr[2], held=he[2], ntr=tr[0], nhe=he[0], up=ups, ns=len(ss))
