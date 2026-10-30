"""10/30 QUESTIONABLE PLAYERS - STEP 2 (NBA): play rates, the per-player history (held out), and the market.
Reads nba_listings.csv.gz (nba_build.py). Seasons are the report's end year (2024 = 2023-24).
TRAIN = 2019..2023 report seasons, HOLDOUT = 2024..2026 (2023-24, 2024-25, 2025-26). Usage: python nba_study.py"""
import csv
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import sports_absences as sa  # noqa: E402

rows = list(csv.DictReader(gzip.open(os.path.join(HERE, "nba_listings.csv.gz"), "rt")))
for r in rows:
    for k in ("played", "key", "top1", "reg", "won", "streak"):
        r[k] = int(r[k])
    r["season"] = int(r["season"])
rows = [r for r in rows if r["stype"] == "2"]          # regular season only (the playoffs are another animal)
TRAIN, HOLD = range(2019, 2024), range(2024, 2027)


def rate(sub):
    n = len(sub)
    return f"{sum(r['played'] for r in sub) / n * 100:5.1f}% of {n:6d}" if n else "   -  of      0"


def by_season(sub):
    s = defaultdict(list)
    for r in sub:
        s[r["season"]].append(r)
    return " ".join(f"{y % 100:02d}:{sum(x['played'] for x in v) / len(v) * 100:.0f}" for y, v in sorted(s.items()))


print("=" * 100)
print("1. PLAY RATE BY STATUS (regular season, every listed man we can see in the team's box scores)")
for col, label in (("morning", "status at the 1:30 PM ET report (what the engine waits on)"), ("final", "final status before tip")):
    print(f"\n  by {label}")
    for st in ("Available", "Probable", "Questionable", "Doubtful", "Out"):
        sub = [r for r in rows if r[col] == st]
        print(f"   {st:13s} all {rate(sub)} | key men {rate([r for r in sub if r['key']])} | top scorer "
              f"{rate([r for r in sub if r['top1']])} | by season {by_season(sub)}")

Q = [r for r in rows if r["morning"] == "Questionable"]
print("\n  QUESTIONABLE at 1:30 PM -> what his FINAL status was:")
fin = defaultdict(list)
for r in Q:
    fin[r["final"]].append(r)
for k, v in sorted(fin.items(), key=lambda x: -len(x[1])):
    print(f"   final {k or '(dropped)':13s} {len(v) / len(Q) * 100:5.1f}% of the questionables, played {rate(v)}")

print("\n2. QUESTIONABLE (morning) BY KIND OF LISTING")
kinds = defaultdict(list)
for r in Q:
    kinds[r["kind"] if r["kind"] != "injury" else "injury: " + r["part"]].append(r)
for k, v in sorted(kinds.items(), key=lambda x: -len(x[1])):
    if len(v) >= 60:
        print(f"   {k:28s} {rate(v)}  key men {rate([r for r in v if r['key']])}")

print("\n3. QUESTIONABLE (morning) - STAR vs ROLE")
for lab, f in (("top scorer (top1)", lambda r: r["top1"]), ("key man (top-3 / starter 3+ of 10)", lambda r: r["key"]),
               ("regular, not key", lambda r: r["reg"] and not r["key"]), ("fringe (played <3 of last 10)", lambda r: not r["reg"])):
    v = [r for r in Q if f(r)]
    print(f"   {lab:36s} {rate(v)}  train {rate([r for r in v if r['season'] in TRAIN])}  hold {rate([r for r in v if r['season'] in HOLD])}")

print("\n4. QUESTIONABLE (morning) - HOW MANY GAMES IN A ROW HE'S BEEN LISTED QUESTIONABLE BEFORE THIS ONE")
for k in (0, 1, 2, 3, 5, 10):
    v = [r for r in Q if (r["streak"] == k if k < 3 else (3 <= r["streak"] < 5 if k == 3 else (5 <= r["streak"] < 10 if k == 5 else r["streak"] >= 10)))]
    lab = {0: "first listing", 1: "2nd in a row", 2: "3rd in a row", 3: "4th-5th", 5: "6th-10th", 10: "11th+"}[k]
    print(f"   {lab:14s} all {rate(v)}  key men {rate([r for r in v if r['key']])}")

# ---------------------------------------------------------------- 5. the per-player history, strictly before the game
print("\n5. THE PER-PLAYER HISTORY (strictly before the game; questionable at 1:30 PM; regular season)")
hist = defaultdict(lambda: [0, 0])                  # pid/name -> [listed, played]
# (one pass with the update after each game day so same-day rows don't see each other)
hist.clear()
day, buf = None, []
for r in sorted(Q, key=lambda r: (r["date"], r["gid"])):
    if r["date"] != day:
        for x in buf:
            h = hist[x["pid"] or sa._nm(x["player"])]
            h[0] += 1
            h[1] += x["played"]
        buf, day = [], r["date"]
    h = hist[r["pid"] or sa._nm(r["player"])]
    r["prior_n"], r["prior_p"] = h[0], h[1]
    buf.append(r)

BASE = sum(r["played"] for r in Q if r["season"] in TRAIN) / max(1, sum(1 for r in Q if r["season"] in TRAIN))
PRIOR_W = 4                                          # shrink toward the league rate with 4 games' weight


def shrunk(n, p, base=BASE, w=PRIOR_W):
    return (p + w * base) / (n + w)


print(f"   league questionable play rate (train) {BASE * 100:.1f}%; shrink weight {PRIOR_W}")
for lab, f in (("no history (first time)", lambda r: r["prior_n"] == 0),
               ("history 1-4", lambda r: 1 <= r["prior_n"] <= 4),
               ("history 5+", lambda r: r["prior_n"] >= 5)):
    v = [r for r in Q if f(r)]
    print(f"   {lab:26s} {rate(v)}")
print("   by the shrunk prior rate (HOLDOUT seasons only - the history is from before each game):")
for lo, hi in ((0, .5), (.5, .65), (.65, .75), (.75, .85), (.85, .9), (.9, 1.01)):
    for keyonly in (False, True):
        v = [r for r in Q if r["season"] in HOLD and lo <= shrunk(r["prior_n"], r["prior_p"]) < hi and (r["key"] or not keyonly)]
        print(f"     prior {lo * 100:3.0f}-{min(hi, 1) * 100:3.0f}% {'key men' if keyonly else 'all    '} {rate(v)}")
for n_min in (5, 8, 10):
    v = [r for r in Q if r["season"] in HOLD and r["key"] and r["prior_n"] >= n_min and shrunk(r["prior_n"], r["prior_p"]) >= .85]
    w = [r for r in Q if r["season"] in HOLD and r["key"] and not (r["prior_n"] >= n_min and shrunk(r["prior_n"], r["prior_p"]) >= .85)]
    print(f"   HOLDOUT key men, {n_min}+ prior listings and shrunk rate 85%+: {rate(v)}   | every other key questionable {rate(w)}")
    for y in HOLD:
        vv = [r for r in v if r["season"] == y]
        print(f"        {y}: {rate(vv)}")

# the "always questionable, always plays" men (whole sample, 10+ listings)
tot = defaultdict(lambda: [0, 0, "", 0])
for r in Q:
    t = tot[r["pid"] or sa._nm(r["player"])]
    t[0] += 1
    t[1] += r["played"]
    t[2] = r["player"]
    t[3] += r["key"]
print("\n   MOST-LISTED QUESTIONABLE MEN (2018-19..2025-26 regular seasons, morning questionable)")
for k, (n, p, nm, kk) in sorted(tot.items(), key=lambda x: -x[1][0])[:30]:
    print(f"     {nm:26s} listed {n:3d}  played {p:3d}  {p / n * 100:5.1f}%   (as a key man {kk})")
print("   always-questionable, always-plays (25+ listings, 90%+):")
for k, (n, p, nm, kk) in sorted(tot.items(), key=lambda x: -x[1][1] / x[1][0]):
    if n >= 25 and p / n >= .9:
        print(f"     {nm:26s} {p}/{n} = {p / n * 100:.0f}%")
print("   and the ones who usually SIT (25+ listings, under 50%):")
for k, (n, p, nm, kk) in sorted(tot.items(), key=lambda x: x[1][1] / x[1][0]):
    if n >= 25 and p / n < .5:
        print(f"     {nm:26s} {p}/{n} = {p / n * 100:.0f}%")
for nm in ("Rui Hachimura", "Anthony Davis", "Yaxel Lendeborg", "LeBron James", "Kawhi Leonard", "Joel Embiid",
           "Giannis Antetokounmpo", "Stephen Curry", "Jimmy Butler", "Kevin Durant", "Zion Williamson", "Ja Morant"):
    t = next((v for v in tot.values() if v[2] == nm), None)
    if t:
        print(f"     {nm:26s} {t[1]}/{t[0]} = {t[1] / t[0] * 100:.0f}%")

# ---------------------------------------------------------------- 6. the market
print("\n6. THE MARKET - team-games with a KEY man questionable at 1:30 PM (his team's side), regular season")


def dec(ml):
    ml = float(ml)
    return 1 + (ml / 100 if ml > 0 else 100 / -ml)


def nv(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


tg = defaultdict(list)
for r in Q:
    if r["key"]:
        tg[(r["gid"], r["team"])].append(r)
# control: every team-game in the same seasons with NO key man questionable / doubtful / out at 1:30
listed_key = {(r["gid"], r["team"]) for r in rows if r["key"] and r["morning"] in ("Questionable", "Doubtful", "Out")}
ctrl = {}
import glob  # noqa: E402
for f in sorted(glob.glob(os.path.join(REPO, "data/sports/games/nba/*.csv"))):
    for g in csv.DictReader(open(f)):
        if g["stype"] != "2" or g["status"] != "final" or not g["ml_home"] or not g["ml_away"]:
            continue
        for side, opp in (("home", "away"), ("away", "home")):
            if (g["id"], g[side]) not in listed_key:
                ctrl[(g["id"], g[side])] = dict(ml=g["ml_" + side], ml_opp=g["ml_" + opp], ml_open=g.get("ml_" + side + "_open"),
                                                ml_opp_open=g.get("ml_" + opp + "_open"), won=int(float(g[side + "_score"]) > float(g[opp + "_score"])),
                                                date=g["start"][:10])
TG = []
for k, v in tg.items():
    r0 = v[0]
    if not r0["ml"] or not r0["ml_opp"]:
        continue
    TG.append(dict(ml=r0["ml"], ml_opp=r0["ml_opp"], ml_open=r0["ml_open"], ml_opp_open=r0["ml_opp_open"], won=r0["won"],
                   all_played=int(all(x["played"] for x in v)), any_sat=int(any(not x["played"] for x in v)),
                   season=r0["season"], top1=int(any(x["top1"] for x in v)), date=r0["date"]))


def mkt(sub, lab):
    n = len(sub)
    if not n:
        print(f"   {lab:44s} n=0")
        return
    exp = sum(nv(r["ml"], r["ml_opp"]) for r in sub)
    w = sum(r["won"] for r in sub)
    roi = sum((dec(r["ml"]) - 1) if r["won"] else -1 for r in sub) / n * 100
    op = [r for r in sub if r["ml_open"] and r["ml_opp_open"]]
    if op:
        mv = sum(nv(r["ml"], r["ml_opp"]) - nv(r["ml_open"], r["ml_opp_open"]) for r in op) / len(op) * 100
        clv = sum(nv(r["ml"], r["ml_opp"]) * dec(r["ml_open"]) - 1 for r in op) / len(op) * 100
        roi_o = sum((dec(r["ml_open"]) - 1) if r["won"] else -1 for r in op) / len(op) * 100
        extra = f" | open->close move {mv:+5.2f} pts, bet-at-open value vs the close {clv:+5.1f}%, ROI at open {roi_o:+5.1f}% (n {len(op)})"
    else:
        extra = ""
    print(f"   {lab:44s} n={n:5d} won {w / n * 100:5.1f}% vs close no-vig {exp / n * 100:5.1f}% ({(w - exp) / n * 100:+5.1f}) ROI at close {roi:+6.1f}%{extra}")


mkt(TG, "ALL key-questionable team-games")
mkt([r for r in TG if r["all_played"]], "  ...he PLAYED")
mkt([r for r in TG if r["any_sat"]], "  ...he SAT")
mkt([r for r in TG if r["top1"]], "top scorer questionable")
mkt([r for r in TG if r["top1"] and r["all_played"]], "  ...he PLAYED")
mkt([r for r in TG if r["top1"] and r["any_sat"]], "  ...he SAT")
mkt(list(ctrl.values()), "CONTROL: no key man listed at 1:30 PM")
for y in sorted({r["season"] for r in TG}):
    mkt([r for r in TG if r["season"] == y], f"  season {y}")

print("\n7. WHAT THE HOLD DOES (bet at the open vs wait for the news) - key-questionable team-games with an open price")
op = [r for r in TG if r["ml_open"] and r["ml_opp_open"]]
pl = [r for r in op if r["all_played"]]
st = [r for r in op if r["any_sat"]]
if op:
    f_pl = len(pl) / len(op)
    clv_pl = sum(nv(r["ml"], r["ml_opp"]) * dec(r["ml_open"]) - 1 for r in pl) / max(1, len(pl))
    clv_st = sum(nv(r["ml"], r["ml_opp"]) * dec(r["ml_open"]) - 1 for r in st) / max(1, len(st))
    print(f"   he played {f_pl * 100:.1f}% of {len(op)}; betting at the open was worth {clv_pl * 100:+.1f}% vs the close when he played,"
          f" {clv_st * 100:+.1f}% when he sat")
    print(f"   no hold, bet every one at the open: {(f_pl * clv_pl + (1 - f_pl) * clv_st) * 100:+.2f}% a bet (vs the close)")
    print(f"   hold, bet only if he plays (at the close): 0% vs the close on {f_pl * 100:.0f}% of the bets; the open price"
          f" he'd have had: {f_pl * clv_pl * 100:+.2f}% a slot given up, {-(1 - f_pl) * clv_st * 100:+.2f}% a slot saved")
