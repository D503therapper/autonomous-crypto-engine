"""S4 - THE POSTED NUMBER vs THE CLOSE. We hold no opening totals in the game files or the line history (moneyline +
spread only), but every engine run commits the game CSVs - so the git history of data/sports/games/ncaab/2026-11.csv
is a total-by-total tape for this season (11/3 on). For every college hoops game: when the total first showed, what
it was then, at 8 AM PT game day, and at the last look before the tip; then the altitude floors apart.
Small (one week of a season) - it answers WHEN a number exists and WHICH WAY it moves, not the ROI."""
import csv
import io
import os
import pickle
import statistics
import subprocess
from datetime import datetime, timedelta, timezone

import lib

PATH = "data/sports/games/ncaab/2026-11.csv"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_studies", "totals1111_tape.pkl")


def tape():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    log = subprocess.run(["git", "log", "--format=%H %cI", "--", PATH], cwd=lib.ROOT, capture_output=True,
                         text=True).stdout.split("\n")
    out = {}                                    # game id -> [(commit time, total, over odds)] in time order
    for ln in reversed([x for x in log if x]):
        h, t = ln.split()
        t = datetime.fromisoformat(t).astimezone(timezone.utc)
        txt = subprocess.run(["git", "show", f"{h}:{PATH}"], cwd=lib.ROOT, capture_output=True, text=True).stdout
        for r in csv.DictReader(io.StringIO(txt)):
            if r.get("status") != "pre" or not r.get("total"):
                continue
            out.setdefault(r["id"], []).append((t, float(r["total"]), r.get("over_odds") or ""))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(out, open(CACHE, "wb"))
    return out


T = tape()
G = {r["id"]: r for r in lib.load("ncaab", finals=False) if r["start"] >= "2026-11"}
rows = []
for gid, tp in T.items():
    g = G.get(gid)
    if not g or g["status"] != "final" or g["tot"] is None:
        continue
    st = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    tp = [x for x in tp if x[0] < st]
    if not tp:
        continue
    pt_day = (st - timedelta(hours=8)).date()
    am8 = datetime(pt_day.year, pt_day.month, pt_day.day, 16, 0, tzinfo=timezone.utc)      # 8 AM PT (PST) game day
    at8 = [x for x in tp if x[0] <= am8 + timedelta(minutes=45)]
    rows.append(dict(g=g, first=tp[0], last=tp[-1], lead=(st - tp[0][0]).total_seconds() / 3600,
                     at8=at8[-1] if at8 else None, pts=g["hs"] + g["as"], st=st, tp=tp,
                     eve=any(x[0] < am8 - timedelta(hours=8) for x in tp)))
print(f"college hoops finals this season with a total on the tape: {len(rows)}")
lead = [r["lead"] for r in rows]
print(f"   the total first shows a median {statistics.median(lead):.1f} hours before the tip "
      f"(quartiles {statistics.quantiles(lead, n=4)[0]:.1f} / {statistics.quantiles(lead, n=4)[2]:.1f})")
print(f"   on file the NIGHT BEFORE (before midnight PT): {sum(r['eve'] for r in rows)} of {len(rows)}; "
      f"on file by 8 AM PT game day: {sum(1 for r in rows if r['at8'])} of {len(rows)}")


def show(lab, rs):
    if not rs:
        print(f"   {lab}: none")
        return
    mv = [r["last"][1] - r["first"][1] for r in rs]
    up = sum(1 for m in mv if m > 0)
    dn = sum(1 for m in mv if m < 0)
    w1 = sum(1 for r in rs if r["pts"] > r["first"][1])
    l1 = sum(1 for r in rs if r["pts"] < r["first"][1])
    w2 = sum(1 for r in rs if r["pts"] > r["last"][1])
    l2 = sum(1 for r in rs if r["pts"] < r["last"][1])
    print(f"   {lab}: n{len(rs)}  first look -> last look {statistics.mean(mv):+.2f} pts (up {up} / down {dn} / same "
          f"{len(rs) - up - dn});  the over at the FIRST number {w1}-{l1}, at the LAST {w2}-{l2}")


show("every game", rows)
show("low ground (<600 m), home floor", [r for r in rows if not r["g"]["neu"] and (r["g"]["el"] or 0) < 600])
show("1,220-1,399 m", [r for r in rows if not r["g"]["neu"] and 1220 <= (r["g"]["el"] or 0) < 1400])
alt = [r for r in rows if not r["g"]["neu"] and (r["g"]["el"] or 0) >= 1400]
show("4,600 ft+ (1,400 m+)", alt)
print("\n   the 4,600 ft+ games one by one (PT times; first look -> 8 AM game day -> last look before the tip, final):")
for r in sorted(alt, key=lambda r: r["st"]):
    g = r["g"]
    f8 = f"{r['at8'][1]:g} ({r['at8'][2]})" if r["at8"] else "none yet"
    print(f"   {g['start'][5:10]} {g['away_name']} @ {g['home_name']} ({g['el'] * lib.FT:,.0f} ft): first "
          f"{r['first'][1]:g} ({r['first'][2]}) {r['lead']:.0f}h before | 8 AM {f8} | last {r['last'][1]:g} "
          f"({r['last'][2]}) | scored {r['pts']:g}")
if alt:
    m8 = [r["last"][1] - r["at8"][1] for r in alt if r["at8"]]
    print(f"\n   8 AM PT number -> the last look, 4,600 ft+: {statistics.mean(m8):+.2f} pts on {len(m8)} "
          f"(up {sum(1 for m in m8 if m > 0)}, down {sum(1 for m in m8 if m < 0)})")
    w = sum(1 for r in alt if r["at8"] and r["pts"] > r["at8"][1])
    l_ = sum(1 for r in alt if r["at8"] and r["pts"] < r["at8"][1])
    print(f"   the over at the 8 AM PT number: {w}-{l_}")

print("\n== HOW MUCH LINE CAN THE EDGE GIVE AWAY? (every season, 4,600 ft+ home floors, the over at the close + X points)")
H = [r for r in lib.load("ncaab") if (r.get("stype") or "2") == "2" and not r["neu"] and (r["el"] or 0) >= 1400
     and r["tot"] is not None and r["hs"] is not None]
for x in (-3, -2, -1, 0, 1, 2, 3, 4, 5):
    ps, tr, bl = [], [], []
    for r in H:
        pts, t = r["hs"] + r["as"], r["tot"] + x
        p = 0.0 if pts == t else (100 / 110 if pts > t else -1.0)
        ps.append(p)
        (tr if r["season"] <= lib.TRAIN_TO else bl).append(p)
    a, b, c = lib.stats(ps), lib.stats(tr), lib.stats(bl)
    print(f"   over (close {x:+d}) at -110: {a['w']}-{a['l']} {100 * a['roi']:+.1f}% z{a['z']:+.1f} | train "
          f"{100 * b['roi']:+.1f}% | blind {100 * c['roi']:+.1f}%")
print("   and at the close by the price paid (what -120 / -130 / -140 would have cost):")
for o in (-110, -115, -120, -130, -140, -150):
    ps = []
    for r in H:
        pts = r["hs"] + r["as"]
        ps.append(0.0 if pts == r["tot"] else (100 / -o if pts > r["tot"] else -1.0))
    a = lib.stats(ps)
    print(f"   every over priced at {o}: {100 * a['roi']:+.1f}% (z{a['z']:+.1f})")
