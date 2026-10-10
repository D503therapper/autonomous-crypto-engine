"""DEX POST-MORTEM (owner 10-10: "we are doing pretty bad"): every live DEX trade of seasons 1-4, the live result,
alternative exits replayed on the scanner log, and the result by entry features.  python dex_postmortem_study.py"""
import csv,glob,gzip,json,re,statistics,math
from datetime import datetime,timezone
T=lambda s: datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()
# price paths by token address from scanner log
path={}
for p in sorted(glob.glob('data/dex/scan/*.csv.gz')):
    for r in csv.DictReader(gzip.open(p,'rt')):
        try: px=float(r['price']); liq=float(r['liq'])
        except: continue
        path.setdefault(r['addr'].lower(),[]).append((T(r['time']),px,liq))
for k in path: path[k].sort()
# all live trades
seasons=[('S1','data/dex/archive/season1'),('S2','data/dex/archive/2026-09-29'),('S3','data/dex/archive/2026-10-06'),('S4','data/dex/dex_hunter')]
rows=[]
for s,d in seasons:
    tr=list(csv.DictReader(open(f'{d}/trades.csv')))
    pf=json.load(open(f'{d}/portfolio.json'))
    addr={}
    for f in (f'{d}/outcomes.csv','data/dex/outcomes.csv' if s=='S4' else None):
        if f:
            try:
                for o in csv.DictReader(open(f)): addr[o['coin']]=o['address']
            except FileNotFoundError: pass
    for k,v in pf['positions'].items(): addr[k]=v['addr']
    by={}
    for t in tr: by.setdefault(t['coin'],[]).append(t)
    for coin,ts in by.items():
        buys=[t for t in ts if t['side']=='BUY']; sells=[t for t in ts if t['side']=='SELL']
        if not buys: continue
        b=buys[0]; cost=sum(float(t['usd']) for t in buys)
        got=sum(float(t['usd'])-float(t['fee']) for t in sells)
        if coin in pf['positions']:
            v=pf['positions'][coin]; got+=v['qty']*(v.get('px') or 0)
        m=re.search(r'1h \+?(-?\d+)% 6h \+?(-?\d+)% buys/sells (\d+)/(\d+)',b['reason'])
        h1,h6,bb,ss=(int(x) for x in m.groups()) if m else (None,None,None,None)
        a=(addr.get(coin) or '').lower(); t0=T(b['time']); e=float(b['price'])
        pth=[x for x in path.get(a,[]) if t0<=x[0]<=t0+7*86400]
        rows.append(dict(s=s,coin=coin.split('@')[0],chain=coin.split('@')[1].split(':')[0],t=t0,cost=cost,ret=got/cost-1,
            first=float(b['usd']),h1=h1,h6=h6,br=(bb/max(ss,1)) if bb else None,e=e,path=pth,addon=len(buys)>1))
print('trades',len(rows),'with paths',sum(1 for r in rows if len(r['path'])>3))
tot_cost=sum(r['cost'] for r in rows); tot=sum(r['cost']*r['ret'] for r in rows)
print(f"live P/L ${tot:+.0f} on ${tot_cost:.0f} bet; mean {statistics.fmean(r['ret'] for r in rows):+.1%} median {statistics.median(r['ret'] for r in rows):+.1%}")
print('by season:',{s:round(sum(r['cost']*r['ret'] for r in rows if r['s']==s)) for s,_ in seasons})
print('win rate',sum(r['ret']>0 for r in rows)/len(rows), ' <=-80%:',sum(r['ret']<=-0.8 for r in rows)/len(rows))
# alternative exits on paths (per $1)
C=0.013
def alt(r,rule):
    e=r['e']; pth=r['path']
    if len(pth)<3: return None
    peak=e; cash=0; q=1
    for t,p,l in pth:
        peak=max(peak,p)
        x=p/e
        if rule[0]=='sell_all' and x>=rule[1]: return x*(1-C)-1
        if rule[0]=='half' and q==1 and x>=rule[1]: cash+=0.5*x*(1-C); q=0.5
        if rule[0]=='trail' and peak>=e*rule[1] and p<=peak*(1-rule[2]): return cash+q*x*(1-C)-1
        if rule[0]=='half_trail':
            if q==1 and x>=rule[1]: cash+=0.5*x*(1-C); q=0.5
            if q<1 and p<=peak*(1-rule[2]): return cash+q*x*(1-C)-1
    return cash+q*pth[-1][1]/e*(1-C)-1
R=[r for r in rows if len(r['path'])>=3]
R.sort(key=lambda r:r['t']); mid=len(R)//2
print(f"\nexits replayed on {len(R)} live trades with scanner paths (per $1, older/newer half):")
for name,rule in [('hold 7d',('none',)),('sell all 1.5x',('sell_all',1.5)),('sell all 2x',('sell_all',2)),('sell all 3x',('sell_all',3)),
                  ('half at 2x',('half',2)),('half at 1.5x',('half',1.5)),('trail 40% after 1.5x',('trail',1.5,0.4)),('trail 50% after 2x',('trail',2,0.5)),
                  ('half at 2x + trail 50%',('half_trail',2,0.5))]:
    xs=[alt(r,rule) for r in R]
    a=sum(xs[:mid]); b=sum(xs[mid:])
    print(f"  {name:<24} sum {sum(xs):+6.2f} ({a:+.2f}/{b:+.2f}) mean {statistics.fmean(xs):+.1%} median {statistics.median(xs):+.1%}")
print('\nentry features (live result):')
for lab,f in [('6h < +100%',lambda r:r['h6'] is not None and r['h6']<100),('6h 100-300%',lambda r:r['h6'] is not None and 100<=r['h6']<300),('6h >= 300%',lambda r:r['h6'] is not None and r['h6']>=300),
              ('buys/sells < 1.5',lambda r:r['br'] and r['br']<1.5),('buys/sells >= 1.5',lambda r:r['br'] and r['br']>=1.5),
              ('1h < 20%',lambda r:r['h1'] is not None and r['h1']<20),('1h >= 20%',lambda r:r['h1'] is not None and r['h1']>=20),
              ('solana',lambda r:r['chain']=='solana'),('ethereum',lambda r:r['chain']=='ethereum'),('base',lambda r:r['chain']=='base')]:
    xs=[r['ret'] for r in rows if f(r)]
    if xs: print(f"  {lab:<18} n {len(xs):>3} mean {statistics.fmean(xs):+.1%} median {statistics.median(xs):+.1%} win {sum(x>0 for x in xs)/len(xs):.0%}")
peaks=[max(p for _,p,_ in r['path'])/r['e'] for r in R]
print('\npeak after buy: >=1.5x',sum(p>=1.5 for p in peaks),' >=2x',sum(p>=2 for p in peaks),' >=3x',sum(p>=3 for p in peaks),' of',len(peaks))
