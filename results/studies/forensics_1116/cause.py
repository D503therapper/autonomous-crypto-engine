"""11/16 FABLE - WHY WE LOSE: every graded unit play and early play 10/25-11/15, its path, its size, the read vs the
price, the close, the result - and the CAUSE of every loss (read by hand off the card, the box score and the rules):
  A  a false / stale input (the pick's named reason or its card stood on a man who played / a man who didn't)
  B  a rule or kind the replay says loses (and the date it was cut)
  C  sized past its edge (the units over what the kind's own replay size is)
  D  an honest loss - a fair bet at a fair price
  O  the owner's own post
Wins are netted into each KIND's line (a cut kind's wins count against its losses).
python results/studies/forensics_1116/cause.py -> the table + the tallies (also ~/.cache/d503_forensics1116/cause.json)."""
import json, os, sys, collections
sys.path.insert(0, '.')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sports, sports_early
from datetime import datetime, timezone

FROM = '2026-10-25'
p = json.load(open('data/sports/picks.json'))
e = json.load(open('data/sports/early.json'))
clv = {(c['date'], c['team'], c['kind'], c['market']): c for c in json.load(open('data/sports/clv_record.json'))['picks']}
led = sports.units_ledger(p, e['picks'])
early_by = {}
for x in e['picks']:
    if x.get('result') in ('won', 'lost', 'push'):
        d = datetime.strptime(x['start'][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(sports.PT).strftime("%Y-%m-%d")
        early_by[(d, x['team'])] = x

# (date, team) -> [(cause, units, note)] for LOSSES; anything not listed = D (honest) at its full size
CAUSE = {
    ('2026-10-28', 'Bucks'): [('B', 0.5, 'an NBA half-unit dog past +199 (capped 11/12)')],
    ('2026-10-28', 'Flames'): [('A', 0.5, "its one named reason 'opponent missing key players' was Ekholm - he played")],
    ('2026-10-28', 'New Mexico St'): [('O', 1.0, "the owner's own post")],
    ('2026-10-29', 'Blue Jackets'): [('B', 0.5, 'the hockey fallback Dog with its own read 0.45 over the market (2+ needed from 10/29)')],
    ('2026-10-30', 'Clippers'): [('B', 0.5, 'the runner-up dog in the NBA (hockey / NFL only from 11/13) at +215 (NBA half-unit dogs to +199 from 11/12)')],
    ('2026-10-30', 'UCF'): [('B', 1.0, 'the 🔍 college football play (a home dog; paused 11/13)')],
    ('2026-10-31', 'Kansas St'): [('B', 1.0, 'the 🔍 college football play (paused 11/13); the QB it assumed did not start')],
    ('2026-10-31', 'Arizona'): [('B', 0.5, 'the blowout early spot (paused 11/12)')],
    ('2026-10-31', 'Northwestern'): [('B', 0.5, 'the blowout early spot (paused 11/12)')],
    ('2026-10-31', 'Bucks'): [('C', 0.5, 'the NBA opening-line play at 1u (½u from 11/3)'), ('D', 0.5, '')],
    ('2026-11-02', 'Heat'): [('A', 0.5, "its one named reason 'opponent missing key players' was Ziaire Williams - he played 15 minutes")],
    ('2026-11-02', 'Suns'): [('B', 0.5, 'the runner-up dog in the NBA (hockey / NFL only from 11/13)')],
    ('2026-11-04', 'E Michigan'): [('B', 0.5, 'the runner-up dog in college football (hockey / NFL only from 11/13)')],
    ('2026-11-05', 'Stars'): [('B', 1.0, 'the forced ⭐ on a day with no unit play (off 11/12)')],
    ('2026-11-06', 'South Florida'): [('B', 0.5, 'the blowout early spot (paused 11/12)')],
    ('2026-11-07', 'UConn'): [('B', 1.0, 'the 🔍 college football play (a home dog; paused 11/13)')],
    ('2026-11-07', 'Tulane'): [('B', 1.0, 'the 🔍 college football play (a home dog, raw gap 39; paused 11/13)')],
    ('2026-11-07', 'Kansas St'): [('B', 1.0, "the 🔍 college football play (a home dog; paused 11/13) - and A: its regular QB Avery Johnson (6 starts) was on the out list, read as a backup (fixed 11/16)")],
    ('2026-11-07', 'Miami'): [('B', 1.0, 'the 🔍 college football play (paused 11/13)')],
    ('2026-11-07', 'Ole Miss'): [('B', 1.0, 'the 🔍 college football play (a home dog; paused 11/13)')],
    ('2026-11-07', 'NC State'): [('B', 0.5, 'the runner-up dog in college football (hockey / NFL only from 11/13)')],
    ('2026-11-07', 'Boston College'): [('A', 1.0, "a Dog chosen on 'opponent drama: coach fired' off a headline that doesn't say it (today's checker holds it - 11/11); also a +190 Dog the ⭐ raised from ½u to 1u")],
    ('2026-10-29', 'Panthers'): [('A', 0.5, "a floor play chosen on 'opponent drama: legal trouble' off a headline that doesn't say it (today's checker holds it - 11/11)")],
    ('2026-11-01', 'Vikings'): [('A', 0.5, "a floor play chosen on 'the stronger team' at a 40% read (today's checker holds it - 11/4)")],
    ('2026-11-11', 'Ducks'): [('C', 0.5, 'a ½u value play the ⭐ raised to 1u'), ('D', 0.5, '')],
    ('2026-11-12', 'Red Wings'): [('A', 0.5, "its one named reason 'opponent missing key players' was Vilmanis - he played")],
    ('2026-11-14', 'Georgia St'): [('C', 1.0, 'the exam-scan dog sized 1.5u on Kelly of the raw read (½u flat from 11/16)'), ('D', 0.5, '')],
    ('2026-11-15', 'Packers'): [('A', 1.0, "Kyler Murray, the Vikings' regular QB (5 starts), was on the out list and read as a BACKUP, so 'starting QB out -> go by the market' never fired: "
                                         "re-built with him read as the starter the Packers are 55.9% - no Lock, no units (as it ran 59.1%, the Lock, the ⭐ 1u). The card also named Carson Wentz; Kirk Cousins started")],
}
EARLY_KEYS = {('2026-10-31', 'Arizona'), ('2026-10-31', 'Northwestern'), ('2026-10-31', 'Bucks'), ('2026-11-06', 'South Florida'),
              ('2026-11-14', 'Georgia St')}      # the CAUSE rows that are EARLY plays (every other row is a board play)
EARLY_B = {'blowout': 'the blowout early spot (paused 11/12)',
           'hammered': 'a hammered spot posted 11/2-11/3 before the fresh-number / one-voice rules (11/12)'}

rows = []
for pk, u, net, _ in led['rows']:
    if u <= 0 or pk['date'] < FROM:
        continue
    l = pk['legs'][0]
    k = pk.get('kind')
    if k == 'early':
        x = early_by.get((pk['date'], l['team'])) or {}
        path = 'early: ' + (x.get('spot') or 'exam scan')
        own, mkt = x.get('own'), x.get('mkt')
        cl = x.get('close')
        res = x.get('result')
        need = 1 / sports._dec(l['odds'])
        read = x.get('main') or own
    else:
        fl = pk.get('floor')
        path = ('NBA floor' if isinstance(fl, dict) and fl.get('nba') else 'floor' if fl else '🔍 gap (college football)' if pk.get('gap') is not None and l.get('league') == 'ncaaf'
                else '🔍 gap (college hoops)' if pk.get('gap') is not None else 'runner-up dog' if pk.get('dog_play') and k == 'play' else 'NBA favorite play' if pk.get('nba_fav')
                else 'college hoops slot' if pk.get('ncaab_play') else 'forced ⭐' if pk.get('forced') else 'owner post' if pk.get('owner_post') and k == 'play'
                else {'lock': 'Lock', 'dog': 'Dog of the Day', 'play': 'value play', 'solo': 'one-game pick', 'night': 'night pick'}.get(k, k))
        c = clv.get((pk['date'], l.get('team'), k, l.get('market')))
        cl = c and c['close']
        res = l.get('result') or pk.get('status')
        need = 1 / (l.get('dec') or sports._dec(l['odds']))
        read = sports.read_of(l)
    cs = CAUSE.get((pk['date'], l['team']))
    if (k == 'early') != ((pk['date'], l['team']) in EARLY_KEYS):
        cs = None                                            # (the same team's other play that day has its own cause)
    if net < 0:
        if cs is None and path.startswith('early: ') and path[7:] in EARLY_B:
            cs = [('B', u, EARLY_B[path[7:]])]
        cs = cs or [('D', u, '')]
        # the listed parts never add to more than the stake; what's left is honest
        left = u - sum(x[1] for x in cs)
        if left > 1e-9:
            cs = cs + [('D', left, '')]
    else:
        cs = []
    rows.append(dict(date=pk['date'], path=path, best=bool(pk.get('best')), lg=l.get('league') or pk.get('league'), team=l['team'], odds=l['odds'], u=u, net=round(net, 2),
                     read=read, need=need, close=cl, res=res, cause=cs, score=l.get('score')))
json.dump(rows, open(os.path.expanduser('~/.cache/d503_forensics1116/cause.json'), 'w'))
print("date  path                        ⭐ lg    team             price    u    net  read-need close  result  cause")
for r in rows:
    rn = f"{100 * (r['read'] - r['need']):+5.1f}" if r['read'] is not None else '   - '
    cz = '; '.join(f"{c} {uu:g}u {n}".strip() for c, uu, n in r['cause'])
    print(f"{r['date'][5:]} {r['path'][:27]:27s} {'⭐' if r['best'] else '  '} {r['lg'] or '':5s} {r['team'][:16]:16s} {r['odds']:>5} {r['u']:>4g} {r['net']:+6.2f} {rn}  {str(r['close']):>6} {r['res']:5s} {cz}")

print("\n== BY KIND (W-L, units; ⭐ counted inside its kind; 'expected' = the wins its prices say, juice in; z = how far"
      " off luck - past -2 is worse than luck explains)")
K = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0.0])
SIZE = lambda u: '½u' if u <= 0.5 else '1u' if u <= 1.0 else '1.5u-2u'
for r in rows:
    q = 1 / sports._dec(r['odds'])
    for key in (r['path'], 'ALL', 'ALL board' if not r['path'].startswith('early') else 'ALL early', 'size ' + SIZE(r['u']),
                'sport ' + str(r['lg']), 'dogs (plus money)' if r['odds'] >= 100 else 'favorites') + (('the ⭐',) if r['best'] else ()):
        t = K[key]
        t[0] += r['net'] > 0
        t[1] += r['net'] < 0
        t[2] += r['net']
        t[3] += r['u']
        t[4] += q
        t[5] += q * (1 - q)
for k, t in sorted(K.items(), key=lambda x: x[1][2]):
    z = (t[0] - t[4]) / (t[5] ** 0.5) if t[5] else 0.0
    print(f"  {k:30s} {t[0]:2d}-{t[1]:<2d} {t[2]:+6.2f}u on {t[3]:5.1f}u ({t[2] / t[3]:+5.0%}) | expected {t[4]:4.1f} wins, z {z:+.2f}")

print("\n== UNITS LOST BY CAUSE (losses only)")
C = collections.defaultdict(float)
N = collections.Counter()
for r in rows:
    for c, uu, n in r['cause']:
        C[c] += uu
        N[c] += 1 if uu else 0
tl = sum(C.values())
names = {'A': 'a false / stale input', 'B': 'a rule the replay says loses (all cut by 11/13)', 'C': 'sized past its edge', 'D': 'an honest loss', 'O': "the owner's own post"}
for c in 'ABCDO':
    print(f"  {c} {names[c]:48s} {C[c]:5.1f}u ({C[c] / tl:.0%}) in {N[c]} losses")
print(f"  total lost {tl:.1f}u; won back {sum(r['net'] for r in rows if r['net'] > 0):.2f}u; net {sum(r['net'] for r in rows):+.2f}u")

print("\n== THE SAME STRETCH, SPLIT BY WHAT TODAY'S ENGINE WOULD STILL POST (wins and losses alike)")
CUT = ('🔍 gap (college football)', 'forced ⭐', 'early: blowout', 'owner post')
HELD_WINS = {('2026-11-10', 'Predators')}     # a WIN today's checker would hold too (its one reason: a headline about another team)


def kind_cut(r):
    return (r['path'] in CUT or any(c == 'B' for c, _, _ in r['cause'])
            or (r['path'] == 'runner-up dog' and r['lg'] not in ('nhl', 'nfl')))


def bad_input(r):
    return any(c == 'A' for c, _, _ in r['cause']) or (r['date'], r['team']) in HELD_WINS


for name, x in (("a kind since cut / paused / capped (+ the owner's post)", [r for r in rows if kind_cut(r)]),
                ("a false input (today's checker / the 11/16 fixes hold it)", [r for r in rows if bad_input(r) and not kind_cut(r)]),
                ("EVERYTHING ELSE - what still posts today", [r for r in rows if not kind_cut(r) and not bad_input(r)])):
    w, l_ = sum(r['net'] > 0 for r in x), sum(r['net'] < 0 for r in x)
    print(f"  {name:58s} {w}-{l_} {sum(r['net'] for r in x):+.2f}u on {sum(r['u'] for r in x):.1f}u")
print("  (the cut kinds' wins are counted against them: Fresno St +190 🔍, Iowa +105 blowout. Hindsight: the kinds were cut")
print("   partly ON these results - this says where the money went, not what the next month will pay.)")

print("\n== BEAT THE CLOSE (board unit plays with a close on file)")
b = [r for r in rows if r['close'] is not None and not r['path'].startswith('early') and isinstance(r['close'], (int, float))]
def imp(o):
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)
beat = sum(imp(r['close']) > imp(r['odds']) + 1e-9 for r in b)
same = sum(abs(imp(r['close']) - imp(r['odds'])) <= 1e-9 for r in b)
print(f"  {len(b)} plays: beat it {beat}, matched it {same}, worse {len(b) - beat - same}")
for nm, sel in (('beat the close', lambda r: imp(r['close']) > imp(r['odds']) + 1e-9), ('matched', lambda r: abs(imp(r['close']) - imp(r['odds'])) <= 1e-9),
                ('worse than the close', lambda r: imp(r['close']) < imp(r['odds']) - 1e-9)):
    x = [r for r in b if sel(r)]
    print(f"    {nm:22s} {sum(r['net'] > 0 for r in x)}-{sum(r['net'] < 0 for r in x)} {sum(r['net'] for r in x):+.2f}u on {sum(r['u'] for r in x):.1f}u")
