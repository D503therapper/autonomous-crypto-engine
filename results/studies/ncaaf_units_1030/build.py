"""Build every college football side row (tools/early_football_study.build) once and save it, plus the game ids /
names / weekday so the weeknight studies can slice it. Also saves the per-game first-fair price. No look-ahead: the
early prices come from ready_at / fair (both teams' last games over)."""
import json
import os
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import early_football_study as efs  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rows_ncaaf.json")

t = time.time()
games = sd.load_games("ncaaf")
# monkeypatch: we want the game id on every row -> wrap rows.append via a replaced build. Simpler: re-implement the loop
# by calling build and matching rows back to games on (season, side, won, close, month, neutral) is ambiguous, so we
# patch efs.build's inner by copying it with the id attached.
pr, miss = efs.match(efs.snapshots(efs.SPORTS["ncaaf"]), games)
lastg = efs.last_games(games, "ncaaf")
ready = efs.ready_at(games, "ncaaf")
rows = []
E, M, G = efs.E, efs.M, efs.G
for season in efs.SEASONS + (2026,):
    lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
    p = sm.tune(learn, "ncaaf")
    if not p or "w" not in p:
        print("no params", season)
        continue
    _, played = sm.replay(sm.finals(games, "ncaaf"), p["k"], p["hfa"], "ncaaf")
    for g, f, *_ in played:
        if not lo <= g["start"] < hi or g["id"] not in pr:
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
        win = {}
        ahead = sorted(x for x in pr[g["id"]] if 1.5 <= x[0] < 7.5 and efs.fair(ready, g["id"], g["start"], x[0]))
        if ahead:
            win[E] = ahead[-1]
            if len(ahead) > 1:
                win[M] = ahead[0]
        morning = [x for x in pr[g["id"]] if 0.05 <= x[0] < 1.5]
        if morning:
            win[G] = max(morning)
        for side, sign in (("home", 1), ("away", -1)):
            o = (lambda x: x) if side == "home" else (lambda x: 1 - x)
            w = {}
            for name, (_, mh, ma, bh, ba) in win.items():
                pa, pb = 1 / efs._dec(mh), 1 / efs._dec(ma)
                mk = pa / (pa + pb)
                gm = {**g, "ml_home": str(mh), "ml_away": str(ma), "ml_home_open": str(mh), "ml_away_open": str(ma)}
                w[name] = {"price": mh if side == "home" else ma, "best": bh if side == "home" else ba,
                           "mkt": o(mk), "blend": o(sm.final_p(p, f, gm))}
            rest, lm = lastg.get(g["id"], {}).get(side, (None, None))
            orest, olm = lastg.get(g["id"], {}).get("away" if side == "home" else "home", (None, None))
            rows.append({"gid": g["id"], "start": g["start"], "season": season, "side": side,
                         "team": g[side], "opp": g["away" if side == "home" else "home"],
                         "team_name": g[side + "_name"], "opp_name": g[("away" if side == "home" else "home") + "_name"],
                         "won": (hs > as_) == (side == "home"), "margin": (hs - as_) * sign,
                         "close": ch if side == "home" else ca, "close_opp": ca if side == "home" else ch,
                         "own": o(own), "own_blind": o(own_blind), "blend_close": o(sm.final_p(p, f, g)),
                         "elo_p": o(f.get("p_elo", 0.5)), "elo_pts": f.get("elo_pts", 0.0) * sign, "f": {k: (v if isinstance(v, (int, float, str, bool)) or v is None else str(v)) for k, v in f.items()},
                         "w": w, "rest": rest, "orest": orest, "last_margin": lm, "opp_last_margin": olm,
                         "neutral": str(g.get("neutral")) == "1", "month": int(g["start"][5:7])})
    print(season, len(rows), round(time.time() - t))
json.dump(rows, open(OUT, "w"))
print("rows", len(rows), "priced games", len(pr), "miss", miss, round(time.time() - t))
print("feature keys sample:", sorted(f.keys())[:40] if isinstance(f, dict) else type(f))
