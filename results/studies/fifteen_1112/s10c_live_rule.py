"""S10c - THE NBA 'TOP MEN OUT' OVER AS THE LIVE CODE CAN RUN IT. s10b's top three are 'by minutes so far this
season', which keeps a man who was traded in December or lost for the year in a team's top three forever - the live
injury report won't list a traded man, and a man gone for months is old news the team's own scoring already holds.
THE LIVE DEFINITION: a team's top three by total minutes over its LAST 15 GAMES (10+ team games this season) - the
men it is leaning on NOW; 'out' = no minutes tonight (live: listed OUT on the injury report before the tip).
Cells: the same rule, the read gate (both teams' season scoring no more than 3 under the total), the price limit,
the number a point worse, months, a placebo. Then windows of 10 / 20 games to show the 15 is not tuned."""
import json, random
from collections import defaultdict, deque

import lib as L
import box as B

mins = defaultdict(dict)
for row in B.R.load("nba"):
    try:
        m = float(json.loads(row["stats"]).get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m
nba = L.table("nba")


def stamp(win):
    hist = defaultdict(lambda: deque(maxlen=win))
    gp = defaultdict(int)
    key = f"o{win}"
    for g in nba:
        bx = mins.get(g["id"])
        for side, t in (("H", g["home"]), ("A", g["away"])):
            k = (g["season"], t)
            g[side][key] = None
            if bx and t in bx and gp[k] >= 10:
                tm = defaultdict(float)
                for gm in hist[k]:
                    for p, m in gm.items():
                        tm[p] += m
                top = [p for p, _ in sorted(tm.items(), key=lambda kv: -kv[1])[:3]]
                last = hist[k][-1]
                out = [p for p in top if bx[t].get(p, 0) <= 0]
                g[side][key] = len(out)
                g[side][key + "f"] = sum(1 for p in out if last.get(p, 0) > 0)       # fresh: he played the last game
            if bx and t in bx:
                hist[k].append(dict(bx[t]))
                gp[k] += 1


for w in (10, 15, 20):
    stamp(w)
ov = lambda rows, sh=0.0: [(g["season"], L.tot(g, "over", sh)) for g in rows]     # noqa: E731
un = lambda rows: [(g["season"], L.tot(g, "under")) for g in rows]               # noqa: E731
rd = lambda g: (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"]   # noqa: E731
N = [g for g in nba if L.reg(g) and g["tot"] is not None and g["H"].get("o15") is not None and g["A"].get("o15") is not None]
base = L.cell("every NBA over (both teams 10+ games in)", ov(N))
pool = [p for _, p in base["bets"]]
for w in (10, 15, 20):
    k = f"o{w}"
    print(f"\nTOP THREE BY MINUTES OVER THE LAST {w} GAMES")
    for n in (0, 1, 2):
        L.cell(f"  exactly {n} of the six out -> OVER", ov([g for g in N if g["H"][k] + g["A"][k] == n]))
    L.cell("  3+ of the six out -> OVER", ov([g for g in N if g["H"][k] + g["A"][k] >= 3]))
    L.cell("  3+ of the six out -> UNDER", un([g for g in N if g["H"][k] + g["A"][k] >= 3]))
    L.cell("  3+ out and the scoring read not 3+ under the total -> OVER",
           ov([g for g in N if g["H"][k] + g["A"][k] >= 3 and rd(g) > -3]))
print("\nTHE LIVE RULE (the 15-game window): 3+ of the six out, the read not fighting, the over no worse than -115")
R_ = [g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and rd(g) > -3 and (g["ovo"] or -110) >= -115]
x = L.cell("THE RULE -> OVER", ov(R_))
L.cell("  -> UNDER (the mirror)", un(R_))
L.cell("  the close 1 point against us", ov(R_, -1))
L.cell("  the close 1.5 against us", ov(R_, -1.5))
L.cell("  the close 2 against us", ov(R_, -2))
L.cell("  every one of them missed the last game too (old news)", ov([g for g in R_ if g["H"]["o15f"] + g["A"]["o15f"] == 0]))
L.cell("  at least one played the last game (fresh)", ov([g for g in R_ if g["H"]["o15f"] + g["A"]["o15f"] >= 1]))
L.cell("  exactly 3 out", ov([g for g in R_ if g["H"]["o15"] + g["A"]["o15"] == 3]))
L.cell("  4+ out", ov([g for g in R_ if g["H"]["o15"] + g["A"]["o15"] >= 4]))
for mm, nm in ((("10", "11", "12"), "Oct-Dec"), (("01",), "January"), (("02",), "February"), (("03",), "March"), (("04",), "April")):
    L.cell(f"  {nm}", ov([g for g in R_ if g["start"][5:7] in mm]))
L.cell("  before March 15", ov([g for g in R_ if not (g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04"))]))
L.cell("  from March 15", ov([g for g in R_ if g["start"][5:10] >= "03-15" and g["start"][5:7] in ("03", "04")]))
L.cell("  total under 225", ov([g for g in R_ if g["tot"] < 225]))
L.cell("  total 225+", ov([g for g in R_ if g["tot"] >= 225]))
L.cell("  spread under 10", ov([g for g in R_ if g["sp"] is not None and abs(g["sp"]) < 10]))
L.cell("  spread 10+", ov([g for g in R_ if g["sp"] is not None and abs(g["sp"]) >= 10]))
L.cell("  the rule WITHOUT the read gate", ov([g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and (g["ovo"] or -110) >= -115]))
L.cell("  the games the read gate drops", ov([g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and rd(g) <= -3]))
L.cell("  the games the price limit drops", ov([g for g in N if g["H"]["o15"] + g["A"]["o15"] >= 3 and rd(g) > -3 and (g["ovo"] or -110) < -115]))
ps = [p for _, p in x["bets"]]
print(f"\nplacebo: random {len(ps)} NBA overs as good as the rule: {L.placebo(pool, len(ps), sum(ps) / len(ps))} of 2000")
tr = [p for s, p in x["bets"] if s <= 2021]
bl = [p for s, p in x["bets"] if s > 2021]
ptr = [p for s, p in base["bets"] if s <= 2021]
pbl = [p for s, p in base["bets"] if s > 2021]
rnd = random.Random(5)
k = sum(1 for _ in range(4000) if sum(rnd.sample(ptr, len(tr))) / len(tr) >= sum(tr) / len(tr)
        and sum(rnd.sample(pbl, len(bl))) / len(bl) >= sum(bl) / len(bl))
print(f"   ... as good in BOTH halves at once: {k} of 4000")
w = sum(1 for p in ps if p > 0)
l_ = sum(1 for p in ps if p < 0)
by = defaultdict(float)
for s, p in x["bets"]:
    by[s] += 0.5 * p
print(f"the rule: {w}-{l_} = {100 * w / (w + l_):.1f}%; at 1/2u {0.5 * sum(ps):+.1f}u on {len(ps)} (about {len(ps) / 8:.0f} a season), "
      f"worst stretch {0.5 * L.worst(ps):.1f}u, worst season {min(by.values()):+.1f}u")
L.done()
