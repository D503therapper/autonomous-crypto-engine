"""11/20 daily studies S2-S5, S7-S9 - the facts the cards print that were never set against a price, from the game files
(ESPN's close at its own juice; regular season; a team's games THIS season before tonight, no look-ahead):
  S2  NHL the third period (goals for minus against in the 3rd, last 10)            - the card's "⏱️ third period" line
  S3  the closers elsewhere: NBA 4th quarter (last 10), college hoops 2nd half (last 5), football 2nd half (last 4)
  S4  the record against winning teams (opponents over .500 on the day they met), every league
  S5  scoring bursts: NHL 4+ goals in 3+ of the last 5; NBA 120+ scored / allowed in 3+ of the last 5 ("💣" / the
      Warriors' line under the pick 11/19)
  S7  NHL the game after giving up 6+ / scoring 6+
  S8  the total after both teams' last games sailed over (or under) their numbers - NHL / NBA / college hoops
  S9  college hoops: the game after a non-D1 tune-up
Cells are fixed before the run (no tuned cut). python results/studies/daily_1120/s_game.py [nhl nba ncaab nfl ncaaf]"""
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025, 2026]


def ls(x):
    try:
        return [int(float(v)) for v in str(x or "").split(",") if v.strip() != ""]
    except ValueError:
        return []


def load(lg):
    cache = os.path.join(lib.CACHE, f"_g1120_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = []
    for g in sm.finals(sd.load_games(lg), lg):
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        out.append({"id": g["id"], "start": g["start"], "season": lib.season(g["start"]), "home": g["home"], "away": g["away"],
                    "hs": hs, "as": as_, "mlh": lib.num(g.get("ml_home")), "mla": lib.num(g.get("ml_away")),
                    "sp": lib.num(g.get("spread_home")), "spho": lib.num(g.get("spread_home_odds")),
                    "spao": lib.num(g.get("spread_away_odds")), "total": lib.num(g.get("total")),
                    "ovo": lib.num(g.get("over_odds")), "uno": lib.num(g.get("under_odds")),
                    "neutral": str(g.get("neutral")) == "1", "stype": str(g.get("stype") or "2"),
                    "lh": ls(g.get("ls_home")), "la": ls(g.get("ls_away"))})
    out.sort(key=lambda x: x["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def part(g, team, lg):
    """(for, against) in the closing stretch of game g for team: NHL 3rd period, NBA / football 4th quarter... see LATE."""
    lh, la = g["lh"], g["la"]
    need = {"nhl": 3, "nba": 4, "ncaab": 2, "nfl": 4, "ncaaf": 4}[lg]
    if len(lh) < need or len(la) < need:
        return None
    if lg == "nhl":
        f, a = lh[2], la[2]
    elif lg == "nba":
        f, a = lh[3], la[3]
    elif lg == "ncaab":
        f, a = lh[1], la[1]
    else:
        f, a = lh[2] + lh[3], la[2] + la[3]
    return (f, a) if g["home"] == team else (a, f)


LATE = {"nhl": (10, 5), "nba": (10, 25), "ncaab": (5, 20), "nfl": (4, 21), "ncaaf": (4, 28)}   # (games back, the margin)
MIN_G = {"nhl": 10, "nba": 10, "ncaab": 5, "nfl": 4, "ncaaf": 4}


def run(lg):
    O = h.Out(f"s_game_{lg}", TRAIN, HELD)
    fin = load(lg)
    d1 = None
    if lg == "ncaab":
        try:
            d1 = sm.ncaab_d1(sd.load_games(lg) and [g for g in sm.finals(sd.load_games(lg), lg)])
        except Exception as e:  # noqa: BLE001
            O.p("no D1 set:", e)
    tl = {}
    rec = {}                                             # (season, team) -> [w, l] before tonight (built as we go)
    n_games = 0
    for g in fin:
        s = g["season"]
        reg = g["stype"] == "2"
        feats = {}
        for side, team, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            past = [x for x in tl.get(team, []) if x["season"] == s]
            f = {}
            # --- the closing stretch
            nb, cut = LATE[lg]
            last = past[-nb:]
            ps = [part(x, team, lg) for x in last]
            if len(last) == nb and all(ps):
                m = sum(a - b for a, b in ps)
                f["late"] = 1 if m >= cut else -1 if m <= -cut else 0
                w = sum(1 for a, b in ps if a > b)
                l_ = sum(1 for a, b in ps if a < b)
                f["late_w"] = 1 if w * 10 >= nb * 7 else -1 if l_ * 10 >= nb * 7 else 0
            # --- the record against winning teams
            vw = [x for x in past if x.get("opp_win_" + team)]
            if len(vw) >= (5 if lg in ("nhl", "nba") else 3) and len(past) >= MIN_G[lg]:
                w = sum(1 for x in vw if (x["hs"] > x["as"]) == (x["home"] == team))
                allw = sum(1 for x in past if (x["hs"] > x["as"]) == (x["home"] == team))
                f["vw"] = w / len(vw)
                f["allp"] = allw / len(past)
            # --- bursts
            if lg in ("nhl", "nba") and len(past) >= 5:
                pf = [(x["hs"], x["as"]) if x["home"] == team else (x["as"], x["hs"]) for x in past[-5:]]
                bar = 4 if lg == "nhl" else 120
                f["burst_f"] = sum(1 for a, b in pf if a >= bar) >= 3
                f["burst_a"] = sum(1 for a, b in pf if b >= bar) >= 3
            if lg == "nhl" and past:
                x = past[-1]
                a, b = (x["hs"], x["as"]) if x["home"] == team else (x["as"], x["hs"])
                f["gave6"], f["got6"] = b >= 6, a >= 6
            # --- the last game against its total
            if past and past[-1].get("total"):
                x = past[-1]
                f["tot_gap"] = x["hs"] + x["as"] - x["total"]
            # --- college hoops: the last game was a non-D1 tune-up
            if d1 is not None and past:
                x = past[-1]
                o_ = x["away"] if x["home"] == team else x["home"]
                f["tune"] = str(o_) not in d1
                f["me_d1"] = str(team) in d1
            feats[side] = f
        if reg and g["mlh"] and g["mla"] and g["hs"] != g["as"] and not (d1 is not None and (str(g["home"]) not in d1 or str(g["away"]) not in d1)):
            n_games += 1
            hw = g["hs"] > g["as"]
            for side, o, won in (("home", g["mlh"], hw), ("away", g["mla"], not hw)):
                f, fo = feats[side], feats["away" if side == "home" else "home"]
                b = h.band(o)
                pr = lib.profit(won, lib.dec(o))
                at = lib.ats(g, side)
                names = []
                if "late" in f:
                    names += [f"late margin {'+' if f['late'] > 0 else '-' if f['late'] < 0 else '0'}"]
                    if f["late"] > 0 and fo.get("late") == -1:
                        names.append("late closer vs fader")
                    if f["late"] < 0 and fo.get("late") == 1:
                        names.append("late fader vs closer")
                    if f["late_w"]:
                        names.append(f"late won 7of10 {'+' if f['late_w'] > 0 else '-'}")
                if "vw" in f:
                    if f["vw"] >= 0.6:
                        names.append("vs winners .600+")
                    if f["vw"] <= 0.3:
                        names.append("vs winners .300-")
                    if f["allp"] >= 0.6 and f["vw"] <= 0.35:
                        names.append("flat-track bully (.600+ overall, .350- vs winners)")
                    if f["allp"] <= 0.45 and f["vw"] >= 0.5:
                        names.append("plays up (.450- overall, .500+ vs winners)")
                    if "vw" in fo and f["vw"] - fo["vw"] >= 0.3:
                        names.append("vs winners .300+ better than the opponent")
                if f.get("burst_f"):
                    names.append("burst: scored the bar 3+ of 5")
                if fo.get("burst_a"):
                    names.append("burst: opponent allowed the bar 3+ of 5")
                if f.get("burst_a"):
                    names.append("burst: allowed the bar 3+ of 5")
                if f.get("gave6"):
                    names.append("gave up 6+ last game")
                if f.get("got6"):
                    names.append("scored 6+ last game")
                if fo.get("gave6"):
                    names.append("opponent gave up 6+ last game")
                if f.get("tune") and f.get("me_d1"):
                    names.append("off a non-D1 tune-up")
                    if fo.get("tune") is False:
                        names.append("off a non-D1 tune-up vs a team off a D1 game")
                for nm in ["ALL"] + names:
                    if b:
                        O.add(f"{nm} | {b}", s, pr, o)
                    if at is not None:
                        O.add(f"{nm} | ats", s, at)
            # totals
            fh, fa = feats["home"], feats["away"]
            if g["total"] and "tot_gap" in fh and "tot_gap" in fa and lg in ("nhl", "nba", "ncaab"):
                big = {"nhl": 2.0, "nba": 15.0, "ncaab": 12.0}[lg]
                tot = g["hs"] + g["as"]
                if tot != g["total"]:
                    po = lib.profit(tot > g["total"], lib.dec(g["ovo"] or -110))
                    pu = lib.profit(tot < g["total"], lib.dec(g["uno"] or -110))
                    O.add("TOTAL ALL | over", s, po)
                    O.add("TOTAL ALL | under", s, pu)
                    if fh["tot_gap"] >= big and fa["tot_gap"] >= big:
                        O.add("TOTAL both sailed over last game | over", s, po)
                        O.add("TOTAL both sailed over last game | under", s, pu)
                    if fh["tot_gap"] <= -big and fa["tot_gap"] <= -big:
                        O.add("TOTAL both sailed under last game | over", s, po)
                        O.add("TOTAL both sailed under last game | under", s, pu)
                    if fh["tot_gap"] > 0 and fa["tot_gap"] > 0:
                        O.add("TOTAL both over last game | under", s, pu)
                    if fh["tot_gap"] < 0 and fa["tot_gap"] < 0:
                        O.add("TOTAL both under last game | over", s, po)
        # --- after the game: stamp whether each opponent was a winning team on the day, then log
        for team, opp in ((g["home"], g["away"]), (g["away"], g["home"])):
            w, l_ = rec.get((s, opp), [0, 0])
            g["opp_win_" + team] = (w + l_) >= MIN_G[lg] and w > l_
        if g["hs"] != g["as"]:
            hw = g["hs"] > g["as"]
            for team, won in ((g["home"], hw), (g["away"], not hw)):
                r = rec.setdefault((s, team), [0, 0])
                r[0 if won else 1] += 1
        tl.setdefault(g["home"], []).append(g)
        tl.setdefault(g["away"], []).append(g)
    O.p(f"===== {lg}: {n_games} priced regular-season games; TRAIN {TRAIN} / HELD {HELD}")
    res = O.show(minn=40)
    O.p("--- NOTABLE (150+ rows, 5+ points off the band's base, the same sign in TRAIN and HELD)")
    for k, r in res.items():
        nm, bd = k.rsplit(" | ", 1)
        pool = res.get(("TOTAL ALL | " if nm.startswith("TOTAL") else "ALL | ") + bd)
        if not pool or nm in ("ALL", "TOTAL ALL") or r["all"]["n"] < 150 or not r["train"] or not r["held_all"]:
            continue
        d = [r[x]["roi"] - pool[x]["roi"] for x in ("all", "train", "held_all")]
        if abs(d[0]) >= 0.05 and d[1] * d[2] > 0:
            O.p("  *", lib.fmt(k, r))
    O.p("--- placebos (2,000 random same-size sets from the same band)")
    for k in sorted(O.c):
        if k.startswith(("ALL", "TOTAL ALL")) or len(O.c[k]) < 80:
            continue
        nm, bd = k.rsplit(" | ", 1)
        pool = ("TOTAL ALL | " if nm.startswith("TOTAL") else "ALL | ") + bd
        v = O.c[k]
        roi = sum(p for _, p, _ in v) / len(v)
        base = sum(p for _, p, _ in O.c[pool]) / len(O.c[pool])
        if abs(roi - base) >= 0.05:
            O.placebo(k, pool, fade=roi < base)
    O.save()


if __name__ == "__main__":
    for lg_ in (sys.argv[1:] or ["nhl", "nba", "ncaab", "nfl", "ncaaf"]):
        run(lg_)
