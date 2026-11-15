"""S1c - the second source for S1b: the NFL dog facing a team off its bye, on OUR game files (ESPN's close at its own
juice 2018-26, the engine's own rest rule: the bye team 13+ days since its last game, the dog 8 or fewer)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib2  # noqa: E402

L = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)


R = lib2.rows("nfl")
d = lambda h: None if h is None else h / 24      # noqa: E731
dogs = [r for r in R if 100 <= r["odds"] <= 350]
vs = [r for r in dogs if (d(r["oprev_gap_h"]) or 0) >= 13 and (d(r["prev_gap_h"]) or 99) <= 8.5]
by = [r for r in dogs if (d(r["prev_gap_h"]) or 0) >= 13 and (d(r["oprev_gap_h"]) or 99) <= 8.5]
lib2.cell("every NFL dog +100..+350 (ESPN close 2018-26)", dogs, say=say)
lib2.cell("dog vs a team off its bye", vs, say=say)
say("   placebo (as badly):", 2000 - (lib2.placebo(vs, dogs) or 0), "of 2000")
lib2.cell("   .. home", [r for r in vs if r["home"]], say=say)
lib2.cell("   .. road", [r for r in vs if not r["home"]], say=say)
lib2.cell("   .. ATS", vs, kind="ats", say=say)
lib2.cell("the bye dog itself", by, say=say)
anyp = [r for r in R if r["odds"] >= 100 and (d(r["oprev_gap_h"]) or 0) >= 13 and (d(r["prev_gap_h"]) or 99) <= 8.5]
lib2.cell("dog (any plus price) vs a bye team", anyp, say=say)
say(f"price-free: won {100 * sum(r['won'] for r in vs) / len(vs):.1f}% vs the no-vig close {100 * sum(r['p_nv'] for r in vs) / len(vs):.1f}% ({len(vs)})")
fv = [r for r in R if r["odds"] < 0 and (d(r["prev_gap_h"]) or 0) >= 13 and (d(r["oprev_gap_h"]) or 99) <= 8.5]
lib2.cell("the bye team as a favorite, any price", fv, say=say)
lib2.cell("the bye team as a favorite -150..-101", [r for r in fv if r["odds"] >= -150], say=say)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1c_out.txt"), "w").write("\n".join(L) + "\n")
