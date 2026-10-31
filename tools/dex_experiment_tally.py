"""Experiment 14-18 tally (10-31): every DEX buy since 10-18 06:48 by entry rule (survivor = 1h < +10%) and chain, cost vs
sold + still-held value. Run from the repo root."""
import csv, json, re
from collections import defaultdict
T=[r for r in csv.DictReader(open("data/dex/dex_hunter/trades.csv")) if r["time"]>="2026-10-18 06:48"]
P=json.load(open("data/dex/dex_hunter/portfolio.json"))["positions"]
buys=[]
for r in T:
    k=r["coin"]
    if r["side"]=="BUY":
        h1=float(re.search(r"1h ([+-]\d+)%",r["reason"]).group(1))/100
        buys.append(dict(k=k,t=r["time"],rule="survivor" if h1<0.10 else "fresh",chain=k.split("@")[1].split(":")[0],
                         pump=k.split(":")[1] if False else None,cost=float(r["usd"])+float(r["fee"]),back=0.0))
    else:
        c=[b for b in buys if b["k"]==k]
        if c: c[-1]["back"]+=float(r["usd"])-float(r["fee"])
for k,pos in P.items():
    c=[b for b in buys if b["k"]==k]
    if c: c[-1]["back"]+=pos["qty"]*pos["px"]
agg=defaultdict(lambda:[0,0.0,0.0,0,0])
for b in buys:
    x=b["back"]/b["cost"]
    for g in (b["rule"], b["chain"], b["rule"]+"/"+b["chain"], "ALL"):
        a=agg[g]; a[0]+=1; a[1]+=b["cost"]; a[2]+=b["back"]; a[3]+=x>=1; a[4]+=x>=2
for g,(n,c,bk,w,w2) in sorted(agg.items()):
    print(f"{g:22} n{n:3} cost ${c:7.2f} now ${bk:7.2f} P/L {bk-c:+8.2f} ({(bk/c-1)*100:+.0f}%) winners {w} 2x+ {w2}")
for lab,lo,hi in (("exp14-17 10-18..10-20","2026-10-18","2026-10-20 21:30"),("exp18+ 10-20 21:30..","2026-10-20 21:30","2027")):
    s=[b for b in buys if lo<=b["t"]<hi]; c=sum(b["cost"] for b in s); bk=sum(b["back"] for b in s)
    print(lab, len(s), f"P/L {bk-c:+.2f} ({(bk/c-1)*100:+.0f}%)")
print("best:", sorted(((round(b['back']/b['cost'],2),b['k'].split('@')[0],b['rule']) for b in buys), reverse=True)[:6])
