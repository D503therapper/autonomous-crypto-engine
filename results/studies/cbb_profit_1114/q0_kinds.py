"""11/14 quick look: the college hoops unit kinds on the 11/13 funnel rows (flat 1u at the close)."""
import os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "early_cbb_1113"))
import elib as E

F = pickle.load(open(os.path.expanduser("~/.cache/d503_early1113/rows.pkl"), "rb"))
for k in ("lock", "gap", "ncaabplay", "stackplay", "floor", "play"):
    rows = [r for r in F if r["kind"] == k]
    if k == "ncaabplay":
        E.rec("slot fav", [r for r in rows if r["odds"] < 0])
        E.rec("slot dog", [r for r in rows if r["odds"] > 0])
    E.rec(k, rows)
