"""s8 - THE NBA STAR'S SECOND GAME BACK (the 11/4 college hoops weight's NBA twin; the 10/22 NBA study built the
favorite's top-5 man's FIRST game back as a fade). From the box scores 2016-26: the team's top scorer by this season's
points a game (5+ games played before tonight) missed 2+ straight team games and PLAYED the team's last game -
tonight is his 2nd game back (known from the last box before tip). Cells: that side as a dog +100..+350 / favorite
-101..-150 / -151..-300 / ATS, the side across; the 1st game back (ex post - he could have sat) and the 3rd for the
shape; by the length of the absence (2-3 / 4+). The paid 2020-23 MORNING price as the second check.
Train 2016-22, held out 2023 / 2024 / 2025 / 2026."""
import lib

C = lib.Cells()


def pts(st, r):
    m = lib.num(st.get("minutes"))
    p = lib.num(st.get("points"))
    return (p, m) if p is not None and m is not None and m > 0 else None


box = lib.boxes("nba", pts)
fin = lib.finals("nba")
allf = [g for g in lib.all_finals("nba") if g["stype"] == "2"]
tl = lib.team_log(allf)
mo = lib.nba_morning()


def mark(team, g):
    """('back', nth game back, games missed) when the team's top scorer missed 2+ straight and is now in his nth
    game back (n = 1 means tonight would be his first - ex post); None otherwise."""
    prev = [p for p in lib.before(tl, team, g["start"]) if p["season"] == g["season"] and p["id"] in box]
    if len(prev) < 6:
        return None
    tot, gp = {}, {}
    for p in prev:
        for pid, (pt, m) in box[p["id"]].get(team, {}).items():
            tot[pid] = tot.get(pid, 0) + pt
            gp[pid] = gp.get(pid, 0) + 1
    cands = [(tot[p] / gp[p], p) for p in tot if gp[p] >= 5]
    if not cands:
        return None
    star = max(cands)[1]
    played = [star in box[p["id"]].get(team, {}) for p in prev]
    # walk back from the last game: count games played since the last absence run
    n = 0
    i = len(played) - 1
    while i >= 0 and played[i]:
        n += 1
        i -= 1
    missed = 0
    while i >= 0 and not played[i]:
        missed += 1
        i -= 1
    if missed < 2 or n > 3:
        return None
    return n + 1, missed       # tonight = game n+1 back


for g in fin:
    if g["stype"] != "2":
        continue
    s = g["season"]
    marks = {side: mark(team, g) for side, team, opp, o, won, home in lib.sides(g)}
    for side, team, opp, o, won, home in lib.sides(g):
        p = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        ms = lib.morning_side(mo, g["id"], side)
        pm = lib.profit(won, ms[1]) if ms else None
        mk, mo_ = marks[side], marks["away" if side == "home" else "home"]
        cuts = []
        if mk:
            n, missed = mk
            cuts += [f"star game {n} back", f"star game {n} back, missed {'2-3' if missed <= 3 else '4+'}"]
        if mo_:
            cuts.append(f"ACROSS star game {mo_[0]} back")
        if not cuts:
            cuts = ["base"]
        for cut in cuts:
            C.add(f"{cut} ATS", s, a)
            C.add(f"{cut} ML any", s, p)
            if lib.dog_band(o):
                C.add(f"{cut} dog +100..+350", s, p)
                C.add(f"{cut} dog +100..+350 MORNING", s, pm)
            if lib.fav_band(o):
                C.add(f"{cut} fav -101..-150", s, p)
                C.add(f"{cut} fav -101..-150 MORNING", s, pm)
            if -300 <= o <= -151:
                C.add(f"{cut} fav -151..-300", s, p)

C.dump("s8", "s8 NBA TOP SCORER'S Nth GAME BACK after missing 2+ straight (game 2 = tonight is known from the last box) - "
       "train 2016-22, held 2023 / 2024 / 2025 / 2026", (2016, 2022), [2023, 2024, 2025, 2026])
