"""S8 - THE NBA, THE SAME WAY (short): opponent-adjusted points per possession, offence and defence apart, plus pace,
re-fit before EVERY game day on earlier games only (a weighted ridge, last season in at a fading discount), rest /
back-to-backs on top; stage 2 (the margin on the pieces) re-fit before each season. Team box 2021-26; test 2022-26
(2022-23 = the settings' seasons, 2024-26 held out). Graded at the close only (our NBA spread history stops in 2023
and holds no injuries by date - the one thing an NBA number most needs)."""
import math
from collections import defaultdict
from datetime import date
import numpy as np
import splib as S

B, L = S.B, S.L
o = S.Out("s8_nba")
tb = L.teambox("nba")
TAU, OFFD, LAM = 45.0, 30.0, 1500.0      # days; an off-season counts 30 days; ridge in possessions


def line(t):
    try:
        fg = L.pair(t["fieldGoalsMade-fieldGoalsAttempted"])
        ft = L.pair(t["freeThrowsMade-freeThrowsAttempted"])
        return fg[1] - float(t["offensiveRebounds"]) + float(t.get("totalTurnovers") or t["turnovers"]) + 0.44 * ft[1]
    except (KeyError, TypeError, ValueError):
        return None


gs = []
for g in B.all_finals("nba"):
    if g["season"] < 2021 or g["stype"] != "2" or g["id"] not in tb:
        continue
    ph, pa = line(tb[g["id"]].get(g["home"]) or {}), line(tb[g["id"]].get(g["away"]) or {})
    if not ph or not pa:
        continue
    gs.append(dict(g, poss=(ph + pa) / 2, d=date.fromisoformat(g["start"][:10]).toordinal()))
fin = {x["id"]: x for x in B.finals("nba")}
o.p("NBA regular-season games with a box 2021-26:", len(gs))
days = defaultdict(list)
for g in gs:
    days[g["d"]].append(g)
feat, done, last = {}, [], {}
for d in sorted(days):
    todays = days[d]
    season = todays[0]["season"]
    prior = [g for g in done if g["season"] >= season - 1]
    if len([g for g in prior if g["season"] == season]) >= 60 or (prior and season > 2021):
        teams = {}
        rows = []
        for g in prior:
            a = d - g["d"]
            if g["season"] != season:
                a = max(OFFD, a - 170 + OFFD)
            w = math.exp(-a / TAU) * g["poss"]
            hi, ai = teams.setdefault(g["home"], len(teams)), teams.setdefault(g["away"], len(teams))
            hf = 0.0 if g["neutral"] else 1.0
            rows.append((hi, ai, hf, g["hs"] / g["poss"], w))
            rows.append((ai, hi, -hf, g["as"] / g["poss"], w))
        nt = len(teams)
        X = np.zeros((len(rows), 2 * nt + 2))
        for i, r in enumerate(rows):
            X[i, r[0]] = 1
            X[i, nt + r[1]] = -1
            X[i, 2 * nt] = 1
            X[i, 2 * nt + 1] = r[2]
        b = S.ridge_w(X, [r[3] for r in rows], [r[4] for r in rows], LAM, free=(2 * nt, 2 * nt + 1))
        for g in todays:
            h, a = teams.get(g["home"]), teams.get(g["away"])
            if h is None or a is None:
                continue
            net = (b[h] - b[nt + a]) - (b[a] - b[nt + h])
            rst = [min(4, d - last[t]) if t in last else 3 for t in (g["home"], g["away"])]
            feat[g["id"]] = [net * 100, (1 if rst[0] == 1 else 0) - (1 if rst[1] == 1 else 0),
                             (1 if rst[0] >= 3 else 0) - (1 if rst[1] >= 3 else 0), 0.0 if g["neutral"] else 1.0]
    for g in todays:
        last[g["home"]] = last[g["away"]] = d
    done.extend(todays)
by = defaultdict(list)
for g in gs:
    if g["id"] in feat:
        by[g["season"]].append(g)
pred = {}
for s in sorted(by):
    tr = [g for y in by if y < s for g in by[y]]
    if len(tr) < 800:
        continue
    X = np.array([feat[g["id"]] for g in tr])
    bw = np.linalg.lstsq(X, np.array([g["hs"] - g["as"] for g in tr]), rcond=None)[0]
    for g in by[s]:
        pred[g["id"]] = float(np.dot(feat[g["id"]], bw))
    o.p(f"  stage 2 before {s}: net rating per 100 x {bw[0]:.2f}, back-to-back {bw[1]:+.2f}, 2+ days rest {bw[2]:+.2f}, home {bw[3]:+.2f}")
o.p("  season     n   | MAE model  close | RMSE model  close | weight on (model - close), se")
allb = defaultdict(list)
for s in sorted({g["season"] for g in gs if g["id"] in pred}):
    g2 = [g for g in gs if g["season"] == s and g["id"] in pred and g["id"] in fin and fin[g["id"]]["sp"] is not None]
    m = np.array([g["hs"] - g["as"] for g in g2])
    p = np.array([pred[g["id"]] for g in g2])
    c = np.array([-fin[g["id"]]["sp"] for g in g2])
    x = p - c
    b = float(x @ (m - c) / (x @ x))
    se = float(np.sqrt(((m - c - b * x) ** 2).sum() / (len(m) - 1) / (x @ x)))
    o.p("  %d  %5d | %6.2f  %6.2f | %6.2f  %6.2f | %+.3f  %.3f" % (s, len(m), np.abs(m - p).mean(), np.abs(m - c).mean(),
        np.sqrt(((m - p) ** 2).mean()), np.sqrt(((m - c) ** 2).mean()), b, se))
    for g, e in zip(g2, x):
        for lo in (0, 1.5, 2.5, 4, 6):
            if abs(e) >= lo and e != 0:
                r = (g["hs"] - g["as"]) + fin[g["id"]]["sp"]
                r = r if e > 0 else -r
                allb[lo].append((s, 0.0 if r == 0 else (100 / 110 if r > 0 else -1.0)))
o.p("  ATS at the close (-110), the model's side by edge:")
for lo in sorted(allb):
    bets = allb[lo]
    bys = defaultdict(list)
    for s, p in bets:
        bys[s].append(p)
    o.p(f"   edge {lo}+  ALL {S.line_stats([p for _, p in bets])} | HELD 2024-26 {S.line_stats([p for s, p in bets if s >= 2024])} | "
        + " ".join(f"{str(s)[2:]}:{sum(v) / len(v) * 100:+.0f}({len(v)})" for s, v in sorted(bys.items())))
o.save()
