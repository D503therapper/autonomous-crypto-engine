"""THE BOARD REPLAY (10/9): every past board day re-built the way the 8:35 AM PT post would have built it - the day's
games set back to 'pre' at their closing prices, every game after that day gone, the ratings / form / dog states built
from the games before it, the model re-tuned each July on the seasons before (blind). Writes one row per Lock / Dog /
value play (with its rank on the day, gate, read, price) and the real result - the raw material for the 10/2 unit
system, the 10/4 no-cap replay and the 10/9 "why do the value plays lose" study.

Usage: python tools/value_play_replay.py 2023-01-01 2023-12-31 out.jsonl [step]   (run the years in parallel - 7-14 s a
board day; step 2 = every other day; REPLAY_PARAMS_DIR=<dir> caches the tuned params so parallel runs share them)

Caveats (same as 10/2): no injury reports exist in history (sports.hurt / waiting never fire), the study weights and
gates were built with every season seen (only the model params are blind), and the prices are the CLOSE."""
import copy
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_form              # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402
import sports_coaches           # noqa: E402
import sports_coach_changes     # noqa: E402

PT = sports.PT
BOARD_AT = (8, 35)
TUNE_MONTH_DAY = "07-01"        # params re-tuned every July 1 on everything before it (a season never sees itself)
PARAMS_DIR = os.environ.get("REPLAY_PARAMS_DIR")   # set it to cache the tuned params (parallel chunks share a cutoff)


def _pt_date(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT).date()


def _utc(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


class Replay:
    def __init__(self, games, cache):
        self.all = games
        self.cache = cache                                     # the box-score rows (sports_players), every league
        self.by_day = defaultdict(list)
        for g in games.values():
            if g.get("start"):
                self.by_day[_pt_date(g["start"])].append(g)
        self.hist = {}                                         # every game before the current day
        self.elo = {}                                          # incremental ratings per league
        self.model = {"params": {}, "log": []}
        self.tuned_before = None
        sm.ratings = lambda games, model: self.elo             # (the day's ratings: built once, fed day by day)
        sports.fair_open = lambda games, g: None               # (no hourly line history before 9/2026)
        sports.announce_pick = lambda pk: None
        # speed: the box-score files load once (not every day), and the context / spots / explorer fact indexes (17 s
        # to build on 100k games) are rebuilt once a month from that day's snapshot - a month stale at worst, never ahead
        import sports_roster as sr
        memo = {}
        real_load = sr.load

        def load(league, seasons=None):
            k = (league, tuple(seasons or ()))
            if k not in memo:
                memo[k] = real_load(league, seasons)
            return memo[k]
        sr.load = load
        self.idx = {}
        self.idx_month = None

        def index(games, kind):
            if kind not in self.idx:
                import sports_context, sports_spots, sports_explorer
                self.idx[kind] = {"context": sports_context.Index, "spots": sports_spots.index,
                                  "explorer": sports_explorer.index}[kind](games)
            return self.idx[kind]
        sports._index = index
        self.first_home = {}                                   # {(league, home): first regular-season home game this season}

        def home_opener(games, g):                             # (the engine's scans every game per candidate - indexed)
            if (g.get("stype") or "") != "2":
                return False
            first = self.first_home.get((g.get("league"), g["home"]))
            return first is None or first >= g["start"]
        sports.home_opener = home_opener

    def cache_before(self, cutoff_iso):
        return {lg: [r for r in rows if r.get("start", "") < cutoff_iso] for lg, rows in self.cache.items()}

    def tune(self, cutoff):
        """Blind params: every league tuned on the finals before `cutoff` (a date)."""
        cut_iso = cutoff.isoformat()
        store = os.path.join(PARAMS_DIR, f"params_{cut_iso}.json") if PARAMS_DIR else None
        if store and os.path.exists(store):
            with open(store) as f:
                self.model["params"] = json.load(f)
        else:
            before = {k: g for k, g in self.all.items() if g.get("start", "")[:10] < cut_iso and g.get("status") == "final"}
            cache = self.cache_before(cut_iso)
            sm.KEY_EDGE = sp.key_edges(before, cache)
            for lg in sd.LEAGUES:
                p = sm.tune(before, lg, self.model["params"].get(lg))
                self.model["params"][lg] = p or sm.default_params(lg)
            if store:
                with open(store + ".tmp", "w") as f:
                    json.dump(self.model["params"], f)
                os.replace(store + ".tmp", store)
        self.tuned_before = cutoff
        self.elo = {}
        for lg in sd.LEAGUES:                                  # fresh ratings with the new params, up to self.hist
            p = self.model["params"][lg]
            self.elo[lg], _ = sm.replay(sm.finals(self.hist, lg), p["k"], p["hfa"], lg)

    def feed(self, day):
        """The day's real games join history; the ratings take its finals."""
        new = {}
        for g in self.by_day.get(day, []):
            self.hist[g["id"]] = g
            new[g["id"]] = g
        for lg in sd.LEAGUES:
            if lg not in self.elo:
                continue
            for g in sm.finals(new, lg):
                self.elo[lg].update(g)

    def states(self, snap, now):
        iso = now.strftime("%Y-%m-%dT%H:%MZ")
        cache = self.cache_before(iso)
        sp.CACHE = cache
        S = sports
        S.HOT_KEY.clear(); S.HOT_KEY.update(sports_form.hot_sides(snap, cache, iso))
        S.TEAM_STATE.clear(); S.TEAM_STATE.update(sports_form.team_states(snap, iso))
        S.LAST_STARTS.clear(); S.LAST_STARTS.update(sports_form.last_starts(snap))
        a_, m_ = sports_form.ats_states(snap)
        S.ATS[0].clear(); S.ATS[0].update(a_); S.ATS[1].clear(); S.ATS[1].update(m_)
        S.SEASON_START.clear(); S.SEASON_START.update(S.season_starts(snap, now))
        for box, fn in ((S.COACH, lambda: sports_coaches.states(iso)), (S.FIRED, lambda: sports_coach_changes.recent(iso)),
                        (S.FIRST_TIMER, lambda: sports_coach_changes.first_timers(snap, iso)),
                        (S.DOG_ST, lambda: sports_form.dog_states(snap, iso)), (S.PDO, lambda: sports_form.pdo_states(snap, iso)),
                        (S.SV_SLUMP, lambda: (str(t) for t in sports_form.sv_slump())),
                        (S.OUTSHOT, lambda: sports_form.outshot_states(cache.get("nhl") or [], iso))):
            try:
                box.clear()
                box.update(fn())
            except Exception:                                  # noqa: BLE001
                pass
        y, m = now.year, now.month
        season0 = f"{y if m >= 7 else y - 1}-07-01"
        self.first_home = {}
        for g in snap.values():
            if g.get("stype") == "2" and g.get("start", "") >= season0:
                k = (g.get("league"), g["home"])
                if k not in self.first_home or g["start"] < self.first_home[k]:
                    self.first_home[k] = g["start"]
        S._TOT_STATE.clear()
        if self.idx_month != now.strftime("%Y-%m"):             # the fact indexes: rebuilt on the month's first board
            self.idx.clear()
            self.idx_month = now.strftime("%Y-%m")
        # the key-player edge for TODAY's games: the last starter before today (never the box score of the game itself)
        today = {k: g for k, g in snap.items() if g.get("status") == "pre"}
        try:
            sm.KEY_EDGE = {**{k: v for k, v in sm.KEY_EDGE.items() if k not in today}, **sp.key_edges(today, cache)}
        except Exception:                                      # noqa: BLE001
            pass

    def day(self, day):
        """The board for one day -> rows."""
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= TUNE_MONTH_DAY else day.year - 1}-{TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        if self.tuned_before != tune_at:
            self.tune(tune_at)
        now = datetime(day.year, day.month, day.day, BOARD_AT[0], BOARD_AT[1], tzinfo=PT).astimezone(timezone.utc)
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
            avoid = set()
            for kind in ("lock", "dog", "solo"):
                b = board.get(kind)
                if b:
                    for leg in b["legs"]:
                        avoid.add(leg["game_id"])
                        rows.append(self.row(day, kind, 0, leg, real, far, len(cands)))
            for i, c in enumerate(sports.plays(cands, avoid), 1):
                rows.append(self.row(day, "play", i, c, real, far, len(cands)))
        self.feed(day)
        return rows

    def row(self, day, kind, rank, c, real, far, n_cands):
        g = real.get(c["game_id"])
        res = sports.grade_leg(c, g, far) if g else None
        dog_gate = False
        try:
            dog_gate = bool(sports.dog_gate(dict(c)))
        except Exception:                                      # noqa: BLE001
            pass
        dsc = None
        if c.get("market") == "ml" and c.get("odds", 0) >= 100:
            try:
                dsc = round(sports.dog_score(c), 2)
            except Exception:                                  # noqa: BLE001
                pass
        return {"date": day.isoformat(), "kind": kind, "rank": rank, "league": c["league"], "market": c["market"],
                "side": c["side"], "team": c.get("team"), "opp": c.get("opp"), "odds": c["odds"], "dec": round(c["dec"], 4),
                "line": c.get("line"), "p": round(c["p"], 4), "p_market": round(c.get("p_market") or 1 / c["dec"], 4),
                "edge": round(c["edge"], 4), "edge_own": None if c.get("edge_own") is None else round(c["edge_own"], 4),
                "dog_p": c.get("dog_p"), "w_p": c.get("w_p"), "rank_p": round(sports.rank_p(c), 4),
                "tier": sports.leg_tier(c), "proven": sports.proven(c), "dog_gate": dog_gate, "dog_score": dsc,
                "lock_ok": sports.lock_ok(c), "own_agrees": sports.own_agrees(c), "stype": c.get("stype"),
                "reasons": [str(r)[:60] for r in (c.get("reasons") or [])][:4], "result": res, "n_cands": n_cands,
                "score": f"{g['home_score']}-{g['away_score']}" if g else None}


def main(start, end, out, step=1):
    """step=2: every other day gets a board (the days between still feed the ratings) - half the time, half the sample."""
    t0 = time.time()
    games = sd.load_games()
    cache = sp.load()
    rp = Replay(games, cache)
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    for day in sorted(d for d in rp.by_day if d < d0):       # history up to the start (no ratings needed yet)
        for g in rp.by_day[day]:
            rp.hist[g["id"]] = g
    n = 0
    with open(out, "w") as f:
        d = d0
        while d <= d1:
            try:
                if (d - d0).days % step:
                    rp.feed(d)
                    rows = []
                else:
                    rows = rp.day(d)
            except Exception as e:                             # noqa: BLE001
                print(f"{d}: FAILED {str(e)[:120]}", flush=True)
                rp.feed(d)
                rows = []
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()                                          # (a day on disk the moment it's done - a restart loses nothing)
            n += len(rows)
            if d.day == 1 or d == d1:
                print(f"{d}: {n} rows so far, {time.time() - t0:.0f}s", flush=True)
            d += timedelta(days=1)
    print(f"done: {n} rows in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)
