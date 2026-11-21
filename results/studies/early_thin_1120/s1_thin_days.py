"""11/20 - EARLY PLAYS + THIN BOARD DAYS, part 2: THE THIN DAYS (the owner, 11/20: "We don't really have any plays today
besides the early plays").
The rig: dogs_1117's R3 rows (the board re-built on the 11/17 code, every board day 2023-10 -> 2026-11 at the closing
price, every moneyline side with its reads / gates / dog score) through money_1117's live shape (mlib.board - what the
live post makes of it). NOT on the rig, said once: baseball, the college hoops spread stack play, the totals, the early
plays, mid-day adds, injury reports - so a real day carries a little more than the rig shows in-season and less when a
report holds a side.
THE QUESTIONS: (1) how often is the board 0 or 1 unit plays; (2) what did the NEXT side in line do on those days - each
candidate the best ONE a thin day (the floor's own ranking - the dog score - unless said), train (to 6/30/2025) and held
out (after) apart; (3) does any of them clear the standing bar: up in both halves, most seasons up, a random same-size
set from its own pool as good under 100 of 2,000 times, a point worse than the close still up, a real sample.
Usage: python3 results/studies/early_thin_1120/s1_thin_days.py > results/studies/early_thin_1120/s1_thin_days.out"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "money_1117"))
import mlib as M  # noqa: E402

D = M.D
R = D.r3()
plays, days = M.board()
N = Counter(p["date"] for p in plays)
BY = defaultdict(list)
for r in R:
    BY[r["date"]].append(r)
ONKEY = {(p["gid"], p["side"]) for p in plays}
ONGAME = defaultdict(set)
for p in plays:
    ONGAME[p["date"]].add(p["gid"])
NBA_ON = {p["date"] for p in plays if p["league"] == "nba"}
SEASON = lambda d: d[5:10] >= "10-15" or d[5:10] <= "04-15"   # noqa: E731


def say(*a):
    print(*a, flush=True)


def free(r):
    """a side the board is not on (no pick on its game that day)"""
    return (r["gid"], r["side"]) not in ONKEY and r["gid"] not in ONGAME[r["date"]]


def dog(r):
    return 100 <= r["odds"] <= 350


def pool_ok(r):
    """the daily floor's own pool: a dog +100..+350, never a trap, a named reason, never fighting, not waiting, an NBA
    ½u dog only to +199"""
    return dog(r) and not r.get("trap") and r.get("reasons") and not r.get("fighting") and not r.get("waiting") \
        and not (r["league"] == "nba" and r["odds"] > 199)


def sc(r):
    return r["dog_score"] if r.get("dog_score") is not None else -99


def best_a_day(rows, key=sc, dayset=None, k=1):
    by = defaultdict(list)
    for r in rows:
        if dayset is None or r["date"] in dayset:
            by[r["date"]].append(r)
    out = []
    for d, rs in by.items():
        seen = set()
        for r in sorted(rs, key=lambda r: -key(r)):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                out.append(r)
            if len(seen) >= k:
                break
    return out


def cell(name, rs, pool=None):
    c = D.cell(name, rs, say=say, w=74)
    pb = D.placebo(rs, pool) if pool is not None else None
    if pb is not None:
        say(f"      placebo: a random same-size set from its own pool as good {pb} of 2,000")
    return c, pb


say("=" * 30, "1. HOW OFTEN IS THE BOARD THIN (unit plays a board day, the rig)")
for nm, f in (("every board day", lambda d: True), ("in season (10/15 - 4/15)", SEASON)):
    for h in ("train", "held", "live"):
        ds = [d for d in days if f(d) and D.half(d) == h]
        if ds:
            z, o, t = (sum(N.get(d, 0) == 0 for d in ds), sum(N.get(d, 0) == 1 for d in ds), sum(N.get(d, 0) >= 2 for d in ds))
            say(f"  {nm:26s} {h:5s} {len(ds):4d} days | none {z:3d} ({100 * z / len(ds):4.1f}%) | one {o:3d} ({100 * o / len(ds):4.1f}%) "
                f"| two or more {t:3d} ({100 * t / len(ds):4.1f}%)")
bm = defaultdict(lambda: [0, 0, 0])
for d in days:
    bm[d[5:7]][0] += 1
    bm[d[5:7]][1] += N.get(d, 0) == 0
    bm[d[5:7]][2] += N.get(d, 0) == 1
say("  by month (days / none / one): " + " · ".join(f"{m} {v[0]}/{v[1]}/{v[2]}" for m, v in sorted(bm.items())))
slate = lambda d: tuple(sorted({r["league"] for r in BY[d]}))   # noqa: E731
for lab, k in (("no unit play", 0), ("one unit play", 1)):
    c = Counter(slate(d) for d in days if N.get(d, 0) == k and SEASON(d))
    say(f"  in season, {lab} - the slate that day: " + " · ".join(f"{'+'.join(s)} {n}" for s, n in c.most_common(8)))
nh = [d for d in days if SEASON(d) and "nhl" not in slate(d)]
say(f"  in-season days with NO hockey game: {len(nh)} - none {sum(N.get(d, 0) == 0 for d in nh)}, one {sum(N.get(d, 0) == 1 for d in nh)}, "
    f"two+ {sum(N.get(d, 0) >= 2 for d in nh)}")

say("\n" + "=" * 30, "2. WHAT THE BOARD'S OWN PLAYS DID - by how many it posted that day (as sized today)")
for lab, f in (("the day's ONLY unit play", lambda n: n == 1), ("days with 2", lambda n: n == 2), ("days with 3+", lambda n: n >= 3)):
    rs = [p for p in plays if f(N[p["date"]])]
    D.sched(lab, [(p, p["u"]) for p in rs], say=say)
    D.cell("   flat", rs, say=say, w=40)

THIN = {d for d in days if N.get(d, 0) <= 1}
ZERO = {d for d in days if N.get(d, 0) == 0}
ONE = THIN - ZERO
ALLD = [r for r in R if dog(r) and not r.get("kind")]
say(f"\nthin days: {len(THIN)} ({len(ZERO)} none, {len(ONE)} one); every dog +100..+350 the board is NOT on, any day:")
D.cell("every dog not on the board", ALLD, say=say, w=40)

say("\n" + "=" * 30, "3. THE NEXT SIDE IN LINE ON A THIN DAY (0-1 unit plays) - the best ONE a day by the dog score")
FP = [r for r in R if pool_ok(r) and free(r) and not r.get("kind")]
say("-- (a) the floor's own pool (a named reason, not fighting), the dogs the floor's rules hold back")
for lab, f in (
        ("floor pool, any reason held (best a thin day)", lambda r: True),
        ("  not skipped, score under 0 (the 11/11 second-play rule)", lambda r: not r.get("floor_skip") and sc(r) < 0),
        ("  not skipped, score 0+ (should be none - the floor takes it)", lambda r: not r.get("floor_skip") and sc(r) >= 0),
        ("  skipped: college hoops dog", lambda r: r["league"] == "ncaab"),
        ("  skipped: college hoops dog, score 2+", lambda r: r["league"] == "ncaab" and sc(r) >= 2),
        ("  skipped: college football dog", lambda r: r["league"] == "ncaaf"),
        ("  skipped: NBA dog (a 2nd NBA dog / under the NBA floor)", lambda r: r["league"] == "nba"),
        ("  skipped: NBA dog, score 0+", lambda r: r["league"] == "nba" and sc(r) >= 0),
        ("  skipped: NBA dog, score under 0", lambda r: r["league"] == "nba" and sc(r) < 0),
        ("  skipped: NFL home dog", lambda r: r["league"] == "nfl" and r.get("floor_skip") and r.get("home")),
        ("  skipped: hockey dog, raw read 3c+ over (not thin)", lambda r: r["league"] == "nhl" and r.get("floor_skip")),
        ("  hockey dog in the pool, any score", lambda r: r["league"] == "nhl"),
        ("  hockey dog in the pool, score under 0", lambda r: r["league"] == "nhl" and sc(r) < 0)):
    pl = [r for r in FP if f(r)]
    cell(lab, best_a_day(pl, dayset=THIN), pool=[r for r in pl if r["date"] in THIN])
    cell("    ... the same rule on EVERY day (every such dog, not one a day)", pl)

say("-- (b) dogs with NO named reason (out of the floor's pool), not a trap, not fighting")
NR = [r for r in R if dog(r) and free(r) and not r.get("kind") and not r.get("trap") and not r.get("fighting") and not r.get("reasons")
      and not (r["league"] == "nba" and r["odds"] > 199)]
for lab, f in (("hockey, score 3 to 6 (under the named-score gate)", lambda r: r["league"] == "nhl" and 3 <= sc(r) < 6),
               ("hockey, score 0 to 3", lambda r: r["league"] == "nhl" and 0 <= sc(r) < 3),
               ("hockey, score under 0", lambda r: r["league"] == "nhl" and sc(r) < 0),
               ("NBA, score under 0", lambda r: r["league"] == "nba" and sc(r) < 0),
               ("NFL, any score", lambda r: r["league"] == "nfl"),
               ("college football, any score", lambda r: r["league"] == "ncaaf")):
    pl = [r for r in NR if f(r)]
    cell(lab + " - best a thin day", best_a_day(pl, dayset=THIN), pool=[r for r in pl if r["date"] in THIN])
    cell("    ... every such dog, every day", pl)

say("-- (c) the college hoops dog slot's next side (the dog read; the slot takes 2 a night at 4+, a true road dog at 3)")
CB = [r for r in R if r["league"] == "ncaab" and dog(r) and free(r) and not r.get("kind") and r.get("dog_read") is not None]
rd = lambda r: r.get("dog_read") or -99   # noqa: E731
for lab, f in (("read 4+ and the games rule ok - a 3rd (or held) slot dog", lambda r: rd(r) >= 4 and r.get("dog_read_ok")),
               ("read 3 to 4, games ok (read_parts)", lambda r: 3 <= rd(r) < 4 and (r.get("read_parts") or {}).get("games_ok")),
               ("read 2 to 3, games ok", lambda r: 2 <= rd(r) < 3 and (r.get("read_parts") or {}).get("games_ok"))):
    pl = [r for r in CB if f(r)]
    cell(lab + " - best a thin day", best_a_day(pl, key=rd, dayset=THIN), pool=[r for r in pl if r["date"] in THIN])
    cell("    ... every such dog, every day", pl)
    for nm, g in (("not a trap, not fighting", lambda r: not r.get("trap") and not r.get("fighting")),
                  ("true road", lambda r: not r.get("home") and not r.get("neutral")),
                  ("home", lambda r: r.get("home") and not r.get("neutral")), ("neutral", lambda r: r.get("neutral"))):
        cell(f"        {nm}", [r for r in pl if g(r)])

say("-- (d) favorites -150..-101 the value bar held back (the best ONE a thin day by the own read's margin)")
FV = [r for r in R if -150 <= r["odds"] <= -101 and free(r) and not r.get("kind") and not r.get("trap") and not r.get("fighting")]
om = lambda r: ((r["edge_own"] + 1) / r["dec"] - 1 / r["dec"]) * 100 if r.get("edge_own") is not None else -99   # noqa: E731
for lab, f in (("own read over the price by 0 to 1 pt (under the 11/12 edge bar), good", lambda r: r.get("good") and 0 <= om(r) < 1),
               ("own read over the price 1+ pt, good, not posted (why: real_value / the cap)", lambda r: r.get("good") and om(r) >= 1),
               ("own read over the price, no named reason (not good)", lambda r: not r.get("good") and om(r) >= 0),
               ("any favorite, own read under the price by 0 to 2", lambda r: -2 <= om(r) < 0)):
    for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
        pl = [r for r in FV if f(r) and r["league"] == lg]
        if len(pl) >= 30:
            cell(f"{lab} - {lg}, best a thin day", best_a_day(pl, key=om, dayset=THIN), pool=[r for r in pl if r["date"] in THIN])
            cell("    ... every such favorite, every day", pl)

say("-- (e) a day with NO unit play at all: the best dog by score left on the slate (not a trap, not fighting; reason or not)")
ZP = [r for r in R if dog(r) and not r.get("trap") and not r.get("fighting") and not (r["league"] == "nba" and r["odds"] > 199)]
cell("best dog by score, a no-play day", best_a_day(ZP, dayset=ZERO), pool=[r for r in ZP if r["date"] in ZERO])
for lg in ("nhl", "nba", "ncaab", "ncaaf", "nfl"):
    pl = [r for r in ZP if r["league"] == lg]
    cell(f"   {lg} only", best_a_day(pl, dayset=ZERO), pool=[r for r in pl if r["date"] in ZERO])
cell("best dog by score 0+, a no-play day", best_a_day([r for r in ZP if sc(r) >= 0], dayset=ZERO))
cell("best dog by score 2+, a no-play day", best_a_day([r for r in ZP if sc(r) >= 2], dayset=ZERO))
