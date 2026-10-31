"""10/31 college sweep: every college moneyline candidate in the 10/30 funnel rows (today's board code, closing prices,
params re-tuned each July, no injuries) split by the gates that keep dogs / slight favorites off. Train = 2023-10..2025-06,
held out = 2025-07..2026-10. Flat 1u at the close."""
import json, math, sys
D = (sys.argv[1] if len(sys.argv) > 1 else "funnel_rows") + "/"   # the fA..fD / fLive jsonl rows of results/studies/thin_1029/funnel_replay.py (10/30 run)
rows = []
seen = set()
for f in ["fA.jsonl", "fB.jsonl", "fC.jsonl", "fD.jsonl", "fLive.jsonl"]:
    for l in open(D + f):
        r = json.loads(l)
        if r.get("league") != "ncaaf" or r.get("result") not in ("won", "lost"):
            continue
        k = (r["date"], r["team"], r["opp"], r.get("odds"))
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
print("college ml rows graded:", len(rows))


def season(r):
    y, m = int(r["date"][:4]), int(r["date"][5:7])
    return y if m >= 7 else y - 1


def pl(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0


def cell(name, sel):
    out = []
    for half, f in (("train", lambda r: r["date"] < "2025-07-01"), ("held", lambda r: r["date"] >= "2025-07-01")):
        xs = [r for r in rows if sel(r) and f(r)]
        n = len(xs)
        if not n:
            out.append(f"{half} 0")
            continue
        w = sum(r["result"] == "won" for r in xs)
        roi = sum(pl(r) for r in xs) / n
        # z vs the price-implied (vigged) chance
        exp = sum(1 / r["dec"] for r in xs)
        var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in xs)
        z = (w - exp) / math.sqrt(var) if var else 0
        out.append(f"{half} {w}-{n - w} {roi:+.1%} z{z:+.1f}")
    by = {}
    for r in rows:
        if sel(r):
            by.setdefault(season(r), []).append(pl(r))
    ss = " ".join(f"{s}:{sum(v) / len(v):+.0%}/{len(v)}" for s, v in sorted(by.items()))
    print(f"{name:62} {' | '.join(out)} || {ss}")


dog = lambda r: 100 <= r["odds"] <= 350
fav = lambda r: -150 <= r["odds"] <= -101
print("\n== DOGS +100..+350 ==")
cell("every dog", dog)
cell("dog +100..+150", lambda r: dog(r) and r["odds"] <= 150)
cell("dog +151..+350", lambda r: dog(r) and r["odds"] > 150)
cell("dog gate PASS", lambda r: dog(r) and r.get("dog_gate"))
cell("dog gate FAIL", lambda r: dog(r) and r.get("dog_gate") is False)
cell("named reason 0 (n_reasons==0)", lambda r: dog(r) and not r.get("n_reasons"))
cell("named reason 1+", lambda r: dog(r) and r.get("n_reasons"))
cell("score 4+ & no named reason", lambda r: dog(r) and (r.get("dog_score") or -99) >= 4 and not r.get("n_reasons"))
cell("score 4+ & named reason", lambda r: dog(r) and (r.get("dog_score") or -99) >= 4 and r.get("n_reasons"))
for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 99)):
    cell(f"dog score {lo}..{hi}", lambda r, lo=lo, hi=hi: dog(r) and r.get("dog_score") is not None and lo <= r["dog_score"] < hi)
cell("score 4+ +100..+150", lambda r: dog(r) and r["odds"] <= 150 and (r.get("dog_score") or -99) >= 4)
cell("score 4+ +151..+350", lambda r: dog(r) and r["odds"] > 150 and (r.get("dog_score") or -99) >= 4)
cell("score 6+ +100..+150", lambda r: dog(r) and r["odds"] <= 150 and (r.get("dog_score") or -99) >= 6)
cell("dog_own_ok", lambda r: dog(r) and r.get("dog_own_ok"))
cell("beats_price", lambda r: dog(r) and r.get("beats_price"))
cell("good()", lambda r: dog(r) and r.get("good"))
cell("gate FAIL but score 4+ (named reason missing)", lambda r: dog(r) and not r.get("dog_gate") and (r.get("dog_score") or -99) >= 4)
cell("home dog", lambda r: dog(r) and r.get("home"))
cell("home dog +100..+150", lambda r: dog(r) and r.get("home") and r["odds"] <= 150)
cell("raw_own over no-vig 15+ (gap)", lambda r: dog(r) and r.get("own_gap") is not None and r["own_gap"] >= 15)
cell("raw_own over no-vig 10-15", lambda r: dog(r) and r.get("own_gap") is not None and 10 <= r["own_gap"] < 15)
cell("raw_own over no-vig 5-10", lambda r: dog(r) and r.get("own_gap") is not None and 5 <= r["own_gap"] < 10)
cell("raw gap 10-15 & elo backs dog", lambda r: dog(r) and r.get("own_gap") is not None and 10 <= r["own_gap"] < 15 and (r.get("elo_edge") or 0) > 0)
cell("raw gap 15+ & elo backs dog", lambda r: dog(r) and r.get("own_gap") is not None and r["own_gap"] >= 15 and (r.get("elo_edge") or 0) > 0)
cell("money toward (drift>0.02)", lambda r: dog(r) and (r.get("drift") or 0) > 0.02)
cell("posted as dog/dogplay", lambda r: dog(r) and r.get("kind") in ("dog", "dogplay"))
cell("NOT posted (kind None)", lambda r: dog(r) and not r.get("kind"))

print("\n== FAVORITES -101..-150 ==")
cell("every slight favorite", fav)
cell("-101..-119", lambda r: fav(r) and r["odds"] >= -119)
cell("-120..-150", lambda r: fav(r) and r["odds"] < -119)
cell("-130..-150 (lean band)", lambda r: fav(r) and r["odds"] <= -130)
cell("own_beats", lambda r: fav(r) and r.get("own_beats"))
cell("lock_ok", lambda r: fav(r) and r.get("lock_ok"))
cell("lock_ok & own_agrees", lambda r: fav(r) and r.get("lock_ok") and r.get("own_agrees"))
cell("real_value", lambda r: fav(r) and r.get("real_value"))
cell("good()", lambda r: fav(r) and r.get("good"))
cell("edge_own > 0", lambda r: fav(r) and (r.get("edge_own") or -1) > 0)
cell("edge_own > 0.03", lambda r: fav(r) and (r.get("edge_own") or -1) > 0.03)
cell("raw gap 5+ over no-vig", lambda r: fav(r) and r.get("own_gap") is not None and r["own_gap"] >= 5)
cell("raw gap 10+", lambda r: fav(r) and r.get("own_gap") is not None and r["own_gap"] >= 10)
cell("home fav", lambda r: fav(r) and r.get("home"))
cell("road fav", lambda r: fav(r) and not r.get("home"))
cell("money toward fav (drift>0.02)", lambda r: fav(r) and (r.get("drift") or 0) > 0.02)
cell("n_reasons 2+", lambda r: fav(r) and (r.get("n_reasons") or 0) >= 2)
cell("posted (kind set)", lambda r: fav(r) and r.get("kind"))

print("\n== real_value favorites, posted vs not ==")
cell("real_value & posted", lambda r: fav(r) and r.get("real_value") and r.get("kind"))
cell("real_value & NOT posted", lambda r: fav(r) and r.get("real_value") and not r.get("kind"))
cell("real_value & NOT posted & own_beats", lambda r: fav(r) and r.get("real_value") and not r.get("kind") and r.get("own_beats"))
cell("real_value & NOT posted & not own_beats", lambda r: fav(r) and r.get("real_value") and not r.get("kind") and not r.get("own_beats"))
cell("real_value & thin", lambda r: fav(r) and r.get("real_value") and r.get("thin"))
cell("real_value & -101..-119", lambda r: fav(r) and r.get("real_value") and r["odds"] >= -119)
cell("real_value & -120..-150", lambda r: fav(r) and r.get("real_value") and r["odds"] < -119)
cell("good & own_beats & NOT posted", lambda r: fav(r) and r.get("good") and r.get("own_beats") and not r.get("kind"))
from collections import Counter
print(Counter(r.get("kind") for r in rows if fav(r) and r.get("kind")))
print(Counter(r.get("kind") for r in rows if dog(r) and r.get("kind")))
print(Counter((r.get("kind"), r.get("lean")) for r in rows if r.get("kind")))
