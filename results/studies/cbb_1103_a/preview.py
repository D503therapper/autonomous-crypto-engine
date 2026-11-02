"""Readiness: the real post_board on a college hoops day, offline - injuries stubbed (no network), the day's posted
picks dropped so the opening board builds fresh. Usage: python preview.py YYYY-MM-DD [all|half|none] [HH:MM]
  all  = every team on the slate covered by an (empty) injury report - the best case
  half = only every other college hoops team covered (the rest UNKNOWN) - the rule check
  none = the college hoops feed dead (None)
Writes results/board_preview.txt (restore it after) and prints it, plus a college hoops summary."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import board_preview as bp      # noqa: E402

day = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "all"
hm = sys.argv[3] if len(sys.argv) > 3 else "08:35"

_games = sd.load_games()
ids = {}
for g in _games.values():
    if g["start"][:10] in (day, (datetime.strptime(day, "%Y-%m-%d").date().replace() .isoformat())):
        pass
    for s in ("home", "away"):
        ids.setdefault(g["league"], set()).add(g[s])


def fake_inj(league):
    if league == "ncaab" and mode == "none":
        return None
    teams = sorted(ids.get(league, ()))
    if league == "ncaab" and mode == "half":
        teams = teams[::2]
    return {t: [] for t in teams}


sd.fetch_injuries = fake_inj
_load = sports._load


def load_wo_day(name, default):
    x = _load(name, default)
    if name == "picks.json":
        x = [p for p in x if p.get("date") != day]
    return x


sports._load = load_wo_day
bp.main(f"{day}T{hm}")
raw = [c for c in sports.LAST_RAW if c.get("league") == "ncaab"]
print(f"\nNCAAB candidates read: {len(raw)} sides on {len({c['game_id'] for c in raw})} games; "
      f"waiting on 'not in our data': {sum(1 for c in raw if any('(not in our data)' in w for w in c.get('waiting') or []))}")
ml = [c for c in raw if c.get("market") == "ml"]
import statistics  # noqa: E402
gaps = [((sports.read_of(c) or 0) - 1 / c["dec"]) for c in ml if c.get("dec")]
if gaps:
    print(f"NCAAB ml read - price: mean {statistics.mean(gaps):+.3f}, max {max(gaps):+.3f}, min {min(gaps):+.3f}")
for c in sorted(ml, key=lambda c: -((sports.read_of(c) or 0) - 1 / c["dec"]))[:12]:
    print(f"  {c['team']:22} {c['odds']:+5} read {sports.read_of(c) or 0:.3f} price {1 / c['dec']:.3f} own_edge {c.get('edge_own')} p {c.get('p')}")
