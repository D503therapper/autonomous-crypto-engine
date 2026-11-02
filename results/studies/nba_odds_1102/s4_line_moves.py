"""STUDY 4 (11/2): NBA LINE MOVEMENT AND THE BOOKS - untested in the NBA (every earlier line-move / book study was
football: 10/8 shape + book outliers, 10/10 first-mover + softest opener, 10/11 spread outlier).
The data (step 0): the next-day line exists for only ~4% of 2020-23 regular-season games, so the 'overnight' leg is a
side table; the real legs are the GAME-DAY MORNING median-book look (15:00Z, ~10h before tip) -> ESPN's close.
TRAIN = 2020-21 + 2021-22, HELD OUT = 2022-23; a second check on 2023-25 with ESPN's open -> close where it applies.
  A. THE LATE MOVE: the side the price moved TO between the morning and the close, bet at the CLOSE (follow / fade), by
     size and by dog / favorite. (Betting at the morning the side that WILL move is look-ahead - shown as CLV only.)
  B. BOOK BY BOOK at the morning: how far each book sits from the close (sharp / soft), which book LAGS the consensus in
     the direction the market then goes (slowest to move), and THE OUTLIER BET - a side one book prices 2+ / 3+ no-vig
     points cheaper than the median of the others, bet at that book's price (per book too).
  C. THE OVERNIGHT (next-day line -> morning, the ~130 games that have one): the move's size, follow / fade at the morning."""
import json
import os
import statistics
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib                       # noqa: E402

games = lib.load_games()
lk = lib.looks(games)
prev = lib.prev_tips(games)
G = [("train 20-21", {2020, 2021}), ("held 22", {2022})]
REF = [("2023-25 ref", {2023, 2024, 2025})]


def result(g):
    hs, as_ = lib.num(g.get("home_score")), lib.num(g.get("away_score"))
    return None if hs is None or as_ is None or hs == as_ else (1 if hs > as_ else 0)


fin = [g for g in games.values() if g.get("stype") == "2" and g.get("status") == "final" and result(g) is not None
       and lib.num(g.get("ml_home")) is not None]
A = lib.Cells("A. THE LATE MOVE (morning -> close), bet at the CLOSE, flat 1u", G + REF)
CLV = {}
for g in fin:
    s = lib.season(g["start"])
    hw = result(g)
    ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
    pc = lib.nv(ch, ca)
    if s in (2020, 2021, 2022):
        mo = lib.pick_looks(lk, prev, g["id"])[1] if g["id"] in lk else None
        if not mo:
            continue
        po = mo["p"]
    elif s in (2023, 2024, 2025) and lib.num(g.get("ml_home_open")) is not None:
        po = lib.nv(int(float(g["ml_home_open"])), int(float(g["ml_away_open"])))
    else:
        continue
    mv = pc - po                                             # + = toward home
    to, frm = ("home", "away") if mv > 0 else ("away", "home")
    pr = {"home": (ch, hw), "away": (ca, 1 - hw)}
    a = abs(mv)
    for lo, hi in ((0.0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.05), (0.05, 1)):
        if lo <= a < hi and a > 0:
            ml, w = pr[to]
            A.add(f"follow, moved {lo * 100:.0f}-{hi * 100:.0f} pts", s, lib.profit(w, lib.dec(ml)))
            ml, w = pr[frm]
            A.add(f"fade,   moved {lo * 100:.0f}-{hi * 100:.0f} pts", s, lib.profit(w, lib.dec(ml)))
    if a >= 0.03:
        for side, nm in ((to, "follow"), (frm, "fade")):
            ml, w = pr[side]
            kind = "dog" if ml > 0 else "fav"
            if ml > 0 and ml > 350 or ml < -400:
                continue
            A.add(f"{nm} 3+ pts, the side a {kind}", s, lib.profit(w, lib.dec(ml)))
    if s <= 2022:                                            # CLV of the morning price (look-ahead: what a move is worth)
        CLV.setdefault("move", []).append(a)
A.dump()
print(f"  (2020-22: mean |morning -> close| {statistics.mean(CLV['move']) * 100:.2f} pts, "
      f"{sum(1 for x in CLV['move'] if x >= 0.03) / len(CLV['move']):.0%} of games 3+)")

# ---------------------------------------------------------------- B. BOOK BY BOOK
print("\nB. BOOK BY BOOK at the game-day morning look (2020-22 regular season):")
stat = {}
B = lib.Cells("B. THE OUTLIER BOOK at the morning: a side one book prices N+ no-vig pts under the others' median, bet at "
              "that book's price (one bet a game - the biggest gap), flat 1u", G)
per_book = lib.Cells("B2. the 2+ outlier bet, by book", G)
best_px = lib.Cells("B3. every side at the BEST price on the board vs the MEDIAN book (dogs +100..+350 / favs -101..-200)", G)
for g in fin:
    s = lib.season(g["start"])
    if s not in (2020, 2021, 2022):
        continue
    mo = lib.pick_looks(lk, prev, g["id"])[1] if g["id"] in lk else None
    if not mo or len(mo["books"]) < 4:
        continue
    hw = result(g)
    pc = lib.nv(int(float(g["ml_home"])), int(float(g["ml_away"])))
    books = mo["books"]
    nvs = {b: lib.nv(h, a) for b, (h, a) in books.items()}
    for b, p in nvs.items():
        others = statistics.median([v for k, v in nvs.items() if k != b])
        st = stat.setdefault(b, {"n": 0, "dev_close": 0.0, "lag": 0.0, "lag_n": 0, "hold": 0.0})
        st["n"] += 1
        st["dev_close"] += abs(p - pc)
        h, a = books[b]
        st["hold"] += 1 / lib.dec(h) + 1 / lib.dec(a) - 1
        mvm = pc - others                                    # where the market went from the pack's morning number
        if abs(mvm) >= 0.01:
            st["lag"] += (others - p) * (1 if mvm > 0 else -1)   # + = this book sat on the side the market LEFT (stale)
            st["lag_n"] += 1
    best = None
    for b, p in nvs.items():
        others = statistics.median([v for k, v in nvs.items() if k != b])
        h, a = books[b]
        for side, gap, ml, oth_p in (("home", others - p, h, others), ("away", p - others, a, 1 - others)):
            if gap <= 0 or 1 / lib.dec(ml) >= (oth_p if side == "home" else oth_p):
                continue                                     # (the raw price must still beat the consensus no-vig)
            if best is None or gap > best[0]:
                best = (gap, b, side, ml)
    if best:
        gap, b, side, ml = best
        w = hw if side == "home" else 1 - hw
        pnl = lib.profit(w, lib.dec(ml))
        kind = "dog" if ml > 0 else "fav"
        for cut in (0.02, 0.03, 0.04):
            if gap >= cut:
                B.add(f"outlier {cut * 100:.0f}+ pts", s, pnl)
                B.add(f"outlier {cut * 100:.0f}+ pts, a {kind}", s, pnl)
        if gap >= 0.02:
            per_book.add(b, s, pnl)
        if gap >= 0.03 and ml < 0:
            per_book.add(f"FAV 3+: {b}", s, pnl)
            pcs = pc if side == "home" else 1 - pc
            oth = statistics.median([v for k, v in nvs.items() if k != b])
            oth = oth if side == "home" else 1 - oth
            CLV.setdefault("fav3", []).append((pcs - oth, pcs - 1 / lib.dec(ml)))
    for side, w in (("home", hw), ("away", 1 - hw)):
        i = 0 if side == "home" else 1
        decs = [lib.dec(v[i]) for v in books.values()]
        med = statistics.median(decs)
        top = max(decs)
        mla = lib.amer(med)
        band = "dog" if 100 <= mla <= 350 else "fav" if -200 <= mla <= -101 else None
        if band:
            best_px.add(f"{band} at the median book", s, lib.profit(w, med))
            best_px.add(f"{band} at the best book", s, lib.profit(w, top))
print(f"  {'book':16s} {'games':>6s} {'|book - close|':>15s} {'lag (+ = stale)':>16s} {'hold':>6s}")
for b, st in sorted(stat.items(), key=lambda kv: kv[1]["dev_close"] / kv[1]["n"]):
    if st["n"] >= 300:
        print(f"  {b:16s} {st['n']:6d} {st['dev_close'] / st['n'] * 100:14.2f}p {st['lag'] / max(1, st['lag_n']) * 100:15.2f}p "
              f"{st['hold'] / st['n'] * 100:5.1f}%")
B.dump()
per_book.dump()
f3 = CLV.get("fav3", [])
if f3:
    print(f"  the FAV 3+ outliers: n {len(f3)}; the close vs the OTHER books' morning median {statistics.mean([a for a, _ in f3]) * 100:+.2f}"
          f" pts (+ = the pack moved to the outlier book); the close vs the outlier's raw price "
          f"{statistics.mean([b for _, b in f3]) * 100:+.2f} pts; the close beat the outlier price on "
          f"{sum(1 for _, b in f3 if b > 0)} of {len(f3)}")
best_px.dump()

# ---------------------------------------------------------------- C. THE OVERNIGHT
C = lib.Cells("C. THE OVERNIGHT (fair next-day line -> game-day morning), bet at the MORNING, flat 1u", [("2020-22", {2020, 2021, 2022})])
ov = []
for g in fin:
    s = lib.season(g["start"])
    if s not in (2020, 2021, 2022) or g["id"] not in lk:
        continue
    op, mo = lib.pick_looks(lk, prev, g["id"])
    if not op or not mo:
        continue
    hw = result(g)
    mv = mo["p"] - op["p"]
    ov.append(abs(mv))
    if abs(mv) < 0.01:
        continue
    to = "home" if mv > 0 else "away"
    for side, nm in ((to, "follow"), ("away" if to == "home" else "home", "fade")):
        ml = mo["mh"] if side == "home" else mo["ma"]
        w = hw if side == "home" else 1 - hw
        C.add(f"{nm} the overnight move 1+ pts", s, lib.profit(w, lib.dec(ml)))
    # did the overnight move keep going to the close?
    pc = lib.nv(int(float(g["ml_home"])), int(float(g["ml_away"])))
    C.add("(the move kept going to the close: +1 yes / -1 no)", s, 1 if (pc - mo["p"]) * mv > 0 else -1)
C.dump()
if ov:
    print(f"  overnight moves: n {len(ov)}, mean {statistics.mean(ov) * 100:.2f} pts, 2+ pts {sum(1 for x in ov if x >= 0.02)}")
json.dump({"A": A.as_dict(), "B": B.as_dict(), "B2": per_book.as_dict(), "B3": best_px.as_dict(), "C": C.as_dict(),
           "books": {b: {"n": st["n"], "dev_close": round(st["dev_close"] / st["n"], 4),
                         "lag": round(st["lag"] / max(1, st["lag_n"]), 4)} for b, st in stat.items()}},
          open(os.path.join(lib.OUT, "s4_out.json"), "w"), indent=1)
