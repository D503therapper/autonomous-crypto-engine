"""NBA-only funnel replay (10/30): the 10/27 funnel (results/studies/thin_1029/funnel_replay.py) on today's code with the
games filtered to the NBA - every NBA moneyline candidate of every board day with the engine's reads (p, edge_own, w_p,
nba_fav_w, lock_ok, own_agrees, thin...) and the result. Usage: REPO=<repo> python nba_funnel.py 2023-10-01 2024-06-30 out.jsonl"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ["REPO"]
os.environ.setdefault("REPLAY_PARAMS_DIR", os.path.join(HERE, "params"))
os.makedirs(os.environ["REPLAY_PARAMS_DIR"], exist_ok=True)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "results", "studies", "thin_1029"))
import sports_data as sd
import sports_players as sp
import funnel_replay as fr

_real_load = sd.load_games


def main(start, end, out):
    import json, time
    from datetime import datetime, timedelta
    t0 = time.time()
    games = {k: g for k, g in _real_load().items() if g.get("league") == "nba"}
    cache = sp.load()
    cache = {lg: rows for lg, rows in cache.items() if lg == "nba"}
    rp = fr.Funnel(games, cache)
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
            except Exception as e:  # noqa
                import traceback; traceback.print_exc()
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
