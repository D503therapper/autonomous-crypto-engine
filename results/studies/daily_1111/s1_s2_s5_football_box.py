"""S1 (NFL) / S2 (college football) - THE SACK MARGIN, and S5 (both) - THE RUN-HEAVY SIDE (never studied: the only
'sack' lines on file are the 10/16 key-defender INJURY study; no play-mix study on file).
SACK MARGIN = sacks made minus sacks allowed (the opponent's sacks) a game, season to date before tonight, 3+ boxed
games (box scores 2021-26: the defensive group's 'sacks'). A pass rush that wins / a line that leaks is a strength
the public sees in highlights - does the price have it?
RUN SHARE = rushing attempts / (rushing attempts + passing attempts + sacks taken), season to date, 3+ boxed games.
The old angle: run-heavy dogs shorten the game (fewer possessions = more variance for the dog) - does it pay?
Cuts picked from the TRAIN quantiles (2021-22) only. Cells: favorite -101..-250 / dog +100..+350 at the close, ATS
at the close, and the first FAIR number of the paid odds history (ready_at / fair - no look-ahead) as the second
price. TRAIN 2021-22, HELD 2023 / 2024 / 2025 apart, 2026 live."""
import sys
from collections import defaultdict

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
TAG = {"nfl": "s1", "ncaaf": "s2"}[LG]
box = lib.box_rows(LG)
fin = lib.finals(LG)
allf = [g for g in lib.all_finals(LG) if g["stype"] == "2"]
hist = {x["id"]: x for x in lib.load_football(LG)}


def team_game(gid, team):
    """(sacks made, rush att, pass att) from the box, or None."""
    b = (box.get(gid) or {}).get(team)
    if not b:
        return None
    sk = ra = pa = 0.0
    seen = set()
    for r in b:
        st = r["st"]
        if r["group"] == "defensive" and st.get("sacks") not in (None, ""):
            sk += lib.num(st.get("sacks")) or 0
            seen.add("d")
        elif r["group"] == "rushing":
            ra += lib.num(st.get("rushingAttempts")) or 0
            seen.add("r")
        elif r["group"] == "passing":
            ca = str(st.get("completions/passingAttempts") or "")
            if "/" in ca:
                pa += lib.num(ca.split("/")[1]) or 0
                seen.add("p")
    return (sk, ra, pa) if {"d", "r", "p"} <= seen else None


run = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0, 0.0])   # (season, team) -> [n, sacks made, sacks allowed, ra, pa, sk taken]
pre = {}
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    th, ta = team_game(g["id"], g["home"]), team_game(g["id"], g["away"])
    if not th or not ta:
        continue
    for me, op, team in ((th, ta, g["home"]), (ta, th, g["away"])):
        r = run[(g["season"], team)]
        r[0] += 1
        r[1] += me[0]
        r[2] += op[0]
        r[3] += me[1]
        r[4] += me[2]
        r[5] += op[0]


def feats(gid, side):
    n, sm_, sa, ra, pa, sk = pre.get((gid, side), (0, 0, 0, 0, 0, 0))
    if n < 3 or ra + pa + sk <= 0:
        return None
    return {"sack": (sm_ - sa) / n, "run": ra / (ra + pa + sk)}


# train-only cuts
tr = {"sack": [], "run": []}
for g in fin:
    if g["stype"] != "2" or not (2021 <= g["season"] <= 2022):
        continue
    for side in ("home", "away"):
        f = feats(g["id"], side)
        if f:
            for k in tr:
                tr[k].append(f[k])
for k in tr:
    tr[k].sort()
q = {k: {p: tr[k][int(len(tr[k]) * p)] for p in (.1, .2, .5, .8, .9)} for k in tr}
print(LG, "train quantiles", {k: {p: round(v, 3) for p, v in d.items()} for k, d in q.items()})

cells = lib.Cells()
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    F = {s: feats(g["id"], s) for s in ("home", "away")}
    if not F["home"] or not F["away"]:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        me, op = F[side], F["away" if home else "home"]
        labs = []
        if me["sack"] >= q["sack"][.9]:
            labs.append("SACK margin top 10%")
        if me["sack"] >= q["sack"][.8]:
            labs.append("SACK margin top 20%")
        if me["sack"] <= q["sack"][.2]:
            labs.append("SACK margin bottom 20%")
        if me["sack"] <= q["sack"][.1]:
            labs.append("SACK margin bottom 10%")
        if q["sack"][.2] < me["sack"] < q["sack"][.8]:
            labs.append("SACK control: middle 60%")
        if me["sack"] - op["sack"] >= q["sack"][.9] - q["sack"][.1]:
            labs.append("SACK gap vs the opponent (top-bottom 10% wide)+")
        if me["run"] >= q["run"][.8]:
            labs.append("RUN share top 20% (run-heavy)")
        if me["run"] >= q["run"][.9]:
            labs.append("RUN share top 10%")
        if me["run"] <= q["run"][.2]:
            labs.append("RUN share bottom 20% (pass-heavy)")
        if q["run"][.2] < me["run"] < q["run"][.8]:
            labs.append("RUN control: middle 60%")
        if me["run"] >= q["run"][.8] and op["run"] <= q["run"][.5]:
            labs.append("RUN-heavy vs a pass-leaning opponent")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        ep = lib.early_price(hist, g["id"], side)
        for lab in labs:
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if ep and -250 <= ep[0] <= -101:
                    cells.add(f"{lab} | FAV ML first fair", s, lib.profit(won, ep[1]))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if ep and lib.dog_band(ep[0]):
                    cells.add(f"{lab} | DOG ML first fair", s, lib.profit(won, ep[1]))
            cells.add(f"{lab} | ATS", s, a)
cells.dump(TAG + "_s5", f"{TAG.upper()} / S5 {LG} - sack margin and run share, season to date, 3+ boxed games; close / ATS / "
           f"first fair; TRAIN 2021-22 (cuts from train quantiles)", (2021, 2022), (2023, 2024, 2025, 2026))
