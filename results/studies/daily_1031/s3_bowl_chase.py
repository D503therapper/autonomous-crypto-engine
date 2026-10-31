"""Study 3 (10/31): COLLEGE FOOTBALL - THE BOWL CHASE. Six wins makes a team bowl-eligible. Late in the season
(10/20 - 11/30, FBS vs FBS, regular season, 2020 left out - no eligibility rule that year):
  - the team sitting on 5 wins (one short), the one on 5 wins in its LAST regular-season game (now or never),
  - the team already ELIMINATED (can't reach 6 even winning out: wins + games left < 6),
  - the team already eligible (6+) facing one that needs it.
Wins count every finished game on file this season (FCS wins included - they count toward 6). Games left = the team's
later regular-season games on the schedule (the schedule is known before the season). A team with fewer games on
file than its weeks played (a hole in our feed) is left out (the never-false-info rule: we must see all its games).
Graded at the close (moneyline +100..+350 dogs / -101..-150 favorites, and ATS), and at the first FAIR early number
from the paid odds history. Train 2018-22 (no 2020), held out 2023 / 2024 / 2025 / 2026 apart."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import sports_players as spl  # noqa: E402

TRAIN, HELD = (2018, 2022), (2023, 2024, 2025, 2026)
games = lib.sd.load_games("ncaaf")
fin_all = [g for g in lib.sm.finals(games, "ncaaf") if (g.get("stype") or "2") == "2"]
sched = defaultdict(list)            # (season, team) -> [starts] every regular-season game on file (any status)
for g in games.values():
    if g.get("league") != "ncaaf" or (g.get("stype") or "2") != "2" or lib.sd.exhibition(g):
        continue
    s = lib.season(g["start"])
    for t in (g["home"], g["away"]):
        sched[(s, t)].append(g["start"])
for k in sched:
    sched[k].sort()
wins = defaultdict(list)             # (season, team) -> [(start, won)]
for g in sorted(fin_all, key=lambda x: x["start"]):
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (TypeError, ValueError):
        continue
    s = lib.season(g["start"])
    wins[(s, g["home"])].append((g["start"], hs > as_))
    wins[(s, g["away"])].append((g["start"], as_ > hs))

# first fair early number per game (paid odds history)
early = {}
for x in lib.load_football("ncaaf"):
    f = lib.first_fair(x["ml"])
    if f:
        early[x["id"]] = f[1]


def state(s, team, start):
    past = [w for st, w in wins[(s, team)] if st < start]
    left = sum(1 for st in sched[(s, team)] if st > start)
    # weeks since the team's first game (a hole = fewer games on file than weeks played, minus 2 byes)
    sch_before = [st for st in sched[(s, team)] if st < start]
    return sum(past), len(past) - sum(past), left, len(sch_before), len(past)


cells = defaultdict(list)


def add(k, s, p):
    cells[k].append((s, p))


n_games = 0
for g in lib.finals("ncaaf"):
    s = g["season"]
    if s == 2020:
        continue
    md = g["start"][5:10]
    if not ("10-20" <= md <= "11-30"):
        continue
    fbs = spl.fbs_set(games, g["start"])
    if fbs is None or g["home"] not in fbs or g["away"] not in fbs:
        continue
    st = {}
    ok = True
    for t in (g["home"], g["away"]):
        w, l, left, sch_b, fin_b = state(s, t, g["start"])
        if fin_b < sch_b:                          # a game before this one with no final on file - can't see all
            ok = False
        st[t] = (w, l, left)
    if not ok:
        continue
    n_games += 1
    for side, team, opp, o, won, home in lib.sides(g):
        w, l, left = st[team]
        ow, ol, oleft = st[opp]
        need1 = w == 5
        last = left == 0
        elim = w + left + 1 < 6                    # even winning tonight and out, short of 6
        elig = w >= 6
        opp_need1 = ow == 5
        opp_elim = ow + oleft + 1 < 6
        tags = []
        if need1:
            tags.append("needs 1 (5 wins)")
            if last:
                tags.append("needs 1, last regular-season game")
        if elim:
            tags.append("eliminated (can't reach 6)")
        if elig and opp_need1:
            tags.append("already eligible vs a team needing 1")
        if need1 and (ow >= 6 or opp_elim):
            tags.append("needs 1 vs a team with nothing to play for")
        if opp_elim and not elim:
            tags.append("vs an eliminated team")
        pr = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        e = early.get(g["id"])
        ep = None
        if e:
            hdec, adec, _ = lib.ml_med(e)
            d = hdec if home else adec
            if d > 1.0:
                eo = (d - 1) * 100 if d >= 2 else -100 / (d - 1)
                ep = (eo, lib.profit(won, d))
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else None
        for t in ["all"] + tags:
            if band:
                add(f"{band} | {t}", s, pr)
                if ep and ((band.startswith("dog") and 100 <= ep[0] <= 350) or (band.startswith("fav") and -150 <= ep[0] <= -101)):
                    add(f"{band} | {t} | FIRST FAIR price", s, ep[1])
            if a is not None:
                add(f"ATS | {t}", s, a)

res = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
lines = [f"COLLEGE FOOTBALL BOWL CHASE (10/20-11/30, FBS vs FBS, both teams' games all on file): {n_games} games"]
lines += [lib.fmt(k, v) for k, v in res.items()]
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, "s3_out.txt"), "w").write(txt + "\n")
json.dump(res, open(os.path.join(lib.OUT, "s3_out.json"), "w"), indent=1)
