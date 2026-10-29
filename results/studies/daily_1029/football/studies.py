"""10/29 daily run - 5 football studies (the 10/28 harness). Prices: closing moneyline from the game files (2018-26);
second check: the first FAIR early look (paid odds history 2020-25, the daily_1023 loader's cache - nothing re-pulled)
and ATS on the same games. Train 2018-24 / holdout 2025 / now 2026. Flat 1u. Every cell printed with its same-price base.
S1 THE BOOK'S FIRST-HALF SHARE: the 1st-half spread as a share of the full-game spread - a small share = the book thinks
   the favorite wins it late (the dog is close at the half); a big share = a front-runner. Does the shape carry value?
S2 THE FIRST-HALF FLIP: the full-game dog that is the 1st-half favorite or pick'em (the book thinks it starts better).
S3 THE DOME TEAM IN THE COLD: a team that plays home games indoors, outdoors at 40F or colder (and the cold home team).
S4 THE LAST GAME'S TOTAL MISS: the side's last game went way OVER its closing total (a shootout) or way UNDER (a rock
   fight) - does the market overreact to the scoreboard?
S5 THE BEATEN-DOWN DOG: a dog of +200 or longer in each of its last 2 games, a dog again (the market tired of it); and
   the mirror - a team favored in every game this season (3+), a dog for the first time."""
import os, pickle, math, statistics
from collections import defaultdict
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1029")
S = pickle.load(open(os.path.join(CACHE, "fb_sides.pkl"), "rb"))
try:
    EARLY = pickle.load(open(os.path.join(CACHE, "fb_early.pkl"), "rb"))
except Exception:
    EARLY = {}
CELLS, LINES = [], []


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def prof(x):
    return (dec(x["ml"]) - 1) if x["won"] else -1.0


def eprof(x):
    e = EARLY.get(x["gid"])
    if not e:
        return None
    d = e[0] if x["side"] == "home" else e[1]
    return (d - 1) if x["won"] else -1.0


def atsp(x):
    if x["ats"] is None or x["ats"] == 0:
        return None
    return 0.9091 if x["ats"] > 0 else -1.0


def st(ps):
    if not ps:
        return None
    n = len(ps); m = sum(ps) / n
    sdv = statistics.pstdev(ps) if n > 1 else 1
    return n, sum(1 for p in ps if p > 0) / n, m, (m / (sdv / math.sqrt(n)) if sdv else 0)


def f(r):
    return "-" if not r else f"{r[0]}/{r[2]:+.1%}"


def cell(name, rows, base=None, primary=True):
    rows = [x for x in rows if x["season"] >= 2018 and x["stype"] == "2"]
    a = st([prof(x) for x in rows])
    if not a:
        LINES.append(f"  {name:62s} -"); return
    by = defaultdict(list)
    for x in rows:
        by[x["season"]].append(prof(x))
    seas = {k: (len(v), round(100 * sum(v) / len(v))) for k, v in sorted(by.items())}
    tr = st([prof(x) for x in rows if x["season"] <= 2024])
    ho = st([prof(x) for x in rows if x["season"] == 2025])
    cu = st([prof(x) for x in rows if x["season"] == 2026])
    l3 = st([prof(x) for x in rows if x["season"] >= 2023])
    ep = [p for p in (eprof(x) for x in rows) if p is not None]
    at = [p for p in (atsp(x) for x in rows) if p is not None]
    up = sum(1 for k, v in by.items() if k <= 2024 and sum(v) > 0)
    nt = sum(1 for k in by if k <= 2024)
    bl = ""
    if base is not None:
        b = st([prof(x) for x in base if x["season"] >= 2018 and x["stype"] == "2"])
        bl = f" | base {f(b)}"
    LINES.append(f"  {name:62s} n {a[0]:4d} win {a[1]:.1%} ROI {a[2]:+.1%} z {a[3]:+.1f} | train {f(tr)} up {up}/{nt}"
                 f" | 2023+ {f(l3)} | hold25 {f(ho)} | 2026 {f(cu)} | early {f(st(ep))} | ATS {f(st(at))}{bl}")
    LINES.append(f"      seasons {seas}")
    if primary:
        CELLS.append((name, a, tr, ho))


def band(x, lo, hi):
    return lo <= x["ml"] <= hi


BANDS = (("dog +100..+350", 100, 350), ("fav -101..-150", -150, -101), ("fav -151..-400", -400, -151))
LG = {"ncaaf": [x for x in S if x["league"] == "ncaaf"], "nfl": [x for x in S if x["league"] == "nfl"]}


def by_bands(label, rows, pool):
    for bn, lo, hi in BANDS:
        cell(f"{label} - {bn}", [x for x in rows if band(x, lo, hi)], [x for x in pool if band(x, lo, hi)])



# ---------------- S1 THE BOOK'S FIRST-HALF SHARE ----------------
def share(x):
    if x["h1sp"] is None or x["pts"] is None or abs(x["pts"]) < 2.5:
        return None
    return x["h1sp"] / x["pts"]


LINES.append("S1 THE BOOK'S FIRST-HALF SHARE (1st-half spread / full spread, full spread 2.5+)")
for lg, rows in LG.items():
    pool = [x for x in rows if share(x) is not None]
    for nm, lo, hi in (("small share under 0.45 (late-game favorite)", -9, 0.45), ("middle 0.45-0.60", 0.45, 0.60),
                       ("big share 0.60+ (front-runner favorite)", 0.60, 9)):
        by_bands(f"{lg} {nm}", [x for x in pool if lo <= share(x) < hi], pool)

# ---------------- S2 THE FIRST-HALF FLIP ----------------
LINES.append("\nS2 THE FIRST-HALF FLIP (a full-game dog that is the 1st-half favorite or pick'em)")
for lg, rows in LG.items():
    pool = [x for x in rows if x["h1sp"] is not None and band(x, 100, 350)]
    cell(f"{lg} dog, 1st-half spread 0 or better for it", [x for x in pool if x["h1sp"] <= 0], pool)
    cell(f"{lg} dog, 1st-half moneyline -100 or shorter", [x for x in pool if x["h1ml"] is not None and -500 < x["h1ml"] <= -100], pool)
    cell(f"{lg} dog +100..+150, 1st-half spread 0 or better", [x for x in pool if x["h1sp"] <= 0 and x["ml"] <= 150],
         [x for x in pool if x["ml"] <= 150])

# ---------------- S3 THE DOME TEAM IN THE COLD ----------------
LINES.append("\nS3 THE DOME TEAM IN THE COLD (home games 75%+ indoors; tonight outdoors at the temp)")
for lg, rows in LG.items():
    pool = [x for x in rows if not x["indoor"] and x["temp"] is not None and not x["home"]]
    for cut in (40, 32):
        by_bands(f"{lg} dome team on the road, outdoors {cut}F or colder", [x for x in pool if x["dome_team"] and x["temp"] <= cut],
                 [x for x in pool if x["temp"] <= cut])
    hp = [x for x in rows if x["home"] and not x["indoor"] and x["temp"] is not None]
    oppdome = {x["gid"] for x in pool if x["dome_team"]}
    by_bands(f"{lg} cold home team (40F or colder) vs a dome team", [x for x in hp if x["temp"] <= 40 and x["gid"] in oppdome],
             [x for x in hp if x["temp"] <= 40])

# ---------------- S4 THE LAST GAME'S TOTAL MISS ----------------
LINES.append("\nS4 THE LAST GAME'S TOTAL MISS (points in its last game minus that game's closing total)")
for lg, rows in LG.items():
    hi, lo = (21, -17) if lg == "ncaaf" else (17, -14)
    pool = [x for x in rows if x["tmiss"] is not None]
    by_bands(f"{lg} last game went {hi}+ OVER (a shootout)", [x for x in pool if x["tmiss"] >= hi], pool)
    by_bands(f"{lg} last game went {-lo}+ UNDER (a rock fight)", [x for x in pool if x["tmiss"] <= lo], pool)
    by_bands(f"{lg} BOTH teams' last games went {hi}+ over", [x for x in pool if x["tmiss"] >= hi and (x["o_tmiss"] or -99) >= hi], pool)

# ---------------- S5 THE BEATEN-DOWN DOG ----------------
LINES.append("\nS5 THE BEATEN-DOWN DOG / THE FIRST-TIME DOG")
for lg, rows in LG.items():
    pool = [x for x in rows if band(x, 100, 350) and len(x["prev_ml"]) >= 2]
    cell(f"{lg} dog, +200 or longer in each of its last 2", [x for x in pool if min(x["prev_ml"][-2:]) >= 200], pool)
    cell(f"{lg} dog, a dog in each of its last 4 (any price)", [x for x in pool if len(x["prev_ml"]) >= 4 and min(x["prev_ml"][-4:]) > 0], pool)
    p3 = [x for x in rows if band(x, 100, 350) and len(x["prev_ml"]) >= 3]
    cell(f"{lg} FIRST-TIME DOG (favored in every game so far, 3+)", [x for x in p3 if max(x["prev_ml"]) < 0], p3)
    f3 = [x for x in rows if band(x, -150, -101) and len(x["prev_ml"]) >= 3]
    cell(f"{lg} fav -101..-150, a dog in every game so far (first-time fav)", [x for x in f3 if min(x["prev_ml"]) > 0], f3)

print("\n".join(LINES))
print(f"\nprimary cells {len(CELLS)}; expected ~{0.05*len(CELLS):.0f} |z|>2 by chance; |z|>2 here: "
      + str(sum(1 for c in CELLS if abs(c[1][3]) > 2)))
for c in CELLS:
    a, tr, ho = c[1], c[2], c[3]
    if tr and ho and tr[0] >= 40 and tr[2] > 0.03 and ho[2] > 0 and a[3] > 1.5:
        print("SURVIVOR (train >+3%, hold >0, z>1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
    if tr and ho and tr[0] >= 40 and tr[2] < -0.05 and ho[2] < 0 and a[3] < -1.5:
        print("FADE (train <-5%, hold <0, z<-1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
