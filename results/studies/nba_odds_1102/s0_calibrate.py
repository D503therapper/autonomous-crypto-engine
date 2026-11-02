"""STEP 0 (11/2): WHAT THE NEW DATA REALLY HOLDS, and how far the game-day morning price is from the open.
(a) The 2020-23 history: how many regular-season games hold a next-day (20h+) look vs only the game-day 15:00Z look.
(b) Our own hourly line history this season (data/sports/line_history, 2026-27 NBA): the ESPN open (the first price),
    the price at the game day's 15:00Z, the close - how much of the open->close no-vig move is already in by 15:00Z.
    That says how well the 2020-23 morning look stands in for the open the 2023-26 studies used."""
import glob, json, os, statistics, sys
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

g = lib.load_games()
lk = lib.looks(g)
prev = lib.prev_tips(g)
reg = [gid for gid in lk if g[gid]["stype"] == "2"]
n20 = sum(1 for gid in reg if any(c["h_before"] >= 20 for c in lk[gid]["ml"]))
nf = sum(1 for gid in reg if lib.pick_looks(lk, prev, gid)[0])
nm = sum(1 for gid in reg if lib.pick_looks(lk, prev, gid)[1])
hb = [lib.pick_looks(lk, prev, gid)[1]["h_before"] for gid in reg if lib.pick_looks(lk, prev, gid)[1]]
print(f"(a) 2020-23 regular season: {len(reg)} games with a look; a 20h+ (next-day) look on {n20} ({n20 / len(reg):.1%}),"
      f" fair {nf}; the game-day morning look on {nm} (median {statistics.median(hb):.1f}h before tip)")

rows = []
for p in sorted(glob.glob(os.path.join(lib.ROOT, "data/sports/line_history/*.jsonl"))):
    for line in open(p):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if str(r.get("g", "")).startswith("nba:"):
            rows.append(r)
by = {}
for r in rows:
    by.setdefault(r["g"], []).append(r)
moves = []
for gid, rs in by.items():
    x = g.get(gid)
    if not x or x.get("status") != "final" or x.get("stype") != "2":
        continue
    try:
        oh, oa, ch, ca = (int(float(x[k])) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
    except (TypeError, ValueError, KeyError):
        continue
    tip = lib.t(x["start"])
    gd = (tip - timedelta(hours=9)).date()
    cut = f"{gd.isoformat()}T15:00Z"
    m = None
    for r in sorted(rs, key=lambda r: r["t"]):
        if r["t"] <= cut and r.get("h") not in (None, "") and r.get("a") not in (None, ""):
            m = r
    if m is None:
        continue
    po, pm, pc = lib.nv(oh, oa), lib.nv(int(float(m["h"])), int(float(m["a"]))), lib.nv(ch, ca)
    moves.append((pc - po, pm - po, pc - pm))
tot = [abs(a) for a, _, _ in moves]
part = [abs(b) for _, b, _ in moves]
late = [abs(c) for _, _, c in moves]
same = sum(1 for a, b, _ in moves if abs(a) >= 0.01 and a * b > 0 and abs(b) >= abs(a) * 0.5)
big = [m for m in moves if abs(m[0]) >= 0.01]
print(f"(b) 2026-27 NBA finals with the open, a game-day 15:00Z price and the close: {len(moves)}")
if moves:
    print(f"    mean |open->close| {statistics.mean(tot) * 100:.2f} pts; |open->15:00Z| {statistics.mean(part) * 100:.2f};"
          f" |15:00Z->close| {statistics.mean(late) * 100:.2f}")
    print(f"    of {len(big)} games that moved 1+ pt open->close, {same} ({same / max(1, len(big)):.0%}) had half+ of it in by"
          f" 15:00Z game day; corr(open->15Z, open->close) "
          f"{statistics.correlation([b for _, b, _ in moves], [a for a, _, _ in moves]):.2f}")
