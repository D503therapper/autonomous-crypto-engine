"""S5 - (d) THE FAVORITE'S BACKUP IS IN: season by season, with the pulled-starter trap out, and what WAITING for it
would have paid (the price after the news = the close).
The cell: a dog +100..+350 whose favorite started somebody other than its clear #1 (the man on file faced 24+ shots,
so he is the real starter), vs the same dogs facing the #1 (24+ shots too)."""
from collections import defaultdict
import glib
from glib import line, st

say = glib.Tee(glib.HERE + "/s5_backup.out")
S = glib.games()
for r in S:
    me, op = r["g_me"], r["g_op"]
    r["rm"] = None if not me["n1"] else "n1" if me["actual"] == me["n1"] else "bk"
    r["ro"] = None if not op["n1"] else "n1" if op["actual"] == op["n1"] else "bk"
    r["sa_o"], r["sa_m"] = float(op["sa"] or 0), float(me["sa"] or 0)
    r["b2b"], r["ob2b"] = me["b2b"], op["b2b"]
    r["share_o"] = op["n1_share"]
    r["act_n10"] = op["n10"].get(op["actual"], 0)
D = [r for r in S if 100 <= r["odds_c"] <= 350 and r["sa_o"] >= 24 and r["ro"]]

say("=== every dog +100..+350 at the close, the favorite's goalie on file faced 24+ shots - by season")
say(f"  {'season':8s} {'their #1':>26s} {'their backup':>26s}   gap")
for s in sorted({r["season"] for r in D}):
    a = st([r for r in D if r["season"] == s and r["ro"] == "n1"])
    b = st([r for r in D if r["season"] == s and r["ro"] == "bk"])
    say(f"  {s:8s} {a['w']:4d}-{a['n'] - a['w']:<4d} {a['roi']:+6.1f}% z {a['z']:+5.2f}   {b['w']:4d}-{b['n'] - b['w']:<4d} {b['roi']:+6.1f}% z {b['z']:+5.2f}   {b['roi'] - a['roi']:+6.1f}")
say("\n=== the same cell cut finer (2018-26, the close)")
bk = [r for r in D if r["ro"] == "bk"]
n1 = [r for r in D if r["ro"] == "n1"]
line("their #1", n1, say=say)
line("their backup", bk, say=say)
line("their backup, the favorite on a b2b", [r for r in bk if r["ob2b"]], say=say)
line("their backup, the favorite rested", [r for r in bk if not r["ob2b"]], say=say)
line("their #1, the favorite on a b2b", [r for r in n1 if r["ob2b"]], say=say)
line("their backup, a true #2 (0-2 of the last 10 starts)", [r for r in bk if r["act_n10"] <= 2], say=say)
line("their backup, a 1B (3+ of the last 10 starts)", [r for r in bk if r["act_n10"] >= 3], say=say)
line("their backup, the #1 is a workhorse (8+ of 10)", [r for r in bk if (r["share_o"] or 0) >= 0.8], say=say)
line("their backup, dog +100..+150", [r for r in bk if r["odds_c"] <= 150], say=say)
line("their #1, dog +100..+150", [r for r in n1 if r["odds_c"] <= 150], say=say)
line("their backup, dog +151..+350", [r for r in bk if r["odds_c"] > 150], say=say)
line("their #1, dog +151..+350", [r for r in n1 if r["odds_c"] > 150], say=say)
line("their backup, the dog at home", [r for r in bk if r["home"]], say=say)
line("their backup, the dog on the road", [r for r in bk if not r["home"]], say=say)
line("their backup AND our #1 in", [r for r in bk if r["rm"] == "n1"], say=say)
line("their backup AND our backup in", [r for r in bk if r["rm"] == "bk"], say=say)
pool = D
say(f"  placebo (their backup vs a random same-size set of these dogs): as good {glib.placebo(bk, pool)} of 2,000")
say(f"  placebo (their #1): as bad {glib.placebo(n1, pool, lo=True)} of 2,000")

say("\n=== the same cell at the price BEFORE the news (same 24+ shots rule)")
for key, lab, pk in (("dec_m", "the paid MORNING 2021-23", "p_m"), ("dec_o", "ESPN's OPEN 2023-26", "p_o")):
    Q = [r for r in S if r.get(key) and 100 <= glib.am(r[key]) <= 350 and r["sa_o"] >= 24 and r["ro"]]
    for k in ("n1", "bk"):
        c = [r for r in Q if r["ro"] == k]
        line(f"{lab}: their {k}", c, key, say)
        mv = [100 * (r["p_c"] - r[pk]) for r in c]
        say(f"      the same bets at the close {st(c, 'dec_c')['roi']:+.1f}%; the market's move to the dog by the close {sum(mv) / len(mv):+.2f} pts")

say("\n=== the favorite's side of it: a favorite -101..-250 at the close whose OWN backup is in (24+ shots on him)")
F = [r for r in S if -250 <= r["odds_c"] <= -101 and r["sa_m"] >= 24 and r["rm"]]
line("the favorite starts its #1", [r for r in F if r["rm"] == "n1"], say=say)
line("the favorite starts its backup", [r for r in F if r["rm"] == "bk"], say=say)
by = defaultdict(list)
for r in F:
    by[(r["season"], r["rm"])].append(r)
say("  by season (the favorite's ROI: #1 / backup): " + "; ".join(
    f"{s} {st(by[(s, 'n1')])['roi']:+.1f} / {st(by[(s, 'bk')])['roi']:+.1f}" for s in sorted({k[0] for k in by})))
