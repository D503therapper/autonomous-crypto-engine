"""EARLY STUDY #3 - DID THE LINE OVERREACT TO LAST WEEK? (10/1). Books post next week's line BEFORE this week's games
(the look-ahead line), then move it after the results. That jump = how hard the market reacted to ONE game. For each
game: the last look-ahead price (posted before both teams' last games ended) vs the first FAIR price (after). Bet the
side the market just ran AWAY from (its win % dropped the most) at the fair price - and, the other way, the side it ran
TO - graded on WINS at that fair price (bettable: posted after the results). Moneylines and spreads, NFL and college.
Saves results/early_overreaction.json."""
import gzip
import json
import os
import statistics
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402


def novig(h, a):
    ph, pa = 1 / ef._dec(h), 1 / ef._dec(a)
    return ph / (ph + pa)


def all_looks(lg, games, kind):
    """{game id: [(days out, fair?, value home-first)]} - moneyline: (no-vig home %, median home, median away);
    spreads: median home spread. Every look up to 16 days out."""
    ready = ef.ready_at(games, lg)
    path = os.path.join(sd.DATA, "odds_history", f"{ef.SPORTS[lg]}{'_spreads' if kind == 'spreads' else ''}.jsonl.gz")
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    with gzip.open(path, "rt") as f:
        for r in map(json.loads, f):
            if "b" not in r:
                continue
            t = ef._t(r["t"])
            days = (t - ef._t(r["snap"])).total_seconds() / 86400
            if not 1.0 <= days < 16:
                continue
            hit = None
            for d in (-1, 0, 1):
                for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), []):
                    if abs((ef._t(g["start"]) - t).total_seconds()) > 14 * 3600:
                        continue
                    if sd._same(g.get("home_name") or "", r["h"]) and sd._same(g.get("away_name") or "", r["a"]):
                        hit = (g, False)
                    elif sd._same(g.get("home_name") or "", r["a"]) and sd._same(g.get("away_name") or "", r["h"]):
                        hit = (g, True)
                    if hit:
                        break
                if hit:
                    break
            if not hit:
                continue
            g, flip = hit
            vals = [v for v in r["b"].values() if v and v[0] is not None and (kind == "spreads" or v[1] is not None)]
            if len(vals) < 2:
                continue
            if kind == "spreads":
                val = statistics.median((-v[0] if flip else v[0]) for v in vals)
            else:
                hs_ = [ef._dec(v[1] if flip else v[0]) for v in vals]
                as_ = [ef._dec(v[0] if flip else v[1]) for v in vals]
                mh, ma = ef._am(statistics.median(hs_)), ef._am(statistics.median(as_))
                val = (novig(mh, ma), mh, ma)
            out.setdefault(g["id"], []).append((days, ef.fair(ready, g["id"], g["start"], days), val))
    return out


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        games = sd.load_games(lg)
        res = {}
        for kind in ("h2h", "spreads"):
            lk = all_looks(lg, games, kind)
            rows = []
            for gid, ls in lk.items():
                g = games[gid]
                try:
                    hs, as_ = float(g["home_score"]), float(g["away_score"])
                except (KeyError, ValueError):
                    continue
                if g.get("status") != "final" or hs == as_:
                    continue
                pre = [x for x in ls if not x[1]]
                post = [x for x in ls if x[1] and x[0] >= 1.5]
                if not pre or not post:
                    continue
                pre = min(pre, key=lambda x: x[0])                      # the last look-ahead (closest to the results)
                post = max(post, key=lambda x: x[0])                    # the first fair look
                y, mo = int(g["start"][:4]), int(g["start"][5:7])
                season = y if mo >= 7 else y - 1
                for side, sg in (("home", 1), ("away", -1)):
                    if kind == "spreads":
                        move = (post[2] - pre[2]) * sg                  # + = this side now GETS more / lays less = it
                        #                                                 got WORSE in the market's eyes (ran away from)
                        ln = post[2] * sg
                        m = (hs - as_) * sg
                        if m + ln == 0:
                            continue
                        rows.append({"season": season, "away_from": move, "won": m + ln > 0, "dec": 1 + 10 / 11})
                    else:
                        p0 = pre[2][0] if side == "home" else 1 - pre[2][0]
                        p1 = post[2][0] if side == "home" else 1 - post[2][0]
                        o = post[2][1] if side == "home" else post[2][2]
                        if not -150 <= o <= 400:
                            continue
                        rows.append({"season": season, "away_from": (p0 - p1) * 100, "won": (hs > as_) == (side == "home"),
                                     "dec": ef._dec(o), "dog": o >= 100})
            print(f"\n===== {lg.upper()} {('MONEYLINES' if kind == 'h2h' else 'SPREADS')}: {len(rows)} sides with a "
                  f"look-ahead AND a fair price")
            unit = "pts" if kind == "spreads" else "win-% pts"
            for lo in ((1.5, 3, 4.5) if kind == "spreads" else (3, 6, 10)):
                for lbl, f in (("the side the market ran AWAY from", lambda r, lo=lo: r["away_from"] >= lo),
                               ("the side the market ran TO", lambda r, lo=lo: r["away_from"] <= -lo)):
                    for sub, sf in ((("all", lambda r: True),) if kind == "spreads" else
                                    (("dogs", lambda r: r["dog"]), ("favorites", lambda r: not r["dog"]))):
                        sel = [r for r in rows if f(r) and sf(r)]
                        if not sel:
                            continue
                        by = {}
                        for r in sel:
                            by.setdefault(r["season"], []).append((r["dec"] - 1) if r["won"] else -1)
                        n = len(sel)
                        last = [x for s, v in by.items() if s >= 2023 for x in v]
                        gr = {"n": n, "won": round(sum(r["won"] for r in sel) / n, 3),
                              "roi": round(sum(x for v in by.values() for x in v) / n, 3),
                              "last3_and_now": [len(last), round(sum(last) / len(last), 3) if last else None],
                              "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}
                        k = f"{kind} | moved {lo}+ {unit} | {lbl} | {sub}"
                        res[k] = gr
                        print(f"   {k:78s} {n:4d}  {'covered' if kind == 'spreads' else 'won'} {gr['won']:.1%}  "
                              f"ROI {gr['roi']:+.1%}  last 3 + now {gr['last3_and_now']}  {gr['by']}")
        rep[lg] = res
    with open("results/early_overreaction.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
