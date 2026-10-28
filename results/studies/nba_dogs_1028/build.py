"""10/28 NBA DOG STUDIES - build one sides table (nothing from after tip-off). Run from the repo root."""
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


def main():
    games = sd.load_games("nba")
    rows = sr.load("nba")
    # per game per team: list of (minutes, points, 3pa, 3pm, fga)
    box = defaultdict(lambda: defaultdict(list))
    for r in rows:
        try:
            st = json.loads(r["stats"])
            m = float(st.get("minutes") or 0)
            tp = st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted") or ""
            fg = st.get("fieldGoalsMade-fieldGoalsAttempted") or ""
            tpm, tpa = (int(x) for x in tp.split("-")) if "-" in tp else (None, None)
            fga = int(fg.split("-")[1]) if "-" in fg else None
            pts = float(st.get("points") or 0)
        except (ValueError, TypeError):
            continue
        if m > 0:
            box[r["gid"]][r["team"]].append((m, pts, tpa, tpm, fga, r["pid"]))
    fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")),
                 key=lambda g: g["start"])
    # schedule by team (final regular-season games in order) for the look-ahead
    sched = defaultdict(list)
    for g in fin:
        sched[g["home"]].append(g)
        sched[g["away"]].append(g)
    idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
    elo = defaultdict(lambda: 1500.0)
    seen_season = {}
    rec = defaultdict(lambda: [0, 0])
    hist = defaultdict(list)           # (team, season) -> list of dict(start, opp, margin, won, home, gid, as_dog, opp_elo)
    sides = []
    n3 = 0
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
            sp = float(g["spread_home"])
        except (TypeError, ValueError):
            sp = None
        try:
            tot = float(g["total"])
        except (TypeError, ValueError):
            tot = None
        pre = {}
        for side, oth in (("home", "away"), ("away", "home")):
            t, o = g[side], g[oth]
            hh = hist[(t, s)]
            ho = hist[(o, s)]
            d = {"team": t, "opp": o, "home": side == "home", "elo": elo[t], "opp_elo": elo[o]}
            d["g"] = len(hh)
            d["wp"] = sum(x["won"] for x in hh) / len(hh) if hh else None
            lg_ = hh[-1] if hh else None
            d["rest"] = (t_(g["start"]) - t_(lg_["start"])).days if lg_ else None
            d["last_won"] = lg_["won"] if lg_ else None
            d["last_margin"] = lg_["margin"] if lg_ else None
            d["last_opp_elo"] = lg_["opp_elo"] if lg_ else None
            d["last_opp_same"] = (lg_["opp"] == o) if lg_ else None
            d["last_ot"] = lg_["ot"] if lg_ else None
            d["last_opp_same_days"] = (t_(g["start"]) - t_(lg_["start"])).days if lg_ and lg_["opp"] == o else None
            # meetings so far this season vs this opp
            mt = [x for x in hh if x["opp"] == o]
            d["met"] = len(mt)
            d["last_meet_margin"] = mt[-1]["margin"] if mt else None
            # margin variance last 10 / 15
            m10 = [x["margin"] for x in hh[-10:]]
            d["sd10"] = statistics.pstdev(m10) if len(m10) >= 8 else None
            m15 = [x["margin"] for x in hh[-15:]]
            d["sd15"] = statistics.pstdev(m15) if len(m15) >= 12 else None
            d["avg10"] = sum(m10) / len(m10) if len(m10) >= 8 else None
            # dense schedule: games in the last 6 / 4 days
            now = t_(g["start"])
            d["in4"] = sum(1 for x in hh if (now - t_(x["start"])).days < 4) + 1
            d["in6"] = sum(1 for x in hh if (now - t_(x["start"])).days < 6) + 1
            # next game (schedule look-ahead, known in advance): days until, opponent Elo now, home / away
            gs = sched[t]
            i = idx[t][g["id"]]
            nx = gs[i + 1] if i + 1 < len(gs) else None
            if nx is not None and season_of(nx["start"]) == s:
                no = nx["away"] if nx["home"] == t else nx["home"]
                d["next_days"] = (t_(nx["start"]) - now).days
                d["next_opp_elo"] = elo[no]
                d["next_home"] = nx["home"] == t
                d["next_opp_same"] = no == o
                hn = hist[(no, s)]
                d["next_opp_g"] = len(hn)
                d["next_opp_wp"] = sum(x["won"] for x in hn) / len(hn) if hn else None
            else:
                d["next_days"] = d["next_opp_elo"] = d["next_home"] = d["next_opp_same"] = d["next_opp_wp"] = d["next_opp_g"] = None
            # threes and minutes from the box: last 10 games this season (before tonight)
            tpa = tpm = fga = 0.0
            nb = 0
            for x in hh[-10:]:
                bx = box.get(x["gid"], {}).get(t)
                if not bx or any(p[2] is None for p in bx) or any(p[4] is None for p in bx):
                    continue
                nb += 1
                tpa += sum(p[2] for p in bx)
                tpm += sum(p[3] for p in bx)
                fga += sum(p[4] for p in bx)
            d["box_n"] = nb
            d["tpa_g"] = tpa / nb if nb >= 5 else None
            d["tp_rate"] = tpa / fga if nb >= 5 and fga else None
            d["tp_pct"] = tpm / tpa if nb >= 5 and tpa else None
            # last game's heavy minutes (the top 3 men by minutes last game) + last game's 3P%
            if lg_:
                bx = box.get(lg_["gid"], {}).get(t) or []
                mins = sorted((p[0] for p in bx), reverse=True)
                d["last_top3_min"] = sum(mins[:3]) / 3 if len(mins) >= 3 else None
                d["last_max_min"] = mins[0] if mins else None
                la = sum(p[2] for p in bx if p[2] is not None)
                lm = sum(p[3] for p in bx if p[3] is not None)
                d["last_tp_pct"] = lm / la if la else None
                d["last_tpa"] = la if bx and all(p[2] is not None for p in bx) else None
            else:
                d["last_top3_min"] = d["last_max_min"] = d["last_tp_pct"] = d["last_tpa"] = None
            pre[side] = d
        if mh is not None and ma is not None and mh != ma:
            nv_h = novig(mh, ma)
            margin_h = hs - as_
            # slate size that day (UTC date of start shifted -8h -> PT day)
            for side, oth in (("home", "away"), ("away", "home")):
                ml = mh if side == "home" else ma
                oml = ma if side == "home" else mh
                d = dict(pre[side])
                for k, v in pre[oth].items():
                    d["o_" + k] = v
                d.update(gid=g["id"], start=g["start"], season=s, ml=ml, opp_ml=oml,
                         nv=nv_h if side == "home" else 1 - nv_h,
                         won=(margin_h > 0) if side == "home" else (margin_h < 0),
                         margin=margin_h if side == "home" else -margin_h,
                         spread=(sp if side == "home" else (-sp if sp is not None else None)), total=tot,
                         elev=g.get("elev"), city=g.get("city"))
                sides.append(d)
        # update state
        hh_m = hs - as_
        for t, o, mg, hm in ((h, a, hh_m, True), (a, h, -hh_m, False)):
            ml = (mh if hm else ma)
            hist[(t, s)].append(dict(start=g["start"], opp=o, margin=mg, won=mg > 0, home=hm, gid=g["id"], ot=len(str(g.get("ls_home") or "").split(",")) > 4,
                                     as_dog=(ml is not None and ml > 0), opp_elo=elo[o]))
        exp_h = 1 / (1 + 10 ** (-((elo[h] + HOME) - elo[a]) / 400))
        res_h = 1.0 if hh_m > 0 else 0.0
        mult = (abs(hh_m) + 3) ** 0.8 / (7.5 + 0.006 * abs((elo[h] + HOME) - elo[a]))
        elo[h] += K * mult * (res_h - exp_h)
        elo[a] -= K * mult * (res_h - exp_h)
    # slate size per PT day
    days = defaultdict(set)
    for d in sides:
        pt = (t_(d["start"]) .timestamp() - 8 * 3600)
        day = datetime.utcfromtimestamp(pt).strftime("%Y-%m-%d")
        d["day"] = day
        days[day].add(d["gid"])
    for d in sides:
        d["slate"] = len(days[d["day"]])
    with open(OUT, "wb") as f:
        pickle.dump(sides, f)
    print("sides", len(sides), "with box threes", sum(1 for d in sides if d["tpa_g"] is not None))
    by = defaultdict(int)
    for d in sides:
        if d["tpa_g"] is not None:
            by[d["season"]] += 1
    print("threes by season", sorted(by.items()))


if __name__ == "__main__":
    main()
