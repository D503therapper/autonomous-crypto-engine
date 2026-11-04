"""🏀 COLLEGE HOOPS KNOWLEDGE - one documented read of everything the engine knows about a team before a game (the
owner, 11/3: "Have Fable become an expert ... understand every aspect of the players, the games, the teams, the
coaches ... be on the right side of the price"). Built by the 11/3 FABLE KNOWLEDGE (A) study (results/studies/
cbb_knowledge_a/, SPORTS_FINDINGS "11/3 - FABLE: COLLEGE HOOPS KNOWLEDGE (A)") for the board's weights (sports.py)
AND for the college hoops dog read / any model that wants the same facts (import this, call read()).

    read(games, team, opp, start) -> {field: value}   (None = unknown - never a guess; every field is known before tip)

FIELDS (what each one is, where it comes from, what the study found on DOGS +100..+350 at ESPN's close 2018-26):
  coach            the head coach's name (sports_ncaab_coaches - Wikipedia's change tables on disk + ESPN's current list)
  coach_tenure     seasons with the team counting this one (None = he was there before our first page, 2015-16)
  coach_new        True = his first season with the program. The new coach's DOG: Nov-Dec +0.0% (at the price), Jan-Mar
                   -10.6% on 2,208 (vs -6.6%) - fades late; his -101..-150 favorite Jan-Mar -11.4% (the built weight)
  coach_first_time True / False / None - the hire read as a first-time head coach (the reason text; a hint). First-time
                   coaches' dogs -5.4% vs experienced hires' -8.2%: no difference the engine can use
  coach_mid        the date of a mid-season change this season (the interim since then), else None
  long_out         regulars (top 7 by minutes, not the top scorer) missing the last 4+ games (sports_ncaab_roster.
                   long_out). The DOG with one -15.0% on 847 vs -8.2% (0 of 5 seasons at the base, the open -21.8%)
  long_out_who     [(name, minutes a game, games missed)]
  roster_tin       the share of this season's minutes by D1 transfers (sports_ncaab_roster.roster_mix). The transfer-
                   heavy DOG Jan-Mar -10.0% on 2,466 vs -8.5%; the new-look dog's one window is games 6-10 (a lead)
  roster_new       the share by newcomers with no earlier D1 box (freshmen / JUCO / overseas). The freshman-heavy DOG
                   Feb-Mar -4.3% on 1,422 vs -10.2% for experienced rosters - the young dog holds up late
  to_margin        turnovers forced minus committed a game, season to date (sports_ncaab_box.identity, 5+ box games).
                   The turnover-margin DOG -8.9% (nothing), the turnover-prone -101..-150 favorite -9.7% (the built weight)
  off / def        points scored / allowed per 100 possessions over the D1 average so far. OFFENSE-FIRST (off 5.5+ over,
                   def not 4.8+ under) DOG Jan-Mar -15.1% on 1,283 vs -8.9% (a lead); DEFENSE-FIRST dog vs a bottom-third
                   offense +14.8% on 315 (1 of 2 train / 3 of 3 held, the open +14.1%) - the one dog cell that paid
  off_first        True when the team reads offense-first (above)
  def_first        True when the team reads defense-first (def 4.8+ under, off not 5.5+ over); the s7 dog view's STACK:
                   a dog with 1+ good fact (defense-first vs a bottom-third offense, a whole team vs 2+ regulars out
                   across) and no bad fact +14.5% on 337 (2 of 2 train / 2 of 3 held, the open +10.9%); 2+ bad facts
                   -16.0% on 1,801 - the facts add up on a dog, which is what a dog model should use them for
  conf_gb          conference games out of first at tip (this season's same-conference finals; conferences inferred
                   from the schedule - no conference field on file); None before 8 conference games or outside a league
  opp_conf_gb      the opponent's
  conf_power       True = a power league (holds a Duke / Kansas / Kentucky / Michigan / Villanova / Arizona)
  race_dog         Feb-Mar, 5+ games back vs a team within a game of first, not a power league: that DOG -31.2% on 664
                   (8 of 8 seasons, the open -29.3%) vs -8.6% - the built -3; vs a fellow also-ran -0.5% (even)
The weights these feed: sports.NCAAB_NEW_COACH_FAV_W / NCAAB_LONG_OUT_PTS / NCAAB_RACE_PTS / NCAAB_TO_FAV_W /
NCAAB_ROSTER_W (all inside STUDY_CAP / FAV_CAP / the rank nudge, never a trigger).

THE 11/4 FABLE EXPERT KNOWLEDGE fields (results/studies/cbb_expert_1104/, SPORTS_FINDINGS "11/4 - FABLE: COLLEGE HOOPS
EXPERT KNOWLEDGE" - the owner: "teams in shambles ... home court advantage, away teams that come in and upset ...
shooting with really good percentage, star players and injuries"; every one on DOGS +100..+350 at the close, the open
as the second check, box years 2021-22 train / 2023-25 held):
  top_out          the top scorer (points a game, 3+ games, 20+ minutes) missed the team's last game (the 11/3 DEEP -2)
  top_out_run      games he has missed running. 5+ = that DOG -24.7% on 250 (0 of 5 seasons up, the open -31.6%) vs
                   -12.9% for a 1-4 game miss - the built weight's dose, one more point (sports.NCAAB_TOP_OUT_LONG_PTS)
  top_out_who      (name, points a game)
  star_back        True = his 2ND GAME BACK tonight (he missed 2+ games, played the last one; sports_ncaab_roster.
                   star_back). The books price him as all the way back: that side ATS -25.0% on 240 (0 of 5 seasons up,
                   z -4.1), its DOG -51.1% on 87 (0 of 5, the open -40.6%), its -101..-250 favorite -17.7%; the side
                   ACROSS it ATS +15.9% on 240 (5 of 5 up). The 3rd game back fades (-11.7% ATS), the 1st is ex post.
                   BUILT: dog_spots -3, the favorite's read -0.03, the spread rank -0.03 / +0.03 across
  star_back_who    (name, points a game, games he missed)
  turmoil          regulars (top 7 by minutes) with 0 minutes in the last 3+ games who last played within 21 days - a
                   team that LOST rotation men lately (sports_ncaab_roster.turmoil). 2+ is 87 sides in five seasons: the
                   team's own dog -49.5% on 28, the side across at the vig (ATS +2.5% on 84) - a field + tracker, never
                   a weight (the one-man absences are the built long_out / top_out weights)
  turmoil_who      [(name, minutes a game, games missed)]
  turmoil_news     [(kind, headline)] - this team's news of the last 10 days (suspension, coach fired, legal trouble,
                   family / personal, a man leaving, illness) from sports_news. No archive to test: a fact on the card
  road_cm          the team's average cover margin on TRUE road floors this season (3+ road games; the games file's
                   closing spreads), road_games = how many. road_cold = True on a road team at -6 or worse: that ROAD DOG
                   -15.9% on 735 (2018-25 8 of 8 seasons down, the open -16.1%) vs -6.8% for every dog; the dose steps
                   at -6; ATS the vig (these dogs don't WIN). BUILT: dog_spots -2 (sports.NCAAB_ROAD_COLD_PTS). The HOT
                   road dog (+6) is priced (-9.4%, held -25%); a team's per-season home edge does NOT persist (corr
                   +0.01 first half vs second - dead, like the league version)
  efg_gap          eFG% over the last 5 games minus its season (sports_ncaab_box.shooting, 5+ team boxes); tp_gap /
                   two_gap the same for 3P% / 2P%. HOT shooting is in the price (the hot dog -4.0%, the hot favorite
                   -0.2%, the hot dog vs a cold favorite -17.2%). cold_shoot (eFG 4+ under) = the Jan-Mar DOG -15.5% on
                   818 (4 of 5 seasons down, 2025 +5%, the open -12.7%) - a tracker LEAD; hot_deep (3P% 6+ over, 2P% not
                   up = 3P luck) = that ROAD dog -25.0% on 318 (4 of 5 down) vs the 2P-hot road dog +3.4% - a LEAD
  good_facts       the facts the studies found PAY on a dog, as they stand on this read (the 11/3 (A) dog view, kept
  bad_facts        up: 1+ good and no bad +14.5% on 337; 2+ bad -16.0% on 1,801 - the facts add up): good = def_first vs
                   a bottom-third offense (needs opp), opp 2+ regulars lost (turmoil), the opponent's star in his 2nd
                   game back; bad = top_out, long_out, race_dog, star_back, road_cold (away only), cold_shoot (Jan-Mar),
                   hot_deep on the road, the new coach / transfer-heavy roster late. sports.ncaab_dog_good_bad adds the
                   board-only facts (the skid, the rubber match, the ranked road team, the glass, the early road dog)
DEAD in the 11/4 study (never re-run): hot shooting, shot quality vs 3P luck on favorites, free-throw streaks, my eFG
vs their defense, road teams on a roll, the per-team home edge, the star's usage share / drop-off, the opponent's star
out as a dog boost (the vig; Nov-Dec +20.8% on 83 a WATCH), the first game back (ex post), cover margin / Elo-adjusted
margin / improvement over the last 5 (priced; improving + covering = the hot-ATS fade), the letdown, the big win."""
from datetime import datetime, timedelta

import sports_data as sd

POWER_ANCHORS = {"Duke", "Kansas", "Kentucky", "Michigan", "Villanova", "Arizona"}   # a league holding one = power
RACE_GB = 5.0                # out of the race: 5+ conference games back
RACE_CONTEND = 1.0           # a contender: within a game of first
RACE_MIN_GAMES = 8           # both teams 8+ conference games before the standings mean anything
RACE_MONTHS = ("02", "03")
ROAD_COLD_CM = -6.0          # 11/4 EXPERT: a road cover margin at or under this (3+ true road games) = road_cold
ROAD_COLD_GAMES = 3
TOP_OUT_LONG = 5             # 11/4 EXPERT: the top scorer out this many games running = the long absence
FIELDS = ("coach", "coach_tenure", "coach_new", "coach_first_time", "coach_mid", "long_out", "long_out_who", "roster_tin",
          "roster_new", "to_margin", "off", "def", "off_first", "def_first", "conf_gb", "opp_conf_gb", "conf_power", "race_dog",
          # 11/4 EXPERT
          "top_out", "top_out_run", "top_out_who", "star_back", "star_back_who", "turmoil", "turmoil_who", "turmoil_news",
          "road_cm", "road_games", "road_cold", "efg_gap", "tp_gap", "two_gap", "cold_shoot", "hot_deep",
          "cold_shoot_late", "hot_deep_road", "opp_star_back", "opp_turmoil",   # (the gated names sports.NCAAB_DOG_FACTS reads)
          "good_facts", "bad_facts")
_MEMO = {}                   # (season, len(games)) -> (conferences, standings)


def month_of(start):
    try:
        return (datetime.fromisoformat(str(start).replace("Z", "+00:00")) - timedelta(hours=5)).strftime("%m")
    except ValueError:
        return ""


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


def conferences(games, season):
    """{team id: (conference key, power)} inferred from the schedule: teams that played each other at home / on the
    road in Jan 3 - Mar 1 of LAST season or from this January on, sharing 3+ opponents in that pool -> connected
    components (5+ teams); power = the component holds a POWER_ANCHORS school."""
    adj, names = {}, {}
    lo_last, hi_last = f"{season - 1}-01-03", f"{season - 1}-03-01"
    lo_now = f"{season + 1}-01-01"
    for gid, g in (games or {}).items():
        if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final" or str(g.get("stype") or "2") != "2":
            continue
        s = str(g.get("start") or "")
        if str(g.get("neutral")) == "1" or not ((lo_last <= s[:10] <= hi_last) or s[:10] >= lo_now):
            continue
        h, a = str(g.get("home")), str(g.get("away"))
        adj.setdefault(h, set()).add(a)
        adj.setdefault(a, set()).add(h)
        names[h], names[a] = g.get("home_name") or "", g.get("away_name") or ""
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
    comp = {}
    for t in adj:
        comp.setdefault(find(t), set()).add(t)
    out = {}
    for k, mem in comp.items():
        if len(mem) < 5:
            continue
        power = any(names.get(t) in POWER_ANCHORS for t in mem)
        for t in mem:
            out[t] = (k, power)
    return out


def standings(games, season, conf):
    """{team id: [conference wins, losses]} this season - regular-season finals between two teams of one league."""
    tab = {}
    lo = f"{season}-07-01"
    for gid, g in (games or {}).items():
        if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final" or str(g.get("stype") or "2") != "2":
            continue
        s = str(g.get("start") or "")
        if s[:10] < lo:
            continue
        h, a = str(g.get("home")), str(g.get("away"))
        if h not in conf or a not in conf or conf[h][0] != conf[a][0]:
            continue
        try:
            won = float(g["home_score"]) > float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        for t, w in ((h, won), (a, not won)):
            r = tab.setdefault(t, [0, 0])
            r[0 if w else 1] += 1
    return tab


def race(games, team, opp, start):
    """{"conf_gb", "opp_conf_gb", "conf_power", "race_dog_side"} at tip: games out of first for both teams in their
    shared league (None outside a league / under RACE_MIN_GAMES); race_dog_side = True when THIS team is 5+ back
    facing a contender within a game of first in Feb-Mar, not a power league (the price decides if it's the dog)."""
    out = {"conf_gb": None, "opp_conf_gb": None, "conf_power": None, "race_dog_side": False}
    start = str(start or "")
    if len(start) < 10:
        return out
    season = season_of(start)
    key = (season, id(games), len(games or {}))              # (one standings table per games dict per run)
    if key not in _MEMO:
        _MEMO.clear()
        try:
            conf = conferences(games, season)
            _MEMO[key] = (conf, standings(games, season, conf))
        except (TypeError, ValueError, KeyError):
            _MEMO[key] = ({}, {})
    conf, tab = _MEMO[key]
    team, opp = str(team), str(opp)
    if team not in conf or opp not in conf or conf[team][0] != conf[opp][0]:
        return out
    out["conf_power"] = conf[team][1]
    league = [t for t, v in conf.items() if v[0] == conf[team][0]]
    rows = [tab.get(t) for t in league if tab.get(t)]
    if len(rows) < 6 or not all(sum(tab.get(t, (0, 0))) >= RACE_MIN_GAMES for t in (team, opp)):
        return out
    lead = max(r[0] - r[1] for r in rows)
    out["conf_gb"] = (lead - (tab[team][0] - tab[team][1])) / 2
    out["opp_conf_gb"] = (lead - (tab[opp][0] - tab[opp][1])) / 2
    out["race_dog_side"] = (month_of(start) in RACE_MONTHS and not conf[team][1] and out["conf_gb"] >= RACE_GB
                            and out["opp_conf_gb"] <= RACE_CONTEND)
    return out


def road_cover(games, team, start):
    """(average cover margin on true road floors this season before `start`, road games with a closing spread) from
    the games dict - (None, 0) when there is nothing to read (the 11/4 EXPERT road-cold read)."""
    start = str(start or "")
    if len(start) < 10:
        return None, 0
    season = season_of(start)
    lo = f"{season}-07-01"
    v = []
    for gid, g in (games or {}).items():
        if g.get("league", "ncaab") != "ncaab" or g.get("status") != "final" or str(g.get("stype") or "2") != "2":
            continue
        s = str(g.get("start") or "")
        if not (lo <= s < start) or str(g.get("away")) != str(team) or str(g.get("neutral")) == "1":
            continue
        try:
            sp = float(g["spread_home"])
            m = float(g["home_score"]) - float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        v.append(-m - sp)
    return ((sum(v) / len(v)) if v else None), len(v)


def turmoil_news(team, start, news=None):
    """[(kind, headline)] - this team's college hoops news of the turmoil kinds in the 10 days before `start`
    (sports_news; the feed holds what ESPN's league news said - never a number, never a weight)."""
    try:
        import sports_news
        news = sports_news.load() if news is None else news
        cut = (datetime.fromisoformat(str(start).replace("Z", "+00:00")) - timedelta(days=sports_news.DRAMA_DAYS)).strftime("%Y-%m-%d")
        kinds = ("suspension", "coach fired", "legal trouble", "family/personal", "trade drama", "illness")
        return [(e["kind"], e["headline"]) for e in sports_news.drama(news, "ncaab", str(team))
                if e.get("kind") in kinds and str(e.get("date", "")) >= cut]
    except Exception:                                        # noqa: BLE001
        return []


def dog_facts(k, opp_k=None, start="", away=None):
    """{"good": [...], "bad": [...]} from a knowledge read `k` (and the opponent's read `opp_k`, when given): the dog
    view's bookkeeping - which studied facts stand FOR a dog with this read and which AGAINST it (see the module doc)."""
    month = month_of(start)
    good, bad = [], []
    o = opp_k or {}
    if k.get("def_first") and o.get("off") is not None:
        import sports_ncaab_box as nb
        if o["off"] <= nb.OFF_LO:
            good.append("def_first_vs_bad_offense")
    if (o.get("turmoil") or 0) >= 2:
        good.append("opp_turmoil")
    if o.get("star_back"):
        good.append("opp_star_back")
    if k.get("top_out"):
        bad.append("top_out")
    if k.get("long_out"):
        bad.append("long_out")
    if k.get("race_dog"):
        bad.append("race_dog")
    if k.get("star_back"):
        bad.append("star_back")
    if k.get("road_cold") and away:
        bad.append("road_cold")
    if k.get("cold_shoot") and month in ("01", "02", "03"):
        bad.append("cold_shoot")
    if k.get("hot_deep") and away:
        bad.append("hot_deep_road")
    if k.get("coach_new") and month in ("01", "02", "03"):
        bad.append("new_coach_late")
    if k.get("roster_tin") is not None and month in ("02", "03"):
        import sports_ncaab_roster as nr
        if k["roster_tin"] >= nr.TIN_HEAVY:
            bad.append("transfer_heavy_late")
    return {"good": good, "bad": bad}


def read(games, team, opp, start, neutral=False, away=None, facts=True):
    """Every FIELDS entry for `team` facing `opp` at `start` (see the module doc). Unknown = None, never a guess.
    `away` = True when the team is on a true road floor (road_cold and the road facts need it; None = unknown);
    facts=True fills good_facts / bad_facts (reads the opponent too - one extra read, cached inside the modules)."""
    import sports_ncaab_box as nb
    import sports_ncaab_coaches as nc
    import sports_ncaab_roster as nr
    out = {k: None for k in FIELDS}
    team, opp = str(team), str(opp)
    # ---- 11/4 EXPERT: the star, the turmoil, the road, the shooting ----
    to = nr.top_out(games, team, start)
    if to:
        out["top_out"] = bool(to["out"])
        out["top_out_run"] = (to.get("run") or 0) if to["out"] else 0
        out["top_out_who"] = (to["name"], to["ppg"])
    sb = nr.star_back(games, team, start)
    if sb:
        out["star_back"] = bool(sb["back2"])
        out["star_back_who"] = (sb["name"], sb["ppg"], sb["missed"]) if sb["back2"] else None
    tu = nr.turmoil(games, team, start)
    if tu:
        out["turmoil"], out["turmoil_who"] = tu["lost"], tu["who"]
    out["turmoil_news"] = turmoil_news(team, start)
    cm, n = road_cover(games, team, start)
    if cm is not None and n >= ROAD_COLD_GAMES:
        out["road_cm"], out["road_games"] = round(cm, 2), n
        out["road_cold"] = cm <= ROAD_COLD_CM
    sh = nb.shooting(games, team, start)
    if sh:
        out.update({"efg_gap": sh["efg_gap"], "tp_gap": sh["tp_gap"], "two_gap": sh["two_gap"],
                    "cold_shoot": sh["cold"], "hot_deep": sh["hot_deep"],
                    "cold_shoot_late": sh["cold"] and month_of(start) in ("01", "02", "03"),
                    "hot_deep_road": bool(sh["hot_deep"] and away)})
    st = nc.state(team, start)
    if st:
        out.update({"coach": st["coach"], "coach_tenure": st.get("tenure"), "coach_new": bool(st.get("new")),
                    "coach_first_time": st.get("first_time"), "coach_mid": st.get("mid")})
    lo = nr.long_out(games, team, start)
    if lo:
        out["long_out"], out["long_out_who"] = lo["n"], lo["who"]
    mix = nr.roster_mix(games, team, start)
    if mix:
        out["roster_tin"], out["roster_new"] = mix["tin"], mix["new"]
    idn = nb.identity(games, team, start)
    if idn:
        out.update({"to_margin": idn["tom"], "off": idn["off"], "def": idn["def"],
                    "off_first": idn["off"] >= nb.OFF_HI and idn["def"] > nb.DEF_GOOD,
                    "def_first": idn["def"] <= nb.DEF_GOOD and idn["off"] < nb.OFF_HI})
    if not neutral:
        r = race(games, team, opp, start)
        out.update({"conf_gb": r["conf_gb"], "opp_conf_gb": r["opp_conf_gb"], "conf_power": r["conf_power"],
                    "race_dog": r["race_dog_side"]})
    else:
        out["race_dog"] = False
    if facts:
        opp_k = read(games, opp, team, start, neutral, away=(None if away is None else not away), facts=False)
        out["opp_star_back"] = opp_k.get("star_back")
        out["opp_turmoil"] = opp_k.get("turmoil")
        f = dog_facts(out, opp_k, start, away)
        out["good_facts"], out["bad_facts"] = f["good"], f["bad"]
    return out
