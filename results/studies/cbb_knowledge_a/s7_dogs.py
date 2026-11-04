"""S7 - THE DOG VIEW (the owner, 11/3: "be able to predict these dogs ... be on the right side of the price"): every
knowledge piece from s1-s5 read on DOGS +100..+350 only - which dogs WIN against the price and which lose - one grid:
each fact x all / home / road / +100..+200 / +201..+350 / Nov-Dec / Jan-Mar, the dog's ATS beside it, and the STACK
(how the facts combine: the dog with 2+ good facts and none bad, the dog with 2+ bad facts). Train / held out as in
each study (prices 2018-26; the box / roster facts 2021-26); ESPN's open on every ML cell."""
import importlib.util, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403
import sports_ncaab_coaches as nc

out = Out("s7")
rows_ = regular(rows())
rows_.sort(key=lambda x: (x["start"], x["id"]))
month = lambda x: x["start"][5:7]
# ---- coaches ----
table = nc.load()
for x in rows_:
    x["c"], x["oc"] = nc.state(x["team"], x["start"], table), nc.state(x["opp"], x["start"], table)
# ---- standings (s5) ----
stand = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for x in rows_:
    if not x["same_conf"] or not x["conf"]:
        continue
    tab = stand[(x["season"], x["conf"])]
    mine, theirs = tab[x["team"]], tab[x["opp"]]
    if len(tab) >= 6 and mine[0] + mine[1] >= 8 and theirs[0] + theirs[1] >= 8:
        lead = max(v[0] - v[1] for v in tab.values())
        x["gb"], x["ogb"] = (lead - (mine[0] - mine[1])) / 2, (lead - (theirs[0] - theirs[1])) / 2
    tab[x["team"]][0 if x["won"] else 1] += 1
# ---- identity (s4) ----
TB = teambox()
score = {(x["id"], x["team"]): (x["pts"] + x["margin"]) / 2 for x in rows_}
agg, lg, feat = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float)), {}
for x in rows_:
    if x["season"] < 2021:
        continue
    s, tm, op = x["season"], x["team"], x["opp"]
    a, L = agg[(s, tm)], lg[s]
    if a["n"] >= 5 and L["n"] >= 200:
        feat[(x["id"], tm)] = {"off": 100 * a["pts"] / a["poss"] - 100 * L["pts"] / L["poss"],
                               "def": 100 * a["opts"] / a["oposs"] - 100 * L["pts"] / L["poss"], "tom": (a["oto"] - a["to"]) / a["n"]}
    b = TB.get(x["id"])
    if b and tm in b and op in b and (x["id"], tm) in score and (x["id"], op) in score:
        me, th = b[tm], b[op]
        for d in (a, L):
            d["n"] += 1; d["pts"] += score[(x["id"], tm)]; d["poss"] += me["poss"]; d["opts"] += score[(x["id"], op)]
            d["oposs"] += th["poss"]; d["to"] += me["to"]; d["oto"] += th["to"]
for x in rows_:
    x["f"], x["of"] = feat.get((x["id"], x["team"])), feat.get((x["id"], x["opp"]))
# ---- availability (s2) ----
box = playerbox()
by_team = defaultdict(list)
for x in rows_:
    if x["season"] >= 2021:
        by_team[(x["season"], x["team"])].append(x)
av = {}
for (s, tm), xs in by_team.items():
    hist = []
    for x in xs:
        b = (box.get(x["id"]) or {}).get(tm)
        if len(hist) >= 5:
            mp = defaultdict(float)
            for hb in hist:
                for pid, m in hb.items():
                    mp[pid] += m
            n = len(hist)
            regs = sorted(((v / n, pid) for pid, v in mp.items() if v / n >= 15), reverse=True)[:7]
            top = max(mp.items(), key=lambda kv: kv[1])[0]
            long_, out_last = 0, 0
            for _, pid in regs:
                run = 0
                for hb in reversed(hist):
                    if hb.get(pid, 0) > 0:
                        break
                    run += 1
                if run >= 1:
                    out_last += 1
                if run >= 4 and pid != top:
                    long_ += 1
            av[(x["id"], tm)] = (long_, out_last)
        if b is not None:
            hist.append({pid: v[0] for pid, v in b.items()})
for x in rows_:
    x["av"], x["oav"] = av.get((x["id"], x["team"])), av.get((x["id"], x["opp"]))
# ---- roster mix (s3, the deep roster table) ----
_dl = importlib.util.spec_from_file_location("lib", os.path.join(ROOT, "results/studies/deep_cbb_roster/lib.py"))
DL = importlib.util.module_from_spec(_dl)
_mine = sys.modules.get("lib")
sys.modules["lib"] = DL
_dl.loader.exec_module(DL)
_spec = importlib.util.spec_from_file_location("deep_feat", os.path.join(ROOT, "results/studies/deep_cbb_roster/features.py"))
FE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FE)
if _mine is not None:
    sys.modules["lib"] = _mine
F = FE.build()
for x in rows_:
    f, of = F.get((x["id"], x["team"])), F.get((x["id"], x["opp"]))
    x["rm"] = (f.get("sf_tin"), f.get("sf_new")) if f and f.get("sf_n", 0) >= 10 else None
    x["orm"] = (of.get("sf_tin"), of.get("sf_new")) if of and of.get("sf_n", 0) >= 10 else None

D = dogs(rows_)
late = lambda x: month(x) in ("01", "02", "03")
early = lambda x: month(x) in ("11", "12")
# the facts, each a predicate on a dog row (GOOD = the dog wins vs the price, BAD = it loses)
cut = {}
for k in ("off", "def", "tom"):
    for s in sorted({x["season"] for x in rows_ if x["f"]}):
        v = sorted(x["f"][k] for x in rows_ if x["season"] == s and x["f"])
        cut[(k, s)] = (v[len(v) // 3], v[2 * len(v) // 3])
hi = lambda x, k, w="f": x[w] and x[w][k] >= cut[(k, x["season"])][1]
lo = lambda x, k, w="f": x[w] and x[w][k] <= cut[(k, x["season"])][0]
FACTS = {
    "BAD  new coach, Jan-Mar": lambda x: x["c"] and x["c"]["new"] and late(x),
    "     new coach, Nov-Dec": lambda x: x["c"] and x["c"]["new"] and early(x),
    "     coach 8+ years": lambda x: x["c"] and (x["c"].get("tenure") or x["c"].get("tenure_min")) >= 8,
    "     vs a new coach": lambda x: x["oc"] and x["oc"]["new"],
    "BAD  a regular out 4+ games": lambda x: x["av"] and x["av"][0] >= 1,
    "     2+ regulars out of the last game": lambda x: x["av"] and x["av"][1] >= 2,
    "GOOD whole vs 2+ out across": lambda x: x["av"] and x["oav"] and x["av"][1] == 0 and x["oav"][1] >= 2,
    "     vs a regular out 4+ across": lambda x: x["oav"] and x["oav"][0] >= 1,
    "BAD  transfer-heavy (top third), Jan-Mar": lambda x: x["rm"] and x["rm"][0] >= 0.28 and late(x),
    "     freshman-heavy (top third), Feb-Mar": lambda x: x["rm"] and x["rm"][1] >= 0.26 and month(x) in ("02", "03"),
    "     vs a freshman-heavy team, Feb-Mar": lambda x: x["orm"] and x["orm"][1] >= 0.26 and month(x) in ("02", "03"),
    "BAD  offense-first, Jan-Mar": lambda x: hi(x, "off") and not lo(x, "def") and late(x),
    "GOOD defense-first vs a bottom-third offense": lambda x: lo(x, "def") and not hi(x, "off") and lo(x, "off", "of"),
    "     defense-first, Jan-Mar": lambda x: lo(x, "def") and not hi(x, "off") and late(x),
    "     turnover-margin (top third)": lambda x: hi(x, "tom"),
    "     vs a turnover-prone fav": lambda x: lo(x, "tom", "of"),
    "BAD  5+ back vs a contender, Feb-Mar": lambda x: x.get("gb") is not None and x["gb"] >= 5 and x["ogb"] <= 1 and month(x) in ("02", "03") and x["tier"] != "power",
    "     5+ back vs 5+ back, Feb-Mar": lambda x: x.get("gb") is not None and x["gb"] >= 5 and x["ogb"] >= 5 and month(x) in ("02", "03"),
    "     the contender as a road dog, Feb-Mar": lambda x: x.get("gb") is not None and x["gb"] <= 1 and x["venue"] == "away" and month(x) in ("02", "03"),
    "     the leader as a dog, Feb-Mar": lambda x: x.get("gb") is not None and x["gb"] == 0 and month(x) in ("02", "03"),
    "     bottom-three home dog, Feb-Mar": lambda x: x.get("gb") is not None and x["gb"] >= 5 and x["venue"] == "home" and month(x) in ("02", "03"),
}
out.h("THE DOG GRID (dogs +100..+350 at the close; ML ROI | train / held | the open) - BAD = the built fade, GOOD = the dog pays")
out.c("base: every college hoops dog +100..+350", D)
out.c("base: home dogs", [x for x in D if x["venue"] == "home"])
out.c("base: road dogs", [x for x in D if x["venue"] == "away"])
out.c("base: Jan-Mar dogs", [x for x in D if late(x)])
for name, fn in FACTS.items():
    sub = [x for x in D if fn(x)]
    out.c(name, sub)
    out.c(f"   {name.strip()[:34]} | home", [x for x in sub if x["venue"] == "home"])
    out.c(f"   {name.strip()[:34]} | road", [x for x in sub if x["venue"] == "away"])
    out.c(f"   {name.strip()[:34]} | +100..+200", [x for x in sub if x["ml"] <= 200])
    out.c(f"   {name.strip()[:34]} | +201..+350", [x for x in sub if x["ml"] > 200])
    out.c(f"   {name.strip()[:34]} | ATS", spreads(sub), profit_ats)
out.h("THE STACK - how the facts combine on one dog (2021+ dogs with the box / roster reads)")
bad = [fn for k, fn in FACTS.items() if k.startswith("BAD")]
good = [fn for k, fn in FACTS.items() if k.startswith("GOOD")]
D2 = [x for x in D if x["season"] >= 2021 and x["f"] and x["av"] is not None]
nb_ = lambda x: sum(1 for fn in bad if fn(x))
ng_ = lambda x: sum(1 for fn in good if fn(x))
out.c("2021+ dogs with reads: base", D2)
out.c("no bad fact, no good fact", [x for x in D2 if nb_(x) == 0 and ng_(x) == 0])
out.c("1 bad fact", [x for x in D2 if nb_(x) == 1])
out.c("2+ bad facts", [x for x in D2 if nb_(x) >= 2])
out.c("1+ good fact, no bad", [x for x in D2 if ng_(x) >= 1 and nb_(x) == 0])
out.c("1+ good fact, no bad, Jan-Mar", [x for x in D2 if ng_(x) >= 1 and nb_(x) == 0 and late(x)])
out.c("1+ good fact, no bad, +100..+200", [x for x in D2 if ng_(x) >= 1 and nb_(x) == 0 and x["ml"] <= 200])
out.c("1+ good fact, no bad, home", [x for x in D2 if ng_(x) >= 1 and nb_(x) == 0 and x["venue"] == "home"])
out.c("1+ good AND 1+ bad", [x for x in D2 if ng_(x) >= 1 and nb_(x) >= 1])
# next to the built college hoops dog weights (the 11/3 (A)/(B)/DEEP/FABLE ones the side table can see)
skid = lambda x: x.get("streak", 0) <= -5
out.c("no bad fact, not on a 5+ skid, games 6+ (the floor's crowd)", [x for x in D2 if nb_(x) == 0 and not skid(x) and x["gn"] >= 6])
out.c("no bad fact, not on a skid, games 6+, home, +100..+200", [x for x in D2 if nb_(x) == 0 and not skid(x) and x["gn"] >= 6 and x["venue"] == "home" and x["ml"] <= 200])
out.save()
