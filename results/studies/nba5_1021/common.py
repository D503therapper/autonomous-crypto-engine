"""Shared NBA study dataset: one row per regular-season game with a closing moneyline, every feature PRE-GAME
(Elo replayed in order, schedule from the games before, box-score features from earlier box scores + this game's
box only for 'who played' - the proxy for the injury report). Repo is read-only; everything lands in nba5/."""
import collections
import csv
import gzip
import json
import math
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone

WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"
OUT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5"
sys.path.insert(0, WT)
os.chdir(WT)
import sports_data as sd          # noqa: E402
import sports_model as sm         # noqa: E402

import pandas as pd               # noqa: E402
import numpy as np                # noqa: E402

TRAIN = (2018, 2019, 2020, 2021, 2022)
BLIND = (2023, 2024, 2025, 2026)


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    if y == 2020 and m <= 10:
        return 2019
    return y if m >= 9 else y - 1


def us_date(start):
    """Game date in US time (UTC - 5h is good enough to split nights)."""
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M") - timedelta(hours=5)
    return t.date()


def dec(ml):
    ml = int(ml)
    return 1 + (ml / 100 if ml > 0 else 100 / -ml)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build():
    games = sd.load_games("nba")
    fin = sm.finals(games, "nba")           # regular season + playoffs, sorted, no preseason
    # ---------- Elo replay (default NBA settings k=20, hfa=70 - the engine re-picks these daily; close enough)
    elo = sm.Elo(20, 70, "nba")
    feats = {}
    ratings_pre = {}
    for g in fin:
        f = elo.features(g)
        feats[g["id"]] = f
        ratings_pre[g["id"]] = (elo.r.get(g["home"], 1500.0), elo.r.get(g["away"], 1500.0))
        elo.update(g)
    # ---------- schedule, per team (regular + playoffs in order)
    by_team = collections.defaultdict(list)
    for g in fin:
        d = us_date(g["start"])
        by_team[g["home"]].append((d, g, "home"))
        by_team[g["away"]].append((d, g, "away"))
    home_tz, home_elev = {}, {}
    for tm, lst in by_team.items():
        tz = collections.Counter(_num(g["tzo"]) for d, g, s in lst if s == "home" and str(g.get("neutral")) != "1" and _num(g["tzo"]) is not None)
        el = collections.Counter(_num(g["elev"]) for d, g, s in lst if s == "home" and str(g.get("neutral")) != "1" and _num(g["elev"]) is not None)
        home_tz[tm] = tz.most_common(1)[0][0] if tz else None
        home_elev[tm] = el.most_common(1)[0][0] if el else None
    sched = {}   # (gid, team) -> dict
    season_wpct = {}  # (team, season) -> regular season win pct
    for tm, lst in by_team.items():
        lst.sort(key=lambda x: (x[1]["start"], x[1]["id"]))
        hist = []   # (date, side, margin, season, stype)
        trip = 0
        last_trip = 0
        wins = collections.defaultdict(lambda: [0, 0])
        for d, g, side in lst:
            s = season_of(g["start"])
            reg = str(g.get("stype")) == "2"
            prev = [h for h in hist]
            prev_same = [h for h in prev if h[3] == s and h[4]]
            n_season = len(prev_same)
            rest = (d - prev[-1][0]).days if prev else 10
            n4 = sum(1 for h in prev if (d - h[0]).days <= 3) + 1
            n6 = sum(1 for h in prev if (d - h[0]).days <= 5) + 1
            n8 = sum(1 for h in prev if (d - h[0]).days <= 7) + 1
            # trip: consecutive away games (same season), reset on a home game
            if prev and prev[-1][3] != s:
                trip = 0
            if side == "away":
                trip_game = trip + 1
                home_after = 0
            else:
                trip_game = 0
                home_after = trip if (prev and prev[-1][1] == "away" and prev[-1][3] == s) else 0
            tzo = _num(g.get("tzo"))
            tz_cross = abs(tzo - home_tz[tm]) if tzo is not None and home_tz.get(tm) is not None and side == "away" else 0.0
            tz_dir = (tzo - home_tz[tm]) if tzo is not None and home_tz.get(tm) is not None and side == "away" else 0.0
            elev = _num(g.get("elev")) or 0.0
            alt = 1 if side == "away" and elev >= 1000 and (home_elev.get(tm) or 0) < 1000 else 0
            # long-ago tz: where was the previous game (tz of previous game venue) -> zones moved since last game
            prev_tz = _num(prev[-1][5]) if prev else None
            tz_move = abs(tzo - prev_tz) if tzo is not None and prev_tz is not None else 0.0
            last_margin = prev_same[-1][2] if prev_same else None
            l5 = [h[2] for h in prev_same[-5:]]
            l10 = [h[2] for h in prev_same[-10:]]
            w, n = wins[s]
            wl, nl = wins[s - 1]
            sched[(g["id"], tm)] = dict(
                n_season=n_season, rest=rest, b2b=int(rest <= 1), n4=n4, n6=n6, n8=n8, trip_game=trip_game,
                home_after=home_after, tz_cross=tz_cross, tz_dir=tz_dir, tz_move=tz_move, alt=alt,
                last_margin=last_margin, m5=(sum(l5) / len(l5)) if l5 else None, m10=(sum(l10) / len(l10)) if l10 else None,
                wp_season=(w / n) if n else None, wp_last=(wl / nl) if nl else None, n_last=nl,
                prev_side=(prev[-1][1] if prev else None), prev_rest=(prev[-1][6] if prev else None))
            hs, as_ = int(g["home_score"]), int(g["away_score"])
            margin = (hs - as_) if side == "home" else (as_ - hs)
            hist.append((d, side, margin, s, reg, g.get("tzo"), rest))
            if side == "away":
                trip += 1
            else:
                trip = 0
            if reg:
                wins[s][1] += 1
                wins[s][0] += int(margin > 0)
    rows = []
    for g in fin:
        if str(g.get("stype")) != "2":
            continue
        try:
            mh, ma = int(g["ml_home"]), int(g["ml_away"])
        except (TypeError, ValueError):
            continue
        f = feats[g["id"]]
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        sh, sa = sched[(g["id"], g["home"])], sched[(g["id"], g["away"])]
        r = dict(gid=g["id"], start=g["start"], date=str(us_date(g["start"])), season=season_of(g["start"]),
                 home=g["home"], away=g["away"], home_name=g["home_name"], away_name=g["away_name"],
                 hs=hs, as_=as_, home_win=int(hs > as_), ml_home=mh, ml_away=ma,
                 mp_home=sd.no_vig(mh, ma), dec_home=dec(mh), dec_away=dec(ma),
                 ml_home_open=_num(g.get("ml_home_open")), ml_away_open=_num(g.get("ml_away_open")),
                 spread_home=_num(g.get("spread_home")), neutral=str(g.get("neutral")) == "1",
                 p_elo=f["p_elo"], elo_pts=f["elo_pts"], r_home=ratings_pre[g["id"]][0], r_away=ratings_pre[g["id"]][1],
                 feat=f)
        for k, v in sh.items():
            r["h_" + k] = v
        for k, v in sa.items():
            r["a_" + k] = v
        rows.append(r)
    return rows


def load(force=False):
    p = os.path.join(OUT, "games.pkl")
    if not force and os.path.exists(p):
        with open(p, "rb") as fh:
            return pickle.load(fh)
    rows = build()
    with open(p, "wb") as fh:
        pickle.dump(rows, fh)
    return rows


def sides(rows):
    """Two rows per game: one per side, with price, implied no-vig p, result and the side's own/opp schedule."""
    out = []
    for r in rows:
        for side in ("home", "away"):
            opp = "away" if side == "home" else "home"
            ml = r["ml_" + side]
            mp = r["mp_home"] if side == "home" else 1 - r["mp_home"]
            win = r["home_win"] if side == "home" else 1 - r["home_win"]
            s = {k: v for k, v in r.items() if not k.startswith(("h_", "a_"))}
            s.update(side=side, ml=ml, dec=r["dec_" + side], mp=mp, win=win, is_home=int(side == "home"),
                     p_elo=r["p_elo"] if side == "home" else 1 - r["p_elo"],
                     elo_pts=r["elo_pts"] if side == "home" else -r["elo_pts"])
            pre = "h_" if side == "home" else "a_"
            opre = "a_" if side == "home" else "h_"
            for k, v in r.items():
                if k.startswith(pre):
                    s["t_" + k[2:]] = v
                elif k.startswith(opre):
                    s["o_" + k[2:]] = v
            out.append(s)
    return out


def grade(df, label="", by_season=True):
    """W-L, win% vs implied, ROI at the close (flat 1u)."""
    if len(df) == 0:
        return dict(label=label, n=0)
    w = df["win"].sum()
    roi = ((df["win"] * (df["dec"] - 1)) - (1 - df["win"])).sum() / len(df)
    out = dict(label=label, n=len(df), w=int(w), l=int(len(df) - w), win=round(w / len(df) * 100, 1),
               imp=round(df["mp"].mean() * 100, 1), roi=round(roi * 100, 1))
    if by_season:
        out["seasons"] = {int(s): (len(d), round((((d["win"] * (d["dec"] - 1)) - (1 - d["win"])).sum() / len(d)) * 100, 1))
                          for s, d in df.groupby("season")}
    return out


def fmt(gd):
    if gd.get("n", 0) == 0:
        return f"{gd.get('label','')}: n=0"
    s = f"{gd['label']}: n={gd['n']} {gd['w']}-{gd['l']} {gd['win']}% vs {gd['imp']}% implied, ROI {gd['roi']:+.1f}%"
    if "seasons" in gd:
        s += "  [" + " ".join(f"{k}:{v[0]}/{v[1]:+.1f}" for k, v in sorted(gd["seasons"].items())) + "]"
    return s


def split(df):
    return df[df["season"].isin(TRAIN)], df[df["season"].isin(BLIND)]


def report(df, label, base=None):
    """Train / blind lines plus the band baseline (all sides in the same price band)."""
    tr, bl = split(df)
    lines = [fmt(grade(tr, label + " TRAIN")), fmt(grade(bl, label + " BLIND"))]
    if base is not None:
        btr, bbl = split(base)
        lines.append("   baseline " + fmt(grade(btr, "TRAIN")) + " | " + fmt(grade(bbl, "BLIND")))
    return "\n".join(lines)


if __name__ == "__main__":
    rows = load(force=True)
    print(len(rows), "games with a closing ML;", collections.Counter(r["season"] for r in rows))
