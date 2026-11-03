"""S4 - TEAM-SPECIFIC MARKET BIAS: does a team the market over- or under-rated LAST season (its win % minus the no-vig
price over 60+ priced games) stay that way this season - overall, as a dog / favorite, home / road, early (Oct-Dec) vs
late? And THIS season's running record (15+ games) for the rest of the season? Walk-forward by construction."""
import lib

T = lib.build()
C = lib.Cells()
n = 0
for d in T:
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else "fav big" if d["ml"] < -150 else None
    bl = d["bias_last"]
    if bl is not None:
        n += 1
        b = "under-rated last season (+5%+)" if bl >= 0.05 else "over-rated last season (-5%-)" if bl <= -0.05 else "priced last season"
        lib.add_all(C, f"1 {b}: all", d)
        if kind:
            lib.add_all(C, f"1 {b}: {kind}", d)
            ph = "early (Oct-Dec)" if d["month"] in (10, 11, 12) else "late (Jan-Apr)"
            lib.add_all(C, f"1b {b}, {ph}: {kind}", d)
        lib.add_all(C, f"1c {b}, {'home' if d['home'] else 'road'}: all", d)
        if d["o_bias_last"] is not None and kind:
            if bl >= 0.05 and d["o_bias_last"] <= -0.05:
                lib.add_all(C, f"1d under-rated vs an over-rated team (last season): {kind}", d)
            if bl <= -0.05 and d["o_bias_last"] >= 0.05:
                lib.add_all(C, f"1e over-rated vs an under-rated team (last season): {kind}", d)
    bn = d["bias_now"]
    if bn is not None and d["bias_now_n"] >= 15:
        b = "beating its price this season (+8%+)" if bn >= 0.08 else "losing to its price this season (-8%-)" if bn <= -0.08 else "at its price this season"
        lib.add_all(C, f"2 {b}: all", d)
        if kind:
            lib.add_all(C, f"2 {b}: {kind}", d)
        if d["bias_now_n"] >= 30:
            lib.add_all(C, f"2b {b} (30+ games): all", d)
    if bl is not None and bn is not None and d["bias_now_n"] >= 15:
        if bl >= 0.05 and bn >= 0.08:
            lib.add_all(C, "3 under-rated last season AND beating its price this season: all", d)
        if bl <= -0.05 and bn <= -0.08:
            lib.add_all(C, "3b over-rated last season AND losing to its price this season: all", d)
C.dump("s4", lib.header("S4 TEAM-SPECIFIC MARKET BIAS (last season's / this season's win % minus the price)", n), lib.split)
# the persistent teams: each team's mean residual by season (train seasons vs held out), printed small
by = {}
for d in T:
    by.setdefault(d["team"], {}).setdefault(d["season"], []).append((1.0 if d["won"] else 0.0) - d["nv"])
names = {}
import sports_data as sd
for g in sd.load_games("nba").values():
    names[g["home"]] = g.get("home_name")
print("\nPER TEAM: mean (win - no-vig) x100, train 2018-22 | held 2023-25 | corr across teams")
rows = []
for t, m in by.items():
    tr = [x for s, v in m.items() if 2018 <= s <= 2022 for x in v]
    he = [x for s, v in m.items() if s in (2023, 2024, 2025) for x in v]
    if len(tr) >= 200 and len(he) >= 150:
        rows.append((names.get(t, t), 100 * sum(tr) / len(tr), 100 * sum(he) / len(he)))
rows.sort(key=lambda r: -r[1])
for nm, a, b in rows:
    print(f"  {nm:14s} train {a:+5.1f}  held {b:+5.1f}")
import statistics
xs, ys = [r[1] for r in rows], [r[2] for r in rows]
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
print(f"  corr(train, held) across {len(rows)} teams = {cov / den:+.2f}")
