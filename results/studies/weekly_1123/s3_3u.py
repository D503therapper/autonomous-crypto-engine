"""11/23 - THE WEEKLY FABLE SIZING + EDGES REVIEW - S3: THE 💎 3u HOCKEY DOG TIER (the owner's open item, 11/20, after
the Ducks +110 3u lost 4-0: "Ducks got blown out terrible max play").
THE QUESTION: does the rested hockey Dog against a back-to-back favorite at a dog score of 8+ EARN 3u over the 2u the
short hockey Dog carries - on every season a rig can rebuild, both halves, a placebo - and does the DOG'S OWN LOAD (the
Ducks were on their 4th game in 6 nights; the spot only reads "didn't play last night") change it?
THE RIGS (all read-only, caches under ~/.cache, never the repo):
  OOS  the 11/2 paid-odds rig 2020-23 at the morning price - three seasons the 8+ cut never saw (nhl_odds_1102)
  R1 / R2  the 10/30 funnel boards 2023-26 (sizing_1114) - the rows the cut was first seen on
  R3L  the board TODAY's code builds 2023-26 (best_1122 / money_1117) - the rows STATUS quotes (17-14, held 10-5)
  RAW  every NHL regular-season side at the close 2018-26 with its schedule facts (max_pro_1116/mp.py) - no dog score,
       eight seasons: the rested dog against a b2b favorite by the DOG's own load (n4 = games in the 3 nights before,
       n6 = games in the 5 nights before; the Ducks 11/19: n6 = 3)
NEW HERE (not a repeat of 11/16's s3_score8): R3L as a fourth rig, the 3u-vs-2u test INSIDE the short Dogs with the live
games in, the size re-figured after the Ducks, and the dog's own load on every rig + eight raw seasons.
Usage: python results/studies/weekly_1123/s3_3u.py > results/studies/weekly_1123/s3_3u.out"""
import contextlib
import importlib.util
import io
import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(STUD))
sys.path.insert(0, os.path.join(STUD, "max_pro_1116"))
import mp  # noqa: E402

sys.path.insert(0, os.path.join(STUD, "sizing_1114"))
_d = sys.modules.pop("lib")
import lib as L  # noqa: E402
BO = L.boards()
sys.modules.pop("lib")
NH = os.path.join(STUD, "nhl_odds_1102")
sys.path.insert(0, NH)
with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)
nlib = sys.modules["lib"]
sys.modules["lib"] = _d
for _m in ("blib", "plib", "mlib", "dlib", "lib"):        # other studies' modules of the same names are loaded above
    sys.modules.pop(_m, None)
sys.path.insert(0, os.path.join(STUD, "best_1122"))
_sp = importlib.util.spec_from_file_location("blib_1122", os.path.join(STUD, "best_1122", "blib.py"))
B = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(B)


def st(rs, key="prof"):
    n = len(rs)
    if not n:
        return "n   0"
    w = sum(r["won"] for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:4d} {w:4d}-{n - w:<4d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(r[key] for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


def seasons(rs):
    s = defaultdict(list)
    for r in rs:
        s[r["season"]].append(r)
    return " ".join(f"{k}:{sum(x['won'] for x in v)}-{len(v) - sum(x['won'] for x in v)}" for k, v in sorted(s.items(), key=lambda kv: str(kv[0])))


def plc(sel, pool, n=2000, seed=7):
    if not sel or len(pool) < len(sel):
        return -1
    rnd = random.Random(seed)
    ps = [r["prof"] for r in pool]
    tgt = sum(r["prof"] for r in sel)
    return sum(1 for _ in range(n) if sum(rnd.sample(ps, len(sel))) >= tgt)


def kelly(rs, se_k):
    n = len(rs)
    p = sum(r["won"] for r in rs) / n
    se = math.sqrt(p * (1 - p) / n)
    b = sum(r["dec"] for r in rs) / n - 1
    pl = p - se_k * se
    return max(0.0, 25 * (pl * b - (1 - pl)) / b)


# ------------------------------------------------------------ the rigs: the Dog of the Day rows
_OD = defaultdict(set)                         # the OOS rig's own schedule: team -> the days it played
for _r in s1.ROWS:
    _OD[_r["home"]].add(date.fromisoformat(str(_r["date"])[:10]))
    _OD[_r["away"]].add(date.fromisoformat(str(_r["date"])[:10]))


def OOS_N(team, day, nights):
    """games the team played in the `nights` nights before `day` (the OOS rig's schedule)"""
    d0 = date.fromisoformat(day)
    return sum(1 for k in range(1, nights + 1) if d0 - timedelta(days=k) in _OD[team])


def oos(at="morning"):
    bd = s1.cands(at)
    dogs = []
    for day, xs in sorted(bd.items()):
        x, kind = s1.pick(xs)
        for y in xs:
            if y is not x or s1.fighting(y) or y["own"] < y["pm"]:
                continue
            dogs.append(dict(src="OOS", date=str(day)[:10], season=y["r"]["season"], odds=y["am"], dec=y["dec"], won=bool(y["won"]),
                             prof=y["profit"], score=y["score"], rb=bool(y["ob2b"] and not y["b2b"]), team=y["team"], half="held",
                             n6=OOS_N(y["team"], str(day)[:10], 5), n4=OOS_N(y["team"], str(day)[:10], 3)))
    return dogs


def board(name):
    bd, by = BO[name]
    dogs = []
    for d in sorted(bd):
        posted = {id(r) for r, u, k in bd[d] if k == "dog"}
        for r in by.get(d, []):
            if id(r) not in posted or r["league"] != "nhl" or r["result"] not in ("won", "lost") or r.get("dog_score") is None:
                continue
            dogs.append(dict(src=name, date=d, season=L.season(d), odds=r["odds"], dec=r["dec"], won=r["result"] == "won",
                             prof=(r["dec"] - 1) if r["result"] == "won" else -1.0, score=r["dog_score"],
                             rb=bool(r.get("rested_vs_b2b") or (r.get("x") or {}).get("rested_vs_b2b")), team=r["team"], half=L.half(d)))
    return dogs


def r3l():
    dogs = []
    for r in B.P:
        if r["league"] != "nhl" or r["kind"] != "dog":
            continue
        dogs.append(dict(src="R3L", date=r["date"], season=B.season(r["date"]), odds=r["odds"], dec=r["dec"], won=r["result"] == "won",
                         prof=B.flat(r), score=r.get("dog_score") or 0.0, rb=bool((r.get("x") or {}).get("rested_vs_b2b")),
                         team=r["team"], half=B.half(r["date"]), u0=r["u0"]))
    return dogs


RIG = {"OOS": oos(), "R1": board("R1"), "R2": board("R2"), "R3L": r3l()}
for nm in ("R1", "R2"):                       # the b2b flag on the 10/30 boards: the cut as s3_score8 read it = the score alone
    if not any(r["rb"] for r in RIG[nm]):
        for r in RIG[nm]:
            r["rb"] = None


def is_max(r):
    return r["score"] >= 8 and (r["rb"] is None or r["rb"])


def nl(rs):
    return [r for r in rs if r["half"] != "live"]


print("================ (1) THE MAX-PLAY CELL ON EVERY RIG, EVERY SEASON (the Dog of the Day, b2b spot, score 8+; flat 1u)")
for nm, rs in RIG.items():
    rs = nl(rs)
    mx = [r for r in rs if is_max(r)]
    sh = [r for r in rs if not is_max(r) and r["odds"] <= 150]
    lg = [r for r in rs if not is_max(r) and r["odds"] > 150]
    print(f" {nm}: 💎 {st(mx)} | {seasons(mx)}")
    print(f"      train {st([r for r in mx if r['half'] == 'train'])[:44]} | held {st([r for r in mx if r['half'] == 'held'])[:44]}")
    print(f"      the 2u tier (the other Dogs +100..+150) {st(sh)}")
    print(f"      the ½u tier (the other Dogs +151..+350) {st(lg)}")
    print(f"      placebo: 💎 against a random same-size draw of that rig's other short Dogs + itself: {plc(mx, mx + sh)} of 2,000")

print("\n================ (2) 3u vs 2u - DOES THE 8+ CELL WIN MORE THAN THE 2u DOG, POOLED")
O = nl(RIG["OOS"])
for nm in ("R1", "R2", "R3L"):
    rs = O + nl(RIG[nm])
    mx = [r for r in rs if is_max(r)]
    sh = [r for r in rs if not is_max(r) and r["odds"] <= 150]
    print(f" OOS + {nm}: 💎 {st(mx)} | the 2u Dogs {st(sh)} | placebo inside the short Dogs {plc([r for r in mx if r['odds'] <= 150], [r for r in mx if r['odds'] <= 150] + sh)} of 2,000")
    print(f"      the SIZE - a quarter of Kelly at 1 / 1.5 / 2 standard errors under the win rate: {kelly(mx, 1):.1f}u / {kelly(mx, 1.5):.1f}u / {kelly(mx, 2):.1f}u")
    for u in (2.0, 3.0):
        per = defaultdict(float)
        for r in mx:
            per[r["date"]] += u * r["prof"]
        cum = peak = dd = 0.0
        for d in sorted(per):
            cum += per[d]
            peak = max(peak, cum)
            dd = min(dd, cum - peak)
        print(f"      the 💎 at {u:g}u: {sum(per.values()):+6.1f}u on {u * len(mx):5.0f}u, worst stretch {dd:+.1f}u")
print("  the board rigs ALONE (no OOS), the same question - 3 looks at the same 2023-26 seasons:")
for nm in ("R1", "R2", "R3L"):
    rs = nl(RIG[nm])
    mx = [r for r in rs if is_max(r)]
    print(f"   {nm}: 💎 {st(mx)} | Kelly/4 at 1 / 1.5 / 2 se: {kelly(mx, 1):.1f}u / {kelly(mx, 1.5):.1f}u / {kelly(mx, 2):.1f}u")
print("  OOS alone (2020-23, the only seasons the cut never saw):")
mx = [r for r in O if is_max(r)]
print(f"   💎 {st(mx)} | Kelly/4 at 1 / 1.5 / 2 se: {kelly(mx, 1):.1f}u / {kelly(mx, 1.5):.1f}u / {kelly(mx, 2):.1f}u")

print("\n================ (3) LIVE (picks.json) - the hockey Dog of the Day in the max-play shape")
pk = json.load(open(os.path.join(ROOT, "data/sports/picks.json")))
lv = []
for q in pk:
    lg_ = (q.get("legs") or [{}])[0]
    if lg_.get("league") == "nhl" and q.get("kind") == "dog" and lg_.get("dog_score") is not None and q.get("status") in ("won", "lost"):
        lv.append(dict(date=q["date"], team=lg_.get("team"), odds=q["american"], dec=q["dec"], won=q["status"] == "won",
                       prof=(q["dec"] - 1) if q["status"] == "won" else -1.0, score=lg_["dog_score"], rb=bool(lg_.get("rested_vs_b2b")),
                       season="live", half="live"))
lm = [r for r in lv if r["rb"] and r["score"] >= 8]
print(f"  live shape {st(lm)}: " + ", ".join(f"{r['team']} {r['odds']:+d} {'W' if r['won'] else 'L'}" for r in lm))
allm = [r for r in O + nl(RIG["R3L"]) if is_max(r)] + lm
print(f"  OOS + R3L + live: {st(allm)} | Kelly/4 at 1 / 1.5 / 2 se: {kelly(allm, 1):.1f}u / {kelly(allm, 1.5):.1f}u / {kelly(allm, 2):.1f}u")
print("  THE QUIT RULE (25 graded under 44%) - what the tier's own judge needs: at 2-2 the shape is on pace; 11+ of 25.")

# ------------------------------------------------------------ the dog's own load
RAW = [r for r in mp.build("nhl")]
KEY = {}
for r in RAW:
    KEY[(r["date"], r["team"])] = r


def raw_of(r):
    """the raw rig's row for a rig row (the same team, the same local day or a day either side)"""
    d0 = date.fromisoformat(r["date"][:10])
    for k in (0, -1, 1):
        x = KEY.get((str(d0 + timedelta(days=k)), r["team"]))
        if x:
            return x
    t = r["team"].split()[-1]
    for k in (0, -1, 1):
        for (d, tm), x in KEY.items():
            if d == str(d0 + timedelta(days=k)) and tm.endswith(t):
                return x
    return None


print("\n================ (4) THE DOG'S OWN LOAD - RAW, every rested dog +100..+350 against a favorite that played last night, the close, 2018-26")
SP = [r for r in RAW if 100 <= r["odds"] <= 350 and r["o_b2b"] and not r["b2b"]]
ALLD = [r for r in RAW if 100 <= r["odds"] <= 350]
mp.cell("every hockey dog +100..+350", ALLD, "nhl")
mp.cell("THE SPOT: rested dog, the favorite on a b2b", SP, "nhl")
for nm, f in (("the dog's 1st game in 4+ nights (rest 4+)", lambda r: r["rest"] >= 4),
              ("the dog's 2nd game in 3 nights (rest 2, n4 = 1)", lambda r: r["rest"] == 2 and r["n4"] == 1),
              ("the dog's 3rd game in 4 nights (n4 = 2)", lambda r: r["n4"] >= 2),
              ("the dog's 3rd game in 6 nights or fewer (n6 <= 2)", lambda r: r["n6"] <= 2),
              ("the dog's 4th game in 6 nights (n6 = 3+) - the Ducks", lambda r: r["n6"] >= 3),
              ("n6 <= 1 (fresh: at most one game in the five nights before)", lambda r: r["n6"] <= 1),
              ("n6 = 2", lambda r: r["n6"] == 2),
              ("the dog rest 2 exactly", lambda r: r["rest"] == 2), ("the dog rest 3+", lambda r: r["rest"] >= 3)):
    x = [r for r in SP if f(r)]
    c = mp.cell("  spot + " + nm, x, "nhl")
    print(f"        placebo inside the spot: {plc(x, SP)} of 2,000 as good | as BAD or worse: {2000 - plc(x, SP)}")
print("  the same load with NO b2b spot (does the 4th-in-6 dog lose anywhere?)")
mp.cell("  no spot, the dog's 4th game in 6 nights (n6 3+, not on a b2b)", [r for r in ALLD if not r["o_b2b"] and not r["b2b"] and r["n6"] >= 3], "nhl")
mp.cell("  no spot, n6 <= 2, not on a b2b", [r for r in ALLD if not r["o_b2b"] and not r["b2b"] and r["n6"] <= 2], "nhl")
print("  the spot by season, n6 3+ vs under:")
for s in sorted({r["season"] for r in SP}):
    a = [r for r in SP if r["season"] == s and r["n6"] >= 3]
    b = [r for r in SP if r["season"] == s and r["n6"] < 3]
    print(f"    {s}: 4th-in-6 {st(a)[:46]} | fresher {st(b)[:46]}")

print("\n================ (5) THE DOG'S OWN LOAD INSIDE THE MAX-PLAY CELL (each rig's 8+ Dogs joined to the raw schedule)")
for nm in ("OOS", "R1", "R2", "R3L"):
    mx = [r for r in nl(RIG[nm]) if is_max(r)]
    j = [(r, r if "n6" in r else raw_of(r)) for r in mx]
    miss = sum(1 for _, x in j if not x)
    hv = [r for r, x in j if x and x["n6"] >= 3]
    lt = [r for r, x in j if x and x["n6"] < 3]
    t3 = [r for r, x in j if x and x["n4"] >= 2]
    print(f" {nm}: joined {len(mx) - miss}/{len(mx)} | the dog's 4th game in 6 nights {st(hv)} | fresher {st(lt)} | 3rd in 4 nights {st(t3)[:44]}")
pool = [r for nm in ("OOS", "R3L") for r in nl(RIG[nm]) if is_max(r)]
j = [(r, r if "n6" in r else raw_of(r)) for r in pool]
hv = [r for r, x in j if x and x["n6"] >= 3]
lt = [r for r, x in j if x and x["n6"] < 3]
print(f" OOS + R3L: 4th in 6 {st(hv)} | fresher {st(lt)} | placebo (the heavy ones as bad as a random draw of the cell): {2000 - plc(hv, hv + lt)} of 2,000 as bad or worse")
print(f"   fresher only: Kelly/4 at 1 / 1.5 / 2 se: {kelly(lt, 1):.1f}u / {kelly(lt, 1.5):.1f}u / {kelly(lt, 2):.1f}u" if lt else "")
print("\ncells printed on the raw rig:", len(mp.TRIED))

print("\n================ (6) THE WHOLE BOARD (R3L, today's code and sizes, 2023-26) with the 💎 at 3u / 2u / the Dog's own size")
for nm, f in (("the 💎 at 3u (today)", lambda r: r["u0"]), ("the 💎 at 2u any price (WIRED 11/25)", lambda r: 2.0 if r["u0"] >= 3 else r["u0"]),
              ("the 💎 off (the Dog's own size: 2u short, ½u long)", lambda r: (2.0 if r["odds"] <= 150 else 0.5) if r["u0"] >= 3 else r["u0"])):
    per, t = defaultdict(float), defaultdict(lambda: [0.0, 0.0])
    for r in B.P:
        h = B.half(r["date"])
        if h == "live":
            continue
        u = f(r)
        per[r["date"]] += u * B.flat(r)
        t[h][0] += u * B.flat(r)
        t[h][1] += u
    net, risk = t["train"][0] + t["held"][0], t["train"][1] + t["held"][1]
    print(f"  {nm:52s} {net / 3.03:+6.1f}u a year ({net:+6.1f}u on {risk:6.0f}u, {100 * net / risk:+5.1f}%) | train {t['train'][0]:+6.1f}u | held {t['held'][0]:+6.1f}u"
          f" | worst stretch {B.worst(per):+.1f}u")
