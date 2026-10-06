# D503 Sports Engine - where things stand (read this first in every new chat)

Kept up to date at the end of every working session, so a fresh chat knows what the last one did. The owner's standing
rules are in CLAUDE.md; what the studies found is in SPORTS_FINDINGS.md. Newest notes on top.

## 10/6 - when to bet our hockey picks: 8 AM or near puck drop? (report only, nothing built)
- The repo has NO book-by-book hockey price history (the paid odds pull was football only); the study used the NHL
  opener vs close 2023-26 (4,152 games), our own hourly snapshots since 10/1 (35 games) and our 11 posted NHL picks.
  Favorites get bet during the day (bet them at 8 AM); dogs drift longer market-wide and on all 6 of our real dog
  plays, while a blind proxy of the engine's sides says the books come toward us 60% of the time over 3 seasons - a
  LEAD, mixed on the current season. tools/nhl_bet_timing_study.py; SPORTS_FINDINGS.md (10/6). NEXT: journal the
  8 AM / close price on every pick and re-run with 300+ hourly NHL games (early November).

## 10/6 - MLB pitcher-vs-team / rematch study (report only, nothing built)
- The owner asked for the pitcher-level version of "has their number" (team level DEAD 10/5). DEAD too: a starter's
  history vs today's lineup runs the wrong way against the price (most dominant quintile -6.8%), a rematch costs the
  pitcher about a third of a run per 9 but the close already has it (lineup side -1.0%). 18 cuts, all in
  SPORTS_FINDINGS.md (10/6); tools/mlb_pitcher_vs_team_study.py. Engine logic / weights / units untouched.

## 10/4 (evening) - early value plays audit (code + the live early.json vs the games)
- Fixed (tests in sports_test.test_early_play_and_the_same_board_pick_both_count): (1) the unit ledger keyed the early
  play and the game-day pick on the same (day, game, side) - the Jaguars ½u early row overwrote the 1u Dog, the unit
  record / today's results / bankroll lost +1.2u (the owner, 10/4: both count); (2) an early card said "winning 55%"
  (55.2% rounded) - the win % only shows OVER 55; (3) the game-day 'better price now' call read the market off the
  opponent's price at post time, now today's. Every graded / open early pick checked against the games: sides, prices,
  scores, dates and 'bye' claims all right (Tulane off 9/26, Army played 10/3).
- Live early record: 1-0 (+0.6u; the Jaguars 'best' backup). Price moves since we posted (closing-line value, the real
  early test): Alabama +130 -> -115 (+9 pts), Tulane +205 -> +140 (+9), Florida St +215 -> +180 (+4), Fresno / New
  Mexico St flat, NC State +124 -> +145 (-4), Jaguars +120 -> +124 close (-1). Not a sample yet.
- Owner's calls (recommendations, nothing changed): the 'hammered' spot is wired for college with NFL-only evidence
  (4 of 6 seasons); the Monday-night spot is +3.3% on 80 in the band (weak); the 'ice cold' fade counts FCS blowouts
  (NC State 73-0 over Richmond made a 3-1 team 'ice cold'); euro under and the hammered/blowout/engine spots keep
  their own records - judge at 30-40 bets each.

## 10/4 - banged up is a weight in football (the owner, 10/3: "it all just depends")
- Study (SPORTS_FINDINGS 10/4, our box scores 2021-26): a football side with 2+ regulars out does NOT lose vs its price
  (NFL -0.4 pts on 2,035, college +0.1 on 4,900) and the own read isn't fooled by depth bodies - the block was costing
  picks (Missouri +180 on 10/3) for nothing. Only lead: the NFL side 2+ MORE banged up than its opponent, -2.5 (4 of 6).
- Built: NFL / college with box scores - the 2+ out / 4+ questionable block and the 'more banged-up team' block are
  OFF; depth gap = a capped weight on the own read (sports.depth_penalty: NFL ½ pt a head, cap 3; college 0). Key
  players still sports_absences.penalty. Hockey / hoops / baseball keep the block (study them next, cheap to run:
  the 10/4 study script's approach - regulars on prior games vs the game's box score). Early plays' key-out rule kept.
- Watch on live picks: the NFL 'more banged-up' lead and '2+ skill regulars out' (-3.7) - grow the weight if they hold.

## 10/2 (overnight session)

**Live on main tonight**
- Live bets: never a 3-way / regulation-only / period line as the moneyline (the Devils +145 came from a backup book's
  3rd-period line - voided with the owner's OK); two books far apart = no price; a pregame favorite tied or ahead at
  plus money needs a second book; every live bet logs which book priced it; one box at a time (BET IT NOW, then
  TONIGHT'S LIVE BETS).
- Injuries: a QB / goalie on the report is only "the starter" if our box scores show he started lately - unknown is
  never claimed or weighed (the Steelers card called two BACKUP QBs starters). Re-run: the engine still had the
  Steelers (59%, a lean) with the right data.
- Daily pick audit (sports_audit.py -> data/sports/pick_audit.json), read by the 1 AM daily review routine.
- Units: every value play / Lock / Dog ½u+, leans 0; own read under 3% over the price = ½u. (The 8% line and
  "favorites ½u" were tried and rolled back - "no half units across the board".)
- Every factor weighed for both sides (weigh_favorites); study angles on a dog capped at ±6 (STUDY_CAP) - BEING TESTED.
- Thursday-night fade removed; momentum leads wired (NBA comeback-win fade, MLB late-rally dog); "washed" = an old QB
  (career by 2012) who's cold.
- Five audits' bug fixes (live, data merge of college games, early-play pings, board rules, grading). College games
  restored (316 had been wiped by the hourly job; game files now merge by id).
- Daily board dry run: tools/board_preview.py / Actions -> board_preview.
- The factor check before the 8 AM board (sports.factor_check) now also checks the data is FRESH: most of the slate
  priced 12h+ ago (odds pull failed), recent games with no final score, the QB / pitcher / goalie stats missing - each
  holds the board until the last try; a game or two the books stopped listing is only a note. The daily pick audit
  also checks the cards' own words (streaks, home/road, players named out vs the injury report).

**Studies done overnight (all in SPORTS_FINDINGS.md 10/2)**
- Unit system BUILT: the Lock by its own read, the Dog flat 1u, value plays ½u (712-day replay: since 7/2023 +10.5u
  vs the old sizing -15.2u; value plays lose at any size).
- Point system BUILT: NBA overreaction +5, NHL both-lost +3.5, MLB +200..+249 -4, NHL road-opener off, no double
  counting (NHL hot key / key edge; college ice cold + losing streak), college bye only within 30 days. STUDY_CAP 6,
  linear stacking and the favorites' weighing confirmed (no change). Per-sport point scaling = a LEAD (re-check).
- The backup near_lock loses (-17% flat) - kept at ½u because the owner wants a Lock every day.

**10/2 morning**
- Units: unchanged (value plays ½u, Dog 1u, Lock by read, backup Lock ½u). Claude's recommendation: keep them and
  reassess on OUR live results after 100-200 graded unit plays, not the replay - the owner was ASKING, not deciding
  (his words: "I'm not telling you anything. I'm asking you"); value plays -> no units is still open (the replay ran the current engine over 2023-26:
  -1.1% overall, +1.2% since 7/2023 - roughly break-even, and partly flattered by peeking; the owner doesn't trust it
  as proof). Live so far: Lock 4-0 +7.61u, Dog 0-3 -2u, plays 0-1.
- Backup Lock: titled LOCK with its own box above ("nothing met our Lock of the Day standard").
- The full pre-board check: data freshness (prices, finals, opening lines, models, player stats, weather, injuries),
  a sizing check, and a checker self-test (12 broken inputs, each must be caught).
- NEXT (offered, not built): a "beat the closing price" record on the dashboard - the fastest real test of an edge.

**10/2 later morning - INJURY DATA (the owner: "the most important thing in sports")**
- Found: ESPN's college injury feed listed 3 teams - Virginia Tech, Pitt, Penn State, Northwestern... were read as
  "nobody hurt". Fixed: official reports file (injuries_official.json) + a twice-daily routine that fills it; a team
  with no injury data gets no pick; 2+ out / 4+ questionable = no units, card names who's out; the 10/2 board was held
  until the owner said post (HOLD_DAYS).
- NEXT (big): weigh every position from box scores (RB / WR / OL / defense in football, top scorers in hockey, NBA
  starters) instead of the blunt no-units rule; automate the conference reports (their pages are script-built).
- Dylan Larkin (Red Wings captain) out 2 games; Hellebuyck (Jets) suspended to 10/17 - both were on the feed but
  skaters / suspensions weren't weighed.

**10/2 afternoon**
- NO FORCED LOCK (the owner's call): a Lock only when the read beats the price; the Lock spot says so otherwise.
- Missing key players now move the engine's own read (sports_absences, the 10/2 absence studies - SPORTS_FINDINGS).
- Injury data pipeline for college: workers find the official reports -> GitHub reads the pages (Actions ->
  fetch_pages, results/pages) -> verified lists go into injuries_official.json (10/3: 29 teams so far). Snippets alone
  are never trusted (several were 2024/2025 articles). A game with no injury report is off the table (not 'waiting').
- Fixed today: duplicate picks (merge keyed by post time), board posts at 8:00 sharp (7:44/7:47 runs), stale summer
  opens, 'running on fumes' on rested teams, both-teams-hot streak lines, report jobs failing to save, Cloudflare CPU.
- Waiting on the owner: the 8 AM note rewrite (on the claude/ branch, not main).
- 10/2 evening: Dr. Bob tracker LIVE (sports_capper -> data/sports/capper_drbob.json): his free NFL Leans from
  drbobsports.com/nfl-analysis, logged the first time seen with his number, graded off the final next to our pick on
  the same game (with_us / against_us). Record only - never moves a pick. First lean: Cleveland +3 -115 (won, 27-24).
  His site confirms: NO college football this year (NFL only).
- 10/2 evening: early hockey / baseball study done (SPORTS_FINDINGS) - NOTHING built: every spot either dead or a lead
  under 2 SE. Best lead: NHL rested team vs a back-to-back, engine 3+ over the open - log it live before any units.
- Waiting on the owner: the beat-the-close box on the dashboard (preview sent; code sits uncommitted on the claude/
  branch checkout - sports_dashboard.close_box + its test).
- 10/2 night: GitHub skipped the engine's hourly runs 3 hours - the hourly bug check now restarts it after 80 min.
- College injury coverage, the hard truth (10/2 night, 10/3 slate): 52 of ~200 lined-game teams verified. NO official
  report exists for non-conference games (UNC-Notre Dame, Syracuse-UConn, Cal-UNLV...) or for the Sun Belt / CUSA /
  AAC; the MAC posts game-day reports only (~3h before kickoff, getsomemaction.com). Those games stay off the board
  (no pick off blind data). The 5:47 / 11:47 routine knows all this now (prompt updated 10/2).
- 10/4: the owner's NFL SURVIVOR pool is tracked in data/sports/survivor.json (used: Ravens, Buccaneers (LOST), 49ers, Jaguars; two losses allowed, one used). Help him pick each week from the engine's win reads, never a used team.
- 10/4: 🌍 Europe morning NFL under LIVE at ½u (owner OK): posted the night before as an early play, own record, quit rule under 50% after 15 (sports_early.euro_unders). Early plays no longer ping.
- 10/4 routines: 7:05 AM PT pre-board check (builds the board as it would post, checks every card, fixes by 7:45),
  8:03 AM PT drop confirm, 1:07 AM daily review - NO phone pings from any of them (the owner, 10/4: the only
  notifications are mid-day value plays and live bets). Results go in STATUS.md. Europe morning NFL under tracked
  (sports_intl -> data/sports/intl_unders.json, no units). Early-morning (before-8-AM) game post the night before:
  TO BUILD (owner OK'd the idea; build after a clean 8 AM board, preview first - never touch the opening-board logic blind).
- 10/4: football injuries are WEIGHED, not a block (study: the line already prices who's out); no cap on unit plays
  (leans still fill to 5); early cards lead with the engine's read, never the same wording twice; day games say
  'today'; an early play can also be the game-day Dog / play (owner OK, 10/4 - Jaguars ½u early + 1u Dog).
- 10/3 evening: THE ENGINE READS COLLEGE INJURY REPORTS ITSELF every run (the owner: "the engine needs to be able to
  do the same" as Google). Football: Covers' public injury page (sports_data.page_injuries - 127 schools on 10/3, every
  one matched; a school listed with "No injuries to report" counts as covered). Basketball: Rotowire's feed
  (sports_data.web_injuries - 150 schools). Official reports in injuries_official.json still override. Short names
  ("J. Dawson") match the box-score regulars (sports_absences.match). Rotowire's FOOTBALL feed is too thin (7 rows) -
  not used. Check the engine log line "ncaaf injury page: N schools".
- 10/3: futures study (SPORTS_FINDINGS) - preseason longshots never beat their price; daily futures price log LIVE
  (sports_futures); the owner, 10/3: WAIT - no futures on the board until the mid-season study finds a real edge. Patty vs the
  Algorithm removed for good (the owner). No-Lock days: the question box names what the Lock would have been
  (sports.lock_miss).
- 10/3 Fable sweep (8 checks): ~25 bugs fixed + live (pacer, holds, injuries, grading, pick logic). Model check: the
  engine can't beat closing lines on spreads or favorite moneylines (SPORTS_FINDINGS 10/3) - few Locks is honest.
  Owner's open call: keep the Lock rule strict (recommended) or post more knowing they lose. Written but NOT pushed:
  NBA always on + hockey/MLB IL players count only if playing (wt stash) - owner to say go. TODO: card grammar pass
  (school names singular, no vague lines), sport-aware own_agrees tiebreak, key_edges train/predict match, college
  hoops injury source before November.
- THE OWNER'S QUEUE (10/3, do after his usage resets - in this order):
  1. MULTIPLE LOCKS: every game that clears the Lock test posts as a Lock (the best = Lock of the Day on top, the rest
     LOCK cards right under it, each sized by its own read, all in the unit-plays record). Show a preview first.
  2. Missing players are WEIGHED, never a hard rule (the owner: "it all just depends"): turn hurt() 'no units', the
     early-play 'never a side with a key player out/questionable' and 'key QB/goalie out -> go by the market' into
     study-sized weights (walk-forward on past games); update the CLAUDE.md injury rule wording.
  3. Push the wt stash: NBA always on (sports_strength.OWNER_ON) + hockey/MLB injured-list players count only if
     they've been playing (sports_absences.played_lately) - tested 328 green.
  4. Park the 'inj' learned feature (16-23 games of history) until a full season.
  5. Card grammar pass (school names singular, no vague/filler lines).
- 10/6: Dr. Bob blind study done (SPORTS_FINDINGS 10/6, tools/drbob_study.py): on his archived free NFL sides saved
  before kickoff (31, 2020-24), engine-same-side 6-7-1, Bob alone 14-15-2, engine opposite 8-8-1 - DEAD as a
  confidence / unit signal, far too thin anyway; no weight built. Found + fixed: the live tracker logged a total lean's
  matchup ('Over (51.5) – CINCINNATI (-2.5) vs Jacksonville') as a side; two bogus 10/4 'lost' sides (Bengals -2.5,
  Chiefs -4.5) still sit in data/sports/capper_drbob.json - owner's call to drop them.
- NEXT: capper studies (1)-(5) below; NHL rested-vs-back-to-back live log (no units); weigh OL / defense absences.

**Capper studies (the owner, 10/2 - "find the clowns and the actual cappers ... what the best are doing right")**
- Benchmark: Dr. Bob (Bob Stoll, drbobsports.com) - the owner's pick as THE proven capper. Self-published: NFL best
  bets 514-379-12 (57.6%) in 10 seasons (play-by-play model), college football best bets 55.1% since 1999, his
  releases move lines worldwide (outside proof of beating the close). Not doing college football in 2026.
- Five studies planned: (1) claimed vs graded records, (2) beat the close, (3) do max plays win more, (4) do hot
  cappers stay hot, (5) what the real ones do that we don't (spreads, play-by-play model, early timing, star sizing).
  Data: public pages only (SuperContest / Circa contest picks, dated expert picks) - no logins, no tricks.
- Compare: our engine's early NFL spread read (3.5+ pts off the Tuesday number) covered 58.5% on 554 (findings 10/1)
  - Dr. Bob-level, but a study, not live; build the early NFL spread play and track it live vs his 57.6%.

**10/4 big-dog study (NFL + college, dogs +150..+250 at the close, 2018-26)**: 29 situational angles the engine
doesn't weigh (home dog, conference proxy, off a loss, favorite off an emotional win, point differential vs record,
look-ahead, weather, totals, spread mismatch, streaks, road trips, late season) - 0 of 58 tests pass the false-discovery
check; nothing built. Full table in SPORTS_FINDINGS.md (10/4). One watch: an NFL favorite off an upset win (dog +17%
on 102, 3 of 6 seasons) - re-check after 2027.

**Open decisions (the owner's call)**
- "No forced locks": a Lock of the Day only when the read really beats the price, else "No Lock today" (CLAUDE.md
  still says ALWAYS a Lock until the owner says the words). The Dog stays real-value only; leans fill to 5+ picks.
- Card labels showing the edge size in words ("BIG EDGE - 3 UNITS" / "SMALL EDGE - ½ UNIT").

**Next builds**
- Stars beyond QB/goalie (NFL lead rusher / receiver, NBA top scorers) - verified from box scores only.
- Re-check the NHL elimination-dog finding before April; college hoops dog fix before November.
- Hockey: the engine has no real edge there yet (-2% on 1,851) - hockey dogs leave the Dog of the Day if the replay
  says they lose.
