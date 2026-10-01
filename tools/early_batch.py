"""EARLY STUDIES #5-#20 (10/1, the owner: "20 studies, one by one - stop when one finds the edge for the early value
play"). All on the odds history, fair prices only (posted after both teams' last games), a NORMAL book's price (the
middle of the books - the owner: no line shopping), graded on wins / covers at the price bet. A study PASSES only if:
80+ bets, +3% or better overall, the last 3 seasons + this one +3% or better on 40+ bets, up in 2 of 2023-25, and
this season not caved in. Runs them in order and stops at the first that passes. Saves results/early_batch.json."""
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402

CACHE = os.path.join(os.environ.get("EARLY_CACHE", "/tmp"), "early_batch_{lg}.pkl")
SP = 1 + 10 / 11


def novig(h, a):
    ph, pa = 1 / ef._dec(h), 1 / ef._dec(a)
    return ph / (ph + pa)


def build(lg):
    path = CACHE.format(lg=lg)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    import early_move_model as mm
    import early_overreaction as eo
    games = sd.load_games(lg)
    rows = mm.build(lg)
    looks = eo.all_looks(lg, games, "h2h")
    for r in rows:
        ls = sorted((x for x in looks.get(r["gid"], []) if x[1] and x[0] >= 0.05), key=lambda x: -x[0])
        home = r["side"] == "home"
        r["path"] = [(d, v[0] if home else 1 - v[0], v[1] if home else v[2], v[2] if home else v[1]) for d, _, v in ls]
        g = games[r["gid"]]
        r["close_ml"] = r.get("ml_close")
        r["hs_as"] = (float(g["home_score"]), float(g["away_score"]))
    # season-to-date market errors per team (from the CLOSING prices of earlier games that season)
    fin = sorted((g for g in games.values() if g.get("status") == "final" and g.get("start")), key=lambda g: g["start"])
    season = lambda s: int(s[:4]) if int(s[5:7]) >= 7 else int(s[:4]) - 1
    acc, before = {}, {}
    for g in fin:
        s = season(g["start"])
        for side in ("home", "away"):
            h = acc.get((s, g[side]), {"ml": [], "ats": []})
            before[(g["id"], g[side])] = {"ml": list(h["ml"]), "ats": list(h["ats"])}
        try:
            m = float(g["home_score"]) - float(g["away_score"])
        except (TypeError, ValueError):
            continue
        for side, sg in (("home", 1), ("away", -1)):
            h = acc.setdefault((s, g[side]), {"ml": [], "ats": []})
            try:
                o = int(float(g[f"ml_{side}"]))
                h["ml"].append((ef._dec(o) - 1) if m * sg > 0 else -1)
            except (KeyError, TypeError, ValueError):
                pass
            try:
                h["ats"].append(m * sg + float(g["spread_home"]) * sg)
            except (KeyError, TypeError, ValueError):
                pass
    for r in rows:
        b = before.get((r["gid"], r["tid"]), {"ml": [], "ats": []})
        ob = before.get((r["gid"], r["oid"]), {"ml": [], "ats": []})
        r["ml_roi_td"] = (sum(b["ml"]) / len(b["ml"])) if len(b["ml"]) >= 4 else None
        r["ats_td"] = (sum(b["ats"]) / len(b["ats"])) if len(b["ats"]) >= 4 else None
        r["ats_l3"] = (sum(b["ats"][-3:]) / 3) if len(b["ats"]) >= 3 else None
        r["o_ats_td"] = (sum(ob["ats"]) / len(ob["ats"])) if len(ob["ats"]) >= 4 else None
    with open(path, "wb") as f:
        pickle.dump(rows, f)
    return rows


# ------------------------------------------------------------------ grading
def ml_bet(r, look=0):
    """(decimal price, won) betting this side's moneyline at fair look #look (0 = the first)."""
    if len(r["path"]) <= look:
        return None
    o = r["path"][look][2]
    if not -150 <= o <= 400:
        return None
    return ef._dec(o), r["won"]


def sp_bet(r):
    return (SP, r["cover"]) if r.get("cover") is not None else None


def grade(bets):
    """bets: [(season, decimal, won)]."""
    if not bets:
        return None
    by = {}
    for s, d, w in bets:
        by.setdefault(s, []).append((d - 1) if w else -1)
    n = len(bets)
    last = [x for s, v in by.items() if s >= 2023 for x in v]
    return {"n": n, "won": round(sum(w for _, _, w in bets) / n, 3), "roi": round(sum(x for v in by.values() for x in v) / n, 3),
            "last3_and_now": [len(last), round(sum(last) / len(last), 3) if last else None],
            "by": {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}}


def passes(gr):
    """(and then by hand: the cutoffs next to it have to hold too - study 7's '3+' passed alone and its neighbors
    didn't: a lucky cut, not an edge)"""
    return _passes(gr)


def _passes(gr):
    if not gr or gr["n"] < 80 or gr["roi"] < 0.03:
        return False
    ln, lr = gr["last3_and_now"]
    if ln < 40 or lr is None or lr < 0.03:
        return False
    up = sum(1 for s in (2023, 2024, 2025) if s in gr["by"] and gr["by"][s][1] > 0)
    if up < 2:
        return False
    now = gr["by"].get(2026)
    return not (now and now[0] >= 8 and now[1] < -0.25)


def bets(rows, test, how):
    out = []
    for r in rows:
        try:
            if not test(r):
                continue
        except (TypeError, KeyError, IndexError):
            continue
        b = how(r)
        if b:
            out.append((r["season"], b[0], b[1]))
    return out


# ------------------------------------------------------------------ the studies
def mv(r, a, b):
    """win-% points this side's price came IN between fair looks a and b (+ = toward it)."""
    return (r["path"][b][1] - r["path"][a][1]) * 100


def hold(r):
    d1, d2 = ef._dec(r["path"][0][2]), ef._dec(r["path"][0][3])
    return 1 / d1 + 1 / d2 - 1


def studies():
    dog = lambda r: r["path"] and r["path"][0][2] >= 100
    fav = lambda r: r["path"] and r["path"][0][2] < 100
    S = []
    S.append(("5 high-hold markets (books unsure) - dogs at the first look",
              [("hold 6%+ dogs", lambda r: dog(r) and hold(r) >= .06, ml_bet), ("hold under 4% dogs", lambda r: dog(r) and hold(r) < .04, ml_bet),
               ("hold 6%+ favorites", lambda r: fav(r) and hold(r) >= .06, ml_bet)]))
    S.append(("6 the buyback: moved one way early, then back (bet the side it came back to, at the 3rd look)",
              [("back 2+ after 2+ away", lambda r: len(r["path"]) >= 3 and mv(r, 0, 1) <= -2 and mv(r, 1, 2) >= 2, lambda r: ml_bet(r, 2)),
               ("back 3+ after 3+ away", lambda r: len(r["path"]) >= 3 and mv(r, 0, 1) <= -3 and mv(r, 1, 2) >= 3, lambda r: ml_bet(r, 2))]))
    S.append(("7 steady steam: in toward a side early AND still coming (bet it at the 3rd look)",
              [("2+ then 1+ more", lambda r: len(r["path"]) >= 3 and mv(r, 0, 1) >= 2 and mv(r, 1, 2) >= 1, lambda r: ml_bet(r, 2)),
               ("3+ early, bet at the 2nd look", lambda r: len(r["path"]) >= 2 and mv(r, 0, 1) >= 3, lambda r: ml_bet(r, 1))]))
    S.append(("8 the market keeps underrating a team (its moneyline ROI so far this season)",
              [("ROI to date +30%+", lambda r: (r["ml_roi_td"] or -9) >= .3, ml_bet),
               ("ROI to date -30% or worse (fade: bet them anyway?)", lambda r: r["ml_roi_td"] is not None and r["ml_roi_td"] <= -.3, ml_bet),
               ("ROI to date +30%+ as a dog", lambda r: (r["ml_roi_td"] or -9) >= .3 and dog(r), ml_bet)]))
    S.append(("9 beating the spread all season (avg margin vs the closing spread, 4+ games)",
              [("+5 pts/game, spread", lambda r: (r["ats_td"] or -99) >= 5, sp_bet), ("-5 pts/game, spread", lambda r: (r["ats_td"] or 99) <= -5, sp_bet),
               ("+5 pts/game, moneyline", lambda r: (r["ats_td"] or -99) >= 5, ml_bet)]))
    S.append(("10 the last 3 games vs the spread",
              [("+7 pts/game last 3, spread", lambda r: (r["ats_l3"] or -99) >= 7, sp_bet), ("-7 pts/game last 3, spread", lambda r: (r["ats_l3"] or 99) <= -7, sp_bet),
               ("-7 last 3, moneyline dog", lambda r: (r["ats_l3"] or 99) <= -7 and dog(r), ml_bet)]))
    S.append(("11 the market's season error, us vs them (ours beating the spread, theirs not)",
              [("us +3, them -3, spread", lambda r: (r["ats_td"] or -99) >= 3 and (r["o_ats_td"] or 99) <= -3, sp_bet),
               ("us -3, them +3, spread", lambda r: (r["ats_td"] or 99) <= -3 and (r["o_ats_td"] or -99) >= 3, sp_bet),
               ("us +3, them -3, moneyline dog", lambda r: (r["ats_td"] or -99) >= 3 and (r["o_ats_td"] or 99) <= -3 and dog(r), ml_bet)]))
    S.append(("12 short favorites early (-101 to -125)",
              [("first look", lambda r: r["path"] and -125 <= r["path"][0][2] <= -101, ml_bet)]))
    S.append(("13 pick'em spreads early (+/-2.5 or less)",
              [("spread", lambda r: r.get("line") is not None and abs(r["line"]) <= 2.5, sp_bet)]))
    S.append(("14 big spreads early (+/-14 or more): the dog side",
              [("getting 14+", lambda r: (r.get("line") or 0) >= 14, sp_bet), ("getting 21+", lambda r: (r.get("line") or 0) >= 21, sp_bet)]))
    S.append(("15 a dog whose price already came in 2+ pts by the 2nd look AND the engine likes it (bet the 2nd look)",
              [("", lambda r: len(r["path"]) >= 2 and dog(r) and mv(r, 0, 1) >= 2 and (r.get("ml_gap") or -1) >= .02, lambda r: ml_bet(r, 1))]))
    S.append(("16 the line moved AGAINST the engine's read by the 2nd look (does the engine know better?)",
              [("engine likes, price went out 2+", lambda r: len(r["path"]) >= 2 and (r.get("ml_gap") or -1) >= .04 and mv(r, 0, 1) <= -2, lambda r: ml_bet(r, 1))]))
    MAXV = lambda r: (r.get("night") == "monday" and dog(r)) or ((r.get("rest") or 0) >= 13 and (r.get("orest") or 99) <= 8 and dog(r)) \
        or ((r.get("last") or 0) >= 17 and dog(r)) or (r["side"] == "away" and (r["ctx"]["home_tz"] or -9) >= -5
                                                       and (r["ctx"]["game_tz"] or 0) <= -7 and dog(r))
    FADE = lambda r: (r.get("coach") or (False,))[0] or (r.get("streak") or 0) <= -3 or \
        (r.get("pd3") is not None and r.get("pd") is not None and r.get("games", 0) >= 5 and r["pd3"] - r["pd"] <= -7)
    S.append(("17 the max-value dog spots together (Monday night, off a bye, blew someone out, East team flying West)",
              [("any of them", MAXV, ml_bet)]))
    S.append(("18 ...with the engine agreeing", [("engine +2", lambda r: MAXV(r) and (r.get("ml_gap") or -1) >= .02, ml_bet)]))
    S.append(("19 ...minus the fades (coach's 1st season, 3+ losing streak, ice cold)",
              [("no fades", lambda r: MAXV(r) and not FADE(r), ml_bet)]))
    S.append(("20 ...minus the fades AND the engine agreeing",
              [("no fades + engine +2", lambda r: MAXV(r) and not FADE(r) and (r.get("ml_gap") or -1) >= .02, ml_bet)]))
    return S


def main():
    data = {lg: build(lg) for lg in ("nfl", "ncaaf")}
    rep = {}
    start = int(os.environ.get("START") or 0)
    for name, variants in studies():
        if int(name.split()[0]) < start:
            continue
        rep[name] = {}
        found = []
        for lg, rows in data.items():
            for vname, test, how in variants:
                gr = grade(bets(rows, test, how))
                rep[name][f"{lg} {vname}"] = gr
                if passes(gr):
                    found.append((lg, vname, gr))
        print(f"study {name}: {'FOUND ' + str([(l, v) for l, v, _ in found]) if found else 'nothing'}", flush=True)
        if found:
            for lg, vname, gr in found:
                print("   ", lg, vname, gr)
            break
    with open("results/early_batch.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
