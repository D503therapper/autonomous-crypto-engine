"""11/26 daily studies S1-S10 - ten questions SPORTS_FINDINGS.md has never answered (checked first). The quarter family
had the NBA 2nd / 4th, the NHL 2nd / 3rd period, football's 3rd / 4th and the hoops halves (11/20-11/25) - never a
FIRST quarter and never football's second. NHL special teams and faceoffs were set aside on 10/1 because the box
scores held no power-play data ("no such box data") and every later list carried them as done - the TEAM box holds
powerPlayGoals / powerPlayOpportunities / faceoffPercent now: NEW data, read for the first time. The player box's
assists and rebounds BY MAN, the skater box's goals by position and football's second passer were never read. S1 is
asked by the 11/25 look-back (both spread stack plays stood on "their top scorer sat their last game": BYU's man sat
again, Alcorn St's sat the day before and came back for 24).
What a team did THIS season before tonight (no look-ahead), every rate LEAGUE-RELATIVE (the top / bottom fifth of the
league's current values that night), ESPN's close at its own juice, regular season. Cells fixed before the run.
  S1  COLLEGE HOOPS: THE TOP SCORER WHO SAT - by how long ago the game he missed was (yesterday / 2-4 days / 5+)
  S2  FOOTBALL: THE FIRST-QUARTER TEAM - first-quarter margin a game (the scripted start)
  S3  FOOTBALL: THE SECOND-QUARTER TEAM - second-quarter margin a game (the points before the half)
  S4  NBA: THE FIRST-QUARTER TEAM
  S5  NHL: SPECIAL TEAMS - the power play against the penalty kill (the team box's powerPlayGoals / Opportunities)
  S6  NHL: THE FACEOFF TEAM (the team box's faceoffPercent)
  S7  NHL: THE BLUE LINE THAT SCORES - the defensemen's share of the team's goals / shots (the skater box)
  S8  COLLEGE HOOPS: THE POINT-GUARD TEAM - the top assist man's share of the team's assists
  S9  COLLEGE HOOPS: THE ONE-MAN GLASS - the top rebounder's share of the team's rebounds
  S10 FOOTBALL: THE TWO-QUARTERBACK GAME - two men threw 8+ passes in the team's last game
python results/studies/daily_1126/s_today.py [s1 s2nfl s2ncaaf s3nfl s3ncaaf s4 s5 s6 s7 s8 s9 s10nfl s10ncaaf]"""
import bisect
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
from core import teambox, cells, ranked, hi, lo, BT, BH, LT, LH  # noqa: E402
import sports_data as sd  # noqa: E402

FB_T = {"nfl": 20, "ncaaf": 60}


def rank_walk(allf, value, update, minteams):
    """{(gid, team): (value, league pct)} - value(season, team) from the state BEFORE the game (None = not ready),
    ranked among every team's latest value that season; update(g, team, opp) folds the game in after."""
    out, latest = {}, defaultdict(dict)
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            v = value(s, t)
            if v is not None:
                cur[t] = v
                latest[s][t] = v
        vals = latest[s]
        if len(vals) >= minteams:
            srt = sorted(vals.values())
            for t, v in cur.items():
                out[(g["id"], t)] = (v, bisect.bisect_left(srt, v) / (len(srt) - 1))
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            update(g, t, o)
    return out


def last_games(allf):
    """{(gid, team): (the team's previous game this season, days since it)}."""
    prev, out = {}, {}
    for g in allf:
        for t in (g["home"], g["away"]):
            p = prev.get((g["season"], t))
            if p:
                out[(g["id"], t)] = (p, lib.days_between(p["start"], g["start"]))
            prev[(g["season"], t)] = g
    return out


def where(g, side):
    return "neutral" if g["neutral"] else "home" if side == "home" else "road"


# ------------------------------------------------------------------ S1 the top scorer who sat, by the gap
def s1(ret=False):
    import sports_ncaab_roster as nr
    lg = "ncaab"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    d1 = nr.d1_set(sd.load_games(lg)) or set()
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            bx.setdefault(gid, {})[str(t)] = {r["pid"]: (lib.num(r["st"].get("minutes")) or 0.0, lib.num(r["st"].get("points")) or 0.0)
                                               for r in rows}
    hist = defaultdict(list)                              # (season, team) -> [(game, {pid: (min, pts)})] boxed games
    lastany = {}                                          # (season, team) -> the previous game (boxed or not)
    rk, back = {}, defaultdict(lambda: [0, 0])
    for g in allf:
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            key = (g["season"], t)
            rows, prev = hist[key], lastany.get(key)
            if len(rows) >= nr.TEAM_MIN_BOX and prev is not None and rows[-1][0]["id"] == prev["id"]:
                gp = {}
                for _, ps in rows:
                    for pid, (m, p) in ps.items():
                        if m > 0:
                            a = gp.setdefault(pid, [0, 0.0, 0.0])
                            a[0] += 1
                            a[1] += p
                            a[2] += m
                cand = [(a[1] / a[0], pid) for pid, a in gp.items() if a[0] >= nr.TOP_MIN_GAMES and a[2] / a[0] >= nr.TOP_MIN_MPG]
                if cand:
                    ppg, pid = max(cand)
                    out = rows[-1][1].get(pid, (0, 0))[0] <= 0
                    run = 0
                    for _, ps in reversed(rows):
                        if ps.get(pid, (0, 0))[0] > 0:
                            break
                        run += 1
                    popp = prev["away"] if prev["home"] == t else prev["home"]
                    tune = bool(d1) and str(t) in d1 and str(popp) not in d1
                    gap = lib.days_between(prev["start"], g["start"])
                    rk[(g["id"], t)] = {"out": out and not tune, "gap": gap, "run": run, "ppg": ppg, "tune": tune}
                    if out and not tune:
                        tb = (bx.get(g["id"]) or {}).get(str(t))
                        if tb is not None:
                            k = "1" if gap <= 1.5 else "2-4" if gap <= 4.5 else "5+"
                            back[(k, "run1" if run == 1 else "run2+")][0] += 1
                            back[(k, "run1" if run == 1 else "run2+")][1] += tb.get(pid, (0, 0))[0] > 0
        for t in (g["home"], g["away"]):
            b = (bx.get(g["id"]) or {}).get(str(t))
            if b:
                hist[(g["season"], t)].append((g, b))
            lastany[(g["season"], t)] = g
    if ret:
        return fin, rk
    O = h.Out("s1_ncaab_top_scorer_sat_gap", BT, BH)
    O.p("S1 - COLLEGE HOOPS: THE TOP SCORER WHO SAT THE LAST GAME, BY HOW LONG AGO THAT GAME WAS (sports_ncaab_roster's own")
    O.p("  read: the leader in points a game, 3+ games at 20+ minutes, 0 minutes in the team's last game, a D1 team's")
    O.p("  non-D1 tune-up not counted; the player box 2021-26, train 2021-23 / held 2024-26). ACROSS = the other side.")
    O.p("DID HE PLAY TONIGHT (ex post - nobody knows it before the tip):")
    for k in sorted(back):
        n, b = back[k]
        O.p(f"  the game he missed was {k[0]:>3s} day(s) ago, {k[1]:5s}: he played tonight {b} of {n} ({b / max(n, 1) * 100:.0f}%)")

    def flags(me, th, side, g):
        t = []
        if me and me["out"]:
            k = "yesterday" if me["gap"] <= 1.5 else "2-4 days ago" if me["gap"] <= 4.5 else "5+ days ago"
            t += ["its top scorer SAT the last game", f"its top scorer SAT the last game, {k}",
                  f"its top scorer SAT the last game, missed {'only that one' if me['run'] == 1 else '2+ running'}"]
            if me["gap"] <= 1.5 and me["run"] == 1:
                t.append("its top scorer SAT the last game, yesterday, only that one")
        if th and th["out"]:
            k = "yesterday" if th["gap"] <= 1.5 else "2-4 days ago" if th["gap"] <= 4.5 else "5+ days ago"
            t += ["ACROSS a top scorer who sat", f"ACROSS a top scorer who sat, {k}",
                  f"ACROSS a top scorer who sat, missed {'only that one' if th['run'] == 1 else '2+ running'}"]
            if th["gap"] <= 1.5 and th["run"] == 1:
                t.append("ACROSS a top scorer who sat, yesterday, only that one")
            if th["gap"] > 1.5 and th["run"] == 1:
                t.append("ACROSS a top scorer who sat, 2+ days ago, only that one")
        return t
    cells(O, fin, rk, flags, need_both=False)


# ------------------------------------------------------------------ S2 / S3 / S4 the quarter team
def quarter(lg, q, tag, title, cap, minn, y0=2018, ret=False, fbs_only=False):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= y0]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= y0]
    G = sd.load_games(lg)
    if fbs_only:                                         # the control: the read counts FBS-vs-FBS games only
        import sports_players as sp
        allf = [g for g in allf if (lambda f: f and g["home"] in f and g["away"] in f)(sp.fbs_set(G, g["start"]))]
    sums = defaultdict(lambda: [0.0, 0.0, 0])            # (season, team) -> [that quarter's margin, the rest's margin, games]

    def value(s, t):
        a = sums[(s, t)]
        if a[2] < minn:
            return None
        return a[0] / a[2]

    def update(g, t, o):
        gg = G.get(g["id"]) or {}
        hq, aq = lib.quarters(gg.get("ls_home")), lib.quarters(gg.get("ls_away"))
        if not hq or not aq or len(hq) < 4 or len(aq) < 4:
            return
        sign = 1 if g["home"] == t else -1
        a = sums[(g["season"], t)]
        a[0] += max(-cap, min(cap, (hq[q] - aq[q]) * sign))
        a[2] += 1
    rk = rank_walk(allf, value, update, 20 if lg in ("nfl", "nba") else 60)
    if ret:
        return fin, rk
    O = h.Out(tag, LT, LH)
    O.p(title)

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        if me[1] >= 0.8:
            t += ["TOP fifth", "TOP fifth, " + where(g, side)]
            if th[1] <= 0.2:
                t.append("TOP fifth vs a bottom fifth")
        if me[1] >= 0.9:
            t.append("TOP tenth")
        if me[1] <= 0.2:
            t += ["BOTTOM fifth", "BOTTOM fifth, " + where(g, side)]
            if th[1] >= 0.8:
                t.append("BOTTOM fifth vs a top fifth")
        if me[1] <= 0.1:
            t.append("BOTTOM tenth")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both top two fifths", lambda a, b: bool(a and b and a[1] >= 0.6 and b[1] >= 0.6)),
        ("both bottom two fifths", lambda a, b: bool(a and b and a[1] <= 0.4 and b[1] <= 0.4))])


# ------------------------------------------------------------------ S5 / S6 the NHL team box
def _pair(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def s5(ret=False):
    lg = "nhl"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    tb = teambox(lg)

    def counters(g, t, o):
        b = tb.get(g["id"]) or {}
        me, op = b.get(str(t)), b.get(str(o))
        if not me or not op:
            return None
        v = [_pair(me.get("powerPlayGoals")), _pair(me.get("powerPlayOpportunities")), _pair(op.get("powerPlayGoals")),
             _pair(op.get("powerPlayOpportunities")), _pair(me.get("shortHandedGoals")), _pair(op.get("shortHandedGoals"))]
        if v[1] is None or v[3] is None:
            return None
        return {"ppg": v[0] or 0, "ppo": v[1], "oppg": v[2] or 0, "oppo": v[3], "shg": v[4] or 0, "shga": v[5] or 0}

    def feats(s, n):
        if s["ppo"] < 20 or s["oppo"] < 20:
            return None
        pp, pk = s["ppg"] / s["ppo"], 1 - s["oppg"] / s["oppo"]
        return {"pp": pp, "pk": pk, "net": pp + pk, "sh": (s["shg"] - s["shga"]) / n, "shf": s["shg"] / n}
    rk = ranked(allf, counters, feats, 10)
    if ret:
        return fin, rk
    O = h.Out("s5_nhl_special_teams", BT, BH)
    O.p("S5 - NHL: SPECIAL TEAMS (the TEAM box's powerPlayGoals / powerPlayOpportunities / shortHandedGoals - never read: the")
    O.p("  10/1 study was set aside with 'no power-play data in the box scores'; season to date, 10+ boxed games, 20+ chances")
    O.p("  each way, ranked in the league that night; 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "pp"):
            t.append("POWER PLAY top fifth")
            if lo(th, "pk"):
                t.append("POWER PLAY top fifth vs a bottom-fifth KILL")
        if lo(me, "pp"):
            t.append("POWER PLAY bottom fifth")
        if hi(me, "pk"):
            t.append("KILL top fifth")
            if hi(th, "pp"):
                t.append("KILL top fifth vs a top-fifth power play")
        if lo(me, "pk"):
            t.append("KILL bottom fifth")
        if hi(me, "net"):
            t += ["SPECIAL TEAMS (PP% + PK%) top fifth", "SPECIAL TEAMS top fifth, " + where(g, side)]
            if lo(th, "net"):
                t.append("SPECIAL TEAMS top fifth vs a bottom fifth")
        if lo(me, "net"):
            t += ["SPECIAL TEAMS bottom fifth", "SPECIAL TEAMS bottom fifth, " + where(g, side)]
            if hi(th, "net"):
                t.append("SPECIAL TEAMS bottom fifth vs a top fifth")
        if hi(me, "shf"):
            t.append("SHORT-HANDED GOALS for, top fifth")
        if lo(me, "sh"):
            t.append("SHORT-HANDED GOALS net, bottom fifth (gives them up)")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both power plays top two fifths", lambda a, b: a["pp"][1] >= 0.6 and b["pp"][1] >= 0.6),
        ("both kills bottom two fifths", lambda a, b: a["pk"][1] <= 0.4 and b["pk"][1] <= 0.4),
        ("both kills top two fifths", lambda a, b: a["pk"][1] >= 0.6 and b["pk"][1] >= 0.6)])


def s6():
    lg = "nhl"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    tb = teambox(lg)

    def counters(g, t, o):
        me = (tb.get(g["id"]) or {}).get(str(t))
        v = _pair((me or {}).get("faceoffPercent"))
        if v is None or v <= 0:
            return None
        return {"fo": v, "home": 1.0 if g["home"] == t else 0.0, "foh": v if g["home"] == t else 0.0}

    def feats(s, n):
        return {"fo": s["fo"] / n}
    rk = ranked(allf, counters, feats, 10)
    O = h.Out("s6_nhl_faceoffs", BT, BH)
    O.p("S6 - NHL: THE FACEOFF TEAM (the TEAM box's faceoffPercent a game, season to date, 10+ boxed games, ranked in the")
    O.p("  league that night; 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "fo"):
            t += ["FACEOFFS top fifth", "FACEOFFS top fifth, " + where(g, side)]
            if lo(th, "fo"):
                t.append("FACEOFFS top fifth vs a bottom fifth")
        if me["fo"][1] >= 0.9:
            t.append("FACEOFFS top tenth")
        if lo(me, "fo"):
            t += ["FACEOFFS bottom fifth", "FACEOFFS bottom fifth, " + where(g, side)]
            if hi(th, "fo"):
                t.append("FACEOFFS bottom fifth vs a top fifth")
        if me["fo"][1] <= 0.1:
            t.append("FACEOFFS bottom tenth")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both top two fifths", lambda a, b: a["fo"][1] >= 0.6 and b["fo"][1] >= 0.6),
        ("both bottom two fifths", lambda a, b: a["fo"][1] <= 0.4 and b["fo"][1] <= 0.4)])


# ------------------------------------------------------------------ S7 the blue line that scores
def s7():
    lg = "nhl"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            d = [0.0, 0.0, 0.0, 0.0]                      # D goals, all goals, D shots, all shots
            for r in rows:
                if r["pos"] == "G":
                    continue
                gl, sh = lib.num(r["st"].get("goals")) or 0.0, lib.num(r["st"].get("shotsTotal")) or 0.0
                d[1] += gl
                d[3] += sh
                if r["pos"] == "D":
                    d[0] += gl
                    d[2] += sh
            if d[3] > 0:
                bx.setdefault(gid, {})[str(t)] = d
    sums = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])

    def mk(i, j, need):
        def value(s, t):
            a = sums[(s, t)]
            if a[4] < 10 or a[j] < need:
                return None
            return a[i] / a[j]
        return value

    def update(g, t, o):
        d = (bx.get(g["id"]) or {}).get(str(t))
        if d:
            a = sums[(g["season"], t)]
            for i in range(4):
                a[i] += d[i]
            a[4] += 1
    gs = rank_walk(allf, mk(0, 1, 20), lambda g, t, o: None, 20)   # (values read before update - one walk does both)
    # two reads need the same walk: run the walk once with both values
    sums.clear()
    out_g, out_s = {}, {}
    latest_g, latest_s = defaultdict(dict), defaultdict(dict)
    vg, vs = mk(0, 1, 20), mk(2, 3, 200)
    for g in allf:
        s = g["season"]
        for val, latest, out in ((vg, latest_g, out_g), (vs, latest_s, out_s)):
            cur = {}
            for t in (g["home"], g["away"]):
                v = val(s, t)
                if v is not None:
                    cur[t] = v
                    latest[s][t] = v
            if len(latest[s]) >= 20:
                srt = sorted(latest[s].values())
                for t, v in cur.items():
                    out[(g["id"], t)] = (v, bisect.bisect_left(srt, v) / (len(srt) - 1))
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            update(g, t, o)
    del gs
    rk = {k: {"g": out_g[k], "s": out_s[k]} for k in out_g if k in out_s}
    O = h.Out("s7_nhl_blue_line", BT, BH)
    O.p("S7 - NHL: THE BLUE LINE THAT SCORES (the defensemen's share of the team's goals and of its shots, the skater box's")
    O.p("  position column, season to date, 10+ boxed games, ranked in the league that night; 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "g"):
            t += ["D SCORES (top fifth share of the goals)", "D SCORES, " + where(g, side)]
        if lo(me, "g"):
            t += ["D DOESN'T SCORE (bottom fifth share of the goals)", "D DOESN'T SCORE, " + where(g, side)]
        if hi(me, "s"):
            t += ["D SHOOTS (top fifth share of the shots)"]
            if lo(me, "g"):
                t.append("D SHOOTS and doesn't score (top fifth shots, bottom fifth goals)")
        if lo(me, "s"):
            t += ["FORWARDS SHOOT (bottom fifth D share of the shots)"]
        return t
    cells(O, fin, rk, flags, totals=[
        ("both D-shooting teams (top two fifths)", lambda a, b: a["s"][1] >= 0.6 and b["s"][1] >= 0.6),
        ("both forward-shooting teams (bottom two fifths)", lambda a, b: a["s"][1] <= 0.4 and b["s"][1] <= 0.4)])


# ------------------------------------------------------------------ S8 / S9 one man's share of a college box column
def share(col, tag, title, big, small):
    lg = "ncaab"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            d = {r["pid"]: lib.num(r["st"].get(col)) or 0.0 for r in rows if lib.num(r["st"].get("minutes"))}
            if d and sum(d.values()) > 0:
                bx.setdefault(gid, {})[str(t)] = d
    tot = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)

    def value(s, t):
        d = tot[(s, t)]
        if n[(s, t)] < 5 or sum(d.values()) <= 0:
            return None
        return max(d.values()) / sum(d.values())

    def update(g, t, o):
        d = (bx.get(g["id"]) or {}).get(str(t))
        if d:
            for pid, v in d.items():
                tot[(g["season"], t)][pid] += v
            n[(g["season"], t)] += 1
    rk = rank_walk(allf, value, update, 100)
    O = h.Out(tag, BT, BH)
    O.p(title)

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        if me[1] >= 0.8:
            t += [f"{big} (top fifth share)", f"{big}, " + where(g, side)]
            if th[1] <= 0.2:
                t.append(f"{big} vs {small}")
        if me[1] >= 0.9:
            t.append(f"{big} (top tenth share)")
        if me[1] <= 0.2:
            t += [f"{small} (bottom fifth share)", f"{small}, " + where(g, side)]
            if th[1] >= 0.8:
                t.append(f"{small} vs {big}")
        if me[1] <= 0.1:
            t.append(f"{small} (bottom tenth share)")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S10 the two-quarterback game
def s10(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    lastg = last_games(allf)
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            att = []
            for r in rows:
                if r["group"] != "passing":
                    continue
                try:
                    att.append(float(str(r["st"].get("completions/passingAttempts")).split("/")[1]))
                except (IndexError, ValueError):
                    continue
            if att:
                bx.setdefault(gid, {})[str(t)] = sorted(att, reverse=True)
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x:
                continue
            p, d = x
            a = (bx.get(p["id"]) or {}).get(str(t))
            if not a:
                continue
            m = lib.margin_g(p, t)
            rk[(g["id"], t)] = {"two": len(a) >= 2 and a[1] >= 8, "m": m, "second": a[1] if len(a) > 1 else 0.0}
    O = h.Out(f"s10_{lg}_two_quarterbacks", BT, BH)
    O.p(f"S10 - {lg.upper()}: THE TWO-QUARTERBACK GAME (two men threw 8+ passes in the team's last game - the player box's passing")
    O.p("  group, 2021-26, train 2021-23 / held 2024-26; 'a real game' = that game ended within 16 points, so no mop-up duty)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["two"]:
            t.append("TWO QBs last game")
            if abs(me["m"]) <= 16:
                t.append("TWO QBs last game, a real game (within 16)")
            if me["m"] < 0:
                t.append("TWO QBs last game, a loss")
            if me["m"] <= -17:
                t.append("TWO QBs last game, a loss by 17+")
            if me["m"] >= 17:
                t.append("TWO QBs last game, a win by 17+ (mop-up)")
            if me["second"] >= 15:
                t.append("TWO QBs last game, the second man threw 15+")
        if th and th["two"] and abs(th["m"]) <= 16:
            t.append("ACROSS a two-QB team (a real game)")
        return t
    cells(O, fin, rk, flags, totals=[
        ("a two-QB team on either side (a real game)", lambda a, b: bool((a and a["two"] and abs(a["m"]) <= 16) or (b and b["two"] and abs(b["m"]) <= 16)))],
        need_both=False)


if __name__ == "__main__":
    Q = "{} - {}: THE {}-QUARTER TEAM ({} quarter margin a game, each game capped at {}, season to date, {}+ line scores,\n  ranked in the league that night; the line scores 2018-26, train 2018-21 / held 2022-26)"
    RUN = {
        "s1": s1,
        "s2nfl": lambda: quarter("nfl", 0, "s2_nfl_first_quarter", Q.format("S2", "NFL", "FIRST", "first", 14, 4), 14, 4),
        "s2ncaaf": lambda: quarter("ncaaf", 0, "s2_ncaaf_first_quarter", Q.format("S2", "COLLEGE FOOTBALL", "FIRST", "first", 14, 4), 14, 4),
        "s3nfl": lambda: quarter("nfl", 1, "s3_nfl_second_quarter", Q.format("S3", "NFL", "SECOND", "second", 14, 4), 14, 4),
        "s3ncaaf": lambda: quarter("ncaaf", 1, "s3_ncaaf_second_quarter", Q.format("S3", "COLLEGE FOOTBALL", "SECOND", "second", 14, 4), 14, 4),
        "s4": lambda: quarter("nba", 0, "s4_nba_first_quarter", Q.format("S4", "NBA", "FIRST", "first", 15, 10), 15, 10),
        "s5": s5, "s6": s6, "s7": s7,
        "s8": lambda: share("assists", "s8_ncaab_point_guard_team",
                            "S8 - COLLEGE HOOPS: THE POINT-GUARD TEAM (the top assist man's share of the team's assists, season to date, 5+ boxed\n"
                            "  games, ranked in the league that night; the player box 2021-26, train 2021-23 / held 2024-26)",
                            "ONE PASSER", "EVERYBODY PASSES"),
        "s9": lambda: share("rebounds", "s9_ncaab_one_man_glass",
                            "S9 - COLLEGE HOOPS: THE ONE-MAN GLASS (the top rebounder's share of the team's rebounds, season to date, 5+ boxed\n"
                            "  games, ranked in the league that night; the player box 2021-26, train 2021-23 / held 2024-26)",
                            "ONE-MAN GLASS", "GANG REBOUNDS"),
        "s10nfl": lambda: s10("nfl"), "s10ncaaf": lambda: s10("ncaaf")}
    for a in sys.argv[1:] or list(RUN):
        RUN[a]()
