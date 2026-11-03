"""Study 4 (11/3): NFL - THE HOT QB AND THE DUD. The 11/2 NBA study found the small favorite whose top scorer just had
40+ lost (-14%). The NFL version: the team whose QB (the passer with the most attempts in its last game, the box scores
2021-26) threw for 350+ yards last game / 300+ in each of its last two (the hot hand the public buys), and the team whose
QB had 150 or fewer yards with 20+ attempts (the dud the public sells). Sides: as a favorite -101..-200 (ML), as a dog
+100..+350 (ML), ATS; the opponent across. Closing prices + the paid history's first fair number. College football the
same way (FBS box scores). Train 2021-23, held out 2024 / 2025 / 2026 apart (box scores start 2021)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2021, 2023), (2024, 2025, 2026)
C = lib.Cells()
for lg in ("nfl", "ncaaf"):
    fin = lib.finals(lg)
    allf = lib.all_finals(lg)
    tl = lib.team_log(allf)
    box = lib.box_rows(lg)
    xby = {x["id"]: x for x in lib.load_football(lg)}

    def qb_line(gid, team):
        rows = (box.get(gid) or {}).get(team) or []
        best = None
        for r in rows:
            if r["group"] != "passing":
                continue
            ca = str(r["st"].get("completions/passingAttempts") or "0/0")
            try:
                att = float(ca.split("/")[-1])
                yds = float(r["st"].get("passingYards") or 0)
            except ValueError:
                continue
            if best is None or att > best[0]:
                best = (att, yds, r["pid"])
        return best

    for g in fin:
        if g["season"] < 2021:
            continue
        tags = {}
        for side, team in (("home", g["home"]), ("away", g["away"])):
            prev = [x for x in lib.before(tl, team, g["start"], 2) if x["season"] == g["season"]]
            t = []
            if prev:
                q1 = qb_line(prev[-1]["id"], team)
                if q1:
                    if q1[1] >= 350:
                        t.append("QB 350+ yds last game")
                    if q1[0] >= 20 and q1[1] <= 150:
                        t.append("QB 150 or fewer yds last game (20+ att)")
                    if len(prev) == 2:
                        q2 = qb_line(prev[0]["id"], team)
                        if q2 and q1[1] >= 300 and q2[1] >= 300 and q1[2] == q2[2]:
                            t.append("same QB 300+ in each of the last 2")
            tags[side] = t
        for side, team, opp, o, won, is_home in lib.sides(g):
            d = lib.dec(o)
            p = lib.profit(won, d)
            a = lib.ats(g, side)
            other = "away" if side == "home" else "home"
            for tg in tags[side]:
                C.add(f"{lg} | {tg} | ATS", g["season"], a)
                if -200 <= o <= -101:
                    C.add(f"{lg} | {tg} | fav ML -101..-200", g["season"], p)
                if lib.dog_band(o):
                    C.add(f"{lg} | {tg} | dog ML +100..+350", g["season"], p)
                    e = lib.early_price(xby, g["id"], side)
                    if e:
                        C.add(f"{lg} | {tg} | dog ML | FIRST FAIR", g["season"], lib.profit(won, e[1]))
            for tg in tags[other]:
                C.add(f"{lg} | vs: {tg} | ATS", g["season"], a)
                if lib.dog_band(o):
                    C.add(f"{lg} | vs: {tg} | dog ML +100..+350", g["season"], p)
                if -200 <= o <= -101:
                    C.add(f"{lg} | vs: {tg} | fav ML -101..-200", g["season"], p)
C.dump("s4", "FOOTBALL: THE HOT QB (350+ last game / 300+ twice) AND THE DUD (150 or fewer) - close; train 2021-23, "
       "held 2024-26", TRAIN, HELD)
