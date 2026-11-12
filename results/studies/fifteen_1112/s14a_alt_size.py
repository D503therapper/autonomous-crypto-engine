"""S14a - THE ⛰️ ALTITUDE OVER: DOES IT EARN 1u? (the 11/11 rule re-built here from scratch on lib.table - a third
build of the same cell - then sized.) The rule: a college regular-season game on a home floor 1,400 m+, never neutral,
the over at the close, price no worse than -130, the plain points read (both teams' scoring; last season fills in
before 5 finals, 10+ finals last season) no more than 3 under the total."""
import math
import lib as L

G = [g for g in L.table("ncaab") if L.reg(g) and g["tot"] is not None]


def fill(f):
    n = f["n"]
    if n >= 5:
        return f["pf"], f["pa"]
    pv = f.get("prev")
    if not pv or pv["n"] < 10:
        return None
    pf = (f.get("pf", 0) * n + (5 - n) * pv["pf"]) / 5
    pa = (f.get("pa", 0) * n + (5 - n) * pv["pa"]) / 5
    return pf, pa


def read(g):
    h, a = fill(g["H"]), fill(g["A"])
    if not h or not a:
        return None
    return (h[0] + a[1] + a[0] + h[1]) / 2


rule = []
for g in G:
    if g["neutral"] or (g["elev"] or 0) < 1400:
        continue
    o = g["ovo"] or -110
    if o < -130:
        continue
    r = read(g)
    if r is None or r - g["tot"] < -3:
        continue
    rule.append(g)

print("THE RULE AT THE CLOSE")
c = L.cell("altitude over, the 11/11 rule", [(g["season"], L.tot(g, "over")) for g in rule])
L.cell("  the under (the mirror)", [(g["season"], L.tot(g, "under")) for g in rule])
L.cell("  the over, the close + 1 point against us", [(g["season"], L.tot(g, "over", -1)) for g in rule])
L.cell("  the over, the close + 1.5 against us", [(g["season"], L.tot(g, "over", -1.5)) for g in rule])
L.cell("  November", [(g["season"], L.tot(g, "over")) for g in rule if g["start"][5:7] == "11"])
L.cell("  December", [(g["season"], L.tot(g, "over")) for g in rule if g["start"][5:7] == "12"])
L.cell("  Jan-Mar", [(g["season"], L.tot(g, "over")) for g in rule if g["start"][5:7] in ("01", "02", "03")])
L.cell("  conference-season weeknights (Mon-Thu)", [(g["season"], L.tot(g, "over")) for g in rule if g["day"].weekday() < 4])
L.cell("  2023 on only", [(g["season"], L.tot(g, "over")) for g in rule if g["season"] >= 2023])
low = [g for g in G if not g["neutral"] and (g["elev"] or 0) < 900]
pool = [L.tot(g, "over") for g in low]
ps = [p for _, p in c["bets"]]
print(f"placebo: random {len(ps)} low-ground home overs as good as the rule: "
      f"{L.placebo(pool, len(ps), sum(ps) / len(ps), k=2000)} of 2000")

print("\nSIZING (flat units a play, in game order; 1u = 1% of the roll)")
n = len(ps)
w = sum(1 for p in ps if p > 0)
l_ = sum(1 for p in ps if p < 0)
avg_win = sum(p for p in ps if p > 0) / w
p_hat = w / (w + l_)
kelly = (p_hat * avg_win - (1 - p_hat)) / avg_win
lo = p_hat - 1.645 * math.sqrt(p_hat * (1 - p_hat) / (w + l_))        # the 5% low end of the win rate
kelly_lo = (lo * avg_win - (1 - lo)) / avg_win
print(f"won {w} lost {l_} = {100 * p_hat:.1f}% at an average win of {avg_win:.3f}; full Kelly {100 * kelly:.1f}% of the roll, "
      f"quarter-Kelly {25 * kelly:.2f}u; on the win rate's 5% low end ({100 * lo:.1f}%): quarter-Kelly {25 * kelly_lo:.2f}u")
bl = [p for s, p in c["bets"] if s > L.TRAIN_TO]
for u in (0.5, 1.0, 2.0):
    by = {}
    for s, p in c["bets"]:
        by.setdefault(s, []).append(p * u)
    print(f"  {u}u: {u * sum(ps):+.1f}u on {n} ({u * sum(bl):+.1f}u blind), worst stretch {u * L.worst(ps):.1f}u, "
          f"worst season {min(sum(v) for v in by.values()):+.1f}u, by season "
          + " ".join(f"{str(s)[2:]}:{sum(v):+.1f}" for s, v in sorted(by.items())))
# the longest losing run and the worst 30
run = worst_run = 0
for p in ps:
    run = run + 1 if p < 0 else 0
    worst_run = max(worst_run, run)
w30 = min(sum(ps[i:i + 30]) for i in range(len(ps) - 29))
print(f"  longest losing run {worst_run}; the worst 30 plays in a row {w30:+.1f}u at 1u")
L.done()
