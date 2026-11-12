"""11/12 DEEP PROGRAM - D3: THE NBA SPREAD WITH A ROSTER-BASED NUMBER (the owner's ask; the 11/12 run found the close
beats our team-level margin: 13.80 vs 13.32). Instead of rating TEAMS, rate the MEN and add up who plays tonight:
  a player's value = his box-score production per minute (Hollinger's game score: points, boards, assists, steals,
  blocks, misses, turnovers, fouls), an exponentially-weighted average over his earlier games (half-life 25 games),
  pulled to a replacement level until he has minutes; a team's number tonight = the sum over tonight's men of
  (the minutes we expect) x (his value), on a 240-minute night.
THREE WAYS TO KNOW WHO PLAYS (the leak ladder, named):
  KNOWN   the men who played the team's LAST game, at their usual minutes  (nothing from tonight - bettable any time)
  REPORT  the men who take the floor tonight, at their USUAL minutes       (the injury report's fact - known at the tip,
          and the close has it; the bet would have to wait for the report like the NBA over does)
  ORACLE  tonight's real minutes                                           (a look-ahead - the ceiling, never a bet)
The margin model: home margin ~ home edge + team Elo edge (sports_model's ratings, walk-forward) + the roster edge,
fit each season on the seasons before. Graded: the miss against the final margin vs the closing spread's miss, and the
side the number takes when it sits 2+ / 3+ / 4+ / 6+ points off the close, at the close's own juice.
TRAIN to 2021 / BLIND 2022 on. Usage: python results/studies/deep_1112/d3_nba_roster.py > results/studies/deep_1112/d3_nba_roster.out"""
import json, math, os, sys
from collections import defaultdict
import numpy as np
import dlib as D
import lib as L          # fifteen_1112

os.chdir(D.ROOT)
sys.path.insert(0, D.ROOT)
import sports_data as sd       # noqa: E402
import sports_model as sm      # noqa: E402
import sports_roster as R      # noqa: E402

HALF = 25.0
PRIOR_MIN = 150.0            # minutes of replacement-level play mixed into every man
DEC = 0.5 ** (1 / HALF)


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def pair(x):
    a = str(x or "0-0").split("-")
    return f(a[0]), (f(a[1]) if len(a) > 1 else 0.0)


def gmsc(st):
    fg, fga = pair(st.get("fieldGoalsMade-fieldGoalsAttempted"))
    ft, fta = pair(st.get("freeThrowsMade-freeThrowsAttempted"))
    return (f(st.get("points")) + 0.4 * fg - 0.7 * fga - 0.4 * (fta - ft) + 0.7 * f(st.get("offensiveRebounds"))
            + 0.3 * f(st.get("defensiveRebounds")) + f(st.get("steals")) + 0.7 * f(st.get("assists")) + 0.7 * f(st.get("blocks"))
            - 0.4 * f(st.get("fouls")) - f(st.get("turnovers")))


box = defaultdict(lambda: defaultdict(dict))
for r in R.load("nba"):
    try:
        st = json.loads(r["stats"])
    except ValueError:
        continue
    m = f(st.get("minutes"))
    if m > 0:
        box[r["gid"]][r["team"]][r["pid"]] = (m, gmsc(st), f(st.get("plusMinus")))
# the team Elo edge, walk-forward (today's reaction speed / home edge)
model = json.load(open("data/sports/model.json"))
p0 = model["params"]["nba"]
games = sd.load_games("nba")
_, erows = sm.replay(sm.finals(games, "nba"), p0["k"], p0["hfa"], "nba")
ELO = {g["id"]: fe["elo_raw"] for g, fe, _, _ in erows}
T = [g for g in L.table("nba") if g["id"] in ELO]
val = defaultdict(lambda: [0.0, 0.0])          # pid -> [weighted game score, weighted minutes]
umin = defaultdict(lambda: [0.0, 0.0])         # pid -> [weighted minutes, weight] (his usual minutes when he plays)
lastbox = {}                                   # team -> {pid: minutes} of its last game
REPL = [0.30]                                  # replacement-level game score a minute (running league mean x 0.6)
lg_sum = [0.0, 0.0]
rows = []
for g in T:
    b = box.get(g["id"])
    rec = {"g": g, "elo": ELO[g["id"]], "y": g["hs"] - g["as"], "season": g["season"]}
    ok = bool(b) and g["home"] in b and g["away"] in b

    def v(pid):
        a = val[pid]
        return (a[0] + PRIOR_MIN * REPL[0]) / (a[1] + PRIOR_MIN)

    def usual(pid):
        u = umin[pid]
        return u[0] / u[1] if u[1] > 0 else 12.0

    def team(pl):                              # {pid: minutes} -> the 240-minute number
        tot = sum(pl.values())
        return sum(m * v(pid) for pid, m in pl.items()) * (240.0 / tot) if tot > 0 else None
    if ok:
        for side, t in (("h", g["home"]), ("a", g["away"])):
            tonight = b[t]
            rec[side + "_oracle"] = team({pid: x[0] for pid, x in tonight.items()})
            rec[side + "_report"] = team({pid: usual(pid) for pid in tonight})
            lb = lastbox.get(t)
            rec[side + "_known"] = team({pid: usual(pid) for pid in lb}) if lb else None
            # the men missing tonight who played the last game, by value x usual minutes (what the report took away)
            rec[side + "_lost"] = sum(usual(pid) * (v(pid) - REPL[0]) for pid in (lb or {}) if pid not in tonight)
        rows.append(rec)
        for t in (g["home"], g["away"]):       # update AFTER the game
            for pid, (m, gs, pm) in b[t].items():
                a = val[pid]
                a[0], a[1] = a[0] * DEC + gs, a[1] * DEC + m
                u = umin[pid]
                u[0], u[1] = u[0] * 0.85 + m, u[1] * 0.85 + 1.0
                lg_sum[0] += gs
                lg_sum[1] += m
            lastbox[t] = {pid: x[0] for pid, x in b[t].items()}
        REPL[0] = 0.6 * lg_sum[0] / max(1.0, lg_sum[1])
print(f"NBA games with both box scores and ratings: {len(rows)} ({rows[0]['g']['start'][:10]} -> {rows[-1]['g']['start'][:10]})")
R2 = [r for r in rows if all(r.get(k) is not None for k in ("h_oracle", "a_oracle", "h_report", "a_report", "h_known", "a_known")) and r["g"]["A"]["n"] >= 5 and r["g"]["H"]["n"] >= 5]
MODELS = {"team Elo only": lambda r: [1.0, r["elo"] / 25],
          "Elo + roster KNOWN": lambda r: [1.0, r["elo"] / 25, r["h_known"] - r["a_known"]],
          "Elo + roster REPORT": lambda r: [1.0, r["elo"] / 25, r["h_report"] - r["a_report"]],
          "roster REPORT only": lambda r: [1.0, r["h_report"] - r["a_report"]],
          "Elo + KNOWN + who the report took away": lambda r: [1.0, r["elo"] / 25, r["h_known"] - r["a_known"], r["h_lost"] - r["a_lost"]],
          "Elo + roster ORACLE (look-ahead)": lambda r: [1.0, r["elo"] / 25, r["h_oracle"] - r["a_oracle"]]}
seasons = sorted({r["season"] for r in R2})
pred = {k: {} for k in MODELS}
for k, fx in MODELS.items():
    for s in seasons:
        tr = [r for r in R2 if r["season"] < s]
        te = [r for r in R2 if r["season"] == s]
        if len(tr) < 1500:
            continue
        X = np.array([fx(r) for r in tr])
        y = np.array([r["y"] for r in tr])
        w = np.linalg.solve(X.T @ X + 1e-3 * np.eye(X.shape[1]), X.T @ y)
        for r in te:
            pred[k][r["g"]["id"]] = float(np.array(fx(r)) @ w)
        if s == seasons[-1]:
            print(f"   {k:42s} weights (last fit): " + " ".join(f"{x:+.3f}" for x in w))
E = [r for r in R2 if r["g"]["sp"] is not None and r["g"]["id"] in pred["team Elo only"] and r["season"] >= 2018]
print(f"graded: {len(E)} games with a closing spread, seasons {min(r['season'] for r in E)}-{max(r['season'] for r in E)}")
print("\n1. THE MISS (mean absolute error against the final margin)")
cl = np.array([abs(r["y"] + r["g"]["sp"]) for r in E])
print(f"   {'the closing spread':42s} {cl.mean():.3f}")
for k in MODELS:
    e = np.array([abs(r["y"] - pred[k][r["g"]["id"]]) for r in E])
    d = e - cl
    D.CELLS[0] += 1
    # does the number add anything to the close? margin ~ -spread + b * (number + spread)
    x = np.array([pred[k][r["g"]["id"]] + r["g"]["sp"] for r in E])
    resid = np.array([r["y"] + r["g"]["sp"] for r in E])
    bcoef = float((x @ resid) / (x @ x))
    se = float(np.sqrt(((resid - bcoef * x) ** 2).sum() / (len(x) - 1) / (x @ x)))
    print(f"   {k:42s} {e.mean():.3f} ({d.mean():+.3f} vs the close, z {d.mean() / (d.std() / math.sqrt(len(d))):+.1f}) | what it adds to the close: b {bcoef:+.3f} (se {se:.3f}, z {bcoef / se:+.1f})")
print("\n2. ITS SIDE WHEN IT SITS OFF THE CLOSE (the close's own juice; train to 2021 / blind 2022 on)")
for k in MODELS:
    print(f" -- {k}")
    for lo, hi in ((2, 3), (3, 4), (4, 6), (6, 99), (3, 99)):
        bets = []
        for r in E:
            diff = pred[k][r["g"]["id"]] + r["g"]["sp"]             # > 0: our number likes the home side more than the close
            if lo <= abs(diff) < hi:
                bets.append((r["season"], L.ats(r["g"], "H" if diff > 0 else "A")))
        L.cell(f"   {lo}-{hi if hi < 99 else '+'} off the close", bets)
print("\n3. THE NEWS ITSELF: the report took real value away from one team tonight (men who played the last game and sit; value x minutes over replacement)")
for lo in (3.0, 6.0, 10.0):
    for nm, side_of in (("the short-handed side ATS", lambda s: s), ("the side ACROSS ATS", lambda s: L.other(s))):
        bets = []
        for r in E:
            dl = r["h_lost"] - r["a_lost"]
            if abs(dl) >= lo and min(r["h_lost"], r["a_lost"]) < 1.0:
                short = "H" if dl > 0 else "A"
                bets.append((r["season"], L.ats(r["g"], side_of(short))))
        L.cell(f"   lost {lo:g}+ of value: {nm}", bets)
L.done()
