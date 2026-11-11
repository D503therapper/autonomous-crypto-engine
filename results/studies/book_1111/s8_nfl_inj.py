"""STUDY 8 - NFL INJURIES BY POSITION, WEIGHTED BY SNAPS (the input the 11/11 spread study named as the one a pro prices
and our number doesn't). nflverse's public files (fetch_nfl.py + the schedules release: plain downloads, no key):
  - injuries_<y>.csv: every player on each week's FINAL report (Out / Doubtful / Questionable), 2015-26
  - snap_counts_<y>.csv: every player's share of his team's offensive / defensive snaps, every game
  - games.csv: every game's result, closing moneylines and spread
THE MEASURE (fair - only what the Friday report and PAST games say): a player's ROLE = his average snap share over the
last 4 games he played this season (2+ games needed, so weeks 3+); a team's MISSING SNAPS in a position group = the sum
of the roles of its players listed Out / Doubtful this week (1.0 = one every-down starter). Plus the CARRIED absences an
injury report never lists (injured reserve): a regular (role 50%+) who did not play the team's last game and is not on
this week's report - checked below against whether he then played (a look-ahead used ONLY to say how good the proxy is).
THE TESTS: (1) does the missing-snaps gap move the result beyond the CLOSING moneyline (a logistic fit on top of the
no-vig close, train 2016-21, held out 2022-26); (2) bet the healthier side at the close - every group, three sizes of
gap; (3) does it improve a ratings-only read (Elo) - the engine's own NFL read's kind - and by how much next to the
market. Cells counted at the end.   Usage: python s8_nfl_inj.py > s8_nfl_inj.out"""
import csv
import math
import os
import re
from collections import defaultdict

import numpy as np

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_book1111", "dl")
OFF = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL"}
DEF = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB", "CB": "DB", "S": "DB",
       "SS": "DB", "FS": "DB", "DB": "DB"}
GROUPS = ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")
TEAM = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA", "WSH": "WAS", "JAC": "JAX", "GNB": "GB", "KAN": "KC", "NWE": "NE",
        "NOR": "NO", "SFO": "SF", "TAM": "TB", "LVR": "LV", "HST": "HOU", "BLT": "BAL", "CLV": "CLE", "ARZ": "ARI"}


def tm(t):
    return TEAM.get(t, t)


def nm(s):
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s.lower())
    return re.sub(r"[^a-z]", "", s)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


# ---------------------------------------------------------------- load
games = []
for r in csv.DictReader(open(os.path.join(DL, "games.csv"))):
    y = int(r["season"])
    if y < 2015 or r["game_type"] != "REG" or not r["home_score"] or not r["home_moneyline"] or not r["away_moneyline"]:
        continue
    hs, as_ = int(r["home_score"]), int(r["away_score"])
    dh, da = dec(r["home_moneyline"]), dec(r["away_moneyline"])
    games.append(dict(gid=r["game_id"], season=y, week=int(r["week"]), date=r["gameday"], home=tm(r["home_team"]), away=tm(r["away_team"]),
                      hs=hs, as_=as_, dh=dh, da=da, pm=(1 / dh) / (1 / dh + 1 / da), neutral=r["location"] != "Home",
                      hqb=r["home_qb_id"], aqb=r["away_qb_id"]))
games.sort(key=lambda g: (g["date"], g["gid"]))
print(f"regular-season games with a closing moneyline 2015-26: {len(games)}")

snaps = defaultdict(dict)        # (season, team) -> {week: {name: (group, share)}}
for y in range(2015, 2027):
    p = os.path.join(DL, f"snap_counts_{y}.csv")
    if not os.path.exists(p):
        continue
    for r in csv.DictReader(open(p)):
        if r["game_type"] != "REG":
            continue
        pos = r["position"]
        if pos in OFF:
            g, sh = OFF[pos], float(r["offense_pct"] or 0)
        elif pos in DEF:
            g, sh = DEF[pos], float(r["defense_pct"] or 0)
        else:
            continue
        snaps[(y, tm(r["team"]))].setdefault(int(r["week"]), {})[nm(r["player"])] = (g, sh)

inj = defaultdict(dict)          # (season, team, week) -> {name: status}
for y in range(2015, 2027):
    p = os.path.join(DL, f"injuries_{y}.csv")
    if not os.path.exists(p):
        continue
    for r in csv.DictReader(open(p)):
        if r["game_type"] != "REG":
            continue
        inj[(y, tm(r["team"]), int(r["week"]))][nm(r["full_name"])] = r["report_status"] or "listed"


def roles(season, team, week):
    """{name: (group, role, played the team's last game?)} from the team's games before `week` this season."""
    wk = sorted(w for w in snaps.get((season, team), {}) if w < week)
    if len(wk) < 2:
        return None
    seen = defaultdict(list)
    for w in wk:
        for n, (g, sh) in snaps[(season, team)][w].items():
            seen[n].append((w, g, sh))
    out = {}
    for n, v in seen.items():
        v = v[-4:]
        if len(v) < 2:
            continue
        out[n] = (v[-1][1], sum(x[2] for x in v) / len(v), v[-1][0] == wk[-1])
    return out


carried_n = carried_played = 0
listed_out_n = listed_out_played = 0
q_n = q_played = 0
rows = []
for g in games:
    if g["season"] < 2016:
        continue
    feat = {}
    ok = True
    for side, team in (("h", g["home"]), ("a", g["away"])):
        ro = roles(g["season"], team, g["week"])
        if ro is None:
            ok = False
            break
        rep = inj.get((g["season"], team, g["week"]), {})
        now = snaps.get((g["season"], team), {}).get(g["week"], {})      # (look-ahead - the proxy check only)
        miss = defaultdict(float)
        car = defaultdict(float)
        ques = defaultdict(float)
        for n, (grp, role, last) in ro.items():
            st = rep.get(n)
            if st in ("Out", "Doubtful"):
                miss[grp] += role
                listed_out_n += 1
                listed_out_played += n in now and now[n][1] > 0
            elif st == "Questionable":
                ques[grp] += role
                q_n += 1
                q_played += n in now and now[n][1] > 0
            elif st is None and not last and role >= 0.5:
                car[grp] += role
                carried_n += 1
                carried_played += n in now and now[n][1] > 0
        for grp in GROUPS:
            feat[side + grp] = miss[grp]
            feat[side + "c" + grp] = car[grp]
            feat[side + "q" + grp] = ques[grp]
    if not ok:
        continue
    r = dict(g)
    for grp in GROUPS:
        r["d" + grp] = feat["a" + grp] - feat["h" + grp]                # + = the AWAY team misses more (good for home)
        r["dc" + grp] = (feat["a" + grp] + feat["ac" + grp]) - (feat["h" + grp] + feat["hc" + grp])
        r["dq" + grp] = feat["aq" + grp] - feat["hq" + grp]
    r["hmiss"] = sum(feat["h" + x] for x in GROUPS if x != "QB")
    r["amiss"] = sum(feat["a" + x] for x in GROUPS if x != "QB")
    r["hmissc"] = r["hmiss"] + sum(feat["hc" + x] for x in GROUPS if x != "QB")
    r["amissc"] = r["amiss"] + sum(feat["ac" + x] for x in GROUPS if x != "QB")
    rows.append(r)
print(f"games with both teams' roles (weeks 3+), 2016-26: {len(rows)}")
print(f"THE PROXY CHECK: listed Out / Doubtful -> played anyway {listed_out_played}/{listed_out_n} ({100 * listed_out_played / listed_out_n:.1f}%); "
      f"Questionable -> played {q_played}/{q_n} ({100 * q_played / q_n:.1f}%); CARRIED (a 50%+ regular who missed the last game, not on the "
      f"report) -> played {carried_played}/{carried_n} ({100 * carried_played / max(1, carried_n):.1f}%)")
av = lambda k: sum(r[k] for r in rows) / len(rows)   # noqa: E731
print(f"average missing snaps a team (starters' worth, no QB): listed {av('hmiss'):.2f}, with the carried {av('hmissc'):.2f}")

TRAIN = lambda r: r["season"] <= 2021       # noqa: E731
N = [0]


def logit(p):
    return math.log(p / (1 - p))


def fit(X, y, off, lam=1.0, it=30):
    """Logistic with an offset (Newton), a small ridge."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    off = np.asarray(off, float)
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-(off + X @ b)))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + lam * np.eye(X.shape[1])
        b = b + np.linalg.solve(H, X.T @ (y - p) - lam * b)
    p = 1 / (1 + np.exp(-(off + X @ b)))
    W = p * (1 - p)
    cov = np.linalg.inv(X.T @ (X * W[:, None]) + lam * np.eye(X.shape[1]))
    return b, np.sqrt(np.diag(cov))


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


y_all = np.array([1.0 if r["hs"] > r["as_"] else 0.0 for r in rows])
tie = np.array([r["hs"] == r["as_"] for r in rows])
tr = np.array([TRAIN(r) for r in rows]) & ~tie
he = ~np.array([TRAIN(r) for r in rows]) & ~tie
off_mkt = np.array([logit(r["pm"]) for r in rows])

print("\n=== TEST 1: beyond the CLOSING moneyline (logistic on top of the no-vig close; + = the side whose OPPONENT misses more wins more than its price)")
for name, keys in (("each group, listed Out / Doubtful", ["d" + g for g in GROUPS]),
                   ("each group, listed + carried", ["dc" + g for g in GROUPS]),
                   ("each group, Questionable", ["dq" + g for g in GROUPS])):
    X = np.array([[r[k] for k in keys] for r in rows])
    b, se = fit(X[tr], y_all[tr], off_mkt[tr])
    bh, seh = fit(X[he], y_all[he], off_mkt[he])
    p_he = 1 / (1 + np.exp(-(off_mkt[he] + X[he] @ b)))
    print(f" {name}: held-out log loss, the close alone {ll(1 / (1 + np.exp(-off_mkt[he])), y_all[he]):.5f} -> the close + injuries (fit on train) {ll(p_he, y_all[he]):.5f}")
    for k, bb, s, bb2, s2 in zip(keys, b, se, bh, seh):
        print(f"    {k:6s} train {bb:+.3f} (z {bb / s:+.2f})   held {bb2:+.3f} (z {bb2 / s2:+.2f})")
        N[0] += 1
for name, k in (("ALL non-QB missing snaps (listed)", "tot"), ("ALL non-QB (listed + carried)", "totc")):
    x = np.array([[(r["amiss"] - r["hmiss"]) if k == "tot" else (r["amissc"] - r["hmissc"])] for r in rows])
    b, se = fit(x[tr], y_all[tr], off_mkt[tr])
    bh, seh = fit(x[he], y_all[he], off_mkt[he])
    print(f" {name}: train {b[0]:+.4f} (z {b[0] / se[0]:+.2f})   held {bh[0]:+.4f} (z {bh[0] / seh[0]:+.2f})  per starter's worth of snaps")
    N[0] += 1


def bet(name, pick):
    """pick(r) -> 'h' / 'a' / None; the moneyline at the close."""
    res = {"train": [], "held": []}
    seas = defaultdict(float)
    for r in rows:
        s = pick(r)
        if s is None or r["hs"] == r["as_"]:
            continue
        won = (r["hs"] > r["as_"]) == (s == "h")
        pr = ((r["dh"] if s == "h" else r["da"]) - 1) if won else -1.0
        res["train" if TRAIN(r) else "held"].append(pr)
        seas[r["season"]] += pr
    out = []
    for h in ("train", "held"):
        v = res[h]
        if v:
            m = sum(v) / len(v)
            sd_ = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
            out.append(f"{h} {100 * m:+6.1f}% on {len(v):4d} (z {m / (sd_ / math.sqrt(len(v))) if sd_ else 0:+.2f})")
        else:
            out.append(f"{h} none")
    up = sum(v > 0 for v in seas.values())
    print(f"  {name:66s} " + " | ".join(out) + f" | seasons up {up}/{len(seas)} | 2026 {seas.get(2026, 0):+.1f}u")
    N[0] += 1


print("\n=== TEST 2: BET THE HEALTHIER SIDE at the closing moneyline (the gap in missing snaps, starters' worth)")
for label, hk, ak in (("listed Out / Doubtful, non-QB", "hmiss", "amiss"), ("listed + carried, non-QB", "hmissc", "amissc")):
    for cut in (1.0, 2.0, 3.0):
        bet(f"{label}: healthier by {cut:g}+", lambda r, cut=cut, hk=hk, ak=ak: "h" if r[ak] - r[hk] >= cut else "a" if r[hk] - r[ak] >= cut else None)
        bet(f"   ...the healthier side is the DOG", lambda r, cut=cut, hk=hk, ak=ak: ("h" if r["dh"] > r["da"] else None) if r[ak] - r[hk] >= cut else ("a" if r["da"] > r["dh"] else None) if r[hk] - r[ak] >= cut else None)
        bet(f"   ...the healthier side is the FAVORITE to -150", lambda r, cut=cut, hk=hk, ak=ak: ("h" if 1.6667 <= r["dh"] < r["da"] else None) if r[ak] - r[hk] >= cut else ("a" if 1.6667 <= r["da"] < r["dh"] else None) if r[hk] - r[ak] >= cut else None)
for grp in ("OL", "WR", "DL", "LB", "DB", "RB", "TE"):
    for cut in (0.75, 1.5):
        bet(f"{grp}: the opponent misses {cut:g}+ more {grp} snaps (listed)", lambda r, grp=grp, cut=cut: "h" if r["d" + grp] >= cut else "a" if r["d" + grp] <= -cut else None)
bet("the offense: opponent misses 1.5+ more OL+WR+TE+RB", lambda r: "h" if sum(r["d" + g] for g in ("OL", "WR", "TE", "RB")) >= 1.5 else "a" if sum(r["d" + g] for g in ("OL", "WR", "TE", "RB")) <= -1.5 else None)
bet("the defense: opponent misses 1.5+ more DL+LB+DB", lambda r: "h" if sum(r["d" + g] for g in ("DL", "LB", "DB")) >= 1.5 else "a" if sum(r["d" + g] for g in ("DL", "LB", "DB")) <= -1.5 else None)
bet("FADE the banged-up FAVORITE to -150 (it misses 2+ more, listed + carried) = its dog", lambda r: ("a" if r["dh"] < r["da"] and r["dh"] >= 1.6667 else None) if r["hmissc"] - r["amissc"] >= 2 else ("h" if r["da"] < r["dh"] and r["da"] >= 1.6667 else None) if r["amissc"] - r["hmissc"] >= 2 else None)
bet("BACK the banged-up DOG +100..+350 (it misses 2+ more; the market over-marks it?)", lambda r: ("h" if r["dh"] > r["da"] and r["dh"] <= 4.5 else None) if r["hmissc"] - r["amissc"] >= 2 else ("a" if r["da"] > r["dh"] and r["da"] <= 4.5 else None) if r["amissc"] - r["hmissc"] >= 2 else None)

print("\n=== TEST 3: does it improve a RATINGS-ONLY read (Elo, K 20, home 48, walk-forward on every game 2015-26)?")
elo = defaultdict(lambda: 1500.0)
ep = {}
last_season = None
for g in games:
    if g["season"] != last_season:
        for t in list(elo):
            elo[t] = 1500 + 0.67 * (elo[t] - 1500)
        last_season = g["season"]
    d = elo[g["home"]] - elo[g["away"]] + (0 if g["neutral"] else 48)
    p = 1 / (1 + 10 ** (-d / 400))
    ep[g["gid"]] = p
    s = 1.0 if g["hs"] > g["as_"] else 0.0 if g["hs"] < g["as_"] else 0.5
    k = 20 * math.log(abs(g["hs"] - g["as_"]) + 1) * 2.2 / (2.2 + 0.001 * abs(d))
    elo[g["home"]] += k * (s - p)
    elo[g["away"]] -= k * (s - p)
off_elo = np.array([logit(min(0.97, max(0.03, ep[r["gid"]]))) for r in rows])
for name, keys in (("QB / RB / WR (what the engine weighs today)", ["dQB", "dRB", "dWR"]), ("every group, listed", ["d" + g for g in GROUPS]),
                   ("every group, listed + carried", ["dc" + g for g in GROUPS]), ("one number: all non-QB missing snaps + QB", ["dQB", "TOT"])):
    X = np.array([[(r["amissc"] - r["hmissc"]) if k == "TOT" else r[k] for k in keys] for r in rows])
    b, se = fit(X[tr], y_all[tr], off_elo[tr])
    p_he = 1 / (1 + np.exp(-(off_elo[he] + X[he] @ b)))
    print(f" Elo + {name}: held-out log loss {ll(1 / (1 + np.exp(-off_elo[he])), y_all[he]):.5f} -> {ll(p_he, y_all[he]):.5f}   (the closing line: {ll(1 / (1 + np.exp(-off_mkt[he])), y_all[he]):.5f})")
    print("    " + "  ".join(f"{k} {bb:+.3f} (z {bb / s:+.1f})" for k, bb, s in zip(keys, b, se)))
    # in win-chance points for one starter's worth at a coin flip
    print("    one starter's worth of snaps = " + "  ".join(f"{k} {100 * bb / 4:+.1f} pts" for k, bb in zip(keys, b)))
print(f"\n{N[0]} cells / coefficients printed; at |z| 2 about {N[0] * 0.05:.0f} would clear by luck")
