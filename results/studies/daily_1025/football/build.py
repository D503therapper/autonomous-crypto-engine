"""10/25 football studies - per-side rows, everything known BEFORE kickoff (walk-forward Elo, last game, rest,
kickoff hour ET, power tier, open/close moneylines, closing spread). Read-only on the worktree."""
import os, sys, pickle
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"
sys.path.insert(0, WT); os.chdir(WT)
import sports_data as sd  # noqa
OUT = os.path.dirname(os.path.abspath(__file__))
P = {"nfl": (20.0, 55.0, 0.33), "ncaaf": (25.0, 60.0, 0.2)}
ET = ZoneInfo("America/New_York")
SEC = "Alabama Arkansas Auburn Florida Georgia Kentucky LSU|Ole Miss|Mississippi St|Missouri|South Carolina|Tennessee|Texas A&M|Vanderbilt"
BASE_P = set("Alabama|Arkansas|Auburn|Florida|Georgia|Kentucky|LSU|Ole Miss|Mississippi St|Missouri|South Carolina|Tennessee|Texas A&M|Vanderbilt|"
             "Illinois|Indiana|Iowa|Maryland|Michigan|Michigan St|Minnesota|Nebraska|Northwestern|Ohio State|Penn State|Purdue|Rutgers|Wisconsin|"
             "Boston College|Clemson|Duke|Florida St|Georgia Tech|Louisville|Miami|NC State|North Carolina|Pitt|Syracuse|Virginia|Virginia Tech|Wake Forest|"
             "Baylor|Iowa State|Kansas|Kansas St|Oklahoma|Oklahoma St|TCU|Texas|Texas Tech|West Virginia|"
             "Arizona|Arizona St|California|Colorado|Oregon|Oregon St|Stanford|UCLA|USC|Utah|Washington|Washington St|Notre Dame".split("|"))
JOIN = {"BYU": 2023, "Cincinnati": 2023, "Houston": 2023, "UCF": 2023, "SMU": 2024}
LEFT = {"Oregon St": 2024, "Washington St": 2024}
ACAD = {"Army", "Navy", "Air Force"}


def power(name, s):
    if name in JOIN:
        return s >= JOIN[name]
    if name in LEFT:
        return s < LEFT[name]
    return name in BASE_P


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
        fin = sorted((g for g in games.values() if g.get("status") == "final" and ti(g.get("home_score")) is not None
                      and ti(g.get("away_score")) is not None), key=lambda g: g["start"])
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
            kt = t(g["start"]); et = kt.astimezone(ET)
            ok = mh is not None and ma is not None and abs(mh) >= 100 and abs(ma) >= 100 and hs != as_
            if ok:
                mp_h = novig(mh, ma)
                op_h = novig(oh, oa) if (oh is not None and oa is not None and abs(oh) >= 100 and abs(oa) >= 100) else None
                for side, oth in (("home", "away"), ("away", "home")):
                    tm, o = g[side], g[oth]
                    nm, onm = g[side + "_name"], g[oth + "_name"]
                    L, OL = last.get(tm), last.get(o)
                    sgn = 1 if side == "home" else -1
                    pts = None if sp is None else (sp if side == "home" else -sp)
                    margin = (hs - as_) * sgn
                    r, orc = rec[(tm, s)], rec[(o, s)]
                    sides.append(dict(
                        league=lg, season=s, gid=g["id"], start=g["start"], stype=g.get("stype") or "2",
                        side=side, home=side == "home" and not neutral, neutral=neutral, team=nm, opp=onm,
                        ml=mh if side == "home" else ma, mp=mp_h if side == "home" else 1 - mp_h,
                        op=None if op_h is None else (op_h if side == "home" else 1 - op_h),
                        won=margin > 0, margin=margin, pts=pts, ats=None if pts is None else margin + pts,
                        elo_p=exp_home if side == "home" else 1 - exp_home, elo=elo[tm], o_elo=elo[o],
                        w=r[0], l=r[1], ow=orc[0], ol=orc[1],
                        pw=power(nm, s), opw=power(onm, s),
                        et_hour=et.hour + et.minute / 60, et_dow=et.weekday(),
                        rest=(kt - t(L["start"])).total_seconds() / 86400 if L and L["season"] == s else None,
                        o_rest=(kt - t(OL["start"])).total_seconds() / 86400 if OL and OL["season"] == s else None,
                        last_won=L["won"] if L and L["season"] == s else None,
                        last_home=L["home"] if L and L["season"] == s else None,
                        last_dow=L["dow"] if L and L["season"] == s else None,
                        last_opp=L["opp"] if L and L["season"] == s else None,
                        o_last_won=OL["won"] if OL and OL["season"] == s else None,
                        o_last_home=OL["home"] if OL and OL["season"] == s else None,
                        o_last_opp=OL["opp"] if OL and OL["season"] == s else None,
                        o_last_dow=OL["dow"] if OL and OL["season"] == s else None,
                        last_was_fav=L["fav"] if L and L["season"] == s else None,
                        ))
            margin = hs - as_
            km = K * (1 + min(abs(margin), 28) / 14.0)
            res = 1 if margin > 0 else (0.5 if margin == 0 else 0)
            elo[h] += km * (res - exp_home); elo[a] -= km * (res - exp_home)
            for tm, onm, won, hm, ml in ((h, g["away_name"], margin > 0, not neutral, mh), (a, g["home_name"], margin < 0, False, ma)):
                rec[(tm, s)][0 if won else 1] += 1
                last[tm] = dict(start=g["start"], season=s, won=won, home=hm, opp=onm, dow=et.weekday(),
                                fav=(ml is not None and ml < 0))
    pickle.dump(sides, open(os.path.join(OUT, "sides.pkl"), "wb"))
    print("sides", len(sides))


if __name__ == "__main__":
    main()
