import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5")
from common import grade, TRAIN, BLIND, load, sides
import pandas as pd, numpy as np, pickle
P="/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/"
D2=pd.read_pickle(P+"nbadogs/dogs2.pkl")           # dog sides with every feature (both teams' facts)
# favorites = the other side of each dog row: rebuild from all sides
S=pd.DataFrame(sides(load()))
bf,_=pickle.load(open(P+"nba5/box.pkl","rb"))
F=S[(S.ml<0)&(S.ml>=-300)].copy()
# bring the dog-row features over (keyed by gid): dog's facts are the fav's opponent facts
key=D2.set_index("gid")
cols=["d_prev_blew","d_prev_ot","d_prev_pts","d_streak","f_prev_ot","f_prev_pts","f_streak","pm_margin","total","t_home_after","o_trip_game","t_last_margin","o_last_margin","t_n_season","is_home","t_wp_last","t_rest","o_rest"]
F=F[F.gid.isin(key.index)]
for c in cols: F["dog_"+c]=key.loc[F.gid,c].values
for c in ("top5_back","top5_out","top2_out"):
    F["me_"+c]=[bf.get((g,(h if s=="home" else a)),{}).get(c) for g,h,a,s in zip(F.gid,F.home,F.away,F.side)]
    F["op_"+c]=[bf.get((g,(a if s=="home" else h)),{}).get(c) for g,h,a,s in zip(F.gid,F.home,F.away,F.side)]
F["mp"]=F.mp; 
def L(m,label):
    sub=F[pd.Series(m,index=F.index).fillna(False).astype(bool)]
    out=[]
    for k,ss in (("TRAIN",TRAIN),("BLIND",BLIND)):
        x=sub[sub.season.isin(ss)]
        if len(x)==0: out.append(f"{k} n=0"); continue
        r=grade(x,k); up=sum(v[1]>0 for v in r["seasons"].values())
        out.append(f"{k} n={r['n']} {r['win']}% vs {r['imp']}% ROI {r['roi']:+.1f}% ({up}/{len(r['seasons'])})")
    print(f"{label:58s} | "+" | ".join(out))
L(F.ml<=0,"all favorites -300..-100 (baseline)")
L(F.ml>=-150,"favorites -150..-100 (our band)")
band=F.ml>=-150
print("== star absence / return (box 2021+)")
L(band&(F.me_top5_back>=1),"1 fav's top-5 man back after 2+ missed")
L(band&(F.op_top2_out>=1),"2 fav vs team missing a top-2 man")
L(band&(F.op_top5_out>=1),"2b fav vs team missing a top-5 man")
L(band&(F.me_top2_out>=1),"3 fav missing its own top-2 man")
print("== mirror of the dog traps (fav side)")
L(band&(F.dog_d_prev_blew==True),"4 opponent (dog) blew a 10+ half lead last game")
L(band&(F.dog_f_prev_pts<=95),"5 fav scored <=95 last game (bounce)")
L(band&(F.dog_d_streak>=3),"6 opponent dog on a 3+ win streak")
L(band&(F.dog_f_prev_ot==True),"7 fav played OT last game")
L(band&((F.dog_o_rest-F.dog_t_rest)>=2),"8 fav 2+ more days rest")
L(band&(F.dog_o_last_margin>=20),"9 fav off a 20+ win")
L(band&(F.dog_o_trip_game>=4),"10 fav on road game 4+")
L(band&(F.dog_is_home==1)&F.dog_t_n_season.between(30,59),"11 fav at a home dog in games 31-60")
L(band&(F.dog_t_n_season<5),"12 week one (team games 1-5)")
