"""S10b - THE NBA OVER WHEN THE TOP-MINUTES MEN SIT (s10's one cell that stood out: three+ of the six top-minutes men
out -> the over +11.0% on 615, 8 of 8 seasons). Taken apart:

WHO IS 'OUT' AND WHEN WE'D KNOW IT. From the box scores, walk-forward: a team's top three by minutes so far this season
(10+ team games); 'out' = no minutes tonight. Two kinds - KNOWN (he also missed the team's last game: on the injury
report for a day or more, known at the 8 AM board) and FRESH (he played the last game: tonight's news - a rest night, a
late scratch - which the 8 AM board may not have). The play has to live on the KNOWN ones.
Then: the dose, months, the total's size, price, the number a point worse, a second definition of the top men (top
five by minutes a game), a placebo, both halves, every season."""
import json, os, random, sys
from collections import defaultdict

import lib as L
import box as B

R = B.R
mins = defaultdict(dict)
for row in R.load("nba"):
    try:
        m = float(json.loads(row["stats"]).get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m

nba = L.table("nba")
tot_m = defaultdict(lambda: defaultdict(float))
gpl = defaultdict(lambda: defaultdict(int))          # games played by player
gp = defaultdict(int)
last_played = defaultdict(dict)                       # (season, team) -> {pid: did he play the team's last game}
for g in nba:
    bx = mins.get(g["id"])
    for side, t in (("H", g["home"]), ("A", g["away"])):
        k = (g["season"], t)
        f = g[side]
        f["known"] = f["fresh"] = f["out3"] = f["out5"] = f["known5"] = None
        if bx and t in bx and gp[k] >= 10:
            top3 = [p for p, _ in sorted(tot_m[k].items(), key=lambda kv: -kv[1])[:3]]
            # top five by minutes a game among men with 5+ games
            mpg = sorted(((tot_m[k][p] / gpl[k][p], p) for p in tot_m[k] if gpl[k][p] >= 5), reverse=True)[:5]
            top5 = [p for _, p in mpg]
            out = [p for p in top3 if bx[t].get(p, 0) <= 0]
            f["out3"] = len(out)
            f["known"] = sum(1 for p in out if not last_played[k].get(p, False))
            f["fresh"] = len(out) - f["known"]
            f["out3g"] = sum(1 for p in top5[:3] if bx[t].get(p, 0) <= 0)
            o5 = [p for p in top5 if bx[t].get(p, 0) <= 0]
            f["out5"] = len(o5)
            f["known5"] = sum(1 for p in o5 if not last_played[k].get(p, False))
        if bx and t in bx:
            for p, m in bx[t].items():
                tot_m[k][p] += m
                if m > 0:
                    gpl[k][p] += 1
            last_played[k] = {p: m > 0 for p, m in bx[t].items()}
            gp[k] += 1

N = [g for g in nba if L.reg(g) and g["tot"] is not None and g["H"]["out3"] is not None and g["A"]["out3"] is not None]
ov = lambda rows, sh=0.0: [(g["season"], L.tot(g, "over", sh)) for g in rows]     # noqa: E731
un = lambda rows: [(g["season"], L.tot(g, "under")) for g in rows]               # noqa: E731
o3 = lambda g: g["H"]["out3"] + g["A"]["out3"]                                   # noqa: E731
kn = lambda g: g["H"]["known"] + g["A"]["known"]                                 # noqa: E731
fr = lambda g: g["H"]["fresh"] + g["A"]["fresh"]                                 # noqa: E731

print(f"{len(N)} regular-season NBA games with a total and both teams 10+ games in")
base = L.cell("every one, the over", ov(N))
pool0 = [p for _, p in base["bets"]]
print("\nTHE DOSE - how many of the six top-minutes men sit")
for k in range(0, 5):
    L.cell(f"exactly {k} out -> OVER", ov([g for g in N if o3(g) == k]))
L.cell("3+ out -> OVER", ov([g for g in N if o3(g) >= 3]))
L.cell("3+ out -> UNDER", un([g for g in N if o3(g) >= 3]))
print("\nKNOWN (missed the last game too) vs FRESH (played the last game)")
for k in range(0, 5):
    L.cell(f"exactly {k} KNOWN out -> OVER", ov([g for g in N if kn(g) == k]))
for k in (2, 3, 4):
    L.cell(f"{k}+ KNOWN out -> OVER", ov([g for g in N if kn(g) >= k]))
    L.cell(f"{k}+ KNOWN out -> UNDER", un([g for g in N if kn(g) >= k]))
for k in (1, 2, 3):
    L.cell(f"{k}+ FRESH out, none known -> OVER", ov([g for g in N if fr(g) >= k and kn(g) == 0]))
L.cell("3+ out, ALL of them known -> OVER", ov([g for g in N if o3(g) >= 3 and fr(g) == 0]))
L.cell("3+ out, at least one fresh -> OVER", ov([g for g in N if o3(g) >= 3 and fr(g) >= 1]))
K3 = [g for g in N if kn(g) >= 3]
x = L.cell("THE CELL: 3+ of the six KNOWN out -> OVER", ov(K3))
print("\nTHE CELL, CUT")
L.cell("  the close 1 point against us", ov(K3, -1))
L.cell("  the close 2 points against us", ov(K3, -2))
for mm, nm in ((("10", "11"), "Oct-Nov"), (("12",), "December"), (("01",), "January"), (("02",), "February"), (("03",), "March"), (("04",), "April")):
    L.cell(f"  {nm}", ov([g for g in K3 if g["start"][5:7] in mm]))
L.cell("  before March 15", ov([g for g in K3 if not (g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04"))]))
L.cell("  from March 15 (the tank)", ov([g for g in K3 if g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04")]))
L.cell("  both teams have a man out", ov([g for g in K3 if g["H"]["known"] >= 1 and g["A"]["known"] >= 1]))
L.cell("  all on one team", ov([g for g in K3 if g["H"]["known"] == 0 or g["A"]["known"] == 0]))
qs = sorted(g["tot"] for g in N)
L.cell("  total under 220", ov([g for g in K3 if g["tot"] < 220]))
L.cell("  total 220-230", ov([g for g in K3 if 220 <= g["tot"] < 230]))
L.cell("  total 230+", ov([g for g in K3 if g["tot"] >= 230]))
L.cell("  over priced -112 or cheaper", ov([g for g in K3 if (g["ovo"] or -110) >= -112]))
L.cell("  over priced worse than -112", ov([g for g in K3 if (g["ovo"] or -110) < -112]))
L.cell("  spread 0-6.5", ov([g for g in K3 if g["sp"] is not None and abs(g["sp"]) <= 6.5]))
L.cell("  spread 7-11.5", ov([g for g in K3 if g["sp"] is not None and 7 <= abs(g["sp"]) <= 11.5]))
L.cell("  spread 12+", ov([g for g in K3 if g["sp"] is not None and abs(g["sp"]) >= 12]))
L.cell("  a team on a back-to-back", ov([g for g in K3 if g["H"].get("b2b") or g["A"].get("b2b")]))
L.cell("  nobody on a back-to-back", ov([g for g in K3 if not (g["H"].get("b2b") or g["A"].get("b2b"))]))
# the teams' own scoring read against the total (never one factor: is the read fighting the over?)
rd = lambda g: (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"]   # noqa: E731
L.cell("  both teams' season scoring 4+ OVER the total", ov([g for g in K3 if rd(g) >= 4]))
L.cell("  season scoring within 4 of the total", ov([g for g in K3 if abs(rd(g)) < 4]))
L.cell("  season scoring 4+ UNDER the total", ov([g for g in K3 if rd(g) <= -4]))
l5 = lambda g: (g["H"]["l5pf"] + g["A"]["l5pa"] + g["A"]["l5pf"] + g["H"]["l5pa"]) / 2 - g["tot"]   # noqa: E731
L.cell("  the last five games' scoring 4+ over the total", ov([g for g in K3 if l5(g) >= 4]))
L.cell("  the last five 4+ under the total", ov([g for g in K3 if l5(g) <= -4]))
print("\nTHE WIDER CELL - 3+ of the six OUT TONIGHT, known or fresh (the rule a live play would run once the injury report"
      " lists them out)")
O3 = [g for g in N if o3(g) >= 3]
y = L.cell("3+ of the six out -> OVER", ov(O3))
L.cell("  the close 1 point against us", ov(O3, -1))
L.cell("  the close 1.5 against us", ov(O3, -1.5))
L.cell("  the close 2 points against us", ov(O3, -2))
for mm, nm in ((("10", "11", "12"), "Oct-Dec"), (("01",), "January"), (("02",), "February"), (("03",), "March"), (("04",), "April")):
    L.cell(f"  {nm}", ov([g for g in O3 if g["start"][5:7] in mm]))
L.cell("  before March 15", ov([g for g in O3 if not (g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04"))]))
L.cell("  from March 15 (the tank)", ov([g for g in O3 if g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04")]))
L.cell("  both teams have a man out", ov([g for g in O3 if g["H"]["out3"] >= 1 and g["A"]["out3"] >= 1]))
L.cell("  all on one team", ov([g for g in O3 if g["H"]["out3"] == 0 or g["A"]["out3"] == 0]))
L.cell("  total under 220", ov([g for g in O3 if g["tot"] < 220]))
L.cell("  total 220-230", ov([g for g in O3 if 220 <= g["tot"] < 230]))
L.cell("  total 230+", ov([g for g in O3 if g["tot"] >= 230]))
L.cell("  over priced -112 or cheaper", ov([g for g in O3 if (g["ovo"] or -110) >= -112]))
L.cell("  over priced worse than -112", ov([g for g in O3 if (g["ovo"] or -110) < -112]))
L.cell("  a team on a back-to-back", ov([g for g in O3 if g["H"].get("b2b") or g["A"].get("b2b")]))
L.cell("  nobody on a back-to-back", ov([g for g in O3 if not (g["H"].get("b2b") or g["A"].get("b2b"))]))
L.cell("  season scoring 4+ OVER the total", ov([g for g in O3 if rd(g) >= 4]))
L.cell("  season scoring within 4", ov([g for g in O3 if abs(rd(g)) < 4]))
L.cell("  season scoring 4+ UNDER the total", ov([g for g in O3 if rd(g) <= -4]))
L.cell("  season scoring 3+ under the total (the read fights the over)", ov([g for g in O3 if rd(g) <= -3]))
L.cell("  season scoring no more than 3 under (the read is not fighting)", ov([g for g in O3 if rd(g) > -3]))
L.cell("  home floor (not neutral)", ov([g for g in O3 if not g["neutral"]]))
ps3 = [p for _, p in y["bets"]]
print(f"   placebo: random {len(ps3)} NBA overs as good: {L.placebo(pool0, len(ps3), sum(ps3) / len(ps3))} of 2000")
tr3 = [p for s_, p in y["bets"] if s_ <= 2021]
bl3 = [p for s_, p in y["bets"] if s_ > 2021]
rnd3 = random.Random(5)
k3 = sum(1 for _ in range(4000) if sum(rnd3.sample([p for s_, p in base["bets"] if s_ <= 2021], len(tr3))) / len(tr3) >= sum(tr3) / len(tr3)
         and sum(rnd3.sample([p for s_, p in base["bets"] if s_ > 2021], len(bl3))) / len(bl3) >= sum(bl3) / len(bl3))
print(f"   ... as good in BOTH halves at once: {k3} of 4000")
w3 = sum(1 for p in ps3 if p > 0)
l3 = sum(1 for p in ps3 if p < 0)
print(f"   won {w3}-{l3} = {100 * w3 / (w3 + l3):.1f}%; at 1/2u {0.5 * sum(ps3):+.1f}u on {len(ps3)}, worst stretch "
      f"{0.5 * L.worst(ps3):.1f}u; about {len(ps3) / 8:.0f} a season")
# a third definition: the top three by minutes A GAME (5+ games played)
print("\nA THIRD DEFINITION - the top three by minutes a game")
L.cell("3+ of the six (by minutes a game) out -> OVER", ov([g for g in N if g["H"]["out3g"] + g["A"]["out3g"] >= 3]))
L.cell("2 of the six (by minutes a game) out -> OVER", ov([g for g in N if g["H"]["out3g"] + g["A"]["out3g"] == 2]))
L.cell("4+ of the ten (top five a team, any) out -> OVER", ov([g for g in N if g["H"]["out5"] + g["A"]["out5"] >= 4]))
L.cell("5+ of the ten out -> OVER", ov([g for g in N if g["H"]["out5"] + g["A"]["out5"] >= 5]))
L.cell("6+ of the ten out -> OVER", ov([g for g in N if g["H"]["out5"] + g["A"]["out5"] >= 6]))

print("\nA SECOND DEFINITION - the top five by minutes a game (5+ games played)")
k5 = lambda g: g["H"]["known5"] + g["A"]["known5"]   # noqa: E731
for k in (3, 4, 5, 6):
    L.cell(f"{k}+ of the ten KNOWN out -> OVER", ov([g for g in N if k5(g) >= k]))
L.cell("exactly 0 of the ten out -> OVER", ov([g for g in N if g["H"]["out5"] + g["A"]["out5"] == 0]))
print("\nTHE MISS (points scored minus the total, the price-free read)")
for nm, rows in (("no one known out", [g for g in N if kn(g) == 0]), ("1", [g for g in N if kn(g) == 1]),
                 ("2", [g for g in N if kn(g) == 2]), ("3+", K3)):
    for lab, sel in (("train", lambda g: g["season"] <= 2021), ("blind", lambda g: g["season"] > 2021)):
        v = [g["hs"] + g["as"] - g["tot"] for g in rows if sel(g)]
        print(f"   {nm} known out, {lab}: {sum(v) / len(v):+.2f} points on {len(v)}")
ps = [p for _, p in x["bets"]]
pool = [p for _, p in base["bets"]]
print(f"\nplacebo: random {len(ps)} NBA overs as good as the cell: {L.placebo(pool, len(ps), sum(ps) / len(ps))} of 2000")
tr = [p for s, p in x["bets"] if s <= 2021]
bl = [p for s, p in x["bets"] if s > 2021]
ptr = [p for s, p in base["bets"] if s <= 2021]
pbl = [p for s, p in base["bets"] if s > 2021]
rnd = random.Random(5)
k = sum(1 for _ in range(4000) if sum(rnd.sample(ptr, len(tr))) / len(tr) >= sum(tr) / len(tr)
        and sum(rnd.sample(pbl, len(bl))) / len(bl) >= sum(bl) / len(bl))
print(f"   ... as good in BOTH halves at once: {k} of 4000")
print(f"sizing: at 1/2u {0.5 * sum(ps):+.1f}u on {len(ps)}, worst stretch {0.5 * L.worst(ps):.1f}u; about {len(ps) / 8:.0f} a season")
w = sum(1 for p in ps if p > 0)
l_ = sum(1 for p in ps if p < 0)
print(f"   won {w}-{l_} = {100 * w / (w + l_):.1f}% (the juice needs 52.4%)")
L.done()
