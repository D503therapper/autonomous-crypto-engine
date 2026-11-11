"""S6 - NFL: (1) THE QUARTERBACK ADJUSTMENT (what Dr. Bob is best known for) and (2) a MARKET-AWARE number.
(1) Games where a team's starter is not the QB of its last game (2018-26, 2020-26 with early lines): is the model's
    QB swing (its number with the new starter minus its number with the old one) the size of the line's move? ATS of
    backing / fading the team with the new QB at the close; a 'green' QB (under 200 career dropbacks) at the close.
(2) Instead of my own number, predict what the early line MISSES: a ridge on the cover margin at the first fair
    median line, on the model's gap and its pieces, fit on 2020-22, re-fit each season after -> bets 2023-26 at the
    best book by the size of the predicted miss."""
from collections import defaultdict
import statistics
import numpy as np
import splib as S
import records as R

o = S.Out("s6")
recs = R.records("nfl")
HELD = set(range(2020, 2027))
CELLS = [0]


def show(name, bets):
    CELLS[0] += 1
    if not bets:
        o.p(f"  {name:52s} -")
        return
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    held = [p for s, p in bets if s in HELD]
    up = sum(1 for s in by if s in HELD and sum(by[s]) > 0)
    o.p(f"  {name:52s} ALL {S.line_stats([p for _, p in bets])} | HELD {S.line_stats(held)} up {up}/{sum(1 for s in by if s in HELD)} | "
        + " ".join(f"{str(s)[2:]}:{sum(by[s]) / len(by[s]) * 100:+.0f}({len(by[s])})" for s in sorted(by)))


o.p("(1) THE QB ADJUSTMENT")
ch = [r for r in recs if r["feat"]["qbchg_h"] + r["feat"]["qbchg_a"] == 1]
o.p(f"   games where exactly one team starts a QB who did not start its last game: {len(ch)} of {len(recs)}")
x, y = [], []
for r in ch:
    if not r["look"]:
        continue
    sg = 1 if r["feat"]["qbchg_h"] else -1
    x.append(sg * (r["pA"] - r["pP"]))                       # the model's swing for the changing team (its margin)
    y.append(sg * (R.med_line(r["look"])[0] - r["close"]))   # the line's move toward that team, early -> close
x, y = np.array(x), np.array(y)
b = float(x @ y / (x @ x))
o.p(f"   {len(x)} with an early line: the model's QB swing for that team averages {x.mean():+.2f} pts (mean size {np.abs(x).mean():.2f}); "
    f"the line moved {y.mean():+.2f} toward it early -> close (mean size {np.abs(y).mean():.2f}); move = {b:+.2f} x swing, corr {np.corrcoef(x, y)[0, 1]:+.2f}")
for nm, cond in (("any change", lambda r, t: True),
                 ("the new starter is GREEN (<200 dropbacks)", lambda r, t: r["feat"]["green_" + t] == 1),
                 ("the new starter is a veteran", lambda r, t: r["feat"]["green_" + t] == 0),
                 ("model: the new QB is a DOWNGRADE of 1+ pts", lambda r, t: (r["pA"] - r["pP"]) * (1 if t == "h" else -1) <= -1),
                 ("model: the new QB is an UPGRADE of 1+ pts", lambda r, t: (r["pA"] - r["pP"]) * (1 if t == "h" else -1) >= 1)):
    back, backe = [], []
    for r in ch:
        t = "h" if r["feat"]["qbchg_h"] else "a"
        if not cond(r, t):
            continue
        sd = "home" if t == "h" else "away"
        back.append((r["season"], R.pay(r["margin"], r["close"], sd, S.dec(-110))))
        if r["look"]:
            bl, bd, _ = R.best_for(r["look"], sd)
            backe.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
    show(f"BACK the team with the new QB at the close - {nm}"[:52], back)
    show(f"  ... at the early best book - {nm}"[:52], backe)
o.p("   (fading it = the mirror image minus the juice: a back at -8% is a fade near +3%, a back at -2% is a fade at -7%)")
# the model on QB-change games at the close, the actual starter in the number
for lo in (0, 2, 3):
    b_ = []
    for r in recs:
        if r["qbchg"] == 0:
            continue
        e = r["pA"] + r["close"]
        if abs(e) >= lo and e != 0:
            b_.append((r["season"], R.pay(r["margin"], r["close"], "home" if e > 0 else "away", S.dec(-110))))
    show(f"the model's side at the close, a QB change, edge {lo}+", b_)

o.p("\n(2) A MARKET-AWARE NUMBER: predict the early line's MISS (walk-forward, first fit 2020-22, bets 2023-26)")
early = [r for r in recs if r["look"]]
NAMES = ["gap", "dPP", "dR", "dSP", "dSR", "dPts", "rest", "line"]


def vec(r):
    ml = R.med_line(r["look"])[0]
    f = r["feat"]
    return [r["pP"] + ml, f["dPP"], f["dR"], f["dSP"], f["dSR"], f["dPts"], f["rest"], ml]


pred = {}
for s in (2023, 2024, 2025, 2026):
    tr = [r for r in early if r["season"] < s]
    X = np.array([vec(r) for r in tr])
    yv = np.array([r["margin"] + R.med_line(r["look"])[0] for r in tr])
    sdv = X.std(axis=0)
    bw = S.ridge_w(X / sdv, yv, np.ones(len(yv)), 50.0) / sdv
    for r in early:
        if r["season"] == s:
            pred[r["id"]] = float(np.dot(vec(r), bw))
    o.p(f"   fit before {s} on {len(tr)} games: " + ", ".join(f"{n} {w * sd_:+.2f}" for n, w, sd_ in zip(NAMES, bw, sdv)) + "  (points of cover per 1 sd)")
HELD = {2023, 2024, 2025, 2026}
for lo in (0, 0.25, 0.5, 1.0):
    b_ = []
    for r in early:
        p = pred.get(r["id"])
        if p is None or abs(p) < lo or p == 0:
            continue
        sd = "home" if p > 0 else "away"
        bl, bd, _ = R.best_for(r["look"], sd)
        b_.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
    show(f"predicted miss {lo}+ pts, early best book", b_)
o.p(f"\ncells graded: {CELLS[0]}")
o.save()
