"""S6b - THE HEAVY LAST GAME x THE BACK-TO-BACK, against its controls: every NHL dog on the 2nd night of a b2b, the
b2b dogs whose ice-time leader logged under 26 last night, the dose (24 / 25 / 26 / 27+), whether last night went to
OT, and road / home. Also the RESTED dog after a heavy game (the fatigue should fade with a day off). Close + the paid
morning look (2021-23)."""
from collections import defaultdict

import lib

fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
rows = lib.box_rows("nhl")
mo = lib.nhl_morning()
TRAIN, HELD = (2016, 2021), (2022, 2023, 2024, 2025, 2026)


def lead_toi(gid, team):
    rs = (rows.get(gid) or {}).get(team)
    if not rs:
        return None
    t = [lib.toi(r["st"].get("timeOnIce")) for r in rs
         if not (r.get("group") == "goalies" or r.get("pos") == "G" or "saves" in r["st"])]
    t = [x for x in t if x]
    return max(t) if len(t) >= 15 else None


tl = lib.team_log(allf)
cells = lib.Cells()
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        if not lib.dog_band(o):
            continue
        p = lib.before(tl, team, g["start"], 1)
        if not p:
            continue
        prev = p[-1]
        rest = lib.days_between(prev["start"], g["start"])
        lm = lead_toi(prev["id"], team)
        if lm is None:
            continue
        b2b = rest < 1.5
        po = lib.before(tl, opp, g["start"], 1)
        opp_b2b = bool(po) and lib.days_between(po[-1]["start"], g["start"]) < 1.5
        labs = []
        if b2b:
            labs.append("b2b dog ALL (control)")
            labs.append("b2b dog, leader 26+" if lm >= 26 else "b2b dog, leader under 26")
            labs.append(f"b2b dog, leader {'27+' if lm >= 27 else '26-27' if lm >= 26 else '25-26' if lm >= 25 else '24-25' if lm >= 24 else 'under 24'}")
            if lm >= 26:
                labs.append(f"b2b dog, leader 26+, {'road' if not home else 'home'}")
                labs.append(f"b2b dog, leader 26+, opp {'also b2b' if opp_b2b else 'rested'}")
            else:
                labs.append(f"b2b dog, leader under 26, opp {'also b2b' if opp_b2b else 'rested'}")
        else:
            labs.append("rested dog, leader 26+ last game" if lm >= 26 else "rested dog, leader under 26 last game")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        m = lib.morning_side(mo, g["id"], side) if mo else None
        for lab in labs:
            cells.add(f"{lab} | DOG ML", s, pl)
            if m and lib.dog_band(m[0]):
                cells.add(f"{lab} | DOG ML paid morning", s, lib.profit(won, m[1]))
cells.dump("s6b", "S6b NHL - the heavy last game x the back-to-back vs its controls (dogs +100..+350); close / paid morning",
           TRAIN, HELD)
