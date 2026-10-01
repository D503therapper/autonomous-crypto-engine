"""WHAT CHANGES SEASON TO SEASON (10/1, the owner: "every season is so different - what's so different season to
season, how does that change our model, and what can we expect this season?"). For every sport, every season since
2018 (closing prices): scoring, home edge, close games, upsets, how favorites / dogs / price bands paid, favorites vs
dogs on the spread, overs, how often the price was right (market log loss), and the engine's own accuracy (each season
graded by an engine trained only on the 3 before it). This season so far is shown against the last 3, and anything
outside their range is flagged. Saves results/season_drift.json."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd    # noqa: E402
import sports_model as sm   # noqa: E402

LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")
FIRST = 2018


def season_of(lg, start):
    y, m = int(start[:4]), int(start[5:7])
    if lg == "mlb":
        return y
    return y if m >= 7 else y - 1


def _dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def stats(rows):
    n = len(rows)
    if not n:
        return None
    out = {"games": n}
    pts = [r["hs"] + r["as"] for r in rows]
    out["points_per_game"] = round(sum(pts) / n, 1)
    out["home_win"] = round(sum(r["hs"] > r["as"] for r in rows if not r["neutral"]) / max(1, sum(not r["neutral"] for r in rows)), 3)
    out["home_margin"] = round(sum(r["hs"] - r["as"] for r in rows if not r["neutral"]) / max(1, sum(not r["neutral"] for r in rows)), 2)
    close = {"nfl": 7, "ncaaf": 7, "nba": 5, "ncaab": 5, "nhl": 1, "mlb": 1}[rows[0]["lg"]]
    out["close_games"] = round(sum(abs(r["hs"] - r["as"]) <= close for r in rows) / n, 3)
    ml = [r for r in rows if r["mh"] is not None]
    if ml:
        favw, dogs, bands, ll = 0, [], {}, 0.0
        for r in ml:
            ph, pa = 1 / _dec(r["mh"]), 1 / _dec(r["ma"])
            p = ph / (ph + pa)
            hw = r["hs"] > r["as"]
            ll -= math.log(max(1e-6, p if hw else 1 - p))
            fav_home = p >= .5
            favw += (hw == fav_home)
            o, won = (r["ma"], not hw) if fav_home else (r["mh"], hw)
            if o >= 100:
                dogs.append((o, won))
                b = "+100..+149" if o < 150 else "+150..+249" if o < 250 else "+250 and up"
                bands.setdefault(b, []).append((o, won))
        roi = lambda xs: round(sum((_dec(o) - 1) if w else -1 for o, w in xs) / len(xs), 3) if xs else None
        out["favorites_won"] = round(favw / len(ml), 3)
        out["dog_win_rate"] = round(sum(w for _, w in dogs) / len(dogs), 3) if dogs else None
        out["dogs_roi"] = roi(dogs)
        for b in ("+100..+149", "+150..+249", "+250 and up"):
            out[f"dogs {b} roi"] = roi(bands.get(b, []))
        out["price_log_loss"] = round(ll / len(ml), 4)          # lower = the books priced the season better
    sp = [r for r in rows if r["sp"] is not None and r["hs"] - r["as"] + r["sp"] != 0]
    if sp:
        fc = [((r["hs"] - r["as"] + r["sp"] > 0) == (r["sp"] < 0)) for r in sp if r["sp"] != 0]
        out["favorites_covered"] = round(sum(fc) / len(fc), 3) if fc else None
        out["home_covered"] = round(sum(r["hs"] - r["as"] + r["sp"] > 0 for r in sp) / len(sp), 3)
    to = [r for r in rows if r["tot"] is not None and r["hs"] + r["as"] != r["tot"]]
    if to:
        out["overs"] = round(sum(r["hs"] + r["as"] > r["tot"] for r in to) / len(to), 3)
    return out


def engine_accuracy(games, lg, season):
    """The engine's own pick right % that season, trained only on the 3 seasons before it."""
    lo = f"{season}-07-01" if lg != "mlb" else f"{season}-01-01"
    hi = f"{season + 1}-07-01" if lg != "mlb" else f"{season + 1}-01-01"
    learn_lo = f"{season - 3}-07-01" if lg != "mlb" else f"{season - 3}-01-01"
    learn = {k: g for k, g in games.items() if learn_lo <= g.get("start", "") < lo}
    p = sm.tune(learn, lg)
    if not p or "w" not in p:
        return None
    _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
    right = n = 0
    for g, f, *_ in played:
        if not lo <= g["start"] < hi:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError):
            continue
        if hs == as_:
            continue
        right += (sm.own_p(p, f) >= .5) == (hs > as_)
        n += 1
    return round(right / n, 3) if n else None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    rep = {}
    for lg in LEAGUES:
        games = sd.load_games(lg)
        by = {}
        for g in sm.finals(games, lg):
            hs, as_ = num(g.get("home_score")), num(g.get("away_score"))
            if hs is None or as_ is None:
                continue
            s = season_of(lg, g["start"])
            if s < FIRST:
                continue
            mh, ma = num(g.get("ml_home")), num(g.get("ml_away"))
            by.setdefault(s, []).append({"lg": lg, "hs": hs, "as": as_, "neutral": str(g.get("neutral")) == "1",
                                         "mh": mh if mh and ma and abs(mh) >= 100 and abs(ma) >= 100 else None,
                                         "ma": ma if mh and ma and abs(mh) >= 100 and abs(ma) >= 100 else None,
                                         "sp": num(g.get("spread_home")), "tot": num(g.get("total"))})
        seasons = sorted(by)
        res = {}
        for s in seasons:
            st = stats(by[s])
            if st:
                if s >= FIRST + 3:
                    st["engine_right"] = engine_accuracy(games, lg, s)
                res[s] = st
        cur = seasons[-1] if seasons else None
        print(f"\n===================== {lg.upper()}  (seasons {seasons[0] if seasons else '-'}-{cur}; {cur} = this season so far, "
              f"{res.get(cur, {}).get('games', 0)} games)")
        keys = [k for k in res.get(seasons[-2] if len(seasons) > 1 else cur, {}) if k != "games"]
        print("   " + "".join(f"{str(s)[-4:]:>8}" for s in seasons) + "   this season vs the last 3")
        flags = {}
        for k in keys:
            vals = [res[s].get(k) for s in seasons]
            last3 = [res[s].get(k) for s in seasons[-4:-1] if res[s].get(k) is not None]
            now = res.get(cur, {}).get(k)
            note = ""
            if now is not None and len(last3) == 3 and res[cur]["games"] >= 30:
                lo, hi = min(last3), max(last3)
                if now > hi:
                    note = f"HIGHER than all of the last 3 ({lo}..{hi})"
                elif now < lo:
                    note = f"LOWER than all of the last 3 ({lo}..{hi})"
                if note:
                    flags[k] = {"now": now, "last3": last3}
            print(f"   {k:20s}" + "".join(f"{('-' if v is None else v):>8}" for v in vals) + ("   << " + note if note else ""))
        rep[lg] = {"seasons": res, "this_season_flags": flags}
    os.makedirs("results", exist_ok=True)
    with open("results/season_drift.json", "w") as f:
        json.dump(rep, f, indent=1, default=str)


if __name__ == "__main__":
    main()
