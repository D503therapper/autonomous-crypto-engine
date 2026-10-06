"""🥅 THE GOALIE-ROLES RE-CHECK (10/6): does an NHL dog that starts its #1 goalie beat its price when the favorite
doesn't start its #1 (and the reverse)? Blind: our box scores (data/sports/players/nhl.csv - the one goalie row a
team-game is the starter; the actual starter stands in for what a confirmed starter becomes), the closing price,
dogs +100..+220, season by season. "#1" = most starts in the team's previous N games THIS season (6+ held, a clear
leader). Run: python tools/goalie_roles_study.py [N=10] [top of the band=220]. Result (SPORTS_FINDINGS 10/6): every
dog -4.0%; the dog with its #1 vs a favorite without: +1.5% on 1,098, better 7 of 8 seasons (N=10); the reverse noise.
Read only - it changes nothing."""
import csv
import glob
import math
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
LO, HI = 100, int(sys.argv[2]) if len(sys.argv) > 2 else 220
MIN_HELD = 6


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{str(y + 1)[2:]}" if m >= 9 else f"{y - 1}-{str(y)[2:]}"


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def number_one(hist, team, ssn):
    h = [s for sn, s in hist[team] if sn == ssn][-N:]
    if len(h) < MIN_HELD:
        return None
    c = Counter(h).most_common(2)
    if len(c) > 1 and c[0][1] == c[1][1]:
        return None
    return c[0][0]


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/sports/players/nhl.csv"))))
    act = {(r["gid"], r["team"]): r["player"] for r in rows if r.get("role", "G") == "G"}
    games = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/nhl/*.csv"))):
        for g in csv.DictReader(open(f)):
            if g["status"] == "final" and g.get("stype") in ("2", "3") and g["home_score"] != "" and g["ml_home"] != "":
                games.append(g)
    games.sort(key=lambda g: g["start"])
    hist = defaultdict(list)                                   # team -> [(season, starter)] in order, before the game
    res = defaultdict(lambda: defaultdict(lambda: [0.0, 0, 0]))   # bucket -> season -> [pnl, n, wins]
    for g in games:
        ssn = season(g["start"])
        try:
            oh, oa = int(float(g["ml_home"])), int(float(g["ml_away"]))
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except ValueError:
            continue
        sh, sa = act.get((g["id"], g["home"])), act.get((g["id"], g["away"]))
        if sh and sa and hs != as_:
            for o, won, me, me_team, opp, opp_team in ((oh, hs > as_, sh, g["home"], sa, g["away"]),
                                                       (oa, as_ > hs, sa, g["away"], sh, g["home"])):
                if not LO <= o <= HI:
                    continue
                n1_me, n1_opp = number_one(hist, me_team, ssn), number_one(hist, opp_team, ssn)
                pnl = (dec(o) - 1) if won else -1.0
                buckets = ["all dogs"]
                if n1_me is not None and n1_opp is not None:
                    a, b = me == n1_me, opp == n1_opp
                    buckets += ["both known", {(True, False): "dog #1, fav not", (False, True): "fav #1, dog not",
                                               (True, True): "both #1", (False, False): "neither #1"}[(a, b)]]
                for bk in buckets:
                    r = res[bk][ssn]
                    r[0] += pnl
                    r[1] += 1
                    r[2] += won
        for team, who in ((g["home"], sh), (g["away"], sa)):
            if who:
                hist[team].append((ssn, who))
    seasons = sorted({s for b in res.values() for s in b})
    print(f"N={N} band +{LO}..+{HI}")
    for bk in ("all dogs", "both known", "dog #1, fav not", "fav #1, dog not", "both #1", "neither #1"):
        line, tot, better, cmp_ = [], [0.0, 0, 0], 0, 0
        for s in seasons:
            r, base = res[bk].get(s), res["all dogs"].get(s)
            if not r or r[1] < 20:
                continue
            roi, broi = r[0] / r[1] * 100, base[0] / base[1] * 100
            line.append(f"{s}: {roi:+.1f}% n={r[1]} (all {broi:+.1f}%)")
            tot = [tot[0] + r[0], tot[1] + r[1], tot[2] + r[2]]
            if bk != "all dogs":
                cmp_ += 1
                better += roi > broi
        roi = tot[0] / tot[1] * 100 if tot[1] else 0
        t = tot[0] / (1.45 * math.sqrt(tot[1])) if tot[1] else 0     # rough: a flat dog bet's pnl has sd ~1.45
        print(f"\n{bk}: ROI {roi:+.1f}% on {tot[1]} ({tot[2] / tot[1] * 100 if tot[1] else 0:.1f}% won), "
              f"better than all dogs {better} of {cmp_}, t~{t:.1f}")
        print("  " + " | ".join(line))


if __name__ == "__main__":
    main()
