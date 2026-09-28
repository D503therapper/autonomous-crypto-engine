"""THE SIM RUN (3x a day): the walk-forward game simulator re-grades its best sims and suspects on the latest games,
tries NEW sim variants it has never tried (sports_sim.run), then simulates today's board (sports_sim.today).
What each run found goes in data/sports/sims_log.json (newest first, the last 60 runs)."""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, ".")
import sports_data as sd  # noqa: E402
import sports_sim as ss  # noqa: E402

LOG = os.path.join(sd.DATA, "sims_log.json")


def main():
    t0 = time.time()
    games = sd.load_games()
    run = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "games": len(games)}
    try:
        res = ss.run(games)
        run["sim"] = {"ok": True, "proven": res["proven"], "suspects": res["suspects"], "tested": res["tested_configs"],
                      "tested_total": res["tested_total"], "cell_tests": res["cell_tests"],
                      "expected_by_luck": res["expected_by_luck"], "new_suspects": res["new_suspects"],
                      "new_proven": res["new_proven"], "new_killed": res["new_killed"], "best": res["best"],
                      "secs": res["secs"]}
    except Exception as e:                                   # noqa: BLE001 - still refresh today's slate
        run["sim"] = {"ok": False, "error": str(e)[:300]}
        print(f"❌ sim run: {e}", flush=True)
        traceback.print_exc()
    try:
        td = ss.today(games)
        run["today"] = {"ok": True, "games": len(td["games"]), "secs": td["secs"]}
    except Exception as e:                                   # noqa: BLE001
        run["today"] = {"ok": False, "error": str(e)[:300]}
        print(f"❌ today's sims: {e}", flush=True)
        traceback.print_exc()
    run["secs"] = round(time.time() - t0)
    try:
        with open(LOG) as f:
            log = json.load(f)
    except (OSError, ValueError):
        log = []
    log = [run] + log[:59]
    with open(LOG + ".tmp", "w") as f:
        json.dump(log, f, indent=1)
    os.replace(LOG + ".tmp", LOG)
    print(f"sim run done in {run['secs']}s")


if __name__ == "__main__":
    main()
