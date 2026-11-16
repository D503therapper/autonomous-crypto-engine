"""11/16 FABLE - WHY WE LOSE, Q4: THE LEANS on today's code. The board's own leans (viewer_leans) on the two replay
row sets built on today's code - the 11/14 football board (2018-26) and the 11/12 deep rows (every sport, 2023-26) -
by path: sport, market, favorite / dog (the "dog its own read says is underpriced" lean), the fill, the price band."""
import glob, json, os
from collections import defaultdict


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def roi(x):
    return sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x) / max(1, len(x))


def cell(n, x, cut):
    x = [r for r in x if r.get('result') in ('won', 'lost')]
    if len(x) < 10:
        print(f"  {n:52s} n {len(x)}")
        return
    tr = [r for r in x if r['date'] < cut]
    he = [r for r in x if r['date'] >= cut]
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    q = sum(1 / r['dec'] for r in x)
    v = sum((1 / r['dec']) * (1 - 1 / r['dec']) for r in x)
    print(f"  {n:52s} {w:4d}-{len(x) - w:<4d} {w / len(x):5.1%} {roi(x):+7.1%} z {(w - q) / v ** 0.5:+5.2f} | train {roi(tr):+7.1%} on {len(tr):4d} | held {roi(he):+7.1%} on {len(he):4d} | up {sum(roi(v_) > 0 for v_ in by.values())}/{len(by)}")


def run(name, rows, cut):
    L = [r for r in rows if r.get('lean') and not r.get('kind')]
    print(f"== {name}: {len(L)} leans")
    cell('all leans', L, cut)
    for lg in sorted({r['league'] for r in L}):
        X = [r for r in L if r['league'] == lg]
        cell(f'{lg}: all', X, cut)
        cell(f'{lg}: moneyline favorite', [r for r in X if r['market'] == 'ml' and r['odds'] < 0], cut)
        cell(f'{lg}:   -150..-130', [r for r in X if r['market'] == 'ml' and -150 <= r['odds'] <= -130], cut)
        cell(f'{lg}:   -129..-101', [r for r in X if r['market'] == 'ml' and -129 <= r['odds'] < 0], cut)
        cell(f'{lg}: moneyline DOG (its own read says underpriced)', [r for r in X if r['market'] == 'ml' and r['odds'] >= 100], cut)
        cell(f'{lg}: spread', [r for r in X if r['market'] == 'spread'], cut)
        cell(f'{lg}:   spread, laying points', [r for r in X if r['market'] == 'spread' and (r.get('line') or 0) < 0], cut)
        cell(f'{lg}:   spread, getting points', [r for r in X if r['market'] == 'spread' and (r.get('line') or 0) > 0], cut)
        cell(f'{lg}: the fill', [r for r in X if r.get('fill')], cut)
    cell('every moneyline DOG lean', [r for r in L if r['market'] == 'ml' and r['odds'] >= 100], cut)
    cell('every moneyline favorite lean', [r for r in L if r['market'] == 'ml' and r['odds'] < 0], cut)
    cell('every spread lean', [r for r in L if r['market'] == 'spread'], cut)
    cell('the night picks that are leans', [r for r in rows if r.get('night') and not r.get('kind')], cut)


rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k not in seen:
            seen.add(k)
            rows.append(r)
run("FOOTBALL, the 11/14 replay board (today's code, 2018-26)", rows, '2023-07-01')

rows = []
D = os.path.expanduser('~/.cache/d503_deep1112/funnel_new')
keys = set()
for p in 'ABCD':
    for ln in open(os.path.join(D, f'f{p}.jsonl')):
        r = json.loads(ln)
        keys |= set(r)
        if r.get('lean') or r.get('fill') or r.get('night'):
            rows.append(r)
print(sorted(keys))
run("EVERY SPORT, the 11/12 deep rows (today's dials, 2023-26)", rows, '2025-07-01')
