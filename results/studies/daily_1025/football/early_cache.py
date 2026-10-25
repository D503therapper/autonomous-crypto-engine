"""Build the FAIR early-look price cache (median books, first fair look 1.5..7.5 days out) - lib.load from daily_1023."""
import sys, os, pickle
OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt/results/studies/daily_1023/football")
import lib
lib.OUT = OUT
res = {}
for lg in ("nfl", "ncaaf"):
    for r in lib.load(lg):
        early = [x for x in r["ml"] if 1.5 <= x[0] < 7.5]
        if early:
            h, a, _ = lib.ml_med(early[0][1])
            res[r["id"]] = (h, a)
pickle.dump(res, open(os.path.join(OUT, "early_prices.pkl"), "wb"))
print("early prices", len(res))
