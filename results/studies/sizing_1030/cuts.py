"""10/30 SIZING, step 5: are the two splits real or a lucky cut? The Lock by its own read over the no-vig market (gap, points)
and the short Dog by its dog score - every neighbouring cutoff, both halves, by season. A real split holds at the
neighbours too. Usage: python cuts.py > cuts.out"""
from board import PLAYS, gap
from cells import show

lk = [p for p in PLAYS if p[2] == "lock"]
print("== THE LOCK: own read over the no-vig market under X vs X+ points")
for x in (5, 6, 7, 8, 9):
    show(f"gap under {x}", [p for p in lk if (gap(p[1]) or 0) < x])
    show(f"gap {x}+", [p for p in lk if (gap(p[1]) or 0) >= x])
print("\n== THE LOCK not football (the size-up applies outside football only)")
nf = [p for p in lk if p[1]["league"] not in ("nfl", "ncaaf")]
show("gap under 7", [p for p in nf if (gap(p[1]) or 0) < 7])
show("gap 7+", [p for p in nf if (gap(p[1]) or 0) >= 7])
sd = [p for p in PLAYS if p[2] == "dog" and p[1]["league"] in ("nhl", "nfl", "ncaaf") and p[1]["odds"] <= 150]
print("\n== THE SHORT DOG (+100..+150): dog score under X vs X+")
for x in (6, 7, 8, 9, 10):
    show(f"score under {x}", [p for p in sd if (p[1].get("dog_score") or 0) < x])
    show(f"score {x}+", [p for p in sd if (p[1].get("dog_score") or 0) >= x])
ld = [p for p in PLAYS if p[2] == "dog" and p[1]["league"] in ("nhl", "nfl", "ncaaf") and p[1]["odds"] > 150]
print("\n== THE LONG DOG (+151..+350) by score")
show("score under 8", [p for p in ld if (p[1].get("dog_score") or 0) < 8])
show("score 8+", [p for p in ld if (p[1].get("dog_score") or 0) >= 8])
print("\n== THE DOG price cut: +100..+X vs past it")
fd = [p for p in PLAYS if p[2] == "dog" and p[1]["league"] in ("nhl", "nfl", "ncaaf")]
for x in (130, 140, 150, 160, 175, 200):
    show(f"+100..+{x}", [p for p in fd if p[1]["odds"] <= x])
    show(f"+{x + 1}..+350", [p for p in fd if p[1]["odds"] > x])
