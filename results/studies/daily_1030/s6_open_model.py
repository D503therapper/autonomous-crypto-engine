"""STUDIES 6 + 9 (10/30) - THE OPENING-LINE WHOLE READ, ported from the NBA (sports_nba_open, built 10/23) to
  6) the NHL (never tried - the 10/2 hockey open study was the Elo alone vs the open, a LEAD at gap 8+), and
  9) COLLEGE HOOPS (prep - the season opens early November).
The same 37 inputs (the open price, home / dog, stage of season, rest, back-to-backs, 3-in-4 / 4-in-6, road trips, time
zones, altitude, last margin, 5 / 10-game form, this and last season's records, the Elo gap - nothing from injuries or
box scores), the same ridge (lam 300) fit at the CLOSE on the seasons BEFORE the graded one only, scored at the OPEN.
Opens exist 2023-26 only (ESPN's recorded opening number). Graded: (a) the ONE best side a night with score 4+ points,
open -150..+300 (the NBA play's exact rule), at the open and at the close; (b) every side with score 4+ / 6+.
Train-side model seasons: everything before the graded season; graded 2023 / 2024 / 2025 / 2026 (now) apart.
Usage: python s6_open_model.py nhl | ncaab"""
import inspect
import json
import os
import sys

import lib
import sports_nba_open as no

LG = sys.argv[1] if len(sys.argv) > 1 else "nhl"
K = {"nhl": (lib.sm.BASE_K["nhl"], lib.sm.DEFAULT_HFA["nhl"]), "ncaab": (lib.sm.BASE_K["ncaab"], lib.sm.DEFAULT_HFA["ncaab"])}[LG]

src = inspect.getsource(no.table)
src = src.replace('g.get("league") != "nba"', 'g.get("league") != LG').replace('sm.Elo(ELO_K, ELO_HFA, "nba")', 'sm.Elo(ELO_K, ELO_HFA, LG)')
ns = dict(no.__dict__)
ns.update({"LG": LG, "ELO_K": K[0], "ELO_HFA": K[1]})
exec(src, ns)
table = ns["table"]


def main():
    games = lib.sd.load_games(LG)
    tab = table(games)
    lines, res = [f"=== {LG.upper()}: {len(tab)} games in the table ==="], {}
    picks_top, picks_all4, picks_all6 = [], [], []
    for season in (2023, 2024, 2025, 2026):
        m = no.fit(games, season, path=False, tab=tab)
        if not m:
            lines.append(f"{season}: no model")
            continue
        by_date = {}
        for gid, row in tab.items():
            if row["season"] != season or not row["reg"] or row["home_win"] is None:
                continue
            if row["ml_home_open"] is None or row["ml_away_open"] is None or row["ml_home"] is None:
                continue
            if row["h"]["n_season"] < 1 or row["a"]["n_season"] < 1:
                continue
            mp = no._mp(row["ml_home_open"], row["ml_away_open"])
            if mp is None:
                continue
            for side, ml, cl, p, won in (("home", row["ml_home_open"], row["ml_home"], mp, row["home_win"]),
                                         ("away", row["ml_away_open"], row["ml_away"], 1 - mp, 1 - row["home_win"])):
                if not -150 <= ml <= 300 or abs(ml) < 100:
                    continue
                sc = no.score(m, row, side, p)
                c = (sc, season, won, no._dec(ml), no._dec(cl) if cl and abs(cl) >= 100 else no._dec(ml))
                by_date.setdefault(row["date"], []).append(c)
                if sc >= 0.04:
                    picks_all4.append(c)
                if sc >= 0.06:
                    picks_all6.append(c)
        for d, cs in by_date.items():
            best = max(cs, key=lambda c: c[0])
            if best[0] >= 0.04:
                picks_top.append(best)
        lines.append(f"{season}: model rows {m['rows']}, train seasons {m['train_seasons'][0]}-{m['train_seasons'][-1]}")
    for nm, ps in (("BEST side a night, score 4+", picks_top), ("EVERY side score 4+", picks_all4), ("EVERY side score 6+", picks_all6)):
        for at, k in (("@open", 3), ("@close", 4)):
            b = [(c[1], lib.profit(c[2] > 0.5, c[k])) for c in ps]
            s = lib.summ(b, (2023, 2023), [2024, 2025, 2026])
            res[f"{nm} {at}"] = s
            lines.append(lib.fmt(f"{LG} {nm} {at}", s))
        for tag, lo, hi in (("dogs", 2.0, 9), ("favs", 1.0, 2.0)):
            b = [(c[1], lib.profit(c[2] > 0.5, c[3])) for c in ps if lo <= c[3] < hi]
            s = lib.summ(b, (2023, 2023), [2024, 2025, 2026])
            res[f"{nm} {tag} @open"] = s
            lines.append(lib.fmt(f"   {tag} @open", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, f"s6_open_model_{LG}_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, f"s6_open_model_{LG}_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
