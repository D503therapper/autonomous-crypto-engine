"""The live hockey dog-side picks (pick_journal.json) against the 10/29 study angles: win streak, won the last meeting, b2b."""
import json
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
rows = {r['id']: r for r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rows.json')))}
j = json.load(open(f'{ROOT}/data/sports/pick_journal.json'))
h = [x for x in j if x.get('league') == 'nhl' and x.get('result') in ('won', 'lost') and x.get('odds', 0) >= 100]
print(len(h), 'graded hockey dog-side picks in the journal')


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


tot = {}
for x in h:
    r = rows.get(x['game_id'])
    if not r:
        print('no row', x['date'], x['team']); continue
    s = 'h' if r['hn'] == x['team'] else 'a'
    o = 'a' if s == 'h' else 'h'
    stk = r[f'stk_{s}']; pw = r['prev_win_h'] if s == 'h' else (None if r['prev_win_h'] is None else 1 - r['prev_win_h'])
    b2b = r[f'b2b_{s}']; ob2b = r[f'b2b_{o}']
    u = x['units'] or 0
    pnl = (dec(x['odds']) - 1) * u if x['result'] == 'won' else -u
    gap = 100 * (x['own_read'] - x['price_says']) if x.get('own_read') and x.get('price_says') else None
    print(f"{x['date']} {x['kind']:5} {'lean' if x['lean'] else 'unit':4} {x['team']:14} {x['odds']:+4} {x['result']:4} u{u} streak {stk:+d} prev_win {pw} b2b {b2b} opp_b2b {ob2b} own-price {gap and round(gap, 1)}")
    for tag, cond in (('win3+', stk >= 3), ('prev_won', pw == 1), ('b2b', b2b == 1), ('all', True)):
        if cond and not x['lean']:
            t = tot.setdefault(tag, [0, 0, 0.0]); t[0] += x['result'] == 'won'; t[1] += x['result'] == 'lost'; t[2] += pnl
print({k: (f'{v[0]}-{v[1]}', round(v[2], 2)) for k, v in tot.items()})
