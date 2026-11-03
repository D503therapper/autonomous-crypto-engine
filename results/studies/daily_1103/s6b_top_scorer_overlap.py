"""Study 6b (11/3): the NHL top scorer who missed the team's last game (s6's side finding) - is it the built absence
penalty again (the report lists him out tonight) or new information? Split by what happened TONIGHT (the box, after the
fact): he is OUT again (the report would have had him - the built -6 covers it) vs he is BACK tonight (the report said
nothing or said he plays - the market prices his return; the engine's penalty is 0). Top scorer = points over the
team's last 10 games before its last game (the s6 window). Dog +100..+350 / favorite -101..-200 at the close, the
2021-23 morning; train 2021-23, held 2024 / 2025 / 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2021, 2023), (2024, 2025, 2026)
fin = lib.finals("nhl")
allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021]
tl = lib.team_log(allf)
box = lib.box_rows("nhl")
mo = lib.nhl_morning()


def skaters(gid, team):
    return {r["pid"] for r in (box.get(gid) or {}).get(team) or [] if r["group"] != "goalies"}


def top_scorer(window, team):
    pts = {}
    for x in window:
        for r in (box.get(x["id"]) or {}).get(team) or []:
            if r["group"] == "goalies":
                continue
            try:
                pts[r["pid"]] = pts.get(r["pid"], 0) + float(r["st"].get("goals") or 0) + float(r["st"].get("assists") or 0)
            except ValueError:
                pass
    return max(pts, key=pts.get) if pts else None


C = lib.Cells()
for g in fin:
    if g["season"] < 2021:
        continue
    info = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        prev = [x for x in lib.before(tl, team, g["start"], 11) if x["season"] == g["season"]]
        if len(prev) < 6:
            info[side] = None
            continue
        last, window = prev[-1], prev[-11:-1]
        ts = top_scorer(window, team)
        lastbox = skaters(last["id"], team)
        tonight = skaters(g["id"], team)
        if ts is None or not lastbox or not tonight:
            info[side] = None
            continue
        played_before = sum(1 for x in window[-4:] if ts in skaters(x["id"], team))
        info[side] = {"missed": ts not in lastbox and played_before >= 3, "out_tonight": ts not in tonight}
    for side, team, opp, o, won, is_home in lib.sides(g):
        me = info[side]
        if not me or not me["missed"]:
            continue
        d = lib.dec(o)
        p = lib.profit(won, d)
        tag = "top scorer missed last game, OUT again tonight" if me["out_tonight"] else "top scorer missed last game, BACK tonight"
        for tg in (tag, "top scorer missed last game (either)"):
            C.add(f"{tg} | ML any", g["season"], p)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML +100..+350", g["season"], p)
                m = lib.morning_side(mo, g["id"], side)
                if m and lib.dog_band(m[0]):
                    C.add(f"{tg} | dog ML | MORNING", g["season"], lib.profit(won, m[1]))
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML -101..-200", g["season"], p)
C.dump("s6b", "NHL: THE TOP SCORER MISSED THE TEAM'S LAST GAME - out again tonight (the built absence penalty's cell) vs "
       "BACK tonight (close + the paid 2021-23 morning; train 2021-23, held 2024-26)", TRAIN, HELD)
