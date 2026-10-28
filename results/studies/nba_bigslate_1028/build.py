"""10/28 BIG-SLATE NBA UPSET STUDIES - one sides table (nothing from after tip-off). Run from the repo root.
Extends results/studies/nba_dogs_1028/build.py with: team box-score rates over the last 10 games (pace, rebounding,
turnovers, net rating), the top man by minutes and whether he played the last game, the opening moneyline (2023+),
the tip hour, the weekday, the market size, the dog's place in the night's order."""
import json
import os
import pickle
import statistics
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.getcwd())
import sports_data as sd      # noqa: E402
import sports_roster as sr    # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "sides.pkl")
K, HOME, REGRESS = 20.0, 70.0, 0.33
# market size by franchise (metro TV market, a fixed list)
BIG = {"13", "12", "18", "17", "4", "9", "2", "20", "6", "10", "14", "28", "1", "21", "27"}       # LAL LAC NYK BKN CHI GSW BOS PHI DAL HOU MIA TOR ATL PHX WAS
SMALL = {"29", "25", "3", "24", "15", "26", "22", "11", "30", "19", "23", "16", "5", "7", "8"}    # MEM OKC NOP SAS MIL UTA POR IND CHA ORL SAC MIN CLE DEN DET


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 9 else y - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def t_(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def num(st, k):
    try:
        return float(st.get(k))
    except (TypeError, ValueError):
        return None


def pair(st, k):
    v = st.get(k) or ""
    if "-" in v:
        a, b = v.split("-")
        return int(a), int(b)
    return None, None


def main():
    games = sd.load_games("nba")
    rows = sr.load("nba")
    box = defaultdict(lambda: defaultdict(lambda: {"min": [], "pid": [], "fga": 0, "fta": 0, "oreb": 0, "dreb": 0, "tov": 0, "pts": 0, "n": 0, "ok": True}))
    for r in rows:
        try:
            st = json.loads(r["stats"])
            m = float(st.get("minutes") or 0)
        except (ValueError, TypeError):
            continue
        b = box[r["gid"]][r["team"]]
        if m > 0:
            b["min"].append(m)
            b["pid"].append((m, r["pid"]))
        fgm, fga = pair(st, "fieldGoalsMade-fieldGoalsAttempted")
        ftm, fta = pair(st, "freeThrowsMade-freeThrowsAttempted")
        oreb, dreb, tov, pts = num(st, "offensiveRebounds"), num(st, "defensiveRebounds"), num(st, "turnovers"), num(st, "points")
        if None in (fga, fta, oreb, dreb, tov, pts):
            b["ok"] = False
            continue
        b["fga"] += fga; b["fta"] += fta; b["oreb"] += oreb; b["dreb"] += dreb; b["tov"] += tov; b["pts"] += pts; b["n"] += 1
    fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")
                  and g["home"].isdigit() and int(g["home"]) <= 30 and g["away"].isdigit() and int(g["away"]) <= 30),
                 key=lambda g: g["start"])
    sched = defaultdict(list)
    for g in fin:
        sched[g["home"]].append(g)
        sched[g["away"]].append(g)
    idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
    elo = defaultdict(lambda: 1500.0)
    seen_season = {}
    hist = defaultdict(list)
    pmin = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))   # (team, season) -> pid -> [minutes, games]
    sides = []
    for g in fin:
        s = season_of(g["start"])
        h, a = g["home"], g["away"]
        for t in (h, a):
            if seen_season.get(t) != s:
                elo[t] = 1500 + (elo[t] - 1500) * (1 - REGRESS)
                seen_season[t] = s
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        try:
            mh, ma = int(g["ml_home"]), int(g["ml_away"])
        except (TypeError, ValueError):
            mh = ma = None
        try:
            oh, oa = int(g["ml_home_open"]), int(g["ml_away_open"])
        except (TypeError, ValueError):
            oh = oa = None
        try:
            sp = float(g["spread_home"])
        except (TypeError, ValueError):
            sp = None
        try:
            tot = float(g["total"])
        except (TypeError, ValueError):
            tot = None
        now = t_(g["start"])
        pre = {}
        for side, oth in (("home", "away"), ("away", "home")):
            t, o = g[side], g[oth]
            hh = hist[(t, s)]
            d = {"team": t, "opp": o, "home": side == "home", "elo": elo[t], "opp_elo": elo[o]}
            d["g"] = len(hh)
            d["wp"] = sum(x["won"] for x in hh) / len(hh) if hh else None
            d["w5"] = sum(x["won"] for x in hh[-5:]) if len(hh) >= 5 else None
            lg_ = hh[-1] if hh else None
            d["rest"] = (now - t_(lg_["start"])).days if lg_ else None
            d["last_won"] = lg_["won"] if lg_ else None
            d["last_margin"] = lg_["margin"] if lg_ else None
            d["last_ot"] = lg_["ot"] if lg_ else None
            m10 = [x["margin"] for x in hh[-10:]]
            d["avg10"] = sum(m10) / len(m10) if len(m10) >= 8 else None
            d["sd10"] = statistics.pstdev(m10) if len(m10) >= 8 else None
            d["in4"] = sum(1 for x in hh if (now - t_(x["start"])).days < 4) + 1
            d["in6"] = sum(1 for x in hh if (now - t_(x["start"])).days < 6) + 1
            d["road_run"] = 0
            for x in reversed(hh):
                if x["home"]:
                    break
                d["road_run"] += 1
            gs = sched[t]
            i = idx[t][g["id"]]
            nx = gs[i + 1] if i + 1 < len(gs) else None
            if nx is not None and season_of(nx["start"]) == s:
                no = nx["away"] if nx["home"] == t else nx["home"]
                d["next_days"] = (t_(nx["start"]) - now).days
                hn = hist[(no, s)]
                d["next_opp_g"] = len(hn)
                d["next_opp_wp"] = sum(x["won"] for x in hn) / len(hn) if hn else None
            else:
                d["next_days"] = d["next_opp_wp"] = d["next_opp_g"] = None
            poss = pts = opts = oreb = odreb = tov = fga = 0.0
            nb = 0
            for x in hh[-10:]:
                bt, bo = box.get(x["gid"], {}).get(t), box.get(x["gid"], {}).get(x["opp"])
                if not bt or not bo or not bt["ok"] or not bo["ok"] or bt["n"] < 5 or bo["n"] < 5:
                    continue
                nb += 1
                p_t = bt["fga"] + 0.44 * bt["fta"] - bt["oreb"] + bt["tov"]
                p_o = bo["fga"] + 0.44 * bo["fta"] - bo["oreb"] + bo["tov"]
                poss += (p_t + p_o) / 2
                pts += bt["pts"]; opts += bo["pts"]; oreb += bt["oreb"]; odreb += bo["dreb"]; tov += bt["tov"]; fga += bt["fga"]
            d["box_n"] = nb
            if nb >= 5 and poss:
                d["pace"] = poss / nb
                d["net100"] = (pts - opts) / poss * 100
                d["oreb_pct"] = oreb / (oreb + odreb) if oreb + odreb else None
                d["tov_rate"] = tov / poss
            else:
                d["pace"] = d["net100"] = d["oreb_pct"] = d["tov_rate"] = None
            pm = pmin[(t, s)]
            top = sorted(((v[0] / v[1], pid) for pid, v in pm.items() if v[1] >= 5), reverse=True)
            d["star_mpg"] = top[0][0] if top else None
            if top and lg_ and box.get(lg_["gid"], {}).get(t):
                star = top[0][1]
                played = [any(p == star for _, p in box.get(x["gid"], {}).get(t, {"pid": []})["pid"]) for x in hh[-3:]]
                d["star_out_last"] = not played[-1]
                d["star_out_2"] = len(played) >= 2 and not played[-1] and not played[-2]
                d["star_back"] = played[-1] and len(played) >= 2 and not played[-2]
            else:
                d["star_out_last"] = d["star_out_2"] = d["star_back"] = None
            if lg_:
                mins = sorted(box.get(lg_["gid"], {}).get(t, {"min": []})["min"], reverse=True)
                d["last_top3_min"] = sum(mins[:3]) / 3 if len(mins) >= 3 else None
            else:
                d["last_top3_min"] = None
            pre[side] = d
        if mh is not None and ma is not None and mh != ma:
            nv_h = novig(mh, ma)
            margin_h = hs - as_
            for side, oth in (("home", "away"), ("away", "home")):
                ml = mh if side == "home" else ma
                oml = ma if side == "home" else mh
                d = dict(pre[side])
                for k, v in pre[oth].items():
                    d["o_" + k] = v
                d.update(gid=g["id"], start=g["start"], season=s, ml=ml, opp_ml=oml,
                         ml_open=(oh if side == "home" else oa) if oh is not None else None,
                         nv=nv_h if side == "home" else 1 - nv_h,
                         nv_open=(novig(oh, oa) if side == "home" else 1 - novig(oh, oa)) if oh is not None and oh != oa else None,
                         won=(margin_h > 0) if side == "home" else (margin_h < 0),
                         margin=margin_h if side == "home" else -margin_h,
                         spread=(sp if side == "home" else (-sp if sp is not None else None)), total=tot,
                         market=("big" if d["team"] in BIG else "small" if d["team"] in SMALL else "mid"),
                         o_market=("big" if d["opp"] in BIG else "small" if d["opp"] in SMALL else "mid"),
                         tip_utc=now.hour + now.minute / 60)
                sides.append(d)
        hh_m = hs - as_
        for t, o, mg, hm in ((h, a, hh_m, True), (a, h, -hh_m, False)):
            hist[(t, s)].append(dict(start=g["start"], opp=o, margin=mg, won=mg > 0, home=hm, gid=g["id"],
                                     ot=len(str(g.get("ls_home") or "").split(",")) > 4))
            for m, pid in box.get(g["id"], {}).get(t, {"pid": []})["pid"]:
                pmin[(t, s)][pid][0] += m
                pmin[(t, s)][pid][1] += 1
        exp_h = 1 / (1 + 10 ** (-((elo[h] + HOME) - elo[a]) / 400))
        res_h = 1.0 if hh_m > 0 else 0.0
        mult = (abs(hh_m) + 3) ** 0.8 / (7.5 + 0.006 * abs((elo[h] + HOME) - elo[a]))
        elo[h] += K * mult * (res_h - exp_h)
        elo[a] -= K * mult * (res_h - exp_h)
    days = defaultdict(dict)
    for d in sides:
        pt = datetime.utcfromtimestamp(t_(d["start"]).timestamp() - 8 * 3600)
        d["day"] = pt.strftime("%Y-%m-%d")
        d["wday"] = pt.weekday()
        days[d["day"]][d["gid"]] = d["start"]
    for d in sides:
        starts = sorted(days[d["day"]].values())
        d["slate"] = len(starts)
        d["order"] = sum(1 for x in starts if x < d["start"])
        d["last_tip"] = d["start"] == starts[-1]
        d["first_tip"] = d["start"] == starts[0]
    with open(OUT, "wb") as f:
        pickle.dump(sides, f)
    print("sides", len(sides), "with box rates", sum(1 for d in sides if d["pace"] is not None),
          "with open", sum(1 for d in sides if d["ml_open"] is not None),
          "with star fact", sum(1 for d in sides if d["star_out_last"] is not None))


if __name__ == "__main__":
    main()
