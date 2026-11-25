"""11/25 daily studies S1-S10 - ten questions SPORTS_FINDINGS.md has never answered (checked first: no study on the
pros' PARTY-CITY road stop, a football team in weather far colder than its own home norm (the dome team was read
10/15 / 10/29 - this is the outdoor team's own climate), the passing game that runs through ONE receiver, the back who
carried the load last week, the college football team off a NON-FBS tune-up (the hoops twin was built 11/20-21), last
week's TURNOVER battle as one game's luck, the college hoops ONE-MAN team (the NBA top-2 share was 11/19 S10), the
college hoops SECOND-HALF team (the pros' quarters / periods were 11/9 - 11/24), the GUARD-HEAVY team off the box's
position column). The brief's Thanksgiving list was answered before (short weeks and Thursday 11/12 b1, the holidays
10/31, rivalry week 10/31 + 11/1 + 11/21, the game after an event 11/3) - not re-run.
What a team did THIS season before tonight (no look-ahead), every rate LEAGUE-RELATIVE (the top / bottom fifth of the
league's current values that night), ESPN's close at its own juice, regular season. Cells fixed before the run.
  S1  NBA: THE PARTY CITY - a visitor with a free night (2+ days since its last game) in Miami / Los Angeles /
      New York / New Orleans
  S2  NHL: THE PARTY CITY - Las Vegas / Nashville / Sunrise / Tampa / Los Angeles / New York / Montreal / Tempe
  S3  FOOTBALL: THE COLD SHOCK - an outdoor team playing 20+ degrees under its own November-January home norm, 40 F
      or colder
  S4  FOOTBALL: THE ONE-MAN PASSING GAME - the top receiver's share of the team's receiving yards (the player box)
  S5  FOOTBALL: THE WORKHORSE BACK - one back carried 25+ (NFL) / 28+ (college) times last game; the season share
  S6  COLLEGE FOOTBALL: OFF A NON-FBS TUNE-UP against a team off an FBS game
  S7  FOOTBALL: LAST WEEK'S TURNOVER BATTLE - won / lost it by 3+ (the team box's turnovers, one game)
  S8  COLLEGE HOOPS: THE ONE-MAN TEAM - the top scorer's share of the points; the count of 10-a-game men
  S9  COLLEGE HOOPS: THE SECOND-HALF TEAM - second-half margin minus first-half margin a game (the line scores)
  S10 COLLEGE HOOPS + NBA: THE GUARD-HEAVY TEAM - the share of the minutes its guards play (the box's position)
python results/studies/daily_1125/s_today.py [s1 s2 s3nfl s3ncaaf s4nfl s4ncaaf s5nfl s5ncaaf s6 s7nfl s7ncaaf s8 s9 s10ncaab s10nba]"""
import bisect
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
from core import teambox, cells, BT, BH, LT, LH  # noqa: E402
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


# ------------------------------------------------------------------ S1 / S2 the party city
PARTY = {"nba": {"Miami", "Los Angeles", "Inglewood", "New York", "Brooklyn", "New Orleans"},
         "nhl": {"Las Vegas", "Nashville", "Sunrise", "Tampa", "Los Angeles", "New York", "Montreal", "Tempe"}}


def party(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2018 and not g["neutral"]]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2018]
    G = sd.load_games(lg)
    lastg = last_games(allf)
    rk = {}
    for g in fin:
        city = (G.get(g["id"]) or {}).get("city") or ""
        for t in (g["home"], g["away"]):
            lg_ = lastg.get((g["id"], t))
            if not lg_:
                continue
            p, d = lg_
            pcity = (G.get(p["id"]) or {}).get("city") or ""
            rk[(g["id"], t)] = {"city": city, "rest": d, "same": pcity == city or {pcity, city} <= {"Los Angeles", "Inglewood"}
                                or {pcity, city} <= {"New York", "Brooklyn", "Newark", "Elmont"},
                                "dow": lib._t(g["start"]).weekday()}
    O = h.Out(f"s{1 if lg == 'nba' else 2}_{lg}_party_city", LT, LH)
    O.p(f"S{1 if lg == 'nba' else 2} - {lg.upper()}: THE PARTY CITY ({', '.join(sorted(PARTY[lg]))}; the visitor's days since its last game;")
    O.p("  a free night = 1.5+ days since a game in another city; 2018-26, train 2018-21 / held 2022-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        pc = me["city"] in PARTY[lg]
        free = me["rest"] >= 1.5 and not me["same"]
        if side == "away":
            t.append("VISITOR, any city")
            if free:
                t.append("VISITOR with a free night, any OTHER city" if not pc else "VISITOR with a free night in a PARTY city")
                if pc:
                    t.append(f"VISITOR free night in {me['city'] if me['city'] not in ('Inglewood', 'Brooklyn') else ('Los Angeles' if me['city'] == 'Inglewood' else 'New York')}")
                    if me["rest"] >= 2.5:
                        t.append("VISITOR with TWO+ free nights in a PARTY city")
                    else:
                        t.append("VISITOR with ONE free night in a PARTY city")
                    if me["dow"] in (5, 6, 0):               # (UTC: a Fri / Sat / Sun night game = a weekend night before)
                        t.append("VISITOR free night in a PARTY city, a weekend game")
                elif me["rest"] >= 2.5:
                    t.append("VISITOR with TWO+ free nights, any OTHER city")
            elif pc:
                t.append("VISITOR in a PARTY city, NO free night (back-to-back or already in town)")
        else:
            if pc and th and th["rest"] >= 1.5 and not th["same"]:
                t.append("HOME side in a PARTY city vs a visitor with a free night")
            elif (not pc) and th and th["rest"] >= 1.5 and not th["same"]:
                t.append("HOME side in any OTHER city vs a visitor with a free night")
        return t
    cells(O, fin, rk, flags, need_both=False)
    for kind in ("ATS", "dog +100..+350", "small fav -150..-101", "fav past -150"):
        O.placebo(f"VISITOR with a free night in a PARTY city: {kind}", f"VISITOR with a free night, any OTHER city: {kind}", fade=True)
    O.save()


# ------------------------------------------------------------------ S3 the cold shock
def cold(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2018]
    G = sd.load_games(lg)
    home_t = defaultdict(list)                           # team -> its Nov-Jan home temps (indoors = 70), every season
    for g in G.values():
        if g.get("status") != "final" or str(g.get("neutral")) == "1" or g["start"][5:7] not in ("11", "12", "01"):
            continue
        if str(g.get("indoor")) == "1":
            home_t[g["home"]].append(70.0)
        else:
            t = lib.num(g.get("wx_temp"))
            if t is not None:
                home_t[g["home"]].append(t)
    norm = {t: statistics.median(v) for t, v in home_t.items() if len(v) >= 4}
    dome = {t for t, v in home_t.items() if len(v) >= 4 and sum(1 for x in v if x == 70.0) / len(v) >= 0.75}
    rk = {}
    for g in fin:
        gg = G.get(g["id"]) or {}
        t = lib.num(gg.get("wx_temp"))
        if t is None or str(gg.get("indoor")) == "1" or g["start"][5:7] not in ("11", "12", "01"):
            continue
        for tm in (g["home"], g["away"]):
            if tm in norm:
                rk[(g["id"], tm)] = {"t": t, "gap": norm[tm] - t, "dome": tm in dome, "wind": lib.num(gg.get("wx_wind")) or 0.0}
    O = h.Out(f"s3_{lg}_cold_shock", LT, LH)
    O.p(f"S3 - {lg.upper()}: THE COLD SHOCK (outdoor games Nov-Jan with a kickoff temperature on file; a team's NORM = the")
    O.p("  median temperature of its own Nov-Jan home games, a roof = 70 F; shock = the game is 20+ F under its norm and 40 F or colder)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE outdoor Nov-Jan game")
        cold_ = me["t"] <= 40
        if cold_:
            t.append("ANY team at 40 F or colder")
        shock = cold_ and me["gap"] >= 20
        used = th is not None and th["gap"] < 10
        if shock:
            t.append("SHOCKED team (20+ under its norm, 40 F or colder)")
            if not me["dome"]:
                t.append("SHOCKED OUTDOOR team (its home has no roof)")
                if used:
                    t.append("SHOCKED OUTDOOR team vs a team used to it (within 10 of its norm)")
                if me["t"] <= 32:
                    t.append("SHOCKED OUTDOOR team at freezing or colder")
            if me["gap"] >= 30:
                t.append("SHOCKED team, 30+ under its norm")
        if cold_ and th is not None and th["t"] <= 40 and th["gap"] >= 20 and not th["dome"] and me["gap"] < 10:
            t.append("the team USED to it vs a shocked outdoor team")
        return t

    def both(f):
        return lambda a, b: bool(a and b and f(a, b))
    cells(O, fin, rk, flags, totals=[
        ("one side shocked (outdoor team, 20+ under its norm, 40 F or colder)",
         both(lambda a, b: a["t"] <= 40 and ((a["gap"] >= 20 and not a["dome"]) != (b["gap"] >= 20 and not b["dome"])))),
        ("40 F or colder", both(lambda a, b: a["t"] <= 40))], need_both=False)


# ------------------------------------------------------------------ football player box helpers
def fb_box(lg):
    """{gid: {team: {"rec": {pid: yards}, "rush": {pid: attempts}}}} from the player box."""
    out = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            d = {"rec": defaultdict(float), "rush": defaultdict(float)}
            for r in rows:
                if r["group"] == "receiving":
                    v = lib.num(r["st"].get("receivingYards"))
                    if v is not None:
                        d["rec"][r["pid"]] += max(0.0, v)
                elif r["group"] == "rushing":
                    v = lib.num(r["st"].get("rushingAttempts"))
                    if v is not None:
                        d["rush"][r["pid"]] += v
            out.setdefault(gid, {})[str(t)] = d
    return out


def s4(lg, ret=False):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = fb_box(lg)
    tot = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)

    def value(s, t):
        d = tot[(s, t)]
        if n[(s, t)] < 4 or sum(d.values()) <= 0:
            return None
        return max(d.values()) / sum(d.values())

    def update(g, t, o):
        d = (bx.get(g["id"]) or {}).get(str(t))
        if d and d["rec"]:
            for pid, v in d["rec"].items():
                tot[(g["season"], t)][pid] += v
            n[(g["season"], t)] += 1
    rk = rank_walk(allf, value, update, FB_T[lg])
    if ret:
        return fin, rk
    O = h.Out(f"s4_{lg}_one_man_passing_game", BT, BH)
    O.p(f"S4 - {lg.upper()}: THE ONE-MAN PASSING GAME (the top receiver's share of the team's receiving yards, season to date,")
    O.p("  4+ boxed games, ranked in the league that night; the player box 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        if me[1] >= 0.8:
            t.append("ONE-MAN passing game (top fifth share)")
            if th[1] <= 0.5:
                t.append("ONE-MAN passing game vs a team in the bottom half")
            t.append("ONE-MAN passing game, " + ("home" if side == "home" else "road"))
        if me[1] <= 0.2:
            t.append("SPREADS IT (bottom fifth share)")
            if th[1] >= 0.8:
                t.append("SPREADS IT vs a one-man passing game")
        if me[1] >= 0.9:
            t.append("ONE-MAN passing game (top tenth)")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both one-man passing games (top two fifths)", lambda a, b: bool(a and b and a[1] >= 0.6 and b[1] >= 0.6)),
        ("both spread it (bottom two fifths)", lambda a, b: bool(a and b and a[1] <= 0.4 and b[1] <= 0.4))])


def s5(lg, ret=False):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = fb_box(lg)
    lastg = last_games(allf)
    big = 25 if lg == "nfl" else 28
    tot = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)

    def value(s, t):
        d = tot[(s, t)]
        if n[(s, t)] < 4 or sum(d.values()) <= 0:
            return None
        return max(d.values()) / sum(d.values())

    def update(g, t, o):
        d = (bx.get(g["id"]) or {}).get(str(t))
        if d and d["rush"]:
            for pid, v in d["rush"].items():
                tot[(g["season"], t)][pid] += v
            n[(g["season"], t)] += 1
    share = rank_walk(allf, value, update, FB_T[lg])
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            lg_ = lastg.get((g["id"], t))
            if not lg_:
                continue
            p, d = lg_
            b = (bx.get(p["id"]) or {}).get(str(t))
            if not b or not b["rush"]:
                continue
            rk[(g["id"], t)] = {"top": max(b["rush"].values()), "days": d, "won": lib.won_g(p, t), "share": share.get((g["id"], t))}
    if ret:
        return fin, rk
    O = h.Out(f"s5_{lg}_workhorse_back", BT, BH)
    O.p(f"S5 - {lg.upper()}: THE WORKHORSE BACK (one man carried {big}+ times in the team's last game; the top back's share of")
    O.p("  the season's carries, 4+ boxed games, ranked in the league; the player box 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["top"] >= big:
            t.append(f"its back carried {big}+ last game")
            if me["days"] <= 6.5:
                t.append(f"its back carried {big}+ last game, 6 days or less ago")
            if me["won"]:
                t.append(f"its back carried {big}+ last game in a win")
            if th and th["top"] < big:
                t.append(f"its back carried {big}+ last game, the other side's did not")
        if me["top"] >= big + 5:
            t.append(f"its back carried {big + 5}+ last game")
        if me["share"] and me["share"][1] >= 0.8:
            t.append("BELL COW (top fifth share of the season's carries)")
        if me["share"] and me["share"][1] <= 0.2:
            t.append("COMMITTEE (bottom fifth share of the season's carries)")
        return t
    cells(O, fin, rk, flags, totals=[
        (f"a back carried {big}+ last game on either side", lambda a, b: bool((a and a["top"] >= big) or (b and b["top"] >= big))),
        (f"a back carried {big}+ last game on both sides", lambda a, b: bool(a and b and a["top"] >= big and b["top"] >= big))],
        need_both=False)


# ------------------------------------------------------------------ S6 college football off a non-FBS tune-up
def s6():
    import sports_players as sp
    G = sd.load_games("ncaaf")
    fin = [g for g in lib.finals("ncaaf") if g["stype"] == "2" and g["season"] >= 2018]
    allf = [g for g in lib.all_finals("ncaaf") if g["season"] >= 2018]
    lastg = last_games(allf)
    rk = {}
    for g in fin:
        fbs = sp.fbs_set(G, g["start"])
        if not fbs or g["home"] not in fbs or g["away"] not in fbs:
            continue
        for t in (g["home"], g["away"]):
            lg_ = lastg.get((g["id"], t))
            if not lg_:
                continue
            p, d = lg_
            o = p["away"] if p["home"] == t else p["home"]
            rk[(g["id"], t)] = {"tune": o not in fbs, "days": d, "m": lib.margin_g(p, t), "home_last": p["home"] == t,
                                "month": g["start"][5:7]}
    O = h.Out("s6_ncaaf_non_fbs_tune_up", LT, LH)
    O.p("S6 - COLLEGE FOOTBALL: OFF A NON-FBS TUNE-UP (FBS vs FBS games; a team's last game, 6-9 days ago, was against a")
    O.p("  team outside the FBS - sports_players.fbs_set, walk-forward; 2018-26, train 2018-21 / held 2022-26)")

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        wk = me["days"] <= 9.5 and th["days"] <= 9.5
        t.append("BASE FBS vs FBS, both with a game this season")
        if me["tune"] and me["days"] <= 9.5:
            t.append("OFF A TUNE-UP (any opponent)")
            if not th["tune"] and wk:
                t.append("OFF A TUNE-UP vs a team off an FBS game")
                t.append("OFF A TUNE-UP vs a team off an FBS game, " + ("Nov" if me["month"] in ("11", "12") else "Sep-Oct"))
                t.append("OFF A TUNE-UP vs a team off an FBS game, " + ("home" if side == "home" else "road"))
                if th["m"] < 0:
                    t.append("OFF A TUNE-UP vs a team off an FBS LOSS")
                else:
                    t.append("OFF A TUNE-UP vs a team off an FBS WIN")
                if me["m"] >= 35:
                    t.append("OFF A 35+ TUNE-UP WIN vs a team off an FBS game")
        if (not me["tune"]) and th["tune"] and wk:
            t.append("OFF AN FBS GAME vs a team off a tune-up")
        return t
    cells(O, fin, rk, flags, totals=[
        ("one side off a tune-up, the other off an FBS game", lambda a, b: bool(a and b and a["tune"] != b["tune"] and a["days"] <= 9.5 and b["days"] <= 9.5))])


# ------------------------------------------------------------------ S7 last week's turnover battle
def s7(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    tb = teambox(lg)
    lastg = last_games(allf)
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            lg_ = lastg.get((g["id"], t))
            if not lg_:
                continue
            p, d = lg_
            o = p["away"] if p["home"] == t else p["home"]
            b = tb.get(p["id"]) or {}
            a_, b_ = lib.num((b.get(str(t)) or {}).get("turnovers")), lib.num((b.get(str(o)) or {}).get("turnovers"))
            if a_ is None or b_ is None or d > 15:
                continue
            rk[(g["id"], t)] = {"tm": b_ - a_, "won": lib.won_g(p, t), "m": lib.margin_g(p, t)}
    O = h.Out(f"s7_{lg}_turnover_battle_last_game", BT, BH)
    O.p(f"S7 - {lg.upper()}: LAST WEEK'S TURNOVER BATTLE (the team box's turnovers in the team's last game: taken minus given;")
    O.p("  the team box 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["tm"] >= 3:
            t.append("WON the turnover battle by 3+ last game")
            if me["won"]:
                t.append("WON the turnover battle by 3+ last game and the game")
                if me["m"] <= 8:
                    t.append("WON the turnover battle by 3+ last game and the game by 8 or less")
            if th and th["tm"] <= 0:
                t.append("WON the turnover battle by 3+ last game, the other side did not win its own")
        if me["tm"] <= -3:
            t.append("LOST the turnover battle by 3+ last game")
            if not me["won"]:
                t.append("LOST the turnover battle by 3+ last game and the game")
            if th and th["tm"] >= 0:
                t.append("LOST the turnover battle by 3+ last game, the other side did not lose its own")
        if me["tm"] >= 3 and th and th["tm"] <= -3:
            t.append("WON it by 3+ vs a team that LOST it by 3+")
        if me["tm"] <= -3 and th and th["tm"] >= 3:
            t.append("LOST it by 3+ vs a team that WON it by 3+")
        return t
    cells(O, fin, rk, flags, need_both=False)


# ------------------------------------------------------------------ S8 / S10 the hoops player box
def hoop_box(lg):
    """{gid: {team: [(pid, minutes, points, is guard)]}}."""
    out = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            lst = []
            for r in rows:
                m, p = lib.num(r["st"].get("minutes")), lib.num(r["st"].get("points"))
                if m:
                    lst.append((r["pid"], m, p or 0.0, r["pos"] in ("G", "PG", "SG")))
            if lst:
                out.setdefault(gid, {})[str(t)] = lst
    return out


def s8(ret=False):
    lg = "ncaab"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = hoop_box(lg)
    pts = defaultdict(lambda: defaultdict(float))
    gp = defaultdict(lambda: defaultdict(int))
    n = defaultdict(int)

    def value(s, t):
        d = pts[(s, t)]
        if n[(s, t)] < 5 or sum(d.values()) <= 0:
            return None
        return max(d.values()) / sum(d.values())

    def tens(s, t):
        k = n[(s, t)]
        return sum(1 for pid, v in pts[(s, t)].items() if gp[(s, t)][pid] >= max(3, k // 2) and v / gp[(s, t)][pid] >= 10)
    tens_at = {}

    def update(g, t, o):
        tens_at[(g["id"], t)] = tens(g["season"], t) if n[(g["season"], t)] >= 5 else None
        lst = (bx.get(g["id"]) or {}).get(str(t))
        if lst:
            for pid, m, p, _ in lst:
                pts[(g["season"], t)][pid] += p
                gp[(g["season"], t)][pid] += 1
            n[(g["season"], t)] += 1
    share = rank_walk(allf, value, update, 100)
    rk = {k: {"pct": v[1], "v": v[0], "tens": tens_at.get(k)} for k, v in share.items()}
    if ret:
        return fin, rk
    O = h.Out("s8_ncaab_one_man_team", BT, BH)
    O.p("S8 - COLLEGE HOOPS: THE ONE-MAN TEAM (the top scorer's share of the team's points, season to date, 5+ boxed games,")
    O.p("  ranked in the league that night; the men at 10+ a game; the player box 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        if me["pct"] >= 0.8:
            t.append("ONE-MAN team (top fifth share)")
            t.append("ONE-MAN team, " + ("neutral" if g["neutral"] else "home" if side == "home" else "road"))
            if th["pct"] <= 0.2:
                t.append("ONE-MAN team vs a balanced team")
        if me["pct"] >= 0.9:
            t.append("ONE-MAN team (top tenth share)")
        if me["pct"] <= 0.2:
            t.append("BALANCED team (bottom fifth share)")
            t.append("BALANCED team, " + ("neutral" if g["neutral"] else "home" if side == "home" else "road"))
            if th["pct"] >= 0.8:
                t.append("BALANCED team vs a one-man team")
        if me["tens"] is not None:
            if me["tens"] >= 4:
                t.append("FOUR+ men at 10 a game")
            if me["tens"] <= 1:
                t.append("ONE man or none at 10 a game")
        return t
    cells(O, fin, rk, flags)


def s9(ret=False):
    lg = "ncaab"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2018]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2018]
    G = sd.load_games(lg)
    sums = defaultdict(lambda: [0.0, 0.0, 0])            # (season, team) -> [1st-half margin, 2nd-half margin, games]

    def value(s, t):
        a = sums[(s, t)]
        if a[2] < 5:
            return None
        return (a[1] - a[0]) / a[2]

    def update(g, t, o):
        gg = G.get(g["id"]) or {}
        hq, aq = lib.quarters(gg.get("ls_home")), lib.quarters(gg.get("ls_away"))
        if not hq or not aq or len(hq) < 2 or len(aq) < 2:
            return
        sign = 1 if g["home"] == t else -1
        m1 = max(-20, min(20, (hq[0] - aq[0]) * sign))
        m2 = max(-20, min(20, (hq[1] - aq[1]) * sign))
        a = sums[(g["season"], t)]
        a[0] += m1
        a[1] += m2
        a[2] += 1
    rk0 = rank_walk(allf, value, update, 100)
    full = {}
    for k, v in rk0.items():
        full[k] = v
    if ret:
        return fin, full
    O = h.Out("s9_ncaab_second_half_team", LT, LH)
    O.p("S9 - COLLEGE HOOPS: THE SECOND-HALF TEAM (second-half margin minus first-half margin a game, each half capped at 20,")
    O.p("  season to date, 5+ games, ranked in the league that night; the line scores 2018-26, train 2018-21 / held 2022-26)")

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        if me[1] >= 0.8:
            t.append("SECOND-HALF team (top fifth)")
            t.append("SECOND-HALF team, " + ("neutral" if g["neutral"] else "home" if side == "home" else "road"))
            if th[1] <= 0.2:
                t.append("SECOND-HALF team vs a first-half team")
        if me[1] >= 0.9:
            t.append("SECOND-HALF team (top tenth)")
        if me[1] <= 0.2:
            t.append("FIRST-HALF team (bottom fifth - fades after the break)")
            t.append("FIRST-HALF team, " + ("neutral" if g["neutral"] else "home" if side == "home" else "road"))
            if th[1] >= 0.8:
                t.append("FIRST-HALF team vs a second-half team")
        if me[1] <= 0.1:
            t.append("FIRST-HALF team (bottom tenth)")
        return t
    cells(O, fin, full, flags, totals=[
        ("both second-half teams (top two fifths)", lambda a, b: bool(a and b and a[1] >= 0.6 and b[1] >= 0.6)),
        ("both first-half teams (bottom two fifths)", lambda a, b: bool(a and b and a[1] <= 0.4 and b[1] <= 0.4))])


def s10(lg, ret=False):
    y0 = 2021 if lg == "ncaab" else 2018
    tr, he = (BT, BH) if lg == "ncaab" else (LT, LH)
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= y0]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= y0]
    bx = hoop_box(lg)
    gm = defaultdict(lambda: [0.0, 0.0, 0])              # guard minutes, all minutes, games

    def value(s, t):
        a = gm[(s, t)]
        if a[2] < 5 or a[1] <= 0:
            return None
        return a[0] / a[1]

    def update(g, t, o):
        lst = (bx.get(g["id"]) or {}).get(str(t))
        if lst:
            a = gm[(g["season"], t)]
            a[0] += sum(m for _, m, _, gd in lst if gd)
            a[1] += sum(m for _, m, _, _ in lst)
            a[2] += 1
    rk = rank_walk(allf, value, update, 100 if lg == "ncaab" else 20)
    if ret:
        return fin, rk
    O = h.Out(f"s10_{lg}_guard_heavy", tr, he)
    O.p(f"S10 - {lg.upper()}: THE GUARD-HEAVY TEAM (the share of a team's minutes its guards play - the box's position column,")
    O.p(f"  season to date, 5+ boxed games, ranked in the league that night; train {tr[0]}-{tr[1]} / held {he[0]}-{he[-1]})")

    def flags(me, th, side, g):
        t = []
        if not me or not th:
            return t
        where = "neutral" if g["neutral"] else "home" if side == "home" else "road"
        if me[1] >= 0.8:
            t.append("GUARD-HEAVY team (top fifth)")
            t.append("GUARD-HEAVY team, " + where)
            if th[1] <= 0.2:
                t.append("GUARD-HEAVY team vs a BIG team")
        if me[1] <= 0.2:
            t.append("BIG team (bottom fifth guard minutes)")
            t.append("BIG team, " + where)
            if th[1] >= 0.8:
                t.append("BIG team vs a guard-heavy team")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both guard-heavy (top two fifths)", lambda a, b: bool(a and b and a[1] >= 0.6 and b[1] >= 0.6)),
        ("both big (bottom two fifths)", lambda a, b: bool(a and b and a[1] <= 0.4 and b[1] <= 0.4))])


if __name__ == "__main__":
    RUN = {"s1": lambda: party("nba"), "s2": lambda: party("nhl"), "s3nfl": lambda: cold("nfl"), "s3ncaaf": lambda: cold("ncaaf"),
           "s4nfl": lambda: s4("nfl"), "s4ncaaf": lambda: s4("ncaaf"), "s5nfl": lambda: s5("nfl"), "s5ncaaf": lambda: s5("ncaaf"),
           "s6": s6, "s7nfl": lambda: s7("nfl"), "s7ncaaf": lambda: s7("ncaaf"), "s8": s8, "s9": s9,
           "s10ncaab": lambda: s10("ncaab"), "s10nba": lambda: s10("nba")}
    for a in sys.argv[1:] or list(RUN):
        RUN[a]()
