"""11/11 THE BOOK, part 1 - the live unit-play ledger since 9/27 (sports.units_ledger: data/sports/picks.json + early.json,
read only), cut by every axis: kind, sport, price band, size, thin vs real edge, read-vs-market gap, home / road, the slot
(the 8 AM board vs a mid-day add), closing-line value, day of week; then the leans, the owner's calls, live plus money.

Per cell: W-L, units won on units risked, ROI, flat-1u ROI, the wins the PRICE expected (sum of 1/decimal - the "fair bet"
count, vig in) and z = (wins - expected) / sd: how unlikely the record is if the cell were a coin weighted at its price.
|z| under 2 on a cell this small is noise - 60 cells cut here, ~3 would pass |z| 2 by luck.
Usage: python results/studies/book_1111/p1_book.py > results/studies/book_1111/p1_book.out"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_early  # noqa: E402

picks = json.load(open("data/sports/picks.json"))
early = json.load(open("data/sports/early.json")).get("picks") or []
led = sports.units_ledger(picks, early)
clv = {}
for c in json.load(open("data/sports/clv_record.json")).get("picks") or []:
    clv[(c["date"], c["team"], c.get("market") or "ml")] = c

rows = []
for p, u, net, _ in led["rows"]:
    if u <= 0:
        continue
    l = (p.get("legs") or [{}])[0]
    am = l.get("odds") or p.get("american")
    dec = sports._dec(am)
    if not net:
        continue                                     # a push
    kind = "early:" + (next((e.get("spot") or "exam band / owner" for e in early
                             if e.get("team") == l.get("team") and e.get("odds") == am and e.get("result") in ("won", "lost", "push")
                             and datetime.strptime(e["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(sports.PT).strftime("%Y-%m-%d") == p["date"]), None) or "?") \
        if p.get("kind") == "early" else "parlay leg" if p.get("kind") == "pick" else sports.posted_kind(p)
    if p.get("kind") == "play" and kind == "play":
        kind = "value play"
    own = l.get("raw_own") if l.get("edge_own") is None else (l["edge_own"] + 1) / dec
    pm = l.get("p_market")
    posted = p.get("posted") or ""
    try:
        ph = datetime.strptime(posted, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(sports.PT)
        slot = "8 AM board" if ph.hour < 9 else "mid-day add (9 AM-2 PM)" if ph.hour < 14 else "late add (2 PM on)"
        st = datetime.strptime(l["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        lead = (st - ph.astimezone(timezone.utc)).total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        slot, lead = "?", None
    if p.get("kind") == "early":
        slot = "early (days ahead)"
    c = clv.get((p["date"], l.get("team"), l.get("market") or "ml"))
    rows.append(dict(date=p["date"], u=u, net=net, won=net > 0, am=am, dec=dec, kind=kind, lg=l.get("league") or p.get("league"),
                     thin=(sports.thin_edge(l) if l.get("edge_own") is not None else None), best=bool(p.get("best")),
                     gap=None if own is None or pm is None else 100 * (own - pm), eown=l.get("edge_own"),
                     home=l.get("home"), slot=slot, lead=lead, clv=None if not c else c.get("pts"),
                     dow=datetime.strptime(p["date"], "%Y-%m-%d").strftime("%a"), team=l.get("team"),
                     market=l.get("market") or "ml", dscore=l.get("floor_score")))


def line(name, rs, out=None):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    st = sum(r["u"] for r in rs)
    pr = sum(r["net"] for r in rs)
    flat = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    s = (f"  {name:34s} {w:3d}-{len(rs) - w:<3d} {pr:+7.2f}u on {st:6.1f}u ({pr / st * 100:+6.1f}%)  flat 1u {flat / len(rs) * 100:+6.1f}%  "
         f"price expects {bev:5.1f} wins  z {z:+.2f}")
    print(s)


def cut(title, key, order=None):
    print(f"\n{title}")
    d = defaultdict(list)
    for r in rows:
        k = key(r)
        if k is not None:
            d[k].append(r)
    for k in (order or sorted(d, key=lambda k: -sum(r["net"] for r in d[k]))):
        line(str(k), d.get(k, []))


def band(am):
    for lo, hi in ((-150, -131), (-130, -120), (-119, -101), (100, 119), (120, 150), (151, 199), (200, 350)):
        if lo <= am <= hi:
            return f"{lo:+d}..{hi:+d}"
    return "past -150 (early / owner)" if am < -150 else "past +350"


print(f"THE BOOK - every graded unit play {rows[0]['date']} -> {rows[-1]['date']} ({len(rows)} rows)")
line("ALL UNIT PLAYS", rows)
line("favorites", [r for r in rows if r["am"] < 0])
line("dogs", [r for r in rows if r["am"] > 0])
cut("BY KIND", lambda r: r["kind"])
cut("BY KIND GROUP", lambda r: "early plays" if r["kind"].startswith("early") else r["kind"])
cut("BY SPORT", lambda r: r["lg"])
cut("BY SPORT x SIDE", lambda r: f"{r['lg']} {'dog' if r['am'] > 0 else 'fav'}")
cut("BY PRICE BAND", lambda r: band(r["am"]), ["-150..-131", "-130..-120", "-119..-101", "+100..+119", "+120..+150", "+151..+199", "+200..+350", "past -150 (early / owner)", "past +350"])
cut("BY SIZE", lambda r: f"{r['u']}u", ["0.5u", "1.0u", "1.5u", "2.0u", "2.5u", "3.0u", "3.5u", "4.0u", "5.0u"])
cut("BY SIZE GROUP x SIDE", lambda r: ("½u" if r["u"] == 0.5 else "1u" if r["u"] == 1 else "2u+") + (" dog" if r["am"] > 0 else " fav"))
cut("THIN vs REAL EDGE (own read under / over 3% past the price; board picks only)", lambda r: None if r["thin"] is None else "thin" if r["thin"] else "real edge")
cut("THIN x SIDE", lambda r: None if r["thin"] is None else ("thin" if r["thin"] else "real edge") + (" dog" if r["am"] > 0 else " fav"))
cut("OWN READ vs THE NO-VIG MARKET (points)", lambda r: None if r["gap"] is None else "under 0" if r["gap"] < 0 else "0-2" if r["gap"] < 2 else "2-5" if r["gap"] < 5 else "5-10" if r["gap"] < 10 else "10+",
    ["under 0", "0-2", "2-5", "5-10", "10+"])
cut("HOME / ROAD", lambda r: None if r["home"] is None else "home" if r["home"] else "road")
cut("HOME / ROAD x SIDE", lambda r: None if r["home"] is None else ("home" if r["home"] else "road") + (" dog" if r["am"] > 0 else " fav"))
cut("THE SLOT (when it posted, PT)", lambda r: r["slot"])
cut("HOURS FROM POST TO START (board picks)", lambda r: None if r["lead"] is None or r["kind"].startswith("early") else "under 3h" if r["lead"] < 3 else "3-6h" if r["lead"] < 6 else "6-10h" if r["lead"] < 10 else "10h+",
    ["under 3h", "3-6h", "6-10h", "10h+"])
cut("CLOSING LINE (points of win chance we beat the close by)", lambda r: None if r["clv"] is None else "beat the close" if r["clv"] > 0 else "same" if r["clv"] == 0 else "close beat us",
    ["beat the close", "same", "close beat us"])
cut("DAY OF WEEK", lambda r: r["dow"], ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
cut("⭐ BEST PICK", lambda r: "⭐" if r["best"] else None)
cut("BY MONTH-HALF", lambda r: r["date"][:8] + ("01-15" if r["date"][8:] <= "15" else "16-31"), sorted({r["date"][:8] + ("01-15" if r["date"][8:] <= "15" else "16-31") for r in rows}))
cut("HOCKEY by kind", lambda r: r["kind"] if r["lg"] == "nhl" else None)
cut("NBA by kind", lambda r: r["kind"] if r["lg"] == "nba" else None)
cut("COLLEGE FOOTBALL by kind", lambda r: r["kind"] if r["lg"] == "ncaaf" else None)
cut("NFL by kind", lambda r: r["kind"] if r["lg"] == "nfl" else None)
cut("DOGS by price (board, not early)", lambda r: None if r["am"] < 0 or r["kind"].startswith("early") else "+100..+150" if r["am"] <= 150 else "+151..+350",
    ["+100..+150", "+151..+350"])

# where the money is: the 10 biggest wins / losses
print("\nTHE 12 BIGGEST SWINGS")
for r in sorted(rows, key=lambda r: -abs(r["net"]))[:12]:
    print(f"  {r['date']} {r['lg']:6s} {r['kind']:14s} {r['team'] or '':22s} {r['am']:+5d} {r['u']}u -> {r['net']:+.2f}u")
tot = sum(r["net"] for r in rows)
big = [r for r in rows if r["u"] >= 2]
print(f"\n  total {tot:+.2f}u; the 2u+ plays {sum(r['net'] for r in big):+.2f}u on {len(big)} plays; everything at 1u and under {tot - sum(r['net'] for r in big):+.2f}u on {len(rows) - len(big)}")
flat = sum((r["dec"] - 1) if r["won"] else -1 for r in rows)
print(f"  the same picks FLAT 1u each: {flat:+.2f}u on {len(rows)}u ({flat / len(rows) * 100:+.1f}%) vs as sized {tot / sum(r['u'] for r in rows) * 100:+.1f}% - the SIZING added "
      f"{tot / sum(r['u'] for r in rows) * 100 - flat / len(rows) * 100:+.1f} points of ROI")

# CLV detail
cl = [r for r in rows if r["clv"] is not None]
print(f"\nCLOSING LINE - {len(cl)} unit plays with a close on file; average {sum(r['clv'] for r in cl) / len(cl):+.2f} points")
for name, f in (("8 AM board", lambda r: r["slot"] == "8 AM board"), ("mid-day / late add", lambda r: "add" in r["slot"]), ("dogs", lambda r: r["am"] > 0), ("favs", lambda r: r["am"] < 0)):
    rs = [r for r in cl if f(r)]
    if rs:
        print(f"  {name:20s} n {len(rs):3d}  avg {sum(r['clv'] for r in rs) / len(rs):+.2f} pts  beat {sum(r['clv'] > 0 for r in rs)} / same {sum(r['clv'] == 0 for r in rs)} / worse {sum(r['clv'] < 0 for r in rs)}")
for lg in sorted({r["lg"] for r in cl}):
    rs = [r for r in cl if r["lg"] == lg]
    print(f"  {lg:20s} n {len(rs):3d}  avg {sum(r['clv'] for r in rs) / len(rs):+.2f} pts  beat {sum(r['clv'] > 0 for r in rs)} / same {sum(r['clv'] == 0 for r in rs)} / worse {sum(r['clv'] < 0 for r in rs)}")

# leans
print("\nTHE LEANS (no units; flat 1u for the read only)")
ln = []
for p in picks:
    if not p.get("lean") or p.get("status") not in ("won", "lost") or p.get("pulled") or p.get("void") or p.get("date", "") < "2026-09-29":
        continue
    l = (p.get("legs") or [{}])[0]
    am = l.get("odds") or p.get("american")
    ln.append(dict(u=1, net=(sports._dec(am) - 1) if p["status"] == "won" else -1, won=p["status"] == "won", am=am, dec=sports._dec(am),
                   lg=l.get("league"), market=l.get("market") or "ml", home=l.get("home")))
line("all leans", ln)
for k in sorted({r["lg"] for r in ln}):
    line(f"leans {k}", [r for r in ln if r["lg"] == k])
line("leans favorites", [r for r in ln if r["am"] < 0 and r["market"] == "ml"])
line("leans dogs (ML)", [r for r in ln if r["am"] > 0 and r["market"] == "ml"])
line("leans on a spread", [r for r in ln if r["market"] != "ml"])

# the owner's calls
oc = [c for c in json.load(open("data/sports/owner_calls.json")).get("calls") or [] if c.get("result") in ("won", "lost")]
print("\n🧠 THE OWNER'S CALLS (logged, no units)")
line("owner calls", [dict(u=1, won=c["result"] == "won", am=c["odds"], dec=sports._dec(c["odds"]), net=(sports._dec(c["odds"]) - 1) if c["result"] == "won" else -1) for c in oc])

# early plays by spot
print("\n⏰ EARLY PLAYS by spot (their own sizes)")
es = defaultdict(list)
for e in early:
    if e.get("result") in ("won", "lost") and not e.get("pulled"):
        u = sports_early.units(e)
        d = sports._dec(e["odds"])
        es[e.get("spot")].append(dict(u=u, won=e["result"] == "won", am=e["odds"], dec=d, net=u * (d - 1) if e["result"] == "won" else -u))
for k in sorted(es, key=lambda k: -sum(r["net"] for r in es[k])):
    line(f"early: {k}", es[k])
line("early: ALL", [r for v in es.values() for r in v])
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p1_rows.json"), "w"), indent=0, default=str)
