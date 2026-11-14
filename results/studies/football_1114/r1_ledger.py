"""11/14 FOOTBALL - R1 THE LEDGER: where the football board's money comes from and where it leaks, on TODAY'S code.
Rows: funnel5.py (every football board day 2018-08 -> 2026-11-13, every date gate open, closes, the whole board).
Every football unit play the board makes (the Lock / the Dog / one-game-day / value plays / the runner-up dog / the
floor / the Monday-Thursday night pick), cut by kind, league, favorite / dog, price band, home / road / neutral,
conference game or not (college; inferred from the schedule), the week of the season, the month; flat at the close AND
at its own units (today's sizing). Then the LEANS (no units) by the same cuts, and the candidates the board did NOT
take that sit next to a profitable cell (the under-bet check).
Train = the 2018-22 seasons, held out = 2023-26 (the 2026 season is the live one).
The dog score / weighed read carry study weights fit with every season seen - a weight-picked cell's halves are not a
clean out-of-sample test (said where it matters).
Usage: python results/studies/football_1114/r1_ledger.py > results/studies/football_1114/r1_out.txt"""
from collections import defaultdict
import flib as F

R = F.replay(markets=("ml", "spread"))
SIDE = {}
for lg in ("nfl", "ncaaf"):
    for s in F.sides(lg):
        SIDE[(s["id"], s["side"])] = s
for r in R:
    s = SIDE.get((r["gid"], r["side"])) or {}
    r["conf_game"] = s.get("conf_game")
    r["week"] = s.get("week")
    r["fbs_both"] = bool(s.get("fbs") and s.get("ofbs"))
    r["neutral"] = str(r.get("neutral_g")) == "1"
    r["month"] = int(r["date"][5:7])
print(f"{len(R)} football rows ({sum(1 for r in R if r['market'] == 'ml')} moneyline), "
      f"{len({r['date'] for r in R})} board days, seasons {sorted({r['season'] for r in R})}")
U = [r for r in R if r.get("kind")]
L = [r for r in R if r.get("lean") and not r.get("kind")]


def band(o):
    for lo, hi, nm in ((-150, -131, "-150..-131"), (-130, -116, "-130..-116"), (-115, -101, "-115..-101"), (100, 150, "+100..+150"),
                       (151, 200, "+151..+200"), (201, 350, "+201..+350")):
        if lo <= o <= hi:
            return nm
    return "other"


def cuts(rs, title):
    print(f"\n==== {title} ====")
    F.rline("ALL", rs)
    for lg in ("nfl", "ncaaf"):
        x = [r for r in rs if r["league"] == lg]
        print(f" -- {lg.upper()}")
        F.rline("all", x)
        for nm, f in (("favorites", lambda r: r["odds"] < 100), ("dogs", lambda r: r["odds"] >= 100)):
            F.rline(nm, [r for r in x if f(r)])
        for k in sorted({r["kind"] or "lean" for r in x}):
            for nm, f in (("fav", lambda r: r["odds"] < 100), ("dog", lambda r: r["odds"] >= 100)):
                y = [r for r in x if (r["kind"] or "lean") == k and f(r)]
                if y:
                    F.rline(f"kind {k} {nm}", y)
        for b in ("-150..-131", "-130..-116", "-115..-101", "+100..+150", "+151..+200", "+201..+350", "other"):
            y = [r for r in x if band(r["odds"]) == b and r["market"] == "ml"]
            if y:
                F.rline(f"price {b}", y)
        y = [r for r in x if r["market"] == "spread"]
        if y:
            F.rline("spread (any)", y)
        for nm, f in (("home", lambda r: r["home"] and not r["neutral"]), ("road", lambda r: not r["home"] and not r["neutral"]),
                      ("neutral", lambda r: r["neutral"])):
            for side, g in (("fav", lambda r: r["odds"] < 100), ("dog", lambda r: r["odds"] >= 100)):
                y = [r for r in x if f(r) and g(r)]
                if y:
                    F.rline(f"{nm} {side}", y)
        if lg == "ncaaf":
            for nm, f in (("conference game", lambda r: r["conf_game"]), ("non-conference", lambda r: r["conf_game"] is False)):
                for side, g in (("fav", lambda r: r["odds"] < 100), ("dog", lambda r: r["odds"] >= 100)):
                    y = [r for r in x if f(r) and g(r)]
                    if y:
                        F.rline(f"{nm} {side}", y)
        for nm, lo, hi in (("weeks 1-3", 1, 3), ("weeks 4-6", 4, 6), ("weeks 7-10", 7, 10), ("weeks 11+", 11, 99)):
            for side, g in (("fav", lambda r: r["odds"] < 100), ("dog", lambda r: r["odds"] >= 100)):
                y = [r for r in x if r["week"] and lo <= r["week"] <= hi and g(r)]
                if y:
                    F.rline(f"{nm} {side}", y)


cuts(U, "THE UNIT PLAYS (today's code)")
cuts(L, "THE LEANS (no units)")
print("\n==== SATURDAYS: college unit plays a day ====")
by = defaultdict(list)
for r in U:
    if r["league"] == "ncaaf":
        by[r["date"]].append(r)
for k in (1, 2, 3):
    days = [v for v in by.values() if (len(v) == k if k < 3 else len(v) >= 3)]
    F.rline(f"days with {k}{'+' if k == 3 else ''} college unit plays ({len(days)} days)", [r for v in days for r in v])
print("\n==== EVERY football unit play listed for 2026 (the live season) ====")
for r in sorted([r for r in U if r["season"] == 2026], key=lambda r: r["date"]):
    print(f"  {r['date']} {r['league']:5s} {r['kind']:8s} {r['team']:22s} {r['odds']:+5d} {r['market']:6s} {r.get('units')}u {r['result']}")
