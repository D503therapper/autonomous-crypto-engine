"""S2 - A COLLEGE HOOPS OPENING-LINE PLAY? (the NBA one's idea, rebuilt for college: predict the OPEN -> CLOSE move
from what is known when the open posts, then buy the side the market will move to, at the open.)

Not a repeat of 10/30's s6 (the NBA module's 37-input win model ported - flat): this one targets the MOVE (closing
no-vig minus opening no-vig = closing-line value), which is far less noisy than results, so three seasons of opens can
fit and test it. Walk-forward: fit 2023 -> test 2024; fit 2023-24 -> test 2025. Graded at the OPEN (what we'd get)
and by CLV (the move itself).

Inputs per side, all known before the open (the side's view): the open's no-vig logit; our results-Elo win chance
minus the open (ratings vs the open); the side's and the opponent's last-game cover margin (margin + closing spread)
and last-5 average cover margin (the market's miss on them lately); last game won; rest days both; home / neutral;
game number (early season); tier (power / mid / low) of both. FAIR flag = both teams' last games 3+ nights before
tip (the open, ~46h out in 2026's feed, was then posted AFTER both last games - the live 'ready' rule); unfair rows
show how much is just the open being stale."""
import math
from collections import defaultdict

import lib

out = lib.Out("s2_open_play", train=(2023,), held=(2024, 2025))
R = lib.nc_sides()


def feats(x):
    if x.get("po") is None or x.get("p") is None or x["stype"] != "2":
        return None
    if not (0.03 < x["po"] < 0.97):
        return None
    hadv = 0 if x["neutral"] else (75 if x["side"] == "home" else -75)
    ep = 1 / (1 + 10 ** (-(x["elo"] - x["oelo"] + hadv) / 400))

    def cov_hist(i, k):
        v = []
        while i is not None and len(v) < k:
            r = R[i]
            if r.get("sp") is not None:
                v.append(r["margin"] + r["sp"])
            i = r.get("prev_i")
        return v
    me = cov_hist(x.get("prev_i"), 5)
    # opponent's row for this game = the other side of the same id: find via its own prev chain
    return me, ep, hadv


# index both sides of each game
by_id = defaultdict(list)
for i, x in enumerate(R):
    by_id[x["id"]].append(i)


def cov_hist(i, k):
    v = []
    while i is not None and len(v) < k:
        r = R[i]
        if r.get("sp") is not None:
            v.append(r["margin"] + r["sp"])
        i = r.get("prev_i")
    return v


RK = {"power": 2, "mid": 1, "low": 0, "none": -1}
rows = []
for gid, ii in by_id.items():
    if len(ii) != 2:
        continue
    for a, b in ((ii[0], ii[1]), (ii[1], ii[0])):
        x, o = R[a], R[b]
        if x["season"] not in (2023, 2024, 2025) or x["stype"] != "2" or x.get("po") is None or x.get("p") is None:
            continue
        if not (0.05 < x["po"] < 0.95):
            continue
        hadv = 0 if x["neutral"] else (75 if x["side"] == "home" else -75)
        ep = 1 / (1 + 10 ** (-(x["elo"] - x["oelo"] + hadv) / 400))
        mc, oc = cov_hist(x.get("prev_i"), 5), cov_hist(o.get("prev_i"), 5)
        lp = R[x["prev_i"]] if x.get("prev_i") is not None else None
        olp = R[o["prev_i"]] if o.get("prev_i") is not None else None
        rest = x.get("rest") or 7
        orest = x.get("orest") or 7
        f = {
            "lo": math.log(x["po"] / (1 - x["po"])),
            "elo_gap": ep - x["po"],
            "last_cov": mc[0] / 10 if mc else 0.0,
            "olast_cov": oc[0] / 10 if oc else 0.0,
            "cov5": (sum(mc) / len(mc) / 10) if mc else 0.0,
            "ocov5": (sum(oc) / len(oc) / 10) if oc else 0.0,
            "last_won": (1 if lp and lp["won"] else -1) if lp else 0,
            "olast_won": (1 if olp and olp["won"] else -1) if olp else 0,
            "rest": min(rest, 7) / 7, "orest": min(orest, 7) / 7,
            "home": 1 if (x["side"] == "home" and not x["neutral"]) else 0,
            "away": 1 if (x["side"] == "away" and not x["neutral"]) else 0,
            "early": 1 if x["gn"] <= 5 else 0,
            "tier": RK.get(x["tier"], -1), "otier": RK.get(x["otier"], -1),
        }
        fair = (x.get("rest") or 9) >= 3 and (x.get("orest") or 9) >= 3
        rows.append({"x": x, "f": f, "y": x["p"] - x["po"], "fair": fair, "season": x["season"],
                     "gt": "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L")})
KEYS = list(rows[0]["f"])
out.note(f"sides with an open 2023-25: {len(rows)} (fair {sum(r['fair'] for r in rows)})")


def ridge(tr, lam=50.0):
    """Least squares with a ridge (standardized inputs), pure Python normal equations."""
    k = len(KEYS)
    mu = [sum(r["f"][c] for r in tr) / len(tr) for c in KEYS]
    sd = [max(1e-6, math.sqrt(sum((r["f"][c] - mu[j]) ** 2 for r in tr) / len(tr))) for j, c in enumerate(KEYS)]
    ym = sum(r["y"] for r in tr) / len(tr)
    A = [[0.0] * k for _ in range(k)]
    bvec = [0.0] * k
    for r in tr:
        z = [(r["f"][c] - mu[j]) / sd[j] for j, c in enumerate(KEYS)]
        yy = r["y"] - ym
        for i in range(k):
            bvec[i] += z[i] * yy
            zi = z[i]
            Ai = A[i]
            for j in range(k):
                Ai[j] += zi * z[j]
    for i in range(k):
        A[i][i] += lam
    # solve
    M = [A[i][:] + [bvec[i]] for i in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(M[r_][c]))
        M[c], M[p] = M[p], M[c]
        for r_ in range(k):
            if r_ != c and M[c][c]:
                fct = M[r_][c] / M[c][c]
                for j in range(c, k + 1):
                    M[r_][j] -= fct * M[c][j]
    w = [M[i][k] / M[i][i] for i in range(k)]
    return mu, sd, w, ym


def pred(m, r):
    mu, sd, w, ym = m
    return ym + sum(w[j] * (r["f"][c] - mu[j]) / sd[j] for j, c in enumerate(KEYS))


def r2(m, rs):
    ys = [r["y"] for r in rs]
    my = sum(ys) / len(ys)
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((r["y"] - pred(m, r)) ** 2 for r in rs)
    return 1 - sse / sst


for fair_only in (False, True):
    out.h(f"MOVE MODEL, walk-forward ({'FAIR rows only' if fair_only else 'all rows'})")
    allbets = defaultdict(list)
    for tr_s, te_s in (((2023,), 2024), ((2023, 2024), 2025)):
        tr = [r for r in rows if r["season"] in tr_s and (r["fair"] or not fair_only)]
        te = [r for r in rows if r["season"] == te_s and (r["fair"] or not fair_only)]
        m = ridge(tr)
        out.note(f"fit {tr_s} -> {te_s}: train R2 {r2(m, tr):.3f}, test R2 {r2(m, te):.3f}; weights " +
                 " ".join(f"{c}:{w*1000:+.1f}" for c, w in zip(KEYS, m[2])))
        for r in te:
            r["pm"] = pred(m, r)
        for thr in (0.01, 0.02, 0.03, 0.04):
            for r in te:
                if r["pm"] >= thr and -150 <= r["x"]["mlo"] <= 300:
                    allbets[thr].append(r)
    for thr, bs in allbets.items():
        clv = sum(r["y"] for r in bs) / len(bs) * 100 if bs else 0
        out.bets(f"pred move >= {thr*100:.0f} pts, open -150..+300, at the OPEN (clv {clv:+.2f})",
                 [(r["season"], lib.ml_pl(r["x"]["mlo"], r["x"]["won"])) for r in bs])
        out.bets("   same sides at the CLOSE", [(r["season"], lib.ml_pl(r["x"]["ml"], r["x"]["won"])) for r in bs])
        for g in ("P", "M", "L"):
            sb = [r for r in bs if r["gt"] == g]
            if sb:
                c = sum(r["y"] for r in sb) / len(sb) * 100
                out.bets(f"   tier {g} at the OPEN (clv {c:+.2f})", [(r["season"], lib.ml_pl(r["x"]["mlo"], r["x"]["won"])) for r in sb])
        for side in ("dog", "fav"):
            sb = [r for r in bs if (r["x"]["mlo"] > 0) == (side == "dog")]
            if sb:
                c = sum(r["y"] for r in sb) / len(sb) * 100
                out.bets(f"   {side}s at the OPEN (clv {c:+.2f})", [(r["season"], lib.ml_pl(r["x"]["mlo"], r["x"]["won"])) for r in sb])

out.h("ONE-INPUT CHECKS (all 3 seasons, fair rows): which single thing does the move follow?")
F = [r for r in rows if r["fair"]]
for c in KEYS:
    xs = [r["f"][c] for r in F]
    ys = [r["y"] for r in F]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / n
    vx = sum((a - mx) ** 2 for a in xs) / n
    vy = sum((b - my) ** 2 for b in ys) / n
    out.note(f"  {c:10s} corr with the move {cov / math.sqrt(vx * vy) if vx and vy else 0:+.3f}")
out.save()
