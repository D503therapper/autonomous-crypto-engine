"""S7 - FOLLOW-UPS on the three cells that showed something: (a) the faster team (pace over the last 10) losing to the
number - the dose, every price, the mirror; (b) the favorite in its first home game after a 4+ game trip - the dose
by trip length, every favorite price, the opponent's state; (c) the West visitor at a 7-7:30 ET tip in the East -
by season and by the body clock (a Pacific-zone team only)."""
import lib

T = lib.build()
C = lib.Cells()
PACIFIC = {"Lakers", "Clippers", "Warriors", "Kings", "Trail Blazers", "Suns"}
import sports_data as sd
names = {}
for g in sd.load_games("nba").values():
    names[g["home"]] = g.get("home_name")
n = 0
for d in T:
    if d["g"] < 5 or d["o_g"] < 5:
        continue
    n += 1
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else "fav big" if d["ml"] < -150 else "dog long"
    # (a) pace
    if d["pace"] is not None and d["o_pace"] is not None and d["g"] >= 10 and d["o_g"] >= 10:
        gap = d["pace"] - d["o_pace"]
        b = "6+ faster" if gap >= 6 else "4-6 faster" if gap >= 4 else "2-4 faster" if gap >= 2 else "within 2" if gap > -2 else "2-4 slower" if gap > -4 else "4-6 slower" if gap > -6 else "6+ slower"
        C.add(f"a pace {b}: all [ATS]", s, lib.ats(d))
        C.add(f"a pace {b}: all [ML close]", s, lib.ml(d))
        if abs(gap) >= 4:
            C.add(f"a2 pace {'4+ faster' if gap > 0 else '4+ slower'}: {kind} [ML close]", s, lib.ml(d))
            C.add(f"a2 pace {'4+ faster' if gap > 0 else '4+ slower'}: {kind} [ATS]", s, lib.ats(d))
            if d.get("m_dec"):
                C.add(f"a2 pace {'4+ faster' if gap > 0 else '4+ slower'}: {kind} [ML morning]", s, lib.ml(d, "morning"))
            C.add(f"a3 pace {'4+ faster' if gap > 0 else '4+ slower'}, {'home' if d['home'] else 'road'}: all [ATS]", s, lib.ats(d))
            C.add(f"a4 pace {'4+ faster' if gap > 0 else '4+ slower'}: [over]", s, lib.tot(d, True))
    # (b) the favorite home after a trip
    if d["ml"] < 0 and d["home_after_trip"] >= 3:
        b = "3" if d["home_after_trip"] == 3 else "4" if d["home_after_trip"] == 4 else "5+"
        C.add(f"b fav home after a {b} game trip: all favorites [ML close]", s, lib.ml(d))
        C.add(f"b fav home after a {b} game trip: all favorites [ATS]", s, lib.ats(d))
        if d["home_after_trip"] >= 4:
            C.add(f"b2 fav home after a 4+ trip: {kind} [ML close]", s, lib.ml(d))
            C.add(f"b2 fav home after a 4+ trip: {kind} [ATS]", s, lib.ats(d))
            if d.get("m_dec"):
                C.add(f"b2 fav home after a 4+ trip: {kind} [ML morning]", s, lib.ml(d, "morning"))
            if d.get("dec_open"):
                C.add(f"b2 fav home after a 4+ trip: {kind} [ML open]", s, lib.ml(d, "open"))
            ob = "opp on a b2b" if d["o_b2b"] else "opp rested"
            C.add(f"b3 fav home after a 4+ trip, {ob}: all favorites [ML close]", s, lib.ml(d))
            tb = "we are on a b2b" if d["b2b"] else "we are rested"
            C.add(f"b4 fav home after a 4+ trip, {tb}: all favorites [ML close]", s, lib.ml(d))
            C.add(f"b5 fav home after a 4+ trip, trip record {'winning' if (d['m5'] or 0) > 0 else 'losing'} (m5): all favorites [ML close]", s, lib.ml(d))
    if d["ml"] < 0 and d["home_after_trip"] == 0 and d["home"] and d["stand_game"] >= 2:
        C.add("b6 fav at home mid-homestand (the control): all favorites [ML close]", s, lib.ml(d))
        C.add("b6 fav at home mid-homestand (the control): all favorites [ATS]", s, lib.ats(d))
    if d["ml"] < 0 and d["home"] and d["home_after_trip"] in (1, 2):
        C.add("b7 fav home after a 1-2 game trip (the control): all favorites [ML close]", s, lib.ml(d))
    # (c) the West visitor at an early ET tip
    if not d["home"] and d["o_conf"] == "E" and d["et_hour"] <= 19.5 and kind == "dog":
        pac = names.get(d["team"]) in PACIFIC
        C.add(f"c {'Pacific-zone' if pac else 'Mountain/Central West'} visitor, 7-7:30 ET tip in the East: dog [ML close]", s, lib.ml(d))
        C.add(f"c {'Pacific-zone' if pac else 'Mountain/Central West'} visitor, 7-7:30 ET tip in the East: dog [ATS]", s, lib.ats(d))
        if d["conf"] == "W":
            C.add(f"c2 West visitor 7-7:30 ET tip in the East, {'trip game 1' if d['trip_game'] == 1 else 'trip game 2+'}: dog [ML close]", s, lib.ml(d))
    if not d["home"] and d["o_conf"] == "E" and d["conf"] == "W" and d["et_hour"] > 19.5 and kind == "dog":
        C.add("c3 West visitor at a LATER ET tip in the East (the control): dog [ML close]", s, lib.ml(d))
        C.add("c3 West visitor at a LATER ET tip in the East (the control): dog [ATS]", s, lib.ats(d))
C.dump("s7", lib.header("S7 FOLLOW-UPS: pace dose / the favorite home after a trip / the West visitor's early tip", n), lib.split)
