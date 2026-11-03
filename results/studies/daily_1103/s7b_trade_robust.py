"""Study 7b (11/3): the team that LOST a rotation man (s7) - is it the trade, or the seller tanking? Same table as s7.
Cuts on the LOST side, games 1-10 after the man left: by month (Nov-Jan vs Feb-Apr - the deadline sellers), by the
team's record at the time (.500+ / under .500 / under .300 - the built NBA cold-dog cell), by whether the man was a
starter (28+ min) or a bench man (20-28), by who got him (a man who turned up for a new team the same week = a trade,
vs 8+ days later = waived / signed), and the plain base for every NBA side in the same months. Dog ML / fav ML / ATS;
the 2020-23 morning look. Train 2016-22, held out 2023 / 2024 / 2025 / 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
fin = lib.finals("nba")
allf = lib.all_finals("nba")
tl = lib.team_log(allf)
box = lib.box_rows("nba")
mo = lib.nba_morning()
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
lost = {}            # (season, old team) -> [(the man's last game with A, his first with B, mins)]
for pid, rows in plog.items():
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if a[4] != b[4] or a[2] == b[2]:
            continue
        hist = [x for x in rows[:i] if x[4] == b[4] and x[2] == a[2]][-10:]
        if len(hist) < 5 or sum(x[3] for x in hist) / len(hist) < 20:
            continue
        n_before = sum(1 for x in tl.get(b[2], []) if x["season"] == b[4] and x["start"] < b[0])
        if n_before < 5:
            continue
        lost.setdefault((a[4], a[2]), []).append((a[0], b[0], sum(x[3] for x in hist) / len(hist)))


def record(team, g):
    rows = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
    if len(rows) < 5:
        return None
    return sum(1 for x in rows if lib.won_g(x, team)) / len(rows)


C = lib.Cells()
for g in fin:
    month = int(g["start"][5:7])
    half = "Nov-Jan" if month in (10, 11, 12, 1) else "Feb-Apr"
    for side, team, opp, o, won, is_home in lib.sides(g):
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        rec = record(team, g)
        C.add(f"base {half} | ATS", g["season"], a)
        if lib.dog_band(o):
            C.add(f"base {half} | dog ML", g["season"], p)
        ms = [m for m in lost.get((g["season"], team), []) if m[1] <= g["start"]]
        if not ms:
            continue
        last_a, first_b, mins = max(ms, key=lambda x: x[1])
        n = sum(1 for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"] and x["start"] >= first_b) + 1
        n = max(n - 1, 1)
        if n > 10:
            continue
        quick = lib.days_between(last_a, first_b) <= 8
        tags = [f"lost | {half}", f"lost | {'starter 28+' if mins >= 28 else 'bench 20-28'}",
                f"lost | {'trade (new team within 8 days)' if quick else 'cut / signed later'}"]
        if rec is not None:
            tags.append(f"lost | record {'.500+' if rec >= 0.5 else 'under .300' if rec < 0.3 else '.300-.499'}")
            if rec >= 0.3:
                tags.append(f"lost | NOT a cold team (.300+) | {half}")
        tags.append(f"lost | games {'1-3' if n <= 3 else '4-10'} | {half}")
        for tg in tags:
            C.add(f"{tg} | ATS", g["season"], a)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"{tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML", g["season"], p)
C.dump("s7b", "NBA: THE TEAM THAT LOST A 20+ MINUTE MAN, games 1-10 - by month / record / his role / trade vs cut "
       "(close + the 2020-23 morning; train 2016-22, held 2023-26)", TRAIN, HELD)
