"""THE LINE-MOVE MODEL (10/1, the owner: "figure out what drove that line and what the outcome was - train our model to
pick the early plays that move in our favor, like the sharps"). For every side of every NFL / college game since 2020:
everything known at the FIRST FAIR number of the week (after both teams' last games), and what the line did by kickoff.
  1. WHAT DRIVES A MOVE: the average move toward a side, by each driver (injury news, last week, coach, weather, prime
     time, travel, popular teams...).
  2. A MODEL that learns those drivers from past seasons only (walk-forward), predicts which sides the line will move
     TO, and we bet its top picks at the early number - graded on WINS / COVERS at that number.
Saves results/early_move_model.json."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import early_round2 as r2           # noqa: E402
import early_round3 as r3           # noqa: E402
import sports_data as sd            # noqa: E402

POPULAR = {"nfl": ("Cowboys", "Steelers", "Packers", "Chiefs", "49ers", "Eagles", "Patriots", "Bears", "Raiders"),
           "ncaaf": ("Alabama", "Ohio State", "Michigan", "Georgia", "Notre Dame", "Texas", "USC", "LSU", "Oklahoma",
                     "Penn State", "Florida", "Clemson", "Oregon", "Tennessee")}


def cents_in(first, close):
    """+ = the price moved TOWARD this side (it got shorter): +150 -> +120 = 30, -110 -> -140 = 30."""
    if first is None or close is None:
        return None
    imp = lambda o: 1 / ef._dec(o)
    return round((imp(close) - imp(first)) * 100, 1)          # in win-% points (works across + and -)


def build(lg):
    games = sd.load_games(lg)
    rows = r2.build(lg)
    ctx = r3.context(lg, games)
    names = {}
    for g in games.values():
        for side in ("home", "away"):
            names[g[side]] = g.get(side + "_name") or ""
    inj = {}
    if lg == "nfl":
        import early_injuries as ei
        rep = ei.reports()
        wk = ei.week_of(rows)
        blank = {"qb_out": False, "qb_q": False, "n_out": 0}
        for r in rows:
            w = wk[r["gid"]]
            inj[(r["gid"], r["tid"])] = (rep.get((r["season"], r["tid"], w - 1), blank), rep.get((r["season"], r["oid"], w - 1), blank),
                                        rep.get((r["season"], r["tid"], w), blank), rep.get((r["season"], r["oid"], w), blank))
    out = []
    for r in rows:
        c = ctx.get((r["gid"], r["tid"]))
        if c is None:
            continue
        r["mv_ml"] = cents_in(r.get("ml"), r.get("ml_close"))
        r["mv_sp"] = (r["line"] - r["sp_close"]) if r.get("line") is not None and r.get("sp_close") is not None else None
        #             (+ = the spread moved toward this side: +9.5 -> +3.5 = +6)
        r["ctx"] = c
        r["popular"] = any(p in names.get(r["tid"], "") for p in POPULAR[lg])
        r["opp_popular"] = any(p in names.get(r["oid"], "") for p in POPULAR[lg])
        r["inj"] = inj.get((r["gid"], r["tid"]))
        out.append(r)
    return out


def X(r):
    c = r["ctx"]
    i = r["inj"]
    gap = r.get("ml_gap") if r.get("ml_gap") is not None else 0.0
    se = r.get("sp_edge") if r.get("sp_edge") is not None else 0.0
    return [1.0, gap * 10, max(-10, min(10, se)) / 7, max(-21, min(21, r.get("line") or 0)) / 14,
            1.0 if r["side"] == "home" and not r["neutral"] else 0.0, 1.0 if r["neutral"] else 0.0,
            max(-28, min(28, r.get("last") or 0)) / 14, max(-5, min(5, r.get("streak") or 0)) / 3,
            max(-5, min(5, r.get("ostreak") or 0)) / 3, max(-5, min(5, r.get("ats") or 0)) / 3,
            max(-7, min(7, (r.get("rest") or 7) - (r.get("orest") or 7))) / 7,
            1.0 if (r.get("coach") or (False,))[0] else 0.0, 1.0 if (r.get("ocoach") or (False,))[0] else 0.0,
            1.0 if r.get("night") else 0.0, 1.0 if c["division"] else 0.0,
            min(c["wind"] or 0, 30) / 15, 1.0 if (c["temp"] is not None and c["temp"] <= 35) else 0.0,
            1.0 if r["popular"] else 0.0, 1.0 if r["opp_popular"] else 0.0,
            1.0 if (i and i[0]["qb_out"]) else 0.0, 1.0 if (i and i[1]["qb_out"]) else 0.0,
            ((i[1]["n_out"] - i[0]["n_out"]) / 4) if i else 0.0,
            1.0 if r.get("games", 0) < 3 else 0.0, (r.get("pd") or 0) / 14]


NAMES = ["bias", "engine ml read", "engine spread read", "the line", "home", "neutral", "last week margin", "win streak",
         "opp win streak", "cover streak", "rest edge", "our coach new", "their coach new", "prime time", "division",
         "wind", "cold", "popular team", "popular opponent", "our QB out last wk", "their QB out last wk",
         "their extra injuries last wk", "first 3 games", "season point diff"]


def fit(Xs, ys, lam=2.0, iters=400, lr=0.3):
    w = [0.0] * len(Xs[0])
    n = len(Xs)
    for _ in range(iters):
        g = [lam * wi / n for wi in w]
        g[0] = 0.0
        for x, y in zip(Xs, ys):
            z = sum(a * b for a, b in zip(w, x))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            for j, v in enumerate(x):
                g[j] += (p - y) * v / n
        w = [wi - lr * gi for wi, gi in zip(w, g)]
    return w


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        rows = build(lg)
        print(f"\n===================== {lg.upper()}: {len(rows)} sides")
        res = {"drivers": {}, "model": {}}
        # 1. what drives a move (average move toward the side, in spread points / win-% points)
        drivers = {
            "every side": lambda r: True, "engine likes it (ml +4)": lambda r: (r.get("ml_gap") or 0) >= .04,
            "engine spread read 3.5+": lambda r: (r.get("sp_edge") or -99) >= 3.5,
            "blew someone out last week": lambda r: (r.get("last") or 0) >= 17, "got blown out last week": lambda r: (r.get("last") or 0) <= -17,
            "popular team": lambda r: r["popular"], "vs a popular team": lambda r: r["opp_popular"],
            "our coach's 1st season": lambda r: (r.get("coach") or (False,))[0], "prime time": lambda r: bool(r.get("night")),
            "win streak 3+": lambda r: (r.get("streak") or 0) >= 3, "losing streak 3+": lambda r: (r.get("streak") or 0) <= -3,
            "home": lambda r: r["side"] == "home" and not r["neutral"], "off a bye": lambda r: (r.get("rest") or 0) >= 13,
            "their QB out last week": lambda r: bool(r["inj"] and r["inj"][1]["qb_out"]),
            "our QB out last week": lambda r: bool(r["inj"] and r["inj"][0]["qb_out"]),
            "LATER: their QB ruled out": lambda r: bool(r["inj"] and r["inj"][3]["qb_out"] and not r["inj"][1]["qb_out"]),
            "LATER: our QB ruled out": lambda r: bool(r["inj"] and r["inj"][2]["qb_out"] and not r["inj"][0]["qb_out"]),
        }
        print("-- what moves the line (avg move toward the side by kickoff: spread pts | win-% pts on the moneyline)")
        for nm, t in drivers.items():
            sel = [r for r in rows if t(r)]
            sp = [r["mv_sp"] for r in sel if r["mv_sp"] is not None]
            ml = [r["mv_ml"] for r in sel if r["mv_ml"] is not None]
            if not sel:
                continue
            res["drivers"][nm] = {"n": len(sel), "spread_pts": round(sum(sp) / len(sp), 2) if sp else None,
                                  "ml_pts": round(sum(ml) / len(ml), 2) if ml else None,
                                  "moved_our_way_1pt": round(sum(1 for x in sp if x >= 1) / len(sp), 3) if sp else None}
            d = res["drivers"][nm]
            print(f"   {nm:32s} {d['n']:5d}  spread {d['spread_pts'] if d['spread_pts'] is not None else '-':>6}  "
                  f"ml {d['ml_pts'] if d['ml_pts'] is not None else '-':>6}  moved 1+ our way {d['moved_our_way_1pt']}")
        # 2. the model: learn (past seasons) which sides the line moves TO; bet its top picks at the early number
        for market, target, grade, ok in (
                ("spread", lambda r: r["mv_sp"] >= 1, r2.grade_sp, lambda r: r["mv_sp"] is not None and r.get("cover") is not None),
                ("ML dog", lambda r: r["mv_ml"] >= 2, r2.grade_ml, lambda r: r["mv_ml"] is not None and r.get("ml") is not None and 100 <= r["ml"] <= 600)):
            for top in (.05, .1, .2):
                picks, hit, wts = [], [], None
                for s in ef.SEASONS:
                    tr = [r for r in rows if r["season"] < s and ok(r)]
                    te = [r for r in rows if r["season"] == s and ok(r)]
                    if len(tr) < 400 or not te:
                        continue
                    w = fit([X(r) for r in tr], [1.0 if target(r) else 0.0 for r in tr])
                    wts = w
                    te.sort(key=lambda r: -sum(a * b for a, b in zip(w, X(r))))
                    k = te[:max(1, int(len(te) * top))]
                    picks += k
                    hit += [target(r) for r in k]
                g = grade(picks)
                if not g:
                    continue
                g["moved_our_way"] = round(sum(hit) / len(hit), 3)
                res["model"][f"{market} top {int(top * 100)}%"] = g
                print(f"   MODEL {market:7s} top {int(top * 100):2d}%  {g['n']:4d}  line moved our way {g['moved_our_way']:.0%}  "
                      f"{'won' if market != 'spread' else 'covered'} {g['rate']:.1%} (needs {g['said']:.1%})  ROI {g['roi']:+.1%}  "
                      f"up {g['up']} {g['by']}")
            if wts:
                res["model"][f"{market} weights (last season's model)"] = {n: round(v, 3) for n, v in zip(NAMES, wts)}
                top_w = sorted(zip(NAMES[1:], wts[1:]), key=lambda x: -abs(x[1]))[:6]
                print(f"   {market} - what the model learned matters most: " + ", ".join(f"{n} {v:+.2f}" for n, v in top_w))
        rep[lg] = res
    with open("results/early_move_model.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
