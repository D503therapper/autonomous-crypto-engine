"""11/16 FABLE - WHY WE LOSE: every hockey pick since 10/25 - the goalies the posted card named (its breakdown lines,
the 🔄 updates) against the men who really started (the box scores). A goalie named on the card who didn't start = a
stale input on the card; the read barely moves on it (the hockey 'key' weight is ~0), the roles weight can."""
import json, re, sys, collections
sys.path.insert(0, '.')
import sports, sports_players as sp, sports_data as sd

FROM = sys.argv[1] if len(sys.argv) > 1 else '2026-10-25'
cache = sp.load()
games = sd.load_games('nhl')
by_game = collections.defaultdict(dict)
goalies = set()
for r in cache.get('nhl') or []:
    by_game[r['gid']][str(r['team'])] = r['player']
    goalies.add(r['player'])
picks = json.load(open('data/sports/picks.json'))
tot = collections.Counter()
for pk in picks:
    if pk['date'] < FROM or pk.get('kind') in sports.PARLAY_KINDS:
        continue
    for l in pk.get('legs') or []:
        if l.get('league') != 'nhl':
            continue
        g = games.get(l['game_id'])
        if not g:
            continue
        me, op = (g['home'], g['away']) if l['side'] == 'home' else (g['away'], g['home'])
        act = {by_game[g['id']].get(str(me)), by_game[g['id']].get(str(op))}
        text = ' '.join(str(x) for x in (l.get('breakdown') or [])) + ' ' + str(l.get('why_line') or '')
        named = {n for n in goalies if n and n in text}
        wrong = sorted(named - act)
        u = sports.leg_units(pk, l) or 0
        res = l.get('result') or pk.get('status')
        greason = [r for r in (l.get('reasons') or []) if 'goalie' in r]
        tot[('wrong' if wrong else 'named ok' if named else 'none named', 'unit' if u else 'lean', res)] += 1
        if wrong or greason:
            print(f"{pk['date'][5:]} {pk['kind']:5s} u={u} {l['team']:14s} {l['odds']:>5} {res:5s} started={sorted(x for x in act if x)} "
                  f"named-but-did-not-start={wrong} roles={l.get('g_role_me')}/{l.get('g_role_opp')} fresh={l.get('fresh')} {greason}")
for k, v in sorted(tot.items()):
    print(k, v)
