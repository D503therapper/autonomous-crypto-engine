"""s6 - THE SHAPE OF THE NHL BACK-TO-BACK (a dose check on a core input: the hockey read is the line + b2b / rest,
hockey.json's b2b weight is one number for every back-to-back). Night 2 by where night 1 was and where tonight is:
home->home, home->road, road->home, road->road, and the same-city / different-city road->road; the b2b side, the
rested side across it, the dog / favorite on each; both on a b2b. Prices: the close 2016-26 and the paid 2021-23
MORNING price as the second check. Train 2016-21, held out 2022 / 2023 / 2024 / 2025 / 2026."""
import lib

C = lib.Cells()
fin = lib.finals("nhl")
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
mo = lib.nhl_morning()
co = lib.coords("nhl")


def last(team, g):
    pr = lib.before(tl, team, g["start"], 1)
    return pr[0] if pr else None


for g in fin:
    if g["stype"] != "2" or g["neutral"]:
        continue
    s = g["season"]
    shape = {}
    for side, team, opp, o, won, home in lib.sides(g):
        p = last(team, g)
        b2b = p is not None and p["season"] == s and lib.days_between(p["start"], g["start"]) < 1.2
        if not b2b:
            shape[side] = "rested" if (p is None or lib.days_between(p["start"], g["start"]) >= 1.8) else "1off"
            continue
        was_home = p["home"] == team and not p["neutral"]
        now = "home" if home else "road"
        k = f"{'home' if was_home else 'road'}->{now}"
        if k == "road->road":
            a, b = co.get(p["id"]), co.get(g["id"])
            if a and b:
                k += " same city" if lib.miles(a, b) < 40 else " new city"
        shape[side] = k
    for side, team, opp, o, won, home in lib.sides(g):
        me, other = shape[side], shape["away" if side == "home" else "home"]
        p = lib.profit(won, lib.dec(o))
        ms = lib.morning_side(mo, g["id"], side)
        pm = lib.profit(won, ms[1]) if ms else None
        cuts = []
        if "->" in me and "->" not in other:
            cuts += [f"B2B side {me} vs rested", "B2B side any vs rested"]
        if "->" in other and "->" not in me:
            cuts += [f"RESTED side vs b2b {other}", "RESTED side vs b2b any"]
        if "->" in me and "->" in other:
            cuts += ["both b2b side"]
        if not cuts:
            cuts = ["base (no b2b)"]
        for cut in cuts:
            C.add(f"{cut} ML any", s, p)
            C.add(f"{cut} ML any MORNING", s, pm)
            if lib.dog_band(o):
                C.add(f"{cut} dog +100..+350", s, p)
                C.add(f"{cut} dog +100..+350 MORNING", s, pm)
            if lib.fav_band(o):
                C.add(f"{cut} fav -101..-150", s, p)
            if -250 <= o <= -151:
                C.add(f"{cut} fav -151..-250", s, p)

C.dump("s6", "s6 NHL BACK-TO-BACK SHAPE (night 1 where -> tonight where; the b2b side and the rested side across) - "
       "train 2016-21, held 2022 / 2023 / 2024 / 2025 / 2026", (2016, 2021), [2022, 2023, 2024, 2025, 2026])
