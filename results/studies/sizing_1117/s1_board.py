"""11/17 - SIZING: "the half a units is just retarded ... I feel like we could do better with the sizing" (the owner, 11/16).

The two replay boards of the 11/14 / 11/15 sizing studies (sizing_1114/lib.py: R1 = the 10/30 funnel rows, R2 = the 11/12
deep-program rows on today's code; 2023-10 -> 2026-11, closing prices; train = to 2025-06-30, held out = after; live
apart), today's sizes + the ⭐ raise.
 (0) what each kind earns now
 (1) THE THIN-EDGE QUESTION: every ½u kind split by the OWN read's edge over the price (under it / 0-3c thin / 3c+ real)
     and by the read its units ride on - the record, the units, and the share of the kind's LOST units in each band
 (2) THE SIZE-UP CELLS, named before looking: a cell earns the bigger size only when it wins MORE vs the price than the
     rest of its kind in BOTH halves on BOTH boards, a random same-size set of its kind does as well under 5% of the time,
     and the worst stretch does not blow out. Each one: the cell / its siblings / the placebo / the board before -> after.
Usage: python results/studies/sizing_1117/s1_board.py > results/studies/sizing_1117/s1_board.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402

FOOT = ("nfl", "ncaaf")
HALF_KINDS = ("floor", "floorfb", "nbafloor", "dogplay", "play", "backup")


def own_edge(r):
    return r.get("edge_own")


def band(r):
    e = own_edge(r)
    if e is None:
        return "no own read"
    return "own read UNDER the price" if e < 0 else "own read 0-3c over (THIN)" if e < 0.03 else "own read 3c+ over (REAL)"


def star_fn(board):
    st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
    return (lambda d, r, u, k: max(1.0, u) if (d, r["team"], k) in st else u), st


def kind_table(board, star):
    print("-- (0) every kind at today's size (the ⭐ raise in)")
    by = defaultdict(list)
    for d, ps in board.items():
        for r, u, k in ps:
            kk = k
            if k == "dog":
                kk = "dog nba" if r["league"] == "nba" else "dog short (+100..+150) 2u" if r["odds"] <= 150 else "dog long (+151..+350) ½u"
            if k == "lock":
                kk = f"lock {u:g}u"
            by[kk].append((d, r, star(d, r, u, k)))
    for kk in sorted(by):
        L.line(kk, by[kk], units=True)


def thin_table(board, star):
    print("-- (1) the ½u plays by the own read's edge: flat ROI, and the share of the kind's LOST units (train + held)")
    for kind in ("floor+floorfb", "nbafloor", "dogplay", "play", "backup", "dog long", "ALL ½u plays"):
        rs = []
        for d, ps in board.items():
            for r, u, k in ps:
                if u != 0.5:
                    continue
                ok = (kind == "ALL ½u plays" or (kind == "floor+floorfb" and k in ("floor", "floorfb"))
                      or k == kind or (kind == "dog long" and k == "dog" and r["league"] != "nba"))
                if ok:
                    rs.append((d, r, u))
        if not rs:
            continue
        lost_all = sum(u for d, r, u in rs if r["result"] == "lost" and L.half(d) != "live")
        print(f"  [{kind}]")
        for b in ("own read UNDER the price", "own read 0-3c over (THIN)", "own read 3c+ over (REAL)", "no own read"):
            c = [x for x in rs if band(x[1]) == b]
            if not c:
                continue
            lost = sum(u for d, r, u in c if r["result"] == "lost" and L.half(d) != "live")
            net = sum(L.pnl(r, u) for d, r, u in c if L.half(d) != "live")
            o = L.line("   " + b, c)
            print(f"        -> {100 * lost / lost_all if lost_all else 0:4.0f}% of the kind's lost units, net {net:+.1f}u at ½u")


# ---------------------------------------------------------------- the size-up cells (named before looking)
def rm(r, k):
    return L.read_margin(r, k)


def om(r):
    m = L.own_margin(r)
    return -99 if m is None else m


CELLS = [
    # name, the kind filter, the cell, the new size
    ("floor dog, dog score 3+ -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: (r.get("dog_score") or -9) >= 3, 1.0),
    ("floor dog, dog score 4+ -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: (r.get("dog_score") or -9) >= 4, 1.0),
    ("floor dog, +100..+150 -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: r["odds"] <= 150, 1.0),
    ("floor dog, the weighed dog read 2c+ over the price -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: rm(r, "dog") >= 2, 1.0),
    ("floor dog, hockey -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: r["league"] == "nhl", 1.0),
    ("floor dog, NFL (road by the 11/15 rule) -> 1u", lambda r, u, k: k in ("floor", "floorfb"), lambda r, u, k: r["league"] == "nfl" and not r["home"], 1.0),
    ("NBA floor, own read over the price -> 1u", lambda r, u, k: k == "nbafloor", lambda r, u, k: om(r) > 0, 1.0),
    ("NBA floor, dog score 3+ -> 1u", lambda r, u, k: k == "nbafloor", lambda r, u, k: (r.get("dog_score") or -9) >= 3, 1.0),
    ("NBA floor, +100..+150 -> 1u", lambda r, u, k: k == "nbafloor", lambda r, u, k: r["odds"] <= 150, 1.0),
    ("runner-up dog, own read over the price -> 1u", lambda r, u, k: k == "dogplay", lambda r, u, k: om(r) > 0, 1.0),
    ("runner-up dog, dog score 6+ -> 1u", lambda r, u, k: k == "dogplay", lambda r, u, k: (r.get("dog_score") or -9) >= 6, 1.0),
    ("value play, own read 3c+ over (not thin) -> 1u", lambda r, u, k: k == "play", lambda r, u, k: (own_edge(r) or -1) >= 0.03, 1.0),
    ("value play, own read 5 pts+ over what the price needs -> 1u", lambda r, u, k: k == "play", lambda r, u, k: om(r) >= 5, 1.0),
    ("value play, the weighed read over the price too -> 1u", lambda r, u, k: k == "play", lambda r, u, k: r.get("w_p") is not None and r["w_p"] * r["dec"] > 1, 1.0),
    ("NBA favorite play, own read over the price too -> 2u", lambda r, u, k: k == "nbafav", lambda r, u, k: om(r) > 0, 2.0),
    ("NBA favorite play, -130..-101 -> 2u", lambda r, u, k: k == "nbafav", lambda r, u, k: r["odds"] >= -130, 2.0),
    ("long Dog (+151..+350), own read over the price -> 2u", lambda r, u, k: k == "dog" and r["league"] != "nba" and r["odds"] > 150, lambda r, u, k: om(r) > 0, 2.0),
    ("long Dog, own read 3c+ over (not thin) -> 2u", lambda r, u, k: k == "dog" and r["league"] != "nba" and r["odds"] > 150, lambda r, u, k: (own_edge(r) or -1) >= 0.03, 2.0),
    ("long Dog, +151..+199 -> 1u", lambda r, u, k: k == "dog" and r["league"] != "nba" and r["odds"] > 150, lambda r, u, k: r["odds"] <= 199, 1.0),
    ("short Dog (2u), own read 3c+ over (not thin) -> 3u", lambda r, u, k: k == "dog" and u == 2.0, lambda r, u, k: (own_edge(r) or -1) >= 0.03, 3.0),
    ("short Dog (2u), both reads over the price -> 3u", lambda r, u, k: k == "dog" and u == 2.0, lambda r, u, k: om(r) > 0 and rm(r, k) > 0, 3.0),
    ("short Dog (2u), dog score 8+ -> 3u", lambda r, u, k: k == "dog" and u == 2.0, lambda r, u, k: (r.get("dog_score") or -9) >= 8, 3.0),
    ("NBA Dog, own read over the price (1u) -> 2u", lambda r, u, k: k == "dog" and r["league"] == "nba", lambda r, u, k: om(r) > 0, 2.0),
    ("the 2u Lock, both reads over the price -> 3u", lambda r, u, k: k == "lock" and u == 2.0, lambda r, u, k: om(r) > 0 and r.get("w_p") is not None and r["w_p"] * r["dec"] > 1, 3.0),
    ("the 2u Lock, own read 3-7 over the market -> 3u", lambda r, u, k: k == "lock" and u == 2.0, lambda r, u, k: 3 <= (L.sv.gap(r) or 0) < 7, 3.0),
    ("ANY ½u play, both reads over the price -> 1u", lambda r, u, k: u == 0.5, lambda r, u, k: om(r) > 0 and rm(r, k) > 0, 1.0),
    ("ANY ½u play, own read 3c+ over (not thin) -> 1u", lambda r, u, k: u == 0.5, lambda r, u, k: (own_edge(r) or -1) >= 0.03, 1.0),
    ("ANY ½u DOG at +100..+150 -> 1u", lambda r, u, k: u == 0.5 and r["odds"] >= 100, lambda r, u, k: r["odds"] <= 150, 1.0),
    ("ANY ½u FAVORITE -> 1u", lambda r, u, k: u == 0.5, lambda r, u, k: r["odds"] < 0, 1.0),
    ("ANY 1u+ play, both reads over the price -> +1u", lambda r, u, k: u >= 1.0, lambda r, u, k: om(r) > 0 and rm(r, k) > 0, None),
]


def cells(boards):
    print("=" * 30, "(2) THE SIZE-UP CELLS - the cell vs the rest of its kind, flat 1u vs the price; both boards")
    verdicts = []
    for name, kf, cf, nu in CELLS:
        print(f"## {name}")
        oks, notes = [], []
        for bn, (board, _by) in boards.items():
            star, st = STAR[bn]
            pool = [(d, r, u, k) for d, ps in board.items() for r, u, k in ps if kf(r, u, k)]
            c = [(d, r, u) for d, r, u, k in pool if cf(r, u, k)]
            rest = [(d, r, u) for d, r, u, k in pool if not cf(r, u, k)]
            a = L.line(f"{bn} THE CELL", c)
            b = L.line(f"{bn} the rest of the kind", rest)
            pl = L.placebo(c, [(d, r, u) for d, r, u, k in pool])
            more = (a["train"]["n"] >= 8 and a["held"]["n"] >= 8 and a["train"]["roi"] > max(0, b["train"]["roi"])
                    and a["held"]["roi"] > max(0, b["held"]["roi"]))
            cellkeys = {(d, r["team"], k) for d, r, u, k in pool if cf(r, u, k)}

            def fn(d, r, u, k, ps, _ck=cellkeys, _nu=nu, _star=star):
                base = _star(d, r, u, k)
                if (d, r["team"], k) in _ck:
                    return max(base, _nu) if _nu is not None else base + 1.0
                return base
            s0 = L.schedule("before", board, lambda d, r, u, k, ps, _s=star: _s(d, r, u, k), quiet=True)
            s1 = L.schedule("after", board, fn, quiet=True)
            print(f"     {bn}: wins MORE than its siblings in both halves: {'YES' if more else 'no'}; placebo {pl} of 2,000; "
                  f"board {s0['net']:+.1f}u on {s0['risk']:.0f}u (worst {s0['dd']:+.1f}) -> {s1['net']:+.1f}u on {s1['risk']:.0f}u "
                  f"(worst {s1['dd']:+.1f}); the added units earn {100 * (s1['net'] - s0['net']) / (s1['risk'] - s0['risk']) if s1['risk'] > s0['risk'] else 0:+.1f}% "
                  f"(train {s1['train'] - s0['train']:+.1f}u / held {s1['held'] - s0['held']:+.1f}u)")
            oks.append(more and pl is not None and pl < 100 and s1["train"] > s0["train"] and s1["held"] > s0["held"])
            notes.append((a["all"]["n"], pl))
        v = "CLEARS both boards" if all(oks) else "clears ONE board" if any(oks) else "no"
        verdicts.append((name, v, notes))
        print(f"   => {v}")
    print("=" * 30, "VERDICTS")
    for name, v, notes in verdicts:
        print(f"  {v:20s} {name}  (n / placebo R1 {notes[0]}, R2 {notes[1]})")


STAR = {}


def main():
    boards = L.boards()
    for bn, (board, _by) in boards.items():
        STAR[bn] = star_fn(board)
        star, st = STAR[bn]
        print("=" * 30, f"BOARD {bn}: {len(board)} days, {sum(len(v) for v in board.values())} unit plays, ⭐ on {len(st)} days")
        L.schedule("TODAY (today's sizes + the ⭐ raise)", board, lambda d, r, u, k, ps, _s=star: _s(d, r, u, k))
        L.schedule("every play flat ½u", board, lambda d, r, u, k, ps: 0.5)
        L.schedule("every play flat 1u", board, lambda d, r, u, k, ps: 1.0)
        L.schedule("every ½u play at 1u (the owner's 'no more half units')", board, lambda d, r, u, k, ps, _s=star: max(1.0, _s(d, r, u, k)))
        L.schedule("every ½u play OFF (only the 1u+ plays)", board, lambda d, r, u, k, ps, _s=star: _s(d, r, u, k) if _s(d, r, u, k) >= 1 else 0.0)
        L.schedule("every play one step up (½->1, 1->2, 2->3)", board, lambda d, r, u, k, ps, _s=star: {0.5: 1.0, 1.0: 2.0, 2.0: 3.0}.get(_s(d, r, u, k), _s(d, r, u, k)))
        L.schedule("the ⭐ at 2u (today 1u at least)", board, lambda d, r, u, k, ps, _st=st, _s=star: max(2.0, u) if (d, r["team"], k) in _st else _s(d, r, u, k))
        L.schedule("the ⭐ at 3u", board, lambda d, r, u, k, ps, _st=st, _s=star: max(3.0, u) if (d, r["team"], k) in _st else _s(d, r, u, k))
        both = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today) if om(r) > 0}
        L.schedule("the ⭐ at 2u only with the OWN read over the price too", board, lambda d, r, u, k, ps, _b=both, _s=star: max(2.0, u) if (d, r["team"], k) in _b else _s(d, r, u, k))
        print("-- the ⭐ itself (flat 1u): all / with the own read over the price too / without")
        stl = S.stars(board, S.today)
        L.line("the ⭐", [(d, r, u) for d, r, u, k in stl])
        L.line("the ⭐, own read over the price too", [(d, r, u) for d, r, u, k in stl if om(r) > 0])
        L.line("the ⭐, own read NOT over", [(d, r, u) for d, r, u, k in stl if om(r) <= 0])
        L.line("the ⭐ that was a ½u play raised to 1u", [(d, r, u) for d, r, u, k in stl if u == 0.5])
        L.line("the ⭐ on a 1u+ play", [(d, r, u) for d, r, u, k in stl if u >= 1])
        print("   placebo (the ⭐ vs a random eligible play a day):",
              L.placebo([(d, r, u) for d, r, u, k in stl], [(d, r, u) for d in board for r, u, k in board[d] if S.eligible(r, u, k)]))
        kind_table(board, star)
        thin_table(board, star)
    cells(boards)


if __name__ == "__main__":
    main()
