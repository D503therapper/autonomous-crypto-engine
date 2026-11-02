"""The NBA-only funnel replay (the 10/30 nba_units_1030/nba_funnel.py on TODAY's code: every NBA moneyline candidate of
every board day with the board's reads and gate flags - dog_score, dog_gate, dog_own_ok, edge_own, p_market... - closing
prices, params re-tuned each July, no injury reports) run on 2020-21 .. 2022-23 for STUDY 3. Two changes for the old
seasons: (1) each game's 'open' (ml_*_open, empty before 2023-24) is filled with the game-day MORNING median-book look from
the paid odds history, so sports.market_trend (the 10/30 fade weight) can read those seasons the way it reads ESPN's open;
(2) each row carries its game_id, so the study can grade the pick at the morning price (the 8 AM board's hour) too.
Usage: python funnel_1102.py 2021-01-01 2021-02-28 out.jsonl"""
import json
import os
import sys
import time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib                                       # noqa: E402  (chdir to the repo)
REPO = lib.ROOT
os.environ.setdefault("REPLAY_PARAMS_DIR", os.path.join(HERE, "params"))
os.makedirs(os.environ["REPLAY_PARAMS_DIR"], exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "results", "studies", "thin_1029"))
import sports_data as sd                         # noqa: E402
import sports_players as sp                      # noqa: E402
import funnel_replay as fr                       # noqa: E402

_real_load = sd.load_games


class F(fr.Funnel):
    def row(self, day, kind, c, real, far, n_games, lean):
        r = super().row(day, kind, c, real, far, n_games, lean)
        r["game_id"] = c.get("game_id")
        r["mkt_trend"] = c.get("mkt_trend")
        r["dog_more"] = {k: v for k, v in (c.get("dog_more") or {}).items() if isinstance(v, (int, float, str, bool))}
        return r


def main(start, end, out):
    t0 = time.time()
    games = {k: g for k, g in _real_load().items() if g.get("league") == "nba"}
    lk = lib.looks(games)
    prev = lib.prev_tips(games)
    filled = 0
    for gid, g in games.items():
        if g.get("ml_home_open") in (None, "") and gid in lk:
            mo = lib.pick_looks(lk, prev, gid)[1]
            if mo:
                g["ml_home_open"], g["ml_away_open"] = str(mo["mh"]), str(mo["ma"])
                filled += 1
    print(f"filled {filled} opens from the morning look", flush=True)
    cache = sp.load()
    cache = {lg: rows for lg, rows in cache.items() if lg == "nba"}
    rp = F(games, cache)
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
