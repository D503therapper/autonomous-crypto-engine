"""STUDY 10 (10/30) - COLLEGE HOOPS PREP: THE NOVEMBER MARKET (the season opens early November).
Every college hoops side at the close, the first 5 weeks of each season (to Dec 10) vs the rest:
  (a) NEUTRAL-SITE early-season tournament games (the Thanksgiving events) - dogs +100..+350 / favorites -101..-150,
      vs the same-window home / road games;
  (b) each team's FIRST 3 games - favorites -101..-150 (the Lock band; the open 10/16 proposal "college hoops Locks small
      the first 2 weeks" has no study behind it) and dogs;
  (c) last season's record says the books are wrong early: a dog whose LAST season was .200+ better than the favorite's,
      in its first 5 games (the market over-moving on roster turnover?) - and the mirror.
TRAIN 2018-21 seasons, HELD OUT 2022 / 2023 / 2024 / 2025 apart (2025 = 2025-26)."""
import json
import os

import lib

TRAIN, HELD = (2018, 2021), [2022, 2023, 2024, 2025]


def main():
    games = sorted((g for g in lib.sd.load_games("ncaab").values() if (g.get("stype") or "?") in ("2",) and g.get("start")),
                   key=lambda g: g["start"])
    n, rec = {}, {}
    rows = []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        s = lib.season(g["start"])
        md = g["start"][5:10]
        early = md >= "10-01" and md <= "12-10"
        mh, ma = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
        neutral = str(g.get("neutral")) == "1"
        if mh and ma and abs(mh) >= 100 and abs(ma) >= 100 and hs != as_:
            for side, t, o, ml in (("home", g["home"], g["away"], mh), ("away", g["away"], g["home"], ma)):
                w, k = rec.get((t, s - 1), (0, 0))
                ow, ok = rec.get((o, s - 1), (0, 0))
                rows.append({"season": s, "early": early, "neutral": neutral, "home": side == "home",
                             "gn": n.get((t, s), 0) + 1, "ogn": n.get((o, s), 0) + 1,
                             "last": w / k if k >= 15 else None, "olast": ow / ok if ok >= 15 else None,
                             "d": lib.dec(ml), "won": (hs > as_) == (side == "home")})
        for t, m in ((g["home"], hs - as_), (g["away"], as_ - hs)):
            n[(t, s)] = n.get((t, s), 0) + 1
            w, k = rec.get((t, s), (0, 0))
            rec[(t, s)] = (w + (1 if m > 0 else 0), k + 1)
    lines, res = [f"=== COLLEGE HOOPS: {len(rows)} priced sides ==="], {}
    cells = {
        "EARLY neutral site": lambda r: r["early"] and r["neutral"],
        "EARLY home": lambda r: r["early"] and not r["neutral"] and r["home"],
        "EARLY road": lambda r: r["early"] and not r["neutral"] and not r["home"],
        "LATER neutral site": lambda r: not r["early"] and r["neutral"],
        "LATER home (base)": lambda r: not r["early"] and not r["neutral"] and r["home"],
        "LATER road (base)": lambda r: not r["early"] and not r["neutral"] and not r["home"],
        "team's games 1-3": lambda r: r["gn"] <= 3,
        "team's games 1-3, home": lambda r: r["gn"] <= 3 and r["home"] and not r["neutral"],
        "team's games 1-3, road / neutral": lambda r: r["gn"] <= 3 and not (r["home"] and not r["neutral"]),
        "team's games 4-10": lambda r: 4 <= r["gn"] <= 10,
        "team's games 11+": lambda r: r["gn"] >= 11,
        "games 1-5, LAST season .200+ better than the opp": lambda r: r["gn"] <= 5 and r["last"] is not None and r["olast"] is not None and r["last"] - r["olast"] >= 0.2,
        "games 1-5, LAST season .200+ worse than the opp": lambda r: r["gn"] <= 5 and r["last"] is not None and r["olast"] is not None and r["olast"] - r["last"] >= 0.2,
        "games 6+, LAST season .200+ better than the opp": lambda r: r["gn"] >= 6 and r["last"] is not None and r["olast"] is not None and r["last"] - r["olast"] >= 0.2,
    }
    for nm, fn in cells.items():
        cell = [r for r in rows if fn(r)]
        for tag, lo, hi in (("dog +100..+350", 2.0, 4.5), ("fav -101..-150", 1.6667, 2.0)):
            b = [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if lo <= r["d"] <= hi]
            s = lib.summ(b, TRAIN, HELD)
            res[f"{nm} {tag}"] = s
            lines.append(lib.fmt(f"{nm[:42]} {tag}", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s10_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, "s10_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
