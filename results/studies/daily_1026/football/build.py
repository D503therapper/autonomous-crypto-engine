"""10/26 football studies - per-side rows, everything known BEFORE kickoff (walk-forward Elo, last game, record, the
team's NEXT scheduled opponent and that opponent's rating as of today, the team's last home game of the regular
season, open/close moneylines, closing spread). Read-only on the worktree; the row cache goes to the scratchpad."""
import os, sys, pickle
from collections import defaultdict
from datetime import datetime, timezone
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, WT); os.chdir(WT)
import sports_data as sd  # noqa
CACHE = os.environ.get("STUDY_CACHE", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/d1026")
os.makedirs(CACHE, exist_ok=True)
P = {"nfl": (20.0, 55.0, 0.33), "ncaaf": (25.0, 60.0, 0.2)}


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 7 else y - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def ti(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def tf(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def main():
    sides = []
    for lg in ("nfl", "ncaaf"):
        K, HOME, REG = P[lg]
        games = sd.load_games(lg)
        allg = sorted((g for g in games.values() if g.get("start") and g.get("home") and g.get("away")
                       and (g.get("stype") or "2") in ("2", "3")), key=lambda g: (g["start"], g["id"]))
        sched = defaultdict(list)                       # every scheduled game (any status) - the schedule is public
        for g in allg:
            sched[g["home"]].append(g); sched[g["away"]].append(g)
        pos = {tm: {g["id"]: i for i, g in enumerate(gs)} for tm, gs in sched.items()}
        last_home = {}                                  # (team, season) -> id of its last regular-season true home game
        for g in allg:
            if (g.get("stype") or "2") == "2" and str(g.get("neutral") or "0") != "1":
                last_home[(g["home"], season_of(g["start"]))] = g["id"]
        fin = [g for g in allg if g.get("status") == "final" and ti(g.get("home_score")) is not None
               and ti(g.get("away_score")) is not None]
        elo = defaultdict(lambda: 1500.0); seen = {}; rec = defaultdict(lambda: [0, 0]); last = {}
        for g in fin:
            s = season_of(g["start"]); h, a = g["home"], g["away"]
            for tm in (h, a):
                if seen.get(tm) != s:
                    elo[tm] = 1500 + (elo[tm] - 1500) * (1 - REG); seen[tm] = s
            hs, as_ = ti(g["home_score"]), ti(g["away_score"])
            neutral = str(g.get("neutral") or "0") == "1"
            mh, ma = ti(g.get("ml_home")), ti(g.get("ml_away"))
            oh, oa = ti(g.get("ml_home_open")), ti(g.get("ml_away_open"))
            sp = tf(g.get("spread_home"))
            exp_home = 1 / (1 + 10 ** (-(elo[h] + (0 if neutral else HOME) - elo[a]) / 400))
            kt = t(g["start"])
            ok = mh is not None and ma is not None and abs(mh) >= 100 and abs(ma) >= 100 and hs != as_
            if ok:
                mp_h = novig(mh, ma)
                op_h = novig(oh, oa) if (oh is not None and oa is not None and abs(oh) >= 100 and abs(oa) >= 100) else None
                for side, oth in (("home", "away"), ("away", "home")):
                    tm, o = g[side], g[oth]
                    L, OL = last.get(tm), last.get(o)
                    L = L if L and L["season"] == s else None
                    OL = OL if OL and OL["season"] == s else None
                    i = pos[tm][g["id"]]
                    nxt = sched[tm][i + 1] if i + 1 < len(sched[tm]) else None
                    if nxt is not None and (season_of(nxt["start"]) != s or (t(nxt["start"]) - kt).days > 21):
                        nxt = None
                    n_opp = None if nxt is None else (nxt["away"] if nxt["home"] == tm else nxt["home"])
                    sgn = 1 if side == "home" else -1
                    pts = None if sp is None else (sp if side == "home" else -sp)
                    margin = (hs - as_) * sgn
                    r, orc = rec[(tm, s)], rec[(o, s)]
                    sides.append(dict(
                        league=lg, season=s, gid=g["id"], start=g["start"], stype=g.get("stype") or "2",
                        side=side, home=side == "home" and not neutral, neutral=neutral, team=g[side + "_name"],
                        opp=g[oth + "_name"],
                        ml=mh if side == "home" else ma, mp=mp_h if side == "home" else 1 - mp_h,
                        op=None if op_h is None else (op_h if side == "home" else 1 - op_h),
                        won=margin > 0, margin=margin, pts=pts, ats=None if pts is None else margin + pts,
                        elo_p=exp_home if side == "home" else 1 - exp_home, elo=elo[tm], o_elo=elo[o],
                        w=r[0], l=r[1], ow=orc[0], ol=orc[1],
                        n_opp_elo=None if n_opp is None else elo[n_opp],
                        n_opp_rec=None if n_opp is None else tuple(rec[(n_opp, s)]),
                        n_home=None if nxt is None else nxt["home"] == tm,
                        senior=side == "home" and not neutral and last_home.get((tm, s)) == g["id"],
                        month=int(g["start"][5:7]),
                        last_won=L["won"] if L else None, last_home=L["home"] if L else None,
                        last_margin=L["margin"] if L else None, last_rec=L["rec_before"] if L else None,
                        last_pf=L["pf"] if L else None, last_pa=L["pa"] if L else None,
                        o_last_won=OL["won"] if OL else None, o_last_margin=OL["margin"] if OL else None,
                        o_last_home=OL["home"] if OL else None,
                        ))
            margin = hs - as_
            km = K * (1 + min(abs(margin), 28) / 14.0)
            res = 1 if margin > 0 else (0.5 if margin == 0 else 0)
            for tm, won, hm, mg, pf, pa in ((h, margin > 0, not neutral, margin, hs, as_), (a, margin < 0, False, -margin, as_, hs)):
                last[tm] = dict(season=s, won=won, home=hm, margin=mg, rec_before=tuple(rec[(tm, s)]), pf=pf, pa=pa)
                rec[(tm, s)][0 if won else 1] += 1
            elo[h] += km * (res - exp_home); elo[a] -= km * (res - exp_home)
    pickle.dump(sides, open(os.path.join(CACHE, "fb_sides.pkl"), "wb"))
    print("sides", len(sides))


if __name__ == "__main__":
    main()
