"""11/16 MAX PLAY HUNT - S5: THE NFL, CONFLUENCE AT THE CLOSE 2006-26 (nflverse's schedule file - ten_1115/nfl_lib).
The engine's NFL weights, stacked: the dog off a blowout loss (overreact), the 0-2 / skidding dog, the road dog, the
favorite off its bye (the 11/15 "dog vs a team off its bye" fade seen from the favorite's side), a QB change across,
the rest edge. Train 2006-16 / held out 2017-26. Do 3+ agreeing win far more than one?
Usage: python results/studies/max_pro_1116/s5_nfl.py > results/studies/max_pro_1116/s5_nfl.out"""
import os
import sys

import mp

sys.path.insert(0, os.path.join(mp.HERE, "..", "ten_1115"))
import nfl_lib as N  # noqa: E402

R = N.sides()
for r in R:
    r["dec"] = N.dec(r["odds"])
C = lambda name, rs: mp.cell(name, rs, "nfl")   # noqa: E731
dogs = [r for r in R if 100 <= r["odds"] <= 350]
short = [r for r in dogs if r["odds"] <= 150]
favs = [r for r in R if -150 <= r["odds"] <= -101]
print("================ NFL - every regular-season side at the close, train 2006-16 / held 2017-26 ================")
C("BASE every dog +100..+350", dogs)
C("BASE every dog +100..+150", short)
C("BASE every favorite -150..-101", favs)
bye = lambda r: (r["rest"] or 7) >= 13      # noqa: E731
obye = lambda r: (r["orest"] or 7) >= 13    # noqa: E731
qbch = lambda r: r["prev_qb"] and r["qb"] and r["qb"] != r["prev_qb"]       # noqa: E731
oqbch = lambda r: r["oprev_qb"] and r["oqb"] and r["oqb"] != r["oprev_qb"]  # noqa: E731
print(" -- F1-F7 the single spots")
C("F1 fav -150..-101 off its bye, the dog on a normal week", [r for r in favs if bye(r) and not obye(r)])
C("F1b ... at home", [r for r in favs if bye(r) and not obye(r) and r["home"]])
C("F2 road dog +100..+150 off a 14+ loss", [r for r in short if not r["home"] and r["prev_m"] is not None and r["prev_m"] <= -14])
C("F3 dog +100..+150 on a 2+ game skid", [r for r in short if r["streak"] <= -2])
C("F4 dog +100..+150, the favorite's QB changed from last week", [r for r in short if oqbch(r)])
C("F5 fav -150..-101, the dog's QB changed from last week", [r for r in favs if oqbch(r)])
C("F6 home dog +100..+150 in the division", [r for r in short if r["home"] and r["div"]])
C("F7 fav -150..-101 with 3+ more days of rest (no bye)", [r for r in favs if not bye(r) and (r["rest"] or 7) - (r["orest"] or 7) >= 3])
C("F8 dog +100..+150 with 3+ more days of rest (no bye)", [r for r in short if not bye(r) and (r["rest"] or 7) - (r["orest"] or 7) >= 3])
C("F9 fav -150..-101 off a loss, the dog off a win by 14+", [r for r in favs if (r["prev_m"] or 0) < 0 and (r["oprev_m"] or 0) >= 14])
C("F10 dog +100..+150 off a loss, the favorite off a 14+ win", [r for r in short if (r["prev_m"] or 0) < 0 and (r["oprev_m"] or 0) >= 14])


def dcount(r):
    k = 0
    k += 1 if (r["prev_m"] is not None and r["prev_m"] <= -14) else 0
    k += 1 if r["streak"] <= -2 else 0
    k += 1 if not r["home"] else 0
    k += 1 if oqbch(r) else 0
    k += 1 if (r["oprev_m"] or 0) >= 14 else 0
    k += 1 if (r["rest"] or 7) - (r["orest"] or 7) >= 2 and not bye(r) else 0
    k -= 1 if obye(r) and not bye(r) else 0
    k -= 1 if qbch(r) else 0
    return k


def fcount(r):
    k = 0
    k += 1 if bye(r) and not obye(r) else 0
    k += 1 if oqbch(r) else 0
    k += 1 if r["home"] else 0
    k += 1 if (r["prev_m"] or 0) < 0 else 0                    # the favorite off a loss (the bounce)
    k += 1 if r["ostreak"] >= 3 else 0                         # the dog is the hot one
    k += 1 if (r["rest"] or 7) - (r["orest"] or 7) >= 2 else 0
    k -= 1 if qbch(r) else 0
    return k


print(" -- F11 the dog confluence COUNT (off a 14+ loss, a 2+ skid, on the road, the fav's QB changed, the fav off a 14+ win, a rest edge; -1 facing a bye team / our QB changed)")
for r in dogs:
    r["k"] = dcount(r)
for k in range(-1, 6):
    C(f"F11 dog +100..+350 count == {k}", [r for r in dogs if r["k"] == k])
for k in (2, 3, 4):
    sel = [r for r in short if r["k"] >= k]
    C(f"F11 dog +100..+150 count >= {k}", sel)
    print(f"      placebo vs every short dog: {mp.placebo(sel, short)} of 2000")
    mp.size_line([r for r in sel if r["season"] >= 2017])
print(" -- F12 the favorite confluence COUNT (off its bye, the dog's QB changed, at home, off a loss, the dog hot, a rest edge; -1 our QB changed)")
for r in favs:
    r["k"] = fcount(r)
for k in range(-1, 5):
    C(f"F12 fav -150..-101 count == {k}", [r for r in favs if r["k"] == k])
for k in (2, 3, 4):
    sel = [r for r in favs if r["k"] >= k]
    C(f"F12 fav count >= {k}", sel)
    print(f"      placebo vs every fav in band: {mp.placebo(sel, favs)} of 2000")
    mp.size_line([r for r in sel if r["season"] >= 2017])
print(f"\ncells printed: {len(mp.TRIED)}")
