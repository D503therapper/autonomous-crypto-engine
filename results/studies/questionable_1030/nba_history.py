"""10/30 QUESTIONABLE PLAYERS - the per-player history, held out: key men questionable at 1:30 PM ET, their play rate
by what their history (strictly before the game) said. train = 2018-19..2022-23, HOLD = 2023-24..2025-26.
Usage: python nba_history.py nba_listings.csv.gz"""
import csv, gzip, collections, sys
rows = [r for r in csv.DictReader(gzip.open(sys.argv[1], 'rt')) if r['stype'] == '2']
for r in rows:
    for k in ('played', 'key', 'top1', 'reg', 'streak'):
        r[k] = int(r[k])
    r['season'] = int(r['season'])
Q = sorted([r for r in rows if r['morning'] == 'Questionable'], key=lambda r: (r['date'], r['gid']))
hist = collections.defaultdict(lambda: [0, 0]); day = None; buf = []
recent = collections.defaultdict(list)
for r in Q:
    if r['date'] != day:
        for x in buf:
            k = x['pid'] or x['player']; hist[k][0] += 1; hist[k][1] += x['played']; recent[k].append((x['date'], x['played']))
        buf = []; day = r['date']
    k = r['pid'] or r['player']; r['n'], r['p'] = hist[k]
    cut = str(int(r['date'][:4]) - 2) + r['date'][4:]
    rc = [p for d, p in recent[k] if d >= cut]
    r['rn'], r['rp'] = len(rc), sum(rc)
    buf.append(r)
H = [r for r in Q if r['season'] >= 2024 and r['key']]
T = [r for r in Q if r['season'] < 2024 and r['key']]


def show(lab, f):
    for nm, S in (("train", T), ("HOLD", H)):
        v = [r for r in S if f(r)]
        if v:
            print(f"{nm} {lab:44s} {sum(r['played'] for r in v) / len(v) * 100:5.1f}% of {len(v):4d}",
                  {y: f"{sum(r['played'] for r in v if r['season'] == y)}/{sum(1 for r in v if r['season'] == y)}" for y in sorted({r['season'] for r in v})})


for n in (5, 10, 20):
    for t in (.75, .8, .85, .9):
        show(f"raw prior n>={n} rate>={t}", lambda r: r['n'] >= n and r['p'] / r['n'] >= t)
for n in (5, 10):
    for t in (.8, .85, .9):
        show(f"last-2-yr n>={n} rate>={t}", lambda r: r['rn'] >= n and r['rp'] / r['rn'] >= t)
show("streak>=3 key", lambda r: r['streak'] >= 3)
show("raw prior <=.4 n>=10", lambda r: r['n'] >= 10 and r['p'] / r['n'] <= .4)
show("no prior", lambda r: r['n'] == 0)
