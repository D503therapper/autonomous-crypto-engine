"""S2 - SCHEDULE SPOTS NOT YET TESTED: the 4th game in 6 nights, the last game of a long road trip, the first home game
after a long trip (the favorite side), the first road game after a long homestand, Sunday matinees after a Saturday
night, afternoon tips, the game after an overtime game (the favorite side; on a back-to-back), late East-coast tips,
a national-TV PROXY (a lone Tue / Thu 7:30 or 10 ET tip), and the dense-schedule gap between the two teams."""
import lib

T = lib.build()
C = lib.Cells()
n = 0
for d in T:
    if d["g"] < 5 or d["o_g"] < 5:
        continue
    n += 1
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else None
    if not kind:
        continue
    # 1. 4th game in 6 nights (3rd in 4 shown beside it); the opponent rested (not dense)
    dense, odense = d["in6"] >= 4, d["o_in6"] >= 4
    if dense and not odense:
        lib.add_all(C, f"1 4th in 6 nights vs a team not: {kind}", d)
        if not d["b2b"]:
            lib.add_all(C, f"1b 4th in 6 nights, NOT a b2b, vs a team not: {kind}", d)
    if odense and not dense:
        lib.add_all(C, f"1c opp 4th in 6 nights, we are not: {kind}", d)
    if dense and odense:
        lib.add_all(C, f"1d both 4th in 6 nights: {kind}", d)
    if d["in4"] >= 3 and d["o_in4"] < 3:
        lib.add_all(C, f"1e 3rd in 4 nights vs a team not: {kind}", d)
    gap = d["in8"] - d["o_in8"]
    if abs(gap) >= 2:
        lib.add_all(C, f"1f games in 8 nights, {'2+ MORE' if gap > 0 else '2+ FEWER'} than the opp: {kind}", d)
    # 2. the last game of a road trip (next game is home)
    if d["trip_end"] and d["trip_game"] >= 4:
        lib.add_all(C, f"2 last game of a 4+ game trip: {kind}", d)
    if d["trip_end"] and d["trip_game"] >= 5:
        lib.add_all(C, f"2b last game of a 5+ game trip: {kind}", d)
    if d["o_trip_end"] and d["o_trip_game"] >= 4:
        lib.add_all(C, f"2c opp on the last game of a 4+ trip: {kind}", d)
    if d["trip_game"] >= 5 and not d["trip_end"]:
        lib.add_all(C, f"2d trip game 5+, trip goes on: {kind}", d)
    # 3. the first home game after a long trip - the favorite side (the dog side is the built -2)
    if d["home_after_trip"] >= 4:
        lib.add_all(C, f"3 first home game after a 4+ trip: {kind}", d)
    if d["home_after_trip"] >= 5:
        lib.add_all(C, f"3b first home game after a 5+ trip: {kind}", d)
    if d["o_home_after_trip"] >= 4:
        lib.add_all(C, f"3c opp in its first home game after a 4+ trip: {kind}", d)
    # 4. the first road game after a long homestand
    if d["away_after_stand"] >= 5:
        lib.add_all(C, f"4 first road game after a 5+ homestand: {kind}", d)
    if d["o_away_after_stand"] >= 5:
        lib.add_all(C, f"4b opp in its first road game after a 5+ homestand: {kind}", d)
    if d["stand_game"] >= 6:
        lib.add_all(C, f"4c homestand game 6+: {kind}", d)
    # 5. Sunday matinee (local tip before 4 PM) after a Saturday night
    mat = d["loc_hour"] < 16
    if d["wd"] == 6 and mat:
        lib.add_all(C, f"5 Sunday matinee: {kind}", d)
        if d["b2b"] and not d["o_b2b"]:
            lib.add_all(C, f"5b Sunday matinee off a Saturday night, opp rested: {kind}", d)
        if d["o_b2b"] and not d["b2b"]:
            lib.add_all(C, f"5c Sunday matinee, opp off a Saturday night, we rested: {kind}", d)
        if d["b2b"] and d["o_b2b"]:
            lib.add_all(C, f"5d Sunday matinee, both off a Saturday night: {kind}", d)
    if mat and d["wd"] != 6:
        lib.add_all(C, f"5e weekday / Saturday matinee: {kind}", d)
    if mat and d["b2b"] and not d["o_b2b"]:
        lib.add_all(C, f"5f any matinee on a b2b, opp rested: {kind}", d)
    if mat and d["home"] and d["o_last_home"] is False and d["o_b2b"]:
        lib.add_all(C, f"5g matinee at home, opp played on the road last night: {kind}", d)
    # 6. after an overtime game (the dog side is built both ways; the favorite side / the b2b version)
    if d["last_ot"] and d["rest"] is not None and d["rest"] <= 3:
        lib.add_all(C, f"6 played OT last game (within 3 days): {kind}", d)
        if d["b2b"]:
            lib.add_all(C, f"6b played OT last NIGHT (b2b): {kind}", d)
    if d["o_last_ot"] and d["o_rest"] is not None and d["o_rest"] <= 3:
        lib.add_all(C, f"6c opp played OT last game (within 3 days): {kind}", d)
        if d["o_b2b"]:
            lib.add_all(C, f"6d opp played OT last NIGHT (b2b): {kind}", d)
    # 7. the late tip (10 PM ET or later) for the visiting East team (a 10 PM body clock), the early tip for a West
    #    visitor (a 4 PM body clock at a 7 PM ET tip)
    if d["et_hour"] >= 22 and not d["home"] and d["conf"] == "E":
        lib.add_all(C, f"7 East visitor at a 10 PM ET tip: {kind}", d)
    if d["et_hour"] <= 19.5 and not d["home"] and d["conf"] == "W" and d["o_conf"] == "E":
        lib.add_all(C, f"7b West visitor at a 7-7:30 PM ET tip in the East: {kind}", d)
    # 8. national TV PROXY: a Tuesday / Thursday game tipping 7:30 or 10 PM ET with 5 or fewer games that night
    if d["wd"] in (1, 3) and d["slate"] <= 5 and (abs(d["et_hour"] - 19.5) < 0.1 or abs(d["et_hour"] - 22) < 0.1):
        lib.add_all(C, f"8 national-TV proxy (Tue/Thu 7:30 or 10 ET, small slate): {kind}", d)
    if d["wd"] in (2, 4) and d["slate"] >= 8 and (abs(d["et_hour"] - 19.5) < 0.1 or abs(d["et_hour"] - 22) < 0.1):
        lib.add_all(C, f"8b ESPN-night proxy (Wed/Fri 7:30 or 10 ET, big slate): {kind}", d)
    # 9. rest 4+ days (the long break - rust?) vs a team in rhythm
    if d["rest"] is not None and d["rest"] >= 4 and d["o_rest"] is not None and d["o_rest"] <= 2:
        lib.add_all(C, f"9 off 4+ days vs a team in rhythm: {kind}", d)
    if d["o_rest"] is not None and d["o_rest"] >= 4 and d["rest"] is not None and d["rest"] <= 2:
        lib.add_all(C, f"9b opp off 4+ days, we are in rhythm: {kind}", d)
C.dump("s2", lib.header("S2 SCHEDULE SPOTS", n), lib.split)
