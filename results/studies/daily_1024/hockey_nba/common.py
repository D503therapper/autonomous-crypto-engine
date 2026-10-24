"""Shared loader for the 10/23 NHL + NBA studies. Read-only on the repo. One row per side, every feature
known before puck drop / tip (schedule + results of EARLIER games only). Graded flat 1u at the closing ML."""
import sys, csv, collections, math
from datetime import datetime, timedelta
WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"
sys.path.insert(0, WT)
import os; os.chdir(WT)
import sports_data as sd

def season(start):
    y, m = int(start[:4]), int(start[5:7])
    if y == 2020 and m <= 10: return 2019          # bubble
    return y if m >= 9 else y - 1
def dt(s): return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")
def us_date(s): return (dt(s) - timedelta(hours=8)).date()   # Pacific-ish night
def prob(ml): ml = float(ml); return 100/(ml+100) if ml > 0 else -ml/(-ml+100)
def pay(ml): ml = float(ml); return ml/100 if ml > 0 else 100/-ml

def load(league, start="2016-09-01"):
    G = sd.load_games(league)
    fin = [g for g in G.values() if g.get("status") == "final" and str(g.get("stype")) == "2"
           and g.get("home_score") not in ("", None) and g.get("start", "") >= start and g.get("home") and g.get("away")]
    fin.sort(key=lambda g: (g["start"], g["id"]))
    sched = collections.defaultdict(list)
    for g in fin:
        sched[g["home"]].append(g); sched[g["away"]].append(g)
    return fin, sched

TRAIN = None  # set per study
def band(ml):
    return "dog" if 100 <= ml <= 300 else "fav" if -150 <= ml <= -100 else None

def report(rows, f, name, train, hold, cur=(2026,), out=print):
    """rows: dicts with season, ml, nv, won, roi. Prints train / holdout / current, by season, vs expected."""
    r = [x for x in rows if f(x)]
    line = [name]
    for part, ss in (("TRAIN", train), ("HOLD", hold), ("CUR", cur)):
        rs = [x for x in r if x["season"] in ss]
        if not rs: line.append(f"{part}: n=0"); continue
        n = len(rs); w = sum(x["won"] for x in rs); e = sum(x["nv"] for x in rs)
        roi = sum(x["roi"] for x in rs) / n * 100
        sd_ = math.sqrt(sum(x["nv"]*(1-x["nv"]) for x in rs)) or 1
        z = (w - e) / sd_
        bys = " ".join(f"{s%100}:{sum(x['roi'] for x in rs if x['season']==s)/max(1,sum(1 for x in rs if x['season']==s))*100:+.0f}({sum(1 for x in rs if x['season']==s)})"
                       for s in ss if any(x['season']==s for x in rs))
        up = sum(1 for s in ss if any(x['season']==s for x in rs) and sum(x['roi'] for x in rs if x['season']==s) > 0)
        tot = sum(1 for s in ss if any(x['season']==s for x in rs))
        line.append(f"{part}: n={n} {w/n*100:.1f}% vs {e/n*100:.1f}% exp z{z:+.1f} ROI {roi:+.1f}% up {up}/{tot} [{bys}]")
    out("\n   ".join(line))
    return r
