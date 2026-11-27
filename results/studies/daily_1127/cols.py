"""11/27 daily studies - what columns the files hold (the team box, the player box, the game file), with how often
SPORTS_FINDINGS.md names each one (0 = never read).  python results/studies/daily_1127/cols.py"""
import csv
import glob
import gzip
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd  # noqa: E402


def main():
    txt = open("SPORTS_FINDINGS.md").read()
    for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
        c, n = Counter(), 0
        fs = [os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")] + sorted(glob.glob(os.path.join(sd.DATA, "teamstats", lg, "*.jsonl")))
        for f in fs[-2:]:
            if not os.path.exists(f):
                continue
            for ln in open(f):
                r = json.loads(ln)
                for b in r["teams"].values():
                    c.update(b.keys())
                    n += 1
        print(f"== {lg} team box ({n} rows): " + ", ".join(f"{k}[{txt.count(k)}]" for k, _ in c.most_common()))
        c2, groups = Counter(), Counter()
        fn = sorted(glob.glob(os.path.join(sd.DATA, "roster", f"{lg}_*.csv.gz")))
        if fn:
            with gzip.open(fn[-1], "rt") as f:
                for i, r in enumerate(csv.DictReader(f)):
                    if i > 20000:
                        break
                    groups[r.get("group")] += 1
                    try:
                        c2.update((r.get("group") or "") + "." + k for k in json.loads(r["stats"] or "{}"))
                    except ValueError:
                        pass
            print(f"   player box {os.path.basename(fn[-1])} cols {list(r.keys())}: " + ", ".join(f"{k}[{txt.count(k.split('.')[-1])}]" for k, _ in c2.most_common(80)))
        g = sd.load_games(lg)
        kc = Counter()
        for x in list(g.values())[-3000:]:
            kc.update(k for k, v in x.items() if v not in ("", None))
        print("   game file: " + ", ".join(f"{k}:{v}" for k, v in kc.most_common()))


if __name__ == "__main__":
    main()
