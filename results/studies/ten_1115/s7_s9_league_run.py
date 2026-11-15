"""S7 (college hoops) / S9 (NBA) - DOES THE TOTAL LAG THE LEAGUE'S OWN RUN?  The 11/14 NBA watch (games 1-14 while the
league's games so far ran 3+ points under the closing total -> the under) asked the general way, on two leagues:
before each day, the league's miss (points - closing total) over (a) this season's games so far and (b) its last N
priced games (a rolling window, all season); bet the side the run points to. Every game enters the run only after its
day. College hoops: the 11/14 totals table (28k+ priced games 2018-26, the altitude floors left in), -110 flat (the
archive's totals juice is not trusted - 11/12 study 15). NBA: ESPN's close at its own juice (2018-26).
TRAIN 2018-21 / HELD 2022-26 each season apart."""
import os
import statistics
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import clib  # noqa: E402

TR, HE = (2018, 2021), [2022, 2023, 2024, 2025, 2026]


def run_league(name, games, N, early_n):
    """games: [{start, season, pts, tot, po, pu, n (the lesser of the two teams' games played)}] sorted by start."""
    O = h.Out("s7_s9_" + name, TR, HE)
    O.p(f"==== {name}: {len(games)} priced games; rolling window {N}; 'early' = both teams under {early_n} games ====")
    sea = defaultdict(list)
    roll = deque(maxlen=N)
    buf, cur = [], None
    for g in games:
        d = g["start"][:10]
        if d != cur:
            for s, m in buf:
                sea[s].append(m)
                roll.append(m)
            buf, cur = [], d
        s = g["season"]
        if g["pts"] != g["tot"]:
            r = sea[s]
            sr = statistics.mean(r) if len(r) >= 40 else None
            rr = statistics.mean(roll) if len(roll) == N else None
            early = g["n"] is not None and g["n"] < early_n
            for over in (True, False):
                pr = (g["po"] if over else g["pu"]) if ((g["pts"] > g["tot"]) == over) else -1.0
                w = "over" if over else "under"
                O.add(f"{w} ALL", s, pr)
                if early:
                    O.add(f"{w} early ALL", s, pr)
                for lab, v in (("season run", sr), ("rolling", rr)):
                    if v is None:
                        continue
                    k = "3+ under" if v <= -3 else "1.5..3 under" if v <= -1.5 else "0..1.5 under" if v < 0 else "0..1.5 over" if v < 1.5 else "1.5..3 over" if v < 3 else "3+ over"
                    O.add(f"{w} | {lab} {k}", s, pr)
                    if early:
                        O.add(f"{w} | early, {lab} {k}", s, pr)
                    if v <= -1.5:
                        O.add(f"{w} | {lab} 1.5+ under (all)", s, pr)
                    if v >= 1.5:
                        O.add(f"{w} | {lab} 1.5+ over (all)", s, pr)
        buf.append((s, g["pts"] - g["tot"]))
    O.show()
    for nm in ("under | season run 1.5+ under (all)", "over | season run 1.5+ over (all)", "under | rolling 1.5+ under (all)",
               "over | rolling 1.5+ over (all)", "under | early, season run 3+ under", "under | early, rolling 3+ under"):
        if nm in O.c:
            O.placebo(nm, nm.split(" ")[0] + " ALL")
    # the season's own opening run, a line a season (the first 100 / 300 priced games)
    first = defaultdict(list)
    for g in games:
        if len(first[g["season"]]) < early_n * 20:
            first[g["season"]].append(g["pts"] - g["tot"])
    O.p("the opening run a season (mean miss over the first %d priced games): " % (early_n * 20)
        + "  ".join(f"{s}: {statistics.mean(v):+.2f}" for s, v in sorted(first.items())))
    O.save()


# ---- college hoops
T = [g for g in clib.tlib.build() if g.get("tot") is not None and g.get("pts") is not None and g["stype"] == "2" and g["season"] >= 2018]
T.sort(key=lambda g: g["start"])
cb = [{"start": g["start"], "season": g["season"], "pts": g["pts"], "tot": g["tot"], "po": 100 / 110, "pu": 100 / 110,
       "n": min(g.get("gh") or 0, g.get("ga") or 0)} for g in T]
run_league("ncaab", cb, 300, 6)

# ---- NBA
fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["total"] is not None and g["season"] >= 2018]
cnt = defaultdict(int)
nb = []
for g in fin:
    s = g["season"]
    n = min(cnt[(g["home"], s)], cnt[(g["away"], s)])
    cnt[(g["home"], s)] += 1
    cnt[(g["away"], s)] += 1
    nb.append({"start": g["start"], "season": s, "pts": g["hs"] + g["as"], "tot": g["total"],
               "po": lib.dec(g["ovo"] or -110) - 1, "pu": lib.dec(g["uno"] or -110) - 1, "n": n})
run_league("nba", nb, 100, 15)
