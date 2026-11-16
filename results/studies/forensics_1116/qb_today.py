"""11/16 FABLE: tonight's NFL game(s) - the QB the engine reads for each side (settled or unknown), his starts on file,
and the key-player edge the read carries. python results/studies/forensics_1116/qb_today.py [game id ...]"""
import sys
sys.path.insert(0, '.')
import sports_data as sd, sports_players as sp, sports_model as sm

games = sd.load_games('nfl')
cache = sp.load()
rows = cache['nfl']
ke = sp.key_edges(games, cache)
ids = sys.argv[1:] or [k for k, g in games.items() if g['status'] == 'pre' and g['start'][:10] <= '2026-11-20']
for gid in ids:
    g = games[gid]
    print(gid, g['start'], g['away_name'], '@', g['home_name'], 'key edge (home +):', ke.get(gid))
    for side in ('home', 'away'):
        t = g[side]
        print('  ', g[side + '_name'], 'settled QB:', sp.qb_settled(rows, t, g['start']), '| last starter:', sp.last_starter(rows, t, g['start']))
        mine = [r for r in rows if str(r['team']) == str(t) and r['start'] < g['start']][-6:]
        for r in mine:
            print('      ', r['start'][:10], r['player'], 'att', r['att'], 'yds', r['yds'], 'td', r['td'], 'int', r['int'])
