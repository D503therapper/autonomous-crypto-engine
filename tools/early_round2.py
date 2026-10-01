"""EARLY STUDIES ROUND 2 (10/1, the owner: "now that we have the odds in front of us - streaks, start of the season,
recent form, coaches, injuries, Monday / Thursday night, games out of the country - every angle, money lines AND
spreads, college AND NFL"). Every angle is graded in four markets at the EARLY number (the first look of the week):
NFL / college moneyline DOGS (won at the early price) and NFL / college SPREADS (covered the early number, -110).
Each angle is also shown with the engine agreeing (its own read, walk-forward, Tuesday-known info only).
Injuries and the starting QB are game-day facts - marked HINDSIGHT (they say what the info is worth, not a bet).

Prints a report, saves results/early_round2.json."""
import gzip
import json
import os
import statistics
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402
import sports_model as sm           # noqa: E402

ET = ZoneInfo("America/New_York")
MIN_N = 40
BLIND = {"inj": 0.0, "key": 0.0, "weather": 0.0, "cold": 0.0}


def spread_index(lg, games):
    """{game id: home spread at the first look of the week (median book)}."""
    path = os.path.join(sd.DATA, "odds_history", f"{ef.SPORTS[lg]}_spreads.jsonl.gz")
    if not os.path.exists(path):
        return {}
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    ready = ef.ready_at(games, lg)
    out = {}
    with gzip.open(path, "rt") as f:
        for x in f:
            r = json.loads(x)
            if "b" not in r:
                continue
            t = ef._t(r["t"])
            days = (t - ef._t(r["snap"])).total_seconds() / 86400
            if not 1.5 <= days < 7.5:
                continue
            pts = [v[0] for v in r["b"].values() if v and v[0] is not None]
            if len(pts) < 2:
                continue
            line = statistics.median(pts)
            for d in (-1, 0, 1):
                for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), []):
                    if abs((ef._t(g["start"]) - t).total_seconds()) > 14 * 3600:
                        continue
                    if not ef.fair(ready, g["id"], g["start"], days):
                        continue                    # (posted before last week's games ended - 10/1 audit)
                    if sd._same(g.get("home_name") or "", r["h"]) and sd._same(g.get("away_name") or "", r["a"]):
                        v = (days, line)
                    elif sd._same(g.get("home_name") or "", r["a"]) and sd._same(g.get("away_name") or "", r["h"]):
                        v = (days, -line)
                    else:
                        continue
                    if g["id"] not in out or days > out[g["id"]][0]:
                        out[g["id"]] = v            # the earliest fair look
    return out


def history(games, lg):
    """Per game, per team: win streak (+) / losing streak (-), cover streak at the closing spread, season games so
    far, season point diff per game, last-3 point diff per game, met this opponent earlier this season."""
    fin = sm.finals(games, lg)
    season = lambda s: s[:4] if s[5:7] >= "07" else str(int(s[:4]) - 1)
    st = {}
    out = {}
    for g in fin:
        s = season(g["start"])
        row = {}
        for side, other in (("home", "away"), ("away", "home")):
            k = (s, g[side])
            h = st.get(k, {"streak": 0, "ats": 0, "pd": [], "opps": set()})
            pd = h["pd"]
            row[side] = {"streak": h["streak"], "ats": h["ats"], "games": len(pd),
                         "pd": (sum(pd) / len(pd)) if pd else None, "pd3": (sum(pd[-3:]) / len(pd[-3:])) if len(pd) >= 3 else None,
                         "met": g[other] in h["opps"]}
        out[g["id"]] = row
        m = float(g["home_score"]) - float(g["away_score"])
        try:
            spr = float(g["spread_home"])
        except (KeyError, ValueError, TypeError):
            spr = None
        for side, mg, sp in (("home", m, spr), ("away", -m, -spr if spr is not None else None)):
            k = (s, g[side])
            h = st.setdefault(k, {"streak": 0, "ats": 0, "pd": [], "opps": set()})
            h["streak"] = (max(h["streak"], 0) + 1) if mg > 0 else (min(h["streak"], 0) - 1)
            if sp is not None and mg + sp != 0:
                c = mg + sp > 0
                h["ats"] = (max(h["ats"], 0) + 1) if c else (min(h["ats"], 0) - 1)
            h["pd"].append(mg)
            h["opps"].add(g["away" if side == "home" else "home"])
    return out


def coaches(lg, games):
    """{(season, team id): (first season with this team, head-coach seasons before, mid-season change)}."""
    out = {}
    if lg == "nfl":
        import sports_coach_history as ch
        hist = ch.load()
        exp = ch.experience(hist, "nfl")
        names = {}
        for g in games.values():
            for side in ("home", "away"):
                names.setdefault(g[side], g.get(side + "_name") or "")
        for (team, s), (coach, prior, first, mid) in exp.items():
            for tid, nm in names.items():
                if nm and sd._same(nm, team):
                    out[(str(s), tid)] = (first, prior, mid)
    else:
        try:
            import sports_coach_changes as cc
            rows = cc.hires(None, ("ncaaf",))
        except Exception as e:                         # noqa: BLE001
            print("no college coaching data:", str(e)[:60])
            return out
        ids = {}
        for g in games.values():
            for side in ("home", "away"):
                if g.get(side + "_name"):
                    ids.setdefault(cc._norm(g[side + "_name"]), g[side])
        for r in rows:
            tid = ids.get(cc._norm(r["team"]))
            if tid:
                out[(str(r["season"]), tid)] = (True, 0 if r["first_time"] else 5, False)
    return out


def build(lg):
    games = sd.load_games(lg)
    import early_dog_studies as eds
    looks = eds.match_all(lg, games)
    spreads = spread_index(lg, games)
    hist = history(games, lg)
    coach = coaches(lg, games)
    lastg = ef.last_games(games, lg)
    ready = ef.ready_at(games, lg)
    try:
        import sports_players as sp
        keys = sp.key_edges(games, sp.load())
    except Exception:                                   # noqa: BLE001
        keys = {}
    rows = []
    for season in ef.SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        sm.KEY_EDGE = {}
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if not lo <= g["start"] < hi:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            if hs == as_:
                continue
            fb = {**f, **BLIND}
            own = sm.own_p(p, fb)
            ours = sum(a * b for a, b in zip(p["sw"], sm._spread_x(fb))) if "sw" in p else None
            lk = sorted((x for x in looks.get(g["id"], []) if ef.fair(ready, g["id"], g["start"], x[0])), key=lambda x: -x[0])
            first = lk[0] if lk and lk[0][0] >= 1.5 else None
            sp_ = spreads.get(g["id"])
            if not first and not sp_:
                continue
            et = ef._t(g["start"]).astimezone(ET)
            night = "monday" if et.weekday() == 0 else "thursday" if et.weekday() == 3 else \
                "sunday night" if et.weekday() == 6 and et.hour >= 19 else None
            try:
                ih, ia = int(float(g.get("inj_home") or 0)), int(float(g.get("inj_away") or 0))
            except ValueError:
                ih = ia = 0
            for side, other, sg in (("home", "away", 1), ("away", "home", -1)):
                mg = (hs - as_) * sg
                r = {"gid": g["id"], "tid": g[side], "oid": g[other], "start": g["start"],
                     "season": season, "side": side, "won": mg > 0, "neutral": str(g.get("neutral")) == "1",
                     "intl": str(g.get("intl")) == "1", "night": night, "month": int(g["start"][5:7])}
                if first:
                    i = 1 if side == "home" else 2
                    pa, pb = 1 / ef._dec(first[1]), 1 / ef._dec(first[2])
                    mk = pa / (pa + pb) if side == "home" else pb / (pa + pb)
                    r.update(ml=first[i], ml_gap=(own if side == "home" else 1 - own) - mk)
                try:
                    r["ml_close"] = int(float(g[f"ml_{side}"]))
                except (KeyError, ValueError, TypeError):
                    r["ml_close"] = None
                try:
                    r["sp_close"] = float(g["spread_home"]) * sg
                except (KeyError, ValueError, TypeError):
                    r["sp_close"] = None
                if sp_:
                    ln = sp_[1] * sg
                    if mg + ln != 0:
                        r.update(line=ln, cover=mg + ln > 0,
                                 sp_edge=(sg * ours + ln) if ours is not None else None)
                me, them = hist.get(g["id"], {}).get(side, {}), hist.get(g["id"], {}).get(other, {})
                s_ = str(season)
                r.update(streak=me.get("streak", 0), ostreak=them.get("streak", 0), ats=me.get("ats", 0),
                         oats=them.get("ats", 0), games=me.get("games", 0), pd=me.get("pd"), pd3=me.get("pd3"),
                         met=me.get("met", False),
                         coach=coach.get((s_, g[side])), ocoach=coach.get((s_, g[other])),
                         inj=(ia - ih) * sg,                                 # + = the OTHER side has more hurt
                         key=keys.get(g["id"], 0.0) * sg,
                         rest=lastg.get(g["id"], {}).get(side, (None, None))[0],
                         orest=lastg.get(g["id"], {}).get(other, (None, None))[0],
                         last=lastg.get(g["id"], {}).get(side, (None, None))[1])
                rows.append(r)
    return rows


def grade_ml(rows):
    rows = [r for r in rows if r.get("ml") is not None and 100 <= r["ml"] <= 600]
    if not rows:
        return None
    n = len(rows)
    roi = sum((ef._dec(r["ml"]) - 1) if r["won"] else -1 for r in rows) / n
    by = {}
    for r in rows:
        by.setdefault(r["season"], []).append((ef._dec(r["ml"]) - 1) if r["won"] else -1)
    up = sum(1 for v in by.values() if sum(v) > 0)
    return {"n": n, "rate": round(sum(r["won"] for r in rows) / n, 3),
            "said": round(sum(1 / ef._dec(r["ml"]) for r in rows) / n, 3), "roi": round(roi, 3), "up": f"{up}/{len(by)}",
            "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}


def grade_sp(rows):
    rows = [r for r in rows if r.get("cover") is not None]
    if not rows:
        return None
    n = len(rows)
    roi = sum((10 / 11) if r["cover"] else -1 for r in rows) / n
    by = {}
    for r in rows:
        by.setdefault(r["season"], []).append((10 / 11) if r["cover"] else -1)
    up = sum(1 for v in by.values() if sum(v) > 0)
    return {"n": n, "rate": round(sum(r["cover"] for r in rows) / n, 3), "said": 0.524, "roi": round(roi, 3),
            "up": f"{up}/{len(by)}", "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}


def angles():
    """name -> test(row). Each runs plain and with the engine agreeing."""
    A = {}
    A["1 win streak 3+"] = lambda r: r["streak"] >= 3
    A["1 opponent on a 3+ win streak"] = lambda r: r["ostreak"] >= 3
    A["2 losing streak 3+"] = lambda r: r["streak"] <= -3
    A["2 opponent on a 3+ losing streak"] = lambda r: r["ostreak"] <= -3
    A["3 covered 3+ straight"] = lambda r: r["ats"] >= 3
    A["3 failed to cover 3+ straight"] = lambda r: r["ats"] <= -3
    A["4 first 3 games of the season"] = lambda r: r["games"] < 3
    A["5 hot: last 3 games 7+ pts better than season"] = lambda r: r["pd3"] is not None and r["games"] >= 5 and r["pd3"] - r["pd"] >= 7
    A["5 cold: last 3 games 7+ pts worse than season"] = lambda r: r["pd3"] is not None and r["games"] >= 5 and r["pd3"] - r["pd"] <= -7
    A["6 coach's first season with the team"] = lambda r: r["coach"] is not None and r["coach"][0]
    A["6 opponent coach's first season"] = lambda r: r["ocoach"] is not None and r["ocoach"][0]
    A["7 first-time head coach (0 years before)"] = lambda r: r["coach"] is not None and r["coach"][1] == 0
    A["7 veteran coach (8+ yrs) vs a first-timer"] = lambda r: (r["coach"] is not None and r["coach"][1] >= 8
                                                                and r["ocoach"] is not None and r["ocoach"][1] == 0)
    A["8 HINDSIGHT: opponent 3+ more players hurt"] = lambda r: r["inj"] >= 3
    A["8 HINDSIGHT: we have 3+ more hurt"] = lambda r: r["inj"] <= -3
    A["9 HINDSIGHT: QB / key starter edge ours"] = lambda r: r["key"] >= 0.5
    A["9 HINDSIGHT: QB / key starter edge theirs"] = lambda r: r["key"] <= -0.5
    A["10 Monday night"] = lambda r: r["night"] == "monday"
    A["10 Thursday night"] = lambda r: r["night"] == "thursday"
    A["10 Sunday night"] = lambda r: r["night"] == "sunday night"
    A["11 out of the country"] = lambda r: r["intl"]
    A["12 rematch (met earlier this season)"] = lambda r: r["met"]
    A["13 off a bye vs a team that played"] = lambda r: (r["rest"] or 0) >= 13 and (r["orest"] or 99) <= 8
    A["13 short week vs a rested team"] = lambda r: (r["rest"] or 99) <= 5 and (r["orest"] or 0) >= 7
    A["14 blown out last week (17+)"] = lambda r: r["last"] is not None and r["last"] <= -17
    A["14 blew someone out last week (17+)"] = lambda r: r["last"] is not None and r["last"] >= 17
    A["15 losing record, priced up vs a winning team"] = lambda r: (r["pd"] is not None and r["games"] >= 4 and r["pd"] < 0
                                                                   and r["streak"] <= 0)
    return A


def main():
    rep = {}
    A = angles()
    for lg in ("nfl", "ncaaf"):
        rows = build(lg)
        print(f"\n===================== {lg.upper()}: {len(rows)} sides "
              f"({sum(1 for r in rows if r.get('ml') is not None and 100 <= r['ml'] <= 600)} dogs with an early price, "
              f"{sum(1 for r in rows if r.get('cover') is not None)} with an early spread)")
        out = {}
        base_ml, base_sp = grade_ml(rows), grade_sp(rows)
        print(f"   baseline: dogs ROI {base_ml['roi']:+.1%} | spreads cover {base_sp['rate']:.1%}" if base_sp else
              f"   baseline: dogs ROI {base_ml['roi']:+.1%} | no spreads yet")
        for name, t in A.items():
            sel = [r for r in rows if t(r)]
            res = {"ML dog": grade_ml(sel),
                   "ML dog + engine likes": grade_ml([r for r in sel if (r.get("ml_gap") or -1) >= .04]),
                   "spread": grade_sp(sel),
                   "spread + engine 2+ pts": grade_sp([r for r in sel if (r.get("sp_edge") or -99) >= 2])}
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
    with open("results/early_round2.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
