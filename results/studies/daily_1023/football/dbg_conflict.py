import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, s123_odds_moves as s
for lg in ('ncaaf','nfl'):
    xs=s.rows(lg)
    for x in xs:
        if x['tue'] is None or x['close'] is None: continue
        smv=x['tue']-x['close']; mmv=x['p1']-x['p0']
        if (smv>=0.5 and mmv<=-0.01) or (smv<=-0.5 and mmv>=0.01):
            ch=lib.num(x['c_mlh']); ca=lib.num(x['c_mla'])
            pc=lib.nv(ch,ca) if ch and ca else None
            lastd=lib.first_last(x['ml'])[1][0]
            print(lg,x['start'],x['id'],'tue',x['tue'],'close',x['close'],'p0 %.3f p1 %.3f gf %s'%(x['p0'],x['p1'], '%.3f'%pc if pc else '-'),'last %.2fd'%lastd,'margin',x['margin'], 'spside', 'h' if smv>0 else 'a')
