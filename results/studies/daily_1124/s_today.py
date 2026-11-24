"""11/24 daily studies S1-S10 - ten questions SPORTS_FINDINGS.md has never answered (checked first: no study on a pro
team's HOME / ROAD SPLIT, the pros' margin SWING, a pro team's record against WINNING teams, the NFL sack rate off the
team box, NFL defensive touchdowns, the NBA second quarter, the NHL second period, a college hoops team's DEPTH on the
second day of an event, football's fourth quarter). The Thanksgiving / rivalry-week / early-tournament questions the
brief named were answered before (short weeks 11/12 b1, the holidays 10/31, rivalry week 10/31 + 11/21, the bowl
chase, senior day, MTE stakes and the consolation game 11/1 + 11/21, neutral floors 11/3 - 11/21) - not re-run.
What a team did THIS season before tonight (no look-ahead), every read LEAGUE-RELATIVE (the top / bottom fifth of the
league's current values that night), ESPN's close at its own juice, regular season. Cells fixed before the run.
  S1  NBA: THE HOME / ROAD SPLIT - home margin minus road margin a game, season to date (6+ each)
  S2  NHL: THE HOME / ROAD SPLIT
  S3  NBA + NHL: THE SWING TEAM - how far its margins swing game to game (the spread of its last 15 margins)
  S4  NBA + NHL: THE RECORD AGAINST WINNING TEAMS - win % vs losing teams minus win % vs winning teams (5+ each)
  S5  NFL: THE SACK RATE (the team box's sacksYardsLost over drop-backs) - the line that gives them up, the rush
      that gets them, and the two against each other
  S6  NFL: DEFENSIVE TOUCHDOWNS - the points that don't repeat (the team box's defensiveTouchdowns, last 3 games)
  S7  NBA: THE SECOND QUARTER (the bench quarter) - last 10 (11/20 read the 4th, 11/23 the 3rd)
  S8  NHL: THE SECOND PERIOD (the long change) - last 15 (11/9 the first, 11/20 the third)
  S9  COLLEGE HOOPS: DEPTH ON THE SECOND DAY - the share of a team's minutes its top 5 play, on a game the day after
      a game (the events' back-to-backs; the 10/23 depth read was the NBA's)
  S10 FOOTBALL (NFL + college): THE FOURTH QUARTER - season to date
python results/studies/daily_1124/s_today.py [nba nhl s5 s7 s8 s9 s10nfl s10ncaaf]"""
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
from core import teambox, ranked, cells, hi, lo, BT, BH, LT, LH  # noqa: E402


# ------------------------------------------------------------------ S1-S4 the pros: split / swing / who they beat
def pro(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2018]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2018 and g["stype"] == "2"]
    rec = defaultdict(lambda: [0, 0])                    # (season, team) -> [won, lost] before the game
    recb = {}
    for g in allf:
        for t in (g["home"], g["away"]):
            recb[(g["id"], t)] = tuple(rec[(g["season"], t)])
        hw = g["hs"] > g["as"]
        rec[(g["season"], g["home"])][0 if hw else 1] += 1
        rec[(g["season"], g["away"])][1 if hw else 0] += 1

    def counters(g, t, o):
        home = g["home"] == t
        m = (g["hs"] - g["as"]) * (1 if home else -1)
        if lg == "nhl":                                  # (an overtime / shootout game is a one-goal game either way)
            m = max(-6.0, min(6.0, m))
        else:
            m = max(-30.0, min(30.0, m))
        w, lo_ = recb[(g["id"], o)]
        good = 1.0 if (w + lo_ >= 8 and w > lo_) else 0.0
        bad = 1.0 if (w + lo_ >= 8 and w < lo_) else 0.0
        won = 1.0 if m > 0 else 0.0
        nb = g.get("neutral")
        return {"h_n": 0.0 if (not home or nb) else 1.0, "h_m": m if (home and not nb) else 0.0,
                "r_n": 0.0 if (home or nb) else 1.0, "r_m": m if (not home and not nb) else 0.0,
                "m": m, "g_n": good, "g_w": good * won, "b_n": bad, "b_w": bad * won}

    def feats(s, n):
        return {"split": (s["h_m"] / s["h_n"] - s["r_m"] / s["r_n"]) if s["h_n"] >= 6 and s["r_n"] >= 6 else 0.0,
                "split_ok": 1.0 if s["h_n"] >= 6 and s["r_n"] >= 6 else 0.0,
                "bully": (s["b_w"] / s["b_n"] - s["g_w"] / s["g_n"]) if s["g_n"] >= 5 and s["b_n"] >= 5 else 0.0,
                "bully_ok": 1.0 if s["g_n"] >= 5 and s["b_n"] >= 5 else 0.0,
                "all": s["m"] / n}
    rk = ranked(allf, counters, feats, 15)
    # the swing: the spread of the last 15 margins (walk-forward, ranked that night) - its own pass
    sw, hist, latest = {}, defaultdict(list), defaultdict(dict)
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            ms = hist[(s, t)][-15:]
            if len(ms) >= 15:
                mu = sum(ms) / 15
                cur[t] = math.sqrt(sum((x - mu) ** 2 for x in ms) / 15)
                latest[s][t] = cur[t]
        vals = latest[s]
        if len(vals) >= 20:
            for t, v in cur.items():
                sw[(g["id"], t)] = (v, sum(1 for x in vals.values() if x < v) / (len(vals) - 1))
        for t in (g["home"], g["away"]):
            m = (g["hs"] - g["as"]) * (1 if g["home"] == t else -1)
            hist[(s, t)].append(max(-6.0, min(6.0, m)) if lg == "nhl" else max(-30.0, min(30.0, m)))
    O = h.Out(f"s1_s4_{lg}", LT, LH)
    O.p(f"S1-S4 - {lg.upper()}: THE HOME / ROAD SPLIT, THE SWING TEAM, THE RECORD AGAINST WINNING TEAMS")
    O.p("  (scores 2018-26, season to date, 15+ games, league-relative fifths; train 2018-21 / held 2022-26)")

    def flags(me, th, side, g):
        t = []
        team = g["home"] if side == "home" else g["away"]
        opp = g["away"] if side == "home" else g["home"]
        if me["split_ok"][0] and not g.get("neutral"):
            where = "AT HOME" if side == "home" else "ON THE ROAD"
            if hi(me, "split"):
                t.append(f"S1 home-heavy team (top fifth home minus road margin) {where}")
                if th["split_ok"][0] and lo(th, "split") and side == "home":
                    t.append("S1 home-heavy team AT HOME vs a team that travels (bottom fifth split)")
                if me["all"][1] >= 0.5 and side == "away":
                    t.append("S1 home-heavy team ON THE ROAD, a winning margin overall (top half)")
            if lo(me, "split"):
                t.append(f"S1 travels-well team (bottom fifth home minus road margin) {where}")
                if th["split_ok"][0] and hi(th, "split") and side == "away":
                    t.append("S1 travels-well team ON THE ROAD at a home-heavy team")
        a, b = sw.get((g["id"], team)), sw.get((g["id"], opp))
        if a:
            if a[1] >= 0.8:
                t.append("S3 swing team (top fifth spread of its last 15 margins)")
                if b and b[1] <= 0.2:
                    t.append("S3 swing team vs a steady one (bottom fifth)")
            if a[1] <= 0.2:
                t.append("S3 steady team (bottom fifth spread of its last 15 margins)")
                if b and b[1] >= 0.8:
                    t.append("S3 steady team vs a swing team")
        if me["bully_ok"][0]:
            w, l_ = recb[(g["id"], opp)]
            good, bad = w + l_ >= 8 and w > l_, w + l_ >= 8 and w < l_
            if hi(me, "bully"):
                t.append("S4 beats the bad ones only (top fifth: win % vs losing teams minus vs winning teams)")
                if good:
                    t.append("S4 beats the bad ones only, vs a WINNING team tonight")
                if bad:
                    t.append("S4 beats the bad ones only, vs a LOSING team tonight")
            if lo(me, "bully"):
                t.append("S4 plays to its opponent (bottom fifth: as good against winning teams as losing ones)")
                if good:
                    t.append("S4 plays to its opponent, vs a WINNING team tonight")
                if bad:
                    t.append("S4 plays to its opponent, vs a LOSING team tonight")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S5 / S6 the NFL team box
def _pair(x):
    try:
        a, b = str(x).replace("/", "-").split("-")[:2]
        return float(a), float(b)
    except (ValueError, TypeError):
        return None


def s5():
    tb = teambox("nfl")
    fin = [g for g in lib.finals("nfl") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nfl") if g["season"] >= 2021 and g["stype"] == "2"]

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        sa, sb = _pair(a.get("sacksYardsLost")), _pair(b.get("sacksYardsLost"))
        ca, cb = _pair(a.get("completionAttempts")), _pair(b.get("completionAttempts"))
        if None in (sa, sb, ca, cb):
            return None
        return {"sk": sa[0], "db": ca[1] + sa[0], "o_sk": sb[0], "o_db": cb[1] + sb[0],
                "dtd": lib.num(a.get("defensiveTouchdowns")) or 0.0, "o_dtd": lib.num(b.get("defensiveTouchdowns")) or 0.0}

    def feats(s, n):
        if s["db"] < 60 or s["o_db"] < 60:
            return None
        return {"taken": s["sk"] / s["db"], "made": s["o_sk"] / s["o_db"], "net": s["o_sk"] / s["o_db"] - s["sk"] / s["db"]}
    rk = ranked(allf, counters, feats, 4, minteams=24)
    rk3 = ranked(allf, counters, lambda s, n: {"dtd": s["dtd"], "o_dtd": s["o_dtd"]}, 3, window=3, minteams=24)
    O = h.Out("s5_s6_nfl_sacks_def_td", BT, BH)
    O.p("S5 / S6 - NFL: THE SACK RATE (sacks over drop-backs, season to date, 4+ games) AND DEFENSIVE TOUCHDOWNS (last 3 games)")
    O.p("  (team box 2021-26, league-relative fifths; train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "taken"):
            t.append("S5 its QB gets sacked (top fifth sack rate taken)")
            if hi(th, "made"):
                t.append("S5 its QB gets sacked, vs a top fifth pass rush")
        if lo(me, "taken"):
            t.append("S5 keeps its QB clean (bottom fifth sack rate taken)")
        if hi(me, "made"):
            t.append("S5 top fifth pass rush (sack rate made)")
            if hi(th, "taken"):
                t.append("S5 top fifth pass rush vs a line that gives them up")
        if lo(me, "made"):
            t.append("S5 bottom fifth pass rush")
        if hi(me, "net"):
            t.append("S5 top fifth NET sack rate (made minus taken)")
            if lo(th, "net"):
                t.append("S5 top fifth net sack rate vs a bottom fifth one")
        if lo(me, "net"):
            t.append("S5 bottom fifth NET sack rate")
        x, y = rk3.get((g["id"], g["home"] if side == "home" else g["away"])), rk3.get((g["id"], g["away"] if side == "home" else g["home"]))
        if x:
            if x["dtd"][0] >= 2:
                t.append("S6 scored 2+ defensive touchdowns in its last 3 games")
            elif x["dtd"][0] >= 1:
                t.append("S6 scored 1 defensive touchdown in its last 3 games")
            else:
                t.append("S6 no defensive touchdown in its last 3 games")
            if x["o_dtd"][0] >= 2:
                t.append("S6 GAVE UP 2+ defensive touchdowns in its last 3 games")
            if y and x["dtd"][0] >= 1 and y["dtd"][0] == 0 and x["o_dtd"][0] == 0:
                t.append("S6 has a defensive touchdown lately, gave none, vs a team with none")
        return t

    def both(f):
        return lambda a, b: bool(a and b and f(a, b))
    cells(O, fin, rk, flags, totals=[
        ("S5 both lines give up sacks (both top two fifths taken)", both(lambda a, b: a["taken"][1] >= 0.6 and b["taken"][1] >= 0.6)),
        ("S5 both QBs kept clean (both bottom two fifths taken)", both(lambda a, b: a["taken"][1] <= 0.4 and b["taken"][1] <= 0.4)),
        ("S5 both top two fifths pass rush", both(lambda a, b: a["made"][1] >= 0.6 and b["made"][1] >= 0.6))])


# ------------------------------------------------------------------ S7 / S8 / S10 a stretch of the game
def stretch(lg, tag, idx, word, window, minn, train, held, since, nparts):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= since]

    def counters(g, t, o):
        a, b = lib.quarters(g.get("ls_h")), lib.quarters(g.get("ls_a"))
        if not a or not b or len(a) < nparts or len(b) < nparts:
            return None
        me, th = (a, b) if g["home"] == t else (b, a)
        reg = sum(me[:nparts]) - sum(th[:nparts])
        return {"q": me[idx] - th[idx], "rest": reg - (me[idx] - th[idx]), "all": reg}

    def feats(s, n):
        return {"q": s["q"] / n, "rest": s["rest"] / n, "all": s["all"] / n}
    rk = ranked(fin, counters, feats, minn, window=window)
    O = h.Out(tag, train, held)
    O.p(f"{tag.upper()} - {lg.upper()} {word.upper()} ({'last ' + str(window) if window else 'season to date'}, {minn}+ games; "
        f"league-relative fifths; train {train[0]}-{train[1]} / held {held[0]}-{held[-1]})")

    def flags(me, th, side, g):
        t = []
        if hi(me, "q"):
            t.append(f"TOP fifth {word} margin")
            if lo(th, "q"):
                t.append(f"TOP fifth {word} vs a BOTTOM fifth one")
            if me["rest"][1] < 0.5:
                t.append(f"TOP fifth {word}, the rest of the game under the league middle")
            if me["all"][1] < 0.5:
                t.append(f"TOP fifth {word} on a team outscored overall (bottom half by margin)")
        if lo(me, "q"):
            t.append(f"BOTTOM fifth {word} margin")
            if hi(th, "q"):
                t.append(f"BOTTOM fifth {word} vs a TOP fifth one")
            if me["all"][1] >= 0.5:
                t.append(f"BOTTOM fifth {word} on a team that wins overall (top half by margin)")
            if me["rest"][1] >= 0.5:
                t.append(f"BOTTOM fifth {word}, the rest of the game over the league middle")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S9 college hoops: depth on the second day
def s9():
    fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2021]
    bx = lib.box_rows("ncaab")
    mins = defaultdict(lambda: defaultdict(float))       # (season, team) -> pid -> minutes
    gms = defaultdict(int)
    prev = {}                                            # (season, team) -> the start of its last game
    read, latest = {}, defaultdict(dict)                 # (gid, team) -> (top-5 share, league pct, days since last)
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            key = (s, t)
            tot = mins[key]
            if gms[key] >= 4 and sum(tot.values()) > 0:
                top = sorted(tot.values(), reverse=True)[:5]
                cur[t] = sum(top) / sum(tot.values())
                latest[s][t] = cur[t]
        vals = latest[s]
        if len(vals) >= 100:
            srt = sorted(vals.values())
            for t, v in cur.items():
                import bisect
                d = lib.days_between(prev[(s, t)], g["start"]) if (s, t) in prev else 99.0
                read[(g["id"], t)] = (v, bisect.bisect_left(srt, v) / (len(srt) - 1), d)
        for t in (g["home"], g["away"]):
            rows = (bx.get(g["id"]) or {}).get(str(t)) or []
            got = False
            for r in rows:
                m = lib.num(r["st"].get("minutes"))
                if m:
                    mins[(s, t)][r["pid"]] += m
                    got = True
            if got:
                gms[(s, t)] += 1
            prev[(s, t)] = g["start"]
    O = h.Out("s9_ncaab_depth_second_day", BT, BH)
    O.p("S9 - COLLEGE HOOPS: DEPTH ON THE SECOND DAY (the share of a team's minutes its top 5 play, 4+ boxed games;")
    O.p("  a game within 1.3 days of its last one; the player box 2021-26; train 2021-23 / held 2024-26)")
    rk = read

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        b2b = me[2] <= 1.3
        t.append("BASE read (4+ boxed games)")
        if b2b:
            t.append("ANY team on the second day")
            if th and th[2] <= 1.3:
                t.append("ANY team on the second day, the other side too")
        if me[1] <= 0.2:
            t.append("DEEP team (bottom fifth top-5 share)")
            if b2b:
                t.append("DEEP team on the second day")
                if th and th[2] <= 1.3 and th[1] >= 0.8:
                    t.append("DEEP team on the second day vs a SHORT bench also on its second day")
                if th and th[2] <= 1.3 and th[1] >= 0.5:
                    t.append("DEEP team on the second day vs a top-half top-5 share also on its second day")
        if me[1] >= 0.8:
            t.append("SHORT bench (top fifth top-5 share)")
            if b2b:
                t.append("SHORT bench on the second day")
                if th and th[2] > 1.3:
                    t.append("SHORT bench on the second day vs a rested team")
        return t

    def both(f):
        return lambda a, b: bool(a and b and f(a, b))
    cells(O, fin, rk, flags, totals=[
        ("both on the second day", both(lambda a, b: a[2] <= 1.3 and b[2] <= 1.3)),
        ("both on the second day, both short benches (top two fifths)", both(lambda a, b: a[2] <= 1.3 and b[2] <= 1.3 and a[1] >= 0.6 and b[1] >= 0.6)),
        ("both on the second day, both deep (bottom two fifths)", both(lambda a, b: a[2] <= 1.3 and b[2] <= 1.3 and a[1] <= 0.4 and b[1] <= 0.4))],
        need_both=False)


if __name__ == "__main__":
    for a in sys.argv[1:] or ("nba", "nhl", "s5", "s7", "s8", "s9", "s10nfl", "s10ncaaf"):
        if a in ("nba", "nhl"):
            pro(a)
        elif a == "s5":
            s5()
        elif a == "s7":
            stretch("nba", "s7_nba_second_quarter", 1, "second quarter", 10, 10, LT, LH, 2018, 4)
        elif a == "s8":
            stretch("nhl", "s8_nhl_second_period", 1, "second period", 15, 15, LT, LH, 2018, 3)
        elif a == "s9":
            s9()
        elif a == "s10nfl":
            stretch("nfl", "s10_nfl_fourth_quarter", 3, "fourth quarter", None, 4, LT, LH, 2018, 4)
        elif a == "s10ncaaf":
            stretch("ncaaf", "s10_ncaaf_fourth_quarter", 3, "fourth quarter", None, 4, LT, LH, 2018, 4)
