"""11/24 - S2c: THE BOARD'S OWN HOCKEY SIDES with the home / road split read on them (the 11/17 replay board rows,
dogs_1117 R3: every board day 2023-10 -> 2026-11 at the close, each side with the kind it posted as).
LAGS = the HOME side whose home margin lags its road margin (bottom fifth home-minus-road split, 6+ games each);
ACROSS = the road side against one. What a weight would have taken off the board, and what it would have kept.
python results/studies/daily_1124/s2c_board_replay.py"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dogs_1117"))
import lib  # noqa: E402
import h  # noqa: E402
import s_follow as F  # noqa: E402
import dlib  # noqa: E402

rk, _rest = F.split_reads("nhl")
byid = {g["id"]: g for g in lib.all_finals("nhl") if g["season"] >= 2018}
R = [r for r in dlib.r3() if r.get("league") == "nhl" and r.get("market") == "ml" and -200 <= r["odds"] <= 350]
O = h.Out("s2c_board_replay", (2023, 2024), [2025, 2026])
kinds = defaultdict(int)
for r in R:
    kinds[str(r.get("kind"))] += 1
O.p(f"S2c - THE REPLAY BOARD'S HOCKEY SIDES (2023-26, the close): {len(R)} sides -200..+350")
O.p("  kinds: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
for r in R:
    g = byid.get(r["gid"])
    if not g or g.get("neutral"):
        continue
    a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
    if not a or not b:
        continue
    lags = r["side"] == "home" and a["split"][1] <= 0.2
    across = r["side"] == "away" and a["split"][1] <= 0.2
    s = lib.season(r["date"])
    pr = dlib.flat(r)
    kind = r.get("kind")
    band = "dog +100..+350" if r["odds"] >= 100 else "fav -200..-101"
    O.add(f"every replay hockey side, {band}", s, pr, r["odds"])
    if lags:
        O.add(f"every replay hockey side, {band}: LAGS", s, pr, r["odds"])
    if across:
        O.add(f"every replay hockey side, {band}: ACROSS", s, pr, r["odds"])
    if kind:
        O.add("POSTED hockey side (any unit kind)", s, pr, r["odds"])
        O.add(f"POSTED hockey {band}", s, pr, r["odds"])
        O.add(f"POSTED as {kind}", s, pr, r["odds"])
        O.add("POSTED hockey side: " + ("LAGS" if lags else "ACROSS" if across else "neither"), s, pr, r["odds"])
        O.add(f"POSTED hockey {band}: " + ("LAGS" if lags else "ACROSS" if across else "neither"), s, pr, r["odds"])
        if lags or across:
            O.add(f"POSTED as {kind}: " + ("LAGS" if lags else "ACROSS"), s, pr, r["odds"])
O.show()
O.placebo("POSTED hockey side: LAGS", "POSTED hockey side (any unit kind)", fade=True)
O.placebo("POSTED hockey side: ACROSS", "POSTED hockey side (any unit kind)", fade=False)
O.save()
