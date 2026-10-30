"""10/30 QUESTIONABLE PLAYERS (Ricky's ask) - STEP 1 (NBA): join every NBA official injury report listing to who
actually played.

SOURCES (both public, no keys):
  - the NBA's official injury report, every published version 2018-12-17 .. 2026-07 (sportsdataverse-data GitHub release
    'nba_stats_injury_report', injury_report_{2019..2026}.csv - a parse of the league's PDFs; nba.com itself is blocked
    from this session). Pass the folder holding the CSVs: python nba_build.py <dir>
  - our ESPN box scores (data/sports/roster/nba_*.csv.gz - a man in the box with minutes > 0 PLAYED) and our games /
    prices (data/sports/games/nba).

ONE ROW per (game, listed player) - written to nba_listings.csv.gz:
  morning  = his status on the last report version at or before 1:30 PM ET game day (what the engine sees at 8 AM PT,
             the 1:30 PM report is in every era) - '' when he was first listed later
  final    = his status on the last version before the game
  played   = in the box with minutes > 0; rows where we can't see him in the team's box scores at all that season (a
             G-Leaguer, a name we can't match, a long-term absence) are dropped - never counted as a sit
  key      = the engine's 10/28 key man (sports.nba_key_man): a top-3 scorer over the team's last 10 box scores or a
             starter in 3+ of them; top1 = the team's top scorer; reg = played 3+ of the last 10
  streak   = how many of the team's games right before this one he was also listed questionable (morning)
"""
import csv
import glob
import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import sports_absences as sa  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "src")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------- ESPN games: (ET date, nickname) -> game / side
games = {}
by_key = {}
for f in sorted(glob.glob(os.path.join(REPO, "data/sports/games/nba/*.csv"))):
    for r in csv.DictReader(open(f)):
        if r.get("stype") not in ("2", "3", "5") or r["status"] != "final":
            continue
        st = datetime.strptime(r["start"][:16], "%Y-%m-%dT%H:%M")
        d = (st - timedelta(hours=5)).date().isoformat()
        games[r["id"]] = r
        by_key[(d, r["home_name"])] = (r["id"], "home")
        by_key[(d, r["away_name"])] = (r["id"], "away")
NICK = sorted({k[1] for k in by_key}, key=len, reverse=True)

# ---------------------------------------------------------------- box scores
box = defaultdict(dict)            # gid -> team id -> {name: (minutes, points, starter)}
team_games = defaultdict(list)     # team id -> [(start, gid)]
for f in sorted(glob.glob(os.path.join(REPO, "data/sports/roster/nba_*.csv.gz"))):
    for r in csv.DictReader(gzip.open(f, "rt")):
        try:
            st = json.loads(r["stats"] or "{}")
        except ValueError:
            st = {}
        t = box[r["gid"]].setdefault(r["team"], {})
        if not t:
            team_games[r["team"]].append((r["start"], r["gid"]))
        t[sa._nm(r["player"])] = (num(st.get("minutes")), num(st.get("points")), r.get("starter") == "1")
for t in team_games:
    team_games[t].sort()
gidx = {(t, g): i for t, lst in team_games.items() for i, (_, g) in enumerate(lst)}


def season_pool(team, i):
    """Names who played for the team within 41 games either side - the 'we can see him' pool."""
    lst = team_games[team]
    pool = set()
    for _, g in lst[max(0, i - 41): i + 41]:
        pool |= {n for n, v in box[g][team].items() if v[0] > 0}
    return pool


def key_info(team, i):
    last = [g for _, g in team_games[team][max(0, i - 10): i]]
    pts, starts, played = defaultdict(float), defaultdict(int), defaultdict(int)
    for g in last:
        for n, (m, p, s) in box[g][team].items():
            if m > 0:
                pts[n] += p
                played[n] += 1
                starts[n] += s
    top = [n for n, _ in sorted(pts.items(), key=lambda x: -x[1])[:3]]
    return top, {n for n, k in starts.items() if k >= 3}, {n for n, k in played.items() if k >= 3}, len(last)


def flip(name):
    if "," in name:
        last, first = name.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return name


def reason_kind(reason):
    r = (reason or "").strip()
    head = r.split(" - ")[0].split(";")[0].strip()
    if head.lower().startswith("injury/illness"):
        body = r.split(" - ", 1)[1] if " - " in r else ""
        part, _, kind = body.partition(";")
        p = part.lower()
        if "illness" in p or "non-covid" in p:
            return "illness", "illness"
        for w in ("ankle", "knee", "hamstring", "calf", "back", "hip", "groin", "foot", "toe", "wrist", "hand",
                  "finger", "thumb", "shoulder", "elbow", "achilles", "quad", "thigh", "concussion", "head", "neck",
                  "rib", "abdom", "oblique", "eye", "nose", "face", "heel", "shin", "adductor", "lumbar", "pelvi"):
            if w in p:
                return "injury", w
        return "injury", "other"
    for k in ("rest", "injury management", "personal", "return to competition", "g league", "health and safety",
              "not with team", "suspension", "concussion"):
        if k in r.lower():
            return k, ""
    if head in ("-", ""):
        return "(none given)", ""
    # the 2018-19 era wrote the injury as free text ("Left ankle sprain")
    low = r.lower()
    if "illness" in low or "flu" in low:
        return "illness", "illness"
    if "rest" in low:
        return "rest", ""
    for w in ("ankle", "knee", "hamstring", "calf", "back", "hip", "groin", "foot", "toe", "wrist", "hand", "finger",
              "thumb", "shoulder", "elbow", "achilles", "quad", "thigh", "concussion", "neck", "rib", "eye", "heel"):
        if w in low:
            return "injury", w
    return "other", ""


# ---------------------------------------------------------------- the reports
listings = defaultdict(list)       # (date, team full, player) -> [(report_dt, status, reason, person_id)]
for f in sorted(glob.glob(os.path.join(SRC, "injury_report_*.csv"))):
    for r in csv.DictReader(open(f)):
        if not r["report_player_name"] or not r["current_status"]:
            continue
        listings[(r["game_date"], r["team"], r["report_player_name"])].append(
            (r["report_datetime"][:16], r["current_status"], r["reason"], r["person_id"], r["season"]))

out_rows = []
miss = defaultdict(int)
for (d, team_full, pname), vers in listings.items():
    nick = next((n for n in NICK if team_full.endswith(n)), None)
    hit = by_key.get((d, nick)) if nick else None
    if not hit:
        miss["no game"] += 1
        continue
    gid, side = hit
    g = games[gid]
    tid = g[side]
    if gid not in box or tid not in box[gid] or (tid, gid) not in gidx:
        miss["no box"] += 1
        continue
    vers.sort()
    cut = f"{d}T13:30"
    am = [v for v in vers if v[0] <= cut]
    morning = am[-1][1] if am else ""
    final = vers[-1][1]
    reason = (am[-1] if am else vers[-1])[2]
    name = sa._nm(flip(pname))
    i = gidx[(tid, gid)]
    pool = season_pool(tid, i)
    if not sa.match(name, pool):
        miss["never in the box"] += 1
        continue
    here = {n: v for n, v in box[gid][tid].items()}
    m = next((v for n, v in here.items() if n == name), None)
    if m is None:
        cand = [n for n in here if sa.match(name, {n})]
        m = here[cand[0]] if len(cand) == 1 else None
    played = bool(m and m[0] > 0)
    top, starters, regs, nlast = key_info(tid, i)
    key = sa.match(name, set(top)) or sa.match(name, starters)
    top1 = bool(top) and sa.match(name, {top[0]})
    reg = sa.match(name, regs)
    kind, part = reason_kind(reason)
    opp = "away" if side == "home" else "home"
    out_rows.append(dict(
        season=vers[-1][4], date=d, gid=gid, team=tid, team_name=g[side + "_name"], side=side, player=flip(pname),
        pid=vers[-1][3], morning=morning, final=final, first=vers[0][1], first_dt=vers[0][0], kind=kind, part=part,
        played=int(played), minutes=(m or (0,))[0], key=int(key), top1=int(top1), reg=int(reg), nlast=nlast,
        stype=g["stype"], ml=g["ml_" + side], ml_opp=g["ml_" + opp], ml_open=g.get("ml_" + side + "_open", ""),
        ml_opp_open=g.get("ml_" + opp + "_open", ""), won=int(num(g[side + "_score"]) > num(g[opp + "_score"]))))

# streak: the team's games right before this one with him listed questionable in the morning
q_by = defaultdict(set)
for r in out_rows:
    if r["morning"] == "Questionable":
        q_by[(r["team"], sa._nm(r["player"]))].add(gidx[(r["team"], r["gid"])])
for r in out_rows:
    s = q_by.get((r["team"], sa._nm(r["player"])), set())
    i, k = gidx[(r["team"], r["gid"])], 0
    while i - 1 - k in s:
        k += 1
    r["streak"] = k

out_rows.sort(key=lambda r: (r["date"], r["gid"], r["player"]))
with gzip.open(os.path.join(HERE, "nba_listings.csv.gz"), "wt", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)
print(len(out_rows), "rows;", dict(miss))
