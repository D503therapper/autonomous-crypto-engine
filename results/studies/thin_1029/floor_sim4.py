"""Round three: the candidate rule with the owner's one-a-day fallback, kinds and seasons. Usage: python floor_sim4.py "f*.jsonl" """
import sys
from collections import defaultdict

sys.argv = [sys.argv[0], sys.argv[1]]
import floor_sim2 as F   # noqa: E402
from floor_sim3 import season_line   # noqa: E402

NOT_NBA_NCAAF = lambda r: r["league"] not in ("nba", "ncaaf")     # noqa: E731
THIN = lambda r: bool(r.get("thin"))                               # noqa: E731


def run(label, show_kinds=True, **kw):
    cfg = dict(F.BASE, **kw)
    pb = {d: F.build(d, cfg) for d in F.days}
    F.stats(pb, label, show_kinds)
    print("   seasons", season_line(pb))
    return pb


for label, kw in (
        ("TODAY", {}),
        ("A. floor: thin only, fallback to the best dog for 1 a day", {"floor_filter": THIN, "fallback_min": 1}),
        ("B. floor: no NBA / college football, fallback 1", {"floor_filter": NOT_NBA_NCAAF, "fallback_min": 1}),
        ("C. floor: no NBA / college football + thin only, fallback 1", {"floor_filter": lambda r: NOT_NBA_NCAAF(r) and THIN(r), "fallback_min": 1}),
        ("C2. same, fallback to 2", {"floor_filter": lambda r: NOT_NBA_NCAAF(r) and THIN(r), "fallback_min": 2}),
        ("D. floor: no NBA + thin only, fallback 1", {"floor_filter": lambda r: r["league"] != "nba" and THIN(r), "fallback_min": 1}),
        ("E. floor: no NBA, fallback 1", {"floor_filter": lambda r: r["league"] != "nba", "fallback_min": 1}),
):
    pb = run(label, **kw)
    if label[:2] in ("C.", "A.", "D."):
        F.floor_table(pb, label)
