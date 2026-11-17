"""11/17 FULL SWEEP - S10 THE FOOTBALL LOCK (live since 10/25: 1-2, the ⭐ on it 1-1; the Packers -142 ⭐ 1u lost 11/15).
The 11/14 football replay board's rows (today's code, 2018-26, the close; ~/.cache/d503_fb1114 - the same rows the 11/16
thin-Lock call was checked on): every Lock-grade moneyline FAVORITE row (make_board's Lock before the thin rule; the 9
plus-money rows the 11/16 favorites-only rule bars are left out). As it posts from 11/16: thin = the Lock at ½u, the NFL
½u thin or not, a not-thin college football Lock 1u. Cells named before looking: home / road, the price band, the
month, the league, the own read's margin; a college thin Lock carrying the ⭐ at 1u (the 11/16 note left it to the owner).
Train = seasons 2018-22 (to 2023-06), held out = 2023-26.
Usage: python results/studies/sweep_1117/s4_football_lock.py > results/studies/sweep_1117/s4_football_lock.out"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import slib  # noqa: E402
import sports  # noqa: E402

rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_fb1114/rows/f*.jsonl"))):
    for line in open(f):
        r = json.loads(line)
        k = (r["gid"], r["side"], r["market"])
        if k not in seen:
            seen.add(k)
            rows.append(r)
half = lambda d: "held" if d >= "2023-07-01" else "train"  # noqa: E731


def leg(r):
    return {**r, "start": r.get("start") or (r["date"] + "T20:00Z"), "game_id": r["gid"]}


def thin(r):
    try:
        return bool(sports.thin_lock({"legs": [leg(r)]}))
    except Exception:  # noqa: BLE001
        return False


def units(r):
    if thin(r) or r["league"] == "nfl":
        return 0.5
    return 1.0


L_ = [(r["date"], r, units(r)) for r in rows if r.get("kind") == "lock" and r["market"] == "ml" and r["odds"] < 100
      and r["result"] in ("won", "lost")]
print(f"football Lock-grade favorite rows 2018-26: {len(L_)} (NFL {sum(r['league'] == 'nfl' for _, r, _ in L_)}, "
      f"college {sum(r['league'] == 'ncaaf' for _, r, _ in L_)}; thin {sum(thin(r) for _, r, _ in L_)})")
slib.five("EVERY football Lock as it posts from 11/16", L_, None, half)
net = sum(slib.flat(r) * u for _, r, u in L_)
print(f"   at today's sizes: {net:+.1f}u on {sum(u for _, _, u in L_):.1f}u, worst stretch {slib.worst(L_, units=True):+.1f}u")
om = lambda r: (r.get("edge_own") or 0)  # noqa: E731
clear = []
for nm, f in (("NFL", lambda r: r["league"] == "nfl"), ("college football", lambda r: r["league"] == "ncaaf"),
              ("home", lambda r: r["home"] and not r.get("neutral")), ("road", lambda r: not r["home"] and not r.get("neutral")),
              ("NFL home", lambda r: r["league"] == "nfl" and r["home"]), ("NFL road", lambda r: r["league"] == "nfl" and not r["home"]),
              ("college home", lambda r: r["league"] == "ncaaf" and r["home"]), ("college road", lambda r: r["league"] == "ncaaf" and not r["home"]),
              ("-150..-135", lambda r: r["odds"] <= -135), ("-134..-120", lambda r: r["odds"] > -135),
              ("thin (own read under 3c over)", thin), ("not thin", lambda r: not thin(r)),
              ("own read 5c+ over the price", lambda r: om(r) >= .05), ("September-October", lambda r: r["date"][5:7] in ("08", "09", "10")),
              ("November on", lambda r: r["date"][5:7] in ("11", "12", "01", "02")),
              ("college thin Lock (½u; the ⭐ would make it 1u)", lambda r: r["league"] == "ncaaf" and thin(r)),
              ("college NOT-thin Lock (1u)", lambda r: r["league"] == "ncaaf" and not thin(r)),
              ("NFL thin Lock (½u)", lambda r: r["league"] == "nfl" and thin(r)), ("NFL not-thin Lock (½u)", lambda r: r["league"] == "nfl" and not thin(r))):
    c = [x for x in L_ if f(x[1])]
    if len(c) < 10:
        print(f"  {nm:58s} n {len(c)} - too few")
        continue
    a = slib.five(nm, c, L_, half)
    b = slib.loses("   ...as a CUT", c, L_, half)
    if a["clears"] or b["clears"]:
        clear.append((nm, "size-up" if a["clears"] else "cut"))
ct = [(d, r, u) for d, r, u in L_ if r["league"] == "ncaaf" and thin(r)]
print(f"the college thin Lock: at ½u {sum(slib.flat(r) * .5 for _, r, _ in ct):+.1f}u (worst {0.5 * slib.worst(ct):+.1f}u); with the ⭐'s 1u on "
      f"every one {sum(slib.flat(r) for _, r, _ in ct):+.1f}u (worst {slib.worst(ct):+.1f}u) - train "
      f"{sum(slib.flat(r) for d, r, _ in ct if half(d) == 'train'):+.1f}u / held {sum(slib.flat(r) for d, r, _ in ct if half(d) == 'held'):+.1f}u")
print("cells that clear:", clear or "NONE")
print("-- THE COLLEGE THIN LOCK: 1u instead of ½u? (the size the not-thin college Lock already carries)")
th = [x for x in L_ if thin(x[1])]
slib.five("college thin vs every THIN football Lock (its own kind)", ct, th, half)
slib.five("college thin vs every COLLEGE football Lock", ct, [x for x in L_ if x[1]["league"] == "ncaaf"], half)
import math  # noqa: E402
w, n = sum(r["result"] == "won" for _, r, _ in ct), len(ct)
avg = sum(r["dec"] for _, r, _ in ct) / n
for z, nm in ((1.0, "one standard error"), (1.645, "the 5% end")):
    p_ = w / n
    d_ = 1 + z * z / n
    lo = (p_ + z * z / (2 * n) - z * math.sqrt(p_ * (1 - p_) / n + z * z / (4 * n * n))) / d_
    k = max(0.0, (lo * (avg - 1) - (1 - lo)) / (avg - 1)) / 4 * 100
    print(f"   a quarter of Kelly on the low end of its win rate ({nm}: {100 * lo:.1f}% at an average {avg:.2f}): {k:.1f}u")
for nm, f in (("BEFORE (11/16): thin ½u, the NFL ½u, a not-thin college Lock 1u", units),
              ("AFTER: the college thin Lock 1u too (every college Lock 1u, the NFL ½u)", lambda r: 0.5 if r["league"] == "nfl" else 1.0),
              ("not wired: every thin football Lock 1u (the NFL's too)", lambda r: 1.0 if thin(r) or r["league"] == "ncaaf" else 0.5),
              ("not wired: the not-thin college Lock ½u", lambda r: 0.5)):
    rs = [(d, r, f(r)) for d, r, _ in L_]
    tr = sum(slib.flat(r) * u for d, r, u in rs if half(d) == "train")
    he = sum(slib.flat(r) * u for d, r, u in rs if half(d) == "held")
    seas = {}
    for d, r, u in rs:
        seas[slib.season(d)] = seas.get(slib.season(d), 0.0) + slib.flat(r) * u
    print(f"   {nm:72s} {tr + he:+5.1f}u on {sum(u for _, _, u in rs):5.1f}u ({100 * (tr + he) / sum(u for _, _, u in rs):+.1f}%) | train {tr:+.1f}u / held {he:+.1f}u | "
          f"worst stretch {slib.worst(rs, units=True):+.1f}u | seasons up {sum(v > 0 for v in seas.values())}/{len(seas)}")
print("   the college thin Lock by season (W-L): " + "  ".join(
    f"{s} {sum(1 for d, r, _ in ct if slib.season(d) == s and r['result'] == 'won')}-{sum(1 for d, r, _ in ct if slib.season(d) == s and r['result'] == 'lost')}"
    for s in sorted({slib.season(d) for d, _, _ in ct})))
