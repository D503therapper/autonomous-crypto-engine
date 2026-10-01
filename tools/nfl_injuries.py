"""NFL INJURY REPORTS 2020-now (10/1, the owner: "factor in who's injured with these odds"). nflverse's public injury
data (free, on GitHub - no key): every player on each week's report, his game status (Out / Doubtful / Questionable)
and practice status. Saved slim to data/sports/injuries/nfl.csv.gz. Re-run any time: python tools/nfl_injuries.py"""
import csv
import gzip
import io
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd  # noqa: E402

URL = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{y}.csv"
OUT = os.path.join(sd.DATA, "injuries", "nfl.csv.gz")
KEEP = ("season", "game_type", "team", "week", "position", "full_name", "report_status", "practice_status",
        "date_modified")


def fetch(y):
    req = urllib.request.Request(URL.format(y=y), headers={"User-Agent": "D503-sports-engine/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def main(first=2020):
    rows = []
    for y in range(first, datetime.now(timezone.utc).year + 1):
        try:
            got = fetch(y)
        except Exception as e:                      # noqa: BLE001 (a season not posted yet)
            print(y, str(e)[:60])
            continue
        rows += [{k: r.get(k, "") for k in KEEP} for r in got]
        print(y, len(got))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEEP)
        w.writeheader()
        w.writerows(rows)


def load(path=OUT):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
