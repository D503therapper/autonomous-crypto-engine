"""NFL rows for the 10/30 unit-play studies: every side of every graded NFL game 2020-26 with the engine's reads
(trained on the 3 seasons before - walk-forward, blind), the close, and the paid early prices (first fair look / last
look before game day / game morning). Saves rows.pkl."""
import os, sys, pickle, time
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # the repo root
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import early_football_study as efs
import sports_data as sd, sports_model as sm
t0 = time.time()
lg = "nfl"
games = sd.load_games(lg)
pr, miss = efs.match(efs.snapshots(efs.SPORTS[lg]), games)
lastg = efs.last_games(games, lg)
ready = efs.ready_at(games, lg)
rows = []
for season in efs.SEASONS + (2026,):
    lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
    p = sm.tune(learn, lg)
    if not p or "w" not in p:
        print("no params", season); continue
    _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
    for g, f, *_ in played:
        if not lo <= g["start"] < hi:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_:
            continue
        own = sm.own_p(p, f)
        own_blind = sm.own_p(p, {**f, "inj": 0.0, "key": 0.0})
        blend = sm.final_p(p, f, g)
        mkc = sm.market_p(g)
        win = {}
        looks = pr.get(g["id"], [])
        ahead = sorted(x for x in looks if 1.5 <= x[0] < 7.5 and efs.fair(ready, g["id"], g["start"], x[0]))
        if ahead:
            win["E"] = ahead[-1]
            if len(ahead) > 1:
                win["M"] = ahead[0]
        morning = [x for x in looks if 0.05 <= x[0] < 1.5]
        if morning:
            win["G"] = max(morning)
        for side, sign in (("home", 1), ("away", -1)):
            o = (lambda x: x) if side == "home" else (lambda x: 1 - x)
            w = {}
            for name, (days, mh, ma, bh, ba) in win.items():
                pa, pb = 1 / efs._dec(mh), 1 / efs._dec(ma)
                mk = pa / (pa + pb)
                gm = {**g, "ml_home": str(mh), "ml_away": str(ma), "ml_home_open": str(mh), "ml_away_open": str(ma)}
                w[name] = {"days": days, "price": mh if side == "home" else ma, "best": bh if side == "home" else ba,
                           "mkt": o(mk), "blend": o(sm.final_p(p, f, gm))}
            rest, lm = lastg.get(g["id"], {}).get(side, (None, None))
            orest = lastg.get(g["id"], {}).get("away" if side == "home" else "home", (None, None))[0]
            rows.append({"gid": g["id"], "season": season, "side": side, "team": g[side], "opp": g["away" if side == "home" else "home"],
                         "team_name": g[side + "_name"], "opp_name": g[("away" if side == "home" else "home") + "_name"],
                         "start": g["start"], "won": (hs > as_) == (side == "home"), "margin": (hs - as_) * sign,
                         "close": ch if side == "home" else ca, "mkt_close": o(mkc) if mkc is not None else None,
                         "own": o(own), "own_blind": o(own_blind), "blend": o(blend),
                         "inj": f.get("inj", 0.0) * sign, "key": f.get("key", 0.0) * sign,
                         "w": w, "rest": rest, "orest": orest, "last_margin": lm,
                         "neutral": str(g.get("neutral")) == "1", "month": int(g["start"][5:7]),
                         "spread": (lambda s: (None if s is None else s * sign))(sm._num(g.get("spread_home"))),
                         "home": side == "home"})
    print(season, len(rows), round(time.time() - t0))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rows.pkl")
pickle.dump(rows, open(out, "wb"))
print("saved", len(rows), "rows;", len(pr), "games with history;", miss, "unmatched snaps", round(time.time() - t0), "s")
