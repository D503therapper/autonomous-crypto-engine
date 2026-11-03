"""Study 9 (11/3): NBA - THE SECOND MEETING, 4+ DAYS LATER. The immediate rematch (within 3-4 days) died twice (10/28);
the in-season second meeting itself - the one the public reads as 'revenge' or 'they own them' - was never cut for the
NBA (college / NFL / NHL were). Regular season, the 2nd meeting of two teams 4+ days after the first: the team that LOST
the first by 15+ / won it by 15+ / lost it by 1-5 (the close one), the venue flip (the first meeting's home team now on
the road), the 2nd meeting on the SAME floor, the loser as a dog / favorite, ATS. Closing prices 2016-26 + the paid
2020-23 MORNING look. Train 2016-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
fin = lib.finals("nba")
allf = lib.all_finals("nba")
mo = lib.nba_morning()
# meetings by pair per season, in order
pairs = {}
for g in allf:
    k = (g["season"], tuple(sorted((g["home"], g["away"]))))
    pairs.setdefault(k, []).append(g)
C = lib.Cells()
for g in fin:
    k = (g["season"], tuple(sorted((g["home"], g["away"]))))
    ms = pairs.get(k) or []
    idx = next((j for j, x in enumerate(ms) if x["id"] == g["id"]), None)
    if idx != 1:
        continue                                    # the 2nd meeting only
    first = ms[0]
    days = lib.days_between(first["start"], g["start"])
    if days < 4:
        continue
    for side, team, opp, o, won, is_home in lib.sides(g):
        m1 = lib.margin_g(first, team)
        same_floor = (first["home"] == team) == is_home
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        tags = []
        if m1 <= -15:
            tags.append("lost the 1st meeting by 15+")
        if m1 >= 15:
            tags.append("won the 1st meeting by 15+")
        if -5 <= m1 <= -1:
            tags.append("lost the 1st meeting by 1-5")
        if 1 <= m1 <= 5:
            tags.append("won the 1st meeting by 1-5")
        if m1 < 0:
            tags.append("lost the 1st meeting (any)")
            if not same_floor:
                tags.append("lost the 1st meeting, venue flipped")
            else:
                tags.append("lost the 1st meeting, same floor")
        if m1 > 0 and same_floor:
            tags.append("won the 1st meeting, same floor")
        if days <= 10:
            tags.append(f"2nd meeting within 10 days, {'lost' if m1 < 0 else 'won'} the 1st")
        for tg in tags:
            C.add(f"{tg} | ATS", g["season"], a)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML +100..+350", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"{tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML -101..-200", g["season"], p)
C.dump("s9", "NBA: THE SECOND MEETING 4+ DAYS AFTER THE FIRST (by the first meeting's margin and the venue; close + the "
       "paid 2020-23 morning; train 2016-22, held 2023-26)", TRAIN, HELD)
