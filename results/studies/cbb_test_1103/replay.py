"""🏀 THE COLLEGE HOOPS TEST - the honest replay (11/3; the owner: "scared money don't make no money ... we should have unit
plays pretty much every day"). Every past college hoops board day re-built like tools/value_play_replay.py (the day's
games set back to 'pre' at their CLOSING prices, the ratings / form / dog states from the games before it, the model
params re-tuned each July 1 on the seasons before - blind), with TODAY's sports.candidates (every 11/3 college hoops
weight in it: the early road dog, the Nov-Dec away small favorite, the efficiency filter, the rubber / skid dog, the top
scorer out, the ranked road team, the hot-ATS side, the glass, the big home favorite). EVERY college hoops side is dumped
with its whole weighed read next to the price and the real result, so the selection rule can be chosen OFFLINE on
2018-22 (analyze.py) and graded on 2023-25 held out.

Usage: python replay.py 2018-11-01 2019-04-10 out.jsonl     (one season a process; REPLAY_PARAMS_DIR caches the params)

Caveats (the same as every board replay): no injury reports in history (hurt / waiting never fire - the top-scorer-out
weight comes from box scores, so it does), the prices are the CLOSE (the 8 AM number is a different price), the weights
were built on 2018-25 (each cut train 2018-22 / held 2023-25 - the rule picked here is chosen on 2018-22 only)."""
import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("REPO") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))
os.environ.setdefault("REPLAY_PARAMS_DIR", os.path.join(HERE, "params"))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402
import value_play_replay as vpr  # noqa: E402

PT = sports.PT
KEEP = ("game_id", "league", "side", "team", "opp", "market", "line", "odds", "dec", "p", "p_market", "edge", "edge_own",
        "raw_own", "w_p", "elo_edge", "home", "neutral", "games_in", "opp_games_in", "trap", "drift", "hot_key",
        "top_out", "opp_top_out", "ranked_road", "vs_ranked_road", "ats_gap", "reb_gap", "ncaab_away_fav", "ncaab_eff_fav",
        "ncaab_top_out_fav", "rubber_dog", "ncaab_skid", "eff_p", "opp_dog_pts", "lost_last", "opp_lost_last", "ats_run",
        "big_cover", "coach", "fired_on", "first_timer", "rested_vs_b2b", "tired_vs_rested", "form_state", "start", "stype")


def _flags(c):
    """The read every rule reads: the dog's whole score / the favorite's weighed read / the spread's rank, each next to
    the price - and every gate flag the live board applies."""
    d = dict(c)
    out = {k: c.get(k) for k in KEEP}
    out["dog_ctx"] = c.get("dog_ctx")
    out["dog_more"] = {k: v for k, v in (c.get("dog_more") or {}).items() if not isinstance(v, (list, dict))}
    out["n_reasons"] = len(c.get("reasons") or [])
    try:
        out["fighting"] = bool(sports.fighting(dict(d)))
    except Exception as e:          # noqa: BLE001
        out["fighting"] = f"ERR {str(e)[:30]}"
    try:
        out["rank_p"] = round(sports.rank_p(d), 4)
    except Exception:               # noqa: BLE001
        out["rank_p"] = None
    try:
        out["early_lock"] = sports.ncaab_early_lock(d)
    except Exception:               # noqa: BLE001
        out["early_lock"] = None
    try:
        out["early_road_dog"] = bool(sports.ncaab_early_road_dog(d))
        out["big_home_fav"] = bool(sports.ncaab_big_home_fav(d))
    except Exception:               # noqa: BLE001
        pass
    if c.get("market") == "ml" and c.get("odds", 0) >= 100:
        try:
            own = (c.get("edge_own", c["edge"]) + 1) / c["dec"]
            base = (own - (c.get("p_market") or own)) * 100
            if base > sports.OWN_CAP:
                base = 0.0 if c.get("league") in sports.OWN_TRAP else sports.OWN_CAP
            out["dog_base"] = round(base, 2)
            out["dog_score"] = round(sports.dog_score(dict(d)), 2)
            out["dog_spots"] = round(sports.dog_spots(dict(d)), 2)
        except Exception as e:      # noqa: BLE001
            out["dog_score"] = f"ERR {str(e)[:30]}"
    return out


class CBB(vpr.Replay):
    """The board replay on college hoops only (every other league's games left out - the ratings / states / params are
    the college hoops ones; the test never reads another sport)."""

    def tune(self, cutoff):
        cut_iso = cutoff.isoformat()
        store = os.path.join(vpr.PARAMS_DIR, f"params_{cut_iso}.json") if vpr.PARAMS_DIR else None
        if store and os.path.exists(store):
            with open(store) as f:
                self.model["params"] = json.load(f)
        else:
            before = {k: g for k, g in self.all.items() if g.get("start", "")[:10] < cut_iso and g.get("status") == "final"}
            self.model["params"] = {}
            for lg in sd.LEAGUES:
                if lg == "ncaab":
                    p = sm.tune(before, lg, None)
                    self.model["params"][lg] = p or sm.default_params(lg)
                else:
                    self.model["params"][lg] = sm.default_params(lg)
            if store:
                os.makedirs(os.path.dirname(store), exist_ok=True)
                with open(store + ".tmp", "w") as f:
                    json.dump(self.model["params"], f)
                os.replace(store + ".tmp", store)
        self.tuned_before = cutoff
        self.elo = {}
        p = self.model["params"]["ncaab"]
        self.elo["ncaab"], _ = sm.replay(sm.finals(self.hist, "ncaab"), p["k"], p["hfa"], "ncaab")

    def feed(self, day):
        new = {}
        for g in self.by_day.get(day, []):
            self.hist[g["id"]] = g
            new[g["id"]] = g
        if "ncaab" in self.elo:
            for g in sm.finals(new, "ncaab"):
                self.elo["ncaab"].update(g)

    def day(self, day):
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else day.year - 1}-{vpr.TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        if self.tuned_before != tune_at:
            self.tune(tune_at)
        now = datetime(day.year, day.month, day.day, vpr.BOARD_AT[0], vpr.BOARD_AT[1], tzinfo=PT).astimezone(timezone.utc)
        snap = dict(self.hist)
        real = {}
        for g in self.by_day.get(day, []):
            real[g["id"]] = g
            c = copy.copy(g)
            c["status"], c["home_score"], c["away_score"] = "pre", "", ""
            c["inj_home"], c["inj_away"] = "", ""
            snap[g["id"]] = c
        rows = []
        if any(g.get("ml_home", "") != "" and g.get("status") == "final" for g in real.values()):
            self.states(snap, now)
            cands = sports.candidates(snap, self.model, now, day, None)
            far = now + timedelta(days=30)
            n_games = len({c["game_id"] for c in cands})
            for c in cands:
                if c.get("league") != "ncaab" or c.get("market") not in ("ml", "spread"):
                    continue
                g = real.get(c["game_id"])
                r = _flags(c)
                r["date"] = day.isoformat()
                r["n_games"] = n_games
                r["result"] = sports.grade_leg(c, g, far) if g else None
                r["score"] = f"{g['home_score']}-{g['away_score']}" if g else None
                rows.append(r)
        self.feed(day)
        return rows


def main(start, end, out):
    t0 = time.time()
    games = {k: g for k, g in sd.load_games().items() if g.get("league") == "ncaab"}
    cache = {"ncaab": sp.load().get("ncaab") or []}
    rp = CBB(games, cache)
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    for day in sorted(d for d in rp.by_day if d < d0):
        for g in rp.by_day[day]:
            rp.hist[g["id"]] = g
    n = 0
    with open(out, "w") as f:
        d = d0
        while d <= d1:
            try:
                rows = rp.day(d)
            except Exception as e:                             # noqa: BLE001
                print(f"{d}: FAILED {str(e)[:160]}", flush=True)
                import traceback
                traceback.print_exc()
                rp.feed(d)
                rows = []
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            n += len(rows)
            if d.day in (1, 15) or d == d1:
                print(f"{d}: {n} rows so far, {time.time() - t0:.0f}s", flush=True)
            d += timedelta(days=1)
    print(f"done: {n} rows in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
