"""S8. COLLEGE FOOTBALL BIG SPREADS (14+): the dog getting 14 / 21 / 28+, by the total (garbage-time points need a
game with points in it), home / road, the month, the favorite's last game - and the BACKDOOR itself from the
quarter scores: how often a big dog that wasn't covering after three quarters got there in the fourth.
Game files' closes 2016-26 at their own juice (train 2016-21, held 2022-26); the first FAIR number at the best book
(the paid history, 2021-26) for the dogs getting 20+.  Not re-run: favorites laying 21+ at the close (10/30: the vig),
the 14.5+ model slice (11/11 S9: luck).   python s8_ncaaf_big.py"""
import statistics
from collections import defaultdict
import lib2 as L

o = L.Out("s8")
B = L.B
FIN = [g for g in B.finals("ncaaf") if g["sp"] is not None and abs(g["sp"]) <= 60 and g["stype"] == "2"]
ALL = B.all_finals("ncaaf")
TL = B.team_log(ALL)
SPLIT = 2021


def q3(g):
    try:
        h = [float(x) for x in str(g["ls_h"]).split(",")]
        a = [float(x) for x in str(g["ls_a"]).split(",")]
    except (ValueError, TypeError):
        return None
    if len(h) < 4 or len(a) < 4:
        return None
    return sum(h[:3]) - sum(a[:3])


T = defaultdict(list)
bd = defaultdict(lambda: [0, 0, 0, 0])      # band -> [n, covering after 3, covered at the end having NOT been covering after 3, lost it in the 4th]
for g in FIN:
    if abs(g["sp"]) < 14:
        continue
    dog = "home" if g["sp"] > 0 else "away"
    pts = abs(g["sp"])
    p = B.ats(g, dog)
    if p is None:
        continue
    s = g["season"]
    band = "14-20.5" if pts < 21 else ("21-27.5" if pts < 28 else "28+")
    mth = g["start"][5:7]
    favt, dogt = (g["away"], g["home"]) if dog == "home" else (g["home"], g["away"])

    def add(k):
        T[k].append((s, p))
    add("every dog getting 14+")
    add(f"dog getting {band}")
    add(f"   {band}: home dog" if dog == "home" and not g["neutral"] else f"   {band}: road / neutral dog")
    if g["total"]:
        tb = "total 48 or less" if g["total"] <= 48 else ("total 48.5-58" if g["total"] <= 58 else "total 58.5+")
        add(f"dog getting 14+, {tb}")
        if pts >= 21:
            add(f"   dog getting 21+, {tb}")
    add("dog getting 14+, Sept" if mth in ("08", "09") else ("dog getting 14+, Oct" if mth == "10" else "dog getting 14+, Nov-Dec"))
    pf = B.before(TL, favt, g["start"], 1)
    pdg = B.before(TL, dogt, g["start"], 1)
    if pf and pf[-1]["season"] == s:
        lm = B.margin_g(pf[-1], favt)
        if lm >= 28:
            add("dog getting 14+ from a favorite off a 28+ win")
        if lm < 0:
            add("dog getting 14+ from a favorite off a LOSS")
    if pdg and pdg[-1]["season"] == s:
        lm = B.margin_g(pdg[-1], dogt)
        if lm <= -28:
            add("dog getting 14+ off a 28+ loss (nobody wants them)")
        if lm > 0:
            add("dog getting 14+ off a win")
    m3 = q3(g)
    if m3 is not None:
        d3 = (m3 if dog == "home" else -m3) + pts          # the dog's cover margin after three quarters
        mf = (g["hs"] - g["as"]) if dog == "home" else (g["as"] - g["hs"])
        df = mf + pts
        b = bd[band]
        b[0] += 1
        b[1] += d3 > 0
        b[2] += (d3 < 0 and df > 0)
        b[3] += (d3 > 0 and df < 0)
        if g["total"] and g["total"] >= 58.5 and pts >= 21:
            b2 = bd["21+ in a 58.5+ total"]
            b2[0] += 1; b2[1] += d3 > 0; b2[2] += (d3 < 0 and df > 0); b2[3] += (d3 > 0 and df < 0)

o(f"== College football dogs getting 14+ at the close ({len(T['every dog getting 14+'])} games 2016-26; train 2016-21 / held 2022-26) ==")
for k in T:
    r = T[k]
    if len(r) < 50:
        continue
    tr = [(s, p) for s, p in r if s <= SPLIT]
    he = [(s, p) for s, p in r if s > SPLIT]
    ut, uh = L.by_season(tr), L.by_season(he)
    o(f"   {k[:56]:56s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% ({ut[0]}/{ut[1]}) | HELD {L.st([p for _, p in he])} ({uh[0]}/{uh[1]} up: {uh[2]})")
o(f"   cells: {len(T)}")
o("\n== THE BACKDOOR, from the quarter scores (the big dog's cover after three quarters vs at the final) ==")
for k, b in bd.items():
    o(f"   dog getting {k:22s} n {b[0]:5d}: covering after three {b[1] / b[0] * 100:4.1f}% | the 4th-quarter BACKDOOR (not covering after 3, covered) {b[2] / b[0] * 100:4.1f}% | lost the cover in the 4th {b[3] / b[0] * 100:4.1f}%")
o("   (the back door opens about as often as it shuts - the number already has the garbage time in it)")

o("\n== THE FIRST FAIR NUMBER for the big dogs (the paid history 2021-26; median price / the best book) ==")
F = [g for g in L.football("ncaaf") if g["c_sp"] is not None and abs(g["c_sp"] - g["med"]) <= 10]
for lo, hi in ((14, 20.5), (21, 27.5), (28, 60), (20, 60)):
    a, b, c = [], [], []
    for g in F:
        if not (lo <= abs(g["med"]) <= hi):
            continue
        dog = "home" if g["med"] > 0 else "away"
        bk = {k: v for k, v in g["first"][1].items() if abs(v[0] - g["med"]) <= 1.5 and v[0] == -v[2] and -140 <= v[1] <= 125 and -140 <= v[3] <= 125}
        if len(bk) < 5:
            continue
        at = [L.dec(v[1] if dog == "home" else v[3]) for v in bk.values() if v[0] == g["med"]]
        best = max(((v[0], L.dec(v[1])) if dog == "home" else (v[2], L.dec(v[3]))) for v in bk.values())
        a.append((g["season"], L.cover(g["margin"], g["med"], dog, B.american(statistics.median(at)) if at else -110)))
        b.append((g["season"], L.cover(g["margin"], best[0] if dog == "home" else -best[0], dog, B.american(best[1]))))
        c.append((g["season"], L.cover(g["margin"], g["c_sp"], dog, (g["c_sho"] if dog == "home" else g["c_sao"]) or -110)))
    ub = L.by_season(b)
    o(f"   dog getting {lo}-{hi}: first fair, median {L.st([p for _, p in a])} | BEST BOOK {L.st([p for _, p in b])} ({ub[0]}/{ub[1]} up: {ub[2]}) | the close {L.st([p for _, p in c])}")
o(f"\ncells read: {len(T)} + 4 backdoor rows + 4 x 3 = ~{len(T) + 16}")
o.save()
