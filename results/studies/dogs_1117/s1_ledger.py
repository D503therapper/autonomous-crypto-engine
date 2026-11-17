"""11/17 UNDERDOG EDGE - (1) THE LIVE DOG LEDGER: every graded PLUS-MONEY moneyline unit play since 10/25
(data/sports/picks.json + data/sports/early.json; no leans - they're gone), by path, by sport, by price band, by home /
road, by the own read's edge - W-L, units, ROI, and what the prices alone expected. The sanity check, never the judge.
Usage: python results/studies/dogs_1117/s1_ledger.py > results/studies/dogs_1117/s1_ledger.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FROM = "2026-10-25"


def dec_of(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


rows = []
for p in json.load(open(os.path.join(REPO, "data", "sports", "picks.json"))):
    if p.get("lean") or p.get("status") not in ("won", "lost") or not p.get("units") or len(p.get("legs") or []) != 1:
        continue
    if p["date"] < FROM:
        continue
    l = p["legs"][0]
    if l.get("market") != "ml" or (l.get("odds") or 0) < 100:
        continue
    kind = p.get("kind")
    fl = p.get("floor") or {}
    if p.get("floor"):
        kind = "NBA floor" if fl.get("nba") else ("floor FALLBACK" if fl.get("fallback") else "floor")
    elif p.get("dog_play"):
        kind = "runner-up dog"
    elif p.get("gap") is not None:
        kind = "🔍 gap play (" + ("college hoops" if l.get("league") == "ncaab" else "college football") + ")"
    elif p.get("ncaab_play"):
        kind = "college hoops dog slot"
    elif kind == "dog":
        kind = "Dog of the Day" + (" 💎 max play" if p.get("max_play") else "")
    elif kind == "play":
        kind = "value play (dog)"
    elif kind in ("lock", "solo"):
        kind = kind + " (plus money)"
    rows.append(dict(date=p["date"], path=kind, u=float(p["units"]), dec=p.get("dec") or l.get("dec") or dec_of(l["odds"]),
                     won=p["status"] == "won", lg=l.get("league"), team=l.get("team"), opp=l.get("opp"), odds=l["odds"],
                     home=l.get("home"), eo=l.get("edge_own"), best=bool(p.get("best")), sc=l.get("dog_score") or fl.get("dog_score"),
                     src="board"))
e = json.load(open(os.path.join(REPO, "data", "sports", "early.json")))
ep = e["picks"]
ep = list(ep.values()) if isinstance(ep, dict) else ep
for p in ep:
    if p.get("result") not in ("won", "lost") or (p.get("start") or "")[:10] < FROM:
        continue
    if (p.get("market") or "ml") != "ml" or (p.get("odds") or 0) < 100 or p.get("spot") in ("euro_under", "alt_over", "nba_out_over"):
        continue
    rows.append(dict(date=(p.get("start") or "")[:10], path="⏰ early: " + (p.get("spot") or "exam scan"), u=float(p.get("units") or 0.5),
                     dec=dec_of(p["odds"]), won=p["result"] == "won", lg=p.get("league"), team=p.get("team"), opp=p.get("opp"),
                     odds=p["odds"], home=p.get("home"), eo=None, best=False, sc=None, src="early"))


def show(name, rs):
    if not rs:
        return
    n = len(rs)
    w = sum(r["won"] for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["won"] else -r["u"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    print(f"  {name:44s} {w:3d}-{n - w:<3d} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) | flat 1u {fl:+6.1f}u ({100 * fl / n:+6.1f}%) "
          f"| the prices expected {exp:5.1f} wins, z {(w - exp) / math.sqrt(var) if var else 0:+.2f}")


def by(key, rs, order=None):
    g = defaultdict(list)
    for r in rs:
        g[key(r)].append(r)
    for k in (order or sorted(g, key=lambda k: -len(g[k]))):
        show(str(k), g.get(k, []))


def band(r):
    return "+100..+150" if r["odds"] <= 150 else "+151..+250" if r["odds"] <= 250 else "+251..+350"


BANDS = ["+100..+150", "+151..+250", "+251..+350"]
board = [r for r in rows if r["src"] == "board"]
early = [r for r in rows if r["src"] == "early"]
print(f"graded plus-money moneyline unit plays {min(r['date'] for r in rows)} -> {max(r['date'] for r in rows)}: {len(rows)} "
      f"({len(board)} board, {len(early)} early)")
show("EVERY DOG UNIT PLAY", rows)
show("the board's dogs", board)
show("the early dogs", early)
print("-- BY PATH")
by(lambda r: r["path"], rows)
print("-- BY SPORT (board + early)")
by(lambda r: r["lg"], rows)
print("-- BY PRICE BAND")
by(band, rows, BANDS)
print("-- BY SPORT x PRICE BAND")
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    for b in BANDS:
        show(f"{lg} {b}", [r for r in rows if r["lg"] == lg and band(r) == b])
print("-- BY SIZE POSTED")
by(lambda r: f"{r['u']:g}u", rows, ["0.5u", "1u", "1.5u", "2u", "2.5u", "3u"])
print("-- HOME / ROAD (the board's dogs; the leg's own flag)")
by(lambda r: "home" if r["home"] else "road" if r["home"] is False else "?", board)
print("-- THE BOARD'S DOGS BY THE OWN READ'S EDGE")
by(lambda r: "no own read" if r["eo"] is None else "own read UNDER the price" if r["eo"] < 0 else "0-3c over (thin)" if r["eo"] < 0.03 else "3c+ over", board)
print("-- PATH x SPORT")
by(lambda r: f"{r['path']} / {r['lg']}", rows)
print("-- BY WEEK (the game's day)")
by(lambda r: "10/25-10/31" if r["date"] <= "2026-10-31" else "11/01-11/07" if r["date"] <= "2026-11-07" else "11/08-11/14" if r["date"] <= "2026-11-14" else "11/15 on", rows,
   ["10/25-10/31", "11/01-11/07", "11/08-11/14", "11/15 on"])
print("-- EVERY PLAY")
for r in sorted(rows, key=lambda r: r["date"]):
    print(f"  {r['date']} {r['lg']:5s} {str(r['team'])[:18]:18s} {r['odds']:+5d} {r['u']:g}u {'W' if r['won'] else 'L'} {'home' if r['home'] else 'road' if r['home'] is False else '?':4s} "
          f"{r['path']}{' ⭐' if r['best'] else ''} own edge {None if r['eo'] is None else round(r['eo'], 3)} score {r['sc']}")
