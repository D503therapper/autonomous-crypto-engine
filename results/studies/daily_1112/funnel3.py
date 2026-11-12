"""11/12 DAILY - FOOTBALL'S MONEY CHECK: THE REPLAY BOARD, FOOTBALL DAYS ONLY, EVERY ARM IN ONE PASS.
The 11/12 deep program's funnel (results/studies/deep_1112/funnel2.py) on today's code: every board day with a football
game re-built the way the 8:35 AM post builds it (the day's games at their CLOSING prices, nothing after that day known,
the model re-tuned each July 1 on the games before, no injury reports). The WHOLE board is built (every sport's
candidates compete for the Lock / the Dog, as live); only the football moneyline rows are written.
  ARM=old  the blend's dials as they were through 11/12 (the last 900 games) - TODAY'S football - one board: "old"
  ARM=new  the honest dials (fit on every game, pulled to zero; the FBS fit) - boards, one per variant:
           hon   today's money check (own read over the price) on the honest dials (BLEND_STABLE_SKIP = ())
           wt    the re-based check: a dog's weighed dog read over the price, a favorite's weighed read (w_p) over it
           wtd   dogs only re-based          wtf   favorites only re-based
           wt4   wt + the NFL Dog gate at 4 (the honest NFL dog score rarely reaches 8)
Rows -> ~/.cache/d503_daily1112/<arm>/f?.jsonl (never the repo).
NOTE: the 11/12 rows were made with the FIRST version of the hook - on the honest dials a football dog's check was the
close + its WHOLE dog score over the price, in PLACE of the own-read rule. The wired version (sports.weighed_dog_beats /
dog_own_ok) adds the score's STUDY part check ON TOP of the own-read rule on the old dials; mc4_dog_split.py tests that
one on the OLD rows (it needs no re-run: same reads, a filter). Re-running wt / wtd today gives no football dogs.
Usage: ARM=new python results/studies/daily_1112/funnel3.py 2023-10-01 2024-07-05 /path/fA.jsonl"""
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

if ARM == "new":
    sm.BLEND_STABLE_FROM = sm.NCAAF_FBS_FIT_FROM = "0000"
    sm.BLEND_STABLE_SKIP = ()
else:
    sm.BLEND_STABLE_FROM = sm.NCAAF_FBS_FIT_FROM = "9999"
PT = sports.PT
UNITS_DAY = "2026-11-14"
FB = ("nfl", "ncaaf")
VARIANTS = {"old": [("old", {})]}.get(ARM) or [
    ("hon", {}),
    ("wt", {"FOOTBALL_CHECK_FROM": "0000", "FOOTBALL_CHECK_PARTS": ("dog", "fav")}),
    ("wtd", {"FOOTBALL_CHECK_FROM": "0000", "FOOTBALL_CHECK_PARTS": ("dog",)}),
    ("wtf", {"FOOTBALL_CHECK_FROM": "0000", "FOOTBALL_CHECK_PARTS": ("fav",)}),
    ("wt4", {"FOOTBALL_CHECK_FROM": "0000", "FOOTBALL_CHECK_PARTS": ("dog", "fav"), "NFL_DOG_GATE_WEIGHED": 4.0}),
]


def units(kind, c):
    pk = {"kind": kind, "date": UNITS_DAY, "legs": [dict(c)], "status": "open"}
    try:
        return sports.units_for(pk)
    except Exception:               # noqa: BLE001
        return None


def board(cands):
    """{(gid, side, market): (kind, leg)} - the 8:35 board's unit plays (Lock / Dog / solo, value plays, the runner-up
    dog, the NBA favorite play)."""
    chosen, avoid = {}, set()
    b = sports.make_board(cands)
    for kind in ("lock", "dog", "solo"):
        if b.get(kind):
            for leg in b[kind]["legs"]:
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
    except Exception:               # noqa: BLE001
        pass
    return chosen


class Funnel(vpr.Replay):
    def day(self, day):
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else day.year - 1}-{vpr.TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        real = {g["id"]: g for g in self.by_day.get(day, [])}
        if not any(g.get("league") in FB and g.get("ml_home", "") != "" and g.get("status") == "final" for g in real.values()):
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
        picks = {}
        for name, setting in VARIANTS:
            keep = {k: getattr(sports, k) for k in setting}
            for k, v in setting.items():
                setattr(sports, k, v)
            try:
                picks[name] = board(copy.deepcopy(cands))
            except Exception as e:  # noqa: BLE001
                print(f"{day} {name}: board failed {str(e)[:120]}", flush=True)
                picks[name] = {}
            finally:
                for k, v in keep.items():
                    setattr(sports, k, v)
        far = now + timedelta(days=30)
        rows = []
        for c in cands:
            if c.get("league") not in FB or c.get("market") != "ml":
                continue
            g = real.get(c["game_id"])
            k = (c["game_id"], c["side"], c["market"])
            d = copy.deepcopy(c)
            try:
                sc = round(sports.dog_score(d), 2) if c.get("odds", 0) >= 100 else None
            except Exception:       # noqa: BLE001
                sc = None
            r = {"date": day.isoformat(), "league": c["league"], "side": c["side"], "gid": c["game_id"], "market": "ml",
                 "team": c.get("team"), "opp": c.get("opp"), "home": c.get("home"), "odds": c["odds"], "dec": round(c["dec"], 4),
                 "p": round(c["p"], 4), "p_market": None if c.get("p_market") is None else round(c["p_market"], 4),
                 "edge_own": None if c.get("edge_own") is None else round(c["edge_own"], 4), "w_p": c.get("w_p"),
                 "raw_own": c.get("raw_own"), "trap": bool(c.get("trap")), "dog_score": sc, "n_games": len({x["game_id"] for x in cands}),
                 "result": sports.grade_leg(c, g, far) if g else None,
                 "score": f"{g['home_score']}-{g['away_score']}" if g else None}
            for name, _ in VARIANTS:
                kind, leg = picks[name].get(k, (None, None))
                r["k_" + name] = kind
                if kind:
                    keep = {kk: getattr(sports, kk) for kk in dict(VARIANTS)[name]}
                    for kk, v in dict(VARIANTS)[name].items():
                        setattr(sports, kk, v)
                    try:
                        u = units({"dogplay": "play", "nbafav": "play"}.get(kind, kind), leg)
                    finally:
                        for kk, v in keep.items():
                            setattr(sports, kk, v)
                    r["u_" + name] = u
            rows.append(r)
        self.feed(day)
        return rows


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
