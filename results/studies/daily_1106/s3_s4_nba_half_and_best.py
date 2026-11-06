"""S3 - THE NBA ½u DOGS (0-6 live, z -2.05 on 11/5): what the six live losers share vs the replay's NBA ½u dogs.
S4 - THE ⭐ BEST PICK (0-2 live: the Suns +125 Dog 11/4, the forced Stars -130 11/5): the FORCED ⭐ (a day with no unit
play - the surest side, read beats price, 1u) vs the ⭐ on an existing play, in the replay.
The replay: the 10/30 funnel rows (1,097 board days 2023-10 -> 2026-10-12 + the live stretch 10/13-10/29, closing
prices, no injury reports) through the 11/4 sim_volume board ((c15): the floor v2 + the NBA floor + the hockey named
reason), the scratchpad copy results/studies/plays_every_day_1104/bestpick.py used. Train = to 2025-06-30, held =
2025-07-01 on, live apart. Read only; nothing here changes the engine."""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/vol")
import sim_volume as sv  # noqa: E402

BOARD = dict(floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))
plays = {d: sv.build(d, **BOARD) for d in sv.days}
out = []


def line(name, picks):
    """picks: [(d, r, u)] -> W-L, units, ROI by train / held / live, seasons up."""
    st = defaultdict(lambda: [0, 0, 0.0, 0.0])
    seas = defaultdict(float)
    for d, r, u in picks:
        h = sv.half(d)
        s = st[h]
        s[0] += r["result"] == "won"
        s[1] += r["result"] == "lost"
        s[2] += sv.pnl(r, u)
        s[3] += u
        if h != "live":
            seas[sv.season(d)] += sv.pnl(r, u)
    parts = []
    for h in ("train", "held", "live"):
        w, l_, net, risk = st[h]
        parts.append(f"{h} {w}-{l_} {net:+6.1f}u {100 * net / risk if risk else 0:+6.1f}%")
    w = st["train"][0] + st["held"][0]
    l_ = st["train"][1] + st["held"][1]
    net = st["train"][2] + st["held"][2]
    risk = st["train"][3] + st["held"][3]
    s = f"  {name:70s} | " + " | ".join(parts) + f" | ALL {w}-{l_} {100 * net / risk if risk else 0:+6.1f}% up {sum(v > 0 for v in seas.values())}/{len(seas)}"
    print(s)
    out.append(s)


def say(x):
    print(x)
    out.append(x)


# ---------------- S3: the replay's NBA ½u dogs, cut the way the live six look
nba_half = [(d, r, u) for d in sv.days for r, u, k in plays[d] if r["league"] == "nba" and u == 0.5 and r["odds"] >= 100]
say("S3 - THE REPLAY'S NBA ½u DOGS (every kind: NBA floor / runner-up / ½u Dog / ½u play)")
line("all", nba_half)
for lo, hi in ((100, 129), (130, 159), (160, 199), (200, 350)):
    line(f"+{lo}..+{hi}", [x for x in nba_half if lo <= x[1]["odds"] <= hi])
line("home", [x for x in nba_half if x[1]["home"]])
line("road", [x for x in nba_half if not x[1]["home"]])
line("the own read UNDER the price (edge_own < 0)", [x for x in nba_half if (x[1].get("edge_own") or 0) < 0])
line("the own read over the price", [x for x in nba_half if (x[1].get("edge_own") or 0) >= 0])
line("weighed read under the market (p < p_market)", [x for x in nba_half if x[1]["p"] < (x[1].get("p_market") or 0)])
line("the WEIGHED read x price under 1 (p x dec - 1 < 0 - all six live losers)", [x for x in nba_half if x[1]["p"] * x[1]["dec"] < 1])
line("the weighed read x price 1+", [x for x in nba_half if x[1]["p"] * x[1]["dec"] >= 1])
line("+200..+350 AND the weighed read under the price", [x for x in nba_half if x[1]["odds"] >= 200 and x[1]["p"] * x[1]["dec"] < 1])
line("money moving TO the dog (drift > 0)", [x for x in nba_half if (x[1].get("drift") or 0) > 0])
line("money moving AWAY (drift < 0)", [x for x in nba_half if (x[1].get("drift") or 0) < 0])
line("money against flag", [x for x in nba_half if x[1].get("money_against")])
for lo, hi in ((0, 3), (3, 6), (6, 99)):
    line(f"dog score {lo}..{hi}", [x for x in nba_half if x[1].get("dog_score") is not None and lo <= x[1]["dog_score"] < hi])
line("no dog score (a ½u play / Dog by its read)", [x for x in nba_half if x[1].get("dog_score") is None])
line("season games 1-10 (October / early November)", [x for x in nba_half if (x[1].get("season_games") or 99) <= 10])
line("season games 11+", [x for x in nba_half if (x[1].get("season_games") or 0) > 10])

# ---------------- S4: the ⭐
say("")
say("S4 - THE ⭐ BEST PICK: on an existing play (R1 - the wired rank) vs FORCED (no unit play that day), 1u")
KIND_RANK = {"lock": 0, "dog": 1, "nbafav": 2, "dogplay": 3, "nbafloor": 4, "floor": 5, "play": 6, "backup": 7, "floorfb": 8, "solo": 9}


def read_edge(r, k):
    if k in ("dog", "dogplay", "nbafloor", "floor", "floorfb") and r.get("dog_score") is not None and r.get("p_market") is not None:
        return min(0.95, r["p_market"] + r["dog_score"] / 100) * r["dec"] - 1
    if r.get("w_p") is not None:
        return r["w_p"] * r["dec"] - 1
    return r.get("edge_own") if r.get("edge_own") is not None else r["edge"]


on_play, on_play_bp, forced, forced_bp, forced_thin, forced_real = [], [], [], [], [], []
for d in sv.days:
    ps = plays[d]
    if ps:
        r, u, k = min(ps, key=lambda x: (KIND_RANK.get(x[2], 9), -x[1], -read_edge(x[0], x[2])))
        on_play.append((d, r, 1.0))
        bp = [x for x in ps if x[0].get("beats_price")]
        if bp:
            r, u, k = min(bp, key=lambda x: (KIND_RANK.get(x[2], 9), -x[1], -read_edge(x[0], x[2])))
            on_play_bp.append((d, r, 1.0))
        continue
    pool = [r for r in sv.by_day[d] if -150 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"] and not r.get("waiting")]
    if not pool:
        continue
    r = max(pool, key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"]))
    forced.append((d, r, 1.0))
    pbp = [r for r in pool if r.get("beats_price")]
    if pbp:
        r = max(pbp, key=lambda r: ((r.get("rank_p") or r["p"]), r["edge"]))
        forced_bp.append((d, r, 1.0))
        e = r["p"] * r["dec"] - 1
        (forced_thin if e < 0.03 else forced_real).append((d, r, 1.0))
line("⭐ on a play (R1, any)", on_play)
line("⭐ on a play whose read beats its price (the 11/5 rule)", on_play_bp)
line("⭐ FORCED, the surest side (11/4 rule)", forced)
line("⭐ FORCED, the surest side whose read beats its price (the 11/5 rule)", forced_bp)
line("   ... of those, a THIN edge (weighed read x price under +3%)", forced_thin)
line("   ... of those, a real edge (+3%+)", forced_real)
line("   ... forced favorites", [x for x in forced_bp if x[1]["odds"] < 0])
line("   ... forced dogs", [x for x in forced_bp if x[1]["odds"] > 0])
say(f"  days: {len(sv.days)}; with a unit play {sum(1 for d in sv.days if plays[d])}; forced days {len(forced)} "
    f"({len(forced_bp)} with a side whose read beats its price)")
for d, r, u in forced_bp:
    say(f"    forced {d} {r['league']:5s} {r['team']:22s} {r['odds']:+5d} {r['result']:4s} p {r['p']:.3f} x{r['dec']:.2f} "
        f"edge {r['p'] * r['dec'] - 1:+.3f}")
open(os.path.join(HERE, "s3_s4_out.txt"), "w").write("\n".join(out) + "\n")
