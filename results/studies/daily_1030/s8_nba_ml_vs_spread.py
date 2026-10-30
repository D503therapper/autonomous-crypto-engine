"""STUDY 8 (10/30) - NBA: THE MONEYLINE vs ITS OWN SPREAD at the close (the 10/8 study was NFL / college only - college
was a LEAD there). The spread's win % comes from a curve P(win) = logistic(a + b * spread) fit ONLY on the train seasons;
the moneyline's is its no-vig number. Where the moneyline rates a side 2 / 3 / 4+ points CHEAPER than its spread says,
bet that moneyline (the cheap market); where it rates it 2-4+ points DEARER, the other side's moneyline.
TRAIN 2018-21 (the curve and the cuts), HELD OUT 2022 / 2023 / 2024 / 2025 apart, NOW 2026."""
import json
import math
import os

import lib

TRAIN, HELD = (2018, 2021), [2022, 2023, 2024, 2025, 2026]


def fit_curve(xs, ys):
    a, b = 0.0, -0.15
    for _ in range(50):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            p = 1 / (1 + math.exp(-(a + b * x)))
            r, w = p - y, p * (1 - p)
            ga += r
            gb += r * x
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        a, b = a - da, b - db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def main():
    games = [g for g in lib.sd.load_games("nba").values() if (g.get("stype") or "?") in ("2",)]
    rows = []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            mh, ma = float(g["ml_home"]), float(g["ml_away"])
            sp = float(g["spread_home"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or abs(mh) < 100 or abs(ma) < 100:
            continue
        rows.append({"season": lib.season(g["start"]), "sp": sp, "pml": lib.nv(mh, ma), "dh": lib.dec(mh), "da": lib.dec(ma),
                     "hw": hs > as_})
    tr = [r for r in rows if TRAIN[0] <= r["season"] <= TRAIN[1]]
    a, b = fit_curve([r["sp"] for r in tr], [1.0 if r["hw"] else 0.0 for r in tr])
    lines, res = [f"=== NBA: {len(rows)} games; curve P(home win) = logistic({a:.3f} + {b:.4f} * home spread), fit on {len(tr)} train games ==="], {}
    for cut in (0.02, 0.03, 0.04, 0.06):
        cheap_dog, cheap_fav, dear_other_dog, dear_other_fav = [], [], [], []
        for r in rows:
            psp = 1 / (1 + math.exp(-(a + b * r["sp"])))
            for side, pm, ps, d, od, won in (("home", r["pml"], psp, r["dh"], r["da"], r["hw"]),
                                            ("away", 1 - r["pml"], 1 - psp, r["da"], r["dh"], not r["hw"])):
                if ps - pm >= cut:                 # the moneyline is CHEAPER than the spread says -> bet it
                    if 2.0 <= d <= 4.5:
                        cheap_dog.append((r["season"], lib.profit(won, d)))
                    elif 1.6667 <= d < 2.0:
                        cheap_fav.append((r["season"], lib.profit(won, d)))
        for nm, b_ in (("ML cheaper than its spread -> ML dog +100..+350", cheap_dog),
                       ("ML cheaper than its spread -> ML fav -101..-150", cheap_fav)):
            s = lib.summ(b_, TRAIN, HELD)
            res[f"{nm} gap {cut}"] = s
            lines.append(lib.fmt(f"gap {cut*100:.0f}+ {nm}", s))
    base = []
    for r in rows:
        for d, won in ((r["dh"], r["hw"]), (r["da"], not r["hw"])):
            if 2.0 <= d <= 4.5:
                base.append((r["season"], lib.profit(won, d)))
    lines.append(lib.fmt("BASE every dog +100..+350", lib.summ(base, TRAIN, HELD)))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s8_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, "s8_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
