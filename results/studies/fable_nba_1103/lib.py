"""11/3 FABLE: NBA DEEP DIVE - one side table for every angle (nothing from after tip-off). Read-only on the repo;
caches live in the scratch cache (STUDY_CACHE or ~/.cache/d503_studies), never in the repo.

Rows = every NBA regular-season side with a closing moneyline (2018-19 .. 2026-27), team-oriented. For each side:
the prices (close, ESPN's open 2023+, the paid 2020-23 game-day MORNING look), the schedule (rest, back-to-backs,
4-in-6, road-trip game, the trip's last game, the first home game after a trip, the tip hour / weekday in the venue's
clock, the next game), the last game (margin, overtime, points), box-score style over the last 10 games (pace,
offensive rebounding, turnovers, threes), the roster (player values = plus-minus a minute from the box scores so far,
last season as a prior; the rotation = the top 10 by minutes over the last 10 games; who is OUT on the 1:30 PM ET
official report - results/studies/questionable_1030/nba_listings.csv.gz; the minutes-weighted strength with and
without them; role men vs key men out; a rotation man back tonight after missing 3+), the standings (conference rank,
games left, play-in zone, tanking), and the team's market record (last season's and this season's win % minus the
no-vig price, walk-forward).

TRAIN = 2018-2022 (five seasons), HELD OUT = 2023 / 2024 / 2025 apart, NOW = 2026 (92 games when built)."""
import csv
import gzip
import importlib.util
import json
import math
import os
import pickle
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd      # noqa: E402
import sports_roster as sr    # noqa: E402
from sports_absences import _nm   # noqa: E402  (the report's names vs the box score's - different id systems)

_spec = importlib.util.spec_from_file_location("d1102", os.path.join(ROOT, "results/studies/daily_1102/lib.py"))
d1102 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d1102)
os.chdir(ROOT)
d1102.OUT = OUT                      # (its Cells.dump writes next to THIS study's scripts, never into daily_1102/)
summ, fmt, stats, Cells, dec, profit = d1102.summ, d1102.fmt, d1102.stats, d1102.Cells, d1102.dec, d1102.profit
TRAIN, HELD = (2018, 2022), (2023, 2024, 2025)
TABLE = os.path.join(CACHE, "fable_nba_1103_sides.pkl")
LISTINGS = os.path.join(ROOT, "results/studies/questionable_1030/nba_listings.csv.gz")

EAST = {"Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks",
        "Hornets", "Heat", "Magic", "Wizards"}
K, HOME, REGRESS = 20.0, 70.0, 0.33
PRIOR_MIN = 400.0        # a player's plus-minus a minute is shrunk to the replacement rate by 400 minutes of evidence
ROT_N = 10               # the rotation: the top 10 by minutes over the team's last 10 games


def t_(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 9 else y - 1


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _box_rows():
    """{gid: {team: [player dicts]}} from every saved NBA box score (minutes > 0)."""
    cache = os.path.join(CACHE, "fable_nba_1103_box.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    box = defaultdict(lambda: defaultdict(list))
    for r in sr.load("nba"):
        try:
            st = json.loads(r["stats"] or "{}")
            m = float(st.get("minutes") or 0)
        except (ValueError, TypeError):
            continue
        if m <= 0:
            continue

        def pair(k):
            v = st.get(k) or ""
            if "-" in v:
                a, b = v.split("-")
                return _int(a), _int(b)
            return None, None
        fgm, fga = pair("fieldGoalsMade-fieldGoalsAttempted")
        tpm, tpa = pair("threePointFieldGoalsMade-threePointFieldGoalsAttempted")
        ftm, fta = pair("freeThrowsMade-freeThrowsAttempted")
        pm = st.get("plusMinus")
        box[r["gid"]][r["team"]].append({
            "pid": r["pid"], "name": r["player"], "min": m, "pts": num(st.get("points")) or 0.0,
            "pm": num(str(pm).replace("+", "")) if pm not in (None, "") else None,
            "fga": fga, "fgm": fgm, "tpa": tpa, "tpm": tpm, "fta": fta, "oreb": _int(st.get("offensiveRebounds")),
            "dreb": _int(st.get("defensiveRebounds")), "reb": _int(st.get("rebounds")), "to": _int(st.get("turnovers")),
            "starter": str(r.get("starter")) == "1"})
    box = {k: dict(v) for k, v in box.items()}
    pickle.dump(box, open(cache, "wb"))
    return box


def _listings():
    """{(gid, team id): [row dicts]} of the official report (the 1:30 PM ET 'morning' status)."""
    out = defaultdict(list)
    with gzip.open(LISTINGS, "rt") as f:
        for r in csv.DictReader(f):
            out[(r["gid"], r["team"])].append(r)
    return out


def _local(g):
    """(local tip hour, local weekday 0=Mon, ET hour) from the venue's UTC offset in the game row."""
    t = t_(g["start"])
    tzo = num(g.get("tzo"))
    if tzo is None:
        tzo = -5.0
    loc = t + timedelta(hours=tzo)
    m = t.month
    et = t + timedelta(hours=-5 if m in (11, 12, 1, 2) or (m == 3 and t.day < 10) else -4)
    return loc.hour + loc.minute / 60, loc.weekday(), et.hour + et.minute / 60


def _pt_day(start):
    return (t_(start) - timedelta(hours=8)).strftime("%Y-%m-%d")


def build():
    if os.path.exists(TABLE):
        return pickle.load(open(TABLE, "rb"))
    games = sd.load_games("nba")
    box = _box_rows()
    lst = _listings()
    morning = d1102.nba_morning()
    fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")
                  and g.get("home_name") not in ("EAST", "WEST", "USA") and not str(g.get("home_name", "")).startswith("Team")),
                 key=lambda g: (g["start"], g["id"]))
    sched = defaultdict(list)
    for g in fin:
        sched[g["home"]].append(g)
        sched[g["away"]].append(g)
    idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
    conf = {}
    for g in fin:
        conf[g["home"]] = "E" if g["home_name"] in EAST else "W"
        conf[g["away"]] = "E" if g["away_name"] in EAST else "W"
    elo = defaultdict(lambda: 1500.0)
    seen_season = {}
    hist = defaultdict(list)          # (team, season) -> [dict(start, opp, margin, won, home, gid, ot, pts, opts)]
    pval = {}                         # pid -> [pm sum, minutes sum] this season (rolling)
    pval_last = {}                    # (season) -> {pid: (pm sum, minutes)} frozen at season end
    cur_season = None
    resid = defaultdict(list)         # (team, season) -> [won - nv] (priced games)
    rest_hist = defaultdict(lambda: [0, 0, 0, 0])   # (team, season) -> [b2b nights listed, with a rest-out, other, with]
    sides = []
    for g in fin:
        s = season_of(g["start"])
        if s != cur_season:
            if cur_season is not None:
                pval_last[cur_season] = {k: tuple(v) for k, v in pval.items()}
            pval = {}
            cur_season = s
        h, a = g["home"], g["away"]
        for t in (h, a):
            if seen_season.get(t) != s:
                elo[t] = 1500 + (elo[t] - 1500) * (1 - REGRESS)
                seen_season[t] = s
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        mh, ma = _int(g.get("ml_home")), _int(g.get("ml_away"))
        sp, tot = num(g.get("spread_home")), num(g.get("total"))
        oh, oa = _int(g.get("ml_home_open")), _int(g.get("ml_away_open"))
        lh = str(g.get("ls_home") or "").split(",")
        ot_now = len([x for x in lh if x.strip() != ""]) > 4
        loc_h, wd, et_h = _local(g)
        now = t_(g["start"])
        day = _pt_day(g["start"])
        prev_last = pval_last.get(s - 1, {})
        pre = {}
        for side, oth in (("home", "away"), ("away", "home")):
            t, o = g[side], g[oth]
            hh, ho = hist[(t, s)], hist[(o, s)]
            d = {"team": t, "opp": o, "home": side == "home", "elo": elo[t], "opp_elo": elo[o], "conf": conf[t],
                 "g": len(hh), "wp": (sum(x["won"] for x in hh) / len(hh)) if hh else None,
                 "wins": sum(x["won"] for x in hh)}
            last = hh[-1] if hh else None
            d["rest"] = (now - t_(last["start"])).days if last else None
            d["b2b"] = d["rest"] == 1
            d["last_margin"] = last["margin"] if last else None
            d["last_ot"] = last["ot"] if last else None
            d["last_pts"] = last["pts"] if last else None
            d["last_home"] = last["home"] if last else None
            d["win_streak"] = 0
            for x in reversed(hh):
                if x["won"]:
                    d["win_streak"] += 1
                else:
                    break
            d["in4"] = sum(1 for x in hh if (now - t_(x["start"])).days < 4) + 1
            d["in6"] = sum(1 for x in hh if (now - t_(x["start"])).days < 6) + 1
            d["in8"] = sum(1 for x in hh if (now - t_(x["start"])).days < 8) + 1
            # road trip / homestand (consecutive games of the same kind including tonight, this season)
            run = 0
            for x in reversed(hh):
                if x["home"] == (side == "home"):
                    run += 1
                else:
                    break
            d["trip_game"] = run + 1 if side == "away" else 0
            d["stand_game"] = run + 1 if side == "home" else 0
            prev_run = 0
            for x in reversed(hh):
                if x["home"] != (side == "home"):
                    prev_run += 1
                else:
                    break
            d["home_after_trip"] = prev_run if side == "home" and hh and not hh[-1]["home"] else 0
            d["away_after_stand"] = prev_run if side == "away" and hh and hh[-1]["home"] else 0
            m10 = [x["margin"] for x in hh[-10:]]
            d["m10"] = sum(m10) / len(m10) if len(m10) >= 5 else None
            d["sd10"] = statistics.pstdev(m10) if len(m10) >= 8 else None
            m5 = [x["margin"] for x in hh[-5:]]
            d["m5"] = sum(m5) / len(m5) if len(m5) >= 3 else None
            # next game (the schedule is known in advance)
            gs = sched[t]
            i = idx[t][g["id"]]
            nx = gs[i + 1] if i + 1 < len(gs) else None
            if nx is not None and season_of(nx["start"]) == s:
                no = nx["away"] if nx["home"] == t else nx["home"]
                d["next_days"] = (t_(nx["start"]) - now).days
                d["next_home"] = nx["home"] == t
                hn = hist[(no, s)]
                d["next_opp_wp"] = (sum(x["won"] for x in hn) / len(hn)) if len(hn) >= 10 else None
                d["next_opp_elo"] = elo[no]
            else:
                d["next_days"] = d["next_home"] = d["next_opp_wp"] = d["next_opp_elo"] = None
            d["trip_end"] = side == "away" and d["next_home"] is True
            d["stand_end"] = side == "home" and d["next_home"] is False
            # last season
            hl = hist[(t, s - 1)]
            d["last_wp"] = (sum(x["won"] for x in hl) / len(hl)) if len(hl) >= 60 else None
            # market record (walk-forward): last season's and this season's win % minus the no-vig price
            rl = resid[(t, s - 1)]
            d["bias_last"] = sum(rl) / len(rl) if len(rl) >= 60 else None
            rc = resid[(t, s)]
            d["bias_now"] = sum(rc) / len(rc) if len(rc) >= 15 else None
            d["bias_now_n"] = len(rc)
            # box-score style over the last 10 games (both teams' totals in those games)
            poss = pts_f = pts_a = oreb = oreb_opp_dreb = to = fga = tpa = tpm = 0.0
            nb = 0
            for x in hh[-10:]:
                bt, bo = box.get(x["gid"], {}).get(t), box.get(x["gid"], {}).get(x["opp"])
                if not bt or not bo or any(p["fga"] is None or p["fta"] is None or p["oreb"] is None or p["to"] is None
                                           or p["tpa"] is None for p in bt + bo):
                    continue
                nb += 1
                for p in bt:
                    fga += p["fga"]; tpa += p["tpa"]; tpm += p["tpm"]; oreb += p["oreb"]; to += p["to"]
                    poss += p["fga"] - p["oreb"] + p["to"] + 0.44 * p["fta"]
                oreb_opp_dreb += sum(p["dreb"] or 0 for p in bo)
                for p in bo:
                    poss += p["fga"] - p["oreb"] + p["to"] + 0.44 * p["fta"]
            d["box_n"] = nb
            if nb >= 5:
                d["pace"] = poss / (2 * nb)
                d["oreb_pct"] = oreb / (oreb + oreb_opp_dreb) if oreb + oreb_opp_dreb else None
                d["to_rate"] = to / (poss / 2) if poss else None
                d["tp_rate"] = tpa / fga if fga else None
                d["tp_pct"] = tpm / tpa if tpa else None
            else:
                d["pace"] = d["oreb_pct"] = d["to_rate"] = d["tp_rate"] = d["tp_pct"] = None
            # the roster: minutes over the last 10 games, values from the box scores so far (+ last season's prior)
            mins, gp = defaultdict(float), defaultdict(int)
            names = {}
            last10 = hh[-10:]
            for x in last10:
                for p in box.get(x["gid"], {}).get(t, []):
                    mins[p["pid"]] += p["min"]; gp[p["pid"]] += 1; names[p["pid"]] = p["name"]
            top_scorers = []
            if last10:
                pts_by = defaultdict(float)
                for x in last10:
                    for p in box.get(x["gid"], {}).get(t, []):
                        pts_by[p["pid"]] += p["pts"]
                top_scorers = [pid for pid, _ in sorted(pts_by.items(), key=lambda kv: -kv[1])[:3]]
            rot = [pid for pid, _ in sorted(mins.items(), key=lambda kv: -kv[1])[:ROT_N]]

            def value(pid):
                pm, mn = pval.get(pid, (0.0, 0.0))
                lpm, lmn = prev_last.get(pid, (0.0, 0.0))
                return (pm + lpm * 0.5) / (mn + lmn * 0.5 + PRIOR_MIN)      # shrunk toward 0 (the average man)
            d["rot_n"] = len(rot)
            rows_l = lst.get((g["id"], t), [])
            by_name = {}                                   # the report (NBA ids) -> the box score (ESPN ids), by name
            for r in rows_l:
                st = (r.get("morning") or r.get("first") or "").strip()
                by_name[_nm(r["player"])] = (st, r.get("kind") or "", r)
            status = {pid: by_name[_nm(nm)] for pid, nm in names.items() if _nm(nm) in by_name}
            out_pids = {pid for pid, (st, _, _) in status.items() if st in ("Out", "Doubtful")}
            prev_out = set()                               # out on the report of the team's previous game
            if last:
                prev_out = {_nm(r["player"]) for r in lst.get((last["gid"], t), [])
                            if (r.get("morning") or r.get("first") or "").strip() in ("Out", "Doubtful")}
            d["listed"] = bool(rows_l)
            if len(last10) >= 5 and rot:
                mpg = {pid: mins[pid] / max(1, gp[pid]) for pid in rot}
                full = sum(value(pid) * mpg[pid] for pid in rot)
                avail = [pid for pid in rot if pid not in out_pids]
                av_min = sum(mpg[pid] for pid in avail)
                d["strength_full"] = full * 240 / max(1.0, sum(mpg.values()))
                d["strength_avail"] = (sum(value(pid) * mpg[pid] for pid in avail) * 240 / av_min) if av_min else None
                d["out_rot"] = len([pid for pid in rot if pid in out_pids])
                d["out_key"] = len([pid for pid in rot if pid in out_pids and pid in top_scorers])
                d["out_role"] = len([pid for pid in rot if pid in out_pids and pid not in top_scorers and mpg[pid] >= 15])
                d["out_min"] = sum(mpg[pid] for pid in rot if pid in out_pids)
                d["out_rest"] = any(pid in out_pids and status[pid][1] == "rest" for pid in rot)
                d["q_rot"] = len([pid for pid in rot if status.get(pid, ("",))[0] == "Questionable"])
                d["top1_out"] = bool(top_scorers) and top_scorers[0] in out_pids
                # back tonight: a 20+ mpg man who missed the team's last 3+ games (not in those boxes) and is NOT out
                back = []
                recent = hh[-3:]
                if len(recent) == 3:
                    for pid in rot:
                        if mpg[pid] < 20 or pid in out_pids:
                            continue
                        missed = all(pid not in {p["pid"] for p in box.get(x["gid"], {}).get(t, [])} for x in recent)
                        known = status.get(pid, ("",))[0] in ("Available", "Probable", "Questionable") \
                            or (pid not in status and _nm(names[pid]) in prev_out)
                        if missed and gp[pid] >= 3 and known:
                            back.append(pid)
                d["back_n"] = len(back)
                d["back_star"] = any(pid in top_scorers for pid in back)
                d["back_mpg"] = max((mpg[pid] for pid in back), default=0.0)
                d["back_listed"] = any(status.get(pid, ("",))[0] in ("Available", "Probable", "Questionable") for pid in back)
            else:
                for kk in ("strength_full", "strength_avail", "out_rot", "out_key", "out_role", "out_min", "out_rest", "q_rot",
                           "top1_out", "back_n", "back_star", "back_mpg", "back_listed"):
                    d[kk] = None
            # load management history this season (before tonight): how often a rotation man sat with a 'rest'
            # listing on the 2nd night of a back-to-back vs on other nights
            rh = rest_hist[(t, s)]
            d["rest_rate_b2b"] = rh[1] / rh[0] if rh[0] >= 4 else None
            d["rest_rate_oth"] = rh[3] / rh[2] if rh[2] >= 10 else None
            d["_rest_out"] = bool(rows_l) and any(pid in out_pids and status[pid][1] == "rest" for pid in rot)
            pre[side] = d
        # standings at tip (conference rank by win % among teams with games, this season before tonight)
        if mh is not None and ma is not None and mh != ma and dec(mh) > 1 and dec(ma) > 1:
            nv_h = novig(mh, ma)
            margin_h = hs - as_
            mo = morning.get(g["id"]) or {}
            ranks = {}
            for cf in ("E", "W"):
                teams = [(tt, (sum(x["won"] for x in hist[(tt, s)]) / len(hist[(tt, s)])) if hist[(tt, s)] else 0.5)
                         for tt in conf if conf[tt] == cf and (seen_season.get(tt) == s)]
                teams.sort(key=lambda kv: -kv[1])
                for i, (tt, _) in enumerate(teams):
                    ranks[tt] = i + 1
            for side, oth in (("home", "away"), ("away", "home")):
                d = dict(pre[side])
                for k, v in pre[oth].items():
                    d["o_" + k] = v
                ml = mh if side == "home" else ma
                oml = ma if side == "home" else mh
                oml_open = oa if side == "home" else oh
                ml_open = oh if side == "home" else oa
                nv_open = novig(oh, oa) if oh and oa and dec(oh) > 1 and dec(oa) > 1 else None
                mp = mo.get("p")
                d.update(gid=g["id"], start=g["start"], season=s, day=day, ml=ml, opp_ml=oml, dec=dec(ml),
                         nv=nv_h if side == "home" else 1 - nv_h,
                         ml_open=ml_open, nv_open=(nv_open if side == "home" else (1 - nv_open if nv_open else None)),
                         dec_open=dec(ml_open) if ml_open and dec(ml_open) > 1 else None,
                         m_nv=(mp if side == "home" else (1 - mp if mp is not None else None)),
                         m_dec=(mo.get("dh") if side == "home" else mo.get("da")),
                         won=(margin_h > 0) if side == "home" else (margin_h < 0),
                         margin=margin_h if side == "home" else -margin_h,
                         spread=(sp if side == "home" else (-sp if sp is not None else None)),
                         sp_odds=num(g.get("spread_home_odds") if side == "home" else g.get("spread_away_odds")),
                         total=tot, pts_total=hs + as_, ovo=num(g.get("over_odds")), uno=num(g.get("under_odds")),
                         ot=ot_now, loc_hour=loc_h, wd=wd, et_hour=et_h, month=now.month,
                         rank=ranks.get(g[side]), o_rank=ranks.get(g[oth]), elev=num(g.get("elev")))
                sides.append(d)
            resid[(h, s)].append((1.0 if margin_h > 0 else 0.0) - nv_h)
            resid[(a, s)].append((1.0 if margin_h < 0 else 0.0) - (1 - nv_h))
        # update the state
        for side in ("home", "away"):
            d = pre[side]
            if d.get("listed"):
                rh = rest_hist[(d["team"], s)]
                j = 0 if d["b2b"] else 2
                rh[j] += 1
                rh[j + 1] += 1 if d.get("_rest_out") else 0
        mg = hs - as_
        for t, o, m, hm, pts, opts in ((h, a, mg, True, hs, as_), (a, h, -mg, False, as_, hs)):
            hist[(t, s)].append(dict(start=g["start"], opp=o, margin=m, won=m > 0, home=hm, gid=g["id"], ot=ot_now,
                                     pts=pts, opts=opts))
        for t in (h, a):
            for p in box.get(g["id"], {}).get(t, []):
                if p["pm"] is not None:
                    v = pval.setdefault(p["pid"], [0.0, 0.0])
                    v[0] += p["pm"]; v[1] += p["min"]
        exp_h = 1 / (1 + 10 ** (-((elo[h] + HOME) - elo[a]) / 400))
        res_h = 1.0 if mg > 0 else 0.0
        mult = (abs(mg) + 3) ** 0.8 / (7.5 + 0.006 * abs((elo[h] + HOME) - elo[a]))
        elo[h] += K * mult * (res_h - exp_h)
        elo[a] -= K * mult * (res_h - exp_h)
    days = defaultdict(set)
    for d in sides:
        days[d["day"]].add(d["gid"])
    for d in sides:
        d["slate"] = len(days[d["day"]])
        d["games_left"] = None
    # games left in the regular season for the standings angles (82 - played, 72 in 2020-21)
    for d in sides:
        d["games_left"] = (72 if d["season"] == 2020 else 82) - d["g"]
    pickle.dump(sides, open(TABLE, "wb"))
    return sides


def ats(d):
    """profit of this side at the closing spread, None on a push / no spread."""
    if d["spread"] is None:
        return None
    r = d["margin"] + d["spread"]
    if r == 0:
        return None
    return profit(r > 0, dec(d["sp_odds"] or -110))


def ml(d, price="close"):
    """profit of this side's moneyline at the close / the open / the paid morning look (None when that price is missing)."""
    if price == "close":
        return profit(d["won"], d["dec"])
    if price == "open":
        return profit(d["won"], d["dec_open"]) if d["dec_open"] else None
    return profit(d["won"], d["m_dec"]) if d.get("m_dec") else None


def tot(d, over):
    if d["total"] is None or d["pts_total"] == d["total"]:
        return None
    o = (d["ovo"] if over else d["uno"]) or -110
    return profit((d["pts_total"] > d["total"]) == over, dec(o))


def dog(d, lo=100, hi=350):
    return lo <= d["ml"] <= hi


def fav(d, lo=-150, hi=-101):
    return lo <= d["ml"] <= hi


def split(k):
    return TRAIN, HELD


def header(title, n):
    return f"{title}\n(n sides {n}; TRAIN 2018-22, HELD OUT 2023 / 2024 / 2025 apart; z = ROI / its standard error)"


def add_all(cells, name, d, price="close", band=None):
    """ML at the close (+ the open / morning when asked) and ATS in one go."""
    s = d["season"]
    cells.add(name + " [ML close]", s, ml(d))
    if d.get("dec_open"):
        cells.add(name + " [ML open]", s, ml(d, "open"))
    if d.get("m_dec"):
        cells.add(name + " [ML morning]", s, ml(d, "morning"))
    cells.add(name + " [ATS]", s, ats(d))
