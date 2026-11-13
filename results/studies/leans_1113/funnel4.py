"""11/13 FABLE - SHOULD THE COLLEGE HOOPS LEANS CARRY UNITS: THE REPLAY BOARD, COLLEGE HOOPS DAYS, TODAY'S CODE.
The 11/12 funnel (results/studies/deep_1112/funnel2.py - tools/value_play_replay.Replay) on today's code: every board
day with a priced college hoops game re-built the way the 8:35 AM post builds it (the day's games at their CLOSING
prices, nothing after that day known, the model re-tuned each July 1 on the games before, no injury reports). The WHOLE
board is built (every sport - the unit plays take their games first, as live); only the college hoops rows are written.
EVERY DATE GATE IS OPEN: every sports.*_FROM / sports_model.*_FROM that holds a 2026 date is set to "0000", so the
replay runs the code that posts a board TODAY (11/13: the leans judged on lean_read - a spread on its studied weights -
the CBB10 weights, the deep-program weights, the weighed-under favorite rule, the stack play, the slots, the gap play).
One row a college hoops moneyline / spread candidate, with:
  lean      viewer_leans() took it (2 a sport, after the unit plays' games) - what the board would show, by the lean
            rule as it ran on 11/13 (sports.LEANS_1113_FROM shut - the study's subject)
  lean_any  the side viewer_leans() would take in that game with no 2-a-sport cap (the lean rule's whole pool)
  lean_new / lean_any_new   the same two with the 11/13 fix on (a college hoops spread lean needs a studied weight)
  kind      the unit play the board made of it (lock / dog / play / gap / ncaabplay / stackplay / floor ...)
Rows -> the OUT file (never the repo). The study weights were fit with every season seen (only the model's params are
blind) - the train / held-out split of a weight-picked cell is NOT a clean out-of-sample test; the analysis says so.
Usage: python results/studies/leans_1113/funnel4.py 2023-11-01 2024-04-10 /path/s2023.jsonl"""
import copy, json, os, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.environ["REPLAY_PARAMS_DIR"] = os.path.join(os.path.expanduser("~"), ".cache", "d503_leans1113", "params")
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
for mod in (sports, sm):
    for k in dir(mod):
        v = getattr(mod, k)
        if "_FROM" in k and isinstance(v, str) and v[:4] == "2026":
            setattr(mod, k, "0000")
            OPENED.append(k)
        elif "_FROM" in k and isinstance(v, dict) and v and all(isinstance(x, str) and x[:4] == "2026" for x in v.values()):
            setattr(mod, k, {a: "0000" for a in v})
            OPENED.append(k)
sports.stick = lambda c, pool: c            # (no lean memory in a replay - and never a write to data/sports/lean_sides.json)
PT = sports.PT


def safe(fn, d=None):
    try:
        return fn()
    except Exception:               # noqa: BLE001
        return d


class Funnel(vpr.Replay):
    def day(self, day):
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else day.year - 1}-{vpr.TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        real = {g["id"]: g for g in self.by_day.get(day, [])}
        if not any(g.get("league") == "ncaab" and g.get("ml_home", "") != "" and g.get("status") == "final" for g in real.values()):
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
        chosen, avoid = {}, set()
        b = sports.make_board(cands)
        for kind in ("lock", "dog", "solo"):
            if b.get(kind):
                for leg in b[kind]["legs"]:
                    avoid.add(leg["game_id"])
                    chosen[(leg["game_id"], leg["side"], leg["market"])] = kind
        for kind, pool, cap in (("play", sports.plays, 99), ("gap", sports.gap_plays, 99), ("dogplay", sports.dog_plays, sports.DOG_PLAY_MAX),
                                ("ncaabplay", sports.ncaab_play_plays, 3), ("stackplay", sports.ncaab_stack_plays, sports.NCAAB_STACK_PLAY_MAX_DAY),
                                ("nbafav", sports.nba_fav_plays, 99), ("nbafloor", sports.nba_floor_plays, 1)):
            used = set(avoid)
            if kind == "ncaabplay":                                # (the dog slot may take the gap play's dog - same side)
                twin = {g_: s_ for (g_, s_, m_), k_ in chosen.items() if k_ == "gap" and g_.startswith("ncaab")}
                used -= set(twin)
                src = [c for c in cands if c["game_id"] not in twin or c["side"] == twin[c["game_id"]]]
            else:
                src = cands
            if kind == "nbafloor" and any(g_.startswith("nba") for g_, _, _ in chosen):
                continue                                           # (the NBA floor: only an NBA day with no NBA unit play)
            try:
                got = pool(src, used)[:cap]
            except Exception as e:  # noqa: BLE001
                print(f"{day} {kind}: failed {str(e)[:100]}", flush=True)
                got = []
            for c in got:
                chosen.setdefault((c["game_id"], c["side"], c["market"]), kind)
                avoid.add(c["game_id"])
        n_units = len(chosen)
        for c in safe(lambda: sports.floor_plays(cands, avoid), []):    # the daily floor, as post_board fills it: up to
            if len(chosen) >= sports.FLOOR_MIN:                         # FLOOR_MIN unit plays; a skipped dog / a dog under
                break                                                   # FLOOR_SECOND_SCORE only when the board has none
            if len(chosen) >= sports.FLOOR_FALLBACK_MIN and (c.get("floor_fallback") or (c.get("floor_score") if c.get("floor_score") is not None else -99) < sports.FLOOR_SECOND_SCORE):
                continue
            chosen.setdefault((c["game_id"], c["side"], c["market"]), "floor")
            avoid.add(c["game_id"])
        def lean_sets(gate):                                       # gate "9999": the lean rule as it ran 11/13 (the study's
            sports.LEANS_1113_FROM = gate                          # subject); "0000": with the 11/13 fix (a college hoops
            a = {}                                                 # spread lean needs a studied weight for the side)
            for i, c in enumerate(sports.viewer_leans(cands, avoid)):
                a[(c["game_id"], c["side"], c["market"])] = (i, bool(c.get("fill")))
            keep = sports.LEAN_PER_SPORT
            sports.LEAN_PER_SPORT = 10 ** 6
            try:
                b = {(c["game_id"], c["side"], c["market"]): bool(c.get("fill")) for c in sports.viewer_leans(cands, avoid)}
            finally:
                sports.LEAN_PER_SPORT = keep
            return a, b
        leans, any_ = lean_sets("9999")
        leans2, any2 = lean_sets("0000")
        far = now + timedelta(days=30)
        rows = []
        for c in cands:
            if c.get("league") != "ncaab" or c.get("market") not in ("ml", "spread"):
                continue
            g = real.get(c["game_id"])
            k = (c["game_id"], c["side"], c["market"])
            d = copy.deepcopy(c)
            r = {"date": day.isoformat(), "gid": c["game_id"], "side": c["side"], "market": c["market"], "line": c.get("line"),
                 "team": c.get("team"), "opp": c.get("opp"), "home": c.get("home"), "neutral": (g or {}).get("neutral"),
                 "stype": c.get("stype"), "odds": c["odds"], "dec": round(c["dec"], 4), "p": round(c["p"], 4),
                 "p_market": None if c.get("p_market") is None else round(c["p_market"], 4),
                 "edge_own": None if c.get("edge_own") is None else round(c["edge_own"], 4), "w_p": c.get("w_p"),
                 "games_in": c.get("games_in"), "opp_games_in": c.get("opp_games_in"), "trap": bool(c.get("trap")),
                 "rank_p": safe(lambda: round(sports.rank_p(d), 4)), "lean_read": safe(lambda: round(sports.lean_read(d), 4)),
                 "lean_rank": safe(lambda: round(sports.lean_rank(d), 4)), "fighting": safe(lambda: bool(sports.fighting(d))),
                 "stack": c.get("spread_stack"), "stack_n": c.get("spread_stack_n"),
                 "kind": chosen.get(k), "game_taken": c["game_id"] in avoid,
                 "lean": k in leans, "lean_i": leans.get(k, (None, None))[0], "fill": leans.get(k, (None, False))[1],
                 "lean_any": k in any_, "fill_any": any_.get(k, False), "n_units": n_units,
                 "lean_new": k in leans2, "fill_new": leans2.get(k, (None, False))[1], "lean_any_new": k in any2,
                 "sw": safe(lambda: sports.spread_weights(d)),
                 "result": sports.grade_leg(c, g, far) if g else None,
                 "hs": (g or {}).get("home_score"), "as": (g or {}).get("away_score"),
                 "spread_home": (g or {}).get("spread_home"), "ml_home": (g or {}).get("ml_home"), "ml_away": (g or {}).get("ml_away"),
                 "ml_home_open": (g or {}).get("ml_home_open"), "ml_away_open": (g or {}).get("ml_away_open")}
            if c["market"] == "ml" and c["odds"] >= 100:
                r["dog_score"] = safe(lambda: round(sports.dog_score(copy.deepcopy(c)), 2))
                r["dog_read"] = safe(lambda: sports.ncaab_dog_read(copy.deepcopy(c)))
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
            t1 = time.time()
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
            if d.day in (1, 15) or d == d1 or os.environ.get("VERBOSE"):
                print(f"{d}: {n} rows so far, {time.time() - t0:.0f}s (day {time.time() - t1:.0f}s)", flush=True)
            d += timedelta(days=1)
    print(f"done: {n} rows in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
