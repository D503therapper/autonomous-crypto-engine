import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5")
from common import grade, TRAIN, BLIND
import pandas as pd, numpy as np
D = pd.read_pickle("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nbadogs/dogs.pkl")
def g(sub, nm):
    out=[]
    for k,s in (("TRAIN",TRAIN),("BLIND",BLIND)):
        x=sub[sub.season.isin(s)]
        if len(x)==0: out.append(f"{k} n=0"); continue
        r=grade(x,k); up=sum(v[1]>0 for v in r["seasons"].values())
        out.append(f"{k} n={r['n']} win {r['win']}% vs {r['imp']}% ROI {r['roi']:+.1f}% ({up}/{len(r['seasons'])})")
    print(f"{nm:40s} | "+" | ".join(out))
e=D.t_n_season<10
g(D[e],"all dogs, team games 1-10")
for lo,hi in ((100,130),(130,200),(200,300)): g(D[e&D.ml.between(lo+1 if lo>100 else lo,hi)],f"  g1-10 +{lo}..+{hi}")
g(D[e&(D.is_home==0)],"  g1-10 road dogs"); g(D[e&(D.is_home==1)],"  g1-10 home dogs")
plus = ((D.t_last_margin<=-15).astype(int) + ((D.is_home==1)&D.t_n_season.between(5,29)).astype(int)
        + (D.total>=235).astype(int) + (D.pm_margin<=-15).astype(int))
minus = (((D.is_home==1)&D.t_n_season.between(30,59)).astype(int) + (D.t_last_margin>=15).astype(int)
         + (D.total<=215).astype(int) + (D.o_trip_game>=4).astype(int) + ((D.is_home==1)&(D.t_home_after>=4)).astype(int)
         + (D.o_last_margin>=20).astype(int))
D["sc"]=plus-minus
for t in (2,1,0,-1,-2): g(D[D.sc==t] if abs(t)<2 else D[(D.sc>=2) if t>0 else (D.sc<=-2)], f"20 combo score {'>=' if t==2 else ('<=' if t==-2 else '=')}{t}")
# best-scored dog per day
day=D[D.sc>=1].sort_values(["date","sc","mp"],ascending=[True,False,False]).groupby("date").head(1)
g(day,"20 top-scored dog each day (sc>=1)")
