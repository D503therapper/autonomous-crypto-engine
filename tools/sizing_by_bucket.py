"""THE 10/16 SIZING AUDIT: our unit plays by their SIZE on the 10/9 board replay (results/value_play_replay_2023_26.jsonl -
every board day 2023-01..2026-09 at the closing price, model params blind per season), re-sized under TODAY's unit rules
(sports.units_for: the Lock by its own read ½u-10u, the Dog 1u-2u by edge / NHL 1u / hoops ½u, every value play ½u).
Answers "why does the 1-2u bucket lose live?" - by bucket, by kind, by sport, and the Dog / Lock sizing alternatives.
Usage: python tools/sizing_by_bucket.py [replay.jsonl]      Flat 1u ROI = does the SIZE tell us anything at all."""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports                   # noqa: E402

TEST_FROM = "2025-01-01"        # graded blind from here (the 10/9 split: rules chosen on 2023-24)


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def pnl1(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def leg(r):
    return {k: r[k] for k in ("team", "odds", "dec", "p", "edge_own", "dog_p", "w_p", "league", "market", "p_market") if k in r}


def units(r, dog_rule="edge"):
    """What today's engine would put on a replay row: the Lock by its own read (a backup Lock ½u), the Dog by the rule
    named (edge = today's 1u-2u / NHL 1u / hoops ½u; flat = 1u / hoops ½u; half; two), a value play ½u."""
    l = leg(r)
    if r["kind"] == "lock":
        if not r.get("lock_ok", True):
            l["near_price"] = True
        return sports.units_for({"kind": "lock", "date": sports.DOG_SIZED_FROM, "legs": [l]})
    if r["kind"] == "dog":
        if dog_rule == "flat":
            return sports.DOG_UNITS_BY.get(r["league"], sports.DOG_UNITS)
        if dog_rule == "half":
            return 0.5
        if dog_rule == "two":
            return 2.0 if r["league"] not in ("nba", "ncaab") else 0.5
        return sports.units_for({"kind": "dog", "date": sports.DOG_SIZED_FROM, "legs": [l]})
    return sports.PLAY_UNITS


def bucket(u):
    return "2u+" if u >= 2 else "1-2u" if u >= 1 else "<1u"


def stat(rs, us=None):
    us = us or [1.0] * len(rs)
    w = sum(r["result"] == "won" for r in rs)
    lo = sum(r["result"] == "lost" for r in rs)
    net = sum(pnl1(r) * u for r, u in zip(rs, us))
    risk = sum(us)
    seas = defaultdict(float)
    for r, u in zip(rs, us):
        seas[season(r["date"])] += pnl1(r) * u
    up = sum(v > 0 for v in seas.values())
    return f"{w}-{lo} on {len(rs):4d}  {net:+7.1f}u / {risk:6.1f}u  ROI {net / risk * 100 if risk else 0:+6.1f}%  {up}/{len(seas)} seasons up"


def split(label, rs, us=None):
    us = us or [1.0] * len(rs)
    tr = [(r, u) for r, u in zip(rs, us) if r["date"] < TEST_FROM]
    te = [(r, u) for r, u in zip(rs, us) if r["date"] >= TEST_FROM]
    print(f"  {label:44s} ALL   {stat(rs, us)}")
    print(f"  {'':44s} 23-24 {stat([r for r, _ in tr], [u for _, u in tr])}")
    print(f"  {'':44s} BLIND {stat([r for r, _ in te], [u for _, u in te])}")


def own_edge(r):
    if r.get("w_p") is not None:
        return r["w_p"] * r["dec"] - 1
    return r["edge_own"] if r.get("edge_own") is not None else r["p"] * r["dec"] - 1


def main(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    rows = [r for r in rows if r["result"] in ("won", "lost", "push") and r["kind"] in ("lock", "dog", "play")]
    us = [units(r) for r in rows]
    print("##### TODAY'S SIZING by bucket (at its size, then the same bets flat 1u)")
    by = defaultdict(list)
    for r, u in zip(rows, us):
        by[bucket(u)].append((r, u))
    for b in ("<1u", "1-2u", "2u+"):
        rs = by[b]
        print(f"\n== {b}")
        split("at size", [r for r, _ in rs], [u for _, u in rs])
        split("flat 1u", [r for r, _ in rs])
        for k in ("lock", "dog", "play"):
            sub = [(r, u) for r, u in rs if r["kind"] == k]
            if sub:
                split(f"  {k} at size", [r for r, _ in sub], [u for _, u in sub])
        if b == "1-2u":
            for lg in sorted({r["league"] for r, _ in rs}):
                sub = [(r, u) for r, u in rs if r["league"] == lg]
                if len(sub) >= 10:
                    split(f"  sport {lg} at size", [r for r, _ in sub], [u for _, u in sub])
    dogs = [r for r in rows if r["kind"] == "dog"]
    locks = [r for r in rows if r["kind"] == "lock"]
    plays = [r for r in rows if r["kind"] == "play"]
    print("\n##### THE DOG OF THE DAY: sizing rules on the same dogs")
    for rule in ("flat", "edge", "half", "two"):
        split(f"dog rule {rule}", dogs, [units(r, rule) for r in dogs])
    print("\n-- the Dog's OWN read vs the price (fighting() allows 3 points under)")
    below = [r for r in dogs if (r["edge_own"] or 0) < 0]
    above = [r for r in dogs if (r["edge_own"] or 0) >= 0]
    split("own read below the price", below)
    split("own read beats the price", above)
    for lg in ("nhl", "ncaab", "ncaaf"):
        split(f"  {lg} own below", [r for r in below if r["league"] == lg])
        split(f"  {lg} own beats", [r for r in above if r["league"] == lg])
    split("own-below Dogs at ½u, rest today", dogs, [0.5 if (r["edge_own"] or 0) < 0 else units(r) for r in dogs])
    split("own-below Dogs dropped, rest flat 1u", dogs, [0.0 if (r["edge_own"] or 0) < 0 else units(r, "flat") for r in dogs])
    print("\n-- dogs by dog score / price, flat 1u")
    for lo, hi in ((0, 4), (4, 6), (6, 8), (8, 12), (12, 99)):
        sub = [r for r in dogs if lo <= (r["dog_score"] or 0) < hi]
        if sub:
            split(f"dog score {lo}-{hi}", sub)
    for lo, hi in ((100, 120), (120, 150), (150, 200), (200, 301)):
        sub = [r for r in dogs if lo <= r["odds"] < hi]
        if sub:
            split(f"dog +{lo}..+{hi}", sub)
    print("\n##### THE LOCK: by its Kelly size, flat 1u (does a bigger own edge win more?)")
    lu = [units(r) for r in locks]
    for lo, hi in ((0.5, 1), (1, 2), (2, 3), (3, 5), (5, 11)):
        sub = [r for r, u in zip(locks, lu) if lo <= u < hi]
        if sub:
            split(f"lock sized {lo}-{hi}u, flat", sub)
    for lo, hi in ((-1, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 9)):
        sub = [r for r in locks if lo <= own_edge(r) < hi]
        if sub:
            split(f"lock own edge {lo}..{hi}, flat", sub)
    print("\n-- the Lock's sizing rules on the same Locks")
    split("today (Kelly ½u-10u)", locks, lu)
    split("flat 1u", locks)
    split("½u thin / 1u", locks, [0.5 if u <= 0.5 else 1.0 for u in lu])
    split("capped 2u", locks, [min(u, 2.0) for u in lu])
    print("\n-- own read vs how often the Lock won")
    for lo, hi in ((0.5, 0.56), (0.56, 0.6), (0.6, 0.65), (0.65, 0.7), (0.7, 1.0)):
        sub = [r for r in locks if lo <= (own_edge(r) + 1) / r["dec"] < hi]
        if sub:
            n = len([r for r in sub if r["result"] != "push"]) or 1
            print(f"  own read {lo:.2f}-{hi:.2f}: n={len(sub)} won {sum(r['result'] == 'won' for r in sub) / n * 100:.1f}%"
                  f"  the market said {sum(1 / r['dec'] for r in sub) / len(sub) * 100:.1f}%  {sum(pnl1(r) for r in sub):+.1f}u flat")
    print("\n##### THE WHOLE BOARD (plays ½u): units won, Lock rule x Dog rule")
    pu = sum(pnl1(r) * sports.PLAY_UNITS for r in plays)
    pub = sum(pnl1(r) * sports.PLAY_UNITS for r in plays if r["date"] >= TEST_FROM)
    for lname, lf in (("Lock Kelly (today)", lambda u: u), ("Lock flat 1u", lambda u: 1.0),
                      ("Lock ½u thin / 1u", lambda u: 0.5 if u <= 0.5 else 1.0), ("Lock capped 2u", lambda u: min(u, 2.0))):
        for dname, dr in (("Dog edge (today)", "edge"), ("Dog flat 1u", "flat")):
            du = [units(r, dr) for r in dogs]
            tot = sum(pnl1(r) * lf(u) for r, u in zip(locks, lu)) + sum(pnl1(r) * u for r, u in zip(dogs, du)) + pu
            bl = sum(pnl1(r) * lf(u) for r, u in zip(locks, lu) if r["date"] >= TEST_FROM) \
                + sum(pnl1(r) * u for r, u in zip(dogs, du) if r["date"] >= TEST_FROM) + pub
            risk = sum(lf(u) for u in lu) + sum(du) + sports.PLAY_UNITS * len(plays)
            print(f"  {lname:20s} + {dname:16s}: ALL {tot:+7.1f}u on {risk:.0f}u ({tot / risk * 100:+.1f}%)   BLIND {bl:+6.1f}u")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results",
                                                             "value_play_replay_2023_26.jsonl"))
