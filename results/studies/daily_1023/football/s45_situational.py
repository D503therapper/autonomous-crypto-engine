"""Studies 4-5 (10/23), game files 2018-26 at CLOSING prices (moneyline -150..+350, spreads at the closing number
+ its juice). Train 2018-24, holdout 2025, current 2026. Everything used is known before kickoff (schedule, last
week's closing line and result).
4 LAST WEEK'S BIG DOG: a team that was a 14+ point dog last game (NFL 10+), within 9 days - does the market over- or
  under-rate it next week?  5 NIGHT -> NOON: a team that played at night (7 PM ET+ college / Sunday or Monday night
  NFL) and now kicks off at noon ET or earlier (NFL: the 1 PM Sunday window) on a normal week, vs an opponent that
  did not."""
import json
from datetime import datetime, timedelta
import lib

sd, sm = lib.sd, lib.sm


def et(start):
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
    dst = t.month < 11 or (t.month == 11 and t.day <= 7)
    return t - timedelta(hours=4 if dst else 5)


def num(x):
    return lib.num(x)


def prof_ml(g, side):
    o = num(g.get(f"ml_{side}"))
    if o is None or abs(o) < 100 or not (-150 <= o <= 350):
        return None
    m = float(g["home_score"]) - float(g["away_score"])
    if m == 0:
        return None
    won = m > 0 if side == "home" else m < 0
    return lib.dec(o) - 1 if won else -1.0


def prof_sp(g, side):
    s = num(g.get("spread_home"))
    if s is None:
        return None
    pts = s if side == "home" else -s
    m = float(g["home_score"]) - float(g["away_score"])
    m = m if side == "home" else -m
    if m + pts == 0:
        return None
    pr = lib.sp_dec(g.get("spread_home_odds") if side == "home" else g.get("spread_away_odds"))
    return pr - 1 if m + pts > 0 else -1.0


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        fin = [g for g in sm.finals(sd.load_games(lg), lg) if g["start"] >= "2018-07-01"]
        last = {}
        sides = []
        for g in fin:
            t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
            row = {}
            for side, oth in (("home", "away"), ("away", "home")):
                tm = g[side]
                pv = last.get(tm)
                row[side] = pv if pv and 5 <= (t - pv["t"]).days <= 9 else None
            for side, oth in (("home", "away"), ("away", "home")):
                sides.append((g, side, row[side], row[oth]))
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            s = num(g.get("spread_home"))
            for side, sg in (("home", 1), ("away", -1)):
                pts = None if s is None else (s if side == "home" else -s)
                mg = (hs - as_) * sg
                last[g[side]] = {"t": t, "et": et(g["start"]), "pts": pts, "margin": mg,
                                 "covered": None if pts is None else mg + pts > 0}
        R = {}
        def add(name, pred):
            for mk, fn in (("ML", prof_ml), ("ATS", prof_sp)):
                b = []
                for g, side, me, op in sides:
                    if pred(g, side, me, op):
                        p = fn(g, side)
                        if p is not None:
                            b.append((lib.season(g["start"]), p))
                R[f"{name} | {mk}"] = lib.summ(b, train=(2018, 2024))
        add("base every side", lambda g, s, me, op: True)
        dogm = lambda g, s: (num(g.get(f"ml_{s}")) or 0) >= 100
        add("base every dog", lambda g, s, me, op: dogm(g, s))
        add("base every favorite", lambda g, s, me, op: not dogm(g, s))
        big = 10 if lg == "nfl" else 14
        bd = lambda me: me is not None and me["pts"] is not None and me["pts"] >= big
        add(f"4 last game a {big}+ pt dog", lambda g, s, me, op: bd(me))
        add(f"4 last game a {big}+ pt dog, now a dog", lambda g, s, me, op: bd(me) and dogm(g, s))
        add(f"4 last game a {big}+ pt dog, now a favorite", lambda g, s, me, op: bd(me) and not dogm(g, s))
        add(f"4 last game a {big}+ pt dog AND covered", lambda g, s, me, op: bd(me) and me["covered"])
        add(f"4 last game a {big}+ pt dog AND didn't cover", lambda g, s, me, op: bd(me) and me["covered"] is False)
        add(f"4 opponent was a {big}+ pt dog last game", lambda g, s, me, op: bd(op) and not bd(me))
        if lg == "ncaaf":
            night = lambda me: me is not None and me["et"].hour >= 19
            early = lambda g: et(g["start"]).hour < 13 and et(g["start"]).weekday() == 5
        else:
            night = lambda me: me is not None and me["et"].hour >= 20 and me["et"].weekday() in (6, 0)
            early = lambda g: et(g["start"]).hour == 13 and et(g["start"]).weekday() == 6
        add("5 night -> noon, opponent not", lambda g, s, me, op: early(g) and night(me) and not night(op))
        add("5 night -> noon, opponent not, as a dog", lambda g, s, me, op: early(g) and night(me) and not night(op) and dogm(g, s))
        add("5 night -> noon, opponent not, as a favorite", lambda g, s, me, op: early(g) and night(me) and not night(op) and not dogm(g, s))
        add("5 night -> noon, on the road", lambda g, s, me, op: early(g) and night(me) and not night(op) and s == "away" and str(g.get("neutral")) != "1")
        print(f"\n===== {lg.upper()} {len(fin)} finals")
        for k, v in R.items():
            print(lib.line(k, v))
        rep[lg] = R
    json.dump(rep, open(lib.OUT + "/s45_out.json", "w"), indent=1)


if __name__ == "__main__":
    main()
