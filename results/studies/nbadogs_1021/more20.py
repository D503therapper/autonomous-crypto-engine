import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5")
from common import grade, TRAIN, BLIND, sd
import pandas as pd, numpy as np
P = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nbadogs/"
D = pd.read_pickle(P + "dogs.pkl")          # dog sides, +100..+300, with the first batch's features
games = sd.load_games("nba")
fin = sorted((g for g in games.values() if g.get("status") == "final" and str(g.get("stype")) == "2"
              and g.get("home_score") not in ("", None)), key=lambda g: g["start"])
def ls(g, k):
    try: return [float(v) for v in str(g.get(k) or "").split(",") if v.strip()]
    except ValueError: return []
# per-team history: previous game facts + rolling ATS / streaks / splits
prevf = {}
hist = collections.defaultdict(list)
for g in fin:
    for side in ("home", "away"):
        tm = g[side]; h = hist[tm]
        s = int(g["start"][:4]) if int(g["start"][5:7]) >= 9 else int(g["start"][:4]) - 1
        cur = [x for x in h if x["season"] == s]
        f = {}
        if cur:
            p = cur[-1]
            f.update(prev_ot=p["ot"], prev_blew=p["blew"], prev_comeback=p["cb"], prev_pts=p["pts"], prev_opp_pts=p["opp"],
                     prev_home=p["home"])
        res = [x["win"] for x in cur]
        st = 0
        for w in reversed(res):
            if w: st = st + 1 if st >= 0 else 1
            else: st = st - 1 if st <= 0 else -1
            if (st > 0) != w: break
        # streak: count same results from the end
        k = 0
        if res:
            last = res[-1]
            for w in reversed(res):
                if w != last: break
                k += 1
            f["streak"] = k if last else -k
        ats = [x["cover"] for x in cur if x["cover"] is not None][-5:]
        f["ats5"] = sum(ats) if len(ats) == 5 else None
        hw = [x["win"] for x in cur if x["home"]]; aw = [x["win"] for x in cur if not x["home"]]
        f["home_wp"] = sum(hw) / len(hw) if len(hw) >= 5 else None
        f["away_wp"] = sum(aw) / len(aw) if len(aw) >= 5 else None
        meet = [x for x in cur if x["opp_id"] == g["away" if side == "home" else "home"]]
        f["meet_n"] = len(meet); f["meet_w"] = sum(x["win"] for x in meet)
        f["g4in6"] = sum(1 for x in h if 0 < (pd.Timestamp(g["start"][:10]) - pd.Timestamp(x["start"][:10])).days <= 5) + 1
        prevf[(g["id"], tm)] = f
        # record this game
        hs, as_ = float(g["home_score"]), float(g["away_score"])
        me, op = (hs, as_) if side == "home" else (as_, hs)
        lh, la = ls(g, "ls_home"), ls(g, "ls_away")
        mel, opl = (lh, la) if side == "home" else (la, lh)
        half = (sum(mel[:2]) - sum(opl[:2])) if len(mel) >= 2 and len(opl) >= 2 else None
        q3 = (sum(mel[:3]) - sum(opl[:3])) if len(mel) >= 3 and len(opl) >= 3 else None
        try:
            spr = float(g["spread_home"]) * (1 if side == "home" else -1)
            cover = int(me - op + spr > 0) if me - op + spr != 0 else None
        except (TypeError, ValueError):
            cover = None
        hist[tm].append(dict(season=s, win=me > op, ot=len(mel) > 4, blew=bool(half is not None and half >= 10 and me < op),
                             cb=bool(q3 is not None and q3 <= -10 and me > op), pts=me, opp=op, home=side == "home",
                             cover=cover, opp_id=g["away" if side == "home" else "home"], start=g["start"]))
def add(prefix, team_col):
    for k in ("prev_ot", "prev_blew", "prev_comeback", "prev_pts", "prev_opp_pts", "prev_home", "streak", "ats5", "home_wp", "away_wp", "meet_n", "meet_w", "g4in6"):
        D[prefix + k] = [prevf.get((gid, t), {}).get(k) for gid, t in zip(D.gid, team_col)]
D["dog_id"] = np.where(D.side == "home", D.home, D.away); D["fav_id"] = np.where(D.side == "home", D.away, D.home)
add("d_", D.dog_id); add("f_", D.fav_id)
D["month"] = [int(d[5:7]) for d in D.date]
CELLS = 0
def L(m, label):
    global CELLS; CELLS += 1
    sub = D[pd.Series(m, index=D.index).fillna(False).astype(bool)]
    out = []
    for nm, seas in (("TRAIN", TRAIN), ("BLIND", BLIND)):
        x = sub[sub.season.isin(seas)]
        if len(x) == 0: out.append(f"{nm} n=0"); continue
        g = grade(x, nm); up = sum(1 for v in g["seasons"].values() if v[1] > 0)
        out.append(f"{nm} n={g['n']} win {g['win']}% vs {g['imp']}% ROI {g['roi']:+.1f}% ({up}/{len(g['seasons'])})")
    eb = sub[(sub.t_n_season < 10) & sub.season.isin(BLIND)]
    early = f"g1-10 blind n={len(eb)} ROI {grade(eb,'')['roi']:+.1f}%" if len(eb) else "g1-10 n=0"
    print(f"{label:50s} | " + " | ".join(out) + " | " + early)
print("== 21 blown lead last game"); L(D.d_prev_blew == True, "21a dog blew a 10+ halftime lead last game"); L(D.f_prev_blew == True, "21b fav blew a 10+ half lead last game")
print("== 22 comeback last game"); L(D.d_prev_comeback == True, "22a dog came back from 10+ down after 3 to win"); L(D.f_prev_comeback == True, "22b fav did")
print("== 23 overtime last game"); L(D.d_prev_ot == True, "23a dog played OT last game"); L(D.f_prev_ot == True, "23b fav played OT last game")
print("== 24 scoring last game"); L(D.d_prev_pts >= 130, "24a dog scored 130+ last game"); L(D.f_prev_pts <= 95, "24b fav scored <=95 last game"); L(D.d_prev_opp_pts >= 135, "24c dog allowed 135+ last game")
print("== 25 streaks"); L(D.d_streak <= -5, "25a dog lost 5+ straight"); L(D.d_streak >= 3, "25b dog won 3+ straight"); L(D.f_streak >= 7, "25c fav won 7+ straight"); L(D.f_streak <= -3, "25d fav lost 3+ straight")
print("== 26 ATS form"); L(D.d_ats5 >= 4, "26a dog covered 4+ of last 5"); L(D.d_ats5 <= 1, "26b dog covered 0-1 of last 5"); L(D.f_ats5 <= 1, "26c fav covered 0-1 of last 5"); L(D.f_ats5 >= 4, "26d fav covered 4+ of last 5")
print("== 27 home/road splits"); L((D.is_home == 0) & (D.d_away_wp >= 0.5), "27a road dog .500+ on the road"); L((D.is_home == 1) & (D.f_away_wp < 0.4), "27b home dog vs fav under .400 on the road")
L((D.is_home == 1) & (D.d_home_wp >= 0.6), "27c home dog .600+ at home")
print("== 28 season series"); L((D.d_meet_n >= 1) & (D.d_meet_w == D.d_meet_n), "28a dog won every meeting this season"); L((D.d_meet_n >= 2) & (D.d_meet_w == 0), "28b dog lost 2+ meetings, won none")
print("== 29 Elo gap vs price"); L((D.elo_pts <= -150) & (D.ml <= 150), "29a market much closer than Elo (Elo -150, ML <=+150)"); L((D.elo_pts >= -30) & (D.ml >= 200), "29b Elo near even, ML +200+")
print("== 30 4 in 6"); L(D.f_g4in6 >= 4, "30a fav 4th game in 6 nights"); L(D.d_g4in6 >= 4, "30b dog 4th in 6")
print("== 31 rest gap"); L((D.t_rest - D.o_rest) >= 2, "31a dog 2+ more days rest"); L((D.o_rest - D.t_rest) >= 2, "31b fav 2+ more days rest")
print("== 32 b2b second leg on road after home"); L((D.o_b2b == 1) & (D.is_home == 1) & (D.f_prev_home == True), "32 fav b2b: home last night, at us tonight")
print("== 33 month");
for mo in (10, 11, 12, 1, 2, 3, 4): L(D.month == mo, f"33 month {mo}")
print("== 34 near pick'em"); L((D.ml <= 115) & (D.is_home == 1), "34a +100..+115 home"); L((D.ml <= 115) & (D.is_home == 0), "34b +100..+115 road")
print("== 35 dog's last-game total points"); L((D.d_prev_pts + D.d_prev_opp_pts) >= 250, "35 dog's last game 250+ combined")
print("== 36 fav scored big + won big (letdown 2)"); L((D.f_prev_pts >= 130) & (D.o_last_margin >= 15), "36 fav scored 130+ and won by 15+")
print("== 37 dog blowout loss AND rested"); L((D.t_last_margin <= -15) & (D.t_rest >= 2), "37 dog lost by 15+, 2+ days rest")
print("== 38 young season record"); L((D.t_n_season.between(5, 15)) & (D.t_wp_season >= 0.6), "38a dog .600+ in games 6-16"); L((D.t_n_season.between(5, 15)) & (D.o_wp_season <= 0.4), "38b fav under .400 in games 6-16")
print("== 39 last year's record"); L((D.t_n_season < 15) & (D.t_wp_last >= 0.55), "39a early, dog was .550+ last year"); L((D.t_n_season < 15) & (D.o_wp_last <= 0.45), "39b early, fav was under .450 last year")
print("== 40 big spread, home"); L((D.is_home == 1) & (D.ml >= 200), "40 home dog +200..+300")
print("cells tried", CELLS, "- expected false positives ~", round(CELLS * .05, 1))
D.to_pickle(P + "dogs2.pkl")
