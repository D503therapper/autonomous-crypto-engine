import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, s123_odds_moves as s, statistics
for lg in ('nfl','ncaaf'):
    xs=s.rows(lg); rev=0; n=0; mlc=[]; fav=0; lastd=[]; amA=[]
    for x in xs:
        if x['tue'] is None or x['close'] is None: continue
        smv=x['tue']-x['close']; mmv=x['p1']-x['p0']
        A = 'h' if (smv>=0.5 and mmv<=-0.01) else 'a' if (smv<=-0.5 and mmv>=0.01) else None
        if not A: continue
        n+=1
        if x['pc'] is not None:
            late = x['pc']-x['p1']
            if (late>0) == (A=='h'): rev+=1
            d = lib.dec(lib.num(x['c_mlh']) if A=='h' else lib.num(x['c_mla']))
            p = lib.mlp(x, A, d)
            if p is not None: mlc.append((x['season'],p))
        pA = x['p1'] if A=='h' else 1-x['p1']
        fav += pA>0.5; lastd.append(lib.first_last(x['ml'])[1][0])
    print(lg,'n',n,'gf close ML swung back to A',rev,'A is fav',fav,'median last look days %.2f'%statistics.median(lastd))
    print(lib.line('A ML at the game-file close (any price)', lib.summ(mlc)))
