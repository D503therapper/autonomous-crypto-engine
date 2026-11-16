"""11/16 FABLE - WHY WE LOSE, Q4b: the Monday / Thursday NFL night pick when it is a LEAN (night_pick's "likeliest side
it isn't fighting") on the 11/14 football replay board (today's code, 2018-26, the close): 111-129, 46.2%. By what it
picked - and what the other choices on the same game did."""
import glob, json, os, random
from collections import defaultdict

rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k not in seen:
            seen.add(k)
            rows.append(r)
by_game = defaultdict(list)
for r in rows:
    by_game[r['gid']].append(r)


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def roi(x):
    return sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x) / max(1, len(x))


def cell(n, x):
    x = [r for r in x if r.get('result') in ('won', 'lost')]
    if len(x) < 6:
        print(f"  {n:60s} n {len(x)}")
        return
    tr = [r for r in x if r['date'] < '2023-07-01']
    he = [r for r in x if r['date'] >= '2023-07-01']
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    q = sum(1 / r['dec'] for r in x)
    v = sum((1 / r['dec']) * (1 - 1 / r['dec']) for r in x)
    print(f"  {n:60s} {w:4d}-{len(x) - w:<4d} {w / len(x):5.1%} {roi(x):+7.1%} z {(w - q) / v ** 0.5:+5.2f} | train {roi(tr):+7.1%} on {len(tr):3d} | held {roi(he):+7.1%} on {len(he):3d} | up {sum(roi(v_) > 0 for v_ in by.values())}/{len(by)}")


N = [r for r in rows if r.get('night') and not r.get('kind')]
print(len(N), 'night leans;', sorted({str(r.get('night')) for r in N})[:5])
cell('all night leans', N)
cell('moneyline favorite', [r for r in N if r['market'] == 'ml' and r['odds'] < 0])
cell('   -150..-130', [r for r in N if r['market'] == 'ml' and -150 <= r['odds'] <= -130])
cell('   -129..-101', [r for r in N if r['market'] == 'ml' and -129 <= r['odds'] < 0])
cell('moneyline dog', [r for r in N if r['market'] == 'ml' and r['odds'] >= 100])
cell('spread, laying points', [r for r in N if r['market'] == 'spread' and (r.get('line') or 0) < 0])
cell('   laying 7+', [r for r in N if r['market'] == 'spread' and (r.get('line') or 0) <= -7])
cell('   laying under 7', [r for r in N if r['market'] == 'spread' and -7 < (r.get('line') or 0) < 0])
cell('spread, getting points', [r for r in N if r['market'] == 'spread' and (r.get('line') or 0) > 0])
cell('   getting 7+', [r for r in N if r['market'] == 'spread' and (r.get('line') or 0) >= 7])
cell('   getting under 7', [r for r in N if r['market'] == 'spread' and 0 < (r.get('line') or 0) < 7])
cell('home side', [r for r in N if r.get('home')])
cell('road side', [r for r in N if not r.get('home')])
cell('with a named reason', [r for r in N if r.get('reasons')])
cell('no named reason', [r for r in N if not r.get('reasons')])
print('-- the other choices on the same games')
alt = defaultdict(list)
for r in N:
    for x in by_game[r['gid']]:
        if x['market'] not in ('ml', 'spread') or x.get('result') not in ('won', 'lost'):
            continue
        fav = (x['odds'] < 0) if x['market'] == 'ml' else ((x.get('line') or 0) < 0)
        alt[(x['market'], 'favorite' if fav else 'dog')].append(x)
        if x['market'] == 'spread':
            alt[('spread', 'home' if x.get('home') else 'road')].append(x)
for k, v in sorted(alt.items()):
    cell(f'every {k[0]} {k[1]} on those games', v)
print('-- every NFL Monday / Thursday game on the board (any pick or none): the spread sides')
ng = {r['gid'] for r in rows if r.get('night')}
allsp = [x for g in ng for x in by_game[g] if x['market'] == 'spread']
cell('spread favorite', [x for x in allsp if (x.get('line') or 0) < 0])
cell('spread dog', [x for x in allsp if (x.get('line') or 0) > 0])
cell('spread home', [x for x in allsp if x.get('home')])
cell('spread road', [x for x in allsp if not x.get('home')])
random.seed(5)
pool = [x for g in {r['gid'] for r in N} for x in by_game[g] if x['market'] in ('ml', 'spread') and x.get('result') in ('won', 'lost') and x['odds'] >= -150]
t = roi([r for r in N if r.get('result') in ('won', 'lost')])
n = len([r for r in N if r.get('result') in ('won', 'lost')])
hit = sum(roi(random.sample(pool, n)) <= t for _ in range(2000))
print(f"  placebo: a random {n} sides of those games (-150 or better) did as badly {hit} of 2000 (leans {t:+.1%}, pool {roi(pool):+.1%} on {len(pool)})")
