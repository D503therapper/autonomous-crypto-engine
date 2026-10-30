"""STUDY 7 (10/30) - NBA: THE FULL-GAME DOG THE BOOKS MAKE THE 1ST-HALF FAVORITE (the 1st-half flip).
The 10/29 flip study was NFL / college only (22 / 19 games); the NBA has thousands of closing 1st-half lines (2018-24).
A full-game dog +100..+350 whose 1st-half spread is 0 or less (favored / pick'em for the half), or whose 1st-half
moneyline is shorter than its full-game one by a lot, says the books think it starts strong and fades (a deep bench on
the other side / a short rotation on this one) - does the full-game dog win more or less than its price?
Also the mirror: the full-game favorite -101..-150 that is a 1st-half dog.
Graded at the closing full-game moneyline. TRAIN 2018-21, HELD OUT 2022 / 2023 / 2024 apart (the 1st-half lines thin out
after 2024)."""
import json
import os

import lib

TRAIN, HELD = (2018, 2021), [2022, 2023, 2024]


def main():
    games = [g for g in lib.sd.load_games("nba").values() if (g.get("stype") or "?") in ("2",)]
    rows = []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            mh, ma = float(g["ml_home"]), float(g["ml_away"])
            h1s = float(g["h1_spread_home"])
            sp = float(g["spread_home"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or abs(mh) < 100 or abs(ma) < 100:
            continue
        h1h, h1a = lib.num(g.get("h1_ml_home")), lib.num(g.get("h1_ml_away"))
        s = lib.season(g["start"])
        for side, ml, h1, full, h1ml in (("home", mh, h1s, sp, h1h), ("away", ma, -h1s, -sp, h1a)):
            rows.append({"season": s, "d": lib.dec(ml), "won": (hs > as_) == (side == "home"), "h1": h1, "full": full,
                         "share": (h1 / full) if full else None})
    lines, res = [f"=== NBA: {len(rows)} sides with a closing 1st-half spread ==="], {}
    cells = {
        "dog, 1st-half FAVORED / pick (h1 spread <= 0)": lambda r: r["full"] > 0 and r["h1"] <= 0,
        "dog, 1st-half spread under 30% of the full": lambda r: r["full"] > 0 and 0 < r["h1"] < 0.30 * r["full"],
        "dog, 1st-half share 0.30-0.45": lambda r: r["full"] > 0 and 0.30 * r["full"] <= r["h1"] < 0.45 * r["full"],
        "dog, 1st-half share 0.45-0.60 (normal)": lambda r: r["full"] > 0 and 0.45 * r["full"] <= r["h1"] < 0.60 * r["full"],
        "dog, 1st-half share 0.60+": lambda r: r["full"] > 0 and r["h1"] >= 0.60 * r["full"],
        "fav, 1st-half DOG (h1 spread > 0)": lambda r: r["full"] < 0 and r["h1"] > 0,
        "fav, 1st-half share under 0.30": lambda r: r["full"] < 0 and r["h1"] <= 0 and r["h1"] > 0.30 * r["full"],
    }
    for nm, fn in cells.items():
        cell = [r for r in rows if fn(r)]
        for tag, lo, hi in (("dog +100..+350", 2.0, 4.5), ("fav -101..-150", 1.6667, 2.0), ("any", 1.0, 99)):
            b = [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if lo <= r["d"] <= hi]
            s = lib.summ(b, TRAIN, HELD)
            res[f"{nm} {tag}"] = s
            lines.append(lib.fmt(f"{nm[:42]} {tag}", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s7_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, "s7_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
