"""10/29 TEN HOCKEY STUDIES on rows.json (2018-19 .. 2026-27, closing moneylines, actual starters). Train 2018-23 (five
seasons), judge held-out 2023-27 (four, the current one tiny). Flat 1u at the close. z = ROI / (sd / sqrt n)."""
import json, math, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(f'{HERE}/rows.json'))
TRAIN = {'2018-19', '2019-20', '2020-21', '2021-22', '2022-23'}
CELLS = []


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def logit(p):
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


# --- the engine's live hockey read: the line + b2b / rest, fit on the TRAIN seasons only (sports_hockey's form)
def fit_read():
    rs = [r for r in rows if r['season'] in TRAIN]
    w = {'b2b': 0.0, 'rest': 0.0}
    for _ in range(300):
        grad = {'b2b': 0.0, 'rest': 0.0}
        for r in rs:
            x = {'b2b': r['b2b_a'] - r['b2b_h'], 'rest': (r['rest_h'] - r['rest_a']) / 7}
            e = sig(logit(r['mkt_h']) + sum(w[k] * x[k] for k in w)) - r['hw']
            for k in w:
                grad[k] += e * x[k]
        for k in w:
            w[k] -= 0.5 * (grad[k] / len(rs) + 0.002 * w[k])
    return w


W = fit_read()
print('live hockey read weights (train only):', {k: round(v, 4) for k, v in W.items()})
for r in rows:
    x = {'b2b': r['b2b_a'] - r['b2b_h'], 'rest': (r['rest_h'] - r['rest_a']) / 7}
    r['own_h'] = sig(logit(r['mkt_h']) + sum(W[k] * x[k] for k in W))


def sides(r):
    for s in ('h', 'a'):
        o = r['oh'] if s == 'h' else r['oa']
        opp = 'a' if s == 'h' else 'h'
        won = r['hw'] if s == 'h' else 1 - r['hw']
        p = r['mkt_h'] if s == 'h' else 1 - r['mkt_h']
        own = r['own_h'] if s == 'h' else 1 - r['own_h']
        d = dict(side=s, home=s == 'h', odds=o, won=won, p=p, own=own, gap_mkt=(own - p) * 100, gap_price=(own - 1 / dec(o)) * 100,
                 season=r['season'], month=r['month'], r=r)
        for k in ('b2b', 'move', 'rest', 'bk', 'n1', 'n1name', 'night1', 'svs', 'gst', 'svo', 'grun', 'l5w', 'l5d', 'gp', 'wp', 'gd', 'stk', 'gk'):
            d[k] = r.get(f'{k}_{s}'); d['o' + k] = r.get(f'{k}_{opp}')
        d['prev_win'] = None if r['prev_win_h'] is None else (r['prev_win_h'] if s == 'h' else 1 - r['prev_win_h'])
        d['prev_margin'] = r['prev_margin']
        d['open'] = r['oho'] if s == 'h' else r['oao']
        yield d


ALL = [b for r in rows for b in sides(r)]


def grade(bets):
    n = len(bets)
    if not n:
        return '0 bets', 0, 0.0
    pnl = [(dec(b['odds']) - 1) if b['won'] else -1.0 for b in bets]
    tot = sum(pnl); roi = tot / n
    sd = (sum((x - roi) ** 2 for x in pnl) / max(1, n - 1)) ** 0.5
    z = roi / (sd / n ** 0.5) if sd else 0
    w = sum(b['won'] for b in bets)
    pts = (w / n - sum(b['p'] for b in bets) / n) * 100
    return f'{w}-{n - w} n={n} ROI {roi:+.1%} ({tot:+.1f}u) pts vs no-vig {pts:+.1f} z {z:+.1f}', n, roi


def split(name, f, quiet=False):
    all_ = [b for b in ALL if f(b)]
    tr = [b for b in all_ if b['season'] in TRAIN]
    te = [b for b in all_ if b['season'] not in TRAIN]
    gtr, ntr, rtr = grade(tr); gte, nte, rte = grade(te)
    by = defaultdict(list)
    for b in te:
        by[b['season']].append(b)
    ups = sum(grade(by[s])[2] > 0 for s in by)
    CELLS.append((name, ntr, rtr, nte, rte, ups, len(by)))
    if not quiet:
        print(f'\n{name}')
        print('  train 2018-23 :', gtr)
        print('  held 2023-27  :', gte)
        for s in sorted(by):
            print(f'    {s}: {grade(by[s])[0]}')
        print(f'  held-out seasons up: {ups} of {len(by)}')
    return tr, te


fav = lambda b: b['odds'] < 0
dog = lambda b: b['odds'] >= 100
band = lambda b, lo, hi: lo <= b['odds'] <= hi
DOG = lambda b: band(b, 100, 350)
LOCK = lambda b: band(b, -150, -127)   # 56%+ favorites (-127 = 55.9%) to the -150 cap

print('=== BASELINES')
split('every dog +100..+350', DOG)
split('every favorite -150..-127 (the Lock band, 56%+)', LOCK)
split('favorites -126..-101', lambda b: band(b, -126, -101))

print('\n\n=== STUDY 1: THE GOALIE QUALITY GAP (season-to-date save %, shrunk, both starters 5+ starts in) - is the better goalie priced?')
def svgap(b):
    return None if b['svs'] is None or b['osvs'] is None else (b['svs'] - b['osvs']) * 1000
split('S1a dog +100..+350, its starter .010+ better on the season', lambda b: DOG(b) and (svgap(b) or 0) >= 10 and svgap(b) is not None)
split('S1b dog, its starter .005..+.010 better', lambda b: DOG(b) and svgap(b) is not None and 5 <= svgap(b) < 10)
split('S1c dog, starters within .005', lambda b: DOG(b) and svgap(b) is not None and -5 < svgap(b) < 5)
split('S1d dog, its starter .010+ WORSE', lambda b: DOG(b) and svgap(b) is not None and svgap(b) <= -10)
split('S1e favorite -101..-150, its starter .010+ better', lambda b: band(b, -150, -101) and svgap(b) is not None and svgap(b) >= 10)
split('S1f favorite -101..-150, its starter .010+ WORSE', lambda b: band(b, -150, -101) and svgap(b) is not None and svgap(b) <= -10)
split('S1g COMBINED: dog on its #1 with the better goalie (.005+) vs a favorite on its BACKUP', lambda b: DOG(b) and b['bk'] is False and b['obk'] is True and svgap(b) is not None and svgap(b) >= 5)
split('S1h COMBINED: dog on its backup AND the worse goalie (.005+) - the fade', lambda b: DOG(b) and b['bk'] is True and svgap(b) is not None and svgap(b) <= -5)

print('\n\n=== STUDY 2: THE FAVORITE ON NIGHT 2 OF A BACK-TO-BACK - who is in net, and is it priced? (tonight: Hurricanes at the Blue Jackets)')
fb2b = [b for b in ALL if fav(b) and b['b2b']]
n1_played = [b for b in fb2b if b['night1'] and b['n1name'] and b['night1'] == b['n1name']]
print(f'favorites on a b2b: {len(fb2b)}; the #1 played night 1: {len(n1_played)}; of those, the backup starts night 2: '
      f'{sum(1 for b in n1_played if b["gk"] != b["n1name"])} ({sum(1 for b in n1_played if b["gk"] != b["n1name"]) / max(1, len(n1_played)):.0%}); '
      f'the #1 goes again: {sum(1 for b in n1_played if b["gk"] == b["n1name"])}')
split('S2a favorite on a b2b, its #1 played night 1, BACKUP in net tonight: bet the FAVORITE', lambda b: fav(b) and b['b2b'] and b['night1'] and b['n1name'] and b['night1'] == b['n1name'] and b['gk'] != b['n1name'])
split('S2b ... bet the DOG +100..+350 (rested dog vs the b2b favorite on its backup)', lambda b: DOG(b) and b['ob2b'] and not b['b2b'] and b['onight1'] and b['on1name'] and b['onight1'] == b['on1name'] and b['ogk'] != b['on1name'])
split('S2c favorite on a b2b, its #1 played night 1 AND goes again: bet the DOG', lambda b: DOG(b) and b['ob2b'] and not b['b2b'] and b['onight1'] and b['on1name'] and b['onight1'] == b['on1name'] and b['ogk'] == b['on1name'])
split('S2d favorite on a b2b (any goalie), rested dog +100..+350: bet the DOG', lambda b: DOG(b) and b['ob2b'] and not b['b2b'])
split('S2e S2b at +100..+150', lambda b: band(b, 100, 150) and b['ob2b'] and not b['b2b'] and b['onight1'] and b['on1name'] and b['onight1'] == b['on1name'] and b['ogk'] != b['on1name'])
split('S2f S2b at +151..+350', lambda b: band(b, 151, 350) and b['ob2b'] and not b['b2b'] and b['onight1'] and b['on1name'] and b['onight1'] == b['on1name'] and b['ogk'] != b['on1name'])
split('S2g S2b, the favorite -150 or shorter (a big favorite on a tired backup)', lambda b: DOG(b) and b['odds'] >= 130 and b['ob2b'] and not b['b2b'] and b['onight1'] and b['on1name'] and b['onight1'] == b['on1name'] and b['ogk'] != b['on1name'])

print('\n\n=== STUDY 3: THE GOOD BACKUP vs THE BAD BACKUP (the backup\'s own season save %, 5+ starts)')
split('S3a dog on its backup, the backup .910+ on the season: bet the dog', lambda b: DOG(b) and b['bk'] is True and b['svs'] is not None and b['svs'] >= 0.910)
split('S3b dog on its backup, the backup under .895: bet the dog', lambda b: DOG(b) and b['bk'] is True and b['svs'] is not None and b['svs'] < 0.895)
split('S3c favorite on a WEAK backup (<.895) -> bet the dog on its #1', lambda b: DOG(b) and b['obk'] is True and b['bk'] is False and b['osvs'] is not None and b['osvs'] < 0.895)
split('S3d favorite on a GOOD backup (.910+) -> bet the dog on its #1', lambda b: DOG(b) and b['obk'] is True and b['bk'] is False and b['osvs'] is not None and b['osvs'] >= 0.910)
split('S3e favorite -101..-150 on a weak backup: bet the favorite', lambda b: band(b, -150, -101) and b['bk'] is True and b['svs'] is not None and b['svs'] < 0.895)

print('\n\n=== STUDY 4: THE DOG\'S LAST-5 GOAL DIFFERENTIAL vs ITS LAST-5 RECORD (underlying form)')
split('S4a dog, last 5: 2 or fewer wins but goal diff 0 or better (unlucky lately)', lambda b: DOG(b) and b['l5w'] is not None and b['l5w'] <= 2 and b['l5d'] >= 0)
split('S4b dog, last 5: 3+ wins but goal diff under 0 (lucky lately) - fade?', lambda b: DOG(b) and b['l5w'] is not None and b['l5w'] >= 3 and b['l5d'] < 0)
split('S4c dog, last-5 goal diff +4 or better', lambda b: DOG(b) and b['l5d'] is not None and b['l5d'] >= 4)
split('S4d dog, last-5 goal diff -6 or worse', lambda b: DOG(b) and b['l5d'] is not None and b['l5d'] <= -6)
split('S4e dog whose SEASON goal diff a game beats the favorite\'s (both 15+ games)', lambda b: DOG(b) and b['gp'] >= 15 and b['ogp'] >= 15 and b['gd'] / b['gp'] > b['ogd'] / b['ogp'])
split('S4f dog whose season goal diff a game is 0.5+ WORSE than the favorite\'s', lambda b: DOG(b) and b['gp'] >= 15 and b['ogp'] >= 15 and b['gd'] / b['gp'] <= b['ogd'] / b['ogp'] - 0.5)

print('\n\n=== STUDY 5: THE DOG WITH THE BETTER RECORD (both 20+ games in)')
split('S5a dog with the better win % (5+ points) than the favorite', lambda b: DOG(b) and b['gp'] >= 20 and b['ogp'] >= 20 and b['wp'] >= b['owp'] + 0.05)
split('S5b dog with the better win % AND the better goal diff a game', lambda b: DOG(b) and b['gp'] >= 20 and b['ogp'] >= 20 and b['wp'] > b['owp'] and b['gd'] / b['gp'] > b['ogd'] / b['ogp'])
split('S5c the ROAD dog with the better record (the home-ice premium)', lambda b: DOG(b) and not b['home'] and b['gp'] >= 20 and b['ogp'] >= 20 and b['wp'] >= b['owp'] + 0.05)
split('S5d a home favorite -101..-150 with the WORSE record (10+ points) than the dog', lambda b: band(b, -150, -101) and b['home'] and b['gp'] >= 20 and b['ogp'] >= 20 and b['wp'] <= b['owp'] - 0.10)

print('\n\n=== STUDY 6: THE BACK-TO-BACK WITH A MOVE (the tired team and where it slept)')
split('S6a dog on a b2b that did NOT move (home both nights / same time zone): bet the dog', lambda b: DOG(b) and b['b2b'] and not b['move'])
split('S6b dog on a b2b that moved (road team after a game in another time zone / home team home from the road)', lambda b: DOG(b) and b['b2b'] and b['move'])
split('S6c rested dog vs a favorite on a b2b that MOVED', lambda b: DOG(b) and not b['b2b'] and b['ob2b'] and b['omove'])
split('S6d rested dog vs a favorite on a b2b that did NOT move', lambda b: DOG(b) and not b['b2b'] and b['ob2b'] and not b['omove'])
split('S6e rested favorite -127..-150 vs a dog on a b2b that moved', lambda b: LOCK(b) and not b['b2b'] and b['ob2b'] and b['omove'])
split('S6f rested favorite -127..-150 vs a dog on a b2b that did not move', lambda b: LOCK(b) and not b['b2b'] and b['ob2b'] and not b['omove'])

print('\n\n=== STUDY 7: THE HOCKEY DOG BY PRICE BAND x THE ENGINE\'S READ GAP (the live read = the line + b2b / rest, fit on train)')
for lo, hi in ((100, 150), (151, 199), (200, 350)):
    split(f'S7 band +{lo}..+{hi}: every dog', lambda b, lo=lo, hi=hi: band(b, lo, hi))
    split(f'S7 band +{lo}..+{hi}: own read OVER the no-vig market (any)', lambda b, lo=lo, hi=hi: band(b, lo, hi) and b['gap_mkt'] > 0.05)
    split(f'S7 band +{lo}..+{hi}: own read over the no-vig market by 2+ points', lambda b, lo=lo, hi=hi: band(b, lo, hi) and b['gap_mkt'] >= 2)
    split(f'S7 band +{lo}..+{hi}: own read over the PRICE (the juice too)', lambda b, lo=lo, hi=hi: band(b, lo, hi) and b['gap_price'] > 0)
    split(f'S7 band +{lo}..+{hi}: own read UNDER the market by 2+', lambda b, lo=lo, hi=hi: band(b, lo, hi) and b['gap_mkt'] <= -2)

print('\n\n=== STUDY 8: THE GOALIE vs THIS OPPONENT (career save % against them in our data, 3+ starts) and the goalie\'s run of starts')
split('S8a dog whose starter is .930+ career vs this opponent', lambda b: DOG(b) and b['svo'] is not None and b['svo'] >= 0.930)
split('S8b dog whose starter is under .890 career vs this opponent', lambda b: DOG(b) and b['svo'] is not None and b['svo'] < 0.890)
split('S8c dog facing a goalie .930+ career vs the dog', lambda b: DOG(b) and b['osvo'] is not None and b['osvo'] >= 0.930)
split('S8d dog whose starter is on his 6th+ straight start', lambda b: DOG(b) and b['grun'] >= 6)
split('S8e dog facing a favorite\'s goalie on his 6th+ straight start', lambda b: DOG(b) and b['ogrun'] >= 6)
split('S8f favorite -101..-150 whose goalie is on his 8th+ straight start', lambda b: band(b, -150, -101) and b['grun'] >= 8)

print('\n\n=== STUDY 9: THE SEASON SERIES (the last meeting this season)')
split('S9a dog that WON the last meeting this season', lambda b: DOG(b) and b['prev_win'] == 1)
split('S9b dog that won the last meeting by 3+', lambda b: DOG(b) and b['prev_win'] == 1 and b['prev_margin'] >= 3)
split('S9c dog that LOST the last meeting by 3+ (revenge)', lambda b: DOG(b) and b['prev_win'] == 0 and b['prev_margin'] >= 3)
split('S9d dog that lost the last meeting by 1', lambda b: DOG(b) and b['prev_win'] == 0 and b['prev_margin'] == 1)
split('S9e favorite -101..-150 that lost the last meeting', lambda b: band(b, -150, -101) and b['prev_win'] == 0)
split('S9f streaks: dog on a 3+ game WIN streak', lambda b: DOG(b) and b['stk'] >= 3)
split('S9g favorite -101..-150 on a 3+ game LOSS streak', lambda b: band(b, -150, -101) and b['stk'] <= -3)

print('\n\n=== STUDY 10: THE HOCKEY LOCK (56%+ favorites, -127..-150) by goalie matchup x rest - a stronger filter?')
split('S10a Lock band, favorite on its #1 (not backup)', lambda b: LOCK(b) and b['bk'] is False)
split('S10b Lock band, favorite on its BACKUP', lambda b: LOCK(b) and b['bk'] is True)
split('S10c Lock band, dog on its backup', lambda b: LOCK(b) and b['obk'] is True)
split('S10d Lock band, favorite on #1, dog on backup', lambda b: LOCK(b) and b['bk'] is False and b['obk'] is True)
split('S10e Lock band, rested vs a dog on a b2b', lambda b: LOCK(b) and not b['b2b'] and b['ob2b'])
split('S10f Lock band, rested vs a b2b dog OR the dog on its backup (either edge)', lambda b: LOCK(b) and b['bk'] is False and ((not b['b2b'] and b['ob2b']) or b['obk'] is True))
split('S10g Lock band, favorite on #1, dog on #1, both rested (no edge at all)', lambda b: LOCK(b) and b['bk'] is False and b['obk'] is False and not b['b2b'] and not b['ob2b'])
split('S10h Lock band, favorite on its #1 with the better season save % (.005+)', lambda b: LOCK(b) and b['bk'] is False and svgap(b) is not None and svgap(b) >= 5)
split('S10i Lock band, favorite ON a b2b', lambda b: LOCK(b) and b['b2b'])
split('S10j Lock band, favorite\'s goalie .010+ WORSE than the dog\'s', lambda b: LOCK(b) and svgap(b) is not None and svgap(b) <= -10)
split('S10k Lock band, HOME favorite on #1 vs a dog on a b2b or its backup', lambda b: LOCK(b) and b['home'] and b['bk'] is False and ((not b['b2b'] and b['ob2b']) or b['obk'] is True))
split('S10l Lock band, ROAD favorite on #1 vs a dog on a b2b or its backup', lambda b: LOCK(b) and not b['home'] and b['bk'] is False and ((not b['b2b'] and b['ob2b']) or b['obk'] is True))

print('\n\n=== MULTIPLE TESTING: cells looked at', len(CELLS), '- cells with train AND held both over +3% and held-out seasons up 3+ of 4:')
for c in CELLS:
    if c[2] > 0.03 and c[4] > 0.03 and c[5] >= 3 and c[1] >= 30 and c[3] >= 30:
        print(f'  {c[0]}: train {c[2]:+.1%} (n {c[1]}) / held {c[4]:+.1%} (n {c[3]}) up {c[5]} of {c[6]}')
print('cells with train AND held both under -5% (fades), 0-1 of 4 up:')
for c in CELLS:
    if c[2] < -0.05 and c[4] < -0.05 and c[5] <= 1 and c[1] >= 30 and c[3] >= 30:
        print(f'  {c[0]}: train {c[2]:+.1%} (n {c[1]}) / held {c[4]:+.1%} (n {c[3]}) up {c[5]} of {c[6]}')
