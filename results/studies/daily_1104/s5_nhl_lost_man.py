"""s5 - THE NHL TEAM THAT LOST A ROTATION SKATER (the 11/3 NBA weight's hockey twin; box scores 2021-26, TOI per
skater, no transaction feed). A skater at 15+ minutes a night over his last 10 games with team A (5+ played) turns up
in team B's box the same season (a trade, or a waiver claim) - team A's next 10 games (1-3 / 4-10), team B's too, and
the GOALIE version (a goalie with 5+ starts for A who starts for B). Moneylines only (no puck lines on the board):
the dog +100..+350, the favorite -101..-200, any side; the paid 2021-23 MORNING price as the second check.
Train 2021-23, held out 2024 / 2025 / 2026."""
import lib

C = lib.Cells()
rows = lib.box_rows("nhl")
fin = lib.finals("nhl")
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
mo = lib.nhl_morning()

# per player: ordered list of (start, gid, team, toi, is_goalie, started)
pl = {}
for gid, teams in rows.items():
    for t, rs in teams.items():
        for r in rs:
            m = lib.toi(r["st"].get("timeOnIce"))
            if m is None:
                continue
            pl.setdefault(r["pid"], []).append((r["start"], gid, t, m, r["group"] == "goalies"))
for v in pl.values():
    v.sort()

# moves: (season, team A, team B, first start with B, minutes with A, goalie?)
moves = []
for pid, lst in pl.items():
    for i in range(1, len(lst)):
        s0, s1 = lib.season(lst[i - 1][0]), lib.season(lst[i][0])
        if s0 != s1 or lst[i][2] == lst[i - 1][2]:
            continue
        prevA = [x for x in lst[:i] if x[2] == lst[i - 1][2] and lib.season(x[0]) == s1][-10:]
        if len(prevA) < 5:
            continue
        goalie = lst[i][4]
        if goalie:
            starts = [x for x in prevA if x[3] >= 30]
            if len(starts) < 5:
                continue
        else:
            mins = sum(x[3] for x in prevA) / len(prevA)
            if mins < 15:
                continue
        # same man must not reappear with A within 5 games (a loan / AHL swap would not show anyway)
        moves.append((s1, lst[i - 1][2], lst[i][2], lst[i][0], (sum(x[3] for x in prevA) / len(prevA)), goalie))
print("moves found:", len(moves), "goalies:", sum(1 for m in moves if m[5]))

# flag each (season, team) game by games since the move (the first box elsewhere is known the morning after)
flag = {}
for s, A, B, first_b, mins, goalie in moves:
    for who, team in (("LOST", A), ("GOT", B)):
        lst = [g for g in tl.get(team, []) if g["season"] == s and g["start"] > first_b]
        for n, g in enumerate(lst[:10], 1):
            k = (g["id"], team)
            flag.setdefault(k, []).append((who, n, mins, goalie))

for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    s = g["season"]
    for side, team, opp, o, won, home in lib.sides(g):
        p = lib.profit(won, lib.dec(o))
        ms = lib.morning_side(mo, g["id"], side)
        pm = lib.profit(won, ms[1]) if ms else None
        fl = flag.get((g["id"], team), [])
        fo = flag.get((g["id"], opp), [])
        cuts = ["base"]
        for who, n, mins, goalie in fl:
            kind = "goalie" if goalie else ("18+ min" if mins >= 18 else "15-18 min")
            win = "games 1-3" if n <= 3 else "games 4-10"
            cuts += [f"{who} skater {win}" if not goalie else f"{who} goalie {win}", f"{who} {kind} games 1-10"]
        for who, n, mins, goalie in fo:
            if not goalie:
                cuts.append(f"OPP of the team that {who} a skater games 1-10")
        for cut in set(cuts):
            C.add(f"{cut} side ML any", s, p)
            if lib.dog_band(o):
                C.add(f"{cut} dog +100..+350", s, p)
                C.add(f"{cut} dog +100..+350 MORNING", s, pm)
            if -200 <= o <= -101:
                C.add(f"{cut} fav -101..-200", s, p)
                C.add(f"{cut} fav -101..-200 MORNING", s, pm)

C.dump("s5", "s5 NHL TEAM THAT LOST / GOT A ROTATION SKATER (15+ min over his last 10, 5+ played; a goalie with 5+ starts) - next 10 games - "
       "train 2021-23, held 2024 / 2025 / 2026", (2021, 2023), [2024, 2025, 2026])
