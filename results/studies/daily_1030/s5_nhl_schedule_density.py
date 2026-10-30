"""STUDY 5 (10/30) - NHL SCHEDULE DENSITY beyond the back-to-back: the 3rd game in 4 nights and the 4th in 6 (never run
for hockey - the 10/21 fatigue study was the NBA; the hockey engine weighs only the back-to-back and rest days).
Every regular-season NHL side at the close 2018-26 (the dates of every real game count, priced or not).
Cells: 3-in-4 NOT on a back-to-back tonight, 3-in-4 that IS a b2b, 4-in-6, each vs an opponent that is NOT dense;
the team as a dog +100..+350 / favorite -101..-150, and the rested opponent across from it.
TRAIN 2018-22, HELD OUT 2023 / 2024 / 2025 apart, NOW 2026."""
import json
import os
from datetime import datetime

import lib

TRAIN, HELD = (2018, 2022), [2023, 2024, 2025, 2026]


def rows_for():
    games = sorted((g for g in lib.sd.load_games("nhl").values()
                    if (g.get("stype") or "?") in lib.sd.REAL and g.get("start")), key=lambda g: g["start"])
    dates = {}
    for g in games:
        d = datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
        dloc = (d.timestamp() - 5 * 3600) // 86400           # a hockey 'night' (ET-ish day index)
        for t in (g["home"], g["away"]):
            dates.setdefault(t, []).append((dloc, g["id"]))
    idx = {}
    for t, lst in dates.items():
        for i, (dl, gid) in enumerate(lst):
            prev = [x for x, _ in lst[max(0, i - 4):i]]
            b2b = bool(prev) and dl - prev[-1] == 1
            in4 = 1 + sum(1 for x in prev if dl - x <= 3)
            in6 = 1 + sum(1 for x in prev if dl - x <= 5)
            idx[(t, gid)] = {"b2b": b2b, "in4": in4, "in6": in6}
    out = []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            mh, ma = float(g["ml_home"]), float(g["ml_away"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or abs(mh) < 100 or abs(ma) < 100:
            continue
        s = lib.season(g["start"])
        for side, t, o, ml in (("home", g["home"], g["away"], mh), ("away", g["away"], g["home"], ma)):
            out.append({"season": s, "me": idx[(t, g["id"])], "op": idx[(o, g["id"])], "d": lib.dec(ml),
                        "won": (hs > as_) == (side == "home"), "home": side == "home"})
    return out


def main():
    rows = rows_for()
    lines, res = [f"=== NHL: {len(rows)} priced sides ==="], {}

    def dense(x):
        return x["in4"] >= 3 or x["in6"] >= 4
    cells = {
        "3rd in 4, NOT a b2b tonight, opp not dense": lambda r: r["me"]["in4"] >= 3 and not r["me"]["b2b"] and not dense(r["op"]),
        "3rd in 4 AND a b2b tonight, opp not dense": lambda r: r["me"]["in4"] >= 3 and r["me"]["b2b"] and not dense(r["op"]),
        "4th in 6, opp not dense": lambda r: r["me"]["in6"] >= 4 and not dense(r["op"]),
        "4th in 6, NOT a b2b tonight, opp not dense": lambda r: r["me"]["in6"] >= 4 and not r["me"]["b2b"] and not dense(r["op"]),
        "4th in 6, NOT b2b, opp not dense / not b2b": lambda r: r["me"]["in6"] >= 4 and not r["me"]["b2b"] and not dense(r["op"]) and not r["op"]["b2b"],
        "b2b but NOT 3 in 4 (the built weight's own cell)": lambda r: r["me"]["b2b"] and r["me"]["in4"] < 3 and not dense(r["op"]),
        "OPP 3rd in 4 not b2b, me not dense": lambda r: r["op"]["in4"] >= 3 and not r["op"]["b2b"] and not dense(r["me"]),
        "OPP 4th in 6, me not dense": lambda r: r["op"]["in6"] >= 4 and not dense(r["me"]),
        "neither dense, neither b2b (base)": lambda r: not dense(r["me"]) and not dense(r["op"]) and not r["me"]["b2b"] and not r["op"]["b2b"],
    }
    for nm, fn in cells.items():
        cell = [r for r in rows if fn(r)]
        for tag, lo, hi in (("dog +100..+350", 2.0, 4.5), ("fav -101..-150", 1.6667, 2.0)):
            b = [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if lo <= r["d"] <= hi]
            s = lib.summ(b, TRAIN, HELD)
            res[f"{nm} {tag}"] = s
            lines.append(lib.fmt(f"{nm[:44]} {tag}", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s5_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, "s5_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
