"""Does the engine's pure-Python efficiency read (sports_cbb_eff) reproduce the study model? For sample nights of the
held-out seasons: the live read's home margin vs the study's walk-forward margin (deep_final.pkl) on every game that
night, and how often the -3 favorite filter agrees. Also times one live read. Writes check_live_out.txt."""
import os
import pickle
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
import sports_cbb_eff as ce  # noqa: E402
import sports_data as sd  # noqa: E402

import lib  # noqa: E402
from analyze import fit_logit, sig  # noqa: E402


def main():
    os.chdir(lib.ROOT)
    games = sd.load_games("ncaab")
    preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final.pkl"), "rb"))
    box = ce.load_box()
    by_night = {}
    for g in games.values():
        if g["id"] in preds and g.get("status") == "final":
            by_night.setdefault((ce.season_of(g["start"]), ce.night_of(g["start"])), []).append(g)
    random.seed(7)
    keys = sorted(k for k in by_night if k[0] in (2024, 2025) and len(by_night[k]) >= 8)
    pick = random.sample(keys, 12)
    diffs, agree, n_flag = [], 0, 0
    out = []
    for k in sorted(pick):
        gs = by_night[k]
        t = time.time()
        ce._CACHE.clear()
        res = [(g, ce.predict(games, g, box)) for g in gs]
        dt = time.time() - t
        d = [abs(r["margin"] - preds[g["id"]]["mh"]) for g, r in res if r]
        diffs += d
        for g, r in res:
            if not r or not g.get("ml_home") or not g.get("ml_away"):
                continue
            mk = sd.no_vig(int(float(g["ml_home"])), int(float(g["ml_away"])))
            ps = 1 / (1 + 2.718281828 ** (-(ce.CAL[0] + ce.CAL[1] * preds[g["id"]]["mh"])))
            for side_h in (True, False):
                odds = int(float(g["ml_home"] if side_h else g["ml_away"]))
                if not -150 <= odds <= -101:
                    continue
                e_live = (r["p_home"] - mk) * (1 if side_h else -1)
                e_study = (ps - mk) * (1 if side_h else -1)
                n_flag += 1
                agree += (e_live <= -0.03) == (e_study <= -0.03)
        out.append(f"season {k[0]} night {k[1]}: {len(gs)} games, mean |live - study| margin {sum(d) / max(1, len(d)):.2f} "
                   f"pts, max {max(d) if d else 0:.2f}; read took {dt:.1f}s")
    out.append(f"ALL: {len(diffs)} games, mean |diff| {sum(diffs) / len(diffs):.2f} pts, 90th pct "
               f"{sorted(diffs)[int(0.9 * len(diffs))]:.2f}; the favorite filter agrees on {agree} of {n_flag} slight favorites")
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(HERE, "check_live_out.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
