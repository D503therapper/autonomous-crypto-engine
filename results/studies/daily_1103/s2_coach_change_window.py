"""Study 2 (11/3): THE IN-SEASON COACH CHANGE, AFTER THE HONEYMOON. The 10/15 study graded the first 1-3 games under a
replacement (NFL 15-38; college four long shots) and the 9/30 fired-coach fade sits in the Dog score (sports_coach_changes).
Nobody has looked PAST game 3: does the interim bounce fade, or does the market keep over-selling the team? For every
in-season head-coach change on file (data/sports/coach_changes.json - NFL, college football, NBA, NHL; the date falls
inside the team's season), the team's games 1-3 / 4-8 / 9-15 under the new man: as a dog +100..+350 (ML), as a favorite
-101..-200 (ML), ATS (football / NBA), and the opponent across. Closing prices; train 2016-22, held out 2023 / 2024 /
2025 / 2026 apart (few changes a season - the cells are small by nature; this study says whether anything is there)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)
changes = json.load(open(os.path.join(lib.sd.DATA, "coach_changes.json")))
C = lib.Cells()
for lg in ("nfl", "ncaaf", "nba", "nhl"):
    fin = lib.finals(lg)
    allf = lib.all_finals(lg)
    tl = lib.team_log(allf)
    ch = [c for c in changes if c["league"] == lg]
    # (team, season) -> the change date, when it falls inside the team's season (between its first and last game)
    idx = {}
    for c in ch:
        s = lib.season(c["date"] + "T12:00Z")
        rows = [g for g in tl.get(str(c["team"]), []) if g["season"] == s]
        if not rows:
            continue
        if rows[0]["start"][:10] < c["date"] <= rows[-1]["start"][:10]:
            idx[(str(c["team"]), s)] = c["date"]
    # games since the change, per team-season
    for g in fin:
        for side, team, opp, o, won, is_home in lib.sides(g):
            d0 = idx.get((team, g["season"]))
            if not d0 or g["start"][:10] < d0:
                continue                                    # before the change: not under the new coach
            n = sum(1 for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"] and x["start"][:10] >= d0)
            n += 1                                      # tonight = game n under the new coach
            win = "1-3" if n <= 3 else "4-8" if n <= 8 else "9-15" if n <= 15 else None
            if not win:
                continue
            d = lib.dec(o)
            p = lib.profit(won, d)
            a = lib.ats(g, side)
            if lib.dog_band(o):
                C.add(f"{lg} | new coach, games {win} | dog ML +100..+350", g["season"], p)
            if -200 <= o <= -101:
                C.add(f"{lg} | new coach, games {win} | fav ML -101..-200", g["season"], p)
            C.add(f"{lg} | new coach, games {win} | ATS", g["season"], a)
            # the opponent across (any price)
            op = lib.profit(not won, lib.dec(g["mla"] if side == "home" else g["mlh"]))
            C.add(f"{lg} | vs a new coach, games {win} | opp ML any", g["season"], op)
            C.add(f"{lg} | vs a new coach, games {win} | opp ATS", g["season"], lib.ats(g, "away" if side == "home" else "home"))
            if lg in ("nfl", "ncaaf"):
                C.add(f"football | new coach, games {win} | ATS", g["season"], a)
                if lib.dog_band(o):
                    C.add(f"football | new coach, games {win} | dog ML +100..+350", g["season"], p)
            else:
                C.add(f"nba+nhl | new coach, games {win} | ATS/any", g["season"], a if a is not None else p)
                if lib.dog_band(o):
                    C.add(f"nba+nhl | new coach, games {win} | dog ML +100..+350", g["season"], p)
C.dump("s2", "THE IN-SEASON COACH CHANGE BY GAME WINDOW (1-3 / 4-8 / 9-15 under the new coach; close; train 2016-22, "
       "held 2023-26)", TRAIN, HELD)
