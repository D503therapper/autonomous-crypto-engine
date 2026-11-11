"""STUDY 1 (part B) + STUDIES 2 / 3 - size schedules on today's replay board (blib.PLAYS). Each schedule is
fn(kind, row, units_today) -> units. A schedule PASSES only if it wins more units than today's in BOTH train and held
out, its worst stretch (peak-to-trough by day, both halves and overall) is no deeper than today's, and no season flips
down. 21 schedules tried: at "beats today in both halves" alone, ~1 in 4 would pass by luck; the worst-stretch bar and
the cell bar (s1_cells.out: the sized-up cell wins more vs the price than its sibling in both halves) cut that down.
Usage: python s1_sizing.py > s1_sizing.out"""
from blib import schedule

TODAY = lambda k, r, u: u       # noqa: E731


def with_(**over):
    def f(k, r, u):
        return over[k](r, u) if k in over else u
    return f


print("SIZE SCHEDULES (today's board; today's sizes: Lock 2u / 1u, football 1u; Dog 2u to +150 / ½u past; NBA Dog 1u / ½u; plays ½u; NBA favorite 1u; floors ½u)")
base = schedule("TODAY", TODAY)
S = [
    ("everything flat 1u", lambda k, r, u: 1.0),
    ("everything flat ½u", lambda k, r, u: 0.5),
    # the best kinds - size up?
    ("A1 NBA floor 1u", with_(nbafloor=lambda r, u: 1.0)),
    ("A2 NBA floor 1u on the road, ½u home", with_(nbafloor=lambda r, u: 0.5 if r["home"] else 1.0)),
    ("A3 runner-up dog 1u", with_(dogplay=lambda r, u: 1.0)),
    ("A4 NBA favorite play 2u", with_(nbafav=lambda r, u: 2.0)),
    ("A5 Dog +120..+150 3u (the rest as today)", with_(dog=lambda r, u: 3.0 if u == 2 and 120 <= r["odds"] <= 150 else u)),
    ("A6 Dog +100..+119 1u, +120..+150 2u", with_(dog=lambda r, u: 1.0 if u == 2 and r["odds"] < 120 else u)),
    ("A7 Dog +100..+119 1u, +120..+150 3u", with_(dog=lambda r, u: (1.0 if r["odds"] < 120 else 3.0) if u == 2 else u)),
    ("A8 short Dog 3u", with_(dog=lambda r, u: 3.0 if u == 2 else u)),
    ("A9 floor 1u at +120..+150, ½u else", with_(floor=lambda r, u: 1.0 if 120 <= r["odds"] <= 150 else 0.5)),
    ("A10 floor 1u", with_(floor=lambda r, u: 1.0)),
    # the weak kinds - cut?
    ("B1 no value plays", with_(play=lambda r, u: 0.0)),
    ("B2 value plays only at -150..-131 / -119..-101", with_(play=lambda r, u: 0.0 if -130 <= r["odds"] <= -120 else u)),
    ("B3 Lock flat 1u", with_(lock=lambda r, u: 1.0 if u >= 1 else u)),
    ("B4 no long Dog (+151 on)", with_(dog=lambda r, u: 0.0 if r["odds"] > 150 and r["league"] != "nba" else u)),
    ("B5 no floor at +100..+119", with_(floor=lambda r, u: 0.0 if r["odds"] < 120 else u)),
    ("B6 no floor when the money ran away 2+ pts (close-to-open: a look-ahead at 8 AM)", with_(floor=lambda r, u: 0.0 if (r.get("drift") or 0) >= 0.02 else u)),
    ("B7 no home floor play", with_(floor=lambda r, u: 0.0 if r["home"] else u)),
    # combos of what the cells back
    ("C1 = A1 + A3", with_(nbafloor=lambda r, u: 1.0, dogplay=lambda r, u: 1.0)),
    ("C2 = A2 + A3", with_(nbafloor=lambda r, u: 0.5 if r["home"] else 1.0, dogplay=lambda r, u: 1.0)),
    ("C3 = A1 + A3 + A6", with_(nbafloor=lambda r, u: 1.0, dogplay=lambda r, u: 1.0, dog=lambda r, u: 1.0 if u == 2 and r["odds"] < 120 else u)),
]
ok = []
for name, fn in S:
    r = schedule(name, fn)
    if r["train"] > base["train"] and r["held"] > base["held"] and r["dd"] >= base["dd"] - 0.05 and r["dd_tr"] >= base["dd_tr"] - 0.05 \
            and r["dd_he"] >= base["dd_he"] - 0.05 and r["up"] >= base["up"]:
        ok.append(name)
print(f"\nPASS (more units in BOTH halves, no deeper worst stretch in either half or overall, no season lost): {ok or 'NONE'}")
print("more units in both halves but a deeper worst stretch:")
for name, fn in S:
    r = schedule(name, fn, quiet=True)
    if r["train"] > base["train"] and r["held"] > base["held"] and name not in ok:
        print(f"   {name}: {r['net']:+.1f}u vs {base['net']:+.1f}u, worst {r['dd']:+.1f} vs {base['dd']:+.1f} (train {r['dd_tr']:+.1f} vs {base['dd_tr']:+.1f}, held {r['dd_he']:+.1f} vs {base['dd_he']:+.1f})")
