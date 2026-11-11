"""STUDY 1 (part A) - what each KIND of unit play earns in the replay under today's board (blib.PLAYS), flat 1u, train /
held out, and every kind cut by every sizing signal a row carries: sport, price band, home / road, thin, the own read's
margin over the price, the own read over the no-vig market (gap), the dog score, the move since the open (drift), the
number of named reasons, the weekday. THE BAR for a size-up (the 10/30 bar): the cell wins MORE vs the price than its
sibling in BOTH train and held out, with a sample (40+ a half), most seasons up. Cells printed: counted at the end.
Usage: python s1_cells.py > s1_cells.out"""
from collections import defaultdict
from datetime import datetime

from blib import PLAYS, cell, half

by_kind = defaultdict(list)
for d, r, u, k in PLAYS:
    by_kind[k].append((d, r, u))
N = [0]


def cuts(title, rs, key, order=None):
    print(f" {title}")
    g = defaultdict(list)
    for x in rs:
        k = key(x[1], x[0])
        if k is not None:
            g[k].append(x)
    for k in (order or sorted(g)):
        if len(g.get(k, [])) >= 15:
            cell(f"   {k}", g[k])
            N[0] += 1


def band(r, d=None):
    o = r["odds"]
    return ("-150..-131" if o <= -131 else "-130..-120" if o <= -120 else "-119..-101") if o < 0 else \
        ("+100..+119" if o <= 119 else "+120..+150" if o <= 150 else "+151..+199" if o <= 199 else "+200..+350")


def margin(r, d=None):
    if r.get("edge_own") is None:
        return None
    m = 100 * r["edge_own"] / r["dec"]
    return "own under the price" if m < 0 else "own 0-1 pt over" if m < 1 else "own 1-3 over" if m < 3 else "own 3-6 over" if m < 6 else "own 6+ over"


def gapb(r, d=None):
    from blib import gap
    g = gap(r)
    return None if g is None else "gap under 0" if g < 0 else "gap 0-2" if g < 2 else "gap 2-5" if g < 5 else "gap 5-7" if g < 7 else "gap 7+"


def drift(r, d=None):
    x = r.get("drift")
    return None if x is None else "money came TO us 2+ pts" if x <= -0.02 else "money ran AWAY 2+ pts" if x >= 0.02 else "flat since the open"


def score(r, d=None):
    s = r.get("dog_score")
    return None if s is None else "score under 0" if s < 0 else "score 0-3" if s < 3 else "score 3-6" if s < 6 else "score 6-9" if s < 9 else "score 9+"


print(f"TODAY'S BOARD IN THE REPLAY: {len(PLAYS)} unit plays ({sum(1 for p in PLAYS if half(p[0]) == 'train')} train / "
      f"{sum(1 for p in PLAYS if half(p[0]) == 'held')} held / {sum(1 for p in PLAYS if half(p[0]) == 'live')} live)\n")
print("EVERY KIND, flat 1u")
for k in sorted(by_kind, key=lambda k: -len(by_kind[k])):
    cell(k, by_kind[k])
cell("ALL favorites", [(d, r, u) for d, r, u, k in PLAYS if r["odds"] < 0])
cell("ALL dogs", [(d, r, u) for d, r, u, k in PLAYS if r["odds"] > 0])
cell("ALL 2u plays (today's sizes)", [(d, r, u) for d, r, u, k in PLAYS if u >= 2])
cell("ALL 1u plays", [(d, r, u) for d, r, u, k in PLAYS if u == 1])
cell("ALL ½u plays", [(d, r, u) for d, r, u, k in PLAYS if u == 0.5])

for k in sorted(by_kind, key=lambda k: -len(by_kind[k])):
    rs = by_kind[k]
    if len(rs) < 60:
        continue
    print(f"\n=== {k} ({len(rs)})")
    cuts("by sport", rs, lambda r, d: r["league"])
    cuts("by price", rs, band)
    cuts("home / road", rs, lambda r, d: "home" if r["home"] else "road")
    cuts("thin", rs, lambda r, d: None if r.get("thin") is None else "thin" if r["thin"] else "real edge")
    cuts("own read over the price", rs, margin)
    cuts("own read over the no-vig market", rs, gapb)
    cuts("dog score", rs, score)
    cuts("the move since the open", rs, drift)
    cuts("named reasons", rs, lambda r, d: f"{min(3, r.get('n_reasons2') if r.get('n_reasons2') is not None else r['n_reasons'])} reasons")
    cuts("weekday", rs, lambda r, d: datetime.strptime(d, "%Y-%m-%d").strftime("%a") if True else None, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    cuts("sport x price", rs, lambda r, d: f"{r['league']} {'short' if r['odds'] <= 150 else 'long'}" if r["odds"] > 0 else f"{r['league']} {'-119..-101' if r['odds'] > -120 else '-150..-120'}")
    cuts("sport x home", rs, lambda r, d: f"{r['league']} {'home' if r['home'] else 'road'}")
print(f"\n{N[0]} cells printed (15+ rows). At |z| 2 about {N[0] * 0.05:.0f} would clear by luck; 'better than its sibling in BOTH halves' by luck ~1 in 4 per pair.")
