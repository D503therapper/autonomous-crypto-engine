"""STUDY 4 - CONFERENCE STRENGTH EARLY + HOW LAST SEASON CARRIES OVER.
No conference field on file, so 'power' = a top-75 team by last season's closing rating (our own margin Elo, carried
over 2/3 - lib.annotate), 'mid-major' = every other Division I team (20+ games on file both seasons).
(a) November-to-Dec 15 games between a power team and a mid-major (the non-conference season): the mid-major dog /
    the power favorite at the moneyline close and ATS, by price band, opening week / games 1-5 vs the rest - and the
    same matchup type in the 2nd half of the season (Jan+, mostly conference tournaments/postseason - rare) as base.
(b) THE CARRYOVER: does last season's carried rating add anything to the closing price in each team's games 1-5 / 6-10
    / 11+? Fit on TRAIN: P(home) = sigmoid(logit(close no-vig) + b * (logit(Elo p) - logit(close no-vig))); b > 0 =
    the ratings know something the close doesn't. Then the held-out log loss with b vs the close alone. This is the
    test behind sports.early_trust (college hoops reads = the market until 10 games) and the 10/16 open question
    'college hoops Locks small the first 2 weeks'.
Train 2018-22, held out 2023 / 24 / 25 apart."""
import math
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load())]
# last season's final rating rank: the carried Elo at a team's first game of a season, ranked within that season
first_elo = {}
for r in rows:
    for side in ("home", "away"):
        if r["gn_" + side] == 1:
            first_elo[(r["season"], r[side])] = r["elo_" + side]
rank = {}
by_season = defaultdict(list)
for (s, t), e in first_elo.items():
    by_season[s].append((e, t))
for s, xs in by_season.items():
    for i, (e, t) in enumerate(sorted(xs, reverse=True)):
        rank[(s, t)] = i + 1

cells = defaultdict(lib.Cell)
fitd = defaultdict(list)
for r in rows:
    s = r["season"]
    if s < 2018 or not (r["d1_home"] and r["d1_away"] and r["prevd1_home"] and r["prevd1_away"]):
        continue
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except (TypeError, ValueError):
        continue
    if abs(mh) < 100 or abs(ma) < 100:
        continue
    pc = lib.novig(mh, ma)
    hw = r["hs"] > r["as_"]
    gmin = min(r["gn_home"], r["gn_away"])
    ph_fit = "games 1-5" if gmin <= 5 else ("games 6-10" if gmin <= 10 else "games 11+")
    pe = min(0.99, max(0.01, r["elo_p_home"]))
    pcc = min(0.99, max(0.01, pc))
    fitd[(ph_fit, "held" if s in lib.HELD else "train")].append((math.log(pcc / (1 - pcc)), math.log(pe / (1 - pe)), 1.0 if hw else 0.0))
    rh, ra = rank.get((s, r["home"]), 999), rank.get((s, r["away"]), 999)
    ph = "opening week" if r["day_in_season"] <= 7 else ("games 1-5" if max(r["gn_home"], r["gn_away"]) <= 5 else
                                                         ("Nov-Dec15" if (r["dt"].month == 11 or (r["dt"].month == 12 and r["dt"].day <= 15)) else None))
    if ph is None:
        continue
    pw = (rh <= 75) != (ra <= 75)
    if not pw:
        continue
    for side, odds, won, myrank in (("home", mh, hw, rh), ("away", ma, not hw, ra)):
        who = "POWER" if myrank <= 75 else "MID"
        site = "neutral" if str(r["neutral"]) == "1" else side
        sp = lib.fnum(r["spread_home"])
        if odds > 0 and odds <= 350:
            cells[f"{who} dog +100..+350 | {ph}"].add(s, lib.ml_profit(odds, won), won)
            cells[f"{who} dog +100..+350 {site} | {ph}"].add(s, lib.ml_profit(odds, won), won)
        elif -400 <= odds < 0:
            band = "-101..-150" if odds >= -150 else "-151..-400"
            cells[f"{who} fav {band} | {ph}"].add(s, lib.ml_profit(odds, won), won)
        if sp is not None:
            line = sp if side == "home" else -sp
            margin = (r["hs"] - r["as_"]) * (1 if side == "home" else -1)
            so = lib.fnum(r.get(f"spread_{side}_odds")) or -110.0
            if abs(so) < 100:
                so = -110.0
            cells[f"{who} ATS {'fav' if line < 0 else 'dog'} | {ph}"].add(s, lib.ats_profit(margin + line, so))

print(__doc__)
print("(a) power (last season's top 75) vs mid-major, non-conference season:")
for k in sorted(cells):
    print(cells[k].line(k))


def ll(data, b):
    t = 0.0
    for lm, le, y in data:
        p = 1 / (1 + math.exp(-(lm + b * (le - lm))))
        p = min(1 - 1e-9, max(1e-9, p))
        t -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return t / len(data)


print("\n(b) the carryover: b (train fit) and held-out log loss, close alone vs close + b * (Elo - close)")
for ph in ("games 1-5", "games 6-10", "games 11+"):
    tr = fitd[(ph, "train")]
    best = min((ll(tr, b / 100), b / 100) for b in range(-30, 61, 2))
    he = fitd[(ph, "held")]
    print(f"  {ph:10} train n={len(tr)} best b {best[1]:+.2f} (train ll {best[0]:.4f} vs close {ll(tr, 0):.4f}) | "
          f"held n={len(he)} ll close {ll(he, 0):.4f} vs with b {ll(he, best[1]):.4f} ({(ll(he, 0) - ll(he, best[1])) * 1000:+.2f} mnats)"
          f" | Elo alone held {ll(he, 1.0):.4f}")
