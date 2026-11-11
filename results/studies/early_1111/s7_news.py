"""S7 - NEWS RISK. (a) LIVE: how many of our early plays had a key player ruled out after the post (sports_early.watch
fills key_out), and what the plays the close ran away from did. (b) HISTORY, the NFL (nflverse's public game file names
each game's STARTING QB; the weekly final injury report lists who was Questionable / Doubtful / Out - the files the
11/11 book study fetched, ~/.cache/d503_book1111/dl): an early dog (+100..+350 at the first fair number) whose
starting QB turns out to be a DIFFERENT man than last game's - how often, what the price did after the first fair
number, what the bet did. Then the flags a scan CAN see when it posts: the QB was on LAST week's final report; the
team started a different QB in either of its last two games. (c) Both leagues: does the move after the first fair
number go with winning - the ROI at the first fair price by what the close then did (the answer to 'does beating the
close predict winning' in history)."""
import csv
import json
import os

import base
import elib as E

out = E.Tee("s7_news_out.txt")
DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_book1111", "dl")
ABBR = {"ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2", "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5", "DAL": "6",
        "DEN": "7", "DET": "8", "GB": "9", "HOU": "34", "IND": "11", "JAX": "30", "KC": "12", "LA": "14", "LAR": "14",
        "LAC": "24", "LV": "13", "OAK": "13", "MIA": "15", "MIN": "16", "NE": "17", "NO": "18", "NYG": "19", "NYJ": "20",
        "PHI": "21", "PIT": "23", "SEA": "26", "SF": "25", "TB": "27", "TEN": "10", "WAS": "28"}


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


out("S7 (a) LIVE")
st = json.load(open(E.se.PATH))
ps = [p for p in st["picks"] if p.get("market") != "total"]
ko = [p for p in ps if p.get("key_out")]
out(f" early moneyline plays posted: {len(ps)}; with the injury watch running on them: {sum(1 for p in ps if 'out_at_post' in p)}; "
    f"a key player ruled OUT after the post (key_out): {len(ko)}; with a key player already out at the post: "
    f"{sum(1 for p in ps if p.get('out_at_post'))}")
rows1 = json.load(open(os.path.join(E.OUT, "s1_live_rows.json")))
bad = [r for r in rows1 if r["clv"] is not None and r["clv"] <= -2 and r["league"] in ("nfl", "ncaaf")]
out(f" football plays the close ran 2+ points AWAY from after the post: {len(bad)} "
    f"({sum(1 for r in bad if r['result'] == 'won')}-{sum(1 for r in bad if r['result'] == 'lost')}, "
    f"{sum(1 for r in bad if r['pulled'])} pulled): " + ", ".join(f"{r['team']} {r['odds']:+d}->{r['close'][0]:+d} ({r['spot'] or 'exam'})" for r in bad))
out(f" by spot: " + ", ".join(f"{s} {sum(1 for r in bad if (r['spot'] or 'exam') == s)}" for s in sorted({r['spot'] or 'exam' for r in bad})))

out("\nS7 (b) THE NFL: THE STARTING QB CHANGES AFTER THE FIRST FAIR NUMBER (nflverse starters, 2020-26)")
qb = {}                                               # (season, espn team id) -> [(gameday, qb id, week)]
gm = {}
with open(os.path.join(DL, "games.csv")) as f:
    for r in csv.DictReader(f):
        if int(r["season"]) < 2019 or r["game_type"] != "REG" or not r.get("home_qb_id"):
            continue
        for side in ("home", "away"):
            tid = ABBR.get(r[f"{side}_team"])
            qb.setdefault((int(r["season"]), tid), []).append((r["gameday"], r[f"{side}_qb_id"], int(r["week"])))
            gm[(r["gameday"], tid)] = (int(r["season"]), int(r["week"]))
for v in qb.values():
    v.sort()
rep = {}                                              # (season, week, espn team id) -> {gsis: status} QBs on the FINAL report
for y in range(2019, 2027):
    p = os.path.join(DL, f"injuries_{y}.csv")
    if not os.path.exists(p):
        continue
    with open(p) as f:
        for r in csv.DictReader(f):
            if r["position"] == "QB" and r["game_type"] == "REG" and (r.get("report_status") or "").strip():
                rep.setdefault((int(r["season"]), int(r["week"]), ABBR.get(r["team"])), {})[r["gsis_id"]] = r["report_status"]

rows = []
for r in base.build("nfl"):
    f = base.first_fair(r)
    if not f:
        continue
    day = E.t(r["start"]).astimezone(E.ET).strftime("%Y-%m-%d")
    k = gm.get((day, r["team"]))
    if not k:
        continue
    lst = qb.get((k[0], r["team"]), [])
    i = next((j for j, x in enumerate(lst) if x[0] == day), None)
    if i is None or i == 0:
        continue
    this, last = lst[i][1], lst[i - 1][1]
    two = lst[i - 2][1] if i >= 2 else last
    last_wk = lst[i - 1][2]
    rows.append({"r": r, "f": f, "changed": this != last, "unsettled": last != two,
                 "on_last_report": last in rep.get((k[0], last_wk, r["team"]), {}),
                 "this_status": rep.get((k[0], k[1], r["team"]), {}).get(last)})
dogs = [x for x in rows if 100 <= x["f"][2] <= 350]
out(f" NFL early dogs matched to the starters file: {len(dogs)}")


def cell(nm, v):
    if len(v) < 8:
        out(f"   {nm:64s} n {len(v)}")
        return
    m = [(x["r"]["close_p"] - x["f"][3]) * 100 for x in v]
    a = [pl(x["r"], x["f"][2]) for x in v]
    c = [pl(x["r"], x["r"]["close_o"]) for x in v]
    he = [pl(x["r"], x["f"][2]) for x in v if x["r"]["season"] >= 2023]
    out(f"   {nm:64s} move after {E.mean(m):+5.2f} pts (t {E.tstat(m):+4.1f}; 3+ away {sum(1 for q in m if q <= -3) / len(m) * 100:3.0f}%) | "
        f"first fair {E.roi(a)} | held {E.roi(he)} | at the close {E.mean(c) * 100:+6.1f}%")


cell("every early dog", dogs)
cell("NEWS: the dog starts a DIFFERENT QB than last game", [x for x in dogs if x["changed"]])
cell("  ... and the old QB is Out / Doubtful on this week's report", [x for x in dogs if x["changed"] and x["this_status"] in ("Out", "Doubtful")])
cell("the dog's QB is the same man", [x for x in dogs if not x["changed"]])
by = {}
for x in dogs:
    by.setdefault(x["r"]["id"], x)
opp = {(x["r"]["id"], x["r"]["side"]): x for x in rows}
cell("NEWS on the other side: the FAVORITE starts a different QB", [x for x in dogs if opp.get((x["r"]["id"], "away" if x["r"]["home"] else "home"), {}).get("changed")])
out(" what a scan can see when it posts:")
cell("FLAG: the QB was on LAST week's final injury report", [x for x in dogs if x["on_last_report"]])
cell("  no flag", [x for x in dogs if not x["on_last_report"]])
cell("FLAG: a different QB started one of the last two games (unsettled)", [x for x in dogs if x["unsettled"]])
cell("  settled", [x for x in dogs if not x["unsettled"]])
fl = [x for x in dogs if x["on_last_report"] or x["unsettled"]]
nf = [x for x in dogs if not (x["on_last_report"] or x["unsettled"])]
out(f"   a QB change this week: flagged dogs {sum(1 for x in fl if x['changed'])} of {len(fl)} "
    f"({sum(1 for x in fl if x['changed']) / max(1, len(fl)) * 100:.0f}%), unflagged {sum(1 for x in nf if x['changed'])} of {len(nf)} "
    f"({sum(1 for x in nf if x['changed']) / max(1, len(nf)) * 100:.0f}%)")
out(" 'post later for a flagged team' (the same flagged dogs, bet at the first fair number vs the 1-day look):")
for nm, v in (("flagged", fl), ("unflagged", nf)):
    w = [(pl(x["r"], x["f"][2]), pl(x["r"], k[2])) for x in v
         for k in [next((q for q in x["r"]["looks"] if 0.5 <= q[0] < 1.5), None)] if k]
    if w:
        out(f"   {nm:10s} n {len(w)}: first fair {E.mean(a for a, _ in w) * 100:+.1f}% | the 1-day look {E.mean(b for _, b in w) * 100:+.1f}% | "
            f"waiting = {E.mean(b - a for a, b in w) * 100:+.2f}% a bet (t {E.tstat([b - a for a, b in w]):+.1f})")

out("\nS7 (c) DOES THE MOVE AFTER THE FIRST FAIR NUMBER GO WITH WINNING (dogs +100..+350 at the first fair number, "
    "flat 1u at THAT price, by what the close then did)")
for lg in ("nfl", "ncaaf"):
    v = [(r, base.first_fair(r)) for r in base.build(lg) if base.first_fair(r) and 100 <= base.first_fair(r)[2] <= 350]
    out(f" {lg}")
    for nm, lo, hi in (("the close ran 4+ pts AWAY", -99, -4), ("ran away 2-4", -4, -2), ("ran away 1-2", -2, -1),
                       ("inside a point", -1, 1), ("came to it 1-2", 1, 2), ("came to it 2-4", 2, 4),
                       ("came to it 4+ pts", 4, 99)):
        s = [(r, f) for r, f in v if lo <= (r["close_p"] - f[3]) * 100 < hi]
        a = [pl(r, f[2]) for r, f in s]
        he = [pl(r, f[2]) for r, f in s if r["season"] >= 2023]
        out(f"   {nm:28s} {len(s) / len(v) * 100:4.1f}% of dogs | first fair {E.roi(a)} | held {E.roi(he)} | won "
            f"{sum(1 for r, f in s if r['won']) / max(1, len(s)) * 100:.1f}% (the first fair price said {E.mean(f[3] for r, f in s) * 100:.1f}%, "
            f"the close {E.mean(r['close_p'] for r, f in s) * 100:.1f}%)")
