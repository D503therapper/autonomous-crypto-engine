"""S11b - ONE VOICE on what's open right now (read-only: nothing is posted, pulled or changed): the engine's main read
(sports.candidates -> sports.read_of, the board's own row on the game's Pacific day, no injury fetch here) against what
our price needs, for every early moneyline play still open. A check that sports_early.main_read finds a row."""
import json
from datetime import datetime, timezone

import elib as E

import sports
import sports_model as sm

out = E.Tee("s11b_open_plays_now_out.txt")
se = E.se
games = {}
for lg in E.sd.LEAGUES:
    try:
        games.update(E.sd.load_games(lg))
    except Exception:                                        # noqa: BLE001
        pass
model = sm.load() if hasattr(sm, "load") else json.load(open(E.os.path.join(E.sd.DATA, "model.json")))
now = datetime.now(timezone.utc)
st = json.load(open(se.PATH))
cache = {}
for p in st["picks"]:
    if p.get("result") or p.get("market") == "total":
        continue
    g = games.get(p["game_id"]) or {}
    if g.get("status") != "pre":
        continue
    mr = se.main_read(p, games, model, None, now, cache)
    if not mr:
        out(f" {p['start'][:10]} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team']:16s} {p['odds']:+5d}: no main read")
        continue
    out(f" {p['start'][:10]} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team']:16s} {p['odds']:+5d}: early read "
        f"{(p.get('own') or 0) * 100:4.1f}% | main read {mr[0] * 100:4.1f}% vs the {mr[1] * 100:4.1f}% the price needs -> "
        f"{'one voice' if mr[0] >= mr[1] else 'the main read FIGHTS it (would not post from 11/12)'}")
