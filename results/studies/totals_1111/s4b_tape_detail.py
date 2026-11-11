"""S4b - the tape hour by hour for the 4,600 ft+ games (when does the number move?) + today's two games."""
import pickle
import os
from datetime import datetime, timedelta, timezone

import lib

T = pickle.load(open(os.path.join(os.path.expanduser("~"), ".cache", "d503_studies", "totals1111_tape.pkl"), "rb"))
G = {r["id"]: r for r in lib.load("ncaab", finals=False) if r["start"] >= "2026-11"}
mv_eve, mv_all = [], []
for gid, tp in sorted(T.items(), key=lambda kv: G[kv[0]]["start"] if kv[0] in G else ""):
    g = G.get(gid)
    if not g or g["neu"] or (g["el"] or 0) < 1400:
        continue
    st = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    tp = [x for x in tp if x[0] < st]
    if not tp:
        continue
    ch, last = [], None
    for t, v, o in tp:
        if v != last:
            ch.append(f"{(t - timedelta(hours=8)):%m-%d %H:%M} {v:g}({o})")
            last = v
    pt_day = (st - timedelta(hours=8)).date()
    eve6 = datetime(pt_day.year, pt_day.month, pt_day.day, 2, 0, tzinfo=timezone.utc)   # 6 PM PT the day before
    at6 = [x for x in tp if x[0] >= eve6]
    print(f"{g['status']:5} {g['away_name']} @ {g['home_name']} tip {(st - timedelta(hours=8)):%m-%d %H:%M} PT: "
          + " -> ".join(ch) + (f" | final {g['hs'] + g['as']:g}" if g["hs"] is not None and g["status"] == "final" else ""))
    if at6 and g["status"] == "final":
        mv_eve.append((tp[0][1], at6[0][1], tp[-1][1], g["hs"] + g["as"]))
print("\nfirst look / the first look after 6 PM PT the night before / last look / scored:")
for x in mv_eve:
    print("  ", x)
n = len(mv_eve)
if n:
    print(f"   first -> 6 PM the night before {sum(b - a for a, b, c, d in mv_eve) / n:+.2f}; 6 PM -> last "
          f"{sum(c - b for a, b, c, d in mv_eve) / n:+.2f} (n{n}); the over at the 6 PM number "
          f"{sum(1 for a, b, c, d in mv_eve if d > b)}-{sum(1 for a, b, c, d in mv_eve if d < b)}")
