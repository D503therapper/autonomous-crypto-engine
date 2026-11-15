"""S1b - the NFL dog FACING a team off its bye (the dog on a normal week): the second checks."""
import nfl_lib as N

L = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)


S = N.sides()
dogs = [r for r in S if N.dog(r)]
vs = lambda r, lo=13: (r["orest"] or 0) >= lo and (r["rest"] or 99) <= 8
x = [r for r in dogs if vs(r)]
N.cell("dog +100..+350 vs a bye team", x, say=say)
say("   placebo (as badly):", N.placebo(x, dogs, fade=True), "of 2000")
N.cell("  home", [r for r in x if r["home"]], say=say)
N.cell("  road", [r for r in x if not r["home"]], say=say)
say("   placebo road vs road dogs:", N.placebo([r for r in x if not r["home"]], [r for r in dogs if not r["home"]], fade=True))
say("   placebo home vs home dogs:", N.placebo([r for r in x if r["home"]], [r for r in dogs if r["home"]], fade=True))
for lo, hi in ((100, 150), (151, 200), (201, 350)):
    N.cell(f"  +{lo}..+{hi}", [r for r in x if lo <= r["odds"] <= hi], say=say)
    N.cell(f"     (every dog +{lo}..+{hi})", [r for r in dogs if lo <= r["odds"] <= hi], say=say)
for a, b in ((2006, 2010), (2011, 2016), (2017, 2021), (2022, 2026)):
    N.cell(f"  {a}-{b}", [r for r in x if a <= r["season"] <= b], say=say)
N.cell("  division game", [r for r in x if r["div"]], say=say)
N.cell("  non-division", [r for r in x if not r["div"]], say=say)
N.cell("  dog off a win", [r for r in x if (r["prev_m"] or 0) > 0], say=say)
N.cell("  dog off a loss", [r for r in x if (r["prev_m"] or 0) < 0], say=say)
N.cell("  the bye team off a loss", [r for r in x if (r["oprev_m"] or 0) < 0], say=say)
N.cell("  the bye team off a win", [r for r in x if (r["oprev_m"] or 0) > 0], say=say)
N.cell("  weeks 5-9", [r for r in x if r["week"] <= 9], say=say)
N.cell("  weeks 10+", [r for r in x if r["week"] >= 10], say=say)
N.cell("dog (any plus price) vs a bye team", [r for r in S if r["odds"] >= 100 and vs(r)], say=say)
N.cell("dog +351 or longer vs a bye team", [r for r in S if r["odds"] > 350 and vs(r)], say=say)
N.cell("the dose: vs a team on 9-12 days (mini-bye)", [r for r in dogs if 9 <= (r["orest"] or 0) <= 12 and (r["rest"] or 99) <= 8], say=say)
N.cell("the dose: both off a bye", [r for r in dogs if (r["orest"] or 0) >= 13 and (r["rest"] or 0) >= 13], say=say)
N.cell("FAV -150..-101 vs a bye team", [r for r in S if N.fav(r) and vs(r)], say=say)
N.cell("FAV any price vs a bye team", [r for r in S if r["odds"] < 0 and vs(r)], say=say)
# the price-free read: did the dog win less than the no-vig close said?
pw = sum(r["p_nv"] for r in x) / len(x)
say(f"price-free: won {sum(r['won'] for r in x)/len(x)*100:.1f}% vs {pw*100:.1f}% no-vig close ({len(x)})")
for nm, f in (("train", lambda r: r["season"] <= 2016), ("held", lambda r: r["season"] >= 2017)):
    y = [r for r in x if f(r)]
    say(f"   {nm}: won {sum(r['won'] for r in y)/len(y)*100:.1f}% vs {sum(r['p_nv'] for r in y)/len(y)*100:.1f}% ({len(y)})")
by = {}
for r in x:
    by.setdefault(r["season"], []).append(r)
say("  by season: " + "  ".join(f"{s} {sum(r['won'] for r in v)}-{sum(not r['won'] for r in v)} {sum(r['prof'] for r in v):+.1f}" for s, v in sorted(by.items())))
# spread check on the same games (ATS for the dog at -110): margin + line
ats = [(1 / 1.1 if r["margin"] + r["line"] > 0 else -1.0) for r in x if r["line"] is not None and r["margin"] + r["line"] != 0]
say(f"ATS the same dogs (flat -110): {sum(a > 0 for a in ats)}-{sum(a < 0 for a in ats)} {sum(ats)/len(ats)*100:+.1f}%")
open("s1b_vs_bye_out.txt", "w").write("\n".join(L) + "\n")
