"""STUDY 6b - THE FAVORITE THE ENGINE'S OWN WEIGHTS ARE AGAINST. Every favorite -150..-101 in the funnel rows (closing
prices, every sport), by where the weighed read (w_p - the market number plus every study weight on that side) sits
against the no-vig market. A lean is a who-wins call on a favorite in this band: is a favorite whose weighed read is
UNDER the market a bad lean in every sport, and from how far under? Then the dog ACROSS from it, and the leans the
replay board actually posted. 6 sports x 4 bands + neighbours = ~40 cells; ~2 would clear |z| 2 by luck.
Usage: python s6b_weighed_under.py > s6b_weighed_under.out"""
from collections import defaultdict

from blib import cell, sv

rows = sv.rows
by_game = defaultdict(list)
for r in rows:
    by_game[(r["date"], frozenset((r["team"], r["opp"])))].append(r)


def wg(r):
    return None if r.get("w_p") is None or r.get("p_market") is None else 100 * (r["w_p"] - r["p_market"])


favs = [r for r in rows if -150 <= r["odds"] <= -101 and wg(r) is not None]
print(f"favorites -150..-101 with a weighed read: {len(favs)} (of {sum(1 for r in rows if -150 <= r['odds'] <= -101)})")
for lg in ("ALL", "nhl", "nba", "ncaab", "mlb", "nfl", "ncaaf"):
    rs = [r for r in favs if lg == "ALL" or r["league"] == lg]
    print(f"\n=== {lg} ({len(rs)})")
    for name, f in (("weighed 3+ UNDER the market", lambda g: g <= -3), ("weighed 2+ UNDER", lambda g: g <= -2), ("weighed 1+ UNDER", lambda g: g <= -1),
                    ("weighed UNDER (any)", lambda g: g < 0), ("weighed 0-1 under", lambda g: -1 < g < 0), ("weighed 0-2 OVER", lambda g: 0 <= g < 2),
                    ("weighed 2+ OVER", lambda g: g >= 2)):
        x = [(r["date"], r, 1) for r in rs if f(wg(r))]
        if len(x) >= 15:
            cell(f"   {name}", x)
    # the dog across from a favorite weighed 2+ under
    dogs = []
    for r in rs:
        if wg(r) <= -2:
            for o in by_game[(r["date"], frozenset((r["team"], r["opp"])))]:
                if o is not r and o["team"] == r["opp"]:
                    dogs.append((o["date"], o, 1))
    if len(dogs) >= 15:
        cell("   THE DOG ACROSS from a favorite weighed 2+ under", dogs)

print("\n=== THE LEANS THE REPLAY BOARD POSTED (favorites -150..-101)")
leans = [r for r in rows if r.get("lean") and -150 <= r["odds"] <= -101]
for lg in ("ALL", "nhl", "nba", "ncaab", "mlb"):
    rs = [r for r in leans if lg == "ALL" or r["league"] == lg]
    cell(f"{lg} leans, weighed UNDER the market", [(r["date"], r, 1) for r in rs if wg(r) is not None and wg(r) < 0])
    cell(f"{lg} leans, weighed 2+ UNDER", [(r["date"], r, 1) for r in rs if wg(r) is not None and wg(r) <= -2])
    cell(f"{lg} leans, weighed over / no weighed read", [(r["date"], r, 1) for r in rs if wg(r) is None or wg(r) >= 0])
