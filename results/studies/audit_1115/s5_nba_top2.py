"""11/15 FABLE FULL ENGINE AUDIT - S5: two built NBA favorite weights re-read (sports.NBA_FAV_W "opp_top2_out" -2 and
"own_top2_out" -2 on a -150..-101 favorite's weighed read - the 10/22 study: the favorite across a team missing a top-2
man -7.1% / -14.4%, "the books over-move"). Why re-read: the live tracker's tag "NBA fav vs a team missing a top-2 man
(fade)" has the faded favorites 39-13 +4.3% on 52 (the fade's side is winning), and the 11/12 deep program found the
close has a missing top scorer exactly (the side across one won 60.1% against a close of 60.0% on 2,210).
Here: every NBA regular-season close 2018-26 from the box scores - a team's top-2 men by minutes so far this season
(10+ team games), "out" = no minutes in tonight's box. One season of box rows in memory at a time.
Run from the repo root:  python results/studies/audit_1115/s5_nba_top2.py"""
import json, os, pickle, random, sys
sys.path.insert(0, os.getcwd())
import sports_data as sd
import sports_model as sm
import sports_roster

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_audit1115")
os.makedirs(CACHE, exist_ok=True)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def season(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 8 else y - 1


def build():
    path = os.path.join(CACHE, "s5_nba.pkl")
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    games = sd.load_games("nba")
    fin = [g for g in sm.finals(games, "nba") if (g.get("stype") or "2") == "2"]
    out = []
    for y in range(2018, 2027):
        rows = sports_roster.load("nba", seasons=[y])
        by = {}
        for r in rows:
            try:
                m = float(json.loads(r.get("stats") or "{}").get("minutes") or 0)
            except (ValueError, TypeError):
                m = 0.0
            by.setdefault(r["gid"], {}).setdefault(r["team"], {})[r["player"]] = m
        del rows
        tot, n = {}, {}
        for g in fin:
            if season(g["start"]) != y or g["id"] not in by:
                continue
            box = by[g["id"]]
            info = {}
            for side in ("home", "away"):
                t = str(g[side])
                if n.get(t, 0) >= 10 and t in box:
                    top = sorted(tot[t].items(), key=lambda kv: -kv[1])[:2]
                    info[side] = sum(1 for p, _ in top if box[t].get(p, 0) <= 0)
                else:
                    info[side] = None
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
                mh, ma = int(float(g["ml_home"])), int(float(g["ml_away"]))
            except (KeyError, ValueError, TypeError):
                mh = None
            if mh and ma and hs != as_ and None not in info.values():
                for side, o, won, other in (("home", mh, hs > as_, "away"), ("away", ma, as_ > hs, "home")):
                    out.append({"y": y, "odds": o, "won": won, "own_out": info[side], "opp_out": info[other], "home": side == "home",
                                "start": g["start"]})
            for side in ("home", "away"):
                t = str(g[side])
                if t in box:
                    n[t] = n.get(t, 0) + 1
                    d = tot.setdefault(t, {})
                    for p, m in box[t].items():
                        d[p] = d.get(p, 0.0) + m
        print(y, "sides so far", len(out), flush=True)
    pickle.dump(out, open(path, "wb"))
    return out


def roi(rs):
    return sum((dec(r["odds"]) - 1) if r["won"] else -1 for r in rs) / len(rs) if rs else 0.0


def cell(name, rs, base=None):
    if not rs:
        print(f"  {name:<62} n=0")
        return
    w = sum(r["won"] for r in rs)
    tr, he = [r for r in rs if r["y"] <= 2022], [r for r in rs if r["y"] >= 2023]
    ys = sorted({r["y"] for r in rs})
    up = sum(1 for y in ys if roi([r for r in rs if r["y"] == y]) > 0)
    pl = ""
    if base:
        random.seed(1115)
        mine = roi(rs)
        hit = sum(1 for _ in range(2000) if roi(random.sample(base, len(rs))) <= mine)
        pl = f"  placebo (as bad or worse) {hit} of 2,000"
    print(f"  {name:<62} {w}-{len(rs) - w}  ROI {roi(rs) * 100:+.1f}% on {len(rs)}  train {roi(tr) * 100:+.1f}% on {len(tr)} / "
          f"held {roi(he) * 100:+.1f}% on {len(he)}  seasons up {up}/{len(ys)}{pl}")


def main():
    rs = build()
    band = [r for r in rs if -150 <= r["odds"] <= -101]
    favs = [r for r in rs if r["odds"] <= -101]
    print(f"NBA regular-season sides at the close 2018-26, both teams 10+ games in: {len(rs)}")
    print(" -- the favorite -150..-101 (the weights' band) --")
    cell("every favorite in the band", band)
    cell("the OPPONENT missing 1+ of its top-2 minutes men", [r for r in band if r["opp_out"] >= 1], band)
    cell("  ... missing both", [r for r in band if r["opp_out"] >= 2])
    cell("  ... and our own top-2 both playing", [r for r in band if r["opp_out"] >= 1 and r["own_out"] == 0], band)
    cell("our OWN top-2: 1+ out", [r for r in band if r["own_out"] >= 1], band)
    cell("  ... and theirs both playing", [r for r in band if r["own_out"] >= 1 and r["opp_out"] == 0], band)
    cell("nobody's top-2 out", [r for r in band if r["own_out"] == 0 and r["opp_out"] == 0])
    for y in sorted({r["y"] for r in band}):
        cell(f"    season {y}: opponent missing 1+", [r for r in band if r["y"] == y and r["opp_out"] >= 1])
    print(" -- every favorite (any price) --")
    cell("every favorite", favs)
    cell("the opponent missing 1+ of its top-2", [r for r in favs if r["opp_out"] >= 1], favs)
    cell("our own top-2: 1+ out", [r for r in favs if r["own_out"] >= 1], favs)
    print(" -- the favorite -150..-101 at HOME / on the ROAD, the opponent missing 1+ --")
    cell("home", [r for r in band if r["opp_out"] >= 1 and r["home"]])
    cell("road", [r for r in band if r["opp_out"] >= 1 and not r["home"]])


if __name__ == "__main__":
    main()
