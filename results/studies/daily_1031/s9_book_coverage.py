"""Study 9 (10/31): the paid odds history, NFL + college football - HOW MANY BOOKS HANG THE GAME (book-by-book, never
run as COVERAGE: the 10/8 / 10/10 studies were one book's price vs the others, the first mover, the dispersion).
A game few books bother to price at the first fair look is a thin, less-watched market: is its first fair number
softer - does it move more by the close, and do its dogs / favorites beat the first fair price or the close?
Coverage = the books posting a moneyline at the first FAIR look (ef.ready_at / fair), cut in thirds within the
league-season (books joined the feed over the years, so the cut is relative). Also: the books that join LATE (the
count at the first fair look vs the most books seen at any look) - a game the market keeps adding books to.
Graded on dogs +100..+350 and favorites -101..-150 at the first fair price (the median book) and at the close; the move
= |close no-vig - first fair no-vig|. Train 2020-23, held out 2024 / 2025 / 2026 apart."""
import json, os, statistics, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2020, 2023), (2024, 2025, 2026)
out, lines = {}, []
for lg in ("nfl", "ncaaf"):
    G = lib.load_football(lg)
    rows = []
    for x in G:
        f = lib.first_fair(x["ml"])
        if not f or x["c_mlh"] is None or x["c_mla"] is None:
            continue
        nb = len(f[1])
        most = max(len(b) for _, b in x["all_ml"]) if x["all_ml"] else nb
        rows.append((x, f, nb, most))
    by_s = defaultdict(list)
    for x, f, nb, most in rows:
        by_s[x["season"]].append(nb)
    cut = {s: (sorted(v)[len(v) // 3], sorted(v)[2 * len(v) // 3]) for s, v in by_s.items()}
    cells = defaultdict(list)
    moves = defaultdict(list)
    for x, f, nb, most in rows:
        s = x["season"]
        lo, hi = cut[s]
        cov = "THIN (bottom third of books)" if nb <= lo and lo < hi else "WIDE (top third)" if nb >= hi else "middle"
        h0, a0, p0 = lib.ml_med(f[1])
        p1 = lib.nv(x["c_mlh"], x["c_mla"])
        moves[cov].append(abs(p1 - p0))
        late = most - nb >= 3
        for side in ("home", "away"):
            d0 = h0 if side == "home" else a0
            dc = lib.dec(x["c_mlh"] if side == "home" else x["c_mla"])
            won = (x["margin"] > 0) if side == "home" else (x["margin"] < 0)
            am0 = (d0 - 1) * 100 if d0 >= 2 else -100 / (d0 - 1)
            band = "dog +100..+350" if 100 <= am0 <= 350 else "fav -101..-150" if -150 <= am0 <= -101 else None
            if not band:
                continue
            moved_to = ((p1 - p0) if side == "home" else (p0 - p1)) >= 0.02
            for tag in ("all", cov) + (("3+ books joined after the first fair look",) if late else ()):
                cells[f"{band} | {tag} | at the FIRST FAIR price"].append((s, lib.profit(won, d0)))
                cells[f"{band} | {tag} | at the close"].append((s, lib.profit(won, dc)))
            if cov.startswith("THIN") and moved_to:
                cells[f"{band} | THIN and the close moved 2+ TO it | at the first fair price"].append((s, lib.profit(won, d0)))
    r = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
    mv = {k: {"n": len(v), "mean_move": round(statistics.mean(v), 4), "share_2pts+": round(sum(1 for m in v if m >= 0.02) / len(v), 3)}
          for k, v in moves.items()}
    out[lg] = {"cuts": cut, "moves": mv, "cells": r}
    lines.append(f"== {lg}: {len(rows)} games; books at the first fair look, cuts by season {cut}")
    lines.append("   first fair -> close no-vig move by coverage: " + json.dumps(mv))
    lines += [lib.fmt(k, v) for k, v in r.items()]
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, "s9_out.txt"), "w").write(txt + "\n")
json.dump(out, open(os.path.join(lib.OUT, "s9_out.json"), "w"), indent=1, default=str)
