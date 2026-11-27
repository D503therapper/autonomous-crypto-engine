"""11/27 daily studies - yesterday's pick (11/26: Chiefs +130 half a unit, the floor) read off the files.
python results/studies/daily_1127/yday.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
DAY = "2026-11-26"


def find(o, path=""):
    if isinstance(o, dict):
        if o.get("date") == DAY and "legs" not in o:
            print(path, json.dumps(o)[:1500])
            return
        for k, v in o.items():
            find(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            find(v, path + "/" + str(i))
    elif isinstance(o, str) and ("Chiefs" in o or "401873082" in o):
        print(path, o[:600])


def main():
    p = json.load(open("data/sports/picks.json"))
    for r in p:
        if r.get("date") == DAY:
            leg = r["legs"][0]
            skip = ("breakdown", "facts", "spare", "bd_tags")
            print({k: v for k, v in r.items() if k != "legs"})
            print({k: leg[k] for k in sorted(leg) if k not in skip})
    for fn in ("pick_audit.json", "clv_record.json", "pick_check.json"):
        a = json.load(open("data/sports/" + fn))
        print("==", fn, list(a.keys())[:20] if isinstance(a, dict) else len(a))
        find(a)
        if fn == "clv_record.json":
            print("spreads_moved:", a.get("spreads_moved"))


if __name__ == "__main__":
    main()
