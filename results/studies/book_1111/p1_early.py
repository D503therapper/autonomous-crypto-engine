"""THE BOOK, part 1b - every graded early play, in order, with its spot (data/sports/early.json, read only)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_early  # noqa: E402

e = json.load(open("data/sports/early.json"))
tot = {}
for p in sorted(e["picks"], key=lambda p: p.get("posted") or ""):
    if p.get("result") not in ("won", "lost"):
        continue
    u = sports_early.units(p)
    d = sports._dec(p["odds"])
    net = u * (d - 1) if p["result"] == "won" else -u
    k = (p.get("spot") or "exam band / owner", "from 10/25 (FBS-only blowout)" if (p.get("posted") or "") >= "2026-10-25" else "to 10/24")
    t = tot.setdefault(k, [0, 0, 0.0])
    t[0 if p["result"] == "won" else 1] += 1
    t[2] += net
    print(f"{(p.get('posted') or '')[:10]} {p.get('league'):6s} {str(p.get('spot')):11s} {p['team']:20s} {p['odds']:+5d} {u}u {p['result']:4s} {net:+.2f}u  spots {p.get('spots')} own {p.get('own')} mkt {p.get('mkt')} pulled {bool(p.get('pulled'))}")
print()
for k in sorted(tot):
    print(f"{k[0]:20s} {k[1]:30s} {tot[k][0]}-{tot[k][1]} {tot[k][2]:+.2f}u")
