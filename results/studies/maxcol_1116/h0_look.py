import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib
R = mlib.rows()
print(len(R))
ml = [r for r in R if r["market"] == "ml"]
print(len(ml), sum(r.get("dog_read") is not None for r in ml), sum(r.get("eff") is not None for r in ml))
x = [r for r in ml if r["kind"] == "lock"][5]
print({k: (v if not isinstance(v, (list, dict)) else str(v)[:300]) for k, v in x.items()})
x = [r for r in ml if (r.get("dog_read") or 0) >= 6][:1]
print(x)
print(collections.Counter(r["season"] for r in ml if r.get("dog_read") is not None))
