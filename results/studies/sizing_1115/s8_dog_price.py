"""11/15 - THE DOG OF THE DAY'S PRICE BAND (2u at +100..+150, ½u at +151..+350 - the 10/30 sizing) ON EVERY RIG, the
seasons the rule was chosen on AND the seasons it never saw:
  R1 / R2   the two replay boards, 2023-26 (the 10/30 sizing was CHOSEN on R1's rows - "short +22% both halves, long -15%")
  NHL-OOS   the 11/2 NHL odds-history rig, 2020-23, the live hockey Dog one a day at the MORNING price (nhl_odds_1102) -
            three seasons no rule or weight ever saw
  FB        the 11/14 football replay board on today's code, 2018-26 (football_1114) - 2018-22 never in the 10/30 sizing
Each: the Dog short vs long, flat 1u vs its price, by season; then WHAT EACH SIZE RULE MAKES on that rig's Dogs (units
won / risked, ROI on the units, the worst stretch), and all rigs' Dogs together (R1 for 2023-26 hockey + football; the
OOS rigs for the seasons before - no game counted twice).
Usage: python results/studies/sizing_1115/s8_dog_price.py > results/studies/sizing_1115/s8_dog_price.out"""
import contextlib
import importlib.util
import io
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUD, "sizing_1114"))
import lib as L  # noqa: E402

RULES = [("2u short / ½u long (TODAY)", lambda o: 2.0 if o <= 150 else 0.5),
         ("flat 1u", lambda o: 1.0),
         ("flat 2u", lambda o: 2.0),
         ("2u short / 1u long", lambda o: 2.0 if o <= 150 else 1.0),
         ("1u short / ½u long", lambda o: 1.0 if o <= 150 else 0.5),
         ("1u short / 2u long (the reverse)", lambda o: 1.0 if o <= 150 else 2.0),
         ("flat ½u", lambda o: 0.5)]


def stat(bets):
    """bets = [(date, season, odds, dec, won)]"""
    n = len(bets)
    if not n:
        return "n   0"
    w = sum(b[4] for b in bets)
    fl = sum((b[3] - 1) if b[4] else -1 for b in bets)
    exp = sum(1 / b[3] for b in bets)
    var = sum((1 / b[3]) * (1 - 1 / b[3]) for b in bets)
    seas = defaultdict(lambda: [0, 0.0])
    for b in bets:
        seas[b[1]][0] += 1
        seas[b[1]][1] += (b[3] - 1) if b[4] else -1
    up = sum(v[1] > 0 for v in seas.values())
    return (f"n {n:3d} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% z {(w - exp) / math.sqrt(var):+5.2f} | up {up}/{len(seas)} | "
            + " ".join(f"{s}:{v[0]}/{100 * v[1] / v[0]:+.0f}%" for s, v in sorted(seas.items())))


def worst(bets, fn):
    per = defaultdict(float)
    for b in bets:
        per[b[0]] += fn(b[2]) * ((b[3] - 1) if b[4] else -1)
    cum = peak = w = 0.0
    for d in sorted(per):
        cum += per[d]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def rules(bets, indent="   "):
    for nm, fn in RULES:
        net = sum(fn(b[2]) * ((b[3] - 1) if b[4] else -1) for b in bets)
        risk = sum(fn(b[2]) for b in bets)
        print(f"{indent}{nm:34s} {net:+7.1f}u on {risk:6.1f}u ({100 * net / risk:+5.1f}%) worst stretch {worst(bets, fn):+6.1f}u"
              f" | a unit risked earns {net / risk:+.3f}")


def band(name, bets):
    print(f"  {name}")
    print(f"     short +100..+150   {stat([b for b in bets if b[2] <= 150])}")
    print(f"     long  +151..+350   {stat([b for b in bets if b[2] > 150])}")
    for lo, hi in ((100, 119), (120, 150), (151, 199), (200, 350)):
        print(f"        +{lo}..+{hi}        {stat([b for b in bets if lo <= b[2] <= hi])}")


ALL = {}
# ---------------------------------------------------------------- R1 / R2
for name, (board, _by) in L.boards().items():
    print("=" * 30, f"BOARD {name} (2023-26): the Dog of the Day, hockey / football (the NBA Dog sizes on its own rule)")
    dogs = [(d, L.season(d), r["odds"], r["dec"], r["result"] == "won", r["league"], L.half(d))
            for d in sorted(board) for r, u, k in board[d] if k == "dog" and r["league"] != "nba" and r["result"] in ("won", "lost")
            and L.half(d) != "live"]
    for lg in ("nhl", "nfl", "ncaaf", None):
        x = [b for b in dogs if lg is None or b[5] == lg]
        if x:
            band(f"{lg or 'every league'} ({len(x)})", x)
            for h in ("train", "held"):
                y = [b for b in x if b[6] == h]
                print(f"       {h}: short {stat([b for b in y if b[2] <= 150])[:44]} | long {stat([b for b in y if b[2] > 150])[:44]}")
    print("  what each size rule makes on these Dogs:")
    rules(dogs)
    ALL[name] = dogs

# ---------------------------------------------------------------- NHL out of sample
NH = os.path.join(STUD, "nhl_odds_1102")
sys.path.insert(0, NH)
_mine = sys.modules.pop("lib")                       # (that study imports ITS lib.py by the same name)
with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)
sys.modules.pop("lib", None)
sys.modules["lib"] = _mine
sys.path.remove(NH)
print("=" * 30, "NHL OUT OF SAMPLE (2020-21 .. 2022-23, the live hockey Dog one a day, the MORNING price)")
bd = s1.cands("morning")
nhl = []
for day, xs in sorted(bd.items()):
    x, kind = s1.pick(xs)
    if x:
        nhl.append((day, x["r"]["season"], x["am"], x["dec"], bool(x["won"]), "nhl", kind))
band(f"the hockey Dog ({len(nhl)})", nhl)
band("   gated only (6+)", [b for b in nhl if b[6] == "gated"])
print("  what each size rule makes on these Dogs:")
rules(nhl)
ALL["NHL-OOS"] = nhl

# ---------------------------------------------------------------- football 2018-26
import glob  # noqa: E402
import json  # noqa: E402
fbd, seen = [], set()
for fp in sorted(glob.glob(os.path.expanduser("~/.cache/d503_fb1114/rows/f*.jsonl"))):   # (flib.replay's own reading rule)
    for ln in open(fp):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r["league"] not in ("nfl", "ncaaf") or r["market"] != "ml" or r.get("result") not in ("won", "lost") or r.get("kind") != "dog":
            continue
        k = (r["date"], r["gid"], r["side"], r["market"])
        if k in seen:
            continue
        seen.add(k)
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        sea = y if m >= 7 else y - 1
        fbd.append((r["date"], str(sea), r["odds"], r["dec"], r["result"] == "won", r["league"], "train" if sea <= 2022 else "held"))
if fbd:
    print("=" * 30, "FOOTBALL REPLAY BOARD on today's code (2018-26; the 10/30 sizing never saw 2018-22)")
    for lg in ("nfl", "ncaaf", None):
        x = [b for b in fbd if lg is None or b[5] == lg]
        band(f"{lg or 'football'} Dog of the Day ({len(x)})", x)
        for lo, hi, nm in ((2018, 2022, "2018-22 (never in the sizing study)"), (2023, 2026, "2023-26")):
            y = [b for b in x if lo <= int(b[1]) <= hi]
            print(f"       {nm}: short {stat([b for b in y if b[2] <= 150])[:44]} | long {stat([b for b in y if b[2] > 150])[:44]}")
    print("  what each size rule makes on these Dogs:")
    rules(fbd)
    ALL["FB"] = fbd
else:
    print("football rig rows not on this machine (~/.cache/d503_fb1114/rows)")

# ---------------------------------------------------------------- everything, no game twice
print("=" * 30, "EVERY DOG OF THE DAY ON FILE, NO GAME TWICE")
pool_oos = list(ALL.get("NHL-OOS", [])) + [b for b in ALL.get("FB", []) if int(b[1]) <= 2022]
pool_in = [b for b in ALL["R1"] if b[5] == "nhl"] + [b for b in ALL.get("FB", []) if int(b[1]) >= 2023]
print("  (a) THE SEASONS THE 10/30 SIZING NEVER SAW: hockey 2020-23 + football 2018-22")
band(f"Dogs ({len(pool_oos)})", pool_oos)
rules(pool_oos)
print("  (b) THE SEASONS IT WAS CHOSEN ON: hockey 2023-26 (R1) + football 2023-26")
band(f"Dogs ({len(pool_in)})", pool_in)
rules(pool_in)
print("  (c) ALL OF IT")
band(f"Dogs ({len(pool_oos) + len(pool_in)})", pool_oos + pool_in)
rules(pool_oos + pool_in)
both = pool_oos + pool_in
for lg in ("nhl", "nfl", "ncaaf"):
    x = [b for b in both if b[5] == lg]
    print(f"  {lg} only, all seasons:")
    band(f"{lg} Dogs ({len(x)})", x)
    rules(x, "      ")
    for nm, pool in (("never-saw", [b for b in pool_oos if b[5] == lg]), ("chosen-on", [b for b in pool_in if b[5] == lg])):
        print(f"      {nm}: short {stat([b for b in pool if b[2] <= 150])[:44]} | long {stat([b for b in pool if b[2] > 150])[:44]}")
print("  (c) by league: " + " | ".join(
    f"{lg} short {stat([b for b in both if b[5] == lg and b[2] <= 150])[:40]} long {stat([b for b in both if b[5] == lg and b[2] > 150])[:40]}"
    for lg in ("nhl", "nfl", "ncaaf")))
# a placebo for the split: how often does a random relabel of the same Dogs give the short side as big a lead?
import random  # noqa: E402
rnd = random.Random(1115)
fl = lambda b: (b[3] - 1) if b[4] else -1.0   # noqa: E731
for nm, pool in (("never-saw seasons", pool_oos), ("chosen-on seasons", pool_in), ("all", both)):
    s = [fl(b) for b in pool if b[2] <= 150]
    lg_ = [fl(b) for b in pool if b[2] > 150]
    if not s or not lg_:
        continue
    lead = sum(s) / len(s) - sum(lg_) / len(lg_)
    vals = [fl(b) for b in pool]
    hit = 0
    for _ in range(2000):
        rnd.shuffle(vals)
        a, c = vals[:len(s)], vals[len(s):]
        hit += (sum(a) / len(a) - sum(c) / len(c)) >= lead
    print(f"  {nm}: short minus long = {100 * lead:+.1f} points of ROI; a random split of the same Dogs gave short that lead or more {hit} of 2,000")
