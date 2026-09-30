"""STUDY 5 - WHO'S IN NET / ON THE MOUND (the owner, 9/30: "find the dogs when they win").

Every NHL starting goalie and MLB starting pitcher gets a running grade from ONLY the starts before that day (no
peeking): goals / runs his team allowed in his starts vs the league average, shrunk toward average when he has few
starts, plus how many starts he's had lately (a backup barely starts). Then, for every past underdog (+100..+280):
  - the dog's starter vs the favorite's starter (better / worse),
  - the favorite starting a BACKUP,
graded on every season, and walk-forward: the spot has to make money season after season, not in one hot year.
Run: python tools/starters_study.py
"""
import json
import os
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

SHRINK = {"nhl": 12, "mlb": 8}      # starts of shrinkage toward the league average
RECENT_D = 45                       # 'lately': starts in the last 45 days (a backup has few)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def season(d, lg):
    y, m = int(d[:4]), int(d[5:7])
    if lg == "nhl":
        return f"{y}-{str(y + 1)[2:]}" if m >= 9 else f"{y - 1}-{str(y)[2:]}"
    return str(y)


def rows(games, lg):
    fin = sorted((g for g in games.values() if g.get("league") == lg and g.get("status") == "final"
                  and g.get("home_score") not in (None, "") and g.get("away_score") not in (None, "")),
                 key=lambda g: g["start"])
    allowed = defaultdict(lambda: [0.0, 0])      # starter -> [runs/goals allowed, starts]
    recent = defaultdict(deque)                  # starter -> start times
    lg_tot = [0.0, 0]
    out = []
    for g in fin:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except ValueError:
            continue
        sh, sa = g.get("sp_home") or "", g.get("sp_away") or ""
        t = _t(g["start"])
        avg = lg_tot[0] / lg_tot[1] if lg_tot[1] else None

        def grade(name):
            a, n = allowed[name]
            if not name or avg is None:
                return None, 0
            k = SHRINK[lg]
            ra = (a + k * avg) / (n + k)                  # shrunk runs / goals allowed per start
            dq = recent[name]
            while dq and t - dq[0] > timedelta(days=RECENT_D):
                dq.popleft()
            return avg - ra, len(dq)                      # + = better than average
        gh, nh = grade(sh)
        ga, na = grade(sa)
        try:
            oh, oa = int(g["ml_home"]), int(g["ml_away"])
        except (ValueError, KeyError, TypeError):
            oh = oa = None
        if oh is not None and hs != as_ and gh is not None and ga is not None:
            for side, o, won, mine, theirs, n_theirs in (("home", oh, hs > as_, gh, ga, na), ("away", oa, as_ > hs, ga, gh, nh)):
                if 100 <= o <= 280:
                    out.append({"d": g["start"][:10], "won": won, "dec": dec(o), "edge": mine - theirs,
                                "fav_backup": n_theirs <= 2})
        # update AFTER the game (the next game sees it)
        for name, conceded in ((sh, as_), (sa, hs)):
            if name:
                allowed[name][0] += conceded
                allowed[name][1] += 1
                recent[name].append(t)
                lg_tot[0] += conceded
                lg_tot[1] += 1
    return out


def roi(b):
    return sum((r["dec"] - 1) if r["won"] else -1 for r in b) / len(b) if b else 0.0


if __name__ == "__main__":
    games = sd.load_games()
    for lg, cuts in (("nhl", (0.2, 0.4)), ("mlb", (0.5, 1.0))):
        rs = rows(games, lg)
        print(f"{lg.upper()}: {len(rs)} dogs with both starters graded")
        spots = {"every dog": lambda r: True, "fav starts a BACKUP": lambda r: r["fav_backup"]}
        for c in cuts:
            spots[f"dog's starter better by {c}+"] = (lambda c: lambda r: r["edge"] >= c)(c)
            spots[f"dog better by {c}+ AND fav backup"] = (lambda c: lambda r: r["edge"] >= c and r["fav_backup"])(c)
        for name, keep in spots.items():
            b = [r for r in rs if keep(r)]
            by = defaultdict(list)
            for r in b:
                by[season(r["d"], lg)].append(r)
            good = sum(roi(v) > 0 for v in by.values() if len(v) >= 30)
            seasons = sum(len(v) >= 30 for v in by.values())
            print(f"   {name:38} {len(b):5} dogs won {sum(r['won'] for r in b) / max(1, len(b)):.0%} money {roi(b):+.1%}"
                  f" | made money in {good} of {seasons} seasons")
