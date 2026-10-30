"""THE FUNNEL REPLAY (10/27): every past board day re-built like tools/value_play_replay.py (closing prices, params re-tuned
each July, no injury reports), but EVERY moneyline candidate is dumped with every gate flag the live board applies - so each
gate's kill count and the money a loosened gate would have made can be read offline. Usage:
  python funnel_replay.py 2023-10-01 2024-06-30 out.jsonl
"""
import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("REPO") or "/home/user/autonomous-crypto-engine/.claude/worktrees/agent-ae23cc9a369e50331"
os.environ.setdefault("REPLAY_PARAMS_DIR", os.path.join(HERE, "params"))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_players as sp     # noqa: E402
import value_play_replay as vpr  # noqa: E402

PT = sports.PT
UNITS_DAY = "2026-10-30"        # units by today's rules


def flags(c):
    d = dict(c)
    out = {}
    for name, fn in (("lock_ok", sports.lock_ok), ("own_agrees", sports.own_agrees), ("own_beats", sports.own_beats),
                     ("real_value", sports.real_value), ("beats_price", sports.beats_price), ("fighting", sports.fighting),
                     ("good", sports.good), ("proven", sports.proven), ("nhl_pricey", sports.nhl_pricey),
                     ("hockey_fav_bad", sports.hockey_fav_bad), ("money_against", sports.money_against),
                     ("nba_week_one", sports.nba_week_one), ("dog_own_ok", sports.dog_own_ok)):
        try:
            out[name] = bool(fn(dict(d)))
        except Exception as e:      # noqa: BLE001
            out[name] = f"ERR {str(e)[:30]}"
    try:
        out["tier"] = sports.leg_tier(dict(d))
    except Exception:               # noqa: BLE001
        out["tier"] = None
    try:
        out["rank_p"] = round(sports.rank_p(d), 4)
    except Exception:               # noqa: BLE001
        out["rank_p"] = None
    try:
        out["thin"] = bool(sports.thin_edge(dict(d)))
    except Exception:               # noqa: BLE001
        out["thin"] = None
    try:
        out["own_gap"] = sports.hockey_own_gap(d)
    except Exception:               # noqa: BLE001
        out["own_gap"] = None
    try:
        out["hot_dog"] = bool(sports.hot_dog(dict(d))) if c.get("odds", 0) >= 100 else False
    except Exception:               # noqa: BLE001
        out["hot_dog"] = None
    try:
        sports.score_reason(d)
        out["n_reasons2"] = len(d.get("reasons") or [])
    except Exception:               # noqa: BLE001
        out["n_reasons2"] = None
    if c.get("odds", 0) >= 100:
        try:
            out["dog_score"] = round(sports.dog_score(d), 2)
        except Exception:           # noqa: BLE001
            out["dog_score"] = None
        dd = dict(d)
        try:
            out["dog_gate"] = bool(sports.dog_gate(dd))
            out["dog_p"] = dd.get("dog_p")
        except Exception:           # noqa: BLE001
            out["dog_gate"] = None
    return out


def units(kind, c):
    pk = {"kind": kind, "date": UNITS_DAY, "legs": [dict(c)], "status": "open"}
    try:
        return sports.units_for(pk)
    except Exception:               # noqa: BLE001
        return None


class Funnel(vpr.Replay):
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
            cands = [c for c in cands if not c.get("hurt")]
            board = sports.make_board(cands)
            far = now + timedelta(days=30)
            chosen = {}
            avoid = set()
            for kind in ("lock", "dog", "solo"):
                b = board.get(kind)
                if b:
                    for leg in b["legs"]:
                        avoid.add(leg["game_id"])
                        chosen[(leg["game_id"], leg["side"], leg["market"])] = (kind, leg)
            for c in sports.plays(cands, avoid):
                chosen.setdefault((c["game_id"], c["side"], c["market"]), ("play", c))
                avoid.add(c["game_id"])
            for c in sports.dog_plays(cands, avoid):
                chosen.setdefault((c["game_id"], c["side"], c["market"]), ("dogplay", c))
                avoid.add(c["game_id"])
            try:
                for c in sports.nba_fav_plays(cands, avoid):
                    chosen.setdefault((c["game_id"], c["side"], c["market"]), ("nbafav", c))
                    avoid.add(c["game_id"])
            except Exception as e:  # noqa: BLE001
                print("nbafav failed", str(e)[:80], flush=True)
            leans = {(c["game_id"], c["side"], c["market"]) for c in sports.viewer_leans(cands, avoid)}
            n_games = len({c["game_id"] for c in cands})
            for c in cands:
                if c.get("market") != "ml":
                    continue
                k = (c["game_id"], c["side"], c["market"])
                kind, leg = chosen.get(k, (None, c))
                rows.append(self.row(day, kind, leg, real, far, n_games, k in leans))
        self.feed(day)
        return rows

    def row(self, day, kind, c, real, far, n_games, lean):
        g = real.get(c["game_id"])
        res = sports.grade_leg(c, g, far) if g else None
        f = flags(c)
        u = None
        if kind:
            u = units({"dogplay": "play", "nbafav": "play"}.get(kind, kind), c)
            if kind == "nbafav":
                u = sports.NBA_FAV_UNITS
        r = {"date": day.isoformat(), "kind": kind, "lean": lean, "units": u, "league": c["league"], "side": c["side"],
             "team": c.get("team"), "opp": c.get("opp"), "home": c.get("home"), "odds": c["odds"], "dec": round(c["dec"], 4),
             "p": round(c["p"], 4), "p_market": None if c.get("p_market") is None else round(c["p_market"], 4),
             "edge": round(c["edge"], 4), "edge_own": None if c.get("edge_own") is None else round(c["edge_own"], 4),
             "w_p": c.get("w_p"), "raw_own": c.get("raw_own"), "elo_edge": c.get("elo_edge"),
             "season_games": c.get("season_games"), "nba_fav_w": c.get("nba_fav_w"), "trap": bool(c.get("trap")),
             "n_reasons": len(c.get("reasons") or []), "drift": c.get("drift"), "waiting": bool(c.get("waiting")),
             "key_out_me": bool(c.get("key_out_me")), "stype": c.get("stype"), "n_games": n_games,
             "result": res, "score": f"{g['home_score']}-{g['away_score']}" if g else None}
        r.update(f)
        return r


def main(start, end, out):
    t0 = time.time()
    games = sd.load_games()
    cache = sp.load()
    rp = Funnel(games, cache)
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
            except Exception as e:  # noqa: BLE001
                print(f"{d}: FAILED {str(e)[:160]}", flush=True)
                rp.feed(d)
                rows = []
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()
            n += len(rows)
            if d.day in (1, 15) or d == d1:
                print(f"{d}: {n} rows so far, {time.time() - t0:.0f}s", flush=True)
            d += timedelta(days=1)
    print(f"done: {n} rows in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
