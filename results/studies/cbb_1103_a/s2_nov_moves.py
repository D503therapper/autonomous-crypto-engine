"""STUDY 2 - LINE MOVEMENT open -> close, college hoops, the FIRST 3 WEEKS vs later. ESPN's open + close moneylines
(2023-25 only - the opens start in 2023): the move = the no-vig home chance at the close minus at the open. FOLLOW =
the side the line moved TO, FADE = the side it moved AWAY from, each bet at the CLOSE (what we can get after the move)
and, for the follow side, at the OPEN (the price before the move - not gettable live without the history, a ceiling).
Moves of 2-4 / 4-8 / 8+ points of win chance; phase = days 0-21 of the season vs later; games 1-5 per team.
Three seasons only, each read apart (no train before 2023 exists for opens) - a cell needs 3 of 3 up to be a lead."""
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load()) if r["season"] >= 2023]
cells = defaultdict(lib.Cell)
moves = defaultdict(list)
for r in rows:
    try:
        mh, ma, oh, oa = (float(r[k]) for k in ("ml_home", "ml_away", "ml_home_open", "ml_away_open"))
    except (TypeError, ValueError):
        continue
    if min(abs(mh), abs(ma), abs(oh), abs(oa)) < 100:
        continue
    pc, po = lib.novig(mh, ma), lib.novig(oh, oa)
    mv = pc - po
    s = r["season"]
    d = r["day_in_season"]
    ph = "days 0-21" if d <= 21 else "day 22+"
    early5 = max(r["gn_home"], r["gn_away"]) <= 5
    moves[ph].append(abs(mv))
    a = abs(mv)
    if a < 0.02:
        continue
    band = "2-4" if a < 0.04 else ("4-8" if a < 0.08 else "8+")
    hw = r["hs"] > r["as_"]
    to_home = mv > 0
    f_odds, f_open, f_won = (mh, oh, hw) if to_home else (ma, oa, not hw)
    x_odds, x_won = (ma, not hw) if to_home else (mh, hw)
    if -400 <= f_odds <= 350:
        for lab in (f"move {band} | {ph}", f"move 2+ | {ph}") + ((f"move 2+ | games 1-5",) if early5 else ()):
            cells[f"FOLLOW at close {lab}"].add(s, lib.ml_profit(f_odds, f_won), f_won)
            if -400 <= f_open <= 350:
                cells[f"FOLLOW at OPEN  {lab}"].add(s, lib.ml_profit(f_open, f_won), f_won)
    if -400 <= x_odds <= 350:
        for lab in (f"move {band} | {ph}", f"move 2+ | {ph}") + ((f"move 2+ | games 1-5",) if early5 else ()):
            cells[f"FADE   at close {lab}"].add(s, lib.ml_profit(x_odds, x_won), x_won)
            if x_odds > 0:
                cells[f"FADE (dog side) {lab}"].add(s, lib.ml_profit(x_odds, x_won), x_won)
print(__doc__)
for ph, xs in moves.items():
    xs.sort()
    print(f"{ph}: {len(xs)} games, median move {xs[len(xs) // 2]:.3f}, 2+ pts {sum(x >= .02 for x in xs) / len(xs):.0%}, 4+ {sum(x >= .04 for x in xs) / len(xs):.0%}")
for k in sorted(cells):
    print(cells[k].line(k))
