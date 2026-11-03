"""S5 - MOTIVATION LATE IN THE SEASON (March / April prep): tanking teams (sub-.350 after 50 games), the play-in zone
(conference rank 7-10, from the 2020-21 season), eliminated teams (rank 13+ with 20 or fewer games left), locked-in top
seeds, the team resting a rotation man tonight in April, and the totals in those games."""
import lib

T = lib.build()
C = lib.Cells()
n = 0


def situation(d, who=""):
    g, wp, rank, left, s = d[who + "g"], d[who + "wp"], d[who + "rank"], (72 if d["season"] == 2020 else 82) - d[who + "g"], d["season"]
    if g < 50 or wp is None or rank is None:
        return None
    if wp <= 0.35:
        return "tanking (sub-.350)"
    if left <= 20 and rank >= 13:
        return "eliminated-ish (rank 13+)"
    if s >= 2020 and left <= 25 and 7 <= rank <= 10:
        return "play-in zone (7-10)"
    if left <= 15 and rank <= 2:
        return "top-2 seed"
    if s >= 2020 and left <= 25 and 5 <= rank <= 6:
        return "fighting the play-in (5-6)"
    return "other"


for d in T:
    if d["month"] not in (3, 4):
        continue
    n += 1
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else "fav big" if d["ml"] < -150 else None
    me, op = situation(d), situation(d, "o_")
    if me is None or op is None:
        continue
    if kind:
        lib.add_all(C, f"1 {me}: {kind}", d)
        lib.add_all(C, f"1b vs {op}: {kind}", d)
    C.add(f"1c {me}: all [over]", s, lib.tot(d, True))
    if me == "tanking (sub-.350)" and op in ("play-in zone (7-10)", "fighting the play-in (5-6)") and kind:
        lib.add_all(C, f"2 tanking team vs a play-in fighter: {kind}", d)
    if me in ("play-in zone (7-10)", "fighting the play-in (5-6)") and op == "tanking (sub-.350)" and kind:
        lib.add_all(C, f"2b play-in fighter vs a tanking team: {kind}", d)
    if me == "top-2 seed" and op in ("play-in zone (7-10)", "fighting the play-in (5-6)") and kind:
        lib.add_all(C, f"2c top-2 seed vs a play-in fighter: {kind}", d)
    if me in ("play-in zone (7-10)", "fighting the play-in (5-6)") and op == "top-2 seed" and kind:
        lib.add_all(C, f"2d play-in fighter vs a top-2 seed: {kind}", d)
    if me in ("play-in zone (7-10)", "fighting the play-in (5-6)") and op in ("play-in zone (7-10)", "fighting the play-in (5-6)") and kind:
        lib.add_all(C, f"2e both fighting for the play-in: {kind}", d)
    # April: a rotation man rested tonight (listed), by situation
    if d["month"] == 4 and d["out_rest"] and kind:
        lib.add_all(C, f"3 April, rests a rotation man tonight, {me}: {kind}", d)
    if d["month"] == 4 and d["o_out_rest"] and kind:
        lib.add_all(C, f"3b April, opp rests a rotation man tonight, opp {op}: {kind}", d)
    # the tanking team's outs (how many rotation men out) - resting the vets
    if me == "tanking (sub-.350)" and d["out_rot"] is not None and kind:
        lib.add_all(C, f"4 tanking team with {'2+' if d['out_rot'] >= 2 else '0-1'} rotation men out: {kind}", d)
    if op == "tanking (sub-.350)" and d["o_out_rot"] is not None and kind:
        lib.add_all(C, f"4b vs a tanking team with {'2+' if d['o_out_rot'] >= 2 else '0-1'} rotation men out: {kind}", d)
    # April games with a tanking team: the over (the 11/3 lead, by the tanker's situation)
    if d["month"] == 4 and d["home"]:
        tk = "a tanking team in it" if "tanking" in (me, op) else "no tanking team"
        C.add(f"5 April, {tk}: [over]", s, lib.tot(d, True))
        C.add(f"5 April, {tk}: [under]", s, lib.tot(d, False))
C.dump("s5", lib.header("S5 LATE-SEASON MOTIVATION (March / April, standings at tip)", n), lib.split)
