"""11/15 - ARE WE GETTING THE BEST PICKS: THE FUNNEL on both replay boards (sizing_1114/lib.py). Every graded moneyline
side -150..+350 of every board day is either POSTED as a unit play (by kind) or KEPT OFF - and every kept-off side gets
the FIRST reason it failed, in the order the engine checks. Flat 1u vs the price, train (to 6/2025) / held, seasons.
 A gate TOO TIGHT = a kept-off cell that made money in both halves on both boards (and beats a random draw of kept-off
 sides of the same sport and price side). A gate TOO LOOSE = a posted cell that lost in both halves on both boards.
Then: within the kept-off dogs / favorites, the cells nearest the gates (gated dogs past the one Dog + one runner-up, the
floor's next dogs by score, favorites that pass the play bar but miss the 1-point edge, own read under the price).
Usage: python results/studies/sizing_1115/s3_funnel.py > results/studies/sizing_1115/s3_funnel.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
import lib as L  # noqa: E402

G = L.sv.GAMES


def why_off(r, on_game):
    """the first reason a side is not a unit play."""
    fav = r["odds"] < 100
    if on_game:
        return "x the game is on the board (the other side / a second pick)"
    if r.get("waiting"):
        return "0 waiting on injuries"
    if r["trap"]:
        return "1 a trap"
    if r["fighting"]:
        return "2 the own read is fighting it"
    if fav:
        if not r["good"]:
            return "F3 favorite: not a real play (under 53% / no named reason)"
        if not r["own_beats"]:
            return "F4 favorite: own read under the price"
        if not r["real_value"]:
            return "F5 favorite: own read over, no real value on the blend"
        m = L.own_margin(r)
        if m is not None and m < 1.0:
            return "F6 favorite: passes, edge under 1 point"
        return "F7 favorite: passes everything, not posted (tier / one a game)"
    if r.get("dog_score") is None:
        return "D3 dog: no dog score"
    n = r.get("n_reasons2")
    n = r["n_reasons"] if n is None else n
    if r.get("dog_gate"):
        if not r["dog_own_ok"]:
            return "D7 dog: GATED, the own-read rule fails"
        return "D8 dog: GATED and clean, not posted (a 2nd / 3rd dog)"
    if n <= 0:
        return "D4 dog: no named reason"
    if r["dog_score"] < 0:
        return "D5 dog: dog score under 0"
    return "D6 dog: score 0+ under the gate (the floor's next dogs)"


def run(name, board, by):
    posted, off = defaultdict(list), defaultdict(list)
    alloff = []
    for d in sorted(by):
        on = {}
        for r, u, k in board.get(d, []):
            on[(r["team"], r["opp"])] = k
        games = {G(r) for r, u, k in board.get(d, [])}
        for r in by[d]:
            if r.get("market", "ml") != "ml" or not -150 <= r["odds"] <= 350 or r["result"] not in ("won", "lost"):
                continue
            k = on.get((r["team"], r["opp"]))
            if k:
                posted[("fav " if r["odds"] < 100 else "dog ") + k].append((d, r, 1))
                continue
            w = why_off(r, G(r) in games)
            off[w].append((d, r, 1))
            if not w.startswith("x"):
                alloff.append((d, r, 1))
    print("=" * 30, f"BOARD {name}")
    print("POSTED (by kind and price side)")
    for c in sorted(posted, key=lambda c: -len(posted[c])):
        L.line(c, posted[c])
    L.line("EVERY POSTED PLAY", [x for v in posted.values() for x in v])
    print("KEPT OFF (the first reason)")
    for c in sorted(off):
        L.line(c, off[c])
    L.line("EVERY KEPT-OFF SIDE (not on a posted game)", alloff)
    print("KEPT OFF, by sport")
    for c in sorted(off):
        if c[0] in "x0":
            continue
        for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
            x = [t for t in off[c] if t[1]["league"] == lg]
            if len(x) >= 40:
                L.line(f"   {c[:34]:34s} {lg}", x)
    print("NEAR THE GATES")
    d8 = off["D8 dog: GATED and clean, not posted (a 2nd / 3rd dog)"]
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   gated clean dog not posted, {lg}", [t for t in d8 if t[1]["league"] == lg])
    L.line("   gated clean dog not posted, +100..+150", [t for t in d8 if t[1]["odds"] <= 150])
    L.line("   gated clean dog not posted, no college hoops", [t for t in d8 if t[1]["league"] != "ncaab"])
    d7 = off["D7 dog: GATED, the own-read rule fails"]
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
        L.line(f"   gated dog, own-read rule fails, {lg}", [t for t in d7 if t[1]["league"] == lg])
    d6 = off["D6 dog: score 0+ under the gate (the floor's next dogs)"]
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 99)):
        L.line(f"   under-gate dog, score {lo}..{hi}", [t for t in d6 if lo <= t[1]["dog_score"] < hi])
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   under-gate dog score 0+, {lg}", [t for t in d6 if t[1]["league"] == lg])
        L.line(f"   under-gate dog score 2+, {lg}", [t for t in d6 if t[1]["league"] == lg and t[1]["dog_score"] >= 2])
    L.line("   under-gate dog 0+, thin (the floor's kind), not nba/ncaaf/ncaab", [t for t in d6 if t[1].get("thin") and t[1]["league"] in ("nhl", "mlb", "nfl")])
    L.line("   under-gate dog 0+, +100..+150", [t for t in d6 if t[1]["odds"] <= 150])
    f6 = off["F6 favorite: passes, edge under 1 point"]
    L.line("   favorite passing, edge under 1 point", f6)
    f4 = off["F4 favorite: own read under the price"]
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   favorite, own read under the price, {lg}", [t for t in f4 if t[1]["league"] == lg])
    L.line("   favorite own under, weighed read (w_p) OVER the price", [t for t in f4 if t[1].get("w_p") is not None and t[1]["w_p"] * t[1]["dec"] > 1])
    L.line("   favorite own under by less than 1 point", [t for t in f4 if (L.own_margin(t[1]) or -99) > -1])
    f5 = off["F5 favorite: own read over, no real value on the blend"]
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   favorite own over, no real value, {lg}", [t for t in f5 if t[1]["league"] == lg])
    for lo, hi in ((0, 1), (1, 3), (3, 99)):
        L.line(f"   favorite own over by {lo}..{hi}, no real value", [t for t in f5 if lo <= (L.own_margin(t[1]) or -99) < hi])
    # the board's day against the best it kept off: on a day the board posted P plays, the top kept-off dog by score
    print("THE DAY'S BEST KEPT-OFF DOG BY SCORE (one a day, not on a posted game) vs the day's posted plays")
    best, bestg = [], []
    for d in sorted(by):
        games = {G(r) for r, u, k in board.get(d, [])}
        on = {(r["team"], r["opp"]) for r, u, k in board.get(d, [])}
        pool = [r for r in by[d] if r.get("market", "ml") == "ml" and 100 <= r["odds"] <= 350 and r["result"] in ("won", "lost")
                and (r["team"], r["opp"]) not in on and G(r) not in games and r.get("dog_score") is not None
                and not r["trap"] and not r["fighting"] and not r.get("waiting")]
        if pool:
            b = max(pool, key=lambda r: r["dog_score"])
            best.append((d, b, 1))
            if b["dog_score"] >= 3:
                bestg.append((d, b, 1))
    L.line("   the best kept-off dog a day", best)
    L.line("   ... when its score is 3+", bestg)
    return posted, off


def main():
    for name, (board, by) in L.boards().items():
        run(name, board, by)


if __name__ == "__main__":
    main()
