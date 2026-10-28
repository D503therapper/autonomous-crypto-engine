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
