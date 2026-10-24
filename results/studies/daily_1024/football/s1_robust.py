"""S1 robustness (NFL dog's defense trend): windows / thresholds / opponent-adjusted / yards allowed (box 2021-26)."""
import sys, os, gzip, csv, json, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1024 as S
from s1024 import lib, sd, sm, dec, season, num, summ, fmt

def yards_box(lg):
    out = collections.Counter()
    for y in range(2021, 2027):
        p = os.path.join(sd.DATA, "roster", f"{lg}_{y}.csv.gz")
        with gzip.open(p, "rt") as f:
            for row in csv.DictReader(f):
                if row["group"] not in ("rushing", "passing"):
                    continue
                st = json.loads(row["stats"])
                k = "rushingYards" if row["group"] == "rushing" else "passingYards"
                try: out[(row["gid"], row["team"])] += float(st.get(k) or 0)
                except ValueError: pass
    return out

for lg in ("nfl", "ncaaf"):
    games = sd.load_games(lg)
    fin = sorted([g for g in sm.finals(games, lg) if (g.get("stype") or "2") == "2"], key=lambda g: g["start"])
    yb = yards_box(lg)
    hist = collections.defaultdict(list)
    C = collections.defaultdict(list)
    for g in fin:
        se = season(g["start"])
        try: hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError): continue
        mh, ma = num(g.get("ml_home")), num(g.get("ml_away"))
        if mh is not None and ma is not None and se >= 2018 and hs != as_:
            for side, am, oam, won in (("h", mh, ma, hs > as_), ("a", ma, mh, as_ > hs)):
                if not (100 <= am <= 350 and oam < 0): continue
                dog = g["home"] if side == "h" else g["away"]
                p = (dec(am) - 1) if won else -1.0
                dh = hist[(se, dog)]
                for w in (2, 3, 4):
                    if len(dh) >= w + 2:
                        d = statistics.mean(x["pa"] for x in dh[-w:]) - statistics.mean(x["pa"] for x in dh[:-w])
                        for th in (5, 7, 10):
                            if d <= -th: C[f"pts allowed last{w} {th}+ better"].append((se, p))
                        # opponent-adjusted: pa minus that opponent's season-to-date scoring avg
                        da = [x["adj"] for x in dh if x["adj"] is not None]
                        if len(da) >= w + 2:
                            d2 = statistics.mean(da[-w:]) - statistics.mean(da[:-w])
                            if d2 <= -7: C[f"OPP-ADJUSTED pts allowed last{w} 7+ better"].append((se, p))
                    ya = [x["ya"] for x in dh if x["ya"] is not None]
                    if se >= 2021 and len(ya) >= w + 2:
                        d3 = statistics.mean(ya[-w:]) - statistics.mean(ya[:-w])
                        for th in (50, 80):
                            if d3 <= -th: C[f"YARDS allowed last{w} {th}+ better (2021+)"].append((se, p))
                if len(dh) >= 5: C["control: all dogs 5+ games in"].append((se, p))
        # opp scoring averages before this game
        for side, team, opp in (("h", g["home"], g["away"]), ("a", g["away"], g["home"])):
            pa = as_ if side == "h" else hs
            oh = hist[(se, opp)]
            adj = pa - statistics.mean(x["pf"] for x in oh) if oh else None
            ya = yb.get((g["id"], opp)) if (g["id"], opp) in yb else None
            hist[(se, team)].append({"pa": pa, "pf": hs if side == "h" else as_, "adj": adj, "ya": ya})
    print(f"\n=== {lg} ===")
    for k in sorted(C): print(fmt(k, summ(C[k])))
