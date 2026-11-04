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
    """The leads firing on one candidate side (moneylines; a spread side only for its own spread leads)."""
    if c.get("market") == "spread":
        return spread_tags(c, sports)
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
                      "home_dog_mid": "NBA fav at a home dog, games 31-60",
                      "faster": "NBA fav 4+ possessions faster than the dog (fade)",          # 11/3 FABLE NBA deep
                      "home_after_trip": "NBA fav, first home game after a 4+ trip (fade)"}[k])   # dive (weights)
    if lg == "nba" and dog and nba_fast_dog(c):             # 11/3 FABLE NBA deep dive (a LEAD, never a weight)
        t.append("NBA dog 4+ possessions faster than the favorite (fade)")
    if lg == "nba" and not dog and -150 <= c.get("odds", 0) <= -101 and mo.get("rest") is not None \
            and mo.get("opp_rest") is not None and mo["rest"] <= 1 and mo["opp_rest"] <= 1:
        t.append("NBA fav -101..-150, both teams on a b2b")   # 10/30 NBA favorite rest / travel study: the ONE cell of 36
        #                                                     up in both halves (train 55-33 +12.6% on 88, 3 of 6 seasons;
        #                                                     held out 20-11 +14.2%, 2 of 2; now 3-4) - a LEAD (3 of 6 =
        #                                                     not a weight); every rested-favorite spot LOST (the books
        #                                                     over-move for rest)
    if lg == "nhl" and NHL_FEB_HOME_ODDS[0] <= c.get("odds", 0) <= NHL_FEB_HOME_ODDS[1] and nhl_feb_home(c):
        t.append("NHL home side in February (fade)")   # 11/2 daily study 5 (NHL home ice by month): the home side in
        #   February -12.1% on 705 train (2018-21, 0 of 4 up) / -7.2% on 496 held out (2022-25; 2024 +0.7%) at the close,
        #   the paid 2021-23 MORNING price -13.5% on 458, vs -2..-5% for the other months; but the neighbors flip
        #   (December -7.2%, January / March near the base), ~50 month cells looked at, no mechanism and no live
        #   February yet - a LEAD, tracked only (fires from February), never a weight
    if lg == "ncaab" and HOOPS_BLOWOUT_ODDS[0] <= c.get("odds", 0) <= HOOPS_BLOWOUT_ODDS[1] and hoops_blowout_b2b(c):
        t.append("college hoops side the day after a 15+ loss (fade)")   # 11/1 daily study 9 (college hoops prep, the
        #   Nov-Dec tournament back-to-back - the consolation game): ATS -13.1% on 75 train (2018-21) / -21.3% on 68 held
        #   out (2022-25, 4 of 4 down) at a neutral site, -32.8% on 40 at home / road; the moneyline -10.4% / -16.8%
        #   (neutral, -400..+350) - but the dose is ragged (lost by 10-14 ATS +3.1%, 15-19 -27.2%, 20+ -13.2%) and ~60
        #   cells looked at: a LEAD, tracked only, never a weight (the season opens 11/3 - no live games yet)
    if dog and lg == "ncaab" and c.get("rubber_dog") and c.get("odds", 0) <= 350:
        t.append("college hoops rubber-match dog (fade)")   # 11/3 college hoops (B) study 2 (BUILT as a -2 dog_spots
        #   weight): the 3rd meeting after a 1-1 split, the dog -22.1% on 457 (0 of 5 train, 0 of 3 held out) - its live record
    if dog and lg == "ncaab" and (c.get("ncaab_skid") or 0) >= sports.NCAAB_SKID and c.get("odds", 0) <= 350:
        t.append("college hoops dog on a 5+ game skid (fade)")   # 11/3 college hoops (B) study 4 (BUILT as a -2 dog_spots
        #   weight): -20.0% on 1,127, Jan-Mar 0 of 5 train / 0 of 3 held out up - its live record
    if dog and lg == "ncaab" and c.get("top_out") and c.get("odds", 0) <= 350:
        t.append("college hoops dog, top scorer missed its last game (fade)")   # 11/3 DEEP (BUILT as a -2 dog_spots
        #   weight, sports.mark_ncaab_top_out): -20.5% on 617 vs -5.7% at the close 2022-25 (0 of 4 seasons at the
        #   base), the open -20.7% - its live record; judge at 50: running at or above -6% = the weight comes off
    if lg == "ncaab" and c.get("ncaab_top_out_fav"):
        t.append("college hoops fav -101..-250, top scorer missed its last game (fade)")   # 11/3 DEEP (BUILT as a -2
        #   weight on the favorite's read, sports.weigh_ncaab_top_out): -7.8% on 344 vs -4.0% - its live record
    # 11/3 FABLE - COLLEGE HOOPS SECOND OPINION (results/studies/fable_cbb_1103/; BUILT as weights in sports.py -
    # dog_spots / ncaab_fable_spread_w): the live records of the moneyline sides. Judge each at 50.
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("ranked_road"):
        t.append("college hoops top-25 team as a road dog, Nov-Dec (fade)")   # -31.1% on 104 (0 of 5 train, 1 of 3 held)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("vs_ranked_road"):
        t.append("college hoops home dog vs a top-25 road team, Nov-Dec")   # +14.0% on 146 (3 of 5 / 3 of 3 held, open +30.9%)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and (c.get("ats_gap") or 0) >= sports.NCAAB_ATS_GAP:
        t.append("college hoops hot-ATS dog, gap 3+ (fade)")   # the hot side as a dog -9.4% on 1,656 (1 of 5 / 0 of 3)
    if not dog and lg == "ncaab" and -150 <= c.get("odds", 0) <= -101 and c.get("ats_gap") is not None \
            and c["ats_gap"] <= -sports.NCAAB_ATS_GAP:
        t.append("college hoops cold-ATS fav -101..-150, gap -3")   # +1.1% on 811 (3 of 5 / 2 of 3, the open +7.5%) vs -4%
        #   for the band - a LEAD on the moneyline (only the spread side is a weight); the owner's 'slight favorites'
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and (c.get("reb_gap") or 0) >= sports.NCAAB_REB_GAP_BIG:
        t.append("college hoops dog out-rebounding by 8+ a game")   # +10.0% on 397 (4 of 5 seasons up, the open +8.4%)
    if not dog and lg == "ncaab" and -200 <= c.get("odds", 0) <= -101 and c.get("reb_gap") is not None \
            and c["reb_gap"] <= -sports.NCAAB_REB_GAP:
        t.append("college hoops fav -101..-200 out-rebounded by 6+ a game (fade)")   # -17.9% on 368 at 8+ (0 of 5 up)
    # 11/3 FABLE - COLLEGE HOOPS KNOWLEDGE (A) (results/studies/cbb_knowledge_a/; the weights live in sports.py):
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("long_out"):
        t.append("college hoops dog, a regular out 4+ games (fade)")   # BUILT as a -2 dog_spots weight
        #   (sports.mark_ncaab_long_out): -15.0% on 847 vs -8.2% (0 of 2 train / 0 of 3 held out up, the open -21.8%)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("race_dog"):
        t.append("college hoops dog 5+ games back vs a contender, Feb-Mar (fade)")   # BUILT as a -3 dog_spots weight
        #   (sports.mark_ncaab_race): -31.2% on 664, 8 of 8 seasons down, the open -29.3% - its live record
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("ncaab_new_coach") and _month(c) in sports.NCAAB_NEW_COACH_MONTHS:
        t.append("college hoops dog, first-year coach, Jan-Mar (fade)")   # a LEAD (the favorite is the weight):
        #   -10.6% on 2,208 vs -6.6% (0 of 5 train up, 1 of 3 held, the open -10.8%) - the new coach's team fades late
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("def_first") and c.get("opp_off_low"):
        t.append("college hoops defense-first dog vs a bottom-third offense")   # a LEAD (the s7 dog view): +14.0% on 313
        #   (train 1 of 2 up, held out 3 of 3, the open +13.3%) vs -7.3% for every dog - z 1.9, tracked only; judge at 50
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("off_first") and _month(c) in ("01", "02", "03"):
        t.append("college hoops offense-first dog, Jan-Mar (fade)")   # a LEAD (sports_ncaab_box.identity - a top-third
        #   offense without a best-third defense): -15.1% on 1,283 vs -8.9% (0 of 2 / 0 of 3, the open -17.6%) - but the
        #   dose is odd (the worst defenses -9.0%) and Nov-Dec flips (+4.7%): tracked only, never a weight
    # 11/4 FABLE - COLLEGE HOOPS EXPERT KNOWLEDGE (results/studies/cbb_expert_1104/): the two weights' live records,
    # the dose, and five LEADS (tracked only, never a weight) - judge each at 50
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("star_back"):
        t.append("college hoops dog, top scorer's 2nd game back (fade)")   # BUILT as a -3 dog_spots weight: -51.1% on
        #   87 (0 of 5 seasons up, the open -40.6%); the side ATS -25.0% on 240
    if not dog and lg == "ncaab" and sports.NCAAB_STAR_BACK_FAV_BAND[0] <= c.get("odds", 0) <= sports.NCAAB_STAR_BACK_FAV_BAND[1] and c.get("star_back"):
        t.append("college hoops fav -101..-250, top scorer's 2nd game back (fade)")   # BUILT as -0.03 on its read: -17.7% on 62
    if lg == "ncaab" and c.get("opp_star_back") and (dog or -250 <= c.get("odds", 0) <= -101) and c.get("odds", 0) <= 350:
        t.append("college hoops side vs a top scorer's 2nd game back")   # the mirror: the favorite across -151..-250
        #   +20.8% on 40 (3 of 3 held), the dog across +10.8% on 72; the side ATS +15.9% on 240 (5 of 5 up)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("ncaab_road_cold"):
        t.append("college hoops road dog 6+ short of its number on the road (fade)")   # BUILT as a -2 dog_spots weight:
        #   -15.9% on 735 (8 of 8 seasons down, the open -16.1%) vs -6.8%
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("top_out") and (c.get("top_out_run") or 0) >= sports.NCAAB_TOP_OUT_LONG:
        t.append("college hoops dog, top scorer out 5+ games (fade)")   # the built -2's dose (+1): -24.7% on 250 (0 of 5 up)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("cold_shoot") and _month(c) in ("01", "02", "03") \
            and (c.get("ncaab_skid") or 0) < sports.NCAAB_SKID:
        t.append("college hoops cold-shooting dog, Jan-Mar (fade)")   # a LEAD: eFG% last 5 at least 4 under its season
        #   -15.5% on 818 with no skid (4 of 5 seasons down, 2025 +5%, the open -12.7%) vs -8.4% - never a weight
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("hot_deep") and not c.get("home") and not c.get("neutral"):
        t.append("college hoops 3P-hot road dog (fade)")   # a LEAD: 3P% last 5 +6 over its season, 2P% not up (3P luck)
        #   -25.0% on 318 (4 of 5 down, 2025 +16%, the open -26.0%) vs the 2P-hot road dog +3.4%
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and (c.get("opp_turmoil") or 0) >= 2:
        t.append("college hoops dog vs a team that lost 2+ rotation men in 3 weeks")   # a LEAD: 87 sides in five seasons,
        #   the dog across +4.8% on 29 (the vig) - the owner's 'team in shambles', tracked live
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("opp_top_out") and _month(c) in ("11", "12"):
        t.append("college hoops dog vs a top scorer out, Nov-Dec")   # a WATCH: +20.8% on 83 (Jan-Mar -6.8%, all -2.2%)
    if dog and lg == "ncaab" and 100 <= c.get("odds", 0) <= 200 and c.get("upset_winner"):
        t.append("college hoops upset winner (beat a top-25 team as a +150 dog), a dog again +100..+200")   # a LEAD:
        #   +26.7% on 117 (3 of 5 train, 3 of 3 held, the open +22.1%, z 2.4); +201..+350 +0.6% - the owner's confidence spot
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and c.get("dog_good") is not None:
        if c["dog_good"] and not c["dog_bad"]:
            t.append("college hoops dog, 1+ good fact and no bad fact")   # the 11/3 (A) dog view's STACK: +14.5% on 337
        elif len(c["dog_bad"]) >= 2:
            t.append("college hoops dog, 2+ bad facts (fade)")   # -16.0% on 1,801 - the facts add up (sports.ncaab_dog_good_bad)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 350 and ncaab_newlook_dog(c):
        t.append("college hoops new-look dog (transfer-heavy), games 6-10")   # 11/3 DEEP study 5 (a LEAD, tracked
        #   only): a dog whose roster leans on strong D1 transfers (sports_ncaab_roster.tin_m 0.03+, the top third) in
        #   its games 6-10 +9.8% on 380 (train 2022-23 +2.3%, held out +29.0% / +4.1%; the open +5.4%) vs -5.6% for the
        #   other dogs; the study's Elo version +13.8% on 401 (4 of 4 up) - but a narrow window found by looking
        #   (games 1-5 -15%, 11-15 +2%), ~160 cells, z 1.4-2.0, and the same teams as favorites LOSE (-10%): never a weight
    if dog and lg == "ncaab":                                # 🔍🏀 11/4 DOG EXPERT: the college hoops gap play's bands
        t.extend(gap_band(c))                                #   (its 50-play judge by gap) and the dog read's gate
        try:
            if sports.ncaab_dog_read_ok(c):
                t.append("college hoops dog read 4+")        # +16.5% on 600 at the close (5/5 train, 3/3 held, open +11.5%)
        except Exception:                                    # noqa: BLE001
            pass
    # 11/3 FABLE - COLLEGE HOOPS KNOWLEDGE (B) (results/studies/cbb_knowledge_b/ s3 / s6): the owner's 'good slight
    # favorites' - two LEADS, tracked only, never a weight (looked-for cells among ~250; each a single idea)
    if lg == "ncaab" and not dog and HOOPS_SLIGHT_BAND[0] <= c.get("odds", 0) <= HOOPS_SLIGHT_BAND[1]:
        if hoops_march_home_fav(c):
            t.append("college hoops home slight fav -101..-150 in March")   # s6 (a): +9.4% on 255 at the close (train
            #   2018-22 +11.1%, 5 of 5 up; held out 2023-25 +7.0%, 2 of 3; the open +6.7%) vs -4.3% for every slight
            #   favorite and -2.5% for the February home favorite; the whole March favorite pool sits at the vig
        if hoops_glass_eff_fav(c):
            t.append("college hoops home slight fav out-rebounding by 4+, efficiency read 3+ over")   # s3 B: +13.2% on
            #   151 (box seasons 2021-22 +20.5%, 2 of 2; held out 2023-25 +8.7%, 3 of 3; the open +8.3%) vs +4.8% on 314
            #   for the glass alone and -2.9% for the efficiency agreement alone at home; fires once both teams have
            #   5 box games (~mid-November)
    if dog and lg == "nba" and c.get("odds", 0) <= 350 and nba_rest_stack(c):
        t.append("NBA dog on 2+ days off vs a team on a back-to-back")   # 11/2 daily study 3 (rest stacking): the dog
        #   with 2+ nights off vs a b2b team +6.2% on 104 train (2016-22, 3 of 5 up) / +13.4% on 65 held out vs -0.1% /
        #   -6.3% for the 1-day-off dog vs a b2b; the 2020-23 morning price +12.3% on 56 vs -7.7%; the same side as a
        #   -151..-300 favorite +6.2% vs -5.9%, ATS +0.6% vs -5.5% - one sign everywhere, but z 0.8 on 169: a dose of the
        #   BUILT +3 rested_vs_b2b, tracked only, never a second weight
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
    if dog and lg == "nhl" and c.get("odds", 0) <= 350 and (c.get("drift") or 0) >= 0.02:   # the BUILT drift -4 (the money ran
        t.append("NHL dog, the money left it 2+ since the open (fade)")   # away since the open) - re-confirmed on the 11/2
        #   paid 2021-23 history at the 8 AM price: -19.2% on 579 vs -10.8% for every dog, 0 of 3 seasons up, z -3.9 - its live record
    if dog and lg == "nhl" and sports.hot_dog(c):            # 10/29 ten hockey studies (built as a -2 weight): its live record
        t.append("NHL dog on a 3+ game win streak (fade)")   # (-10.5% train / -13.3% held out vs the band's -6.9% / -3.8%)
    if dog and lg == "ncaaf" and c.get("raw_own") is not None and c.get("p_market") is not None \
            and c["raw_own"] - c["p_market"] >= 0.10:            # (10/17: the RAW ratings read - the college board's
        #                                                      edge_own IS the market, so the old test never fired)
        t.append("college dog, engine 10+ over the books")   # the owner, 10/16 (Tulane): "lay off" - but keep its live
        #                                                      score (the posted / pulled ones went 0-6 through 10/16)
    if dog and lg == "ncaab" and c.get("odds", 0) <= 150 and c.get("eff_p") is not None \
            and c.get("p_market") is not None and c["eff_p"] - c["p_market"] >= 0.03:
        t.append("college hoops short dog the efficiency read is 3+ over")   # 11/3 DEEP s_short_dog.py: +3.9% on 2,687
        #   at the close 2018-25 (train +2.6%, 4 of 5 up; held out +6.0%, 3 of 3) vs -2.8% for every short dog and -5.2%
        #   when the read is against it - but z 1.8, no dose (edge 3-6 +6.9%, 6-10 +2.5%, 10+ +1.3%), the open +0.5%,
        #   one of 110 hunt cells: a LEAD, tracked only (judge at 100)
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
            if bowl_need1(c):
                t.append("college dog needing its 6th win (fade)")   # 10/31 daily study 3 (the bowl chase), FBS vs
                #   FBS 10/20-11/30: +6.5% on 68 train (2018-22) then -21.4% / -17.9% / -26.0% held out (2023-25) and
                #   ATS -13.9% held (base -4.7%) - the market now pays up for 'they need it'; train never agreed - a LEAD
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
        if lg in sports.MKT_TREND_LEAGUES and c.get("odds", 0) <= 350:   # 10/30 daily study 2 (the market's last-3-games
            if sports.market_fade_spot(c):                                #  move on this team): the fade is BUILT as a -2
                t.append("NBA / NHL dog, the market faded its last 3 games (fade)")   # weight in the NBA (the NHL weight came
                #   off 11/2 - the 2021-23 odds history said nothing; the NHL side keeps its live record here)
            elif (c.get("mkt_trend") or 0) >= sports.MKT_FADE_SUM and lg in MKT_BACKED_LEAGUES:
                t.append("NBA / NHL dog, the market backed its last 3 games")   # the mirror: a LEAD, tracked only (NBA
                #   +9.9% / NHL +11.9% at the open on 501 / 392, at the close +7.8% / +7.2%, 2023 train small) - no weight
        if lg == "nhl" and c.get("odds", 0) <= 350 and nhl_four_in_six(c):
            t.append("NHL dog, 4th game in 6 nights (fade)")   # 10/30 daily study 5: -8.4% on 716 train (2018-22, 2 of 5
            #   up) / -9.5% on 476 held out (2023 -8.3, 2024 -11.9, 2025 -10.1) vs -1.7% / -2.1% for the rested base; but
            #   the rested team across it is NOT up (-4.6% / -2.7%) and z -1.7 held - tracked only, never a weight
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
        if lg == "ncaaf" and -150 <= c.get("odds", 0) <= -101 and c.get("dec") and c.get("w_p") is not None \
                and c["w_p"] * c["dec"] > 1 and not sports.own_beats(c):
            t.append("college small fav: weighed read over the price, own read under")   # 10/31 college sweep: the
            #   favorite the weights (rule A, off-a-loss, depth) carry over the price but the 10/18 own-read rule keeps off
            #   the board - the funnel replay 24-13 +17.3% train / 10-5 +21.7% held out (4 of 4 seasons), but the 10/30
            #   study's same cell over the odds history 79-54 +6.9% with train 2020-23 -7.4%, and ~60 cells looked at -
            #   a LEAD, tracked for its own record (judge at 30), never a play
        if lg == "ncaaf" and -150 <= c.get("odds", 0) <= -101 and shredded_loss(c):
            t.append("college small fav off a loss allowing 40+ (fade)")   # 10/28 daily study: -28.3% on 142 vs -15.6%
            #   for every band favorite off a loss (train 0 of 7 up, 2023+ -22.6%, holdout -35% on 17, early price -26%,
            #   ATS -32%; the dog across +35.8% on 89) - but 2026 +2% on 18, no clean dose (0-20 allowed -25%, 30-39 -4.5%)
            #   and the NFL flat; it sits inside the BUILT off-a-loss fade (-3) - tracked only, never a weight
        if lg == "ncaab" and -150 <= c.get("odds", 0) <= -101 and hoops_early_away(c):
            t.append("college hoops small fav away from home, games 1-3 (fade)")   # 10/30 daily study 10 (college
            #   hoops prep): -101..-150 favorites on the road / at a neutral site in their first 3 games -18.1% on 95 train
            #   (2018-21, 1 of 4 up) / -12.1% on 84 held out (2022-25, 0 of 4 up) vs -4.1% for road favorites later; at
            #   home +2.1% - the open 10/16 'college hoops Locks small the first 2 weeks' question; tracked only
        if c.get("ncaab_away_fav"):                          # 11/3 college hoops (B) study 4b (BUILT as a -3 weight,
            t.append("college hoops small fav away from home, Nov-Dec (fade)")   # sports.weigh_ncaab_away_fav): its live
            #   record - -11.6% on 1,097 at the close 2018-25 (0 of 5 train, 0 of 3 held out up); judge at 50: the fade
            #   side winning 55%+ against a -125 average price = the weight comes off
        if c.get("ncaab_eff_fav"):                           # 11/3 DEEP college hoops efficiency model (BUILT as a -3
            t.append("college hoops slight fav the efficiency read is 3+ under (fade)")   # weight, sports.weigh_ncaab_eff_fav):
            #   its live record - -9.6% on 2,338 at the close 2018-25 (0 of 5 train, 0 of 3 held out up); judge at 50: the
            #   faded favorites running at or above -4.5% (every slight favorite's base) = the weight comes off
        if c.get("ncaab_new_coach_fav"):                     # 11/3 KNOWLEDGE (A) study 1 (BUILT as a -3 weight,
            t.append("college hoops small fav, first-year coach, Jan-Mar (fade)")   # sports.weigh_ncaab_new_coach_fav):
            #   -11.4% on 762 at the close 2018-25 (7 of 8 seasons down, the open -9.1%) vs -3.5%; judge at 50: the faded
            #   favorites at or above -3.5% = the weight comes off
        if c.get("ncaab_to_fav"):                            # 11/3 KNOWLEDGE (A) study 4 (BUILT as a -2 weight,
            t.append("college hoops small fav, turnover-prone (fade)")   # sports.weigh_ncaab_to_fav): -9.7% on 1,314
            #   2021-25 (0 of 2 train / 0 of 3 held out up, the open -7.2%) vs -4.2%; judge at 50 the same way
        if lg == "ncaab" and -150 <= c.get("odds", 0) <= -101 and hoops_rust(c):
            t.append("college hoops small fav off 7+ days vs a team in rhythm (fade)")   # 10/31 daily study 10: -17.9%
            #   on 167 train (2018-21, 1 of 4 up) / -12.3% on 243 held out (2022-25, 3 of 4 down) outside December vs
            #   -3.8% for every band favorite; ATS the same side -7.2% / -7.5% (Dec) vs -4.5%; but the December exam
            #   window itself +5.1% train, 10+ days no worse than 7+ - a LEAD, tracked only
        if lg == "nhl" and -150 <= c.get("odds", 0) <= -101 and c.get("absent"):
            t.append("NHL small fav, a top scorer out (fade)")   # 10/31 daily study 8: a -101..-150 favorite whose
            #   top-2 scorer (this season's points a game) missed the last game and is out again: -11.4% on 446 vs
            #   -3.2% for the band (train 2021-22 -3.7% vs -0.8%, held out 2023-25 -15.6%, 3 of 3 down) - the BUILT
            #   hockey absence penalty (top scorer -6 / top-2 -4 off the own read) is the right size; this is its live
            #   record, never a second weight
        if lg == "nba" and -150 <= c.get("odds", 0) <= -101 and nba_star40(c):
            t.append("NBA small fav, its top scorer just had 40+ (fade)")   # 11/2 daily study 4: the -101..-150
            #   favorite the game after its top scorer put up 40+: -15.5% on 104 train (2016-22, 1 of 5 up) / -12.0% on 64
            #   held out (2024 +15.5%), the 2020-23 morning price -17.3% on 70, vs -4.5% for the band; ATS -7.1% vs -4.2%;
            #   the -151..-300 favorite and the dogs at their base, z -2.0 - a LEAD, tracked only, never a weight
        if lg == "nba" and -150 <= c.get("odds", 0) <= -100 and halftime_comeback(c):
            t.append("NBA small fav off a 10+ halftime comeback win")   # 10/27 daily study: train +31.8% on 68
            #   (6 of 7 up, 8+ / 12+ the same sign) but holdout 2025 3-6 -42% and the NHL version flat - tracked only
        if lg == "nfl" and c.get("odds", 0) <= -151 and shootout_win(mo):
            t.append("NFL big fav off a 30-30 shootout win")         # 10/26 daily study: -151..-400 favorites that
            #   won a game both teams scored 30+ in: +20.2% on 62 (train 7 of 7 up, 2025 -11% on 8, early price +17%);
            #   college 35+ the same sign (+8.8% on 78) but not at 31+ / 42+; the bettable -101..-150 band doesn't
            #   hold - tracked only, never a weight
    gi = c.get("games_in") if lg == "ncaab" else None    # 🏀 11/3 college hoops (A) - results/studies/cbb_1103_a/
    if gi is not None:
        if sports.ncaab_early_road_dog(c):
            t.append("college hoops road dog, games 1-3 (fade)")   # s7 - BUILT as a -2 dog-score weight; its live
            #   record (ML -20.0% on 581, open -26.1%, ATS -16.4%, held 3 of 3 down)
        if 100 <= c.get("odds", 0) <= 150 and gi + 1 <= 2:
            t.append("college hoops short dog +100..+150, games 1-2")   # s0 / s0b: opening week +14.6% on 273 (train
            #   +12.2% 3/5 up, held +21.0% 3/3 up) - but the sides that OPENED there +0.4% (the second check fails),
            #   +151..+200 next door -19.4%, ~50 cells (2-3 at |z| 2 by luck). A LEAD - games 1-2 stand in for the week
        if -150 <= c.get("odds", 0) <= -120 and gi + 1 <= 2:
            t.append("college hoops Lock-band fav -120..-150, games 1-2 (fade)")   # s6: days 0-7 -12.9% on 156
            #   (train 1/5 up, held -20.2% 3/3 down), days 8-14 +5.7% - the open 10/16 Lock question; tracked only
        if (c.get("drift") or 0) <= -0.08 and gi + 1 <= 6:
            t.append("college hoops side the line jumped 8+ to, games 1-6 (fade)")   # s2: following an 8+ point
            #   open->close move in the first 3 weeks -23.3% at the close on 104 (2023 / 2024 down, 2025 +3.8%) vs
            #   -8.1% later; fading it +17.6% - 3 seasons of opens only, a LEAD
    # 11/3 DAILY STUDIES (results/studies/daily_1103/): one WEIGHT's live record + four moneyline LEADS (tracked only)
    if dog and lg == "nba" and c.get("odds", 0) <= 350 and c.get("lost_man"):
        t.append("NBA dog that lost a 20+ minute man in its last 10 games (fade)")   # s7 / s7b - BUILT as a -2 dog-score
        #   weight (sports.NBA_LOST_MAN_PTS): the dog in games 4-10 after a rotation man left -19.7% on 284 (0 of 5 train
        #   up, 3 of 3 held down, the morning -16.5%); judge at 50 - the flagged dogs winning at the price = it comes off
    if dog and lg == "nba" and c.get("odds", 0) <= 350 and nba_lucky(c):
        t.append("NBA lucky dog (record 15+ pts over its margin), games 6-20 (fade)")   # s8: the early-season sample-size
        #   trap - a dog whose win % sits 0.15+ over its Pythagorean (exponent 14) in games 6-20 -31.9% on 77 (train
        #   -20.8%, 1 of 5 up; held out -100% / -69% / -38% / 2026 +19% on 4; the paid morning -44.0% on 28, 0 of 3), the
        #   same team as a favorite -17.5% on 50, ATS -22.3% held; but 77 bets and ~45 cells looked at - a LEAD only
    if dog and lg == "nba" and c.get("odds", 0) <= 350 and nba_beat_here(c):
        t.append("NBA dog that already beat this team on this floor this season (fade)")   # s9: the 2nd meeting 4+ days
        #   on, the dog that won the 1st meeting at the same venue -21.8% on 144 (train -29.1%, 0 of 5 up; held out
        #   -3.4% / -11.2% / -13.0%; the morning -48.0% on 40, 0 of 3) - "they already beat them here" is in the price
        #   and then some; 144 bets, ~45 cells - a LEAD only
    if lg == "nhl" and nhl_top_missed(c):                     # s6 / s6b: the NHL top scorer (points over the team's last
        if dog and c.get("odds", 0) <= 350:                   #   10 before its last game) MISSED THE LAST GAME - the side
            t.append("NHL dog, top scorer missed its last game (fade)")   #   -17.8% on 337 (train -21.4% 0 of 3 up, held
        elif -200 <= c.get("odds", 0) <= -101:                #   -18.1% / -6.4%), the dog -32.2% on 163 (morning -63%),
            t.append("NHL fav -101..-200, top scorer missed its last game (fade)")   #   and BACK tonight still -20.9%
        #   on 110 (fav -20.1% on 49) - the part the built report penalty (sports_absences, -6 when he's OUT) can't see;
        #   out again tonight = that penalty's cell (dog -34.7%). Tracked next to it, never a second weight yet
    # 11/4 DAILY STUDIES (results/studies/daily_1104/): one WEIGHT's live record + two moneyline LEADS (tracked only)
    if dog and lg == "ncaaf" and c.get("odds", 0) <= 350 and c.get("int_unlucky"):
        t.append("college football dog, interception-unlucky (-0.5 a game or worse)")   # s1 / s1b - BUILT as a +2
        #   dog-score weight (sports.NCAAF_INT_LUCK_PTS): the college dog whose season INT margin runs -0.5 a game or
        #   worse +20.4% on 277 (3 of 3 train up, held 2024 / 2025 / 2026 up, the first fair +25.1%); judge at 50 -
        #   the flagged dogs losing at the price = the weight comes off
    if dog and lg == "nhl" and c.get("odds", 0) <= 350 and nhl_vs_new_city_b2b(c):
        t.append("NHL dog vs a favorite on a road-road back-to-back in a new city")   # s6: the shape of the b2b - the
        #   rested dog across a favorite that played on the road last night and flew to a NEW city for tonight +12.5%
        #   on 182 (train +6.9% 3 of 4 up, held 2022-25 4 of 4 up) vs +3.4% for every rested dog vs a b2b; the b2b
        #   side itself -20.9% as a dog (0 of 4 up). A dose of the built rested_vs_b2b +3 - a LEAD, judge at 50
    if dog and lg == "nba" and c.get("odds", 0) <= 350 and nba_star_third_back(c):
        t.append("NBA dog, top scorer's 3rd game back (fade)")   # s8: the NBA top scorer (season points a game) who
        #   missed 2+ straight and has played 2 since - the dog in his 3rd game back -35.8% on 107 (train -35.6%, 4 of
        #   5 down; held +6.3% / -56.3% / -43.1%; the paid morning -12.3% on 49), the side ML any -17.0% on 334; his
        #   2nd game back (the college hoops weight's cell) is nothing here (+4.8%). ~100 cells looked at - a LEAD only
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


def ncaab_newlook_dog(c):
    """11/3 DEEP study 5 (a LEAD, tracked only): a college hoops side in its games 6-10 whose transfer strength
    (sports_ncaab_roster.tin_m - last season's points by its D1 transfers x their old teams' margins) is 0.03+."""
    if c.get("league") != "ncaab":
        return False
    n = c.get("games_in")
    if n is None:
        n = c.get("season_games")
    if n is None or not 6 <= n + 1 <= 10:
        return False
    g = _game(c)
    team = g.get(c.get("side") or "")
    if not team or len(str(g.get("start") or "")) < 10:
        return False
    try:
        import sports_ncaab_roster as nr
        v = nr.tin_m(_GAMES.get("ncaab") or {}, team, g["start"])
    except Exception:                                        # noqa: BLE001
        return False
    return v is not None and v >= nr.TIN_M_CUT


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
    """The tracker tags for a rating-backed college gap dog (raw own read 15+ over the no-vig market, Elo for the dog).
    College hoops (11/4 DOG EXPERT): the efficiency read 15+ over, the ratings backing the dog, no study fade, both
    teams 4+ games - the 🔍 play's own bands for its 50-play judge."""
    if c.get("league") == "ncaab":
        if not 100 <= (c.get("odds") or 0) <= 350 or c.get("eff_p") is None or c.get("p_market") is None:
            return []
        if c["eff_p"] <= 0.5 or min(c.get("games_in") or 0, c.get("opp_games_in") or 0) < 4:
            return []
        gap = c["eff_p"] - c["p_market"]
        if gap < GAP_WATCH[0]:
            return []
        try:
            import sports
            if round(sports.dog_spots(c), 2) < 0:
                return []
        except Exception:                                    # noqa: BLE001
            return []
        return ["college hoops gap dog 15-20" if gap < GAP_WATCH[1] else "college hoops gap dog 20+"]
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


def _month(c):
    """The game's month in the US evening clock ('01'..'12'), '' when the start is missing."""
    try:
        from datetime import datetime, timedelta
        return (datetime.fromisoformat(str(c.get("start") or "").replace("Z", "+00:00")) - timedelta(hours=5)).strftime("%m")
    except ValueError:
        return ""


def _night(start):
    """A US 'night' index for a start time (UTC - 5h, whole days) - the study's day count."""
    from datetime import datetime
    t = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
    return int((t.timestamp() - 5 * 3600) // 86400)


def nhl_four_in_six(c):
    """Tonight is this team's 4th game in 6 nights and NOT the 2nd night of a back-to-back (the b2b has its own weight) -
    the 10/30 hockey schedule-density study. Finals this season only."""
    team, rows = _season_before(c)
    if not team or not rows:
        return False
    try:
        now = _night(c.get("start") or _game(c).get("start"))
        prev = [now - _night(x["start"]) for x in rows]
    except (TypeError, ValueError):
        return False
    return 1 + sum(1 for d in prev if 1 <= d <= 5) >= 4 and 1 not in prev


def hoops_early_away(c):
    """A college hoops side away from home (road or neutral site) in its first 3 games this season - 10/30 study 10."""
    team, rows = _season_before(c)
    if not team:
        return False
    g = _game(c)
    home_court = c.get("side") == "home" and str(g.get("neutral")) != "1"
    return not home_court and len(rows) <= 2


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


BOWL_WINDOW = ("10-20", "11-30")   # the 10/31 bowl-chase study's late-season window (month-day, the start's date)


def bowl_need1(c):
    """10/31 daily study 3 (a LEAD, tracked only): a college team sitting on exactly 5 wins - one short of bowl
    eligibility - late in the season, both teams FBS. Wins = every finished game this season on file (FCS wins count
    toward 6, as they do for eligibility)."""
    if c.get("league") != "ncaaf" or c.get("fbs_game") is not True:
        return False
    start = str(c.get("start") or _game(c).get("start") or "")
    if len(start) < 10 or not (BOWL_WINDOW[0] <= start[5:10] <= BOWL_WINDOW[1]):
        return False
    team, rows = _season_before(c)
    if not team or not rows:
        return False
    w = 0
    for x in rows:
        me, op = ("home", "away") if x["home"] == team else ("away", "home")
        try:
            w += float(x[me + "_score"]) > float(x[op + "_score"])
        except (TypeError, ValueError):
            return False
    return w == 5


HOOPS_RUST_DAYS, HOOPS_RHYTHM_DAYS = 7, 4   # the 10/31 layoff study's cuts


def hoops_rust(c):
    """10/31 daily study 10 (college hoops prep; a LEAD, tracked only): this side's last game was 7+ nights ago and
    the opponent played within the last 4 nights - both teams 3+ games into the season."""
    if c.get("league") != "ncaab":
        return False
    team, rows = _season_before(c)
    other = "away" if c.get("side") == "home" else "home"
    oteam, orows = _season_before(dict(c, side=other))
    if not team or not oteam or len(rows) < 3 or len(orows) < 3:
        return False
    try:
        now = _night(c.get("start") or _game(c).get("start"))
        gap, ogap = now - _night(rows[-1]["start"]), now - _night(orows[-1]["start"])
    except (TypeError, ValueError):
        return False
    return gap >= HOOPS_RUST_DAYS and ogap <= HOOPS_RHYTHM_DAYS


MKT_BACKED_LEAGUES = ("nhl",)       # 11/2 NBA odds-history study 2 (results/studies/nba_odds_1102/s2): the market-BACKED mirror
#   lead is CUT for the NBA - on 2020-22 (the paid odds history, morning -> close moves) NBA dogs the market backed 8+ in
#   their last 3 went 108-207 -10.5% at the close (0 of 3 seasons up; 2023-25 had +5.1%) - noise. NHL keeps tracking it
#   (the tag's name stays the same so its record carries on).


HOOPS_BLOWOUT_LOSS = 15             # the 11/1 study's cut: lost yesterday by 15+
HOOPS_BLOWOUT_ODDS = (-400, 350)    # the moneyline range the study graded
HOOPS_BLOWOUT_MONTHS = ("11", "12")  # the study's window: the November / December tournament back-to-backs


def hoops_blowout_b2b(c):
    """11/1 daily study 9 (college hoops prep; a LEAD, tracked only): this side played LAST NIGHT (the night before
    tonight's game - the early-season tournament back-to-back) and lost that game by 15+. Finals this season only."""
    if c.get("league") != "ncaab":
        return False
    start = str(c.get("start") or _game(c).get("start") or "")
    if start[5:7] not in HOOPS_BLOWOUT_MONTHS:
        return False
    team, rows = _season_before(c)
    if not team or not rows:
        return False
    x = rows[-1]
    try:
        if _night(c.get("start") or _game(c).get("start")) - _night(x["start"]) != 1:
            return False
        me, op = ("home", "away") if x["home"] == team else ("away", "home")
        return float(x[op + "_score"]) - float(x[me + "_score"]) >= HOOPS_BLOWOUT_LOSS
    except (TypeError, ValueError, KeyError):
        return False


def _key(day, gid, side, market):
    """One tracker row per game side per day - a spread side keeps its own row next to the moneyline one."""
    return (day, gid, side) + (("spread",) if market == "spread" else ())


def spread_tags(c, sports):
    """The spread leads (graded against the line): 11/2 daily study 1 - the NBA early-season spread favorite, BUILT as a
    -0.03 rank weight (sports.early_spread_w); its live cover record here (judge at 50: covering 52%+ = it comes off)."""
    t = []
    if sports.nba_early_spread_fav(c):
        t.append("NBA spread fav 3.5-12.5, games 1-20 (fade)")
    # 11/3 FABLE - COLLEGE HOOPS KNOWLEDGE (A): the Feb-Mar roster weights' cover records (sports.ncaab_roster_spread_w)
    # and the first-year coach's late-season spread side (a LEAD: ATS -8.4% on 3,509 from game 21, 1 of 5 / 0 of 3 up)
    if c.get("league") == "ncaab" and _month(c) in sports.NCAAB_ROSTER_MONTHS:
        w = sports.ncaab_roster_spread_w(c)
        if w < 0:
            t.append("college hoops transfer-heavy spread side, Feb-Mar (fade)")
        elif w > 0:
            t.append("college hoops freshman-heavy side vs an experienced team, Feb-Mar")
    if c.get("league") == "ncaab" and c.get("ncaab_new_coach") and (c.get("games_in") or 0) >= 21:
        t.append("college hoops spread side, first-year coach, games 21+ (fade)")
    if c.get("league") == "ncaab" and c.get("top_out"):
        t.append("college hoops spread side, top scorer missed its last game (fade)")   # 11/3 DEEP (BUILT as a -0.03
        #   rank weight, sports.ncaab_top_out_spread_w): ATS -10.8% on 1,521 vs -4.4% (0 of 4 seasons at the base)
    # 11/3 FABLE - COLLEGE HOOPS SECOND OPINION (BUILT as rank weights, sports.ncaab_fable_spread_w): the live cover
    # records of the three spread weights (judge at 50 each: the faded side covering 52%+ = its weight comes off), plus
    # one tracker-only LEAD (the public name on Saturday - a hand-picked list, never a weight)
    if c.get("league") == "ncaab" and c.get("ranked_road"):
        t.append("college hoops top-25 team on the road, Nov-Dec (fade)")   # ATS -19.4% on 329 (7 of 8 seasons down)
    if c.get("league") == "ncaab" and c.get("vs_ranked_road"):
        t.append("college hoops home side vs a top-25 road team, Nov-Dec")   # ATS +10.3% on 329 (3 of 5 / 2 of 3)
    if c.get("league") == "ncaab" and (c.get("ats_gap") or 0) >= sports.NCAAB_ATS_GAP:
        t.append("college hoops hot-ATS side, gap 3+ (fade)")   # ATS -7.4% on 7,258 (0 of 5 / 0 of 3 up, z -6.6)
    if c.get("league") == "ncaab" and c.get("reb_gap") is not None and c["reb_gap"] <= -sports.NCAAB_REB_GAP:
        t.append("college hoops spread side out-rebounded by 6+ a game (fade)")   # the favorite ATS -10.8% on 1,009 (5 of 5)
    if c.get("league") == "ncaab" and public_saturday(c):
        t.append("college hoops public name on a Saturday (fade)")   # ATS -7.6% on 2,046 (0 of 5 / 0 of 3; at home
        #   -9.6%), the side across +0.2% - a hand-picked list of 30 names, a LEAD only (never a weight)
    if hoops_rested_vs_two(c):
        t.append("college hoops spread side on 4-5 nights rest vs a team on 2 (fade)")   # 11/3 college hoops (B) study 1
        #   (s6_followups.py c): home / road games, the side rested 4-5 nights vs a team that played 2 nights ago (the
        #   Thursday-Saturday team) ATS -14.5% on 717 (train -13.5%, 0 of 5 up; held out -16.6%, 0 of 3) - but the dose is
        #   ragged (rested 3 -7.7%, 6+ -3.8%), the moneyline doesn't carry it (the rested favorite -9.6% then +3.0% held
        #   out) and there are no spread opens for a 2nd check: a LEAD, tracked only, never a weight
    # 11/3 DAILY STUDIES (results/studies/daily_1103/): one spread WEIGHT's live record + two spread LEADS (tracked only)
    if c.get("league") == "nba" and c.get("lost_man"):
        t.append("NBA spread side that lost a 20+ minute man in its last 10 games (fade)")   # s7 - BUILT as a -0.03
        #   rank weight (sports.nba_lost_man_spread_w): ATS -12.3% on 556 (games 1-3) / -11.4% on 721 (4-10) vs -4.4%
    if nfl_first_cold(c):
        t.append("NFL side in its first sub-40F game vs a team that already had one (fade)")   # s3: ATS -36.4% on 69
        #   (train -36.3% on 48, 1 of 5 up; held out 0-5 / -36.6% on 9 / +8.4% on 7), the side across +27.3% (4 of 5 train
        #   up) - the game file's temperature (a forecast before kickoff), 69 games in ten seasons, ~45 cells: a LEAD only
    if hoops_host_home_from_neutral(c):
        t.append("college hoops host in its first game back from 3+ neutral games (fade)")   # s10: the home team just
        #   back (within 10 days) from 3+ straight neutral-site games (the November / December tournament trip) ATS
        #   -11.2% on 256 (train -20.5%, 0 of 4 up; held out -11.5% / -2.3% / -16.0% / +15.8%), the road side across
        #   +2.2% (train +11.2%, 4 of 4 up) - the dog across isn't up on the moneyline; a LEAD only
    return t


PUBLIC_NAMES = {"Duke", "Kentucky", "Kansas", "North Carolina", "UCLA", "Michigan St", "Indiana", "Syracuse", "Gonzaga",
                "Arizona", "Louisville", "Villanova", "UConn", "Michigan", "Ohio St", "Purdue", "Alabama", "Auburn",
                "Tennessee", "Houston", "Baylor", "Texas", "Florida", "LSU", "Memphis", "Georgetown", "Marquette",
                "Illinois", "Iowa St", "Creighton"}   # 11/3 FABLE study 5: the 30 public names (a hand-picked list)


def public_saturday(c):
    """A college hoops spread side that is one of PUBLIC_NAMES playing on a Saturday (ET night) - a LEAD, tracked only."""
    if c.get("league") != "ncaab":
        return False
    g = _game(c)
    name = g.get(f"{c.get('side')}_name") or c.get("team") or ""
    if name not in PUBLIC_NAMES:
        return False
    try:
        return (_night(c.get("start") or g.get("start")) + 3) % 7 == 5
    except (TypeError, ValueError):
        return False


HOOPS_SLIGHT_BAND = (-150, -101)   # 11/3 FABLE college hoops knowledge (B): the owner's 'slight favorite' band
HOOPS_GLASS_FAV = 4.0              # s3: the home slight favorite out-rebounding the dog by 4+ a game (sports.mark_ncaab_reb)
HOOPS_EFF_AGREE = 0.03             # ...with the efficiency read (sports_cbb_eff, c['eff_p']) 3+ points OVER the no-vig price


def hoops_march_home_fav(c):
    """A college hoops moneyline favorite on its own floor (not neutral) in March, by the US night - a LEAD, tracked only."""
    if c.get("league") != "ncaab" or c.get("market", "ml") != "ml" or c.get("side") != "home":
        return False
    g = _game(c)
    if str(g.get("neutral")) == "1":
        return False
    start = str(g.get("start") or c.get("start") or "")
    try:
        from datetime import datetime, timedelta
        return (datetime.fromisoformat(start.replace("Z", "+00:00")) - timedelta(hours=5)).strftime("%m") == "03"
    except ValueError:
        return False


def hoops_glass_eff_fav(c):
    """A college hoops home (not neutral) moneyline favorite whose season rebound margin beats the dog's by
    HOOPS_GLASS_FAV+ a game (c['reb_gap'], both teams 5+ box games) with the efficiency read HOOPS_EFF_AGREE+ over the
    no-vig price (c['eff_p'] - c['p_market']) - a LEAD, tracked only."""
    if c.get("league") != "ncaab" or c.get("market", "ml") != "ml" or c.get("side") != "home":
        return False
    if str(_game(c).get("neutral")) == "1":
        return False
    rg, ep, pm = c.get("reb_gap"), c.get("eff_p"), c.get("p_market")
    return rg is not None and ep is not None and pm is not None and rg >= HOOPS_GLASS_FAV and ep - pm >= HOOPS_EFF_AGREE


HOOPS_RESTED = (4, 5)        # 11/3 college hoops (B) study 1: this side's nights since its last game
HOOPS_TIRED_NIGHTS = 2       # ...vs an opponent that played exactly 2 nights ago


def hoops_rested_vs_two(c):
    """A college hoops side at home / on the road (not a neutral site) whose last game was 4-5 nights ago, vs an opponent
    whose last game was exactly 2 nights ago - this season's finals only."""
    if c.get("league") != "ncaab":
        return False
    g = _game(c)
    if str(g.get("neutral")) == "1":
        return False
    team, rows = _season_before(c)
    oteam, orows = _season_before(dict(c, side="away" if c.get("side") == "home" else "home"))
    if not team or not oteam or not rows or not orows:
        return False
    try:
        now = _night(c.get("start") or g.get("start"))
        return HOOPS_RESTED[0] <= now - _night(rows[-1]["start"]) <= HOOPS_RESTED[1] \
            and now - _night(orows[-1]["start"]) == HOOPS_TIRED_NIGHTS
    except (TypeError, ValueError):
        return False


NHL_FEB_HOME_ODDS = (-250, 350)     # 11/2 daily study 5: the bands graded (home favorites to -250, home dogs to +350)
NBA_STAR_PTS = 40                   # 11/2 daily study 4: the top scorer's points last game
NBA_REST_STACK_NIGHTS = 3           # 11/2 daily study 3: last game 3+ nights ago = 2+ days off


def nhl_feb_home(c):
    """11/2 daily study 5 (a LEAD, tracked only): the home side (not a neutral site) of an NHL game in February."""
    if c.get("league") != "nhl" or c.get("side") != "home":
        return False
    g = _game(c)
    start = str(c.get("start") or g.get("start") or "")
    return start[5:7] == "02" and str(g.get("neutral")) != "1"


def nba_rest_stack(c):
    """11/2 daily study 3 (a LEAD, tracked only): this NBA side's last game was 3+ nights ago (2+ days off) and the
    opponent played LAST NIGHT (the 2nd night of its back-to-back) - this season's finals only."""
    if c.get("league") != "nba":
        return False
    team, rows = _season_before(c)
    oteam, orows = _season_before(dict(c, side="away" if c.get("side") == "home" else "home"))
    if not team or not oteam or not rows or not orows:
        return False
    try:
        now = _night(c.get("start") or _game(c).get("start"))
        return now - _night(rows[-1]["start"]) >= NBA_REST_STACK_NIGHTS and now - _night(orows[-1]["start"]) == 1
    except (TypeError, ValueError):
        return False


def nba_fast_dog(c):
    """11/3 FABLE NBA deep dive (a LEAD, tracked only - never a weight): an NBA moneyline dog +100..+350 that plays
    sports.NBA_PACE_GAP+ possessions a game faster than the favorite over the last 10 (dog_more pace / opp_pace from
    sports_nba_roster.pace_last). -9.0% at the close on 970 but flat in train (2 of 5 up) - the favorite's side is the
    weight; this one is judged live."""
    import sports
    mo = c.get("dog_more") or {}
    if c.get("league") != "nba" or c.get("market") != "ml" or not (100 <= c.get("odds", 0) <= 350):
        return False
    return mo.get("pace") is not None and mo.get("opp_pace") is not None and mo["pace"] - mo["opp_pace"] >= sports.NBA_PACE_GAP


def nba_star40(c):
    """11/2 daily study 4 (a LEAD, tracked only): this NBA side's top scorer had 40+ points in its last game (this
    season, within the last 4 nights) - from the saved box scores (sports_absences._games)."""
    if c.get("league") != "nba":
        return False
    team, rows = _season_before(c)
    if not team or not rows:
        return False
    x = rows[-1]
    try:
        if _night(c.get("start") or _game(c).get("start")) - _night(x["start"]) > 4:
            return False
        import sports_absences
        box = next((rs for s_, gid, rs in sports_absences._games("nba").get(str(team), []) if gid == x["id"]), None)
    except Exception:                                        # noqa: BLE001
        return False
    if not box:
        return False
    best = 0.0
    for r in box:
        try:
            best = max(best, float(json.loads(r.get("stats") or "{}").get("points") or 0))
        except (TypeError, ValueError):
            continue
    return best >= NBA_STAR_PTS


# ---------------- 11/3 daily studies: the lead helpers ----------------
NBA_LUCK_EXP = 14.0          # s8: the NBA Pythagorean exponent
NBA_LUCK_GAP = 0.15          # s8: win % 0.15+ over the margin-implied win %...
NBA_LUCK_GAMES = (6, 20)     # s8: ...in the team's games 6-20 (5-19 finals before tonight)
NBA_BEAT_HERE_DAYS = 4       # s9: the 2nd meeting 4+ days after the first (the quick rematch died twice, 10/28)
NHL_TOP_WINDOW = 10          # s6: the top scorer = points over the team's 10 games before its last game...
NHL_TOP_MIN_GAMES = 6        # s6: ...the team 6+ box games in, and he played 3 of the 4 before the one he missed
NFL_COLD_F = 40              # s3: a sub-40F outdoor game (the game file's wx_temp - a forecast before kickoff)
HOOPS_NEUTRAL_RUN = 3        # s10: 3+ straight neutral-site games, the first game back within 10 days
HOOPS_HOME_WITHIN = 10
_NHL_BOX = {}                # season -> {team: [(start, gid, {pid: points})]} from this season's NHL box scores


def nba_lucky(c):
    """11/3 daily study 8 (a LEAD, tracked only): this NBA side's win % this season sits NBA_LUCK_GAP+ over its
    Pythagorean expectation in its games 6-20 - the early-season record the margin doesn't back."""
    if c.get("league") != "nba":
        return False
    team, rows = _season_before(c)
    n = len(rows)
    if not team or not (NBA_LUCK_GAMES[0] <= n + 1 <= NBA_LUCK_GAMES[1]):
        return False
    try:
        pf = sum(float(x["home_score"] if x["home"] == team else x["away_score"]) for x in rows)
        pa = sum(float(x["away_score"] if x["home"] == team else x["home_score"]) for x in rows)
        w = sum(1 for x in rows if (float(x["home_score"]) > float(x["away_score"])) == (x["home"] == team)) / n
    except (TypeError, ValueError, KeyError):
        return False
    if not pf or not pa:
        return False
    exp = pf ** NBA_LUCK_EXP / (pf ** NBA_LUCK_EXP + pa ** NBA_LUCK_EXP)
    return w - exp >= NBA_LUCK_GAP


def nba_beat_here(c):
    """11/3 daily study 9 (a LEAD, tracked only): tonight is the 2nd meeting of the season (4+ days after the 1st) and
    this side WON the 1st at the same venue (home then and now, or away then and now) - this season's finals only."""
    if c.get("league") != "nba":
        return False
    g = _game(c)
    team, rows = _season_before(c)
    opp = g.get("away" if c.get("side") == "home" else "home")
    if not team or not opp:
        return False
    met = [x for x in rows if opp in (x["home"], x["away"])]
    if len(met) != 1:
        return False
    first = met[0]
    try:
        if _night(c.get("start") or g.get("start")) - _night(first["start"]) < NBA_BEAT_HERE_DAYS:
            return False
        won = (float(first["home_score"]) > float(first["away_score"])) == (first["home"] == team)
    except (TypeError, ValueError, KeyError):
        return False
    return won and (first["home"] == team) == (c.get("side") == "home")


def _nhl_box(season):
    """{team id: [(start, gid, {pid: points})]} for this NHL season's saved box scores (skaters only), oldest first."""
    if season not in _NHL_BOX:
        _NHL_BOX.clear()
        by = {}
        try:
            import sports_roster as sr
            rows = sr.load("nhl", seasons=[season])
        except Exception:                                    # noqa: BLE001
            rows = []
        for r in rows:
            if r.get("group") == "goalies":
                continue
            try:
                st = json.loads(r.get("stats") or "{}")
                pts = float(st.get("goals") or 0) + float(st.get("assists") or 0)
            except (ValueError, TypeError):
                pts = 0.0
            by.setdefault(r["team"], {}).setdefault(r["gid"], (r["start"], {}))[1][r["pid"]] = pts
        _NHL_BOX[season] = {t: sorted((s, gid, p) for gid, (s, p) in d.items()) for t, d in by.items()}
    return _NHL_BOX[season]


def nhl_top_missed(c, box=None):
    """11/3 daily study 6 / 6b (a LEAD, tracked only): this NHL side's top scorer (points over its NHL_TOP_WINDOW games
    before its last game, the team NHL_TOP_MIN_GAMES+ box games in) was NOT in the box of the team's last game after
    playing 3 of the 4 before it. No box scores = False, never a guess."""
    if c.get("league") != "nhl":
        return False
    g = _game(c)
    team, start = g.get(c.get("side") or ""), str(c.get("start") or g.get("start") or "")
    if not team or len(start) < 7:
        return False
    y, m = int(start[:4]), int(start[5:7])
    season = y if m >= 7 else y - 1
    rows = [x for x in (box if box is not None else _nhl_box(season)).get(str(team), []) if x[0] < start]
    if len(rows) < NHL_TOP_MIN_GAMES:
        return False
    last, window = rows[-1], rows[-(NHL_TOP_WINDOW + 1):-1]
    pts = {}
    for _, _, p in window:
        for pid, v in p.items():
            pts[pid] = pts.get(pid, 0.0) + v
    if not pts or not last[2]:
        return False
    top = max(pts, key=pts.get)
    played_before = sum(1 for _, _, p in window[-4:] if top in p)
    return top not in last[2] and played_before >= 3


NBA_STAR_MIN_GP = 5          # 11/4 s8: the top scorer = this season's points a game over 5+ games played
NBA_STAR_MISSED = 2          # ...who missed 2+ straight team games
NBA_STAR_NTH = 3             # ...and tonight is his 3rd game back (he played the team's last 2)
NHL_SAME_CITY_MI = 40        # 11/4 s6: a road-road back-to-back counts as a NEW city when last night's venue sits 40+ miles away
_NBA_BOX = {}                # season -> {team: [(start, gid, {pid: points})]} from this season's NBA box scores


def _nba_box(season):
    """{team id: [(start, gid, {pid: points})]} for this NBA season's saved box scores (men who played), oldest first."""
    if season not in _NBA_BOX:
        _NBA_BOX.clear()
        by = {}
        try:
            import sports_roster as sr
            rows = sr.load("nba", seasons=[season])
        except Exception:                                    # noqa: BLE001
            rows = []
        for r in rows:
            try:
                st = json.loads(r.get("stats") or "{}")
                mins, pts = float(st.get("minutes") or 0), float(st.get("points") or 0)
            except (ValueError, TypeError):
                continue
            if mins <= 0:
                continue
            by.setdefault(r["team"], {}).setdefault(r["gid"], (r["start"], {}))[1][r["pid"]] = pts
        _NBA_BOX[season] = {t: sorted((s, gid, p) for gid, (s, p) in d.items()) for t, d in by.items()}
    return _NBA_BOX[season]


def nba_star_third_back(c, box=None):
    """11/4 daily study 8 (a LEAD, tracked only): this NBA side's top scorer (this season's points a game, NBA_STAR_MIN_GP+
    played) missed NBA_STAR_MISSED+ straight team games and has played exactly NBA_STAR_NTH - 1 since - tonight is his
    NBA_STAR_NTH-th game back, known from the last box before tip. No box scores = False, never a guess."""
    if c.get("league") != "nba":
        return False
    g = _game(c)
    team, start = g.get(c.get("side") or ""), str(c.get("start") or g.get("start") or "")
    if not team or len(start) < 7:
        return False
    y, m = int(start[:4]), int(start[5:7])
    season = y if m >= 7 else y - 1
    rows = [x for x in (box if box is not None else _nba_box(season)).get(str(team), []) if x[0] < start]
    if len(rows) < NBA_STAR_MIN_GP + NBA_STAR_MISSED:
        return False
    tot, gp = {}, {}
    for _, _, p in rows:
        for pid, v in p.items():
            tot[pid] = tot.get(pid, 0.0) + v
            gp[pid] = gp.get(pid, 0) + 1
    cands = [(tot[p] / gp[p], p) for p in tot if gp[p] >= NBA_STAR_MIN_GP]
    if not cands:
        return False
    star = max(cands)[1]
    played = [star in p for _, _, p in rows]
    i, n = len(played) - 1, 0
    while i >= 0 and played[i]:
        n += 1
        i -= 1
    missed = 0
    while i >= 0 and not played[i]:
        missed += 1
        i -= 1
    return n == NBA_STAR_NTH - 1 and missed >= NBA_STAR_MISSED


def nhl_vs_new_city_b2b(c):
    """11/4 daily study 6 (a LEAD, tracked only): this NHL side is at HOME and did not play last night, while the opponent
    played last night ON THE ROAD somewhere else (its last final was away, one night ago, NHL_SAME_CITY_MI+ miles from
    tonight's rink by the game file's city) - the road-road back-to-back in a new city."""
    if c.get("league") != "nhl" or c.get("side") != "home":
        return False
    g = _game(c)
    if str(g.get("neutral")) == "1":
        return False
    other = "away"
    _, mine = _season_before(c)
    opp, rows = _season_before(dict(c, side=other))
    if not opp or not rows:
        return False
    last = rows[-1]
    try:
        tonight = _night(c.get("start") or g.get("start"))
        if mine and tonight - _night(mine[-1]["start"]) < 2:
            return False                                     # we played last night too: not the rested side
        if tonight - _night(last["start"]) != 1 or last.get("away") != opp:
            return False
    except (TypeError, ValueError):
        return False
    try:
        import sports_context as sc
        ven = sc.venues()
        a, b = sc._where(last, ven), sc._where(g, ven)
        if a and b:
            return sc.miles(a, b) >= NHL_SAME_CITY_MI
    except Exception:                                        # noqa: BLE001
        pass
    return (last.get("city") or "") != (g.get("city") or "")


def nfl_first_cold(c):
    """11/3 daily study 3 (a spread LEAD, tracked only): an outdoor NFL game under NFL_COLD_F (the game file's wx_temp)
    that is this side's FIRST sub-40F game of the season while the opponent has already played one. Finals this season
    only; a dome game counts as warm; no temperature on file = False."""
    if c.get("league") != "nfl" or c.get("market") != "spread":
        return False
    g = _game(c)
    try:
        if str(g.get("indoor")) == "1" or float(g.get("wx_temp")) >= NFL_COLD_F:
            return False
    except (TypeError, ValueError):
        return False

    def had_cold(side):
        _, rows = _season_before(dict(c, side=side))
        for x in rows:
            try:
                if str(x.get("indoor")) != "1" and float(x.get("wx_temp")) < NFL_COLD_F:
                    return True
            except (TypeError, ValueError):
                continue
        return False
    other = "away" if c.get("side") == "home" else "home"
    return (not had_cold(c.get("side"))) and had_cold(other)


def hoops_host_home_from_neutral(c):
    """11/3 daily study 10 (a spread LEAD, tracked only): the college hoops HOME side (not a neutral site) whose last
    HOOPS_NEUTRAL_RUN+ games were all at neutral sites, the last of them within HOOPS_HOME_WITHIN nights."""
    if c.get("league") != "ncaab" or c.get("market") != "spread" or c.get("side") != "home":
        return False
    g = _game(c)
    if str(g.get("neutral")) == "1":
        return False
    team, rows = _season_before(c)
    if not team or len(rows) < HOOPS_NEUTRAL_RUN:
        return False
    run = rows[-HOOPS_NEUTRAL_RUN:]
    if not all(str(x.get("neutral")) == "1" for x in run):
        return False
    try:
        return _night(c.get("start") or g.get("start")) - _night(run[-1]["start"]) <= HOOPS_HOME_WITHIN
    except (TypeError, ValueError):
        return False


def load():
    try:
        return json.load(open(PATH))
    except (OSError, ValueError):
        return []


DOG_MAX = 350               # 11/3 daily check: a lead row only COUNTS at a price the engine could ever play - a dog to
FAV_MIN = -150              # +350 (sports.DAILY_DOG_MAX, every dog study's band) and, on the three sharp-money tags (any
SHARP_TAGS = ("money 10+ over tickets", "70%+ of tickets", "reverse line move to it")   # side, no study band of their
#   own), a favorite no shorter than -150 (sports.MAX_FAV). Before this the tracker logged every side on the slate: East
#   Texas A&M +5000 won on opening night 11/2 and put +50u on "money 10+ over tickets" in one game (+1.6% on 269 ->
#   +17.8% on 311 - inside the band it is 115-142 +3.8%), and the +1000..+5000 opening-night road dogs made "college hoops
#   road dog, games 1-3 (fade)" 4-58 -45u on a study whose cell was +100..+350 (inside the band: 3-5). A record the owner
#   judges at 50 / 100 has to be the study's band, so log and grade skip the rest (the rows stay - never deleted).


def counts(tag, odds):
    """Does a lead row at this price count toward the tag's record (the engine's playable band)?"""
    o = odds if odds is not None else 100
    if o > DOG_MAX:
        return False
    return not (tag in SHARP_TAGS and o < FAV_MIN)


def log(day_iso, cands, sports):
    """Add today's firing leads (once per game side per day - the first look the board run took)."""
    rows = load()
    have = {_key(r["day"], r["game_id"], r["side"], r.get("market")) for r in rows}
    added = 0
    for c in cands:
        key = _key(day_iso, c.get("game_id"), c.get("side"), c.get("market"))
        if key in have:
            continue
        tg = [t for t in tags(c, sports) if counts(t, c.get("odds"))]   # (11/3: only at a price the engine could play)
        if not tg:
            continue
        row = {"day": day_iso, "game_id": c["game_id"], "league": c.get("league"), "side": c.get("side"),
               "team": c.get("team"), "odds": c.get("odds"), "tags": tg}
        if c.get("market") == "spread":                      # (11/2: a spread lead grades against its line)
            row.update(market="spread", line=c.get("line"))
        rows.append(row)
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
        if r.get("market") == "spread":
            try:
                m = (hs - as_ if r["side"] == "home" else as_ - hs) + float(r["line"])
            except (KeyError, TypeError, ValueError):
                continue
            if m == 0:
                continue                                     # a push grades nothing
            won = m > 0
        elif hs == as_:
            continue
        else:
            won = (hs > as_) == (r["side"] == "home")
        o = r.get("odds") or 100
        net = (o / 100 if o > 0 else 100 / -o) if won else -1.0
        for t in r["tags"]:
            if not counts(t, o):                             # (11/3: a +5000 row never counts - the study's band)
                continue
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
