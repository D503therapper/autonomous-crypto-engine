# What the studies found (9/30, the all-night session)

Every number below: the engine trained only on seasons BEFORE the ones it's graded on (no peeking), graded at real
prices. "Last 3" = 2023-26 alone (the owner: the sports have changed, old seasons can mislead). Built = in the engine.

**THE RULE BEFORE ANYTHING IS CALLED AN EDGE (the owner, 10/1 - three "breakthroughs" were taken back the same night,
every time because the result was reported before the leak checks).** Until ALL five pass it's a "LEAD", never an edge
or a breakthrough - and the report says which checks it passed: (1) FAIR PRICES - posted after both teams' last games
ended (early_football_study.fair), no look-ahead lines; (2) BLIND - each season graded by a model trained only on the
seasons before it, and no game-day facts (injury report, starters, weather) unless the bet waits for them; (3) MOST
SEASONS up, not one hot year; (4) THE CURRENT SEASON - games no model has seen; (5) A SECOND, INDEPENDENT CHECK of the
same idea (another cut, another sport, or our own line history). The owner, 10/1: "the sport changes every year -
going back so far isn't helping" - so (3) is judged on the LAST 3 SEASONS + this one; older seasons are only a
tiebreaker, never a reason to kill a lead on their own. (1) never bends - tonight's take-backs were leaks, not old data.

## 10/10 - COLLEGE FOOTBALL DOGS + how leans are picked (the owner: "a -150 college lean when the dog smacks"): college dogs are NOT beating the price this season, the 4+ gate is right, value-picked leans lose blind; college favorite leans at -150..-130 dropped
College-football-only board replay (tools/value_play_replay.Replay, 237 board days 2023-26, closing prices, blind params) + every ncaaf closing moneyline 2018-26. TRAIN 2023-24, TEST 2025-26.
- Every college dog +100..+220 at the close 2018-26: 40.3% won vs 40.4% needed, -0.4% (3 of 9 seasons up); 2023-26 -2.4%; THIS SEASON 44-80, -12.6%. The upsets are loud, not many (dogs won 19.9% of games this year vs 18-26% 2021-25). Home dogs -13.8% in 2025-26; conference road dogs -10.0% on 718.
- Dog gate: 2+ -9.5% blind on 128, 3+ -2.7% on 104, 4+ (today) -0.8% on 77 - loosening it loses. The 2..4 dog-score band is the worst (-22.6% blind). Only steady cell: 4+ at +100..+129.
- Leans: six value-picked lean rules all lost blind (-4.6% to -13.5%) vs who-wins (-7.1% same days). College favorite leans -150..-130: -6.6% / -24.1% (red both halves). BUILT 10/10 (the owner): who-wins leans, no college favorite lean at -150..-130 (sports.LEAN_NCAAF_FAV_BAND) - a lead on 29 blind leans, no units involved.

## 10/10 - COLLEGE HOOPS READINESS (the season opens ~11/3): the pipeline end to end on 2025-26, two bugs fixed, the injury picture, and a blind replay of every college hoops dog 2022-26 - today's dog rule lost blind, a dog-score gate ran flat, nothing cleared the five checks (the owner's call)
Checked on the real 2025-26 files the way the 8:35 AM post builds it (2026-01-15: 50 college hoops games, 30 priced, next to 10 NHL / 9 NBA): the model tunes (55,655 finals, the own read 72.8% right vs the market's 72.6% - trust 0.02, it leans on the line), candidates build (122 college hoops sides in 30 games), every hoops weight fires on real games (last result / the favorite lost its last, 2+ close wins, 'the stronger team', form, rest, the inside-scoring favorite, the coach file), the slate check lets the 19 unpriced small-school games through without a hold, the 'missing result' gap never fires (the 18 non-final 2025-26 games are all void), the dashboard renders the 🏀 College Basketball card. No crash. Exhibitions: ESPN marks them season type 1 - never a candidate (pinned, like the NBA).
- **BUG 1 (fixed, test_college_hoops_injury_feed_never_blind): a dead injury read = a BLIND college hoops pick with units.** ncaab was missing from sports_data.INJ_LEAGUES, so on a run where every hoops injury read failed (None) the engine posted a college hoops Lock at ½u (Oakland -148) and two leans with no injury data at all, while the NBA and NHL games waited on their reports. Now a dead hoops report holds hoops like every other sport. Second half of the fix: ESPN's college feed failing (it lists ~3 teams on a good day) no longer throws away Rotowire's report / the official reports - fetch_injuries returns None only when NO read came back.
- **BUG 2 (fixed, test_college_hoops_d1_team_passes_the_completeness_check): the completeness check (seen_all) wiped most of the college hoops board for the first month.** It judged a hoops team by the busiest teams' pace (80% of the 97th-percentile game count) - hoops schedules run 4-5 games apart by January (multi-team events), so on the real 2025-26 files it read 11 of 11 priced games on 11/4, 39 of 39 on 11/7, 23 of 23 on 11/12, 15 of 39 on 11/18, 17 of 18 on 11/22, 26 of 33 on 11/26, 25 of 47 on 12/3 and still 21 Division I teams on 1/15 (New Mexico St, UMBC, North Alabama, Sacramento St, Portland St at 15 games vs 'need 15.2') as "we don't hold all their games" - no pick, no record line, for nothing. ESPN's D1 feed (groups=50) is complete: all 365 D1 teams ended 2025-26 with 25+ games in our files; the only short records are the non-D1 opponents (348 teams, 1-3 games), and those games are almost never priced. Now a team that played a full D1 season last year (sports_breakdown_v24.NCAAB_D1_GAMES = 20 in the 365 days before the season) is complete; a non-D1 opponent or a first-year D1 team still has to earn it by the pace test; opening night (nothing played) passes everyone as before. Football's own-calendar test is untouched.
- **INJURIES (report only, nothing built).** The rule holds: a college hoops team not in the injury data is UNKNOWN - no pick (sd.covered, "injury report (not in our data)"), and the hoops 2+ out / 4+ questionable no-units rule (sports.hurt) runs on the plain list (no hoops box scores, so no 'regulars' filter). What the data covers: ESPN's hoops feed (~0-3 teams), Rotowire's college basketball report (sports_data.WEB_INJ ncaab - every school it lists, Out / Doubtful / Questionable only), the official reports in injuries_official.json. How much that blocks: on 1/15/2026 with an empty hoops read, all 60 teams on the 30 priced games were uncovered -> 0 college hoops picks possible (the board posted NHL / NBA only); opening night 2025-11-03 had 68 priced games / 136 teams, the first week 203 priced games, November 779 priced games across 308 schools - every one of them needs BOTH schools on a report. Rotowire's hoops list can't be measured from the sandbox (the proxy blocks rotowire.com and site.api.espn.com); Actions -> injury_report on 11/3 prints "NCAAB - the feed lists N teams". THE PLAN for the 'D503 official injury reports' routine (public pages, no key, no disguise): (1) the biggest lever is Covers' college basketball injuries page (covers.com/sport/basketball/ncaab/injuries) - the football version (WEB_PAGE ncaaf) already lists every school, healthy ones too ("No injuries to report."), so a school on it counts as covered; adding ncaab to WEB_PAGE with the same parser (parse_team_page) turns "both schools must be on Rotowire" into "every D1 school covered" - verify the page's layout once on a GitHub run (fetch_pages.yml) before wiring it; (2) the SEC publishes official men's basketball availability reports for CONFERENCE games (initial report 8 PM ET the night before: probable / questionable / doubtful / out; final 90 minutes before tip) - the routine reads those into injuries_official.json from January on, the way it reads the football ones; no other conference publishes one for hoops; (3) non-conference / everyone else stays Rotowire + Covers. A school on none of them keeps getting no pick - the rule, not a bug.
- **THE DOG REPLAY (every college hoops moneyline dog +100..+220 on every board day, 567 board days 2022-26, closing prices, params re-tuned each July 1 on the seasons before, no injury reports; thresholds chosen on 2022-23 + 2023-24 = TRAIN, graded blind on 2024-25 + 2025-26 = TEST; flat 1u; tools: scratch ncaab_dog_replay.py on tools/value_play_replay.Replay).** 7,199 graded dogs. Every dog: TRAIN -7.5% on 3,711, TEST -3.8% on 3,488 (all 4 seasons red). Not a trap, not fighting the own read: TRAIN -6.0% on 805, TEST +3.6% on 445. Caution on 2023-24: the blind params of that season read nearly every dog under the line (76 of 1,865 not 'fighting'), so TRAIN is mostly 2022-23.
  - TODAY'S RULE (NCAAB_DOG_EDGE - own read 4+ pts over the price): TRAIN 197-274, -4.7% on 471; TEST 14-22, -5.7u, -15.8% on 36 (2024-25 +33% on 15, 2025-26 -51% on 21). Every own-read cutoff 0..5 pts is red in TRAIN; 6+ is 7-4 blind on 11 (nothing). Own-read bands blind: 0-2 pts +3.4% (382), 2-4 pts +8.2% (206), 4-6 pts +6.4% (53), 6-8 +10% (16) - but TRAIN says -6% / -14% / -10% / -2% on the same bands: the own read alone doesn't find hoops dogs (the 10/2 and 10/9 finding, now 4 seasons).
  - A DOG-SCORE GATE like the NBA's (dog_score >= N, not trap / fighting): 4+ TRAIN 200-259, -1.2% on 459; TEST 38-44, -0.1u, -0.1% on 82 (2024-25 +17% on 36, 2025-26 -13% on 46) - flat, 1 of 2 test seasons. 2+ TRAIN -2.9% on 577, TEST +7.8% on 195 (3 of 3 test-side seasons up - but TRAIN would never have chosen it). 6+ TRAIN +2.5% on 349, TEST 10-17 -20.5% on 27 FAILS. The best dog of the day at 4+: TRAIN -5.0% on 118, TEST 31-32 +7.0% on 63 (inconsistent). Score bands blind: 4-6 +16.7% on 121 (TRAIN -8.8%), 6+ -1.0%.
  - The pieces: the favorite lost its last -0.5% / -0.2% (noise as a dog weight here); 'we lost, they won' fade -10.9% / -9.6% (0 of 4 seasons up - the fade is right); 2+ close wins fade -16.5% / -4.3% (right); home dogs -5.9% / -1.3% vs road -8.3% / -5.4%; +150..+179 -15.6% TRAIN / -0.2% TEST; +180..+220 -6.3% / -9.3% (0 of 4). By month, both gates: November / December GREEN in TRAIN (+8% to +14%) and January-March red (-18% to -6%) - the early-season soft-line fact again (10/9), a LEAD at most (TEST November 9-6 on 15).
  - What the current engine would actually post with hoops alone on the board: 2022-23 Dog 42-55 -3.1u (97 Dogs), plays 79-98 +2.2u; 2023-24 nothing; 2024-25 Dog 9-6 +4.9u; 2025-26 Dog 4-12 -7.8u, plays 1-4 -2.9u. Days with a score-4+ dog: 114 / 4 / 31 / 32 a season - a score gate would post ~30 college hoops Dogs a year.
  - FIVE CHECKS: fair YES (closing prices), blind YES, most seasons NO for every gate (today's rule 1 of 2 blind, 0 of 2 in TRAIN by season; score 4+ 1 of 2; score 2+ would pass blind but is red in TRAIN), current season n/a (no 2026-27 games), second check NO. NOTHING cleared -> no new rule. Built as a constant only, default unchanged (the owner decides): sports.NCAAB_DOG_RULE = "own" (today) / "score" (dog score NCAAB_DOG_GATE = 4+, units by the weighed read, like the NBA) / "off" (college hoops dogs carry no units), pinned by test_college_hoops_dog_rule_constant; the dashboard's brain line follows it.
- **RECOMMENDATION (the owner's call): "off" - no units on college hoops dogs (no college hoops Dog of the Day) for the first 50 college hoops Dogs' worth of season, with the score-4+ dog logged as a LEAD record (no units) to judge live; keep the college hoops Lock (own read + the price, like the NBA's).** Today's rule is the worst of the three blind (-15.8%); "score" is flat and would put ~30 Dogs a year at 1u on a coin flip; "off" costs nothing and the leans still fill the board.
## 10/9 - BEST DAY TO BET, favorites vs dogs (NFL + college): the timing rule CONFIRMED for college, REFINED for the NFL - a timing fact, not a bet
- Paid feed looks: Tue / Thu / Sat / game morning (no Sunday-night opener, no Wed/Fri) - Tuesday is the first fair number in ~90% of games. Same side's ROI at each look minus at the close; 2020-22 vs 2023+ blind; 89 cells.
- COLLEGE: a DOG bet Tuesday is +2.5 pts of ROI over the same bet at the close (7 of 7 seasons; blind +2.3); Thursday +2.4; Saturday morning +1.7 - the 8 AM board gives up a third of it. A FAVORITE bet Tuesday is -1.6 pts vs the close (1 of 7 up) - favorites keep getting cheaper through kickoff.
- NFL: the early dog edge is gone since 2023 for big dogs (+141..+220 blind -1.6); what's left is SMALL dogs +100..+140 on Tuesday (+2.1, blind +1.3) and SEPTEMBER dogs (+3.3, blind +2.5). NFL favorites: every look is worse than the close - they can wait.
- VERDICT: college rule CONFIRMED (dogs Tue-Thu, favorites at game time); NFL refined (only small / September dogs gain by going early). Betting every side blind loses at any look - timing is worth 1-3 pts, never a bet. No code change.

## 10/9 - CONFERENCE TIER EFFICIENCY (are Group-of-5 / FCS lines softer early?): DEAD; the G5-dog-vs-Power cell stays a LEAD
- 4,067 college games by tier. The close improves on Tuesday's number by the same tiny amount in every tier - small-school lines are quieter, not wrong. The dog's early-price worth is the same everywhere (+2.4 to +3.9 pts).
- G5 DOG vs a POWER team at +100..+220, Tuesday price: train +17.9%, blind 21-20 +22.9%, all 92 bets +20.1% (z 1.5) - LEAD, re-check at 150+. FCS dogs: a fade fact (-38% blind; seen_all already keeps FCS sides off). College home favorites -150..-101 lose at every price (-11%) - a pricing fact.
- DEAD as "soft early lines". Nothing wired.
## 10/9 - AFTER A THURSDAY GAME (~10 days off vs an opponent on a normal week) + the Thursday game itself: the post-Thursday ROAD DOG covers = LEAD; the rest DEAD
- NFL 2018-26, closing prices, 224 post-Thursday sides; 2018-22 train / 2023+ blind; 45 cells across both studies.
- All post-Thursday teams: ATS 53.1%, ML -6.5% - the extra days are priced. At home a fade if anything (home dogs 12-18 ATS).
- THE ONE CELL: post-Thursday ROAD DOG against the spread - train 23-11 (+29.4%), BLIND 16-10 (+19.0%), all 39-21 (65%, 6 of 8 seasons, z 2.3) vs every road dog 55% / 50%. Moneyline flat - a cover, not a win. The line doesn't move midweek (no need to be early).
- The Thursday game itself: noise (dog ATS 53.5%, favorite ATS 46.6%).
- LEAD (one of 45 cells, not past correction). If it holds this season: +1.5 on that road dog's spread read, never a trigger.

## 10/9 - DIVISION REMATCH (does the team that lost the first meeting get it back?): DEAD overall; a 7+ loser as a +100..+220 dog covers = LEAD
- NFL 2018-26, 370 rematches, closing prices.
- All first-meeting losers: ATS 51.1%, ML -5.5% - the market has it. Lost by 21+: ATS 42.1% - a blowout loser does NOT bounce back. Close losers 60.7% train -> 48.5% blind - dead.
- The one cell: a 7+ loser now a +100..+220 dog, ATS train 29-19, BLIND 16-10, all 45-29 (60.8%, 7 of 8 seasons, z 1.9) vs every such dog 54% / 50%. The mirror (7+ loser now favored) covered 41.3% - a mild fade.
- DEAD as a rule (confirms 10/1); the dog cell = LEAD. If it holds: +1 on that side's spread read, -1 on a 7+ loser laying points.
## 10/9 - NHL ROAD TRIPS: first home game after a 4+ game trip, and the 5th+ straight road game (DEAD both ways; the 9/30 WATCH closed)
- Closing moneylines, regular season, train 2018-24 (13,414 sides), blind 2024-26 + 2026-27 (5,378). 39 looks.
- FIRST HOME GAME after a 4+ trip: -4.8% on 572 train, +0.2% on 237 blind - same as every home side; dogs/favorites flip sign between halves. The 9/30 WATCH (4+ trip, 2+ days rest) is DEAD: -4.6% on 434, -1.1% on 182 blind.
- 5TH+ STRAIGHT ROAD GAME: +0.2% on 380 train, -16.1% on 170 blind - every cell flips sign; the home team facing it -9.1% train, +4.0% blind.
- DEAD. The books price the trip. Nothing wired; don't re-chase.

## 10/9 - NHL START TIME and TIME ZONES (afternoon games; East team at a 10 PM body clock out West; West team at a 4 PM body clock in the East): DEAD - "road team loses" is the whole story
- Local start from the venue's zone, body-clock start = local minus the zone gap. ~75 looks.
- Afternoon road side -10.6% on 429 train, -8.6% on 172 blind - but no cell beats the price both halves (home favorites +3.5% then -1.4%).
- East team 2+ zones West at a 10 PM+ body clock: -9.2% train, +7.1% blind - flips.
- West team 2+ zones East: -8.5% on 1,129 train, -7.1% on 504 blind - until the control: Eastern teams on the road within one zone are just as bad (-9.8% / -8.9%). It's the road side, not the trip. The home dog facing an eastbound team +9.9% / +8.0% - a LEAD at best after 75 looks; recheck at 300+ blind games.
- DEAD. Nothing wired.
## 10/9 - LOOK-AHEAD / SANDWICH favorite (college: a favorite vs a weak team with a much stronger opponent next week): DEAD; one thin cell a LEAD at most
- College 2018-26, closing spread + ML, FBS vs FBS, 3,366 favorites (2018-22 train / 2023+ blind), 75 cells; best raw p .014 - nothing passes correction. The books price the sandwich (matches 10/1 NFL and 10/4 college).
- "Next opponent .750+" cells are flat in train and only look good blind - a sign flip = noise.
- Only same-sign cell: favorite vs a .250-or-worse team whose NEXT opponent went .750+ last season - the dog covers 57-37 (+15.6%, z 1.7, ~15 games a season). LEAD at best; the dog still wins nothing straight up.
- DEAD. Not a weight.

## 10/9 - POWER vs GROUP-of-5 non-conference (G5 dog vs a Power team, home / road, by price): DEAD; the 10/1 September "+23%" WATCH did not hold blind
- 619 priced Power-vs-G5 games 2018-26 (a by-name conference map with realignment years - the game files carry no conference). 32 cells; best raw p .145.
- G5 home dogs +100..+800: ML +36.9% train -> -6.1% blind; road dogs +0.5% -> -22.6%. Big "paycheck game" dogs (+800 up) are a graveyard (-29% / -39%).
- The 10/1 September G5-dog WATCH: +17% train -> +3% blind - closed, DEAD.
- Only cell up both halves: G5 home dog +150..+250, 10-9 on 19 games in nine seasons - too thin.
- DEAD. Nothing wired. (Note: a real conference map doesn't exist in the repo - it should live in sports_data / data/sports/conferences.json if a future study needs it.)
## 10/9 - TENNIS FATIGUE (the fresher player vs one who just played a long one / won 4+ in a week): DEAD - the books price tiredness
- 68,902 ATP+WTA matches 2012-26, Pinnacle and average closing prices, 2012-23 train / 2024-26 blind, 72 cells; nothing clears.
- Opponent played a 3-setter yesterday, ours didn't play: noise around the baseline (ATP dog +5.2% train -> -18.8% blind).
- Opponent won 4+ matches in 7 days: the fresh DOG gets smoked (ATP -12.2% train, -18.0% blind; WTA -20.4% train); backing the hot favorite is only break-even - priced.
- DEAD. The engine's fatigue weight (sports_tennis.Ratings) stays as is; nothing wired.

## 10/9 - TENNIS INDOOR SWING (first indoor events after the Asia swing, strong prior indoor record, first match after flying Asia -> Europe): DEAD; one paper lead
- 240 cells tried. WTA has no fall indoor events in 2024-26 (train-only).
- 65%+ prior indoor record in the swing's first two events: ATP favorite +7.7% on 95 train, 9-1 blind - 105 bets, z 1.7 = paper LEAD; re-check after the 2026 fall swing (needs ~500 more bets).
- First match after Asia -> Europe: ATP favorites -10.2% train -> +19.6% blind - a clean sign flip; DEAD both ways (the jet lag is in the price). Indoor favorites simply ran hot in the blind seasons.
- DEAD. Nothing wired.

## 10/9 - NBA READINESS (the season opens in two weeks): the pipeline end to end on 2025-26, three bugs fixed, and a blind replay of the NBA board 2023-26 - the Lock is the only NBA unit play the rules produce, and it won
Checked on the real 2025-26 files: the model tunes (11,530 finals, 66.6% vs the market's 69.4% - it leans on the line); candidates build for a past day (2026-01-15: 36 sides); every NBA weight fires on real games over 636 board days (rested dog vs a back-to-back 960 sides, the overreaction bounce 380, won 2+ close 490, the comeback-win fade 221 each way, hot stars 924); the hoops injury rule behaves (2 out / 4 questionable among the rotation = no units); the dashboard renders the NBA card. No crash.
- BUGS (fixed, tests, main 94632bdb4): (1) the live watcher could match a PRESEASON game (a live bet on an exhibition); (2) a preseason game the feed never finalized read as a 'missing result' in sports.data_gaps (would block the team / hold the board); (3) cover streaks never reset over the summer - 3 NBA teams would have opened on a 4-5 game streak from April; a 30+ day break now ends a streak (sports_form.ATS_FRESH_D).
- THE BLIND REPLAY (NBA only, the real post_board at 8:35 AM PT, closing prices, each season's model fit on the seasons before it, today's rules, no injury reports; 2023-24 tuning, 2024-25 + 2025-26 graded): Lock 2023-24 6-6 +0.8u; 2024-25 35-23 +5.2u on 36u (+14.5%); 2025-26 19-9 +3.2u on 16u (+20%). Graded together 54-32 (62.8%), +8.4u on 52u, +16.2% (said 56%, hit 63%; mostly the ½u backup Lock). Leans 263-237 (52.6%), -3.9% flat. No value plays clear (1 in 3 seasons).
- THE NBA DOG OF THE DAY CAN'T HAPPEN under today's rules: good() needs a proven angle or a dog gate, and dog_gate has no NBA branch - 0 real-value dogs in 3,747 NBA dog sides. The NBA dog weights DO work (flat 1u, 23/24/25): rested vs a back-to-back -0.6% / +22.1% / +13.3%; the overreaction bounce +13.1% / +18.4% / +50.9%; won 2+ close -44% / -10% / -23%. Dog score 4+ as a gate (chosen on 2023-24): graded 15-12, +11.5u on 27 - a LEAD, far too thin; not built.
- Caveats: closing prices, not the 8 AM number; no injury data in history; NBA alone on the board (live, an NBA Lock posts only when it's the day's best Lock). sports_strength still flags the NBA 'weak' on the engine's own graded picks (-7.1% on 910) - OWNER_ON overrides it.
- RECOMMENDATION (the owner's call): units on the NBA Lock from day one, leans only for everything else; judge the Lock live at 50. Open build: an NBA dog gate at score 4+ (½u, own record).
## 10/9 - why the value plays lose (the owner's -6.7%): a replay of TODAY's engine, every board day 2023-26, rule chosen on 2023-24 and graded blind on 2025-26
The machinery: tools/value_play_replay.py (kept this time) - every calendar day 2023-01-01..2026-09-30 rebuilt as the 8:35 AM
PT board would have built it: the day's games set back to 'pre' at the CLOSING price, every later game gone, ratings / form /
dog states / fact indexes built from the games before it, model params re-tuned each July 1 on everything before (blind;
the gates and study weights were built with every season seen, same caveat as 10/2), no injury reports (none exist in
history). 795 board days with a unit pick: 675 Locks, 387 Dogs, 1,199 value plays (sports.plays). Slices in
tools/value_play_cells.py, the rule test in tools/value_play_rules.py (42 cells: 36 written down BEFORE any 2023-24 row
existed, 6 combos added after the train ranking). Flat 1u numbers (the ½u system scales them).
- **The headline is partly stale.** By TODAY's engine the value plays are about break-even, not -6.7%: 2023-24 -1.0% on
  843 (-19u / +10u / +1u by season), blind 2025-26 +2.6% on 356 (-3u / +15u / -3u); the Lock +2.1% / +3.6%, the Dog +6.1% /
  +3.6%. The -6.7% came from the 10/2 code snapshot (its rows are still in the scratchpad: 601 of its 713 days are 2025-26,
  where it had NBA shut off as 'weak' - OWNER_ON came 10/3 - no favorites' weighing, and MLB tuned each January): on
  those same 2025-26 dates it ran -6.3% on 416 plays, with MLB favorites -15.0% on 163 and short favorites -11.7% on 115.
  Same-window check (1/24-2/28/2025): 37 of its 38 plays are on today's board too, which adds 23 more (NBA, more hoops).
- **What loses, in BOTH halves:** (a) SPREAD value plays: 2023-24 -21.3% on 131 (college hoops -19.5% on 121), blind -15.1%
  on 9 - 0 of 4 seasons up. They carry no own read (strust = 0, the 10/3 sweep: the engine's margin model is worse than the
  closing spread), so real_value() passes them on the blended edge and the ½u rides on a study shift alone. Today's engine
  hardly makes them any more (9 in 21 months), so this is a hole to close, not a profit engine. (b) Short moneyline
  favorites -129..-101: -1.6% on 239, blind -3.9% on 88 (1 of 5 seasons up) vs favorites -150..-130 +6.5% on 335 / blind
  +8.7% on 202 (4 of 5 up). (c) College hoops dogs through NCAAB_DOG_EDGE (own read 4%+ over the price, no dog score):
  -6.4% on 106, blind -36.5% on 13 (0 of 2) - the own read alone doesn't find dogs (the 10/2 point study said so). (d) MLB
  favorites: -6.4% on 98 (0 of 2 seasons) here; -15.0% on 163 in the 10/2 snapshot's 2025 - 0 of 5 seasons across both.
  Every gated dog as a ½u play: +0.3% on 131 / blind -6.0% on 57 (the BEST one, the Dog of the Day, is what makes money).
- **What wins:** moneyline favorites -150..-130 (above); NBA favorites +13.8% on 39 / +21.7% on 28; football dogs +33% on
  12 / +17% on 37; hockey favorites +10.0% on 136 / +2.4% on 60 (the weighed w_p ones +6.1% / +3.8%); and the favorites
  the engine's own read beats by UNDER 3% - the THIN ½u ones - +4.1% on 219 / +8.6% on 162, while own edge 10%+ ran
  +5.4% / -10.6%: edge size says nothing (the 10/2 finding again). Playoffs +16.6% on 22 / -42% on 3: noise.
- **Rank on the day is NOISE** - the 10/4 "3rd play down loses" pattern flipped: #1 +5.2% then blind -2.9% (154); #2 -14.9%
  then +18.4% (80); #3+ +0.4% then -0.7%. The "cap at 2 / ½u past #2" idea is dead. Plays-per-day also flipped.
- **The rule, chosen on 2023-24 (the best large, every-season-up cell): MONEYLINE ONLY** (sports.PLAY_MARKETS = ("ml",):
  a spread candidate stays a lean / Lock-eligible read, carries no units). Train +2.7% on 712 (3 of 3 seasons) vs as-is
  -1.0%; blind 2025-26 +3.1% on 347 vs +2.6% on 356 - the 9 spreads it drops lost 1.4u. Five checks: fair YES (closing
  prices, blind params), blind YES, most seasons YES (the dropped plays down 4 of 4), current season n/a (no spread play
  yet in 2026-27), second check YES (10/3 strust = 0 - there is no own read behind a spread, and the owner's rule is units
  sized by the own read). Honest size: +0.5 pt a play blind on a cell of 9 - real, small, free. BUILT as a constant
  only, default unchanged (the owner decides rules): sports.PLAY_MARKETS, pinned by
  sports_test.test_value_play_markets_constant.
- **Other cells, graded blind (not rules):** ml + no college hoops +7.1% -> +9.6% on 147 (1 of 3 test seasons, drops 60% of
  the plays - the owner wants picks); ml + favorites -150..-130 or dog +4.8% -> +5.5% on 259 (1 of 3) - a LEAD on the short
  favorites, watch it live; ml + no MLB +4.2% -> +3.2% (MLB barely plays in today's engine - see the caveat); rank 1 only
  +5.2% -> -2.9% FAILS; own edge 5%+ -2.8% -> -10.2% FAILS (bigger own edge, worse); dogs only +0.3% -> -6.0% FAILS; pros
  only +2.9% -> +3.6% on 104 (1 of 2). 42 cells - expect 2 at the 5% level by luck; the spread cell survives because it
  lost in every season and has a mechanism, not because of its p-value.
- **Caveats:** (1) only the model params are blind - the dog angles, gates and strength / big-study calibration were
  built with these seasons seen; (2) the July 1 re-tune leaves MLB with almost no plays July-September every year (2023:
  96 plays March-June, 0 after) - the live engine re-tunes daily, so the real summer board differs; the MLB verdict leans
  on the 10/2 snapshot's 163 plays; (3) closing prices, no injury reports, today's code (goalie / 40-shot weights need
  live files that don't exist in history, so they never fired); (4) 2026-27 is 3 months. Re-run after the football
  season: `REPLAY_PARAMS_DIR=... python tools/value_play_replay.py 2026-07-01 2026-12-31 out.jsonl` (~7-14 s a day;
  years in parallel; step 2 = every other day).

## 10/8 - BOOK-BY-BOOK DISAGREEMENT (one book's moneyline off the other books' median, bet the outlier price): DEAD as a general angle; one per-book sub-cell is a paper LEAD we can't bet
NFL 1,750 + college 4,067 graded games with a fair look (after both teams' last games), 2020-26, every book's price kept. "Outlier" = a book whose no-vig price on a side sits 2/3/4/5% under the median of the OTHER books (5+ books posted) AND whose raw price still beats that consensus; one bet per game at that book's real price. Thresholds picked on 2020-22, 2023+ blind. 48 cells; none beats p .01 after correction. (The 10/1 round-4 "book dispersion" DEAD, re-checked blind and per book.)
- College, first fair look, 2%+ gap, dogs: train +22.4% on 211 (3/3) but the sides won 27.5% vs consensus 27.2% - the ROI was the outlier price on big dogs (avg +570), not better picks. Holdout 2023+ +8.1% on 129 (2 of 4, p .64; -3.7% at the close). +100..+220 only: train +6.8% on 70, holdout +19.9% on 47 (p .24) - too thin.
- NFL: nothing. First look 2%+ +100..+220 dogs train -9.7% on 28, holdout -1.6% on 28.
- The LAST look before kickoff is a trap: college 2%+ outliers -9.1% on 290 train, -33.1% on 133 holdout (0/4, p .002). Late, the book off the pack moved first - the pack is stale, the outlier is right.
- Soft books (first fair look): college FanDuel is the outlier most often and won above the market (train +49% on 68, holdout +49% on 33, p .09) - one book in 48 cells, avg +500 dogs (outside our +100..+220 rule) = paper LEAD at best; our live feed has no FanDuel.
- Can't be wired: 71% NFL / 58% college outliers are back to consensus by the next look. Five checks: fair YES, blind YES, most seasons NO, current season NO (2026 -12% on 12), second check NO. Nothing built.

## 10/8 - LINE-MOVE SHAPE (steady drift / one jump / reversal, first fair look -> last look before kickoff): DEAD for drift and jump; the 10/1 reversal spike-side lead unproven at n 47
Median book's no-vig home % at every fair look (3+ looks). Net move 2/3/4%+; one step 70%+ of it = JUMP, else DRIFT; moved 2%+ then came back half+ = REVERSAL. Bet the side the shape favors (and its mirror) at the last look's median price. 36 cells; thresholds on 2020-22, 2023+ blind. Nothing clears p .01.
- NFL DRIFT, follow: train +13.8% on 157 (3/3) -> 2023+ -1.9% on 189 (1 of 4). The 2020-22 drift money was a slow market; it's priced now.
- College JUMP, follow: train +10.9% on 254 -> holdout -6.1% on 341 (1 of 4). Fading jumps loses both ways. NFL jumps lose every cut.
- REVERSAL, NFL spike side (10/1 lead +19% on 53): train +10.7% on 22, holdout +6.5% on 25 (13-12, p .76) - nothing provable. College fade-the-spike +36.8% on 14 -> +10.7% on 24 - small, keep in the log.
- Five checks fail (most seasons, current season, second check). Not a weight; the only use of a move stays the TIMING rule (dogs early, favorites game day).
## 10/8 - KEY NUMBERS: a half point at 3 / 7, and the line crossing them early (NFL 2020-26): DEAD as a bet, a PRICING FACT
1,730 NFL games with a first fair early spread and a closing spread; 1,757 finals for the landing table; 43 cells; 2020-22 judged, 2023+ held out.
- What a half point is worth: the favorite wins by exactly 3 in 9.8% of games near a 3 line (a half point = ~5 cover points, ~-110 -> -135 of juice), 7 = 5.7% (~3 points), 6 = 4.0%, everything else 1-3%. Shop the half point at 3; pay for it nowhere else. The sim already learns these margins (sports_sim KEY_PRIOR) - this confirms the sizes.
- Hindsight: when the line moved through 3, the side it moved toward covered 29-8 at the early number - but that needs the move called ahead, and the 10/7 blind re-check killed the move model.
- Blind, bettable: a dog on +3.5 at the first fair number 2020-22 +19.7% on 79 -> 2023+ -16.8% on 95. Every key-number cell (+3, +2.5, +7, -2.5, -3...) 46-54%; getting the key number early did NOT beat the close (50.9% on 57). Nothing built; if an early NFL spread play ever goes live, prefer the right side of 3 at the same price.

## 10/8 - SPREAD vs MONEYLINE DISAGREEMENT (a book's moneyline and its own spread say different win %): NFL DEAD; college LEAD
Curve P(home win) = logistic(closing spread) fit on 2020-22, calibrated on 2023+. At the first fair look, same book: moneyline % minus the spread's %; 3%+ apart = bet the cheaper market. ~120 cells.
- NFL: nothing blind (moneyline side +3.3% -> -1.2%; spread side = the ATS baseline). The closing-feed moneyline side 2023+ +13.8% on 245 was -3.1% in the choosing years - not our 8 AM price anyway.
- College: when the moneyline rates a side 3%+ above its spread, that side's SPREAD covers 47% (-11.1% on 628, 0 of 6 seasons up) and its OPPONENT on the moneyline pays +7.4% on 628 (5 of 6); inside -150..+400 +8.7% on 564 (2020-22 +8.1%, 2023+ +9.1%, 6 of 6) - but t 1.5 (p ~.12), ~120 cells, and the 10/1 version with a different curve binned it for 2023: method-sensitive = fragile. LEAD, not built; watch it through 2026. If it holds: +1..+2 on that college dog's moneyline in the early spots, never a trigger.
## 10/8 - NHL early-season regression: fade the hot start, back the cold start? (DEAD as a rule; hot-start fade a weak LEAD)
- Setup: both teams 3-10 games into the season, each with 40+ games last season; "deviation" = this year's win% (or goal diff a game) minus last year's. 270 cells on 2018-23, closing moneylines; baseline every early side -3.7%. Blind 2024-26. (Not the 10/1 "early dogs by last year's standing" DEAD - this is the gap to last year.)
- Train looked like something (team 35+ points under last year's win%: +11.5% on 68; the plain "Flames spot" - .34 or worse after 3-6 games, .55+ last year - +25.4% on 45), best cell z 1.07 - chance across 270 cells.
- BLIND 2024-26: backing the cold team died (-22.5% on 48, -3.8% on 36; the Flames spot -4.1% on 23). The hot side kept its direction: a team 10-20 points OVER last year -19.2% on 70, 35+ over -11.7% on 17.
- Verdict: DEAD for backing cold starts (the market prices the bounce - an 0-3 team is not a buy on that alone). Hot-start fade = weak LEAD (p nowhere near .01 after 270 cells). Not built; re-check after 2026-27's first month.

## 10/8 - NHL goalie workload + the team that just got OUTSHOT 40+ (goalie fatigue DEAD; "allowed 40+ shots, plays again within 2 days" = BUILT as a weight)
- 171 goalie cells, closing ML, regular season, 2018-23 train, 2024-26 blind. Goalie fatigue itself DEAD: 3rd start in 4 nights -5.4% on 136 blind (same as every side); started last night flips blind; the back-to-back is the team's (already built), not the goalie's.
- What popped is the TEAM: allowed 40+ shots last game and plays again within 2 days: -13.7% on 909 train (won 42.4% at 48.4% implied, 1 of 6 seasons up, z -3.8), -30.2% on 167 BLIND (won 32.9% at 47.2%, 0 of 3, z -3.8). Same whichever goalie starts (a different goalie -26.8% on 117 blind), after a win or a loss, home or road; gone with 3+ days rest (+1.9% on 235). Not the built last-10 shot-share weight (still loses inside both halves). The other side (bet the team FACING it) +3.3% on 905 train, +19.9% on 165 blind (3/3).
- Multiple testing: train p ~1e-4 x ~190 cells ~ .03, the blind holdout confirms on its own at p ~1e-4. 40+ shot games are rarer now (~125 team-games a season) - 2-3 sides a week.
- Five checks: fair YES (box score known the morning after), blind YES, most seasons YES (1/6 + 0/3 up), current season too few, second check YES (both sides of the bet agree). BUILT 10/8 as a WEIGHT (never a trigger): sports.outshot_40 - a side that allowed 40+ shots last game, playing within 2 days: -2 on its dog score / -1.5 on a favorite's weighed read; the side facing it +1 (inside STUDY_CAP / FAV_CAP). Lead tag 'outshot 40+' in sports_leads for its own live record.
## 10/8 - MLB playoffs: postseason pricing and series spots: DEAD (the favorite fade confirmed, nothing to bet)
349 priced postseason games 2018-26, 19,735 regular-season games as the reference; series state from the games before each one only; dev 2018-23 / blind 2024-26; ~25 cells (x60 with the next study).
- Favorites -8.2% on 349 (the 10/1 -8.9% holds) but only 3 of 9 seasons down - not a steady fade; holdout +0.9%. Home/road, won-the-last-game, series leader: every cell flips in the holdout.
- Facing elimination -18.3% on 102 (2 of 9 up; holdout -5.9%) - a fade lead at best. Game 1 / bye rust: nothing (as 10/1).
- DEAD. October favorites not earning their price already sits in the engine as "no forced Lock / never past -150".

## 10/8 - MLB playoffs: starter rest and BULLPEN workload: bullpen = strong LEAD (thin - paper-tracked, not wired); starter rest LEAD/DEAD
Relievers' innings on the 1-2 days before the game from the roster boxes (2021-26, 231 priced postseason games); thresholds 4/6/8 IP and 2/3/4 IP more than the opponent pre-set; dev 2021-23, blind 2024-26.
- BULLPEN: a team whose relievers threw 4+ innings over the last 2 days, facing a pen that threw under 4 - bet the FRESH side: 61-24, +36.9%, 6 of 6 postseasons; BLIND 31-12 (+30.4%, 3 of 3). Every sibling threshold won blind too (6+ IP 40-18; 2+ IP more than the opponent 66-31). Fresh dog 27-8, fresh favorite 34-16. p .00006, x60 cells .004 - clears the bar, but it's 85 games over 6 Octobers; the true edge is far smaller than +20 pts. Regular season the same cell is -5.4% on 2,638 - October only (the same 3-4 arms go every day).
- Starter on short rest in October: 33 games, nothing (10/1 DEAD stands). Regular season the listed starter on <=3 days rest +14.1% on 241 (8 of 9 seasons) - LEAD, re-check in April.
- Starter on long rest (7+ days) as the FAVORITE -21.6% on 106 (holdout -10.4%) - LEAD, fade only.
- Not wired 10/8: 85 games is far under the owner's "thousands of games" bar. If it keeps winning: +3 on a fresh playoff dog's score / -2 on a tired playoff favorite's read, MLB postseason only, inside STUDY_CAP / FAV_CAP.
## 10/8 - the backup QB's SECOND start (NFL - does the market overreact to a bad first start?): DEAD as a buy; small FADE lead
- NFL 2018-26 reg season, closing spreads. QB1 = the passer listed most this season so far; one QB line per box score, so a QB1 hurt mid-game reads as a backup (the 10/1 'fake edge' problem) - the pregame cuts avoid it. Train 2018-23, blind 2024-26, ~22 cells.
- Any team on a backup: ATS 51.1% train, 46.6% blind (-10.6%) - matches the 10/1 DEAD entry.
- Backup's 2nd start in a row: 44.8% train, 42.6% blind (1 of 9 seasons up). After a BAD first start (2+ INT or under 150 yds) 30-40-2 all told (42.9%). The market does NOT overreact - the team keeps losing the spread (same direction as the built "QB1 out a second straight week" -3).
- The one strong cell is a FADE: a backup whose first start had 2+ INTs covered 11-26 (29.7%) in start 2 - n 37, one of ~22 cuts, not after correction = LEAD. Nothing built. (10/8: the Bucs' Jalon Daniels is this exact spot at Dallas.)

## 10/8 - WINLESS and UNBEATEN starts (0-3+ / 3-0+) against the spread, NFL + college: NFL winless ATS = LEAD (close to a build); college DEAD; unbeaten favorites a mild fade
- NFL 2018-26, closing spreads; record = this season's games before this one. Winless 0-3+, next game ATS: train 42-28-3 (60.0%), BLIND 13-6-2 (68.4%, 3 of 3) - 55-34-5 (61.8%, z 2.2). Moneyline flat: they still lose, they keep it inside the number.
- As a DOG: 45-23-4 (66%, z 2.7; blind 9-2-2); road 34-14-2 (70.8%); dogs of 7-13.5 19-7-1, 14+ 5-6. Exactly 0-3 24-13-4. Control: a 3+ losing streak on a team WITH a win is 50-53% - it's the winless label. Loss margins add nothing.
- Midweek (odds history): at the first number of the week 42-21; the line moves ~0.2 pts toward them by the close - early is better, the close still pays.
- Unbeaten NFL 3-0+ favorites: 30-45 ATS (40%, 0 of 9 seasons up), ML -11% / -16% - mild FADE lead (p ~.08).
- College: winless 0-3+ ATS +5.5% train, +2.6% blind, dogs -11.5% blind - DEAD.
- ~45 cells per league, so p > .01 corrected: LEAD, not built. If it holds: +2 on an NFL 0-3+ side's spread read (0.5-13.5, +1 on the road), -1 on an NFL 3-0+ favorite. Re-check after this season. (Tonight's Bucs +8.5 lean has BOTH: winless road dog of 8.5 = the good spot; a backup's 2nd start after a 2-INT first = the fade - they roughly cancel.)

## 10/7 - THE MOVE MODEL, RE-CHECKED BLIND BEFORE GOING LIVE (the owner: "we need to be on these lines before they move - that's the edge. Lock everything you need to in the engine"): DEAD - the 10/1 edge was a look-ahead feature. Nothing built.
tools/early_move_recheck.py -> results/early_move_recheck.json; tools/early_move_live.py -> results/early_move_live.json.
No paid re-pull, no network. The 10/1 "STILL STANDING" finding (early_dog_studies study 1: a model fit on past seasons
picks the dogs the money comes to - NFL top 20% 75% moved, +6.0% at the first fair price, 4 of 5; college 74% moved,
+5.8%, 4 of 5) was about to become the seventh early spot. Held to the five checks first, on the paid football history
2020-26, in the spot's band +100..+220, graded on WINS at the first fair price:
- **THE LEAK:** the 10/1 model's inputs carried "early_move" - the dog's price move from the week's FIRST look to its
  SECOND (a later snapshot) - and the bet was graded at the FIRST price. You can't have the first price once the second
  look is out. That ONE input is the whole edge: on its own it "makes" NFL +10.7% (83% moved, 3 of 6) and college +3.7%
  (84% moved); the full 10/1 feature set NFL +10.6% / college -1.6%. Its honest form - bet at the SECOND look once the
  money's already coming - is the 🔨 'hammered early' spot (study 4), live since 10/1 with its own record. The book
  features (price spread across books, best book vs middle, books posted) need every book's price; the engine sees one
  feed - and they add nothing (honest + books: NFL -5.9%, college -4.6%).
- **HONEST (every input known at the first fair number, the engine's read blind to injuries / starters / weather and
  tuned only on the 3 seasons before, the model fit only on earlier seasons, the cutoff fixed from those seasons' top
  20% - what a live scan can do; the season's own top 20% can't be bet, it needs the whole season to rank):**
  NFL 200 bets, won 39.0% (the price said 41.8%), -5.9% at the first price, -7.5% at the close, the money came to the
  dog 57% (every band dog: 50%), 2 of 6 seasons up: 2021 -5.8% (21), 2022 +15.9% (38), 2023 +33.3% (44), 2024 -42.5%
  (47), 2025 -24.1% (32), **2026 -19.4% on 18**. College 334 bets, won 40.1% (said 41.0%), -2.7% at the first price,
  -5.2% at the close, moved to the dog 61% (every band dog: 59%), 4 of 6 up but pennies - 2021 +1.1% (71), 2022 +8.1%
  (55), 2023 +0.9% (61), 2024 +2.2% (69), 2025 -25.6% (61), **2026 -3.2% on 17**. The model can't call the move
  without seeing it start: +7 points over any dog in the NFL, +2 in college.
- **THIS SEASON'S LIVE LINES (line_history, hourly since 10/1 - the first price recorded after both teams' last games
  vs the last before kickoff; the model fit through 2025, the engine's read pre-game from the replay):** NFL 22 band
  dogs (12 final: 6-6, +14.5% at the first price, 27% moved to the dog, the money LEFT the dog 6 cents on average);
  the model picked 1 (Chargers +154 on 10/11, pending, hasn't moved). College 69 band dogs (41 final: 20-21, +20%, 42%
  moved); the model picked 9: 6-1 graded (+128%), 8 of 9 moved to the dog (E Michigan +195 -> +185, Temple +205 ->
  +190, Louisiana Tech +105 -> -110, Drake +164 -> +120, AR-Pine Bluff +151 -> +115, Western KY +114 -> +105 lost;
  Tulane +205 -> +140 and Coastal +120 -> +130 pending). Seven finals, three of them FCS games - not a sample; the
  paid 2026 rows above (18 NFL / 17 college) are the honest this-season read, and they're down.
- **Our ten posted early plays, got -> now:** Alabama +130 -> -122 (52 cents came to us), Falcons +120 -> -170 (90),
  Florida St +215 -> +150 (65), Tulane +205 -> +140 (65), UMass +120 -> +110 (10), Jaguars +120 -> +120 (won), Fresno
  St +205 flat, NC State +124 -> +145 (-21), New Mexico St +180 -> +195 (-15), Iowa +120 -> +142 (-22). Five of nine
  open plays the money came to, three it left - the spots are doing what they're for; the 10/4 note stands: not a
  sample yet.
- Five checks: (1) fair YES (2) blind YES (3) most seasons up NO in both leagues (NFL 2 of 6; college 4 of 6 but the
  total is negative and the last two seasons -25.6% / -3.2%) (4) this season NO (NFL -19.4%, college -3.2%) (5) the
  live replay: too few to grade. **DEAD. Not built for either league** - no spot, no weight, no units, no model file.
  The study scripts and this entry are the record; study 1 in tools/early_dog_studies.py is marked LOOK-AHEAD so
  results/early_dogs.json's "+6%" can't be read as a finding again. "Being on the line before it moves" is what the
  six spots already do: they post at the first fair number, and their own records say whether it pays.
- A side fix in the new scripts: a price move across the line counts right (+105 -> -110 is 15 cents, not 215 - a
  plain subtraction had Louisiana Tech "moving 215 cents"); early_dog_studies.cents still subtracts (its 10+ cutoff
  only cares about the sign there).

## 10/7 - "How often is sharp money actually right?" (the owner bet New Mexico St +200 after FIU went -218 -> -240; our early play went against the money; report only)
tools/sharp_money_study.py -> results/sharp_money_study.json. No paid re-pull, no network. "Sharp money" = the side the
line moved TOWARD between the opener and the close (the only sharp signal that exists for every game), plus the real
money-vs-tickets splits where we hold them (Action Network, 2024+). Graded three ways: at the OPEN (what the bettor who
moved the line got - hindsight, nobody gets that price after the move), at the CLOSE (betting WITH the money after the
move - what a viewer can actually do), and the OTHER side at the close (fading it). Prior findings this agrees with:
10/1 "sharp money" (237 split cuts, all dead but the NHL sharp dog), 10/1 overnight studies (steam / RLM dead), the
NHL bet-timing study (the market comes toward the engine's side). Nothing new is built; nothing changed.
- **THE PLAIN ANSWER:** the side the money moves to wins straight up MORE than half the time because it's usually
  the favorite - 54.7% over 29,007 games 2023-26 (favorites moved to: 68.1%, dogs moved to: 39.3%) - and the move IS
  information: betting it at the opener (before the move) made +3.0% (SE 0.7) everywhere, +17.7% on NBA dogs, +10.3%
  on NHL dogs, +24.6% on NFL dogs (the NFL game-file opener looks stale - 83% of its moves are 20+ cents - so trust
  the paid-history NFL number below: +12.2% on dogs). BUT betting WITH it after the move, at the close: -5.3% (SE 0.6),
  0 of 4 seasons up, every sport red (NFL -3.0, college football -8.8, NBA -1.5, college hoops -8.4, NHL -0.1, MLB
  -4.8). Fading it at the close is worse: -6.6% (SE 0.7). The price already moved; the vig eats what's left. Nobody
  wins by following OR fading a move that already happened.
- **By move size (the NMSU move was ~20 cents):** 20+ cent moves: the moved-to side wins 56.6% but pays -6.5% at the
  close (n 16,926; 0 of 4 seasons); 10-19 cents 51.3% / -4.3%; under 10 cents 51.1% / -2.9%. Bigger move = more
  right straight up, same loss at the close. The ONE cell that holds: NHL 10-19 cent moves, the moved-to side +5.0% at
  the close (n 1,142, 3 of 4 seasons; the dogs in it +8.8% on 589, 4 of 4, SE 4.5) - the same NHL sharp-dog lead the
  10/1 study wired at +1 on the dog score (sharp_dog), seen from another angle; out of ~120 cells here, one at 2 SE is
  what luck gives. LEAD, no more weight.
- **Football, the paid time-stamped history (first FAIR look of the week -> close, 2020-26):** NFL (1,496 games) the
  moved-to side won 57.2%, +9.0% at the first look (6 of 7 seasons up for dogs moved to by 20+ cents: +22.7% on 416),
  +1.3% at the close (3 of 7); 20+ cent moves +2.8% at the close (5 of 7, SE 3.4) - the NFL is the one sport where
  following a big move at the close is about breakeven, not a bet. College football (3,043): the moved-to side 51.3%,
  +0.7% at the first look, -7.0% at the close, 1 of 7 seasons; dogs the money came to -9.1% at the close, 0 of 7 for
  20+ cents (-15.7%). College money is NOT sharp: the 20+ cent college move loses at every price. SPREADS (the side
  the number moved toward): NFL covers 55.6% at the early number (+6.0%, 6 of 7 seasons; 2+ point moves 60.6% /
  +15.7%, 3+ points 60.0% / +14.8%, 7 of 7) but 50.5% at the close (-3.3%) - the known hindsight prize, nothing to bet
  after the move; college 53.5% early (+2.2%), 49.8% at the close.
- **The split signals (money % vs tickets %, 2024+, 24,103 games):** at the close, EVERY one loses: 70%+ of the
  tickets (ride the public) -4.0% on 17,055 (0 of 4 seasons) and fading them -10.0%; money 10+ over tickets -10.3%
  (dogs -13.6%; college hoops -26%); money 20+ over -12.9%; reverse line move (line to it, under half the tickets)
  -3.8% on 4,444 (hindsight at the open +11.1%); RLM vs a 65%+ public with money 10+ over -9.4%; "money on it but the
  line ran AWAY from it" -8.0% at the close. The sharp dog (dog, line to it 2+, money 10+ over tickets): -10.8% on 991
  overall, 0 of 4 seasons - ONLY the NHL version wins: +14.5% at the close on 182, won 50.0%, 2 of 2 seasons (the 10/1
  lead, +14.3% on 190 - the same games). Live lead tracker since 10/1: money 10+ over tickets 22-26 (-5.2%), 70%+ of
  tickets 46-25 (-5.3%), reverse line move 8-5 (+27.5% on 13), sharp dog 2-4. The rigged.json cells say the same.
- **OUR SPOT - the engine's side when the line then runs AGAINST it 15+ cents (the NMSU case):** blind proxy, every
  sport, opener -> close 2023-26: 11,032 engine sides; the 2,522 the market ran 15+ cents against won 38.0%, -16.1% at
  our (opening) price, -4.3% at the close; the 3,866 the market came TO won 52.9%, +11.3% at the opener. The move
  carries real information about our side: when the money leaves it, it was usually a bad side (NFL -19.8%, NBA
  -22.7%, college hoops -12.7%, NHL -8.2%, MLB -18.7% at our price; dogs -16.7%, favorites -14.1%). College football
  at the FIRST look of the week (the real early-play moment, 2020-26) is the one exception: the 180 engine sides the
  line ran 15+ against won 48.9%, +5.3% at our price (SE 8.4) and +18.6% at the close (4 of 7 seasons at the close;
  dogs +4.6% at our price / +18.4% at the close on 109, 6 of 7; 2026 -50% on 6); the NFL version -23.6% at our price
  (won 34.5%, 2 of 7). At the price we actually get the college number is breakeven inside one SE - a fair fight, not
  an edge; the NFL and every other sport say the money leaving our side is bad news.
- **The 10/6 "college dogs the money ran against overnight won 48.6% +18.4%" - RE-CHECKED AND THE WORDING WAS
  BACKWARDS.** The 10/6 code's "ran against" bucket is the dog whose price got SHORTER overnight (cents(morning) -
  cents(night) <= -20) - that is the money coming TO the dog, not leaving it. On every season (2020-26, the paid
  history): the engine's college dogs the money came TO overnight (20+ cents shorter): won 47.1%, +24.0% at the night
  price / +12.1% in the morning on 51 (4 of 7 seasons); the dogs the money LEFT overnight (20+ cents longer - the NMSU
  shape): won 27.8%, -29.7% at the night price on 36 (2 of 6). Every college dog, not just the engine's: money left it
  15+ -> 37.6% won, -4.3% at the night price (125); money came to it 20+ -> 40.7%, +7.2% (113). NFL the same sign
  (engine dogs the money left 20+: 40.9% won on 22; the money came to: 30.0% on 20 - too few). The 10/6 text in that
  section is corrected below in place.
- **Our real picks (64 graded moneylines since 9/27):** posted vs close -1.1 cents on average (the market neither
  comes to us nor leaves us yet); only 1 pick ran 15+ cents against us (lost). The pending early plays: NMSU +180 ->
  +195 now (the money left, 15 cents), Iowa +120 -> +142, NC State +124 -> +145 (the money left); Alabama +130 -> -122,
  Florida St +215 -> +150, Tulane +205 -> +140, Falcons +120 -> -170 (the money came to us, big). Too few to grade.
- Five checks on "follow sharp money at the close": (1) fair YES, (2) blind YES (fixed rules), (3) most seasons NO
  (0 of 4 overall), (4) this season NO, (5) second check - the splits and the game files agree it loses: DEAD (as
  10/1 found). On "the NHL 10-19 cent / sharp dog": LEAD (already wired at +1). On "a college early dog the money
  leaves is fine": (1) YES (2) YES (3) at our price 3 of 7 (4) 2026 NO (5) the overnight cut says the opposite sign:
  NOT PROVEN - the early plays keep their rules (a dog the money ran 50+ cents out all week stays a fade, 10/1).
- VERDICT for the owner: sharp money is "right" about 55-57% of the time straight up because it mostly lands on
  favorites, and the opener-to-close move does predict the game - but the only price that pays is the one BEFORE the
  move. Following it at the new price loses ~5% in every sport (hockey the exception, about even). Our early plays go
  against the money by design: we bet the first number. When the money then leaves our side it is usually a worse
  side (every sport but college football, where it's a coin flip) - which is why the early plays keep their fades and
  their records, and why a line running against us is a flag to look at, never a reason to chase the other side.

## 10/6 - post the UNIT PLAYS at 8 PM the night before, or keep 8 AM on game day? (the owner: "we want the best lines and accurate picks"; report only)
tools/night_vs_morning_study.py -> results/night_vs_morning_study.json. No paid re-pull, no network. The engine's side
is the same BLIND proxy as the hockey timing study (sports_model tuned only on the 3 seasons before, injuries / key
zeroed, side = own read beats the no-vig price at that moment by 3%+, price -150..+220). "Night worth" = ROI of the
night board at the night price minus the same bets at the morning price. What the repo holds, honestly:
- FOOTBALL: the paid time-stamped history (2020-26) has the 8 AM look (NFL Sunday ~7 AM PT, college Saturday ~6 AM
  PT) but NO 8 PM-the-night-before look - the nearest earlier snapshot is Saturday 10 AM PT for an NFL Sunday game
  (24 hours before the morning look) and Thursday 10 AM PT for a college Saturday (44 hours). So the football
  "night" below is EARLIER than a real 8 PM post: it carries more overnight-news risk than 8 PM would, and the price
  gap is an upper bound on what 8 PM gets.
- Our own hourly snapshots (line_history, since 10/1): a REAL 8 PM PT vs 8 AM PT vs close - NHL 27 finished games,
  MLB 7, NFL 14, college 86. NHL + MLB game files 2023-26: the opener (NHL ~38h ahead; MLB ~2 days - our first
  snapshot sits a median 49 hours out and matches the file's open in 1 of 7 games) vs the close.
- Our 20 real posted picks with an 8 PM price in the hourly history (10 unit plays). NFL injury reports with a time
  stamp (nflverse) for "a QB ruled out between the two looks". No timed goalie or starting-pitcher history anywhere.

**A. PRICE.**
- **NFL (1,556 games; the engine's night sides 641):** nothing to gain. Its side got LONGER by morning (+0.9 cents,
  SE 0.5; morning longer 40% / shorter 41%); ROI at the night price -7.7% vs -7.6% at the morning price -> night
  worth -0.1% (SE 0.2), every season inside ±0.7%. Favorites (124) -0.3%, dogs (517) -0.1%, the 6%+ reads (486)
  0.0%. The market in the play band moves 0.0 cents overnight (1,417 sides). The only overnight money is on big
  favorites past -150 (all favorites -7.7 cents) - never on the board.
- **College (3,376 games; night sides 875):** a little, dogs only. The engine's dogs (671) get SHORTER by morning
  (-1.5 cents, SE 0.5; shorter 49% / longer 36%): ROI at night +0.4% vs -0.6% at the morning price -> +0.9% (SE 0.3),
  5 of 7 seasons (2021 -1.1%, 2026 -0.3% on 29). Its favorites (204) go the other way: LONGER by morning (+1.2
  cents) -> night worth -0.9% (SE 0.4), 0 of 7 seasons up. Remember the night look here is Thursday - a Friday 8 PM
  post would sit between the two, so figure about half.
- **NHL:** the opener -> close (4,152 games 2023-26, engine sides 1,612) is -6.5 cents / +2.6% for early (the 10/6
  hockey entry, 3 of 3 full seasons). The new piece is WHERE in the day it happens - our 27 hourly games, the
  favorite's signed move: open -> 8 PM -3.1 cents, 8 PM -> 8 AM -4.8, 8 AM -> close -3.1 (sizes 12.5 / 7.0 / 7.8) -
  the overnight leg is about 40% of the whole move, so an 8 PM post is worth roughly +1% ROI on the engine's sides
  IF the seasons hold. This season they don't yet: the engine's 17 hourly sides got LONGER overnight (+3.9 cents,
  longer 53% / shorter 6%, night worth -1.1%), and our 20 real picks with an 8 PM price closed the same way -
  the posted (8 AM) price was LONGER in 9, shorter in 2, +2.2 cents (the 10 unit plays +1.7); ROI at the 8 PM
  price -17.1% vs -17.4% as posted. 8 AM has been the better hockey price so far this season.
- **MLB:** opener -> close (9,854 games 2023-26, engine sides 4,878): -4.0 cents, early worth +1.6% (SE 0.15),
  4 of 4 seasons (2.1 / 1.8 / 1.4 / 1.0 - shrinking); favorites +2.2% (4/4), dogs +1.4% (4/4, 2026 +0.2), 6%+ reads
  +2.3%. BUT that opener is ~2 days out, and the 7 hourly games say the overnight leg is the quiet one: the
  favorite +4.9 cents 8 PM -> 8 AM, then -11.6 from 8 AM to first pitch (lineups / pitchers) - a move both posting
  times catch. The engine's 6 hourly sides: -6.0 cents overnight (all 6 shorter), +2.7% - six bets.

**B. ACCURACY / OVERNIGHT NEWS (what happens to a night pick between the two looks).**
- **NFL:** small share, real cost. The side ran 20+ cents against between the looks on 4% of night picks (23): they
  won 26%, -29%. A QB RULED OUT overnight on our side: 6 of 641 (1%) - 0-6, all lost; their QB out: 3, all lost
  too (the market re-priced past us). Any player ruled out overnight on our side: 8% (51), 31% won, -24.6%. A night
  pick the morning price no longer justified (48): -20.7%; a side only the morning price made a pick (49): -12.6%.
  The whole night board -7.7% vs the whole morning board -7.1% - the morning board is the (slightly) better board,
  and the 24-hour football "night" gap is wider than 8 PM -> 8 AM would be. Real-season check: the 14 NFL games in
  our hourly history - 0 overnight 20+ moves on the engine's sides, in-band games moved 20+ overnight 7% of the
  time.
- **College:** the opposite sign - [CORRECTED 10/7, tools/sharp_money_study.py: the code's "ran against" bucket is
  the dog whose price got SHORTER overnight = the money came TO it; the labels below were backwards] a dog the money
  CAME TO overnight (20+ cents shorter; 8%, 70) WON 48.6%, +18.4% (SE 15) at the night price; the ones the money LEFT
  (20+ cents longer; 6%, 53) lost -27%. College overnight moves are news: the morning number knows which dog is live.
  Night board -2.2% vs morning board -2.4%: no accuracy lost.
- **NHL:** 12% of in-band games move 20+ cents overnight (27 games). The engine's side "ran against" 20+ open ->
  close on 25% of its 2023-26 sides - and those WON (55.6%, +13.2% at the open): the market coming toward us, not
  bad news. Goalies: no timed history; the goalie file stamps its confirmations 8 AM - noon PT on game day (10/6: 8:16 - 11:36 AM) - at 8 PM
  nothing is confirmed, and the 10/6 study saw no goalie bump in the 9 AM - 1 PM window. Risk unmeasured, not zero.
- **MLB:** 0 of 7 hourly games moved 20+ overnight; no timed pitcher-change history. Open -> close "ran against"
  16%: +3.7% at the open (same market-comes-to-us pattern).
- Five checks on "post at night": (1) fair - every football night look is after both teams' last games (ef.fair),
  the NHL / MLB openers too: YES; (2) blind YES; (3) most seasons - NFL NO (flat), college dogs 5/7, NHL 3/3,
  MLB 4/4; (4) this season - college dogs -0.3% (29), NHL the other way (17 + our 20 picks): NO; (5) second check -
  our hourly history agrees for football (nothing overnight), DISAGREES for hockey. A timing LEAD for college dogs
  and NHL favorites, nothing more. Nothing changed: posting times, picks, weights, units all as they were.

**VERDICT, plain words:**
- **NFL: keep 8 AM.** There is no better line at night for the sides we take (±1 cent), and the night carries the
  QB-out / ruled-out risk that cost every one of those picks.
- **College football: keep 8 AM for favorites / Locks (they get longer by morning, 0 of 7 seasons up at night);
  dogs could go up the night before** for about +0.9% on ½u plays (5 of 7) - worth pennies, not a rule change yet;
  this season says no (29 dogs, -0.3%). If anything, a Friday-night college DOG board, favorites in the morning.
- **NHL: not yet.** Three seasons say the market comes to our side overnight (~40% of a +2.6% early edge = ~+1%),
  this season's 27 games and all 20 of our real picks say the 8 AM price has been better, and no goalie is
  confirmed at 8 PM. Re-run when the hourly history has 300+ NHL games (early November) - a dog is never hurt by
  waiting, a Lock / favorite might be.
- **MLB: keep 8 AM** (season's over anyway): the early edge is real over 4 seasons but it lives in the opener, not
  the 8 PM -> 8 AM leg; the big move is 8 AM -> first pitch and 8 AM catches it. Re-check in April with the hourly
  history.
- NEXT: no new logging (the owner, 10/6: pick-price timing logs "take years") - the hourly history already holds
  every pick's 8 PM price, so re-running this script grades OUR picks (part 4) as the season fills in; re-run with
  300+ hourly NHL games (early November) and again in April for baseball.

## 10/6 - WHEN to bet our hockey picks: at the 8 AM board or closer to puck drop? (the owner's question; report only)
What the repo holds for hockey (honest inventory): the paid odds history (data/sports/odds_history) is FOOTBALL ONLY -
there is NO book-by-book, time-stamped hockey price history anywhere in the repo, so "best book on hockey dogs" (part 4)
can't be answered from what we hold. What CAN be: (a) every NHL game's OPENING and CLOSING moneyline, 2023-24 on
(4,152 games, 8,304 sides; the 10/6 check against our own hourly snapshots: the NHL "open" is the price up ~38 hours
before the game, the overnight number, NOT a stale summer look-ahead like the NFL's); (b) our own hourly snapshots
(data/sports/line_history, NHL from 10/1/2026 - 35 finished games so far, the only intraday hockey history we have);
(c) our 11 real posted NHL picks' post price vs the close (moves.json). tools/nhl_bet_timing_study.py ->
results/nhl_bet_timing_study.json. "+ cents" below = the side got LONGER by the close (waiting would have paid more).
- **The whole market, opener -> close (2023-26):** favorites get bet during the day, dogs drift longer: favorites -3.2
  cents (SE 0.5; shorter 52% / longer 44%), dogs +2.1 (SE 0.4; longer 51% / shorter 44%). Biggest: AWAY favorites -7.8
  cents (shorter 63% of the time, n 1,306) and HOME dogs +5.3 (longer 61%, n 1,486); home favorites / away dogs barely
  move (-1.0 / +0.4). By band: -101..-150 -2.2, +100..+150 +1.6, +150..+220 +2.4. But NOT every season: 2023 and 2024
  favorites -4.3 / -7.5, 2025 the other way +2.4 (dogs -2.0), 2026 so far favorites -8.8 (39 sides). The typical move
  is real money: median 15 cents, 75th pct 26, 90th 41; 67% of sides move 10+ cents, 39% move 20+. For a RANDOM side
  the timing is worth nothing (ROI at open -4.3% vs at close -4.5%).
- **The engine's sides (BLIND proxy - sports_model tuned only on the 3 seasons before, injuries / key zeroed, side =
  own read beats the no-vig OPEN by 3%+, price -150..+220; 1,612 sides):** the market comes TOWARD us by the close -
  our side got SHORTER 60% of the time, -6.5 cents (SE 0.6), +1.16 pts of no-vig price. Betting at the open: ROI -1.3%
  (SE 2.6); the same bets at the close -3.9% -> **early is worth +2.6% ROI, and the sign held 3 of 3 full seasons**
  (2023 -7.1 cents / +2.6% for early, 2024 -5.5 / +2.5%, 2025 -7.5 / +2.9%); 2026 so far 27 sides +2.4 cents (the
  other way, SE 4.2 - too few to say). Dogs the engine likes (1,049): -4.9 cents, early worth +2.8%; favorites it likes
  (563): -9.6 cents, +2.1%; the bigger the read's edge the faster the market closes it (edge 6%+: -9.3 cents, early
  worth +4.0%). Every band: -101..-150 -9.2, +100..+150 -4.3, +150..+220 -6.1. Read: when the engine's read disagrees
  with the opener, the close moves our way about 1.2 pts - the read carries real information and the books catch up
  during the day. NOTE this is NOT a winning record: even at the open these sides lose -1.3% (the vig), it's only that
  the close is worse.
- **How much of that is left at 8 AM?** Our hourly snapshots (35 games): the first-snapshot->8 AM move averages 13.2
  cents, the 8 AM->close move 7.4 - about 65% of the day's move is in the price by 8 AM. So the 8 AM-to-close part of
  the engine-side edge is roughly a third of the open-to-close figure: around +1% ROI for betting at the board, not
  +2.6%. Over the 35 games: dogs +2.8 cents 8 AM -> close (longer 42% / shorter 17% / same 42%), favorites -4.0 (same
  pattern as the seasons).
- **Our 11 real posted NHL picks (post ~8 AM -> close):** the SIX unit plays (all dogs: Kings +160->+170, Blackhawks
  +180->+190, Blues +154 same, Flyers +110->+114, Predators +114->+120, Sharks +145->+170) ALL got longer or stayed -
  +9.2 cents avg, 5 of 6 longer, 0 shorter; the 5 leans/favorites closed where they posted. The OPPOSITE of what the
  blind proxy says the engine's sides do - and three of the six sat inside the proxy's own rule (own read 3%+ over the
  price: Flyers 53.8% vs 47.6% at +110, Predators 52.9% vs 46.7% at +114, Sharks 46.7% vs 40.8% at +145 - all three
  drifted longer, the Sharks 25 cents). Six bets can't overturn 1,612 sides over 3 seasons, but they are the real
  board, early in the season (opening-week lines are thin - 2026's 27 proxy sides also moved the other way), and they
  say the market has NOT been coming toward our dogs so far this season.
- **The morning goalie-confirmation window (9 AM - 1 PM PT, 34 games):** the price moved in 26% of games (all of them
  5+ cents), 6 toward the favorite / 3 toward the dog, favorite avg -1.4 cents; the five hours BEFORE 9 AM moved
  59% of games. No visible goalie bump in this sample (goalies are mostly known by the morning skate; the big
  overnight moves are the opener settling). Too few games - re-run in a month (the snapshots grow every day).
- Five checks, on "bet the engine's side early, it gets bet into": (1) fair - the opener is up ~38h ahead, after both
  teams' last games in nearly every case, and the engine's read uses only past games (YES); (2) blind YES (walk-
  forward, game-day inputs zeroed); (3) most seasons YES (3 of 3 full seasons, +2.5% to +2.9% each); (4) current
  season NO / too few (27 sides, the other sign); (5) second check: our own 35-game hourly history agrees on the
  market pattern (favorites bet, dogs drift) but our 6 real dog plays went the other way - MIXED. A LEAD on timing,
  not an edge in picks. Nothing built, no change to picks / weights / units / the 8 AM post.
- **VERDICT in plain words:** it depends on the side. (1) A hockey Lock or any FAVORITE on the board: bet it AT 8 AM.
  Favorites get bet during the day in 3 of 4 seasons (away favorites shorter 63% of the time), and the favorites the
  engine's read backs got 9-12 cents worse by puck drop in every full season. (2) A hockey DOG (the Dog of the Day,
  a plus-money value play): the two pieces of evidence disagree. Three seasons of history say a dog our read backs
  gets bet into (5 cents worse by the close, about a third of that still ahead at 8 AM - worth about 1% of the stake
  for betting early). The market as a whole, our 35-game hourly history and ALL SIX of our real dog plays this season
  say dogs drift LONGER through the day (home dogs +5 cents, longer 61% of the time; ours +9 cents, none shorter). So
  for a dog there is little to lose by waiting - the honest answer right now is "bet it at 8 AM if the number is the
  one you want, and if you wait, wait for a HOME dog or a dog facing an away favorite, where the drift is biggest" -
  and let the live journal settle it (a dog's price at 8 AM vs its close on every pick we post). Either way the
  engine's record grades at the posted price; this is about the owner's own ticket. Never wait on a number that is
  already running: the typical NHL side moves 15 cents and 4 in 10 move 20+.
- NEXT: add the price at post time vs the 8 AM / 10 AM / 1 PM / close marks to every pick's journal row so this
  grades itself on OUR picks (the real test), and re-run tools/nhl_bet_timing_study.py when the hourly history has 300+
  NHL games (early November).
## 10/6 - NHL: who's in net - the confirmed starter, and the goalie-roles dog spot (BUILT; the owner OK'd the build)
- THE SOURCE: Daily Faceoff's public starting-goalies page (a plain request on GitHub's servers, read only -
  sports_goalies.sync, every hourly run) - per game both goalies with the page's own word: Confirmed / Likely /
  Unconfirmed, plus the news line and its source. ESPN's game summary has no probable-goalie field; the NHL schedule
  feed names only the WINNING goalie after the game; ESPN's scoreboard "probable" (our sp_home / sp_away) is pre-filled
  days ahead (it was right 96-98% of the time on finals, but that's measured after ESPN swaps in the real starter) - a
  guess, never read as a confirmation. Saved in data/sports/nhl_goalies.json with the time seen; stale after 8 hours =
  unknown again. Unknown = no weight, no line, never a guess.
- THE RE-CHECK (blind, tools/goalie_roles_study.py: our box scores 2018-27 - the one goalie row a team-game is the
  starter, the closing price, dogs +100..+220; "#1" = most starts in the team's previous N games THIS season, 6+ held,
  a clear leader; the actual starter stands in for what a confirmed starter becomes): every dog -4.0% on 8,050. The
  dog starting its #1 vs a favorite NOT starting its #1 (N=10): +1.5% on 1,098, better than all dogs 7 of 8 seasons,
  2023-24 +16.7% / 2024-25 +7.1% / 2025-26 +7.1% (vs -3.8 / -5.7 / +2.9) - about +10 pts on 439 the last three.
  N=12: -1.7% (+2.3 pts, 5 of 8); N=15: -2.2% (+1.8, 4 of 8) - the role is a recent thing, a 10-game window it is.
  t about 0.3 overall - a LEAD-sized weight, not an edge. THE REVERSE (favorite with its #1, dog without): -4.8% vs
  -4.0%, better 5 of 8 - noise. Both #1: -4.7%; neither: -4.2%.
- BUILT: sports_goalies.ROLE_W = +2 on the Dog's score (dog_spots, inside STUDY_CAP) when BOTH starters are known
  (confirmed or likely) and the dog's is its #1 while the favorite's isn't; the favorite across from it is weighed
  down through mark_hockey_favorites (½ pt per point, inside NHL_FAV_CAP). The reverse ROLE_W_REV = 0 (nothing to
  weigh). The hot / slumping-goalie and goalie-rating weights (sports_form.hot_sides, sports_players.key_edges, the
  breakdown's goalie line) now read the CONFIRMED / likely starter when known instead of the last starter
  (sports_players.starter_for). The card names a starter only when CONFIRMED (🥅 In net: ... — their #1, 8 of their
  last 10 starts / not their usual #1); a goalie confirmed after a hockey pick is posted shows on the card like an
  injury alert (sports.key_status / injury_watch) - no phone ping, the pick never changes on its own. Tests:
  sports_test.test_goalie_*.
- JUDGE: its own live tally comes out of the pick journal (g_role_me / g_role_opp on every hockey candidate); 150+
  dogs with the spot before it's called anything but a lead.

## 10/6 - MLB: the PITCHER has this team's number / "they just saw him" (the owner; the pitcher-level version of 10/5)
Data: every MLB starter's line 2017-26 (data/sports/players/mlb.csv - both starters in 23,252 of 23,254 non-spring final
games, 99.6% match the game file's listed starters), closing moneylines 2018-26 (the last price before first pitch =
same-day prices, FAIR by construction), 40,156 priced pitcher-sides. History strictly BEFORE each game, nothing fit, no
model = BLIND by construction. tools/mlb_pitcher_vs_team_study.py -> results/mlb_pitcher_vs_team_study.json. 18 cuts
counted (one of them post-hoc, marked). Baseline: every pitcher side at the close -3.5% (the vig).
- **Angle 1, his history vs this team** (3+ past starts vs them, 15+ starts overall; his runs allowed per 9 vs them,
  shrunk 5 starts toward his own normal, minus his normal): the correlation with beating the price is -0.02 on 16,165
  (the team-level 10/5 number was -0.01) - the WRONG sign. Quintiles, his side at the close: most crushed by them
  51.9% vs 50.4% implied (-1.2%), neutral 53.1 vs 52.0 (-1.5%), most dominant 49.8% vs 51.4% implied (-6.8%, 3,233
  each). "Dominated them" (2+ runs better, A1) only 13 cases 6-7, -15.5%; 1+ run better (A3) 1,380: 48.9% vs 51.3%,
  -8.2% (SE 1.3), 3 of 9 seasons up, 2024 +11.5% / 2025 -22.3% / 2026 -8.1%. "Crushed by them", bet the lineup (A2,
  294): 50.7% vs 51.8%, -5.6%, 3 of 9 up; looser (A4, 1,782) -5.1%, 1 of 9 up. The books price the pitcher's overall
  quality (his team 53.2% implied when he's better than the league, 46.6% when worse) and his record vs this team adds
  nothing - if anything it reverts. POST-HOC fade (A3r - bet the lineup against the dominator, 1,380): 51.1% vs 48.7%
  implied, +1.7% ROI, SE 1.3 (t 1.8 - expected by chance across 18 cuts), 6 of 9 up, last 3: 2024 -20.4% / 2025
  +12.2% / 2026 +3.1%. Noise after that many cuts; not a lead.
- **Angle 2, "just faced them"** (his previous start was vs this same team - 2,136 priced; 1,897 with 15+ starts):
  the pitcher DOES pitch worse the second time - 4.72 runs per 9 vs 4.39 expected from his own last 10 starts (+0.33 a
  game; never faced them 0.00, neutral history +0.05, faced them within 14 days but NOT the previous start -0.08 on
  988). So the hitters-just-saw-him effect is real, about a third of a run - and the market has it: his side 49.0% vs
  50.1% implied, -5.6%, 0 of 9 seasons up; the LINEUP that just saw him 51.0% vs 49.9% (+1.2 pts, SE 1.1), -1.0% ROI,
  3 of 9 up, 2024 -11.1% / 2025 -8.6% / 2026 -6.7%. Within 14 days any start (B2, 2,865): his side -4.3%, the lineup
  -2.7%. Playoff rematches (B3, 134): his side 47.8%, -6.8%.
- **Cousins:** revenge (they scored 5+ on him last start, C1, 344): 47.4% vs 47.2%, -3.0%, 5 of 9 up (2022 -40%, 2026
  +15.7% on 25 = noise). He shut them down last start (<=1 run, 6+ IP), his side again (C2, 381): 50.7% vs 53.9%,
  -8.4%; the lineup bounces back (C2r): 49.3% vs 46.1% (+3.3 pts, SE 2.6), +5.0%, 4 of 9 up, 2025 -18% / 2026 -9.7% -
  the last two seasons say no. They crushed him 6+ in the last meeting within a year, not a rematch (C3, 1,752): -0.3%,
  4 of 9. Rematch and his team LOST the last meeting (C4, 1,050) -2.6%; WON it (C5, 1,086) -8.5%.
- VERDICT: DEAD, like the team-level version - both the pitcher-vs-team history and the rematch. Five checks on the
  best-looking cut (C2r / A3r): (1) fair YES, (2) blind YES, (3) most seasons NO (1 of 3 / 2 of 3 last three, 4-6 of
  9), (4) current season NO / barely (-9.7% / +3.1%), (5) second check NO - and both are 1 of 18 cuts. The one real
  finding is for the WRITE-UPS, not the picks: a starter facing the lineup he just faced gives up about a third of a run
  more than his norm, and the price already carries it. Nothing built, no weight, no units.

## 10/6 - siding with Dr. Bob (the owner: "run a blind study on all the games the engine sides with Bob Stoll - are we profitable on them?" and should his agreeing raise our confidence / units?)
Data: his archived free NFL analysis pages (web.archive.org snapshots of drbobsports.com/nfl-analysis, 35 that fetched,
2019-25; 19 carry free picks - the rest were paywall / no-play weeks, several 2023-25 fetches failed or cut off at 30,000
chars). Every free SIDE (Lean / Strong Opinion / Best Bet / bare "TEAM (-3) over OTHER" headline) read with his number,
matched to our game, counted once; totals, team totals, teasers, props skipped. The ENGINE's read is blind (spread model
fit on the 3 seasons before, Elo chronological, game-day injury inputs zeroed) and its side = where that read sits against
the real CLOSING spread. Graded ATS at the close, -110 (and at his number / price). tools/drbob_study.py -> results/drbob_study.json.
- THE CLEAN SET (pages saved BEFORE kickoff - 31 sides: 2020 2, 2021 7, 2022 8, 2023 1, 2024 13, 2025 0; 28 Leans +
  3 headlines, NOT ONE of his Best Bets / Strong Opinions - those pages were all saved after the games):
  Bob alone 14-15-2 (48%, SE 9) -2.3u, 2 of 5 seasons up. ENGINE SAME SIDE 6-7-1 (46%, SE 14) -1.5u (at his number
  5-8-1, -3.5u). Engine OPPOSITE him 8-8-1 (50%) -0.7u (at his number 9-7-1, +1.2u). Same side AND engine 2+ pts off
  the close 4-3-1; same side under 2 pts 2-4. Where he printed his model's number (18): both models his way 4-4-1,
  his model alone 3-5-1. Engine alone on every game those weeks 112-112-2 (50%, -4.5%); its 2+ pt edges 76-58-1
  (56.7%, SE 4, 5 of 5 up - the known engine-vs-the-line lead, nothing new).
- The LOOSE set (every parsed pick, 70 - adding 39 from pages the Wayback Machine saved the Monday AFTER the games;
  his pre-game text, but nothing proves it wasn't touched, so it can't count): Bob alone 41-26-3 (61%) +16%; his Best
  Bets / Strong Opinions 13-4 (all from after-the-fact pages); engine same side 15-13-1 (54%) +2%; engine opposite
  26-13-2 (67%) +26%. The late pages run 27-11 against the clean pages' 14-15 - the gap itself says treat them as unverified.
- VERDICT: DEAD as a confidence / unit signal, and far too thin to be anything else. On the one clean set, "the engine
  agrees with Bob" went 6-7-1 (SE 14 points - a 20-point swing either way is noise) and his free Leans themselves lost
  (14-15-2); his own site calls the free Leans his coin-flip tier (the paid Best Bets are the 57.5% product, and we
  hold none of those pre-game). The engine opposite him did no worse than with him. Five checks: (1) fair prices YES
  (real close, no look-ahead), (2) blind YES, (3) most seasons up NO (2 of 5), (4) current season NO (0 clean 2025-26
  picks here; the live tracker has 5 graded sides), (5) second check NO. Zero of five on the thing that matters. Nothing
  built - no weight, no unit bump; the live tracker (sports_capper) keeps the clean 2026 record, judge it on a season.
- Parse bug found and fixed (sports_capper.parse, regression test): "Lean – Over (51.5) – CINCINNATI (-2.5) vs
  Jacksonville" is a TOTAL lean naming the matchup ('vs' - his side leans say 'over'); the tracker had logged the
  Bengals -2.5 and Chiefs -4.5 (10/4) as side leans (both 'lost'). data/sports/capper_drbob.json still holds those two
  rows - the owner's call to drop them (his real 10/4 sides: Arizona -2.5 lost, Rams -3.5 won).

## 10/5 - "a team has another team's number" (the owner: Hurts 5-0 vs the Rams), every sport, closing prices
- For every game with 3+ meetings in the last 5 years: how much each team beat (or fell short of) the PRICE in the last
  6 meetings, then betting the side that "has their number" at the close. DEAD everywhere: the past over-performance
  vs the price predicts nothing next time (correlation +0.02 NFL, +0.01 college, +0.01 NBA, -0.01 NHL, -0.01 MLB,
  +0.01 college hoops - on 854 to 21,335 games). Betting it: NFL -2.3% (big edge +9.4% on 143, 4 of 6 seasons, t 1.0 =
  noise), college -3%/-7%, NBA -4.5%, NHL -4%/-10% (0 of 8 seasons), MLB -4%/-5%, college hoops -5%/-6%. A team that
  "owns" another already shows up in the price (the books know Hurts is 5-0); the style-matchup version (pass O vs
  pass D etc.) was dead on 10/1 too. Not built.

## 10/4 - NFL games out of the country (London / Germany / Mexico / Brazil...), 2016-26, our game files' intl flag
- 44 international games, 34 with a closing total / moneyline. UNDER 20-14 (59%), +12.5% at the close vs -1.7% for
  every NFL under (2,244). By season (unders-overs): 2018 3-0, 2019 3-2, 2021 1-1, 2022 2-3, 2023 5-0, 2024 2-3,
  2025 3-4, 2026 1-1 - up in 3 of 8, and only 34 games: WATCH, not proven, nothing built. Favorites +4.0% / dogs
  -12.2% on 34 (noise); the listed home team covered 17 of 33 (coin flip). Re-check each season; an early-morning
  international game kicks off before the 8 AM PT board, so a pick there would need its own earlier post.
- Why the unders hit (the owner, 10/4: "figure out why"), 34 games: Europe 18-10 under vs Mexico / Brazil /
  Australia 2-4 (warm night games went over); 9:30 AM ET kickoffs 16-9 vs later 4-5; total 44+ 13-7 vs under 44 7-7;
  cold (<50F) 7-2; rain 7-3; Jaguars games 7-2; Europe + morning + total 44+ 9-4. Wind and close spreads: nothing.
  Unders missed by 10 pts on average, overs by 7. Fits a body-clock / weather story (a 6:30 AM PT body clock, cold
  wet European fall), but every cell is 9-25 games - LEAD only; re-check each season, never weighted yet.

## 10/4 - banged up: a weight, not a block (the owner, 10/3: "just because a QB or a star is out or a team is too banged up doesn't necessarily mean no units. It all just depends.")
The question behind the 2+ out / 4+ questionable no-units rule (sports.hurt) and the 'more banged-up team' rule
(MAX_EXTRA_OUT): does a side missing regulars LOSE against its price? Our own box scores 2021-26 (NFL 2,912 team-games,
college 7,919 - every game with a box score, a closing price and prior-game regulars). A 'regular' = sports_absences.regulars
on the team's PRIOR games (no look-ahead: QB, top 2 ball carriers, top 4 catchers, top 11 tacklers over its last 3);
'missing' = not in the game's box score. Residual = win - closing no-vig price, flat 1u ROI alongside. Caveat: a tackler
with no tackle is also 'missing' from ESPN's box, so the counts run high on the defensive side (the 0-missing control
is small); QB / RB / WR are clean. The 10/3 board blocked ~15 college sides this way, Missouri (+180, beat Florida) in them.
- NFL vs the price: 2+ regulars missing -0.4 pts (n 2,035, SE 1.0; dogs +0.5, favorites -1.3) - THE MARKET HAS IT.
  By count: 1 missing +2.5, 2-3 -0.8, 4-6 +2.2, 7+ -4.7 (172, SE 3.5, 4 of 6). 2+ skill regulars (QB1 / top rusher /
  top-2 catchers) missing -3.7 (215, SE 3.1, 4 of 6) - a lead. By role: QB out -1.2 (470; as a dog -1.3), RB out +0.8,
  WR out -2.1 (494; dog -2.9, 4 of 6). The MORE banged-up side (2+ more regulars missing than the opponent): -2.5
  (667, SE 1.8, 4 of 6; the healthier side +2.6, 5 of 6) - a LEAD, under 2 SE.
- NFL vs the OWN read (Elo, default params, chronological; net of the 0-missing control): 2+ missing +0.9 (SE 1.1);
  no key player out but 2+ bodies missing +2.6 (1,120, SE 1.4) / 4+ missing +7.5 (231, 6 of 6) - the own read is NOT
  fooled by depth absences (if anything a team missing bodies and nobody key beats its read - a good team rotating).
  Key out (QB / RB / WR) -0.7 here (the 10/2 study's full-engine replay had the real size: QB -10.6 - already built).
- College vs the price: 2+ missing +0.1 (4,900, SE 0.6); dogs -0.6, favorites +0.8; by count 0 -1.1 / 1 +0.6 / 2-3 +0.5
  / 4-6 -0.6 / 7+ -0.2; the more banged-up side +0.2 (1,973, 2 of 6). QB out +0.2 (1,528), RB out -0.8 (dog -1.5), WR
  out -0.2 (dog -1.7, favorite +1.5). NOTHING - the market has every bit of it. (College dog ROI is -9% to -28% in
  every bucket, healthy or not - that's the vig and the long shots, not the injuries.)
- College vs the OWN read: 2+ missing -1.0 (4,900, SE 0.6, 6 of 6) but no-key 2+ missing +0.5 and 4+ no-key -0.1: the
  whole effect is the QB / RB / WR, already weighed (QB -3, two+ -5). Depth bodies: 0.
BUILT (football only, the owner's priority): with box scores to say who plays, the 2+ out / 4+ questionable block and
the 'more banged-up team' block are OFF in NFL and college football - sports.hurt returns nothing there; the depth gap
is a small capped weight on the OWN read: sports.depth_penalty - NFL ½ a point of win chance per regular more missing
than the opponent, cap 3 (sports.DEPTH_PTS / DEPTH_CAP); college 0 (the data says nothing is there). The card still
names who's out (injury_line); the key players keep sports_absences.penalty; a team with no box scores keeps the old
block (we can't tell who plays). NOT BUILT: a QB-out block (NFL QB-out dogs -1.3 vs the price - already weighed in the
dog score, -3, and in penalty); any weight in college (0); hockey / hoops / baseball untouched (not studied here - the
owner wants football first; their block stays). The early plays' 'never a side with a key player out or questionable'
stays: that rule is about a price taken days before the news lands (the owner, 9/30), which box scores can't test.
Watch live: the NFL 'more banged-up' lead (-2.5) and the 2+ skill regulars lead (-3.7) - if they hold on our picks, the
weight grows; if the own read's +2.6 on no-key depth holds, it may shrink to nothing.

## Built into the engine
- **Get in early - CORRECTED 10/1 (data audit):** the 9/30 numbers (NFL +8+ +24.7%, NBA +5.8%, NHL +8.9%) were graded
  at the "open" - and the NFL's open is often the SUMMER look-ahead line (Ravens opened -250, closed +265), a price the
  scan can never bet a week out. All of the NFL's edge was in dogs whose price ran 10+ points our way (+57%, 97% moved
  - stale opens); the rest lost -23%. The exam now grades only dogs the live scan could have taken (price not already
  run MOVED_MAX+ toward them - sports_early.bettable). Re-run: only MLB short dogs (+100..+149, own read +8..12)
  pass (+6.6% / +13.6%); NFL / NBA / NHL / college fail. MLB opens before 2023 = the close (no real open) - skipped.
  sports_early.py, re-examined 3x a day.
  The 5 early plays posted 9/30 under the bad exam (Jaguars, Predators, Blues, Flyers, Blackhawks) were pulled
  before their games with the owner's OK (10/1) - never graded, not in any record.
- **The Lock:** the priciest favorite under -150 is not the Lock. The engine's own read has to agree; 1,808 days:
  58.1% vs 56.8%, the only rule that made money. The books are sharp on favorites (7 seasons: no rule beats them).
- **Money running away from a dog** (NFL -40%, NCAAF -9%, NBA -8%, NHL -6% every season): weighed in the Dog of the
  Day. Hockey money coming IN on a dog: +6% / +15% (2 of 3 seasons).
- **Goalies:** the books overprice the better goalie - the dog WITH it -9% to -12%, the dog facing it +2% (NHL 2023+).
- **Playoff series spot:** a favorite that just lost the last game - baseball won 50% (-14%), NBA/NHL favorites facing
  elimination -15% / -19%. Wild Card Game 1 winners closed out 17 of 24; teams shut out in Game 1 went 0 for 5.

- **Unit sizing (9/30 - its 'at the opening price' numbers carry the same stale-open problem; quarter-Kelly by the
  edge stays, the +242u / +124u totals don't hold):** at the OPENING price, the bigger the engine's edge the
  more the line moves our way (NFL biggest edges: moved our way 80%, flipped to favorites 61%; NHL 78% / 39%; MLB 76% /
  31%) and the more money it makes - sizing early plays by the edge (quarter-Kelly, ½-10u) beat flat units: NFL +242u
  vs +20u, NBA +124u vs -18u, NHL +90u vs +57u, college football +72u vs -9u. Rest, home, season phase add almost
  nothing on top (a separate move model did worse than the edge alone). At GAME-TIME prices a bigger edge did NOT win
  more (sizing up lost more in every sport) - so game-day plays are flat 1u (slight lean ½u). College hoops and MLB
  early: sizing didn't help. Live plus money and tennis: no units (their own records).
  The daily Lock / Dog replayed (2,034 / 2,385 days): Lock won 58.1% but flat 1u broke even (-2u); sized by the
  engine's own read +141u (+2.3%, 5 of 7 seasons). Dog sized by its read vs the price +121u (+5.6%, 6 of 7). BUT the
  last 3 seasons were red for both however sized - watch the bankroll box; early plays are the real money-maker.

- **Tennis live: a set means more than the model said (9/30, ~69,000 tour matches at Pinnacle's close, fit 2012-20,
  graded 2021+):** a player down a set really wins less - women's "57%" was 50%, men's 57% was 52% - and up a set,
  more. Live plus money is almost always the player behind, so the engine kept over-rating the players it bet (tennis
  live 3-6, 7 of 9 women's). Built: sports_tennis_live.SET_FIX (lands on the real rate in every bucket, 2021+). Would
  have skipped Sonmez and Bondar (both down a set, both lost). Still unproven: first-set bets (no live-price history to
  test them) - watch the tennis live record.

- **Recent form (9/30, every player's box score 2021-now, closing prices, seasons never seen):** team form (last
  5/10 vs expectations) and win/loss streaks add nothing over the price in any sport. Player form: the books - and the
  public - OVER-rate a hot key player. The side whose goalie is much hotter (top 20%): worse than an average bet 5 of
  5 NHL seasons (-12.4% vs -4.0%); NBA stars 3 of 4 (-10.4% vs -5.1%). Backing the COLD side doesn't beat the vig
  either - it's a caution, not a bet. Built: sports_form (hot goalie / hot stars count against a pick: HOT_W in the
  Lock and parlay line, -3 on the Dog's score; form older than 3 weeks never counts). Baseball pitchers, QBs, college:
  mixed - not used. Coaches: no data yet.

- **The overreaction (9/30, form dug deeper, closing prices 2018-26):** win streaks, losing streaks and "hot scoring"
  vs the total mostly lose to the vig everywhere - but bettors overreact to ONE ugly loss / a cold run: football dogs
  off a BLOWOUT loss (college 30+, NFL 21+): college +11.6% (6 of 8 seasons, last 3 +31.6%), NFL +7.9% (last 3
  +23.2%) vs -3.6% for every dog; college hoops FAVORITES on a 6+ game losing streak +6.7% (7 of 8, last 3 +9.4%) vs
  -3.8% for every favorite. Built: sports_form.overreaction / sports.overreact (+3 on the Dog's score, a bump up the
  Lock / parlay line). Watch: college football dogs off a blowout WIN +9.2% (5 of 7).
- **Scoring drought (10/1, the owner's Red Sox point - every MLB line score 2018-26):** a FAVORITE that hasn't scored
  in 12+ innings in a row: +4.9% on 363 vs -3.8% for every favorite; at -150..-101 +10.2% on 217, better 7 of 9
  seasons. Bettors fade cold bats too hard. Dogs in a drought: -6.9% vs -3.3% (not steady - nothing built). Built:
  sports_form.DROUGHT (team_states counts scoreless innings; overreaction +1 -> a bump up the Lock / parlay line).

- **Fatigue (9/30, box scores 2021-26):** a RESTED dog facing a team that played last night: NBA +6.5% (4 of 5
  seasons), NHL +1.9% (4 of 5) vs about -6% for every dog. Built: +3 on the Dog's score (sports_form.last_starts /
  played_yesterday). A goalie on back-to-back nights, stars' heavy minutes, MLB tired bullpens and hot/cold lineups:
  nothing over the price.

- **Puck luck (9/30, NHL box scores 2021-26):** PDO (shooting % + save %, last 10 games): an UNLUCKY dog (<= 985)
  -0.9% (better than the -5.8% of every dog 4 of 5 seasons), a LUCKY dog (>= 1015) -10.3% (worse 4 of 5). Built: the
  Dog's score +2 / -3 (sports_form.pdo_states). NBA stars' shooting slumps / hot streaks and MLB starters' strikeout-
  minus-walk form: nothing over the price.

- **Upsets (9/30, closing prices 2018-26):** an NBA team that got upset as a -250 favorite bounces back - next game
  +4.9% as a favorite (6 of 8 seasons), +7.1% as a dog. A dog right after its +200 upset win is a HANGOVER as a dog
  again: NFL -30%, college football -28%, MLB -14% vs about -3% for every dog. Built: the bounce counts like the
  overreaction angle; the hangover -3 on the Dog's score. Road trips (4th+ road game, first game home) and NFL/college
  off a bye: nothing steady.

- **Cover streaks & revenge (9/30, closing prices 2018-26):** the public chases a cover streak - a team that FAILED to
  cover 4+ straight beat the average spread bet NBA 8 of 8 seasons, college hoops 6 of 8, college football 6 of 8
  (+2.9%), NFL 5 of 8; COVERED 4+ straight did worse (NFL -11.8%, college -10.7%). College football dogs facing the
  team that blew them out last meeting +15.7% (6 of 7). Built: sports.cover_run_w (spread picks up/back the line),
  +3 on the Dog's score for the revenge dog. Revenge in the other sports, blowout winners next meeting: nothing steady.

- **Coaching, round 1 - PULLED 10/1 (bad data):** ESPN's per-season coach list repeats TODAY's coach back through
  every season in the NFL / NHL / MLB / college football (Belichick at UNC in 2016) and is partly wrong in the NBA /
  college hoops (Mazzulla on the 2020 Celtics). Both weights below are OFF (sports_coaches.VET_DOG / NEW_FAV empty)
  until re-tested on real coach history. What it said (9/30, ESPN's head coach per team-season 2016-26, closing prices): NFL DOGS with a 10+ year
  head coach +10.6% (7 of 8 seasons) vs -3.5% for every dog, ATS +2.0% (6 of 8); a NEW coach's team as a FAVORITE is
  over-rated: NBA -6.2% (worse 7 of 8), college hoops -8.5% (7 of 8). Built: +3 on the Dog's score / back of the line
  (sports_coaches.states, sports.coach_w). A coach's past money vs the price: bounces season to season - not used.
  First-year head coaches: a bit worse everywhere, not steady. ESPN lists one coach per season (no mid-season firing
  dates yet). Styles (4th downs, pace, 3s): waiting on data/sports/teamstats to fill in.

- **New head coaches (10/1, the owner's Belichick-at-UNC point - college football hires with Wikipedia's "Previous
  position", 2022-26 seasons):** a FIRST-TIME head coach's first season, his team a +200 or bigger dog: +200..+399
  -40.0% (56) vs -6.7% for every such dog, +400+ -71.7% (81) vs -26.3% - worse every full season 2022-25. Small dogs
  (+100..+199) fine. A coach who's run a program before: about even (+3.1%). Built: -4 on the Dog's score
  (sports_coach_changes.first_timers / FIRST_TIMER_DOG). NFL looked the other way (retreads -14.4% as dogs vs
  first-timers +3.3%) on only 21 hires - not built. Belichick at UNC: 1-4 in the 2025 games we have, 2-1 in 2026.
  **10/1 later - TURNED OFF:** with the 2024-25 games the feed had missed put back (500 -> 888 / 498 -> 892), the
  first-timers' +200..+399 dogs made +28% in 2024 AND 2025 - it only held 2022-23. FIRST_TIMER_DOG = {}.
- **Mid-season firings (9/30, 153 changes 2016-26 from Wikipedia's season pages, closing prices):** a DOG that just
  fired its coach keeps losing in football and hoops - rest of the season NFL -28%, college football -30%, NBA -10.7%,
  college hoops -18.4% (every dog about -4% to -7%): the market prices a bounce that doesn't come. Hockey is the
  opposite: after a change the team beats its price (dogs -0.6% vs -5.4% rest of season; games 4-10 +7.6% / +4.5%).
  Built: -3 / +2 on the Dog's score (sports_coach_changes.recent). Smaller samples (~20-50 changes a sport) - weighed.
  Baseball (10/1, the owner's Red Sox point - 10-17, new manager 4/25, 77-58 after, +4.4% a game): over 21 MLB changes
  dogs after a change -7.0% (vs -3.3%), favorites +0.4% (vs -3.8%) - team by team all over the place. Not built.

- **Early-season hockey (9/30, lock-grade NHL favorites by week of the season, 7 seasons):** first 2 weeks 55.3%,
  -4.3% (3 of 7 up) - the ratings still lean on last year; weeks 3-4 64.9%, +11.7% (6 of 7); rest -1.0%. Built:
  sports.season_w (early hockey favorites move back the Lock / parlay line). Long run, NHL lock-grade favorites are the
  best of any sport (57.6%, the engine agreeing +1.5%) - a bad night isn't a broken sport. NBA: no early-season effect.

## Found, not built yet
- **Coaching styles, round 1 (9/30, each team's style from its EARLIER games that season, closing prices):** NFL
  4th-down aggressiveness, pass rate, pace: nothing steady (the books know who goes for it). College football: PASS-
  HEAVY favorites worse than every favorite 4 of 5 seasons (-14.5% vs -7.4%), run-heavy favorites better 4 of 5 -
  WATCH. Hockey: high-shot-volume dogs a bit better than every dog 4 of 4 (still losing). Hoops (only ~1 season of
  team stats so far): college 3-point-HEAVY dogs +6%, NBA slow-PACE dogs +5.7% (2 of 2) - high-variance styles making
  upsets; re-run once data/sports/teamstats fills in older seasons. (build before their season / playoffs)
- **NBA star out** (player data, 5 seasons): favorites facing a team missing its star -7.8%, every season (a trap);
  dogs missing their star -0.4% vs -9% for dogs at full strength; a favorite missing its star but with the DEEPER
  bench +4.6% (4 of 5), the dog version +10..18% the last 3 seasons (the owner's Nuggets point).
- **NBA / NHL playoffs - emotion is real:** the team that lost Game 1, as a dog in Game 2: NBA +28.2%, NHL +28.7%;
  dogs facing elimination NBA +10.9%, NHL +10.2%. (Baseball: the opposite - Game 2 is about the pitcher.)
- **Mid-size baseball dogs (+140..+199) the engine backs:** three different studies agree; weakened once starting
  pitchers were in (last 3: +0.7%). Watch.
- **Baseball playoffs (10/1, 404 games 2016-25):** a dog that just lost to the SAME team by 5+ runs: +27.5% on 37, up 6
  of 8 seasons - the blowout pushes the price too far. Regular season the same spot is nothing (+0.3% on 2,315), so
  only 37 games carry it - too thin to build. Every playoff favorite -8.9% (329). Bye-team rust: nothing (21 games).
- **College football big dogs** the engine likes by 12+: 2 of 3 seasons. Close.
- **EARLY FOOTBALL on REAL midweek prices (10/1, The Odds API history the owner paid for: 1,757 NFL + 4,175 college
  games 2020-26, median book, walk-forward - each season graded by an engine trained only on the 3 before it; graded
  on WINS at the price we'd have bet, per the owner).** tools/early_football_study.py, results/early_football.json.
  NFL: DEAD as a moneyline early play - the engine's own read beating the first price of the week lost at every gap
  (dogs -3..-8%, favorites -2..-8%), at every time of the week; the early price is only ~2 pts of ROI better than the
  close. (The 9/30 "+57%" was the stale summer opens - confirmed.) Close to something only: off a bye vs a normal week
  +18% on 59 (4 of 6) - but it vanishes when the engine agrees (+3%), so likely luck. College football: the engine's
  BIG reads (12+ over the first price) on dogs +11.3% on 508, up 4 of 6 - but 2024 and 2025 were flat (-1.5%, -0.2%):
  fading. Neutral-site dogs the engine likes by 4+: +17% on 106, 5 of 6 (small). Blowout winners last week (+4.4% on
  610, 5 of 6 with the engine). Bad spots: a CLOSE LOSS last week (-15% NCAAF / -13% NFL, the engine liking them
  even worse -23%), road favorites (NFL -12.6%, 0 of 6), home dogs in the NFL (-17%). Shopping the best book adds ~3
  points everywhere. (10/1 credits: a push-started re-pull burned ~7,400 - the pull is hand-run only now.) ~70 cuts per sport were tried, so a few "up 4 of 6" are luck - nothing posts off this alone.


- **🛌 THE EARLY-PLAY LEAD THAT HELD: A DOG OFF A BYE vs A TEAM THAT PLAYED (10/1, the 20 early studies -
  tools/early_sharp_books.py, early_ml_vs_spread.py, early_overreaction.py, early_juice.py, early_batch.py;
  results/early_*.json).** Bet the dog's moneyline at the FIRST FAIR number of the week (the middle book's price):
  NFL +29.4% on 48 (13+ days rest, the other team on a normal week; 44% won at a median +180; 5 of 6 seasons up - 2024
  -62%), college +16.4% on 190 (4 of 6 - 2025 -39%); the last 3 seasons + now +24% NFL / +21% college. Holds at every
  rest cutoff (10 / 12 / 13 / 14 days) in both sports; the mirror (a dog FACING a team off a bye) -18% NFL; the line
  moved toward these dogs by kickoff 65% NFL / 60% college (early is right: +180 -> +170). Only the DOG moneyline -
  favorites off a bye and the spreads are priced right. Checks: fair price YES, blind (a fixed rule, schedules are known
  ahead) YES, most seasons YES, two sports + every cutoff YES, THIS SEASON - not yet (college 6 bets +66%; NFL byes
  start week 5). A LEAD ready to go live small, not proven. Everything else in the 20 (sharp books vs regular books,
  moneyline vs its own spread, the look-ahead overreaction, the spread juice, line paths - buybacks / steam, market
  error to date, pick'ems, big spreads) found nothing that held - three "passes" (#7 steam 3+, #15, #16) were lucky
  cutoffs whose neighbors failed. The max-value dog spots together (#17) fade: big 2020-22, ~+1..4% the last 3 seasons,
  2026 -18% on 31 - only the bye spot holds up recent.

- **EARLY ROUND 3 - 20 new angles, fair prices (10/1; tools/early_round3.py, results/early_round3.json).** HELD:
  NFL East team flying West as a dog +17.0% on 88 (6 of 6); college rain / snow dogs +8.1% on 822 (engine +10.9%, 5
  of 6); college dogs vs a December .700+ team... i.e. a .700+ team AS the dog +11.0% (4 of 6); college freezing games,
  spread + the engine 60.9% on 69 (4 of 5). COLLEGE COACHING STYLE (each team's earlier games that season): dogs with
  a CONSERVATIVE coach (fewest 4th-down tries) -10.9%, 0 of 5; PASS-HEAVY teams on the spread 46.5%, 0 of 5;
  FAST-PACE dogs -11.2%, 0 of 5 and their spreads 0 of 5; aggressive-coach dogs +2.9% (3 of 5, not proven).
  Nothing in NFL weather / altitude / OT / division / 4th-down style held (season totals only - real play-by-play
  coaching style is next: nflverse / cfbfastR).

- **⚠️ 10/1 CORRECTION - THE EARLY STUDIES RE-RUN HONESTLY (read this before the early entries below).** Two leaks:
  (1) the "first look of the week" was often posted while last week's games were still being played (NFL Sunday 3 PM
  ET, college Saturday afternoon) - the engine's read already knew those scores, the book's line didn't; (2) the first
  spread study took look-ahead lines posted 2-4 weeks out (same problem, bigger). Every study now only uses a price
  posted AFTER both teams' last games ended (early_football_study.ready_at / fair), within 7.5 days. DEAD after the
  fix: the early NFL spread play (the engine's read vs the fair early number: 49% at 3.5+ - the "58.5%" was the leak),
  the NFL early moneyline read, the NFL win-value model. STILL STANDING (fair prices): the move model - which dogs the
  money comes to - NFL top 20% 75% moved, +6.0% at the early price (4 of 5), college top 20% 74% moved +5.8% (4 of 5);
  NFL dogs already 20+ cents shorter by the 2nd look +15.7% (4 of 6); MONDAY NIGHT NFL dogs +21.4% on 119 (5 of 6);
  a dog OFF A BYE vs a team that played: NFL +26.7% on 49 (5 of 6), college +7.5% on 242 (4 of 6); a dog that BLEW
  SOMEONE OUT last week: NFL +7.9% (with the engine +13.0%, 5 of 6), college +8.8% (engine +12.1%, 5 of 6); NFL dogs
  on a 3+ win streak +6.7% (4 of 6); NFL East team flying West as a dog +17.0% on 88 (6 of 6); college: first 3 games
  dogs +11.3% (+160 and up +12.5%, 6 of 6 - but 2026 -23%), the engine's big (12+) dog reads +10.4% (4 of 6),
  neutral-site dogs it likes +15.7% (5 of 6), rain / snow dogs +8.1% (engine +10.9%, 5 of 6), dogs vs a December
  .700+ team... (the GOOD team as the dog) +11.0%. FADES that held: dogs the money hammered all week (out 50+ cents)
  -30% NFL / -35% college, 0 of 6; dogs that drifted out early -15%; NFL dogs in their coach's first season -17%
  (0 of 6); a dog whose QB is QUESTIONABLE on the final report -20.8% (engine liking it -33.7%, 0 of 6); a dog with
  4+ more players out (final report) -32% (engine -64%, 0 of 6); a dog whose QB was out last week -17.5%. Hindsight
  value of a move: the side the NFL line moved 2+ to covered 60.2% at the early number (6 of 6) - the prize is real,
  calling it ahead is what's hard. Injury reports: data/sports/injuries/nfl.csv.gz (tools/nfl_injuries.py,
  tools/early_injuries.py). The entries below this one were measured BEFORE the fix - trust this one.

- **EARLY ROUND 2 - 15 angles x moneyline dogs AND spreads x NFL AND college, at the first number of the week (10/1,
  the owner: streaks, start of season, form, coaches, injuries, Monday / Thursday night, out of the country;
  tools/early_round2.py, results/early_round2.json). ~200 cuts - trust what shows in BOTH sports.** STRONGEST (both
  sports): a dog that BLEW SOMEONE OUT last week (17+): NFL +8.5% on 158 (4 of 6), with the engine +16.5% (4 of 6);
  college +8.9% on 580 (4 of 6), with the engine +11.6% (5 of 6). A dog OFF A BYE vs a team that played: NFL +22.8% on
  51 (5 of 6); college +7.7% on 244 (4 of 6), with the engine +20.7% (5 of 6). MONDAY NIGHT NFL dogs +21.3% on 118 (5
  of 6), engine agreeing +20.7% (4 of 6); THURSDAY night dogs -10.9% (NFL), -18.6% (college) - REMOVED 10/1 (the owner: "a night of football like
  any other... a small sample"; at the close since 2018: NFL 91 dogs, up 5 of 9 seasons, the -9% from 2018 / 2021 /
  2024; college 72, -6%, all over the place - noise, no fade). The owner's "whole other monster" is the dog on Monday. FADES: an NFL dog in its coach's FIRST season with the team
  -17.0% on 425, 0 of 6 (engine liking it -35%), spread -10.9% (1 of 6) - first-time head coaches -14% (college is
  the other way: +6.9%, 4 of 6); dogs on a 3+ losing streak -15% NFL / -21% college; "cold" dogs (last 3 games 7+ worse
  than their season) -15% / -19%, and "hot" NFL dogs -21%. College dogs in the first 3 games +12.9% (5 of 6 - but 2026
  -23%). HINDSIGHT (game-day facts, not bettable Tuesday): the QB / key starter edge on the dog's side +10% NFL, +29%
  college with the engine - news is worth waiting for. Injury counts: not in the past games' data (0 rows) - can't
  test yet. Out of the country: 22 NFL dogs - too few. College spreads: the engine's read does NOT beat the early
  number (49-51% at every edge - its college margin model is rough); NFL only. (Spread angles that take both sides of
  a game - night games, rematches - sit at 50% by construction.)

- **🏈 EARLY NFL SPREADS - THE ENGINE BEATS THE TUESDAY NUMBER (10/1, the owner: "+9.5 that drops to +3.5 - the
  opening number covering vs the market's correction by game day"). The Odds API Tuesday spreads 2020-26 (median
  book) vs our closing spreads, 3,280 sides; walk-forward (each season's engine trained only on the 3 before it) AND
  only what's known Tuesday (no injury report, starters, weather).** The engine's OWN margin read 3.5+ points better
  than the Tuesday number: covered 58.5% (-110 needs 52.4%), +11.1% on 554, up 5 of 6 seasons; 5+ points 60.7%
  +15.3% (5 of 6); 7+ points 66.1% +25.5% on 127, up ALL 6. The same sides at the game-day number cover only ~51% -
  the edge is the early number (the market moves to the engine: +2..4 pts on average). Getting points 3.5+: 58.1%,
  6 of 6. A learned "which numbers move 3+ our way" model: top 10% 59.4%, 4 of 5. Hindsight (can't be bet, shows the
  prize): the side the line moved 3+ to covered 69% at the Tuesday number, 6 of 6. Key-number bands: nothing special
  past 7 (+7.5..+10.5 50%). NEXT: build as an early NFL spread play once the live Tuesday number is recorded
  (line_history has spreads? - check) and a few weeks of 2026 confirm. Only 6 seasons - size it small at first.

- **15 EARLY DOG STUDIES (10/1, the owner: "train the engine to spot the dogs that win" - all need the midweek
  prices, so none repeat rounds 1-2; tools/early_dog_studies.py, results/early_dogs.json; walk-forward; graded on
  wins at the price bet).** The big one: THE ENGINE CAN LEARN WHICH DOGS THE LINE WILL MOVE TO. A small model trained
  only on past seasons (Tuesday-known stuff: its read, the price, home / road, last week, rest, the books' spread)
  picked NFL dogs that moved toward them by kickoff 81% of the time (top 10%): +11.4% at the first-look price on 127
  (4 of 5 seasons) - the SAME dogs at the close -6.3%. Top 20% +6.2% (79% moved), college top 20% +7.8% (75% moved,
  4 of 5). A win-value model (which dogs win more than the price says): NFL top 20% +13.6% (3 of 5), college top 10%
  +8.5% (4 of 5). Sept 2026 (never seen, tiny): NFL move picks 67-100% moved, +53% on 9; college win-value 0-4 -
  too few to confirm either way. College dogs in the first 3 weeks (last year's prices): +12.7% on 506 (5 of 6),
  +160 and up +14.8% (6 of 6) - but 2026 went -23% on 41: watch. DEAD / BAD: a dog that drifted OUT early (-9..-13%),
  dogs the money hammered all week (out 30+ cents: -19% NFL / -10% college, out 50+: -30% / -28%, 0 of 6 - follow the
  steam), stale-book shopping alone (-1..-6%), split books (-14% NFL), 6 or fewer books up (-15..-18%), look-ahead
  (fav's next opponent 70%+: -15.5% NFL, 0 of 6 - the books price it), letdown, better-record dogs, big +250 dogs.
  NEXT: the move model needs the first-look price live - line_history (hourly, since 10/1) records it; build once a
  few weeks of it confirm the model on this season.

- **NFL style, matchups and coaching (10/1, nflverse play-by-play 2016-26, 2,258 games at the close, blind walk-forward
  2020-26):** DEAD against the closing price - pass offense vs pass D, run vs run D, pass-heavy vs weak pass D, pass
  rate over expected, pace, pressure / sacks, explosives, turnovers / INTs, success rate, vet coach vs first-time head
  coach (-5.7%, vet dogs -11%), coach new to his team. One model with all of it lost to the market's own number 6 of 7
  seasons (its 3+ point edges -6.9%, last 3 + 2026 -12%). LEAD only: a dog whose coach goes for it on 4th down clearly
  less than the other coach covered 48.4% (0 of 9 seasons over breakeven), ML -13.4% - same direction as the college
  conservative-coach fade. Not wired yet (needs live 4th-down go rates); worth -1 on the dog's read. Script/data:
  scratchpad nflstyle (build_games / study / fixed_rules / robust_go4).

- **Overnight studies (10/1, 22 angles, closing prices, fixed rules, multiple-testing aware):**
  - NHL 3rd game in 4 nights: the rested favorite (not on a back-to-back) beat its price 8 of 8 seasons (+5.2 pts vs the
    same price, z 2.7, 2023+ 3 of 3) - LEAD, WIRED +1.5 pts on the favorite's weighed read (third_in_four).
  - NFL West Coast team FAVORED on the road in an Eastern-time city: won 76%, +20.6% at the close, +12.8% at the early
    fair number, 7 of 8 seasons, 3 of 3 recent; the Eastern home dog -23.5% - LEAD (no 2026 games yet), WIRED +2 pts on
    the favorite, -2 on that dog's score (weigh_west_coast_road_fav).
  - Injury timing (NFL 2020-26): QB news is priced by Tuesday; after an Out the line moves ~1.4 pts at the next look
    and stops; backups (587), returning starters (165) and Questionable QBs (119) are priced right at the close - no
    "beat the market" window. LEAD: a dog whose QB1 is out a second straight week (not IR) -54% on 57, covered 33% -
    WIRED -3 on a football dog with its key player out (key_out_me). NOTE: the older "QB questionable dog -20.8%"
    counted backups on the report; with QB1 only it's +4.2% at the close (n=77) - re-check before leaning on it.
  - WATCH: MLB doubleheader game-2 dog (+9.5%, 2026 +31% on 25; the line posts after 8 AM), NFL dog that scored 10 or
    fewer last game (+7%, 2023+ +21%), Group-of-5 dog vs Power-4 (+8.6% at +100..+220), college dog with better yards per
    play than its record (thin data), Week 18 resting teams' opponents (+32.8% on 43).
  - DEAD: NHL favorite off a shutout loss, early-season dogs by last year's standing, goalie lit up last start,
    rematches; MLB elimination games, bye rust, short rest, day after night; NFL out-gained-but-lost dog, EPA "unlucky"
    teams, off a Monday night, division rematches; college conference openers, FCS tune-ups, rivalry week.
  - DATA: MLB sp_home / sp_away hold the ACTUAL starter (overwritten after the game) - pitcher angles must wait for the
    confirmed starter or they leak.

- **Sharp money (10/1, Action Network splits, 24,301 games 2023-26, at the close; 237 cuts):** money-over-tickets
  (on or fade, dogs or favorites, 10 or 20 pts), reverse line moves, "pros vs joes", 70%+ public favorites - all dead
  (the close already has the money in it; the splits are the final kickoff snapshot, so they can't be bet earlier).
  LEAD only: NHL dogs the line moved TO (2+ pts) against the tickets with money 10+ over tickets: +14.3% on 190, beat
  the close by 8 pts, 2 of 2 seasons - WIRED +1 on the dog score (sharp_dog). Every sharp signal is in the lead tracker.
  Steelers-Browns 10/1: money over tickets AND the line move were both on Pittsburgh - the "smart money on the Browns"
  line from a betting site didn't match the numbers.

- **Coaching / play styles, round 2 (10/1; NBA + college hoops 2023-25, college football 2021-25, closing prices, vs
  the same season / side / price band; 120 tests, best z 2.7):** round 1's watch items are DEAD - college 3-point-heavy
  dogs, NBA slow-pace dogs, college football pass-heavy favorites (round 1 compared to every favorite, not the same
  price). Also dead: pace, 4th-down aggressiveness, pass/run mix vs the closing moneyline in all three. LEAD (hoops
  favorites "win inside"): a college favorite that takes few 3s / any favorite that crashes the offensive glass beat its
  price band 3 of 3 seasons under every cutoff (+3 to +7 pts), still only ~break-even ROI. TO WIRE before the 2026-27
  hoops season: +1 win-% point on such a favorite's read (needs this season's team stats live). No dog-score points.

- **Unit-play bar (10/1, walk-forward 2018-26, closing prices, favorites -150..-101):** lowering units from p 56%+ to
  53-56% (own read beating the real price) LOSES: 53-56 band -9.6% on 919 (won 48% when the engine said 53-56%) vs 56%+
  -3.7% on 1,978 (pooled NFL/NCAAF/NBA/NHL/MLB). A bigger value margin doesn't rescue it; quarter-Kelly lost more than
  flat lately. KEEP the 56% floor + the money check. Note: even 56%+ favorites are slightly negative over the seasons -
  the proven money is in the dog angles and the early spots, not in more favorites.

- **The paid odds history, round 4 (10/1; NFL + college 2020-26, ~20 books, fair looks only, median-book prices, ~330
  cuts across two teams):**
  - TIMING RULE (passes all five as timing, not profit): dogs +100..+220 are best bet at the Tuesday fair price (+1.5
    to +2.8 pts of value vs the close; NFL 6/7 seasons, college 7/7, 2026 too); favorites -150..-101 are best on game
    day (Tuesday 1-2 pts worse; NFL road favorites -7.9% on Tuesday vs -4.8% at the close). WIRED: early plays are dogs
    only (the college engine spot let favorites in). Weight 0 on the read.
  - The juice moves before the number: a spread shaded 2%+ on Tuesday moved its way 66% of the time (NFL; 74% at 4%+);
    a juiced favorite on 3 goes up off 3 twice as often - but betting the shaded side at its juice loses (priced in).
    A timing tool: line_history now keeps the spread juice (spo).
  - Catching the side the close crosses 3/7 toward = +11.9% in the NFL, but nothing on Tuesday predicts it.
  - DEAD: book dispersion (consensus or outlier), leader/follower books, regular vs sharp book gaps (tiny, close from
    both sides), ML juice (books don't shade ML), steady / late moves (follow or fade), ML-vs-spread gaps (the ML
    leads, the spread follows, betting the lag loses), the engine's read vs the next move (a coin flip).
  - LEADS (log only): NFL spike-then-revert / round trip, bet the spike side (+19% on 53, no 2026 yet); college early-
    only move, fade it (+8 to +14%, but the NFL goes the other way); NFL dog only one book is out on -10.8% (overlaps
    "split books"). Per-book prices aren't in our live feed yet - needed to re-test the book leads on 2026.

- **Daily studies, 10/1 (10 angles; NHL / MLB / college football / the paid odds history):**
  - WIRED (lead): NHL favorite with a SLUMPING GOALIE (last-10 save % <= last season's bottom quarter, .876 for
    2026-27): beat its price 5 of 5 seasons, +7.9 pts on 852 (2023+ 3 of 3); the dog facing it -8.0, 0 of 5; holds at
    every cut and inside every dog-score third. +1.5 pts on the favorite's weighed read, -2 on that dog's score.
  - CORRECTED: the Monday night NFL dog is +3.3% on 80 inside the +100..+220 band at the first fair price (the +21.4%
    came from bigger dogs / other looks) - game-day weight +2 -> +1, early SPOT_WEIGHT 0.03 -> 0.015.
  - LOG ONLY: NHL home favorite on a back-to-back, first home game after a 3+ road trip (+28 pts on 114, but the
    opponent-rest split contradicts); NFL "dead number" dog (price still while the week's slate moved) -20% (college
    the opposite); fade a college favorite with bad turnover luck vs a lucky opponent (-19.6 pts, 0 of 5, thin).
  - WATCH: NHL first home game after a 4+ trip with 2+ days rest (+10 on 193), close-game-unlucky hockey dog (+3.4),
    Group-of-5 dog vs Power-4 (September +23%, same at the close), MLB playoff game-1 rested home team (10 games).
  - DEAD: kickoff slot (primetime / night games), NFL weeks 1-4 dogs, record vs the week-1 price, college conference
    openers (again), hockey travel / time zones / early vs late in a trip / home letdown, comeback / OT / empty-net
    luck, power-play chances, MLB after 10+ runs, MLB last-10 run-differential and one-run luck, college out-gained-
    but-lost dog. College turnover-luck dogs: fading in 2024-25 - WATCH only.

## 10/2 - five studies on game dynamics: crowd, pressure, nerves, experience, momentum (the owner: "across the sports")
Closing prices, flat 1u, 2018-26; every lead re-built from scratch by a second check (no leaks: line scores match the
finals in all but 15 of ~124k games, the next game always after the trigger ended). Scripts: scratchpad, not in repo.
- **WIRED (small weights on the dog score, never a trigger - sports.comeback_win / late_rally):**
  - NBA team off a COMEBACK win (trailed after 3, won by 3 or less, OT counts): next game fading it +11.2% ATS / +8.5%
    ML on 574, covered 41.7%, up 6 of 8 seasons, 2023-25 +10 / +20 / +18; fades smoothly (won by <=5 +5.5, <=6 +2.8),
    grows with the deficit (trailed 8+ +16). NOT in college hoops (-4.7% on 2,006) or football. Dog score: the
    favorite off one +2, the dog off one -2. Passes checks 1, 3; 4 waits for the NBA season.
  - MLB dog that lost but won the last 3 innings by 4+, next game at +100..+220: +12.0% vs -4.7% at the same prices
    (411, z 2.6; 3+ / 5+ runs +15.6 / +14.2), 2026 +37% on 18. Hockey / basketball versions fail the re-check
    (threshold-fitted). +1.5.
- **WATCH (re-check when the season gets there):** NFL division dog in the last 4 weeks with a team in the playoff race
  85-57 ATS (+14.7%, 6 of 8, 3 of 3 recent - from ~250 cuts); NFL dogs of a 2nd / 3rd-year head coach in Dec / Jan
  -30.5% ML, covered 44.8% (0 of 8 seasons; the same coaches covered 56% Sep-Nov); NBA team losing the close ones but
  winning the rest, as a +100..+220 dog +16.1% on 167 (only the tightest cut); NBA conference finals / Finals dogs
  +17.6% ML (8 of 8) but -2.8% ATS; Game 7 dogs +23% on 78; MLB postseason veteran home starter -16.3% (1 of 9 -
  overlaps playoff favorites -8.9%); NFL / college fortress home dog +15% / +14% (dies with another look-back);
  NBA short dog on a 7+ losing streak (+14 vs base on 150).
- **RE-CHECK:** "NHL dogs facing elimination +10.2%" (above) didn't reproduce: -11.8% on 106 (2018-26). Re-run before
  the NHL playoffs.
- **DEAD:** loud / fortress buildings as bets - the Seahawks 12th man (-6.4% then -6.6% at home), Saints dome -28%,
  Ravens -24%, altitude (Jazz / Nuggets / Rockies priced in), hockey barns; a team's extra home edge doesn't carry to the
  next season in the pros (r ~0). Motivation: needs-it vs nothing to play for -3.3% on 1,718; resting / tanking /
  bowl-chasing teams; college rivalry dogs -24.7% (they don't rise up); conference tourney dogs -12.8%. Clutch is luck in
  every sport (close-game win % doesn't carry: r -0.11..+0.01); blown late leads, comeback-heavy teams, OT records.
  Nerves / experience: first-time playoff teams don't choke (NFL covered 59%), rookie QBs on the road (+1.7 last 3) or
  primetime (+17.9%), young NHL playoff goalies, roster playoff experience. College football 4th-quarter heartbreak dog:
  the "-36%" only held leaving out OT losses; with them -24.4% vs -9.8%, 6 of 9, z -1.3 - noise. Heartbreak / walk-off
  losses, letdown / sandwich spots, finishing strong on its own.

## 10/2 - edge size vs units (the owner: Western KY +110 at 1u on a ~1-point read)
11,941 moneyline candidates 2018-26, each season graded blind (sports_model.tune on the 3 seasons before), closing
prices, the bare own read (no dog gates / spots / calibration). Own edge per dollar -> ROI: <1% -2.4%, 1-2% -3.6%,
2-3% -4.2%, 3-5% -3.2%, 5-8% -4.5%, 8-12% +1.5% (6 of 8), 12%+ +6.2% (6 of 8). Dogs 8%+ +6.7% on 1,506 (8-12% last 3
+5.3%, 3 of 3); favorites 8%+ -4.3% (last 3 -9.7%, 0 of 3). No MIN_EDGE between 1% and 8% makes the bare read a
winner - the profit is in the dog gates. BUILT: own read under 3% = ½u (sports.THIN_EDGE). The 8% line + favorites
½u was built and rolled back the same night (the owner: "we can't be having half units all across the board"). Sizing sim: old -125u / last 3 -139u / 2026 -4.5u -> ½u <8% + favorites ½u +73u / -59u / +6.2u. Re-check on
a full-board replay (gates, spots, calibration) - a LEAD until then.

## 10/2 - the unit system (walk-forward replay of the real board: 712 days, 1,192 unit plays, 2023-26)
Units won / ROI / since 7/2023 / 2026: today's sizing (Kelly on everything) -57.0u / -4.3% / -15.2u / +16.7u; flat 1u
-35.7u / -3.0%; tiers -38.2u; confidence buckets -54.8u; Lock by read + rest flat -27.5u / +0.7u / +27.8u; **Lock by
read, Dog 1u, plays ½u -12.2u / -1.1% / +10.5u / +33.7u (3 of 5 seasons) - BUILT**; same with the Dog 2u (+ hockey 2u)
+13.0u / +1.0% - not built (picked after seeing the numbers, rides one hot hockey season). By kind (flat): value plays
-6.7% (1 of 5 seasons; sized up -10.5%), Lock -6.0% flat but -3.2% by read and +12.7% in 2026, Dog +8.9% (3 of 5;
hockey dogs +11.2% on 211, almost all 2025-26). The backup near_lock -17% flat (78 days) - the owner keeps a Lock
every day, at ½u. Daily units: today's sizing ran from ½u days to a 33.5u day (sd 3.7); the new system sd ~2.
Peeking: model re-tuned per season on earlier seasons, but the rules / study weights were built with every season seen.

## 10/2 - the point system (5 studies, walk-forward, 41,497 dogs +100..+220, 2019-26, closing prices)
- **Hand points beat learned points out of sample** (top pick/day: hand +1.5%, learned -0.2%, no angles +0.1%; all
  dogs score > 0: -2.0% vs -2.6% vs -3.1%; within noise ±2.5%). The own read barely predicts dog wins (0.02-0.09 per
  point); the study angles carry it. 71 angles tested, 4 survive a false-discovery check (q .10).
- **BUILT (passed the false-discovery check or fixed a real double count / bug):** NBA overreaction +3 -> +5 (+11 pts,
  7 of 7); NHL both-lost +2 -> +3.5 (+4.3, 6 of 7); MLB +200..+249 -2 -> -4 (-5.3); NHL road-opener +1.5 -> off
  (wrong sign, -7.3 inside own-read buckets); NHL hot_key and key_edge never both (93% overlap, -5 stacked); college
  ice cold + losing streak -4 together (61% overlap); college 'bye' only within 30 days (it fired on season openers).
- **NOT built (noise / look-ahead in the study):** drift_away cuts (the study measured open-to-close drift - the 8 AM
  board can't see the close), go4 (current rates), the other "too big / too small" suggestions (inside noise).
- **Per-sport point scaling (study 5):** one point is worth ~0.35 points of real win % (NHL .55, NCAAF .74, NFL .48,
  NBA .38, MLB .22); a per-sport-scaled Dog of the Day +6.1% vs +2.9% as-is (2023+ +11.0% vs +6.9%) - but the angles
  were found on the same seasons (partly in-sample): a LEAD - re-check before building. No price scaling (no pattern).
  Hockey stays in the Dog of the Day (since 2023 +1.8% with it vs -1.3% without; NHL score 6+ +12.6%, 7 of 7).
- STUDY_CAP ±6 binds on 3.6% of dogs - kept. The cap / stacking replay (337 game days, make_board at 8:35 AM): caps 4
  to none all the same within noise (only 3 looks worse); positive angles add up fully through ~2 angles, then about
  half per point past ~6 - what the cap already does; negative angles stack fully (two+ = -24.7% ROI, 0 of 5 seasons).
  Favorites' weighed read (weigh_favorites) on at 0.005 / cap 0.04: unit plays +4.3% (4 of 6) vs off +1.6% (2 of 6),
  Locks flat +0.9% vs -3.6% off - kept as is (0.01 a little better on Locks, worse on plays, not proven).

## Tested and dead (don't re-chase)
Hot teams as dogs (-5..-8%, books overcorrect), fading the public (-7..-12% on ~18,000 bets), big money over the bets
(-10%), baseball travel (no effect), baseball bounce-back after a loss (none, even since 2023), Wild Card dogs as a
group (-4.6%), Yankees-Red Sox rivalry dogs overall (-9%; last 3 seasons lean dog, small), opening-week hockey dogs,
hockey parity as a bet-the-dogs signal (it's a stay-away signal), season run differential on top of the price (adds
zero - the books know it), the backup-QB "edge" (fake: in-game injuries).
Buying a favorite late after the money moved it our way 3+ points (10/1 study, -150 to -101): hockey -0.2% on 115,
NBA +2.2%, NFL +3.0% - neutral. Baseball looked bad (-6.5% on 1,224 vs -3.4% for all favorites) but year to year it
wobbles (-1, -7, -2, +2 points vs baseline 2023-26) - not steady enough to weigh. Recheck after 2027.
Hockey home openers (10/1 recheck, 8 seasons): road dogs -16.0% on 164, home favorites +3.8% but down 2024-26 -
noise either way.

- **A leg's 🔒 LOCK label (10/1, the owner - the Flyers):** the label only checked 56%+, which a -142 price gives by
  itself; the engine's own read was against the Flyers' price. Now a leg is a LOCK only if the own read backs it
  (sports.own_agrees - the Lock of the Day's rule); otherwise it shows as a lean.

- **Tennis live tightened (10/1, the owner):** 3-6 (-27%) on its first 9 plays, thin edges (Tsitsipas +104 at 52%)
  on prices that move in seconds, never tested on real live prices (no history of them). A new play now needs a 65%+
  pre-match favorite on the books gone plus money AND a 10%+ edge. Watch its record.

- **Live tuning, round 1 (10/1, the owner - every line score 2018-26; learned 2018-23, checked 2024-26):** the live
  curve vs what happened at every period's end. NFL / NBA / college hoops: right. Runs HIGH the same way both times:
  MLB trailing pregame favorites (said 38-39%, won 36%), college football tied favorites (57% / 51%) and trailing
  favorites (45% / 41-42%), NHL trailing pregame dogs (30-31% / 24-28%) - built: sports_live.LIVE_CAL takes the gap off.
  Late + trailing, the real-history pull: MLB all the way (curve 25.6%, half 23.3%, history 20.9%, won 21.7%), NHL all
  the way (26.1 / 25.4 / 24.7 / 24.6), others stay halfway - built: LATE_HIST_W. Player data (the starting pitcher /
  goalie matchup): a trailing team with the BETTER one won ~3 points under the curve (MLB 36%/33%, NHL 35%/32%) -
  mostly the same games as the trailing-favorite fix, not added twice. Coaches: ESPN's coach history is bad (see the
  audit) - no live coach study until it's rebuilt. A study bug caught on the way: dropping MLB games where the home
  team never batted in the 9th skews everything toward the road team (any line-score study: keep 8-inning games).
  What can't be tested yet: the live PRICES (no history of them) - every live play's price + result is logged now.

- **The 15 dog studies (10/1, the owner: "all these dogs win every day - find them"; closing prices 2018-26, every
  result vs ALL dogs at the same price in the same season, then 2024-26):** BUILT (sports.dog_spots / OWN_CAP):
  NHL dog played last night vs a rested favorite -17.4% vs -4.8% (worse 7 of 8, our check agrees) -3; NFL / college
  football / college hoops: the favorite lost its last +2 (7 of 9), the dog lost & the favorite won -3 (worse 7 of 8);
  NHL both lost their last +2 (7 of 8); NBA dog won & favorite lost -2 (worse 7 of 8); NHL shot share (last 10) dog
  ahead +3 (5 of 5, 2024-26 +9.3%), behind by 3+ -3; MLB run share (last 15) +1.5 (our check: only 5 of 9 at +130..+199
  - weaker than first said); price bands that lose: MLB +200..+249 (-14.9%, 1 of 9) and NHL +200+ -2; big own reads
  are traps (walk-forward: today's rule went -6.9% in 2024-26) - capped at +12, and 0 past +12 in the NFL / NBA.
  FOUND, NOT BUILT YET (needs game-time data): MLB favorite resting 2+ more regulars than the dog: dog +8.9% vs -3.0%
  (5 of 6, 2024-26 +15.7%) - lineups post 2-4 hours before first pitch, after the 8 AM board; NHL goalie roles (dog
  starts its #1, favorite doesn't: -0.6% vs -6.7%, 4 of 5) - needs the confirmed starter (BUILT 10/6, see the 10/6
  goalie section up top - re-checked +1.5% vs -4.0%, 7 of 8, +2 on the Dog's score); college football yards
  margin (+50: +4.9%, 4 of 5); high totals hurt NFL / college hoops dogs (-2). Cautions: NBA dog missing its top scorer
  -10.5% (contradicts the older star-out line - reconcile), football dog's usual QB out (small). NOISE: pitcher form
  streaks, NBA favorite missing a star (carried by 2021 / +300s), rest / byes / road trips, division games outside
  MLB, MLB series spots, line-move sizes outside the NHL, marquee favorites (team by team), public % (look-ahead risk).

- **Dog studies round 2 (10/1 - NEW angles only, ~700 slices, judged strictly for multiple testing):** BUILT: NBA dog
  that WON 2+ close games (3 or less / OT) in its last 5 -20.0% vs -3.4% (worse 7 of 8 - our own check agrees; college
  hoops weaker, -1) -3; NHL dog in the top quarter of hit margin (last 10, ranked within the season) +2.2% vs -6.1%
  (5 of 5, 2024-26 +7.6%; adds to shot share) +2; MLB dog 10+ points unluckier than the favorite (win % vs Pythagorean,
  season) +2.7% vs -3.5% (6 of 9) +1, watch. WATCH: college football dogs with bad turnover luck but even-or-better
  yards (+25% on 113 - thin box-score coverage). DEAD: MLB weather (wind speed / rain / cold - and low-scoring spots HURT
  dogs; hot 85F+ games look bad but may be game-time weather), one-run / one-goal / OT records, football close-game
  luck (close wins there are real), NHL special teams / penalty minutes / faceoffs / blocks, NFL turnover luck, third
  downs / possession / penalties. Data note: NHL takeaways / giveaways are counted differently from 2024 on - rank
  within a season.

## Data audit (10/1, the owner: "gotta confirm we don't gather bad data")
- **Coaches (ESPN per season): BAD** - today's coach copied back through every season (NFL / NHL / MLB / college
  football), partly wrong in hoops. Coaching round 1 weights OFF.
- **Opening lines: STALE in the NFL** (summer look-ahead lines; the open moves 15+ win-% points by kickoff in 7% of
  September games, 35% of December); MLB 2019-22 has no real open (= the close). Early exam fixed (see Get in early).
  Every "since the open" study in the NFL should be read with that in mind.
- **College football re-check with every game (10/1):** dogs off a 30+ blowout loss (last game within 3 weeks) -5.4%
  vs -13.4% for every dog, better 6 of 8 seasons - still real, smaller than first measured (stays). Revenge dogs (lost
  the last meeting by 30+) -1.3%, better only 4 of 8 (2024, 2025 worse) - OFF (sports_form.REVENGE = {}). Cover
  streaks: failed to cover 4+ straight +1.4% vs -4.6% (6 of 8), covered 4+ -11.1% (worse 7 of 8) - stays.
- **College football 2024-25: ~45% of games missing - FIXED 10/1** (ESPN's all-of-FBS feed gives ~25 games a
  Saturday now; the pull goes conference by conference - sports_data.SPLIT; refilled to 888 / 892). (~500 a season vs ~930 before) - ratings and every "last 3
  seasons" college football finding lean on a partial slate. Backfill: ncaaf_backfill.yml.
- **Firings (Wikipedia): 4 of 153 wrong** (Staley's 2023 firing repeated as 2024; 'Charleston Southern' / 'USC Upstate'
  / 'North Carolina A&T' read as other teams) - parser fixed, file rebuilt (149).
- **Team-name match for odds was loose** ('UC Davis' ~ any 'UC' school, 'Texas St' ~ the Longhorns; 11 of ~24,000
  games off) - fixed (sports_data._same).
- **Injuries:** the history is empty except NFL 2026; the injury weights start at 0 and only move on the games that have
  reports (MLB 0.119, NFL 0.204, NHL 0.053) - thin, watch.
- **OK:** closing moneylines (no home/away swaps), line scores (sum to the final 126k of 126k), starting pitchers (99.6%
  match the box score), NHL goalies (95-97%), player box scores (right team, by player id), team stats.
- Small: 2 duplicate MLB games (2017, 2018) - harmless.

## Data the engine gained
Every player's box score, every sport, 2021-now (data/sports/roster, rosters.yml keeps it filling). Next: player
studies for football (stars, backups), baseball (lineups, hot/cold hitters, AAA call-ups), coaches.

## 10/1 - false records from a half-filled college feed (major bug)
- The 2026 college football games were read before the conference-by-conference split: ~25 games a Saturday instead
  of ~65. North Texas showed 1 game ("0-1"; really 2-2), Northwestern "0-1", Minnesota 1 game, and Delaware looked
  "off a bye" - they lost 42-3 at Virginia 9/26. Delaware's early play (+220) came off that and was pulled (the owner's OK).
- Every other league checked whole: NFL 3 games a team, MLB 162, NBA 82, NHL just started.
- Fixes: tools/ncaaf_backfill.py refills 2026; seen_all keeps a partly-seen college team's record, streak, last game
  and series off the card and out of the early spots; the bottom line says our own read vs what the price needs, and a
  read under the price says "lean", never "value".

## 10/2 - what a missing player is worth (the owner: "if the running backs are out and the wide receivers are out ... that changes everything")
Our own box scores 2021-26 regular seasons; key players from each team's own previous games (no look-ahead: football
last 3 - most pass attempts / rushing yards / top-2 receiving yards; hockey / NBA last 10 - points; MLB last 20 - top
bats); 'absent' = not in that game's box score; the engine's own read replayed pre-game; gaps net of a no-one-out control.
- NFL (9,256 team-games): QB out own read overstates -10.6 pts (5 of 5 seasons; the market prices most - ROI -19% at the
  close, ~2 SE), lead RB out -4.5 (3 of 5), a top-2 WR out -5.1 (4 of 5), 2+ of those -13.7 (5 of 5, ROI -24%), both WRs
  n=22 noise. BUILT (shrunk): QB -8, RB -3, WR -3, two+ -10 (cap, never stacked).
- College: RB / WR out ~0 (the ratings and the market have it), QB -3.2 (4 of 5), 2+ -5.2 (4 of 5). BUILT: QB -3, two+ -5.
- NHL (12,355 team-games): top scorer out -7.0 vs the own read (market -4.0; shrinking lately: 2021 -13 ... 2025 -3),
  one of top 2 -4.8, two of top 3 -9.0 (n=108), backup goalie -1.0 (noise). BUILT: -6 / -4 / -7, cap 8; goalie none.
- NBA (2021-25): top scorer out -9.2 (every season), two of top 3 -11.6; the market prices it fully (ROI = vig). BUILT:
  -9 / -11, cap 12.
- MLB: best bat out +0.3, two of top 3 +1.5 - noise. DEAD (no weight); watch: the market may overrate the OPPONENT of a
  depleted lineup by ~3 pts (ROI -12%, 1.9 SE) - a LEAD.
Wired as sports_absences.penalty -> the engine's OWN read only (a starting QB / goalie the engine already treats as key
keeps the go-by-the-market path - never counted twice). 'Out' = the injury report says out / doubtful / suspended.
Caveat: box-score absence counts trades / long injuries too; real-time 'out' lists are cleaner - re-check on live picks.

## Early value plays - hockey / baseball (10/2 study; nothing built)
Real opens exist only for NHL 2023-25 (~3,950 games) and MLB 2023-26 (~9,700) - honest day-before prices (no-vig moves
2.4-2.9 pts both ways), same vig as the close. Engine read walk-forward (prior 3 seasons only). ~70 cuts looked at, so
a +10% here and there is what chance gives; nothing clears 2 SE.
- Every dog +100..+220 at the open: NHL -1.4%, MLB -2.5% (+191..+220: -18% / -13%). DEAD - dogs aren't an edge.
- Favorites at the open, both sports: -3% to -11%. DEAD.
- Engine vs the open: the line DOES move toward the engine's read (corr +0.27 NHL / +0.25 MLB, +1 to +2.3 pts of CLV at
  gaps 5+), but the money doesn't follow: NHL dogs gap 8+ +11.1% (n=205, t=1.3) falls to +6.9% priced mid-move and
  -1.1% once the dogs that already ran are skipped - the profit is the move itself. LEAD (re-test with 2026-27 opens).
- NHL goalie spots: DEAD early (the starter isn't known at the open).
- NHL rested team vs a back-to-back (n=790): +4.2% at open, line moves toward them 70%; engine agrees by 3+ (n=534)
  +6.5%, 3 of 3 seasons, t=1.5. Best LEAD - log live (no units) ~150 plays before it gets any.
- NHL dog ON a back-to-back vs rested: -24% on 372, t=-4.1, 0 of 3 seasons - a FADE weight only (engine has b2b).
- MLB: no spot beats the baseline (off a loss, home/road dog, game 1 of a series). Divisional dogs -5% (t=-2.1) - mild
  fade at most. Keep only the live +100..+149 dog with the engine 8..12 over (n=510 +7.8% at open); widening to 12+ loses.
Scripts + tables: the 10/2 session scratchpad (study_early_nhl_mlb.md) - re-run against fresh opens next season.

## Capper benchmark - Dr. Bob (10/2)
Free NFL Analysis page: a Lean when his predicted margin is 4+ pts off the line ("Lean - Cleveland (+3 -115) or
better"), totals Leans since 2022. His published records: Free Leans 1101-913-38 all-time (college) but 81-80-3 in
2025; Leans 4+ off 1008-853-37; NFL Best Bets 2016-26 517-382-12 (57.5%, paid). No college in 2026. Tracked live in
sports_capper (graded vs ours) - the free Leans are his coin-flip tier, so judge them on a season, never a week.

## Futures - title / conference winners (10/3 study; nothing posted)
Data: preseason + in-season futures for 69 sport-seasons (sportsoddshistory via the Wayback Machine: NFL 2010-23,
NBA 2011-24, NHL 2011-23, MLB 2010-23, college 2018-23); today's prices from ESPN's free API (DraftKings).
- The cut: preseason title markets add to 124-129% (pros), 148% (college); today's DraftKings 121-128%; conference
  markets 113-117%.
- Betting every team preseason (2,291 bets): favorites (< +500) -25%, +500..+1499 -9%, +1500..+4999 -24%, +5000 and
  up -100% (0 for 1,278 - the longest preseason champion in 15 years was +4000: 2017 Eagles, 2023 Rangers). DEAD as a
  group; the odd green cell (NFL / NHL +500..+1499) rides ~10 titles - noise.
- Knowable-before-the-season signals (7 cuts, walk-forward): unlucky teams +35% on 5 titles (and their chances held up
  WORSE by the playoffs) - noise. Our Elo above the market: 0 for 85 - DEAD (it can't see trades / free agency / a QB
  back). The market halving a team's price from last year: 34 bets, 2 titles - too small.
- Conference vs title: the title price = the conference price rolled into the Finals at the price the two imply
  (Blazers 10/3: West +4000, title +8000 -> a 51% Finals). A longshot sprinkle is better on the conference (smaller
  cut); 'the title is a free roll' isn't real - a hedge only locks what the conference already paid.
- BUILT: sports_futures logs every title / conference market daily (data/sports/futures/) - our own history.
- NEXT (the one real lead): mid-season futures vs the game lines - team strength from the books' own closing lines,
  simulate the rest of the season, compare to the slow-moving futures board. Needs conference maps + playoff formats.

## Why so few Locks / value plays (10/3 Fable sweep, walk-forward, real closing prices)
- strust = 0 is CORRECT: the engine's margin predicts the final margin worse than the closing spread in every season of
  every spread sport (NFL RMSE 12.9-14.1 vs market 11.5-13.6; college 17.4-20.6 vs 14.8-16.4). No spread Locks with
  this model. DEAD until a different margin model.
- Own moneyline read vs the close: "own 56%+ and beats the price" at -150..+125 wins 50-53%, -1.3% to -8.9% a unit in
  every sport (NFL -6.7% on 228, college -5.7% on 518, NBA -1.3%, NCAAB -1.9%, NHL -8.9%, MLB -4.4%). Lower or higher
  bars lose more. More Locks = more losses: the leans are the engine being right.
- own_agrees: +5 to +7 ROI pts in college hoops / NHL / MLB, nothing in NFL / college football / NBA (LEAD: make it a
  sport-aware Lock tiebreaker, gate unchanged).
- CORRECTION: the 10/1 "early NFL spread 3.5+ off Tuesday = 58.5% on 554" was a LEAK (last week's games still on).
  Fair: NFL 49.1% on 497, college 49.1% on 1,634 (0 of 5 seasons). DEAD.
- Leaks found: sports_players.key_edges trains 'key' on the actual box-score starter but predicts with the guess (NHL
  goalie guess wrong 53-55%) - fix train/predict match; 'inj' feature has 16-23 games - hold at 0; tune() eval window
  overlaps training (flatters, never hides edge).
- What makes money (built): dog_score angles, the fair-price early dog spots, hockey favorite weights. Nothing else
  cleared n>=200 with 4+ of 7 seasons up (66 cells tested).


## 10/4 - the big-dog study (the owner, after Missouri +180 smacked Florida: "how do we pick out these +180, +200 dogs?")
NFL + college football only (the owner's scope). Every dog +150..+250 at the CLOSE, 2018-26 (9 seasons with closing
prices): NFL 788 dogs (-2.9%, 2023+ -14.6% on 291), college 1,376 (-2.6%, 2023+ -6.2% on 605). 29 situational angles the
engine does NOT already weigh (58 league x angle tests, each vs ALL band dogs in the same league-season, seasons up,
2023+ holdout, Welch t-test, Benjamini-Hochberg q .10). Conference / rivalry proxied as "met in 2+ of the last 3
seasons" (the game files carry no conference or ranking - the one data gap). **RESULT: 0 of 58 pass the
false-discovery check. Nothing built.** Big football dogs win when the engine's full read says so - not off a spot.
- Closest, and why each fails: college FAVORITE on its 2nd+ straight road game (dog home) +13.7% on 150, only 4 of 8
  seasons, 2023+ -3.1% (p .09); college HOME dog +5.4% on 575, 7 of 9 seasons - but 2023+ -11.0% vs -6.2% (the books
  caught up; p .13); NFL favorite off an UPSET win (won as a dog last week) +17.3% on 102, 2023+ +32% on 40, but only
  3 of 6 seasons (p .09) - a WATCH, re-check after 2027; NFL "dog .500 or worse vs a .750+ favorite" +18.4% on 68 (3 of
  5, small). Everything else inside noise or the wrong way.
- The owner's intuitions, tested: home dog (NFL -10.2%, worse 5 of 8 - matches the 10/1 -17%); home dog off a loss
  (NFL -17.2%, college -2.6%); dog vs a favorite off an emotional 17+ win (NFL +7.1% 5 of 8 but college -8.8%, 3 of 9);
  favorite off a narrow escape (3 or less): nothing; dog with the better point differential than the favorite: NFL
  +7.4% (5 of 8, but 2023+ -22.8%), college -14.9% (1 of 8; 7+ better -41.0%, 0 of 6 - the market already prices it
  and then some); "unlucky" dog (win % 15+ under its Pythagorean) college -16.2%, "lucky" favorite -22.1%: dead; dog
  with the better record college -5.5%; late season NFL -6.2% / college -4.1%; look-ahead (favorite's next game a
  pick'em or worse, this dog under .500) college +4.3% / NFL +0.6%, noise; cold 35F NFL +7.0% (3 of 7) / college -9.0%;
  wind NFL +3.7% / college -5.3%; rain-snow college -0.8% (the 10/1 +8.1% was at early prices with the engine - here
  at the close, flat); low total NFL +5.3% (5 of 7), college +1.5% (6 of 8) - small, not steady past 2023; short
  spread at this price (dog +3.5 or less) NFL -2.6% / college -9.2%; favorite on short rest: under 60 games; favorite on
  a 3+ win streak NFL +4.0% / college +1.3% (noise); both off losses NFL -8.5%; dog off a close loss NFL -28.3%,
  college -15.1% (the "they almost won" dog is over-bet); dog on a 2+ win streak NFL +9.1% (5 of 8, 2023+ -1%) -
  the 3+ streak weight already built covers it.
- Price bands (every dog, by season): NFL +150-199 +0.1% (6 of 9), +200-250 -7.3% (2 of 9); college +150-199 -5.1%
  (3 of 9), +200-250 +0.7% (4 of 9) - all over the place, no band weight. +400 and up loses every college season
  (-29.2% on 2,207, 0 of 9) and -17.3% in the NFL - already outside SPOT_DOG (+100..+220).
- Study: /tmp scratch bigdog_study.py (not kept - the table above is the result); re-run after 2027 for the NFL
  upset-hangover favorite.

## 10/4 - replay of the no-cap and injury-weight changes (do the two 10/4 rule changes lose money before real units do?)
Same machinery as the 10/2 unit-system replay (its code snapshot, blind per-season model params, 8:35 AM PT board,
closing prices): 713 board days 2023-01-01..2026-09-30, 1,193 unit plays, old rules -13.2u on 1,099u risked (-1.2%)
at today's sizing (Lock by read, Dog 1u, plays ½u). Nothing changed in the engine - measured only.
- **No cap on value plays (MAX_PLAYS 8 -> none): it hardly ever mattered.** The 8-play cap bit on 7 of 713 days (all
  college-hoops Saturdays); re-run with no cap, 4 of them still stopped at 8 (that's all the slate had), so the cap really
  bound on 3 days (1/7, 2/18, 3/2 of 2023) and let through 17 extra plays ranked 9th to 19th: 9-8, +0.78u at ½u (+9.2%
  ROI, flat 1u +1.6), 16 college hoops (9-7, +1.3u) and 1 hockey dog (lost); 12 of the 17 were dogs, 3 spreads. One
  season, 17 bets - noise, not proof either way. The whole replay with them: -13.2u -> -12.4u. The real read on depth:
  across all 713 days the value plays by their rank on the day (flat 1u) run #1 -6.7% (235), #2 +2.8% (111), #3 -15.8%
  (53), #4 -10.8% (29), #5 -8.2% (22), #6 -8.6% (15), #7 -43.2% (10), #8 -12.8% (7) - the 3rd play down loses more than
  the first two, and value plays as a class lose (-6.7% flat, the 10/2 finding). VERDICT: keep the no-cap (it costs
  nothing we can see - it adds a handful of plays a season), but the thing to watch is not the count, it's the deep
  plays: if the 3rd+ play of the day keeps losing 10%+ on our live record, a cap at 2 (or ½u only past #2) is the fix.
  (Two 2023 days came out with 1-2 of their first 8 plays different from the 10/2 run - the game files have grown since
  - so the 'extra' list is the fresh run's 9th+; the 2025-26 days matched exactly.)
- **Football injuries weighed, not blocked: the block can't be replayed faithfully** - the board replay has no injury
  reports (none exist in history; sports.hurt / MAX_EXTRA_OUT never fired in it, so its 1,193 plays already behave like
  the NEW football rule). Estimated the 10/4-study way on the replay's 76 graded football unit plays (NFL 17, college
  59; 2023-26, both sides with box scores and prior-game regulars): 'out' = a regular from the team's prior 3 games
  (QB, top 2 carriers, top 4 catchers, top 11 tacklers) not in the game's box score. Caveat: a tackler with no tackle
  reads as 'out' too, so this flags far more sides than the real reports would (47 of 76 plays had 2+ non-key regulars
  'out') - it's an upper bound on what the block would have stopped. Those 47: 25-22, +3.3u at our sizing (+10.0% ROI,
  flat +2.9u, 4 of 5 seasons up; NFL 11 plays 8-3 +1.3u, college 36 17-19 +2.0u; favorites 14-4 +4.5u, dogs 11-18
  -1.2u). The 29 'healthy' plays went 11-18, -9.8u. Cleaner count (skill regulars only - QB1 / top rusher / top-2
  catchers, no tackler noise): pick side with 1+ skill regular out 26 plays 13-13 +1.2u (+6.4%); 2+ out 9 plays 5-4
  +0.8u; 0 out 50 plays 23-27 -7.7u. So the football plays the old block stopped did NOT lose - they were the better
  half of our football - which matches the 10/4 study (a side 2+ short runs even against its price). The NEW NFL depth
  weight (½ pt a head, cap 3, on the own read) touched 8 of the 17 NFL plays against the pick side; the 5 it would now
  drop (own read no longer beats the price) went 2-3, -1.8u, and the 8 it helps (opponent thinner) 5-3 +1.1u - the right
  direction, far too few to call. 2023+ holdout: all of this is 2023-26. VERDICT: keep - lifting the block costs
  nothing in the data we have (if anything it put plays back that won); the sample is 76 football plays, so the live
  record decides it: the 'more banged-up' NFL lead (-2.5 vs the price) and the box-score 'missing' noise both get a
  real test this season.
- Combined: old rules with a working block would have run about -16.5u (the 47 'blocked' plays out) to -14.4u (skill
  count); the new rules -12.4u. Neither change moves the needle; the needle is still the value plays' -6.7%.
- Scripts (scratch, not kept): nocap/run_nocap.py (the 7 cap days re-run with sports.MAX_PLAYS unlimited on the 10/2
  snapshot), nocap/nocap_an.py, nocap/injury_est.py. Re-run after the 2026 football season with the real injury
  reports (data/sports/injuries_official.json holds them from 10/2 on) - then the block can be replayed for real.
