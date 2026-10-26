"""10/26 daily run - 5 football studies. Prices: closing moneyline from the game files (2018-26) = what the 8 AM board /
game day can take; second check: the first FAIR early look (paid odds history 2020-25, early_football_study.fair via
the daily_1023 loader). Train 2018-24 / holdout 2025 / now 2026. Flat 1u. Every cell printed with its same-price base.
S1 LOOK-AHEAD: a favorite whose NEXT game (the public schedule) is against a much stronger opponent than today's
   (next opponent's walk-forward Elo 100+ / 150+ over today's) - fade the favorite / back the dog. College main, NFL check.
S2 SENIOR DAY: the home team's last regular-season home game (college, November+); NFL last home game as the check.
S3 THE FIRST WIN AFTER AN 0-3+ START: the game after a team finally wins (both leagues).
S4 AFTER A 21+ POINT HOME LOSS: the team embarrassed at home, next game (both leagues).
S5 AFTER A SHOOTOUT: both teams scored 35+ (college) / 30+ (NFL) last game - the shootout loser / winner next game."""
import os, pickle, math, statistics
from collections import defaultdict
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1026")
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


# ---------------- S1 LOOK-AHEAD ----------------
LINES.append("S1 LOOK-AHEAD - the favorite's NEXT opponent much stronger than today's (walk-forward Elo as of today)")
for lg, rows in LG.items():
    ok = [x for x in rows if x["n_opp_elo"] is not None and x["w"] + x["l"] >= 2]
    for gap in (100, 150):
        la = [x for x in ok if x["n_opp_elo"] - x["o_elo"] >= gap and x["n_opp_elo"] >= x["elo"] - 50]
        LINES.append(f" -- {lg} next opponent {gap}+ Elo over today's (and about as good as us or better)")
        cell(f"{lg} LA{gap} fav -101..-150 (the favorite looking ahead)", [x for x in la if band(x, -150, -101)],
             [x for x in ok if band(x, -150, -101)])
        cell(f"{lg} LA{gap} fav -151..-400", [x for x in la if band(x, -400, -151)], [x for x in ok if band(x, -400, -151)])
        cell(f"{lg} LA{gap} fav -151..-400 at HOME", [x for x in la if band(x, -400, -151) and x["home"]],
             [x for x in ok if band(x, -400, -151) and x["home"]])
    # the dog facing a look-ahead favorite (the mirror side): the opponent's next game
    idx = {(x["gid"], x["side"]): x for x in ok}
    mirror = []
    for x in rows:
        o = idx.get((x["gid"], "away" if x["side"] == "home" else "home"))
        if o and o["n_opp_elo"] - o["o_elo"] >= 150 and o["n_opp_elo"] >= o["elo"] - 50 and band(x, 100, 350):
            mirror.append(x)
    cell(f"{lg} dog +100..+350 facing a LA150 favorite", mirror, [x for x in rows if band(x, 100, 350) and x["w"] + x["l"] >= 2])

# ---------------- S2 SENIOR DAY ----------------
LINES.append("\nS2 SENIOR DAY - the home team's last regular-season home game")
for lg, rows in LG.items():
    late = [x for x in rows if x["home"] and (x["month"] >= 11 if lg == "ncaaf" else x["month"] in (12, 1))]
    sen = [x for x in late if x["senior"]]
    by_bands(f"{lg} last home game ({'Nov+' if lg == 'ncaaf' else 'Dec/Jan'})", sen, late)
    if lg == "ncaaf":
        cell("ncaaf last home game, home team with a losing record - dog", [x for x in sen if x["w"] < x["l"] and band(x, 100, 350)],
             [x for x in late if x["w"] < x["l"] and band(x, 100, 350)])
        cell("ncaaf last home game, home team bowl-bubble (5 wins) - any price", [x for x in sen if x["w"] == 5 and band(x, -400, 350)],
             [x for x in late if x["w"] == 5 and band(x, -400, 350)])

# ---------------- S3 FIRST WIN AFTER 0-3+ ----------------
LINES.append("\nS3 THE GAME AFTER THE FIRST WIN, after an 0-3+ start")
for lg, rows in LG.items():
    fw = [x for x in rows if x["last_won"] is True and x["last_rec"] and x["last_rec"][0] == 0 and x["last_rec"][1] >= 3]
    by_bands(f"{lg} first win after 0-3+", fw, [x for x in rows if x["w"] + x["l"] >= 4])
    cell(f"{lg} first win after 0-3+ - the dog on the ROAD", [x for x in fw if band(x, 100, 350) and not x["home"] and not x["neutral"]],
         [x for x in rows if band(x, 100, 350) and not x["home"] and not x["neutral"] and x["w"] + x["l"] >= 4])

# ---------------- S4 AFTER A 21+ HOME LOSS ----------------
LINES.append("\nS4 THE GAME AFTER A 21+ POINT HOME LOSS")
for lg, rows in LG.items():
    hl = [x for x in rows if x["last_home"] is True and x["last_margin"] is not None and x["last_margin"] <= -21]
    pool = [x for x in rows if x["last_margin"] is not None]
    by_bands(f"{lg} after a 21+ home loss", hl, pool)
    cell(f"{lg} after a 21+ home loss - dog on the road again", [x for x in hl if band(x, 100, 350) and not x["home"]],
         [x for x in pool if band(x, 100, 350) and not x["home"]])
    opp = [x for x in rows if x["o_last_home"] is True and x["o_last_margin"] is not None and x["o_last_margin"] <= -21]
    cell(f"{lg} fav -101..-400 FACING a team off a 21+ home loss", [x for x in opp if band(x, -400, -101)],
         [x for x in pool if band(x, -400, -101)])

# ---------------- S5 AFTER A SHOOTOUT ----------------
LINES.append("\nS5 THE GAME AFTER A SHOOTOUT (both teams 35+ college / 30+ NFL)")
for lg, rows in LG.items():
    cut = 35 if lg == "ncaaf" else 30
    so = [x for x in rows if x["last_pf"] is not None and x["last_pf"] >= cut and x["last_pa"] >= cut]
    pool = [x for x in rows if x["last_pf"] is not None]
    by_bands(f"{lg} shootout LOSER", [x for x in so if x["last_won"] is False], pool)
    by_bands(f"{lg} shootout WINNER", [x for x in so if x["last_won"] is True], pool)

print("\n".join(LINES))
print(f"\nprimary cells {len(CELLS)}; expected ~{0.05*len(CELLS):.0f} |z|>2 by chance; |z|>2 here: "
      + str(sum(1 for c in CELLS if abs(c[1][3]) > 2)))
for c in CELLS:
    a, tr, ho = c[1], c[2], c[3]
    if tr and ho and tr[0] >= 40 and tr[2] > 0.03 and ho[2] > 0 and a[3] > 1.5:
        print("SURVIVOR (train >+3%, hold >0, z>1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
    if tr and ho and tr[0] >= 40 and tr[2] < -0.05 and ho[2] < 0 and a[3] < -1.5:
        print("FADE (train <-5%, hold <0, z<-1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
