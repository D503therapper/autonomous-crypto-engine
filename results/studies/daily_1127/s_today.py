"""11/27 daily studies S1-S10 - ten questions SPORTS_FINDINGS.md has never answered (checked first with seen.py).
The team / player box columns have all been read as SEASON rates (9/30-11/26); what was never read is ONE game's box
as a spot (the game AFTER a team got run on, got its quarterback sacked, saw the option, shot the lights out, got
beat up on the glass), the skater box's plus-minus, the conference TITLE game, the top scorer's DROUGHT in hockey, and - in the paid football history - the line that never moved. Dropped after the check: the book's first-half number against its share of the full spread (answered 10/29 -
sports_leads.h1_share; its first run here is not kept), the soft recent schedule (11/3 + 11/24), the puck line's
price (11/20). Could not be run: the see-saw team (ESPN's leadChanges exists from 2025 only - no train half),
futures (on file from 10/2 only).
What a team did THIS season before tonight (no look-ahead), ESPN's close at its own juice, regular season.
Cells fixed before the run.
  S1  NHL: THE TOP LINE'S PLUS-MINUS (the skater box's plusMinus / timeOnIce - the top three forwards by ice time)
  S2  COLLEGE HOOPS: THE GAME AFTER GETTING BEAT UP ON THE GLASS (out-rebounded by 12+ in the last game, D1 games)
  S3  COLLEGE FOOTBALL: THE CONFERENCE TITLE GAME (championship weekend, FBS vs FBS)
  S4  FOOTBALL: THE GAME AFTER GETTING RUN ON (the last game's rushing yards allowed)
  S5  FOOTBALL: THE GAME AFTER THE QUARTERBACK GOT SACKED 5+ TIMES
  S6  COLLEGE FOOTBALL: THE WEEK AFTER THE OPTION (the last opponent ran on 65%+ of its plays)
  S7  NHL: THE TOP SCORER'S DROUGHT (the team's leader in points without one in his last 4+ games)
  S8  NBA: THE NIGHT FROM THREE (the last game's makes - the hot night / the cold night / the one they gave up)
  S9  COLLEGE HOOPS: THE NIGHT FROM THREE (D1 games)
  S10 FOOTBALL: THE LINE THAT SAT STILL (the paid history: first fair spread = the last look's)
python results/studies/daily_1127/s_today.py [s1 s2 s3 s4nfl s4ncaaf s5nfl s5ncaaf s6 s7 s8 s9 s10nfl s10ncaaf]"""
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
from core import teambox, cells, ranked, hi, lo, BT, BH, LT, LH  # noqa: E402
import sports_data as sd  # noqa: E402


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


def opp_of(g, t):
    return g["away"] if g["home"] == t else g["home"]


def pair(v, sep="-"):
    """'12-37' -> (12.0, 37.0) (None when unreadable)."""
    try:
        a, b = str(v).split(sep)[:2]
        return float(a), float(b)
    except (ValueError, AttributeError):
        return None


# ------------------------------------------------------------------ S1 the top line's plus-minus
def s1(ret=False):
    lg = "nhl"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            fw, df = [], []
            for r in rows:
                toi, pm = lib.toi(r["st"].get("timeOnIce")), lib.num(r["st"].get("plusMinus"))
                if toi is None or pm is None or toi < 4:
                    continue
                if r["group"] == "forwards":
                    fw.append((toi, pm))
                elif r["group"] == "defenses":
                    df.append((toi, pm))
            if len(fw) >= 9 and len(df) >= 4:
                fw.sort(reverse=True)
                df.sort(reverse=True)
                bx.setdefault(gid, {})[str(t)] = {"f": sum(p for _, p in fw[:3]) / 3, "rest": sum(p for _, p in fw[3:]) / len(fw[3:]),
                                                   "d": sum(p for _, p in df[:2]) / 2}

    def counters(g, t, o):
        return (bx.get(g["id"]) or {}).get(str(t))

    def feats(s, n):
        return {"f": s["f"] / n, "d": s["d"] / n, "carry": (s["f"] - s["rest"]) / n}
    rk = ranked(allf, counters, feats, 10, window=10)
    if ret:
        return fin, rk
    O = h.Out("s1_nhl_top_line_plus_minus", BT, BH)
    O.p("S1 - NHL: THE TOP LINE'S PLUS-MINUS (the skater box's plusMinus / timeOnIce, never read: each game's three forwards with")
    O.p("  the most ice time and its top two defensemen, their plus-minus a game over the team's last 10 boxed games, ranked in")
    O.p("  the league that night; CARRIED = the top line's plus-minus minus the other forwards'; 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "f"):
            t += ["TOP LINE WINNING its minutes (top fifth)", "TOP LINE WINNING, " + where(g, side)]
            if lo(th, "f"):
                t.append("TOP LINE WINNING vs a top line losing")
        if lo(me, "f"):
            t += ["TOP LINE LOSING its minutes (bottom fifth)", "TOP LINE LOSING, " + where(g, side)]
        if hi(me, "d"):
            t.append("TOP PAIR WINNING its minutes (top fifth)")
        if lo(me, "d"):
            t.append("TOP PAIR LOSING its minutes (bottom fifth)")
        if hi(me, "carry"):
            t += ["CARRIED by the top line (top fifth gap to the other forwards)", "CARRIED by the top line, " + where(g, side)]
        if lo(me, "carry"):
            t += ["DEPTH better than the top line (bottom fifth gap)"]
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S2 the game after getting beat up on the glass
def s2(ret=False):
    import sports_ncaab_roster as nr
    lg = "ncaab"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    lastg = last_games(allf)
    tb = teambox(lg)
    d1 = nr.d1_set(sd.load_games(lg)) or set()
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x or x[1] > 8:
                continue
            p = x[0]
            o = opp_of(p, t)
            if d1 and (str(t) not in d1 or str(o) not in d1):
                continue
            b = tb.get(p["id"]) or {}
            me, op = lib.num((b.get(str(t)) or {}).get("totalRebounds")), lib.num((b.get(str(o)) or {}).get("totalRebounds"))
            if me is None or op is None:
                continue
            rk[(g["id"], t)] = {"gap": me - op, "won": lib.won_g(p, t), "days": x[1]}
    if ret:
        return fin, rk
    O = h.Out("s2_ncaab_beat_up_on_the_glass", BT, BH)
    O.p("S2 - COLLEGE HOOPS: THE GAME AFTER GETTING BEAT UP ON THE GLASS (the team box's totalRebounds in the team's LAST game,")
    O.p("  within 8 days, both teams Division I: out-rebounded by 12+ / by 18+; the mirror: won the glass by 12+; 2021-26,")
    O.p("  train 2021-23 / held 2024-26). The season-long glass is built (the dog slot / the stack) - this is ONE game as a spot.")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["gap"] <= -12:
            t += ["BEAT UP on the glass last game (-12 or worse)", "BEAT UP on the glass last game, " + where(g, side),
                  f"BEAT UP on the glass last game and {'won' if me['won'] else 'lost'}"]
            if me["days"] <= 2.5:
                t.append("BEAT UP on the glass last game, back within 2 days")
        if me["gap"] <= -18:
            t.append("BEAT UP on the glass last game (-18 or worse)")
        if me["gap"] >= 12:
            t += ["OWNED the glass last game (+12 or more)", "OWNED the glass last game, " + where(g, side)]
        if th and th["gap"] <= -12:
            t.append("ACROSS a team beat up on the glass last game")
        if th and th["gap"] >= 12 and me["gap"] <= -12:
            t.append("BEAT UP on the glass last game, facing a team that just owned it")
        return t
    cells(O, fin, rk, flags, need_both=False)


# ------------------------------------------------------------------ S3 the conference title game
def s3():
    import sports_players as sp
    lg = "ncaaf"
    G = sd.load_games(lg)
    allf = lib.all_finals(lg)
    fin = {g["id"]: g for g in lib.finals(lg)}
    O = h.Out("s3_ncaaf_title_games", LT, LH)
    O.p("S3 - COLLEGE FOOTBALL: THE CONFERENCE TITLE GAME (FBS vs FBS on championship weekend - the first Saturday of December,")
    O.p("  the Thursday before through that night; 2020: Dec 18-19; never Army-Navy; ESPN's close; train 2018-21 / held 2022-25).")
    O.p("  REMATCH = the two met earlier that season. The base = every FBS-vs-FBS regular-season game.")
    met = defaultdict(list)
    for g in allf:
        met[(g["season"], frozenset((g["home"], g["away"])))].append(g)
    n = 0
    for g in allf:
        s = g["season"]
        if s < 2018 or g["id"] not in fin:
            continue
        f = sp.fbs_set(G, g["start"])
        if not f or g["home"] not in f or g["away"] not in f:
            continue
        x = fin[g["id"]]
        d = date(s, 12, 1)
        sat = d + timedelta(days=(5 - d.weekday()) % 7)
        if s == 2020:
            sat = date(2020, 12, 19)
        gd = date(int(g["start"][:4]), int(g["start"][5:7]), int(g["start"][8:10]))
        names = {(G[g["id"]].get("home_name") or ""), (G[g["id"]].get("away_name") or "")}
        title = sat - timedelta(days=2) <= gd <= sat + timedelta(days=1) and not {"Army", "Navy"} <= names
        if title and gd == sat + timedelta(days=1) and g["start"][11:13] > "08":
            title = False                                 # a Sunday game is not a Saturday night's UTC tail
        for side, team, opp, o, won, _ in lib.sides(x):
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(x, side)
            for tag in ["BASE every FBS game"] + (["TITLE GAME"] if title else []):
                O.add(f"{tag}: ATS", s, at)
                O.add(f"{tag}: favorite (any price)" if o < 0 else f"{tag}: dog (any price)", s, pr, o)
                if x["sp"] is not None:
                    fav = (x["sp"] < 0) == (side == "home")
                    O.add(f"{tag}: {'favorite' if fav else 'dog'} ATS", s, at)
            if title:
                O.add(f"TITLE GAME, {'neutral' if x['neutral'] else side + ' on a campus'}: ATS", s, at)
                prior = [p for p in met[(s, frozenset((g["home"], g["away"])))] if p["start"] < g["start"]]
                if prior:
                    p = prior[-1]
                    lost = not lib.won_g(p, team)
                    O.add(f"TITLE GAME REMATCH, {'LOST' if lost else 'WON'} the first one: ATS", s, at)
                    O.add(f"TITLE GAME REMATCH, {'LOST' if lost else 'WON'} the first one: moneyline", s, pr, o)
        for tag in ["BASE every FBS game"] + (["TITLE GAME"] if title else []):
            O.add(f"{tag}: over", s, lib.tot_profit(x, True))
            O.add(f"{tag}: under", s, lib.tot_profit(x, False))
        if title:
            n += 1
            if x["total"] is not None:
                k = "50 or more" if x["total"] >= 50 else "under 50"
                O.add(f"TITLE GAME, total {k}: over", s, lib.tot_profit(x, True))
                O.add(f"TITLE GAME, total {k}: under", s, lib.tot_profit(x, False))
            if x["sp"] is not None:
                k = "a field goal or less" if abs(x["sp"]) <= 3 else "3.5 to 9.5" if abs(x["sp"]) < 10 else "10+"
                for side in ("home", "away"):
                    if (x["sp"] < 0) == (side == "home"):
                        O.add(f"TITLE GAME, spread {k}: favorite ATS", s, lib.ats(x, side))
    O.p(f"title games priced: {n}")
    O.show()
    for k, b in (("TITLE GAME: under", "BASE every FBS game: under"), ("TITLE GAME: favorite ATS", "BASE every FBS game: favorite ATS"),
                 ("TITLE GAME: dog (any price)", "BASE every FBS game: dog (any price)")):
        r = O.c.get(k)
        if r:
            got = sum(p for _, p, _ in r) / len(r)
            base = sum(p for _, p, _ in O.c[b]) / len(O.c[b])
            O.placebo(k, b, fade=got < base)
    O.save()


# ------------------------------------------------------------------ S4 / S5 / S6 one game's football box as a spot
def fbox(lg):
    """{gid: {team: {rush, att, patt, sacked, yards}}} from the team box (sacked: NFL's sacksYardsLost; college: the
    other side's sacks in the player box)."""
    tb = teambox(lg)
    out = {}
    for gid, teams in tb.items():
        for t, b in teams.items():
            ca, sk = pair(b.get("completionAttempts"), "/"), pair(b.get("sacksYardsLost"))
            out.setdefault(gid, {})[str(t)] = {"rush": lib.num(b.get("rushingYards")), "att": lib.num(b.get("rushingAttempts")),
                                               "patt": ca[1] if ca else None, "sacked": sk[0] if sk else None,
                                               "yards": lib.num(b.get("totalYards"))}
    if lg == "ncaaf":
        for gid, teams in lib.box_rows(lg).items():
            if gid not in out or len(teams) != 2:
                continue
            tot = {str(t): sum(lib.num(r["st"].get("sacks")) or 0.0 for r in rows if r["group"] == "defensive") for t, rows in teams.items()}
            (a, sa), (b, sb) = tot.items()
            if a in out[gid] and b in out[gid]:
                out[gid][a]["sacked"], out[gid][b]["sacked"] = sb, sa
    return out


def fb_sets(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    return fin, allf, last_games(allf), fbox(lg)


def s4(lg):
    fin, allf, lastg, bx = fb_sets(lg)
    big, top = (200, 250) if lg == "nfl" else (275, 350)
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x or x[1] > 16:
                continue
            p = x[0]
            b = bx.get(p["id"]) or {}
            me, op = b.get(str(t)), b.get(str(opp_of(p, t)))
            if not me or not op or op["rush"] is None or me["rush"] is None:
                continue
            rk[(g["id"], t)] = {"allowed": op["rush"], "ran": me["rush"], "won": lib.won_g(p, t)}
    O = h.Out(f"s4_{lg}_run_on", BT, BH)
    O.p(f"S4 - {lg.upper()}: THE GAME AFTER GETTING RUN ON (the rushing yards the team ALLOWED in its last game, the team box,")
    O.p(f"  within 16 days; {big}+ = run on, {top}+ = run over; the mirror: the team that ran for {big}+; 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["allowed"] >= big:
            t += [f"RUN ON last game ({big}+ allowed)", f"RUN ON last game, {where(g, side)}",
                  f"RUN ON last game and {'won' if me['won'] else 'lost'}"]
        if me["allowed"] >= top:
            t.append(f"RUN OVER last game ({top}+ allowed)")
        if me["ran"] >= big:
            t += [f"RAN for {big}+ last game", f"RAN for {big}+ last game, {where(g, side)}"]
        if th and th["ran"] >= big and me["allowed"] >= big:
            t.append("RUN ON last game, facing a team that just ran for it")
        if th and th["allowed"] >= big:
            t.append("ACROSS a team run on last game")
        return t
    cells(O, fin, rk, flags, need_both=False)


def s5(lg):
    fin, allf, lastg, bx = fb_sets(lg)
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x or x[1] > 16:
                continue
            p = x[0]
            b = bx.get(p["id"]) or {}
            me, op = b.get(str(t)), b.get(str(opp_of(p, t)))
            if not me or not op or me["sacked"] is None or op["sacked"] is None:
                continue
            rk[(g["id"], t)] = {"sacked": me["sacked"], "got": op["sacked"], "won": lib.won_g(p, t)}
    O = h.Out(f"s5_{lg}_sacked", BT, BH)
    O.p(f"S5 - {lg.upper()}: THE GAME AFTER THE QUARTERBACK GOT SACKED 5+ TIMES (the last game, within 16 days; the NFL team box's")
    O.p("  sacksYardsLost, college the other side's sacks in the player box; the mirror: the defense that got 5+; 2021-26,")
    O.p("  train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        if me["sacked"] >= 5:
            t += ["SACKED 5+ last game", f"SACKED 5+ last game, {where(g, side)}", f"SACKED 5+ last game and {'won' if me['won'] else 'lost'}"]
        if me["sacked"] >= 7:
            t.append("SACKED 7+ last game")
        if me["sacked"] == 0:
            t.append("NOT SACKED last game")
        if me["got"] >= 5:
            t += ["GOT 5+ sacks last game", f"GOT 5+ sacks last game, {where(g, side)}"]
        if th and th["got"] >= 5 and me["sacked"] >= 5:
            t.append("SACKED 5+ last game, facing a defense that just got 5+")
        if th and th["sacked"] >= 5:
            t.append("ACROSS a team sacked 5+ last game")
        return t
    cells(O, fin, rk, flags, totals=[
        ("either side sacked 5+ last game", lambda a, b: bool((a and a["sacked"] >= 5) or (b and b["sacked"] >= 5)))], need_both=False)


def s6():
    lg = "ncaaf"
    fin, allf, lastg, bx = fb_sets(lg)
    run = defaultdict(lambda: [0.0, 0.0, 0])               # (season, team) -> [rush attempts, pass attempts, games]
    opt = {}                                             # (gid, team) -> was `team` an option team going INTO gid
    for g in allf:
        for t in (g["home"], g["away"]):
            a = run[(g["season"], t)]
            if a[2] >= 3 and a[0] + a[1] > 0:
                opt[(g["id"], t)] = a[0] / (a[0] + a[1])
        b = bx.get(g["id"]) or {}
        for t in (g["home"], g["away"]):
            x = b.get(str(t))
            if x and x["att"] is not None and x["patt"] is not None:
                a = run[(g["season"], t)]
                a[0] += x["att"]
                a[1] += x["patt"]
                a[2] += 1
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x or x[1] > 10:
                continue
            p = x[0]
            sh = opt.get((p["id"], opp_of(p, t)))
            mine = opt.get((g["id"], t))
            if sh is None:
                continue
            rk[(g["id"], t)] = {"after": sh >= 0.65, "self": mine is not None and mine >= 0.65, "won": lib.won_g(p, t)}
    O = h.Out("s6_ncaaf_after_the_option", BT, BH)
    O.p("S6 - COLLEGE FOOTBALL: THE WEEK AFTER THE OPTION (the team's last opponent, within 10 days, ran on 65%+ of its plays")
    O.p("  going into that game - 3+ boxed games; the team itself is not an option team; 2021-26, train 2021-23 / held 2024-26)")
    O.p(f"  option teams going into a game: {sum(1 for v in opt.values() if v >= 0.65)} team-games of {len(opt)}")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last opponent on file")
        if me["after"] and not me["self"] and not (th and th["self"]):
            t += ["WEEK AFTER THE OPTION", f"WEEK AFTER THE OPTION, {where(g, side)}",
                  f"WEEK AFTER THE OPTION, {'won' if me['won'] else 'lost'} that game"]
        if th and th["after"] and not th["self"] and not me["self"]:
            t.append("ACROSS a team the week after the option")
        return t
    cells(O, fin, rk, flags, totals=[
        ("a side the week after the option", lambda a, b: bool((a and a["after"] and not a["self"]) or (b and b["after"] and not b["self"])))],
        need_both=False)


# ------------------------------------------------------------------ S7 the top scorer's drought
def s7():
    lg = "nhl"
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    bx = {}
    for gid, teams in lib.box_rows(lg).items():
        for t, rows in teams.items():
            d = {}
            for r in rows:
                if r["pos"] == "G" or r["group"] == "goalies":
                    continue
                d[r["pid"]] = ((lib.num(r["st"].get("goals")) or 0.0), (lib.num(r["st"].get("assists")) or 0.0))
            if d:
                bx.setdefault(gid, {})[str(t)] = d
    hist = defaultdict(list)                             # (season, team) -> [{pid: (goals, assists)}] boxed games
    rk = {}
    for g in allf:
        for t in (g["home"], g["away"]):
            rows = hist[(g["season"], t)]
            if len(rows) >= 10:
                pts, gls, gp = defaultdict(float), defaultdict(float), defaultdict(int)
                for ps in rows:
                    for pid, (a, b) in ps.items():
                        pts[pid] += a + b
                        gls[pid] += a
                        gp[pid] += 1
                top = max(pts, key=lambda k: (pts[k], k))
                topg = max(gls, key=lambda k: (gls[k], k))
                if pts[top] / max(gp[top], 1) >= 0.7 and top in rows[-1]:      # a real scorer who played the last game

                    def dry(pid, idx):
                        n = 0
                        for ps in reversed(rows):
                            if pid not in ps:
                                continue             # a game he missed neither breaks nor adds to the run
                            if (ps[pid][0] if idx == 0 else ps[pid][0] + ps[pid][1]) > 0:
                                break
                            n += 1
                        return n
                    rk[(g["id"], t)] = {"dry": dry(top, 1), "gdry": dry(topg, 0) if topg in rows[-1] else 0,
                                        "ppg": pts[top] / gp[top]}
        for t in (g["home"], g["away"]):
            b = (bx.get(g["id"]) or {}).get(str(t))
            if b:
                hist[(g["season"], t)].append(b)
    O = h.Out("s7_nhl_top_scorer_drought", BT, BH)
    O.p("S7 - NHL: THE TOP SCORER'S DROUGHT (the team's leader in points this season - 10+ boxed games, 0.7+ points a game, he")
    O.p("  played the last game - without a point in his last N games played; the top GOAL scorer without a goal; the skater")
    O.p("  box 2021-26, train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a top scorer on file")
        if me["dry"] >= 3:
            t += ["TOP SCORER no point in 3+", f"TOP SCORER no point in 3+, {where(g, side)}"]
        if me["dry"] >= 4:
            t.append("TOP SCORER no point in 4+")
        if me["dry"] == 0:
            t.append("TOP SCORER scored last game (the control)")
        if me["gdry"] >= 6:
            t.append("TOP GOAL SCORER no goal in 6+")
        if th and th["dry"] >= 3:
            t.append("ACROSS a top scorer with no point in 3+")
        return t
    cells(O, fin, rk, flags, totals=[
        ("both top scorers dry 2+", lambda a, b: bool(a and b and a["dry"] >= 2 and b["dry"] >= 2))], need_both=False)


# ------------------------------------------------------------------ S8 / S9 the night from three
def threes(lg, tag, title, made_hot, att_min, d1_only=False, ret=False):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    lastg = last_games(allf)
    tb = teambox(lg)
    d1 = set()
    if d1_only:
        import sports_ncaab_roster as nr
        d1 = nr.d1_set(sd.load_games(lg)) or set()
    rk = {}
    for g in fin:
        for t in (g["home"], g["away"]):
            x = lastg.get((g["id"], t))
            if not x or x[1] > 8:
                continue
            p = x[0]
            o = opp_of(p, t)
            if d1_only and d1 and (str(t) not in d1 or str(o) not in d1):
                continue
            b = tb.get(p["id"]) or {}
            me = pair((b.get(str(t)) or {}).get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            op = pair((b.get(str(o)) or {}).get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            if not me or not op:
                continue
            rk[(g["id"], t)] = {"m": me[0], "a": me[1], "om": op[0], "oa": op[1], "won": lib.won_g(p, t), "gap": x[1]}
    if ret:
        return fin, rk
    O = h.Out(tag, BT, BH)
    O.p(title)

    def flags(me, th, side, g):
        t = []
        if not me:
            return t
        t.append("BASE with a last-game box")
        hot = me["a"] >= att_min and me["m"] / me["a"] >= 0.5
        cold = me["a"] >= att_min and me["m"] / me["a"] <= 0.22
        if me["m"] >= made_hot:
            t += [f"MADE {made_hot}+ threes last game", f"MADE {made_hot}+ threes last game, {where(g, side)}"]
        if hot:
            t += [f"HOT NIGHT last game (50%+ on {att_min}+)", f"HOT NIGHT last game and {'won' if me['won'] else 'lost'}"]
            if me["gap"] <= 1.5:
                t.append("HOT NIGHT last game, playing the next day")
        if cold:
            t += [f"COLD NIGHT last game (22% or less on {att_min}+)", f"COLD NIGHT last game, {where(g, side)}",
                  f"COLD NIGHT last game and {'won' if me['won'] else 'lost'}"]
        if me["om"] >= made_hot:
            t.append(f"GAVE UP {made_hot}+ threes last game")
        if me["oa"] >= att_min and me["om"] / me["oa"] <= 0.22:
            t.append("OPPONENT ice cold from three last game (22% or less)")
        if th and th["a"] >= att_min and th["m"] / th["a"] >= 0.5:
            t.append("ACROSS a team off a hot night")
        if th and th["a"] >= att_min and th["m"] / th["a"] <= 0.22:
            t.append("ACROSS a team off a cold night")
        return t
    cells(O, fin, rk, flags, totals=[
        ("a side off a hot night", lambda a, b: bool((a and a["a"] >= att_min and a["m"] / a["a"] >= 0.5) or (b and b["a"] >= att_min and b["m"] / b["a"] >= 0.5))),
        ("a side off a cold night", lambda a, b: bool((a and a["a"] >= att_min and a["m"] / a["a"] <= 0.22) or (b and b["a"] >= att_min and b["m"] / b["a"] <= 0.22)))],
        need_both=False)


# ------------------------------------------------------------------ S10 the line that sat still (the paid history)
def s10(lg):
    games = [g for g in lib.load_football(lg) if not g["neutral"] or lg == "nfl"]
    seas = sorted({g["season"] for g in games})
    half = seas[:max(1, len(seas) // 2)]
    train, held = (half[0], half[-1]), [s for s in seas if s > half[-1]]
    O = h.Out(f"s10_{lg}_line_sat_still", train, held)
    O.p(f"S10 - {lg.upper()}: THE LINE THAT SAT STILL (the paid odds history, read - never pulled: the median book's spread at the")
    O.p("  FIRST FAIR look 1.5-7.5 days out against ESPN's closing spread - the spread file holds one look a game; STILL = the")
    O.p("  same number AND the paid no-vig moneyline within 1 point of win chance from its first fair look to its last look")
    O.p("  inside 1.5 days; MOVED 2+ = the spread moved 2 points or more. Graded at ESPN's close.")
    O.p(f"  seasons on file {seas}: train {train} / held {held}")
    n = defaultdict(int)
    for g in games:
        f = lib.first_fair(g["sp"])                      # (the spread file holds ONE look a game - the early one)
        fm, lm = lib.first_fair(g["ml"]), lib.last_look(g["ml"])
        if not f or g["c_sp"] is None or g["c_mlh"] is None or g["c_mla"] is None or not g["margin"]:
            continue
        s0, s1 = lib.sp_med(f[1])[0], g["c_sp"]
        dml = abs(lib.ml_med(fm[1])[2] - lib.ml_med(lm[1])[2]) * 100 if fm and lm else None
        mv = s1 - s0                                       # - = toward the home side
        kind = "STILL" if mv == 0 and dml is not None and dml < 1 else "MOVED 2+" if abs(mv) >= 2 else "moved a little"
        n[kind] += 1
        s = g["season"]
        hw = g["margin"] > 0
        r = g["margin"] + g["c_sp"]
        for side, o, won, sgn, so in (("home", g["c_mlh"], hw, 1, g["c_sho"]), ("away", g["c_mla"], not hw, -1, g["c_sao"])):
            pr = lib.profit(won, lib.dec(o))
            at = None if r == 0 else lib.profit(r * sgn > 0, lib.dec(so or -110))
            fav = (g["c_sp"] < 0) == (side == "home")
            for tag in ("BASE", kind):
                O.add(f"{tag}: ATS, the {side} side", s, at)
                O.add(f"{tag}: ATS, the {'favorite' if fav else 'dog'}", s, at)
                if 100 <= o <= 350:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
                if o < -150:
                    O.add(f"{tag}: fav past -150", s, pr, o)
            if kind == "STILL" and abs(g["c_sp"]) <= 3:
                O.add(f"STILL, a field goal or less: ATS, the {'favorite' if fav else 'dog'}", s, at)
                if 100 <= o <= 350:
                    O.add("STILL, a field goal or less: dog +100..+350", s, pr, o)
    O.p("games: " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())))
    res = O.show()
    for k, r in res.items():
        if k.startswith("BASE") or not r or r["all"]["n"] < 100 or not r["train"] or not r["held_all"]:
            continue
        base = "BASE: " + k.split(": ", 1)[1]
        b = res.get(base)
        if not b:
            continue
        d = r["all"]["roi"] - b["all"]["roi"]
        if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
            O.placebo(k, base, fade=d < 0)
    O.p(f"cells: {len(res)}")
    O.save()


if __name__ == "__main__":
    T3 = ("{} - {}: THE NIGHT FROM THREE (the team box's makes / attempts in the team's LAST game, within 8 days{}; HOT = 50%+\n"
          "  on {}+ attempts, COLD = 22% or less; 2021-26, train 2021-23 / held 2024-26)")
    RUN = {
        "s1": s1, "s2": s2,
        "s3": s3,
        "s4nfl": lambda: s4("nfl"), "s4ncaaf": lambda: s4("ncaaf"),
        "s5nfl": lambda: s5("nfl"), "s5ncaaf": lambda: s5("ncaaf"),
        "s6": s6, "s7": s7,
        "s8": lambda: threes("nba", "s8_nba_night_from_three", T3.format("S8", "NBA", "", 25), 20, 25),
        "s9": lambda: threes("ncaab", "s9_ncaab_night_from_three", T3.format("S9", "COLLEGE HOOPS", ", both teams Division I", 18), 14, 18, d1_only=True),
        "s10nfl": lambda: s10("nfl"), "s10ncaaf": lambda: s10("ncaaf")}
    for a in sys.argv[1:] or list(RUN):
        RUN[a]()
