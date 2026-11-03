"""S1 - PLAYER AVAILABILITY BEYOND THE STAR (the official 1:30 PM ET report joined to the box scores):
role men out (rotation men who are not top-3 scorers), minutes lost, the minutes-weighted lineup read vs the spread,
a rotation man BACK after missing 3+ games, load management (a team's 'rest' habit on back-to-backs)."""
import lib

T = lib.build()
C = lib.Cells()
n = 0
for d in T:
    if d["strength_full"] is None or d["o_strength_full"] is None or not d["listed"] or not d["o_listed"]:
        continue
    n += 1
    s = d["season"]
    isdog, isfav = lib.dog(d), lib.fav(d)
    kind = "dog" if isdog else "fav-150..-101" if isfav else None
    # 1. ROLE MEN OUT (no key man out) - this side
    if d["out_key"] == 0 and d["o_out_rot"] == 0:
        r = d["out_role"]
        b = "0" if r == 0 else "1" if r == 1 else "2" if r == 2 else "3+"
        if kind:
            lib.add_all(C, f"1 role men out {b}, no key man out, opp whole: {kind}", d)
    # 1b. the opponent's role men out, we are whole
    if d["out_rot"] == 0 and d["o_out_key"] == 0 and d["o_out_role"] >= 2 and kind:
        lib.add_all(C, f"1b opp 2+ role men out (no key), we are whole: {kind}", d)
    # 2. minutes lost tonight (rotation men out) - ours / theirs
    for who, om in (("ours", d["out_min"]), ("theirs", d["o_out_min"])):
        b = "0" if om == 0 else "<30" if om < 30 else "30-60" if om < 60 else "60+"
        if kind:
            C.add(f"2 minutes out {who} {b}: {kind} [ML close]", s, lib.ml(d))
            C.add(f"2 minutes out {who} {b}: {kind} [ATS]", s, lib.ats(d))
    # 3. THE LINEUP READ vs THE SPREAD: expected margin from the available lineups (+3 home) minus the market's
    if d["spread"] is not None and d["strength_avail"] is not None and d["o_strength_avail"] is not None:
        lm = d["strength_avail"] - d["o_strength_avail"] + (3.0 if d["home"] else -3.0)
        diff = lm + d["spread"]                   # + = the lineups like us more than the market does
        b = "<=-6" if diff <= -6 else "-6..-3" if diff <= -3 else "-3..3" if diff < 3 else "3..6" if diff < 6 else "6+"
        C.add(f"3 lineup read vs spread {b}: all [ATS]", s, lib.ats(d))
        if kind:
            C.add(f"3 lineup read vs spread {b}: {kind} [ML close]", s, lib.ml(d))
            if d.get("m_dec"):
                C.add(f"3 lineup read vs spread {b}: {kind} [ML morning]", s, lib.ml(d, "morning"))
        # the full-roster read (nobody out) vs the spread - what the ratings say without the report
        lf = d["strength_full"] - d["o_strength_full"] + (3.0 if d["home"] else -3.0)
        df = lf + d["spread"]
        b2 = "<=-6" if df <= -6 else "-6..-3" if df <= -3 else "-3..3" if df < 3 else "3..6" if df < 6 else "6+"
        C.add(f"3b full-roster read vs spread {b2}: all [ATS]", s, lib.ats(d))
        # the lost strength tonight (full - avail) - does the market move too far / not far enough for it?
        lost = d["strength_full"] - (d["strength_avail"] or d["strength_full"])
        olost = d["o_strength_full"] - (d["o_strength_avail"] or d["o_strength_full"])
        for who, v in (("ours", lost), ("theirs", olost)):
            b3 = "0" if v <= 0.5 else "0.5-2" if v < 2 else "2-4" if v < 4 else "4+"
            C.add(f"3c lineup strength lost {who} {b3}: all [ATS]", s, lib.ats(d))
            if kind:
                C.add(f"3c lineup strength lost {who} {b3}: {kind} [ML close]", s, lib.ml(d))
    # 4. BACK TONIGHT after missing 3+ (a 20+ mpg man, not out on the report)
    if d["back_n"]:
        tag = "star" if d["back_star"] else "role"
        lib.add_all(C, f"4 a {tag} back after missing 3+: all", d)
        if kind:
            lib.add_all(C, f"4 a {tag} back after missing 3+: {kind}", d)
        if d["back_mpg"] >= 28:
            lib.add_all(C, "4 a 28+ mpg man back after missing 3+: all", d)
    if d["o_back_n"] and kind:
        lib.add_all(C, f"4b opp has a {'star' if d['o_back_star'] else 'role'} man back after 3+: {kind}", d)
    # 5. LOAD MANAGEMENT: a team that rests men on back-to-backs (its habit this season before tonight), on a b2b night
    if d["b2b"] and d["rest_rate_b2b"] is not None:
        hab = "resters (30%+)" if d["rest_rate_b2b"] >= 0.3 else "never-rest (0%)" if d["rest_rate_b2b"] == 0 else "some"
        if kind:
            lib.add_all(C, f"5 b2b night, team habit {hab}: {kind}", d)
        if d["o_rest_rate_b2b"] is not None:
            C.add(f"5 b2b night, team habit {hab}: all [ATS]", s, lib.ats(d))
    if d["o_b2b"] and d["o_rest_rate_b2b"] is not None and kind:
        hab = "resters (30%+)" if d["o_rest_rate_b2b"] >= 0.3 else "never-rest (0%)" if d["o_rest_rate_b2b"] == 0 else "some"
        lib.add_all(C, f"5b opp on a b2b, opp habit {hab}: {kind}", d)
    # 5c. a 'rest' listing tonight (known by 1:30 PM; the morning price is BEFORE the report)
    if d["out_rest"] and kind:
        lib.add_all(C, f"5c a rotation man rested tonight (listed): {kind}", d)
    if d["o_out_rest"] and kind:
        lib.add_all(C, f"5d opp rests a rotation man tonight (listed): {kind}", d)
    # 6. day of week: who sits (descriptive - the share of sides with a rotation man out by weekday)
    C.add(f"6 weekday {d['wd']}: a rotation man out (share) [ML close]", s, 1.0 if d["out_rot"] else 0.0)
C.dump("s1", lib.header("S1 AVAILABILITY BEYOND THE STAR (the 1:30 PM report + the box scores)", n), lib.split)
