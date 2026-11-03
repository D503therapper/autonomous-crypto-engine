"""Are the big model-vs-OPEN disagreements real prices or bad opens? For the open cell (lag-2 model 12+ points off the
open's no-vig, both teams 6+ games): the open's overround, how far open -> close moved, how many flip favorite, how many
opens sit at a placeholder (-110/-110, +100/-100, even), and the same cell with the suspicious opens taken out.
Usage: python open_sanity.py [out.txt]"""
import math
import os
import pickle
import sys
from collections import Counter

import numpy as np

import lib
from analyze import fit_logit, sig


def main():
    gs, _ = lib.data()
    preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final_lag2.pkl"), "rb"))
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    w = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]), np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
    out = []
    rows_all = []
    for g in gs:
        if g["season"] not in lib.HELD or g["id"] not in preds or g["hs"] == g["as_"]:
            continue
        if None in (g["ml_h"], g["ml_a"], g["mlo_h"], g["mlo_a"]):
            continue
        p = preds[g["id"]]
        pm = float(sig(w[0] + w[1] * p["mh"]))
        po, pc = lib.nv(g["mlo_h"], g["mlo_a"]), lib.nv(g["ml_h"], g["ml_a"])
        side_h = pm > po
        e = abs(pm - po)
        oo = g["mlo_h"] if side_h else g["mlo_a"]
        if not (-400 <= oo <= 350):
            continue
        gn = min(p["gn_h"], p["gn_a"])
        over = 1 / lib.dec(g["mlo_h"]) + 1 / lib.dec(g["mlo_a"]) - 1
        won = (g["hs"] > g["as_"]) == side_h
        pcs = pc if side_h else 1 - pc
        rows_all.append(dict(g=g, e=e, gn=gn, over=over, move=abs(pc - po), flip=(po - 0.5) * (pc - 0.5) < 0,
                             ph=(abs(g["mlo_h"]) in (100, 105, 110) and abs(g["mlo_a"]) in (100, 105, 110)),
                             roi=lib.ml_profit(oo, won), ev=pcs * lib.dec(oo) - 1, clv=(pc - po) * (1 if side_h else -1)))
    for label, sel in (("every open 2023-25", lambda r: True),
                       ("THE CELL: model 12+ off the open, both 6+ games", lambda r: r["e"] >= 0.12 and r["gn"] >= 6),
                       ("model 8+ off, both 6+", lambda r: r["e"] >= 0.08 and r["gn"] >= 6)):
        rs = [r for r in rows_all if sel(r)]
        ov = np.array([r["over"] for r in rs])
        mv = np.array([r["move"] for r in rs])
        out.append(f"{label}: n {len(rs)} | open overround median {np.median(ov):.1%} (under 2%: {np.mean(ov < 0.02):.0%}, "
                   f"over 8%: {np.mean(ov > 0.08):.0%}) | open->close move median {np.median(mv) * 100:.1f} pts, 90th pct "
                   f"{np.quantile(mv, 0.9) * 100:.1f} | favorite flips {np.mean([r['flip'] for r in rs]):.0%} | "
                   f"placeholder-looking opens {np.mean([r['ph'] for r in rs]):.0%}")
        clean = [r for r in rs if 0.02 <= r["over"] <= 0.08 and not r["ph"] and r["move"] < 0.15]
        if clean:
            by = {s: [r for r in clean if r["g"]["season"] == s] for s in lib.HELD}
            ev = np.array([r["ev"] for r in clean])
            out.append(f"   clean opens only (overround 2-8%, no placeholder, moved under 15 pts): n {len(clean)} open ROI "
                       f"{np.mean([r['roi'] for r in clean]):+.1%} | close-implied EV {ev.mean():+.2%} (+/- "
                       f"{ev.std() / math.sqrt(len(ev)):.2%}) | CLV {np.mean([r['clv'] for r in clean]) * 100:+.2f} | "
                       + " ".join(f"{s}: {np.mean([r['roi'] for r in v]):+.1%} / EV {np.mean([r['ev'] for r in v]):+.1%} ({len(v)})"
                                  for s, v in by.items() if v))
    big = sorted([r for r in rows_all if r["e"] >= 0.12 and r["gn"] >= 6], key=lambda r: -r["move"])[:15]
    out.append("\nthe 15 biggest open->close moves in THE CELL:")
    for r in big:
        g = r["g"]
        out.append(f"  {g['start'][:10]} {g['an']} @ {g['hn']}: open {g['mlo_a']:+.0f}/{g['mlo_h']:+.0f} close "
                   f"{g['ml_a']:+.0f}/{g['ml_h']:+.0f} final {g['as_']:.0f}-{g['hs']:.0f}")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
