"""STUDY 4 - CLOSING-LINE VALUE: what predicts beating the close at the time we post?
(A) OUR PICKS (data/sports/pick_journal.json - every pick with its posted price and the close): the points of win
    chance we beat the close by (+ = we got the better number), by sport, kind, side, price band, hours before the
    start, the move since the open at post, and whether beating the close went with winning.
(B) THE WHOLE SLATE (data/sports/line_history/2026-10 / -11.jsonl - every game's moneyline every hour or so, 10/1 on):
    for every side in a band we bet, its no-vig win chance the NIGHT BEFORE (~8 PM PT), at the 8 AM PT board, at
    noon PT, and at the CLOSE (the last look before the start). + = the market moved TO the side after that look
    (taking it then beat the close). This is the slate-wide answer to "post earlier or later?" - no pick selection in it.
Usage: python s4_clv.py > s4_clv.out"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

PT = sports.PT


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def T(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def ms(v):
    if not v:
        return "none"
    m = sum(v) / len(v)
    sd_ = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
    return f"{m:+.2f} pts (n {len(v)}, t {m / (sd_ / math.sqrt(len(v))) if sd_ else 0:+.1f}; beat {sum(x > 0 for x in v)} / same {sum(x == 0 for x in v)} / worse {sum(x < 0 for x in v)})"


# ------------------------------------------------------------------ (A) our picks
J = [p for p in json.load(open("data/sports/pick_journal.json")) if p.get("beat_close_pts") is not None and p.get("market") == "ml"]
picks = {(p["date"], (p.get("legs") or [{}])[0].get("team")): p for p in json.load(open("data/sports/picks.json"))}
print(f"(A) OUR MONEYLINE PICKS WITH A CLOSE ON FILE: {len(J)} ({sum(1 for p in J if not p['lean'])} unit plays, {sum(1 for p in J if p['lean'])} leans)")
for p in J:
    pk = picks.get((p["date"], p["team"])) or {}
    leg = (pk.get("legs") or [{}])[0]
    p["drift"] = leg.get("drift")
    p["public"] = leg.get("public")
    try:
        st = T(leg["start"])
        po = T(p["posted"])
        p["lead"] = (st - po).total_seconds() / 3600
        p["post_hr"] = po.astimezone(PT).hour
    except (KeyError, TypeError, ValueError):
        p["lead"] = p["post_hr"] = None


def cutA(title, key, order=None, rows=None):
    print(f" {title}")
    g = defaultdict(list)
    for p in (rows if rows is not None else J):
        k = key(p)
        if k is not None:
            g[k].append(p["beat_close_pts"])
    for k in (order or sorted(g)):
        if g.get(k):
            print(f"   {str(k):34s} {ms(g[k])}")


print(f" ALL                                  {ms([p['beat_close_pts'] for p in J])}")
cutA("unit plays / leans", lambda p: "lean" if p["lean"] else "unit play")
cutA("by sport", lambda p: p["league"])
cutA("by kind (unit plays)", lambda p: None if p["lean"] else p["kind"])
cutA("dog / favorite", lambda p: "dog" if p["odds"] > 0 else "favorite")
cutA("price band", lambda p: "+100..+150" if 100 <= p["odds"] <= 150 else "+151..+350" if p["odds"] > 150 else "-119..-101" if p["odds"] > -120 else "-150..-120" if p["odds"] >= -150 else "past -150",
     ["-150..-120", "-119..-101", "+100..+150", "+151..+350", "past -150"])
cutA("hours from the post to the start", lambda p: None if p["lead"] is None else "under 3h" if p["lead"] < 3 else "3-6h" if p["lead"] < 6 else "6-10h" if p["lead"] < 10 else "10h+",
     ["under 3h", "3-6h", "6-10h", "10h+"])
cutA("the hour it posted (PT)", lambda p: None if p["post_hr"] is None else "8 AM board (before 9)" if p["post_hr"] < 9 else "9 AM - 2 PM" if p["post_hr"] < 14 else "2 PM on",
     ["8 AM board (before 9)", "9 AM - 2 PM", "2 PM on"])
cutA("the move since the open AT THE POST", lambda p: None if p["drift"] is None else "money already came TO it 2+ pts" if p["drift"] <= -0.02 else "money already ran AWAY 2+ pts" if p["drift"] >= 0.02 else "flat (under 2 pts)",
     ["money already came TO it 2+ pts", "flat (under 2 pts)", "money already ran AWAY 2+ pts"])
cutA("sport x side", lambda p: f"{p['league']} {'dog' if p['odds'] > 0 else 'fav'}")
cutA("sport x hours (hockey / NBA)", lambda p: None if p["lead"] is None or p["league"] not in ("nhl", "nba") else f"{p['league']} {'under 6h' if p['lead'] < 6 else '6h+'}")
cutA("football: hours", lambda p: None if p["lead"] is None or p["league"] not in ("nfl", "ncaaf") else f"{p['league']} {'under 3h' if p['lead'] < 3 else '3-6h' if p['lead'] < 6 else '6h+'}")
print(" does beating the close go with WINNING? (unit plays + leans, flat 1u)")
for name, f in (("beat the close by 1+ pt", lambda x: x >= 1), ("beat it by under 1", lambda x: 0 < x < 1), ("same", lambda x: x == 0), ("close beat us by under 1", lambda x: -1 < x < 0), ("close beat us by 1+", lambda x: x <= -1)):
    rs = [p for p in J if f(p["beat_close_pts"]) and p.get("result") in ("won", "lost")]
    if rs:
        w = sum(p["result"] == "won" for p in rs)
        fl = sum((dec(p["odds"]) - 1) if p["result"] == "won" else -1 for p in rs)
        bev = sum(1 / dec(p["odds"]) for p in rs)
        print(f"   {name:28s} {w}-{len(rs) - w}  flat {100 * fl / len(rs):+6.1f}%  (the price expects {bev:.1f} wins)")

# ------------------------------------------------------------------ (B) the whole slate
looks = defaultdict(list)
for fn in ("2026-10.jsonl", "2026-11.jsonl"):
    with open(os.path.join("data/sports/line_history", fn)) as f:
        for l in f:
            r = json.loads(l)
            try:
                r["h"], r["a"] = float(r["h"]), float(r["a"])
            except (KeyError, TypeError, ValueError):
                continue
            if r["h"] and r["a"] and r.get("s") and abs(r["h"]) >= 100 and abs(r["a"]) >= 100:
                looks[r["g"]].append(r)


def nv(r):
    ph, pa = 1 / dec(r["h"]), 1 / dec(r["a"])
    return ph / (ph + pa)


def at(ls, t, tol_h=2.5):
    """The look nearest to t (within tol_h hours), or None."""
    b = min(ls, key=lambda r: abs((T(r["t"]) - t).total_seconds()))
    return b if abs((T(b["t"]) - t).total_seconds()) <= tol_h * 3600 else None


rowsB = []
for gid, ls in looks.items():
    ls.sort(key=lambda r: r["t"])
    try:
        st = T(ls[-1]["s"])
    except ValueError:
        continue
    pre = [r for r in ls if T(r["t"]) < st]
    if len(pre) < 3 or (st - T(pre[-1]["t"])).total_seconds() > 3 * 3600:
        continue                                             # no look within 3 hours of the start = no close
    close = pre[-1]
    day = st.astimezone(PT).replace(hour=0, minute=0, second=0, microsecond=0)
    t8 = day + timedelta(hours=8, minutes=5)
    tn = day + timedelta(hours=12)
    tp = day - timedelta(hours=4)                            # 8 PM PT the night before
    if st.astimezone(PT).hour < 10:
        continue                                             # (a morning start - the 8 AM board is not "before" it)
    row = dict(lg=gid.split(":")[0], gid=gid, st=st, close=nv(close))
    for name, t in (("night", tp), ("am8", t8), ("noon", tn)):
        if t.astimezone(timezone.utc) >= st - timedelta(hours=1):
            row[name] = None
            continue
        r = at(pre, t.astimezone(timezone.utc))
        row[name] = None if r is None else (nv(r), r["h"], r["a"])
    rowsB.append(row)
print(f"\n(B) THE WHOLE SLATE: {len(rowsB)} games 10/1-11/11 with a close (a look inside 3 hours of the start), by sport: "
      + ", ".join(f"{k} {sum(1 for r in rowsB if r['lg'] == k)}" for k in sorted({r["lg"] for r in rowsB})))
print("   + = the side's win chance at the close was HIGHER than at that look (taking it then beat the close)")
BANDS = (("dog +100..+150", 100, 150), ("dog +151..+350", 151, 350), ("fav -150..-101", -150, -101))
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    print(f" {lg}")
    for bname, lo, hi in BANDS:
        out = []
        for name in ("night", "am8", "noon"):
            v = []
            for r in rowsB:
                if r["lg"] != lg or r.get(name) is None:
                    continue
                p, h, a = r[name]
                for side, o, ps, pc in (("h", h, p, r["close"]), ("a", a, 1 - p, 1 - r["close"])):
                    if lo <= o <= hi:
                        v.append(100 * (pc - ps))
            if v:
                m = sum(v) / len(v)
                sd_ = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
                out.append(f"{name} {m:+.2f} (n {len(v)}, t {m / (sd_ / math.sqrt(len(v))) if sd_ else 0:+.1f})")
        print(f"   {bname:16s} " + " | ".join(out))
print(" every sport pooled - by how far the 8 AM price had ALREADY moved from the night before (momentum or snap-back by the close?)")
for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf", "ALL"):
    g = defaultdict(list)
    for r in rowsB:
        if (lg != "ALL" and r["lg"] != lg) or r.get("night") is None or r.get("am8") is None:
            continue
        for sgn in (1, -1):
            p0 = r["night"][0] if sgn == 1 else 1 - r["night"][0]
            p1 = r["am8"][0] if sgn == 1 else 1 - r["am8"][0]
            pc = r["close"] if sgn == 1 else 1 - r["close"]
            mv = 100 * (p1 - p0)
            k = "came TO it 2+ overnight" if mv >= 2 else "came to it 1-2" if mv >= 1 else None
            if k:
                g[k].append(100 * (pc - p1))
    print(f"   {lg:6s} " + " | ".join(f"{k}: then to the close {ms(v)}" for k, v in sorted(g.items())))
