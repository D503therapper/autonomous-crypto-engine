"""10/28 THE HOT 3-POINT NIGHT - build one sides table for the NBA (nothing from after tip-off in the predictors).
Run from the repo root: python results/studies/nba_threes_1028/build.py -> sides.pkl (one row per team per game).

Each row: the team's ACTUAL threes that night (tpm / tpa - the after-the-fact fact the owner's "85%" lives on) plus every
PRE-GAME input built only from games already played: season-to-date / last 5 / last 10 three-point attempts and %, the
opponent's threes allowed, pace, rest, home / road, the time-zone jump, altitude, last season's shooting (the early-season
prior), and the team's top-3 three-point shooters (by season-to-date makes): whether any sat the team's LAST game
(knowable before tip) and - flagged as look-ahead - whether any is missing from TONIGHT's box score."""
import json
import os
import pickle
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


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pair(st, key):
    v = st.get(key) or ""
    if "-" in v:
        a, b = v.split("-")
        return int(a), int(b)
    return None, None


def main():
    games = sd.load_games("nba")
    rows = sr.load("nba")
    # per game per team: the team box (sums) and the players who played
    box = defaultdict(dict)
    for r in rows:
        try:
            st = json.loads(r["stats"])
            m = float(st.get("minutes") or 0)
        except (ValueError, TypeError):
            continue
        if m <= 0:
            continue
        tpm, tpa = pair(st, "threePointFieldGoalsMade-threePointFieldGoalsAttempted")
        fgm, fga = pair(st, "fieldGoalsMade-fieldGoalsAttempted")
        ftm, fta = pair(st, "freeThrowsMade-freeThrowsAttempted")
        if tpm is None or fga is None:
            continue
        tb = box[r["gid"]].setdefault(r["team"], {"tpm": 0, "tpa": 0, "fga": 0, "fta": 0, "oreb": 0, "tov": 0,
                                                 "pts": 0.0, "players": {}, "n": 0})
        tb["tpm"] += tpm
        tb["tpa"] += tpa
        tb["fga"] += fga
        tb["fta"] += fta or 0
        tb["oreb"] += int(st.get("offensiveRebounds") or 0)
        tb["tov"] += int(st.get("turnovers") or 0)
        tb["pts"] += float(st.get("points") or 0)
        tb["n"] += 1
        tb["players"][r["pid"]] = (tpm, tpa, m, r["player"], r.get("starter") == "1")
    fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")),
                 key=lambda g: g["start"])
    elo = defaultdict(lambda: 1500.0)
    seen_season = {}
    hist = defaultdict(list)           # (team, season) -> list of dicts (one per game played, in order)
    prior = {}                         # (team, season) -> last season's (tpa/g, 3p%, pace) once the season ends
    lg_run = defaultdict(lambda: [0, 0, 0, 0.0])   # season -> [tpm, tpa, games, pace sum] league-wide so far
    sides = []
    for g in fin:
        s = season_of(g["start"])
        h, a = g["home"], g["away"]
        for t in (h, a):
            if seen_season.get(t) != s:
                elo[t] = 1500 + (elo[t] - 1500) * (1 - REGRESS)
                seen_season[t] = s
                # last season's team numbers = the early-season prior
                hp = hist.get((t, s - 1)) or []
                if len(hp) >= 20:
                    prior[(t, s)] = (sum(x["tpa"] for x in hp) / len(hp),
                                     sum(x["tpm"] for x in hp) / max(1, sum(x["tpa"] for x in hp)),
                                     sum(x["pace"] for x in hp) / len(hp))
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        mh, ma = (int(g["ml_home"]), int(g["ml_away"])) if fnum(g.get("ml_home")) is not None and fnum(g.get("ml_away")) is not None else (None, None)
        sp = fnum(g.get("spread_home"))
        tot = fnum(g.get("total"))
        tz = fnum(g.get("tzo"))
        elev = fnum(g.get("elev"))
        now = t_(g["start"])
        bx = box.get(g["id"], {})
        lg = lg_run[s]
        lg_pct = lg[0] / lg[1] if lg[1] >= 2000 else 0.355          # the league's 3P% so far (a prior for regression)
        lg_pace = lg[3] / lg[2] if lg[2] >= 100 else 100.0
        pre = {}
        for side, oth in (("home", "away"), ("away", "home")):
            t, o = g[side], g[oth]
            hh, ho = hist[(t, s)], hist[(o, s)]
            d = {"team": t, "opp": o, "home": side == "home", "elo": elo[t], "opp_elo": elo[o], "g": len(hh),
                 "opp_g": len(ho)}
            d["wp"] = sum(x["won"] for x in hh) / len(hh) if hh else None
            lgm = hh[-1] if hh else None
            d["rest"] = (now - t_(lgm["start"])).days if lgm else None
            d["tz_jump"] = abs(tz - lgm["tz"]) if (lgm and tz is not None and lgm["tz"] is not None) else None
            d["elev"] = elev
            d["in4"] = sum(1 for x in hh if (now - t_(x["start"])).days < 4) + 1

            def agg(lst, key_m="tpm", key_a="tpa"):
                m_ = sum(x[key_m] for x in lst)
                a_ = sum(x[key_a] for x in lst)
                return m_, a_
            # our shooting: season-to-date, last 5, last 10 (attempts a game, raw %, regressed %)
            for lab, lst in (("s", hh), ("l5", hh[-5:]), ("l10", hh[-10:])):
                if lst:
                    m_, a_ = agg(lst)
                    d[lab + "_tpa"] = a_ / len(lst)
                    d[lab + "_pct"] = m_ / a_ if a_ else None
                    d[lab + "_tpm"] = m_ / len(lst)
                    d[lab + "_pace"] = sum(x["pace"] for x in lst) / len(lst)
                    d[lab + "_pts"] = sum(x["pts"] for x in lst) / len(lst)
                else:
                    d[lab + "_tpa"] = d[lab + "_pct"] = d[lab + "_tpm"] = d[lab + "_pace"] = d[lab + "_pts"] = None
            m_, a_ = agg(hh)
            REG = 250.0                                           # regress 3P% to the league on ~250 attempts
            d["s_pct_reg"] = (m_ + lg_pct * REG) / (a_ + REG)
            # the opponent's threes ALLOWED: season-to-date and last 10
            for lab, lst in (("oa_s", ho), ("oa_l10", ho[-10:])):
                if lst:
                    m_, a_ = agg(lst, "opp_tpm", "opp_tpa")
                    d[lab + "_tpa"] = a_ / len(lst)
                    d[lab + "_pct"] = m_ / a_ if a_ else None
                    d[lab + "_tpm"] = m_ / len(lst)
                else:
                    d[lab + "_tpa"] = d[lab + "_pct"] = d[lab + "_tpm"] = None
            m_, a_ = agg(ho, "opp_tpm", "opp_tpa")
            d["oa_s_pct_reg"] = (m_ + lg_pct * REG) / (a_ + REG)
            d["o_s_pace"] = sum(x["pace"] for x in ho) / len(ho) if ho else None
            d["lg_pct"] = lg_pct
            d["lg_pace"] = lg_pace
            d["prior"] = prior.get((t, s))
            d["o_prior"] = prior.get((o, s))
            # the top-3 three-point shooters by season-to-date makes (3+ games) - who sat LAST game (knowable) and who
            # is missing from TONIGHT's box (look-ahead - flagged)
            made = defaultdict(int)
            for x in hh:
                for pid, (pm, pa, mn, nm, st_) in x["players"].items():
                    made[pid] += pm
            top = [pid for pid, _ in sorted(made.items(), key=lambda kv: -kv[1])[:3]] if len(hh) >= 3 else []
            d["top3_share"] = (sum(made[p] for p in top) / sum(made.values())) if top and sum(made.values()) else None
            d["top3_sat_last"] = sum(1 for p in top if lgm and p not in lgm["players"]) if top else None
            tb = bx.get(t)
            d["top3_out_tonight"] = sum(1 for p in top if tb and p not in tb["players"]) if (top and tb) else None
            pre[side] = d
        th, ta = bx.get(h), bx.get(a)
        have_box = bool(th and ta and th["n"] >= 5 and ta["n"] >= 5)
        if mh is not None and ma is not None and mh != ma and have_box:
            nv_h = novig(mh, ma)
            margin_h = hs - as_
            for side, oth in (("home", "away"), ("away", "home")):
                ml = mh if side == "home" else ma
                oml = ma if side == "home" else mh
                d = dict(pre[side])
                for k, v in pre[oth].items():
                    d["o_" + k] = v
                mine, theirs = (th, ta) if side == "home" else (ta, th)
                d.update(gid=g["id"], start=g["start"], season=s, ml=ml, opp_ml=oml,
                         nv=nv_h if side == "home" else 1 - nv_h,
                         won=(margin_h > 0) if side == "home" else (margin_h < 0),
                         margin=margin_h if side == "home" else -margin_h,
                         spread=(sp if side == "home" else (-sp if sp is not None else None)), total=tot,
                         tpm=mine["tpm"], tpa=mine["tpa"], o_tpm=theirs["tpm"], o_tpa=theirs["tpa"])
                sides.append(d)
        # update state (box numbers only when we hold both boxes)
        hh_m = hs - as_
        for t, o, mg, tb, ob in ((h, a, hh_m, th, ta), (a, h, -hh_m, ta, th)):
            if not (tb and ob):
                continue
            pace = tb["fga"] - tb["oreb"] + tb["tov"] + 0.44 * tb["fta"]
            hist[(t, s)].append(dict(start=g["start"], opp=o, margin=mg, won=mg > 0, tz=tz, gid=g["id"],
                                     tpm=tb["tpm"], tpa=tb["tpa"], opp_tpm=ob["tpm"], opp_tpa=ob["tpa"], pace=pace,
                                     pts=tb["pts"], players=tb["players"]))
        if th and ta:
            lg[0] += th["tpm"] + ta["tpm"]
            lg[1] += th["tpa"] + ta["tpa"]
            lg[2] += 2
            lg[3] += (th["fga"] - th["oreb"] + th["tov"] + 0.44 * th["fta"]) + (ta["fga"] - ta["oreb"] + ta["tov"] + 0.44 * ta["fta"])
        exp_h = 1 / (1 + 10 ** (-((elo[h] + HOME) - elo[a]) / 400))
        res_h = 1.0 if hh_m > 0 else 0.0
        mult = (abs(hh_m) + 3) ** 0.8 / (7.5 + 0.006 * abs((elo[h] + HOME) - elo[a]))
        elo[h] += K * mult * (res_h - exp_h)
        elo[a] -= K * mult * (res_h - exp_h)
    for d in sides:                                              # the players dicts are not needed downstream
        pass
    with open(OUT, "wb") as f:
        pickle.dump(sides, f)
    by = defaultdict(int)
    for d in sides:
        by[d["season"]] += 1
    print("sides", len(sides), "by season", sorted(by.items()))


if __name__ == "__main__":
    main()
