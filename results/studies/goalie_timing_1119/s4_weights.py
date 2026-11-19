"""S4 - THE ENGINE'S HOCKEY PLAYS, NO HINDSIGHT + THE GOALIE WEIGHTS THAT READ THE PROJECTION.
(1) the posted hockey dogs split by what the 8 AM PROJECTION said about each net (knowable at the post) and by who
    started with the pulled-starter trap taken out (the man on file faced 24+ shots).
(2) the two goalie weights on the dog score that read the projected men - the save % form gap (key_edge: our man much
    worse lately = +1 "the books overpay for the other goalie's hot run", much better = -2) and the hot goalie (-3) -
    on every hockey dog row of R3 (the close): do they sort dogs at all, do they sort only when the projection was
    RIGHT, and what do they say when re-read off the men who actually started (= a confirmed-starter read)?"""
import os
import sys
import glib
from glib import st

sys.path.insert(0, os.path.join(glib.ROOT, "results", "studies", "money_1117"))
import mlib as M  # noqa: E402
import dlib as D  # noqa: E402
import s2_plays as S2  # noqa: E402  (joins the rows; prints its own tables again into its own file)

say = glib.Tee(glib.HERE + "/s4_weights.out")
hf = D.half


def L(name, rs, key="dec_c"):
    return glib.line(name, rs, key, say, hf=hf, w=62)


for r in S2.ALL + S2.H:
    me, op = r["g_me"], r["g_op"]
    r["pm"] = None if not me["n1"] or not me["proj"] else "n1" if me["proj"] == me["n1"] else "bk"
    r["po"] = None if not op["n1"] or not op["proj"] else "n1" if op["proj"] == op["n1"] else "bk"
    r["sa_o"], r["sa_m"] = float(op["sa"] or 0), float(me["sa"] or 0)
    r["ob2b"], r["mb2b"] = op["b2b"], me["b2b"]
H, DOGS = S2.H, S2.DOGS
PD = [r for r in H if r["odds"] >= 100]

say("=== (1) THE POSTED HOCKEY DOGS (Dog / runner-up / floor) - what the 8 AM projection said (no hindsight)")
for nm, rs in (("every posted hockey dog", PD), ("the Dog of the Day", [r for r in PD if r["kind"] == "dog"]),
               ("the Dog at 2u / 3u (+100..+150 and the 💎 spot)", [r for r in PD if r["kind"] == "dog" and r["u0"] >= 2]),
               ("the runner-up dog", [r for r in PD if r["kind"] == "dogplay"]), ("the floor's dogs", [r for r in PD if r["kind"] == "floor"]),
               ("every gated hockey dog (score 6+), posted or not", [r for r in DOGS if (r.get("dog_score") or -99) >= 6]),
               ("every hockey dog row", DOGS)):
    say(f" -- {nm}")
    L("all", rs)
    L("projected: their #1", [r for r in rs if r["po"] == "n1"])
    L("projected: their backup", [r for r in rs if r["po"] == "bk"])
    L("projected: their backup, they're on a b2b", [r for r in rs if r["po"] == "bk" and r["ob2b"]])
    L("projected: their backup, NOT on a b2b", [r for r in rs if r["po"] == "bk" and not r["ob2b"]])
    L("projected: our #1", [r for r in rs if r["pm"] == "n1"])
    L("projected: our backup", [r for r in rs if r["pm"] == "bk"])
    L("projected: ours #1 / theirs #1", [r for r in rs if r["pm"] == "n1" and r["po"] == "n1"])
    L("the favorite on a b2b (x.rested_vs_b2b)", [r for r in rs if r["x"].get("rested_vs_b2b")])
    L("the favorite NOT on a b2b", [r for r in rs if not r["x"].get("rested_vs_b2b")])
    L("  ..NOT on a b2b, their backup STARTED (24+ shots)", [r for r in rs if not r["x"].get("rested_vs_b2b") and r["ro"] == "bk" and r["sa_o"] >= 24])
    L("  ..NOT on a b2b, their #1 STARTED (24+ shots)", [r for r in rs if not r["x"].get("rested_vs_b2b") and r["ro"] == "n1" and r["sa_o"] >= 24])
    L("started, trap out (24+ shots): their #1", [r for r in rs if r["ro"] == "n1" and r["sa_o"] >= 24])
    L("started, trap out (24+ shots): their backup", [r for r in rs if r["ro"] == "bk" and r["sa_o"] >= 24])
    L("started, trap out (27+ shots): their #1", [r for r in rs if r["ro"] == "n1" and r["sa_o"] >= 27])
    L("started, trap out (27+ shots): their backup", [r for r in rs if r["ro"] == "bk" and r["sa_o"] >= 27])
    L("started (24+ on ours): our #1", [r for r in rs if r["rm"] == "n1" and r["sa_m"] >= 24])
    L("started (24+ on ours): our backup", [r for r in rs if r["rm"] == "bk" and r["sa_m"] >= 24])

say("\n=== (2) THE GOALIE WEIGHTS ON THE DOG SCORE - every hockey dog row +100..+350 (R3, the close)")


def kw(k):
    return None if k is None else -2 if k >= 0.4 else 1 if k <= -0.4 else 0


for r in DOGS:
    r["w_proj"] = kw(r["ke_proj"])
    r["w_act"] = kw(r["ke_act"])
    r["both_ok"] = bool(r["pm_ok"] and r["po_ok"])
say(" -- the save % form gap as the board read it (the projected men)")
for w, nm in ((1, "+1: our man much worse lately"), (0, " 0: no gap"), (-2, "-2: our man much better lately")):
    L(f"weight {nm}", [r for r in DOGS if r["w_proj"] == w and not r["x"].get("hot_key")])
    L("   ...both projections RIGHT", [r for r in DOGS if r["w_proj"] == w and not r["x"].get("hot_key") and r["both_ok"]])
    L("   ...a projection WRONG", [r for r in DOGS if r["w_proj"] == w and not r["x"].get("hot_key") and not r["both_ok"]])
say(" -- the same gap re-read off the men who STARTED (what a confirmed-starter read would say)")
for w, nm in ((1, "+1: our man much worse lately"), (0, " 0: no gap"), (-2, "-2: our man much better lately")):
    L(f"weight {nm}", [r for r in DOGS if r["w_act"] == w])
say(" -- the hot goalie (-3) as the board read it")
L("hot_key on the dog", [r for r in DOGS if r["x"].get("hot_key")])
L("   ...both projections RIGHT", [r for r in DOGS if r["x"].get("hot_key") and r["both_ok"]])
L("   ...a projection WRONG", [r for r in DOGS if r["x"].get("hot_key") and not r["both_ok"]])
L("no hot_key", [r for r in DOGS if not r["x"].get("hot_key")])

say("\n -- what the weights did to the BOARD: gated dogs (score 6+) that the goalie weights carried or kept out")
for r in DOGS:
    p = r.get("parts") or {}
    r["gw"] = (p.get("key_edge") or 0) + (p.get("hot_key") or 0)
say("  parts seen: " + str(sorted({k for r in DOGS for k in (r.get('parts') or {}) if 'key' in k or 'hot' in k or 'role' in k or 'n1' in k or 'sv' in k})))
g6 = [r for r in DOGS if (r.get("dog_score") or -99) >= 6]
L("gated, no goalie weight in the score", [r for r in g6 if not r["gw"]])
L("gated, goalie weight +1 in the score", [r for r in g6 if r["gw"] > 0])
L("gated only BECAUSE of the +1 (score 6..6.99)", [r for r in g6 if r["gw"] > 0 and r["dog_score"] - r["gw"] < 6])
L("gated, goalie weight negative in the score", [r for r in g6 if r["gw"] < 0])
L("kept OUT by a negative goalie weight (5.x, 6+ without)", [r for r in DOGS if (r.get("dog_score") or -99) < 6 and r["gw"] < 0 and (r.get("dog_score") or -99) - r["gw"] >= 6])
say("  (the study part is capped at 6, so 'the score with the fact off' is the row's own parts table; uncapped rows only)")
pd_ = [r for r in PD]
L("POSTED dogs with the +1 in the score", [r for r in pd_ if r["gw"] > 0])
L("POSTED dogs with no goalie weight", [r for r in pd_ if not r["gw"]])
L("POSTED dogs with a negative goalie weight", [r for r in pd_ if r["gw"] < 0])
pool = [r for r in pd_ if hf(r["date"]) != "live"]
c = [r for r in pool if r["gw"] > 0]
say(f"  placebo, posted dogs with the +1: as good {glib.placebo(c, pool)} / as bad {glib.placebo(c, pool, lo=True)} of 2,000 (n {len(c)}, {st(c)['roi']:+.1f}%)")
