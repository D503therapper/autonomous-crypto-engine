"""11/8 S7b - the NBA favorite facing a star off a dud (S7x), cut five ways before any weight:
the star's ppg floor (15 / 18 / 22), the dud's depth (<35% / <30%, 15+ / 20+ shots), the dud team lost or won that game,
the favorite home / road, the month, the opponent off ANY loss (is it just 'the team off a loss'?), and the star's
season FG% (a 40% shooter's dud vs a 50% shooter's). Closing prices; TRAIN 2018-22 / held 2023-26 (box scores 2016-26)."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
C = lib.Cells()


def bare(x):
    return str(x).split(":")[-1]


def nba_val(st, r):
    try:
        fgm, fga = [int(x) for x in str(st.get("fieldGoalsMade-fieldGoalsAttempted", "")).split("-")]
        return (int(st.get("points") or 0), fgm, fga)
    except (ValueError, TypeError):
        return None


bx = lib.boxes("nba", nba_val)
by_tg = {}
for gid, teams in bx.items():
    for t, pl in teams.items():
        by_tg[(bare(gid), bare(t))] = pl
fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
tl = lib.team_log(lib.all_finals("nba"))


def fav_add(k, s, o, won):
    if -250 <= o <= -101:
        C.add(k + " | fav -101..-250", s, lib.profit(won, lib.dec(o)))
    if -150 <= o <= -101:
        C.add(k + " | fav -101..-150", s, lib.profit(won, lib.dec(o)))


for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        if not (-250 <= o <= -101):
            continue
        prev = [x for x in lib.before(tl, opp, g["start"]) if x["season"] == g["season"] and x["stype"] == "2"]
        if len(prev) < 5:
            continue
        pts, gp, fgm_s, fga_s = Counter(), Counter(), Counter(), Counter()
        for x in prev:
            for pid, v in (by_tg.get((bare(x["id"]), bare(opp))) or {}).items():
                pts[pid] += v[0]
                gp[pid] += 1
                fgm_s[pid] += v[1]
                fga_s[pid] += v[2]
        cand = [(pts[p] / gp[p], p) for p in pts if gp[p] >= 3]
        if not cand:
            continue
        ppg, star = max(cand)
        last = by_tg.get((bare(prev[-1]["id"]), bare(opp))) or {}
        v = last.get(star)
        opp_lost = not lib.won_g(prev[-1], opp)
        s = g["season"]
        fav_add("S7b base: every fav (opp star known)", s, o, won)
        fav_add(f"S7b base: opp off a {'loss' if opp_lost else 'win'}", s, o, won)
        if not v:
            fav_add("S7b opp star missed the last game", s, o, won)
            continue
        _, fgm, fga = v
        pct = fgm / fga if fga else 1
        sea = fgm_s[star] / fga_s[star] if fga_s[star] else 0
        for floor in (15, 18, 22):
            if ppg >= floor and fga >= 15 and pct < 0.35:
                fav_add(f"S7b dud <35% on 15+, star {floor}+ ppg", s, o, won)
        if ppg < 18:
            continue
        if fga >= 15 and pct < 0.35:
            k = "S7b [18+] dud <35% on 15+"
            fav_add(k, s, o, won)
            fav_add(k + (" - dud team LOST" if opp_lost else " - dud team WON"), s, o, won)
            fav_add(k + (" - fav at HOME" if home else " - fav on the ROAD"), s, o, won)
            fav_add(k + (" - Oct-Dec" if g["start"][5:7] in ("10", "11", "12") else " - Jan-Apr"), s, o, won)
            fav_add(k + (" - star a 47%+ shooter" if sea >= 0.47 else " - star under 47%"), s, o, won)
            if pct < 0.30:
                fav_add("S7b [18+] dud <30% on 15+", s, o, won)
            if fga >= 20:
                fav_add("S7b [18+] dud <35% on 20+", s, o, won)
        elif fga >= 15 and pct < 0.40:
            fav_add("S7b [18+] 35-40% on 15+ (near miss)", s, o, won)
        elif fga >= 15 and pct >= 0.50:
            fav_add("S7b [18+] 50%+ on 15+ (a hot night)", s, o, won)
        if fga < 15 and pct < 0.35 and fga >= 8:
            fav_add("S7b [18+] <35% on 8-14 shots", s, o, won)

C.dump("s7b", "11/8 S7b - the NBA favorite facing a star off a dud, closing prices; TRAIN 2016-22 / held 2023-2026", TRAIN, HELD)
