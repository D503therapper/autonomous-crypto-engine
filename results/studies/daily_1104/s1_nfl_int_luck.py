"""s1 - INTERCEPTION LUCK, NFL + college (the box scores 2021-26 hold interceptions thrown (passing) and made
(the interceptions group) - no fumbles). A team's season-to-date interception margin a game (made - thrown, 5+ box
games) is takeaway luck the market may carry too far: the +0.5 / game team as a favorite / dog / ATS, the -0.5 team
the same; the last-4-game margin as the hot-hands version. Prices: the close, and the paid history's first FAIR
number for football as the second check. Train 2021-23, held out 2024 / 2025 / 2026."""
import lib

C = lib.Cells()


def ints(st, r):
    if r["group"] == "passing":
        v = lib.num(st.get("interceptions"))
        return ("thrown", v) if v is not None else None
    if r["group"] == "interceptions":
        v = lib.num(st.get("interceptions"))
        return ("made", v) if v is not None else None
    return None


for lg in ("nfl", "ncaaf"):
    box = lib.boxes(lg, ints)
    fin = lib.finals(lg)
    xby = {g["id"]: g for g in lib.load_football(lg)} if lg == "nfl" else {}
    # per game per team: (made, thrown)
    per = {}
    for gid, teams in box.items():
        for t, pl in teams.items():
            made = sum(v[1] for v in pl.values() if v[0] == "made")
            thrown = sum(v[1] for v in pl.values() if v[0] == "thrown")
            per[(gid, t)] = (made, thrown)
    tl = lib.team_log(fin)
    for g in fin:
        if g["stype"] != "2":
            continue
        for side, team, opp, o, won, home in lib.sides(g):
            prev = [p for p in lib.before(tl, team, g["start"]) if p["season"] == g["season"] and (p["id"], team) in per]
            if len(prev) < 5:
                continue
            margins = [per[(p["id"], team)][0] - per[(p["id"], team)][1] for p in prev]
            m = sum(margins) / len(margins)
            m4 = sum(margins[-4:])
            tag = "lucky" if m >= 0.5 else "unlucky" if m <= -0.5 else "mid"
            hot = "hot4" if m4 >= 3 else "cold4" if m4 <= -3 else None
            s = g["season"]
            a = lib.ats(g, side)
            ff = lib.early_price(xby, g["id"], side) if xby else None
            for cut in ([tag] + ([hot] if hot else [])):
                C.add(f"{lg} {cut} ATS", s, a)
                if lib.dog_band(o):
                    C.add(f"{lg} {cut} dog +100..+350", s, lib.profit(won, lib.dec(o)))
                    if ff:
                        C.add(f"{lg} {cut} dog +100..+350 FIRST FAIR", s, lib.profit(won, ff[1]))
                if lib.fav_band(o):
                    C.add(f"{lg} {cut} fav -101..-150", s, lib.profit(won, lib.dec(o)))
                    if ff:
                        C.add(f"{lg} {cut} fav -101..-150 FIRST FAIR", s, lib.profit(won, ff[1]))
                if -300 <= o <= -151:
                    C.add(f"{lg} {cut} fav -151..-300", s, lib.profit(won, lib.dec(o)))
                C.add(f"{lg} {cut} side ML any", s, lib.profit(won, lib.dec(o)))
            C.add(f"{lg} base ATS", s, a)
            if lib.dog_band(o):
                C.add(f"{lg} base dog +100..+350", s, lib.profit(won, lib.dec(o)))
            if lib.fav_band(o):
                C.add(f"{lg} base fav -101..-150", s, lib.profit(won, lib.dec(o)))

C.dump("s1", "s1 INTERCEPTION LUCK (season-to-date INT margin a game; lucky +0.5+, unlucky -0.5-; hot4/cold4 = last 4 games +-3) - "
       "train 2021-23, held 2024 / 2025 / 2026", (2021, 2023), [2024, 2025, 2026])
