"""11/4 - THE ENGINE'S BEST PICK (the owner: "a PICK OF THE DAY ... the best play the engine has for today, and it will
always be sized at least one full unit"): a LABEL on one of the day's unit plays (the (c15) board - the floor v2 + the NBA
floor + the hockey named-reason fix, college hoops out of the general floor), raised to 1u at least. Which ranking picks
the best one? Chosen on train (2023-25), reported held out (2025-27). Plus the forced 1u side on a day with no unit play."""
import sys
from collections import defaultdict

sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/vol")
import sim_volume as sv   # noqa: E402

BOARD = dict(floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))
plays_by_day = {d: sv.build(d, **BOARD) for d in sv.days}
KIND_RANK = {"lock": 0, "dog": 1, "nbafav": 2, "dogplay": 3, "nbafloor": 4, "floor": 5, "play": 6, "backup": 7, "floorfb": 8, "solo": 9}


def read_edge(r, k):
    """The edge of the read the play's units ride on, per dollar."""
    if k in ("dog", "dogplay", "nbafloor", "floor", "floorfb") and r.get("dog_score") is not None and r.get("p_market") is not None:
        return min(0.95, r["p_market"] + r["dog_score"] / 100) * r["dec"] - 1
    if r.get("w_p") is not None:
        return r["w_p"] * r["dec"] - 1
    return (r.get("edge_own") if r.get("edge_own") is not None else r["edge"])


def own_edge(r):
    return r.get("edge_own") if r.get("edge_own") is not None else -9


RANKS = {
    "R1 kind trust (Lock > Dog > NBA fav > runner-up > NBA floor > floor > play), then units, then edge":
        lambda r, u, k: (KIND_RANK.get(k, 9), -u, -read_edge(r, k)),
    "R2 the biggest edge on the read its units ride on":
        lambda r, u, k: (-read_edge(r, k),),
    "R3 the most units, then the biggest read edge":
        lambda r, u, k: (-u, -read_edge(r, k)),
    "R4 the surest (rank_p / win %), then edge":
        lambda r, u, k: (-(r.get("rank_p") or r["p"]), -read_edge(r, k)),
    "R5 both reads over the price first (own + weighed), then the kind trust":
        lambda r, u, k: (0 if (own_edge(r) > 0 and read_edge(r, k) > 0) else 1, KIND_RANK.get(k, 9), -u, -read_edge(r, k)),
    "R6 the kind trust by TRAIN ROI (Dog > NBA fav > runner-up > NBA floor > floor > Lock > play), then units":
        lambda r, u, k: ({"dog": 0, "nbafav": 1, "dogplay": 2, "nbafloor": 3, "floor": 4, "lock": 5, "play": 6}.get(k, 9), -u, -read_edge(r, k)),
    "R7 the Dog first (own read over the price), then the Lock, then the kind trust":
        lambda r, u, k: (0 if k == "dog" and own_edge(r) > 0 else 1, KIND_RANK.get(k, 9), -u, -read_edge(r, k)),
}


def forced_pool(d):
    return [r for r in sv.by_day[d] if -150 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"] and not r.get("waiting")]


FORCED = {
    "F1 the surest side (rank_p) not fighting its price":
        lambda rs: max(rs, key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"])),
    "F2 the biggest edge on the weighed read (p x price)":
        lambda rs: max(rs, key=lambda r: (r["p"] * r["dec"] - 1, r["p"])),
    "F3 the best dog by dog score (clean, own read ok), else the surest":
        lambda rs: (max([r for r in rs if r["odds"] >= 100 and r.get("dog_score") is not None and r["dog_own_ok"] and sv.clean(r)],
                        key=lambda r: (r["dog_score"], r["edge"]), default=None)
                    or max(rs, key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"]))),
    "F4 the surest favorite -150..-101 with a named reason (good), else the surest":
        lambda rs: (max([r for r in rs if r["odds"] < 100 and r["good"]], key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"]), default=None)
                    or max(rs, key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"]))),
}


def report(name, picks):
    """picks: [(d, r, u)]"""
    st = defaultdict(lambda: [0, 0, 0.0, 0.0, 0])
    seas = defaultdict(float)
    for d, r, u in picks:
        h = sv.half(d)
        s = st[h]
        s[0] += r["result"] == "won"
        s[1] += r["result"] == "lost"
        s[2] += sv.pnl(r, u)
        s[3] += u
        s[4] += 1
        if h != "live":
            seas[sv.season(d)] += sv.pnl(r, u)
    line = []
    for h in ("train", "held", "live"):
        w, l, net, risk, n = st[h]
        line.append(f"{h} {w}-{l} {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}%")
    w = st["train"][0] + st["held"][0]
    l = st["train"][1] + st["held"][1]
    net = st["train"][2] + st["held"][2]
    risk = st["train"][3] + st["held"][3]
    print(f"  {name:95} | " + " | ".join(line) + f" | ALL {w}-{l} {net:+6.1f}u {100 * net / risk if risk else 0:+5.1f}% up {sum(v > 0 for v in seas.values())}/{len(seas)}")


print(f"board days {len(sv.days)}; days with a unit play {sum(1 for d in sv.days if plays_by_day[d])}")
print("\n== THE BEST PICK among the day's unit plays, raised to 1u at least (its own record, counted once at the raised size)")
for name, key in RANKS.items():
    picks = []
    kinds = defaultdict(int)
    for d in sv.days:
        ps = plays_by_day[d]
        if not ps:
            continue
        r, u, k = min(ps, key=lambda x: key(x[0], x[1], x[2]))
        picks.append((d, r, max(1.0, u)))
        kinds[k] += 1
    report(name, picks)
    print("        kinds picked:", dict(sorted(kinds.items(), key=lambda kv: -kv[1])))
print("\n  -- the same, flat 1u on the best pick (the raise alone: ½u plays -> 1u)")
for name, key in RANKS.items():
    picks = []
    for d in sv.days:
        ps = plays_by_day[d]
        if not ps:
            continue
        r, u, k = min(ps, key=lambda x: key(x[0], x[1], x[2]))
        picks.append((d, r, 1.0))
    report(name, picks)
print("\n  -- the EXTRA units the raise adds (only the plays raised from ½u to 1u, the extra ½u)")
for name, key in RANKS.items():
    picks = []
    for d in sv.days:
        ps = plays_by_day[d]
        if not ps:
            continue
        r, u, k = min(ps, key=lambda x: key(x[0], x[1], x[2]))
        if u < 1.0:
            picks.append((d, r, 1.0 - u))
    report(name, picks)

print("\n== THE FORCED 1u SIDE on days with NO unit play (reported apart - the owner asked for a pick every day)")
empty = [d for d in sv.days if not plays_by_day[d] and forced_pool(d)]
print(f"  days with no unit play: {sum(1 for d in sv.days if not plays_by_day[d])} of {len(sv.days)} ({len(empty)} with a side to pick)")
for name, fn in FORCED.items():
    picks = []
    for d in empty:
        r = fn(forced_pool(d))
        if r:
            picks.append((d, r, 1.0))
    report(name, picks)

print("\n== THE LOCK's -119..-101 band (full test, not thin) by league - the 10/23 plan's cut")
for lg in ("nhl", "nba", "mlb", "nfl", "ncaaf", "ncaab"):
    rs = [r for r in sv.rows if -119 <= r["odds"] <= -101 and not r["trap"] and not r.get("waiting") and r["good"] and r["lock_ok"]
          and not r["fighting"] and r["own_agrees"] and r["real_value"] and not r["nhl_pricey"] and not r.get("thin") and r["league"] == lg]
    report(f"  {lg}", [(r["date"], r, 1.0) for r in rs])
