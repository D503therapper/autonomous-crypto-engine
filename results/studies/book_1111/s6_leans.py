"""STUDY 6 - THE LEANS (live 58-58 -4.1% flat; hockey leans 19-24 -19.5%, the worst cell on the board with a sample).
The replay's leans (the funnel rows the board posted as a lean, closing prices) by sport and by what the engine knew:
the weighed read (w_p) vs the no-vig market, the own read, the price, home / road. A lean carries no units, but the
viewers bet them - a lean on a side the engine's own weights are AGAINST is a bad call to hand them.
Then the live leans (data/sports/picks.json) cut the same way.  Usage: python s6_leans.py > s6_leans.out"""
import json
import os
from collections import Counter, defaultdict

from blib import cell, sv, gap

N = [0]
print("kinds in the rows:", Counter(r["kind"] for r in sv.rows).most_common())
leans = [r for r in sv.rows if r["kind"] == "lean" or r.get("lean")]
print(f"replay leans: {len(leans)}")


def cut(title, rs, key, mn=20):
    print(f" {title}")
    g = defaultdict(list)
    for r in rs:
        k = key(r)
        if k is not None:
            g[k].append((r["date"], r, 1))
    for k in sorted(g):
        if len(g[k]) >= mn:
            cell(f"   {k}", g[k])
            N[0] += 1


def wside(r):
    if r.get("w_p") is None or r.get("p_market") is None:
        return "no weighed read"
    g = 100 * (r["w_p"] - r["p_market"])
    return "weighed 2+ UNDER the market" if g <= -2 else "weighed 0-2 under" if g < 0 else "weighed 0-2 over" if g < 2 else "weighed 2+ over"


cell("ALL replay leans", [(r["date"], r, 1) for r in leans])
cut("by sport", leans, lambda r: r["league"])
cut("favorite / dog", leans, lambda r: "dog" if r["odds"] > 0 else "favorite -150..-101" if r["odds"] >= -150 else "favorite -151..-250" if r["odds"] >= -250 else "favorite past -250")
for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf", "mlb"):
    rs = [r for r in leans if r["league"] == lg]
    if len(rs) < 40:
        continue
    print(f"\n=== {lg} leans ({len(rs)})")
    cut("price", rs, lambda r: "dog" if r["odds"] > 0 else "-150..-101" if r["odds"] >= -150 else "-151..-200" if r["odds"] >= -200 else "-201..-250" if r["odds"] >= -250 else "past -250")
    cut("the weighed read vs the market", rs, wside)
    cut("the own read vs the market", rs, lambda r: None if gap(r) is None else "own 2+ under" if gap(r) <= -2 else "own 0-2 under" if gap(r) < 0 else "own 0-2 over" if gap(r) < 2 else "own 2+ over")
    cut("home / road", rs, lambda r: "home" if r["home"] else "road")
    cut("the move since the open", rs, lambda r: None if r.get("drift") is None else "money came TO it 2+" if r["drift"] <= -0.02 else "money ran AWAY 2+" if r["drift"] >= 0.02 else "flat")
    cut("flags", rs, lambda r: "hockey_fav_bad" if r.get("hockey_fav_bad") else "fighting" if r.get("fighting") else "trap" if r.get("trap") else "clean")
print(f"\n{N[0]} cells printed")

# ---- the live leans
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
picks = json.load(open(os.path.join(ROOT, "data/sports/picks.json")))
print("\nLIVE LEANS (9/29 on), hockey first")
import math  # noqa: E402


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def lv(name, rs):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    print(f"  {name:52s} {w}-{len(rs) - w}  flat {100 * fl / len(rs):+6.1f}%  price expects {bev:5.1f}  z {(w - bev) / math.sqrt(var):+.2f}")


L = []
for p in picks:
    if not p.get("lean") or p.get("status") not in ("won", "lost") or p.get("pulled") or p.get("void"):
        continue
    l = (p.get("legs") or [{}])[0]
    if (l.get("market") or "ml") != "ml":
        continue
    o = l.get("odds") or p["american"]
    wp, pm = l.get("w_p"), l.get("p_market")
    L.append(dict(lg=l.get("league"), won=p["status"] == "won", dec=dec(o), odds=o, wp=wp, pm=pm, home=l.get("home"), date=p["date"],
                  eo=l.get("edge_own"), team=l.get("team"), drift=l.get("drift"), p=l.get("p")))
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
    rs = [r for r in L if r["lg"] == lg]
    lv(f"{lg} moneyline leans", rs)
    lv(f"   {lg} weighed UNDER the market", [r for r in rs if r["wp"] is not None and r["pm"] is not None and r["wp"] < r["pm"]])
    lv(f"   {lg} weighed OVER the market", [r for r in rs if r["wp"] is not None and r["pm"] is not None and r["wp"] >= r["pm"]])
    lv(f"   {lg} no weighed read on the leg", [r for r in rs if r["wp"] is None or r["pm"] is None])
    lv(f"   {lg} own read under the price", [r for r in rs if r["eo"] is not None and r["eo"] < 0])
    lv(f"   {lg} own read over the price", [r for r in rs if r["eo"] is not None and r["eo"] >= 0])
    lv(f"   {lg} past -150", [r for r in rs if r["odds"] < -150])
    lv(f"   {lg} -150..-101", [r for r in rs if -150 <= r["odds"] < 0])
print()
for r in [r for r in L if r["lg"] == "nhl"]:
    print(f"   {r['date']} {r['team']:16s} {r['odds']:+5d} {'W' if r['won'] else 'L'} w_p {r['wp']} mkt {r['pm']} p {r['p']} edge_own {r['eo']} drift {r['drift']} home {r['home']}")
