"""11/16 FABLE - WHY WE LOSE: what becomes of the football replay board's THIN Locks on the live board? The funnel
rows are make_board's (the Lock before post_board's no-thin-Lock rule); live a thin favorite is no Lock - it rides as
a ½u value play only when the play bar clears (good, real value, the own read over the price by 1+ point of win
chance - sports.VALUE_EDGE_MIN from 11/12). Which of the replay's ½u Locks clear it, and how did each group do?"""
import glob, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports  # noqa: E402

rows, seen = [], set()
for f in sorted(glob.glob(os.path.expanduser('~/.cache/d503_fb1114/rows/f*.jsonl'))):
    for line in open(f):
        r = json.loads(line)
        k = (r['gid'], r['side'], r['market'])
        if k not in seen:
            seen.add(k)
            rows.append(r)
L = [r for r in rows if r.get('kind') == 'lock' and r['result'] in ('won', 'lost')]


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


def roi(x):
    return sum((r['dec'] - 1) if r['result'] == 'won' else -1 for r in x) / max(1, len(x))


def cell(n, x):
    if not x:
        print(f"  {n:64s} n 0")
        return
    tr = [r for r in x if r['date'] < '2023-07']
    he = [r for r in x if r['date'] >= '2023-07']
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    print(f"  {n:64s} {w}-{len(x) - w} {roi(x):+7.1%} | train {roi(tr):+7.1%} on {len(tr)} | held {roi(he):+7.1%} on {len(he)} | up {sum(roi(v) > 0 for v in by.values())}/{len(by)}")


def margin(r):
    c = {**r, 'start': r.get('start') or (r['date'] + 'T20:00Z')}
    try:
        return sports.own_margin(c)
    except Exception:  # noqa: BLE001
        return None


for lg in ('nfl', 'ncaaf', None):
    X = [r for r in L if lg is None or r['league'] == lg]
    half = [r for r in X if r.get('units') == 0.5]
    full = [r for r in X if r.get('units') == 1.0]
    print('==', lg or 'football', '- the board\'s Locks:', len(X))
    cell('the 1u Locks (live: THE LOCK)', full)
    cell('the ½u Locks (live: never the Lock - thin / backup)', half)
    bar = [r for r in half if r.get('good') and r.get('real_value') and r.get('own_beats') and (margin(r) or -9) >= sports.VALUE_EDGE_MIN and r['odds'] < 100]
    rest = [r for r in half if r not in bar]
    cell('   ...that clear the value-play bar (ride at ½u live)', bar)
    cell('   ...that do NOT (live: off the board, a lean at most)', rest)
    cell('      of those: the own read under the price', [r for r in rest if (r.get('edge_own') or 0) <= 0])
    cell('      of those: the own read 0-1 point over', [r for r in rest if (r.get('edge_own') or 0) > 0])
print('VALUE_EDGE_MIN', sports.VALUE_EDGE_MIN)
