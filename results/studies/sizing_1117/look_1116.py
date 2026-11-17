"""11/17 sizing study - what the 11/16 board posted (UMBC +120, the Chargers at Ravens row) and why it was sized so."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BIG = ("breakdown", "facts", "bd_tags", "flow", "ctx", "decider")
day = sys.argv[1] if len(sys.argv) > 1 else "2026-11-16"
p = json.load(open(os.path.join(ROOT, "data/sports/picks.json")))
ps = p if isinstance(p, list) else p.get("picks", p)
for x in ps:
    if x.get("date") != day:
        continue
    top = {k: v for k, v in x.items() if k != "legs"}
    print("PICK", json.dumps(top, default=str)[:1500])
    for leg in x.get("legs", []):
        print("  LEG", json.dumps({k: v for k, v in sorted(leg.items()) if k not in BIG}, default=str))
        for b in leg.get("breakdown", []):
            print("      ", b)
    print()
