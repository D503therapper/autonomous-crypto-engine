"""11/16 FABLE - the early plays by spot, the leans by path, the live bets, by week (live, since 10/25 and all)."""
import json, sys, os, collections
sys.path.insert(0, '.')
import sports, sports_early
from datetime import datetime, timezone

p = json.load(open('data/sports/picks.json'))
e = json.load(open('data/sports/early.json'))
FROM = '2026-10-25'


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def day(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(sports.PT).strftime("%Y-%m-%d")


print("== EARLY by spot (all / since 10/25)")
T = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0, 0, 0.0, 0.0])
for x in e['picks']:
    if x.get('result') not in ('won', 'lost', 'push'):
        continue
    u = sports_early.units(x)
    net = u * (dec(x['odds']) - 1) if x['result'] == 'won' else -u if x['result'] == 'lost' else 0
    d = day(x['start'])
    t = T[x.get('spot') or 'exam']
    t[0] += net > 0; t[1] += net < 0; t[2] += net; t[3] += u
    if d >= FROM:
        t[4] += net > 0; t[5] += net < 0; t[6] += net; t[7] += u
    if d >= FROM:
        cl = x.get('close') or x.get('close_odds')
        print(f"  {d[5:]} {x.get('spot') or 'exam':12s} {x.get('league'):5s} {str(x.get('team'))[:16]:16s} {x['odds']:>5} {u:>4} {net:+.2f} "
              f"own={x.get('own')} mkt={x.get('mkt')} main={x.get('main')} need={x.get('main_need')} close={cl} beat={x.get('beat') or x.get('clv')} {x['result']} {x.get('final') or x.get('score_line') or ''}")
for k, t in sorted(T.items()):
    print(f"{k:14s} all {t[0]}-{t[1]} {t[2]:+.2f}u on {t[3]}u | since 10/25 {t[4]}-{t[5]} {t[6]:+.2f}u on {t[7]}u")
print("pulled:", len(e.get('pulled') or []))
print(sorted(set(k for x in e['picks'] for k in x)))

print("== LEANS")
L = collections.defaultdict(lambda: [0, 0, 0.0, 0, 0, 0.0])
rows = []
for pk in p:
    if not sports.in_record(pk) or pk.get('kind') in sports.PARLAY_KINDS:
        continue
    for l in pk.get('legs') or []:
        if sports.leg_units(pk, l):
            continue
        res = l.get('result') or pk.get('status')
        if res not in ('won', 'lost'):
            continue
        o = l.get('odds') or pk.get('american')
        net = (dec(o) - 1) if res == 'won' else -1
        mk = l.get('market', 'ml')
        fav = (o < 0) if mk == 'ml' else ((l.get('line') or 0) < 0)
        key = (l.get('league'), mk, 'fav' if fav else 'dog')
        for kk in (key, ('ALL',), (l.get('league'),)):
            t = L[kk]
            t[0] += res == 'won'; t[1] += res == 'lost'; t[2] += net
            if pk['date'] >= FROM:
                t[3] += res == 'won'; t[4] += res == 'lost'; t[5] += net
        rows.append((pk['date'], pk.get('kind'), key, l.get('team'), o, l.get('line'), l.get('p'), l.get('raw_own'), l.get('p_market'), res, pk.get('tier'), l.get('reasons')))
for k, t in sorted(L.items(), key=str):
    print(f"{str(k):34s} all {t[0]}-{t[1]} {t[2]:+.2f} | since 10/25 {t[3]}-{t[4]} {t[5]:+.2f}")
json.dump(rows, open(os.path.expanduser('~/.cache/d503_forensics1116/leans.json'), 'w'))

print("== UNIT PLAYS by week")
led = sports.units_ledger(p, e['picks'])
W = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
for pk, u, net, _ in led['rows']:
    if u <= 0:
        continue
    wk = datetime.strptime(pk['date'], '%Y-%m-%d').strftime('%G-W%V')
    t = W[wk]; t[0] += net > 0; t[1] += net < 0; t[2] += net; t[3] += u
for k, t in sorted(W.items()):
    print(k, f"{t[0]}-{t[1]} {t[2]:+.2f}u on {t[3]}u")
D = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
for pk, u, net, _ in led['rows']:
    if u > 0 and pk['date'] >= '2026-11-05':
        t = D[pk['date']]; t[0] += net > 0; t[1] += net < 0; t[2] += net; t[3] += u
for k, t in sorted(D.items()):
    print(k, f"{t[0]}-{t[1]} {t[2]:+.2f}u on {t[3]}u")
