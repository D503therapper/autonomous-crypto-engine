"""S8 - COMMON OPPONENTS in the NBA / NHL / college hoops (the S2 football read): TRANS = the side's site-adjusted
margin vs the opponents both teams played earlier this season minus the other side's (home edge NBA / college hoops
2.5 pts, NHL 0.25 goals); 3+ common opponents. Dogs +100..+350 / favorites -101..-150 at the close, ATS (hoops).
S9 - NHL: THE GOALIE WHO GOT CHASED LAST TIME OUT (never studied): the team's last starter gave up 4+ on 22 or fewer
shots (or 5+ on 25 or fewer) - pulled or should have been; the team's next game (within 4 days), its side at the close
and ESPN's open, split by who starts tonight's projection (sports_players.projected_starter - knowable at 8 AM).
Train: NBA / NHL 2016-22, college hoops 2018-22; held out each newer season apart."""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import sports_players as sp  # noqa: E402

# ---------------- S8
HFA = {"nba": 2.5, "ncaab": 2.5, "nhl": 0.25}
CUT = {"nba": (6, 12), "ncaab": (8, 16), "nhl": (0.75, 1.5)}
for lg in ("nba", "nhl", "ncaab"):
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    tl = lib.team_log(allf)
    lo = 2018 if lg == "ncaab" else 2016
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= lo]
    C = lib.Cells()
    a, b = CUT[lg]
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
                vs.setdefault(opp, []).append(m + (0 if x["neutral"] else (-HFA[lg] if x["home"] == t else HFA[lg])))
            res[t] = vs
        common = set(res[g["home"]]) & set(res[g["away"]])
        if len(common) < 3:
            continue
        avg = lambda t: sum(sum(res[t][c]) / len(res[t][c]) for c in common) / len(common)   # noqa: E731
        th = avg(g["home"]) - avg(g["away"])
        for side, team, opp, o_close, won, home in lib.sides(g):
            tr = th if side == "home" else -th
            cut = f"+{b} or more" if tr >= b else f"+{a}..+{b}" if tr >= a else "middle" if tr > -a else f"-{b}..-{a}" if tr > -b else f"-{b} or less"
            s = g["season"]
            if lib.dog_band(o_close):
                C.add(f"{lg} close dog TRANS {cut}", s, lib.profit(won, lib.dec(o_close)))
            if lib.fav_band(o_close):
                C.add(f"{lg} close fav TRANS {cut}", s, lib.profit(won, lib.dec(o_close)))
            if lg != "nhl":
                p = lib.ats(g, side)
                if p is not None:
                    C.add(f"{lg} ATS TRANS {cut}", s, p)
    C.dump(f"s8_{lg}", f"S8 {lg.upper()} COMMON OPPONENTS (3+ shared)", (lo, 2022), [2023, 2024, 2025, 2026])

# ---------------- S9
rows = [r for r in sp.load()["nhl"] if r.get("role") == "G"]
by_gt = {(r["gid"], r["team"]): r for r in rows}
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2016]
C = lib.Cells()
for g in fin:
    for side, team, opp, o_close, won, home in lib.sides(g):
        prev = lib.before(tl, team, g["start"], 1)
        if not prev or prev[-1]["season"] != g["season"] or lib.days_between(prev[-1]["start"], g["start"]) > 4:
            continue
        r = by_gt.get((prev[-1]["id"], team))
        if not r:
            continue
        sa, ga = float(r["sa"] or 0), float(r["ga"] or 0)
        chased = (ga >= 4 and sa <= 22) or (ga >= 5 and sa <= 25)
        trows = [x for x in by_team[team] if x["start"] < g["start"]]
        proj = sp.projected_starter(trows, team, g["start"])
        cells = ["S9 control: the last starter not chased"] if not chased else \
            ["S9 the last starter got CHASED", "S9 chased, projected AGAIN tonight" if proj == r["player"] else
             "S9 chased, projected a different goalie"]
        s = g["season"]
        o_open = g["oh"] if side == "home" else g["oa"]
        for c in cells:
            if lib.dog_band(o_close):
                C.add(f"{c} | close dog", s, lib.profit(won, lib.dec(o_close)))
            if lib.fav_band(o_close):
                C.add(f"{c} | close fav", s, lib.profit(won, lib.dec(o_close)))
            if o_open and s >= 2023 and lib.dog_band(o_open):
                C.add(f"{c} | OPEN dog", s, lib.profit(won, lib.dec(o_open)))
            if o_open and s >= 2023 and lib.fav_band(o_open):
                C.add(f"{c} | OPEN fav", s, lib.profit(won, lib.dec(o_open)))
        # the side FACING a team whose goalie got chased
        if chased:
            o_won = not won
            o_c = g["mla"] if side == "home" else g["mlh"]
            if lib.dog_band(o_c):
                C.add("S9 FACING a team whose goalie got chased | close dog", s, lib.profit(o_won, lib.dec(o_c)))
            if lib.fav_band(o_c):
                C.add("S9 FACING a team whose goalie got chased | close fav", s, lib.profit(o_won, lib.dec(o_c)))
C.dump("s9", "S9 NHL: the goalie who got chased last time out - his team's next game", (2016, 2022), [2023, 2024, 2025, 2026])
