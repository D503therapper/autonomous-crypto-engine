"""S2 (asked) - THE ALTITUDE WEIGHT AT A NEUTRAL SITE. The read's "alt" input is thin_air(visitors) - thin_air(home):
each team's climb above ITS OWN building (km), counted only in real thin air (1,000 m+). In a true home game that is
"the visitors came up to our altitude". At a neutral site BOTH teams climbed - what is left is the gap between two
home elevations (Mexico City 11/22: the 49ers live at sea level, the Vikings 250 m up - 'alt' = 0.25 for the Vikings).
Does that gap say anything? Every final on file, the live ratings replayed (sm.replay with today's k / hfa):
 (1) the weight the fit gives 'alt' in TRUE HOME games vs at NEUTRAL sites (a one-input logistic on top of the ratings,
     and on top of the closing price); (2) the side the gap favors at a neutral site in thin air, against the close."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
import sports_data as sd
import sports_model as sm

lines = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def fit1(rows):
    """b in P(home) = sigmoid(offset + b * x), Newton, a little ridge; rows = [(offset, x, y)] -> (b, se)."""
    b = 0.0
    for _ in range(40):
        g, hh = 0.01 * b, 0.01
        for off, x, y in rows:
            p = sm.sigmoid(off + b * x)
            g += (p - y) * x
            hh += p * (1 - p) * x * x
        b -= g / hh
    return b, 1 / math.sqrt(hh)


say(__doc__)
model = json.load(open(os.path.join(sd.DATA, "model.json")))
tot = {}
for lg in ("nfl", "ncaaf", "ncaab", "nba"):
    games = sd.load_games(lg)
    p = model["params"].get(lg) or sm.default_params(lg)
    w = dict(zip(["icpt"] + sm.FEATURES, p["w"]))
    fin = sm.finals(games, lg)
    e = sm.Elo(p["k"], p["hfa"], lg)
    if lg == "ncaab":
        e.d1 = sm.ncaab_d1(fin)
    rows, lives = [], {}
    for g in fin:                                        # sm.replay, keeping each team's home elevation BEFORE the game
        lives[g["id"]] = (e.home_elev.get(g["home"]), e.home_elev.get(g["away"]))
        row = (g, *e.update(g))
        if not e.non_d1(g):
            rows.append(row)
    say(f"\n===== {lg}: {len(rows)} finals; the live fit's weight on 'alt' {w['alt']:+.3f} per km "
        f"(a 1 km gap = {abs(w['alt']) * 25:.1f} points of win chance near a coin flip)")
    home, neut = [], []
    cells = {}
    for g, f, res, margin in rows:
        if res == 0.5 or not f["alt"]:
            continue
        neutral = str(g.get("neutral")) == "1"
        mp = sm.market_p(g)
        rec = (sm.logit(min(0.99, max(0.01, f["p_elo"]))), f["alt"], res, sm.logit(mp) if mp else None, g, f)
        (neut if neutral else home).append(rec)
    for name, rs in (("TRUE HOME games in thin air (the visitors climbed)", home), ("NEUTRAL sites in thin air (both climbed)", neut)):
        if len(rs) < 5:
            say(f"  {name}: {len(rs)} games - too few")
            continue
        b, se = fit1([(a, x, y) for a, x, y, *_ in rs])
        pr = [(m, x, y) for a, x, y, m, *_ in rs if m is not None]
        bm, sem = fit1(pr) if len(pr) >= 5 else (float("nan"), float("nan"))
        say(f"  {name}: {len(rs)} games, mean |alt| {sum(abs(r[1]) for r in rs) / len(rs):.2f} km; "
            f"on top of the RATINGS b = {b:+.3f} (se {se:.3f}, z {b / se:+.2f}); "
            f"on top of the CLOSE b = {bm:+.3f} (se {sem:.3f}, z {bm / sem:+.2f}) on {len(pr)} priced")
    # (2) the side the gap favors at a neutral site, against the close
    def high(g):
        return sum(1 for v in lives[g["id"]] if v is not None and v >= sm.THIN_AIR_M)
    for name, rs in (("NEUTRAL, ONE team lives in thin air (1,000 m+) and the other doesn't", [r for r in neut if high(r[4]) == 1]),
                     ("NEUTRAL, NEITHER team lives in thin air (two lowland teams)", [r for r in neut if high(r[4]) == 0])):
        if len(rs) >= 5:
            b, se = fit1([(a, x, y) for a, x, y, *_ in rs])
            pr = [(m, x, y) for a, x, y, m, *_ in rs if m is not None]
            bm, sem = fit1(pr) if len(pr) >= 5 else (float("nan"), float("nan"))
            say(f"  {name}: {len(rs)} games, mean |alt| {sum(abs(r[1]) for r in rs) / len(rs):.2f} km; on top of the RATINGS "
                f"b = {b:+.3f} (se {se:.3f}, z {b / se:+.2f}); on top of the CLOSE b = {bm:+.3f} (se {sem:.3f}, z {bm / sem:+.2f}) on {len(pr)}")
        else:
            say(f"  {name}: {len(rs)} games - too few")
    for kind, gap_min in (("any", 0.0), ("any", 0.1), ("any", 0.3), ("one high", 0.0), ("lowland", 0.0), ("lowland", 0.1)):
        ml, ats, won, exp, n = [], [], 0, 0.0, 0
        for a, x, y, m, g, f in neut:
            if abs(x) < gap_min or abs(x) == 0:
                continue
            if (kind == "one high" and high(g) != 1) or (kind == "lowland" and high(g) != 0):
                continue
            side = "home" if x > 0 else "away"               # + = the visitors are the ones in thin air -> home favored
            hw = y == 1.0
            n += 1
            won += hw == (side == "home")
            pe = f["p_elo"] if side == "home" else 1 - f["p_elo"]
            exp += pe
            mh, ma = sm._num(g.get("ml_home")), sm._num(g.get("ml_away"))
            if mh and ma:
                o = mh if side == "home" else ma
                ml.append((lib.season(g["start"]), lib.profit(hw == (side == "home"), lib.dec(o))))
            sp = sm._num(g.get("spread_home"))
            if sp is not None:
                mgn = float(g["home_score"]) - float(g["away_score"]) + sp
                if mgn:
                    cov = (mgn > 0) == (side == "home")
                    ats.append((lib.season(g["start"]), lib.profit(cov, lib.dec(-110))))
        if n:
            s1, s2 = lib.stats([p_ for _, p_ in ml]), lib.stats([p_ for _, p_ in ats])
            say(f"  neutral, thin air, [{kind}] home-elevation gap {gap_min:.1f} km+: the side the weight favors won {won} of {n} "
                f"(the ratings alone expect {exp:.1f}); moneyline {('%+.1f%% on %d' % (s1['roi'] * 100, s1['n'])) if s1 else '-'}; "
                f"ATS {('%+.1f%% on %d (covered %.0f%%)' % (s2['roi'] * 100, s2['n'], s2['win'] * 100)) if s2 else '-'}")
            tot.setdefault((kind, gap_min), []).append((won, n, exp, [p_ for _, p_ in ml], [p_ for _, p_ in ats]))
    # who these games are
    if neut:
        venues = {}
        for a, x, y, m, g, f in neut:
            k = (g.get("city") or g.get("venue") or "?", g.get("elev"))
            venues[k] = venues.get(k, 0) + 1
        say("  where: " + "; ".join(f"{c} ({el} m) x{n}" for (c, el), n in sorted(venues.items(), key=lambda kv: -kv[1])[:14]))
    # the game that raised it
    for gid, g in games.items():
        if lg == "nfl" and g.get("start", "")[:10] in ("2026-11-22", "2026-11-23") and str(g.get("neutral")) == "1":
            f = e.features(g)
            say(f"  THE MEXICO CITY GAME ({g.get('away_name')} @ {g.get('home_name')}, {g.get('elev')} m): alt {f['alt']:+.3f} km "
                f"(home elevations: {g.get('home_name')} {e.home_elev.get(g['home'], 0):.0f} m, {g.get('away_name')} "
                f"{e.home_elev.get(g['away'], 0):.0f} m) -> {w['alt'] * f['alt']:+.3f} on the own read's logit = "
                f"{(sm.sigmoid(sm.logit(f['p_elo']) + w['alt'] * f['alt']) - f['p_elo']) * 100:+.1f} points of win chance for the home side; "
                f"travel {f['travel']:+.2f} x {w['travel']:+.3f}, intl {f['intl']:+.0f} x {w['intl']:+.3f}")
say("\nEVERY LEAGUE TOGETHER, the side the weight favors at a neutral site in thin air:")
for (kind, gap_min), v in sorted(tot.items()):
    won, n, exp = sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)
    ml = [p_ for x in v for p_ in x[3]]
    ats = [p_ for x in v for p_ in x[4]]
    s1, s2 = lib.stats(ml), lib.stats(ats)
    if not s1 or not s2:
        continue
    say(f"  [{kind}] gap {gap_min:.1f} km+: won {won} of {n} (ratings expect {exp:.1f}); ML {s1['roi'] * 100:+.1f}% on {s1['n']} (z {s1['z']:+.2f}); "
        f"ATS {s2['roi'] * 100:+.1f}% on {s2['n']} (z {s2['z']:+.2f}, covered {s2['win'] * 100:.0f}%)")
open(os.path.join(lib.OUT, "s2_neutral_altitude_out.txt"), "w").write("\n".join(lines) + "\n")
