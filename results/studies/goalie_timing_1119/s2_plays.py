"""S2 - (b) THE ENGINE'S OWN HOCKEY PLAYS x THE GOALIE WHO STARTED (R3: the board on today's code 2023-10 -> 2026-11,
the close; money_1117's live shapes and sizes). Did the plays made off a projection that turned out WRONG do worse?
Does a play's edge live with our #1 in / their backup in? Both at the close (the row's price) and at ESPN's open
(the night-before number - before any goalie news)."""
import sys
import os
import glib
from glib import line, st

sys.path.insert(0, os.path.join(glib.ROOT, "results", "studies", "money_1117"))
import mlib as M  # noqa: E402
import dlib as D  # noqa: E402

say = glib.Tee(glib.HERE + "/s2_plays.out")
SIDES = {(s["gid"], s["side"]): s for s in glib.games()}


def hf(d):
    h = D.half(d)
    return h


def join(r):
    s = SIDES.get((r["gid"], r["side"]))
    if not s:
        return None
    me, op = s["g_me"], s["g_op"]
    r["won"] = r["result"] == "won"
    r["dec_c"] = r["dec"]
    r["dec_o"] = s["dec_o"]
    r["p_c"], r["p_o"] = s["p_c"], s["p_o"]
    r["rm"] = None if not me["n1"] else "n1" if me["actual"] == me["n1"] else "bk"
    r["ro"] = None if not op["n1"] else "n1" if op["actual"] == op["n1"] else "bk"
    r["pm_ok"] = None if not me["proj"] else me["proj"] == me["actual"]
    r["po_ok"] = None if not op["proj"] else op["proj"] == op["actual"]
    r["g_me"], r["g_op"] = me, op
    # the key edge (save % form gap x50) on the PROJECTED men (what 8 AM read) and on the men who STARTED
    def ke(a, b):
        return (me["sv"][a] - op["sv"][b]) * 50 if a in me["sv"] and b in op["sv"] else None
    r["ke_proj"] = ke(me["proj"], op["proj"])
    r["ke_act"] = ke(me["actual"], op["actual"])
    return r


P, DAYS = M.board()
H = [r for r in P if r["league"] == "nhl"]
H = [r for r in H if join(r)]
ALL = [r for r in D.r3() if r["league"] == "nhl" and r["market"] == "ml"]
ALL = [r for r in ALL if join(r)]
DOGS = [r for r in ALL if 100 <= r["odds"] <= 350]
say(f"hockey unit plays on the R3 board: {len(H)}; every hockey dog row: {len(DOGS)}")

# which goalies did the replay's key edge read - the projection or the men who started?
import statistics
xs = [(r["x"].get("key_edge"), r["ke_proj"], r["ke_act"]) for r in DOGS if r["x"].get("key_edge") is not None and r["ke_proj"] is not None and r["ke_act"] is not None]
say(f"the replay's key edge vs ours: |x - projected| median {statistics.median(abs(a - b) for a, b, c in xs):.3f}, "
    f"|x - actual| median {statistics.median(abs(a - c) for a, b, c in xs):.3f}  (n {len(xs)})")
say(f"  exact matches: projected {sum(abs(a - b) < 0.01 for a, b, c in xs)}, actual {sum(abs(a - c) < 0.01 for a, b, c in xs)}")


def L(name, rs, key="dec_c"):
    return line(name, rs, key, say, hf=hf, w=58)


def block(title, rs):
    say(f"\n=== {title} ({len(rs)})")
    for key, nm in (("dec_c", "at the close"), ("dec_o", "at ESPN's open")):
        say(f" -- {nm}")
        L("all", rs, key)
        L("both goalies as projected", [r for r in rs if r["pm_ok"] and r["po_ok"]], key)
        L("OUR projection wrong", [r for r in rs if r["pm_ok"] is False], key)
        L("THEIR projection wrong", [r for r in rs if r["po_ok"] is False], key)
        L("either wrong", [r for r in rs if r["pm_ok"] is False or r["po_ok"] is False], key)
        for a, b in (("n1", "n1"), ("n1", "bk"), ("bk", "n1"), ("bk", "bk")):
            L(f"ours {a} / theirs {b}", [r for r in rs if r["rm"] == a and r["ro"] == b], key)
        L("ours n1 (any)", [r for r in rs if r["rm"] == "n1"], key)
        L("ours bk (any)", [r for r in rs if r["rm"] == "bk"], key)
        L("theirs n1 (any)", [r for r in rs if r["ro"] == "n1"], key)
        L("theirs bk (any)", [r for r in rs if r["ro"] == "bk"], key)


block("EVERY HOCKEY UNIT PLAY", H)
block("EVERY HOCKEY DOG UNIT PLAY (Dog / runner-up / floor)", [r for r in H if r["odds"] >= 100])
block("THE HOCKEY DOG OF THE DAY", [r for r in H if r["kind"] == "dog"])
block("THE DOG OF THE DAY +100..+150 (2u) + the 💎 3u spot", [r for r in H if r["kind"] == "dog" and r["u0"] >= 2])
block("THE 💎 b2b SPOT (3u)", [r for r in H if r["kind"] == "dog" and r["u0"] >= 3])
block("THE RUNNER-UP DOG", [r for r in H if r["kind"] == "dogplay"])
block("THE FLOOR'S HOCKEY DOGS", [r for r in H if r["kind"] == "floor"])
block("HOCKEY FAVORITES (Lock / value play)", [r for r in H if r["odds"] < 0])
block("EVERY GATED HOCKEY DOG (score 6+), posted or not", [r for r in DOGS if (r.get("dog_score") or -99) >= 6])
block("EVERY HOCKEY DOG, posted or not", DOGS)

say("\n=== placebo: the posted hockey dogs with OUR projection wrong vs a random same-size set of posted hockey dogs")
pd = [r for r in H if r["odds"] >= 100]
for nm, c in (("our projection wrong", [r for r in pd if r["pm_ok"] is False]), ("their projection wrong", [r for r in pd if r["po_ok"] is False]),
              ("ours n1 / theirs bk", [r for r in pd if r["rm"] == "n1" and r["ro"] == "bk"]),
              ("ours bk / theirs n1", [r for r in pd if r["rm"] == "bk" and r["ro"] == "n1"]),
              ("theirs bk", [r for r in pd if r["ro"] == "bk"]), ("theirs n1", [r for r in pd if r["ro"] == "n1"])):
    c = [r for r in c if hf(r["date"]) != "live"]
    pool = [r for r in pd if hf(r["date"]) != "live"]
    say(f"  {nm:28s} n {len(c):4d} roi {st(c)['roi']:+6.1f}%  as good {glib.placebo(c, pool)} / as bad {glib.placebo(c, pool, lo=True)} of 2,000")
