"""STUDY 3 (10/30) - THE BOOKS' IMPLIED TEAM TOTAL vs WHAT THE MATCHUP HAS SHOWN (NFL, college football, NBA; NHL left out - its "spread" is the
1.5 puck line, so total/2 - spread/2 is not a goals read).
The closing total + spread give each side's implied points: total/2 - spread/2 (its own spread, minus = favored). The
matchup's form says: (its points scored a game + the opponent's points allowed a game) / 2 over this season's earlier
games (4+ each, regular season). When the books expect a side to score far LESS than the matchup has shown (the market
is down on that offense) - or far MORE - does that side win / cover more than its price says?
Graded at the closing moneyline (dogs +100..+350, favorites -101..-150) and ATS at the closing spread.
TRAIN through the 2022 season, HELD OUT 2023 / 2024 / 2025 apart, NOW 2026. Never-tested angle (the 10/14-10/29 totals
studies were dogs by the total's SIZE, not the team's share of it)."""
import json
import os

import lib

CUTS = {"nfl": (3.0, 6.0), "ncaaf": (4.0, 8.0), "nba": (4.0, 8.0), "nhl": (0.35, 0.7)}
TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]


def rows_for(lg):
    games = sorted((g for g in lib.sd.load_games(lg).values() if (g.get("stype") or "?") in ("2",)),
                   key=lambda g: g.get("start") or "")
    pts = {}       # (season, team) -> [(scored, allowed)]
    out = []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        s = lib.season(g["start"])
        tot, sp = lib.num(g.get("total")), lib.num(g.get("spread_home"))
        mh, ma = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
        ho, ao = lib.num(g.get("spread_home_odds")), lib.num(g.get("spread_away_odds"))
        ph, pa = pts.get((s, g["home"]), []), pts.get((s, g["away"]), [])
        if tot and sp is not None and mh and ma and len(ph) >= 4 and len(pa) >= 4 and hs != as_ and abs(mh) >= 100 and abs(ma) >= 100:
            for side, me, opp, spn, ml, so in (("home", ph, pa, sp, mh, ho), ("away", pa, ph, -sp, ma, ao)):
                implied = tot / 2 - spn / 2
                exp = (sum(x[0] for x in me) / len(me) + sum(x[1] for x in opp) / len(opp)) / 2
                mg = (hs - as_) if side == "home" else (as_ - hs)
                cov = None if mg + spn == 0 else (mg + spn > 0)
                so = so if so and abs(so) >= 100 else -110
                out.append({"season": s, "gap": implied - exp, "d": lib.dec(ml), "won": mg > 0,
                            "ats": None if cov is None else lib.profit(cov, lib.dec(so))})
        pts.setdefault((s, g["home"]), []).append((hs, as_))
        pts.setdefault((s, g["away"]), []).append((as_, hs))
    return out


def main():
    lines, out = [], {}
    for lg in ("nfl", "ncaaf", "nba"):      # NHL left out: its spread is the 1.5 puck line, not a margin read
        rows = rows_for(lg)
        lo, hi = CUTS[lg]
        lines.append(f"\n=== {lg.upper()} - {len(rows)} sides (implied team total minus the matchup's form) ===")
        groups = {f"market LOW by {hi}+": lambda r: r["gap"] <= -hi,
                  f"market LOW by {lo}-{hi}": lambda r: -hi < r["gap"] <= -lo,
                  "within": lambda r: -lo < r["gap"] < lo,
                  f"market HIGH by {lo}-{hi}": lambda r: lo <= r["gap"] < hi,
                  f"market HIGH by {hi}+": lambda r: r["gap"] >= hi}
        for nm, fn in groups.items():
            cell = [r for r in rows if fn(r)]
            for k, b in (("dog +100..+350", [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if 2.0 <= r["d"] <= 4.5]),
                         ("fav -101..-150", [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if 1.6667 <= r["d"] < 2.0]),
                         ("ATS close", [(r["season"], r["ats"]) for r in cell if r["ats"] is not None])):
                s = lib.summ(b, TRAIN, HELD)
                out[f"{lg} {nm} {k}"] = s
                lines.append(lib.fmt(f"{lg} {nm} {k}", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s3_out.txt"), "w").write(txt + "\n")
    json.dump(out, open(os.path.join(lib.OUT, "s3_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
