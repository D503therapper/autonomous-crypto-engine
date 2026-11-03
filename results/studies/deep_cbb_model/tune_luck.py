"""Shooting-luck settings, tuned on the TRAIN box-score seasons only (2021-22, 2022-23): margin RMSE vs results.
Appends to tune_log.txt."""
import os
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
import lib  # noqa: E402
import tune  # noqa: E402

if __name__ == "__main__":
    tries = [{**lib.DEFAULT, "luck3": a, "luckft": b} for a in (0.0, 0.3, 0.5, 0.7) for b in (0.0, 0.5, 1.0)]
    with Pool(4, initializer=tune.init) as pool:
        res = pool.map(tune.score, tries)
    log = open(os.path.join(lib.OUT, "tune_log.txt"), "a")
    for prm, o in res:
        line = (f"luck3={prm['luck3']} luckft={prm['luckft']}: box (2021-22) margin {o['box']:.3f} totals "
                f"{o['box_tot']:.3f} | all train margin {o['train']:.3f}")
        print(line)
        log.write(line + "\n")
