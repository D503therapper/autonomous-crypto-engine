"""EARLY STUDY #1 - FOLLOW THE SHARP BOOK (10/1, the 20 early studies, one at a time). At the first FAIR number of the
week (posted after both teams' last games), the sharp books (LowVig / BetOnline, Circa, Bookmaker, the Betfair exchange
- the offshore market-makers) vs the regular books (DraftKings, FanDuel, MGM, Caesars...). When the sharp books rate a
side higher than the regular books, bet it at the regular books' softer price. No model, no learning - a fixed rule,
so no walk-forward needed; graded on WINS at the price bet, by season (the last 3 + this one are what count).
Saves results/early_sharp_books.json."""
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

SHARP = ("lowvig", "betonlineag", "circasports", "bookmaker", "betfair")
REC = ("draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "pointsbetus", "barstool", "fanatics", "unibet",
       "unibet_us", "sugarhouse", "wynnbet", "superbook", "twinspires", "foxbet", "espnbet", "hardrockbet")


def novig(h, a):
    ph, pa = 1 / ef._dec(h), 1 / ef._dec(a)
    return ph / (ph + pa)


def looks(lg, games):
    """{game id: [(days out, {book: (home, away)})]} - fair looks only, home first."""
    ready = ef.ready_at(games, lg)
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    for r in ef.snapshots(ef.SPORTS[lg]):
        t = ef._t(r["t"])
        days = (t - ef._t(r["snap"])).total_seconds() / 86400
        if not 1.5 <= days < 7.5:
            continue
        for d in (-1, 0, 1):
            hit = None
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
                g, flip = hit
                if ef.fair(ready, g["id"], g["start"], days):
                    bk = {b: ((v[1], v[0]) if flip else (v[0], v[1])) for b, v in r["b"].items()
                          if v and v[0] is not None and v[1] is not None}
                    out.setdefault(g["id"], []).append((days, bk))
                break
    return out


def rows(lg):
    games = sd.load_games(lg)
    lk = looks(lg, games)
    out = []
    for gid, ls in lk.items():
        g = games[gid]
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError):
            continue
        if hs == as_ or g.get("status") != "final":
            continue
        days, bk = max(ls, key=lambda x: x[0])                 # the first fair look
        sh = [novig(*bk[b]) for b in SHARP if b in bk]
        rc = {b: bk[b] for b in REC if b in bk}
        if not sh or len(rc) < 2:
            continue
        s_p = statistics.median(sh)
        r_p = statistics.median(novig(*v) for v in rc.values())
        y, m = int(g["start"][:4]), int(g["start"][5:7])
        season = y if m >= 7 else y - 1
        for side, i, won, sp, rp in (("home", 0, hs > as_, s_p, r_p), ("away", 1, as_ > hs, 1 - s_p, 1 - r_p)):
            best = max((v[i] for v in rc.values()), key=ef._dec)
            med = statistics.median(ef._dec(v[i]) for v in rc.values())
            out.append({"season": season, "won": won, "diff": sp - rp, "sharp_p": sp, "best": best, "med_dec": med,
                        "n_sharp": len(sh)})
    return out


def grade(sel, price):
    if not sel:
        return None
    dec = (lambda r: ef._dec(r["best"])) if price == "best" else (lambda r: r["med_dec"])
    by = {}
    for r in sel:
        by.setdefault(r["season"], []).append((dec(r) - 1) if r["won"] else -1)
    n = len(sel)
    roi = sum(x for v in by.values() for x in v) / n
    last = [x for s, v in by.items() if s >= 2023 for x in v]
    return {"n": n, "won": round(sum(r["won"] for r in sel) / n, 3), "said": round(sum(1 / dec(r) for r in sel) / n, 3),
            "roi": round(roi, 3), "last3_and_now": [len(last), round(sum(last) / len(last), 3) if last else None],
            "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        rs = rows(lg)
        print(f"\n===== {lg.upper()}: {len(rs)} sides with a sharp book AND 2+ regular books at the first fair look")
        res = {}
        for t in (0.01, 0.02, 0.03, 0.05):
            for kind, f in (("any side", lambda r: True), ("dogs (+100..+300)", lambda r: 100 <= r["best"] <= 300),
                            ("favorites (-150..-101)", lambda r: -150 <= r["best"] < 100)):
                sel = [r for r in rs if r["diff"] >= t and f(r) and -150 <= r["best"] <= 300]
                for price in ("best", "median"):
                    gr = grade(sel, price)
                    if not gr:
                        continue
                    k = f"sharps {t:.0%}+ higher | {kind} | {price} regular book"
                    res[k] = gr
                    print(f"   {k:62s} {gr['n']:4d}  won {gr['won']:.1%} (price {gr['said']:.1%})  ROI {gr['roi']:+.1%}  "
                          f"last 3 + now {gr['last3_and_now']}  {gr['by']}")
        rep[lg] = res
    with open("results/early_sharp_books.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
