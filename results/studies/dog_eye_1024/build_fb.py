"""Football sides (ncaaf + nfl) for the dog-eye detectors: pre-game Elo, records, last game, last season."""
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
import sports_data as sd      # noqa: E402
import sports_early as se     # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "fb_sides.pkl")
P = {"nfl": (20.0, 55.0, 0.33), "ncaaf": (25.0, 60.0, 0.2)}


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 7 else y - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def main():
    sides = []
    for lg in ("nfl", "ncaaf"):
        K, HOME, REG = P[lg]
        games = sd.load_games(lg)
        fin = sorted((g for g in games.values() if g.get("status") == "final" and g.get("home_score") not in (None, "")
                      and g.get("away_score") not in (None, "")), key=lambda g: g["start"])
        elo = defaultdict(lambda: 1500.0)
        seen = {}
        rec = defaultdict(lambda: [0, 0, 0.0])
        n_games = defaultdict(int)       # team, season -> games we hold (FBS teams)
        last = {}
        for g in fin:
            s = season_of(g["start"])
            h, a = g["home"], g["away"]
            for t in (h, a):
                if seen.get(t) != s:
                    elo[t] = 1500 + (elo[t] - 1500) * (1 - REG)
                    seen[t] = s
            hs, as_ = int(g["home_score"]), int(g["away_score"])
            neutral = str(g.get("neutral") or "0") == "1"
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
            exp_home = 1 / (1 + 10 ** (-(elo[h] + (0 if neutral else HOME) - elo[a]) / 400))
            pre = {}
            for side, oth in (("home", "away"), ("away", "home")):
                t, o = g[side], g[oth]
                r, lt = rec[(t, s)], rec.get((t, s - 1))
                lg_ = last.get(t)
                d = dict(elo=elo[t], g=r[0] + r[1], wp=r[0] / (r[0] + r[1]) if r[0] + r[1] else None,
                         ly_wp=lt[0] / (lt[0] + lt[1]) if lt and lt[0] + lt[1] >= (14 if lg == "nfl" else 9) else None,
                         ly_g=(lt[0] + lt[1]) if lt else 0,
                         rest=(se._t(g["start"]) - se._t(lg_["start"])).days if lg_ else None,
                         last_won=lg_["won"] if lg_ else None, last_margin=lg_["margin"] if lg_ else None,
                         last_as_dog=lg_["as_dog"] if lg_ else None, last_ml=lg_["ml"] if lg_ else None,
                         last_opp_wp=lg_["opp_wp"] if lg_ else None, last_opp_elo=lg_["opp_elo"] if lg_ else None,
                         last_opp_g=lg_["opp_g"] if lg_ else None, last_same_season=(lg_["season"] == s) if lg_ else None)
                pre[side] = d
            if mh is not None and ma is not None and (g.get("stype") in (None, "", "2") or True):
                mp_h = novig(mh, ma)
                for side, oth in (("home", "away"), ("away", "home")):
                    ml = mh if side == "home" else ma
                    mp = mp_h if side == "home" else 1 - mp_h
                    op = None
                    if oh is not None:
                        op = novig(oh, oa) if side == "home" else 1 - novig(oh, oa)
                    won = hs > as_ if side == "home" else as_ > hs
                    f, o = pre[side], pre[oth]
                    sides.append(dict(league=lg, season=s, gid=g["id"], date=g["start"][:10], side=side, is_home=side == "home" and not neutral,
                                      team=g[side + "_name"], opp=g[oth + "_name"], tid=g[side], oid=g[oth], stype=g.get("stype"),
                                      ml=ml, mp=mp, op_mp=op, won=won, elo_p=exp_home if side == "home" else 1 - exp_home,
                                      **f, **{"o_" + k: v for k, v in o.items()}))
            margin = hs - as_
            km = K * (1 + min(abs(margin), 28) / 14.0)
            elo[h] += km * ((1 if margin > 0 else 0) - exp_home)
            elo[a] -= km * ((1 if margin > 0 else 0) - exp_home)
            for t, o, m, won, ml in ((h, a, margin, margin > 0, mh), (a, h, -margin, margin < 0, ma)):
                r = rec[(t, s)]
                r[0] += won
                r[1] += not won
                r[2] += m
                ro = rec[(o, s)]
                go = ro[0] + ro[1]        # includes tonight
                last[t] = dict(start=g["start"], season=s, won=won, opp=o, margin=m, as_dog=(ml is not None and ml > 0), ml=ml,
                               opp_wp=(ro[0] - (0 if won else 1)) / (go - 1) if go > 1 else None, opp_g=go - 1,
                               opp_elo=pre["home" if o == h else "away"]["elo"])
    pickle.dump(sides, open(OUT, "wb"))
    print("sides", len(sides))


if __name__ == "__main__":
    main()
