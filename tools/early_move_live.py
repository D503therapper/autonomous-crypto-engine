"""📈 THE MOVE MODEL ON THIS SEASON'S LIVE LINES (10/7 - check 5 of tools/early_move_recheck.py). The engine has kept
every price change since 10/1 (data/sports/line_history, hourly - sports_data.record_lines). For every NFL / college
game in it: the FIRST price recorded after both teams' last games ended (the fair first look) and the LAST price before
kickoff. Every +100..+220 dog at that first price gets scored by the model fit through 2025 (results/
early_move_recheck.json, never saw 2026) with the facts a live scan would have (early_move_recheck.move_facts /
move_x - the engine's schedule, nothing from a later price), the engine's read taken pre-game from the replay (no
result leaks into the ratings). Then: how the model's picks moved
and did vs every band dog, and how our posted early plays (data/sports/early.json) moved. Saves
results/early_move_live.json. No network."""
import json
import os
import sys
from datetime import timezone, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_move_recheck as R      # noqa: E402
import sports_data as sd            # noqa: E402
import sports_early as se           # noqa: E402
import sports_model as sm           # noqa: E402

BLIND = {"inj": 0.0, "key": 0.0, "weather": 0.0, "cold": 0.0}
MIN_FINALS = 8


def _imp(o):
    return 1 / se._dec(o)


def history(hist_dir=None):
    """{game id: [(t, home ml, away ml)]} for football, in time order."""
    d = hist_dir or sd.LINE_HIST_DIR
    out = {}
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".jsonl"))
    except OSError:
        return out
    for fn in files:
        with open(os.path.join(d, fn)) as f:
            for x in f:
                try:
                    r = json.loads(x)
                except ValueError:
                    continue
                if str(r.get("g", "")).split(":")[0] not in ("nfl", "ncaaf"):
                    continue
                h, a = se._int(r.get("h")), se._int(r.get("a"))
                if h is None or a is None:
                    continue
                out.setdefault(r["g"], []).append((r["t"], h, a))
    for v in out.values():
        v.sort()
    return out


def looks(games, hist, now=None):
    """{game id: (first fair (t, h, a), last before kickoff (t, h, a))}."""
    now = now or datetime.now(timezone.utc)
    sched = se._schedule(games)
    out = {}
    for gid, rows in hist.items():
        g = games.get(gid)
        if not g or not g.get("start") or (g.get("stype") or "?") not in sd.REAL:
            continue
        r = se.ready(sched, g)
        since = r.strftime("%Y-%m-%dT%H:%MZ") if r else ""
        fair = [x for x in rows if x[0] >= since]
        if not fair:
            continue
        first = fair[0]
        if se._t(first[0]) >= se._t(g["start"]):
            continue
        before = [x for x in rows if x[0] < g["start"]]
        out[gid] = (first, before[-1] if before else first)
    return out


def own_reads(games, model):
    """{game id: home own read (blind)} - finished games from the replay (pre-game features), upcoming from today's
    ratings."""
    out = {}
    params = model.get("params") or {}
    for lg in ("nfl", "ncaaf"):
        p = params.get(lg) or sm.default_params(lg)
        if "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if f.get("known", 0) >= 3:
                out[g["id"]] = sm.own_p(p, {**f, **BLIND})
    elo = sm.ratings(games, model)
    for g in games.values():
        if g.get("league") in ("nfl", "ncaaf") and g.get("status") == "pre" and g["id"] not in out:
            f = elo[g["league"]].features(g)
            if f.get("known", 0) >= 3:
                out[g["id"]] = sm.own_p((params.get(g["league"]) or sm.default_params(g["league"])), {**f, **BLIND})
    return out


def rows(games, hist, model, mm, now=None):
    sched = se._schedule(games)
    own = own_reads(games, model)
    out = []
    for gid, (first, last) in looks(games, hist, now).items():
        g = games[gid]
        lg = g["league"]
        if lg not in mm or gid not in own:
            continue
        _, fh, fa = first
        mk_h = _imp(fh) / (_imp(fh) + _imp(fa))
        for side, other, odds, l_odds in (("home", "away", fh, last[1]), ("away", "home", fa, last[2])):
            if not se.SPOT_DOG[0] <= odds <= se.SPOT_DOG[1]:
                continue
            mk = mk_h if side == "home" else 1 - mk_h
            o = own[gid] if side == "home" else 1 - own[gid]
            f = R.move_facts(sched, g, side, other, lg, o, mk, odds)
            score, hit = R.money_coming(lg, f, mm)
            won = None
            if g.get("status") == "final":
                try:
                    hs, as_ = float(g["home_score"]), float(g["away_score"])
                    won = None if hs == as_ else (hs > as_) == (side == "home")
                except (KeyError, ValueError, TypeError):
                    pass
            out.append({"gid": gid, "league": lg, "team": g.get(f"{side}_name"), "start": g["start"], "first": odds,
                        "last": l_odds, "cents_in": R.cents(odds, l_odds), "score": score, "pick": hit, "won": won,
                        "gap": round(o - mk, 4)})
    return out


def grade(rs):
    fin = [r for r in rs if r["won"] is not None]
    if not rs:
        return None
    g = {"n": len(rs), "finals": len(fin), "moved_to_dog": round(sum(1 for r in rs if r["cents_in"] > 0) / len(rs), 3),
         "moved_10": round(sum(1 for r in rs if r["cents_in"] >= 10) / len(rs), 3),
         "avg_cents_in": round(sum(r["cents_in"] for r in rs) / len(rs), 1)}
    if fin:
        g["won"] = round(sum(r["won"] for r in fin) / len(fin), 3)
        g["roi"] = round(sum((se._dec(r["first"]) - 1) if r["won"] else -1 for r in fin) / len(fin), 3)
        g["roi_close"] = round(sum((se._dec(r["last"]) - 1) if r["won"] else -1 for r in fin) / len(fin), 3)
    return g


def our_plays(games, hist):
    """Our posted early plays: the price we got, the price at kickoff (or now), moved, result."""
    out = []
    for p in se.load().get("picks", []):
        if p.get("market") == "total":
            continue
        g = games.get(p["game_id"]) or {}
        rs = hist.get(p["game_id"]) or []
        before = [x for x in rs if x[0] < (g.get("start") or "9")]
        now_o = (before[-1][1] if p["side"] == "home" else before[-1][2]) if before else se._int(g.get(f"ml_{p['side']}"))
        out.append({"team": p["team"], "league": p["league"], "spot": p.get("spot"), "got": p["odds"], "now": now_o,
                    "cents_in": R.cents(p["odds"], now_o), "result": p.get("result")})
    return out


def main(save=True):
    games = sd.load_games()
    try:
        with open(os.path.join(sd.DATA, "model.json")) as f:
            model = json.load(f)
    except (OSError, ValueError):
        model = {"params": {}}
    try:
        with open("results/early_move_recheck.json") as f:
            rc = json.load(f)
        mm = {lg: v["live_model"] for lg, v in rc.items() if v.get("live_model")}
    except (OSError, ValueError, KeyError):
        print("run tools/early_move_recheck.py first (the live model's weights)")
        return {}
    hist = history()
    rs = rows(games, hist, model, mm)
    rep = {}
    for lg in ("nfl", "ncaaf"):
        mine = [r for r in rs if r["league"] == lg]
        every, picks = grade(mine), grade([r for r in mine if r["pick"]])
        agrees = None
        if picks and picks.get("finals", 0) >= MIN_FINALS and every:
            agrees = picks["roi"] > every["roi"] and picks["moved_to_dog"] > every["moved_to_dog"]
        rep[lg] = {"every band dog": every, "model picks": picks, "agrees": agrees,
                   "picks": [r for r in mine if r["pick"]]}
        print(f"\n== {lg.upper()} since 10/1 (line_history): every +100..+220 dog {every} \n   model picks {picks}\n   agrees: {agrees}")
        for r in mine:
            if r["pick"]:
                print(f"     {r['team']:22s} {r['start'][:10]} +{r['first']} -> {('+' if r['last'] > 0 else '') + str(r['last'])} "
                      f"({r['cents_in']:+d}c)  score {r['score']}  {'won' if r['won'] else 'lost' if r['won'] is False else 'pending'}")
    rep["our_early_plays"] = our_plays(games, hist)
    print("\n== our posted early plays:")
    for p in rep["our_early_plays"]:
        print(f"   {p['team']:16s} {p['league']} {p['spot']:9s} got +{p['got']} -> {p['now']} ({p['cents_in']}c)  {p['result']}")
    if save:
        os.makedirs("results", exist_ok=True)
        with open("results/early_move_live.json", "w") as f:
            json.dump(rep, f, indent=1)
    return rep


if __name__ == "__main__":
    main()
