"""Study 7 (11/3): NBA - THE FIRST GAMES AFTER A TRADE. Never studied (no transaction feed - but the box scores show it):
a rotation man (20+ minutes a game over his last 10 for team A, 5+ of them) turns up in team B's box in the same season.
Team B's games 1-3 / 4-10 with him (the chemistry story the public tells both ways), team A's games 1-3 / 4-10 without
him, and the opponents across. Season starts and the first 5 games of a season are skipped (preseason trades are old
news). Sides: dog +100..+350 (ML), favorite -101..-200 (ML), ATS; the paid 2020-23 MORNING price as the second check.
Box scores 2016-26. Train 2016-22, held out 2023 / 2024 / 2025 / 2026 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
fin = lib.finals("nba")
allf = lib.all_finals("nba")
tl = lib.team_log(allf)
box = lib.box_rows("nba")
mo = lib.nba_morning()

# each player's team-game log in order: pid -> [(start, gid, team, minutes)]
plog = {}
for g in allf:
    for team in (g["home"], g["away"]):
        for r in (box.get(g["id"]) or {}).get(team) or []:
            try:
                m = float(r["st"].get("minutes") or 0)
            except ValueError:
                m = 0.0
            plog.setdefault(r["pid"], []).append((g["start"], g["id"], team, m, g["season"]))
for v in plog.values():
    v.sort()
# the trades: (season, new team, date) with the player's old team
moves = []
for pid, rows in plog.items():
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if a[4] != b[4] or a[2] == b[2]:
            continue
        hist = [x for x in rows[:i] if x[4] == b[4] and x[2] == a[2]][-10:]
        if len(hist) < 5 or sum(x[3] for x in hist) / len(hist) < 20:
            continue
        # not in the season's first 5 games for the new team
        n_before = sum(1 for x in tl.get(b[2], []) if x["season"] == b[4] and x["start"] < b[0])
        if n_before < 5:
            continue
        moves.append({"pid": pid, "season": b[4], "to": b[2], "frm": a[2], "date": b[0], "mins": sum(x[3] for x in hist) / len(hist)})
print("trades found:", len(moves))
by_team = {}
for m in moves:
    by_team.setdefault((m["season"], m["to"]), []).append(("got", m["date"], m["mins"]))
    by_team.setdefault((m["season"], m["frm"]), []).append(("lost", m["date"], m["mins"]))


def window(team, g):
    """('got'/'lost', games since, minutes) for the most recent move inside the team's season, or None."""
    ms = [m for m in by_team.get((g["season"], team), []) if m[1] <= g["start"]]
    if not ms:
        return None
    kind, date, mins = max(ms, key=lambda x: x[1])
    n = sum(1 for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"] and x["start"] >= date) + 1
    if kind == "lost":
        n -= 1                      # the man's first game elsewhere may fall on the old team's game day
        n = max(n, 1)
    return kind, n, mins


C = lib.Cells()
for g in fin:
    for side, team, opp, o, won, is_home in lib.sides(g):
        w, ow = window(team, g), window(opp, g)
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        tags = []
        if w:
            kind, n, mins = w
            win = "1-3" if n <= 3 else "4-10" if n <= 10 else None
            if win:
                tags.append(f"{kind} a 20+ min man, games {win}")
                if mins >= 28:
                    tags.append(f"{kind} a 28+ min man, games {win}")
        if ow and ow[1] <= 3:
            tags.append(f"vs a team that {ow[0]} a man, games 1-3")
        for tg in tags:
            C.add(f"{tg} | ATS", g["season"], a)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML +100..+350", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"{tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML -101..-200", g["season"], p)
C.dump("s7", "NBA: THE FIRST GAMES AFTER A TRADE (a 20+ minute man changes teams mid-season, from the box scores "
       "2016-26; close + the paid 2020-23 morning; train 2016-22, held 2023-26)", TRAIN, HELD)
