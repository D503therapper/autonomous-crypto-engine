"""THE 11/19 STUDY - every question the owner asked, one table each (olib.py has the rules).
Every cell: the side WITH the hole (the 'row' team) - how it did against its closing price (won % vs the no-vig close),
then the bet AGAINST it (the moneyline and the spread at the close, train 2016-21 | held out 2022-26, seasons up), the
same bet a point worse than the close, at the first fair price (2020-26), and a placebo (how many of 2,000 random sets
of the same size did as well).   Usage: python s1_cells.py > s1_cells.out"""
import math
import sys

import numpy as np

import olib

rows = olib.build()
print(f"team-games 2016-26 (a team's game 3+, both teams' starters known): {len(rows)}; seasons {min(r['season'] for r in rows)}-{max(r['season'] for r in rows)}")
st = [r["n_ol_st"] for r in rows]
print(f"starting offensive linemen found a team: mean {sum(st) / len(st):.2f} (tackles {sum(r['n_t_st'] for r in rows) / len(rows):.2f})")
for k in ("ol", "t", "db", "cb", "dl", "de"):
    print(f"  team-games with 1+ starting {k.upper()} out: {sum(1 for r in rows if r[k] >= 1)} ({100 * sum(1 for r in rows if r[k] >= 1) / len(rows):.0f}%)"
          f"   2+: {sum(1 for r in rows if r[k] >= 2)}   (report only 1+: {sum(1 for r in rows if r['r_' + k] >= 1)})")
POOL_ML = [x[1] for x in olib.ml(rows, fade=True)]
POOL_ATS = [x[1] for x in olib.ats(rows, fade=True)]
N_CELLS = [0]
CLEAR = []


def show(name, sel, placebo=True):
    N_CELLS[0] += 1
    print(f"\n--- {name}: {len(sel)} team-games")
    if len(sel) < 20:
        print("   too few")
        return
    print(f"   the side with the hole: {olib.vs_price(sel)}   mean margin vs the spread {np.mean([r['margin'] - r['sp'] for r in sel if r['sp'] is not None]):+.2f}")
    for label, xs, pool in (("FADE it, moneyline at the close", olib.ml(sel), POOL_ML), ("FADE it, the spread at the close", olib.ats(sel), POOL_ATS)):
        txt, a, b, allc = olib.cell(xs)
        pl = olib.placebo(pool, allc["n"], allc["roi"]) if placebo and allc else None
        print(f"   {label:34s} {txt}" + (f" | placebo {pl}/2000" if pl is not None else ""))
        if a and b and a["roi"] > 0 and b["roi"] > 0 and allc["z"] >= 2 and pl is not None and pl < 100:
            CLEAR.append((name, label, txt, pl))
        if a and b and a["roi"] < 0 and b["roi"] < 0 and allc["z"] <= -2 and pl is not None and pl < 100:
            CLEAR.append((name, label + " (the BACK side wins)", txt, pl))
    print(f"   {'  ...a point worse, moneyline':34s} {olib.cell(olib.ml(sel, worse=0.01))[0]}")
    print(f"   {'  ...a point worse, the spread':34s} {olib.cell(olib.ats(sel, worse=1.0))[0]}")
    ffm = olib.ml([r for r in sel if r['ff_d']], key=("ff_d", "ff_d_opp"))
    if len(ffm) >= 20:
        mv = [1 / r["d"] / (1 / r["d"] + 1 / r["d_opp"]) - 1 / r["ff_d"] / (1 / r["ff_d"] + 1 / r["ff_d_opp"]) for r in sel if r["ff_d"]]
        print(f"   {'  ...at the FIRST FAIR price, ML':34s} {olib.cell(ffm)[0]}   (its price moved {100 * np.mean(mv):+.1f} pts of win chance by the close)")
        ffs = [r for r in sel if r["ff_sp"] is not None]
        if len(ffs) >= 20:
            print(f"   {'  ...at the FIRST FAIR spread':34s} {olib.cell(olib.ats(ffs, key='ff_sp'))[0]}   (the number moved {np.mean([r['sp'] - r['ff_sp'] for r in ffs if r['sp'] is not None]):+.2f} pts)")


print("\n================ (a) STARTING OFFENSIVE LINEMEN OUT")
show("1 starting OL out (exactly)", [r for r in rows if r["ol"] == 1])
show("2 starting OL out (exactly)", [r for r in rows if r["ol"] == 2])
show("3+ starting OL out", [r for r in rows if r["ol"] >= 3])
show("2+ starting OL out", [r for r in rows if r["ol"] >= 2])
show("2+ starting OL out - on the REPORT only (no injured-reserve proxy)", [r for r in rows if r["r_ol"] >= 2])
show("1+ starting TACKLE out", [r for r in rows if r["t"] >= 1])
show("BOTH starting tackles out (2+ T)", [r for r in rows if r["t"] >= 2])
show("2+ more starting OL out than the opponent", [r for r in rows if r["ol"] - r["o_ol"] >= 2])
show("2+ starting OL out AND a DOG +100..+350", [r for r in rows if r["ol"] >= 2 and 2.0 <= r["d"] <= 4.5])
show("2+ starting OL out AND a FAVORITE", [r for r in rows if r["ol"] >= 2 and r["d"] < 1.91])
print("\n   ...against the other side's PASS RUSH (sacks per drop-back this season, top third of the week)")
show("1+ starting OL out vs a top-third pass rush", [r for r in rows if r["ol"] >= 1 and r["rush_top"]])
show("1+ starting OL out vs a bottom-third pass rush", [r for r in rows if r["ol"] >= 1 and r.get("rush_bot")])
show("2+ starting OL out vs a top-third pass rush", [r for r in rows if r["ol"] >= 2 and r["rush_top"]])
show("1+ starting TACKLE out vs a top-third pass rush", [r for r in rows if r["t"] >= 1 and r["rush_top"]])
show("1+ starting TACKLE out vs a top-third QB-hit rate", [r for r in rows if r["t"] >= 1 and r["hits_top"]])

print("\n================ (b) STARTING CORNERS / SAFETIES OUT")
show("1 starting DB out (exactly)", [r for r in rows if r["db"] == 1])
show("2+ starting DBs out", [r for r in rows if r["db"] >= 2])
show("3+ starting DBs out", [r for r in rows if r["db"] >= 3])
show("1+ starting CB out", [r for r in rows if r["cb"] >= 1])
show("2+ starting CBs out", [r for r in rows if r["cb"] >= 2])
show("1+ starting safety out", [r for r in rows if r["s"] >= 1])
show("1+ starting CB out vs a top-third passing offense", [r for r in rows if r["cb"] >= 1 and r["pass_top"]])
show("2+ starting DBs out vs a top-third passing offense", [r for r in rows if r["db"] >= 2 and r["pass_top"]])
show("2+ starting DBs out vs a bottom-third passing offense", [r for r in rows if r["db"] >= 2 and r.get("pass_bot")])

print("\n================ (c) THE MEN UP FRONT ON DEFENSE OUT (DE / DT / NT, 50%+ of the snaps)")
show("1+ starting DL out", [r for r in rows if r["dl"] >= 1])
show("2+ starting DL out", [r for r in rows if r["dl"] >= 2])
show("1+ starting DE (edge) out", [r for r in rows if r["de"] >= 1])
show("1+ starting LB out (the 3-4 edge men are listed LB)", [r for r in rows if r["lb"] >= 1])

print("\n================ (d) THE COMBINATION: our line down + their rush healthy")
show("1+ OL out, the other side's starting DL all in", [r for r in rows if r["ol"] >= 1 and r["o_dl"] == 0])
show("1+ OL out, the other side missing a starting DL", [r for r in rows if r["ol"] >= 1 and r["o_dl"] >= 1])
show("2+ OL out, the other side's DL all in + a top-third pass rush", [r for r in rows if r["ol"] >= 2 and r["o_dl"] == 0 and r["rush_top"]])
show("1+ tackle out, the other side's starting edge all in + top-third rush", [r for r in rows if r["t"] >= 1 and r["o_de"] == 0 and r["rush_top"]])
show("OL AND secondary both hit (1+ OL and 1+ DB out)", [r for r in rows if r["ol"] >= 1 and r["db"] >= 1])
show("3+ of these starters out in all (OL + DB + DL)", [r for r in rows if r["ol"] + r["db"] + r["dl"] >= 3])
show("3+ MORE of these starters out than the opponent", [r for r in rows if (r["ol"] + r["db"] + r["dl"]) - (r["o_ol"] + r["o_db"] + r["o_dl"]) >= 3])

print("\n================ QUESTIONABLE starters (the report's coin flips)")
show("1+ starting OL questionable", [r for r in rows if r["q_ol"] >= 1], placebo=False)
show("1+ starting DB questionable", [r for r in rows if r["q_db"] >= 1], placebo=False)

# ---------------------------------------------------------------- on top of the close: one fit
print("\n================ ON TOP OF THE CLOSING LINE (logistic: the home team's no-vig close + the GAP in starters out, home minus away;"
      "\n                 a + number = the side whose OPPONENT misses more wins more than its price)")
home = [r for r in rows if r["home"] and r["win"] != 0.5]


def fit(X, y, off, it=60):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-(off + X @ b)))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
        b = b + np.linalg.solve(H, X.T @ (y - p))
    p = 1 / (1 + np.exp(-(off + X @ b)))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(X.shape[1]))
    return b, np.sqrt(np.diag(cov))


for name, ks in (("OL", ["ol"]), ("tackles", ["t"]), ("DB", ["db"]), ("CB", ["cb"]), ("DL", ["dl"]), ("OL + DB + DL together", ["ol", "db", "dl"]),
                 ("all the unseen starters, one number", ["__sum"])):
    for half, sel in (("train 2016-21", [r for r in home if r["season"] in olib.TRAIN]), ("held 2022-26", [r for r in home if r["season"] not in olib.TRAIN])):
        def col(r, k):
            if k == "__sum":
                return (r["o_ol"] + r["o_db"] + r["o_dl"]) - (r["ol"] + r["db"] + r["dl"])
            return r["o_" + k] - r[k]
        X = np.array([[col(r, k) for k in ks] for r in sel], float)
        y = np.array([r["win"] for r in sel], float)
        off = np.array([math.log(r["p"] / (1 - r["p"])) for r in sel])
        b, se = fit(X, y, off)
        N_CELLS[0] += len(ks)
        print(f"  {name:38s} {half}: " + "  ".join(f"{k} {bb:+.3f} (z {bb / s:+.1f}; ~{100 * bb * 0.25:+.1f} pts a starter)" for k, bb, s in zip(ks, b, se)))

# ---------------------------------------------------------------- what the engine's weight should see: the count gap
print("\n================ THE ENGINE'S 'MORE BANGED-UP SIDE' COUNT, WITH THESE MEN IN IT (the 11/11 book study's cell, re-cut on COUNTS:"
      "\n                 the NFL dog +100..+350 with MORE of these starters out than the favorite - the bet ON that dog)")
for gap in (1, 2, 3):
    sel = [r for r in rows if 2.0 <= r["d"] <= 4.5 and (r["ol"] + r["db"] + r["dl"]) - (r["o_ol"] + r["o_db"] + r["o_dl"]) >= gap]
    print(f"  the dog has {gap}+ more OL / DB / DL starters out: {olib.vs_price(sel)}")
    print(f"       BACK it, moneyline at the close: {olib.cell(olib.ml(sel, fade=False))[0]}")
for gap in (1, 2):
    sel = [r for r in rows if 2.0 <= r["d"] <= 4.5 and r["ol"] - r["o_ol"] >= gap]
    print(f"  the dog has {gap}+ more OL starters out: {olib.vs_price(sel)}")
    print(f"       BACK it, moneyline at the close: {olib.cell(olib.ml(sel, fade=False))[0]}")
    sel = [r for r in rows if 2.0 <= r["d"] <= 4.5 and r["o_ol"] - r["ol"] >= gap]
    print(f"  the dog's OPPONENT has {gap}+ more OL starters out: {olib.vs_price(sel)}")
    print(f"       BACK it, moneyline at the close: {olib.cell(olib.ml(sel, fade=False))[0]}")

print(f"\n{N_CELLS[0]} cells / coefficients looked at; at |z| 2 about {N_CELLS[0] * 0.05:.0f} would clear by luck")
print("CELLS THAT CLEAR THE BAR (both halves the same sign, |z| 2+ overall, placebo under 5%):")
for c in CLEAR:
    print("  ", c)
if not CLEAR:
    print("   none")
sys.stdout.flush()
