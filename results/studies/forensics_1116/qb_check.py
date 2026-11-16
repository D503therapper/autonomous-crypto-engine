"""11/16 FABLE - WHY WE LOSE: every football / hockey pick since 10/25 - the QB / goalie the engine ASSUMED (the last
starter; in hockey the leg's own projected goalie when stamped) against the man who really started, both sides.
A pick whose read carried a key-player edge on a man who didn't play = a stale input."""
import json, sys, collections
sys.path.insert(0, '.')
import sports, sports_players as sp, sports_early

FROM = sys.argv[1] if len(sys.argv) > 1 else '2026-10-25'
cache = sp.load()
picks = json.load(open('data/sports/picks.json'))
early = json.load(open('data/sports/early.json'))['picks']
import sports_data as sd
games = sd.load_games()


def actual(lg, gid, team):
    for r in cache.get(lg) or []:
        if r['gid'] == gid and str(r['team']) == str(team):
            return r['player']
    return None


tot = collections.Counter()
rows = []
for pk in picks:
    if pk['date'] < FROM or pk.get('kind') in sports.PARLAY_KINDS:
        continue
    for l in pk.get('legs') or []:
        lg = l.get('league')
        if lg not in ('nfl', 'ncaaf'):
            continue
        g = games.get(l['game_id'])
        if not g:
            continue
        me, op = (g['home'], g['away']) if l['side'] == 'home' else (g['away'], g['home'])
        res = l.get('result') or pk.get('status')
        u = sports.leg_units(pk, l) or 0
        out = []
        chg = False
        for tag, t in (('us', me), ('them', op)):
            a = sp.last_starter(cache[lg], t, g['start'])
            s2 = sp.qb_settled(cache[lg], t, g['start'])
            b = actual(lg, g['id'], t)
            if a != b:
                chg = True
            out.append(f"{tag}: assumed {a}{'' if s2 else ' (NOT settled)'} / started {b}{'' if a == b else '  <-- WRONG MAN'}")
        ke = l.get('key_edge')
        qb_reason = any('QB play' in r for r in (l.get('reasons') or []))
        tot[('wrong' if chg else 'right', 'unit' if u else 'lean', res)] += 1
        rows.append((pk['date'], pk['kind'], u, l['team'], l.get('odds'), l.get('market'), ke, qb_reason, res, chg, out))
for r in rows:
    print(f"{r[0][5:]} {r[1]:5s} u={r[2]} {r[3]:16s} {r[4]} {r[5]} key={r[6] is not None and round(r[6], 2)} qbreason={r[7]} {r[8]} {'WRONG QB' if r[9] else ''}")
    for o in r[10]:
        if 'WRONG' in o or 'NOT settled' in o:
            print('      ', o)
print(dict(tot))
