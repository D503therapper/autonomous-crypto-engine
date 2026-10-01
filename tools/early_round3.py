"""EARLY STUDIES ROUND 3 - 20 NEW angles with the odds in front of us (10/1, the owner: "weather, home teams, coaching
styles - coaches who go for it on fourth down - all the angles we never had the odds for"). Same honest rules as
round 2 (tools/early_round2.py): the FIRST FAIR number of the week (posted after both teams' last games ended),
walk-forward engine, graded on the result - moneyline dogs (won at the early price) and spreads (covered the early
number, -110), NFL and college. Coaching / style numbers come from each team's EARLIER games that season only.
Weather is the game's (a midweek forecast is close but not exact - noted). Saves results/early_round3.json."""
import json
import os
import sys
from collections import Counter
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import early_round2 as r2           # noqa: E402
import sports_data as sd            # noqa: E402

ET = ZoneInfo("America/New_York")
MIN_N = 40


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pair(x, i):
    try:
        return float(str(x).replace("/", "-").split("-")[i])
    except (TypeError, ValueError, IndexError):
        return None


def style(lg):
    """{(game id, team id): season-to-date style BEFORE that game} - 4th-down tries / game, pass rate, plays / game,
    yards-per-play margin, turnover margin / game (3+ earlier games)."""
    path = os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")
    rows = []
    with open(path) as f:
        for x in f:
            try:
                rows.append(json.loads(x))
            except ValueError:
                pass
    rows.sort(key=lambda r: r.get("start") or "")
    season = lambda s: s[:4] if s[5:7] >= "07" else str(int(s[:4]) - 1)
    acc, out = {}, {}
    for r in rows:
        t = r.get("teams") or {}
        if len(t) != 2:
            continue
        (a, sa), (b, sb) = list(t.items())
        s = season(r.get("start") or "0000-01")
        for me, st, them, so in ((a, sa, b, sb), (b, sb, a, sa)):
            h = acc.get((s, me))
            if h and h["n"] >= 3:
                out[(r["gid"], me)] = {"fourth": h["fourth"] / h["n"], "pass": h["pa"] / max(1, h["pa"] + h["ru"]),
                                       "plays": h["plays"] / h["n"], "ypp": (h["yf"] - h["ya"]) / h["n"],
                                       "to": (h["tot"] - h["tom"]) / h["n"]}
        for me, st, them, so in ((a, sa, b, sb), (b, sb, a, sa)):
            h = acc.setdefault((s, me), {"n": 0, "fourth": 0, "pa": 0, "ru": 0, "plays": 0, "yf": 0, "ya": 0, "tot": 0, "tom": 0})
            def plays(x):                        # (college boxes have no plays / yards-per-play: pass + rush tries)
                p_ = _f(x.get("totalOffensivePlays"))
                if p_ is None and _pair(x.get("completionAttempts"), 1) is not None and _f(x.get("rushingAttempts")) is not None:
                    p_ = _pair(x.get("completionAttempts"), 1) + _f(x.get("rushingAttempts"))
                return p_

            def ypp(x):
                y_ = _f(x.get("yardsPerPlay"))
                if y_ is None and plays(x) and _f(x.get("totalYards")) is not None:
                    y_ = _f(x.get("totalYards")) / plays(x)
                return y_
            vals = (_pair(st.get("fourthDownEff"), 1), _pair(st.get("completionAttempts"), 1), _f(st.get("rushingAttempts")),
                    plays(st), ypp(st), ypp(so), _f(so.get("turnovers")), _f(st.get("turnovers")))
            if None in vals:
                continue
            h["n"] += 1
            h["fourth"] += vals[0]
            h["pa"] += vals[1]
            h["ru"] += vals[2]
            h["plays"] += vals[3]
            h["yf"] += vals[4]
            h["ya"] += vals[5]
            h["tot"] += vals[6]                  # takeaways (their turnovers)
            h["tom"] += vals[7]                  # giveaways
    return out


def context(lg, games):
    """{(game id, team id): {...}} - weather, altitude, travel, road streak, OT last game, division, record."""
    fin = [g for g in games.values() if g.get("start") and (g.get("stype") or "?") in sd.REAL]
    fin.sort(key=lambda g: g["start"])
    tz = {}
    for g in fin:
        if str(g.get("neutral")) != "1" and _f(g.get("tzo")) is not None:
            tz.setdefault(g["home"], Counter())[_f(g["tzo"])] += 1
    home_tz = {t: c.most_common(1)[0][0] for t, c in tz.items()}
    season = lambda s: s[:4] if s[5:7] >= "07" else str(int(s[:4]) - 1)
    meets = Counter()
    for g in fin:
        if g.get("status") == "final":
            meets[(season(g["start"]), frozenset((g["home"], g["away"])))] += 1
    division = {k[1] for k, n in meets.items() if n >= 2} if lg == "nfl" else set()
    road, last_ot, rec, out = {}, {}, {}, {}
    for g in fin:
        s = season(g["start"])
        et = ef._t(g["start"]).astimezone(ET)
        wind, temp, rain = _f(g.get("wx_wind")), _f(g.get("wx_temp")), _f(g.get("wx_rain"))
        indoor = str(g.get("indoor")) == "1"
        gtz = _f(g.get("tzo"))
        for side, other in (("home", "away"), ("away", "home")):
            t = g[side]
            w, l_ = rec.get((s, t), (0, 0))
            ow, ol = rec.get((s, g[other]), (0, 0))
            out[(g["id"], t)] = {
                "outdoor": not indoor, "wind": None if indoor else wind, "temp": None if indoor else temp,
                "rain": None if indoor else rain, "elev": _f(g.get("elev")), "home_tz": home_tz.get(t),
                "opp_home_tz": home_tz.get(g[other]), "game_tz": gtz, "et_hour": et.hour + et.minute / 60,
                "road_streak": road.get(t, 0) + (1 if side == "away" and str(g.get("neutral")) != "1" else 0)
                if side == "away" else 0, "off_ot": last_ot.get(t, False),
                "division": frozenset((g["home"], g["away"])) in division,
                "pct": (w / (w + l_)) if w + l_ >= 4 else None, "opct": (ow / (ow + ol)) if ow + ol >= 4 else None,
                "month": et.month, "opp_dome": None}
        if g.get("status") != "final":
            continue
        for side in ("home", "away"):
            t = g[side]
            road[t] = (road.get(t, 0) + 1) if side == "away" and str(g.get("neutral")) != "1" else 0
            ls = str(g.get(f"ls_{side}") or "")
            last_ot[t] = len([x for x in ls.split(",") if x != ""]) > 4
        try:
            hw = float(g["home_score"]) > float(g["away_score"])
        except (TypeError, ValueError):
            continue
        for t, won in ((g["home"], hw), (g["away"], not hw)):
            w, l_ = rec.get((s, t), (0, 0))
            rec[(s, t)] = (w + 1, l_) if won else (w, l_ + 1)
    # dome teams: home games mostly indoors
    dome = Counter()
    homes = Counter()
    for g in fin:
        if str(g.get("neutral")) != "1":
            homes[g["home"]] += 1
            dome[g["home"]] += str(g.get("indoor")) == "1"
    is_dome = {t: dome[t] / homes[t] >= .6 for t in homes}
    for (gid, t), v in out.items():
        v["dome_team"] = is_dome.get(t, False)
    return out


def angles(lg):
    A = {}
    A["1 windy 15+ mph (outdoors)"] = lambda r, c, s: (c["wind"] or 0) >= 15
    A["2 freezing 32F or colder (outdoors)"] = lambda r, c, s: c["temp"] is not None and c["temp"] <= 32
    A["3 dome / warm team visiting a cold game (40F-)"] = lambda r, c, s: (r["side"] == "away" and c["temp"] is not None
                                                                          and c["temp"] <= 40 and (c["dome_team"] or (c["home_tz"] or 0) <= -7))
    A["4 rain / snow in the forecast"] = lambda r, c, s: (c["rain"] or 0) >= 0.5
    A["5 home dog"] = lambda r, c, s: r["side"] == "home" and not r["neutral"] and ((r.get("ml") or 0) >= 100 or (r.get("line") or 0) > 0)
    A["6 getting 14+ points (backdoor)"] = lambda r, c, s: (r.get("line") or 0) >= 14
    A["7 laying 7+ at home"] = lambda r, c, s: r["side"] == "home" and (r.get("line") or 0) <= -7
    A["8 visiting at altitude (1,500m+)"] = lambda r, c, s: r["side"] == "away" and (c["elev"] or 0) >= 1500
    A["9 West Coast team in an early East game"] = lambda r, c, s: (r["side"] == "away" and (c["home_tz"] or 0) <= -7
                                                                    and (c["game_tz"] or -9) >= -5 and c["et_hour"] < 14)
    A["10 East team flying West"] = lambda r, c, s: (r["side"] == "away" and (c["home_tz"] or -9) >= -5
                                                     and (c["game_tz"] or 0) <= -7)
    A["11 2nd+ straight road game"] = lambda r, c, s: c["road_streak"] >= 2
    A["12 coming off an overtime game"] = lambda r, c, s: c["off_ot"]
    A["13 division game"] = lambda r, c, s: c["division"]
    A["14 aggressive coach (4th-down tries, top quarter)"] = lambda r, c, s: s is not None and s["fourth"] >= Q[lg]["fourth"][1]
    A["15 conservative coach (4th-down tries, bottom quarter)"] = lambda r, c, s: s is not None and s["fourth"] <= Q[lg]["fourth"][0]
    A["16 pass-heavy team (top quarter)"] = lambda r, c, s: s is not None and s["pass"] >= Q[lg]["pass"][1]
    A["16 run-heavy team (bottom quarter)"] = lambda r, c, s: s is not None and s["pass"] <= Q[lg]["pass"][0]
    A["17 fast pace (plays, top quarter)"] = lambda r, c, s: s is not None and s["plays"] >= Q[lg]["plays"][1]
    A["17 slow pace (plays, bottom quarter)"] = lambda r, c, s: s is not None and s["plays"] <= Q[lg]["plays"][0]
    A["18 underrated: out-gains teams (yds/play) but losing record"] = lambda r, c, s: (s is not None and s["ypp"] > 0.3
                                                                                        and c["pct"] is not None and c["pct"] < .5)
    A["19 bad turnover luck, even-or-better yards"] = lambda r, c, s: s is not None and s["to"] <= -0.75 and s["ypp"] >= 0
    A["20 December+: bad team (.300-) / good team (.700+)"] = lambda r, c, s: (c["month"] in (12, 1) and c["pct"] is not None
                                                                              and c["pct"] <= .3)
    A["20 December+: good team (.700+)"] = lambda r, c, s: c["month"] in (12, 1) and c["pct"] is not None and c["pct"] >= .7
    return A


Q = {}


def quarters(vals):
    v = sorted(vals)
    return (v[len(v) // 4], v[3 * len(v) // 4]) if v else (0, 0)


def main():
    rep = {}
    for lg in (sys.argv[1:] or ["nfl", "ncaaf"]):
        games = sd.load_games(lg)
        rows = r2.build(lg)
        ctx = context(lg, games)
        sty = style(lg)
        Q[lg] = {k: quarters([v[k] for v in sty.values()]) for k in ("fourth", "pass", "plays")}
        base_ml, base_sp = r2.grade_ml(rows), r2.grade_sp(rows)
        print(f"\n===================== {lg.upper()}: {len(rows)} sides  (baseline dogs ROI {base_ml['roi']:+.1%}, "
              f"spreads {base_sp['rate']:.1%}; style numbers on {sum(1 for r in rows if (r['gid'], r['tid']) in sty)})")
        print(f"   quarters: {Q[lg]}")
        out = {}
        for name, t in angles(lg).items():
            sel = []
            for r in rows:
                c = ctx.get((r["gid"], r["tid"]))
                if c is None:
                    continue
                try:
                    if t(r, c, sty.get((r["gid"], r["tid"]))):
                        sel.append(r)
                except (TypeError, KeyError):
                    continue
            res = {"ML dog": r2.grade_ml(sel),
                   "ML dog + engine likes": r2.grade_ml([r for r in sel if (r.get("ml_gap") or -1) >= .04]),
                   "spread": r2.grade_sp(sel),
                   "spread + engine 2+ pts": r2.grade_sp([r for r in sel if (r.get("sp_edge") or -99) >= 2])}
            out[name] = res
            print(f"\n-- {name}")
            for k, v in res.items():
                if not v:
                    continue
                up, of = map(int, v["up"].split("/"))
                flag = "  << HOLDS UP" if v["n"] >= MIN_N and v["roi"] > 0 and up >= max(2, -(-2 * of // 3)) else ""
                what = "won" if k.startswith("ML") else "covered"
                print(f"   {k:24s} {v['n']:4d}  {what} {v['rate']:.1%} (needs {v['said']:.1%})  ROI {v['roi']:+.1%}  "
                      f"up {v['up']} {v['by']}{flag}")
        rep[lg] = out
    os.makedirs("results", exist_ok=True)
    try:
        with open("results/early_round3.json") as f:
            rep = {**json.load(f), **rep}
    except (OSError, ValueError):
        pass
    with open("results/early_round3.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
