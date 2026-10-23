"""🌱 YOUNG RISING PLAYERS (the owner, 10/23: "Edgecombe's a beast ... these are the things the engine needs to know"):
does weighting THIS season's early games more heavily for men in their first three seasons (top-10 picks / last
season's All-Rookie first team) read the early season better than the engine's one-size prior (last season's value
worth 20 games for everybody - sports_nba_roster.G_PRIOR)?

Walk-forward, seasons 2022-23 .. 2025-26: a player's rate tonight = (G x last season's plus-minus a minute + n x his
rate over his games so far this season) / (G + n), G = 20 for everyone (the engine) vs G_young for the young men (5 /
10 / 40) vs G = 5 for everybody; a rookie / man with no last season starts at the replacement rate. Team strength
tonight = the men who played, at their usual minutes, scaled to 240. Win chance = a logistic on the strength gap
fitted on the season BEFORE (games 6-20). Scored by log loss on games 6-20 (both teams) and the owner's dog cut.

    python results/studies/nba_stars_1023/young.py > results/studies/nba_stars_1023/young.out
"""
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
import sports_data as sd                  # noqa: E402
import sports_roster as sr                # noqa: E402
import sports_nba_roster as nr            # noqa: E402
import sports_nba_stars as ns             # noqa: E402

SEASONS = (2021, 2022, 2023, 2024, 2025)
LO, HI = 5, 20                            # team games 6-20 (both teams)


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 9 else y - 1


def young(name, season, data):
    """A top-10 pick in his first three seasons, or last season's / the season before's All-Rookie first team."""
    k = ns._nm(name)
    pk = data["picks"].get(k)
    if pk and 0 <= season - pk[0] < 3:
        return True
    ry = data["rookie"].get(k)
    return ry is not None and 0 <= season - ry < 2


def main():
    data = ns.load()
    games = sd.load_games("nba")
    rows = sr.load("nba")
    by_season = defaultdict(list)
    for r in rows:
        by_season[season_of(r["start"])].append(r)
    fin = sorted((g for g in games.values() if g.get("status") == "final" and g.get("stype") == "2"
                  and g.get("ml_home") and g.get("ml_away")), key=lambda g: g["start"])
    variants = {"engine G=20 all": (20, 20), "young G=5": (20, 5), "young G=10": (20, 10), "young G=40 (trust last season MORE)": (20, 40),
                "everyone G=5": (5, 5), "young at this season ONLY (G=0)": (20, 0)}
    results = {v: defaultdict(list) for v in variants}   # variant -> season -> [(gap, home_win, mp)]
    for s in SEASONS:
        last = nr.player_values(by_season.get(s - 1, []))
        if not by_season.get(s - 1):
            continue
        now_rows = sorted(by_season.get(s, []), key=lambda r: (r["start"], r["gid"]))
        rec = defaultdict(list)                          # pid -> [(minutes, pm)] so far this season
        by_gid = defaultdict(lambda: defaultdict(list))
        for r in now_rows:
            by_gid[r["gid"]][r["team"]].append(r)
        n_games = defaultdict(int)
        for g in (x for x in fin if season_of(x["start"]) == s):
            box = by_gid.get(g["id"])
            if not box:
                continue
            gh, ga = n_games[g["home"]], n_games[g["away"]]
            if LO <= gh < HI and LO <= ga < HI:
                mp = None
                try:
                    a, b = int(g["ml_home"]), int(g["ml_away"])
                    da, db = 1 + (a / 100 if a > 0 else 100 / -a), 1 + (b / 100 if b > 0 else 100 / -b)
                    mp = (1 / da) / (1 / da + 1 / db)
                except (ValueError, ZeroDivisionError):
                    pass
                hw = 1.0 if int(g["home_score"]) > int(g["away_score"]) else 0.0
                for v, (g_all, g_young) in variants.items():
                    st = {}
                    for side in ("home", "away"):
                        tot, mins = 0.0, 0.0
                        for r in box[g[side]]:
                            p = last["players"].get(r["pid"])
                            base = p["rate"] if p and p.get("rate") is not None else last["repl"]
                            usual = (p["mpg"] if p else None) or 12.0
                            rr = rec.get(r["pid"], [])
                            n = len(rr)
                            G = g_young if young(r["player"], s, data) else g_all
                            if n and sum(m for m, _ in rr) >= 30:
                                rrate = sum(pm for _, pm in rr) / sum(m for m, _ in rr)
                                usual = max(usual, sum(m for m, _ in rr) / n) if young(r["player"], s, data) else usual
                                rate = (G * base + n * rrate) / (G + n) if (G + n) else rrate
                            else:
                                rate = base
                            tot += usual * (rate - last["repl"])
                            mins += usual
                        st[side] = tot * 240.0 / mins if mins else 0.0
                    results[v][s].append((st["home"] - st["away"], hw, mp, g))
            for side in ("home", "away"):
                for r in box[g[side]]:
                    try:
                        stt = json.loads(r["stats"])
                        m, pm = float(stt.get("minutes") or 0), float(str(stt.get("plusMinus") or "0").replace("+", ""))
                    except (ValueError, TypeError):
                        continue
                    if m > 0:
                        rec[r["pid"]].append((m, pm))
                n_games[g[side]] += 1
    print("log loss, games 6-20 (both teams), each season's logistic (a + b x strength gap) fitted on the season before")
    for v in variants:
        line = []
        for s in SEASONS[1:]:
            tr, te = results[v].get(s - 1), results[v].get(s)
            if not tr or not te:
                continue
            a, b = fit(tr)
            ll = -sum(math.log(max(1e-6, (sig(a + b * x[0]) if x[1] else 1 - sig(a + b * x[0])))) for x in te) / len(te)
            line.append(f"{s}: {ll:.4f} (n {len(te)})")
        print(f"  {v:38s} " + " | ".join(line))
    base = results["engine G=20 all"]
    print("  the market                             " + " | ".join(
        f"{s}: {-sum(math.log(max(1e-6, x[2] if x[1] else 1 - x[2])) for x in base[s] if x[2]) / len([x for x in base[s] if x[2]]):.4f}"
        for s in SEASONS[1:] if base.get(s)))
    print("\nthe owner's cut: DOGS +100..+350 (close) in games 6-20 that the talent read likes 5+ points over the price, flat 1u")
    for v in variants:
        out = []
        for s in SEASONS[1:]:
            tr, te = results[v].get(s - 1), results[v].get(s)
            if not tr or not te:
                continue
            a, b = fit(tr)
            n = w = 0
            u = 0.0
            for gap, hw, mp, g in te:
                if mp is None:
                    continue
                for side, p_side, price, won in (("home", sig(a + b * gap), int(g["ml_home"]), hw == 1.0),
                                                 ("away", 1 - sig(a + b * gap), int(g["ml_away"]), hw == 0.0)):
                    mps = mp if side == "home" else 1 - mp
                    if 100 <= price <= 350 and p_side - mps >= 0.05:
                        n += 1
                        w += won
                        u += (price / 100) if won else -1
            out.append(f"{s}: n {n} {w}-{n - w} {100 * u / n if n else 0:+.0f}%")
        print(f"  {v:38s} " + " | ".join(out))


def sig(z):
    return 1 / (1 + math.exp(-z))


def fit(xs, steps=300, lr=0.5):
    """A two-parameter logistic by gradient steps (standardized gap)."""
    sd_ = (sum(x[0] ** 2 for x in xs) / len(xs)) ** 0.5 or 1.0
    a, b = 0.0, 0.0
    for _ in range(steps):
        ga = gb = 0.0
        for gap, hw, _, _ in xs:
            e = sig(a + b * gap / sd_) - hw
            ga += e
            gb += e * gap / sd_
        a -= lr * ga / len(xs)
        b -= lr * gb / len(xs)
    return a, b / sd_


if __name__ == "__main__":
    main()
