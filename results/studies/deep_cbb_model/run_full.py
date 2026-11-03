"""Run the walk-forward model over every season with the given settings -> ~/.cache/d503_studies/deep_<name>.pkl
(+ _finals.pkl). Usage: python run_full.py NAME '{"halflife": 0, ...}' [scores]   ('scores' = ignore box scores)."""
import json
import os
import pickle
import sys

import lib

if __name__ == "__main__":
    name = sys.argv[1]
    prm = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    use_box = not (len(sys.argv) > 3 and sys.argv[3] == "scores")
    gs, _ = lib.data()
    conf = lib.conferences(gs)
    preds, finals = lib.run(gs, conf, prm, use_box=use_box)
    fn = os.path.join(lib.CACHE, f"deep_{name}.pkl")
    pickle.dump(preds, open(fn, "wb"))
    pickle.dump(finals, open(fn.replace(".pkl", "_finals.pkl"), "wb"))
    print(fn, len(preds))
