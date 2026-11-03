"""S3 - MATCHUP / STYLE ON SIDES, every game (the 10/28 cut was big slates only): pace mismatches, rebounding and
turnover edges, the three-heavy dog getting points (variance), the steady vs wild favorite - last 10 games' box scores."""
import lib

T = lib.build()
C = lib.Cells()
n = 0
# season quartiles of each rate, from the sides before (walk-forward is overkill for a quartile - the season's own)
by_season = {}
for d in T:
    if d["pace"] is None:
        continue
    by_season.setdefault(d["season"], {"pace": [], "oreb_pct": [], "to_rate": [], "tp_rate": [], "sd10": []})
    for k in by_season[d["season"]]:
        if d.get(k) is not None:
            by_season[d["season"]][k].append(d[k])
Q = {}
for s, m in by_season.items():
    Q[s] = {}
    for k, v in m.items():
        v = sorted(v)
        Q[s][k] = (v[len(v) // 4], v[3 * len(v) // 4]) if len(v) >= 40 else None


def q(d, k, who=""):
    v = d.get(who + k)
    if v is None or d["season"] not in Q or Q[d["season"]].get(k) is None:
        return None
    lo, hi = Q[d["season"]][k]
    return "hi" if v >= hi else "lo" if v <= lo else "mid"


for d in T:
    if d["pace"] is None or d["o_pace"] is None or d["g"] < 10 or d["o_g"] < 10:
        continue
    n += 1
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else None
    if not kind:
        continue
    pm, opm = q(d, "pace"), q(d, "pace", "o_")
    if pm == "hi" and opm == "lo":
        lib.add_all(C, f"1 fast team vs a slow team: {kind}", d)
    if pm == "lo" and opm == "hi":
        lib.add_all(C, f"1b slow team vs a fast team: {kind}", d)
    gap = d["pace"] - d["o_pace"]
    if abs(gap) >= 4:
        lib.add_all(C, f"1c pace {'4+ faster' if gap > 0 else '4+ slower'} than the opp: {kind}", d)
    ob, oob = q(d, "oreb_pct"), q(d, "oreb_pct", "o_")
    if ob == "hi" and oob == "lo":
        lib.add_all(C, f"2 top-quartile offensive rebounding vs a bottom-quartile one: {kind}", d)
    if ob == "lo":
        lib.add_all(C, f"2b bottom-quartile offensive rebounding: {kind}", d)
    if ob == "hi":
        lib.add_all(C, f"2c top-quartile offensive rebounding: {kind}", d)
    tb, otb = q(d, "to_rate"), q(d, "to_rate", "o_")
    if tb == "hi":
        lib.add_all(C, f"3 sloppy (top-quartile turnovers): {kind}", d)
    if otb == "hi":
        lib.add_all(C, f"3b opp sloppy (top-quartile turnovers): {kind}", d)
    if tb == "lo" and otb == "hi":
        lib.add_all(C, f"3c careful vs sloppy: {kind}", d)
    tr = q(d, "tp_rate")
    if kind == "dog" and d["spread"] is not None:
        big = d["spread"] >= 7
        if tr == "hi":
            lib.add_all(C, f"4 three-heavy dog {'getting 7+' if big else 'getting under 7'}: dog", d)
        if tr == "lo":
            lib.add_all(C, f"4b three-light dog {'getting 7+' if big else 'getting under 7'}: dog", d)
        if d["sd10"] is not None and q(d, "sd10") == "hi":
            lib.add_all(C, f"4c wild dog (top-quartile margin spread) {'getting 7+' if big else 'under 7'}: dog", d)
    if kind == "fav-150..-101":
        sq = q(d, "sd10")
        if sq == "lo":
            lib.add_all(C, "5 steady favorite (bottom-quartile margin spread): fav-150..-101", d)
        if sq == "hi":
            lib.add_all(C, "5b wild favorite (top-quartile margin spread): fav-150..-101", d)
        if q(d, "sd10", "o_") == "hi":
            lib.add_all(C, "5c favorite vs a wild dog: fav-150..-101", d)
    # the opponent's three-point luck (hot last 10 by 3P% vs its rate) - the market over-rates a hot-shooting team?
    tp = d.get("o_tp_pct")
    if tp is not None:
        if tp >= 0.39:
            lib.add_all(C, f"6 opp shot 39%+ from three over its last 10: {kind}", d)
        if tp <= 0.33:
            lib.add_all(C, f"6b opp shot 33% or worse from three over its last 10: {kind}", d)
C.dump("s3", lib.header("S3 STYLE / MATCHUP ON SIDES (last 10 games' box scores, season quartiles)", n), lib.split)
