"""11/16 FABLE - WHY WE LOSE, Q4c: the NBA moneyline favorite LEAN at -150..-130 (the band the college football and
hockey leans already skip). Three reads: (1) the 11/12 deep rows on today's dials (lean_cells_out.txt: 170-157 -10.7%,
train -7.6% / held -16.3%), (2) the 10/30 funnel rows (the board the 11/11 book study judged - an older code's leans),
(3) EVERY NBA favorite in the band at ESPN's close 2016-26 - the pool the lean picks from - season by season."""
import os, sys, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'book_1111'))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'plays_every_day_1104'))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '08' else 0)


def cell(n, x, cut=None):
    if len(x) < 10:
        print(f"  {n:46s} n {len(x)}")
        return None
    roi = lambda y: sum((r['dec'] - 1) if r['won'] else -1 for r in y) / max(1, len(y))
    by = defaultdict(list)
    for r in x:
        by[season(r['date'])].append(r)
    w = sum(r['won'] for r in x)
    q = sum(1 / r['dec'] for r in x)
    v = sum((1 / r['dec']) * (1 - 1 / r['dec']) for r in x)
    s = f"  {n:46s} {w:4d}-{len(x) - w:<4d} {w / len(x):5.1%} {roi(x):+6.1%} z {(w - q) / v ** 0.5:+5.2f}"
    if cut:
        tr, he = [r for r in x if r['date'] < cut], [r for r in x if r['date'] >= cut]
        s += f" | train {roi(tr):+6.1%} on {len(tr):4d} | held {roi(he):+6.1%} on {len(he):4d}"
    s += f" | up {sum(roi(v_) > 0 for v_ in by.values())}/{len(by)}  " + ' '.join(f"{k % 100:02d}:{roi(v_):+.0%}" for k, v_ in sorted(by.items()))
    print(s)
    return roi(x)


# (2) the 10/30 funnel rows
try:
    import sim_volume as sv
    L = [dict(r, won=r['result'] == 'won') for r in sv.rows if (r.get('kind') == 'lean' or r.get('lean')) and r['league'] == 'nba'
         and r.get('market', 'ml') == 'ml' and r.get('result') in ('won', 'lost')]
    print("(2) the 10/30 funnel rows - NBA moneyline leans")
    cell('-150..-130', [r for r in L if -150 <= r['odds'] <= -130], '2025-07-01')
    cell('-129..-101', [r for r in L if -129 <= r['odds'] <= -101], '2025-07-01')
except Exception as e:  # noqa: BLE001
    print('(2) failed:', repr(e)[:200])

# (3) every NBA favorite in the band at the close
import sports_data as sd
import sports_model as sm
g = sd.load_games('nba')
rows = []
for x in sm.finals(g, 'nba'):
    try:
        mh, ma = float(x.get('ml_home') or 0), float(x.get('ml_away') or 0)
        hs, as_ = float(x['home_score']), float(x['away_score'])
    except (TypeError, ValueError):
        continue
    if not mh or not ma or hs == as_ or str(x.get('stype') or '2') != '2':
        continue
    for side, o, won in (('home', mh, hs > as_), ('away', ma, as_ > hs)):
        rows.append({'date': x['start'][:10], 'side': side, 'odds': o, 'dec': dec(o), 'won': won})
print("(3) every NBA favorite at ESPN's close, regular season")
for lo, hi in ((-150, -130), (-129, -101), (-199, -151)):
    X = [r for r in rows if lo <= r['odds'] <= hi]
    cell(f'{lo}..{hi}', X, '2022-08-01')
    cell(f'   home', [r for r in X if r['side'] == 'home'], '2022-08-01')
    cell(f'   road', [r for r in X if r['side'] == 'away'], '2022-08-01')
band = [r for r in rows if -150 <= r['odds'] <= -130]
pool = [r for r in rows if -150 <= r['odds'] <= -101]
roi = lambda y: sum((r['dec'] - 1) if r['won'] else -1 for r in y) / len(y)
random.seed(9)
t = roi(band)
hit = sum(roi(random.sample(pool, len(band))) <= t for _ in range(2000))
print(f"  placebo: a random {len(band)} favorites -150..-101 did as badly as the -150..-130 ones {hit} of 2000 (band {t:+.1%}, pool {roi(pool):+.1%})")
