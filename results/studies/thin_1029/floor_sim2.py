"""10/29 (night) THIN EDGES - the floor / thin-Dog variants on the 10/30 funnel rows (today's code: the hot hockey dog weight,
the 2-point fallback hockey Dog rule, the no-thin-Lock rule, the NBA favorite play). Every variant keeps the owner's
"at least ONE unit play a day". Usage: python floor_sim2.py "f*.jsonl" [live.jsonl]"""
import glob
import json
import sys
from collections import defaultdict

rows = []
for q in sorted(glob.glob(sys.argv[1])):
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost", "push")]
UNIT_KINDS = ("lock", "dog", "solo", "play", "dogplay", "nbafav")
HELD_FROM = "2025-07-01"                                      # 2023-24 / 2024-25 train, 2025-26 / 2026-27 held out


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def pnl(r, u):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def own_p(r):
    return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]


def gap(r):
    """The own read over the no-vig market, in points (None without a read / market)."""
    o = own_p(r)
    return None if o is None or r.get("p_market") is None else 100 * (o - r["p_market"])


def clean(r):
    n = r.get("n_reasons2")
    if n is None:
        n = r["n_reasons"]
    return n > 0 and not r["trap"] and not r["fighting"] and not r.get("waiting")


def floor_ok(r):
    return 100 <= r["odds"] <= 350 and clean(r) and r.get("dog_score") is not None


def play_bar(r):
    """plays(): good, lock / value tier, never past -150, not fighting / a trap, real value, the own read over the price,
    favorites only."""
    return r["good"] and r["tier"] in ("lock", "value") and -150 <= r["odds"] < 100 and not r["fighting"] \
        and not r["trap"] and r["real_value"] and r["own_beats"]


by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)
days = sorted(by_day)
GAMES = lambda r: frozenset((r["team"], r["opp"]))     # noqa: E731

BASE = {"floor_min": 2, "rank": "score", "floor_gap_min": None, "thin_dog": "keep", "excl": (), "floor_leagues": None,
        "nba_floor": True, "floor_score_min": None, "dog_gap_min": None}


def build(d, cfg):
    """One day's unit plays under a rule set -> [(row, units, kind)]."""
    out = []
    taken = set()
    for r in by_day[d]:
        k = r["kind"]
        if k not in UNIT_KINDS:
            continue
        u = r.get("units") or 0
        if k == "lock" and r.get("thin"):                         # 10/29: no thin Lock - it rides as a ½u play when the bar clears
            if play_bar(r):
                k, u = "play", 0.5
            else:
                continue
        if k == "dog":
            if cfg["thin_dog"] == "drop" and r.get("thin"):
                continue                                      # (e) the thin Dog is no Dog at all - the floor fills
            if cfg["thin_dog"] == "play" and r.get("thin"):
                k, u = "play", 0.5                            # (e') the thin Dog is a ½u value play, not the Dog
            if cfg["dog_gap_min"] is not None and r.get("thin") and (gap(r) is None or gap(r) < cfg["dog_gap_min"]):
                continue
        if not u:
            continue
        out.append((r, u, k))
        taken.add(GAMES(r))
    have = len(out)
    # 🏀 the NBA floor: an NBA day with no NBA unit play gets the best clean NBA dog by score at 0+
    if cfg["nba_floor"] and any(r["league"] == "nba" for r in by_day[d]) and not any(r["league"] == "nba" for r, _, _ in out):
        pool = [r for r in by_day[d] if r["league"] == "nba" and floor_ok(r) and r["dog_score"] >= 0 and GAMES(r) not in taken]
        pool.sort(key=lambda r: (-r["dog_score"], -r["edge"]))
        if pool:
            out.append((pool[0], 0.5, "nbafloor"))
            taken.add(GAMES(pool[0]))
            have += 1
    # 💰 the daily floor
    n = cfg["floor_min"]
    if have < n:
        pool = [r for r in by_day[d] if floor_ok(r) and GAMES(r) not in taken]
        if cfg["floor_gap_min"] is not None:
            pool = [r for r in pool if gap(r) is not None and gap(r) >= cfg["floor_gap_min"]]
        if cfg["floor_score_min"] is not None:
            pool = [r for r in pool if r["dog_score"] >= cfg["floor_score_min"]]
        if cfg["floor_leagues"]:
            pool = [r for r in pool if r["league"] in cfg["floor_leagues"]]
        for lg, lo, hi in cfg["excl"]:
            pool = [r for r in pool if not (r["league"] == lg and lo <= r["odds"] <= hi)]
        if cfg["rank"] == "score":
            key = lambda r: (-r["dog_score"], -r["edge"])                                   # noqa: E731
        elif cfg["rank"] == "gap":
            key = lambda r: (-(gap(r) if gap(r) is not None else -99), -r["dog_score"])     # noqa: E731
        elif cfg["rank"] == "score+gap":
            key = lambda r: (-(r["dog_score"] + (gap(r) if gap(r) is not None else 0)), -r["edge"])   # noqa: E731
        elif cfg["rank"] == "edge_own":
            key = lambda r: (-(r["edge_own"] if r.get("edge_own") is not None else -9), -r["dog_score"])   # noqa: E731
        elif cfg["rank"] == "score_then_gap":                 # score 3+ first by gap, then the rest by score
            key = lambda r: (-(1 if r["dog_score"] >= 3 else 0), -(gap(r) if gap(r) is not None else -99) if r["dog_score"] >= 3 else -r["dog_score"])   # noqa: E731
        pool.sort(key=key)
        full = list(pool)
        if cfg.get("floor_filter"):
            pool = [r for r in pool if cfg["floor_filter"](r)]
        for r in pool:
            if have >= n:
                break
            if GAMES(r) in taken:
                continue
            taken.add(GAMES(r))
            out.append((r, 0.5, "floor"))
            have += 1
        if cfg.get("fallback_min") and have < cfg["fallback_min"]:   # the owner's order: at least one unit play a day -
            for r in full:                                           # the filtered pool empty = the best dog by score anyway
                if have >= cfg["fallback_min"]:
                    break
                if GAMES(r) in taken:
                    continue
                taken.add(GAMES(r))
                out.append((r, 0.5, "floorfb"))
                have += 1
    return out


def stats(picks_by_day, label, show_kinds=False):
    """picks_by_day: {day: [(row, u, kind)]} -> one line (train / held out / all / live)."""
    def one(ds):
        ps = [(r, u, k) for d in ds for (r, u, k) in picks_by_day[d]]
        if not ds:
            return "n/a"
        w = sum(r["result"] == "won" for r, _, _ in ps)
        l = sum(r["result"] == "lost" for r, _, _ in ps)
        net = sum(pnl(r, u) for r, u, _ in ps)
        risk = sum(u for _, u, _ in ps)
        cum = peak = worst = 0.0
        for d in ds:
            cum += sum(pnl(r, u) for r, u, _ in picks_by_day[d])
            peak = max(peak, cum)
            worst = min(worst, cum - peak)
        with1 = sum(1 for d in ds if picks_by_day[d]) / len(ds)
        seas = defaultdict(float)
        for d in ds:
            seas[season(d)] += sum(pnl(r, u) for r, u, _ in picks_by_day[d])
        up = f"{sum(v > 0 for v in seas.values())}/{len(seas)}"
        return (f"{len(ps) / len(ds):.2f}/day {w}-{l} {net:+7.1f}u on {risk:.0f}u ROI {100 * net / risk if risk else 0:+5.1f}% "
                f"worst {worst:+6.1f}u ≥1 play {100 * with1:5.1f}% up {up}")
    tr = [d for d in days if d < HELD_FROM]
    he = [d for d in days if d >= HELD_FROM and d < "2026-10-13"]
    lv = [d for d in days if d >= "2026-10-13"]
    print(f"\n{label}")
    print(f"   train   {one(tr)}")
    print(f"   heldout {one(he)}")
    if lv:
        print(f"   live    {one(lv)}")
    print(f"   ALL     {one([d for d in days if d < '2026-10-13'])}")
    if show_kinds:
        byk = defaultdict(list)
        for d in days:
            for r, u, k in picks_by_day[d]:
                byk[k].append((r, u))
        for k, v in sorted(byk.items(), key=lambda x: -len(x[1])):
            w = sum(r["result"] == "won" for r, _ in v)
            l = sum(r["result"] == "lost" for r, _ in v)
            net = sum(pnl(r, u) for r, u in v)
            risk = sum(u for _, u in v)
            print(f"      {k:9s} {w}-{l} {net:+7.1f}u on {risk:.0f}u ROI {100 * net / risk if risk else 0:+5.1f}%")


def run(label, show_kinds=False, **kw):
    cfg = dict(BASE, **kw)
    pb = {d: build(d, cfg) for d in days}
    stats(pb, label, show_kinds)
    return pb


def floor_table(pb, label, kind="floor"):
    """The FLOOR plays alone (what the variants change), by sport / price band / gap band, train vs held out."""
    fl = [(d, r, u) for d in days for r, u, k in pb[d] if k == kind]
    print(f"\n   -- {label}: the {kind} plays alone, train | held out (flat ROI)")

    def st(rs):
        if not rs:
            return "n=0"
        w = sum(r["result"] == "won" for _, r, _ in rs)
        l = sum(r["result"] == "lost" for _, r, _ in rs)
        net = sum(pnl(r, 1) for _, r, _ in rs)
        return f"{w}-{l} {100 * net / len(rs):+5.1f}%"
    cells = {"all": lambda d, r: True}
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        cells[lg] = (lambda lg: lambda d, r: r["league"] == lg)(lg)
    for lo, hi in ((100, 150), (151, 199), (200, 350)):
        cells[f"+{lo}..+{hi}"] = (lambda lo, hi: lambda d, r: lo <= r["odds"] <= hi)(lo, hi)
    for lo, hi in ((-99, 0), (0, 2), (2, 99)):
        cells[f"gap {lo}..{hi}"] = (lambda lo, hi: lambda d, r: gap(r) is not None and lo <= gap(r) < hi)(lo, hi)
    cells["no gap"] = lambda d, r: gap(r) is None
    for lo, hi in ((-99, 0), (0, 3), (3, 6), (6, 99)):
        cells[f"score {lo}..{hi}"] = (lambda lo, hi: lambda d, r: r.get("dog_score") is not None and lo <= r["dog_score"] < hi)(lo, hi)
    cells["thin"] = lambda d, r: r.get("thin")
    cells["real"] = lambda d, r: not r.get("thin")
    for lg in ("nhl", "nfl", "ncaaf", "nba"):
        for lo, hi in ((100, 150), (151, 350)):
            cells[f"{lg} +{lo}..+{hi}"] = (lambda lg, lo, hi: lambda d, r: r["league"] == lg and lo <= r["odds"] <= hi)(lg, lo, hi)
        for lo, hi in ((-99, 0), (0, 2), (2, 99)):
            cells[f"{lg} gap {lo}..{hi}"] = (lambda lg, lo, hi: lambda d, r: r["league"] == lg and gap(r) is not None and lo <= gap(r) < hi)(lg, lo, hi)
    for name, fn in cells.items():
        tr = [x for x in fl if x[0] < HELD_FROM and fn(x[0], x[1])]
        he = [x for x in fl if HELD_FROM <= x[0] < "2026-10-13" and fn(x[0], x[1])]
        lv = [x for x in fl if x[0] >= "2026-10-13" and fn(x[0], x[1])]
        print(f"      {name:22s} train {st(tr):22s} | held {st(he):22s} | live {st(lv)}")


if __name__ == "__main__":
    print(f"{len(days)} board days {days[0]} -> {days[-1]}, {len(rows)} sides")
    base = run("TODAY'S RULES: floor to 2 by dog score, thin Dog kept (½u), NBA floor", show_kinds=True)
    floor_table(base, "today")
    floor_table(base, "today", kind="dog")
    floor_table(base, "today", kind="lock")
    floor_table(base, "today", kind="play")
    run("(a) floor to 1", floor_min=1)
    run("(a) floor to 3", floor_min=3)
    run("(b) floor needs the own read at/over the no-vig market (gap 0+)", floor_gap_min=0)
    run("(b) floor needs the own read 1+ over the no-vig market", floor_gap_min=1)
    run("(b) floor needs the own read 2+ over the no-vig market", floor_gap_min=2)
    run("(b) floor to 1, gap 0+", floor_min=1, floor_gap_min=0)
    run("(c) floor: no hockey +151..+350", excl=(("nhl", 151, 350),))
    run("(c) floor: no dog past +199 in any sport", excl=tuple((lg, 200, 350) for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb")))
    run("(c) floor: no dog past +150 in any sport", excl=tuple((lg, 151, 350) for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb")))
    run("(c) floor: no NFL", excl=(("nfl", 100, 350),))
    run("(c) floor: no college football", excl=(("ncaaf", 100, 350),))
    run("(c) floor: no college hoops", excl=(("ncaab", 100, 350),))
    run("(c) floor: no MLB", excl=(("mlb", 100, 350),))
    run("(c) floor: hockey + NBA only", floor_leagues=("nhl", "nba"))
    run("(c) floor: score 3+ only", floor_score_min=3)
    run("(c) floor: score 0+ only", floor_score_min=0)
    run("(d) floor ranked by own-read gap", rank="gap")
    run("(d) floor ranked by dog score + gap", rank="score+gap")
    run("(d) floor ranked by edge_own", rank="edge_own")
    run("(d) floor: score 3+ by gap, then by score", rank="score_then_gap")
    run("(e) the thin Dog is no Dog (the floor fills)", thin_dog="drop", show_kinds=True)
    run("(e) the thin Dog needs its own read 2+ over the no-vig market, else no Dog", dog_gap_min=2, show_kinds=True)
    run("(e) the thin Dog needs its own read 1+ over the no-vig market, else no Dog", dog_gap_min=1)
    run("(e) + (a): thin Dog dropped, floor to 1", thin_dog="drop", floor_min=1)
    run("(e) + (b): thin Dog dropped, floor gap 0+", thin_dog="drop", floor_gap_min=0)
    run("(c)+(c): floor no hockey +151..+350, no dog past +199", excl=(("nhl", 151, 350),) + tuple((lg, 200, 350) for lg in ("nba", "nfl", "ncaaf", "ncaab", "mlb")))
