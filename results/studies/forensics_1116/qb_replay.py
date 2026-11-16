"""11/16 FABLE - WHY WE LOSE, Q1: does "better QB play lately" (the key-player edge, read off the LAST starter as live
does) earn anything against the price? The 11/14 football replay board's rows (today's code, 2018-26, closing prices):
every football moneyline side, and the board's own unit plays / Locks / leans, with the QB reason named vs not."""
import glob, json, os, sys, random
from collections import defaultdict

rows = []
seen = set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
print(len(rows), 'rows')


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def cell(name, rs, flat=True):
    rs = [r for r in rs if r.get('result') in ('won', 'lost')]
    if not rs:
        print(f"  {name:58s} -")
        return
    def roi(x):
        n = sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x)
        return n / len(x) if x else 0
    tr = [r for r in rs if season(r['date']) <= 2022]
    he = [r for r in rs if season(r['date']) >= 2023]
    by = defaultdict(list)
    for r in rs:
        by[season(r['date'])].append(r)
    up = sum(roi(v) > 0 for v in by.values())
    w = sum(r['result'] == 'won' for r in rs)
    print(f"  {name:58s} {w}-{len(rs) - w} {roi(rs):+7.1%} on {len(rs):5d} | train {roi(tr):+6.1%} on {len(tr)} | held {roi(he):+6.1%} on {len(he)} | up {up}/{len(by)}")
    return roi(rs)


qb = lambda r: any('QB play' in x for x in (r.get('reasons') or []))
for lg in ('nfl', 'ncaaf'):
    ml = [r for r in rows if r['league'] == lg and r['market'] == 'ml']
    print(f"== {lg}: every moneyline side -150..+350")
    band = [r for r in ml if -150 <= r['odds'] <= 350]
    cell('all', band)
    cell('QB reason named', [r for r in band if qb(r)])
    cell('no QB reason', [r for r in band if not qb(r)])
    cell('fav, QB reason', [r for r in band if qb(r) and r['odds'] < 0])
    cell('fav, no QB reason', [r for r in band if not qb(r) and r['odds'] < 0])
    cell('dog, QB reason', [r for r in band if qb(r) and r['odds'] > 0])
    cell('dog, no QB reason', [r for r in band if not qb(r) and r['odds'] > 0])
    print(f"== {lg}: the board's unit plays")
    up = [r for r in rows if r['league'] == lg and r.get('kind')]
    cell('unit plays', up)
    cell('unit plays, QB reason', [r for r in up if qb(r)])
    cell('unit plays, no QB reason', [r for r in up if not qb(r)])
    for k in ('lock', 'dog', 'floor', 'play'):
        cell(f'{k}, QB reason', [r for r in up if r['kind'] == k and qb(r)])
        cell(f'{k}, no QB reason', [r for r in up if r['kind'] == k and not qb(r)])
    le = [r for r in rows if r['league'] == lg and r.get('lean') and not r.get('kind')]
    cell('leans, QB reason', [r for r in le if qb(r)])
    cell('leans, no QB reason', [r for r in le if not qb(r)])
    # the QB reason as the FIRST named reason (the card leads with it)
    cell('unit plays, QB reason FIRST', [r for r in up if (r.get('reasons') or [''])[0].find('QB play') >= 0])
print(sorted(rows[0].keys()))
