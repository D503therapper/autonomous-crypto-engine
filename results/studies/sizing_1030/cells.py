"""10/30 SIZING, step 3: the cells the proposed schedule sizes on, flat 1u, by half and by season - the size-up is honest
only if the bigger-size cell wins MORE vs the price than the smaller-size cell in BOTH halves.
Usage: python cells.py > cells.out"""
from collections import defaultdict

from board import PLAYS, half, pnl, season

FOOTBALL = ("nfl", "ncaaf")


def st(ps):
    if not ps:
        return "n=0".ljust(22)
    w = sum(r["result"] == "won" for _, r, _, _ in ps)
    l = sum(r["result"] == "lost" for _, r, _, _ in ps)
    net = sum(pnl(r, 1) for _, r, _, _ in ps)
    return f"{w}-{l} {100 * net / len(ps):+6.1f}%".ljust(22)


def show(name, ps):
    by = defaultdict(list)
    for p in ps:
        by[half(p[0])].append(p)
    seas = defaultdict(list)
    for p in ps:
        if half(p[0]) != "live":
            seas[season(p[0])].append(p)
    s = " ".join(f"{k}:{100 * sum(pnl(r, 1) for _, r, _, _ in v) / len(v):+.0f}%({len(v)})" for k, v in sorted(seas.items()))
    print(f"  {name:52s} train {st(by['train'])} held {st(by['held'])} all {st(by['train'] + by['held'])} live {st(by['live'])} | {s}")


lock = [p for p in PLAYS if p[2] == "lock"]
dog = [p for p in PLAYS if p[2] == "dog"]
print("== THE LOCK (full Locks; thin Locks are no Lock since 10/29, backup Locks ½u)")
show("all", lock)
show("own read 3-8% over the price", [p for p in lock if (p[1]["edge_own"] or 0) < 0.08])
show("own read 8%+ over the price", [p for p in lock if (p[1]["edge_own"] or 0) >= 0.08])
show("own 3-8%, not football", [p for p in lock if (p[1]["edge_own"] or 0) < 0.08 and p[1]["league"] not in FOOTBALL])
show("football (NFL + college)", [p for p in lock if p[1]["league"] in FOOTBALL])
show("today's 3u (both reads over)", [p for p in lock if p[3] == 3])
show("today's 1u (no weighed read)", [p for p in lock if p[3] == 1])
show("3u-cell, own 3-8%", [p for p in lock if p[3] == 3 and (p[1]["edge_own"] or 0) < 0.08])
show("3u-cell, own 8%+", [p for p in lock if p[3] == 3 and (p[1]["edge_own"] or 0) >= 0.08])
show("1u-cell, own 3-8%", [p for p in lock if p[3] == 1 and (p[1]["edge_own"] or 0) < 0.08])
show("1u-cell, own 8%+", [p for p in lock if p[3] == 1 and (p[1]["edge_own"] or 0) >= 0.08])
show("ncaab", [p for p in lock if p[1]["league"] == "ncaab"])
show("ncaab own 3-8%", [p for p in lock if p[1]["league"] == "ncaab" and (p[1]["edge_own"] or 0) < 0.08])
show("ncaab own 8%+", [p for p in lock if p[1]["league"] == "ncaab" and (p[1]["edge_own"] or 0) >= 0.08])
show("not ncaab", [p for p in lock if p[1]["league"] != "ncaab"])
print("\n== THE DOG OF THE DAY (football + hockey; NBA / college hoops apart)")
fd = [p for p in dog if p[1]["league"] in ("nhl", "nfl", "ncaaf")]
show("all", fd)
show("+100..+150", [p for p in fd if p[1]["odds"] <= 150])
show("+151..+350", [p for p in fd if p[1]["odds"] > 150])
show("+100..+150 real edge (today 2u)", [p for p in fd if p[1]["odds"] <= 150 and p[3] > 0.5])
show("+100..+150 thin (today ½u)", [p for p in fd if p[1]["odds"] <= 150 and p[3] <= 0.5])
show("+151..+350 real edge (today 2u)", [p for p in fd if p[1]["odds"] > 150 and p[3] > 0.5])
show("+151..+350 thin (today ½u)", [p for p in fd if p[1]["odds"] > 150 and p[3] <= 0.5])
show("real edge (today 2u)", [p for p in fd if p[3] > 0.5])
show("thin (today ½u)", [p for p in fd if p[3] <= 0.5])
for lg in ("nhl", "ncaaf", "nfl"):
    show(f"{lg} +100..+150", [p for p in fd if p[1]["league"] == lg and p[1]["odds"] <= 150])
    show(f"{lg} +151..+350", [p for p in fd if p[1]["league"] == lg and p[1]["odds"] > 150])
show("nba dog", [p for p in dog if p[1]["league"] == "nba"])
show("ncaab dog", [p for p in dog if p[1]["league"] == "ncaab"])
print("\n== EVERY BOARD DOG (Dog + runner-up + floor + NBA floor + fallback) by price - the band holds outside the Dog?")
alld = [p for p in PLAYS if p[1]["odds"] >= 100 and p[1]["league"] in ("nhl", "nfl", "ncaaf")]
show("+100..+150", [p for p in alld if p[1]["odds"] <= 150])
show("+151..+350", [p for p in alld if p[1]["odds"] > 150])
print("\n== cross-check: the Dog vs the Lock vs the others, flat (what each kind earns - the honest size order)")
for k in ("dog", "lock", "nbafav", "nbafloor", "floor", "dogplay", "play"):
    show(k, [p for p in PLAYS if p[2] == k])
