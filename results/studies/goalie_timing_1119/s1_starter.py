"""S1 - (a) HOW MUCH DOES A HOCKEY BET DEPEND ON THE GOALIE WHO ACTUALLY STARTED, against the price?
Three prices: the CLOSE (2018-26, the starter is known and priced), the paid MORNING look (2021-23 - the 8 AM board's
hour, the starter mostly NOT known) and ESPN's OPEN (2023-26, the night before - not known). A cell that loses at the
morning / open and not at the close = news the 8 AM price doesn't have (worth waiting for or re-weighing on); a cell
flat everywhere = the price has it whenever you bet.
  role: n1 = the team's clear #1 started, bk = somebody else did (teams with a clear #1 only)
  surprise: what the engine's own 8 AM projection said vs who started."""
import glib
from glib import line, st

say = glib.Tee(glib.HERE + "/s1_starter.out")
S = glib.games()


def role(g):
    return None if not g["n1"] else "n1" if g["actual"] == g["n1"] else "bk"


def surprise(g):
    """'as projected' / 'backup instead' (we projected the #1, another man started) / '#1 instead' (we projected the
    other man, the #1 started) / 'other' (two non-#1s) / None (no projection or no clear #1)."""
    if not g["proj"] or not g["n1"]:
        return None
    if g["proj"] == g["actual"]:
        return "as projected"
    if g["proj"] == g["n1"]:
        return "backup instead"
    if g["actual"] == g["n1"]:
        return "#1 instead"
    return "other"


for r in S:
    r["rm"], r["ro"] = role(r["g_me"]), role(r["g_op"])
    r["sm"], r["so"] = surprise(r["g_me"]), surprise(r["g_op"])
    r["b2b"], r["ob2b"] = r["g_me"]["b2b"], r["g_op"]["b2b"]

PR = (("close 2018-26", "dec_c", "p_c"), ("MORNING 2021-23", "dec_m", "p_m"), ("OPEN 2023-26", "dec_o", "p_o"))


def band(r, key, lo, hi):
    d = r.get(key)
    if not d:
        return False
    a = glib.am(d)
    return lo <= a <= hi


def move(rs, pk):
    xs = [100 * (r["p_c"] - r[pk]) for r in rs if r.get(pk) is not None]
    return sum(xs) / len(xs) if xs else 0.0


for title, lo, hi in (("DOGS +100..+350", 100, 350), ("FAVORITES -101..-250", -250, -101)):
    say(f"\n================ {title}")
    for nm, key, pk in PR:
        P = [r for r in S if band(r, key, lo, hi) and (key == "dec_c" or r["season"] != "2026-27" or True)]
        say(f"\n--- priced at the {nm}")
        line("every side", P, key, say)
        for a, b in (("n1", "n1"), ("n1", "bk"), ("bk", "n1"), ("bk", "bk")):
            c = [r for r in P if r["rm"] == a and r["ro"] == b]
            line(f"ours {a} / theirs {b}", c, key, say)
            if key != "dec_c":
                say(f"      the market's move to this side by the close: {move(c, pk):+.2f} pts; the same bets at the close: {st(c, 'dec_c')['roi']:+.1f}%")
        for a in ("n1", "bk"):
            line(f"ours {a} (any theirs), neither on a b2b", [r for r in P if r["rm"] == a and not r["b2b"] and not r["ob2b"]], key, say)
        for b in ("n1", "bk"):
            line(f"theirs {b} (any ours), neither on a b2b", [r for r in P if r["ro"] == b and not r["b2b"] and not r["ob2b"]], key, say)
        if key != "dec_c":
            say("  .. the 8 AM projection vs who started (the news after the board):")
            for k in ("as projected", "backup instead", "#1 instead", "other"):
                c = [r for r in P if r["sm"] == k]
                line(f"OUR goalie: {k}", c, key, say)
                say(f"      move to us by the close {move(c, pk):+.2f} pts; at the close {st(c, 'dec_c')['roi']:+.1f}%")
            for k in ("as projected", "backup instead", "#1 instead", "other"):
                c = [r for r in P if r["so"] == k]
                line(f"THEIR goalie: {k}", c, key, say)
                say(f"      move to us by the close {move(c, pk):+.2f} pts; at the close {st(c, 'dec_c')['roi']:+.1f}%")
            c = [r for r in P if r["sm"] == "as projected" and r["so"] == "as projected"]
            line("BOTH as projected", c, key, say)
            c = [r for r in P if r["sm"] and r["so"] and (r["sm"] != "as projected" or r["so"] != "as projected")]
            line("EITHER projection wrong", c, key, say)

say("\n================ the save % gap between a #1 and the other man (what the role is worth on the ice)")
G = glib.goalies()
tot = {"n1": [0.0, 0.0], "bk": [0.0, 0.0]}
for (gid, t), g in G.items():
    k = role(g)
    if k and float(g["sa"] or 0) >= 10:
        tot[k][0] += float(g["sa"]) - float(g["ga"])
        tot[k][1] += float(g["sa"])
for k, (sv, sa) in tot.items():
    say(f"  {k}: save % {sv / sa:.4f} on {sa:.0f} shots")
