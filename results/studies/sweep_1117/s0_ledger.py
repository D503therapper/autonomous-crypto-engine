"""11/17 FULL SWEEP - THE LIVE LEDGER: every NON-DOG unit play since 10/25 (data/sports/picks.json + early.json) by kind,
sport and size: W-L, units, ROI. Non-dog = a moneyline favorite (odds under +100), any spread, any total. The dogs are
the other study's (shown as one line for the frame). Live is the sanity check, never the judge.
Usage: python results/studies/sweep_1117/s0_ledger.py > results/studies/sweep_1117/s0_ledger.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FROM = "2026-10-25"


def dec_of(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def kind_of(p):
    k = p.get("kind")
    if p.get("floor"):
        return "NBA floor" if (p["floor"] or {}).get("nba") else "floor"
    if p.get("dog_play"):
        return "runner-up dog"
    if p.get("gap") is not None:
        return "gap play"
    if p.get("stack_play"):
        return "college hoops spread stack"
    if p.get("ncaab_play"):
        return "college hoops slot"
    if p.get("nba_fav"):
        return "NBA favorite play"
    if p.get("night"):
        return "night football"
    return {"play": "value play", "lock": "Lock", "dog": "Dog"}.get(k, str(k))


rows = []
for p in json.load(open(os.path.join(REPO, "data", "sports", "picks.json"))):
    if p.get("lean") or p.get("status") not in ("won", "lost", "push") or not p.get("units") or len(p.get("legs") or []) != 1:
        continue
    if p["date"] < FROM:
        continue
    l = p["legs"][0]
    d = p.get("dec") or l.get("dec")
    if not d:
        continue
    kd = kind_of(p)
    if kd == "Lock" and l.get("fb_thin_lock"):
        kd = "Lock (football thin)"
    if kd == "Lock" and p.get("backup"):
        kd = "Lock (backup)"
    rows.append(dict(date=p["date"], kind=kd, u=float(p["units"]), dec=d, res=p["status"], best=bool(p.get("best")),
                     lg=l.get("league"), team=l.get("team"), odds=l.get("odds"), eo=l.get("edge_own"), market=l.get("market") or "ml",
                     src="board"))
e = json.load(open(os.path.join(REPO, "data", "sports", "early.json")))
ep = e["picks"]
ep = list(ep.values()) if isinstance(ep, dict) else ep
for p in ep:
    if p.get("result") not in ("won", "lost", "push") or (p.get("start") or "")[:10] < FROM:
        continue
    rows.append(dict(date=(p.get("start") or "")[:10], kind="early: " + (p.get("spot") or "exam scan"), u=float(p.get("units") or 0.5),
                     dec=dec_of(p["odds"]), res=p["result"], best=False, lg=p.get("league"), team=p.get("team") or p.get("pick"),
                     odds=p["odds"], eo=None, market=p.get("market") or "ml", src="early"))


def nondog(r):
    return r["market"] != "ml" or (r["odds"] or 0) < 100


def show(name, rs):
    if not rs:
        return
    w = sum(r["res"] == "won" for r in rs)
    l = sum(r["res"] == "lost" for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["res"] == "won" else -r["u"] if r["res"] == "lost" else 0 for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    print(f"  {name:46s} {w:3d}-{l:<3d} {net:+6.2f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) | the prices expected {exp:5.1f} wins, "
          f"z {(w - exp) / math.sqrt(var) if var else 0:+.2f}")


nd = [r for r in rows if nondog(r)]
print(f"graded unit plays {FROM} -> {max(r['date'] for r in rows)}: {len(rows)} ({len(nd)} non-dog)")
show("EVERY unit play (board + early)", rows)
show("the dogs (moneyline, plus money) - the other study", [r for r in rows if not nondog(r)])
show("THE NON-DOG PLAYS", nd)
print("-- BY MARKET")
for m in sorted({r["market"] for r in nd}):
    show(m, [r for r in nd if r["market"] == m])
print("-- BY KIND")
by = defaultdict(list)
for r in nd:
    by[r["kind"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(k, v)
print("-- BY SPORT")
for lg in sorted({str(r["lg"]) for r in nd}):
    show(lg, [r for r in nd if str(r["lg"]) == lg])
print("-- BY SIZE")
for u in sorted({r["u"] for r in nd}):
    show(f"{u:g}u", [r for r in nd if r["u"] == u])
print("-- BY KIND x SPORT x SIZE")
by = defaultdict(list)
for r in nd:
    by[(r["kind"], str(r["lg"]), r["u"])].append(r)
for k, v in sorted(by.items()):
    show(f"{k[0]} / {k[1]} / {k[2]:g}u", v)
print("-- MONEYLINE FAVORITES BY PRICE")
fav = [r for r in nd if r["market"] == "ml"]
for lo, hi in ((-119, -100), (-134, -120), (-150, -135), (-9999, -151)):
    show(f"{lo}..{hi}", [r for r in fav if lo <= r["odds"] <= hi])
print("-- FAVORITES BY THE OWN READ'S EDGE (board rows)")
for nm, f in (("own read UNDER the price", lambda x: x < 0), ("0-3c over (thin)", lambda x: 0 <= x < .03), ("3c+ over", lambda x: x >= .03)):
    show(nm, [r for r in fav if r["eo"] is not None and f(r["eo"])])
show("the ⭐ (any side)", [r for r in rows if r["best"]])
show("the ⭐ on a non-dog", [r for r in nd if r["best"]])
print("-- EVERY NON-DOG PLAY")
for r in sorted(nd, key=lambda r: r["date"]):
    print(f"  {r['date']} {str(r['lg']):6s} {str(r['team'])[:24]:24s} {r['market']:6s} {r['odds']:+5d} {r['u']:g}u {r['res']:5s} {r['kind']}"
          f"{' ⭐' if r['best'] else ''} own edge {r['eo'] if r['eo'] is None else round(r['eo'], 3)}")
