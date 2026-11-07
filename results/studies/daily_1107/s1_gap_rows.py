"""11/7 S1 rows: the 🔍 college football gap rule's inputs on EVERY priced college game 2018-26 (the 10/31 gap_all.py
build + the game id, both team ids, each team's game number this season, the raw Elo gap, FBS-ness).
Walk-forward: each season's params tuned on the 3 seasons before it. The raw read = sm.own_p (the live raw_own minus
the injury points - the history holds no injury reports). Rows -> ~/.cache/d503_studies/_gap1107_rows.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402  (chdirs to the repo)
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_players as sp  # noqa: E402

games = sd.load_games("ncaaf")
fin_all = sm.finals(games, "ncaaf")
gno = {}   # (gid, team) -> game number in season (1 = first)
cnt = {}
for g in fin_all:
    s = lib.season(g["start"])
    for tm in (g["home"], g["away"]):
        cnt[(s, tm)] = cnt.get((s, tm), 0) + 1
        gno[(g["id"], tm)] = cnt[(s, tm)]
fbs_memo = {}
rows = []
for season in range(2018, 2027):
    lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
    p = sm.tune(learn, "ncaaf")
    if not p or "w" not in p:
        print("no params", season)
        continue
    _, played = sm.replay(fin_all, p["k"], p["hfa"], "ncaaf")
    for g, f, *_ in played:
        if not lo <= g["start"] < hi:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or not ch or not ca:
            continue
        nvh = lib.nv(ch, ca)
        own = sm.own_p(p, f)
        dk = g["start"][:10]
        if dk not in fbs_memo:
            fb = sp.fbs_set(games, g["start"])
            fbs_memo[dk] = None if fb is None else {str(x) for x in fb}
        fbs = fbs_memo[dk]
        kind = None if fbs is None else sum(str(t) in fbs for t in (g["home"], g["away"]))
        for side, sign in (("home", 1), ("away", -1)):
            o = ch if side == "home" else ca
            tm, op = (g["home"], g["away"]) if side == "home" else (g["away"], g["home"])
            rows.append({"season": season, "gid": g["id"], "start": g["start"], "side": side, "team": tm, "opp": op,
                         "tn": g[side + "_name"], "on": g[("away" if side == "home" else "home") + "_name"],
                         "odds": o, "dec": lib.dec(o), "own": own if side == "home" else 1 - own,
                         "nv": nvh if side == "home" else 1 - nvh, "won": (hs > as_) == (side == "home"),
                         "margin": sign * (hs - as_), "sp": lib.num(g.get("spread_home")),
                         "fbs": kind, "elo": sign * f["elo_pts"], "elo_raw": sign * f.get("elo_raw", f["elo_pts"]),
                         "form": sign * f["form"], "gno": gno.get((g["id"], tm)), "ogno": gno.get((g["id"], op)),
                         "neutral": str(g.get("neutral")) == "1"})
    print(season, len(rows), flush=True)
json.dump(rows, open(os.path.join(lib.CACHE, "_gap1107_rows.json"), "w"))
print("rows", len(rows))
