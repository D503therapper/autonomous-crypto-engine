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
  of 6), engine agreeing +20.7% (4 of 6); THURSDAY night dogs -10.9% (NFL), -18.6% (college) - the owner's "whole
  other monster" is real, and it's the dog on Monday. FADES: an NFL dog in its coach's FIRST season with the team
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
  starts its #1, favorite doesn't: -0.6% vs -6.7%, 4 of 5) - needs the confirmed starter; college football yards
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
