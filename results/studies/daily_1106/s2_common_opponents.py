"""S2 - FOOTBALL: COMMON OPPONENTS (the 'transitive' read the public loves - "they beat X by 30, we only beat X by 3"),
college football (Saturday) + the NFL. Never studied before (no 'common opponent' in SPORTS_FINDINGS).
For a game A vs B: every opponent C both teams played EARLIER THIS SEASON (not each other); each team's margin vs C
adjusted for the site (home -2.5 / road +2.5 / neutral 0), averaged per team -> TRANS = the dog's average minus the
favorite's (+ = the dog did better against the same teams). Knowable before the game (finished games only).
Cells: dogs +100..+350 / favorites -101..-150 by TRANS band, at the CLOSE (2016-26) and at the paid history's FIRST FAIR
number (2020-26 - tools/early_football_study.ready_at / fair, the median book). Also ATS at the close.
Train: close 2016-22 / first fair 2020-23; held out each newer season apart."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

HFA = 2.5
for lg in ("ncaaf", "nfl"):
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    tl = lib.team_log(allf)
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2016]
    xby = {x["id"]: x for x in lib.load_football(lg)}
    C = lib.Cells()
    seen_n = 0
    for g in fin:
        res = {}
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            vs = {}
            for x in lib.before(tl, t, g["start"]):
                if x["season"] != g["season"]:
                    continue
                opp = x["away"] if x["home"] == t else x["home"]
                if opp == o:
                    continue
                m = (x["hs"] - x["as"]) if x["home"] == t else (x["as"] - x["hs"])
                adj = 0 if x["neutral"] else (-HFA if x["home"] == t else HFA)
                vs.setdefault(opp, []).append(m + adj)
            res[t] = vs
        common = set(res[g["home"]]) & set(res[g["away"]])
        if not common:
            continue
        seen_n += 1
        avg = lambda t: sum(sum(res[t][c]) / len(res[t][c]) for c in common) / len(common)   # noqa: E731
        trans_home = avg(g["home"]) - avg(g["away"])
        for side, team, opp, o_close, won, home in lib.sides(g):
            tr = trans_home if side == "home" else -trans_home
            band = ("dog" if lib.dog_band(o_close) else "fav" if lib.fav_band(o_close) else None)
            cut = "+14 or more" if tr >= 14 else "+7..+14" if tr >= 7 else "-7..+7" if tr > -7 else "-14..-7" if tr > -14 else "-14 or less"
            n_c = "1 common" if len(common) == 1 else "2+ common"
            s = g["season"]
            if band:
                p = lib.profit(won, lib.dec(o_close))
                C.add(f"{lg} close {band} TRANS {cut}", s, p)
                C.add(f"{lg} close {band} TRANS {cut} ({n_c})", s, p)
                if g["start"][5:7] in ("10", "11", "12"):
                    C.add(f"{lg} close {band} TRANS {cut} (Oct-Dec)", s, p)
            a = lib.ats(g, side)
            if a is not None and g["sp"] is not None:
                C.add(f"{lg} ATS TRANS {cut}", s, a)
            ep = lib.early_price(xby, g["id"], side)
            if ep:
                am, d = ep
                eb = "dog" if lib.dog_band(am) else "fav" if lib.fav_band(am) else None
                if eb:
                    C.add(f"{lg} FIRST FAIR {eb} TRANS {cut}", s + 10000, lib.profit(won, d))
    print(lg, "games with a common opponent:", seen_n)

    def split(k):
        return ((12020, 12023), [12024, 12025, 12026]) if "FIRST FAIR" in k else ((2016, 2022), [2023, 2024, 2025, 2026])
    C.dump(f"s2_{lg}", f"S2 {lg.upper()} COMMON OPPONENTS (TRANS = the side's site-adjusted margin vs the shared opponents minus "
                       f"the other side's; first-fair rows carry season+10000)", split)
