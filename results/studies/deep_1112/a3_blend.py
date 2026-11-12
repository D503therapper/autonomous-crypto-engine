"""11/12 DEEP PROGRAM - A3: THE BLEND'S THREE DAILY-FIT KNOBS (sports_model.tune: 'cal' = the favorite / longshot
bias, 'hdog' = the home-dog shade, 'move_w' = the line move) - ARE THEY SIGNAL OR NOISE?
The live tune fits them every day on the LAST 900 games with odds (lam 8). Here, on every close we hold (2018-26):
  1. the LONG-RUN value of each knob (train to 2021 / blind 2022 on), with its standard error;
  2. the ROLLING 900-game value as the live tune fits it: how far it swings;
  3. the honest test: each game priced with the knobs fit on the 900 games BEFORE it (re-fit every 150 games) vs the
     plain no-vig close vs the knobs fit on EVERY earlier game (an expanding window) vs heavier shrinkage - log loss
     and the calibration of the dog / home-dog / favorite cells. No look-ahead anywhere.
Usage: python results/studies/deep_1112/a3_blend.py > results/studies/deep_1112/a3_blend.out"""
import math
import dlib as D
import lib as L          # results/studies/fifteen_1112/lib.py


def novig(h, a):
    ph, pa = 1 / D.dec(h), 1 / D.dec(a)
    return ph / (ph + pa)


def rows(lg):
    out = []
    for g in L.table(lg):
        if not g["mlh"] or not g["mla"] or g["hs"] == g["as"]:
            continue
        m = novig(g["mlh"], g["mla"])
        mo = novig(g["oh"], g["oa"]) if g["oh"] and g["oa"] else None
        hd = 1.0 if m < 0.5 and not g["neutral"] else 0.0
        mv = (D.logit(m) - D.logit(mo)) if mo is not None else 0.0
        out.append({"m": m, "lm": D.logit(m), "hd": hd, "mv": mv, "y": 1.0 if g["hs"] > g["as"] else 0.0,
                    "season": g["season"], "start": g["start"], "has_open": mo is not None, "g": g})
    out.sort(key=lambda r: r["start"])
    return out


def fit(rs, lam, cols=("mv", "lm", "hd")):
    X = [[r[c] for c in cols] for r in rs]
    return D.fit_offset(X, [r["y"] for r in rs], [r["lm"] for r in rs], lam=lam)


def price(r, w, cols=("mv", "lm", "hd")):
    return D.sig(r["lm"] + sum(a * r[c] for a, c in zip(w, cols)))


for lg in ("nfl", "ncaaf", "nba", "ncaab", "nhl"):
    R = rows(lg)
    print(f"\n==== {lg.upper()}: {len(R)} games with a closing moneyline, {R[0]['start'][:10]} -> {R[-1]['start'][:10]}")
    for nm, sel in (("train to 2021", lambda r: r["season"] <= 2021), ("blind 2022 on", lambda r: r["season"] >= 2022), ("all", lambda r: True)):
        rs = [r for r in R if sel(r)]
        w, se = fit(rs, 1e-6, ("lm", "hd"))
        D.CELLS[0] += 1
        print(f"  long run, {nm:14s} n {len(rs):5d}: cal {w[0]:+.3f} (se {se[0]:.3f})  hdog {w[1]:+.3f} (se {se[1]:.3f})")
    ro = [r for r in R if r["has_open"]]
    if len(ro) > 500:
        w, se = fit(ro, 1e-6)
        print(f"  long run with an open (n {len(ro)}): move_w {w[0]:+.3f} (se {se[0]:.3f})  cal {w[1]:+.3f} (se {se[1]:.3f})  hdog {w[2]:+.3f} (se {se[2]:.3f})")
    # 2 + 3: the rolling fit as the live tune does it
    STEP = 150
    preds = {"market": [], "live (last 900, lam 8)": [], "last 900, lam 80": [], "last 900, lam 400": [],
             "every earlier game, lam 8": [], "cal + hdog only, every earlier game": []}
    ys, keep = [], []
    swing = []
    start = 900
    for i in range(start, len(R), STEP):
        win = R[i - 900:i]
        w8, _ = fit(win, 8.0)
        w80, _ = fit(win, 80.0)
        w400, _ = fit(win, 400.0)
        wall, _ = fit(R[:i], 8.0)
        wch, _ = fit(R[:i], 8.0, ("lm", "hd"))
        swing.append(w8)
        for r in R[i:i + STEP]:
            ys.append(r["y"])
            keep.append(r)
            preds["market"].append(r["m"])
            preds["live (last 900, lam 8)"].append(price(r, w8))
            preds["last 900, lam 80"].append(price(r, w80))
            preds["last 900, lam 400"].append(price(r, w400))
            preds["every earlier game, lam 8"].append(price(r, wall))
            preds["cal + hdog only, every earlier game"].append(price(r, wch, ("lm", "hd")))
    for j, nm in enumerate(("move_w", "cal", "hdog")):
        v = [w[j] for w in swing]
        mu = sum(v) / len(v)
        print(f"  the rolling 900-game {nm:6s}: mean {mu:+.3f}, sd {math.sqrt(sum((x - mu) ** 2 for x in v) / len(v)):.3f}, min {min(v):+.3f}, max {max(v):+.3f} over {len(v)} re-fits")
    base = D.ll(preds["market"], ys)
    print(f"  the honest test on {len(ys)} games (each priced by knobs fit only on earlier games):")
    for nm, ps in preds.items():
        D.CELLS[0] += 1
        d = [(-(y * math.log(p) + (1 - y) * math.log(1 - p))) - (-(y * math.log(m) + (1 - y) * math.log(1 - m))) for p, m, y in zip(ps, preds["market"], ys)]
        mu = sum(d) / len(d)
        sd = math.sqrt(sum((x - mu) ** 2 for x in d) / len(d))
        z = mu / (sd / math.sqrt(len(d))) if sd else 0.0
        # the cells the board leans on
        def cellmiss(sel):
            rs = [(p if True else 0, r) for p, r in zip(ps, keep) if sel(p, r)]
            if not rs:
                return "n 0"
            said = sum(p for p, _ in rs) / len(rs)
            mk = sum(r["m"] for _, r in rs) / len(rs)
            won = sum(r["y"] for _, r in rs) / len(rs)
            return f"n {len(rs):5d} said {100 * said:4.1f} mkt {100 * mk:4.1f} won {100 * won:4.1f}"
        print(f"    {nm:38s} logloss {D.ll(ps, ys):.5f} ({mu:+.5f} vs the close, z {z:+.1f}) | home dog: {cellmiss(lambda p, r: r['hd'] == 1)} | home fav 55-65%: {cellmiss(lambda p, r: 0.55 <= r['m'] < 0.65)}")
    # how often the live blend alone makes a -150..-101 favorite 'beat its price' (the own-read gate) and how those did
    for nm in ("live (last 900, lam 8)", "every earlier game, lam 8"):
        ps = preds[nm]
        for lab, side in (("home", 1), ("road", 0)):
            sel = []
            for p, r in zip(ps, keep):
                g = r["g"]
                o = g["mlh"] if side else g["mla"]
                pp = p if side else 1 - p
                if 1 / D.dec(o) < pp:
                    sel.append({"dec": D.dec(o), "y": r["y"] if side else 1 - r["y"], "odds": o, "season": r["season"], "half": "train" if r["season"] <= 2021 else "held"})
            for band, f in (("fav -150..-101", lambda x: -150 <= x["odds"] <= -101), ("dog +100..+350", lambda x: 100 <= x["odds"] <= 350)):
                D.cell(f"{nm}: {lab} {band} the blend has OVER its price", [x for x in sel if f(x)])
    for lab, side in (("home", 1), ("road", 0)):
        for band, f in (("fav -150..-101", lambda o: -150 <= o <= -101), ("dog +100..+350", lambda o: 100 <= o <= 350)):
            al = [{"dec": D.dec(r["g"]["mlh"] if side else r["g"]["mla"]), "y": r["y"] if side else 1 - r["y"], "season": r["season"],
                   "half": "train" if r["season"] <= 2021 else "held"} for r in keep if f(r["g"]["mlh"] if side else r["g"]["mla"])]
            D.cell(f"BASE: every {lab} {band}", al)
print("\ncells:", D.CELLS[0])
