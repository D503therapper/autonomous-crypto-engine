"""10/29 football robustness, part 2 - the NFL 1st-half share: the raw grid (full spread x 1st-half spread), the
total, home / road, every season. Same row cache."""
import os, pickle, collections
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1029")
S = pickle.load(open(os.path.join(CACHE, "fb_sides.pkl"), "rb"))
dec = lambda o: 1 + (o / 100 if o > 0 else 100 / -o)
pr = lambda x: dec(x["ml"]) - 1 if x["won"] else -1
fm = lambda v: f"{len(v)}/{sum(v)/len(v):+.1%}" if v else "-"
for lg in ("nfl", "ncaaf"):
    d = [x for x in S if x["league"] == lg and x["season"] >= 2018 and x["stype"] == "2" and 100 <= x["ml"] <= 350
         and x["h1sp"] is not None and x["pts"] is not None and x["pts"] >= 2.5]
    print(lg, "dogs: full spread x 1st-half spread (n / ROI), cells with 25+")
    c = collections.defaultdict(list)
    for x in d:
        c[(x["pts"], x["h1sp"])].append(pr(x))
    for k in sorted(c):
        if len(c[k]) >= 25 and k[0] <= 10:
            print(f"   full +{k[0]:<4} h1 {k[1]:+5}  share {k[1]/k[0]:.2f}  {fm(c[k])}")
    tb = collections.defaultdict(lambda: collections.defaultdict(list))
    hb = collections.defaultdict(list)
    sb = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in d:
        s_ = x["h1sp"] / x["pts"]
        b = "big 0.60+" if s_ >= .6 else ("small <0.45" if s_ < .45 else "mid")
        if x["total"] is not None:
            tk = ("<41" if x["total"] < 41 else ("41-47" if x["total"] < 47.5 else "48+")) if lg == "nfl" else \
                 ("<50" if x["total"] < 50 else ("50-59" if x["total"] < 60 else "60+"))
            tb[tk][b].append(pr(x))
        hb[("home" if x["home"] else "road", b)].append(pr(x))
        sb[x["season"]][b].append(pr(x))
    for tk in tb:
        print("   total", tk, {k: fm(v) for k, v in sorted(tb[tk].items())})
    print("   home/road", {f"{k[0]} {k[1]}": fm(v) for k, v in sorted(hb.items())})
    for s in sorted(sb):
        print("   season", s, {k: fm(v) for k, v in sorted(sb[s].items())})
