"""11/16 FABLE - WHY WE LOSE: the floor's "a named reason" gate, reason by reason. The replay boards' unit plays
(the 11/14 football board on today's code 2018-26; the 11/12 deep rows on today's code, every sport 2023-26, through
the 11/14 sizing study's board builder) split by the ONE named reason a play stood on (a play with a single reason)
and by any reason it carried. A reason that is the card's only leg to stand on, and loses, is no reason."""
import glob, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def roi(x):
    return sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x) / max(1, len(x))


def cell(n, x, cut):
    x = [r for r in x if r.get('result') in ('won', 'lost')]
    if len(x) < 8:
        return
    tr = [r for r in x if r['date'] < cut]
    he = [r for r in x if r['date'] >= cut]
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    print(f"  {n[:60]:60s} {w:4d}-{len(x) - w:<4d} {roi(x):+7.1%} | train {roi(tr):+7.1%} on {len(tr):4d} | held {roi(he):+7.1%} on {len(he):4d} | up {sum(roi(v) > 0 for v in by.values())}/{len(by)}")


def norm(r):
    r = str(r)
    for k in ('opponent missing key players:', 'opponent the more banged-up', 'opponent drama', 'the NBA dog score', 'the hockey dog score', 'trend:'):
        if r.startswith(k):
            return k
    return r if len(r) < 45 else r[:42] + '...'


def run(name, plays, cut):
    print(f"== {name}: {len(plays)} unit plays")
    cell('all unit plays', plays, cut)
    for kind in sorted({r['kind'] for r in plays}):
        P = [r for r in plays if r['kind'] == kind]
        if len(P) < 30:
            continue
        print(f" -- {kind}")
        cell('all', P, cut)
        cell('no reason on file', [r for r in P if not r.get('reasons')], cut)
        one = defaultdict(list)
        anyr = defaultdict(list)
        for r in P:
            rs = [norm(x) for x in (r.get('reasons') or [])]
            if len(rs) == 1:
                one[rs[0]].append(r)
            for x in set(rs):
                anyr[x].append(r)
        for k, v in sorted(one.items(), key=lambda kv: -len(kv[1])):
            cell('ONLY reason: ' + k, v, cut)
        for k, v in sorted(anyr.items(), key=lambda kv: -len(kv[1])):
            cell('carries: ' + k, v, cut)


# 1) the football board
rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k not in seen:
            seen.add(k)
            rows.append(r)
run('FOOTBALL replay board 2018-26 (today\'s code)', [r for r in rows if r.get('kind')], '2023-07-01')

# 2) every sport, the R2 board
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'sizing_1114'))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
try:
    import lib as L
    bd, by = L.boards()['R2']
    plays = []
    for d, ps in bd.items():
        for r, u, k in ps:
            plays.append({**r, 'kind': k, 'date': d})
    run('EVERY SPORT, the R2 board 2023-26 (today\'s code)', plays, '2025-07-01')
except Exception as e:  # noqa: BLE001
    print('R2 board failed:', repr(e)[:200])
