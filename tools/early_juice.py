"""EARLY STUDY #4 - THE JUICE ON THE TUESDAY SPREAD (10/1). Instead of moving the number, a book shades the juice (-120
on one side, +100 on the other). Does the side the juice favors cover the Tuesday number, paying that juice? And does
the number move its way by kickoff? Fair looks only (after both teams' last games), the MIDDLE book's price (the owner,
10/1: no line shopping - one book). Graded on covers at the price paid. Saves results/early_juice.json."""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import early_ml_vs_spread as mvs    # noqa: E402
import sports_data as sd            # noqa: E402


def spread_looks(lg, games):
    """{game id: (home spread, home price, away price)} - the first fair Tuesday look, the median book (books on the
    median number only, so the juice is for the same number)."""
    import gzip
    from datetime import timedelta
    ready = ef.ready_at(games, lg)
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    path = os.path.join(sd.DATA, "odds_history", f"{ef.SPORTS[lg]}_spreads.jsonl.gz")
    with gzip.open(path, "rt") as f:
        for r in map(json.loads, f):
            if "b" not in r:
                continue
            t = ef._t(r["t"])
            days = (t - ef._t(r["snap"])).total_seconds() / 86400
            if not 1.5 <= days < 7.5:
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
            if not ef.fair(ready, g["id"], g["start"], days):
                continue
            vals = []
            for v in r["b"].values():
                if not v or None in v[:4]:
                    continue
                hp, hpr, ap, apr = v[:4]
                vals.append((-ap, apr, hpr) if flip else (hp, hpr, apr))    # (home spread, home price, away price)
            if len(vals) < 2:
                continue
            med = statistics.median(x[0] for x in vals)
            on = [x for x in vals if x[0] == med]
            if not on:
                continue
            hpr = statistics.median(ef._dec(x[1]) for x in on)
            apr = statistics.median(ef._dec(x[2]) for x in on)
            if g["id"] not in out or days > out[g["id"]][0]:
                out[g["id"]] = (days, med, hpr, apr)
    return out


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        games = sd.load_games(lg)
        lk = spread_looks(lg, games)
        rows = []
        for gid, (days, sp, hd, ad) in lk.items():
            g = games[gid]
            try:
                m = float(g["home_score"]) - float(g["away_score"])
                close = float(g["spread_home"])
            except (KeyError, ValueError, TypeError):
                continue
            if g.get("status") != "final":
                continue
            y, mo = int(g["start"][:4]), int(g["start"][5:7])
            season = y if mo >= 7 else y - 1
            for side, sg, dec, odec in (("home", 1, hd, ad), ("away", -1, ad, hd)):
                ln, mg = sp * sg, m * sg
                if mg + ln == 0:
                    continue
                shade = (1 / dec) - (1 / odec)              # + = this side carries the heavier juice (books lean it)
                rows.append({"season": season, "shade": shade, "dec": dec, "cover": mg + ln > 0,
                             "moved": (sp - close) * sg})   # + = the number moved toward this side by kickoff
        print(f"\n===== {lg.upper()}: {len(rows)} sides with a fair Tuesday spread")
        res = {}
        for t in (0.01, 0.02, 0.03, 0.05):
            for lbl, f in (("the side the JUICE favors", lambda r, t=t: r["shade"] >= t),
                           ("the cheap side (fading the juice)", lambda r, t=t: r["shade"] <= -t)):
                sel = [r for r in rows if f(r)]
                if not sel:
                    continue
                by = {}
                for r in sel:
                    by.setdefault(r["season"], []).append((r["dec"] - 1) if r["cover"] else -1)
                n = len(sel)
                last = [x for s, v in by.items() if s >= 2023 for x in v]
                gr = {"n": n, "covered": round(sum(r["cover"] for r in sel) / n, 3),
                      "roi": round(sum(x for v in by.values() for x in v) / n, 3),
                      "moved_its_way": round(sum(r["moved"] > 0 for r in sel) / n, 3),
                      "last3_and_now": [len(last), round(sum(last) / len(last), 3) if last else None],
                      "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}
                k = f"juice {t:.0%}+ | {lbl}"
                res[k] = gr
                print(f"   {k:48s} {n:4d}  covered {gr['covered']:.1%}  ROI {gr['roi']:+.1%} (at that juice)  "
                      f"number moved its way {gr['moved_its_way']:.0%}  last 3 + now {gr['last3_and_now']}  {gr['by']}")
        rep[lg] = res
    with open("results/early_juice.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
