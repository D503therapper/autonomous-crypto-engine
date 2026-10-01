"""RECENT FORM (the owner, 9/30: "study every team's streaks and every player's recent performance before the picks").

What the study found (every player's box score 2021-now, graded at the closing price on seasons it never saw -
SPORTS_FINDINGS.md): team form and streaks are already in the price (nothing to use). Player form: the books - and the
public - OVER-rate a hot player. The side whose key player is much hotter (top 20% of gaps) did worse than an average
bet: NHL goalies 5 of 5 seasons (-12.4% vs -4.0%), NBA stars 3 of 4 (-10.4% vs -5.1%). Baseball pitchers, QBs and
college were mixed - not used. So in hockey and the NBA a much hotter key player counts AGAINST a pick (weighed, never
a ban - sports.HOT_W / dog_score).

  NHL: the goalie (the team's last starter) - save %, last 5 starts vs his prior 20
  NBA: the 2 stars (most minutes, last 20 games) - points, last 5 vs their last 20"""
from collections import defaultdict

HOT_CUT = {"nhl": 5.85, "nba": 7.17}      # "much hotter" = the top 20% of gaps (2021-26)
MIN_G = {"nhl": 8, "nba": 10}
FRESH_D = 21                               # form only counts when the last game was within 3 weeks (no last spring's
                                           # hot streak carried into October)


def _days(a, b):
    from datetime import datetime
    return (datetime.strptime(b[:10], "%Y-%m-%d") - datetime.strptime(a[:10], "%Y-%m-%d")).days


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def goalie_form(rows, player, before):
    """Save % last 5 minus his prior 20, x100 (None: not enough starts)."""
    mine = [r for r in rows if r["player"] == player and r["start"] < before and _f(r["sa"]) >= 10]
    h = [1 - _f(r["ga"]) / _f(r["sa"]) for r in mine]
    if len(h) < MIN_G["nhl"] or _days(mine[-1]["start"], before) > FRESH_D:
        return None
    prior = h[-25:-5]
    return (sum(h[-5:]) / 5 - sum(prior) / len(prior)) * 100


def star_form(team_games, before=None):
    """team_games: the team's last games, oldest first, each (start, {player: (minutes, points)}). The 2 stars' points,
    last 5 minus their last 20 (None: not enough games, or the last one's over 3 weeks old)."""
    if not team_games or (before and _days(team_games[-1][0], before) > FRESH_D):
        return None
    last = [b for _, b in team_games[-20:]]
    mins = defaultdict(list)
    for g in last:
        for p, (m, _) in g.items():
            mins[p].append(m)
    stars = sorted((p for p, v in mins.items() if len(v) >= MIN_G["nba"]), key=lambda p: -sum(mins[p]) / len(mins[p]))[:2]
    out = []
    for p in stars:
        pts = [g[p][1] for g in last if p in g]
        if len(pts) >= MIN_G["nba"]:
            out.append(sum(pts[-5:]) / 5 - sum(pts) / len(pts))
    return sum(out) if out else None


def hot_side(league, gap):
    """'home' / 'away' when that side's key player is MUCH hotter (the study's top 20%), else None."""
    cut = HOT_CUT.get(league)
    if cut is None or gap is None:
        return None
    return "home" if gap >= cut else "away" if gap <= -cut else None


def hot_sides(games, players, now_iso, days=2):
    """{game id: 'home' / 'away'} for upcoming NHL / NBA games where one side's key player is much hotter."""
    import sports_players as sp
    import sports_roster as sr
    import json
    out = {}
    up = [g for g in games.values() if g.get("status") == "pre" and g.get("league") in HOT_CUT
          and now_iso[:10] <= g["start"][:10] <= _plus(now_iso, days)]
    if not up:
        return out
    nhl = [r for r in (players.get("nhl") or []) if r.get("role") == "G"]
    nba_by_team = defaultdict(list)
    if any(g["league"] == "nba" for g in up):
        try:
            y = int(now_iso[:4])
            rows = sr.load("nba", seasons=[y - 1, y])
        except Exception:                                    # noqa: BLE001 - no roster data: no form weight
            rows = []
        games_by = defaultdict(lambda: defaultdict(dict))
        for r in rows:
            try:
                st = json.loads(r["stats"])
            except ValueError:
                continue
            games_by[(r["start"], r["gid"])][r["team"]][r["pid"] or r["player"]] = (_f(str(st.get("minutes", 0)).split(":")[0]),
                                                                                  _f(st.get("points")))
        for (start, _), teams in sorted(games_by.items()):
            for t, box in teams.items():
                nba_by_team[t].append((start, box))
    for g in up:
        if g["league"] == "nhl":
            fh = goalie_form(nhl, sp.last_starter(nhl, g["home"], g["start"]), g["start"])
            fa = goalie_form(nhl, sp.last_starter(nhl, g["away"], g["start"]), g["start"])
        else:
            fh = star_form([x for x in nba_by_team.get(g["home"], []) if x[0] < g["start"]], g["start"])
            fa = star_form([x for x in nba_by_team.get(g["away"], []) if x[0] < g["start"]], g["start"])
        side = hot_side(g["league"], None if fh is None or fa is None else fh - fa)
        if side:
            out[g["id"]] = side
    return out


def _plus(iso, days):
    from datetime import datetime, timedelta
    return (datetime.strptime(iso[:10], "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


# THE OVERREACTION (9/30 study, closing prices 2018-26, season by season): bettors overreact to one ugly loss or a cold
# run. Football dogs coming off a BLOWOUT LOSS: college +11.6% (6 of 8 seasons) and NFL +7.9% vs -3.6% for every dog;
# college hoops FAVORITES on a 6+ game losing streak: +6.7% (7 of 8 seasons) vs -3.8% for every favorite.
BLOWOUT = {"nfl": 21, "ncaaf": 30}         # points - "a blowout" (1.5x a normal margin)
COLD_STREAK = {"ncaab": 6}


UPSET_BOUNCE = ("nba",)                    # got upset as a -250 favorite: next game +4.9% as a fav (6 of 8), +7.1% as a dog
UPSET_HANGOVER = ("nfl", "ncaaf", "mlb")   # won as a +200 dog: next game AS A DOG NFL -30%, college -28%, MLB -14%
#                                            (vs about -3% for every dog - the market gets too high on the upset winner)
# SCORING DROUGHT (10/1 study, the owner's Red Sox point - every MLB line score 2018-26, closing prices): a FAVORITE
# that hasn't scored in 12+ innings in a row: +4.9% (363) vs -3.8% for every favorite, at -150..-101 +10.2% (217),
# better 7 of 9 seasons. Bettors fade the cold bats too hard. (Dogs in a drought: -6.9% vs -3.3%, not steady.)
DROUGHT = {"mlb": 12}                      # scoreless innings in a row


def team_states(games, now_iso):
    """{(league, team): (last game's margin, win(+)/loss(-) streak, last game's moneyline, won it, scoreless innings
    in a row)} - real games in the last 3 weeks."""
    import sports_model as sm
    out = {}
    for lg in set(BLOWOUT) | set(COLD_STREAK) | set(UPSET_BOUNCE) | set(UPSET_HANGOVER) | set(DROUGHT):
        streak, last, dry = {}, {}, {}
        for g in sorted(sm.finals(games, lg), key=lambda g: g["start"]):
            if (g.get("stype") or "2") not in ("2", "3"):
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            for t, us, them, ml, ls in ((g["home"], hs, as_, g.get("ml_home"), g.get("ls_home")),
                                        (g["away"], as_, hs, g.get("ml_away"), g.get("ls_away"))):
                try:
                    for r in [int(v) for v in (ls or "").split(",") if v != ""]:
                        dry[t] = dry.get(t, 0) + 1 if r == 0 else 0
                except ValueError:
                    dry[t] = 0
                k = streak.get(t, 0)
                streak[t] = (k + 1 if k >= 0 else 1) if us > them else (k - 1 if k <= 0 else -1) if us < them else 0
                try:
                    ml = int(float(ml))
                except (TypeError, ValueError):
                    ml = None
                last[t] = (us - them, g["start"], ml)
        for t, (mg, st, ml) in last.items():
            if _days(st, now_iso) <= FRESH_D:
                out[(lg, t)] = (mg, streak.get(t, 0), ml, mg > 0, dry.get(t, 0))
    return out


def overreaction(league, side_team, odds, states):
    """+1 when this side is one the market overreacts against (see above), -1 when it's one the market's too high on
    (the upset hangover), else 0."""
    st = tuple(states.get((league, side_team), (0, 0))) + (None, None, None)
    mg, sk, last_ml, won, dry = st[:5]
    if league in UPSET_BOUNCE and last_ml is not None and last_ml <= -250 and won is False:
        return 1                               # an NBA team that got upset as a big favorite: it bounces back
    if league in UPSET_HANGOVER and odds >= 100 and last_ml is not None and last_ml >= 200 and won:
        return -1                              # a dog again after its big upset win: the hangover
    if league in BLOWOUT and odds >= 100 and mg <= -BLOWOUT[league]:
        return 1                               # a football dog coming off a blowout loss
    if league in COLD_STREAK and odds < 0 and sk <= -COLD_STREAK[league]:
        return 1                               # a college hoops favorite on a long losing streak
    if league in DROUGHT and odds < 0 and dry is not None and dry >= DROUGHT[league]:
        return 1                               # a baseball favorite that hasn't scored in a while: bettors overdo it
    return 0


# FATIGUE (9/30 study, every box score 2021-26, closing prices): a RESTED dog facing a team that played last night -
# NBA +6.5% (4 of 5 seasons) vs -6.1% for every NBA dog; NHL +1.9% (4 of 5) vs -5.9%. The books under-rate the second
# night of a back-to-back. (A goalie on back-to-back nights: nothing - already priced.)
B2B_LEAGUES = ("nba", "nhl")


def last_starts(games):
    """{(league, team): [start of each real game, oldest first]} for the back-to-back check."""
    out = {}
    for g in sorted(games.values(), key=lambda g: g.get("start", "")):
        if g.get("league") in B2B_LEAGUES and g.get("status") in ("final", "live") and (g.get("stype") or "2") in ("2", "3"):
            for side in ("home", "away"):
                out.setdefault((g["league"], g[side]), []).append(g["start"])
    return out


def played_yesterday(starts, league, team, start):
    """Did this team play the day before this game (a back-to-back)?"""
    prev = [s for s in starts.get((league, team), []) if s < start]
    return bool(prev) and _days(prev[-1], start) == 1


# PUCK LUCK (9/30 study, every NHL box score 2021-26, closing prices): PDO = shooting % + save % over the last 10 games
# (x1000; 1000 = average, it always comes back). A dog whose luck's been BAD (<= 985): -0.9% (4 of 5 seasons better than
# the -5.8% every dog does); luck's been GOOD (>= 1015): -10.3% (worse 4 of 5). The books over-rate a lucky team.
PDO_BAD, PDO_GOOD = 985, 1015


def pdo_states(games, now_iso):
    """{team: PDO over its last 10 games} (NHL, games in the last 3 weeks only)."""
    import json
    import sports_model as sm
    import sports_roster as sr
    y = int(now_iso[:4])
    try:
        rows = sr.load("nhl", seasons=[y - 1, y])
    except Exception:                                        # noqa: BLE001
        return {}
    shots = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r["group"] in ("forwards", "defenses"):
            try:
                shots[r["gid"]][r["team"]] += float(json.loads(r["stats"]).get("shotsTotal") or 0)
            except (ValueError, TypeError):
                pass
    log, last = defaultdict(list), {}
    for g in sorted(sm.finals(games, "nhl"), key=lambda g: g["start"]):
        sh = shots.get(g["id"])
        if not sh or (g.get("stype") or "2") not in ("2", "3"):
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError):
            continue
        for t, o, gf, ga in ((g["home"], g["away"], hs, as_), (g["away"], g["home"], as_, hs)):
            if sh.get(t) and sh.get(o):
                log[t].append((gf, sh[t], ga, sh[o]))
                last[t] = g["start"]
    out = {}
    for t, L in log.items():
        L = L[-10:]
        if len(L) == 10 and _days(last[t], now_iso) <= FRESH_D:
            gf, sf_, ga, sa = (sum(x[k] for x in L) for k in range(4))
            out[t] = (gf / sf_ + 1 - ga / sa) * 1000
    return out


# COVER STREAKS & REVENGE (9/30 study, closing prices 2018-26): the public chases a cover streak. A team that FAILED to
# cover 4+ straight spreads beat the average spread bet: NBA 8 of 8 seasons, college hoops 6 of 8, college football 6
# of 8 (+2.9%), NFL 5 of 8; one that COVERED 4+ straight did worse (NFL -11.8%, college -10.7%). And a college football
# dog facing the team that blew it out last meeting: +15.7% (6 of 7 seasons) vs -3.6% for every dog.
ATS_LEAGUES = ("nfl", "ncaaf", "nba", "ncaab")
ATS_RUN = 4
REVENGE = {}                               # 10/1 OFF: with the 2024-25 college football games the feed had missed,
#                                            the revenge dog (lost the last meeting by 30+) beat every dog only 4 of 8
#                                            seasons (-1.3% vs -13.4%; 2024 and 2025 both worse). (Was {"ncaaf": 30}.)


def ats_states(games):
    """({(league, team): cover streak (+ covered / - failed)}, {(league, team, opp): last meeting's margin})."""
    import sports_model as sm
    ats, meet = {}, {}
    for lg in ATS_LEAGUES:
        for g in sorted(sm.finals(games, lg), key=lambda g: g["start"]):
            if (g.get("stype") or "2") not in ("2", "3"):
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            meet[(lg, g["home"], g["away"])], meet[(lg, g["away"], g["home"])] = hs - as_, as_ - hs
            try:
                mg = hs - as_ + float(g["spread_home"])
            except (KeyError, TypeError, ValueError):
                continue
            if mg == 0:
                continue
            for t, cov in ((g["home"], mg > 0), (g["away"], mg < 0)):
                k = ats.get((lg, t), 0)
                ats[(lg, t)] = (k + 1 if k >= 0 else 1) if cov else (k - 1 if k <= 0 else -1)
    return ats, meet


# THE DOG STUDIES (10/1, the owner: "all these dogs win every day - find them"; 15 studies, closing prices 2018-26,
# every result vs ALL dogs at the same price in the same season, checked again on 2024-26 it never shaped):
#   - a team's LAST RESULT (within 30 days): NFL / college football / college hoops dogs facing a favorite that LOST its
#     last: -1.0% vs -5.5% (7 of 9 seasons, 2024-26 -0.1% vs -5.4%); a dog that lost its last vs a favorite that won
#     its last: -11.3% vs -6.2% (worse 7 of 8); NHL both teams lost their last: +1.6% vs -4.7% (7 of 8); an NBA dog that
#     won its last vs a favorite that lost its last: -10.0% vs -4.4% (worse 7 of 8)
#   - MLB run share (last 15 games, 7+): the dog's runs-for share 2+ points over the favorite's - small, 5 of 9 seasons
#     at +130..+199 (the 2nd check, ours: weaker than the first said)
#   - NHL shot share (last 10, 5+): a dog out-shooting the favorite +1.0% vs -5.7% (5 of 5, 2024-26 +9.3% vs -1.6%);
#     out-shot by 3+ points -10.5% vs -5.6% (0 of 5)
LAST_FRESH_D = 30


def dog_states(games, now_iso, team_rows=None):
    """{(league, team): {"won": last game won (or None if stale), "rs": MLB run share last 15, "ss": NHL shot share
    last 10}} - from finished regular-season games only."""
    import sports_model as sm
    out = {}
    for lg in ("nfl", "ncaaf", "ncaab", "nba", "nhl", "mlb"):
        hist = {}
        for g in sorted(sm.finals(games, lg), key=lambda g: g["start"]):
            if (g.get("stype") or "2") != "2" or g["start"] > now_iso:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            for t, us, them in ((g["home"], hs, as_), (g["away"], as_, hs)):
                hist.setdefault(t, []).append((g["start"], us, them, g["id"]))
        for t, rows in hist.items():
            st, us, them, _ = rows[-1]
            d = {"won": (us > them) if _days(st, now_iso) <= LAST_FRESH_D else None}
            if lg == "mlb":
                q = [r for r in rows[-15:] if _days(r[0], now_iso) <= 45]
                if len(q) >= 7 and sum(r[1] + r[2] for r in q):
                    d["rs"] = sum(r[1] for r in q) / sum(r[1] + r[2] for r in q)
            out[(lg, t)] = d
    rows = team_rows if team_rows is not None else _nhl_team_rows()
    by_gid = {r["gid"]: r for r in rows}
    shots = {}
    for g in sorted(sm.finals(games, "nhl"), key=lambda g: g["start"]):
        r = by_gid.get(g["id"])
        if not r or (g.get("stype") or "2") != "2" or g["start"] > now_iso or _days(g["start"], now_iso) > 40:
            continue
        tm = r.get("teams") or {}
        try:
            sh, sa = float(tm[str(g["home"])]["shotsTotal"]), float(tm[str(g["away"])]["shotsTotal"])
        except (KeyError, ValueError, TypeError):
            continue
        shots.setdefault(g["home"], []).append((sh, sa))
        shots.setdefault(g["away"], []).append((sa, sh))
    for t, q in shots.items():
        q = q[-10:]
        if len(q) >= 5 and sum(a + b for a, b in q):
            out.setdefault(("nhl", t), {"won": None})["ss"] = sum(a for a, _ in q) / sum(a + b for a, b in q)
    return out


def _nhl_team_rows():
    try:
        import sports_roster
        return sports_roster.team_rows("nhl")
    except Exception:                                        # noqa: BLE001
        return []
