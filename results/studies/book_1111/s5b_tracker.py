"""STUDY 5b - the LIVE paper tracker's hockey favorite tags (data/sports/lead_tracker.json, read only - every NHL favorite
the engine read since 10/1, tagged before the game): 'hockey fav weighed UP' / 'DOWN', by price band, with the z against
the price. This is the forward (never-fit) check on s5's replay cell."""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

import sports_data as sd  # noqa: E402
tr = json.load(open("data/sports/lead_tracker.json"))
G = sd.load_games("nhl")
for r in tr:
    g = G.get(r["game_id"]) or {}
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, ValueError, TypeError):
        continue
    if g.get("status") == "final" and hs != as_:
        r["result"] = "won" if (hs > as_) == (r["side"] == "home") else "lost"
print("keys of a row:", sorted(tr[-1].keys()))


def line(name, rs):
    rs = [r for r in rs if r.get("result") in ("won", "lost")]
    if not rs:
        print(f"  {name:52s} none graded")
        return
    w = sum(r["result"] == "won" for r in rs)
    dec = [sports._dec(r["odds"]) for r in rs]
    fl = sum((d - 1) if r["result"] == "won" else -1 for r, d in zip(rs, dec))
    bev = sum(1 / d for d in dec)
    var = sum((1 / d) * (1 - 1 / d) for d in dec)
    print(f"  {name:52s} {w}-{len(rs) - w}  flat {100 * fl / len(rs):+6.1f}%  price expects {bev:5.1f}  z {(w - bev) / math.sqrt(var):+.2f}")


for tag in ("hockey fav weighed UP", "hockey fav weighed DOWN (fade)"):
    rs = [r for r in tr if tag in (r.get("tags") or [])]
    print(tag, len(rs))
    line("all", rs)
    line("-150..-101", [r for r in rs if -150 <= r["odds"] <= -101])
    line("-200..-151", [r for r in rs if -200 <= r["odds"] <= -151])
    line("past -200", [r for r in rs if r["odds"] < -200])
    line("-150..-101 home", [r for r in rs if -150 <= r["odds"] <= -101 and r.get("side") == "home"])
    line("-150..-101 road", [r for r in rs if -150 <= r["odds"] <= -101 and r.get("side") == "away"])
    for mo in ("2026-10", "2026-11"):
        line(f"-150..-101 {mo}", [r for r in rs if -150 <= r["odds"] <= -101 and r["day"].startswith(mo)])
