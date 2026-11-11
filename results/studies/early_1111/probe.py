"""A look at what the paid odds history holds (per sport: rows, seasons, books, days before the game)."""
import collections
import datetime as D
import gzip
import json
import os

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for s in ["americanfootball_nfl", "americanfootball_ncaaf", "basketball_nba", "icehockey_nhl",
          "americanfootball_nfl_spreads"]:
    n = 0
    first = None
    ts, bk, days, hrs = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    keys = set()
    with gzip.open(f"{R}/data/sports/odds_history/{s}.jsonl.gz", "rt") as f:
        for x in f:
            r = json.loads(x)
            n += 1
            keys |= set(r)
            if "b" not in r:
                if n < 3:
                    print("meta", x[:300])
                continue
            if first is None:
                first = r
            ts[r["snap"][:7]] += 1
            d = (D.datetime.fromisoformat(r["t"].replace("Z", "+00:00"))
                 - D.datetime.fromisoformat(r["snap"].replace("Z", "+00:00"))).total_seconds() / 86400
            days[round(d)] += 1
            hrs[r["snap"][11:13]] += 1
            for b in r["b"]:
                bk[b] += 1
    print(s, n, keys)
    print(dict(sorted(ts.items())))
    print(json.dumps(first)[:500])
    print(bk.most_common(30))
    print(sorted(days.items())[:14])
    print(sorted(hrs.items()))
