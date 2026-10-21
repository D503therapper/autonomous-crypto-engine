import sys, pickle, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5")
from common import load, sides, grade, TRAIN, BLIND, sd
import pandas as pd, numpy as np
rows = load()
games = sd.load_games("nba")
for r in rows:
    g = games.get(r["gid"], {})
    try: r["total"] = float(g.get("total") or "nan")
    except ValueError: r["total"] = float("nan")
# last meeting between the two teams
last = {}
for r in sorted(rows, key=lambda r: r["start"]):
    k = frozenset((r["home"], r["away"]))
    r["prev_meet"] = last.get(k)
    last[k] = (r["season"], r["home"], r["hs"] - r["as_"], r["date"])
S = pd.DataFrame(sides(rows))
bf, _ = pickle.load(open("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5/box.pkl", "rb"))
for c in ("top5_out", "top5_back", "top2_out", "top2_back", "star_out", "out_minutes", "n_box"):
    S["t_" + c] = [bf.get((g, (h if s == "home" else a)), {}).get(c) for g, h, a, s in zip(S.gid, S.home, S.away, S.side)]
    S["o_" + c] = [bf.get((g, (a if s == "home" else h)), {}).get(c) for g, h, a, s in zip(S.gid, S.home, S.away, S.side)]
def prev_meet_margin(r):
    pm = r["prev_meet"]
    if not pm or pm[0] != r["season"]: return None
    m = pm[2] if pm[1] == (r["home"] if r["side"] == "home" else r["away"]) else -pm[2]
    return m
S["pm_margin"] = S.apply(prev_meet_margin, axis=1)
S["pm_days"] = [ (pd.Timestamp(d) - pd.Timestamp(pm[3])).days if pm else None for d, pm in zip(S.date, S.prev_meet)]
S["opp_ml"] = [ (r_a if s=="home" else r_h) for r_h, r_a, s in zip(S.ml_home, S.ml_away, S.side)]
S["open_mp"] = [ (sd.no_vig(int(oh), int(oa)) if s=="home" else 1-sd.no_vig(int(oh), int(oa))) if oh==oh and oa==oa and oh and oa else None
                 for oh, oa, s in zip(S.ml_home_open, S.ml_away_open, S.side)]
S["spr"] = [ (sp if s=="home" else -sp) if sp==sp and sp is not None else None for sp, s in zip(S.spread_home, S.side)]
S["hour"] = [int(st[11:13]) for st in S.start]
S["dow"] = [pd.Timestamp(d).dayofweek for d in S.date]
D = S[(S.ml >= 100) & (S.ml <= 300)].copy()
D["band"] = pd.cut(D.ml, [99, 130, 160, 200, 300])
print("dogs", len(D), "raw win", round(D.win.mean()*100,1), "implied", round(D.mp.mean()*100,1))
# band-adjusted: win minus implied
def line(m, label):
    sub = D[m.fillna(False) if hasattr(m, "fillna") else m]
    out = []
    for nm, seas in (("TRAIN", TRAIN), ("BLIND", BLIND)):
        x = sub[sub.season.isin(seas)]
        if len(x) == 0: out.append(f"{nm} n=0"); continue
        g = grade(x, nm)
        up = sum(1 for v in g["seasons"].values() if v[1] > 0)
        out.append(f"{nm} n={g['n']} win {g['win']}% vs {g['imp']}% ROI {g['roi']:+.1f}% ({up}/{len(g['seasons'])} up)")
    e = sub[sub.t_n_season < 10]
    eb = e[e.season.isin(BLIND)]
    ge = grade(eb, "") if len(eb) else None
    early = f"g1-10 blind n={len(eb)} win {ge['win']}% vs {ge['imp']}% ROI {ge['roi']:+.1f}%" if ge else "g1-10 n=0"
    print(f"{label:52s} | " + " | ".join(out) + " | " + early)
CELLS = 0
def L(m, label):
    global CELLS; CELLS += 1; line(m, label)
print("== baseline"); line(D.win >= 0, "all dogs +100..+300")
for b, x in D.groupby("band", observed=True): line(D.band == b, f"  band {b}")
print("== 1 line move"); mv = D.mp - D.open_mp
L(mv >= 0.02, "1a money came to the dog (+2 pts open->close)"); L(mv >= 0.04, "1b +4 pts"); L(mv <= -0.02, "1c money ran away (-2)"); L(mv <= -0.04, "1d -4")
print("== 2 off a blowout loss"); L(D.t_last_margin <= -15, "2a dog lost last by 15+"); L(D.t_last_margin <= -25, "2b by 25+"); L(D.t_last_margin >= 15, "2c dog WON last by 15+")
print("== 3 rest"); L((D.t_rest >= 2) & (D.o_b2b == 1), "3a rested dog vs fav on b2b"); L((D.t_b2b == 1) & (D.o_rest >= 2), "3b dog on b2b vs rested fav"); L(D.o_n4 >= 3, "3c fav 3rd game in 4 nights")
print("== 4 home dogs by stage")
for lo, hi in ((0, 5), (5, 10), (10, 30), (30, 60), (60, 90)): L((D.is_home == 1) & (D.t_n_season >= lo) & (D.t_n_season < hi), f"4 home dog games {lo+1}-{hi}")
L(D.is_home == 0, "4z road dogs (all)")
print("== 5 form"); L((D.t_m5 - D.o_m5) >= 5, "5a dog's last-5 margin 5+ better than fav's"); L(D.o_m5 < 0, "5b fav cold (last 5 margin < 0)"); L(D.t_m5 >= 5, "5c dog hot (last 5 +5)")
print("== 6 unlucky record"); L((D.t_n_season >= 10) & (D.t_m10 > 0) & (D.t_wp_season < 0.5), "6a dog under .500 but +margin last 10"); L((D.t_n_season >= 15) & (D.o_wp_season - D.t_wp_season >= .2) & (D.o_m10 - D.t_m10 < 2), "6b record gap big, margin gap small")
print("== 7 fav letdown"); L(D.o_last_margin >= 20, "7a fav won last by 20+"); L(D.o_last_margin >= 30, "7b by 30+")
print("== 8 revenge"); L(D.pm_margin <= -15, "8a dog lost last meeting (this season) by 15+"); L((D.pm_margin < 0) & (D.pm_days <= 3), "8b same-opp quick rematch, dog lost game 1")
L((D.pm_margin > 0) & (D.pm_days <= 3), "8c quick rematch, dog WON game 1")
print("== 9/10 stars (box 2021+)"); L(D.o_top5_out >= 1, "9a fav missing a top-5 man"); L(D.o_top2_out >= 1, "9b fav missing a top-2 man"); L(D.t_top2_back >= 1, "9c dog's top-2 man back"); L(D.o_top5_back >= 1, "10 fav's top-5 man returning (dog side)"); L(D.t_top5_out >= 1, "9d dog missing a top-5 man")
print("== 11 travel"); L(D.o_trip_game >= 4, "11a fav on road game 4+"); L((D.is_home == 1) & (D.t_home_after >= 4), "11b dog home after 4+ trip"); L(D.o_tz_cross >= 2, "11c fav crossed 2+ zones"); L((D.is_home==0)&(D.t_tz_cross >= 2), "11d dog crossed 2+ zones")
print("== 12 totals"); tq = D.total
L(tq >= 235, "12a high total 235+"); L(tq <= 215, "12b low total <=215")
print("== 13 threes: no 3PT in our box scores (minutes/points/reb/ast/+- only) - skipped")
print("== 14 spread vs ML")
z = D[D.spr.notna() & D.season.isin(TRAIN)]; fit = np.polyfit(z.spr, z.mp, 2)
res = D.mp - np.polyval(fit, D.spr.fillna(0)); res[D.spr.isna()] = np.nan
L(res <= -0.015, "14a dog ML long for its spread (1.5+ pts)"); L(res >= 0.015, "14b ML short for spread")
print("== 15 division-ish/repeat"); L(D.pm_days <= 10, "15 met within 10 days")
print("== 16 late season"); late = D.t_n_season >= 66
L(late & (D.o_wp_season >= 0.65), "16a late, fav 65%+ (rest risk)"); L(late & (D.t_wp_season.between(0.45, 0.6)), "16b late, playoff-push dog"); L(late & (D.t_wp_season < 0.35), "16c late, tanking dog")
print("== 17 depth"); L((D.o_out_minutes.fillna(0) - D.t_out_minutes.fillna(0)) >= 30, "17 fav missing 30+ more rotation minutes")
print("== 18 elo read"); L((D.p_elo - D.mp) >= 0.05, "18a elo has dog 5+ over market"); L((D.p_elo - D.mp) >= 0.10, "18b 10+"); L((D.p_elo - D.mp) <= -0.05, "18c elo under market 5+")
print("== 19 calendar"); L(D.hour < 22, "19a early tip (before 5 ET)"); L(D.dow.isin([5, 6]), "19b weekend"); L(D.date.str[5:] == "12-25", "19c Christmas")
print("cells tried", CELLS, "- expected false positives at p<.05 ~", round(CELLS*.05, 1))
D.to_pickle("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nbadogs/dogs.pkl")
