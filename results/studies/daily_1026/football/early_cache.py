"""The FAIR early-look price cache (median books, the first fair look 1.5..7.5 days out) - the daily_1023 lib loader,
pointed at this worktree. Writes the scratchpad cache only."""
import os, sys, pickle, types
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1026")
src = open(os.path.join(WT, "results", "studies", "daily_1023", "football", "lib.py")).read()
src = src.replace('WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"',
                  f"WT = {WT!r}").replace("OUT = os.path.dirname(os.path.abspath(__file__))", f"OUT = {CACHE!r}")
lib = types.ModuleType("lib1026")
exec(compile(src, "lib1026", "exec"), lib.__dict__)
res = {}
for lg in ("nfl", "ncaaf"):
    for r in lib.load(lg):
        early = [x for x in r["ml"] if 1.5 <= x[0] < 7.5]
        if early:
            h, a, _ = lib.ml_med(early[0][1])
            res[r["id"]] = (h, a)
pickle.dump(res, open(os.path.join(CACHE, "fb_early.pkl"), "wb"))
print("early prices", len(res))
