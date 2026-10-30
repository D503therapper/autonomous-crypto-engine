"""10/30 COLLEGE FOOTBALL UNIT-PLAY STUDIES (the owner, before a big weekend: "find ways to get good unit plays - 1u, 2u,
3u plays - win more money"). Four studies on the same rows as the 10/28 weeknight study (build.py - every priced college
side 2020-26: the walk-forward own read trained on the 3 seasons before each one, the closing price, the FIRST FAIR early
price E (the earliest look up after both teams' last games), the latest pre-game-day look M, the game-morning look G;
no look-ahead).

  1. FAVORITES -101..-150: which cells the 3u Lock could fire on (own read AND weighed read over the price).
  2. AGREEMENT: Elo + form + rest + last result all on one side - does agreement across factors pay more than any one?
  3. FAVORITES EARLY: the first fair number vs a later look - the favorite the money came to (hammered, for favorites).
  4. DOG SIZING: college dogs +100..+350 by own-read gap band - which band deserves 2u, which ½u.

Train = 2020-2023, held out = 2024 / 2025 / 2026 each on its own. Flat 1u. ROI, the band's own ROI (lift), z vs the
no-vig price. Every cell counted (multiple-testing: ~1 in 20 cells reaches z 2 by chance)."""
import json
import math
import os
import sys
from collections import defaultdict

ROWS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "rows_ncaaf.json")
TRAIN = {2020, 2021, 2022, 2023}
HOLDS = (2024, 2025, 2026)
CELLS = [0]


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def nv(ml, ml_opp):
    a, b = 1 / dec(ml), 1 / dec(ml_opp)
    return a / (a + b)


rows = json.load(open(ROWS))
for r in rows:
    r["dec"] = dec(r["close"])
    r["nv"] = nv(r["close"], r["close_opp"])
    r["gap"] = r["own"] - r["nv"]                      # the raw rating read over the no-vig market (points)
    r["fav"] = r["close"] < 0
    f = r["f"]
    r["ruleA"] = (r["last_margin"] or 0) > 0 and (r["opp_last_margin"] or 0) < 0 and r["elo_pts"] > 0
    r["off_loss"] = (r["last_margin"] or 0) < 0
    w = r["own"] + (0.03 if r["ruleA"] else 0) + (-0.03 if r["off_loss"] else 0)   # the engine's two college favorite
    r["w_p"] = min(r["own"] + 0.04, max(r["own"] - 0.04, w))                        # weights, capped FAV_CAP (4)
    r["mkt_w"] = r["nv"] + (w - r["own"])            # the LIVE college read (trust 0): the market + those weights
    # factor agreement (each +1 for us / -1 against / 0 flat)
    r["ag_elo"] = 1 if r["elo_pts"] > 0 else (-1 if r["elo_pts"] < 0 else 0)
    fm = f.get("form") or 0
    r["ag_form"] = 1 if fm > 0 else (-1 if fm < 0 else 0)
    rs = f.get("rest") or 0
    r["ag_rest"] = 1 if rs > 0 else (-1 if rs < 0 else 0)
    lm, olm = r["last_margin"], r["opp_last_margin"]
    r["ag_last"] = 0 if lm is None or olm is None else (1 if lm > olm else (-1 if lm < olm else 0))
    r["agree"] = sum(x > 0 for x in (r["ag_elo"], r["ag_form"], r["ag_rest"], r["ag_last"]))
    r["against"] = sum(x < 0 for x in (r["ag_elo"], r["ag_form"], r["ag_rest"], r["ag_last"]))


def stat(rs, price_key="close", opp_key="close_opp"):
    """(n, wins, roi, z) flat 1u at the row's price."""
    n = len(rs)
    if not n:
        return 0, 0, 0.0, 0.0
    won = sum(r["won"] for r in rs)
    pnl = sum((dec(r[price_key]) - 1) if r["won"] else -1 for r in rs)
    exp = sum(nv(r[price_key], r[opp_key]) for r in rs)           # expected wins at the no-vig price
    var = sum(nv(r[price_key], r[opp_key]) * (1 - nv(r[price_key], r[opp_key])) for r in rs)
    z = (won - exp) / math.sqrt(var) if var else 0.0
    return n, won, pnl / n * 100, z


def line(name, rs, band=None, pk="close", ok="close_opp"):
    CELLS[0] += 1
    out = []
    tr = [r for r in rs if r["season"] in TRAIN]
    n, w, roi, z = stat(tr, pk, ok)
    ups = sum(1 for s in TRAIN if stat([r for r in tr if r["season"] == s], pk, ok)[2] > 0)
    lift = ""
    if band is not None:
        b = stat([r for r in band if r["season"] in TRAIN], pk, ok)[2]
        lift = f" lift {roi - b:+.1f}"
    out.append(f"train {w}-{n - w} {roi:+.1f}% z {z:+.1f} ({ups} of 4 up){lift}")
    for s in HOLDS:
        hs = [r for r in rs if r["season"] == s]
        n, w, roi, z = stat(hs, pk, ok)
        out.append(f"{s} {w}-{n - w} {roi:+.1f}%" if n >= 8 else f"{s} {w}-{n - w}")
    al = stat(rs, pk, ok)
    print(f"  {name:62s} | " + " | ".join(out) + f" | all {al[1]}-{al[0] - al[1]} {al[2]:+.1f}% z {al[3]:+.1f}")


def five_checks(name, rs, min_n=100):
    """The five-checks rule: train up, every held-out season up (2026 allowed small), n 100+, z 2+ in train."""
    tr = [r for r in rs if r["season"] in TRAIN]
    n, w, roi, z = stat(tr)
    holds = [stat([r for r in rs if r["season"] == s])[2] for s in HOLDS]
    ok = roi > 0 and z >= 2 and n >= min_n and all(h > 0 for h in holds[:2])
    print(f"  FIVE CHECKS {name}: train {roi:+.1f}% z {z:+.1f} n {n}; held {holds[0]:+.1f} / {holds[1]:+.1f} / {holds[2]:+.1f} -> "
          + ("PASS" if ok else "no"))
    return ok


print("rows", len(rows), "games", len({r['gid'] for r in rows}), "seasons",
      {s: sum(1 for r in rows if r["season"] == s) for s in sorted({r["season"] for r in rows})})

# =====================================================================================================================
print("\n=== STUDY 1 - COLLEGE FAVORITES -101..-150 at the close: where could a Lock fire? ===")
favs = [r for r in rows if -150 <= r["close"] <= -101]
line("every favorite -101..-150", favs)
line("  -101..-119 (the plan's skip band)", [r for r in favs if r["close"] >= -119], favs)
line("  -120..-150", [r for r in favs if r["close"] <= -120], favs)
f20 = [r for r in favs if r["close"] <= -120]
line("own read (ratings) over the no-vig", [r for r in favs if r["gap"] > 0], favs)
line("own read beats the PRICE (own x dec > 1)", [r for r in favs if r["own"] * r["dec"] > 1], favs)
line("weighed read beats the price", [r for r in favs if r["w_p"] * r["dec"] > 1], favs)
line("BOTH own and weighed beat the price (the 3u cell)", [r for r in favs if r["w_p"] * r["dec"] > 1 and r["own"] * r["dec"] > 1], favs)
line("  ... at -120..-150", [r for r in f20 if r["w_p"] * r["dec"] > 1 and r["own"] * r["dec"] > 1], favs)
line("weighed over, own under (the 2u cell)", [r for r in favs if r["w_p"] * r["dec"] > 1 and r["own"] * r["dec"] <= 1], favs)
line("neither (the 1u / no-Lock cell)", [r for r in favs if r["w_p"] * r["dec"] <= 1], favs)
line("LIVE read (market + weights) beats the price", [r for r in favs if r["mkt_w"] * r["dec"] > 1], favs)
print(" -- the own-read gap over the no-vig, in bands")
for lo, hi in ((-99, -6), (-6, -3), (-3, 0), (0, 3), (3, 6), (6, 10), (10, 99)):
    line(f"  gap {lo:+d}..{hi:+d}", [r for r in favs if lo <= r["gap"] * 100 < hi], favs)
print(" -- the two built weights, and Elo")
line("rule A (off a win, opp off a loss, Elo-backed)", [r for r in favs if r["ruleA"]], favs)
line("off a loss (the -3 weight)", [r for r in favs if r["off_loss"]], favs)
line("Elo-backed (ratings have the favorite better)", [r for r in favs if r["elo_pts"] > 0], favs)
line("Elo against (ratings have the DOG better)", [r for r in favs if r["elo_pts"] < 0], favs)
line("Elo-backed by 7+ points", [r for r in favs if r["elo_pts"] >= 7], favs)
line("Elo-backed by 7+ AND gap 3+", [r for r in favs if r["elo_pts"] >= 7 and r["gap"] >= 0.03], favs)
print(" -- home / road / month")
line("home favorite", [r for r in favs if r["side"] == "home" and not r["neutral"]], favs)
line("road favorite", [r for r in favs if r["side"] == "away" and not r["neutral"]], favs)
line("road favorite, Elo-backed, gap 3+", [r for r in favs if r["side"] == "away" and r["elo_pts"] > 0 and r["gap"] >= 0.03], favs)
line("home favorite, Elo-backed, gap 3+", [r for r in favs if r["side"] == "home" and r["elo_pts"] > 0 and r["gap"] >= 0.03], favs)
line("September", [r for r in favs if r["month"] == 9], favs)
line("October", [r for r in favs if r["month"] == 10], favs)
line("November+", [r for r in favs if r["month"] >= 11], favs)
line("Nov+, Elo-backed, gap 3+", [r for r in favs if r["month"] >= 11 and r["elo_pts"] > 0 and r["gap"] >= 0.03], favs)
line("favorite off a bye", [r for r in favs if (r["rest"] or 0) >= 12], favs)
line("favorite rested more than the dog (2+ days)", [r for r in favs if (r["rest"] or 0) - (r["orest"] or 0) >= 2], favs)
five_checks("own+weighed over, -120..-150", [r for r in f20 if r["w_p"] * r["dec"] > 1 and r["own"] * r["dec"] > 1])
five_checks("Elo-backed 7+ and gap 3+", [r for r in favs if r["elo_pts"] >= 7 and r["gap"] >= 0.03])
five_checks("rule A", [r for r in favs if r["ruleA"]])

# =====================================================================================================================
print("\n=== STUDY 2 - FACTOR AGREEMENT (Elo / form / rest / last result on one side) ===")
for label, pool in (("favorites -101..-150", favs),
                    ("favorites -151..-250", [r for r in rows if -250 <= r["close"] <= -151]),
                    ("dogs +100..+350", [r for r in rows if 100 <= r["close"] <= 350])):
    print(f" -- {label}")
    for k in range(5):
        line(f"  {k} of 4 factors for us", [r for r in pool if r["agree"] == k], pool)
    line("  all 4 for us, none against", [r for r in pool if r["agree"] == 4], pool)
    line("  3+ for us, 0 against", [r for r in pool if r["agree"] >= 3 and r["against"] == 0], pool)
    line("  Elo + form + rest all for us", [r for r in pool if r["ag_elo"] > 0 and r["ag_form"] > 0 and r["ag_rest"] > 0], pool)
    line("  Elo + form for us", [r for r in pool if r["ag_elo"] > 0 and r["ag_form"] > 0], pool)
    line("  Elo for, form against", [r for r in pool if r["ag_elo"] > 0 and r["ag_form"] < 0], pool)
    line("  Elo against, form for", [r for r in pool if r["ag_elo"] < 0 and r["ag_form"] > 0], pool)
    line("  3+ against us", [r for r in pool if r["against"] >= 3], pool)
    line("  3+ for us AND own read over the no-vig", [r for r in pool if r["agree"] >= 3 and r["gap"] > 0], pool)
    line("  3+ for us AND gap 3+", [r for r in pool if r["agree"] >= 3 and r["gap"] >= 0.03], pool)
five_checks("favorites 3+ for, 0 against", [r for r in favs if r["agree"] >= 3 and r["against"] == 0])
five_checks("dogs 3+ for us", [r for r in rows if 100 <= r["close"] <= 350 and r["agree"] >= 3])

# =====================================================================================================================
print("\n=== STUDY 3 - COLLEGE FAVORITES AT THE FIRST FAIR NUMBER vs a later look (the money came to the favorite) ===")
E, M, G = "first look of the week", "last look before game day", "game morning"
def pr(r, k):
    return r["w"].get(k)
early = [r for r in rows if pr(r, E) and pr(r, M)]
print("rows with both the first fair look and a later pre-game-day look:", len(early))
# the favorite at the LATER look M, bettable at M's price; the move E->M measured in no-vig points toward this side
for r in early:
    r["mv"] = (pr(r, M)["mkt"] - pr(r, E)["mkt"]) * 100
    r["mvc"] = (r["nv"] - pr(r, E)["mkt"]) * 100           # first look -> the close (diagnostic, not bettable)
favM = [r for r in early if -150 <= pr(r, M)["price"] <= -101]
def mline(name, rs, band=None):
    """ROI at the M price."""
    # (the no-vig at M is stored per side as mkt -> the expectation comes from it)
    CELLS[0] += 1
    out = []
    def st(xs):
        n = len(xs)
        if not n:
            return 0, 0, 0.0, 0.0
        won = sum(x["won"] for x in xs)
        pnl = sum((dec(pr(x, M)["price"]) - 1) if x["won"] else -1 for x in xs)
        exp = sum(pr(x, M)["mkt"] for x in xs)
        var = sum(pr(x, M)["mkt"] * (1 - pr(x, M)["mkt"]) for x in xs)
        return n, won, pnl / n * 100, (won - exp) / math.sqrt(var) if var else 0.0
    tr = [r for r in rs if r["season"] in TRAIN]
    n, w, roi, z = st(tr)
    ups = sum(1 for s in TRAIN if st([r for r in tr if r["season"] == s])[2] > 0)
    lift = f" lift {roi - st([r for r in band if r['season'] in TRAIN])[2]:+.1f}" if band else ""
    out.append(f"train {w}-{n - w} {roi:+.1f}% z {z:+.1f} ({ups} of 4 up){lift}")
    for s in HOLDS:
        hs = [r for r in rs if r["season"] == s]
        n, w, roi, z = st(hs)
        out.append(f"{s} {w}-{n - w} {roi:+.1f}%" if n >= 8 else f"{s} {w}-{n - w}")
    al = st(rs)
    print(f"  {name:62s} | " + " | ".join(out) + f" | all {al[1]}-{al[0] - al[1]} {al[2]:+.1f}% z {al[3]:+.1f}")
mline("every favorite -101..-150 at the later look (M price)", favM)
mline("  money came TO the favorite 4+ pts (hammered favorite)", [r for r in favM if r["mv"] >= 4], favM)
mline("  money came TO the favorite 2..4 pts", [r for r in favM if 2 <= r["mv"] < 4], favM)
mline("  flat (within 2)", [r for r in favM if -2 < r["mv"] < 2], favM)
mline("  money went AWAY 2..4 pts", [r for r in favM if -4 < r["mv"] <= -2], favM)
mline("  money went AWAY 4+ pts (the faded favorite)", [r for r in favM if r["mv"] <= -4], favM)
mline("  hammered 4+ AND own read over the no-vig at M", [r for r in favM if r["mv"] >= 4 and r["own"] > pr(r, M)["mkt"]], favM)
mline("  hammered 4+ AND Elo-backed", [r for r in favM if r["mv"] >= 4 and r["elo_pts"] > 0], favM)
mline("  hammered 4+, opened at -101..-120 (opened cheap)", [r for r in favM if r["mv"] >= 4 and -120 <= pr(r, E)["price"] <= -101], favM)
mline("  hammered 4+, was a DOG at the first look", [r for r in favM if r["mv"] >= 4 and pr(r, E)["price"] >= 100], favM)
mline("  faded 4+ AND own read over the no-vig at M", [r for r in favM if r["mv"] <= -4 and r["own"] > pr(r, M)["mkt"]], favM)
print(" -- the same at the CLOSE (first look -> close; diagnostic - the close isn't bettable early)")
line("fav -101..-150 at close, money came to it 4+ since the first look", [r for r in early if -150 <= r["close"] <= -101 and r["mvc"] >= 4], favs)
line("fav -101..-150 at close, money went away 4+ since the first look", [r for r in early if -150 <= r["close"] <= -101 and r["mvc"] <= -4], favs)
line("fav -101..-150 at close, flat since the first look", [r for r in early if -150 <= r["close"] <= -101 and -2 < r["mvc"] < 2], favs)
print(" -- bigger favorites at the later look")
favM2 = [r for r in early if -250 <= pr(r, M)["price"] <= -151]
mline("favorites -151..-250 at M", favM2)
mline("  hammered 4+", [r for r in favM2 if r["mv"] >= 4], favM2)
mline("  faded 4+", [r for r in favM2 if r["mv"] <= -4], favM2)
print(" -- the dog across from a hammered favorite (the price got LONGER): the fade of the fade")
dogM = [r for r in early if 100 <= pr(r, M)["price"] <= 350]
mline("dogs +100..+350 at M", dogM)
mline("  the dog the money left 4+ (opp hammered)", [r for r in dogM if r["mv"] <= -4], dogM)
mline("  the dog the money came to 4+ (the built hammered spot)", [r for r in dogM if r["mv"] >= 4], dogM)
mline("  hammered dog AND own read over the no-vig at M", [r for r in dogM if r["mv"] >= 4 and r["own"] > pr(r, M)["mkt"]], dogM)

# =====================================================================================================================
print("\n=== STUDY 4 - COLLEGE DOG SIZING by the own-read gap band (dogs +100..+350 at the close) ===")
dogs = [r for r in rows if 100 <= r["close"] <= 350]
line("every dog +100..+350", dogs)
for lo, hi in ((100, 150), (151, 250), (251, 350)):
    line(f"  +{lo}..+{hi}", [r for r in dogs if lo <= r["close"] <= hi], dogs)
print(" -- by the raw own-read gap over the no-vig")
bands = ((-99, 0), (0, 5), (5, 10), (10, 15), (15, 20), (20, 99))
for lo, hi in bands:
    line(f"  gap {lo:+d}..{hi:+d}", [r for r in dogs if lo <= r["gap"] * 100 < hi], dogs)
print(" -- Elo-backed (the ratings have the dog better) by gap band")
for lo, hi in bands[1:]:
    line(f"  Elo-backed, gap {lo:+d}..{hi:+d}", [r for r in dogs if r["elo_pts"] > 0 and lo <= r["gap"] * 100 < hi], dogs)
line("  Elo-backed, gap 15+ (the 🔍 play)", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15], dogs)
line("  Elo-backed 15+ at +100..+150", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["close"] <= 150], dogs)
line("  Elo-backed 15+ at +151..+250", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and 151 <= r["close"] <= 250], dogs)
line("  Elo-backed 15+ at +251..+350", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["close"] >= 251], dogs)
line("  Elo-backed 15+, 3+ factors for us", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["agree"] >= 3], dogs)
line("  Elo-backed 15+, home dog", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["side"] == "home" and not r["neutral"]], dogs)
line("  Elo-backed 15+, road dog", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["side"] == "away" and not r["neutral"]], dogs)
line("  Elo-backed 15+, favorite off a loss", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and (r["opp_last_margin"] or 0) < 0], dogs)
line("  Elo-backed 15+, favorite off a win", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and (r["opp_last_margin"] or 0) > 0], dogs)
line("  Elo-backed 15+, October+", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["month"] >= 10], dogs)
line("  Elo-backed 15+, September", [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15 and r["month"] == 9], dogs)
line("  Elo-backed 15+, Elo by 7+ points", [r for r in dogs if r["elo_pts"] >= 7 and r["gap"] >= 0.15], dogs)
line("  Elo-backed 15+, Elo by under 7", [r for r in dogs if 0 < r["elo_pts"] < 7 and r["gap"] >= 0.15], dogs)
print(" -- the weights-only gap (Elo has the FAVORITE better, the read still over): the 10/17 block")
line("  Elo against, gap 10+", [r for r in dogs if r["elo_pts"] < 0 and r["gap"] >= 0.10], dogs)
print(" -- sizing sims: units won at the plan's sizes on the Elo-backed 15+ cell")
cell = [r for r in dogs if r["elo_pts"] > 0 and r["gap"] >= 0.15]
def units(rs, size):
    return sum(size(r) * ((r["dec"] - 1) if r["won"] else -1) for r in rs)
for nm, sz in (("flat 1u", lambda r: 1.0), ("2u all", lambda r: 2.0),
               ("2u at +100..+150, 1u longer", lambda r: 2.0 if r["close"] <= 150 else 1.0),
               ("1u at +100..+150, 2u longer", lambda r: 1.0 if r["close"] <= 150 else 2.0),
               ("2u when gap 20+, else 1u", lambda r: 2.0 if r["gap"] >= 0.20 else 1.0),
               ("2u when Elo 7+, else 1u", lambda r: 2.0 if r["elo_pts"] >= 7 else 1.0),
               ("½u Sept, 1u after", lambda r: 0.5 if r["month"] == 9 else 1.0)):
    tr = [r for r in cell if r["season"] in TRAIN]
    print(f"  {nm:34s} train {units(tr, sz):+.1f}u on {sum(sz(r) for r in tr):.0f}u | "
          + " | ".join(f"{s} {units([r for r in cell if r['season'] == s], sz):+.1f}u" for s in HOLDS))
five_checks("Elo-backed gap 15+ dogs", cell)
five_checks("Elo-backed gap 15+ dogs, +100..+150", [r for r in cell if r["close"] <= 150])
five_checks("Elo-backed 7+ and gap 15+", [r for r in cell if r["elo_pts"] >= 7])
print("\ncells looked at:", CELLS[0], "(expect ~", round(CELLS[0] / 20, 1), "chance hits at z 2)")
