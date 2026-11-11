"""S5b. THE NFL LOOKAHEAD DOG - the one S5 cell that held in both halves: a favorite laying 6+ whose NEXT game is
against a .700+ team (4+ games played) fails its number. Dose, seasons, the base it has to beat, the real juice where
nflverse has it, a placebo, and the Tuesday number from the paid history (2020-25).
   python s5b_lookahead.py"""
import random
from collections import defaultdict
from datetime import date, timedelta
import lib2 as L

o = L.Out("s5b")
B, N = L.B, L.N
random.seed(11)
G = [g for g in N.games() if g["reg"]]
log = defaultdict(list)
for g in G:
    log[(g["season"], g["home"])].append(g)
    log[(g["season"], g["away"])].append(g)


def tm(g, t):
    return g["m"] if g["home"] == t else -g["m"]


def rec(season, t, before):
    pr = [x for x in log[(season, t)] if x["date"] < before]
    return sum(1 for x in pr if tm(x, t) > 0), len(pr)


ROWS = []          # one row per game with a favorite: the DOG's bet
for g in G:
    if g["hl"] == 0:
        continue
    fav, dog = (g["home"], g["away"]) if g["hl"] < 0 else (g["away"], g["home"])
    lay = abs(g["hl"])
    lg = log[(g["season"], fav)]
    i = lg.index(g)
    nxt = lg[i + 1] if i + 1 < len(lg) else None
    dl = log[(g["season"], dog)]
    j = dl.index(g)
    dnxt = dl[j + 1] if j + 1 < len(dl) else None
    r = -tm(g, fav) + lay                     # the dog's cover margin
    juice = (g["aso"] if g["hl"] < 0 else g["hso"]) or -110
    if not -130 <= juice <= 115:
        juice = -110
    row = {"g": g, "season": g["season"], "lay": lay, "res": r, "p110": 0.0 if r == 0 else (L.dec(-110) - 1 if r > 0 else -1.0),
           "p": 0.0 if r == 0 else (L.dec(juice) - 1 if r > 0 else -1.0), "nx": None, "nxn": 0, "dnx": None, "fav": fav, "dog": dog,
           "dog_home": g["hl"] > 0 and not g["neutral"], "gap": None}
    if nxt is not None:
        no = nxt["away"] if nxt["home"] == fav else nxt["home"]
        w, n = rec(g["season"], no, g["date"])
        row["nx"], row["nxn"] = (w / n if n else None), n
        row["gap"] = (date.fromisoformat(nxt["date"]) - date.fromisoformat(g["date"])).days
        row["nxdiv"] = nxt["div"]
    if dnxt is not None:
        no = dnxt["away"] if dnxt["home"] == dog else dnxt["home"]
        w, n = rec(g["season"], no, g["date"])
        row["dnx"] = (w / n) if n >= 4 else None
    ROWS.append(row)


def show(name, rs, key="p110"):
    tr = [(r["season"], r[key]) for r in rs if r["season"] <= 2014]
    bl = [(r["season"], r[key]) for r in rs if r["season"] >= 2015]
    ut, ub = L.by_season(tr), L.by_season(bl)
    o(f"   {name[:62]:62s} {L.st([r[key] for r in rs])} | train {L.st([p for _, p in tr])[6:]} ({ut[0]}/{ut[1]}) | BLIND {L.st([p for _, p in bl])[6:]} ({ub[0]}/{ub[1]})")


o("== the dog's ATS at the close (-110), by what the favorite lays and its NEXT opponent's record (4+ games) ==")
for lay in (3, 6, 7.5, 10):
    base = [r for r in ROWS if r["lay"] >= lay]
    show(f"BASE: every dog getting {lay}+", base)
    for lo, hi in ((0.0, 0.3), (0.3, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01), (0.7, 1.01), (0.6, 1.01)):
        rs = [r for r in base if r["nx"] is not None and r["nxn"] >= 4 and lo <= r["nx"] < hi]
        show(f"   lay {lay}+, the favorite's next opponent {lo:.3f}-{hi:.3f}", rs)
LA = [r for r in ROWS if r["lay"] >= 6 and r["nx"] is not None and r["nxn"] >= 4 and r["nx"] >= 0.7]
o("\n== THE CELL (lay 6+, next opponent .700+): cuts ==")
show("the cell, -110", LA)
show("the cell, nflverse's own closing juice where it has one", LA, "p")
show("   the dog at home", [r for r in LA if r["dog_home"]])
show("   the dog on the road", [r for r in LA if not r["dog_home"]])
show("   next game inside 8 days (no bye between)", [r for r in LA if r["gap"] is not None and r["gap"] <= 8])
show("   the next game is a division game", [r for r in LA if r.get("nxdiv")])
show("   the next game is NOT a division game", [r for r in LA if not r.get("nxdiv")])
show("   this game is a division game", [r for r in LA if r["g"]["div"]])
show("   this game is NOT a division game", [r for r in LA if not r["g"]["div"]])
show("   weeks 5-9", [r for r in LA if r["g"]["week"] <= 9])
show("   weeks 10-18", [r for r in LA if r["g"]["week"] >= 10])
show("   lay 6-9.5", [r for r in LA if r["lay"] < 10])
show("   lay 10+", [r for r in LA if r["lay"] >= 10])
show("   the DOG also has a .700+ team next (both looking ahead)", [r for r in LA if r["dnx"] is not None and r["dnx"] >= 0.7])
show("   2020-2026 only", [r for r in LA if r["season"] >= 2020])
o("   by season (ROI, n): " + L.by_season([(r["season"], r["p110"]) for r in LA])[2])
five = defaultdict(list)
for r in LA:
    five[(r["season"] - 1999) // 4].append(r["p110"])
o("   four-season blocks: " + " | ".join(f"{1999 + 4 * k}-{min(2026, 2002 + 4 * k)}: {L.roi(v):+.1f}% ({len(v)})" for k, v in sorted(five.items())))
# the mirror: the DOG has the lookahead (the dog's next opponent is .700+, the favorite's isn't)
show("MIRROR: the DOG getting 6+ has a .700+ team next, the favorite doesn't", [r for r in ROWS if r["lay"] >= 6 and r["dnx"] is not None and r["dnx"] >= 0.7 and not (r["nx"] is not None and r["nxn"] >= 4 and r["nx"] >= 0.7)])
# the general form: ANY side (favorite or dog, any spread) across a team with a .700+ opponent next, when it has none itself
def nx7(v):
    return v is not None and v >= 0.7
gen_d = [r for r in ROWS if nx7(r["nx"]) and r["nxn"] >= 4 and not nx7(r["dnx"])]            # bet the dog (the favorite looks ahead)
gen_f = [dict(r, p110=(0.0 if r["res"] == 0 else (L.dec(-110) - 1 if r["res"] < 0 else -1.0))) for r in ROWS
         if nx7(r["dnx"]) and not (nx7(r["nx"]) and r["nxn"] >= 4)]                              # bet the favorite (the dog looks ahead)
show("GENERAL: the dog, any spread, when only the favorite has a .700+ team next", gen_d)
show("GENERAL: the favorite, any spread, when only the dog has a .700+ team next", gen_f)
show("GENERAL: both together (the side ACROSS the team looking ahead)", gen_d + gen_f)
show("   ... spreads of 6+ only", [r for r in gen_d + gen_f if r["lay"] >= 6])
show("   ... spreads under 6", [r for r in gen_d + gen_f if r["lay"] < 6])
# the moneyline on the same dogs (information)
ml = []
for r in LA:
    g = r["g"]
    od = g["aml"] if g["hl"] < 0 else g["hml"]
    if od:
        ml.append((r["season"], (L.dec(od) - 1) if r["res"] - r["lay"] > 0 else -1.0))
o(f"   the same dogs on the MONEYLINE (nflverse's close, where it has one): {L.st([p for _, p in ml])}")

o("\n== PLACEBO: random sets of dogs getting 6+ (same count, same train / blind mix) ==")
pool_t = [r["p110"] for r in ROWS if r["lay"] >= 6 and r["season"] <= 2014]
pool_b = [r["p110"] for r in ROWS if r["lay"] >= 6 and r["season"] >= 2015]
nt, nb = sum(1 for r in LA if r["season"] <= 2014), sum(1 for r in LA if r["season"] >= 2015)
real_t, real_b = L.roi([r["p110"] for r in LA if r["season"] <= 2014]), L.roi([r["p110"] for r in LA if r["season"] >= 2015])
real = L.roi([r["p110"] for r in LA])
both = allb = 0
for _ in range(5000):
    a, b = random.sample(pool_t, nt), random.sample(pool_b, nb)
    both += L.roi(a) >= real_t and L.roi(b) >= real_b
    allb += (sum(a) + sum(b)) / (nt + nb) * 100 >= real
o(f"   a random set did as well overall {allb} of 5000 times; as well in BOTH halves {both} of 5000")

# ---------------- the Tuesday number (paid history, 2020-25) ----------------
o("\n== THE TUESDAY NUMBER (the paid history's first fair look, 2020-25): the same dogs at the market number / the best book ==")
fin = B.all_finals("nfl")
by = defaultdict(list)
for x in fin:
    by[x["start"][:10]].append(x)
link = {}
for r in LA:
    g = r["g"]
    d0 = date.fromisoformat(g["date"])
    for dd in (0, 1):
        hit = [x for x in by.get((d0 + timedelta(days=dd)).isoformat(), []) if x["hs"] - x["as"] == g["m"] and x["hs"] + x["as"] == g["pts"]]
        if len(hit) == 1:
            link[g["gid"]] = hit[0]["id"]
            break
F = {g["id"]: g for g in L.football("nfl")}
rows_t, rows_b, rows_c, gains = [], [], [], []
for r in LA:
    f = F.get(link.get(r["g"]["gid"]))
    if not f:
        continue
    import statistics
    bk = {b: v for b, v in f["first"][1].items() if abs(v[0] - f["med"]) <= 1.5 and v[0] == -v[2] and -140 <= v[1] <= 125 and -140 <= v[3] <= 125}
    if len(bk) < 5:
        continue
    med = statistics.median(v[0] for v in bk.values())
    side = "away" if r["g"]["hl"] < 0 else "home"          # the dog (nflverse's home = our home after the score link? check by margin)
    if f["margin"] != r["g"]["m"]:
        side = "home" if side == "away" else "away"
    ln = med if side == "home" else -med
    if ln < 3:
        continue                                            # Tuesday's number had it a different game
    at = [L.dec(v[1] if side == "home" else v[3]) for v in bk.values() if v[0] == med]
    best = max(((v[0], L.dec(v[1])) if side == "home" else (v[2], L.dec(v[3]))) for v in bk.values())
    rows_t.append((r["season"], L.cover(f["margin"], med, side, B.american(statistics.median(at)) if at else -110)))
    rows_b.append((r["season"], L.cover(f["margin"], best[0] if side == "home" else -best[0], side, B.american(best[1]))))
    rows_c.append((r["season"], r["p"]))
    gains.append(ln - r["lay"])
o(f"   {len(rows_t)} of the cell's 2020-25 games have a Tuesday look")
o(f"   Tuesday, the market number at the median price: {L.st([p for _, p in rows_t])}   by season {L.by_season(rows_t)[2]}")
o(f"   Tuesday, the best book:                         {L.st([p for _, p in rows_b])}")
o(f"   the same games at the close:                    {L.st([p for _, p in rows_c])}")
if gains:
    o(f"   the dog's Tuesday number vs its close: {sum(gains) / len(gains):+.2f} points on average (+ = Tuesday gave more points)")
o("\ncells read here: 4 x 9 dose rows + 16 cuts + the placebo + 3 Tuesday rows = ~57 (on top of S5's 34)")
o.save()
