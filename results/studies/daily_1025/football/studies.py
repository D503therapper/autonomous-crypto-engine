"""10/25 daily run - 5 football studies. Prices: closing moneyline from the game files (2018-26) = what the 8 AM
board / game day can take; second check: the first FAIR early look (paid odds history 2020-25, early_football_study.fair).
Train 2018-24 / holdout 2025 / now 2026. Flat 1u. Every cell is printed with its same-price baseline.
S1 college rating-backed gap dogs (walk-forward Elo + home edge 10+ / 15+ over the no-vig close): what separates
   winners - power tier, home/away, spread size, open->close move, price band, week.
S2 road favorites off a HOME WIN (college; NFL = second check), -101..-150 and -151..-300.
S3 college team the week after playing a service academy (Army / Navy / Air Force).
S4 college rest: short week (<=6 days) vs an opponent on 7+; the college mini-bye (8-12 days, a weekday game first)
   vs an opponent on <=7.
S5 NFL Sunday window: early (1 PM ET) vs late (4 PM ET) vs night, dogs and favorites, home and road."""
import os, pickle, math, statistics, sys
from collections import defaultdict
OUT = os.path.dirname(os.path.abspath(__file__))
S = pickle.load(open(os.path.join(OUT, "sides.pkl"), "rb"))
try:
    EARLY = pickle.load(open(os.path.join(OUT, "early_prices.pkl"), "rb"))
except Exception:
    EARLY = {}
CELLS = []
LINES = []


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
    ps = [prof(x) for x in rows]
    a = st(ps)
    if not a:
        LINES.append(f"  {name:58s} -"); return
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
    LINES.append(f"  {name:58s} n {a[0]:4d} win {a[1]:.1%} ROI {a[2]:+.1%} z {a[3]:+.1f} | train {f(tr)} up {up}/{nt}"
                 f" | 2023+ {f(l3)} | hold25 {f(ho)} | 2026 {f(cu)} | early {f(st(ep))} | ATS {f(st(at))}{bl}")
    LINES.append(f"      seasons {seas}")
    if primary:
        CELLS.append((name, a, tr, ho))


def band(x, lo, hi):
    return lo <= x["ml"] <= hi


NC = [x for x in S if x["league"] == "ncaaf"]
NF = [x for x in S if x["league"] == "nfl"]

# ---------------- S1 ----------------
LINES.append("S1 COLLEGE RATING-BACKED GAP DOGS (+100..+350 at the close, Elo+home 10+ / 15+ points over the no-vig close)")
dogs = [x for x in NC if band(x, 100, 350) and x["w"] + x["l"] >= 2]
g10 = [x for x in dogs if x["elo_p"] - x["mp"] >= 0.10]
g15 = [x for x in dogs if x["elo_p"] - x["mp"] >= 0.15]
cell("all college dogs +100..+350 (2+ games in)", dogs, primary=False)
cell("gap 10+", g10, dogs)
cell("gap 15+", g15, dogs)
for nm, gg in (("10+", g10), ("15+", g15)):
    LINES.append(f" -- splits of gap {nm}")
    for lab, fn in (
        ("dog POWER", lambda x: x["pw"]), ("dog G5/other", lambda x: not x["pw"]),
        ("dog power vs power fav", lambda x: x["pw"] and x["opw"]), ("G5 dog vs power fav", lambda x: not x["pw"] and x["opw"]),
        ("G5 vs G5", lambda x: not x["pw"] and not x["opw"]), ("power dog vs G5 fav", lambda x: x["pw"] and not x["opw"]),
        ("dog at HOME", lambda x: x["home"]), ("dog on the ROAD", lambda x: not x["home"] and not x["neutral"]),
        ("dog +100..+150", lambda x: x["ml"] < 150), ("dog +150..+250", lambda x: 150 <= x["ml"] < 250), ("dog +250..+350", lambda x: x["ml"] >= 250),
        ("spread +1..+3.5", lambda x: x["pts"] is not None and x["pts"] <= 3.5), ("spread +4..+7", lambda x: x["pts"] is not None and 3.5 < x["pts"] <= 7),
        ("spread +7.5+", lambda x: x["pts"] is not None and x["pts"] > 7),
        ("line moved TO the dog 2+ pts (open->close)", lambda x: x["op"] is not None and x["mp"] - x["op"] >= 0.02),
        ("line flat (within 2 pts)", lambda x: x["op"] is not None and abs(x["mp"] - x["op"]) < 0.02),
        ("line moved AWAY from the dog 2+ pts", lambda x: x["op"] is not None and x["op"] - x["mp"] >= 0.02),
        ("line moved AWAY 4+ pts", lambda x: x["op"] is not None and x["op"] - x["mp"] >= 0.04),
        ("Sep", lambda x: x["start"][5:7] in ("08", "09")), ("Oct", lambda x: x["start"][5:7] == "10"), ("Nov+", lambda x: x["start"][5:7] in ("11", "12")),
        ("Saturday", lambda x: x["et_dow"] == 5), ("weekday", lambda x: x["et_dow"] != 5),
        ("dog winning record", lambda x: x["w"] > x["l"]), ("dog losing record", lambda x: x["w"] < x["l"]),
        ("dog off a loss", lambda x: x["last_won"] is False), ("dog off a win", lambda x: x["last_won"] is True),
    ):
        sub = [x for x in gg if fn(x)]
        cell(f"gap {nm} {lab}", sub, [x for x in dogs if fn(x)])

# ---------------- S2 ----------------
LINES.append("\nS2 ROAD FAVORITES OFF A HOME WIN (not neutral now; last game this season a home win)")
for lg, rows in (("college", NC), ("NFL", NF)):
    for lo, hi, bn in ((-150, -101, "-101..-150"), (-300, -151, "-151..-300")):
        rf = [x for x in rows if not x["home"] and not x["neutral"] and lo <= x["ml"] <= hi and x["w"] + x["l"] >= 1]
        sub = [x for x in rf if x["last_won"] is True and x["last_home"] is True]
        cell(f"{lg} road fav {bn} off a HOME WIN", sub, rf)
        cell(f"{lg} road fav {bn} off a home win, opp off a loss", [x for x in sub if x["o_last_won"] is False], rf)
        cell(f"{lg} road fav {bn} off a home win, opp off a win", [x for x in sub if x["o_last_won"] is True], rf)
        cell(f"{lg} road fav {bn} off a ROAD win (control)", [x for x in rf if x["last_won"] is True and x["last_home"] is False], rf, primary=False)
        cell(f"{lg} road fav {bn} off a loss (control)", [x for x in rf if x["last_won"] is False], rf, primary=False)
        # the dog facing it
        hd = [x for x in rows if x["home"] and 100 <= x["ml"] <= (130 if hi == -101 else 260)]
        cell(f"{lg} home dog vs a road fav {bn} off a home win", [x for x in hd if x["o_last_won"] is True and x["o_last_home"] is True], hd)

# ---------------- S3 ----------------
LINES.append("\nS3 COLLEGE: THE GAME AFTER PLAYING A SERVICE ACADEMY (triple option); academies themselves excluded")
AC = {"Army", "Navy", "Air Force"}
na = [x for x in NC if x["team"] not in AC and x["opp"] not in AC]
after = [x for x in na if x["last_opp"] in AC and x["rest"] is not None and x["rest"] <= 15]
cell("after an academy - every side", after, na)
cell("after an academy - as a favorite -101..-300", [x for x in after if -300 <= x["ml"] <= -101], [x for x in na if -300 <= x["ml"] <= -101])
cell("after an academy - as a favorite -101..-150", [x for x in after if -150 <= x["ml"] <= -101], [x for x in na if -150 <= x["ml"] <= -101])
cell("after an academy - as a dog +100..+350", [x for x in after if 100 <= x["ml"] <= 350], [x for x in na if 100 <= x["ml"] <= 350])
cell("OPPONENT after an academy - as a dog +100..+350 (bet the fresh team)", [x for x in na if x["o_last_opp"] in AC and x["o_rest"] and x["o_rest"] <= 15 and 100 <= x["ml"] <= 350], [x for x in na if 100 <= x["ml"] <= 350])
cell("OPPONENT after an academy - as a fav -101..-300", [x for x in na if x["o_last_opp"] in AC and x["o_rest"] and x["o_rest"] <= 15 and -300 <= x["ml"] <= -101], [x for x in na if -300 <= x["ml"] <= -101])
cell("after an academy, academy game was a LOSS", [x for x in after if x["last_won"] is False], na)
cell("after an academy, academy game was a WIN", [x for x in after if x["last_won"] is True], na)

# ---------------- S4 ----------------
LINES.append("\nS4 COLLEGE REST: short week vs a rested team; the college mini-bye (weekday game, then 8-12 days)")
rr = [x for x in NC if x["rest"] is not None and x["o_rest"] is not None]
for lab, fn in (
    ("SHORT (<=6d) vs opp 7+d", lambda x: x["rest"] <= 6.2 and x["o_rest"] >= 6.8),
    ("SHORT (<=6d) vs opp 9+d", lambda x: x["rest"] <= 6.2 and x["o_rest"] >= 8.8),
    ("MINI-BYE 8-12d vs opp <=7.2d", lambda x: 7.8 <= x["rest"] <= 12.2 and x["o_rest"] <= 7.2),
    ("MINI-BYE 8-12d after a weekday game vs opp <=7.2d", lambda x: 7.8 <= x["rest"] <= 12.2 and x["o_rest"] <= 7.2 and x["last_dow"] in (0, 1, 2, 3, 4)),
):
    sub = [x for x in rr if fn(x)]
    cell(f"{lab} - dog +100..+350", [x for x in sub if band(x, 100, 350)], [x for x in rr if band(x, 100, 350)])
    cell(f"{lab} - fav -101..-150", [x for x in sub if band(x, -150, -101)], [x for x in rr if band(x, -150, -101)])
    cell(f"{lab} - fav -151..-300", [x for x in sub if band(x, -300, -151)], [x for x in rr if band(x, -300, -151)])

# ---------------- S5 ----------------
LINES.append("\nS5 NFL SUNDAY WINDOW (ET kickoff: early 12:30-2:30, late 3:30-5:30, night 7+)")
sun = [x for x in NF if x["et_dow"] == 6 and not x["neutral"]]
win = {"early": lambda x: 12.4 <= x["et_hour"] < 14.5, "late": lambda x: 15.4 <= x["et_hour"] < 17.5, "night": lambda x: x["et_hour"] >= 19}
for wn, wf in win.items():
    for lab, fn in (("home dog +100..+350", lambda x: x["home"] and band(x, 100, 350)), ("road dog +100..+350", lambda x: not x["home"] and band(x, 100, 350)),
                    ("home fav -101..-150", lambda x: x["home"] and band(x, -150, -101)), ("road fav -101..-150", lambda x: not x["home"] and band(x, -150, -101))):
        cell(f"{wn} - {lab}", [x for x in sun if wf(x) and fn(x)], [x for x in sun if fn(x)])
# west / east body clock inside the late window is built - skip; one extra: late-window road dog that played the early window last week? not run.

print("\n".join(LINES))
print(f"\nprimary cells {len(CELLS)}; expected ~{0.05*len(CELLS):.0f} |z|>2 by chance; |z|>2 here: "
      + str(sum(1 for c in CELLS if abs(c[1][3]) > 2)))
for c in CELLS:
    a, tr, ho = c[1], c[2], c[3]
    if tr and ho and tr[0] >= 40 and tr[2] > 0.03 and ho[2] > 0 and a[3] > 1.5:
        print("SURVIVOR (train >+3%, hold >0, z>1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
    if tr and ho and tr[0] >= 40 and tr[2] < -0.05 and ho[2] < 0 and a[3] < -1.5:
        print("FADE (train <-5%, hold <0, z<-1.5):", c[0], f"{a[0]} {a[2]:+.1%} z{a[3]:+.1f}", f(tr), f(ho))
