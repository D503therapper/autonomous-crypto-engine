"""10/30 SIZING - the board's unit plays, re-built from the 10/30 funnel rows (results/studies/thin_1029/funnel_replay.py on
today's code: 1,097 board days 2023-10-01 -> 2026-10-12 + the live stretch 10/13-10/29, closing prices, params re-tuned
each July, no injury reports) with TODAY'S board rules (floor v2 = 'C': no NBA / college football in the general floor,
thin only, one-a-day fallback; no thin Lock - it rides as a ½u play when the play bar clears; the NBA floor).

Every unit play comes back as (day, row, kind, units_today) so sizing.py can try any size schedule on the same plays.
Kinds: lock / backup (the backup Lock) / dog (Dog of the Day) / play (value play) / dogplay (best runner-up dog) /
nbafav (the NBA favorite play) / nbafloor / floor / floorfb (the fallback floor) / solo.
FUNNEL = the folder with fA-fD.jsonl + fLive.jsonl (default: this session's scratchpad copy - 54 MB, not committed)."""
import glob
import json
import os
from collections import defaultdict

D = os.environ.get("FUNNEL", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030")
HELD_FROM = "2025-07-01"       # train 2023-24 / 2024-25, held out 2025-26 / 2026-27 (the 10/29 split)
LIVE_FROM = "2026-10-13"

rows = []
for q in sorted(glob.glob(D + "/f[A-D].jsonl")) + [D + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost", "push")]
by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)
days = sorted(by_day)
UNIT_KINDS = ("lock", "dog", "solo", "play", "dogplay", "nbafav")
GAMES = lambda r: frozenset((r["team"], r["opp"]))     # noqa: E731


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def half(d):
    return "live" if d >= LIVE_FROM else "held" if d >= HELD_FROM else "train"


def pnl(r, u):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def own_p(r):
    return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]


def gap(r):
    """The own read over the no-vig market, in points."""
    o = own_p(r)
    return None if o is None or r.get("p_market") is None else 100 * (o - r["p_market"])


def w_edge(r):
    """The weighed read (w_p) over the price, per dollar (None without one)."""
    return None if r.get("w_p") is None else r["w_p"] * r["dec"] - 1


def clean(r):
    n = r.get("n_reasons2")
    if n is None:
        n = r["n_reasons"]
    return n > 0 and not r["trap"] and not r["fighting"] and not r.get("waiting")


def floor_ok(r):
    return 100 <= r["odds"] <= 350 and clean(r) and r.get("dog_score") is not None


def play_bar(r):
    return r["good"] and r["tier"] in ("lock", "value") and -150 <= r["odds"] < 100 and not r["fighting"] \
        and not r["trap"] and r["real_value"] and r["own_beats"]


def floor_v2(r):
    return r["league"] not in ("nba", "ncaaf") and bool(r.get("thin"))


def build(d):
    out, taken = [], set()
    for r in by_day[d]:
        k = r["kind"]
        if k not in UNIT_KINDS:
            continue
        u = r.get("units") or 0
        if k == "lock" and r.get("thin"):
            if play_bar(r):
                k, u = "play", 0.5
            else:
                continue
        if k == "lock" and u == 0.5:
            k = "backup"
        if not u:
            continue
        out.append((r, u, k))
        taken.add(GAMES(r))
    have = len(out)
    if any(r["league"] == "nba" for r in by_day[d]) and not any(r["league"] == "nba" for r, _, _ in out):
        pool = [r for r in by_day[d] if r["league"] == "nba" and floor_ok(r) and r["dog_score"] >= 0 and GAMES(r) not in taken]
        pool.sort(key=lambda r: (-r["dog_score"], -r["edge"]))
        if pool:
            out.append((pool[0], 0.5, "nbafloor"))
            taken.add(GAMES(pool[0]))
            have += 1
    if have < 2:
        pool = sorted([r for r in by_day[d] if floor_ok(r) and GAMES(r) not in taken], key=lambda r: (-r["dog_score"], -r["edge"]))
        for r in [r for r in pool if floor_v2(r)]:
            if have >= 2:
                break
            if GAMES(r) in taken:
                continue
            taken.add(GAMES(r))
            out.append((r, 0.5, "floor"))
            have += 1
        if have < 1:
            for r in pool:
                if have >= 1:
                    break
                if GAMES(r) in taken:
                    continue
                taken.add(GAMES(r))
                out.append((r, 0.5, "floorfb"))
                have += 1
    return [(d, r, k, u) for r, u, k in out]


PLAYS = [p for d in days for p in build(d)]
