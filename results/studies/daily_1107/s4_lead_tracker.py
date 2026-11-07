"""11/7 S4 - the lead tracker (data/sports/lead_tracker.json graded as sports_leads.grade does): every tag at 100+ graded
games, split by league, price band, the first vs second half of its rows, and how much of the profit the 3 biggest
wins carry. Read-only."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_leads  # noqa: E402

rows = sports_leads.load()
lgs = sorted({r.get("league") for r in rows if r.get("league")})
games = {}
for lg in lgs:
    try:
        games.update(sd.load_games(lg))
    except Exception as e:  # noqa: BLE001
        print("no games", lg, e)
graded = defaultdict(list)   # tag -> [(day, league, odds, won, net)]
for r in rows:
    g = games.get(r["game_id"]) or {}
    if g.get("status") != "final" or r.get("market") == "spread":
        continue
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, ValueError, TypeError):
        continue
    if hs == as_:
        continue
    won = (hs > as_) == (r["side"] == "home")
    o = r.get("odds") or 100
    net = (o / 100 if o > 0 else 100 / -o) if won else -1.0
    for t in r["tags"]:
        if sports_leads.counts(t, o):
            graded[t].append((r["day"], r.get("league"), o, won, net))
out = []


def line(name, xs):
    n = len(xs)
    if not n:
        return f"  {name:34s} 0"
    w = sum(x[3] for x in xs)
    u = sum(x[4] for x in xs)
    exp = sum(1 / lib.dec(x[2]) for x in xs)
    var = sum((1 / lib.dec(x[2])) * (1 - 1 / lib.dec(x[2])) for x in xs)
    z = (w - exp) / var ** 0.5 if var else 0
    return f"  {name:34s} {w}-{n - w} {u:+7.2f}u {u / n:+6.1%}  z {z:+.2f} (wins vs the vigged price)"


for t, xs in sorted(graded.items(), key=lambda kv: -len(kv[1])):
    if len(xs) < 100:
        continue
    xs.sort()
    out.append(f"\n{t}  ({xs[0][0]} .. {xs[-1][0]})")
    out.append(line("ALL", xs))
    for lg in sorted({x[1] for x in xs}):
        out.append(line(f"league {lg}", [x for x in xs if x[1] == lg]))
    out.append(line("dogs +100..", [x for x in xs if x[2] >= 100]))
    out.append(line("favorites", [x for x in xs if x[2] < 100]))
    h = len(xs) // 2
    out.append(line("first half of rows", xs[:h]))
    out.append(line("second half of rows", xs[h:]))
    wins = sorted((x[4] for x in xs if x[3]), reverse=True)
    out.append(f"  the 3 biggest wins carry {sum(wins[:3]):+.2f}u of {sum(x[4] for x in xs):+.2f}u "
               f"(prices {sorted((x[2] for x in xs if x[3]), reverse=True)[:3]})")
    by_day = defaultdict(float)
    for x in xs:
        by_day[x[0][:7]] += x[4]
    out.append("  by month: " + ", ".join(f"{k} {v:+.1f}u" for k, v in sorted(by_day.items())))
txt = "\n".join(out)
print(txt)
open(os.path.join(lib.OUT, "s4_out.txt"), "w").write(txt + "\n")
