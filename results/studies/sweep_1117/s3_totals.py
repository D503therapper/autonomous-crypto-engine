"""11/17 FULL SWEEP - THE TOTALS PATHS (the 11/12 fifteen-studies rig: fifteen_1112/lib.py - every close 2018-26, one row
a game; TRAIN = seasons to 2021, BLIND = 2022 on - the totals studies' split). Each cell named before looking.
  S7  ⛰️ THE ALTITUDE OVER as wired (1u): the rule rebuilt, then the cells that could earn a bigger size or a cut -
      the height (1,800 m+), the number (150+ / under 140), the month, the visitor's rest, this season so far
  S8  🏀 THE NBA OVER WHEN THE MAIN GUYS SIT (½u): 4+ of the six out vs exactly 3 (a 1u cell?), the fresh news, the price
  S9  🌍 THE EUROPE MORNING NFL UNDER (½u, 3-0 live): nflverse's closes 2007-26, every international game
A bigger size needs the cell to win MORE than its siblings in both halves, most seasons, a placebo under 100 of 2,000
(a random same-size draw of the RULE's own plays), a point worse still up. Nothing here re-opens the rules' gates.
Usage: python results/studies/sweep_1117/s3_totals.py > results/studies/sweep_1117/s3_totals.out"""
import csv
import json
import os
import random
import sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "fifteen_1112"))
os.chdir(os.path.join(HERE, "..", "fifteen_1112"))
import lib as L  # noqa: E402


def judge(name, rows, pool, prof, prof1):
    """rows / pool = games; prof(g) the bet's profit at the close, prof1(g) a point worse. Prints the five checks."""
    c = L.cell(name, [(g["season"], prof(g)) for g in rows])
    rest = [g for g in pool if g not in rows]
    r = L.cell("   the rest of the rule's plays", [(g["season"], prof(g)) for g in rest], show=False)
    ps = [p for _, p in c["bets"]]
    pl = [prof(g) for g in pool if prof(g) is not None]
    pb = L.placebo(pl, len(ps), sum(ps) / len(ps)) if ps and len(pl) > len(ps) else None
    w1 = L.cell("x", [(g["season"], prof1(g)) for g in rows], show=False)
    ok = (c["train"]["n"] >= 10 and c["blind"]["n"] >= 10 and c["train"]["roi"] > max(0, r["train"]["roi"]) and c["blind"]["roi"] > max(0, r["blind"]["roi"])
          and (c["up_tr"] + c["up_bl"]) * 2 > (c["n_tr"] + c["n_bl"]) and pb is not None and pb < 100 and w1["all"]["roi"] > 0)
    print(f"      vs the rest: TR {100 * r['train']['roi']:+.1f}% n{r['train']['n']} / BL {100 * r['blind']['roi']:+.1f}% n{r['blind']['n']} | placebo "
          f"{pb}/2000 | worst {L.worst(ps):+.1f}u | a point worse {100 * w1['all']['roi']:+.1f}%" + ("   <== CLEARS" if ok else ""))
    return ok


# ---------------------------------------------------------------- S7 the altitude over
print("=" * 20, "S7 ⛰️ THE ALTITUDE OVER (wired 1u from 11/13)")
G = [g for g in L.table("ncaab") if L.reg(g) and g["tot"] is not None]


def fill(f):
    n = f["n"]
    if n >= 5:
        return f["pf"], f["pa"]
    pv = f.get("prev")
    if not pv or pv["n"] < 10:
        return None
    return (f.get("pf", 0) * n + (5 - n) * pv["pf"]) / 5, (f.get("pa", 0) * n + (5 - n) * pv["pa"]) / 5


def read(g):
    h, a = fill(g["H"]), fill(g["A"])
    return None if not h or not a else (h[0] + a[1] + a[0] + h[1]) / 2


rule = [g for g in G if not g["neutral"] and (g["elev"] or 0) >= 1400 and (g["ovo"] or -110) >= -130
        and read(g) is not None and read(g) - g["tot"] >= -3]
ov = lambda g: L.tot(g, "over")           # noqa: E731
ov1 = lambda g: L.tot(g, "over", -1)      # noqa: E731
L.cell("THE RULE -> OVER (every play)", [(g["season"], ov(g)) for g in rule])
L.cell("   a point worse than the close", [(g["season"], ov1(g)) for g in rule])
L.cell("   seasons 2024 on", [(g["season"], ov(g)) for g in rule if g["season"] >= 2024])
L.cell("   THIS season (2026-27) so far", [(g["season"], ov(g)) for g in rule if g["season"] >= 2026])
won = []
for nm, f in (("the floor 1,800 m+ (5,900 ft)", lambda g: g["elev"] >= 1800), ("the floor 1,400-1,799 m", lambda g: g["elev"] < 1800),
              ("the number 150+", lambda g: g["tot"] >= 150), ("the number 140-149.5", lambda g: 140 <= g["tot"] < 150),
              ("the number under 140", lambda g: g["tot"] < 140),
              ("November-December", lambda g: g["start"][5:7] in ("11", "12")), ("January on", lambda g: g["start"][5:7] in ("01", "02", "03")),
              ("the visitor on 1 day of rest or a back-to-back", lambda g: (g["A"].get("rest") or 9) <= 2),
              ("the visitor rested 3+ days", lambda g: (g["A"].get("rest") or 0) >= 3),
              ("the scoring read OVER the number", lambda g: read(g) - g["tot"] >= 0),
              ("the scoring read 0-3 under the number", lambda g: read(g) - g["tot"] < 0),
              ("the price -110 or cheaper", lambda g: (g["ovo"] or -110) >= -110), ("the price -111..-130", lambda g: (g["ovo"] or -110) < -110),
              ("both teams 5+ games in", lambda g: g["H"]["n"] >= 5 and g["A"]["n"] >= 5),
              ("a team under 5 games (last season fills in)", lambda g: g["H"]["n"] < 5 or g["A"]["n"] < 5)):
    if judge(nm, [g for g in rule if f(g)], rule, ov, ov1):
        won.append(nm)
ps = [ov(g) for g in sorted(rule, key=lambda g: g["start"]) if ov(g) is not None]
by = defaultdict(float)
for g in rule:
    if ov(g) is not None:
        by[g["season"]] += ov(g)
print(f"the rule at 1u: {sum(ps):+.1f}u on {len(ps)}, worst stretch {L.worst(ps):+.1f}u, worst season {min(by.values()):+.1f}u; "
      f"at 2u the worst stretch is {2 * L.worst(ps):+.1f}u")
print("S7 cells that clear:", won or "NONE")

# ---------------------------------------------------------------- S8 the NBA over, the main guys out
print("=" * 20, "S8 🏀 THE NBA OVER WHEN THE MAIN GUYS SIT (wired ½u from 11/13)")
import box as B  # noqa: E402

mins = defaultdict(dict)
for row in B.R.load("nba"):
    try:
        m = float(json.loads(row["stats"]).get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m
nba = L.table("nba")
hist = defaultdict(lambda: deque(maxlen=15))
gp = defaultdict(int)
for g in nba:
    bx = mins.get(g["id"])
    for side, t in (("H", g["home"]), ("A", g["away"])):
        k = (g["season"], t)
        g[side]["o15"] = None
        if bx and t in bx and gp[k] >= 10:
            tm = defaultdict(float)
            for gm in hist[k]:
                for p, m in gm.items():
                    tm[p] += m
            top = [p for p, _ in sorted(tm.items(), key=lambda kv: -kv[1])[:3]]
            last = hist[k][-1]
            out = [p for p in top if bx[t].get(p, 0) <= 0]
            g[side]["o15"] = len(out)
            g[side]["o15f"] = sum(1 for p in out if last.get(p, 0) > 0)
        if bx and t in bx:
            hist[k].append(dict(bx[t]))
            gp[k] += 1
rd = lambda g: (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"]   # noqa: E731
N = [g for g in nba if L.reg(g) and g["tot"] is not None and g["H"].get("o15") is not None and g["A"].get("o15") is not None]
R_ = [g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and rd(g) > -3 and (g["ovo"] or -110) >= -115]
L.cell("THE RULE -> OVER (every play)", [(g["season"], ov(g)) for g in R_])
L.cell("   seasons 2024 on", [(g["season"], ov(g)) for g in R_ if g["season"] >= 2024])
L.cell("   THIS season (2026-27) so far", [(g["season"], ov(g)) for g in R_ if g["season"] >= 2026])
won = []
for nm, f in (("4+ of the six out", lambda g: g["H"]["o15"] + g["A"]["o15"] >= 4), ("exactly 3 out", lambda g: g["H"]["o15"] + g["A"]["o15"] == 3),
              ("men out on BOTH teams", lambda g: g["H"]["o15"] >= 1 and g["A"]["o15"] >= 1),
              ("all of them on ONE team", lambda g: g["H"]["o15"] == 0 or g["A"]["o15"] == 0),
              ("2+ of them played the last game (fresh news)", lambda g: g["H"]["o15f"] + g["A"]["o15f"] >= 2),
              ("the number 225+", lambda g: g["tot"] >= 225), ("the number under 225", lambda g: g["tot"] < 225),
              ("the spread under 8", lambda g: g["sp"] is not None and abs(g["sp"]) < 8),
              ("the spread 8+", lambda g: g["sp"] is not None and abs(g["sp"]) >= 8),
              ("a team on a back-to-back", lambda g: g["H"].get("b2b") or g["A"].get("b2b")),
              ("nobody on a back-to-back", lambda g: not (g["H"].get("b2b") or g["A"].get("b2b")))):
    if judge(nm, [g for g in R_ if f(g)], R_, ov, ov1):
        won.append(nm)
ps = [ov(g) for g in sorted(R_, key=lambda g: g["start"]) if ov(g) is not None]
print(f"the rule at ½u: {0.5 * sum(ps):+.1f}u on {len(ps)}, worst stretch {0.5 * L.worst(ps):+.1f}u; at 1u {sum(ps):+.1f}u, worst {L.worst(ps):+.1f}u")
print("S8 cells that clear:", won or "NONE")

# ---------------------------------------------------------------- S9 the Europe morning under
print("=" * 20, "S9 🌍 THE EUROPE MORNING NFL UNDER (½u, the quit rule at 15 graded)")
P = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads2_1111", "dl", "games.csv")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


rows, allg = [], []
for r in csv.DictReader(open(P)):
    try:
        hs, as_, tl = float(r["home_score"]), float(r["away_score"]), float(r["total_line"])
    except (TypeError, ValueError):
        continue
    if r["game_type"] != "REG":
        continue
    try:
        uo = float(r["under_odds"])
    except (TypeError, ValueError):
        uo = -110.0
    pts = hs + as_
    pr = 0.0 if pts == tl else (dec(uo) - 1) if pts < tl else -1.0
    pr1 = 0.0 if pts == tl - 1 else (dec(uo) - 1) if pts < tl - 1 else -1.0
    hour = int((r.get("gametime") or "13:00").split(":")[0])
    g = dict(season=int(r["season"]), p=pr, p1=pr1, hour=hour, stadium=r.get("stadium") or "", loc=r.get("location"), day=r["gameday"])
    allg.append(g)
    st = g["stadium"].lower()
    if g["loc"] == "Neutral" and any(k in st for k in ("wembley", "tottenham", "twickenham", "allianz", "frankfurt", "deutsche bank", "munich",
                                                       "bernabeu", "croke", "olympia", "london")):
        rows.append(g)
print(f"international games in Europe with a closing total: {len(rows)} ({min(g['day'] for g in rows)} -> {max(g['day'] for g in rows)})")
L.TRAIN_TO = 2017
eu = lambda gs, k="p": [(g["season"], g[k]) for g in gs]   # noqa: E731
L.cell("every Europe game -> UNDER", eu(rows), train_to=2017)
am = [g for g in rows if g["hour"] < 12]
c = L.cell("kickoff before noon ET -> UNDER (the rule)", eu(am), train_to=2017)
L.cell("   a point worse than the close", eu(am, "p1"), train_to=2017)
L.cell("   2018 on (the study's window)", eu([g for g in am if g["season"] >= 2018]), train_to=2021)
L.cell("   2022 on", eu([g for g in am if g["season"] >= 2022]), train_to=2023)
L.cell("kickoff at noon ET or later -> UNDER", eu([g for g in rows if g["hour"] >= 12]), train_to=2017)
L.cell("every NFL regular-season under (the frame)", eu(allg), train_to=2017)
ps = [p for _, p in c["bets"]]
pool = [g["p"] for g in allg]
print(f"placebo: a random {len(ps)} NFL unders as good as the rule: {L.placebo(pool, len(ps), sum(ps) / len(ps))} of 2000")
rnd = random.Random(1117)
w = sum(1 for p in ps if p > 0)
print(f"the rule: {w}-{sum(1 for p in ps if p < 0)}; at ½u {0.5 * sum(ps):+.1f}u, worst stretch {0.5 * L.worst(ps):+.1f}u - {len(ps)} games in "
      f"{len({g['season'] for g in am})} seasons: a small sample, the quit rule is the judge")
L.done()
