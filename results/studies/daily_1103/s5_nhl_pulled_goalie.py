"""Study 5 (11/3): NHL - THE GOALIE WHO GOT PULLED. Never studied: a team pulled its goalie mid-game last time out (two
goalies faced shots; the one who left early allowed 3+ on under 50 minutes - the hook, not an injury we can't see). What
happens next game: (a) the team, whoever starts; (b) the PULLED goalie's next start (the bounce-back or the hangover);
(c) the relief man gets the next start; (d) the opponent across. Also the team that pulled its goalie in 2 of its last 3.
From the roster box scores 2021-26 (goalies' timeOnIce / shotsAgainst / goalsAgainst). Sides: dog ML +100..+350, favorite
-101..-200, any price; the 2021-23 paid MORNING price as the second check. Train 2021-23, held 2024 / 2025 / 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2021, 2023), (2024, 2025, 2026)
fin = lib.finals("nhl")
allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021]
tl = lib.team_log(allf)
box = lib.box_rows("nhl")
mo = lib.nhl_morning()


def goalies(gid, team):
    """[(pid, toi, sa, ga)] goalies who faced shots, most ice first."""
    out = []
    for r in (box.get(gid) or {}).get(team) or []:
        if r["group"] != "goalies":
            continue
        t = lib.toi(r["st"].get("timeOnIce"))
        try:
            sa, ga = float(r["st"].get("shotsAgainst") or 0), float(r["st"].get("goalsAgainst") or 0)
        except ValueError:
            continue
        if t is None or sa <= 0:
            continue
        out.append((r["pid"], t, sa, ga))
    return sorted(out, key=lambda x: -x[1])


def pulled(gid, team):
    """(pulled goalie pid, relief pid) if the game had a hook, else None."""
    gs = goalies(gid, team)
    if len(gs) < 2:
        return None
    starter, relief = gs[0], gs[1]
    # the man who left: fewer than 50 minutes and 3+ goals against on the one with the shorter night counted as pulled
    for a, b in ((starter, relief), (relief, starter)):
        if a[1] < 50 and a[3] >= 3 and b[1] >= 8:
            return a[0], b[0]
    return None


def starter_tonight(gid, team):
    gs = goalies(gid, team)
    return gs[0][0] if gs else None


C = lib.Cells()
for g in fin:
    if g["season"] < 2021:
        continue
    info = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        prev = [x for x in lib.before(tl, team, g["start"], 3) if x["season"] == g["season"]]
        if not prev:
            info[side] = None
            continue
        pl = pulled(prev[-1]["id"], team)
        n_pulled3 = sum(1 for x in prev if pulled(x["id"], team))
        st = starter_tonight(g["id"], team)
        info[side] = {"pulled": pl, "n3": n_pulled3, "starter": st,
                      "days": lib.days_between(prev[-1]["start"], g["start"])}
    for side, team, opp, o, won, is_home in lib.sides(g):
        me, ot = info[side], info["away" if side == "home" else "home"]
        if me is None or ot is None:
            continue
        d = lib.dec(o)
        p = lib.profit(won, d)
        tags = []
        if me["pulled"]:
            tags.append("pulled its goalie last game (any starter)")
            if me["starter"] == me["pulled"][0]:
                tags.append("pulled goalie starts again")
            elif me["starter"] == me["pulled"][1]:
                tags.append("the relief man starts")
            if me["days"] <= 2:
                tags.append("pulled its goalie last game, plays within 2 days")
        if me["n3"] >= 2:
            tags.append("pulled its goalie in 2 of its last 3")
        if ot["pulled"]:
            tags.append("vs a team that pulled its goalie last game")
            if ot["starter"] == ot["pulled"][0]:
                tags.append("vs the pulled goalie starting again")
        for tg in tags:
            C.add(f"{tg} | ML any", g["season"], p)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML +100..+350", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"{tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML -101..-200", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and -200 <= m[0] <= -101:
                    C.add(f"{tg} | fav ML | MORNING", g["season"], lib.profit(won, m[1]))
C.dump("s5", "NHL: THE TEAM THAT PULLED ITS GOALIE LAST GAME, the pulled man's next start, the relief man (box scores "
       "2021-26; close + the paid 2021-23 morning; train 2021-23, held 2024-26)", TRAIN, HELD)
