"""10/28 THE HOT 3-POINT NIGHT, part 2 - the PLAYER level (the owner's brother): the main shooters' trends and splits
(home / road, b2b / rested, hot / cold streaks - does a hot shooter stay hot?), experience (our data holds NO ages or
draft years - the proxy is a player's first season in our box scores, 2016-17 on, so it is censored: a 2016 veteran reads
as "9 seasons seen" in 2025, a true rookie reads right), the opponent's rotation experience (minutes-weighted), and the
coaches (tenure with the team and career seasons from data/sports/coach_history.json). Defender-vs-shooter matchups are
NOT in box scores - not measured. Everything pre-tip; then the team model from study.py gets the player-built
expectation added and is judged again on the held-out seasons and at the price. Run from the repo root after build.py."""
import json
import math
import os
import pickle
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(__file__))
import sports_data as sd      # noqa: E402
import sports_roster as sr    # noqa: E402
from build import season_of, t_, pair   # noqa: E402

HERE = os.path.dirname(__file__)
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
HOLD = [2024, 2025, 2026]


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def corr(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x) / n)
    sy = math.sqrt(sum((b - my) ** 2 for b in y) / n)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / n / (sx * sy) if sx and sy else 0.0


games = sd.load_games("nba")
rows = sr.load("nba")
fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
              and g.get("home_score") not in (None, "")), key=lambda g: g["start"])
gmeta = {g["id"]: g for g in fin}
# per game per team: players [(pid, tpm, tpa, min, starter)]
box = defaultdict(lambda: defaultdict(list))
for r in rows:
    g = gmeta.get(r["gid"])
    if not g:
        continue
    try:
        st = json.loads(r["stats"])
        m = float(st.get("minutes") or 0)
    except (ValueError, TypeError):
        continue
    if m <= 0:
        continue
    tpm, tpa = pair(st, "threePointFieldGoalsMade-threePointFieldGoalsAttempted")
    if tpm is None:
        continue
    box[r["gid"]][r["team"]].append((r["pid"], tpm, tpa, m, r.get("starter") == "1"))

# ---------------------------------------------------------------- coaches: tenure with the team, career seasons
ch = json.load(open("data/sports/coach_history.json")).get("nba", {})
name_of = {}
for g in fin:
    name_of[g["home"]] = g["home_name"]
    name_of[g["away"]] = g["away_name"]
full = {}
for tid, short in name_of.items():
    for fn in ch:
        if fn.endswith(short) or (short == "Clippers" and "Clippers" in fn):
            full[tid] = fn


def coach_facts(tid, season):
    """(tenure seasons with this team incl. this one, career seasons as a head coach in the file) - the file's year key
    y = the season that ENDS in y (2026 = 2025-26), so season 2025 -> key '2026'."""
    fn = full.get(tid)
    if not fn:
        return None, None
    key = str(season + 1)
    cs = ch[fn].get(key)
    if not cs:
        return None, None
    c = cs[-1]                                              # the coach who finished the season (the usual one)
    ten = 0
    y = season + 1
    while str(y) in ch[fn] and c in ch[fn][str(y)]:
        ten += 1
        y -= 1
    career = sum(1 for t in ch for yy in ch[t] if int(yy) <= season + 1 and c in ch[t][yy])
    return ten, career


# ---------------------------------------------------------------- walk the games: player histories
first_season = {}                                           # pid -> first season seen in our box scores (2016 on)
ph = defaultdict(list)                                      # (pid, season) -> [(start, tpm, tpa, min, home, rest)]
pall = defaultdict(list)                                    # pid -> all games (for home / road, b2b splits before today)
th = defaultdict(list)                                      # (team, season) -> [(start, gid, tpm_team)]
tlast = {}                                                  # team -> last game start
team_rows = {}                                              # (gid, team) -> features
streak_rows = []                                            # the hot-shooter persistence test
exp_rows = []                                               # consistency by experience
split_rows = []                                             # home/road, b2b splits (prior career vs tonight)
for g in fin:
    s = season_of(g["start"])
    bx = box.get(g["id"])
    if not bx or len(bx) < 2:
        continue
    now = t_(g["start"])
    lg_pct = 0.36
    for tid in (g["home"], g["away"]):
        if tid not in bx:
            continue
        opp = g["away"] if tid == g["home"] else g["home"]
        home = tid == g["home"]
        rest = (now - tlast[tid]).days if tid in tlast else 3
        b2b = rest <= 1
        # the team's rotation so far this season: expected attempts and regressed % per man from his season to date +
        # his prior seasons as the prior
        mine = th[(tid, s)]
        # who is the rotation? the men who played in the team's last game (knowable), weighted by their last-5 minutes
        last = mine[-1] if mine else None
        pl_exp = pl_exp_split = pl_exp_hot = 0.0
        shooter_exp_years = []
        top3 = []
        n_rot = 0
        if last:
            lp = box[last[1]][tid]
            # season-to-date makes per man -> the top-3 shooters
            made = defaultdict(int)
            for st_, gid_, _ in mine:
                for pid, tpm, tpa, m, stt in box[gid_][tid]:
                    made[pid] += tpm
            top3 = [p for p, _ in sorted(made.items(), key=lambda kv: -kv[1])[:3]]
            for pid, _, _, m_last, _ in lp:
                hs = ph[(pid, s)]
                allp = pall[pid]
                tpa_s = sum(x[2] for x in hs)
                tpm_s = sum(x[1] for x in hs)
                mins = sum(x[3] for x in hs) or 1
                # prior seasons as the prior for the %
                pm = sum(x[1] for x in allp if x[0] < f"{s}-09")
                pa = sum(x[2] for x in allp if x[0] < f"{s}-09")
                REG = 100.0
                pct = (tpm_s + pm * 0.5 + lg_pct * REG) / (tpa_s + pa * 0.5 + REG)
                att_per_min = (tpa_s + pa * 0.3) / (mins + sum(x[3] for x in allp if x[0] < f"{s}-09") * 0.3) if hs or pa else 0.0
                exp_min = (sum(x[3] for x in hs[-5:]) / len(hs[-5:])) if hs else m_last
                e = exp_min * att_per_min * pct
                pl_exp += e
                # the split version: his own home/road and b2b/rested 3P% before tonight (regressed to his own pct)
                sp = [x for x in allp if x[4] == home]
                spa = sum(x[2] for x in sp)
                spm = sum(x[1] for x in sp)
                pct_h = (spm + pct * 150) / (spa + 150)
                sb = [x for x in allp if x[5] == b2b]
                sba = sum(x[2] for x in sb)
                sbm = sum(x[1] for x in sb)
                pct_b = (sbm + pct * 150) / (sba + 150)
                pl_exp_split += exp_min * att_per_min * (pct_h + pct_b - pct)
                # the hot-hand version: his last 3 games' % blended in (if he's hot, more)
                l3 = hs[-3:]
                l3a = sum(x[2] for x in l3)
                l3m = sum(x[1] for x in l3)
                pct_hot = (l3m + pct * 30) / (l3a + 30) if l3a else pct
                pl_exp_hot += exp_min * att_per_min * pct_hot
                if pid in top3:
                    shooter_exp_years.append(s - first_season.get(pid, s))
                n_rot += 1
        # the opponent's rotation experience (minutes-weighted seasons seen), from ITS last game
        omine = th[(opp, s)]
        opp_exp = None
        if omine:
            lp = box[omine[-1][1]][opp]
            tm = sum(p[3] for p in lp) or 1
            opp_exp = sum(p[3] * (s - first_season.get(p[0], s)) for p in lp) / tm
        ten, car = coach_facts(tid, s)
        oten, ocar = coach_facts(opp, s)
        actual = sum(p[1] for p in bx[tid])
        team_rows[(g["id"], tid)] = dict(pl_exp=pl_exp if last else None, pl_exp_split=pl_exp_split if last else None,
                                         pl_exp_hot=pl_exp_hot if last else None, n_rot=n_rot,
                                         shooter_exp=(sum(shooter_exp_years) / len(shooter_exp_years)) if shooter_exp_years else None,
                                         opp_exp=opp_exp, coach_ten=ten, coach_car=car, ocoach_ten=oten, ocoach_car=ocar,
                                         actual=actual, g=len(mine))
        # player-level tests (only shooters with 3+ attempts a game so far, 10+ games)
        for pid, tpm, tpa, m, stt in bx[tid]:
            hs = ph[(pid, s)]
            if len(hs) >= 10:
                sa = sum(x[2] for x in hs)
                sm = sum(x[1] for x in hs)
                if sa >= 3 * len(hs):
                    spct = sm / sa
                    l3 = hs[-3:]
                    l3a = sum(x[2] for x in l3)
                    l3m = sum(x[1] for x in l3)
                    if l3a >= 9:
                        streak_rows.append((s, l3m / l3a - spct, tpm, tpa, spct, s - first_season.get(pid, s)))
                    # splits: his home/road % before tonight vs tonight
                    allp = [x for x in pall[pid] if x[0] < g["start"]]
                    hr = [x for x in allp if x[4] == home]
                    nr = [x for x in allp if x[4] != home]
                    if sum(x[2] for x in hr) >= 60 and sum(x[2] for x in nr) >= 60:
                        split_rows.append(("home/road", s, sum(x[1] for x in hr) / sum(x[2] for x in hr) - sum(x[1] for x in nr) / sum(x[2] for x in nr), tpm, tpa, spct))
                    bb = [x for x in allp if x[5] == b2b]
                    nb = [x for x in allp if x[5] != b2b]
                    if sum(x[2] for x in bb) >= 60 and sum(x[2] for x in nb) >= 60:
                        split_rows.append(("b2b/rested", s, sum(x[1] for x in bb) / sum(x[2] for x in bb) - sum(x[1] for x in nb) / sum(x[2] for x in nb), tpm, tpa, spct))
                    exp_rows.append((s, s - first_season.get(pid, s), tpm / tpa - spct if tpa else None, tpa))
    # update
    for tid in (g["home"], g["away"]):
        if tid not in bx:
            continue
        home = tid == g["home"]
        rest = (now - tlast[tid]).days if tid in tlast else 3
        for pid, tpm, tpa, m, stt in bx[tid]:
            first_season.setdefault(pid, s)
            ph[(pid, s)].append((g["start"], tpm, tpa, m, home, rest <= 1))
            pall[pid].append((g["start"], tpm, tpa, m, home, rest <= 1))
        th[(tid, s)].append((g["start"], g["id"], sum(p[1] for p in bx[tid])))
    for tid in (g["home"], g["away"]):
        tlast[tid] = now

# ---------------------------------------------------------------- 1. the shooters
print("=== PLAYER LEVEL (3+ attempts a game, 10+ games this season) ===")
print("1. DOES A HOT SHOOTER STAY HOT? his last-3-games 3P% vs his season %, then what he shot TONIGHT (vs his season %)")
for lab, S in (("train", TRAIN), ("holdout", set(HOLD))):
    print(f"  {lab}:")
    for bl, lo, hi in (("ice cold (-15 or worse)", -1, -0.15), ("cold (-15..-5)", -0.15, -0.05), ("normal", -0.05, 0.05), ("hot (+5..+15)", 0.05, 0.15), ("on fire (+15 or more)", 0.15, 1)):
        r = [x for x in streak_rows if x[0] in S and lo <= x[1] < hi]
        a = sum(x[3] for x in r)
        m = sum(x[2] for x in r)
        exp = sum(x[4] * x[3] for x in r)
        if a:
            print(f"    {bl:26s} n {len(r):6d} games - tonight {m / a * 100:5.1f}% on {a / len(r):.1f} attempts vs his season {exp / a * 100:5.1f}% -> {(m - exp) / a * 100:+.1f} pts")
print("   (a hot streak means NOTHING for tonight if every row is near +0; a persistent hot hand would read + on the hot rows)")
print("2. HIS OWN SPLITS - the man's past home/road or b2b/rested gap (60+ attempts each side), and tonight vs his season %:")
for kind in ("home/road", "b2b/rested"):
    for lab, S in (("train", TRAIN), ("holdout", set(HOLD))):
        r = [x for x in split_rows if x[0] == kind and x[1] in S]
        xs = [x[2] for x in r]
        ys = [(x[3] / x[4] - x[5]) if x[4] else 0 for x in r]
        big = [x for x in r if abs(x[2]) >= 0.05]
        ba = sum(x[4] for x in big)
        bm = sum(x[3] for x in big)
        bexp = sum(x[5] * x[4] for x in big)
        bsign = sum((x[3] - x[5] * x[4]) * (1 if x[2] > 0 else -1) for x in big) / ba * 100 if ba else 0
        print(f"   {kind:11s} {lab:8s} n {len(r):6d}: corr(past gap, tonight) {corr(xs, ys):+.3f}; men with a 5+ pt gap on this side n {len(big)} shot {bsign:+.1f} pts in the gap's direction")
print("3. EXPERIENCE (seasons seen in our box scores since 2016-17 - censored, no ages in our data) and night-to-night consistency:")
for lab, S in (("train", TRAIN), ("holdout", set(HOLD))):
    print(f"  {lab}:")
    for bl, lo, hi in (("0 (first season seen)", 0, 0), ("1-2", 1, 2), ("3-5", 3, 5), ("6-9", 6, 9)):
        r = [x for x in exp_rows if x[0] in S and lo <= x[1] <= hi and x[2] is not None and x[3] >= 3]
        if len(r) > 50:
            sdv = math.sqrt(sum(x[2] ** 2 for x in r) / len(r))
            mean = sum(x[2] for x in r) / len(r)
            print(f"    {bl:22s} n {len(r):6d} nights - sd of (tonight's % - his season %) {sdv * 100:.1f} pts, mean {mean * 100:+.1f}, attempts {sum(x[3] for x in r) / len(r):.1f}")
print("   (in 2018 nobody can read over 2 seasons seen; by 2024-26 the proxy runs to 8-9 - compare within a slice)")
# hot-hand by experience
print("   the hot streak by experience (holdout): on-fire men (+15 last 3) tonight vs season -")
for bl, lo, hi in (("0-2", 0, 2), ("3+", 3, 99)):
    r = [x for x in streak_rows if x[0] in set(HOLD) and x[1] >= 0.15 and lo <= x[5] <= hi]
    a = sum(x[3] for x in r)
    if a:
        print(f"     {bl:4s} n {len(r)} {(sum(x[2] for x in r) - sum(x[4] * x[3] for x in r)) / a * 100:+.1f} pts")

# ---------------------------------------------------------------- 4. team level: does any of it add to the model?
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
HOME = [d for d in sides if d["home"]]
import study_lib as sl   # noqa: E402

print("\n=== 4. TEAM LEVEL: the player-built expectation, the opponent's experience and the coaches, added to the model ===")
rows_m = []
for d in HOME:
    f = sl.feats(d)
    tm, to = team_rows.get((d["gid"], d["team"])), team_rows.get((d["gid"], d["opp"]))
    if not f or not tm or not to or tm["pl_exp"] is None or to["pl_exp"] is None or tm["g"] < 5 or to["g"] < 5:
        continue
    extra = {"player-built expected 3PM (plain)": tm["pl_exp"] - to["pl_exp"],
             "player-built, with his home/road + b2b splits": tm["pl_exp_split"] - to["pl_exp_split"],
             "player-built, with his hot hand (last 3)": tm["pl_exp_hot"] - to["pl_exp_hot"],
             "top-3 shooters' experience (seasons seen)": (tm["shooter_exp"] or 0) - (to["shooter_exp"] or 0),
             "opponent rotation experience (min-weighted)": (to["opp_exp"] or 0) - (tm["opp_exp"] or 0),
             "coach tenure with the team": (tm["coach_ten"] or 0) - (to["coach_ten"] or 0),
             "coach career seasons": (tm["coach_car"] or 0) - (to["coach_car"] or 0)}
    rows_m.append((d, f[0], extra))
y_tr = [r[0]["tpm"] - r[0]["o_tpm"] for r in rows_m if r[0]["season"] in TRAIN]
print(f"  n {len(rows_m)} games with every input (both teams 5+ games); one at a time, correlation with the actual 3PM margin (train):")
base_tr = [r for r in rows_m if r[0]["season"] in TRAIN]
beta0 = sl.ols([r[1] for r in base_tr], y_tr)
resid = [(r[0]["tpm"] - r[0]["o_tpm"]) - sl.predict(beta0, r[1]) for r in base_tr]
for k in rows_m[0][2]:
    xs = [r[2][k] for r in base_tr]
    print(f"    {k:48s} raw {corr(xs, y_tr):+.3f}   vs what the team model misses (residual) {corr(xs, resid):+.3f}")
# the opponent's defensive experience and coach on the team's 3P% specifically (the brother's defensive-IQ idea)
print("  the brother's defense idea, straight: the team's 3P% tonight (minus its season %) vs the opponent's rotation experience / coach tenure (train):")
xs1, xs2, xs3, ys = [], [], [], []
for d in sides:
    tm, to = team_rows.get((d["gid"], d["team"])), team_rows.get((d["gid"], d["opp"]))
    if d["season"] in TRAIN and tm and to and d["s_pct"] is not None and to["opp_exp"] is not None and d["tpa"] and d["g"] >= 5:
        xs1.append(tm["opp_exp"])                                # (opp_exp stored on OUR row = the OPPONENT's rotation experience)
        xs2.append(to["coach_ten"] or 0)
        xs3.append(to["coach_car"] or 0)
        ys.append(d["tpm"] / d["tpa"] - d["s_pct"])
print(f"    n {len(ys)}: opponent rotation experience {corr(xs1, ys):+.3f}, opponent coach tenure {corr(xs2, ys):+.3f}, opponent coach career {corr(xs3, ys):+.3f}")
# refit with the extras, judged held out
print("  the model refit WITH the player / experience / coach inputs (train 2018-23), judged held out:")
keys = list(rows_m[0][2].keys())
X = [r[1] + [r[2][k] for k in keys] for r in rows_m]
beta1 = sl.ols([x for x, r in zip(X, rows_m) if r[0]["season"] in TRAIN], y_tr)
pred1 = {}
for lab, S in (("train", TRAIN), ("2024-25", {2024}), ("2025-26", {2025}), ("2026-27", {2026})):
    rs = [(x, r) for x, r in zip(X, rows_m) if r[0]["season"] in S]
    if not rs:
        continue
    y = [r[0]["tpm"] - r[0]["o_tpm"] for _, r in rs]
    p0 = [sl.predict(beta0, r[1]) for _, r in rs]
    p1 = [sl.predict(beta1, x) for x, _ in rs]
    right0 = sum(1 for a, b in zip(p0, y) if b and (a > 0) == (b > 0)) / max(1, sum(1 for b in y if b))
    right1 = sum(1 for a, b in zip(p1, y) if b and (a > 0) == (b > 0)) / max(1, sum(1 for b in y if b))
    print(f"    {lab:8s} n {len(rs):5d}  team-only model R² {sl.r2(p0, y):.3f} (leader right {right0 * 100:.1f}%)  ->  with players/coaches R² {sl.r2(p1, y):.3f} (leader right {right1 * 100:.1f}%)")
    for x, r in rs:
        pred1[r[0]["gid"]] = sl.predict(beta1, x)
print("    added coefficients: " + "; ".join(f"{k} {b:+.3f}" for k, b in zip(keys, beta1[len(rows_m[0][1]):])))
# at the price
print("  AT THE PRICE (closing moneyline, flat 1u) with the fuller model:")
sl.pred = pred1
sl.cell("dogs +100..+350, predicted edge 1.5+ threes", sl.ml_pick(1.5, (100, 350)), HOME)
sl.cell("dogs +100..+350, predicted edge 2.5+ threes", sl.ml_pick(2.5, (100, 350)), HOME)
sl.cell("favorites -101..-150, predicted edge 1.5+ threes", sl.ml_pick(1.5, (-150, -101)), HOME)
sl.cell("favorites -101..-150, predicted edge 2.5+ threes", sl.ml_pick(2.5, (-150, -101)), HOME)
sl.cell("any price, predicted edge 2.5+ threes", sl.ml_pick(2.5, (-100000, 100000)), HOME)
sl.cell("predicted edge 2.5+ threes, ATS", sl.ats_pick(2.5), HOME)
print("  IS IT IN THE PRICE? win % vs the no-vig implied by predicted-edge bucket (fuller model, both sides):")
for lab, S in (("train", TRAIN), ("holdout 2024-26", set(HOLD))):
    out = []
    for bl, lo, hi in (("-4-", -99, -4), ("-4..-2", -4, -2), ("-2..0", -2, 0), ("0..2", 0, 2), ("2..4", 2, 4), ("4+", 4, 99)):
        n = w = e = 0
        for d in sides:
            p = pred1.get(d["gid"])
            if p is None or d["season"] not in S:
                continue
            p = p if d["home"] else -p
            if lo <= p < hi:
                n += 1
                w += 1 if d["won"] else 0
                e += d["nv"]
        if n:
            out.append(f"{bl} n {n} won {w / n * 100:.1f} vs {e / n * 100:.1f} ({(w - e) / n * 100:+.1f})")
    print(f"    {lab}: " + " | ".join(out))
# the hot-hand / split team expectations straight at the price, as their own second checks
for k, nm in (("player-built, with his hot hand (last 3)", "hot-hand player expectation alone"), ("player-built, with his home/road + b2b splits", "splits player expectation alone")):
    sl.pred = {r[0]["gid"]: r[2][k] for r in rows_m}
    sl.cell(f"{nm}: dogs, edge 2.5+", sl.ml_pick(2.5, (100, 350)), HOME)
    sl.cell(f"{nm}: favs -101..-150, edge 2.5+", sl.ml_pick(2.5, (-150, -101)), HOME)
print(f"\n  cells at the price in part 4: {sl.CELLS}")
