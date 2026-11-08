"""11/8 S2 / S10 / S3 - football (never studied - checked against every 'Not re-run' list; the 4th-quarter COMEBACK winner
and the BLOWN 4th-quarter lead (DEAD / WATCH before) change the result - these don't):
S2 NFL / S10 COLLEGE - THE COSMETIC MARGIN: last game's final margin vs its margin after 3 quarters, result unchanged.
   'made it look respectable' = trailed by 14+ after 3, closed 10+ in the 4th, still lost (the final flatters the loser);
   'let them back in'        = led by 14+ after 3, gave 10+ back in the 4th, still won (the final undersells the winner).
   A rating built on final margins (the market's power numbers, our Elo) over-rates the first and under-rates the second?
S3 NFL (college the second check) - THE WIN OVER A BACKUP QB: last game won by 14+ against a team whose top passer that
   day was NOT its main QB (the top passer in most of its earlier games this season, 2+ games); tonight's side as a
   favorite / dog / ATS - does the market over-credit a win over a backup?
Prices: the game files' close; the paid history's FIRST FAIR number (football). TRAIN 2018-22 / held 2023, 2024, 2025 / 2026."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2018, 2022), [2023, 2024, 2025, 2026]
C = lib.Cells()


def add_side(tag, g, side, o, won, s, xby):
    p = lib.profit(won, lib.dec(o))
    if -250 <= o <= -101:
        C.add(f"{tag} | fav -101..-250", s, p)
    if 100 <= o <= 350:
        C.add(f"{tag} | dog +100..+350", s, p)
    C.add(f"{tag} | ATS", s, lib.ats(g, side))
    ep = lib.early_price(xby, g["id"], side)
    if ep:
        if -250 <= ep[0] <= -101:
            C.add(f"{tag} | fav FIRST FAIR", s, lib.profit(won, ep[1]))
        if 100 <= ep[0] <= 350:
            C.add(f"{tag} | dog FIRST FAIR", s, lib.profit(won, ep[1]))


def qmarg(g, team):
    qh, qa = lib.quarters(g["ls_h"]), lib.quarters(g["ls_a"])
    if not qh or not qa or len(qh) < 4 or len(qa) < 4:
        return None
    m3 = sum(qh[:3]) - sum(qa[:3])
    return (m3, g["hs"] - g["as"]) if g["home"] == team else (-m3, g["as"] - g["hs"])


def passer_att(st, r):
    if r["group"] != "passing":
        return None
    try:
        return int(str(st.get("completions/passingAttempts", "0/0")).split("/")[1])
    except (ValueError, IndexError):
        return None


def bare(gid):
    return str(gid).split(":")[-1]


for lg in ("nfl", "ncaaf"):
    L = lg.upper()
    fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
    allf = lib.all_finals(lg)
    tl = lib.team_log(allf)
    fin_by = {g["id"]: g for g in lib.finals(lg)}
    try:
        xby = {x["id"]: x for x in lib.load_football(lg)}
    except Exception as e:  # noqa: BLE001
        print("no odds history", lg, e)
        xby = {}
    bx = lib.boxes(lg, passer_att)            # top passer per team-game (box scores 2021+)
    top = {}
    for gid, teams in bx.items():
        for t, pl in teams.items():
            if pl:
                pid, att = max(pl.items(), key=lambda kv: kv[1])
                if att >= 8:
                    top[(bare(gid), bare(t))] = pid
    for g in fin:
        for side, team, opp, o, won, home in lib.sides(g):
            prev = lib.before(tl, team, g["start"], 1)
            if not prev or prev[0]["season"] != g["season"] or prev[0]["stype"] != "2":
                continue
            lgm = fin_by.get(prev[0]["id"])
            k = "S2 NFL" if lg == "nfl" else "S10 NCAAF"
            if lgm:                                     # --- S2 / S10 the cosmetic margin
                q = qmarg(lgm, team)
                if q:
                    m3, mf = q
                    if m3 <= -14 and mf < 0 and mf - m3 >= 10:
                        add_side(f"{k} made it look respectable (down 14+ after 3, closed 10+, lost)", g, side, o, won, g["season"], xby)
                        if mf - m3 >= 14:
                            add_side(f"{k} ... respectable, closed 14+", g, side, o, won, g["season"], xby)
                    elif m3 >= 14 and mf > 0 and m3 - mf >= 10:
                        add_side(f"{k} let them back in (up 14+ after 3, gave 10+ back, won)", g, side, o, won, g["season"], xby)
                        if m3 - mf >= 14:
                            add_side(f"{k} ... let back in, gave 14+ back", g, side, o, won, g["season"], xby)
                    elif m3 <= -14 and mf < 0:
                        add_side(f"{k} control: down 14+ after 3, lost, closed <10", g, side, o, won, g["season"], xby)
                    elif m3 >= 14 and mf > 0:
                        add_side(f"{k} control: up 14+ after 3, won, gave <10 back", g, side, o, won, g["season"], xby)
            if lib.margin_g(prev[0], team) >= 14:      # --- S3 the win over a backup QB
                o_team = prev[0]["away"] if prev[0]["home"] == team else prev[0]["home"]
                tp = top.get((bare(prev[0]["id"]), bare(o_team)))
                if tp is None:
                    continue
                earlier = [x for x in lib.before(tl, o_team, prev[0]["start"]) if x["season"] == g["season"]]
                tops = [top.get((bare(x["id"]), bare(o_team))) for x in earlier]
                tops = [t for t in tops if t]
                if len(tops) < 2:
                    continue
                main, n = Counter(tops).most_common(1)[0]
                k3 = "S3 " + L
                if tp != main:
                    add_side(f"{k3} won by 14+ over a BACKUP QB last game", g, side, o, won, g["season"], xby)
                else:
                    add_side(f"{k3} control: won by 14+ over the MAIN QB last game", g, side, o, won, g["season"], xby)

C.dump("s2_s3_s10", "11/8 S2 / S3 / S10 football - closing prices + the first fair number; TRAIN 2018-22 / held 2023-2026",
       TRAIN, HELD)
