"""THE OWNER'S DOG EYE (10/24) - build one NBA sides table, nothing from after tip-off except who was in the box
(flagged box_* - a game-day fact; the injury report would have said most of it, but it's a caveat).

    cd <repo>; python <scratchpad>/dogeye/build_nba.py
"""
import json
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
import sports_data as sd                  # noqa: E402
import sports_roster as sr                # noqa: E402
import sports_nba_roster as nr            # noqa: E402
import sports_nba_stars as ns
import sports_early as se

OUT = os.path.join(os.path.dirname(__file__), "nba_sides.pkl")
K, HOME, REGRESS = 20.0, 70.0, 0.33


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 9 else y - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def main():
    games = sd.load_games("nba")
    stars = ns.load()
    rows = sr.load("nba")
    by_gid = defaultdict(lambda: defaultdict(list))      # gid -> team -> [(pid, name, min, starter)]
    by_season_rows = defaultdict(list)
    for r in rows:
        try:
            st = json.loads(r["stats"])
            m = float(st.get("minutes") or 0)
        except (ValueError, TypeError):
            m = 0.0
        by_season_rows[season_of(r["start"])].append(r)
        if m > 0:
            by_gid[r["gid"]][r["team"]].append((r["pid"], r["player"], m, r.get("starter") in ("1", "True", "true")))
    values = {s: nr.player_values(by_season_rows[s]) for s in by_season_rows if len(by_season_rows[s]) > 5000}
    print("box seasons", sorted(values), flush=True)

    fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype") or "2") == "2"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")),
                 key=lambda g: g["start"])
    elo = defaultdict(lambda: 1500.0)
    seen_season = {}
    rec = defaultdict(lambda: [0, 0, 0.0])              # (team, season) -> [w, l, margin sum]
    last_game = {}                                        # team -> dict(start, won, opp, margin, as_dog, opp_wp, opp_elo, ml)
    recent = defaultdict(list)                            # (team, season) -> list of last gids (for lineups)
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
        oh = oa = None
        try:
            if g.get("ml_home_open") and g.get("ml_away_open") and (g["ml_home_open"] != g["ml_home"] or g["ml_away_open"] != g["ml_away"]):
                oh, oa = int(g["ml_home_open"]), int(g["ml_away_open"])
        except (TypeError, ValueError):
            pass
        box = by_gid.get(g["id"], {})
        pre = {}
        for side, oth in (("home", "away"), ("away", "home")):
            t, o = g[side], g[oth]
            r_t, r_o = rec[(t, s)], rec[(o, s)]
            lt, lo = rec.get((t, s - 1)), rec.get((o, s - 1))
            lg_ = last_game.get(t)
            d = {}
            d["elo"] = elo[t]
            d["g"] = r_t[0] + r_t[1]
            d["wp"] = r_t[0] / d["g"] if d["g"] else None
            d["mpg_margin"] = r_t[2] / d["g"] if d["g"] else None
            d["ly_wp"] = lt[0] / (lt[0] + lt[1]) if lt and lt[0] + lt[1] >= 60 else None
            d["rest"] = (se._t(g["start"]) - se._t(lg_["start"])).days if lg_ else None
            d["last_won"] = lg_["won"] if lg_ else None
            d["last_margin"] = lg_["margin"] if lg_ else None
            d["last_as_dog"] = lg_["as_dog"] if lg_ else None
            d["last_opp_wp"] = lg_["opp_wp"] if lg_ else None
            d["last_opp_elo"] = lg_["opp_elo"] if lg_ else None
            d["last_opp_same"] = (lg_["opp"] == o) if lg_ else None
            # lineups from the box (this season so far, before tonight): usual starters, rotation by minutes
            gids = recent[(t, s)][-10:]
            mins, starts, names = defaultdict(float), defaultdict(int), {}
            for gid in gids:
                for pid, nm, m, st_ in by_gid.get(gid, {}).get(t, []):
                    mins[pid] += m
                    starts[pid] += 1 if st_ else 0
                    names[pid] = nm
            d["n_recent"] = len(gids)
            usual_starters = {p for p, c in starts.items() if len(gids) >= 3 and c >= 0.6 * len(gids)}
            rot = sorted(mins, key=lambda p: -mins[p])[:8]
            tonight = {p for p, _, _, _ in box.get(t, [])}
            d["box"] = bool(box.get(t))
            d["box_starters_out"] = len(usual_starters - tonight) if box.get(t) and len(gids) >= 3 else None
            d["box_rot_out"] = len(set(rot) - tonight) if box.get(t) and len(gids) >= 3 else None
            # talent: last season's values on the men who played the last 10 games (minutes-weighted), the roster
            # so far - NO tonight look-ahead. Also the tonight version (flagged).
            v = values.get(s - 1)
            if v is not None and gids:
                ros = [{"pid": p, "name": names[p]} for p in sorted(mins, key=lambda p: -mins[p])[:13]]
                d["talent"] = nr.team_strength(ros, v)
                d["talent_elo_raw"] = d["talent"]
                if box.get(t):
                    ros_t = [{"pid": p, "name": nm} for p, nm, _, _ in box[t]]
                    d["box_talent"] = nr.team_strength(ros_t, v)
                else:
                    d["box_talent"] = None
            else:
                d["talent"] = d["box_talent"] = None
            # stars: honors of the seasons before, on the roster so far (last 10 games' men)
            if stars and ns.covered(s, stars) and gids:
                st = ns.team([names[p] for p in rot], s, stars)
                d["stars"], d["star_n"] = st["score"], st["n"]
            else:
                d["stars"] = d["star_n"] = None
            pre[side] = d
        exp_home = 1 / (1 + 10 ** (-(elo[h] + HOME - elo[a]) / 400))
        if mh is not None and ma is not None:
            mp_h = novig(mh, ma)
            for side, oth in (("home", "away"), ("away", "home")):
                ml = mh if side == "home" else ma
                mp = mp_h if side == "home" else 1 - mp_h
                op = None
                if oh is not None:
                    op = novig(oh, oa) if side == "home" else 1 - novig(oh, oa)
                won = hs > as_ if side == "home" else as_ > hs
                f, o = pre[side], pre[oth]
                elo_p = exp_home if side == "home" else 1 - exp_home
                sides.append(dict(season=s, gid=g["id"], date=g["start"][:10], side=side, is_home=side == "home",
                                  team=g[side + "_name"], opp=g[oth + "_name"], tid=g[side], oid=g[oth],
                                  ml=ml, mp=mp, op_mp=op, won=won, elo_p=elo_p,
                                  **{k: v for k, v in f.items()}, **{"o_" + k: v for k, v in o.items()}))
        # update
        margin = hs - as_
        k_mult = K * (1 + min(abs(margin), 30) / 20.0)
        elo[h] += k_mult * ((1 if margin > 0 else 0) - exp_home)
        elo[a] -= k_mult * ((1 if margin > 0 else 0) - exp_home)
        for t, o, m, won, ml in ((h, a, margin, margin > 0, mh), (a, h, -margin, margin < 0, ma)):
            r = rec[(t, s)]
            r[0] += won
            r[1] += not won
            r[2] += m
            ro = rec[(o, s)]
            go = ro[0] + ro[1] - 1 if ro[0] + ro[1] else 0
            last_game[t] = dict(start=g["start"], won=won, opp=o, margin=m, as_dog=(ml is not None and ml > 0),
                                opp_wp=(ro[0] - (0 if won else 1)) / go if go > 0 else None,
                                opp_elo=pre["home" if o == h else "away"]["elo"])
            recent[(t, s)].append(g["id"])
    pickle.dump(sides, open(OUT, "wb"))
    print("sides", len(sides), "with price", sum(1 for x in sides if x["ml"] is not None))


if __name__ == "__main__":
    main()
