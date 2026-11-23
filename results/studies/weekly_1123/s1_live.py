"""11/23 - THE WEEKLY FABLE SIZING + EDGES REVIEW - S1: THE WEEK AND THE LIVE RECORD (data/sports/picks.json, early.json,
clv_record.json - read only). Every graded unit play and early play 11/17-11/23, and the live record since 10/25 by
size / kind / sport / price band: W-L, units, ROI, what the prices expected (z), the beat-the-close rate. The sanity
check, never the judge - a size is judged on the replay (s2 / s3).
Usage: python results/studies/weekly_1123/s1_live.py > results/studies/weekly_1123/s1_live.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FROM, WEEK = "2026-10-25", ("2026-11-17", "2026-11-23")
ps = json.load(open(os.path.join(REPO, "data", "sports", "picks.json")))
clv = {}
for c in json.load(open(os.path.join(REPO, "data", "sports", "clv_record.json"))).get("picks") or []:
    clv[(c.get("date"), c.get("team"), c.get("market") or "ml")] = c


def kind_of(p):
    k = p.get("kind")
    if p.get("max_play"):
        return "💎 hockey max play (3u)"
    if p.get("ncaab_max"):
        return "💎 college hoops max play"
    if p.get("floor"):
        f = p["floor"] or {}
        return "NBA floor" if f.get("nba") else "floor (fallback)" if f.get("fallback") else "floor"
    if p.get("dog_play"):
        return "runner-up dog"
    if p.get("gap") is not None:
        return "🔍 gap play"
    if p.get("stack_play"):
        return "college hoops spread stack"
    if p.get("ncaab_play"):
        return "college hoops slot"
    if p.get("nba_fav"):
        return "NBA favorite play"
    return {"play": "value play", "dog": "Dog of the Day", "lock": "Lock"}.get(k, str(k))


rows = []
for p in ps:
    if p.get("lean") or p.get("status") not in ("won", "lost") or not p.get("units") or len(p.get("legs") or []) != 1:
        continue
    l = p["legs"][0]
    c = clv.get((p["date"], l.get("team"), l.get("market") or "ml")) or {}
    rows.append(dict(date=p["date"], kind=kind_of(p), u=float(p["units"]), dec=p["dec"], won=p["status"] == "won",
                     best=bool(p.get("best")), lg=l.get("league"), team=l.get("team"), odds=l.get("odds"), market=l.get("market") or "ml",
                     eo=l.get("edge_own"), score=l.get("dog_score"), rb=bool(l.get("rested_vs_b2b")), clv=c.get("pts"),
                     reasons=l.get("reasons") or [], src="board"))
e = json.load(open(os.path.join(REPO, "data", "sports", "early.json")))
ep = e["picks"]
ep = list(ep.values()) if isinstance(ep, dict) else ep
erows = []
for p in ep:
    if p.get("result") not in ("won", "lost") or not p.get("units") or p.get("pulled"):
        continue
    o = p.get("odds") or -110
    dec = 1 + (o / 100 if o > 0 else 100 / -o)
    d = (p.get("start") or "")[:10]
    cl = p.get("clv")
    if cl is None and p.get("close") is not None and p.get("market", "ml") == "ml":
        try:
            co = float(p["close"])
            cl = 100 * (1 / (1 + (co / 100 if co > 0 else 100 / -co)) - 1 / dec)
        except (TypeError, ValueError):
            cl = None
    erows.append(dict(date=d, kind="early: " + str(p.get("spot") or (p.get("spots") or ["?"])[0]), u=float(p["units"]), dec=dec,
                      won=p["result"] == "won", best=False, lg=p.get("league"), team=p.get("team"), odds=o,
                      market=p.get("market") or "ml", eo=None, score=None, rb=False, clv=cl, reasons=[], src="early"))


def show(name, rs, pad=46):
    if not rs:
        return
    n = len(rs)
    w = sum(r["won"] for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["won"] else -r["u"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    cs = [r["clv"] for r in rs if r["clv"] is not None]
    bc = f"beat the close {sum(1 for c in cs if c > 0)}/{len(cs)} (worse {sum(1 for c in cs if c < 0)})" if cs else "no close on file"
    print(f"  {name:{pad}s} {w:3d}-{n - w:<3d} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) | flat {100 * fl / n:+6.1f}% "
          f"| prices expect {exp:5.1f} wins, z {(w - exp) / math.sqrt(var) if var else 0:+.2f} | {bc}")


def tier(u):
    return "½u" if u < 0.75 else "1u" if u < 1.25 else "1.5u" if u < 1.75 else "2u" if u < 2.25 else "2.5u" if u < 2.75 else "3u+"


def band(o):
    return "fav -150..-101" if o < 100 else "+100..+150" if o <= 150 else "+151..+199" if o < 200 else "+200..+350"


def table(title, rs):
    print(f"\n==== {title}: {len(rs)} graded")
    show("ALL", rs)
    print(" -- by the size posted")
    for t in ("½u", "1u", "1.5u", "2u", "2.5u", "3u+"):
        show(t, [r for r in rs if tier(r["u"]) == t])
    print(" -- by kind")
    by = defaultdict(list)
    for r in rs:
        by[r["kind"]].append(r)
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        show(k, v)
    print(" -- by sport")
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        show(lg, [r for r in rs if r["lg"] == lg])
    print(" -- by price (moneylines)")
    ml = [r for r in rs if r["market"] == "ml"]
    for b in ("fav -150..-101", "+100..+150", "+151..+199", "+200..+350"):
        show(b, [r for r in ml if band(r["odds"]) == b])
    show("spreads / totals", [r for r in rs if r["market"] != "ml"])


wk = [r for r in rows if WEEK[0] <= r["date"] <= WEEK[1]]
wke = [r for r in erows if WEEK[0] <= r["date"] <= WEEK[1]]
print(f"THE WEEK {WEEK[0]} -> {WEEK[1]} (11/23's games are still open)")
for r in sorted(wk + wke, key=lambda r: (r["date"], r["src"])):
    c = "" if r["clv"] is None else f" close {r['clv']:+.1f}"
    print(f"  {r['date']} {str(r['team'])[:22]:22s} {r['odds']:+5d} {r['market']:6s} {r['u']:g}u {'W' if r['won'] else 'L'} {'⭐ ' if r['best'] else ''}{r['kind']} [{r['lg']}]{c}")
table("THE WEEK - board unit plays", wk)
table("THE WEEK - early plays", wke)
live = [r for r in rows if r["date"] >= FROM]
elive = [r for r in erows if r["date"] >= FROM]
table(f"LIVE SINCE {FROM} - board unit plays", live)
table(f"LIVE SINCE {FROM} - early plays", elive)
table("EVERY GRADED BOARD UNIT PLAY ON FILE (9/27 on)", rows)

print("\n==== SIZE x KIND since 10/25 (the cells the sizing plans set)")
by = defaultdict(list)
for r in live:
    by[(tier(r["u"]), r["kind"])].append(r)
for k, v in sorted(by.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
    show(f"{k[0]} {k[1]}", v)
print("\n==== SPORT x SIZE since 10/25")
by = defaultdict(list)
for r in live:
    by[(r["lg"], tier(r["u"]))].append(r)
for k, v in sorted(by.items()):
    show(f"{k[0]} {k[1]}", v)

print("\n==== THE HOCKEY DOG OF THE DAY live (every one with a dog score on file)")
hd = [r for r in rows if r["lg"] == "nhl" and r["kind"] in ("Dog of the Day", "💎 hockey max play (3u)") and r["score"] is not None]
for r in hd:
    ab = [x for x in r["reasons"] if "missing key players" in x]
    print(f"  {r['date']} {r['team']:14s} {r['odds']:+5d} {r['u']:g}u score {r['score']:5.2f} {'b2b spot' if r['rb'] else '        '} {'W' if r['won'] else 'L'} {'| ' + ab[0][:70] if ab else ''}")
show("the max-play SHAPE live (b2b spot, score 8+)", [r for r in hd if r["rb"] and r["score"] >= 8])
show("the b2b spot under 8", [r for r in hd if r["rb"] and r["score"] < 8])
show("the hockey Dog, no b2b spot", [r for r in hd if not r["rb"]])

print("\n==== LIVE: hockey unit plays that named 'opponent missing key players' (the absence points on the read)")
ha = [r for r in rows if r["lg"] == "nhl" and any("missing key players" in x for x in r["reasons"])]
show("hockey DOG riding it", [r for r in ha if r["odds"] >= 100])
show("hockey FAVORITE riding it", [r for r in ha if r["odds"] < 100])
for r in ha:
    print(f"     {r['date']} {r['team']:14s} {r['odds']:+5d} {r['u']:g}u {'W' if r['won'] else 'L'} {r['kind']}")

print("\n==== THE ⭐ live (11/4 on)")
st = [r for r in rows if r["best"]]
show("the ⭐", st)
show("the ⭐ 11/22 on (the biggest bet first)", [r for r in st if r["date"] >= "2026-11-22"])
show("every other unit play since 11/4", [r for r in rows if not r["best"] and r["date"] >= "2026-11-04"])
for r in st:
    print(f"     {r['date']} {str(r['team'])[:18]:18s} {r['odds']:+5d} {r['u']:g}u {'W' if r['won'] else 'L'} {r['kind']}")
