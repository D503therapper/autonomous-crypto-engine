"""10/30 SIZING - the LIVE sanity check: every graded unit play since 9/27 (board picks.json + early.json), by kind, sport,
SIZE and thin / real, and the same plays re-sized flat 1u. Never the judge (a few weeks) - a check the replay isn't fooling
us. Usage (from the repo root): python results/studies/sizing_1030/live.py > results/studies/sizing_1030/live.out"""
import json
import os
import sys
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, REPO)
os.chdir(REPO)
import sports                   # noqa: E402

picks = json.load(open("data/sports/picks.json"))
early = json.load(open("data/sports/early.json"))
FROM = "2026-09-27"
rows = []
for p in picks:
    if p["date"] < FROM or p.get("lean") or p["status"] not in ("won", "lost", "push") or p["kind"] in sports.PARLAY_KINDS:
        continue
    u = p.get("units")
    if u is None:
        u = sports.units_for(p)
    if not u:
        continue
    leg = p["legs"][0]
    k = sports.posted_kind(p)
    if k == "play":
        k = "floor" if p.get("floor") else "gap" if p.get("gap") else "dogplay" if p.get("dog_play") else \
            "nbafav" if p.get("nba_fav") else "play"
    if k == "lock" and leg.get("backup_lock"):
        k = "backup"
    if p.get("owner_post"):
        k = "owner:" + k
    rows.append({"date": p["date"], "kind": k, "league": leg["league"], "team": leg.get("team"), "odds": leg["odds"],
                 "dec": leg["dec"], "units": u, "status": p["status"], "thin": sports.thin_edge(leg), "src": "board"})
for e in early["picks"]:
    e.setdefault("date", (e.get("start") or "")[:10])
    if e["date"] < FROM or e.get("result") not in ("won", "lost", "push") or not e.get("units"):
        continue
    rows.append({"date": e["date"], "kind": "early:" + e["spot"], "league": e["league"], "team": e["team"], "odds": e["odds"],
                 "dec": sports._dec(e["odds"]), "units": e["units"], "status": e["result"], "thin": None, "src": "early"})


def pnl(r, u=None):
    u = r["units"] if u is None else u
    return u * (r["dec"] - 1) if r["status"] == "won" else -u if r["status"] == "lost" else 0.0


def st(rs, label):
    rs = [r for r in rs if r["status"] in ("won", "lost")]
    if not rs:
        return
    w = sum(r["status"] == "won" for r in rs)
    net = sum(pnl(r) for r in rs)
    risk = sum(r["units"] for r in rs)
    flat = sum(pnl(r, 1) for r in rs)
    print(f"  {label:40s} {w:3d}-{len(rs) - w:<3d} {net:+7.2f}u on {risk:5.1f}u ROI {100 * net / risk:+6.1f}%  | flat 1u {flat:+6.2f}u ({100 * flat / len(rs):+6.1f}%)")


print(f"{len(rows)} graded unit plays since {FROM}")
st(rows, "ALL")
for title, key in (("KIND", "kind"), ("SPORT", "league"), ("SIZE", "units")):
    print(f"\n== by {title}")
    by = defaultdict(list)
    for r in rows:
        by[r[key]].append(r)
    for k, v in sorted(by.items(), key=lambda x: (-len(x[1]), str(x[0]))):
        st(v, str(k))
print("\n== Dog of the Day by sport")
for lg in ("nhl", "ncaaf", "nfl", "nba", "mlb"):
    st([r for r in rows if r["kind"] == "dog" and r["league"] == lg], f"dog {lg}")
print("\n== Locks by sport and size")
for r in sorted([r for r in rows if r["kind"] in ("lock", "backup")], key=lambda r: r["date"]):
    print(f"  {r['date']} {r['kind']:6s} {r['league']:5s} {r['team']:18s} {r['odds']:+5d} {r['units']}u {r['status']}")
print("\n== the Dog of the Day by price and thin (the 10/30 schedule sizes on the price)")
for lo, hi in ((100, 150), (151, 350)):
    for th in (True, False):
        st([r for r in rows if r["kind"] == "dog" and lo <= r["odds"] <= hi and r["thin"] == th], f"dog +{lo}..+{hi} {'thin' if th else 'real'}")
print("\n== thin vs real (board)")
st([r for r in rows if r["src"] == "board" and r["thin"]], "thin")
st([r for r in rows if r["src"] == "board" and not r["thin"]], "real")
