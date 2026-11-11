"""S5 - THE NFL WINDY UNDER (the brother's: 15+ mph at kickoff, outdoors; blind 148 bets +15.7%, since 2006 159 +15.4%).

Two wind readings, both AFTER THE FACT:
  nflverse - the public schedule file's `wind` (the kickoff reading off the box score), `roof`, `total_line` and the
             over / under prices from 2006 (argv[1] = the downloaded games.csv; not kept in the repo)
  ours     - wx_wind in the game files (Open-Meteo's archive for the game's UTC day)
Neither is the forecast a bettor had. The forecast-history host could not be reached from this session, so the
forecast-vs-actual check is the dose: how fast does the edge die when the reading is a few mph off?"""
import csv
import sys
from collections import defaultdict

import lib

NV = [r for r in csv.DictReader(open(sys.argv[1])) if r["total_line"] not in ("", "NA") and r["total"] not in ("", "NA")]
for r in NV:
    r["season"] = int(r["season"])
    r["tot"] = float(r["total_line"])
    r["hs"], r["as"] = float(r["home_score"]), float(r["away_score"])
    r["w"] = lib.num(r["wind"])
    r["out"] = r["roof"] in ("outdoors", "open")
print(f"nflverse games with a closing total: {len(NV)} ({NV[0]['season']}-{NV[-1]['season']}); with a wind reading: "
      f"{sum(1 for r in NV if r['w'] is not None)}")
print("   wind readings a season, outdoor games:", " ".join(
    f"{s % 100:02d}:{sum(1 for r in NV if r['season'] == s and r['out'] and r['w'] is not None)}/"
    f"{sum(1 for r in NV if r['season'] == s and r['out'])}" for s in range(2018, 2027)))
O = [r for r in NV if r["out"] and r["w"] is not None]

print("\n== (a) nflverse kickoff wind, outdoor / roof open, the UNDER at the close (the real price from 2006, else -110)")
lib.line("15+ mph, 2018 on (train 2018-21 / blind 2022+)", [r for r in O if r["w"] >= 15 and r["season"] >= 2018], "under")
lib.line("15+ mph, every season since 2006 (train = to 2021)", [r for r in O if r["w"] >= 15 and r["season"] >= 2006], "under")
lib.line("15+ mph, 1999 on", [r for r in O if r["w"] >= 15], "under")
lib.line("15+ mph, 2024-26 only", [r for r in O if r["w"] >= 15 and r["season"] >= 2024], "under")
lib.line("15+ mph, regular season only, 2006 on",
         [r for r in O if r["w"] >= 15 and r["season"] >= 2006 and r["game_type"] == "REG"], "under")
lib.line("15+ mph OVER (the mirror), 2006 on", [r for r in O if r["w"] >= 15 and r["season"] >= 2006], "over")
print("   the dose, 2006 on:")
for lo, hi in ((0, 5), (5, 10), (10, 13), (13, 15), (15, 18), (18, 22), (22, 99), (12, 99), (20, 99)):
    lib.line(f"   wind {lo}-{hi} mph", [r for r in O if lo <= r["w"] < hi and r["season"] >= 2006], "under")
print("   by the total, 15+ mph, 2006 on:")
for lo, hi in ((0, 38), (38, 42), (42, 46), (46, 99)):
    lib.line(f"   total {lo}-{hi}", [r for r in O if r["w"] >= 15 and lo <= r["tot"] < hi and r["season"] >= 2006], "under")
print("   by the month, 15+ mph, 2006 on:")
for lab, ms in (("Sep-Oct", ("09", "10")), ("Nov", ("11",)), ("Dec-Feb", ("12", "01", "02"))):
    lib.line(f"   {lab}", [r for r in O if r["w"] >= 15 and r["gameday"][5:7] in ms and r["season"] >= 2006], "under")
print("   has the close caught up? the windy games' closing total vs every outdoor game that season, and the miss:")
for lo, hi in ((2006, 2012), (2013, 2017), (2018, 2021), (2022, 2023), (2024, 2026)):
    a = [r for r in O if lo <= r["season"] <= hi]
    w = [r for r in a if r["w"] >= 15]
    if w:
        print(f"   {lo}-{hi}: windy n{len(w)} total {sum(r['tot'] for r in w) / len(w):.1f} vs all "
              f"{sum(r['tot'] for r in a) / len(a):.1f}; windy games scored "
              f"{sum(r['hs'] + r['as'] - r['tot'] for r in w) / len(w):+.1f} vs the total")

print("\n== (b) OUR reading (wx_wind, the game day's archive number) on the same test")
G = [r for r in lib.load("nfl") if r["tot"] is not None and r["hs"] is not None]
for r in G:
    r["w"] = lib.num(r.get("wx_wind"))
    r["out"] = str(r.get("indoor") or "0") not in ("1", "True", "true")
OG = [r for r in G if r["out"] and r["w"] is not None]
print(f"   our outdoor NFL games with a total and a wind number: {len(OG)}")
lib.line("ours 15+ mph", [r for r in OG if r["w"] >= 15], "under")
lib.line("ours 15+ mph, 2024-26", [r for r in OG if r["w"] >= 15 and r["season"] >= 2024], "under")
for lo, hi in ((10, 15), (15, 20), (20, 99)):
    lib.line(f"   ours {lo}-{hi} mph", [r for r in OG if lo <= r["w"] < hi], "under")

print("\n== (c) THE TWO READINGS ON THE SAME GAMES (2018 on): how far apart are two honest wind numbers?")
by = {r["espn"]: r for r in NV if r["espn"]}
pair = []
for r in OG:
    n = by.get(r["id"].split(":")[1])
    if n and n["w"] is not None and n["out"]:
        pair.append((n["w"], r["w"], r, n))
if pair:
    d = [abs(a - b) for a, b, _, _ in pair]
    both = [x for x in pair if x[0] >= 15 and x[1] >= 15]
    only_n = [x for x in pair if x[0] >= 15 > x[1]]
    only_o = [x for x in pair if x[1] >= 15 > x[0]]
    print(f"   {len(pair)} games with both; the two differ by a mean {sum(d) / len(d):.1f} mph; 15+ on BOTH {len(both)}, "
          f"on the kickoff reading only {len(only_n)}, on ours only {len(only_o)}")
    lib.line("   15+ on both", [x[2] for x in both], "under")
    lib.line("   15+ on the kickoff reading only", [x[2] for x in only_n], "under")
    lib.line("   15+ on ours only", [x[2] for x in only_o], "under")
    lib.line("   either reading 12+ and neither 15+ (a forecast's near miss)",
             [x[2] for x in pair if max(x[0], x[1]) >= 12 and max(x[0], x[1]) < 15], "under")

print("\n== (d) PLACEBO: 500 random sets of outdoor games the size of the 15+ set, by season (2006 on)")
import random  # noqa: E402
random.seed(1111)
base = [r for r in O if r["season"] >= 2006]
real = [r for r in base if r["w"] >= 15]
cnt = defaultdict(int)
for r in real:
    cnt[r["season"]] += 1
bys = defaultdict(list)
for r in base:
    bys[r["season"]].append(r)
rs = lib.stats([lib.bet(r, "under") for r in real])
hit = 0
for _ in range(500):
    ps = [lib.bet(r, "under") for s, k in cnt.items() for r in random.sample(bys[s], k)]
    hit += lib.stats(ps)["roi"] >= rs["roi"]
print(f"   the real set {100 * rs['roi']:+.1f}% on {rs['n']} (z{rs['z']:+.1f}); random sets that did as well: {hit} of 500")
