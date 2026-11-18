"""S2 - THE KEY MAN WHO GOES DOWN AFTER THE EARLY NUMBER (the NFL - the only league with an injury history on file).
nflverse's weekly FINAL injury reports + snap counts (the 11/11 book study's files) against every early dog at the
pre-report look (Tuesday noon for a Sunday game - before Wednesday's first practice report).
A man's ROLE = his average share of his team's offensive / defensive snaps over the last 4 games he played this season
(2+ needed - weeks 3 on; what a scan can see). KEY MEN: the QUARTERBACK (role 50%+), a SKILL STARTER (RB / WR / TE,
role 50%+), any REGULAR (every group, role 50%+). NEWS = a man who PLAYED his team's last game and is on this week's
FINAL report Out / Doubtful (ruled out after our number) or Questionable. A man who already sat the last game is not
news - the number we took had it.
For each cell: how often, what the price did after our number (points of no-vig win %, + = to the dog), the bet at our
pre-report number, the same bet at the after-final-statuses number (what "wait for the news" pays) and at the close;
train 2020-22 / held out 2023-26; and whether anything a scan can SEE on Tuesday sorts the dogs the news then hits."""
import csv
import os
import re
from collections import defaultdict

import ilib
from ilib import E, base, pl

out = ilib.Tee("s2_keyman_out.txt")
DL = ilib.DL
ABBR = {"ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2", "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5", "DAL": "6",
        "DEN": "7", "DET": "8", "GB": "9", "HOU": "34", "IND": "11", "JAX": "30", "KC": "12", "LA": "14", "LAR": "14",
        "LAC": "24", "LV": "13", "OAK": "13", "MIA": "15", "MIN": "16", "NE": "17", "NO": "18", "NYG": "19", "NYJ": "20",
        "PHI": "21", "PIT": "23", "SEA": "26", "SF": "25", "TB": "27", "TEN": "10", "WAS": "28"}
OFF = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL"}
DEF = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB", "CB": "DB", "S": "DB",
       "SS": "DB", "FS": "DB", "DB": "DB"}
TEAM = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA", "WSH": "WAS", "JAC": "JAX", "GNB": "GB", "KAN": "KC", "NWE": "NE",
        "NOR": "NO", "SFO": "SF", "TAM": "TB", "LVR": "LV", "HST": "HOU", "BLT": "BAL", "CLV": "CLE", "ARZ": "ARI"}
tm = lambda t: TEAM.get(t, t)                                 # noqa: E731


def nm(s):
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s.lower())
    return re.sub(r"[^a-z]", "", s)


wk_of = {}                                                    # (ET game day, espn team id) -> (season, week, nflverse team)
for r in csv.DictReader(open(os.path.join(DL, "games.csv"))):
    if int(r["season"]) >= 2020 and r["game_type"] == "REG":
        for side in ("home", "away"):
            wk_of[(r["gameday"], ABBR.get(tm(r[f"{side}_team"])))] = (int(r["season"]), int(r["week"]), tm(r[f"{side}_team"]))
snaps = defaultdict(dict)                                     # (season, team) -> {week: {name: (group, share)}}
inj = defaultdict(dict)                                       # (season, team, week) -> {name: status}
for y in range(2020, 2027):
    p = os.path.join(DL, f"snap_counts_{y}.csv")
    if os.path.exists(p):
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
    p = os.path.join(DL, f"injuries_{y}.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            if r["game_type"] == "REG":
                inj[(y, tm(r["team"]), int(r["week"]))][nm(r["full_name"])] = r["report_status"] or "listed"


def roles(season, team, week):
    wk = sorted(w for w in snaps.get((season, team), {}) if w < week)
    if len(wk) < 2:
        return None, None
    seen = defaultdict(list)
    for w in wk:
        for n, (g, sh) in snaps[(season, team)][w].items():
            seen[n].append((w, g, sh))
    o = {}
    for n, v in seen.items():
        v = v[-4:]
        if len(v) >= 2:
            o[n] = (v[-1][1], sum(x[2] for x in v) / len(v), v[-1][0] == wk[-1])
    return o, wk[-1]


def side_news(season, team, week):
    """What the FINAL report did to this team's regulars who played last game (news), and what a scan could see on
    Tuesday (last week's report)."""
    ro, last_wk = roles(season, team, week)
    if ro is None:
        return None
    rep = inj.get((season, team, week), {})
    prev = inj.get((season, team, last_wk), {})
    now = snaps.get((season, team), {}).get(week, {})
    d = {"qb_out": 0, "qb_q": 0, "skill_out": 0, "skill_q": 0, "reg_out": 0, "reg_q": 0, "q_played": [], "seen_flag": 0,
         "carried": 0}
    for n, (grp, role, last) in ro.items():
        if role < 0.5:
            continue
        st = rep.get(n)
        if not last:                                          # he already sat the last game: the number had it
            d["carried"] += st in ("Out", "Doubtful") or n not in now
            continue
        key = "qb" if grp == "QB" else "skill" if grp in ("RB", "WR", "TE") else None
        if st in ("Out", "Doubtful"):
            d["reg_out"] += 1
            if key:
                d[key + "_out"] += 1
        elif st == "Questionable":
            d["reg_q"] += 1
            if key:
                d[key + "_q"] += 1
                d["q_played"].append(n in now and now[n][1] > 0)
        if key and prev.get(n) in ("Questionable", "Doubtful", "Out"):
            d["seen_flag"] += 1                               # a key man who played through last week's report
    return d


rows = []
for r in base.build("nfl"):
    ks = [k for k in r["looks"] if k[0] >= 1.5 and ilib.phase(r, k) == "pre"]
    if not ks or not 100 <= ks[0][2] <= 350:
        continue
    day = E.t(r["start"]).astimezone(E.ET).strftime("%Y-%m-%d")
    a, b = wk_of.get((day, r["team"])), wk_of.get((day, r["opp"]))
    if not a or not b:
        continue
    me, them = side_news(a[0], a[2], a[1]), side_news(b[0], b[2], b[1])
    if me is None or them is None:
        continue
    fin = next((k for k in r["looks"] if ilib.phase(r, k) == "final" and k[0] >= 0.5), None)
    rows.append({"r": r, "k": ks[0], "fin": fin, "me": me, "them": them, "bar": [h for h in ilib.live_bar(r, ks[0]) if h in ("bye", "mnf", "eastwest", "hammered")]})
out(f"S2 - NFL early dogs (+100..+350 at the pre-report look, weeks 3 on, both teams matched to the snap / report files): {len(rows)}")
out(f"   the spot dogs under the live bar among them: {sum(1 for x in rows if x['bar'])}")


def cell(name, v, pool=None):
    if len(v) < 8:
        out(f"  {name:62s} n {len(v)}")
        return
    mv = [(x["r"]["close_p"] - x["k"][3]) * 100 for x in v]
    f0 = lambda x: pl(x["r"], x["k"][2])                      # noqa: E731
    w = [x for x in v if x["fin"]]
    f1 = lambda x: pl(x["r"], x["fin"][2])                    # noqa: E731
    d = [f1(x) - f0(x) for x in w]
    out(f"  {name:62s} {len(v) / len(pool or rows) * 100:4.1f}% | the price after {E.mean(mv):+5.2f} pts (t {E.tstat(mv):+4.1f}; 3+ away "
        f"{sum(1 for q in mv if q <= -3) / len(mv) * 100:2.0f}%) | OUR number {ilib.halves(v, f0)}")
    out(f"  {'':62s}        waiting for the final statuses {E.roi([f1(x) for x in w])} = {E.mean(d) * 100:+.2f}% a bet (t {E.tstat(d):+.1f}) | "
        f"the close {E.mean(pl(x['r'], x['r']['close_o']) for x in v) * 100:+.1f}% | z vs our price {E.zwin([(x['r']['won'], x['k'][3]) for x in v]):+.2f}")


out("\n(a) NEWS ON OUR SIDE (the dog) after the number - men who played last game, on the FINAL report")
cell("every early dog", rows)
cell("QB ruled OUT / doubtful", [x for x in rows if x["me"]["qb_out"]])
cell("QB QUESTIONABLE", [x for x in rows if x["me"]["qb_q"] and not x["me"]["qb_out"]])
cell("QB on the final report at all (out / doubtful / questionable)", [x for x in rows if x["me"]["qb_q"] or x["me"]["qb_out"]])
cell("a skill starter (RB / WR / TE) OUT / doubtful", [x for x in rows if x["me"]["skill_out"]])
cell("a skill starter QUESTIONABLE (none out)", [x for x in rows if x["me"]["skill_q"] and not x["me"]["skill_out"]])
key_out = [x for x in rows if x["me"]["qb_out"] or x["me"]["skill_out"]]
key_q = [x for x in rows if not (x["me"]["qb_out"] or x["me"]["skill_out"]) and (x["me"]["qb_q"] or x["me"]["skill_q"])]
clean = [x for x in rows if not (x["me"]["qb_out"] or x["me"]["skill_out"] or x["me"]["qb_q"] or x["me"]["skill_q"])]
cell("KEY MAN (QB or skill starter) OUT / doubtful", key_out)
cell("KEY MAN questionable only", key_q)
cell("no key man on the final report", clean)
cell("any REGULAR out / doubtful: 1", [x for x in rows if x["me"]["reg_out"] == 1])
cell("any REGULAR out / doubtful: 2+", [x for x in rows if x["me"]["reg_out"] >= 2])
cell("no regular out / doubtful", [x for x in rows if x["me"]["reg_out"] == 0])
cell("MORE regulars newly out than the favorite", [x for x in rows if x["me"]["reg_out"] > x["them"]["reg_out"]])
cell("FEWER regulars newly out than the favorite", [x for x in rows if x["me"]["reg_out"] < x["them"]["reg_out"]])
qp = [p for x in rows for p in x["me"]["q_played"]]
out(f"  a questionable key man played: {sum(qp)} of {len(qp)} ({sum(qp) / max(1, len(qp)) * 100:.0f}%)")

out("\n(b) NEWS ON THE OTHER SIDE (the favorite)")
cell("the favorite's QB ruled OUT / doubtful", [x for x in rows if x["them"]["qb_out"]])
cell("the favorite's key man OUT / doubtful", [x for x in rows if x["them"]["qb_out"] or x["them"]["skill_out"]])

out("\n(c) THE SPOT DOGS UNDER THE LIVE BAR (what the early box really posts)")
bar = [x for x in rows if x["bar"]]
cell("every spot dog", bar, bar)
cell("KEY MAN out / doubtful after the number", [x for x in bar if x["me"]["qb_out"] or x["me"]["skill_out"]], bar)
cell("KEY MAN questionable only", [x for x in bar if not (x["me"]["qb_out"] or x["me"]["skill_out"]) and (x["me"]["qb_q"] or x["me"]["skill_q"])], bar)
cell("no key man on the final report", [x for x in bar if not (x["me"]["qb_out"] or x["me"]["skill_out"] or x["me"]["qb_q"] or x["me"]["skill_q"])], bar)
cell("any regular out / doubtful", [x for x in bar if x["me"]["reg_out"]], bar)
cell("no regular out / doubtful", [x for x in bar if not x["me"]["reg_out"]], bar)

out("\n(d) PLACEBO - is the key-man-out dogs' record at OUR number worse than a random set of early dogs?")
for name, v in (("key man out / doubtful", key_out), ("key man questionable only", key_q),
                ("QB out / doubtful", [x for x in rows if x["me"]["qb_out"]]),
                ("QB on the final report at all", [x for x in rows if x["me"]["qb_out"] or x["me"]["qb_q"]])):
    f0 = lambda x: pl(x["r"], x["k"][2])                      # noqa: E731
    tgt = E.mean(f0(x) for x in v)
    out(f"  {name}: {tgt * 100:+.1f}% on {len(v)}; a random {len(v)} early dogs did as badly {ilib.placebo(rows, len(v), tgt, f0)} of 2,000 times")

bk = [x for x in bar if x["me"]["qb_out"] or x["me"]["skill_out"]]
f0 = lambda x: pl(x["r"], x["k"][2])                          # noqa: E731
out(f"  the SPOT dogs with a key man out / doubtful: {E.mean(f0(x) for x in bk) * 100:+.1f}% on {len(bk)}; a random {len(bk)} of the "
    f"{len(bar)} spot dogs did as badly {ilib.placebo(bar, len(bk), E.mean(f0(x) for x in bk), f0)} of 2,000 times")

out("\n(e) CAN A SCAN SEE IT COMING ON TUESDAY? (flag = a key man who played last game THROUGH last week's report - "
    "questionable / doubtful then; or a regular already sitting)")
for name, sel in (("flag: a key man played through last week's report", lambda x: x["me"]["seen_flag"] > 0),
                  ("no flag", lambda x: x["me"]["seen_flag"] == 0),
                  ("a regular already sitting (carried)", lambda x: x["me"]["carried"] > 0),
                  ("nobody carried", lambda x: x["me"]["carried"] == 0)):
    v = [x for x in rows if sel(x)]
    hit = sum(1 for x in v if x["me"]["qb_out"] or x["me"]["skill_out"])
    out(f"  {name}: a key man then ruled out {hit} of {len(v)} ({hit / max(1, len(v)) * 100:.0f}%)")
    cell("   " + name, v)

out("\n(f) THE HOLD, AS IT WOULD RUN: hold every NFL early dog until the final statuses, then take it ONLY if no key man "
    "of ours is out / doubtful (at the after-final number, dog still +100..+350)")
for name, pool in (("every early dog", rows), ("the spot dogs", bar)):
    w = [x for x in pool if x["fin"]]
    now_ = [x for x in w]
    held = [x for x in w if not (x["me"]["qb_out"] or x["me"]["skill_out"]) and 100 <= x["fin"][2] <= 350]
    out(f"  {name}: today's timing (our number, every dog) {ilib.halves(now_, lambda x: pl(x['r'], x['k'][2]))}")
    out(f"  {name}: the hold (the later number, key-man-out dogs skipped) {ilib.halves(held, lambda x: pl(x['r'], x['fin'][2]))}")
    tot_now = sum(pl(x["r"], x["k"][2]) for x in now_)
    tot_held = sum(pl(x["r"], x["fin"][2]) for x in held)
    out(f"     flat 1u: today {tot_now:+.1f}u on {len(now_)} | the hold {tot_held:+.1f}u on {len(held)}")
    by = {}
    for x in now_:
        by.setdefault(x["r"]["season"], [0.0, 0.0])[0] += pl(x["r"], x["k"][2])
    for x in held:
        by.setdefault(x["r"]["season"], [0.0, 0.0])[1] += pl(x["r"], x["fin"][2])
    out("     by season (today / the hold): " + "  ".join(f"{s_} {a:+.1f}u / {b:+.1f}u" for s_, (a, b) in sorted(by.items())))
    import random
    rnd = random.Random(18)                                   # the same hold with the skipped dogs drawn at random
    skip_n = sum(1 for x in w if (x["me"]["qb_out"] or x["me"]["skill_out"]))
    as_good = 0
    for _ in range(2000):
        sk = set(rnd.sample(range(len(w)), skip_n))
        t_ = sum(pl(x["r"], x["fin"][2]) for i, x in enumerate(w) if i not in sk and 100 <= x["fin"][2] <= 350)
        as_good += t_ >= tot_held
    out(f"     placebo: the same hold skipping a RANDOM {skip_n} dogs made as much {as_good} of 2,000 times")
