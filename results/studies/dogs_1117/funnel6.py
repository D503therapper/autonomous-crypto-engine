"""11/17 UNDERDOG EDGE STUDY - THE REPLAY BOARD ON TODAY'S CODE, EVERY DOG ROW WITH ITS PARTS (R3).
The 11/14 football funnel (results/studies/football_1114/funnel5.py - tools/value_play_replay.Replay) pointed at EVERY
sport: every board day re-built the way the 8:35 AM post builds it (the day's games at their CLOSING prices, nothing
after that day known, the model re-tuned each July 1 on the games before, no injury reports), EVERY sports.* /
sports_model.* / sports_form.* *_FROM gate holding a 2026 date set to "0000" (the code that posts a board on 11/17).
One row a MONEYLINE candidate (dogs AND favorites; baseball left out of the rows, not out of the board):
  kind     the unit play the board made of it (lock / dog / solo / play / gap / dogplay / ncaabplay / nbafav / nbafloor /
           floor / night) or None;  units = its size under today's sizing (units_for, dated 2026-11-17)
  the reads (p, edge_own, w_p, p_market, raw_own), the gate flags (trap, fighting, good, dog_own_ok, weighed_dog_beats,
  the hockey own gap, the named reasons), the dog score + its base + dog_spots + the NBA dog weights, and - for the
  parts study - every plain flag the candidate carries ("x": the scalars on the candidate, dog_ctx, dog_more).
Rows -> ~/.cache/d503_dogs1117/rows (never the repo). The study weights inside the dog score were fit with these seasons
seen (only the model's params are blind) - a score-picked cell's train / held split is not a clean out-of-sample test.
Usage: python results/studies/dogs_1117/funnel6.py 2023-10-01 2024-07-05 /path/fA.jsonl"""
import copy, json, os, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.environ["REPLAY_PARAMS_DIR"] = os.environ.get("REPLAY_PARAMS_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "d503_dogs1117", "params")
os.makedirs(os.environ["REPLAY_PARAMS_DIR"], exist_ok=True)
os.chdir(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402
import value_play_replay as vpr  # noqa: E402

OPENED = []
import sports_form as sf_  # noqa: E402
for mod in (sports, sm, sf_):
    for k in dir(mod):
        v = getattr(mod, k)
        if k == "DOGS_1117_FROM":
            continue                    # (this study's own wiring stays OFF in its own replay: R3 = the code BEFORE it)
        if "_FROM" in k and isinstance(v, str) and v[:4] == "2026":
            setattr(mod, k, "0000")
            OPENED.append(k)
        elif "_FROM" in k and isinstance(v, dict) and v and all(isinstance(x, str) and x[:4] == "2026" for x in v.values()):
            setattr(mod, k, {a: "0000" for a in v})
            OPENED.append(k)
sports.stick = lambda c, pool: c            # (no lean memory in a replay - and never a write to data/sports/lean_sides.json)
PT = sports.PT
FB = ("nfl", "ncaaf")
UNITS_DAY = "2026-11-17"
KEEP = ("p", "edge", "edge_own", "w_p", "raw_own", "p_market", "line", "games_in", "opp_games_in", "trap", "hurt",
        "spread_stack", "rule_a", "own_p", "elo_p", "p_raw", "neutral", "stype", "tier")


CORE = {"odds", "dec", "edge", "edge_own", "p", "p_market", "league", "market", "home", "team", "opp", "game_id", "side", "start",
        "pick", "reasons", "dog_ctx", "dog_more", "line", "w_p", "raw_own", "team_id", "trap", "waiting", "hurt", "tier"}


def cp(c):
    """a cheap copy of a candidate for a function that may write on it (dog_p, reasons...): shallow + its lists / dicts one level down"""
    d = dict(c)
    for k in ("reasons", "dog_ctx", "dog_more"):
        v = d.get(k)
        if isinstance(v, list):
            d[k] = list(v)
        elif isinstance(v, dict):
            d[k] = dict(v)
    return d


def parts(c):
    """what each fact on the candidate is worth in its dog score: the score with the fact taken off (the cap lifted so a
    capped stack still shows every part) -> {fact: points}. 'ctx.' / 'more.' = a fact inside dog_ctx / dog_more."""
    old = sports.STUDY_CAP
    sports.STUDY_CAP = 99
    out = {}
    try:
        full = sports.dog_score(cp(c))
        for pre, key in (("", None), ("ctx.", "dog_ctx"), ("more.", "dog_more")):
            src = c if key is None else (c.get(key) or {})
            for k in list(src):
                if (key is None and k in CORE) or src[k] is None:
                    continue
                d2 = cp(c)
                (d2 if key is None else d2[key]).pop(k, None)
                try:
                    s2 = sports.dog_score(d2)
                except Exception:           # noqa: BLE001
                    continue
                if abs(full - s2) > 1e-6:
                    out[pre + k] = round(full - s2, 2)
        out["_uncapped"] = round(full, 2)
    finally:
        sports.STUDY_CAP = old
    return out


def safe(fn, d=None):
    try:
        return fn()
    except Exception:               # noqa: BLE001
        return d


def units(kind, c):
    pk = {"kind": {"dogplay": "play", "gap": "play", "floor": "play", "nbafav": "play", "nbafloor": "play"}.get(kind, kind),
          "date": UNITS_DAY, "legs": [dict(c)], "status": "open"}
    if kind == "floor":
        pk["floor"] = {"dog_score": c.get("floor_score")}
    if kind == "gap":
        pk["gap"] = c.get("gap")
    return safe(lambda: sports.units_for(pk))


class Funnel(vpr.Replay):
    def day(self, day):
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else day.year - 1}-{vpr.TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        real = {g["id"]: g for g in self.by_day.get(day, [])}
        if not any(g.get("ml_home", "") != "" and g.get("status") == "final" for g in real.values()):
            self.feed(day)
            return []
        if self.tuned_before != tune_at:
            self.tune(tune_at)
        now = datetime(day.year, day.month, day.day, vpr.BOARD_AT[0], vpr.BOARD_AT[1], tzinfo=PT).astimezone(timezone.utc)
        snap = dict(self.hist)
        for g in real.values():
            c = copy.copy(g)
            c["status"], c["home_score"], c["away_score"] = "pre", "", ""
            c["inj_home"], c["inj_away"] = "", ""
            snap[g["id"]] = c
        self.states(snap, now)
        cands = sports.candidates(snap, self.model, now, day, None)
        cands = [c for c in cands if not c.get("hurt")]
        chosen, legs, avoid = {}, {}, set()
        b = safe(lambda: sports.make_board(cands), {})
        for kind in ("lock", "dog", "solo"):
            if b.get(kind):
                for leg in b[kind]["legs"]:
                    avoid.add(leg["game_id"])
                    k = (leg["game_id"], leg["side"], leg["market"])
                    chosen[k], legs[k] = kind, leg
        for kind, pool, cap in (("play", sports.plays, 99), ("gap", sports.gap_plays, 99), ("dogplay", sports.dog_plays, sports.DOG_PLAY_MAX),
                                ("ncaabplay", sports.ncaab_play_plays, 3), ("stackplay", sports.ncaab_stack_plays, sports.NCAAB_STACK_PLAY_MAX_DAY),
                                ("nbafav", sports.nba_fav_plays, 99), ("nbafloor", sports.nba_floor_plays, 1)):
            used = set(avoid)
            if kind == "nbafloor" and any(g_.startswith("nba") for g_, _, _ in chosen):
                continue
            got = safe(lambda: pool(cands, used)[:cap], [])
            for c in got:
                k = (c["game_id"], c["side"], c["market"])
                chosen.setdefault(k, kind)
                legs.setdefault(k, c)
                avoid.add(c["game_id"])
        for c in safe(lambda: sports.floor_plays(cands, avoid), []):
            if len(chosen) >= sports.FLOOR_MIN:
                break
            if len(chosen) >= sports.FLOOR_FALLBACK_MIN and (c.get("floor_fallback") or (c.get("floor_score") if c.get("floor_score") is not None else -99) < sports.FLOOR_SECOND_SCORE):
                continue
            k = (c["game_id"], c["side"], c["market"])
            chosen.setdefault(k, "floor")
            legs.setdefault(k, c)
            avoid.add(c["game_id"])
        night = {}
        if day.weekday() in sports.NIGHT_DAYS:
            for gid in {c["game_id"] for c in cands if c["league"] == "nfl"} - avoid:
                nb = safe(lambda: sports.night_pick([c for c in cands if c["game_id"] == gid]))
                if nb:
                    leg = nb["legs"][0]
                    k = (leg["game_id"], leg["side"], leg["market"])
                    night[k] = "lean" if nb.get("lean") else "unit"
                    if not nb.get("lean"):
                        chosen.setdefault(k, "night")
                        legs.setdefault(k, leg)
        leans = {}
        for i, c in enumerate(safe(lambda: sports.viewer_leans(cands, avoid), [])):
            leans[(c["game_id"], c["side"], c["market"])] = (i, bool(c.get("fill")))
        far = now + timedelta(days=30)
        rows = []
        for c in cands:
            if c.get("league") == "mlb" or c.get("market") != "ml":
                continue
            g = real.get(c["game_id"])
            k = (c["game_id"], c["side"], c["market"])
            d = cp(c)
            r = {"date": day.isoformat(), "league": c["league"], "gid": c["game_id"], "side": c["side"], "market": c["market"],
                 "team": c.get("team"), "opp": c.get("opp"), "home": c.get("home"), "neutral_g": (g or {}).get("neutral"),
                 "odds": c["odds"], "dec": round(c["dec"], 4), "start": (g or {}).get("start"),
                 "rank_p": safe(lambda: round(sports.rank_p(d), 4)), "lean_read": safe(lambda: round(sports.lean_read(d), 4)),
                 "fighting": safe(lambda: bool(sports.fighting(d))), "good": safe(lambda: bool(sports.good(d))),
                 "real_value": safe(lambda: bool(sports.real_value(d))), "own_beats": safe(lambda: bool(sports.own_beats(d))),
                 "leg_tier": safe(lambda: sports.leg_tier(d)), "reasons": (c.get("reasons") or [])[:8],
                 "waiting": bool(c.get("waiting")), "drift": c.get("drift"), "n_reasons": len(c.get("reasons") or []),
                 "kind": chosen.get(k), "game_taken": c["game_id"] in avoid, "night": night.get(k),
                 "lean": k in leans, "fill": leans.get(k, (None, False))[1],
                 "result": sports.grade_leg(c, g, far) if g else None,
                 "hs": (g or {}).get("home_score"), "as": (g or {}).get("away_score"),
                 "spread_home": (g or {}).get("spread_home"), "total_g": (g or {}).get("total"),
                 "ml_home": (g or {}).get("ml_home"), "ml_away": (g or {}).get("ml_away"),
                 "ml_home_open": (g or {}).get("ml_home_open"), "ml_away_open": (g or {}).get("ml_away_open"),
                 "n_cands": len(cands)}
            for kk in KEEP:
                v = c.get(kk)
                if isinstance(v, (int, float, str, bool)) or v is None:
                    r[kk] = round(v, 4) if isinstance(v, float) else v
            if c["market"] == "spread":
                r["sw"] = safe(lambda: sports.spread_weights(d))
            if c["odds"] >= 100:
                r["dog_score"] = safe(lambda: round(sports.dog_score(cp(c)), 2))
                r["dog_base"] = safe(lambda: round(sports.dog_score_base(cp(c)), 2))
                r["dog_spots"] = safe(lambda: round(sports.dog_spots(cp(c)), 2))
                r["nba_w"] = safe(lambda: round(sports.nba_dog_weights(cp(c)), 2))
                r["wdb"] = safe(lambda: bool(sports.weighed_dog_beats(cp(c))))
                r["dog_own_ok"] = safe(lambda: bool(sports.dog_own_ok(cp(c))))
                r["dog_gate"] = safe(lambda: bool(sports.dog_gate(cp(c))))
                r["own_gap_ok"] = safe(lambda: bool(sports.hockey_own_gap_ok(cp(c))))
                r["floor_skip"] = safe(lambda: bool(sports.floor_skip(cp(c))))
                r["hangover"] = safe(lambda: bool(sports.hangover(cp(c))))
                r["overreact"] = safe(lambda: bool(sports.overreact(cp(c))))
                r["mkt_faded"] = safe(lambda: bool(sports.market_faded(cp(c))))
                r["hot_dog"] = safe(lambda: bool(sports.hot_dog(cp(c))))
                r["vs_bye"] = safe(lambda: bool(sports.nfl_vs_bye(cp(c))))
                r["thin"] = safe(lambda: bool(sports.thin_edge(cp(c))))
                r["parts"] = safe(lambda: parts(c), {}) if c["league"] != "ncaab" else {}
                if c["league"] == "ncaab":
                    d3 = cp(c)
                    r["dog_read"] = safe(lambda: sports.ncaab_dog_read(d3))
                    r["read_parts"] = d3.get("dog_read_parts")
                    r["dog_read_ok"] = safe(lambda: bool(sports.ncaab_dog_read_ok(cp(c))))
                d2 = cp(c)
                safe(lambda: sports.score_reason(d2))
                r["n_reasons2"] = len(d2.get("reasons") or [])
                x = {}
                for src_ in (c, c.get("dog_ctx") or {}, c.get("dog_more") or {}):
                    for kk, v in src_.items():
                        if kk in r or kk in ("start", "team", "opp", "game_id", "league", "side", "market", "pick", "odds", "dec"):
                            continue
                        if isinstance(v, bool) or v is None:
                            if v is not None:
                                x[kk] = v
                        elif isinstance(v, (int, float)):
                            x[kk] = round(v, 4)
                        elif isinstance(v, str) and len(v) <= 24:
                            x[kk] = v
                r["x"] = x
            if r["kind"]:
                r["units"] = units(r["kind"], legs.get(k) or c)
            rows.append(r)
        self.feed(day)
        return rows


def main(start, end, out):
    t0 = time.time()
    print("date gates opened:", len(OPENED), flush=True)
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
                f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            n += len(rows)
            if d.day in (1, 15) or d == d1:
                print(f"{d}: {n} rows so far, {time.time() - t0:.0f}s", flush=True)
            d += timedelta(days=1)
    print(f"done: {n} rows in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
