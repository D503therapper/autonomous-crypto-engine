"""Study 6 (11/3): NHL - THE ICE-TIME LEADER OUT (the #1 defenseman). The 10/31 lead tracks a small favorite missing a
TOP SCORER; the hockey absence penalty counts points. The man who logs the most minutes (nearly always the #1 D) is a
different kind of loss - the one the scoring-based reads under-weigh. From the roster box scores 2021-26: each team's
ice-time leader = the skater with the top average timeOnIce over its last 10 games (5+ played). Known-before-tip cut:
he MISSED THE TEAM'S LAST GAME (played 3 of the 4 before it) - so the morning board knows. Upper bound: he is out of
TONIGHT's box (a leak - after the fact). Sides: dog +100..+350, favorite -101..-200, ATS none (puck lines); the opponent
across; the 2021-23 paid MORNING price. Train 2021-23, held 2024 / 2025 / 2026 apart."""
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
    out = {}
    for r in (box.get(gid) or {}).get(team) or []:
        if r["group"] == "goalies":
            continue
        t = lib.toi(r["st"].get("timeOnIce"))
        if t is not None and t > 0:
            out[r["pid"]] = t
    return out


def leader(prev):
    """the ice-time leader over the games `prev` (team games, oldest first): (pid, avg) or None."""
    tot, n = {}, {}
    for x in prev:
        for pid, t in skaters(x["id"], x["team"]).items():
            tot[pid] = tot.get(pid, 0.0) + t
            n[pid] = n.get(pid, 0) + 1
    best = None
    for pid in tot:
        if n[pid] >= 5:
            avg = tot[pid] / n[pid]
            if best is None or avg > best[1]:
                best = (pid, avg)
    return best


C = lib.Cells()
for g in fin:
    if g["season"] < 2021:
        continue
    info = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        prev = [dict(x, team=team) for x in lib.before(tl, team, g["start"], 11) if x["season"] == g["season"]]
        if len(prev) < 6:
            info[side] = None
            continue
        last = prev[-1]
        window = prev[-11:-1]                       # the 10 before the last game
        ld = leader(window)
        if not ld:
            info[side] = None
            continue
        pid = ld[0]
        played_before = sum(1 for x in window[-4:] if pid in skaters(x["id"], team))
        missed_last = pid not in skaters(last["id"], team) and bool(skaters(last["id"], team)) and played_before >= 3
        tonight = skaters(g["id"], team)
        out_tonight = bool(tonight) and pid not in tonight
        # the top scorer (points over the window) for the comparison
        pts, cnt = {}, {}
        for x in window:
            for r in (box.get(x["id"]) or {}).get(team) or []:
                if r["group"] == "goalies":
                    continue
                try:
                    pts[r["pid"]] = pts.get(r["pid"], 0) + float(r["st"].get("goals") or 0) + float(r["st"].get("assists") or 0)
                except ValueError:
                    pass
        ts = max(pts, key=pts.get) if pts else None
        ts_missed = ts is not None and ts not in skaters(last["id"], team) and bool(skaters(last["id"], team))
        info[side] = {"missed": missed_last, "out": out_tonight, "ts_missed": ts_missed, "same": ts == pid,
                      "back": (not out_tonight) and missed_last}
    for side, team, opp, o, won, is_home in lib.sides(g):
        me, ot = info[side], info["away" if side == "home" else "home"]
        if me is None or ot is None:
            continue
        d = lib.dec(o)
        p = lib.profit(won, d)
        tags = []
        if me["missed"]:
            tags.append("ice-time leader missed its last game")
            if not me["same"]:
                tags.append("ice-time leader (not the top scorer) missed its last game")
            if me["out"]:
                tags.append("ice-time leader missed last game AND out tonight (leak)")
            if me["back"]:
                tags.append("ice-time leader missed last game, BACK tonight (leak)")
        if me["out"] and not me["missed"]:
            tags.append("ice-time leader out tonight, played last game (leak - fresh news)")
        if me["ts_missed"] and not me["missed"]:
            tags.append("top scorer (not the TOI leader) missed its last game")
        if ot["missed"]:
            tags.append("vs a team whose ice-time leader missed its last game")
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
C.dump("s6", "NHL: THE ICE-TIME LEADER (top avg TOI, last 10) MISSED THE TEAM'S LAST GAME - box scores 2021-26; close + "
       "the paid 2021-23 morning; train 2021-23, held 2024-26", TRAIN, HELD)
