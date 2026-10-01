# What the studies found (9/30, the all-night session)

Every number below: the engine trained only on seasons BEFORE the ones it's graded on (no peeking), graded at real
prices. "Last 3" = 2023-26 alone (the owner: the sports have changed, old seasons can mislead). Built = in the engine.

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
