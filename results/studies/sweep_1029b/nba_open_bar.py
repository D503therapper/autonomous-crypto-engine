"""The NBA opening-line play's bar (SCORE_MIN 0.04) re-checked blind at the OPEN: every season 2023-24.. fit on the
seasons before it, the best side a night at the opening prices, graded at the open. Bars 2..7 points."""
import sys, os
sys.path.insert(0, os.getcwd())
import sports_data as sd
import sports_nba_open as no

games = sd.load_games("nba")
tab = no.table(games)
seasons = sorted({r["season"] for r in tab.values() if r["reg"] and r["home_win"] is not None})
print("seasons", seasons)
models = {}
for s in seasons:
    if s < 2023:
        continue
    models[s] = no.fit(games, s, path=False, tab=tab)
    print(s, "model", "ok" if models[s] else "none")
dates = {}
for gid, r in tab.items():
    if r["reg"] and r["home_win"] is not None and r["season"] in models and models[r["season"]] and r["ml_home_open"] and r["ml_away_open"]:
        dates.setdefault((r["season"], r["date"]), {})[gid] = (r["ml_home_open"], r["ml_away_open"])
print("slate dates with opens", len(dates))


def grade(bar, band=(-150, 300), g1_10=None):
    out = {}
    for (s, d), prices in sorted(dates.items()):
        rows = {gid: tab[gid] for gid in prices}
        best = None
        for gid, row in rows.items():
            if row["status"] not in ("final",):
                pass
            mh, ma = prices[gid]
            mp_h = no._mp(mh, ma)
            if mp_h is None or row["h"]["n_season"] < 1 or row["a"]["n_season"] < 1:
                continue
            for side, ml, mp in (("home", mh, mp_h), ("away", ma, 1 - mp_h)):
                if not band[0] <= ml <= band[1]:
                    continue
                n = min(row["h"]["n_season"], row["a"]["n_season"])
                if g1_10 is True and n > 10 or g1_10 is False and n <= 10:
                    continue
                sc = no.score(models[s], row, side, mp)
                if sc < bar:
                    continue
                if best is None or sc > best[0]:
                    best = (sc, gid, side, ml, row)
        if best:
            sc, gid, side, ml, row = best
            won = row["home_win"] if side == "home" else 1 - row["home_win"]
            pnl = (no._dec(ml) - 1) if won else -1
            o = out.setdefault(s, [0, 0, 0.0])
            o[0] += won; o[1] += 1 - won; o[2] += pnl
    tot = [sum(v[0] for v in out.values()), sum(v[1] for v in out.values()), sum(v[2] for v in out.values())]
    n = tot[0] + tot[1]
    return f"{tot[0]:.0f}-{tot[1]:.0f} {tot[2] / n * 100 if n else 0:+.1f}% {tot[2]:+.1f}u  " + "  ".join(f"{s}:{v[0]:.0f}-{v[1]:.0f} {v[2]:+.1f}u" for s, v in sorted(out.items()))


for bar in (0.02, 0.03, 0.04, 0.05, 0.06, 0.07):
    print(f"bar {bar:.2f}: {grade(bar)}")
print("dogs only (+100..+300):")
for bar in (0.03, 0.04, 0.05):
    print(f"bar {bar:.2f}: {grade(bar, band=(100, 300))}")
print("favorites only (-150..-101):")
for bar in (0.03, 0.04, 0.05):
    print(f"bar {bar:.2f}: {grade(bar, band=(-150, -101))}")
print("games 1-10 only / 11+ at 0.04:")
print(" 1-10:", grade(0.04, g1_10=True))
print(" 11+ :", grade(0.04, g1_10=False))


def grade_n(bar, topn, band=(-150, 300)):
    out = {}
    for (s, d), prices in sorted(dates.items()):
        picks = []
        for gid in prices:
            row = tab[gid]
            mh, ma = prices[gid]
            mp_h = no._mp(mh, ma)
            if mp_h is None or row["h"]["n_season"] < 1 or row["a"]["n_season"] < 1:
                continue
            for side, ml, mp in (("home", mh, mp_h), ("away", ma, 1 - mp_h)):
                if not band[0] <= ml <= band[1]:
                    continue
                sc = no.score(models[s], row, side, mp)
                if sc >= bar:
                    picks.append((sc, gid, side, ml, row))
        picks.sort(key=lambda x: -x[0])
        for rank, (sc, gid, side, ml, row) in enumerate(picks[:topn]):
            won = row["home_win"] if side == "home" else 1 - row["home_win"]
            pnl = (no._dec(ml) - 1) if won else -1
            o = out.setdefault((s, rank), [0, 0, 0.0])
            o[0] += won; o[1] += 1 - won; o[2] += pnl
    for rank in range(topn):
        tot = [sum(v[0] for (s, r), v in out.items() if r == rank), sum(v[1] for (s, r), v in out.items() if r == rank),
               sum(v[2] for (s, r), v in out.items() if r == rank)]
        n = tot[0] + tot[1]
        print(f"  bar {bar:.2f} rank #{rank + 1}: {tot[0]:.0f}-{tot[1]:.0f} {tot[2] / n * 100 if n else 0:+.1f}% {tot[2]:+.1f}u  "
              + "  ".join(f"{s}: {v[0]:.0f}-{v[1]:.0f} {v[2]:+.1f}u" for (s, r), v in sorted(out.items()) if r == rank))


print("the #2 / #3 side a night:")
for bar in (0.04, 0.05, 0.06):
    grade_n(bar, 3)
