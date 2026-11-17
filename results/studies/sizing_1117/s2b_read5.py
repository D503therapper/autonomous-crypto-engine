"""11/17 - SIZING: the dog slot's read-5 band, the hard checks. (1) the values the read takes on the rows and whether the
rows carry the 11/14 home-dog -1 (live they do); (2) the slot re-built with that -1 applied (a true-home dog whose
efficiency read is not 15+ over the no-vig reads 1 less); (3) is the read-5 band the 6+ band's twin or the 4 band's?
- a random same-size draw from the read-4 plays doing as well, and from the 6+ plays doing as badly.
Usage: python results/studies/sizing_1117/s2b_read5.py > results/studies/sizing_1117/s2b_read5.out"""
import os
import random
import sys
from collections import Counter, defaultdict

sys.argv = sys.argv[:1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io  # noqa: E402
import contextlib  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import s2_cbb_slot as S2  # noqa: E402

R, A, DOG, line, sched = S2.R, S2.A, S2.DOG, S2.line, S2.sched
print("the read's values on the read-4+ dogs:", sorted(Counter(round(r["dog_read"], 2) for r in A).items()))
print("rows whose read parts carry a 'home' term:", sum(1 for r in A if (r.get("dog_read_parts") or {}).get("home")), "of", len(A))
print("a sample of parts:", [r.get("dog_read_parts") for r in A[:3]])


def live_read(r):
    """the read as LIVE since 11/14: a true-home dog whose efficiency read is NOT 15+ over the no-vig price reads 1 less."""
    x = r["dog_read"]
    if r.get("where") == "home" and not (r.get("dog_read_parts") or {}).get("home"):
        if not ((r.get("effgap") or 0) >= 0.15):
            x -= 1
    return x


def slot(cap=2):
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in DOG:
        if r.get("dog_read") is None or r["mn"] < 4:
            continue
        lr = live_read(r)
        if lr < 4 or r["gid"] in lockg or r["kind"] in ("stackplay", "floor"):
            continue
        if min(0.95, r["p_market"] + lr / 100) * r["dec"] - 1 <= 0:
            continue
        pool[r["date"]].append(dict(r, lr=lr))
    out = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["lr"], -(r.get("effgap") or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= cap:
                    out.append(r)
    return sorted(out, key=lambda r: (r["date"], r["gid"]))


S = slot()
print(f"\nTHE SLOT WITH THE 11/14 HOME-DOG -1 IN (as live today): {len(S)} plays, {len(S) / 8:.0f} a season")
line("the slot, every play", S, DOG)
for lo, hi in ((4, 5), (5, 6), (6, 99), (5, 99)):
    line(f"read {lo}-{hi if hi < 99 else ''}", [r for r in S if lo <= r["lr"] < hi], S)
sched("TODAY: 1u, 2u at 6+", S, lambda r: 2.0 if r["lr"] >= 6 else 1.0)
sched("1u at 4, 2u at 5+", S, lambda r: 2.0 if r["lr"] >= 5 else 1.0)
sched("flat 2u", S, lambda r: 2.0)
sched("1u at 4, 2u at 5, 3u at 6+", S, lambda r: 3.0 if r["lr"] >= 6 else 2.0 if r["lr"] >= 5 else 1.0)
sched("1u, 3u at 6+", S, lambda r: 3.0 if r["lr"] >= 6 else 1.0)

print("\nIS THE READ-5 BAND THE 6+ BAND'S TWIN OR THE 4 BAND'S? (2,000 draws)")
for nm, SS, key in (("the slot as the rows have it", S2.S, "dog_read"), ("the slot with the home-dog -1", S, "lr")):
    b4 = [r["pnl"] for r in SS if r[key] < 5]
    b5 = [r["pnl"] for r in SS if 5 <= r[key] < 6]
    b6 = [r["pnl"] for r in SS if r[key] >= 6]
    rnd = random.Random(1117)
    t = sum(b5)
    hi = sum(1 for _ in range(2000) if sum(rnd.sample(b4, len(b5))) >= t)
    lo = sum(1 for _ in range(2000) if sum(rnd.sample(b6, len(b5))) <= t) if len(b6) > len(b5) else None
    print(f"  {nm}: read 5 = {len(b5)} plays {100 * t / len(b5):+.1f}%; a random {len(b5)} of the read-4 plays did as well {hi} of 2,000; "
          f"a random {len(b5)} of the 6+ plays did as badly {lo} of 2,000")
    for half, f in (("train", lambda r: r["season"] <= 2022), ("held", lambda r: r["season"] >= 2023)):
        x4 = [r["pnl"] for r in SS if r[key] < 5 and f(r)]
        x5 = [r["pnl"] for r in SS if 5 <= r[key] < 6 and f(r)]
        rnd = random.Random(7)
        hi = sum(1 for _ in range(2000) if sum(rnd.sample(x4, len(x5))) >= sum(x5))
        print(f"     {half}: read 5 {len(x5)} plays {100 * sum(x5) / len(x5):+.1f}% vs read 4 {len(x4)} plays {100 * sum(x4) / len(x4):+.1f}%; placebo {hi} of 2,000")
print("\nTHE READ-5 PLAYS, ONE LINE EACH (the slot with the home-dog -1)")
for r in S:
    if 5 <= r["lr"] < 6:
        print(f"  {r['date']} {r['team'][:22]:22s} {r['odds']:+4d} {'W' if r['win'] else 'L'} {r['where']:7s} parts {r.get('dog_read_parts')}")

print("\nTHE UMBC QUESTION (11/16: UMBC +120 at home, ½u, won 75-67 - the owner: 'that was a lock, we should have had 3 units'):")
print("  what it was: NOT the dog slot - its dog read was 3.0 (weights 2 + knowledge 2 - 1 the 11/14 home-dog rule; the slot's gate is 4),")
print("  its own read 44.9% against the 45.5% the price needs, the efficiency read 46.3%; it went up as the day's FLOOR FALLBACK (the one")
print("  ½u play on a board that had no unit play). Every college hoops dog in that shape on the rows (both teams 4+ games):")
U = [r for r in DOG if r.get("dog_read") is not None and r["mn"] >= 4]
for nm, f in (("dog read 3 (the rows' read; 4 before the home-dog -1)", lambda r: 3 <= live_read(r) < 4),
              ("dog read 3, at home, +100..+150", lambda r: 3 <= live_read(r) < 4 and r.get("where") == "home" and r["odds"] <= 150),
              ("dog read 3, +100..+150", lambda r: 3 <= live_read(r) < 4 and r["odds"] <= 150),
              ("dog read 2-4, at home, +100..+150, the own read under the price", lambda r: 2 <= live_read(r) < 4 and r.get("where") == "home" and r["odds"] <= 150 and (r.get("edge_own") or 0) < 0),
              ("dog read 2", lambda r: 2 <= live_read(r) < 3), ("dog read 0-2", lambda r: 0 <= live_read(r) < 2),
              ("dog read under 0", lambda r: live_read(r) < 0)):
    line(nm, [r for r in U if f(r)], U)
