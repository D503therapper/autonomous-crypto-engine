"""11/17 - THE MOST-MONEY STUDY - the shared rig.
THE BOARD (R3L): dogs_1117's R3 rows (funnel6.py - the board re-built on TODAY's code, every 2026 date gate open, every
board day 2023-10 -> 2026-11 at the closing price, the model re-tuned each July, no injury reports) turned into the board
the LIVE post makes of it:
  - a thin-edge Lock outside football is NOT a Lock live (post_board drops it, 10/29): it rides as a ½u value play when
    the value bar clears (own_beats + real_value + good), else it is not on the board;
  - today's sizes (11/17): the hockey Dog 2u short / ½u long, 3u on the 💎 b2b spot at a score of 8+; the college football
    Dog 2u short / 1u long; the NBA favorite play 1u; the college hoops dog slot 1u, 2u at a dog read of 5+; the gap play
    1u / 2u; everything else as units_for stamped it;
  - the ⭐: the day's best unit play by sports.BEST_KIND_RANK (bigger size, then bigger edge) whose read beats its price,
    never the NFL Lock - raised to 1u at least.
One row = one unit play: r["k"] the fine kind, r["u"] today's units (the ⭐ raise in), r["u0"] without the raise, r["star"].
Not on this board (no rows; each has its own study, quoted in the README): the college hoops spread stack play, the road
dog at a read of 3 (11/17), the totals (⛰️ / 🏀 over / 🌍 under), the ⏰ early spots, mid-day adds, baseball.
Train = to 2025-06-30, held out = 2025-07-01 -> 2026-10-12, live (10/13 on) apart. The dog score's weights were fit with
these seasons seen - only the model's params are blind; a "held out" half here is the later half, not a clean blind test.
"""
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "dogs_1117"))
import dlib as D  # noqa: E402

half, season, flat, worst = D.half, D.season, D.flat, D.worst
FB = ("nfl", "ncaaf")
RANK = {"lock": 0, "dog": 1, "nbafav": 2, "gap": 3, "dogplay": 3, "ncaabplay": 4, "nbafloor": 4, "solo": 5, "night": 5, "floor": 6, "play": 7}
LG = {"nhl": "hockey", "nba": "NBA", "nfl": "NFL", "ncaaf": "college football", "ncaab": "college hoops"}


def read_of(r):
    k = r["kind"]
    if k in ("dog", "dogplay") and r["odds"] >= 100 and r.get("dog_score") is not None:
        return min(0.95, (r["p_market"] if r.get("p_market") is not None else 1 / r["dec"]) + r["dog_score"] / 100)
    if r.get("w_p") is not None:
        return r["w_p"]
    if r.get("edge_own") is not None:
        return (r["edge_own"] + 1) / r["dec"]
    return r["p"]


def margin(r):
    return 100 * (read_of(r) - 1 / r["dec"])


def _live_shape(r):
    """-> (kind, fine kind, units) the way the live post would carry the row, or None (not on the live board)."""
    k, lg, o, u = r["kind"], r["league"], r["odds"], r.get("units") or 0.5
    sc = r.get("dog_score") if r.get("dog_score") is not None else -99
    x = r.get("x") or {}
    if k == "lock":
        if lg in FB:
            if lg == "nfl":
                return k, "Lock - NFL (½u)", 0.5
            return k, ("Lock - college football, thin (½u)" if u <= 0.5 else "Lock - college football, not thin (1u)"), u
        if u <= 0.5:                                     # a thin-edge Lock outside football: no Lock (10/29)
            if r.get("own_beats") and r.get("real_value") and r.get("good"):
                return "play", f"value play - {LG[lg]} favorite (½u)", 0.5
            return None
        return k, f"Lock - {LG[lg]}, not thin ({u:g}u)", u
    if k == "dog":
        if lg == "nhl":
            if x.get("rested_vs_b2b") and sc >= 8:
                return k, "Dog - hockey 💎 b2b spot 8+ (3u)", 3.0
            return (k, "Dog - hockey +100..+150 (2u)", 2.0) if o <= 150 else (k, "Dog - hockey +151..+350 (½u)", 0.5)
        if lg == "ncaaf":
            return (k, "Dog - college football +100..+150 (2u)", 2.0) if o <= 150 else (k, "Dog - college football +151..+350 (1u)", 1.0)
        if lg == "nfl":
            return (k, "Dog - NFL +100..+150 (2u)", 2.0) if o <= 150 else (k, "Dog - NFL +151..+350 (½u)", 0.5)
        return k, f"Dog - NBA ({u:g}u)", u
    if k == "dogplay":
        return k, f"runner-up dog - {LG[lg]} (½u)", 0.5
    if k == "floor":
        return k, f"floor - {LG[lg]} dog (½u)", 0.5
    if k == "nbafloor":
        return k, "NBA floor dog (½u)", 0.5
    if k == "nbafav":
        return k, "NBA favorite play (1u)", 1.0
    if k == "ncaabplay":
        if o < 0:
            return k, "college hoops favorite slot (½u)", 0.5
        return (k, "college hoops dog slot, read 5+ (2u)", 2.0) if (r.get("dog_read") or 0) >= 5 else (k, "college hoops dog slot, read 4 (1u)", 1.0)
    if k == "gap":
        return k, f"🔍 college hoops gap play ({u:g}u)", u
    if k == "play":
        return k, f"value play - {LG[lg]} favorite (½u)", 0.5
    return k, f"{k} - {LG[lg]} ({u:g}u)", u


_CACHE = {}


def board():
    """-> (plays, days): plays = the unit plays (dict rows with k / u / u0 / star), days = every board day on the rig."""
    if _CACHE:
        return _CACHE["p"], _CACHE["d"]
    R = D.r3()
    days = sorted({r["date"] for r in R})
    out = []
    for r in R:
        if not r.get("kind"):
            continue
        s = _live_shape(r)
        if not s:
            continue
        r["kind"], r["k"], r["u0"] = s
        r["u"], r["star"] = r["u0"], False
        out.append(r)
    by = defaultdict(list)
    for r in out:
        by[r["date"]].append(r)
    for d, ps in by.items():
        pool = [r for r in ps if -150 <= r["odds"] <= 350 and not r.get("fighting") and margin(r) > 0
                and not (r["kind"] == "lock" and r["league"] == "nfl")]
        if pool:
            b = min(pool, key=lambda r: (-1 if r["u0"] >= 3 else RANK.get(r["kind"], 9), -r["u0"], -margin(r)))
            b["star"] = True
            b["u"] = max(1.0, b["u0"])
    _CACHE["p"], _CACHE["d"] = out, days
    return out, days


def pnl(r, u):
    return u * flat(r)


def summ(plays, days=None, sizes=None):
    """plays = rows; sizes = fn(r) -> units (default r['u']). Train + held only for the headline; live apart.
    -> dict: net, risk, roi, w, l, dd (worst stretch), by half (net, risk, dd), seasons {s: net}, live (w, l, net), share
    of board days with a unit play (days given)."""
    sizes = sizes or (lambda r: r["u"])
    st = defaultdict(lambda: [0.0, 0.0, 0, 0])
    per = defaultdict(float)
    seas = defaultdict(float)
    hasplay = set()
    for r in plays:
        u = sizes(r)
        if not u:
            continue
        h = half(r["date"])
        p = pnl(r, u)
        s = st[h]
        s[0] += p
        s[1] += u
        s[2] += r["result"] == "won"
        s[3] += 1
        hasplay.add(r["date"])
        if h != "live":
            per[r["date"]] += p
            seas[season(r["date"])] += p
    net = st["train"][0] + st["held"][0]
    risk = st["train"][1] + st["held"][1]
    w = st["train"][2] + st["held"][2]
    n = st["train"][3] + st["held"][3]
    o = dict(net=net, risk=risk, roi=100 * net / risk if risk else 0.0, w=w, l=n - w, n=n, dd=worst(per), seas=dict(seas),
             up=sum(v > 0 for v in seas.values()), ns=len(seas),
             tr=st["train"][0], trr=st["train"][1], he=st["held"][0], her=st["held"][1],
             ddtr=worst({d: v for d, v in per.items() if half(d) == "train"}),
             ddhe=worst({d: v for d, v in per.items() if half(d) == "held"}),
             live=(st["live"][2], st["live"][3] - st["live"][2], st["live"][0], st["live"][1]))
    if days is not None:
        dd_ = [d for d in days if half(d) != "live"]
        o["dayshare"] = 100 * sum(d in hasplay for d in dd_) / len(dd_)
    return o


def roi(a, b):
    return 100 * a / b if b else 0.0


def line(name, o, base=None, w=46):
    s = (f"  {name:{w}s} {o['w']:4d}-{o['l']:<4d} {o['net']:+7.1f}u on {o['risk']:6.1f}u {o['roi']:+5.1f}% | train {o['tr']:+6.1f}u {roi(o['tr'], o['trr']):+5.1f}%"
         f" | held {o['he']:+6.1f}u {roi(o['he'], o['her']):+5.1f}% | worst {o['dd']:+6.1f}u | up {o['up']}/{o['ns']}"
         f" | u/worst {(-o['net'] / o['dd']) if o['dd'] else 0:4.1f}")
    if "dayshare" in o:
        s += f" | days {o['dayshare']:4.1f}%"
    lv = o["live"]
    s += f" | live {lv[0]}-{lv[1]} {lv[2]:+.1f}u"
    if base:
        s += f" | vs today {o['net'] - base['net']:+.1f}u, worst x{(o['dd'] / base['dd']) if base['dd'] else 0:.2f}"
    return s


def seas_str(o):
    return " ".join(f"{s} {v:+.1f}" for s, v in sorted(o["seas"].items()))


def shuffle_placebo(plays, sizes, group=lambda r: r["kind"], draws=2000, seed=1117, halves=("train", "held")):
    """THE PLACEBO: the plan's sizes dealt at random to the plays of the same group (kind) - how many of `draws` deals win
    as many units as the plan (train + held)."""
    rs = [r for r in plays if half(r["date"]) in halves]
    mine = sum(pnl(r, sizes(r)) for r in rs)
    by = defaultdict(list)
    for r in rs:
        by[group(r)].append(r)
    rnd = random.Random(seed)
    hit = 0
    packs = [([flat(r) for r in g], [sizes(r) for r in g]) for g in by.values()]
    for _ in range(draws):
        tot = 0.0
        for fl, sz in packs:
            s2 = sz[:]
            rnd.shuffle(s2)
            tot += sum(a * b for a, b in zip(fl, s2))
        hit += tot >= mine
    return hit
