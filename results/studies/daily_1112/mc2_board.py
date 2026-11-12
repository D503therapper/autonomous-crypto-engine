"""11/12 DAILY - MC2: FOOTBALL'S MONEY CHECK ON THE REPLAY BOARD - THE THREE ARMS (+ cuts of the third).
Rows: results/studies/daily_1112/funnel3.py - every board day with a football game 2023-10-01 -> 2026-11-10, the WHOLE
board built (every sport competes for the Lock / the Dog), closing prices, params re-tuned each July 1, no injury reports.
  old  today's football: the blend's dials on the old fit (the last 900 games, as each July's tune left them), the
       money check = the OWN read over the price
  hon  the honest dials (BLEND_STABLE_SKIP = ()), the same check
  wt   the honest dials, the check RE-BASED on the weighed reads (a dog: the close + its dog score over the real price;
       a favorite: w_p over it)   wtd dogs only / wtf favorites only / wt4 wt + the NFL Dog gate at 4
As of the 11/13 rules the college runner-up dog play is gone (the 11/12 sweep) - "11/14 rules" drops it.
flat = 1u a play at the close; units = the play's own size by the 11/14 rules. train = to 2025-06-30, held = after;
2026 = the current season (Aug-Nov 2026), the live window = 2026-09-29 on.
Usage: python results/studies/daily_1112/mc2_board.py > results/studies/daily_1112/mc2_board.out"""
import math, os
import mclib as M
D = M.D

NEW = M.load(os.path.join(M.MINE, "new"))
OLD = M.load(os.path.join(M.MINE, "old"))
print(f"rows: new {len(NEW)} ({len({r['date'] for r in NEW})} football board days), old {len(OLD)} ({len({r['date'] for r in OLD})})")
ARMS = (("old", OLD), ("hon", NEW), ("wt", NEW), ("wtd", NEW), ("wtf", NEW), ("wt4", NEW))
KINDS = ("lock", "dog", "solo", "play", "dogplay")


def units_line(rs, arm):
    """units won / risked at each play's own size."""
    won = risk = 0.0
    for r in rs:
        u = r.get("u_" + arm) or 0.0
        risk += u
        won += u * (r["dec"] - 1) if r["y"] == 1 else -u
    return won, risk


def show(name, rs, arm):
    c = D.cell(name, rs, out=False)
    won, risk = units_line(rs, arm)
    print(f"  {name:44s} {c['w']:3d}-{c['n'] - c['w']:<3d} flat {c['roi']:+6.1f}% z {c['z']:+5.2f} | train {c['train']:+6.1f}% ({c['ntr']:3d}) "
          f"held {c['held']:+6.1f}% ({c['nhe']:3d}) | seasons up {c['up']}/{c['ns']} | units {won:+6.1f}u on {risk:5.1f}u")
    return c


def picked(rows, arm, lg=None, rules1114=True):
    out = []
    for r in rows:
        k = r.get("k_" + arm)
        if not k or (lg and r["league"] != lg):
            continue
        if rules1114 and k == "dogplay" and r["league"] == "ncaaf":
            continue
        out.append(r)
    return out


for lg in ("ncaaf", "nfl", None):
    print(f"\n==== {(lg or 'football, both').upper()} - every unit play (11/14 rules: no college runner-up dog)")
    for arm, rows in ARMS:
        ps = picked(rows, arm, lg)
        print(f" -- arm {arm}")
        show("every unit play", ps, arm)
        show("  favorites", [r for r in ps if r["odds"] < 0], arm)
        show("  dogs", [r for r in ps if r["odds"] > 0], arm)
        for k in KINDS:
            x = [r for r in ps if r["k_" + arm] == k]
            if x:
                show(f"  {k}", x, arm)
        show("  the 2026 season", [r for r in ps if r["date"] >= "2026-07-01"], arm)
        show("  the live window (9/29-11/10)", [r for r in ps if r["date"] >= "2026-09-29"], arm)

print("\n==== THE COLLEGE RUNNER-UP DOG (cut 11/13) - for the record, by arm")
for arm, rows in ARMS:
    x = [r for r in rows if r.get("k_" + arm) == "dogplay" and r["league"] == "ncaaf"]
    if x:
        show(f"{arm}: college dogplay", x, arm)

print("\n==== WHAT THE RE-BASED CHECK ADDS / DROPS AGAINST TODAY (old arm), same days")
ko = {M.key(r): r for r in picked(OLD, "old")}
for arm in ("wt", "wtd", "wtf", "wt4"):
    kn = {M.key(r): r for r in picked(NEW, arm)}
    both = [kn[k] for k in kn if k in ko]
    print(f" -- {arm}")
    show("in both", both, arm)
    show("only today's (the re-base drops)", [ko[k] for k in ko if k not in kn], "old")
    show("only the re-base (it adds)", [kn[k] for k in kn if k not in ko], arm)

print("\n==== THE PLACEBO: the same NUMBER of football plays a season, drawn at random from the eligible band (dogs +100..+350 /"
      " favorites -150..-101, not a trap), 2,000 draws - where does each arm's flat ROI sit?")
import random
random.seed(1112)
pool = [r for r in NEW if not r["trap"] and (100 <= r["odds"] <= 350 or -150 <= r["odds"] <= -101)]
by_season = {}
for r in pool:
    by_season.setdefault((r["season"], r["odds"] > 0), []).append(r)
for arm, rows in ARMS:
    ps = picked(rows, arm)
    if len(ps) < 10:
        continue
    real = D.bet(ps)[2]
    need = {}
    for r in ps:
        need[(r["season"], r["odds"] > 0)] = need.get((r["season"], r["odds"] > 0), 0) + 1
    hits = 0
    for _ in range(2000):
        draw = []
        for k, n in need.items():
            src = by_season.get(k) or []
            draw += random.sample(src, min(n, len(src)))
        if D.bet(draw)[2] >= real:
            hits += 1
    print(f"  {arm:4s} n {len(ps):3d} flat {real:+6.1f}% - random plays with the same season / fav-dog mix beat it {hits} of 2000 (p {hits / 2000:.3f})")
print("\ncells:", D.CELLS[0])
