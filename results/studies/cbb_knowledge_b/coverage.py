"""Build the table and print its coverage (python coverage.py)."""
import time
from collections import Counter

import lib

t0 = time.time()
rows = lib.regular(lib.build())
print(f"{len(rows)} regular-season sides 2018+ in {time.time() - t0:.0f}s")
c = Counter()
for x in rows:
    c["priced"] += x.get("ml") is not None
    c["own"] += x.get("own") is not None
    c["eff"] += x.get("eff") is not None
    c["top_out known"] += x.get("top_out") is not None
    c["top_out True"] += bool(x.get("top_out"))
    c["reb"] += lib.reb_gap(x) is not None
    c["ats_gap"] += lib.ats_gap(x) is not None
    c["move"] += x.get("move") is not None
    c["fav_read"] += x.get("fav_read") is not None
    c["dog_read"] += x.get("dog_read") is not None
    c["ice_cold"] += bool(x.get("ice_cold"))
for k, v in c.items():
    print(f"{k:14s} {v}")
w = Counter()
for x in rows:
    for k in (x.get("fav_w") or {}):
        w[k] += 1
print("favorite weights fired:", dict(w))
d = Counter(x["dog_pts"] for x in rows if x.get("dog_pts") is not None)
print("dog points:", sorted(d.items()))
