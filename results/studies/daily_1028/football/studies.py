"""10/28 daily run - 4 football studies (the 10/27 harness). Prices: closing moneyline from the game files (2018-26);
second check: the first FAIR early look (paid odds history 2020-25, early_football_study.fair via the daily_1023 loader,
cached - nothing re-pulled) and ATS on the same games. Train 2018-24 / holdout 2025 / now 2026. Flat 1u. Every cell
printed with its same-price base.
S1 THE DEFENSE GOT SHREDDED: allowed 40+ (college) / 35+ (NFL) points last game - bounce-back or a broken defense?
S2 THE 4TH-QUARTER COMEBACK WINNER: won its last game after trailing going into the 4th quarter - the market loves a
   comeback; does the team carry it (or is it lucky)? And the team that BLEW a 4th-quarter lead and lost.
S3 THE TURNAROUND TEAM: this season's win % 0.35+ OVER last season's (4+ games) - is the market slow to believe a
   bad team got good (dogs) / slow to sell a good team gone bad (the collapse team, 0.35+ under).
S4 THE DEFENSE ON A ROLL: allowed 10 or fewer (NFL) / 14 or fewer (college) in EACH of the last 2 games."""
import os, pickle, math, statistics
from collections import defaultdict
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1028")
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


def wp(rec):
    return None if not rec or sum(rec) < 6 else rec[0] / sum(rec)


# ---------------- S1 ALLOWED 40+ / 35+ LAST GAME ----------------
LINES.append("S1 THE DEFENSE GOT SHREDDED LAST GAME (allowed 40+ college / 35+ NFL)")
for lg, rows in LG.items():
    cut = 40 if lg == "ncaaf" else 35
    pool = [x for x in rows if x["last_pa"] is not None]
    by_bands(f"{lg} allowed {cut}+ last game", [x for x in pool if x["last_pa"] >= cut], pool)
    by_bands(f"{lg} allowed {cut}+ last game AND LOST it", [x for x in pool if x["last_pa"] >= cut and x["last_won"] is False], pool)
    by_bands(f"{lg} allowed {cut}+ in a WIN last game", [x for x in pool if x["last_pa"] >= cut and x["last_won"] is True], pool)

# ---------------- S2 4TH-QUARTER COMEBACK ----------------
LINES.append("\nS2 THE 4TH-QUARTER COMEBACK (last game: trailed after 3 quarters and won / led after 3 and lost)")
for lg, rows in LG.items():
    pool = [x for x in rows if x["q3_last"] is not None and x["last_won"] is not None]
    by_bands(f"{lg} came back in the 4th to win", [x for x in pool if x["q3_last"] < 0 and x["last_won"]], pool)
    by_bands(f"{lg} came back from 7+ down in the 4th to win", [x for x in pool if x["q3_last"] <= -7 and x["last_won"]], pool)
    by_bands(f"{lg} BLEW a 4th-quarter lead and lost", [x for x in pool if x["q3_last"] > 0 and not x["last_won"]], pool)

# ---------------- S3 THE TURNAROUND TEAM ----------------
LINES.append("\nS3 THE TURNAROUND TEAM (this season's win % vs last season's, 4+ games this season, 6+ last)")
for lg, rows in LG.items():
    pool = [x for x in rows if wp(x["ly"]) is not None and x["w"] + x["l"] >= 4]
    by_bands(f"{lg} TURNAROUND (0.35+ over last year)", [x for x in pool if x["w"] / (x["w"] + x["l"]) - wp(x["ly"]) >= 0.35], pool)
    by_bands(f"{lg} COLLAPSE (0.35+ under last year)", [x for x in pool if x["w"] / (x["w"] + x["l"]) - wp(x["ly"]) <= -0.35], pool)
    by_bands(f"{lg} turnaround 0.25+ over, opp collapse-free", [x for x in pool if x["w"] / (x["w"] + x["l"]) - wp(x["ly"]) >= 0.25
             and (wp(x["o_ly"]) is None or x["ow"] + x["ol"] < 4 or x["ow"] / (x["ow"] + x["ol"]) - wp(x["o_ly"]) > -0.25)], pool)

# ---------------- S4 DEFENSE ON A ROLL ----------------
LINES.append("\nS4 THE DEFENSE ON A ROLL (allowed 10 or fewer NFL / 14 or fewer college in each of the last 2)")
for lg, rows in LG.items():
    cut = 14 if lg == "ncaaf" else 10
    pool = [x for x in rows if len(x["pa2"]) == 2]
    by_bands(f"{lg} held foes to {cut} or fewer twice", [x for x in pool if max(x["pa2"]) <= cut], pool)
    by_bands(f"{lg} OPPONENT held foes to {cut} or fewer twice", [x for x in pool if len(x["o_pa2"]) == 2 and max(x["o_pa2"]) <= cut], pool)

print("\n".join(LINES))
print(f"\nprimary cells {len(CELLS)}; expected ~{0.05*len(CELLS):.0f} |z|>2 by chance; |z|>2 here: "
      + str(sum(1 for c in CELLS if abs(c[1][3]) > 2)))
for c in CELLS:
    a, tr, ho = c[1], c[2], c[3]
    if tr and ho and tr[0] >= 40 and tr[2] > 0.03 and ho[2] > 0 and a[3] > 1.5:
        print("SURVIVOR (train >+3%, hold >0, z>1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
    if tr and ho and tr[0] >= 40 and tr[2] < -0.05 and ho[2] < 0 and a[3] < -1.5:
        print("FADE (train <-5%, hold <0, z<-1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
