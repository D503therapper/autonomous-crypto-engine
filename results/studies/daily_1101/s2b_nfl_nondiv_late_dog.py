"""Study 2b (11/1): robustness of study 2's side finding - the NON-DIVISION NFL dog late in the season (Nov 15+).
Split by price band, home / road, the team's record (.400+ / under), whether it was a dog in each of its last 4 (the
10/29 tracker lead - so the two don't double-count), the window start (Nov 1 / Nov 15 / Dec 1), and the dog across a
non-division favorite at -101..-150 vs -151+. Closing ML and the FIRST FAIR early number. Train 2018-23, held 2024-26."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2023), (2024, 2025, 2026)
meet = Counter()
for g in lib.sd.load_games("nfl").values():
    if g.get("league") != "nfl" or str(g.get("stype") or "2") != "2" or not g.get("start"):
        continue
    meet[(lib.season(g["start"]), frozenset((g["home"], g["away"])))] += 1
fin = [g for g in lib.finals("nfl") if g["stype"] == "2"]
tl = lib.team_log(fin)
xby = {x["id"]: x for x in lib.load_football("nfl")}
C = lib.Cells()
for g in fin:
    if g["neutral"]:
        continue
    s = g["season"]
    div = meet[(s, frozenset((g["home"], g["away"])))] >= 2
    md = g["start"][5:10]
    jan = md < "03-01"
    for side, team, opp, o, won, home in lib.sides(g):
        if not lib.dog_band(o):
            continue
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == s]
        wp = sum(lib.won_g(x, team) for x in prev) / len(prev) if prev else None
        l4 = prev[-4:]
        dog4 = len(l4) == 4 and all(((x["mlh"] if x["home"] == team else x["mla"]) or 0) > 0 for x in l4)
        pr = lib.profit(won, lib.dec(o))
        e = lib.early_price(xby, g["id"], side)
        kind = "division" if div else "NON-division"
        for start_md, wname in (("11-01", "Nov 1+"), ("11-15", "Nov 15+"), ("12-01", "Dec 1+")):
            if md >= start_md or jan:
                C.add(f"{kind} dog | {wname}", s, pr)
        if not (md >= "11-15" or jan):
            continue
        tags = [f"{kind} dog late | {'+100..+150' if o <= 150 else '+151..+350'}",
                f"{kind} dog late | {'home' if home else 'road'}",
                f"{kind} dog late | record {'.400+' if (wp or 0) >= 0.4 else 'under .400'}",
                f"{kind} dog late | {'a dog in each of its last 4' if dog4 else 'NOT a dog in each of its last 4'}"]
        for t in tags:
            C.add(t, s, pr)
        if e and 100 <= e[0] <= 350:
            C.add(f"{kind} dog late | FIRST FAIR", s, lib.profit(won, e[1]))
            if not dog4:
                C.add(f"{kind} dog late | NOT a dog in each of its last 4 | FIRST FAIR", s, lib.profit(won, e[1]))
        C.add(f"{kind} dog late | ATS", s, lib.ats(g, side))

C.dump("s2b", "NFL NON-DIVISION DOG LATE IN THE SEASON - robustness (closing ML; train 2018-23, held 2024-26)", TR, HE)
