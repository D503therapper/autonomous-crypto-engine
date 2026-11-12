"""11/12 DEEP PROGRAM - C1 / C2: COLLEGE HOOPS, LIVE (11/2 on): every college hoops pick on the board (picks.json) by
kind - the slot plays (NCAAB_PLAY_*: favorite / dog), the 🔍 gap twin, the ½u spread stack play, the leans by market -
and the early box's hoops plays (early.json: the altitude over, the road-dog fade), with the price, the read and the
result; then the tracker's college hoops lines (lead_record.json) that have 15+ graded rows.
Usage: python results/studies/deep_1112/c2_hoops_live.py > results/studies/deep_1112/c2_hoops_live.out"""
import json, os, sys
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports                   # noqa: E402

P = json.load(open("data/sports/picks.json"))
E = json.load(open("data/sports/early.json"))
LR = json.load(open("data/sports/lead_record.json"))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


rows = defaultdict(list)
for pk in P:
    leg = (pk.get("legs") or [{}])[0]
    if leg.get("league") != "ncaab" or len(pk.get("legs") or []) != 1:
        continue
    try:
        kind = sports.posted_kind(pk)
    except Exception:              # noqa: BLE001
        kind = pk.get("kind")
    if pk.get("lean"):
        kind = f"lean ({leg.get('market')})"
    try:
        u = 0.0 if pk.get("lean") else float(sports.units_for(pk) or 0)
    except Exception:              # noqa: BLE001
        u = 0.0
    rows[kind].append((pk, leg, u))
print("COLLEGE HOOPS ON THE BOARD, by kind (graded picks; open ones counted apart)")
for kind in sorted(rows, key=str):
    rs = rows[kind]
    g = [(pk, leg, u) for pk, leg, u in rs if pk.get("status") in ("won", "lost")]
    w = sum(pk["status"] == "won" for pk, _, _ in g)
    un = sum(u * ((dec(leg["odds"]) - 1) if pk["status"] == "won" else -1) for pk, leg, u in g)
    fl = sum((dec(leg["odds"]) - 1) if pk["status"] == "won" else -1 for pk, leg, _ in g)
    print(f"  {str(kind):22s} {w}-{len(g) - w}  units {un:+.2f}  flat {100 * fl / max(1, len(g)):+.1f}%  (open {sum(pk.get('status') == 'open' for pk, _, _ in rs)}, push {sum(pk.get('status') == 'push' for pk, _, _ in rs)})")
    for pk, leg, u in rs:
        line = "" if leg.get("line") is None else f" {leg['line']:+g}"
        print(f"      {pk['date']} {leg.get('team', '?')[:18]:18s}{line:7s} {leg.get('odds'):+5d} {u:g}u {pk.get('status'):5s} win% {leg.get('p', 0):.3f} mkt {leg.get('p_market') or 0:.3f} {str((pk.get('ncaab_play') or {}).get('slot') or pk.get('stack') or '')[:40]}")
print("\nTHE EARLY BOX, college hoops")
by = defaultdict(list)
for p in E.get("picks", []) + E.get("pulled", []):
    if p.get("league") == "ncaab":
        by[(p.get("spot"), "pulled" if p in E.get("pulled", []) else "posted")].append(p)
for k, rs in sorted(by.items(), key=str):
    g = [p for p in rs if p.get("result") in ("won", "lost")]
    w = sum(p["result"] == "won" for p in g)
    un = sum((p.get("units") or 0) * ((dec(p.get("odds") or -110) - 1) if p["result"] == "won" else -1) for p in g)
    print(f"  {str(k):34s} {w}-{len(g) - w}  units {un:+.2f}  (rows {len(rs)})")
print("\nTHE TRACKER'S COLLEGE HOOPS LINES WITH 15+ GRADED ROWS")
for tag, r in sorted(LR.items(), key=lambda kv: -(kv[1].get("w", 0) + kv[1].get("l", 0))):
    n = r.get("w", 0) + r.get("l", 0)
    if n >= 15 and ("hoops" in tag.lower() or "ncaab" in tag.lower()):
        print(f"  {tag[:86]:86s} {r['w']}-{r['l']}  {100 * r.get('roi', 0):+.1f}%")
