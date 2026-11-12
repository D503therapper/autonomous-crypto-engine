"""Box-score facts stamped on lib.table rows, walk-forward (only games before tonight):
nba_stars(rows)   -> g[side]['star_out'] / ['two_out'] (the minutes leader / two of the top three by minutes so far this
                     season, 10+ team games, with no minutes tonight - the injury report's fact, known before the tip)
team_box(lg)      -> {gid: {team: stats}} from sports_roster.team_rows
nhl_shots(rows)   -> g[side]['sh'] / ['sv'] / ['sf'] / ['sa'] (season shooting %, save %, shots for / against a game, 10+)
ncaaf_plays(rows) -> g[side]['plays'] (offensive plays a game so far, 3+ box games) for nfl / ncaaf
"""
import json, os, sys
from collections import defaultdict

import lib as L

os.chdir(L.ROOT)
sys.path.insert(0, L.ROOT)
import sports_roster as R  # noqa: E402


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def nba_stars(rows, lg="nba"):
    mins = defaultdict(dict)
    for row in R.load(lg):
        try:
            m = _f(json.loads(row["stats"]).get("minutes"))
        except ValueError:
            m = 0.0
        mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m
    tot_m = defaultdict(lambda: defaultdict(float))
    gp = defaultdict(int)
    for g in rows:
        bx = mins.get(g["id"])
        for side, t in (("H", g["home"]), ("A", g["away"])):
            k = (g["season"], t)
            g[side]["star_out"] = g[side]["two_out"] = None
            g[side]["n_out"] = None
            if bx and t in bx and gp[k] >= 10:
                top = sorted(tot_m[k].items(), key=lambda kv: -kv[1])[:3]
                out = [pid for pid, _ in top if bx[t].get(pid, 0) <= 0]
                g[side]["star_out"] = top[0][0] in out
                g[side]["two_out"] = len(out) >= 2
                g[side]["n_out"] = len(out)
            if bx and t in bx:
                for pid, m in bx[t].items():
                    tot_m[k][pid] += m
                gp[k] += 1
    return rows


def team_box(lg):
    return {r["gid"]: r["teams"] for r in R.team_rows(lg)}


def nhl_shots(rows):
    tb = team_box("nhl")
    acc = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0])        # n, goals for, shots for, goals against, shots against
    for g in rows:
        b = tb.get(g["id"])
        for side, t in (("H", g["home"]), ("A", g["away"])):
            a = acc[(g["season"], t)]
            if a[0] >= 10 and a[2] and a[4]:
                g[side].update(sh=a[1] / a[2], sv=1 - a[3] / a[4], sf=a[2] / a[0], sa=a[4] / a[0], bxn=a[0])
        if b and g["home"] in b and g["away"] in b:
            sh, sa = _f(b[g["home"]].get("shotsTotal")), _f(b[g["away"]].get("shotsTotal"))
            if sh and sa:
                # regulation + overtime goals only (a shootout adds one to the winner's score)
                so = bool(g["lsh"]) and len(g["lsh"]) >= 5
                gh, ga = g["hs"], g["as"]
                if so:
                    if gh > ga:
                        gh -= 1
                    else:
                        ga -= 1
                for t, gf, sf, ga_, sa_ in ((g["home"], gh, sh, ga, sa), (g["away"], ga, sa, gh, sh)):
                    a = acc[(g["season"], t)]
                    a[0] += 1
                    a[1] += gf
                    a[2] += sf
                    a[3] += ga_
                    a[4] += sa_
    return rows


def plays(rows, lg):
    tb = team_box(lg)
    acc = defaultdict(lambda: [0, 0.0, 0.0])                  # n, own plays, opponent plays
    for g in rows:
        b = tb.get(g["id"])
        for side, t in (("H", g["home"]), ("A", g["away"])):
            a = acc[(g["season"], t)]
            if a[0] >= 3:
                g[side].update(plays=a[1] / a[0], oplays=a[2] / a[0], pbn=a[0])
        if b and g["home"] in b and g["away"] in b:
            def pl(x):
                if x.get("totalOffensivePlays"):
                    return _f(x["totalOffensivePlays"])
                ca = str(x.get("completionAttempts") or "0/0").replace("-", "/").split("/")
                return _f(x.get("rushingAttempts")) + (_f(ca[1]) if len(ca) > 1 else 0.0)
            ph, pa = pl(b[g["home"]]), pl(b[g["away"]])
            if ph and pa:
                for t, own, opp in ((g["home"], ph, pa), (g["away"], pa, ph)):
                    a = acc[(g["season"], t)]
                    a[0] += 1
                    a[1] += own
                    a[2] += opp
    return rows

# (the process stays in the repo root: sports_roster reads data/ relative to it)
