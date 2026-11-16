"""11/16 - THE OWNER'S CALL (option (a) of the 11/16 forensics): in football every Lock-grade favorite is the Lock - a
thin edge at ½u instead of being turned away. The re-check on the 11/14 football replay board (today's code, 2018-26,
the close; the funnel rows are make_board's Lock BEFORE post_board's no-thin-Lock rule): is the forensics number what
the rows say, which rows does today's own thin_lock() turn away, and what does the Lock spot post BEFORE and AFTER?

BEFORE (the live rule through 11/15 + the 11/16 NFL size): a thin Lock is dropped; it rides as a ½u VALUE PLAY only
when the value-play bar clears (good, real value, the own read 1+ point over the price); a not-thin Lock posts - the
NFL ½u (LOCK_NFL_HALF_FROM), college football 1u.
AFTER (games from 11/16): every one of them is the Lock - thin ½u, the NFL ½u, a not-thin college football Lock 1u."""
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


def pnl(r, u=1.0):
    return u * ((r['dec'] - 1) if r['result'] == 'won' else -1)


def cell(n, x, units=None):
    if not x:
        print(f"  {n:66s} n 0")
        return
    units = units or (lambda r: 1.0)
    tr = [r for r in x if r['date'] < '2023-07']
    he = [r for r in x if r['date'] >= '2023-07']
    w = sum(r['result'] == 'won' for r in x)
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    roi = lambda y: sum(pnl(r) for r in y) / max(1, len(y))   # noqa: E731
    won = sum(pnl(r, units(r)) for r in x)
    risk = sum(units(r) for r in x)
    print(f"  {n:66s} {w}-{len(x) - w} flat {roi(x):+7.1%} | train {roi(tr):+7.1%} on {len(tr)} | held {roi(he):+7.1%} on {len(he)} "
          f"| up {sum(roi(v) > 0 for v in by.values())}/{len(by)} | {won:+.1f}u on {risk:.1f}u")


def leg(r):
    return {**r, 'start': r.get('start') or (r['date'] + 'T20:00Z'), 'game_id': r['gid']}


def thin(r):
    try:
        return sports.thin_lock({'legs': [leg(r)]})
    except Exception:  # noqa: BLE001
        return None


def margin(r):
    try:
        return sports.own_margin(leg(r))
    except Exception:  # noqa: BLE001
        return None


def bar(r):                                                  # the value-play bar a dropped thin Lock has to clear live
    return bool(r.get('good') and r.get('real_value') and r.get('own_beats') and (margin(r) or -9) >= sports.VALUE_EDGE_MIN and r['odds'] < 100)


print(len(L), 'football Locks on the replay board;', 'odds', min(r['odds'] for r in L), '..', max(r['odds'] for r in L),
      '| plus money:', sum(r['odds'] >= 100 for r in L), '| at -119..-101:', sum(-119 <= r['odds'] <= -101 for r in L))
print('the rows by the size the replay gave them x what today\'s thin_lock() says of the row:')
tab = defaultdict(int)
for r in L:
    tab[(r['league'], r.get('units'), thin(r), bool(r.get('backup_lock') or r.get('near_price')))] += 1
for k in sorted(tab, key=str):
    print('   league %s  units %s  thin_lock %s  backup %s : %d' % (*k, tab[k]))

for lg in ('nfl', 'ncaaf', None):
    X = [r for r in L if lg is None or r['league'] == lg]
    half = [r for r in X if r.get('units') == 0.5]
    full = [r for r in X if r.get('units') != 0.5]
    print('==', lg or 'football')
    cell('the forensics cell: the ½u (thin / backup) Lock-grade favorites', half)
    cell('   ...today\'s thin_lock() True (the rule turned them away)', [r for r in half if thin(r)])
    cell('   ...today\'s thin_lock() not True', [r for r in half if not thin(r)])
    cell('the not-thin Locks', full)
    cell('   ...today\'s thin_lock() True', [r for r in full if thin(r)])
    nfl_u = lambda r: 0.5 if (r['league'] == 'nfl' or r.get('units') == 0.5) else 1.0   # noqa: E731
    before = full + [r for r in half if not thin(r)] + [r for r in half if thin(r) and bar(r)]
    cell('BEFORE - what posts (not-thin Locks + thin ones clearing the play bar)', before, nfl_u)
    cell('   the thin ones the board never posted (off the board)', [r for r in half if thin(r) and not bar(r)], nfl_u)
    cell('AFTER  - every Lock-grade favorite is the Lock (thin ½u, NFL ½u, CFB 1u)', X, nfl_u)
    cell('   AFTER, plus money / -119..-101 left out (lock_no_dog, S6_LOCK_SKIP)',
         [r for r in X if r['odds'] < 100 and not -119 <= r['odds'] <= -101], nfl_u)
