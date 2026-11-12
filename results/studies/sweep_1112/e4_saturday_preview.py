"""11/12 SWEEP (b) - A LOOK AT SATURDAY 11/14's COLLEGE FOOTBALL DOGS as the board's own pools see them TODAY (read-only,
offline: today's prices, no injury fetch - the official reports for Saturday aren't out; nothing is posted). For each
college football dog +100..+350: the price, the main read, the own read, the dog score, and which pools would take it
(the Dog pool / the runner-up, the 🔍 play before and after the 11/11 cut). A preview, not the board.
Usage: python results/studies/sweep_1112/e4_saturday_preview.py [YYYY-MM-DD] > .../e4_saturday_preview.out"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

DAY = datetime.strptime(sys.argv[1] if len(sys.argv) > 1 else "2026-11-14", "%Y-%m-%d").date()
games = {}
for lg in sd.LEAGUES:
    try:
        games.update(sd.load_games(lg))
    except Exception:  # noqa: BLE001
        pass
model = sm.load() if hasattr(sm, "load") else json.load(open(os.path.join(sd.DATA, "model.json")))
now = datetime.now(timezone.utc)
cands = sports.candidates(games, model, now, DAY, None)
cf = [c for c in cands if c.get("league") == "ncaaf" and c.get("market") == "ml" and 100 <= (c.get("odds") or 0) <= 350]
print(f"{DAY}: {len(cf)} college football dogs +100..+350 with a read (of {sum(1 for c in cands if c.get('league') == 'ncaaf' and c.get('market') == 'ml')} moneyline sides)")
_off, sports.GAP_NCAAF_OFF_FROM = sports.GAP_NCAAF_OFF_FROM, None       # the 🔍 pool as it stood BEFORE the 11/12 pause
gap = {c["game_id"] for c in sports.gap_plays(cands, ())}
sports.GAP_NCAAF_OFF_FROM = _off
_lg, sports.DOG_PLAY_LEAGUES_1113 = sports.DOG_PLAY_LEAGUES_1113, sports.DOG_PLAY_LEAGUES   # ...and the runner-up pool
dp = {c["game_id"] for c in sports.dog_plays(cands, ())}
sports.DOG_PLAY_LEAGUES_1113 = _lg
for c in sorted(cf, key=lambda c: -(sports.dog_score(c) if c.get("dog_score") is None else c["dog_score"])):
    rd = sports.read_of(c)
    try:
        gated = sports.dog_gate(dict(c))
    except Exception:  # noqa: BLE001
        gated = None
    own = c.get("raw_own")
    print(f"  {c['team'][:18]:18s} {'H' if c.get('home') else 'A'} v {c['opp'][:16]:16s} {c['odds']:+4d} mkt {c['p_market'] * 100:4.1f}% main read {('%4.1f%%' % (rd * 100)) if rd is not None else '  -  '} "
          f"raw own {('%4.1f%%' % (own * 100)) if own is not None else '  -  '} dog score {sports.dog_score(c):+5.1f} | dog gate {bool(gated)} | "
          f"🔍 before the 11/12 pause {'YES' if c['game_id'] in gap else 'no'} | runner-up pool before the cut {'YES' if c['game_id'] in dp else 'no'} | trap {bool(c.get('trap'))} waiting {bool(c.get('waiting'))} | {'; '.join(c.get('reasons') or [])[:90]}")
