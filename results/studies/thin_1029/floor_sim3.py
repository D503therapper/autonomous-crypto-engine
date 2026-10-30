"""Round two: the floor without the NBA (the NBA floor stays) / without college football / thin-only, with the by-season
units. Usage: python floor_sim3.py "f*.jsonl" """
import sys
from collections import defaultdict

sys.argv = [sys.argv[0], sys.argv[1]]
import floor_sim2 as F   # noqa: E402

BASE = F.BASE
build0 = F.build


def build(d, cfg):
    out = build0(d, cfg)
    return out


def season_line(pb):
    seas = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for d in F.days:
        for r, u, k in pb[d]:
            s = seas[F.season(d)]
            s[0] += r["result"] == "won"
            s[1] += r["result"] == "lost"
            s[2] += F.pnl(r, u)
            s[3] += u
    return " | ".join(f"{k}: {v[0]}-{v[1]} {v[2]:+.1f}u ({100 * v[2] / v[3] if v[3] else 0:+.1f}%)" for k, v in sorted(seas.items()))


def run(label, **kw):
    cfg = dict(BASE, **kw)
    pb = {d: build(d, cfg) for d in F.days}
    F.stats(pb, label)
    print("   seasons", season_line(pb))
    return pb


# monkey-patch floor_ok for the league / thin filters
orig_floor_ok = F.floor_ok
for label, fn in () if __name__ != "__main__" else (
        ("TODAY", lambda r: True),
        ("floor: no NBA in the general floor (the NBA floor stays)", lambda r: r["league"] != "nba"),
        ("floor: no college football", lambda r: r["league"] != "ncaaf"),
        ("floor: no NBA, no college football", lambda r: r["league"] not in ("nba", "ncaaf")),
        ("floor: thin only (own read under 3c over the price)", lambda r: r.get("thin")),
        ("floor: no NBA, no college football, thin only", lambda r: r["league"] not in ("nba", "ncaaf") and r.get("thin")),
        ("floor: own read gap under 2 (never 2+ over the market)", lambda r: F.gap(r) is not None and F.gap(r) < 2),
        ("floor: no NFL +100..+150", lambda r: not (r["league"] == "nfl" and r["odds"] <= 150)),
):
    F.floor_ok = (lambda fn: lambda r: orig_floor_ok(r) and fn(r))(fn)
    pb = run(label)
    if label.startswith("floor: no NBA, no college football, thin"):
        F.floor_table(pb, label)
F.floor_ok = orig_floor_ok
