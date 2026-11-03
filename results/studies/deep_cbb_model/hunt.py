"""THE CELL HUNT (the owner, 11/3: "keep going until you find an efficiency ... spreads, underdogs, slight favorites").
Every bet the model's disagreement with the CLOSE can make, cut every way (market x direction x size of the gap x stage
x tier x venue x price band x games played), 1-3 cuts at a time. THE PROTOCOL (multiple-testing aware): a cell is
CHOSEN only on TRAIN (2018-22: n >= 150, ROI >= +2%, 4+ of 5 seasons up); only the chosen cells are then read on the
held-out seasons 2023 / 2024 / 2025 - and the report says how many chosen cells would hold by luck alone.
Usage: python hunt.py PREDS.pkl [out.txt]"""
import itertools
import math
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import fit_logit, sig, tiers, game_tier


def main(path):
    gs, _ = lib.data()
    preds = pickle.load(open(path, "rb"))
    finals = pickle.load(open(path.replace(".pkl", "_finals.pkl"), "rb"))
    tr = tiers(gs, finals)
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    wc = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]),
                   np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
    season_start = {}
    for g in gs:
        season_start.setdefault(g["season"], g["night"])
    bets = defaultdict(lambda: defaultdict(list))     # cell -> season -> [profit]
    for g in gs:
        if g["id"] not in preds or g["season"] not in lib.TRAIN + lib.HELD:
            continue
        p = preds[g["id"]]
        d = g["night"] - season_start[g["season"]]
        stg = "openwk" if d <= 7 else lib.phase(g)
        ti = game_tier(tr, g)
        gn = min(p["gn_h"], p["gn_a"])
        gnb = "gn<6" if gn < 6 else "gn6-15" if gn < 16 else "gn16+"
        base = {"st": stg, "tier": ti, "gn": gnb}
        if g["spread"] is not None and g["sp_h_odds"] and g["sp_a_odds"] and g["spread"] != 0:
            dd = p["mh"] + g["spread"]
            if abs(dd) >= 2:
                side_h = dd > 0
                res = (g["hs"] - g["as_"] + g["spread"]) * (1 if side_h else -1)
                pl = lib.ats_profit(res, g["sp_h_odds"] if side_h else g["sp_a_odds"])
                fav = (g["spread"] < 0) == side_h
                ven = "neutral" if g["neutral"] else ("home" if side_h else "road")
                sz = abs(g["spread"])
                spb = "sp<4" if sz < 4 else "sp4-9.5" if sz < 10 else "sp10+"
                gap = "gap2-4" if abs(dd) < 4 else "gap4-6" if abs(dd) < 6 else "gap6+"
                add(bets, g["season"], pl, "ATS", {**base, "dir": "fav" if fav else "dog", "ven": ven, "price": spb,
                                                    "gap": gap})
        if g["ml_h"] is not None and g["ml_a"] is not None and g["hs"] != g["as_"]:
            pm = float(sig(wc[0] + wc[1] * p["mh"]))
            mk = lib.nv(g["ml_h"], g["ml_a"])
            for side_h, pp, mm, odds, won in ((True, pm, mk, g["ml_h"], g["hs"] > g["as_"]),
                                              (False, 1 - pm, 1 - mk, g["ml_a"], g["as_"] > g["hs"])):
                e = pp - mm
                if e < 0.03 or not (-300 <= odds <= 350):
                    continue
                pb = ("fav101-150" if odds >= -150 else "fav151-300") if odds < 0 else \
                    ("dog100-150" if odds <= 150 else "dog151-350")
                ven = "neutral" if g["neutral"] else ("home" if side_h else "road")
                gap = "edge3-6" if e < 0.06 else "edge6-10" if e < 0.10 else "edge10+"
                add(bets, g["season"], lib.ml_profit(odds, won), "ML",
                    {**base, "dir": "fav" if odds < 0 else "dog", "ven": ven, "price": pb, "gap": gap})
        if g["total"] is not None and g["o_odds"] and g["u_odds"]:
            dt = p["tot"] - g["total"]
            if abs(dt) >= 3:
                over = dt > 0
                res = (g["hs"] + g["as_"] - g["total"]) * (1 if over else -1)
                pl = lib.ats_profit(res, g["o_odds"] if over else g["u_odds"])
                tb = "tot<135" if g["total"] < 135 else "tot135-150" if g["total"] < 150 else "tot150+"
                gap = "gap3-6" if abs(dt) < 6 else "gap6+"
                add(bets, g["season"], pl, "TOT", {**base, "dir": "over" if over else "under", "ven": "-", "price": tb,
                                                    "gap": gap})
    out = []
    P = out.append
    chosen = []
    for cell, by in bets.items():
        tv = [x for s in lib.TRAIN for x in by.get(s, [])]
        if len(tv) < 150:
            continue
        roi = sum(tv) / len(tv)
        up = sum(1 for s in lib.TRAIN if by.get(s) and sum(by[s]) > 0)
        if roi >= 0.02 and up >= 4:
            chosen.append(cell)
    P(f"cells looked at on TRAIN (n >= 150): {sum(1 for c, by in bets.items() if sum(len(by.get(s, [])) for s in lib.TRAIN) >= 150)}"
      f" of {len(bets)}; CHOSEN on TRAIN (ROI >= +2%, 4+/5 seasons up): {len(chosen)}")
    held_ok = 0
    lines = []
    for cell in chosen:
        by = bets[cell]
        tv = [x for s in lib.TRAIN for x in by.get(s, [])]
        hv = [x for s in lib.HELD for x in by.get(s, [])]
        hup = sum(1 for s in lib.HELD if by.get(s) and sum(by[s]) > 0)
        hr = sum(hv) / len(hv) if hv else 0.0
        z = hr / (np.std(hv) / math.sqrt(len(hv))) if len(hv) > 2 and np.std(hv) > 0 else 0.0
        ok = hr > 0 and hup >= 3 - (1 if len(hv) < 0 else 0)
        held_ok += ok
        per = " ".join(f"{s}:{np.mean(by[s]):+.1%}/{len(by[s])}" for s in lib.HELD if by.get(s))
        lines.append((ok, hr, f"{'HOLDS' if ok else '     '} {cell:<70} TRAIN {sum(tv) / len(tv):+6.1%} on {len(tv):5d} | "
                               f"HELD {hr:+6.1%} on {len(hv):5d} ({hup}/3 up, z {z:+.1f}) [{per}]"))
    lines.sort(key=lambda x: (-x[0], -x[1]))
    for _, _, ln in lines:
        P(ln)
    P(f"\nchosen {len(chosen)} -> held 3/3 up and positive: {held_ok}. By luck alone (each held season a coin flip) about "
      f"{len(chosen) / 8:.1f} of {len(chosen)} would be 3/3 up.")
    txt = "\n".join(out)
    print(txt)
    return txt


DIMS = ("st", "tier", "gn", "dir", "ven", "price", "gap")


def add(bets, season, pl, mkt, f):
    for k in range(0, 4):
        for combo in itertools.combinations(DIMS, k):
            if "dir" not in combo and k == 3:
                continue
            key = mkt + " " + " ".join(f"{d}={f[d]}" for d in combo)
            bets[key][season].append(pl)


if __name__ == "__main__":
    t = main(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(t + "\n")
