"""11/12 DEEP PROGRAM - B4b: THE COLLEGE TEAM PLAYING OUT THE STRING (B4's one strong cell: a team that can no longer
reach six wins, November on, against a team still alive or already in: ATS -14.9% on 462, z -3.4, 8 of 8 seasons).
The follow-ups before it is anything: is it just 'bad teams late' (the control: same record, not yet eliminated), is it
the known big-dog-late fade (11/11 S8: dogs getting 14+ in Nov-Dec -11.1%), the dose, the venue, the price, a placebo.
Usage: python results/studies/deep_1112/b4b_string.py > results/studies/deep_1112/b4b_string.out"""
import os, random, sys
import dlib as D
import lib as L

sys.argv = sys.argv[:1]
import b4_ncaaf_november as B     # noqa: E402  (re-prints B4; this file's lines follow)

print("\n" + "=" * 30 + " B4b: THE STRING, FOLLOW-UPS")
F, oth = B.F, B.other if hasattr(B, "other") else L.other
nov = B.nov


def sides(cond):
    out = []
    for r in F:
        for s in "HA":
            if cond(r, s):
                out.append((r, s))
    return out


def show(name, rs):
    L.cell(f"{name} | ATS", [(r["g"]["season"], L.ats(r["g"], s)) for r, s in rs])
    L.cell(f"{'':{len(name)}} | the side across ATS", [(r["g"]["season"], L.ats(r["g"], L.other(s))) for r, s in rs])


base = lambda r, s: nov(r) and r[s]["dead"] and not r[L.other(s)]["dead"]      # noqa: E731
show("the eliminated team vs alive / in (the cell)", sides(base))
show("  getting under 14 (not the big-dog fade)", sides(lambda r, s: base(r, s) and (L.spread(r["g"], s) or 0) < 14))
show("  getting 14+", sides(lambda r, s: base(r, s) and (L.spread(r["g"], s) or 0) >= 14))
show("  getting 0.5-7", sides(lambda r, s: base(r, s) and 0 < (L.spread(r["g"], s) or 0) <= 7))
show("  getting 7.5-13.5", sides(lambda r, s: base(r, s) and 7 < (L.spread(r["g"], s) or 0) < 14))
show("  laying points", sides(lambda r, s: base(r, s) and (L.spread(r["g"], s) or 0) < 0))
show("  at home", sides(lambda r, s: base(r, s) and s == "H"))
show("  on the road", sides(lambda r, s: base(r, s) and s == "A"))
show("  the other team already bowl-eligible", sides(lambda r, s: base(r, s) and r[L.other(s)]["in"]))
show("  the other team still needs wins (alive, not in)", sides(lambda r, s: base(r, s) and not r[L.other(s)]["in"]))
show("  its last game of the year", sides(lambda r, s: base(r, s) and r[s]["last"]))
show("  not its last game", sides(lambda r, s: base(r, s) and not r[s]["last"]))
show("  0-2 wins", sides(lambda r, s: base(r, s) and r[s]["w"] <= 2))
show("  3-4 wins", sides(lambda r, s: base(r, s) and r[s]["w"] >= 3))
print(" -- CONTROLS")
show("CONTROL: 4 wins or fewer after 8+ games but still ALIVE, vs a team alive / in, Nov on", sides(
    lambda r, s: nov(r) and not r[s]["dead"] and r[s]["n"] >= 8 and r[s]["w"] <= 4 and not r[L.other(s)]["dead"]))
show("CONTROL: both teams eliminated", sides(lambda r, s: nov(r) and r[s]["dead"] and r[L.other(s)]["dead"] and s == "H"))
show("CONTROL: a .333-or-worse team (6+ games) in OCTOBER vs a better record", sides(
    lambda r, s: r["g"]["start"][5:7] == "10" and r[s]["n"] >= 6 and r[s]["w"] / r[s]["n"] <= 0.334 and r[L.other(s)]["n"] and r[L.other(s)]["w"] / max(1, r[L.other(s)]["n"]) > 0.5))
# placebo: random November sides
cell = [(r, s) for r, s in sides(base)]
mine = [L.ats(r["g"], s) for r, s in cell]
mine = [x for x in mine if x is not None]
pool = [L.ats(r["g"], s) for r in F if nov(r) for s in "HA"]
pool = [x for x in pool if x is not None]
tgt = sum(mine) / len(mine)
rnd = random.Random(1112)
hits = sum(1 for _ in range(2000) if sum(rnd.sample(pool, len(mine))) / len(mine) <= tgt)
print(f" -- PLACEBO: a random {len(mine)} November sides did as BADLY as the cell ({100 * tgt:+.1f}%) {hits} of 2,000 times (the pool itself {100 * sum(pool) / len(pool):+.1f}%)")
# the moneyline the board would bet: the favorite across from an eliminated dog, -150..-101; the eliminated dog +100..+350
ml_d, ml_fa, ml_f = [], [], []
for r, s in cell:
    g = r["g"]
    o, oo = L.odds(g, s), L.odds(g, L.other(s))
    if o is not None and 100 <= o <= 350:
        ml_d.append((g["season"], L.ml(g, s)))
    if oo is not None and -150 <= oo <= -101:
        ml_fa.append((g["season"], L.ml(g, L.other(s))))
    if oo is not None and -400 <= oo <= -151:
        ml_f.append((g["season"], L.ml(g, L.other(s))))
print(" -- THE RULE AS THE LIVE ENGINE CAN SEE IT (the feed holds 3 days of schedule, not the season's: 'can't reach six' = 7+ LOSSES; the other team 6 or fewer)")
live = lambda r, s: nov(r) and r[s]["n"] - r[s]["w"] >= 7 and r[L.other(s)]["n"] - r[L.other(s)]["w"] <= 6      # noqa: E731
show("7+ losses vs 6 or fewer, Nov on", sides(live))
show("  as a dog (the dog-score weight's cell)", sides(lambda r, s: live(r, s) and (L.spread(r["g"], s) or 0) > 0))
show("  as a dog getting under 14", sides(lambda r, s: live(r, s) and 0 < (L.spread(r["g"], s) or 0) < 14))
lv = sides(live)
L.cell("7+ losses: its moneyline as a dog +100..+350", [(r["g"]["season"], L.ml(r["g"], s)) for r, s in lv if L.odds(r["g"], s) is not None and 100 <= L.odds(r["g"], s) <= 350])
L.cell("7+ losses: the favorite ACROSS -150..-101, moneyline", [(r["g"]["season"], L.ml(r["g"], L.other(s))) for r, s in lv if L.odds(r["g"], L.other(s)) is not None and -150 <= L.odds(r["g"], L.other(s)) <= -101])
L.cell("the eliminated dog's moneyline +100..+350", ml_d)
L.cell("the favorite ACROSS -150..-101, moneyline", ml_fa)
L.cell("the favorite ACROSS -151..-400, moneyline", ml_f)
L.done()
