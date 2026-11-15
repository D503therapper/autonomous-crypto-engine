"""S1 the NFL bye dog on 21 seasons of closes (the 1u early spot's base cell) / S2 the divisional dog off a win, the
division rematch. nflverse closes 2006-26, engine bands (dog +100..+350, favorite -150..-101)."""
import nfl_lib as N

L = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)


S = N.sides()
dogs = [r for r in S if N.dog(r)]
favs = [r for r in S if N.fav(r)]
say(f"sides {len(S)}  dogs {len(dogs)}  favs {len(favs)}")
say("== S1. THE BYE (rest 13+ days vs an opponent on 8 or fewer)")
bye = lambda r: (r["rest"] or 0) >= 13 and (r["orest"] or 99) <= 8
vsbye = lambda r: (r["orest"] or 0) >= 13 and (r["rest"] or 99) <= 8
N.cell("every dog +100..+350", dogs, say=say)
N.cell("  road dog", [r for r in dogs if not r["home"]], say=say)
N.cell("  home dog", [r for r in dogs if r["home"]], say=say)
b = [r for r in dogs if bye(r)]
N.cell("BYE dog", b, say=say)
say("   placebo:", N.placebo(b, dogs), "of 2000 random dog sets did as well")
N.cell("  bye dog, road", [r for r in b if not r["home"]], say=say)
N.cell("  bye dog, home", [r for r in b if r["home"]], say=say)
N.cell("  bye dog +100..+150", [r for r in b if r["odds"] <= 150], say=say)
N.cell("  bye dog +151..+250", [r for r in b if 150 < r["odds"] <= 250], say=say)
N.cell("  bye dog +251..+350", [r for r in b if r["odds"] > 250], say=say)
N.cell("  bye dog, 2006-10", [r for r in b if r["season"] <= 2010], say=say)
N.cell("  bye dog, 2011-16", [r for r in b if 2011 <= r["season"] <= 2016], say=say)
N.cell("  bye dog, 2017-21", [r for r in b if 2017 <= r["season"] <= 2021], say=say)
N.cell("  bye dog, 2022-26", [r for r in b if r["season"] >= 2022], say=say)
N.cell("  bye dog off a loss", [r for r in b if (r["prev_m"] or 0) < 0], say=say)
N.cell("  bye dog off a win", [r for r in b if (r["prev_m"] or 0) > 0], say=say)
N.cell("  bye dog, division game", [r for r in b if r["div"]], say=say)
N.cell("  bye dog, losing record", [r for r in b if r["w"] < r["l"]], say=say)
N.cell("  bye dog, .500+ record", [r for r in b if r["w"] >= r["l"]], say=say)
N.cell("  bye dog, any plus price", [r for r in S if bye(r) and r["odds"] >= 100], say=say)
N.cell("bye FAVORITE -150..-101", [r for r in favs if bye(r)], say=say)
N.cell("bye favorite, any price", [r for r in S if bye(r) and r["odds"] < 0], say=say)
N.cell("dog FACING a bye team", [r for r in dogs if vsbye(r)], say=say)
N.cell("mini-bye dog (rest 9-12 vs <=8)", [r for r in dogs if 9 <= (r["rest"] or 0) <= 12 and (r["orest"] or 99) <= 8], say=say)
N.cell("short dog (rest <=6 vs 7+)", [r for r in dogs if (r["rest"] or 9) <= 6 and (r["orest"] or 0) >= 7], say=say)
N.cell("short FAV (rest <=6 vs 7+)", [r for r in favs if (r["rest"] or 9) <= 6 and (r["orest"] or 0) >= 7], say=say)
for s in range(2006, 2027):
    x = [r for r in b if r["season"] == s]
    if x:
        say(f"   {s}: {sum(r['won'] for r in x)}-{sum(not r['won'] for r in x)} {sum(r['prof'] for r in x):+.1f}u")

say("== S2. THE DIVISION DOG")
dv = [r for r in dogs if r["div"]]
N.cell("division dog", dv, say=say)
N.cell("non-division dog", [r for r in dogs if not r["div"]], say=say)
x = [r for r in dv if (r["prev_m"] or 0) > 0]
N.cell("division dog OFF A WIN", x, say=say)
say("   placebo vs all dogs:", N.placebo(x, dogs), " vs division dogs:", N.placebo(x, dv))
N.cell("  .. road", [r for r in x if not r["home"]], say=say)
N.cell("  .. home", [r for r in x if r["home"]], say=say)
N.cell("  .. +100..+150", [r for r in x if r["odds"] <= 150], say=say)
N.cell("  .. +151..+350", [r for r in x if r["odds"] > 150], say=say)
N.cell("  .. off a win as a DOG", [r for r in x if r["prev_dog"]], say=say)
N.cell("  .. off a win as a favorite", [r for r in x if r["prev_dog"] is False], say=say)
N.cell("  .. off 2+ wins", [r for r in x if r["streak"] >= 2], say=say)
N.cell("  .. weeks 1-9", [r for r in x if r["week"] <= 9], say=say)
N.cell("  .. weeks 10+", [r for r in x if r["week"] >= 10], say=say)
N.cell("division dog off a loss", [r for r in dv if (r["prev_m"] or 0) < 0], say=say)
N.cell("non-division dog off a win", [r for r in dogs if not r["div"] and (r["prev_m"] or 0) > 0], say=say)
N.cell("non-division dog off a loss", [r for r in dogs if not r["div"] and (r["prev_m"] or 0) < 0], say=say)
say("-- the rematch (2nd meeting of the season)")
re = [r for r in dv if r["meet_m"] is not None]
N.cell("division dog, 2nd meeting", re, say=say)
N.cell("  lost the 1st meeting", [r for r in re if r["meet_m"] < 0], say=say)
N.cell("  lost the 1st by 14+", [r for r in re if r["meet_m"] <= -14], say=say)
N.cell("  lost the 1st by 1-7", [r for r in re if -7 <= r["meet_m"] < 0], say=say)
N.cell("  WON the 1st meeting", [r for r in re if r["meet_m"] > 0], say=say)
N.cell("  won the 1st, at home now", [r for r in re if r["meet_m"] > 0 and r["home"]], say=say)
N.cell("  won the 1st, on the road now", [r for r in re if r["meet_m"] > 0 and not r["home"]], say=say)
N.cell("division dog, 1st meeting", [r for r in dv if r["meet_m"] is None], say=say)
fre = [r for r in favs if r["div"] and r["meet_m"] is not None]
N.cell("division FAV -150..-101, 2nd meeting, won the 1st", [r for r in fre if r["meet_m"] > 0], say=say)
N.cell("division FAV -150..-101, 2nd meeting, lost the 1st", [r for r in fre if r["meet_m"] < 0], say=say)
N.cell("division FAV -150..-101", [r for r in favs if r["div"]], say=say)
N.cell("non-division FAV -150..-101", [r for r in favs if not r["div"]], say=say)
N.cell("every FAV -150..-101", favs, say=say)
N.cell("  home", [r for r in favs if r["home"]], say=say)
N.cell("  road", [r for r in favs if not r["home"]], say=say)
open("s1_s2_nfl_out.txt", "w").write("\n".join(L) + "\n")
