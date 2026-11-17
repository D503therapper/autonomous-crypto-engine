"""11/17 FULL SWEEP - THE FAVORITES ON THE TWO REPLAY BOARDS (sizing_1114/lib.py: R1 = the 10/30 funnel rows, R2 = the
11/12 deep-program rows on today's code; 2023-10 -> 2026-11, closing prices; train = to 2025-06-30, held out = after,
live apart). Five studies, each cell named before looking and judged with the five checks (slib.five / slib.loses):
  S1  THE LOCK as the board posts it: by sport, by size, by price band, by the own read's gap over the market
  S2  THE VALUE PLAY (favorites, ½u): by sport, price band, the read's margin over the price, home / road
  S3  THE NBA FAVORITE PLAY (1u): by price band, home / road, the margin, how many study weights back it; 2u cells
  S4  EVERY POSTED FAVORITE: price band x home / road x sport - a size or a cut that holds across kinds
  S5  THE ⭐ ON A FAVORITE (live 1-3): the ⭐ favorites against the ⭐ dogs and against the favorites it passed over
A finding has to hold on BOTH boards (R2 is today's code; R1 carries the college hoops / football favorites R2's
honest dials no longer post - a cell that exists only on R1 is a cell of the OLD read).
Usage: python results/studies/sweep_1117/s1_favs.py > results/studies/sweep_1117/s1_favs.out"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402
import slib  # noqa: E402

half = L.half
FAV = lambda r: r["odds"] < 100  # noqa: E731


def gather(board, kinds):
    return [(d, r, u) for d, ps in board.items() for r, u, k in ps if k in kinds and FAV(r)]


def cells(title, pool, splits):
    print(f"-- {title}: the pool")
    slib.five("ALL", pool, None, half)
    out = []
    for nm, fn in splits:
        c = [x for x in pool if fn(x[1], x[2])]
        if len([x for x in c if half(x[0]) != "live"]) < 10:
            print(f"  {nm:58s} n {len(c)} - too few to judge")
            continue
        out.append((nm, slib.five(nm, c, pool, half), slib.loses("   ...as a CUT", c, pool, half)))
    return out


def margin(r):
    m = L.own_margin(r)
    return -99 if m is None else m


def gap(r):
    g = L.sv.gap(r)
    return -99 if g is None else g


PRICE = [("-150..-135", lambda r, u: -150 <= r["odds"] <= -135), ("-134..-120", lambda r, u: -134 <= r["odds"] <= -120),
         ("-119..-101", lambda r, u: -119 <= r["odds"] <= -101)]
SITE = [("home", lambda r, u: r["home"]), ("road", lambda r, u: not r["home"])]
verdict = []
for bn, (board, by) in L.boards().items():
    print("=" * 30, "BOARD", bn)
    lock = gather(board, ("lock", "solo"))
    v = cells("S1 THE LOCK", lock,
              [(f"sport {lg}", (lambda r, u, lg=lg: r["league"] == lg)) for lg in ("ncaab", "ncaaf", "nfl", "nhl", "mlb", "nba")]
              + [("posted 2u", lambda r, u: u >= 2), ("posted 1u", lambda r, u: u == 1), ("posted ½u", lambda r, u: u < 1)]
              + PRICE + SITE
              + [("own read 7+ over the market", lambda r, u: gap(r) >= 7), ("own read 3-7 over the market", lambda r, u: 3 <= gap(r) < 7),
                 ("own read under 3 over the market", lambda r, u: -90 < gap(r) < 3),
                 ("both reads 3c+ over the price", lambda r, u: (r.get("edge_own") or -1) >= .03 and L.read_margin(r, "lock") >= 3)])
    verdict += [(bn, "S1 Lock: " + n, a, b) for n, a, b in v]
    play = gather(board, ("play",))
    v = cells("S2 THE VALUE PLAY (favorites, ½u)", play,
              [(f"sport {lg}", (lambda r, u, lg=lg: r["league"] == lg)) for lg in ("ncaab", "ncaaf", "nfl", "nhl", "mlb", "nba")]
              + PRICE + SITE
              + [("margin 1-2 points", lambda r, u: 1 <= margin(r) * 100 < 2), ("margin 2-3 points", lambda r, u: 2 <= margin(r) * 100 < 3),
                 ("margin 3-5 points", lambda r, u: 3 <= margin(r) * 100 < 5), ("margin 5+ points", lambda r, u: margin(r) * 100 >= 5),
                 ("weighed read AND own read 3c+ over", lambda r, u: (r.get("edge_own") or -1) >= .03 and L.read_margin(r, "play") >= 3),
                 ("the drift is WITH us (the money came)", lambda r, u: (r.get("drift") or 0) > 0.01),
                 ("the drift is AGAINST us (the money left)", lambda r, u: (r.get("drift") or 0) < -0.01)])
    verdict += [(bn, "S2 value play: " + n, a, b) for n, a, b in v]
    nf = gather(board, ("nbafav",))
    nw = lambda r: sum(1 for x in (r.get("nba_fav_w") or {}).values() if (x or 0) > 0) if isinstance(r.get("nba_fav_w"), dict) else 0  # noqa: E731
    v = cells("S3 THE NBA FAVORITE PLAY (1u)", nf,
              PRICE + SITE
              + [("two+ study weights back it", lambda r, u: nw(r) >= 2), ("one study weight", lambda r, u: nw(r) == 1),
                 ("weighed read 2+ points over the price", lambda r, u: L.read_margin(r, "nbafav") >= 2),
                 ("weighed read under 2 points over", lambda r, u: L.read_margin(r, "nbafav") < 2),
                 ("games 6-20 of the season", lambda r, u: (r.get("season_games") or 99) <= 20),
                 ("after game 20", lambda r, u: (r.get("season_games") or 99) > 20)])
    verdict += [(bn, "S3 NBA favorite play: " + n, a, b) for n, a, b in v]
    if nf:
        print("   the NBA favorite play's sizes (the same plays): units won / risked, worst stretch")
        for nm, f in (("TODAY 1u", lambda r: 1.0), ("2u", lambda r: 2.0), ("2u at -150..-135, else 1u", lambda r: 2.0 if r["odds"] <= -135 else 1.0),
                      ("2u on the road, else 1u", lambda r: 1.0 if r["home"] else 2.0)):
            rs = [(d, r, f(r)) for d, r, u in nf if half(d) != "live"]
            net = sum(slib.flat(r) * u for d, r, u in rs)
            tr = sum(slib.flat(r) * u for d, r, u in rs if half(d) == "train")
            print(f"     {nm:28s} {net:+6.1f}u on {sum(u for _, _, u in rs):5.0f}u | train {tr:+6.1f}u held {net - tr:+6.1f}u | worst {slib.worst(rs, units=True):+.1f}u")
    allf = [(d, r, u) for d, ps in board.items() for r, u, k in ps if FAV(r)]
    v = cells("S4 EVERY POSTED FAVORITE", allf,
              PRICE + SITE
              + [(f"{s_} x {p_}", (lambda r, u, sf=sf, pf=pf: sf(r, u) and pf(r, u))) for s_, sf in SITE for p_, pf in PRICE]
              + [(f"sport {lg}", (lambda r, u, lg=lg: r["league"] == lg)) for lg in ("ncaab", "ncaaf", "nfl", "nhl", "mlb", "nba")]
              + [("the money left it (drift under -1c)", lambda r, u: (r.get("drift") or 0) < -0.01),
                 ("the money came to it (drift over +1c)", lambda r, u: (r.get("drift") or 0) > 0.01),
                 ("own read UNDER the price", lambda r, u: (r.get("edge_own") if r.get("edge_own") is not None else 1) < 0),
                 ("own read 3c+ over the price", lambda r, u: (r.get("edge_own") or -1) >= .03)])
    verdict += [(bn, "S4 every favorite: " + n, a, b) for n, a, b in v]
    stars = [(d, r, u, k) for d, r, u, k in S.stars(board, S.today)]
    sf_ = [(d, r, u) for d, r, u, k in stars if FAV(r)]
    sd_ = [(d, r, u) for d, r, u, k in stars if not FAV(r)]
    print("-- S5 THE ⭐ ON A FAVORITE vs ON A DOG (the ⭐ = the opening board's best unit play whose read beats its price)")
    slib.five("the ⭐ on a FAVORITE", sf_, sf_ + sd_, half)
    slib.five("the ⭐ on a DOG", sd_, sf_ + sd_, half)
    slib.five("the ⭐ favorites vs EVERY posted favorite", sf_, allf, half)
    for lg in ("ncaab", "nhl", "nba", "nfl", "ncaaf"):
        c = [x for x in sf_ if x[1]["league"] == lg]
        if len(c) >= 10:
            slib.five(f"the ⭐ on a {lg} favorite", c, sf_ + sd_, half)
    seen = {id(r) for _, r, _ in sf_}
    day_fav = {d for d, _, _ in sf_}
    passed = [(d, r, u) for d, r, u in allf if d in day_fav and id(r) not in seen]
    slib.five("the favorites the ⭐ PASSED OVER on its days", passed, allf, half)
    lk = [x for x in sf_ if any(x[1] is r for _, r, _ in lock)]
    slib.five("the ⭐ on the Lock", lk, sf_ + sd_, half)
print("=" * 30, "VERDICT: a cell CLEARS only on BOTH boards (a size-up: slib.five; a cut: slib.loses)")
names = sorted({n for _, n, _, _ in verdict})
for n in names:
    up = {b: a["clears"] for b, m, a, c in verdict if m == n}
    dn = {b: c["clears"] for b, m, a, c in verdict if m == n}
    if any(up.values()) or any(dn.values()):
        print(f"  {n:62s} size-up clears on {[b for b, x in up.items() if x] or '-'} of {sorted(up)}; cut clears on {[b for b, x in dn.items() if x] or '-'}")
print("  (a line above with both boards in one list = a finding; anything else is a lead at most)")
