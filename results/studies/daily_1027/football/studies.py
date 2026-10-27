"""10/27 daily run - 5 football studies. Prices: closing moneyline from the game files (2018-26) = what the 8 AM board /
game day can take; second check: the first FAIR early look (paid odds history 2020-25, early_football_study.fair via
the daily_1023 loader). Train 2018-24 / holdout 2025 / now 2026. Flat 1u. Every cell printed with its same-price base.
S1 PYTHAGOREAN LUCK: this season's win % minus its points-for / points-against expectation (exponent 2.37), 4+ games -
   the LUCKY team (record 0.20+ over its points) and the UNLUCKY one (0.20+ under), both leagues, every price band.
S2 THE SCORING TREND: points scored ROSE in each of the last 3 games (and the last game 7+ over its season average) /
   FELL in each of the last 3 - the hot / cold offense the market may chase.
S3 THE IN-SEASON REMATCH: the second meeting of the same two teams in one season (NFL division / college title games) -
   the team that LOST the first meeting (by 14+ / by any), and the team that won it as a dog.
S4 THE TOTAL'S SIZE: the closing total 7+ (NFL) / 10+ (college) under or over the season's median so far - do dogs /
   favorites do better in low / high games (fewer possessions = more variance for the dog).
S5 SLOW STARTERS: trailed at halftime in each of the last 2 games (win or lose) / led at halftime in both - next game."""
import os, pickle, math, statistics
from collections import defaultdict
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1027")
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



PY = 2.37
def pyth(x):
    if x["gp"] < 4 or x["pf_s"] + x["pa_s"] == 0:
        return None
    e = x["pf_s"] ** PY / (x["pf_s"] ** PY + x["pa_s"] ** PY)
    return x["w"] / max(1, x["w"] + x["l"]) - e

# ---------------- S1 PYTHAGOREAN LUCK ----------------
LINES.append("S1 PYTHAGOREAN LUCK (record vs points this season, 4+ games)")
for lg, rows in LG.items():
    pool = [x for x in rows if pyth(x) is not None]
    by_bands(f"{lg} LUCKY (record 0.20+ over its points)", [x for x in pool if pyth(x) >= 0.20], pool)
    by_bands(f"{lg} UNLUCKY (record 0.20+ under its points)", [x for x in pool if pyth(x) <= -0.20], pool)

# ---------------- S2 SCORING TREND ----------------
LINES.append("\nS2 THE SCORING TREND (last 3 games)")
for lg, rows in LG.items():
    pool = [x for x in rows if len(x["pts3"]) == 3 and x["gp"] >= 4]
    up = [x for x in pool if x["pts3"][0] < x["pts3"][1] < x["pts3"][2] and x["pts3"][2] >= x["pf_s"] / x["gp"] + 7]
    dn = [x for x in pool if x["pts3"][0] > x["pts3"][1] > x["pts3"][2]]
    by_bands(f"{lg} offense ROSE 3 straight (+7 over avg)", up, pool)
    by_bands(f"{lg} offense FELL 3 straight", dn, pool)

# ---------------- S3 IN-SEASON REMATCH ----------------
LINES.append("\nS3 THE IN-SEASON REMATCH (second meeting, same season)")
for lg, rows in LG.items():
    pool = [x for x in rows if x["prev_meet"] is not None]
    allp = rows
    LINES.append(f" -- {lg} rematches: {len(pool)} sides")
    by_bands(f"{lg} LOST the first meeting", [x for x in pool if x["prev_meet"] < 0], allp)
    by_bands(f"{lg} LOST the first meeting by 14+", [x for x in pool if x["prev_meet"] <= -14], allp)
    by_bands(f"{lg} WON the first meeting", [x for x in pool if x["prev_meet"] > 0], allp)

# ---------------- S4 THE TOTAL'S SIZE ----------------
LINES.append("\nS4 THE TOTAL'S SIZE (closing total vs the season's median so far)")
for lg, rows in LG.items():
    cut = 7 if lg == "nfl" else 10
    pool = [x for x in rows if x["total"] is not None and x["total_med"] is not None]
    by_bands(f"{lg} LOW total ({cut}+ under the median)", [x for x in pool if x["total"] <= x["total_med"] - cut], pool)
    by_bands(f"{lg} HIGH total ({cut}+ over the median)", [x for x in pool if x["total"] >= x["total_med"] + cut], pool)

# ---------------- S5 SLOW STARTERS ----------------
LINES.append("\nS5 SLOW STARTERS (halftime score of the last 2 games)")
for lg, rows in LG.items():
    pool = [x for x in rows if len(x["half2"]) == 2 and None not in x["half2"]]
    by_bands(f"{lg} TRAILED at the half in both", [x for x in pool if x["half2"][0] < 0 and x["half2"][1] < 0], pool)
    by_bands(f"{lg} LED at the half in both", [x for x in pool if x["half2"][0] > 0 and x["half2"][1] > 0], pool)

print("\n".join(LINES))
print(f"\nprimary cells {len(CELLS)}; expected ~{0.05*len(CELLS):.0f} |z|>2 by chance; |z|>2 here: "
      + str(sum(1 for c in CELLS if abs(c[1][3]) > 2)))
for c in CELLS:
    a, tr, ho = c[1], c[2], c[3]
    if tr and ho and tr[0] >= 40 and tr[2] > 0.03 and ho[2] > 0 and a[3] > 1.5:
        print("SURVIVOR (train >+3%, hold >0, z>1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
    if tr and ho and tr[0] >= 40 and tr[2] < -0.05 and ho[2] < 0 and a[3] < -1.5:
        print("FADE (train <-5%, hold <0, z<-1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
