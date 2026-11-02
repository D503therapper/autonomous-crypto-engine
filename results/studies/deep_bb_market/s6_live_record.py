"""S6 - EFFICIENCY: our own live basketball picks (data/sports/picks.json + data/sports/early.json) by pick type -
won-lost, units risked, units won, ROI per unit risked. Leans carry no units (graded flat 1u for the who-wins record)."""
import json
import os
from collections import defaultdict

import lib

out = lib.Out("s6_live_record")
P = json.load(open(os.path.join(lib.ROOT, "data/sports/picks.json")))
E = json.load(open(os.path.join(lib.ROOT, "data/sports/early.json"))).get("picks", [])
acc = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0])   # w, l, risked, won-units, flat
for p in P:
    legs = p.get("legs") or []
    if len(legs) != 1 or p.get("void") or p.get("pulled"):
        continue
    lg = legs[0]
    league = lg.get("league") or (lg.get("game_id") or "").split(":")[0]
    if league not in ("nba", "ncaab") or p.get("status") not in ("won", "lost", "push"):
        continue
    kind = p.get("kind")
    if p.get("lean"):
        kind = "lean"
    elif p.get("floor"):
        kind = "floor"
    elif p.get("dog_play"):
        kind = "runner-up dog play"
    elif p.get("gap"):
        kind = "gap play"
    mk = lg.get("market") or ("spread" if lg.get("spread") is not None or lg.get("line") is not None else "ml")
    key = f"{league} {kind} ({mk})"
    a = acc[key]
    u = float(p.get("units") or 0) if not p.get("lean") else 0.0
    if p["status"] == "won":
        a[0] += 1
        a[3] += u * (float(p.get("dec") or 2) - 1)
        a[4] += float(p.get("dec") or 2) - 1
    elif p["status"] == "lost":
        a[1] += 1
        a[3] -= u
        a[4] -= 1
    a[2] += u
for p in E:
    if p.get("league") not in ("nba", "ncaab") or p.get("result") not in ("won", "lost"):
        continue
    a = acc[f"{p['league']} early {p.get('spot')}"]
    u = float(p.get("units") or 0.5)
    d = lib.dec(p["odds"])
    if p["result"] == "won":
        a[0] += 1; a[3] += u * (d - 1); a[4] += d - 1
    else:
        a[1] += 1; a[3] -= u; a[4] -= 1
    a[2] += u
out.h("LIVE BASKETBALL PICKS BY TYPE (graded, single picks)")
for k, (w, l_, r, uw, fl) in sorted(acc.items()):
    out.note(f"{k:40s} {w:3d}-{l_:<3d} risked {r:5.1f}u  result {uw:+6.2f}u  ROI/unit {uw / r * 100 if r else 0:+6.1f}%  "
             f"flat {fl / (w + l_) * 100 if w + l_ else 0:+6.1f}%")
out.save()
