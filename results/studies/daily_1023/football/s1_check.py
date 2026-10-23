"""Study 1 second look: is the conflict edge just 'a late swing in both markets'? Cells:
 (a) spread Tue->close toward A >=0.5 AND ML last look -> close toward A >=1% (any early ML)
 (b) (a) but the early ML (first fair -> last look) moved toward A too (no conflict)
 (c) (a) with the early ML toward B >=1% (the conflict cell)"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, s123_odds_moves as s
for lg in ('nfl','ncaaf'):
    xs=s.rows(lg)
    for nm, cond in (("a late swing both markets", lambda e: True), ("b + early ML same way", lambda e: e >= 0.01),
                     ("c + early ML the other way (conflict)", lambda e: e <= -0.01), ("d + early ML flat", lambda e: abs(e) < 0.01)):
        b=[]
        for x in xs:
            if x['tue'] is None or x['close'] is None or x['pc'] is None: continue
            smv=x['tue']-x['close']; late=x['pc']-x['p1']; early=x['p1']-x['p0']
            for A, sg in (('h',1),('a',-1)):
                if smv*sg>=0.5 and late*sg>=0.01 and cond(early*sg):
                    p=s.bet_sp(x,A)
                    if p is not None: b.append((x['season'],p))
        print(lg, lib.line(nm, lib.summ(b)))
