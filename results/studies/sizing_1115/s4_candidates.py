"""11/15 - THE FUNNEL'S CANDIDATES, CHECKED: the kept-off cells of s3_funnel.out that were up in both halves on both
boards, each through the five checks (fair inputs / held-out half / seasons / a dose / a placebo), and then AS A PLAY -
added to the board the way the engine would post it (one a day, ½u), units and the worst stretch before / after.
 C1  the kept-off HOCKEY dog with a named reason and a dog score 0+ under the Dog gate (the floor's kind, on a day the
     floor was already full or it was outranked)
 C2  the kept-off GATED clean hockey dog (a 2nd / 3rd gated dog the same day)
 C3  the day's best kept-off dog by score at 3+ (any sport)
 C4  a favorite whose own read is under the price but whose WEIGHED read is over it
 C5  the NBA favorite play at 2u (a posted kind - does it win more vs its price than the other favorite kinds?)
Usage: python results/studies/sizing_1115/s4_candidates.py > results/studies/sizing_1115/s4_candidates.out"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402
import s3_funnel as F  # noqa: E402

G = L.sv.GAMES


def kept_off(board, by):
    out = []
    for d in sorted(by):
        on = {(r["team"], r["opp"]) for r, u, k in board.get(d, [])}
        games = {G(r) for r, u, k in board.get(d, [])}
        for r in by[d]:
            if r.get("market", "ml") != "ml" or not -150 <= r["odds"] <= 350 or r["result"] not in ("won", "lost"):
                continue
            if (r["team"], r["opp"]) in on or G(r) in games:
                continue
            out.append((d, r, F.why_off(r, False)))
    return out


def seasons(rs):
    s = defaultdict(lambda: [0, 0, 0.0])
    for d, r, _ in rs:
        if L.half(d) == "live":
            continue
        x = s[L.season(d)]
        x[0] += r["result"] == "won"
        x[1] += r["result"] == "lost"
        x[2] += L.flat(r)
    return "  ".join(f"{k} {w}-{l} {100 * f / max(1, w + l):+.0f}%" for k, (w, l, f) in sorted(s.items()))


def one_a_day(rs, key):
    by = defaultdict(list)
    for d, r, u in rs:
        by[d].append(r)
    return [(d, max(v, key=key), 1) for d, v in sorted(by.items())]


def with_extra(board, extra, units=0.5):
    """the board + the extra plays [(d, r, _)] as kind 'extra' at `units`."""
    nb = {d: list(ps) for d, ps in board.items()}
    for d, r, _ in extra:
        nb.setdefault(d, []).append((r, units, "extra"))
    return nb


def run(name, board, by):
    print("=" * 30, f"BOARD {name}")
    st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
    T = lambda d, r, u, k, ps: max(1.0, u) if (d, r["team"], k) in st else u   # noqa: E731
    off = kept_off(board, by)
    nhl_dogs = [(d, r, 1) for d, r, w in off if r["league"] == "nhl" and r["odds"] >= 100]

    print("C1 the kept-off hockey dog, named reason, score 0+ under the gate")
    c1 = [(d, r, 1) for d, r, w in off if r["league"] == "nhl" and w.startswith("D6")]
    L.line("all", c1)
    print("     seasons:", seasons(c1))
    for lo, hi in ((0, 2), (2, 4), (4, 99)):
        L.line(f"   score {lo}..{hi}", [t for t in c1 if lo <= t[1]["dog_score"] < hi])
    for lo, hi in ((100, 129), (130, 159), (160, 350)):
        L.line(f"   price +{lo}..+{hi}", [t for t in c1 if lo <= t[1]["odds"] <= hi])
    L.line("   thin (own read under 3c over the price)", [t for t in c1 if t[1].get("thin")])
    L.line("   NOT thin (the floor skips it)", [t for t in c1 if not t[1].get("thin")])
    L.line("   own read not under the market (dog_own_ok)", [t for t in c1 if t[1]["dog_own_ok"]])
    L.line("   home", [t for t in c1 if t[1]["home"]])
    L.line("   road", [t for t in c1 if not t[1]["home"]])
    hk_on = lambda d: any(r["league"] == "nhl" for r, u, k in board.get(d, []))   # noqa: E731
    L.line("   on a day the board HAS a hockey unit play", [t for t in c1 if hk_on(t[0])])
    L.line("   on a day the board has NO hockey unit play", [t for t in c1 if not hk_on(t[0])])
    n_un = lambda d: len(board.get(d, []))   # noqa: E731
    L.line("   on a day with 2+ unit plays already", [t for t in c1 if n_un(t[0]) >= 2])
    c1s = [t for t in c1 if t[1]["dog_score"] >= 2]
    print(f"     PLACEBO (score 0+): a random {len([t for t in c1 if L.half(t[0]) != 'live'])} kept-off hockey dogs did as well "
          f"{L.placebo(c1, nhl_dogs)} of 2,000; (score 2+): {L.placebo(c1s, nhl_dogs)} of 2,000; "
          f"score 2+ vs a random draw of the score-0+ cell: {L.placebo(c1s, c1)} of 2,000")
    base = L.schedule("the board today", board, T)
    for nm, pool, key in (("+ the best kept-off hockey dog a day, score 0+, ½u", c1, lambda r: r["dog_score"]),
                          ("+ the best kept-off hockey dog a day, score 2+, ½u", c1s, lambda r: r["dog_score"]),
                          ("+ ... score 2+, only +100..+159, ½u", [t for t in c1s if t[1]["odds"] <= 159], lambda r: r["dog_score"])):
        ex = one_a_day(pool, key)
        L.line("   " + nm[2:40] + " (one a day, flat)", ex)
        print("     seasons:", seasons(ex))
        L.schedule(nm, with_extra(board, ex), T)
        L.schedule(nm.replace("½u", "1u"), with_extra(board, ex, 1.0), T)
    ex_all = [(d, r, 1) for d, r, _ in c1s]
    L.schedule("+ EVERY kept-off hockey dog score 2+, ½u", with_extra(board, ex_all), T)

    print("C2 the kept-off GATED clean hockey dog (a 2nd / 3rd gated dog)")
    c2 = [(d, r, 1) for d, r, w in off if r["league"] == "nhl" and w.startswith("D8")]
    L.line("all", c2)
    print("     seasons:", seasons(c2), "| placebo vs kept-off hockey dogs:", L.placebo(c2, nhl_dogs), "of 2,000")
    L.schedule("+ every kept-off gated hockey dog, ½u", with_extra(board, c2), T)

    print("C3 the day's best kept-off dog by score, 3+ (any sport; clean of trap / fighting / waiting)")
    pool = [(d, r, 1) for d, r, w in off if r["odds"] >= 100 and r.get("dog_score") is not None and w[0] not in "012"]
    c3 = [t for t in one_a_day(pool, lambda r: r["dog_score"]) if t[1]["dog_score"] >= 3]
    L.line("all", c3)
    print("     seasons:", seasons(c3))
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   {lg}", [t for t in c3 if t[1]["league"] == lg])
    nr = lambda r: (r["n_reasons"] if r.get("n_reasons2") is None else r["n_reasons2"])   # noqa: E731
    L.line("   with a named reason", [t for t in c3 if nr(t[1]) > 0])
    L.line("   no named reason", [t for t in c3 if nr(t[1]) <= 0])
    L.line("   gated", [t for t in c3 if t[1].get("dog_gate")])
    L.line("   not gated", [t for t in c3 if not t[1].get("dog_gate")])
    L.schedule("+ the day's best kept-off dog at 3+, ½u", with_extra(board, c3), T)

    print("C4 a favorite -150..-101, own read under the price, WEIGHED read over it (kept off)")
    c4 = [(d, r, 1) for d, r, w in off if w.startswith("F4") and r.get("w_p") is not None and r["w_p"] * r["dec"] > 1]
    L.line("all", c4)
    print("     seasons:", seasons(c4))
    for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
        L.line(f"   {lg}", [t for t in c4 if t[1]["league"] == lg])
    favs = [(d, r, 1) for d, r, w in off if w.startswith("F4")]
    print("     placebo vs kept-off own-under favorites:", L.placebo(c4, favs), "of 2,000")
    for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 99)):
        L.line(f"   weighed read {lo}..{hi} points over the price", [t for t in c4 if lo <= 100 * (t[1]["w_p"] - 1 / t[1]["dec"]) < hi])

    print("C5 THE NBA FAVORITE PLAY (posted 1u): does it earn 2u?")
    plays = [(d, r, u, k) for d in sorted(board) for r, u, k in board[d]]
    nf = [(d, r, u) for d, r, u, k in plays if k == "nbafav"]
    L.line("the NBA favorite play", nf)
    print("     seasons:", seasons(nf))
    favp = [(d, r, u) for d, r, u, k in plays if r["odds"] < 100]
    two = [(d, r, u) for d, r, u, k in plays if u == 2.0]
    L.line("   every other posted favorite", [(d, r, u) for d, r, u, k in plays if r["odds"] < 100 and k != "nbafav"])
    L.line("   the board's 2u plays (the size it would join)", two)
    print(f"     placebo: a random same-size draw of the board's posted favorites did as well {L.placebo(nf, favp)} of 2,000; "
          f"of every posted play {L.placebo(nf, [(d, r, u) for d, r, u, k in plays])} of 2,000")
    for lo, hi in ((-150, -131), (-130, -116), (-115, -101)):
        L.line(f"   price {lo}..{hi}", [t for t in nf if lo <= t[1]["odds"] <= hi])
    for lo, hi in ((6, 20), (21, 45), (46, 99)):
        L.line(f"   the team's game {lo}..{hi} of the season", [t for t in nf if lo <= (t[1].get("season_games") or 0) <= hi])
    wsum = lambda r: sum((r.get("nba_fav_w") or {}).values()) if isinstance(r.get("nba_fav_w"), dict) else 0   # noqa: E731
    vals = sorted(wsum(t[1]) for t in nf)
    if vals:
        med = vals[len(vals) // 2]
        L.line(f"   weights net over the median ({med:.3f})", [t for t in nf if wsum(t[1]) > med])
        L.line("   weights net at / under the median", [t for t in nf if wsum(t[1]) <= med])
    # the kept-off NBA favorites the weights back (why not posted?)
    nb = [(d, r, 1) for d, r, w in off if r["league"] == "nba" and r["odds"] < 100 and isinstance(r.get("nba_fav_w"), dict)
          and sum(r["nba_fav_w"].values()) > 0]
    L.line("   KEPT-OFF NBA favorites with net-positive weights", nb)
    byw = defaultdict(list)
    for d, r, w in off:
        if r["league"] == "nba" and r["odds"] < 100 and isinstance(r.get("nba_fav_w"), dict) and sum(r["nba_fav_w"].values()) > 0:
            byw[w].append((d, r, 1))
    for w, x in sorted(byw.items()):
        L.line(f"      {w[:46]}", x)


if __name__ == "__main__":
    random.seed(1115)
    for name, (board, by) in L.boards().items():
        run(name, board, by)
