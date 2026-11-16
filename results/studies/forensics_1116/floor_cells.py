"""11/16 FABLE - WHY WE LOSE, Q2: THE FLOOR. The two replay boards the 11/14 sizing study built (R1 = the 10/30 funnel
rows, R2 = the 11/12 deep rows on today's code, both 2023-26 at the close): every floor / fallback floor / NBA floor
play by its dog score, by sport, and the plays that were the day's ONLY unit play. The 11/16 Monday board's fallback
(with the Chargers' false QB reason gone) is the Heat +130 at a dog score of -6.43."""
import os, sys, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'sizing_1114'))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
import lib as L  # noqa: E402

B = L.boards()
for name in ('R1', 'R2'):
    bd, by = B[name]
    print(f"== {name}")
    fl, only = [], []
    for d, ps in bd.items():
        n_unit = len(ps)
        for r, u, k in ps:
            if k in ('floor', 'floorfb', 'nbafloor'):
                fl.append((d, r, u, k))
                if n_unit == 1:
                    only.append((d, r, u, k))
    kinds = sorted({k for _, _, _, k in fl})
    print('  kinds:', {k: sum(1 for x in fl if x[3] == k) for k in kinds})

    def cell(nm, xs):
        if len(xs) < 5:
            print(f"  {nm:58s} n {len(xs)}")
            return
        L.line(nm, [(d, r, u) for d, r, u, _ in xs])

    for k in kinds:
        cell(f'{k}: all', [x for x in fl if x[3] == k])
    sc = lambda x: x[1].get('dog_score') if x[1].get('dog_score') is not None else -99
    for lo, hi in ((-99, -5), (-5, -3), (-3, 0), (0, 2), (2, 4), (4, 99)):
        cell(f'floor + fallback, dog score {lo}..{hi}', [x for x in fl if x[3] in ('floor', 'floorfb') and lo <= sc(x) < hi])
    for lg in ('nhl', 'nfl', 'mlb', 'nba', 'ncaaf'):
        cell(f'floor + fallback, {lg}', [x for x in fl if x[3] in ('floor', 'floorfb') and x[1]['league'] == lg])
        cell(f'   {lg}, dog score under 0', [x for x in fl if x[3] in ('floor', 'floorfb') and x[1]['league'] == lg and sc(x) < 0])
        cell(f'   {lg}, dog score under -3', [x for x in fl if x[3] in ('floor', 'floorfb') and x[1]['league'] == lg and sc(x) < -3])
    cell("the day's ONLY unit play: a floor / fallback play", [x for x in only if x[3] in ('floor', 'floorfb')])
    for lo, hi in ((-99, -5), (-5, -3), (-3, 0), (0, 99)):
        cell(f"   ...its dog score {lo}..{hi}", [x for x in only if x[3] in ('floor', 'floorfb') and lo <= sc(x) < hi])
    cell("   ...a FALLBACK (a dog the floor skips)", [x for x in only if x[3] == 'floorfb'])
    cell("   ...a fallback, dog score under 0", [x for x in only if x[3] == 'floorfb' and sc(x) < 0])
    cell("   ...a fallback NBA dog", [x for x in only if x[3] == 'floorfb' and x[1]['league'] == 'nba'])
    cell("   ...a fallback NBA dog, dog score under 0", [x for x in only if x[3] == 'floorfb' and x[1]['league'] == 'nba' and sc(x) < 0])
    cell("every fallback NBA dog", [x for x in fl if x[3] == 'floorfb' and x[1]['league'] == 'nba'])
    cell("every fallback, dog score under -3", [x for x in fl if x[3] == 'floorfb' and sc(x) < -3])
    cell("every floor / fallback, dog score under -3", [x for x in fl if x[3] in ('floor', 'floorfb') and sc(x) < -3])
    under = [x for x in fl if x[3] in ('floor', 'floorfb') and sc(x) < -3]
    pool = [x for x in fl if x[3] in ('floor', 'floorfb')]
    if under:
        fr = lambda xs: sum(L.flat(r) for _, r, _, _ in xs) / len(xs)
        random.seed(11)
        t = fr(under)
        hit = sum(fr(random.sample(pool, len(under))) <= t for _ in range(2000))
        print(f"  placebo: a random {len(under)} floor plays did as badly as the under -3 ones {hit} of 2000 (cell {t:+.1%}, pool {fr(pool):+.1%})")
