"""EARLY STUDY #2 - THE MONEYLINE vs THE SPREAD, SAME BOOK, SAME MOMENT (10/1). At the Tuesday 6 PM ET snapshot (both
markets pulled then; only fair looks - after both teams' last games), a book's spread says how often a side wins (from
how often that spread really won in EARLIER seasons - our closing spreads and results, walk-forward) and its moneyline
says what it pays. When the moneyline pays more than the spread says it should, bet the moneyline at that book.
Graded on WINS at that price. Saves results/early_ml_vs_spread.json."""
import gzip
import json
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402


def snaps(lg, kind):
    path = os.path.join(sd.DATA, "odds_history", f"{ef.SPORTS[lg]}{'_spreads' if kind == 'spreads' else ''}.jsonl.gz")
    with gzip.open(path, "rt") as f:
        return [r for r in map(json.loads, f) if "b" in r]


def index(lg, games, kind):
    """{(game id, snapshot date): {book: values home-first}}."""
    ready = ef.ready_at(games, lg)
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    for r in snaps(lg, kind):
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
                if not ef.fair(ready, g["id"], g["start"], days):
                    break
                bk = {}
                for b, v in r["b"].items():
                    if kind == "spreads":
                        if v and v[0] is not None:
                            bk[b] = (-v[0] if flip else v[0])                     # the HOME spread
                    elif v and v[0] is not None and v[1] is not None:
                        bk[b] = ((v[1], v[0]) if flip else (v[0], v[1]))
                out[(g["id"], r["snap"][:10])] = bk
                break
    return out


def spread_table(games, upto):
    """{home spread (to the half point): home win %} from finished games BEFORE `upto` (a smoothed lookup)."""
    cnt = {}
    for g in games.values():
        if g.get("status") != "final" or not g.get("start") or g["start"] >= upto:
            continue
        try:
            sp, m = float(g["spread_home"]), float(g["home_score"]) - float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        if m == 0:
            continue
        k = round(sp * 2) / 2
        c = cnt.setdefault(k, [0, 0])
        c[0] += m > 0
        c[1] += 1

    def p(sp):
        k = round(sp * 2) / 2
        w = n = 0.0
        for d in (-1.0, -0.5, 0.0, 0.5, 1.0):                   # a little smoothing across the neighbors
            c = cnt.get(k + d)
            if c:
                wt = 1.0 if d == 0 else 0.5
                w += c[0] * wt
                n += c[1] * wt
        return (w / n) if n >= 40 else None
    return p


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        games = sd.load_games(lg)
        ml, spr = index(lg, games, "h2h"), index(lg, games, "spreads")
        both = [k for k in spr if k in ml]
        tables = {}
        rows = []
        for gid, day in both:
            g = games[gid]
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            if hs == as_ or g.get("status") != "final":
                continue
            y, mo = int(g["start"][:4]), int(g["start"][5:7])
            season = y if mo >= 7 else y - 1
            if season not in tables:
                tables[season] = spread_table(games, f"{season}-07-01")
            p_of = tables[season]
            for b, sp in spr[(gid, day)].items():
                if b not in ml[(gid, day)]:
                    continue
                h, a = ml[(gid, day)][b]
                ph = p_of(sp)
                if ph is None:
                    continue
                for side, o, p, won in (("home", h, ph, hs > as_), ("away", a, 1 - ph, as_ > hs)):
                    if not -150 <= o <= 400:
                        continue
                    rows.append({"season": season, "gid": gid, "book": b, "side": side, "odds": o, "p": p,
                                 "gap": p - 1 / ef._dec(o), "won": won})
        print(f"\n===== {lg.upper()}: {len(both)} game-looks with both markets, {len(rows)} book-sides")
        res = {}
        for t in (0.0, 0.02, 0.04, 0.06):
            for kind, f in (("dogs", lambda r: r["odds"] >= 100), ("favorites", lambda r: r["odds"] < 100)):
                best = {}
                for r in rows:                                   # one bet per game side: the book with the biggest gap
                    if r["gap"] >= t and f(r):
                        k = (r["gid"], r["side"])
                        if k not in best or r["gap"] > best[k]["gap"]:
                            best[k] = r
                sel = list(best.values())
                if not sel:
                    continue
                by = {}
                for r in sel:
                    by.setdefault(r["season"], []).append((ef._dec(r["odds"]) - 1) if r["won"] else -1)
                n = len(sel)
                roi = sum(x for v in by.values() for x in v) / n
                last = [x for s, v in by.items() if s >= 2023 for x in v]
                gr = {"n": n, "won": round(sum(r["won"] for r in sel) / n, 3), "roi": round(roi, 3),
                      "last3_and_now": [len(last), round(sum(last) / len(last), 3) if last else None],
                      "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}
                k = f"moneyline pays {t:.0%}+ more than its spread says | {kind}"
                res[k] = gr
                print(f"   {k:56s} {n:4d}  won {gr['won']:.1%}  ROI {gr['roi']:+.1%}  last 3 + now {gr['last3_and_now']}  {gr['by']}")
        rep[lg] = res
    with open("results/early_ml_vs_spread.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
