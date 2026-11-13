"""11/13 FABLE - WHEN CAN THE FIRST COLLEGE HOOPS UNIT PLAY POST? From funnel4.py's rows (today's code on every past
season): by day of the season (day 1 = the season's first priced game), how many college hoops games have both teams
4+ games in, how many dogs +100..+350 clear the dog read (4+), how many spread sides reach a stack of +0.05, and the
first day each unit play fired. If the gates open and nothing posts for weeks, something is blocking; if the plays
start the week the gates open in every season, the slots are just early.
Usage: python results/studies/leans_1113/s6_first_fire.py > results/studies/leans_1113/s6_first_fire.out"""
import collections, glob, json, os
from datetime import date

ROWS = os.path.join(os.path.expanduser("~"), ".cache", "d503_leans1113", "rows", "s20*.jsonl")
by = collections.defaultdict(list)
for f in sorted(glob.glob(ROWS)):
    for line in open(f):
        r = json.loads(line)
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        by[y if m >= 7 else y - 1].append(r)
print("season: first priced day | first day a priced game has both teams 4+ in | first dog-read 4+ dog with both 4+ | first stack +0.05 side | "
      "first unit play of each kind (day of the season)")
for s in sorted(by):
    R = by[s]
    d0 = date.fromisoformat(min(r["date"] for r in R))
    dn = lambda iso: (date.fromisoformat(iso) - d0).days + 1    # noqa: E731
    mn = lambda r: min(r.get("games_in") or 0, r.get("opp_games_in") or 0)   # noqa: E731
    both4 = min((r["date"] for r in R if mn(r) >= 4), default=None)
    dr = min((r["date"] for r in R if r["market"] == "ml" and 100 <= r["odds"] <= 350 and mn(r) >= 4 and (r.get("dog_read") or -9) >= 4), default=None)
    st = min((r["date"] for r in R if r["market"] == "spread" and (r.get("stack") or 0) >= 0.05 - 1e-9), default=None)
    first = {}
    for r in R:
        if r.get("kind"):
            first[r["kind"]] = min(first.get(r["kind"], "9"), r["date"])
    f = lambda x: "-" if x is None else f"{x[5:]} (day {dn(x)})"   # noqa: E731
    print(f"{s}: {d0.isoformat()[5:]} | {f(both4)} | {f(dr)} | {f(st)} | " + "  ".join(f"{k}: {f(v)}" for k, v in sorted(first.items())))
    # the two weeks after the gates open: how many clear, a day
    if both4:
        days = sorted({r["date"] for r in R if both4 <= r["date"]})[:14]
        row = []
        for d in days:
            X = [r for r in R if r["date"] == d]
            g4 = len({r["gid"] for r in X if mn(r) >= 4})
            dogs = [r for r in X if r["market"] == "ml" and 100 <= r["odds"] <= 350 and mn(r) >= 4]
            row.append(f"{d[5:]}: {g4}g/{len(dogs)}d/{sum((r.get('dog_read') or -9) >= 4 for r in dogs)}r/{sum(1 for r in X if r.get('kind') in ('ncaabplay', 'gap', 'stackplay'))}u")
        print("      games both 4+ / dogs in the band / dog read 4+ / hoops unit plays posted: " + "  ".join(row))
