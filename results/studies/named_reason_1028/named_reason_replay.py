"""10/28 THE NAMED REASON - the replay check. Every candidate side of every board day (the 10/27 funnel replay rows,
tools/value_play_replay at 8:35 AM PT, closing prices, params re-tuned each July 1): the football moneyline dogs
+100..+350 that pass the Dog gate's checks (own read over the price - dog_own_ok, not a trap, not fighting) and had NO
named reason (n_reasons 0) = the group the 10/28 football score_reason newly names. Do they win at their price?"""
import glob, json, sys
from collections import defaultdict
D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1027/"
rows = [json.loads(l) for f in sorted(glob.glob(D + "f*.jsonl")) for l in open(f)]
print(len(rows), "rows", min(r["date"] for r in rows), "->", max(r["date"] for r in rows))


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def st(rs):
    rs = [r for r in rs if r["result"] in ("won", "lost")]
    if not rs:
        return "n=0"
    w = sum(r["result"] == "won" for r in rs)
    net = sum((r["dec"] - 1) if r["result"] == "won" else -1 for r in rs)
    need = sum(1 / r["dec"] for r in rs) / len(rs)
    return f"n={len(rs):3d} {w}-{len(rs) - w} ({100 * w / len(rs):.1f}% vs {100 * need:.1f} needed) {net:+.1f}u ROI {100 * net / len(rs):+.1f}%"


for lg in ("ncaaf", "nfl"):
    print(f"\n===== {lg} moneyline dogs +100..+350, not a trap, own read not fighting, own read over the price (dog_own_ok) =====")
    pool = [r for r in rows if r["league"] == lg and 100 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"]
            and r["dog_own_ok"] and r["result"] in ("won", "lost")]
    for r in pool:
        r["over"] = ((r["edge_own"] + 1) / r["dec"] - r["p_market"]) * 100
    named = [r for r in pool if r["n_reasons"] > 0]
    none = [r for r in pool if r["n_reasons"] == 0]
    print("had a named reason        ", st(named))
    print("NO named reason (newly named by score_reason when the score clears the gate)", st(none))
    gate = 4 if lg == "ncaaf" else 8
    for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 9), (9, 99)):
        print(f"  no reason, own read {lo}-{hi} pts over the price   ", st([r for r in none if lo <= r["over"] < hi]))
    print(f"  no reason, own read {gate}+ over (the gate on the own read alone) ", st([r for r in none if r["over"] >= gate]))
    print(f"  no reason, own read {gate}+ over, 2025-07+ (blind-ish)           ", st([r for r in none if r["over"] >= gate and r["date"] >= "2025-07-01"]))
    print(f"  named,     own read {gate}+ over                                  ", st([r for r in named if r["over"] >= gate]))
    by = defaultdict(list)
    for r in none:
        if r["over"] >= gate:
            by[season(r["date"])].append(r)
    print("  no reason, gate+ by season:", " | ".join(f"{s} {st(v)}" for s, v in sorted(by.items())))
    hm = [r for r in none if r["over"] >= gate and r["home"]]
    print(f"  no reason, gate+ HOME dogs (the NM St shape)                      ", st(hm))
    print(f"  no reason, gate+ ROAD dogs                                        ", st([r for r in none if r["over"] >= gate and not r["home"]]))
    print(f"  no reason, gate+ 2u (10/23 plan Dog) net: {2 * sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in none if r['over'] >= gate):+.1f}u")
