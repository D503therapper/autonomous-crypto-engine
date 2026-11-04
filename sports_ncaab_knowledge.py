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
NCAAB_ROSTER_W (all inside STUDY_CAP / FAV_CAP / the rank nudge, never a trigger)."""
from datetime import datetime, timedelta

import sports_data as sd

POWER_ANCHORS = {"Duke", "Kansas", "Kentucky", "Michigan", "Villanova", "Arizona"}   # a league holding one = power
RACE_GB = 5.0                # out of the race: 5+ conference games back
RACE_CONTEND = 1.0           # a contender: within a game of first
RACE_MIN_GAMES = 8           # both teams 8+ conference games before the standings mean anything
RACE_MONTHS = ("02", "03")
FIELDS = ("coach", "coach_tenure", "coach_new", "coach_first_time", "coach_mid", "long_out", "long_out_who", "roster_tin",
          "roster_new", "to_margin", "off", "def", "off_first", "def_first", "conf_gb", "opp_conf_gb", "conf_power", "race_dog")
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


def read(games, team, opp, start, neutral=False):
    """Every FIELDS entry for `team` facing `opp` at `start` (see the module doc). Unknown = None, never a guess."""
    import sports_ncaab_box as nb
    import sports_ncaab_coaches as nc
    import sports_ncaab_roster as nr
    out = {k: None for k in FIELDS}
    team, opp = str(team), str(opp)
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
    return out
