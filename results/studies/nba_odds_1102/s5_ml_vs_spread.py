"""STUDY 5 (11/2, my pick - only this data allows it): THE MONEYLINE vs ITS OWN SPREAD AT THE MORNING, every book.
The 10/30 study (daily_1030 s8) found the NBA moneyline and spread priced together AT THE CLOSE (one source, ESPN). The
paid history holds both markets from every US book at the game-day MORNING (15:00Z), the hour the 8 AM board posts -
when the two markets might not have caught up with each other yet.
The market's own conversion: logit(no-vig home ML %) = a + b * home spread, fit on ESPN's CLOSES 2018-19 (before any
test season). At the morning: gap = the median book's no-vig ML % minus the % its median spread implies. A side whose
moneyline is N+ points CHEAPER than its own spread says is bet on the moneyline at the median morning price, flat 1u.
Also: a book whose ML on a side is N+ points cheaper than ITS OWN spread implies (the per-book mismatch), at that book's
price. And which market moves to the other by the close. TRAIN 2020-21 + 2021-22, HELD OUT 2022-23 (spreads to 2023-04)."""
import json
import math
import os
import statistics
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib                       # noqa: E402

games = lib.load_games()
lk = lib.looks(games)
prev = lib.prev_tips(games)
G = [("train 20-21", {2020, 2021}), ("held 22", {2022})]

# the conversion, on the 2018-19 closes
xs, ys = [], []
for g in games.values():
    if lib.season(g.get("start", "2000-01")) in (2018, 2019) and g.get("stype") == "2":
        sp, mh, ma = lib.num(g.get("spread_home")), lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
        if None not in (sp, mh, ma) and min(abs(mh), abs(ma)) >= 100:
            p = lib.nv(mh, ma)
            xs.append(sp); ys.append(math.log(p / (1 - p)))
mx, my = statistics.mean(xs), statistics.mean(ys)
b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
a = my - b * mx
resid = statistics.pstdev([y - (a + b * x) for x, y in zip(xs, ys)])
print(f"conversion on {len(xs)} closes 2018-19: logit(p_home) = {a:.3f} + {b:.4f} * spread (resid sd {resid:.3f} logits)")
lin = lambda sp: 1 / (1 + math.exp(-(a + b * sp)))   # noqa: E731
# The linear-logit conversion from ESPN's closes put EVERY gap on the favorite's side (a convention gap between one
# source and the median book, not a mismatch) - so the conversion used is the MEDIAN BOOK'S OWN at the morning: for each
# half-point of the favorite's spread, the median no-vig % of the favorite over the TRAIN mornings (2020-21 + 2021-22) -
# a pricing convention, no results in it; the linear fit fills a bin with under 15 games.
bins = {}
for gid, v in lk.items():
    g = games[gid]
    if lib.season(g["start"]) not in (2020, 2021) or g.get("stype") != "2":
        continue
    mo = lib.pick_looks(lk, prev, gid)[1]
    spm = lib.sp_looks(lk, prev, gid)[1]
    if mo and spm and spm["snap"] == mo["snap"] and spm["pt"] != 0:
        fav_p = mo["p"] if spm["pt"] < 0 else 1 - mo["p"]
        bins.setdefault(round(abs(spm["pt"]) * 2) / 2, []).append(fav_p)
conv = {k: statistics.median(v) for k, v in bins.items() if len(v) >= 15}


def imp(sp):
    k = round(abs(sp) * 2) / 2
    if sp == 0:
        return 0.5
    pf = conv.get(k, lin(-abs(sp)))
    return pf if sp < 0 else 1 - pf


print("median-book conversion (fav spread -> fav %): " + ", ".join(f"{k:g}:{v * 100:.1f}" for k, v in sorted(conv.items())[:24]))


def result(g):
    hs, as_ = lib.num(g.get("home_score")), lib.num(g.get("away_score"))
    return None if hs is None or as_ is None or hs == as_ else (1 if hs > as_ else 0)


C = lib.Cells("THE MONEYLINE CHEAPER THAN ITS OWN SPREAD at the morning (median book), bet the ML at the median, flat 1u", G)
P = lib.Cells("PER BOOK: a book's ML N+ pts cheaper than its OWN spread, bet at that book's ML (one a game, the biggest)", G)
M = lib.Cells("WHO MOVES: the gap's side - did the ML close toward the spread (+1) or the spread toward the ML (-1)?", G)
gaps = []
for g in games.values():
    s = lib.season(g.get("start", "2000-01"))
    if s not in (2020, 2021, 2022) or g.get("stype") != "2" or g.get("status") != "final" or result(g) is None:
        continue
    if g["id"] not in lk:
        continue
    mo = lib.pick_looks(lk, prev, g["id"])[1]
    spm = lib.sp_looks(lk, prev, g["id"])[1]
    if not mo or not spm or spm["snap"] != mo["snap"]:
        continue
    hw = result(g)
    gap = mo["p"] - imp(spm["pt"])                            # + = the home ML dearer than its spread says -> away cheap
    gaps.append(abs(gap))
    side = "away" if gap > 0 else "home"
    ml = mo["ma"] if side == "away" else mo["mh"]
    w = 1 - hw if side == "away" else hw
    kind = "dog" if ml > 0 else "fav"
    if -250 <= ml <= 350:
        for cut in (0.01, 0.02, 0.03):
            if abs(gap) >= cut:
                C.add(f"gap {cut * 100:.0f}+ pts", s, lib.profit(w, lib.dec(ml)))
                C.add(f"gap {cut * 100:.0f}+ pts, the cheap side a {kind}", s, lib.profit(w, lib.dec(ml)))
    # who moves by the close (ESPN close ML + close spread)
    csp, cmh, cma = lib.num(g.get("spread_home")), lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
    if abs(gap) >= 0.02 and None not in (csp, cmh, cma):
        ml_move = lib.nv(cmh, cma) - mo["p"]
        sp_move = imp(csp) - imp(spm["pt"])
        M.add("ML moved more toward closing the gap", s, 1 if abs(ml_move) > abs(sp_move) and ml_move * gap < 0 else -1)
    best = None
    for bk, (h, a_) in mo["books"].items():
        pt = spm["books"].get(bk)
        if pt is None:
            continue
        gb = lib.nv(h, a_) - imp(pt)
        if best is None or abs(gb) > abs(best[0]):
            best = (gb, bk, h, a_)
    if best and abs(best[0]) >= 0.02:
        gb, bk, h, a_ = best
        sd_ = "away" if gb > 0 else "home"
        ml = a_ if sd_ == "away" else h
        w = 1 - hw if sd_ == "away" else hw
        if -250 <= ml <= 350:
            for cut in (0.02, 0.03, 0.04):
                if abs(gb) >= cut:
                    P.add(f"book gap {cut * 100:.0f}+ pts", s, lib.profit(w, lib.dec(ml)))
print(f"morning games with both markets: {len(gaps)}; |gap| mean {statistics.mean(gaps) * 100:.2f} pts, "
      f"2+ pts {sum(1 for x in gaps if x >= 0.02)}, 3+ {sum(1 for x in gaps if x >= 0.03)}")
C.dump(); P.dump(); M.dump()
json.dump({"C": C.as_dict(), "P": P.as_dict(), "M": M.as_dict()}, open(os.path.join(lib.OUT, "s5_out.json"), "w"), indent=1)
