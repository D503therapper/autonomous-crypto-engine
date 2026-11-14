"""11/14 COLLEGE HOOPS PROFIT STUDIES - shared helpers (read-only on the repo).
ROWS: the replay board on today's code (funnel5.py rows in ~/.cache/d503_cbb1114/rows when the run is done; the 11/13
funnel4 rows - the same college hoops paths, no slot ranks - before that), joined by game id to the totals table
(tlib.py: the conference game flag, rest days, the visitor's trip, the meeting number - all known before the tip).
THE UNIT PLAYS a row can be (one bet a side; units as the board sizes them):
  gap    the 🔍 college hoops gap play (every one a night)            1u, 2u at a dog read of 6+
  dog    the dog slot (the best 2 dog reads a night; may share the gap play's dog - both count)   1u, 2u at 6+
  fav    the favorite slot (one a night)                                ½u
  stack  the ½u spread stack play (the 2 biggest stacks a night)        ½u
  lock   a college hoops Lock                                           2u (1u when the own read is 7+ over the market)
TRAIN = seasons 2018-22, HELD OUT = 2023-26. Every bet at ESPN's close at its own juice; a push returns 0."""
import glob, json, math, os, pickle, random, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tlib  # noqa: E402

NEW = os.path.join(os.path.expanduser("~"), ".cache", "d503_cbb1114", "rows")
OLD = os.path.join(os.path.expanduser("~"), ".cache", "d503_leans1113", "rows")
KEEP = ("date", "gid", "side", "market", "line", "team", "opp", "home", "neutral", "odds", "dec", "p", "p_market",
        "edge_own", "w_p", "games_in", "opp_games_in", "trap", "fighting", "stack", "stack_n", "kind", "dog_score",
        "dog_read", "dog_read_parts", "slot_i", "fav_slot", "stack_i", "gap_i", "eff_p", "dog_fade", "fav_fade",
        "result", "lean", "lean_new", "lean_any_new", "sw", "start", "reasons", "spread_home", "hs", "as")
random.seed(1114)
CELLS = [0]


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def load(src=None, markets=("ml", "spread"), keep_all=False):
    """The replay rows (graded, regular season), compact, + game features. src None = the new rows if done."""
    src = src or (NEW if os.path.exists(os.path.join(NEW, "DONE")) else OLD)
    G = {r["id"]: r for r in tlib.build()}
    R = []
    for f in sorted(glob.glob(os.path.join(src, "s20*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if r.get("result") not in ("won", "lost", "push") or r["market"] not in markets:
                continue
            if not keep_all and not (r.get("kind") or r.get("slot_i") is not None or r.get("fav_slot") is not None
                                     or r.get("gap_i") is not None or r.get("stack_i") is not None
                                     or (r["market"] == "ml" and (r.get("dog_read") or -99) >= 2)
                                     or (r["market"] == "ml" and -150 <= r["odds"] <= -101)
                                     or (r["market"] == "spread" and (r.get("stack") or 0) >= 0.03)):
                continue
            x = {k: r.get(k) for k in KEEP}
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            x["season"] = y if m >= 7 else y - 1
            x["month"] = r["date"][5:7]
            x["win"] = r["result"] == "won"
            x["pnl"] = 0.0 if r["result"] == "push" else ((r["dec"] - 1) if x["win"] else -1.0)
            x["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
            g = G.get(r["gid"]) or {}
            x["neu"] = bool(g.get("neu")) if g else str(r.get("neutral")) == "1"
            x["where"] = "neutral" if x["neu"] else ("home" if r.get("home") else "road")
            x["conf"] = g.get("conf")
            me, op = ("h", "a") if r["side"] == "home" else ("a", "h")
            x["rest"], x["orest"] = g.get("r" + me), g.get("r" + op)
            x["tz_trip"] = g.get("tz_trip")
            x["meet_n"] = g.get("meet_n")
            x["pow"], x["opow"] = g.get("pow_" + me), g.get("pow_" + op)
            R.append(x)
    return R


def plays(R, new=None):
    """{kind: [rows]} - the unit plays on the replay board, each row with 'u' (its units)."""
    new = any(r.get("slot_i") is not None for r in R) if new is None else new
    out = defaultdict(list)
    for r in R:
        if r["market"] == "ml" and r["kind"] == "gap":
            out["gap"].append(dict(r, u=2.0 if (r.get("dog_read") or 0) >= 6 else 1.0))
        dog = (r.get("slot_i") is not None and r["slot_i"] < 2 and r["kind"] in ("gap", "ncaabplay")) if new else \
              (r["kind"] == "ncaabplay" and r["odds"] > 0)
        if dog:
            out["dog"].append(dict(r, u=2.0 if (r.get("dog_read") or 0) >= 6 else 1.0))
        fav = (r.get("fav_slot") is not None and r["kind"] == "ncaabplay") if new else (r["kind"] == "ncaabplay" and r["odds"] < 0)
        if fav:
            out["fav"].append(dict(r, u=0.5))
        if r["kind"] == "stackplay":
            out["stack"].append(dict(r, u=0.5))
        if r["kind"] == "lock":
            out["lock"].append(dict(r, u=1.0 if (r.get("edge_own") is not None and r["p_market"] is not None
                                                 and r["p"] - r["p_market"] >= 0.07) else 2.0))
    return out


def placebo(rows, pool, n=2000, k="pnl"):
    if len(rows) < 30:
        return None
    by = defaultdict(list)
    for r in pool:
        by[r["season"]].append(r[k])
    need = defaultdict(int)
    for r in rows:
        need[r["season"]] += 1
    mine = sum(r[k] for r in rows)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for s, c in need.items():
            if by[s]:
                tot += sum(random.sample(by[s], c)) if c <= len(by[s]) else sum(random.choices(by[s], k=c))
        hit += tot >= mine
    return hit


def rec(name, rows, pool=None, min_n=15, units=False):
    """W-L, ROI flat at the close (and on its units), z, TRAIN 2018-22 / HELD 2023-26, seasons up, placebo."""
    if len(rows) < min_n:
        if rows:
            print(f"   {name:58s} only {len(rows)} ({sum(r['win'] for r in rows)}-{sum(not r['win'] and r['pnl'] < 0 for r in rows)}, "
                  f"{100 * sum(r['pnl'] for r in rows) / len(rows):+.1f}%)")
        return None
    CELLS[0] += 1
    w = sum(r["win"] for r in rows)
    l_ = sum(r["pnl"] < 0 for r in rows)
    m = sum(r["pnl"] for r in rows) / len(rows)
    sd = math.sqrt(sum((r["pnl"] - m) ** 2 for r in rows) / len(rows)) or 1
    z = m / (sd / math.sqrt(len(rows)))
    tr = [r for r in rows if r["season"] <= 2022]
    he = [r for r in rows if r["season"] >= 2023]
    f = lambda v: (100 * sum(r["pnl"] for r in v) / len(v)) if v else float("nan")
    by = defaultdict(list)
    for r in rows:
        by[r["season"]].append(r["pnl"])
    up = sum(sum(v) > 0 for v in by.values())
    pb = placebo(rows, pool) if pool is not None and len(rows) >= 30 else None
    us = ""
    if units:
        risk = sum(r["u"] for r in rows)
        net = sum(r["u"] * r["pnl"] for r in rows)
        us = f" | {net:+.1f}u on {risk:.0f}u ({100 * net / risk:+.1f}%)"
    print(f"   {name:58s} {w:4d}-{l_:<4d} {100 * w / len(rows):4.1f}% ROI {100 * m:+6.1f}% z {z:+4.1f} | train {f(tr):+6.1f}% n{len(tr):<4d}"
          f"| held {f(he):+6.1f}% n{len(he):<4d}| up {up}/{len(by)}" + us + (f" | placebo {pb}/2000" if pb is not None else "")
          + " | " + " ".join(f"{s % 100}:{100 * sum(v) / len(v):+.0f}" for s, v in sorted(by.items())))
    return {"n": len(rows), "roi": m, "z": z, "tr": f(tr), "he": f(he), "up": up, "ns": len(by), "pb": pb}


def band(o):
    if o < 0:
        return "-150..-130" if o <= -130 else "-129..-101"
    return "+100..+150" if o <= 150 else "+151..+250" if o <= 250 else "+251..+350"
