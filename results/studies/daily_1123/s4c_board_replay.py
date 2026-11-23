"""11/23 - S4c: THE BOARD'S OWN HOCKEY DOGS with the two new reads on them (the 11/17 replay board rows, dogs_1117 R3:
every board day 2023-10 -> 2026-11 at the close, each side with its dog score and the kind it posted as). LOW = the
bottom fifth of takeaways-minus-giveaways in road games (S4); SHELLED = gave up 40+ shots last game, playing again
within 2 days (S6). What a -2 / -1 on the dog score would have taken off the board, and what it would have kept.
python results/studies/daily_1123/s4c_board_replay.py"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dogs_1117"))
import lib  # noqa: E402
import h  # noqa: E402
import s_today as T  # noqa: E402
import dlib  # noqa: E402

tb = T.teambox("nhl")
allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021 and g["stype"] == "2"]
byid = {g["id"]: g for g in allf}
last, prev = {}, {}
for g in allf:
    for t in (g["home"], g["away"]):
        if (g["season"], t) in prev:
            last[(g["id"], t)] = prev[(g["season"], t)] + (g["start"],)
    for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
        b = (tb.get(g["id"]) or {}).get(str(o))
        prev[(g["season"], t)] = (lib.num((b or {}).get("shotsTotal")), g["start"])


def counters(g, t, o):
    a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
    if not a or not b:
        return None
    gv, tk = lib.num(a.get("giveaways")), lib.num(a.get("takeaways"))
    if gv is None or tk is None:
        return None
    road = 1.0 if g["away"] == t else 0.0
    return {"r_n": road, "r_net": road * (tk - gv), "n": 1.0}


rk = T.ranked(allf, counters, lambda s, n: {"rnet": s["r_net"] / s["r_n"]} if s["r_n"] >= 4 else None, 10)
R = [r for r in dlib.r3() if r.get("league") == "nhl" and r.get("market") == "ml" and 100 <= r["odds"] <= 350]
O = h.Out("s4c_board_replay", (2023, 2024), [2025, 2026])
O.p(f"S4c - THE REPLAY BOARD'S HOCKEY DOGS (2023-26, the close): {len(R)} dog sides, {sum(1 for r in R if r.get('kind'))} posted as a unit play")
O.p("  kinds: " + ", ".join(f"{k} {v}" for k, v in sorted(defaultdict(int, {}).items())))
kinds = defaultdict(int)
for r in R:
    kinds[str(r.get("kind"))] += 1
O.p("  kinds: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
sample = next((r for r in R if r.get("kind")), None)
O.p("  score fields on a row: " + ", ".join(k for k in (sample or {}) if "score" in k or k in ("x", "dog", "floor_score")))
for r in R:
    g = byid.get(r["gid"])
    if not g:
        continue
    t = g["home"] if r["side"] == "home" else g["away"]
    me = rk.get((g["id"], t))
    lv = last.get((g["id"], t))
    low = bool(me and me["rnet"][1] <= 0.2)
    shelled = bool(lv and lv[0] is not None and lv[0] >= 40 and lib.days_between(lv[1], lv[2]) <= 2.2)
    s = lib.season(r["date"])
    pr = dlib.flat(r)
    kind = r.get("kind")
    O.add("every replay hockey dog +100..+350", s, pr, r["odds"])
    if low:
        O.add("every replay hockey dog: LOW", s, pr, r["odds"])
    if shelled:
        O.add("every replay hockey dog: SHELLED", s, pr, r["odds"])
    if kind:
        O.add("POSTED hockey dog (any unit kind)", s, pr, r["odds"])
        O.add(f"POSTED as {kind}", s, pr, r["odds"])
        O.add("POSTED hockey dog: " + ("LOW" if low else "not LOW"), s, pr, r["odds"])
        O.add("POSTED hockey dog: " + ("SHELLED" if shelled else "not SHELLED"), s, pr, r["odds"])
        O.add("POSTED hockey dog: " + ("LOW or SHELLED" if (low or shelled) else "neither"), s, pr, r["odds"])
        if low:
            O.add(f"POSTED as {kind}: LOW", s, pr, r["odds"])
O.show()
O.placebo("POSTED hockey dog: LOW", "POSTED hockey dog (any unit kind)", fade=True)
O.placebo("POSTED hockey dog: LOW or SHELLED", "POSTED hockey dog (any unit kind)", fade=True)
O.save()
