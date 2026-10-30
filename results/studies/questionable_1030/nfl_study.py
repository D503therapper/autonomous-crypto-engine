"""10/30 QUESTIONABLE PLAYERS - the NFL. The game status on the final (Friday) injury report (data/sports/injuries/
nfl.csv.gz, nflverse) joined to who actually took a snap (nflverse snap counts, snap_counts_{2020..2026}.csv - public
GitHub release, no key; pass the folder: python nfl_study.py <dir>). Regular season only.
A listed man counts only if he took snaps for the team in 2+ of its 3 games before (a regular - his sitting means
something); a STARTER = 60%+ of the offense or defense snaps on average in the games he played of those 3; the QB =
the team's main QB (most offense snaps at QB) in its last game. Market: the ESPN closing moneyline (data/sports/games/nfl),
the starter's team, played vs sat."""
import csv
import glob
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "src")
NICK = {"ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears",
        "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
        "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs", "LA": "Rams", "LAC": "Chargers",
        "LV": "Raiders", "MIA": "Dolphins", "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
        "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks", "SF": "49ers", "TB": "Buccaneers",
        "TEN": "Titans", "WAS": "Commanders"}
OLD = {"Commanders": ("Washington", "Redskins")}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


snaps = defaultdict(dict)          # (season, team, week) -> {player: (pos, off_pct, def_pct, total snaps)}
gid_of = {}
for fn in sorted(glob.glob(os.path.join(SRC, "snap_counts_*.csv"))):
    for r in csv.DictReader(open(fn)):
        if r["game_type"] != "REG":
            continue
        k = (int(r["season"]), r["team"], int(r["week"]))
        snaps[k][r["player"]] = (r["position"], f(r["offense_pct"]), f(r["defense_pct"]),
                                 f(r["offense_snaps"]) + f(r["defense_snaps"]) + f(r["st_snaps"]))
        gid_of[k] = (r["game_id"], r["opponent"])
weeks = defaultdict(list)
for (s, t, w) in snaps:
    weeks[(s, t)].append(w)
for k in weeks:
    weeks[k].sort()

# ESPN prices: (season, frozenset(nicknames)) -> games in date order
espn = defaultdict(list)
for fn in sorted(glob.glob(os.path.join(REPO, "data/sports/games/nfl/*.csv"))):
    for g in csv.DictReader(open(fn)):
        if g["stype"] != "2" or g["status"] != "final":
            continue
        y, m = int(g["start"][:4]), int(g["start"][5:7])
        season = y if m >= 7 else y - 1
        espn[(season, frozenset((g["home_name"], g["away_name"])))].append(g)
for k in espn:
    espn[k].sort(key=lambda g: g["start"])


def nick_set(abbr):
    return (NICK[abbr],) + OLD.get(NICK[abbr], ())


def espn_game(season, team, opp, week):
    """The ESPN game for this nflverse team-week (two meetings a season: by order)."""
    for a in nick_set(team):
        for b in nick_set(opp):
            lst = espn.get((season, frozenset((a, b))))
            if lst:
                meet = sorted(w for w in weeks[(season, team)] if gid_of[(season, team, w)][1] == opp)
                i = meet.index(week) if week in meet else 0
                if i < len(lst):
                    return lst[i], a
    return None, None


rows = []
inj = list(csv.DictReader(gzip.open(os.path.join(REPO, "data/sports/injuries/nfl.csv.gz"), "rt")))
listed_q = defaultdict(set)
for r in inj:
    if r["game_type"] == "REG" and r["report_status"] == "Questionable":
        listed_q[(int(r["season"]), r["team"], r["full_name"])].add(int(r["week"]))
for r in inj:
    if r["game_type"] != "REG" or r["report_status"] not in ("Questionable", "Doubtful", "Out"):
        continue
    s, t, w, name = int(r["season"]), r["team"], int(r["week"]), r["full_name"]
    if (s, t, w) not in snaps:
        continue                                    # a bye / a week we don't hold
    prev = [x for x in weeks[(s, t)] if x < w][-3:]
    if len(prev) < 2:
        continue
    seen = [snaps[(s, t, x)].get(name) for x in prev]
    on = [x for x in seen if x and x[3] > 0]
    if len(on) < 2:
        continue                                    # not a regular: his sitting tells us nothing
    pos = r["position"]
    pct = sum(max(x[1], x[2]) for x in on) / len(on)
    last = snaps[(s, t, prev[-1])]
    qb_main = max((p for p, v in last.items() if v[0] == "QB"), key=lambda p: last[p][1], default=None)
    me = snaps[(s, t, w)].get(name)
    k, streak = w, 0
    pw = [x for x in weeks[(s, t)] if x < w]
    while pw and pw[-1] in listed_q[(s, t, name)]:
        streak += 1
        pw.pop()
    rows.append(dict(season=s, week=w, team=t, player=name, pos=pos, status=r["report_status"],
                     practice=r["practice_status"], played=int(bool(me and me[3] > 0)), starter=int(pct >= 0.6),
                     qb=int(name == qb_main), streak=streak, gweek=(s, t, w)))
print(len(rows), "regular-season listings of regulars")


def rate(v):
    return f"{sum(x['played'] for x in v) / len(v) * 100:5.1f}% of {len(v):5d}" if v else "   -  of     0"


def by_season(v):
    d = defaultdict(list)
    for x in v:
        d[x["season"]].append(x)
    return " ".join(f"{y % 100}:{sum(x['played'] for x in vv) / len(vv) * 100:.0f}" for y, vv in sorted(d.items()))


print("\n1. PLAY RATE BY THE FINAL REPORT'S STATUS")
for st in ("Questionable", "Doubtful", "Out"):
    v = [x for x in rows if x["status"] == st]
    print(f"   {st:13s} all {rate(v)} | starters {rate([x for x in v if x['starter']])} | the QB {rate([x for x in v if x['qb']])}"
          f" | by season {by_season(v)}")
Q = [x for x in rows if x["status"] == "Questionable"]
print("\n2. QUESTIONABLE - BY POSITION (starters)")
grp = {"QB": ("QB",), "RB": ("RB", "FB"), "WR": ("WR",), "TE": ("TE",), "OL": ("T", "G", "C", "OL", "OT", "OG"),
       "DL": ("DE", "DT", "NT", "DL"), "LB": ("LB", "ILB", "OLB", "MLB"), "DB": ("CB", "S", "FS", "SS", "DB"), "K/P": ("K", "P", "LS")}
for gname, ps in grp.items():
    v = [x for x in Q if x["pos"] in ps]
    print(f"   {gname:4s} all {rate(v)}  starters {rate([x for x in v if x['starter']])}")
print("\n3. QUESTIONABLE - BY FRIDAY'S PRACTICE")
for p in ("Full Participation in Practice", "Limited Participation in Practice", "Did Not Participate In Practice"):
    v = [x for x in Q if x["practice"] == p]
    print(f"   {p:36s} all {rate(v)}  starters {rate([x for x in v if x['starter']])}")
print("\n4. QUESTIONABLE - WEEKS IN A ROW LISTED QUESTIONABLE BEFORE")
for lo, hi, lab in ((0, 0, "first week"), (1, 1, "2nd week"), (2, 3, "3rd-4th"), (4, 99, "5th+")):
    v = [x for x in Q if lo <= x["streak"] <= hi]
    print(f"   {lab:10s} all {rate(v)}  starters {rate([x for x in v if x['starter']])}")

print("\n5. PER-PLAYER HISTORY (prior questionable weeks, strictly before) - starters, 2024-26 vs 2020-23")
hist = defaultdict(lambda: [0, 0])
for x in sorted(Q, key=lambda x: (x["season"], x["week"])):
    h = hist[x["player"]]
    x["n"], x["p"] = h
    h[0] += 1
    h[1] += x["played"]
for lab, fn in (("no history", lambda x: x["n"] == 0), ("5+ prior, 85%+", lambda x: x["n"] >= 5 and x["p"] / x["n"] >= .85),
                ("5+ prior, under 60%", lambda x: x["n"] >= 5 and x["p"] / x["n"] < .6)):
    for nm, yrs in (("2020-23", range(2020, 2024)), ("2024-26", range(2024, 2027))):
        v = [x for x in Q if x["starter"] and x["season"] in yrs and fn(x)]
        print(f"   {lab:22s} {nm} {rate(v)}")
tot = defaultdict(lambda: [0, 0])
for x in Q:
    tot[x["player"]][0] += 1
    tot[x["player"]][1] += x["played"]
print("   most-listed questionable regulars 2020-26:")
for nm, (n, p) in sorted(tot.items(), key=lambda kv: -kv[1][0])[:15]:
    print(f"     {nm:24s} {p}/{n} = {p / n * 100:.0f}%")

print("\n6. THE MARKET - a STARTER questionable (his team's side, ESPN closing moneyline)")


def dec(ml):
    ml = float(ml)
    return 1 + (ml / 100 if ml > 0 else 100 / -ml)


tg = defaultdict(list)
for x in Q:
    if x["starter"]:
        tg[x["gweek"]].append(x)
res = []
for (s, t, w), v in tg.items():
    gid, opp = gid_of[(s, t, w)]
    g, nk = espn_game(s, t, opp, w)
    if not g or not g["ml_home"] or not g["ml_away"]:
        continue
    side = "home" if g["home_name"] == nk else "away"
    o = "away" if side == "home" else "home"
    pa, pb = 1 / dec(g["ml_" + side]), 1 / dec(g["ml_" + o])
    won = f(g[side + "_score"]) > f(g[o + "_score"])
    res.append(dict(nv=pa / (pa + pb), won=int(won), pnl=(dec(g["ml_" + side]) - 1) if won else -1.0,
                    sat=int(any(not x["played"] for x in v)), qb=int(any(x["qb"] for x in v)),
                    mv=(pa / (pa + pb) - (1 / dec(g["ml_" + side + "_open"])) / (1 / dec(g["ml_" + side + "_open"]) + 1 / dec(g["ml_" + o + "_open"])))
                    if g.get("ml_" + side + "_open") and g.get("ml_" + o + "_open") else None))


def mk(v, lab):
    if not v:
        return
    n = len(v)
    mv = [x["mv"] for x in v if x["mv"] is not None]
    print(f"   {lab:30s} n={n:4d} won {sum(x['won'] for x in v) / n * 100:5.1f}% vs close {sum(x['nv'] for x in v) / n * 100:5.1f}%"
          f"  ROI at close {sum(x['pnl'] for x in v) / n * 100:+6.1f}%" + (f"  open->close {sum(mv) / len(mv) * 100:+.2f} pts (n {len(mv)})" if mv else ""))


mk(res, "a starter questionable")
mk([x for x in res if not x["sat"]], "  ...every one played")
mk([x for x in res if x["sat"]], "  ...one sat")
mk([x for x in res if x["qb"]], "the QB questionable")
mk([x for x in res if x["qb"] and not x["sat"]], "  ...he played")
mk([x for x in res if x["qb"] and x["sat"]], "  ...he sat")
