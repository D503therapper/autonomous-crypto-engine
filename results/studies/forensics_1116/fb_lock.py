"""11/16 FABLE - WHY WE LOSE: the football Lock on the 11/14 football replay board (today's code, 2018-26, the close) -
by size, by how far the own read sits over the price, by price, home / road. The Packers -142 of 11/15 was a 1u (not
thin) NFL Lock: own read 63% against 58.7% needed."""
import glob, json, os, random
from collections import defaultdict

rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
L = [r for r in rows if r.get('kind') == 'lock' and r['result'] in ('won', 'lost')]
print(len(L), 'football Locks;', sorted(L[0].keys()))


def roi(x):
    return sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x) / max(1, len(x))


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def cell(n, x):
    tr = [r for r in x if r['date'] < '2023-07']
    he = [r for r in x if r['date'] >= '2023-07']
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    print(f"  {n:44s} {w}-{len(x) - w} {roi(x):+7.1%} | train {sum(r['result'] == 'won' for r in tr)}-{sum(r['result'] == 'lost' for r in tr)} {roi(tr):+7.1%} "
          f"| held {sum(r['result'] == 'won' for r in he)}-{sum(r['result'] == 'lost' for r in he)} {roi(he):+7.1%} | up {sum(roi(v) > 0 for v in by.values())}/{len(by)}")


for lg in ('nfl', 'ncaaf', None):
    X = [r for r in L if lg is None or r['league'] == lg]
    print('==', lg or 'football')
    cell('all', X)
    for u in sorted({r.get('units') for r in X}, key=str):
        cell(f'units {u}', [r for r in X if r.get('units') == u])
    for lo, hi in ((-9, 0), (0, .03), (.03, .06), (.06, .10), (.10, 9)):
        cell(f'own edge (ROI) {lo}..{hi}', [r for r in X if r.get('edge_own') is not None and lo <= r['edge_own'] < hi])
    for lo, hi in ((0, .56), (.56, .58), (.58, .60), (.60, 1)):
        cell(f'win % {lo}..{hi}', [r for r in X if lo <= r['p'] < hi])
    cell('-150..-130', [r for r in X if r['odds'] <= -130])
    cell('-129..-120', [r for r in X if -129 <= r['odds'] <= -120])
    cell('home', [r for r in X if r['home']])
    cell('road', [r for r in X if not r['home']])
    big = [r for r in X if r.get('units') == 1.0]
    random.seed(7)
    if big:
        t = roi(big)
        hit = sum(roi(random.sample(X, len(big))) <= t for _ in range(2000))
        print(f"  placebo: a random {len(big)} of these Locks did as badly as the 1u ones {hit} of 2000")
