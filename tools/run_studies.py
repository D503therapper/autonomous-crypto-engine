"""THE STUDY RUN (twice a day): every study reruns on all the latest games, so the engine keeps learning.

Each study learns on older games and is graded on newer ones it never saw; only what proves out gets used by the
picks (every study module decides that itself). A study that breaks is logged and skipped - the rest still run.
What each one found goes in data/sports/studies_log.json (newest first) so we can watch the engine get smarter."""
import importlib
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, ".")
import sports_data as sd  # noqa: E402

LOG = os.path.join(sd.DATA, "studies_log.json")


def _proven(res):
    """A short 'what's proven' view of a study's result, whatever its shape."""
    if not isinstance(res, dict):
        return None
    out = {}
    for k, v in res.items():
        if isinstance(v, dict):
            if "proven" in v:
                out[k] = v["proven"] if isinstance(v["proven"], (bool, list)) else bool(v["proven"])
            if isinstance(v.get("price"), dict) and "proven" in v["price"]:
                out[f"{k} price check"] = v["price"]["proven"]
    if isinstance(res.get("proven"), list):
        out["proven"] = res["proven"]
    return out or None


def main():
    games = sd.load_games()
    t_all = time.time()
    run = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "games": len(games), "studies": {}}
    jobs = [
        ("underdogs + favorites", "sports_dogs", lambda m: m.study(games)),
        ("over/unders", "sports_totals", lambda m: m.study(games)),
        ("hockey", "sports_hockey", lambda m: m.study(games)),
        ("spread vs moneyline", "sports_ats", lambda m: m.study(games)),
        ("puck lines / run lines", "sports_lines", lambda m: m.study(games)),
        ("halves / first period", "sports_halves", lambda m: m.study(games)),
        ("comebacks", "sports_comeback", lambda m: m.study(games)),
        ("trends", "sports_trends", lambda m: m.study(games)),
        ("rigged / fade the public", "sports_public", lambda m: m.study(games)),
        ("self-check on our picks", "sports_selfcheck", lambda m: m.study()),
        ("situational spots", "sports_spots", lambda m: m.study(games)),        # (runs once it exists)
        ("line movement + CLV", "sports_moves", lambda m: m.study(games)),      # (runs once it exists)
        ("the explorer: NEW angles", "sports_explorer", lambda m: m.explore(games)),   # new questions every run
    ]
    for name, mod, fn in jobs:
        t0 = time.time()
        try:
            m = importlib.import_module(mod)
        except ImportError:
            continue
        try:
            res = fn(m)
            run["studies"][name] = {"ok": True, "secs": round(time.time() - t0, 1), "proven": _proven(res)}
            print(f"✅ {name}: {round(time.time() - t0)}s · proven: {json.dumps(_proven(res))[:300]}", flush=True)
        except Exception as e:                               # noqa: BLE001 - one broken study never stops the rest
            run["studies"][name] = {"ok": False, "error": str(e)[:300]}
            print(f"❌ {name}: {e}", flush=True)
            traceback.print_exc()
    run["secs"] = round(time.time() - t_all)
    try:
        with open(LOG) as f:
            log = json.load(f)
    except (OSError, ValueError):
        log = []
    log = [run] + log[:59]                                   # the last 30 days of runs
    with open(LOG + ".tmp", "w") as f:
        json.dump(log, f, indent=1)
    os.replace(LOG + ".tmp", LOG)
    print(f"study run done in {run['secs']}s: {sum(v.get('ok', False) for v in run['studies'].values())}/"
          f"{len(run['studies'])} studies ok")


if __name__ == "__main__":
    main()
