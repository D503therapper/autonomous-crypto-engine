"""11/14 daily studies - S11 NBA THE BLOWOUT-LOSS BOUNCE-BACK, the cells not run before (11/7 S5 read the game after a
20+ HOME loss; 11/13 S6 the back-to-back night after a 20+ loss): the game after a 20+ / 25+ / 30+ loss with a night or
more of rest, split by where the loss was and where tonight is. Moneyline + spread at ESPN's close (lib2.rows - every
fact known before tip). Train 2016-21 / held 2022-25 apart / now 2026."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import lib2  # noqa: E402
import h  # noqa: E402

o = h.Out("s11_nba_blowout_bounce", (2016, 2021), [2022, 2023, 2024, 2025, 2026])
o.p("S11 NBA THE GAME AFTER A BLOWOUT LOSS, RESTED (prev game 30h+ ago, same season; ML + ATS at the close)")
for r in lib2.rows("nba"):
    if r["stype"] != "2" or r["season"] < 2016:
        continue
    pr = lib2.ml_profit(r)
    bd = h.band(r["odds"])
    s = r["season"]
    if bd:
        o.add(f"BASE {bd}", s, pr, r["odds"])
    o.add("BASE ats", s, r["ats"])
    pm, gap = r["prev_margin"], r["prev_gap_h"]
    if pm is None or gap is None or gap < 30:
        continue
    where = "after a ROAD loss" if r["prev_home"] is False else "after a HOME loss"
    here = "home" if r["home"] else "road"
    for cut in (20, 25, 30):
        if pm <= -cut:
            o.add(f"S11 lost by {cut}+ ATS", s, r["ats"])
            o.add(f"S11 lost by {cut}+ {where}, {here} tonight ATS", s, r["ats"])
            if bd:
                o.add(f"S11 lost by {cut}+ {bd}", s, pr, r["odds"])
                o.add(f"S11 lost by {cut}+ {where}, {here} tonight {bd}", s, pr, r["odds"])
    if r["oprev_margin"] is not None and r["oprev_margin"] <= -25 and (r["oprev_gap_h"] or 0) >= 30 and pm > -25:
        o.add("S11 vs a team off a 25+ loss (rested) ATS", s, r["ats"])
        if bd:
            o.add(f"S11 vs a team off a 25+ loss (rested) {bd}", s, pr, r["odds"])
o.show()
for c in list(o.c):
    if c.startswith("S11") and len(o.c[c]) >= 80:
        pool = "BASE ats" if c.endswith("ATS") else ("BASE dog" if c.endswith("dog") else "BASE fav")
        o.placebo(c, pool, fade=sum(p for _, p, _ in o.c[c]) < 0)
o.save()
