import json, sys, math
HERE = "results/studies/nhl_ten_1029"
rows = json.load(open(f"{HERE}/rows.json"))
TRAIN = {'2018-19', '2019-20', '2020-21', '2021-22', '2022-23'}


def dec(o): return 1 + (o / 100 if o > 0 else 100 / -o)
def logit(p): return math.log(p / (1 - p))
def sig(z): return 1 / (1 + math.exp(-z))


rs = [r for r in rows if r['season'] in TRAIN]
w = {'b2b': 0.0, 'rest': 0.0}
for _ in range(300):
    g = {'b2b': 0.0, 'rest': 0.0}
    for r in rs:
        x = {'b2b': r['b2b_a'] - r['b2b_h'], 'rest': (r['rest_h'] - r['rest_a']) / 7}
        e = sig(logit(r['mkt_h']) + sum(w[k] * x[k] for k in w)) - r['hw']
        for k in w: g[k] += e * x[k]
    for k in w: w[k] -= 0.5 * (g[k] / len(rs) + 0.002 * w[k])
for r in rows:
    x = {'b2b': r['b2b_a'] - r['b2b_h'], 'rest': (r['rest_h'] - r['rest_a']) / 7}
    r['own_h'] = sig(logit(r['mkt_h']) + sum(w[k] * x[k] for k in w))
bets = []
for r in rows:
    for s in ('h', 'a'):
        o = r['oh'] if s == 'h' else r['oa']
        if not 100 <= o <= 350: continue
        won = r['hw'] if s == 'h' else 1 - r['hw']
        p = r['mkt_h'] if s == 'h' else 1 - r['mkt_h']
        own = r['own_h'] if s == 'h' else 1 - r['own_h']
        b2b = r['b2b_h'] if s == 'h' else r['b2b_a']
        ob2b = r['b2b_a'] if s == 'h' else r['b2b_h']
        stk = r['stk_h'] if s == 'h' else r['stk_a']
        bets.append(dict(o=o, won=won, gap=(own - p) * 100, gapp=(own - 1 / dec(o)) * 100, season=r['season'], b2b=b2b, ob2b=ob2b, stk=stk))


def grade(bs, name):
    tr = [b for b in bs if b['season'] in TRAIN]; ho = [b for b in bs if b['season'] not in TRAIN]
    def g(x):
        if not x: return "n0"
        pnl = sum((dec(b['o']) - 1) if b['won'] else -1 for b in x); wn = sum(b['won'] for b in x)
        seas = {}
        for b in x: seas[b['season']] = seas.get(b['season'], 0) + ((dec(b['o']) - 1) if b['won'] else -1)
        up = sum(1 for v in seas.values() if v > 0)
        return f"{wn}-{len(x) - wn} {pnl / len(x) * 100:+.1f}% ({pnl:+.1f}u, {up} of {len(seas)} up)"
    print(f"{name:58s} train {g(tr):42s} held {g(ho)}")


notunder = [b for b in bets if b['gap'] >= 0 and not b['b2b']]
print("fallback-ish: own read not under the no-vig market, dog not on a b2b (the fighting / tired rules), +100..+350")
grade(notunder, "TODAY: any band, own not under market")
grade([b for b in notunder if b['o'] <= 199], "OPTION B: never past +199, own not under")
grade([b for b in notunder if b['gap'] >= 2], "OPTION A: own 2+ over market, any band to +350")
grade([b for b in notunder if b['gap'] >= 2 and b['o'] <= 199], "OPTION C: own 2+ over AND never past +199")
grade([b for b in notunder if b['gap'] >= 2 and b['o'] <= 150], "own 2+ over, +100..+150 only")
grade([b for b in notunder if b['gap'] >= 2 and 151 <= b['o'] <= 199], "own 2+ over, +151..+199")
grade([b for b in notunder if b['gap'] >= 2 and b['o'] >= 200], "own 2+ over, +200..+350")
grade([b for b in notunder if b['gap'] < 2 and b['o'] >= 200], "own under 2 over, +200..+350 (the Jackets cell)")
grade([b for b in notunder if b['gap'] < 2 and b['o'] <= 199], "own under 2 over, +100..+199")
grade([b for b in notunder if b['gap'] >= 1.5 and b['o'] <= 199], "own 1.5+ over, +100..+199")
grade([b for b in notunder if b['gap'] >= 3 and b['o'] <= 199], "own 3+ over, +100..+199")
grade([b for b in notunder if b['gapp'] >= 0 and b['o'] <= 199], "own over the PRICE, +100..+199")
grade([b for b in notunder if b['gapp'] >= 0], "own over the PRICE, any band")
grade([b for b in notunder if b['ob2b'] and b['o'] <= 199], "rested dog vs b2b fav, +100..+199")
grade([b for b in notunder if b['ob2b'] and b['o'] >= 200], "rested dog vs b2b fav, +200..+350")
a = [b for b in notunder if b['gap'] >= 2]
print("own 2+ over: n", len(a), "of them vs a b2b fav", sum(1 for b in a if b['ob2b']))
print("train weights", w)
