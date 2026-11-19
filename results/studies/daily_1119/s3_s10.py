"""11/19 daily studies S3-S10 (the eight of our own choice; S1 / S2 are the two asked). Each checked against
SPORTS_FINDINGS first - none of these was run before:
 S3  NFL the playing surface and the roof (a grass team on turf, a turf team on grass, a dome team outdoors) - nflverse
     2006-26 closes (sports_context: "the data has no turf / grass field, so that one isn't studied")
 S4  NFL the defense's snap load last game (nflverse snap counts 2015-26)
 S5  NFL the quarterback's career starts (nflverse starters 1999-26, closes 2006-26)
 S6  football: the team the market moved AGAINST week after week (the paid history, first fair -> the last look)
 S7  NHL scoring depth - the share of a team's goals from its top 3 scorers (box scores 2021-26)
 S8  the week the clocks change, every league (fall and spring)
 S9  wire to wire - the team that led (trailed) at every break of its last game (line scores)
 S10 hoops scoring concentration - the share of a team's points from its top 2 scorers (NBA 2016-26, college 2021-26)
usage: python s3_s10.py s3 s4 ... (no args = all)."""
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
import lib
import nflv

ALL_HELD = lambda lo, hi: tuple(range(lo, hi + 1))   # noqa: E731


def band_cells(o, name, s, pr, odds):
    """name + ' dog' (+100..+350) / ' fav' (-150..-101) by the price."""
    b = h.band(odds)
    if b:
        o.add(f"{name} | {b}", s, pr, odds)


# ------------------------------------------------------------------ S3
def s3():
    G = nflv.games()
    o = h.Out("s3_nfl_surface", (2006, 2016), ALL_HELD(2017, 2026))
    o.p("S3 - NFL: THE PLAYING SURFACE AND THE ROOF (nflverse 2006-26, the close). A team's surface / roof = the one most of its"
        " home games that season were played on. Road sides only (the home team is on its own).")

    def kind(g):
        s_ = g["surface"].lower()
        return None if not s_ else "grass" if "grass" in s_ else "turf"

    def roof(g):
        return None if not g["roof"] else "in" if g["roof"] in ("dome", "closed") else "out"
    hs, hr = defaultdict(Counter), defaultdict(Counter)
    for g in G:
        if not g["neutral"]:
            if kind(g):
                hs[(g["home"], g["season"])][kind(g)] += 1
            if roof(g):
                hr[(g["home"], g["season"])][roof(g)] += 1
    hs = {k: c.most_common(1)[0][0] for k, c in hs.items()}
    hr = {k: c.most_common(1)[0][0] for k, c in hr.items()}
    for g in G:
        if g["neutral"] or g["hs"] == g["as"]:
            continue
        s = g["season"]
        mine, here = hs.get((g["away"], s)), kind(g)
        rm, rh = hr.get((g["away"], s)), roof(g)
        pr, at, od = nflv.ml_profit(g, "away"), nflv.ats_profit(g, "away"), g["mla"]
        band_cells(o, "A0 every road side", s, pr, od)
        o.add("A0 every road side | ATS", s, at)
        if mine and here:
            nm = "A1 grass team on turf" if (mine, here) == ("grass", "turf") else "A2 turf team on grass" if (mine, here) == ("turf", "grass") \
                else "A3 same surface as home"
            band_cells(o, nm, s, pr, od)
            o.add(nm + " | ATS", s, at)
            if nm[:2] in ("A1", "A2") and g["day"].month in (11, 12, 1):
                band_cells(o, nm + ", Nov on", s, pr, od)
                o.add(nm + ", Nov on | ATS", s, at)
        if rm and rh:
            nm = "B1 dome team outdoors" if (rm, rh) == ("in", "out") else "B2 outdoor team under a roof" if (rm, rh) == ("out", "in") else "B3 same roof as home"
            band_cells(o, nm, s, pr, od)
            o.add(nm + " | ATS", s, at)
            if nm[:2] == "B1" and here:
                band_cells(o, f"B1 dome team outdoors, on {here}", s, pr, od)
        # the over / under on a surface switch
        if mine and here and mine != here:
            o.add("C surface switch | over", s, nflv.tot_profit(g, True))
            o.add("C surface switch | under", s, nflv.tot_profit(g, False))
    o.show()
    for a, b in (("A1 grass team on turf | dog", "A0 every road side | dog"), ("A2 turf team on grass | dog", "A0 every road side | dog"),
                 ("A1 grass team on turf | ATS", "A0 every road side | ATS"), ("A2 turf team on grass | ATS", "A0 every road side | ATS"),
                 ("B1 dome team outdoors | dog", "A0 every road side | dog"), ("B2 outdoor team under a roof | dog", "A0 every road side | dog")):
        o.placebo(a, b)
        o.placebo(a, b, fade=True)
    o.save()


# ------------------------------------------------------------------ S4
def s4():
    o = h.Out("s4_nfl_defense_snaps", (2015, 2020), ALL_HELD(2021, 2026))
    o.p("S4 - NFL: THE DEFENSE'S SNAP LOAD LAST GAME (nflverse snap counts 2015-26: a team's defensive snaps = the most any of"
        " its defenders played; the offense the same). This game's side at the close.")
    snaps = {}
    for y in range(2015, 2027):
        p = os.path.join(nflv.DL, f"snap_counts_{y}.csv")
        if not os.path.exists(p):
            continue
        with open(p) as f:
            for r in csv.DictReader(f):
                k = (r["game_id"], r["team"])
                d = snaps.setdefault(k, [0, 0])
                try:
                    d[0] = max(d[0], int(float(r["defense_snaps"] or 0)))
                    d[1] = max(d[1], int(float(r["offense_snaps"] or 0)))
                except ValueError:
                    pass
    G = nflv.games(2015, 2026)
    last = {}
    dist = []
    for g in G:
        for side, tm, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            pv = last.get((tm, g["season"]))
            if pv and (g["day"] - pv[0]).days <= 15 and g["hs"] != g["as"]:
                dsn, osn = pv[1], pv[2]
                days = (g["day"] - pv[0]).days
                s, od = g["season"], g["mlh"] if side == "home" else g["mla"]
                pr, at = nflv.ml_profit(g, side), nflv.ats_profit(g, side)
                dist.append(dsn)
                nm = "D 78+ snaps" if dsn >= 78 else "D 72-77" if dsn >= 72 else "D 58-71" if dsn >= 58 else "D under 58 (fresh)"
                band_cells(o, f"A {nm}", s, pr, od)
                o.add(f"A {nm} | ATS", s, at)
                band_cells(o, "A0 every side", s, pr, od)
                o.add("A0 every side | ATS", s, at)
                if dsn >= 75 and days <= 6:
                    band_cells(o, "B D 75+ snaps, 6 days or fewer since", s, pr, od)
                    o.add("B D 75+ snaps, 6 days or fewer since | ATS", s, at)
                if dsn - osn >= 15:
                    band_cells(o, "C D out there 15+ snaps more than the offense", s, pr, od)
                    o.add("C D out there 15+ snaps more than the offense | ATS", s, at)
                if osn - dsn >= 15:
                    band_cells(o, "C offense 15+ snaps more than the D (owned the ball)", s, pr, od)
                    o.add("C offense 15+ snaps more than the D (owned the ball) | ATS", s, at)
                opv = last.get((opp, g["season"]))
                if opv and (g["day"] - opv[0]).days <= 15 and opv[1] >= 75 and dsn < 65:
                    band_cells(o, "E fresh D (under 65) vs a team whose D played 75+", s, pr, od)
                    o.add("E fresh D (under 65) vs a team whose D played 75+ | ATS", s, at)
                if dsn >= 75:
                    o.add("F D 75+ last game | over", s, nflv.tot_profit(g, True))
        for tm in (g["home"], g["away"]):
            sn = snaps.get((g["id"], tm))
            if sn and sn[0]:
                last[(tm, g["season"])] = (g["day"], sn[0], sn[1])
    dist.sort()
    o.p(f"team-games with last game's snaps: {len(dist)}; defensive snaps 10th / 50th / 90th pct: "
        f"{dist[len(dist) // 10]} / {dist[len(dist) // 2]} / {dist[len(dist) * 9 // 10]}")
    o.show()
    for a, b in (("A D 78+ snaps | dog", "A0 every side | dog"), ("A D 78+ snaps | ATS", "A0 every side | ATS"),
                 ("B D 75+ snaps, 6 days or fewer since | ATS", "A0 every side | ATS"),
                 ("C D out there 15+ snaps more than the offense | ATS", "A0 every side | ATS"),
                 ("E fresh D (under 65) vs a team whose D played 75+ | ATS", "A0 every side | ATS")):
        o.placebo(a, b)
        o.placebo(a, b, fade=True)
    o.save()


# ------------------------------------------------------------------ S5
def s5():
    o = h.Out("s5_nfl_qb_starts", (2006, 2016), ALL_HELD(2017, 2026))
    o.p("S5 - NFL: THE QUARTERBACK'S CAREER STARTS (nflverse's starters 1999-26, regular season + playoffs; a QB already"
        " starting in 1999 reads short until 2006 - the closes start there). The side at the close.")
    starts = Counter()
    rows = []
    with open(os.path.join(nflv.DL, "games.csv")) as f:
        for r in csv.DictReader(f):
            if r["home_score"] in ("", "NA"):
                continue
            rows.append(r)
    rows.sort(key=lambda r: (r["gameday"], r["game_id"]))
    exp = {}
    for r in rows:
        exp[r["game_id"]] = (starts[r["home_qb_id"]] if r["home_qb_id"] else None, starts[r["away_qb_id"]] if r["away_qb_id"] else None)
        for k in ("home_qb_id", "away_qb_id"):
            if r[k]:
                starts[r[k]] += 1

    def bk(n):
        return "under 8 starts" if n < 8 else "8-31" if n < 32 else "32-99" if n < 100 else "100+"
    for g in nflv.games():
        if g["hs"] == g["as"]:
            continue
        eh, ea = exp.get(g["id"], (None, None))
        if eh is None or ea is None:
            continue
        for side, mine, his, od in (("home", eh, ea, g["mlh"]), ("away", ea, eh, g["mla"])):
            s, pr, at = g["season"], nflv.ml_profit(g, side), nflv.ats_profit(g, side)
            band_cells(o, "A0 every side", s, pr, od)
            o.add("A0 every side | ATS", s, at)
            band_cells(o, f"A QB {bk(mine)}", s, pr, od)
            o.add(f"A QB {bk(mine)} | ATS", s, at)
            if mine == 0:
                band_cells(o, "B his FIRST career start", s, pr, od)
                o.add("B his FIRST career start | ATS", s, at)
            if 1 <= mine <= 3:
                band_cells(o, "B starts 2-4", s, pr, od)
                o.add("B starts 2-4 | ATS", s, at)
            if mine < 8 and his >= 100:
                band_cells(o, "C new QB (under 8) vs a 100+ start veteran", s, pr, od)
                o.add("C new QB (under 8) vs a 100+ start veteran | ATS", s, at)
            if mine >= 100 and his < 8:
                band_cells(o, "C 100+ veteran vs a new QB", s, pr, od)
                o.add("C 100+ veteran vs a new QB | ATS", s, at)
            if mine >= 100 and his >= 100:
                band_cells(o, "C two 100+ veterans", s, pr, od)
            if mine < 32 and side == "away":
                band_cells(o, "D under 32 starts, on the road", s, pr, od)
            if mine < 32 and g["et"] is not None and g["et"] >= 19:
                band_cells(o, "D under 32 starts, at night", s, pr, od)
    o.show()
    for a, b in (("A QB under 8 starts | dog", "A0 every side | dog"), ("A QB 100+ | dog", "A0 every side | dog"),
                 ("B his FIRST career start | ATS", "A0 every side | ATS"), ("C new QB (under 8) vs a 100+ start veteran | dog", "A0 every side | dog"),
                 ("A QB 100+ | fav", "A0 every side | fav"), ("A QB 8-31 | dog", "A0 every side | dog")):
        o.placebo(a, b)
        o.placebo(a, b, fade=True)
    o.save()


# ------------------------------------------------------------------ S6
def s6():
    for lg in ("nfl", "ncaaf"):
        o = h.Out(f"s6_repeat_moves_{lg}", (2020, 2022), (2023, 2024, 2025, 2026))
        o.p(f"S6 - {lg}: THE TEAM THE MARKET MOVED AGAINST WEEK AFTER WEEK (the paid odds history; a game's move = the median"
            " book's no-vig win chance at the last look minus the first FAIR look, 1.5+ points = a move). This week's side at the"
            " FIRST FAIR number (median book) and at the close.")
        X = lib.load_football(lg)
        hist = defaultdict(list)                 # (team, season) -> [(start, move toward the team, won)]
        for x in X:
            ff, ll = lib.first_fair(x["ml"]), lib.last_look(x["ml"])
            for side, tm in (("home", x["home"]), ("away", x["away"])):
                prev = hist[(tm, x["season"])]
                if len(prev) >= 2 and ff:
                    dprice, _ = lib.side_ml(x, side, ff[1])
                    od = lib.american(dprice)
                    won = (x["margin"] > 0) == (side == "home")
                    if x["margin"] != 0:
                        pr = lib.profit(won, dprice)
                        co = x["c_mlh"] if side == "home" else x["c_mla"]
                        pc = lib.profit(won, lib.dec(co)) if co else None
                        m2 = [m for _, m, _ in prev[-2:]]
                        m3 = [m for _, m, _ in prev[-3:]]
                        w2 = [w for _, _, w in prev[-2:]]
                        tags = ["A0 every side with 2+ games of moves"]
                        if all(m <= -0.015 for m in m2):
                            tags.append("A1 moved AGAINST in its last 2")
                            if not any(w2):
                                tags.append("A1b  ...and lost both")
                            if all(w2):
                                tags.append("A1c  ...and won both (the market was wrong twice)")
                        if len(m3) == 3 and all(m <= -0.015 for m in m3):
                            tags.append("A2 moved AGAINST in its last 3")
                        if all(m >= 0.015 for m in m2):
                            tags.append("B1 moved TO in its last 2")
                            if all(w2):
                                tags.append("B1b  ...and won both")
                            if not any(w2):
                                tags.append("B1c  ...and lost both (the market was wrong twice)")
                        if len(m3) == 3 and all(m >= 0.015 for m in m3):
                            tags.append("B2 moved TO in its last 3")
                        if sum(m2) <= -0.06:
                            tags.append("C1 6+ points against over its last 2")
                        if sum(m2) >= 0.06:
                            tags.append("C2 6+ points to it over its last 2")
                        for t in tags:
                            band_cells(o, t + " @first fair", x["season"], pr, od)
                            if co:
                                band_cells(o, t + " @close", x["season"], pc, co)
                if ff and ll and x["margin"] != 0:
                    p0, p1 = lib.ml_med(ff[1])[2], lib.ml_med(ll[1])[2]
                    mv = (p1 - p0) if side == "home" else (p0 - p1)
                    prev.append((x["start"], mv, (x["margin"] > 0) == (side == "home")))
        o.show()
        for a in ("A1 moved AGAINST in its last 2", "A2 moved AGAINST in its last 3", "B1 moved TO in its last 2", "B2 moved TO in its last 3",
                  "C1 6+ points against over its last 2", "C2 6+ points to it over its last 2"):
            for b in ("dog", "fav"):
                o.placebo(f"{a} @first fair | {b}", f"A0 every side with 2+ games of moves @first fair | {b}")
                o.placebo(f"{a} @first fair | {b}", f"A0 every side with 2+ games of moves @first fair | {b}", fade=True)
        o.save()


# ------------------------------------------------------------------ S7 / S10 (scoring shares off the box scores)
def _share_study(lg, stat, top_n, tag, title, train, held, min_games, groups=None, morning=None):
    o = h.Out(tag, train, held)
    o.p(title)

    def val(st, r):
        if groups and r["group"] not in groups:
            return None
        try:
            return int(float(st.get(stat) or 0))
        except ValueError:
            return None
    val.__name__ = f"val_{stat}_{'_'.join(groups) if groups else 'all'}"
    bx = lib.boxes(lg, val)
    fin = lib.finals(lg)
    tot = defaultdict(Counter)                    # (team, season) -> {pid: stat}
    n = Counter()
    rows = []
    for g in fin:
        if g["stype"] != "2":
            continue
        s = g["season"]
        sh = {}
        for side, tm in (("home", g["home"]), ("away", g["away"])):
            c = tot[(tm, s)]
            t = sum(c.values())
            if n[(tm, s)] >= min_games and t > 0:
                sh[side] = sum(v for _, v in c.most_common(top_n)) / t
        if len(sh) == 2:
            rows.append((g, sh))
        b = bx.get(g["id"].split(":")[-1]) or bx.get(g["id"]) or {}
        for tm in (g["home"], g["away"]):
            pl = b.get(tm) or b.get(str(tm))
            if pl:
                for pid, v in pl.items():
                    tot[(tm, s)][pid] += v
                n[(tm, s)] += 1
    tr = sorted(x for g, sh in rows if train[0] <= g["season"] <= train[1] for x in sh.values())
    if not tr:
        o.p("no rows")
        o.save()
        return
    q20, q80 = tr[len(tr) // 5], tr[len(tr) * 4 // 5]
    o.p(f"games with both shares {len(rows)}; the share's 20th / 80th pct on the train seasons: {q20:.3f} / {q80:.3f}")
    for g, sh in rows:
        for side, tm, opp, od, won, is_home in lib.sides(g):
            other = "away" if side == "home" else "home"
            mine, his = sh[side], sh[other]
            pr, at = lib.profit(won, lib.dec(od)), lib.ats(g, side)
            s = g["season"]
            band_cells(o, "A0 every side", s, pr, od)
            o.add("A0 every side | ATS", s, at)
            nm = "A1 TOP-HEAVY (top fifth)" if mine >= q80 else "A2 DEEP (bottom fifth)" if mine <= q20 else "A3 the middle"
            band_cells(o, nm, s, pr, od)
            o.add(nm + " | ATS", s, at)
            if mine >= q80 and his <= q20:
                band_cells(o, "B1 top-heavy vs deep", s, pr, od)
                o.add("B1 top-heavy vs deep | ATS", s, at)
            if mine <= q20 and his >= q80:
                band_cells(o, "B2 deep vs top-heavy", s, pr, od)
                o.add("B2 deep vs top-heavy | ATS", s, at)
            if nm[:2] in ("A1", "A2"):
                band_cells(o, nm + (", home" if is_home else ", road"), s, pr, od)
            if morning is not None:
                ms = lib.morning_side(morning, g["id"], side)
                if ms and nm[:2] in ("A1", "A2"):
                    band_cells(o, nm + " @paid morning", s, lib.profit(won, ms[1]), ms[0])
    o.show()
    for a in ("A1 TOP-HEAVY (top fifth)", "A2 DEEP (bottom fifth)", "B1 top-heavy vs deep", "B2 deep vs top-heavy"):
        for b in ("dog", "fav", "ATS"):
            o.placebo(f"{a} | {b}", f"A0 every side | {b}")
            o.placebo(f"{a} | {b}", f"A0 every side | {b}", fade=True)
    o.save()


def s7():
    _share_study("nhl", "goals", 3, "s7_nhl_scoring_depth",
                 "S7 - NHL: SCORING DEPTH (the share of a team's goals this season from its top 3 goal scorers, 10+ boxed games; "
                 "box scores 2021-26; the close, the paid morning 2021-23 as the second price)",
                 (2021, 2023), (2024, 2025, 2026), 10, groups=("forwards", "defenses"), morning=lib.nhl_morning())


def s10():
    _share_study("nba", "points", 2, "s10_nba_concentration",
                 "S10a - NBA: SCORING CONCENTRATION (the share of a team's points this season from its top 2 scorers, 10+ boxed "
                 "games; box scores 2016-26; the close, the paid morning 2020-23 as the second price)",
                 (2016, 2021), (2022, 2023, 2024, 2025, 2026), 10, morning=lib.nba_morning())
    _share_study("ncaab", "points", 2, "s10_ncaab_concentration",
                 "S10b - COLLEGE HOOPS: SCORING CONCENTRATION (the share of a team's points this season from its top 2 scorers, "
                 "5+ boxed games; box scores 2021-26; the close)",
                 (2021, 2023), (2024, 2025, 2026), 5)


# ------------------------------------------------------------------ S8
def s8():
    o = h.Out("s8_clock_change_week", (2016, 2021), ALL_HELD(2022, 2026))
    o.p("S8 - THE WEEK THE CLOCKS CHANGE, every league (the 7 days from the Sunday of the change; CONTROL = the 7 days before"
        " + the 7 days after that week). The close. 'season' = the league season.")

    def sunday(y, m, n):
        d = date(y, m, 1)
        first = 1 + (6 - d.weekday()) % 7
        return date(y, m, first + 7 * (n - 1))
    weeks = {}
    for y in range(2016, 2028):
        weeks[("fall", y)] = sunday(y, 11, 1)
        weeks[("spring", y)] = sunday(y, 3, 2)
    for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
        for g in lib.finals(lg):
            if g["stype"] != "2" or g["neutral"]:
                continue
            t = lib._t(g["start"]) - timedelta(hours=10)          # the US calendar day
            d = t.date()
            for (kind, y), w0 in weeks.items():
                diff = (d - w0).days
                if -7 <= diff < 14:
                    where = "WEEK" if 0 <= diff < 7 else "control"
                    s = g["season"]
                    for side, tm, opp, od, won, is_home in lib.sides(g):
                        pr = lib.profit(won, lib.dec(od))
                        nm = f"{lg} {kind} {where}: {'home' if is_home else 'road'}"
                        band_cells(o, nm, s, pr, od)
                        o.add(nm + " | ATS", s, lib.ats(g, side))
                    o.add(f"{lg} {kind} {where}: over", s, lib.tot_profit(g, True))
                    o.add(f"{lg} {kind} {where}: under", s, lib.tot_profit(g, False))
                    # the body clock: fall back = everything starts an hour "later" for the body; a night game in the West
                    if g["tzo"] is not None and kind == "fall" and where == "WEEK" and lg in ("nba", "nhl"):
                        loc = (lib._t(g["start"]) + timedelta(hours=g["tzo"])).hour
                        if loc >= 19:
                            o.add(f"{lg} fall WEEK: night game (7 PM local+) | under", s, lib.tot_profit(g, False))
    o.show()
    for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
        for kind in ("fall", "spring"):
            for cell in ("road | dog", "home | dog", "road | ATS"):
                a, b = f"{lg} {kind} WEEK: {cell}", f"{lg} {kind} control: {cell}"
                if a in o.c and b in o.c:
                    o.placebo(a, b)
                    o.placebo(a, b, fade=True)
            for cell in ("over", "under"):
                a, b = f"{lg} {kind} WEEK: {cell}", f"{lg} {kind} control: {cell}"
                if a in o.c and b in o.c:
                    o.placebo(a, b)
    o.save()


# ------------------------------------------------------------------ S9
def s9():
    for lg, train, held in (("nba", (2016, 2021), ALL_HELD(2022, 2026)), ("nhl", (2016, 2021), ALL_HELD(2022, 2026)),
                            ("nfl", (2018, 2021), ALL_HELD(2022, 2026)), ("ncaaf", (2018, 2021), ALL_HELD(2022, 2026))):
        o = h.Out(f"s9_wire_to_wire_{lg}", train, held)
        o.p(f"S9 - {lg}: WIRE TO WIRE (line scores: the team LED at every break of its last game and won / TRAILED at every"
            " break and lost; the next game inside 10 days, this season; the close)")
        fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
        last = {}
        for g in fin:
            for side, tm, opp, od, won, is_home in lib.sides(g):
                pv = last.get((tm, g["season"]))
                if pv and lib.days_between(pv[0], g["start"]) <= 10:
                    pr, at, s = lib.profit(won, lib.dec(od)), lib.ats(g, side), g["season"]
                    band_cells(o, "A0 every side with a last game", s, pr, od)
                    o.add("A0 every side with a last game | ATS", s, at)
                    if pv[1]:
                        band_cells(o, f"A {pv[1]}", s, pr, od)
                        o.add(f"A {pv[1]} | ATS", s, at)
                        opv = last.get((opp, g["season"]))
                        if opv and lib.days_between(opv[0], g["start"]) <= 10 and opv[1] and opv[1] != pv[1]:
                            band_cells(o, f"B {pv[1]} vs a team off the opposite", s, pr, od)
                            o.add(f"B {pv[1]} vs a team off the opposite | ATS", s, at)
            qh, qa = lib.quarters(g["ls_h"]), lib.quarters(g["ls_a"])
            n_reg = 3 if lg == "nhl" else 4
            st = {g["home"]: None, g["away"]: None}
            if qh and qa and len(qh) >= n_reg and len(qa) >= n_reg:
                ch = ca = 0
                lead = []
                for i in range(n_reg - 1):
                    ch += qh[i]
                    ca += qa[i]
                    lead.append(ch - ca)
                hw = g["hs"] > g["as"]
                if all(x > 0 for x in lead) and hw:
                    st[g["home"]], st[g["away"]] = "WIRE-TO-WIRE WIN", "never led at a break, lost"
                elif all(x < 0 for x in lead) and not hw:
                    st[g["away"]], st[g["home"]] = "WIRE-TO-WIRE WIN", "never led at a break, lost"
            for tm in (g["home"], g["away"]):
                last[(tm, g["season"])] = (g["start"], st[tm])
        o.show()
        for a in ("A WIRE-TO-WIRE WIN", "A never led at a break, lost"):
            for b in ("dog", "fav", "ATS"):
                o.placebo(f"{a} | {b}", f"A0 every side with a last game | {b}")
                o.placebo(f"{a} | {b}", f"A0 every side with a last game | {b}", fade=True)
        o.save()


if __name__ == "__main__":
    todo = sys.argv[1:] or ["s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"]
    for k in todo:
        globals()[k]()
