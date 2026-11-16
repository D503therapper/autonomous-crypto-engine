"""11/16 FABLE - WHY WE LOSE: the live ledger since 10/25, one row a unit play, with what posted it.
python results/studies/forensics_1116/led.py  ->  ~/.cache/d503_forensics1116/ledger.json + a printed table."""
import json, sys, os, collections
sys.path.insert(0, '.')
import sports, sports_early

FROM = sys.argv[1] if len(sys.argv) > 1 else '2026-10-25'
p = json.load(open('data/sports/picks.json'))
e = json.load(open('data/sports/early.json'))
clv = json.load(open('data/sports/clv_record.json'))['picks']
cl = {(c['date'], c['team'], c['kind'], c['market']): c for c in clv}
led = sports.units_ledger(p, e['picks'])
rows = [r for r in led['rows'] if r[1] > 0 and r[0]['date'] >= FROM]
ebykey = {(x['game_id'], x['side']): x for x in e['picks']}


def path(pk):
    k = pk.get('kind')
    if k == 'early':
        return 'early'
    t = []
    for f in ('floor', 'gap', 'dog_play', 'nba_fav', 'ncaab_play', 'forced', 'midday', 'upgraded', 'was_dog',
              'owner_post', 'relabeled'):
        if pk.get(f):
            v = pk[f]
            t.append(f + (':nba' if isinstance(v, dict) and v.get('nba') else '')
                     + (':fb' if isinstance(v, dict) and v.get('fallback') else ''))
    return k + ('[' + ','.join(t) + ']' if t else '')


out = []
for pk, u, net, _ in rows:
    l = pk['legs'][0]
    c = cl.get((pk['date'], l.get('team'), pk.get('kind'), l.get('market')))
    out.append(dict(date=pk['date'], path=path(pk), best=bool(pk.get('best')), lg=l.get('league') or pk.get('league'),
                    team=l.get('team'), opp=l.get('opp'), mk=l.get('market', 'ml'), line=l.get('line'),
                    odds=l.get('odds'), u=u, net=round(net, 2), p=l.get('p'), own=l.get('raw_own'),
                    pm=l.get('p_market'), edge=l.get('edge'), eo=l.get('edge_own'), close=c and c['close'],
                    pts=c and c['pts'], res=l.get('result') or pk.get('status'), score=l.get('score'),
                    reasons=l.get('reasons'), key_edge=l.get('key_edge'), outs=l.get('outs'), stale=l.get('stale'),
                    fresh=l.get('fresh'), tier=pk.get('tier'), floor=pk.get('floor'), home=l.get('home'),
                    gid=l.get('game_id'), fs=l.get('floor_score'), posted=pk.get('posted')))
json.dump(out, open(os.path.expanduser('~/.cache/d503_forensics1116/ledger.json'), 'w'))
for o in out:
    print(f"{o['date'][5:]} {o['path'][:26]:26s} {'*' if o['best'] else ' '} {o['lg'] or '':5s} "
          f"{str(o['team'])[:16]:16s} {o['mk']:3s} {str(o['odds']):>5s} {o['u']:>4} {o['net']:+6.2f} "
          f"p={o['p'] and round(o['p'], 3)} own={o['own']} mkt={o['pm'] and round(o['pm'], 3)} cl={o['close']} "
          f"{o['res']} | {o['score']}")
tot = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0])
for o in out:
    t = tot[o['path']]
    t[0] += o['net'] > 0
    t[1] += o['net'] < 0
    t[3] += o['net']
    t[4] += o['u']
for k, t in sorted(tot.items()):
    print(f"{k:30s} {t[0]}-{t[1]} {t[3]:+.2f}u on {t[4]}u")
print(round(sum(o['net'] for o in out), 2), sum(o['u'] for o in out), sum(o['net'] > 0 for o in out),
      sum(o['net'] < 0 for o in out))
