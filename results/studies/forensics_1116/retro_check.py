"""11/16 FABLE - WHY WE LOSE: today's pre-post checker (sports.pick_checks, built 11/4 and grown since) run over every
pick posted 10/25-11/15 as it was posted - which picks would today's checker HOLD, on which input, and how they did.
(No injury report is on file for those days, so the injury checks can't run; the price-age checks are skipped - the
games are long over. What's left: the named reasons, the stronger team, blowouts, byes, the stale revenge game.)"""
import json, sys, collections
from datetime import datetime, timezone
sys.path.insert(0, '.')
import sports, sports_data as sd, sports_players as sp

sports.REASON_TRUTH_FROM = "0000"
games = sd.load_games()
sp.CACHE = sp.load()
picks = json.load(open('data/sports/picks.json'))
SKIP = ('price', 'price_fresh', 'injury', 'injuries', 'covered', 'started', 'start', 'goalies', 'qb', 'waiting')
T = collections.defaultdict(lambda: [0, 0, 0.0])
ctx = {}
for pk in picks:
    if pk['date'] < '2026-10-25' or pk.get('kind') in sports.PARLAY_KINDS or pk.get('status') not in ('won', 'lost'):
        continue
    l = pk['legs'][0]
    u = sports.leg_units(pk, l) or 0
    try:
        now = datetime.strptime(pk['posted'][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        # the pick as posted, its game put back to 'pre' so the checker reads it as the board did
        g0 = games.get(l['game_id'])
        gs = dict(games)
        if g0:
            gs[l['game_id']] = {**g0, 'status': 'pre', 'home_score': '', 'away_score': ''}
        res = sports.pick_checks({**pk, 'status': 'open'}, gs, None, now, ctx, unit=bool(u))
    except Exception as e:  # noqa: BLE001
        print('ERR', pk['date'], l.get('team'), repr(e)[:100])
        continue
    stale = 'revenge game' in (l.get('reasons') or []) and g0 and sports.stale_revenge(games, g0)
    fails = [(n, w) for n, r, w in res if r == 'fail' and n not in SKIP]
    if stale:
        fails.append(('stale revenge', 'the last meeting is over a season back'))
    net = (u or 1) * ((sports._dec(l['odds']) - 1) if pk['status'] == 'won' else -1)
    for n, w in fails:
        t = T[(n, 'unit' if u else 'lean')]
        t[0] += pk['status'] == 'won'
        t[1] += pk['status'] == 'lost'
        t[2] += net if u else 0
        print(f"{pk['date'][5:]} {pk['kind']:5s} u={u} {l.get('league'):5s} {str(l.get('team'))[:16]:16s} {l.get('odds'):>5} {pk['status']:5s} {n}: {str(w)[:170]}")
    t = T[('ANY' if fails else 'clean', 'unit' if u else 'lean')]
    t[0] += pk['status'] == 'won'
    t[1] += pk['status'] == 'lost'
    t[2] += net if u else 0
for k, t in sorted(T.items()):
    print(k, f"{t[0]}-{t[1]} {t[2]:+.2f}u")
