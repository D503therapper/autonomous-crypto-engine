"""11/12 DEEP PROGRAM - THE FUNNEL REPLAY, TWO ARMS (the 10/27-10/30 funnel - results/studies/thin_1029/funnel_replay.py -
on today's code): every past board day re-built the way the 8:35 AM post builds it (the day's games at their CLOSING
prices, nothing after that day known, the model re-tuned each July 1 on the games before, no injury reports), every
moneyline AND spread candidate dumped with the reads and the gate flags the live board stamps, plus what the board made
of it (Lock / Dog / value play / runner-up dog / NBA favorite play / lean).
  ARM=old  the tune as it was through 11/12 (the blend's dials on the last 900 games; college football read on every game)
  ARM=new  the 11/12 calibration fixes (sports_model.BLEND_STABLE_FROM / NCAAF_FBS_FIT_FROM switched on for every day)
Rows go to OUT (never the repo - ~50 MB an arm).
Usage: ARM=new python results/studies/deep_1112/funnel2.py 2023-10-01 2024-07-05 /path/fA.jsonl"""
import copy, json, os, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ARM = os.environ.get("ARM", "new")
os.environ["REPLAY_PARAMS_DIR"] = os.path.join(os.path.expanduser("~"), ".cache", "d503_deep1112", f"params_{ARM}")
os.makedirs(os.environ["REPLAY_PARAMS_DIR"], exist_ok=True)
os.chdir(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402
import value_play_replay as vpr  # noqa: E402

sm.BLEND_STABLE_FROM = sm.NCAAF_FBS_FIT_FROM = "0000" if ARM == "new" else "9999"
PT = sports.PT
UNITS_DAY = "2026-11-13"        # units by today's rules


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
    for name, fn in (("tier", lambda: sports.leg_tier(dict(d))), ("rank_p", lambda: round(sports.rank_p(d), 4)),
                     ("lean_rank", lambda: round(sports.lean_rank(d), 4)), ("thin", lambda: bool(sports.thin_edge(dict(d)))),
                     ("own_gap", lambda: sports.hockey_own_gap(d))):
        try:
            out[name] = fn()
        except Exception:           # noqa: BLE001
            out[name] = None
    try:
        out["hot_dog"] = bool(sports.hot_dog(dict(d))) if c.get("odds", 0) >= 100 else False
    except Exception:               # noqa: BLE001
        out["hot_dog"] = None
    try:
        sports.score_reason(d)
        out["n_reasons2"] = len(d.get("reasons") or [])
    except Exception:               # noqa: BLE001
        out["n_reasons2"] = None
    if c.get("odds", 0) >= 100 and c.get("market") == "ml":
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
            leans = {(c["game_id"], c["side"], c["market"]): bool(c.get("fill")) for c in sports.viewer_leans(cands, avoid)}
            n_games = len({c["game_id"] for c in cands})
            for c in cands:
                if c.get("market") not in ("ml", "spread"):
                    continue
                k = (c["game_id"], c["side"], c["market"])
                kind, leg = chosen.get(k, (None, c))
                r = self.row(day, kind, leg, real, far, n_games, k in leans)
                r["fill"] = leans.get(k, False)
                rows.append(r)
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
             "gid": c["game_id"], "market": c.get("market"), "line": c.get("line"),
             "team": c.get("team"), "opp": c.get("opp"), "home": c.get("home"), "odds": c["odds"], "dec": round(c["dec"], 4),
             "p": round(c["p"], 4), "p_market": None if c.get("p_market") is None else round(c["p_market"], 4),
             "edge": round(c["edge"], 4), "edge_own": None if c.get("edge_own") is None else round(c["edge_own"], 4),
             "w_p": c.get("w_p"), "raw_own": c.get("raw_own"), "elo_edge": c.get("elo_edge"),
             "season_games": c.get("season_games"), "nba_fav_w": c.get("nba_fav_w"), "trap": bool(c.get("trap")),
             "n_reasons": len(c.get("reasons") or []), "drift": c.get("drift"), "waiting": bool(c.get("waiting")),
             "key_out_me": bool(c.get("key_out_me")), "stype": c.get("stype"), "n_games": n_games,
             "result": res, "score": f"{g['home_score']}-{g['away_score']}" if g else None,
             "total": (g or {}).get("total"), "spread_home": (g or {}).get("spread_home"),
             "ml_home": (g or {}).get("ml_home"), "ml_away": (g or {}).get("ml_away")}
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
