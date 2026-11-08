"""11/8 S9 - WHERE THE LIVE SLIDE COMES FROM (the live record 70-80, +26.5u since 9/27; Saturday 11/7 3-7 -5.4u): every
graded unit pick in data/sports/picks.json by kind x league, before / after the 10/31 sizing (SIZING_1031_FROM), units
as posted and flat 1u, wins vs the vigged price (z). Read-only - the picks file is never written."""
import json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

pk = json.load(open("data/sports/picks.json"))
out = []


def kind(x):
    if x.get("gap"):
        return "🔍 gap play"
    if x.get("dog_play"):
        return "runner-up dog play"
    if x.get("floor"):
        return "floor play"
    if x.get("best"):
        return "⭐ best pick"
    return x.get("kind") or "?"


cells = defaultdict(list)
for x in pk:
    if x.get("status") not in ("won", "lost") or not x.get("units") or x.get("void") or x.get("pulled"):
        continue
    legs = x.get("legs") or [{}]
    if len(legs) != 1:
        continue
    l = legs[0]
    d = l.get("dec") or x.get("dec") or sports._dec(l.get("odds") or x.get("american") or 100)
    won = x["status"] == "won"
    u = float(x["units"])
    row = (x["date"], l.get("league"), u, d, won)
    k, per = kind(x), ("from 10/31" if x["date"] >= sports.SIZING_1031_FROM else "to 10/30")
    for key in (("ALL", per), (k, per), (k, "all"), (f"{k} / {l.get('league')}", "all"), ("ALL", "all"),
                (f"league {l.get('league')}", "all"), (f"league {l.get('league')}", per),
                (("thin" if sports.thin_edge(l) else "real edge"), per)):
        cells[key].append(row)


def line(name, xs):
    n = len(xs)
    w = sum(r[4] for r in xs)
    uu = sum(r[2] * ((r[3] - 1) if r[4] else -1) for r in xs)
    flat = sum(((r[3] - 1) if r[4] else -1) for r in xs)
    exp = sum(1 / r[3] for r in xs)
    var = sum((1 / r[3]) * (1 - 1 / r[3]) for r in xs)
    z = (w - exp) / var ** 0.5 if var else 0
    return f"  {name:42s} {w:3d}-{n - w:<3d} as posted {uu:+7.2f}u on {sum(r[2] for r in xs):5.1f}u | flat {flat:+6.2f}u ({flat / n:+6.1%}) z {z:+.2f}"


for per in ("all", "to 10/30", "from 10/31"):
    out.append(f"\n== {per}")
    for k in sorted({k for k, p in cells if p == per}, key=lambda k: (not k.startswith("ALL"), k)):
        out.append(line(k, cells[(k, per)]))
# the last 9 days by day
out.append("\n== by day, from 10/31 (as posted)")
by = defaultdict(list)
for r in cells[("ALL", "from 10/31")]:
    by[r[0]].append(r)
for d in sorted(by):
    out.append(line(d, by[d]))
txt = "\n".join(out)
print(txt)
open(os.path.join(HERE, "s9_out.txt"), "w").write(txt + "\n")
