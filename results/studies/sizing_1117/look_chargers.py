"""11/17 sizing study - the Chargers at Ravens row (11/16 Monday night): every file that names the game."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
GID = "401873065"
DS = os.path.join(ROOT, "data/sports")


def walk(o, path=""):
    if isinstance(o, dict):
        if any(GID in str(v) for v in o.values() if isinstance(v, (str, int))) or GID in path:
            yield path, o
            return
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + f"[{i}]")


for f in ("qb_calls.json", "lead_tracker.json", "pick_check.json", "lean_sides.json", "sharp_fired.json", "pick_audit.json"):
    try:
        o = json.load(open(os.path.join(DS, f)))
    except Exception as e:
        print(f, e)
        continue
    for path, d in walk(o):
        print(f, path, json.dumps(d, default=str)[:2500])
        print()
print("LINE HISTORY")
n = 0
rows = []
for ln in open(os.path.join(DS, "line_history/2026-11.jsonl")):
    if GID in ln:
        rows.append(ln.strip())
print(len(rows))
for ln in rows[:3] + rows[len(rows) // 2:len(rows) // 2 + 2] + rows[-4:]:
    print(ln[:600])
for ln in open(os.path.join(DS, "games/nfl/2026-11.csv")):
    if GID in ln or ln.startswith("id") or n == 0:
        print(ln.strip())
    n += 1
