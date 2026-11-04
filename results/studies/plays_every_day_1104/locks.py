"""11/4 - THE LOCKS: every rule that blocks a Lock, judged on the 10/30 funnel rows (train 2023-25 / held out 2025-27) -
which blocks protected ROI, which only cut winners. Plus the live Lock count by week (picks.json)."""
import glob
import json
import sys
from collections import defaultdict, Counter
from datetime import datetime

D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030"
rows = []
for q in sorted(glob.glob(D + "/f[A-D].jsonl")) + [D + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost", "push")]
by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)
HELD = "2025-07-01"


def pnl(r, u=1.0):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def own_p(r):
    return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]


def gap(r):
    o = own_p(r)
    return None if o is None or r.get("p_market") is None else 100 * (o - r["p_market"])


def cell(name, rs, u=lambda r: 1.0):
    w = sum(r["result"] == "won" for r in rs)
    l = sum(r["result"] == "lost" for r in rs)
    tr = [r for r in rs if r["date"] < HELD]
    he = [r for r in rs if r["date"] >= HELD]
    f = lambda xs: (100 * sum(pnl(r, u(r)) for r in xs) / max(1e-9, sum(u(r) for r in xs if r["result"] != "push")), sum(r["result"] != "push" for r in xs))   # noqa: E731
    seas = defaultdict(float)
    for r in rs:
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        seas[y if m >= 7 else y - 1] += pnl(r, u(r))
    print(f"  {name:78} {w}-{l} {f(rs)[0]:+6.1f}% on {f(rs)[1]:4}  train {f(tr)[0]:+6.1f}% ({f(tr)[1]:3})  held {f(he)[0]:+6.1f}% ({f(he)[1]:3})  "
          f"up {sum(v > 0 for v in seas.values())}/{len(seas)}")


# ---- the live Lock count by week
P = json.load(open(sys.argv[1] + "/data/sports/picks.json"))
locks = [p for p in P if p["kind"] == "lock" and p.get("status") != "waiting" and not p.get("lean")]
wk = Counter()
days = Counter()
for p in P:
    if p.get("status") == "waiting" or p["date"] < "2026-09-27":
        continue
    days[p["date"]] += 0
for p in locks:
    d = datetime.strptime(p["date"], "%Y-%m-%d")
    wk[d.strftime("%G-W%V")] += 1
board_days = sorted(days)
print("LIVE LOCKS by ISO week:", dict(sorted(wk.items())))
before = [p for p in locks if p["date"] <= "2026-10-28"]
after = [p for p in locks if p["date"] >= "2026-10-29"]
nb = sum(1 for d in board_days if d <= "2026-10-28")
na = sum(1 for d in board_days if d >= "2026-10-29")
print(f"9/27-10/28: {len(before)} Locks on {nb} board days ({len(before) / max(1, nb):.2f}/day); 10/29-11/4: {len(after)} on {na} days ({len(after) / max(1, na):.2f}/day)")
for p in locks:
    l = p["legs"][0]
    print("  ", p["date"], l.get("league"), l.get("team"), l.get("odds"), p.get("status"), "units", p.get("units"), "backup" if l.get("backup_lock") else "", "thin" if l.get("thin") else "")

# ---- the replay: the Lock funnel on favorites -150..-101 (ml)
favs = [r for r in rows if -150 <= r["odds"] < 100 and not r["trap"] and not r.get("waiting")]
print("\nTHE LOCK FUNNEL (favorites -150..-101, moneyline, clean):")
cell("every favorite -150..-101", favs)
base = [r for r in favs if r["good"] and r["lock_ok"] and not r["fighting"]]
cell("good + lock_ok (p 56%+) + not fighting  [the Lock pool]", base)
full = [r for r in base if r["own_agrees"] and r["real_value"] and not r["nhl_pricey"]]
cell("  + own_agrees + real_value + not nhl_pricey  [the full Lock test]", full)
cell("     of those in -119..-101 (the S6 skip band)", [r for r in full if r["odds"] > -120])
cell("     of those -150..-120", [r for r in full if r["odds"] <= -120])
cell("     of those THIN (own edge under 3%) - NO_THIN_LOCK drops them", [r for r in full if r.get("thin")])
cell("     of those not thin", [r for r in full if not r.get("thin")])
cell("     not thin, -150..-120 (what can be the Lock today)", [r for r in full if not r.get("thin") and r["odds"] <= -120])
cell("     not thin, -150..-120, own gap under 7 (2u)", [r for r in full if not r.get("thin") and r["odds"] <= -120 and (gap(r) or 0) < 7])
cell("     not thin, -150..-120, own gap 7+ (1u)", [r for r in full if not r.get("thin") and r["odds"] <= -120 and (gap(r) or 0) >= 7])
cell("     thin, -150..-120 (the cut: would they have paid?)", [r for r in full if r.get("thin") and r["odds"] <= -120])
cell("     thin, -119..-101", [r for r in full if r.get("thin") and r["odds"] > -120])
cell("     not thin, -119..-101 (the band cut)", [r for r in full if not r.get("thin") and r["odds"] > -120])
cell("  good + lock_ok but own_agrees FALSE (the own-read block)", [r for r in base if not r["own_agrees"]])
cell("  good + lock_ok + own_agrees but real_value FALSE", [r for r in base if r["own_agrees"] and not r["real_value"]])
cell("  good + lock_ok + own_agrees + real_value but nhl_pricey", [r for r in base if r["own_agrees"] and r["real_value"] and r["nhl_pricey"]])
cell("  not lock_ok (p under 56%) but own read 56%+ and own_beats (the backup Lock pool)", [r for r in favs if r["good"] and not r["lock_ok"] and not r["fighting"] and (own_p(r) or 0) >= 0.56 and r["own_beats"]])
cell("     ...-150..-120", [r for r in favs if r["good"] and not r["lock_ok"] and not r["fighting"] and (own_p(r) or 0) >= 0.56 and r["own_beats"] and r["odds"] <= -120])
cell("  nba_week_one favorites passing the full test", [r for r in full if r.get("nba_week_one")])
print("\nBy league, the full Lock test, not thin, -150..-120:")
for lg in ("nhl", "nba", "mlb", "nfl", "ncaaf", "ncaab"):
    cell(f"  {lg}", [r for r in full if not r.get("thin") and r["odds"] <= -120 and r["league"] == lg])
    cell(f"  {lg} THIN -150..-120", [r for r in full if r.get("thin") and r["odds"] <= -120 and r["league"] == lg])
print("\nThe thin Lock by how thin (own edge per dollar), -150..-120:")
for lo, hi in ((0.0, 0.01), (0.01, 0.02), (0.02, 0.03)):
    cell(f"  own edge {lo:.2f}..{hi:.2f}", [r for r in full if r["odds"] <= -120 and lo <= (r.get("edge_own") or 0) < hi])
print("\nThe posted Lock in the rows (kind lock), by the rows' units:")
lk = [r for r in rows if r["kind"] == "lock"]
cell("  all kind lock", lk)
cell("  thin (dropped since 10/29)", [r for r in lk if r.get("thin")])
cell("  not thin", [r for r in lk if not r.get("thin")])
cell("  backup (units 0.5, not thin)", [r for r in lk if not r.get("thin") and r.get("units") == 0.5])
# one Lock a day: the best by rank_p among the full test, with / without the thin cut
print("\nONE LOCK A DAY (the likeliest by rank_p among the full-test favorites):")
for name, flt in (("today: not thin, -150..-120", lambda r: not r.get("thin") and r["odds"] <= -120),
                  ("thin allowed, -150..-120", lambda r: r["odds"] <= -120),
                  ("thin allowed, -150..-101 (no band cut)", lambda r: True),
                  ("not thin, -150..-101", lambda r: not r.get("thin"))):
    picks = []
    for d, rs in by_day.items():
        pool = [r for r in rs if r in full and flt(r)] if False else [r for r in rs if -150 <= r["odds"] < 100 and not r["trap"] and not r.get("waiting")
                                                                        and r["good"] and r["lock_ok"] and not r["fighting"] and r["own_agrees"] and r["real_value"] and not r["nhl_pricey"] and flt(r)]
        if pool:
            picks.append(max(pool, key=lambda r: (round(r["rank_p"] or 0, 3), r["edge_own"] or 0)))
    cell(name, picks)
    cell("   ...sized 2u gap<7 / 1u (football 1u)", picks, u=lambda r: 1.0 if r["league"] in ("nfl", "ncaaf") or (gap(r) or 0) >= 7 else 2.0)
    print(f"      Locks on {len(picks)} of {len(by_day)} board days")
