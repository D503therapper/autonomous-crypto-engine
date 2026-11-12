"""11/12 SWEEP (a) - the open early plays against TODAY's rules (read-only): the paused spot, one voice (the board's
main read vs what our price needs), the fresh-number rule (was the post on a number the book had re-hung?), and the
price now vs the price we got. Usage: python results/studies/sweep_1112/e1_open_early.py > e1_open_early.out"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd      # noqa: E402
import sports_early as se     # noqa: E402
import sports_model as sm     # noqa: E402

games = {}
for lg in sd.LEAGUES:
    try:
        games.update(sd.load_games(lg))
    except Exception:                                        # noqa: BLE001
        pass
model = sm.load() if hasattr(sm, "load") else json.load(open(os.path.join(sd.DATA, "model.json")))
now = datetime.now(timezone.utc)
st = json.load(open(se.PATH))
cache = {}
imp = lambda o: 100 / (o + 100) if o > 0 else -o / (-o + 100)   # noqa: E731
for p in st["picks"]:
    if p.get("result") or p.get("market") == "total":
        continue
    g = games.get(p["game_id"]) or {}
    if g.get("status") != "pre":
        continue
    spot = p.get("spot") or "exam"
    off = se.spot_off(p.get("spot"), p["start"]) if p.get("spot") else False
    mr = se.main_read(p, games, model, None, now, cache)
    fair = se._t(p["fair_at"]) if p.get("fair_at") else None
    posted = se._t(p["posted"])
    fresh = se.line_fresh(p["game_id"], fair, posted) if fair else None
    ff = se.first_fair(p["game_id"], fair - timedelta(hours=se.FRESH_SLACK_H)) if fair else None
    side = p["side"]
    o_now, opp_now = se._int(g.get(f"ml_{side}")), se._int(g.get(f"ml_{'away' if side == 'home' else 'home'}"))
    nv = lambda a, b: imp(a) / (imp(a) + imp(b))            # noqa: E731
    mv = None if o_now is None or opp_now is None or not p.get("opp_odds") else 100 * (nv(o_now, opp_now) - nv(p["odds"], p["opp_odds"]))
    print(f"{p['start'][:10]} {p['league']:5s} {spot:9s} {p['team']:14s} {p['odds']:+5d} {se.units(p)}u posted {p['posted']} "
          f"(fair {p.get('fair_at')}, {'' if fair is None else round((posted - fair).total_seconds() / 3600, 1)}h after)")
    print(f"    spot paused today: {off} | main read: {'none' if not mr else f'{mr[0] * 100:.1f}% vs {mr[1] * 100:.1f}% needed -> ' + ('one voice' if mr[0] >= mr[1] else 'FIGHTS')}"
          f" | posted on a re-hung number: {fresh} (first re-hang on tape: {ff})"
          f" | now {o_now} / {opp_now}" + ("" if mv is None else f" ({mv:+.1f} pts of no-vig win % {'to us' if mv > 0 else 'away'})")
          + f" | early read {(p.get('own') or 0) * 100:.1f}% fades {p.get('fades')}")
