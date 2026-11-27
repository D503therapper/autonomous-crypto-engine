"""11/27 daily studies - has SPORTS_FINDINGS.md answered this before? Counts the lines that carry each keyword and
prints a short window around the first hits.  python results/studies/daily_1127/seen.py "<regex>" ["<regex>" ...]"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    txt = open(os.path.join(ROOT, "SPORTS_FINDINGS.md")).read()
    lines = txt.split("\n")
    for pat in sys.argv[1:]:
        rx = re.compile(pat, re.I)
        hits = [(i, m) for i, ln in enumerate(lines) for m in rx.finditer(ln)]
        print(f"=== {pat}: {len(hits)} hits on {len(set(i for i, _ in hits))} lines")
        for i, m in hits[:int(os.environ.get('SHOW', 3))]:
            ln = lines[i]
            print(f"  L{i + 1}: ...{ln[max(0, m.start() - 160):m.end() + 220]}...")


if __name__ == "__main__":
    main()
