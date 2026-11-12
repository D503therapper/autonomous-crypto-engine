"""11/12 DEEP PROGRAM - A8: THE ABSENCE POINTS ON THE OWN READ, LIVE. sports_absences.penalty takes 3-12 points off a
team's OWN read when a key man is out (NFL QB -8, NBA top scorer -9, NHL top scorer -6 ...) - numbers measured 10/2
against a ratings read that did NOT know the injury. Today the own read starts from the books' price in every league
(trust ~0; hockey = the line + rest), and the price already has the injury - so the points come off twice and the side
ACROSS reads 'own read over the price'. The live journal: every graded moneyline pick by whether the read was moved by
the opponent's missing men ('opponent missing key players' in its reasons).
Usage: python results/studies/deep_1112/a8_absence_live.py > results/studies/deep_1112/a8_absence_live.out"""
import json, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = json.load(open(os.path.join(ROOT, "data/sports/pick_journal.json")))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def line(name, rs):
    rs = [r for r in rs if r.get("result") in ("won", "lost")]
    if not rs:
        print(f"  {name:58s} none")
        return
    w = sum(r["result"] == "won" for r in rs)
    n = len(rs)
    fl = sum((dec(r["odds"]) - 1) if r["result"] == "won" else -1 for r in rs)
    un = sum(r.get("pnl_units") or 0 for r in rs)
    ps = [r.get("price_says") or 0.5 for r in rs]
    z = (w - sum(ps)) / math.sqrt(sum(p * (1 - p) for p in ps))
    own = [r["own_read"] for r in rs if r.get("own_read")]
    need = [1 / dec(r["odds"]) for r in rs]
    print(f"  {name:58s} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% units {un:+6.2f} | own read said {100 * sum(own) / max(1, len(own)):4.1f}%, the price needed {100 * sum(need) / n:4.1f}%,"
          f" the no-vig price said {100 * sum(ps) / n:4.1f}%, won {100 * w / n:4.1f}% (z {z:+.1f} vs the price)")


opp_out = lambda r: any("opponent missing key players" in str(x) for x in (r.get("reasons") or []))     # noqa: E731
ml = [r for r in J if r["market"] == "ml"]
units = lambda r: not r.get("lean") and (r.get("units") or 0) > 0     # noqa: E731
print("ALL SPORTS, moneyline picks")
line("the read moved by the OPPONENT's missing men: unit plays", [r for r in ml if opp_out(r) and units(r)])
line("                                             leans", [r for r in ml if opp_out(r) and not units(r)])
line("no absence points on it: unit plays", [r for r in ml if not opp_out(r) and units(r)])
line("                         leans", [r for r in ml if not opp_out(r) and not units(r)])
for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
    print(lg.upper())
    line("opponent missing key players: unit plays", [r for r in ml if r["league"] == lg and opp_out(r) and units(r)])
    line("   dogs", [r for r in ml if r["league"] == lg and opp_out(r) and units(r) and r["odds"] > 0])
    line("   favorites", [r for r in ml if r["league"] == lg and opp_out(r) and units(r) and r["odds"] < 0])
    line("no absence points: unit plays", [r for r in ml if r["league"] == lg and not opp_out(r) and units(r)])
    line("   dogs", [r for r in ml if r["league"] == lg and not opp_out(r) and units(r) and r["odds"] > 0])
print("UNIT PLAYS WHOSE OWN READ BEAT THE PRICE ONLY BY THE ABSENCE POINTS (own read over the price, the no-vig price + 1 under it)")
rs = []
for r in ml:
    if units(r) and opp_out(r) and r.get("own_read") and r.get("price_says"):
        need = 1 / dec(r["odds"])
        if r["own_read"] > need and r["own_read"] - r["price_says"] >= 0.03:
            rs.append(r)
line("own read 3+ points over the no-vig price, opponent's men out", rs)
for r in rs:
    print(f"      {r['date']} {r['league']:5s} {r['kind']:5s} {r['team']:16s} {r['odds']:+5d} own {r['own_read']:.3f} no-vig {r['price_says']:.3f} {r['result']} {r.get('score')} | {[x for x in r['reasons'] if 'missing' in str(x)]}")
