"""11/16 FABLE - EVERY FACT TRUE: is the back-to-back weight's edge in the REAL back-to-backs? The rested dog facing a team
that 'played last night', at the closing moneyline, split by what the flag really was:
  real      - the favorite played inside 29 hours (both the old UTC-date rule and the clock say so)
  false     - the old rule said 'played last night', the clock says two nights apart (36-48 hours)
  missed    - a real back-to-back the old rule did not see
NBA / NHL regular seasons 2021-26, flat 1u on the dog, halves 2021-23 / 2024-26.
python results/studies/facts_1116/b2b_roi.py -> b2b_roi_out.txt"""
import os
import sys
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports_data as sd            # noqa: E402

G = sd.load_games()
T = lambda s: datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")           # noqa: E731


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


out = []
for lg in ("nba", "nhl"):
    last = {}
    cells = {}
    for g in sorted(G.values(), key=lambda g: g["start"]):
        if g["league"] != lg or g.get("status") != "final" or g["start"] < "2021-09-01":
            continue
        if str(g.get("stype") or "2") in ("2", "3", "5"):
            flags = {}
            for s in ("home", "away"):
                p = last.get(g[s])
                if p:
                    hrs = (T(g["start"]) - T(p)).total_seconds() / 3600
                    flags[s] = ((T(g["start"][:10] + "T00:00") - T(p[:10] + "T00:00")).days == 1, hrs <= 29, hrs)
            mh, ma = num(g.get("ml_home")), num(g.get("ml_away"))
            if str(g.get("stype") or "2") == "2" and mh and ma and len(flags) == 2:
                for dog, fav, ml in (("home", "away", mh), ("away", "home", ma)):
                    if not 100 <= ml <= 350:
                        continue
                    d_date, d_clock, _ = flags[dog]
                    f_date, f_clock, f_h = flags[fav]
                    won = (int(g["home_score"]) > int(g["away_score"])) == (dog == "home")
                    pnl = ml / 100 if won else -1.0
                    half = "2021-23" if g["start"] < "2024-07-01" else "2024-26"
                    keys = []
                    if f_date and f_clock and not d_clock and not d_date:
                        keys.append("real b2b (both rules)")
                    if f_date and not f_clock and not d_date:
                        keys.append("FALSE b2b (old rule yes, the clock: two nights apart)")
                    if f_clock and not f_date and not d_clock:
                        keys.append("missed b2b (the clock yes, old rule no)")
                    if f_date and not d_date:
                        keys.append("the OLD flag as the weights read it")
                    if f_clock and not d_clock:
                        keys.append("the CLOCK flag (29 hours)")
                    if not f_clock and not d_clock and not f_date and not d_date:
                        keys.append("neither side on a back-to-back")
                    for k in keys:
                        for kk in (k, k + " | " + half):
                            c = cells.setdefault(kk, [0, 0, 0.0])
                            c[0] += won
                            c[1] += 1
                            c[2] += pnl
            for s in ("home", "away"):
                last[g[s]] = g["start"]
    out.append(f"{lg.upper()} - the rested dog (+100..+350) at the close, flat 1u")
    for k in sorted(cells):
        w, n, u = cells[k]
        out.append(f"  {k:62s} {w:4d}-{n - w:<4d} {u / n:+7.1%} on {n}")
txt = "\n".join(out)
print(txt)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "b2b_roi_out.txt"), "w").write(txt + "\n")
