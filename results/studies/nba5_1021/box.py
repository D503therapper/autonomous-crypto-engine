"""Box-score features per (game, team), pre-game except 'who played tonight' (the stand-in for the injury report):
stars by minutes over the team's last 15 games, who's out / back, rotation men out, and the season's roster turnover
(share of last season's minutes that returned, judged on the roster listed in the season's first box score)."""
import collections
import csv
import gzip
import json
import os
import pickle
from common import OUT, WT, season_of

DIR = os.path.join(WT, "data/sports/roster")
WINDOW, MIN_PLAYED = 15, 8


def rows():
    out = []
    for f in sorted(os.listdir(DIR)):
        if f.startswith("nba_") and f.endswith(".csv.gz"):
            with gzip.open(os.path.join(DIR, f), "rt", newline="") as fh:
                for r in csv.DictReader(fh):
                    try:
                        st = json.loads(r["stats"]) if r["stats"] else {}
                    except ValueError:
                        st = {}
                    mn = st.get("minutes")
                    try:
                        mn = float(mn) if mn not in (None, "", "--") else None
                    except ValueError:
                        mn = None
                    try:
                        pm = float(st.get("plusMinus") or 0)
                    except ValueError:
                        pm = 0.0
                    out.append((r["gid"], r["start"], r["team"], r["pid"], r["player"], r["starter"] == "1", mn, pm))
    out.sort(key=lambda x: (x[1], x[0]))
    return out


def build():
    rs = rows()
    by_tg = collections.OrderedDict()
    for gid, start, team, pid, name, starter, mn, pm in rs:
        by_tg.setdefault((team, start, gid), []).append((pid, name, starter, mn, pm))
    by_team = collections.defaultdict(list)
    for (team, start, gid), lst in by_tg.items():
        by_team[team].append((start, gid, lst))
    # last-season minutes per team-player (for turnover)
    season_min = collections.defaultdict(lambda: collections.defaultdict(float))   # (team, season) -> pid -> minutes
    season_games_n = collections.Counter()
    for (team, start, gid), lst in by_tg.items():
        s = season_of(start)
        season_games_n[(team, s)] += 1
        for pid, name, starter, mn, pm in lst:
            if mn:
                season_min[(team, s)][pid] += mn
    feats = {}
    turnover = {}
    for team, lst in by_team.items():
        lst.sort()
        hist = []            # per game: dict pid -> minutes (None = listed, didn't play)
        season_seen = {}
        last_played_idx = {}  # pid -> index of last game he played
        cur_season = None
        for idx, (start, gid, players) in enumerate(lst):
            s = season_of(start)
            if s != cur_season:
                cur_season = s
                season_seen = set()
                # turnover at the first box of the season: roster listed tonight vs last season's minutes
                prev = season_min.get((team, s - 1), {})
                tot = sum(prev.values())
                if tot > 0 and season_games_n[(team, s - 1)] >= 60:
                    listed = {p[0] for p in players}
                    ret = sum(m for pid, m in prev.items() if pid in listed)
                    top3 = sorted(prev.items(), key=lambda x: -x[1])[:3]
                    turnover[(team, s)] = dict(ret_share=ret / tot, top3_back=sum(1 for pid, _ in top3 if pid in listed),
                                               n_listed=len(listed))
            season_seen |= {p[0] for p in players}
            tonight = {p[0]: p[3] for p in players}
            names = {p[0]: p[1] for p in players}
            # stars from the last WINDOW games (pre-game), among men on this season's roster
            win = hist[-WINDOW:]
            mpg = {}
            for pid in season_seen:
                played = [h[pid] for h in win if h.get(pid)]
                if len(played) >= MIN_PLAYED:
                    mpg[pid] = sum(played) / len(played)
            order = sorted(mpg, key=lambda p: -mpg[p])
            top2, top5, top8 = order[:2], order[:5], order[:8]
            def out(pid):
                return 0 if tonight.get(pid) else 1
            def streak(pid):   # consecutive team games missed before tonight
                k = 0
                for h in reversed(hist):
                    if h.get(pid):
                        break
                    k += 1
                return k
            star = order[0] if order else None
            f = dict(n_box=idx, has_stars=bool(order), star=names.get(star, star) if star else None,
                     star_mpg=mpg.get(star) if star else None,
                     star_out=out(star) if star else None, star_streak=streak(star) if star else None,
                     star_back=(1 if star and tonight.get(star) and streak(star) >= 2 else 0) if star else None,
                     top2_out=sum(out(p) for p in top2) if len(top2) == 2 else None,
                     top5_out=sum(out(p) for p in top5) if len(top5) == 5 else None,
                     top8_out=sum(out(p) for p in top8) if len(top8) == 8 else None,
                     top2_back=sum(1 for p in top2 if tonight.get(p) and streak(p) >= 2) if len(top2) == 2 else None,
                     top5_back=sum(1 for p in top5 if tonight.get(p) and streak(p) >= 2) if len(top5) == 5 else None,
                     out_minutes=sum(mpg[p] for p in top8 if out(p)) if len(top8) == 8 else None,
                     n_window=len(win))
            f.update(turnover.get((team, s), {}))
            feats[(gid, team)] = f
            hist.append(tonight)
    return feats, turnover


def load_box(force=False):
    p = os.path.join(OUT, "box.pkl")
    if not force and os.path.exists(p):
        with open(p, "rb") as fh:
            return pickle.load(fh)
    b = build()
    with open(p, "wb") as fh:
        pickle.dump(b, fh)
    return b


if __name__ == "__main__":
    feats, turnover = load_box(force=True)
    print(len(feats), "team-games;", len(turnover), "team-seasons with turnover")
    import statistics
    for s in (2022, 2023, 2024, 2025):
        v = [t["ret_share"] for (tm, ss), t in turnover.items() if ss == s]
        print(s, len(v), "ret_share median %.2f min %.2f max %.2f" % (statistics.median(v), min(v), max(v)))
    so = [f for f in feats.values() if f["star_out"] is not None]
    print("star defined", len(so), "star out", sum(f["star_out"] for f in so), "star back", sum(f["star_back"] for f in so))
