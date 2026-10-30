"""🧪 THE LEAD TRACKER (the owner, 10/1: "you said the dog rule isn't proven - keep a tracker to see if we can prove
your theory. This tracker is for you, not the dashboard"). Every board run logs, for EVERY side on the day's slate
(picked or not), which of the unproven leads fired and its price at that moment. After the games, each lead is graded
at 1 unit at that price - won-lost, units, ROI - so a lead earns full weight once it proves itself, or gets cut.
Files: data/sports/lead_tracker.json (rows) and data/sports/lead_record.json (the grades)."""
import json
import os

import sports_data as sd

PATH = os.path.join(sd.DATA, "lead_tracker.json")
RECORD = os.path.join(sd.DATA, "lead_record.json")


def tags(c, sports):
    """The leads firing on one candidate side (moneylines)."""
    if c.get("market") != "ml":
        return []
    try:                                                     # the sharp-money signals, any side (the owner, 10/1: "the
        import sports_breakdown                              # smart money looks to be on the Browns - track it")
        sp_ = sports_breakdown.public_split(c)
    except Exception:                                        # noqa: BLE001
        sp_ = None
    sharp = []
    if sp_ and sp_[0] is not None and sp_[1] is not None:
        if sp_[1] - sp_[0] >= 10:
            sharp.append("money 10+ over tickets")
        if sp_[0] >= 70:
            sharp.append("70%+ of tickets")
        if sp_[0] < 50 and (c.get("drift") or 0) <= -0.02:
            sharp.append("reverse line move to it")
    t, lg, mo = [], c.get("league"), c.get("dog_more") or {}
    if c.get("outshot_me"):                                  # 10/8 study (built as a weight): its own live record
        t.append("NHL side outshot 40+ last game (fade)")
    if c.get("outshot_opp"):
        t.append("NHL side vs a team outshot 40+")
    if c.get("fav_off_loss"):                                # 10/14 study (built as a weight): its own live record
        t.append("college favorite off a loss (fade)")
    if c.get("fav_form_spot"):                               # 10/17 college lock hunt "rule A" (a weight): its live record
        t.append("college fav off a win vs a team off a loss")
    dog = c.get("odds", 0) >= 100
    if dog and c.get("dec") and not sports.own_beats(c) and sports.beats_price(c) and sports.good(c):
        t.append("dog: own read under the price, weighed read over it")   # (the owner, 10/19 - the Sharks Dog: "let's
        #   track it" - the Dogs that post only on the stacked weights; the 10/17 sweep had them -7..-12% blind)
    if lg == "nba" and c.get("home") and c.get("season_games") is not None \
            and sports.NBA_HOME_DOG_GAMES[0] <= c["season_games"] + 1 <= sports.NBA_HOME_DOG_GAMES[1] \
            and sports.NBA_HOME_DOG_BAND[0] <= c.get("odds", 0) <= sports.NBA_HOME_DOG_BAND[1]:
        t.append("NBA home dog, games 6-20")                 # 10/20 study (a weight)
    if lg == "nba" and c.get("nba_fav_w"):                   # 10/22 NBA favorite study (weights)
        for k in c["nba_fav_w"]:
            t.append({"star_back": "NBA fav, top-5 man back (fade)", "last_ot": "NBA fav off an OT game (fade)",
                      "own_top2_out": "NBA fav missing a top-2 man (fade)", "opp_top2_out": "NBA fav vs a team missing a top-2 man (fade)",
                      "more_rest": "NBA fav 2+ more days rest (fade)", "off_blowout": "NBA fav off a 20+ win",
                      "home_dog_mid": "NBA fav at a home dog, games 31-60"}[k])
    if dog and lg == "nba" and mo.get("last_upset") and c.get("odds", 0) >= sports.NBA_UPSET_DOG_MIN:
        t.append("NBA dog off an upset win, still +180 or longer")   # 10/24 dog-eye study: a LEAD (train +7.2% on 538,
        #                                                             4 of 7 seasons; holdout +1.1% on 73) - tracked, never a weight
    if dog and lg == "nba" and (mo.get("slate") or 0) >= sports.NBA_SLATE_BIG:   # 10/28 studies (a weight): its own record
        t.append("NBA dog on a 12+ game slate")
        if c.get("home"):                                     # 10/28 big-slate studies: a LEAD (tracker only, no extra
            t.append("NBA home dog on a 12+ game slate")      # weight) - the home dog carried the slate edge a little
            #                                                   better in every slice (lift +1.4 / +7.6 / +7.2 over the
            #                                                   big-slate base; z under 1.5) - one of 2 traits of 22 that did
    if dog and lg == "nba" and mo.get("opp_next_soft"):       # 10/28 (a weight, a fade): the favorite's next game is soft
        t.append("NBA dog, favorite's next game is soft (fade)")
    if dog and lg == "nba" and mo.get("opp_heavy_last"):      # 10/28 LEAD (tracker only): the favorite's top 3 men went
        t.append("NBA dog vs a favorite whose top 3 played 38+ last game")   # 38+ minutes last game, no overtime
    if lg == "nfl" and not dog and NFL_LOCK_MIN_FAV <= c.get("odds", 0) <= NFL_LOCK_MAX_FAV and lock_grade(c) \
            and nfl_month(c) in NFL_LOCK_COLD_MONTHS:         # 10/30 NFL unit-play studies: a LEAD, tracked only
        t.append("NFL Lock-grade small favorite in September / December+ (fade)")   # the -101..-150 favorite the engine
        #   calls Lock grade: September -30.5% on 25 (2 of 7 seasons up), Dec+ -33.9% on 26 (1 of 6 up), Oct-Nov +13.0% on
        #   62 (5 of 7) - every -101..-150 favorite leans the same way (Sep -13.2% on 122, Dec+ -10.0% on 137, Oct-Nov
        #   -1.1% on 260); three cells of one cut on small counts - never a weight, never a sizing rule till it's tracked
    if lg == "nba":                                           # 10/21 underdog studies' score (weights)
        nw = sports.nba_dog_weights(c)
        if nw >= 2 * sports.NBA_DOG_W:
            t.append("NBA dog, 10/21 dog score +4 or more")
        elif nw <= -2 * sports.NBA_DOG_W:
            t.append("NBA dog, 10/21 dog score -4 or less (fade)")
    if lg == "nhl" and c.get("ot_last") in ("ot_win", "ot_loss", "so_win"):   # 10/18 study (a weight)
        t.append({"ot_win": "NHL side off an OT win", "ot_loss": "NHL side off an OT loss (fade)",
                  "so_win": "NHL side off a shootout win (fade)"}[c["ot_last"]])
    if dog and lg == "nhl" and (c.get("pyth_luck") or 0) <= sports.PYTH_UNLUCKY:   # 10/17 study (a weight)
        t.append("NHL dog, record 10+ under its goals")
    if lg == "nhl" and c.get("odds", 0) >= sports.NHL_LONG_DOG:   # 10/17 study (built as a weight): its live record
        t.append("NHL dog +220 or longer (fade)")
    if dog and lg == "nhl" and sports.hot_dog(c):            # 10/29 ten hockey studies (built as a -2 weight): its live record
        t.append("NHL dog on a 3+ game win streak (fade)")   # (-10.5% train / -13.3% held out vs the band's -6.9% / -3.8%)
    if dog and lg == "ncaaf" and c.get("raw_own") is not None and c.get("p_market") is not None \
            and c["raw_own"] - c["p_market"] >= 0.10:            # (10/17: the RAW ratings read - the college board's
        #                                                      edge_own IS the market, so the old test never fired)
        t.append("college dog, engine 10+ over the books")   # the owner, 10/16 (Tulane): "lay off" - but keep its live
        #                                                      score (the posted / pulled ones went 0-6 through 10/16)
    if dog:
        try:
            sc = round(sports.dog_score(c), 2)
        except Exception:                                    # noqa: BLE001
            sc = None
        if sc is not None:
            if lg == "nfl" and sc >= sports.DOG_GATE:
                t.append("dog score NFL 8+")
            if lg == "nhl" and sc >= sports.NHL_DOG_GATE:
                t.append("dog score NHL 6+")
            if lg == "nhl" and 0 < sc < sports.NHL_DOG_GATE:
                t.append("hockey dog score 0-6")
            if lg == "ncaaf" and sc >= sports.NCAAF_DOG_GATE:
                t.append("dog score college 4+")
        for k, name in (("bye", "off a bye"), ("mnf", "Monday night dog"), ("neutral", "neutral-site dog")):
            if mo.get(k):
                t.append(name)
        if (mo.get("win_pct") or 0) >= 0.70 and lg == "ncaaf":
            t.append(".700 college dog")
        if lg == "ncaaf" and c.get("big_cover"):
            t.append("college dog off a 21+ cover (fade)")
        if lg == "ncaaf" and c.get("odds", 0) <= sports.DAILY_DOG_MAX:   # 10/28 college weeknight dog studies (LEADS,
            if c.get("home") and weeknight(c):                #  tracked only, never a weight): the Tue-Fri HOME dog lost in
                t.append("college weeknight home dog (fade)")   # every slice (-25.2% on 83 train, -16.4% / -18.0% / -34.5%
                #                                                held out, 138 games); weeknight dogs as a group carry
                #                                                nothing (-17.2% train, +0.4% / +7.2% / 4-11 held out)
            if beat_good_last(c):
                t.append("college dog off a win over a winning team (fade)")   # the owner's NM St story runs the wrong
                #                                                way: -26.7% on 147 train (0 of 4 up), -11.5% / -11.1% / 5-5
            t.extend(gap_band(c))                             # 10/30 college unit-play studies: the 🔍 gap play's bands
            #                                                   split for its 50-play judge (tracker only, no weight)
        if lg == "nfl" and tuple(mo.get("record") or ()) == (0, 2):
            t.append("NFL 0-2 dog")
        if (mo.get("win_streak") or 0) >= 3 and lg == "nfl":
            t.append("NFL dog 3+ win streak")
        try:
            if sports.sharp_dog(c):
                t.append("sharp dog: line to it + money over tickets")
        except Exception:                                    # noqa: BLE001
            pass
        try:                                             # the owner, 10/1 (the Jaguars): "if the engine's right,
            own = (c["edge_own"] + 1) / c["dec"]         # it beat the line - it should believe in itself." Track every
            if own - (c.get("p_market") or 1) >= 0.12:   # dog the engine's own read likes 12+ pts over the line
                t.append("engine read 12+ over the line (believe it?)")
        except (KeyError, TypeError, ZeroDivisionError):
            pass
        if c.get("dh_game2"):
            t.append("MLB doubleheader game-2 dog")
        if lg == "nba" and not c.get("home") and c.get("odds", 0) <= 350 and nba_early_west(c):
            t.append("NBA West road dog, early tip in the East (fade)")   # 10/26 daily study: 10-36 -40.9% train
            #   (1 of 7 seasons up), 0-8 in 2025, ATS 16-28 / 1-7 - a LEAD on 54 games, tracked only, never a weight
        if lg == "nfl" and mo.get("last_pts") is not None and mo["last_pts"] <= 10:
            t.append("NFL dog scored 10 or fewer last game")
        if lg in ("nba", "nhl") and c.get("odds", 0) <= 350 and slow_starts(c):
            t.append("NBA / NHL dog, lost the 1st quarter / period 3 straight (fade)")   # 10/28 daily study: NBA dogs
            #   -9.7% on 861 train / -17.1% on 99 held out (the dog base -3.7% / -6.7%), NHL dogs -16.1% on 347 / -12.6%
            #   on 29 (base -6.6% / +1.9%), worse than teams with the same last-3 results in train; but z only -1.2 / -1.6,
            #   2026 NHL +27% on 9, NBA none yet, NHL favorites the other way - tracked only, never a weight
        if lg == "nfl" and c.get("odds", 0) <= 350:          # 10/29 daily studies: LEADS, tracked only, never a weight
            sh = h1_share(c)
            if sh is not None:
                t.append("NFL dog, 1st-half spread 60%+ of the full" if sh >= H1_SHARE_BIG
                         else "NFL dog, 1st-half spread under 60% of the full (fade)")
            #   the book's 1st-half spread / the full spread (2.5+): NFL dogs at 0.60+ +7.2% on 537 train / +21.7% on 99
            #   (2025) / -5.5% on 41 (2026); under 0.60 -20.9% / -12.9% / -17.8% (685 in all) - inside every spread size,
            #   total, home / road and season; but college runs the OTHER way (0.60+ -7.5% on 1,308), the NBA only a
            #   hair the same way, ATS mixed, no known reason - and the 1st-half line is often not up at 8 AM
            if dog_run(c, 4):
                t.append("NFL dog, a dog in each of its last 4 (fade)")   # -18.3% on 232 train (1 of 7 up), -13.3% on 34
                #   (2025), 2026 -4.2% on 9; the dose 3 / 4 / 5 / 6 straight -9.6 / -17.2 / -19.2 / -20.1%; college flat
            if across_engine_lock(c):                         # 10/30 NFL unit-play studies: a LEAD, tracked only
                t.append("NFL dog across the engine's Lock-grade small favorite")   # the favorite -101..-150 the engine
                #   calls Lock grade (blend 56%+, own read over the price) lost -10.4% on 76 train / -1.3% on 37 held out
                #   at the close and -15.5% / -16.0% at the first fair early number; the dog across it +6.6% / +8.7% at the
                #   close (5 of 7 seasons up, z under 1) - never a weight (the engine never fights its own read; the 10/17
                #   NFL lock hunt had the own-read gap as noise)
        if c.get("opp_sv_slump"):
            t.append("NHL dog vs a slumping goalie (fade)")
        if c.get("west_trip_dog"):
            t.append("East home dog vs West favorite (fade)")
        if c.get("key_out_me") and lg in ("nfl", "ncaaf"):
            t.append("football dog, key player out (fade)")
        g4 = mo.get("go4_gap")
        if g4 is not None:
            import sports_go4
            if g4 <= sports_go4.GAP_LO:
                t.append("timid 4th-down dog (fade)")
            elif g4 >= sports_go4.GAP_HI:
                t.append("bold 4th-down dog")
    else:
        if lg == "nhl" and c.get("w_p") is not None:
            t.append("hockey fav weighed UP" if c["w_p"] > (c.get("p_market") or 0) else "hockey fav weighed DOWN (fade)")
        if any("West Coast favorite" in r for r in c.get("reasons") or []):
            t.append("West Coast road fav in the East")
        if c.get("hoops_inside"):
            t.append("hoops fav wins inside")
        if any("12+ innings" in r for r in c.get("reasons") or []):
            t.append("MLB scoring-drought fav")
        if lg == "ncaaf" and -150 <= c.get("odds", 0) <= -101 and (pyth_luck(c) or 0) <= UNLUCKY_FAV:
            t.append("college small fav, record 0.15+ under its points (fade)")   # 10/27 daily study: -101..-150
            #   favorites whose record sits 0.15+ under its points-for / against: -22.2% on 112 (train 2 of 7 up,
            #   2023+ -27.9%, holdout -38% on 14, 2026 -13% on 24, early price -30%; dose 0.10 -6% / 0.20 -30% /
            #   0.25 -42%), but the NFL cell is flat (-3.9% on 47) - tracked only, never a weight
        if lg == "ncaaf" and -150 <= c.get("odds", 0) <= -101 and shredded_loss(c):
            t.append("college small fav off a loss allowing 40+ (fade)")   # 10/28 daily study: -28.3% on 142 vs -15.6%
            #   for every band favorite off a loss (train 0 of 7 up, 2023+ -22.6%, holdout -35% on 17, early price -26%,
            #   ATS -32%; the dog across +35.8% on 89) - but 2026 +2% on 18, no clean dose (0-20 allowed -25%, 30-39 -4.5%)
            #   and the NFL flat; it sits inside the BUILT off-a-loss fade (-3) - tracked only, never a weight
        if lg == "nba" and -150 <= c.get("odds", 0) <= -100 and halftime_comeback(c):
            t.append("NBA small fav off a 10+ halftime comeback win")   # 10/27 daily study: train +31.8% on 68
            #   (6 of 7 up, 8+ / 12+ the same sign) but holdout 2025 3-6 -42% and the NHL version flat - tracked only
        if lg == "nfl" and c.get("odds", 0) <= -151 and shootout_win(mo):
            t.append("NFL big fav off a 30-30 shootout win")         # 10/26 daily study: -151..-400 favorites that
            #   won a game both teams scored 30+ in: +20.2% on 62 (train 7 of 7 up, 2025 -11% on 8, early price +17%);
            #   college 35+ the same sign (+8.8% on 78) but not at 31+ / 42+; the bettable -101..-150 band doesn't
            #   hold - tracked only, never a weight
    return t + sharp


NBA_WEST = {"Lakers", "Clippers", "Warriors", "Kings", "Suns", "Trail Blazers", "Jazz", "Nuggets", "Thunder",
            "Timberwolves", "Mavericks", "Rockets", "Spurs", "Grizzlies", "Pelicans"}


def nba_early_west(c):
    """A West team on the road in the East with a tip before 5 PM ET (the 10/26 body-clock study)."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    try:
        et = datetime.strptime(c["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo("America/New_York"))
    except (KeyError, TypeError, ValueError):
        return False
    return et.hour < 17 and c.get("team") in NBA_WEST and c.get("opp") not in NBA_WEST and bool(c.get("opp"))


def shootout_win(mo):
    """Won its last game with both teams scoring 30+ (dog_more's last_pts / last_margin - the 10/26 study)."""
    pts, mar = (mo or {}).get("last_pts"), (mo or {}).get("last_margin")
    return pts is not None and mar is not None and mar > 0 and pts >= 30 and pts - mar >= 30


UNLUCKY_FAV = -0.15      # (the 10/27 study's cutoff: this season's win % minus its points expectation, 4+ games)
PYTH_EXP = 2.37         # the football Pythagorean exponent
_GAMES = {}             # league -> the games file (loaded once per run)


def _season_before(c):
    """(team id, [this season's earlier final regular-season games, oldest first]) for the candidate's side - from the
    games file, results only (nothing about today's game)."""
    lg, gid = c.get("league"), c.get("game_id")
    if lg not in _GAMES:
        try:
            _GAMES[lg] = sd.load_games(lg)
        except Exception:                                    # noqa: BLE001
            _GAMES[lg] = {}
    G = _GAMES[lg]
    g = G.get(gid) or {}
    team, start = g.get(c.get("side") or ""), g.get("start") or c.get("start") or ""
    if not team or len(start) < 7:
        return None, []
    y, m = int(start[:4]), int(start[5:7])
    cut = 7 if lg in ("nfl", "ncaaf") else 9
    since = f"{y if m >= cut else y - 1}-{cut:02d}-01"
    rows = [x for x in G.values() if x.get("status") == "final" and str(x.get("stype") or "2") == "2"
            and since <= (x.get("start") or "") < start and team in (x.get("home"), x.get("away"))
            and x.get("home_score") not in ("", None) and x.get("away_score") not in ("", None)]
    return team, sorted(rows, key=lambda x: x["start"])


def pyth_luck(c):
    """This season's win % minus its points-for / points-against expectation (football, 4+ games) - None otherwise."""
    team, rows = _season_before(c)
    if len(rows) < 4:
        return None
    w = l = pf = pa = 0
    for x in rows:
        me, op = ("home", "away") if x["home"] == team else ("away", "home")
        a, b = float(x[me + "_score"]), float(x[op + "_score"])
        pf += a
        pa += b
        w += a > b
        l += a < b
    if pf + pa <= 0 or w + l == 0:
        return None
    return w / (w + l) - pf ** PYTH_EXP / (pf ** PYTH_EXP + pa ** PYTH_EXP)


def beat_good_last(c):
    """10/28 college weeknight dog studies - a LEAD, tracked only: the dog WON its last game this season (3+ games
    in) and that opponent carried a WINNING record (3+ games) into it - the owner's New Mexico St story ("they just
    smacked Western Kentucky, a good team"). It ran the WRONG way: -26.7% on 147 train (0 of 4 seasons up, z -1.7),
    -11.5% on 60 (2024), -11.1% on 52 (2025), 5-5 in 2026 - the market pays up for the dog that just beat somebody
    good (the built hangover fade's cousin). From the games file, results before kickoff only."""
    team, rows = _season_before(c)
    if len(rows) < 3:
        return False
    x = rows[-1]
    me, op = ("home", "away") if x["home"] == team else ("away", "home")
    try:
        if not float(x[me + "_score"]) > float(x[op + "_score"]):
            return False
    except (TypeError, ValueError):
        return False
    opp = x[op]
    G = _GAMES.get(c.get("league")) or {}
    yr, mo = int(x["start"][:4]), int(x["start"][5:7])
    since = f"{yr if mo >= 7 else yr - 1}-07-01"                 # that opponent's games THIS season, before that game
    w = n = 0
    for y in G.values():
        if y.get("status") != "final" or str(y.get("stype") or "2") != "2" or not (since <= (y.get("start") or "") < x["start"]) \
                or opp not in (y.get("home"), y.get("away")) or y.get("home_score") in ("", None) or y.get("away_score") in ("", None):
            continue
        a, b = ("home", "away") if y["home"] == opp else ("away", "home")
        try:
            w += float(y[a + "_score"]) > float(y[b + "_score"])
        except (TypeError, ValueError):
            continue
        n += 1
    return n >= 3 and w / n > 0.5


H1_SHARE_BIG = 0.60     # the 10/29 study's cut: the dog's 1st-half spread at 60%+ of its full-game spread


def _game(c):
    lg = c.get("league")
    if lg not in _GAMES:
        try:
            _GAMES[lg] = sd.load_games(lg)
        except Exception:                                    # noqa: BLE001
            _GAMES[lg] = {}
    return _GAMES[lg].get(c.get("game_id")) or {}


def h1_share(c):
    """The book's 1st-half spread as a share of the full-game spread, for THIS side, from tonight's game row - only when
    the side gets 2.5+ points for the game and the 1st-half line is up (None otherwise). 10/29 daily study."""
    g = _game(c)
    try:
        sp, h1 = float(g["spread_home"]), float(g["h1_spread_home"])
    except (KeyError, TypeError, ValueError):
        return None
    if c.get("side") == "away":
        sp, h1 = -sp, -h1
    elif c.get("side") != "home":
        return None
    return h1 / sp if sp >= 2.5 else None


def dog_run(c, k=4):
    """A dog (closing moneyline +100 or longer) in EACH of its last k games this season - the 10/29 NFL study. A game
    with no closing moneyline breaks the run (False)."""
    team, rows = _last_rows(c, k)
    if not rows:
        return False
    for x in rows:
        me = "home" if x["home"] == team else "away"
        try:
            if float(x["ml_" + me]) < 100:
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


GAP_WATCH = (0.15, 0.20)   # 10/30 college unit-play studies (results/studies/ncaaf_units_1030/): the rating-backed 🔍
GAP_LONG = 251             # gap dog split by band for its 50-play judge - gap 15-20 red in train AND every held-out
#                            season (22-36 -7.1% / -23.7% / -3.8% / -21.0%), gap 20+ +11.0% train / -5.3% / +23.1% /
#                            -29.7%; the +251..+350 one 10-34 -12.6% (train -29.4%, then 2-4 / 3-4 / 0-4). LEADS only
#                            (126 cells looked at, none passed the five checks) - never a weight, GAP_MIN stays 0.15.


def gap_band(c):
    """The tracker tags for a rating-backed college gap dog (raw own read 15+ over the no-vig market, Elo for the dog)."""
    if c.get("league") != "ncaaf" or c.get("raw_own") is None or c.get("p_market") is None:
        return []
    if not 100 <= (c.get("odds") or 0) <= 350 or (c.get("elo_edge") or 0) <= 0:
        return []
    gap = c["raw_own"] - c["p_market"]
    if gap < GAP_WATCH[0]:
        return []
    t = ["college gap dog 15-20 (watch)" if gap < GAP_WATCH[1] else "college gap dog 20+"]
    if c["odds"] >= GAP_LONG:
        t.append("college gap dog +251..+350 (fade)")
    return t


WEEKNIGHTS = ("Tue", "Wed", "Thu", "Fri")


def weeknight(c):
    """A Tue/Wed/Thu/Fri kickoff, Eastern time (the MACtion / CUSA / Sun Belt weeknight slate) - from the start time."""
    try:
        from datetime import datetime, timedelta
        t = datetime.fromisoformat(str(c.get("start") or "").replace("Z", "+00:00")) - timedelta(hours=5)
        return t.strftime("%a") in WEEKNIGHTS
    except (TypeError, ValueError):
        return False


def halftime_comeback(c, down=10):
    """Won its last game (this season, 3+ games in) after trailing by `down`+ at the half (the line score's first two
    quarters) - the 10/27 NBA study."""
    team, rows = _season_before(c)
    if len(rows) < 3:
        return False
    x = rows[-1]
    me, op = ("home", "away") if x["home"] == team else ("away", "home")
    try:
        a = [int(float(v)) for v in str(x.get("ls_" + me) or "").split(",")][:2]
        b = [int(float(v)) for v in str(x.get("ls_" + op) or "").split(",")][:2]
        won = float(x[me + "_score"]) > float(x[op + "_score"])
    except (ValueError, TypeError):
        return False
    return len(a) == 2 and len(b) == 2 and won and sum(a) - sum(b) <= -down


def _last_rows(c, k):
    """(team, the last k games this season) or (None, []) when there are fewer than k."""
    team, rows = _season_before(c)
    return (team, rows[-k:]) if len(rows) >= k else (None, [])


def slow_starts(c, k=3):
    """Outscored in the 1st quarter (NBA) / 1st period (NHL) - the line score's first number - in EACH of its last k
    games this season (the 10/28 study). A game with no line score = not counted as slow (False)."""
    team, rows = _last_rows(c, k)
    if not rows:
        return False
    for x in rows:
        me, op = ("home", "away") if x["home"] == team else ("away", "home")
        try:
            a = int(float(str(x.get("ls_" + me) or "").split(",")[0]))
            b = int(float(str(x.get("ls_" + op) or "").split(",")[0]))
        except (ValueError, TypeError):
            return False
        if a >= b:
            return False
    return True


NFL_LOCK_MIN_FAV, NFL_LOCK_MAX_FAV = -150, -101   # 10/30 NFL unit-play studies (tracker LEADS, never weights): the Lock band
NFL_LOCK_COLD_MONTHS = (9, 12, 1, 2)              # the months the NFL Lock-grade small favorite lost (Sep -30.5%, Dec+ -33.9%)
NFL_ACROSS_DOG_MAX = 150                          # the dog across a -101..-150 favorite sits at +100..+150


def nfl_month(c):
    """The month of the candidate's kickoff (UTC) - None without a start."""
    try:
        return int(str(c.get("start") or "")[5:7])
    except ValueError:
        return None


def _own_read(c):
    """The engine's own win read on this side (edge_own is value per $1: own x dec - 1), or None."""
    if c.get("edge_own") is None or not c.get("dec"):
        return None
    return (c["edge_own"] + 1) / c["dec"]


def lock_grade(c):
    """The board's Lock test on a favorite: the blended win % 56%+ (sports.LOCK_P) and the own read at or over the no-vig
    price (sports.own_agrees) - from the candidate's fields, no line move."""
    own = _own_read(c)
    return (c.get("p") or 0) >= 0.56 and own is not None and c.get("p_market") is not None and own >= c["p_market"]


def across_engine_lock(c):
    """An NFL dog +100..+150 whose favorite the engine calls Lock grade: the favorite's blend 56%+ (so this side's under
    44%) and this side's own read UNDER the no-vig market (the favorite's own read over it)."""
    own = _own_read(c)
    return (c.get("league") == "nfl" and 100 <= c.get("odds", 0) <= NFL_ACROSS_DOG_MAX and (c.get("p") or 1) <= 0.44
            and own is not None and c.get("p_market") is not None and own < c["p_market"])


def shredded_loss(c, cut=40):
    """LOST its last game this season while allowing `cut`+ points (the 10/28 college study)."""
    team, rows = _last_rows(c, 1)
    if not rows:
        return False
    x = rows[-1]
    me, op = ("home", "away") if x["home"] == team else ("away", "home")
    try:
        a, b = float(x[me + "_score"]), float(x[op + "_score"])
    except (TypeError, ValueError):
        return False
    return a < b and b >= cut


def load():
    try:
        return json.load(open(PATH))
    except (OSError, ValueError):
        return []


def log(day_iso, cands, sports):
    """Add today's firing leads (once per game side per day - the first look the board run took)."""
    rows = load()
    have = {(r["day"], r["game_id"], r["side"]) for r in rows}
    added = 0
    for c in cands:
        key = (day_iso, c.get("game_id"), c.get("side"))
        if key in have:
            continue
        tg = tags(c, sports)
        if not tg:
            continue
        rows.append({"day": day_iso, "game_id": c["game_id"], "league": c.get("league"), "side": c.get("side"),
                     "team": c.get("team"), "odds": c.get("odds"), "tags": tg})
        have.add(key)
        added += 1
    if added:
        with open(PATH + ".tmp", "w") as f:
            json.dump(rows, f)
        os.replace(PATH + ".tmp", PATH)
    return added


def grade(games):
    """Grade every logged row with a final score: per lead, W-L, units at 1u, ROI. Writes lead_record.json."""
    rec = {}
    for r in load():
        g = games.get(r["game_id"]) or {}
        if g.get("status") != "final":
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_:
            continue
        won = (hs > as_) == (r["side"] == "home")
        o = r.get("odds") or 100
        net = (o / 100 if o > 0 else 100 / -o) if won else -1.0
        for t in r["tags"]:
            x = rec.setdefault(t, {"w": 0, "l": 0, "units": 0.0})
            x["w" if won else "l"] += 1
            x["units"] = round(x["units"] + net, 3)
    for x in rec.values():
        n = x["w"] + x["l"]
        x["roi"] = round(x["units"] / n, 3) if n else 0.0
    with open(RECORD + ".tmp", "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    os.replace(RECORD + ".tmp", RECORD)
    return rec
