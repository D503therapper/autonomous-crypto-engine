"""S7b. THE ALTITUDE HOME TEAM AGAINST THE SPREAD - S7 found the home team on a 4,600 ft+ floor fails its number
(-8.6% on 965) and the highest floors fail worst. Is it altitude or three teams? By floor, by team, by the visitor's
own floor, by season, on the moneyline (the second market), and a placebo over random home-team sets.
   python s7b_altitude.py"""
import os, pickle, random, statistics
from collections import defaultdict
import lib2 as L
import sports_data as sd

o = L.Out("s7b")
random.seed(11)
rows = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
rows = [r for r in rows if 2016 <= r["season"] <= 2025 and r["stype"] == "2" and r.get("sp") is not None]
GF = sd.load_games("ncaab")


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


home_elev = defaultdict(list)
for r in rows:
    if r["venue"] == "home":
        e = fnum((GF.get(r["id"]) or {}).get("elev"))
        if e is not None:
            home_elev[r["team"]].append(e)
HE = {t: statistics.median(v) for t, v in home_elev.items() if len(v) >= 5}
NAME = {}
for r in rows:
    NAME[r["team"]] = r["name"]


def vis_p(r):
    """the VISITOR's profit (r = the visitor's row)"""
    x = r["margin"] + r["sp"]
    return 0.0 if x == 0 else ((L.dec(r.get("spodds") or -110) - 1) if x > 0 else -1.0)


V = []        # the visitor's rows in true road games, with the floor's elevation and its own
for r in rows:
    if r["venue"] != "away":
        continue
    e = fnum((GF.get(r["id"]) or {}).get("elev"))
    if e is None:
        continue
    V.append(dict(r, elev=e, own=HE.get(r["team"]), p=vis_p(r)))


def show(name, rs, split=2021):
    tr = [(r["season"], r["p"]) for r in rs if r["season"] <= split]
    he = [(r["season"], r["p"]) for r in rs if r["season"] > split]
    ut, uh = L.by_season(tr), L.by_season(he)
    o(f"   {name[:60]:60s} {L.st([r['p'] for r in rs])} | train {L.st([p for _, p in tr])[6:]} ({ut[0]}/{ut[1]}) | HELD {L.st([p for _, p in he])[6:]} ({uh[0]}/{uh[1]})")


o("== THE VISITOR against the closing spread, by the home floor's elevation (true road games 2016-25; train 2016-21 / held 2022-25) ==")
for lo, hi in ((0, 300), (300, 600), (600, 900), (900, 1200), (1200, 1400), (1400, 1600), (1600, 1800), (1800, 9999), (1400, 9999), (1500, 9999)):
    show(f"home floor {lo}-{hi} m ({int(lo * 3.281)}-{int(min(hi, 2300) * 3.281)} ft)", [r for r in V if lo <= r["elev"] < hi])
HI = [r for r in V if r["elev"] >= 1800]
o("\n== THE 5,900 ft+ FLOORS (1,800 m+) ==")
by = defaultdict(list)
for r in HI:
    by[r["oname"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(f"visitor at {k} ({HE.get(v[0]['opp'], 0):.0f} m)", v)
o("   by season: " + L.by_season([(r["season"], r["p"]) for r in HI])[2])
show("the visitor is the favorite", [r for r in HI if r["sp"] < 0])
show("the visitor is the dog", [r for r in HI if r["sp"] > 0])
show("   dog +0.5..+6.5", [r for r in HI if 0 < r["sp"] <= 6.5])
show("   dog +7 or more", [r for r in HI if r["sp"] >= 7])
show("the visitor's own floor is 1,200 m+ (a mountain team)", [r for r in HI if r["own"] is not None and r["own"] >= 1200])
show("the visitor's own floor is under 900 m", [r for r in HI if r["own"] is not None and r["own"] < 900])
show("Nov-Dec", [r for r in HI if r["nd"]])
show("Jan-Mar", [r for r in HI if not r["nd"]])
show("conference game (same_conf)", [r for r in HI if r.get("same_conf")])
show("priced -112 or cheaper", [r for r in HI if (r.get("spodds") or -110) >= -112])
ml = [dict(r, p=((L.dec(r["ml"]) - 1) if r["won"] else -1.0)) for r in HI if r.get("ml") is not None and -400 <= r["ml"] <= 400]
show("SECOND MARKET: the visitor's moneyline at the close (-400..+400)", ml)
mlo = [dict(r, p=((L.dec(r["mlo"]) - 1) if r["won"] else -1.0)) for r in HI if r.get("mlo") is not None and -400 <= r["mlo"] <= 400]
show("the visitor's moneyline at ESPN's OPEN (2023-25)", mlo)
o("\n== MOUNTAIN VISITOR at a mountain floor (both 1,200 m+), by the floor ==")
MM = [r for r in V if r["elev"] >= 1200 and r["own"] is not None and r["own"] >= 1200]
show("every mountain visitor at a 1,200 m+ floor", MM)
show("   the floor 1,200-1,400", [r for r in MM if r["elev"] < 1400])
show("   the floor 1,400-1,800", [r for r in MM if 1400 <= r["elev"] < 1800])
show("   the floor 1,800+", [r for r in MM if r["elev"] >= 1800])
LOWV = [r for r in V if r["elev"] >= 1400 and r["own"] is not None and r["own"] < 900]
show("a low-ground visitor (under 900 m) at a 1,400 m+ floor", LOWV)

o("\n== PLACEBO: is 'three home teams fail their number for ten seasons' rare? ==")
# every home team with 60+ lined home games: the visitor's ROI against it; where do the three sit, and how often does a
# random trio of home teams (same total games, roughly) do as badly in BOTH halves
ht = defaultdict(list)
for r in V:
    ht[r["opp"]].append(r)
big = {t: v for t, v in ht.items() if len(v) >= 60}
rois = sorted(((L.roi([r["p"] for r in v]), NAME.get(t, t), len(v)) for t, v in big.items()), reverse=True)
o(f"   {len(big)} home teams with 60+ lined home games; the visitor's ROI against each: best 8 = " + ", ".join(f"{n} {x:+.0f}% ({k})" for x, n, k in rois[:8]))
trio = sorted({r["opp"] for r in HI}, key=lambda t: -len(ht[t]))[:3]
real = L.roi([r["p"] for r in HI])
real_t = L.roi([r["p"] for r in HI if r["season"] <= 2021])
real_h = L.roi([r["p"] for r in HI if r["season"] > 2021])
teams = list(big)
hit = both = 0
NS = 5000
for _ in range(NS):
    pick = random.sample(teams, 3)
    rs = [r for t in pick for r in big[t]]
    a = L.roi([r["p"] for r in rs])
    hit += a >= real
    both += (L.roi([r["p"] for r in rs if r["season"] <= 2021]) >= real_t and L.roi([r["p"] for r in rs if r["season"] > 2021]) >= real_h)
o(f"   the 5,900 ft+ floors: visitor {real:+.1f}% (train {real_t:+.1f}% / held {real_h:+.1f}%); a random trio of home teams was as good for the visitor {hit} of {NS} times, in BOTH halves {both} of {NS}")
o("\ncells read: 10 floors + ~20 cuts + 6 = ~36 (on top of S7's 50)")
o.save()
