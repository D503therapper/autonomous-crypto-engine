"""STUDY 2 (10/30): sizing the NBA opening-line play by its read margin. Each season 2023-27 fit on the seasons before,
the best side a night at the OPEN with a score of 4+ points (the live bar), graded at the open, flat 1u - then split by
the margin band (4-5 / 5-7 / 7+ and finer) with each band's W-L / ROI by season. Model score only (the board's dog
weights - the 12+ slate, soft next, cold dog - aren't in this table; the slate count is, as a check)."""
import sys, os
sys.path.insert(0, os.getcwd())
import sports_data as sd
import sports_nba_open as no

games = sd.load_games("nba")
tab = no.table(games)
seasons = sorted({r["season"] for r in tab.values() if r["reg"] and r["home_win"] is not None})
models = {s: no.fit(games, s, path=False, tab=tab) for s in seasons if s >= 2023}
dates = {}
for gid, r in tab.items():
    if r["reg"] and r["home_win"] is not None and r["season"] in models and models[r["season"]] and r["ml_home_open"] and r["ml_away_open"]:
        dates.setdefault((r["season"], r["date"]), {})[gid] = (r["ml_home_open"], r["ml_away_open"])
slate_n = {}
for gid, r in tab.items():
    if r["reg"]:
        slate_n[(r["season"], r["date"])] = slate_n.get((r["season"], r["date"]), 0) + 1

picks = []
for (s, d), prices in sorted(dates.items()):
    best = None
    for gid, pr in prices.items():
        row = tab[gid]
        mh, ma = pr
        mp_h = no._mp(mh, ma)
        if mp_h is None or row["h"]["n_season"] < 1 or row["a"]["n_season"] < 1:
            continue
        for side, ml, mp in (("home", mh, mp_h), ("away", ma, 1 - mp_h)):
            if not -150 <= ml <= 300:
                continue
            sc = no.score(models[s], row, side, mp)
            if sc < 0.04:
                continue
            if best is None or sc > best[0]:
                best = (sc, gid, side, ml, row)
    if best:
        sc, gid, side, ml, row = best
        won = row["home_win"] if side == "home" else 1 - row["home_win"]
        pnl = (no._dec(ml) - 1) if won else -1
        # the same side at the close
        mc = row["ml_home"] if side == "home" else row["ml_away"]
        picks.append(dict(season=s, date=d, score=sc, odds=ml, close=mc, won=won, pnl=pnl, dog=ml > 0,
                          slate=slate_n.get((s, d), 0), n=min(row["h"]["n_season"], row["a"]["n_season"])))
print("picks", len(picks), "seasons", sorted({p["season"] for p in picks}))


def rep(name, sel):
    rows = [p for p in picks if sel(p)]
    by = {}
    for p in rows:
        o = by.setdefault(p["season"], [0, 0, 0.0])
        o[0] += p["won"]; o[1] += 1 - p["won"]; o[2] += p["pnl"]
    w = sum(v[0] for v in by.values()); l = sum(v[1] for v in by.values()); u = sum(v[2] for v in by.values())
    n = w + l
    up = sum(1 for v in by.values() if v[2] > 0)
    print(f"{name:34s} {w:.0f}-{l:.0f} {u / n * 100 if n else 0:+6.1f}% {u:+7.1f}u  {up}/{len(by)} up  "
          + "  ".join(f"{s}:{v[0]:.0f}-{v[1]:.0f} {v[2]:+.1f}u" for s, v in sorted(by.items())))
    return n, u


print("\nBY MARGIN BAND (all, flat 1u):")
for lo, hi in ((0.04, 0.05), (0.05, 0.06), (0.06, 0.07), (0.07, 0.08), (0.08, 0.10), (0.10, 9)):
    rep(f"  {lo * 100:.0f}-{hi * 100:.0f} pts", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi)
print("  the owner's bands:")
for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 9)):
    rep(f"  {lo * 100:.0f}-{hi * 100:.0f} pts", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi)
print("\nCUMULATIVE (bar X+):")
for lo in (0.04, 0.05, 0.06, 0.07, 0.08):
    rep(f"  {lo * 100:.0f}+ pts", lambda p, lo=lo: p["score"] >= lo)
print("\nDOGS vs FAVORITES by band:")
for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 9)):
    rep(f"  dogs {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and p["dog"])
    rep(f"  favs {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and not p["dog"])
print("\nPRICE by band (dogs +100..+150 / +151..+300; favs):")
for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 9)):
    rep(f"  +100..+150 {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and 100 <= p["odds"] <= 150)
    rep(f"  +151..+300 {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and p["odds"] > 150)
print("\nSLATE SIZE by band (12+ games):")
for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 9)):
    rep(f"  12+ slate {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and p["slate"] >= 12)
    rep(f"  <12 slate {lo * 100:.0f}-{hi * 100:.0f}", lambda p, lo=lo, hi=hi: lo <= p["score"] < hi and p["slate"] < 12)

print("\nSIZING SCHEMES (units won, worst stretch):")


def scheme(name, fn):
    by = {}
    tot = 0.0; peak = 0.0; worst = 0.0; staked = 0.0
    for p in sorted(picks, key=lambda p: p["date"]):
        u = fn(p)
        if not u:
            continue
        tot += u * p["pnl"]; staked += u
        peak = max(peak, tot); worst = min(worst, tot - peak)
        o = by.setdefault(p["season"], 0.0)
        by[p["season"]] = o + u * p["pnl"]
    print(f"  {name:36s} {tot:+7.1f}u on {staked:.0f}u staked ({tot / staked * 100 if staked else 0:+.1f}%), worst stretch {worst:+.1f}u  "
          + "  ".join(f"{s}:{v:+.1f}u" for s, v in sorted(by.items())))


scheme("flat ½u (live)", lambda p: 0.5)
scheme("flat 1u", lambda p: 1.0)
scheme("½u / 1u / 2u at 4-5 / 5-7 / 7+", lambda p: 0.5 if p["score"] < 0.05 else 1.0 if p["score"] < 0.07 else 2.0)
scheme("1u / 1u / 2u at 4-5 / 5-7 / 7+", lambda p: 1.0 if p["score"] < 0.07 else 2.0)
scheme("1u / 2u / 3u at 4-5 / 5-7 / 7+", lambda p: 1.0 if p["score"] < 0.05 else 2.0 if p["score"] < 0.07 else 3.0)
scheme("½u / 1u at 4-6 / 6+", lambda p: 0.5 if p["score"] < 0.06 else 1.0)
scheme("1u / 2u at 4-6 / 6+", lambda p: 1.0 if p["score"] < 0.06 else 2.0)
scheme("1u favs / ½u dogs", lambda p: 0.5 if p["dog"] else 1.0)
scheme("quarter-Kelly on the read (cap 3u)", lambda p: min(3.0, max(0.0, 0.25 * p["score"] / (no._dec(p["odds"]) - 1) * 10)))

print("\nCLV: the open vs the close on the picks (no-vig points the number moved our way):")
mv = []
for p in picks:
    if p["close"]:
        a, b = no._dec(p["odds"]), no._dec(p["close"])
        mv.append((1 / b - 1 / a, p["score"]))
for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 9)):
    xs = [m for m, s in mv if lo <= s < hi]
    print(f"  {lo * 100:.0f}-{hi * 100:.0f}: n {len(xs)}, avg move {sum(xs) / len(xs) * 100 if xs else 0:+.2f} pts, our way {sum(1 for x in xs if x > 0)} / against {sum(1 for x in xs if x < 0)}")
