"""Cut a killed funnel chunk back to its last WHOLE day and print the day to restart from.
Usage: python resume.py <rows.jsonl> <the chunk's start day>"""
import json
import sys

path, start = sys.argv[1], sys.argv[2]
rows = []
try:
    for ln in open(path):
        try:
            rows.append(json.loads(ln))
        except ValueError:
            break
except FileNotFoundError:
    pass
if not rows:
    print(start)
    sys.exit(0)
last = rows[-1]["date"]
with open(path, "w") as f:
    for r in rows:
        if r["date"] < last:
            f.write(json.dumps(r) + "\n")
print(last)
