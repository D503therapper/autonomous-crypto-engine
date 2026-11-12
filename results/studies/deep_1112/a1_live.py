"""11/12 DEEP PROGRAM - A1: THE LIVE ENGINE BY SPORT. Every graded pick in data/sports/pick_journal.json (the board's
picks with the reads stamped at post time): the record by sport x kind x market, beat-the-close, and the reads'
calibration (what the read said vs what happened). Early plays (data/sports/early.json) on their own line.
Usage: python results/studies/deep_1112/a1_live.py > results/studies/deep_1112/a1_live.out"""
import json, math, os
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = json.load(open(os.path.join(ROOT, "data/sports/pick_journal.json")))
E = json.load(open(os.path.join(ROOT, "data/sports/early.json")))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def line(name, rs):
    rs = [r for r in rs if r.get("result") in ("won", "lost")]
    if not rs:
        return
    w = sum(r["result"] == "won" for r in rs)
    n = len(rs)
    fl = sum((dec(r["odds"]) - 1) if r["result"] == "won" else -1 for r in rs)
    un = sum(r.get("pnl_units") or 0 for r in rs)
    ps = [r.get("price_says") or 1 / dec(r["odds"]) / 1.045 for r in rs]
    exp = sum(ps)
    var = sum(p * (1 - p) for p in ps)
    z = (w - exp) / math.sqrt(var) if var else float("nan")
    cl = [r["beat_close_pts"] for r in rs if r.get("beat_close_pts") is not None]
    beat = sum(x > 0 for x in cl)
    wr = [r["win_p"] for r in rs if r.get("win_p")]
    ow = [r["own_read"] for r in rs if r.get("own_read")]
    print(f"  {name:42s} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% units {un:+6.2f} | price said {100 * exp / n:4.1f}% won {100 * w / n:4.1f}% z {z:+4.1f}"
          f" | win_p {100 * sum(wr) / len(wr) if wr else 0:4.1f}% own {100 * sum(ow) / len(ow) if ow else 0:4.1f}%"
          f" | close: beat {beat}/{len(cl)} avg {sum(cl) / len(cl) if cl else 0:+.2f} pts")


print("pick journal rows:", len(J), "graded:", sum(r.get("result") in ("won", "lost") for r in J))
units = lambda r: not r.get("lean") and (r.get("units") or 0) > 0     # noqa: E731
for lg in ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb"):
    rs = [r for r in J if r["league"] == lg]
    print(f"== {lg.upper()}")
    line("unit plays, all", [r for r in rs if units(r)])
    for k in sorted({r["kind"] + "/" + str(r.get("tier")) for r in rs if units(r)}):
        line("  " + k, [r for r in rs if units(r) and r["kind"] + "/" + str(r.get("tier")) == k])
    line("unit favorites", [r for r in rs if units(r) and r["odds"] < 0])
    line("unit dogs", [r for r in rs if units(r) and r["odds"] > 0])
    line("unit dogs at home", [r for r in rs if units(r) and r["odds"] > 0 and r.get("home")])
    line("unit dogs on the road", [r for r in rs if units(r) and r["odds"] > 0 and not r.get("home")])
    line("leans, all", [r for r in rs if not units(r)])
    line("  leans ML", [r for r in rs if not units(r) and r["market"] == "ml"])
    line("  leans spread", [r for r in rs if not units(r) and r["market"] == "spread"])
    line("  leans spread, favorite", [r for r in rs if not units(r) and r["market"] == "spread" and (r.get("line") or 0) < 0])
    line("  leans spread, dog", [r for r in rs if not units(r) and r["market"] == "spread" and (r.get("line") or 0) > 0])
    line("  leans spread laying 7.5+", [r for r in rs if not units(r) and r["market"] == "spread" and (r.get("line") or 0) <= -7.5])
print("== ALL SPORTS")
line("unit plays", [r for r in J if units(r)])
line("leans ML", [r for r in J if not units(r) and r["market"] == "ml"])
line("leans spread", [r for r in J if not units(r) and r["market"] == "spread"])
line("leans total", [r for r in J if not units(r) and r["market"] == "total"])
print("== CALIBRATION, LIVE (moneyline picks: what each read said vs what happened)")
for key in ("win_p", "own_read", "weighed", "price_says"):
    print(" ", key)
    for lo, hi in ((0, .35), (.35, .45), (.45, .50), (.50, .55), (.55, .60), (.60, .70), (.70, 1)):
        rs = [r for r in J if r.get("result") in ("won", "lost") and r["market"] == "ml" and r.get(key) and lo <= r[key] < hi]
        if rs:
            w = sum(r["result"] == "won" for r in rs)
            p = sum(r[key] for r in rs) / len(rs)
            se = math.sqrt(p * (1 - p) / len(rs))
            print(f"    {lo:.2f}-{hi:.2f}: n {len(rs):3d} said {100 * p:4.1f}% won {100 * w / len(rs):4.1f}%  (z {(w / len(rs) - p) / se:+.1f})")
print("== own read OVER the price vs under, live unit ML plays, by sport")
for lg in ("nfl", "ncaaf", "nba", "ncaab", "nhl"):
    for nm, f in (("own over price", lambda r: r["own_read"] > 1 / dec(r["odds"])), ("own under price", lambda r: r["own_read"] <= 1 / dec(r["odds"]))):
        line(f"{lg} {nm}", [r for r in J if r["league"] == lg and units(r) and r["market"] == "ml" and r.get("own_read") and f(r)])
print("== EARLY PLAYS (early.json picks, graded)")
ep = [p for p in E["picks"] if p.get("result") in ("won", "lost")]
bysp = defaultdict(list)
for p in ep:
    bysp[(p["league"], p.get("spot"))].append(p)
for k in sorted(bysp, key=str):
    rs = bysp[k]
    w = sum(p["result"] == "won" for p in rs)
    u = sum((p.get("units") or 0) * ((dec(p["odds"]) - 1) if p["result"] == "won" else -1) for p in rs)
    own = [p["own"] for p in rs if isinstance(p.get("own"), float)]
    mk = [p["mkt"] for p in rs if isinstance(p.get("mkt"), float)]
    print(f"  {str(k):34s} {w}-{len(rs) - w} units {u:+.2f} | own said {100 * sum(own) / len(own) if own else 0:.0f}% market {100 * sum(mk) / len(mk) if mk else 0:.0f}% won {100 * w / len(rs):.0f}%")
print("  early dogs, the own (raw ratings) read vs the result, by venue:")
for nm, f in (("home", lambda p: p["side"] == "home"), ("road", lambda p: p["side"] == "away")):
    for lg in ("nfl", "ncaaf", "nba"):
        rs = [p for p in ep if p["league"] == lg and f(p) and isinstance(p.get("own"), float) and isinstance(p.get("mkt"), float)]
        if rs:
            w = sum(p["result"] == "won" for p in rs)
            print(f"    {lg} {nm}: {w}-{len(rs) - w}; own said {100 * sum(p['own'] for p in rs) / len(rs):.0f}%, market {100 * sum(p['mkt'] for p in rs) / len(rs):.0f}%, won {100 * w / len(rs):.0f}%")
