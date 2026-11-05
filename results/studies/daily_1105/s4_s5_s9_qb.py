"""S4 / S5 / S9 - THE QUARTERBACK SPOTS (data/sports/players/<lg>.csv - one QB row a team-game = the man who threw
the most passes; football game files for the close, the paid odds history's FIRST FAIR number as the second price).
  S4 NFL - a QB's FIRST CAREER START (never the team's top passer in any earlier game on file; 2018 on, so 2016-17
       are the buffer that catches veterans): the debut side ML (dog +100..+350 / fav -101..-300) and ATS, the side
       ACROSS it (facing the debut), week 1 vs later, rookie-age proxy n/a.
  S5 COLLEGE - THE STARTER MISSED THE LAST GAME: the starter = the team's top passer in most of its games this season
       (3+ games, a clear leader); his team's LAST game was thrown by someone else. Tonight (a) the backup again
       (his 2nd straight - the market saw one game of him) or (b) the starter back.
  S9 NFL - the same two cases in the NFL (the 10/8 backup's second start / 10/18 'known backup' / 10/30 fresh change
       were read on other cuts - here: the STARTER BACK after missing 1+, and the starter back after 2+).
Train 2018-22 (college / NFL), held out 2023 / 2024 / 2025 / 2026 apart. Pre-game knowable: the NFL / college starter
is named before kickoff (the box score is only the after-the-fact record of who it was - the rows are the cases where
the announced starter played)."""
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402


def run(lg):
    qb = {(r["gid"], r["team"]): r["player"] for r in csv.DictReader(open(f"data/sports/players/{lg}.csv"))}
    allf = [g for g in lib.all_finals(lg)]
    tl = lib.team_log(allf)
    fin = lib.finals(lg)
    xby = {x["id"]: x for x in lib.load_football(lg)}
    seen = set()                                             # every QB name seen as a top passer, in time order
    first_seen_season = {}
    order = sorted(fin + [g for g in allf if g["id"] not in {f["id"] for f in fin}], key=lambda g: g["start"])
    finid = {g["id"]: g for g in fin}
    C = lib.Cells()
    for g in order:
        gq = {t: qb.get((g["id"], t)) for t in (g["home"], g["away"])}
        if g["id"] in finid and g["season"] >= 2018 and g["stype"] == "2":
            fg = finid[g["id"]]
            for side, team, opp, o, won, home in lib.sides(fg):
                me = gq.get(team)
                if not me:
                    continue
                prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
                pq = [qb.get((x["id"], team)) for x in prev]
                tags = []
                if lg == "nfl" and me not in seen:
                    tags.append("S4 debut")
                    if not prev:
                        tags.append("S4 debut week1")
                    else:
                        tags.append("S4 debut after week1")
                opp_me = gq.get(opp)
                if lg == "nfl" and opp_me and opp_me not in seen:
                    tags.append("S4 FACING a debut")
                if len(pq) >= 3 and pq[-1]:
                    cnt = Counter(p for p in pq if p)
                    (st, n), = cnt.most_common(1)
                    clear = n >= 3 and n >= 0.6 * len(pq) and (len(cnt) < 2 or cnt.most_common(2)[1][1] < n)
                    if clear and pq[-1] != st:
                        miss = 0
                        for p in reversed(pq):
                            if p == st:
                                break
                            miss += 1
                        if me == st:
                            tags.append("STARTER BACK")
                            tags.append("STARTER BACK after 1" if miss == 1 else "STARTER BACK after 2+")
                        elif me == pq[-1]:
                            tags.append("BACKUP AGAIN")
                            tags.append("BACKUP AGAIN 2nd start" if miss == 1 else "BACKUP AGAIN 3rd+ start")
                pre = "S5 " if lg == "ncaaf" else ("S9 " if lg == "nfl" else "")
                for t in tags:
                    name = t if t.startswith("S4") else pre + t
                    s = g["season"]
                    band = "dog" if lib.dog_band(o) else "fav" if lib.fav_band(o, -300, -101) else None
                    if band:
                        C.add(f"{name} | close ML {band}", s, lib.profit(won, lib.dec(o)))
                    C.add(f"{name} | close ATS", s, lib.ats(fg, side))
                    ep = lib.early_price(xby, g["id"], side)
                    if ep:
                        b2 = "dog" if lib.dog_band(ep[0]) else "fav" if lib.fav_band(ep[0], -300, -101) else None
                        if b2:
                            C.add(f"{name} | first-fair ML {b2}", s, lib.profit(won, ep[1]))
                    # the side across (facing the spot)
                    oo = fg["mla"] if side == "home" else fg["mlh"]
                    oside = "away" if side == "home" else "home"
                    ob = "dog" if lib.dog_band(oo) else "fav" if lib.fav_band(oo, -300, -101) else None
                    if ob and not t.startswith("S4 FACING"):
                        C.add(f"{name} | ACROSS close ML {ob}", s, lib.profit(not won, lib.dec(oo)))
                    if not t.startswith("S4 FACING"):
                        C.add(f"{name} | ACROSS close ATS", s, lib.ats(fg, oside))
        for t, p in gq.items():
            if p:
                seen.add(p)
    return C


for lg in ("nfl", "ncaaf"):
    C = run(lg)
    C.dump(f"s4s5s9_{lg}", f"QB SPOTS - {lg} (train 2018-22, held 2023-26)", (2018, 2022), [2023, 2024, 2025, 2026])
