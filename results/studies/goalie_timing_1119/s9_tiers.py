"""S9 - SIZE x THE GOALIE, and the size tiers as they stand (no size changed by this study).
(1) every hockey size tier on the board (profit_1117's plan = today's sizes, the ⭐ raise in) split by what could be
    known about the nets: at 8 AM (the projection) and after the confirmation (who started, the pulled-starter trap out:
    the man on file faced 24+ shots). A size should follow the goalie only if the cell wins MORE in BOTH halves.
(2) the tiers after this study (unchanged): what is in each, the held-out record, the ROI."""
import os
import sys
from collections import defaultdict
import glib

sys.path.insert(0, os.path.join(glib.ROOT, "results", "studies", "profit_1117"))
import plib as L  # noqa: E402

M = L.M
D = M.D
say = glib.Tee(glib.HERE + "/s9_tiers.out")
CE = ["ru2", "cfb_thin"]
_pre = L.sizes(pieces=CE)
SZ = L.sizes(pieces=CE, star=2.0, star_ok=lambda r: r["odds"] <= 150 and (r["kind"] in ("lock", "dog") or _pre[id(r)][0] >= 1.0))
SIDES = {(s["gid"], s["side"]): s for s in glib.games()}


def fl(rs):
    w = sum(r["result"] == "won" for r in rs)
    return w, len(rs) - w, (100 * sum(M.flat(r) for r in rs) / len(rs) if rs else 0.0)


def cell(name, rs):
    tr = [r for r in rs if M.half(r["date"]) == "train"]
    he = [r for r in rs if M.half(r["date"]) == "held"]
    a, b, c = fl(tr + he), fl(tr), fl(he)
    u = sum(SZ[id(r)][1] * M.flat(r) for r in tr + he)
    say(f"    {name:46s} {a[0]:3d}-{a[1]:<3d} {a[2]:+6.1f}% | train {b[0]:3d}-{b[1]:<3d} {b[2]:+6.1f}% | held {c[0]:3d}-{c[1]:<3d} {c[2]:+6.1f}% | units {u:+6.1f}")


H = []
for r in L.P:
    if r["league"] != "nhl":
        continue
    s = SIDES.get((r["gid"], r["side"]))
    if not s:
        continue
    me, op = s["g_me"], s["g_op"]
    r["pm"] = None if not me["n1"] or not me["proj"] else "n1" if me["proj"] == me["n1"] else "bk"
    r["po"] = None if not op["n1"] or not op["proj"] else "n1" if op["proj"] == op["n1"] else "bk"
    r["rm"] = None if not me["n1"] or float(me["sa"] or 0) < 24 else "n1" if me["actual"] == me["n1"] else "bk"
    r["ro"] = None if not op["n1"] or float(op["sa"] or 0) < 24 else "n1" if op["actual"] == op["n1"] else "bk"
    H.append(r)

say("=== (1) THE HOCKEY SIZE TIERS x THE GOALIE (R3, the close; units at today's sizes)")
for u in (3.0, 2.0, 1.0, 0.5):
    T = [r for r in H if SZ[id(r)][1] == u]
    if not T:
        continue
    kinds = defaultdict(int)
    for r in T:
        kinds[r["k"].rsplit(" (", 1)[0] + (" ⭐" if SZ[id(r)][2] and SZ[id(r)][1] > SZ[id(r)][0] else "")] += 1
    say(f" -- {u:g}u ({len(T)} plays): " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items(), key=lambda x: -x[1])))
    cell("all", T)
    say("   at 8 AM (the projection):")
    cell("projected: our #1", [r for r in T if r["pm"] == "n1"])
    cell("projected: our backup", [r for r in T if r["pm"] == "bk"])
    cell("projected: their #1", [r for r in T if r["po"] == "n1"])
    cell("projected: their backup", [r for r in T if r["po"] == "bk"])
    say("   after the confirmation (who started, 24+ shots on him):")
    cell("our #1 started", [r for r in T if r["rm"] == "n1"])
    cell("our backup started", [r for r in T if r["rm"] == "bk"])
    cell("their #1 started", [r for r in T if r["ro"] == "n1"])
    cell("their backup started", [r for r in T if r["ro"] == "bk"])
    cell("our #1 in OR their backup in", [r for r in T if r["rm"] == "n1" or r["ro"] == "bk"])
    cell("our backup in AND their #1 in", [r for r in T if r["rm"] == "bk" and r["ro"] == "n1"])

say("\n=== (2) THE SIZE TIERS AS THEY STAND (every sport on the rig; the ⭐ raise in) - unchanged by this study")
t = defaultdict(list)
for r in L.P:
    t[SZ[id(r)][1]].append(r)
for u in sorted(t, reverse=True):
    rs = t[u]
    tr = [r for r in rs if M.half(r["date"]) == "train"]
    he = [r for r in rs if M.half(r["date"]) == "held"]
    lv = [r for r in rs if M.half(r["date"]) == "live"]
    a, b, c, d = fl(tr + he), fl(tr), fl(he), fl(lv)
    net = sum(u * M.flat(r) for r in tr + he)
    kinds = defaultdict(int)
    for r in tr + he:
        kinds[r["k"].rsplit(" (", 1)[0] + (" ⭐" if SZ[id(r)][2] and SZ[id(r)][1] > SZ[id(r)][0] else "")] += 1
    say(f" -- {u:g}u: {a[0]}-{a[1]} {a[2]:+.1f}% a bet, {net:+.1f}u | train {b[0]}-{b[1]} {b[2]:+.1f}% | HELD OUT {c[0]}-{c[1]} {c[2]:+.1f}% | the live-replay weeks {d[0]}-{d[1]} {d[2]:+.1f}%")
    say("      " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items(), key=lambda x: -x[1])[:9]))
o = L.summ(SZ)
say(f"\n  the board: {o['net'] / L.YEARS:+.1f}u a year, ROI {o['roi']:+.1f}%, train {o['tr']:+.1f}u / held {o['he']:+.1f}u, worst stretch {o['dd']:+.1f}u, seasons up {o['up']}/{o['ns']}")
