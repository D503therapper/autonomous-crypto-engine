"""11/23 daily studies S1-S10 - ten questions SPORTS_FINDINGS.md has never answered (checked first: no study on the
third quarter, a conference's non-league form, NHL giveaways / takeaways, the NHL penalty differential, the game after
getting shelled, an NBA star's 40-minute night, the foul-prone college road team, NFL points per drive, the running
quarterback). What a team did THIS season before tonight (no look-ahead), every read LEAGUE-RELATIVE (the top / bottom
fifth of the league's current values that night), ESPN's close at its own juice, regular season. Cells fixed before the run.
  S1  NBA: THE THIRD QUARTER - the margin out of halftime, last 10 (the line scores; 11/20 read the 4th quarter)
  S2  FOOTBALL (NFL + college): THE THIRD QUARTER - season to date
  S3  COLLEGE HOOPS: A CONFERENCE'S NON-LEAGUE FORM - how the REST of a team's league has covered outside the league
      this season (Nov-Dec non-league games; leagues inferred from last season's January-March schedule)
  S4  NHL: GIVEAWAYS / TAKEAWAYS (the team box) - takeaways minus giveaways a game, season to date
  S5  NHL: THE PENALTY DIFFERENTIAL - power-play chances drawn minus given, and penalty minutes a game (the team box's
      powerPlayOpportunities / penaltyMinutes; the 10/1 special-teams round had no box and read conversion rates)
  S6  NHL: THE GAME AFTER GETTING SHELLED - 40+ shots against last game
  S7  NBA: THE STAR'S 40-MINUTE NIGHT - a top-2 minutes man played 40+ in the team's last game, 1-2 days ago
  S8  COLLEGE HOOPS: THE FOUL-PRONE TEAM ON THE ROAD (fouls a game, D1 games; 11/4 read fouls on the TOTAL only)
  S9  NFL: POINTS PER DRIVE (the team box's totalDrives) - for minus against, and the drive count on the total
  S10 FOOTBALL: THE RUNNING QUARTERBACK - the top passer's rushing yards a game (the player box)
python results/studies/daily_1123/s_today.py [s1 s2nfl s2ncaaf s3 nhl s7 s8 s9 s10nfl s10ncaaf]"""
import glob
import json
import os
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

BT, BH = (2021, 2023), [2024, 2025, 2026]            # the box seasons
LT, LH = (2018, 2021), [2022, 2023, 2024, 2025, 2026]  # the line-score seasons


def teambox(lg):
    out = {}
    for f in [os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")] + sorted(glob.glob(os.path.join(sd.DATA, "teamstats", lg, "*.jsonl"))):
        if not os.path.exists(f):
            continue
        for ln in open(f):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            out[r["gid"]] = r["teams"]
    return out


def ranked(allf, counters, feats, minn, window=None, minteams=20):
    """{(gid, team): {feat: (value, league pct)}} - each team's features from its earlier games this season (the last
    `window` when given), ranked among every team's current value that night."""
    hist = defaultdict(lambda: deque(maxlen=window))
    latest = defaultdict(dict)
    out = {}
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            rows = hist[(s, t)]
            if len(rows) >= minn:
                sums = defaultdict(float)
                for r in rows:
                    for k, v in r.items():
                        sums[k] += v
                f = feats(sums, len(rows))
                if f:
                    cur[t] = f
                    latest[s][t] = f
        vals = latest[s]
        if len(vals) >= minteams:
            for t, f in cur.items():
                out[(g["id"], t)] = {k: (f[k], sum(1 for x in vals.values() if x[k] < f[k]) / (len(vals) - 1)) for k in f}
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            c = counters(g, t, o)
            if c:
                hist[(s, t)].append(c)
    return out


def cells(O, fin, rk, flags, totals=(), need_both=True):
    """flags(me, them, side, g) -> [tags]; every tag gets ATS / dog / small fav / fav past -150 cells + the BASE."""
    n = 0
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if need_both and (not a or not b):
            continue
        n += 1
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(g, side)
            for tag in ["BASE"] + list(flags(me, th, side, g)):
                O.add(f"{tag}: ATS", s, at)
                if 100 <= o <= 350:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
                if o < -150:
                    O.add(f"{tag}: fav past -150", s, pr, o)
        for name, cond in [("BASE every game", lambda x, y: True)] + list(totals):
            if cond(a, b):
                O.add(f"TOTAL {name}: over", s, lib.tot_profit(g, True))
                O.add(f"TOTAL {name}: under", s, lib.tot_profit(g, False))
    O.p(f"priced games read: {n}")
    res = O.show()
    O.p("")
    for k, r in res.items():
        if k.startswith("BASE") or k.startswith("TOTAL BASE") or not r or r["all"]["n"] < 100 or not r["train"] or not r["held_all"]:
            continue
        kind = k.rsplit(": ", 1)[1]
        base = ("TOTAL BASE every game: " if k.startswith("TOTAL") else "BASE: ") + kind
        b = res.get(base)
        if not b:
            continue
        d = r["all"]["roi"] - b["all"]["roi"]
        if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
            O.placebo(k, base, fade=d < 0)
    O.p(f"cells: {len(res)}")
    O.save()


def hi(x, k, q=0.8):
    return x[k][1] >= q


def lo(x, k, q=0.2):
    return x[k][1] <= q


# ------------------------------------------------------------------ S1 / S2 the third quarter
def third(lg, tag, window, minn, train, held, since):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= since]

    def counters(g, t, o):
        a, b = lib.quarters(g.get("ls_h")), lib.quarters(g.get("ls_a"))
        if not a or not b or len(a) < 4 or len(b) < 4:
            return None
        me, th = (a, b) if g["home"] == t else (b, a)
        return {"q3": me[2] - th[2], "h1": me[0] + me[1] - th[0] - th[1], "all": sum(me) - sum(th)}

    def feats(s, n):
        return {"q3": s["q3"] / n, "h1": s["h1"] / n, "all": s["all"] / n}
    rk = ranked(fin, counters, feats, minn, window=window)
    O = h.Out(tag, train, held)
    O.p(f"{tag.upper()} - {lg.upper()} THE THIRD QUARTER ({'last ' + str(window) if window else 'season to date'}, {minn}+ games; "
        f"league-relative fifths; train {train[0]}-{train[1]} / held {held[0]}-{held[-1]})")

    def flags(me, th, side, g):
        t = []
        if hi(me, "q3"):
            t.append("TOP fifth third-quarter margin")
            if lo(th, "q3"):
                t.append("TOP fifth third quarter vs a BOTTOM fifth one")
            if me["h1"][1] < 0.5:
                t.append("TOP fifth third quarter, first half under the league middle (the adjusters)")
            if me["all"][1] < 0.5:
                t.append("TOP fifth third quarter on a team outscored overall (bottom half by margin)")
        if lo(me, "q3"):
            t.append("BOTTOM fifth third-quarter margin")
            if hi(th, "q3"):
                t.append("BOTTOM fifth third quarter vs a TOP fifth one")
            if me["all"][1] >= 0.5:
                t.append("BOTTOM fifth third quarter on a team that wins overall (top half by margin)")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S3 a conference's non-league form
def s3():
    fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2017]
    allf = lib.all_finals("ncaab")
    d1 = sm.ncaab_d1(allf)
    # leagues a season: teams that played each other on a home floor Jan 3 - Mar 1 of LAST season, 3+ shared opponents
    by_year = defaultdict(lambda: defaultdict(set))
    for g in allf:
        st = g["start"][:10]
        y = int(st[:4])
        if g["neutral"] or g["stype"] != "2" or not (f"{y}-01-03" <= st <= f"{y}-03-01"):
            continue
        by_year[y][g["home"]].add(g["away"])
        by_year[y][g["away"]].add(g["home"])
    conf = {}
    for y, adj in by_year.items():
        par = {t: t for t in adj}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for t, ops in adj.items():
            for o in ops:
                if t < o and len(adj[t] & adj.get(o, set())) >= 3:
                    par[find(t)] = find(o)
        comp = defaultdict(set)
        for t in adj:
            comp[find(t)].add(t)
        conf[y] = {t: k for k, mem in comp.items() if 5 <= len(mem) <= 20 for t in mem}   # season y (Nov y) reads Jan-Mar y
    O = h.Out("s3_conference_form", LT, LH)
    O.p("S3 - COLLEGE HOOPS: A CONFERENCE'S NON-LEAGUE FORM (Nov-Dec non-league D1 games 2018-26; the REST of the league's")
    O.p("     cover rate / win rate against its prices outside the league this season, 25+ such games, the team's own left out)")
    for y in sorted(conf):
        if y >= 2018:
            O.p(f"     season {y}: {len(set(conf[y].values()))} leagues, {len(conf[y])} teams")
    cs = defaultdict(lambda: [0, 0.0, 0.0, 0.0])      # (season, league) -> [n ats, covers, n ml, wins minus expected]
    ts = defaultdict(lambda: [0, 0.0, 0.0, 0.0])      # (season, team)
    for g in fin:
        s = g["season"]
        if g["start"][5:7] not in ("11", "12") or s not in conf or g["home"] not in d1 or g["away"] not in d1:
            continue
        ch, ca = conf[s].get(g["home"]), conf[s].get(g["away"])
        if not ch or not ca or ch == ca:
            continue

        def form(t, c):
            a, b = cs[(s, c)], ts[(s, t)]
            n = a[0] - b[0]
            m = a[2] - b[2]
            return ((a[1] - b[1]) / n if n >= 25 else None, (a[3] - b[3]) / m if m >= 25 else None)
        fh, fa = form(g["home"], ch), form(g["away"], ca)
        ph = lib.nv(g["mlh"], g["mla"])
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (fh, fa) if side == "home" else (fa, fh)
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(g, side)
            tags = ["BASE"]
            if me[0] is not None and th[0] is not None:
                tags.append("BASE both leagues read")
                if me[0] >= 0.55:
                    tags.append("the rest of its league covers 55%+ outside the league")
                if me[0] <= 0.45:
                    tags.append("the rest of its league covers 45% or less outside the league")
                if me[0] - th[0] >= 0.10:
                    tags.append("its league covers 10+ points more often than the other team's")
                if me[0] - th[0] <= -0.10:
                    tags.append("its league covers 10+ points less often than the other team's")
            if me[1] is not None and th[1] is not None:
                if me[1] - th[1] >= 0.05:
                    tags.append("its league WINS 5+ points over its prices more than the other team's")
                if me[1] - th[1] <= -0.05:
                    tags.append("its league WINS 5+ points under its prices against the other team's")
            for tag in tags:
                O.add(f"{tag}: ATS", s, at)
                if 100 <= o <= 350:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
        for t, c, side, p in ((g["home"], ch, "home", ph), (g["away"], ca, "away", 1 - ph)):   # after the game: the books
            at = lib.ats(g, side)
            won = (g["hs"] > g["as"]) == (side == "home")
            for d in (cs[(s, c)], ts[(s, t)]):
                if at is not None:
                    d[0] += 1
                    d[1] += 1.0 if at > 0 else 0.0
                d[2] += 1
                d[3] += (1.0 if won else 0.0) - p
    res = O.show()
    O.p("")
    for k, r in res.items():
        if k.startswith("BASE") or not r or r["all"]["n"] < 100 or not r["train"] or not r["held_all"]:
            continue
        base = "BASE both leagues read: " + k.rsplit(": ", 1)[1]
        b = res.get(base)
        if b:
            d = r["all"]["roi"] - b["all"]["roi"]
            if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
                O.placebo(k, base, fade=d < 0)
    O.p(f"cells: {len(res)}")
    O.save()


# ------------------------------------------------------------------ S4 / S5 / S6 the NHL team box
def nhl():
    tb = teambox("nhl")
    fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021 and g["stype"] == "2"]
    last = {}                                           # (gid, team) -> (shots against last game, days since, won it)
    prev = {}
    for g in allf:
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            if (g["season"], t) in prev:
                last[(g["id"], t)] = prev[(g["season"], t)] + (g["start"],)
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            b = (tb.get(g["id"]) or {}).get(str(o))
            sa = lib.num((b or {}).get("shotsTotal"))
            if sa is not None:
                prev[(g["season"], t)] = (sa, g["start"], lib.won_g(g, t))
            else:
                prev.pop((g["season"], t), None)

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        v = [lib.num(a.get(k)) for k in ("giveaways", "takeaways", "penaltyMinutes", "powerPlayOpportunities")] + \
            [lib.num(b.get(k)) for k in ("giveaways", "takeaways", "penaltyMinutes", "powerPlayOpportunities")]
        if None in v:
            return None
        road = 1.0 if g["away"] == t else 0.0
        return {"gv": v[0], "tk": v[1], "pim": v[2], "ppo": v[3], "o_gv": v[4], "o_tk": v[5], "o_ppo": v[7],
                "r_n": road, "r_net": road * (v[1] - v[0])}

    def feats(s, n):
        return {"net": (s["tk"] - s["gv"]) / n, "gv": s["gv"] / n, "pim": s["pim"] / n, "ppd": (s["ppo"] - s["o_ppo"]) / n,
                "rnet": s["r_net"] / s["r_n"] if s["r_n"] >= 4 else 0.0}
    rk = ranked(allf, counters, feats, 10)
    O = h.Out("s4_s6_nhl", BT, BH)
    O.p("S4 / S5 / S6 - NHL GIVEAWAYS + TAKEAWAYS, THE PENALTY DIFFERENTIAL, THE GAME AFTER GETTING SHELLED")
    O.p("  (team box 2021-26, season to date, 10+ games, league-relative fifths; train 2021-23 / held 2024-26)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "net"):
            t.append("S4 TOP fifth takeaways minus giveaways a game")
        if lo(me, "net"):
            t.append("S4 BOTTOM fifth takeaways minus giveaways a game")
        if hi(me, "rnet") and me["rnet"][0] != 0.0:
            t.append("S4 TOP fifth takeaways minus giveaways in ROAD games only (no home scorer)")
        if lo(me, "rnet") and me["rnet"][0] != 0.0:
            t.append("S4 BOTTOM fifth takeaways minus giveaways in ROAD games only")
        if hi(me, "gv"):
            t.append("S4 TOP fifth giveaways a game (sloppy)")
        if hi(me, "ppd"):
            t.append("S5 TOP fifth penalty differential (draws more power plays than it gives)")
            if lo(th, "ppd"):
                t.append("S5 TOP fifth penalty differential vs a BOTTOM fifth one")
        if lo(me, "ppd"):
            t.append("S5 BOTTOM fifth penalty differential (gives more power plays than it draws)")
            if hi(th, "ppd"):
                t.append("S5 BOTTOM fifth penalty differential vs a TOP fifth one")
        if hi(me, "pim"):
            t.append("S5 TOP fifth penalty minutes a game")
        if lo(me, "pim"):
            t.append("S5 BOTTOM fifth penalty minutes a game")
        team = g["home"] if side == "home" else g["away"]
        opp = g["away"] if side == "home" else g["home"]
        for who, tm in (("", team), ("ACROSS a team that ", opp)):
            lv = last.get((g["id"], tm))
            if lv and lv[0] >= 40:
                d = lib.days_between(lv[1], lv[3])
                nm = f"S6 {who}gave up 40+ shots last game" if who else "S6 gave up 40+ shots last game"
                t.append(nm)
                if not who:
                    t.append(nm + (" and WON it" if lv[2] else " and lost it"))
                    if d <= 2.2:
                        t.append(nm + ", playing again within 2 days")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S7 the NBA star's 40-minute night
def s7():
    fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["season"] >= 2018]
    allf = [g for g in lib.all_finals("nba") if g["season"] >= 2018]
    bx = lib.box_rows("nba")
    mins = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))    # (season, team) -> pid -> [minutes, games]
    prev = {}                                                    # (season, team) -> (start, {pid: minutes})
    flag = {}                                                    # (gid, team) -> (n of top-2 at 40+, n at 38+, days)
    for g in allf:
        for t in (g["home"], g["away"]):
            key = (g["season"], t)
            tot = mins[key]
            reg = sorted((p for p, v in tot.items() if v[1] >= 10), key=lambda p: -tot[p][0] / tot[p][1])[:2]
            if len(reg) == 2 and key in prev and g["stype"] == "2":
                d = lib.days_between(prev[key][0], g["start"])
                lm = prev[key][1]
                flag[(g["id"], t)] = (sum(1 for p in reg if lm.get(p, 0) >= 40), sum(1 for p in reg if lm.get(p, 0) >= 38), d)
        for t in (g["home"], g["away"]):
            rows = (bx.get(g["id"]) or {}).get(str(t)) or []
            lm = {}
            for r in rows:
                m = lib.num(r["st"].get("minutes"))
                if m:
                    lm[r["pid"]] = m
                    v = mins[(g["season"], t)][r["pid"]]
                    v[0] += m
                    v[1] += 1
            if lm:
                prev[(g["season"], t)] = (g["start"], lm)
            else:
                prev.pop((g["season"], t), None)
    O = h.Out("s7_nba_40_minutes", LT, LH)
    O.p("S7 - NBA: THE STAR'S 40-MINUTE NIGHT (the team's top-2 minutes men, 10+ games; the player box 2018-26; train 2018-21 / held 2022-26)")
    rk = {k: v for k, v in flag.items()}

    def flags(me, th, side, g):
        t = []
        if me:
            t.append("BASE top-2 read")
            if me[0] >= 1:
                t.append("a top-2 minutes man played 40+ last game")
                if me[2] <= 1.3:
                    t.append("a top-2 minutes man played 40+ LAST NIGHT (back-to-back)")
                elif me[2] <= 2.3:
                    t.append("a top-2 minutes man played 40+ two nights ago")
                else:
                    t.append("a top-2 minutes man played 40+ last game, 3+ days ago")
            if me[1] >= 2:
                t.append("BOTH top-2 minutes men played 38+ last game")
        if th and th[0] >= 1 and th[2] <= 2.3 and not (me and me[0] >= 1):
            t.append("ACROSS a team whose top-2 man played 40+ in the last 2 nights")
        return t
    cells(O, fin, rk, flags, need_both=False)


# ------------------------------------------------------------------ S8 the foul-prone college team on the road
def s8():
    tb = teambox("ncaab")
    fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2021]
    d1 = sm.ncaab_d1(lib.all_finals("ncaab"))
    fin = [g for g in fin if g["home"] in d1 and g["away"] in d1]

    def counters(g, t, o):
        if t not in d1 or o not in d1:
            return None
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        try:
            fta = float(str(a["freeThrowsMade-freeThrowsAttempted"]).split("-")[1])
            ofta = float(str(b["freeThrowsMade-freeThrowsAttempted"]).split("-")[1])
        except (KeyError, ValueError, IndexError):
            return None
        pf, opf = lib.num(a.get("fouls")), lib.num(b.get("fouls"))
        if pf is None or opf is None:
            return None
        road = 1.0 if (g["away"] == t and not g["neutral"]) else 0.0
        return {"pf": pf, "opf": opf, "fta": fta, "ofta": ofta, "r_n": road, "r_pf": road * (pf - opf)}

    def feats(s, n):
        return {"pf": s["pf"] / n, "net": (s["pf"] - s["opf"]) / n, "ofta": s["ofta"] / n, "fta": s["fta"] / n}
    rk = ranked(allf, counters, feats, 5, minteams=100)
    O = h.Out("s8_ncaab_fouls_road", BT, BH)
    O.p("S8 - COLLEGE HOOPS: THE FOUL-PRONE TEAM ON THE ROAD (team box 2021-26, D1 games, 5+; league-relative fifths)")

    def flags(me, th, side, g):
        t = []
        where = "neutral" if g["neutral"] else ("home" if side == "home" else "road")
        if hi(me, "pf"):
            t.append("TOP fifth fouls a game")
            t.append(f"TOP fifth fouls a game, {where}")
            if where == "road" and hi(th, "fta"):
                t.append("TOP fifth fouls on the road at a team in the top fifth of free-throw attempts")
        if lo(me, "pf"):
            t.append(f"BOTTOM fifth fouls a game, {where}")
        if hi(me, "net") and where == "road":
            t.append("TOP fifth fouls minus fouls drawn, road")
        if hi(me, "fta") and where == "road":
            t.append("TOP fifth free-throw attempts (lives at the line), road")
        if hi(me, "fta") and where == "home":
            t.append("TOP fifth free-throw attempts (lives at the line), home")
        return t
    cells(O, fin, rk, flags)


# ------------------------------------------------------------------ S9 NFL points per drive
def s9():
    tb = teambox("nfl")
    fin = [g for g in lib.finals("nfl") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nfl") if g["season"] >= 2021 and g["stype"] == "2"]

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        dr, odr = lib.num(a.get("totalDrives")), lib.num(b.get("totalDrives"))
        if not dr or not odr:
            return None
        pts, opts = (g["hs"], g["as"]) if g["home"] == t else (g["as"], g["hs"])
        return {"dr": dr, "odr": odr, "pts": pts, "opts": opts}

    def feats(s, n):
        return {"net": s["pts"] / s["dr"] - s["opts"] / s["odr"], "off": s["pts"] / s["dr"], "def": -s["opts"] / s["odr"],
                "drives": (s["dr"] + s["odr"]) / n, "ppg": (s["pts"] - s["opts"]) / n}
    rk = ranked(allf, counters, feats, 4)
    O = h.Out("s9_nfl_points_per_drive", BT, BH)
    O.p("S9 - NFL: POINTS PER DRIVE (team box totalDrives 2021-26, season to date, 4+ games; league-relative fifths)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "net"):
            t.append("TOP fifth net points per drive")
            if me["ppg"][1] < 0.8:
                t.append("TOP fifth net points per drive, NOT top fifth by scoreboard margin")
        if lo(me, "net"):
            t.append("BOTTOM fifth net points per drive")
            if me["ppg"][1] > 0.2:
                t.append("BOTTOM fifth net points per drive, NOT bottom fifth by scoreboard margin")
        if me["net"][1] - th["net"][1] >= 0.4:
            t.append("40+ league places better per drive than the other team")
        if hi(me, "off") and lo(th, "def"):
            t.append("TOP fifth offense per drive vs a BOTTOM fifth defense per drive")
        return t
    cells(O, fin, rk, flags, totals=(("both teams top-40% in drives a game (fast, short drives)", lambda a, b: a["drives"][1] >= 0.6 and b["drives"][1] >= 0.6),
                                     ("both teams bottom-40% in drives a game (long drives)", lambda a, b: a["drives"][1] <= 0.4 and b["drives"][1] <= 0.4),
                                     ("both offenses top-40% per drive", lambda a, b: a["off"][1] >= 0.6 and b["off"][1] >= 0.6),
                                     ("both defenses top-40% per drive", lambda a, b: a["def"][1] >= 0.6 and b["def"][1] >= 0.6)))


# ------------------------------------------------------------------ S10 the running quarterback
def s10(lg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021 and g["stype"] == "2"]
    bx = lib.box_rows(lg)

    def counters(g, t, o):
        rows = (bx.get(g["id"]) or {}).get(str(t)) or []
        att, rush = defaultdict(float), defaultdict(float)       # (a man has one row a group: passing / rushing / ...)
        tot = 0.0
        for r in rows:
            ry = lib.num(r["st"].get("rushingYards"))
            if ry is not None:
                tot += ry
                rush[r["pid"]] += ry
            ca = str(r["st"].get("completions/passingAttempts") or "")
            try:
                att[r["pid"]] += float(ca.split("/")[1])
            except (IndexError, ValueError):
                pass
        if not att:
            return None
        qb = max(att, key=att.get)
        best, qr = att[qb], rush.get(qb, 0.0)
        if best < 10:
            return None
        return {"qr": qr, "rush": tot}

    def feats(s, n):
        return {"qr": s["qr"] / n, "share": s["qr"] / s["rush"] if s["rush"] > 0 else 0.0}
    rk = ranked(allf, counters, feats, 4)
    O = h.Out(f"s10_running_qb_{lg}", BT, BH)
    O.p(f"S10 - {lg.upper()}: THE RUNNING QUARTERBACK (the top passer's rushing yards a game, the player box 2021-26, 4+ games; league-relative fifths)")

    def flags(me, th, side, g):
        t = []
        if hi(me, "qr"):
            t.append("TOP fifth quarterback rushing yards a game")
            if not hi(th, "qr"):
                t.append("TOP fifth running quarterback vs a team without one")
            t.append("TOP fifth running quarterback, " + ("home" if side == "home" else "road"))
        if lo(me, "qr"):
            t.append("BOTTOM fifth quarterback rushing (a statue)")
        if hi(me, "share"):
            t.append("TOP fifth share of the team's rushing that is the quarterback's")
        return t
    cells(O, fin, rk, flags, totals=(("both quarterbacks top-40% runners", lambda a, b: a["qr"][1] >= 0.6 and b["qr"][1] >= 0.6),
                                     ("both quarterbacks bottom-40% runners", lambda a, b: a["qr"][1] <= 0.4 and b["qr"][1] <= 0.4)))


if __name__ == "__main__":
    for a in sys.argv[1:] or ("s1", "s2nfl", "s2ncaaf", "s3", "nhl", "s7", "s8", "s9", "s10nfl", "s10ncaaf"):
        if a == "s1":
            third("nba", "s1_nba_third_quarter", 10, 10, LT, LH, 2018)
        elif a == "s2nfl":
            third("nfl", "s2_nfl_third_quarter", None, 4, LT, LH, 2018)
        elif a == "s2ncaaf":
            third("ncaaf", "s2_ncaaf_third_quarter", None, 4, LT, LH, 2018)
        elif a == "s3":
            s3()
        elif a == "nhl":
            nhl()
        elif a == "s7":
            s7()
        elif a == "s8":
            s8()
        elif a == "s9":
            s9()
        elif a == "s10nfl":
            s10("nfl")
        elif a == "s10ncaaf":
            s10("ncaaf")
