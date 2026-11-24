"""11/24 - S9c: THE COLLEGE HOOPS REPLAY ROWS with the deep-team-on-its-second-day read on them (the 11/16 replay
rows, ~/.cache/d503_maxcol1116/cbb_rows.pkl: every college hoops side 2018-26 with its spread stack, the kind it posted
as and its result at the close; the player box starts 2021, so the read exists from 2021-22).
FOR = the side ACROSS a deep team (bottom fifth share of minutes on its top 5, 4+ boxed games) playing the day after
a game; AGAINST = the deep team itself. What +/-0.03 on the spread stack would add to and take off the 1/2u stack play,
and what the read does on the dog slot's own dogs.
python results/studies/daily_1124/s9c_replay.py"""
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_follow as F  # noqa: E402

W = 0.03
E = 1e-9
read, fin = F.depth_reads()
byid = {g["id"]: g for g in lib.all_finals("ncaab") if g["season"] >= 2021}
R = pickle.load(open(os.path.expanduser("~/.cache/d503_maxcol1116/cbb_rows.pkl"), "rb"))
O = h.Out("s9c_replay", (2021, 2023), [2024, 2025, 2026])
kinds = defaultdict(int)
for r in R:
    kinds[(r.get("market"), str(r.get("kind")))] += 1
O.p(f"S9c - THE REPLAY ROWS: {len(R)} sides; kinds: " + ", ".join(f"{k[0]}/{k[1]} {v}" for k, v in sorted(kinds.items(), key=lambda x: str(x))))
byday = defaultdict(list)
for r in R:
    g = byid.get(r["gid"])
    if not g or r.get("pnl") is None or r["season"] < 2021:
        continue
    t, o = (g["home"], g["away"]) if r["side"] == "home" else (g["away"], g["home"])
    me, th = read.get((g["id"], t)), read.get((g["id"], o))
    mine = bool(me and me[2] <= 1.3 and me[1] <= 0.2)
    theirs = bool(th and th[2] <= 1.3 and th[1] <= 0.2)
    dp = 1 if (theirs and not mine) else -1 if (mine and not theirs) else 0
    s, p = r["season"], r["pnl"]
    word = "FOR (across a deep team on its second day)" if dp == 1 else "AGAINST (the deep team on its second day)" if dp == -1 else "none"
    if r.get("market") == "spread" and r.get("stack") is not None:
        st = r["stack"]
        new = st + W * dp
        byday[r["date"]].append(dict(r, new=new))
        O.add("every spread side", s, p)
        if dp:
            O.add(f"every spread side | {word}", s, p)
        if st >= 0.05 - E:
            O.add("stack +0.05+ (today's play pool)", s, p)
            O.add(f"stack +0.05+ | {word}", s, p)
            if dp == -1 and new < 0.05 - E:
                O.add("DROPPED by the weight (stack +0.05..+0.07, the deep team on its second day)", s, p)
        if 0.05 - W - E <= st < 0.05 - E:
            O.add("stack +0.02..+0.04", s, p)
            O.add(f"stack +0.02..+0.04 | {word}{' - ADDED by the weight' if dp == 1 else ''}", s, p)
        if st < 0.02 - E and dp == 1:
            O.add("stack under +0.02 | FOR (still under the bar)", s, p)
        if new >= 0.05 - E:
            O.add("NEW pool: stack with the weight +0.05+", s, p)
        if r.get("kind") == "stackplay":
            O.add("the replay's posted stack plays", s, p)
            O.add(f"the replay's posted stack plays | {word}", s, p)
    if r.get("market") == "ml":
        if 100 <= (r.get("odds") or 0) <= 350:
            O.add("every moneyline dog +100..+350", s, p, r["odds"])
            if dp:
                O.add(f"every moneyline dog +100..+350 | {word}", s, p, r["odds"])
        if r.get("kind") and r.get("kind") != "stackplay":
            O.add(f"POSTED moneyline {r['kind']}", s, p, r.get("odds"))
            if dp:
                O.add(f"POSTED moneyline {r['kind']} | {word}", s, p, r.get("odds"))
for cap in (3,):
    for name, key in (("OLD", "stack"), ("NEW", "new")):
        for d, v in byday.items():
            seen = set()
            for r in sorted((x for x in v if x[key] >= 0.05 - E), key=lambda x: -x[key]):
                if r["gid"] in seen:
                    continue
                seen.add(r["gid"])
                if len(seen) > cap:
                    break
                O.add(f"top {cap} a night by the {name} stack", r["season"], r["pnl"])
O.show()
O.placebo("every spread side | FOR (across a deep team on its second day)", "every spread side")
O.placebo("every spread side | AGAINST (the deep team on its second day)", "every spread side", fade=True)
O.save()
