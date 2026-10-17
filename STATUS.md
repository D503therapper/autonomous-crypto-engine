# D503 Sports Engine - where things stand (read this first in every new chat)

Kept up to date at the end of every working session, so a fresh chat knows what the last one did. The owner's standing
rules are in CLAUDE.md; what the studies found is in SPORTS_FINDINGS.md. Newest notes on top.

## 10/17 - daily studies + yesterday's picks (SPORTS_FINDINGS.md 10/17 "TEN STUDIES")
- BUG: the 8 AM board posted twice (8:00 sports run + 8:01 live-watcher pass); the merge kept both - Wisconsin Lock +114 AND a play +102, FAU a play AND a 2nd Lock +110. FIXED from 10/18 (one pick per game / one Lock per round, engine load + merge driver). TODAY'S extra 8:01 copies are still on the board - OWNER'S CALL to remove them (posted-pick rule).
- Built (weights): NHL dogs +220 and longer -3; NHL dog whose record is 10+ under its goals (5-20 games in) +2. Fixed the tracker's 10+ gap college tag (raw read).
- 10/16 review: leans 1-1 + void, no unit plays; Coastal beat the close and blew a 24-14 halftime lead.

## 10/17 - the six open early plays audited (the owner: "huge underdogs, upper 200s, at two units") - SPORTS_FINDINGS.md 10/17
- The 2u plays (Tennessee +270, San Diego St +245) are the college EXAM BAND (sports_early.scan), sized by quarter-Kelly on the RAW own read - the rule as written, on the read the 10/15-10/16 studies showed the market beats. The band passed at the bare minimum (60 dogs / 20 / +2.8%) at 16:38Z on 10/16, three hours after failing (53 dogs -9.4%); one 2025-26 result flips it.
- FIXED (worktree, test_early_exam_scan_posts_only_the_band_the_exam_graded): the scan posted by the gap at the price NOW while the exam grades the gap at the OPEN - the scan-only dogs ran -6.3% blind (41) vs +19.6% for the exam's own. Now the band must hold at the early price too (sports_early.exam_band_ok); the exam scan also asks college completeness (seen_all) like the spots. Would have blocked Tennessee (-14.8 at its +100 open) and San Diego St (+8.7 = the failed +8+ band). Posted picks untouched.
- Ranking best to worst: Kentucky +195 1u, Boston College +215 1u, Marshall +114 1u, BYU +300 ½u, San Diego St +245 2u, Tennessee +270 2u (starting QB Faizon Brandon questionable on the Thursday SEC report, filed 19 minutes after the post).
- OWNER'S CALLS: (1) exam-band plays flat 1u (on the band's own 60 dogs flat +7.4% vs Kelly +2.9%; the 2u-sized went 9-15); (2) whether a knife-edge band should carry 6u this week; (3) the NFL blowout spot is still ON in code (blind -12.5%, live 1-8).

## 10/16 (PT morning) - injury reports filled for Sat 10/17: 19 teams, all read from the pages
- Official reports (SEC / Big Ten / ACC / Big 12 / Mountain West, Wed-Thu): Alabama, Tennessee, Michigan, Penn State, Ohio State, Indiana (Wed list only), Michigan St, Northwestern, Duke, North Carolina, Pitt, Louisville, Syracuse, Utah, Colorado, New Mexico, Hawai'i. Team news (Mon 10/12): Notre Dame, BYU. Friday-night and Saturday game-day reports will move statuses - the next routine refreshes them.
- Still nothing (no named list found on a readable public page): Boston College (Pitt's side is in), Wake Forest / Cal, Fresno St / San Diego St, Navy / UTSA, UTEP / San José St, Ohio / Sacramento St, the MAC games, Rice / Tulsa, Sun Belt games, the FCS slate. Covers/Rotowire on game day carries FBS.

## 10/16 - injury coverage audit for Saturday 10/17 + the NFL / NHL weekend - SPORTS_FINDINGS.md 10/16
- Every priced team on the slate (100 college, 26 NFL, 32 NHL) has box scores, so football's weighed rule and hockey's played-lately list run everywhere. College coverage on game day is Covers' page (every FBS school) + Rotowire + ESPN live, plus injuries_official.json - which holds NOTHING for 10/17 yet (61 of the 100 teams carry last Saturday's list, correctly NOT read as current; sd.official reads ±1 day only - now pinned by a test). The owner's 12 named teams: all have box scores; BYU / Air Force / Tennessee / Georgia Tech / E Michigan have stale 10/9-10/10 entries; BC / Rutgers / FAU / Wisconsin / WVU / Rice never had one; Old Dominion isn't on Saturday's slate (Thursday game, early play pulled 10/14).
- FIXED (worktree, test_injury_line_names_the_players_who_play_first): the 🚑 line and a card's 'outs' listed the report's first four rows - the 10/10 Minnesota Lock led with the backup QB. Now the box-score regulars come first (QB / goalie ahead), nothing dropped (sports.who_plays_first).
- SATURDAY CHECKLIST: the 5:47 / 11:47 routine files the SEC / ACC / Big Ten / Big 12 reports under "2026-10-17"; Actions -> injury_report Saturday morning should read "NCAAF - the feed lists 130+ teams" (under 20 = the Covers read broke). LEAD: skip a day-before official entry for a team that already played that day (matters only if pro entries ever get filed).
## 10/16 - recalibrating the college own read (the root of BYU 48% vs market 24%) - SPORTS_FINDINGS.md 10/16
- Walk-forward 2018-26 (fits 2018-22, blind 2023-26, 6,009 priced games): the raw college read (sports_model.own_p, what the early spots use) is calibrated by its own buckets (said 45 won 48, said 55 won 52) but holds nothing the market lacks - the fitted shrink toward the market is 0.000; temperature / isotonic recalibrations are no-ops (BYU 48% -> 47.7% / 51.4%; shrink -> 24%). Market log loss 0.4929 vs the read 0.5572 blind, every season. The sides any recalibrated read likes lose or break even blind (dogs -0.4..+0.7%, favorites in-sample -14%).
- NOT BUILT (no code change): the only honest calibration is trust 0 = the market, which would zero the college gap in the early spots - the OWNER'S CALL from 10/15 (call 1) stands; the 5-point cap (sports_early.NCAAF_GAP_MAX) stays. LEAD: the read needs new information (FCS marker, QB availability, official reports), not a better curve.
## 10/16 - the unit plays by size (1-2u went 5-11 live) - SPORTS_FINDINGS.md 10/16
- The 1-2u bucket is the Dog of the Day (13 of 16; 10 hockey Dogs, 8 of them the best-hockey-dog fallback). 5-8 on 13 Dogs is noise: the same bucket runs +10.0% (blind +8.7%) on the 2023-26 board replay re-sized under today's rules (tools/sizing_by_bucket.py, kept).
- OWNER'S CALLS (proposals with numbers, nothing changed): (1) the Lock's Kelly size - flat 1u +18.4u vs today's by-read -28.7u on 675 replay Locks; the 2u+ Locks lose -3.7% flat in both halves (the live 3-0 at 2.5-5u is luck by these numbers); (2) the Dog whose own read sits under the price (fighting() allows 3 points): -7.4% on 133 (blind -11.6%) vs +11.7% on 254 when the own read beats the price too - Dog only with the own read over the price, or ½u. WATCH: the 2u Dogs (6-12 in the replay) and the +120..+150 Dog band (+28%, a lead).
- Fixed (worktree, test): a posted Dog's leg now keeps "dog_score" next to dog_p (the audit had to back it out).
## 10/16 - bug sweep of the board-building path (worktree, 3 fixes + tests) - SPORTS_FINDINGS.md 10/16
- Fixed: (1) the backup Lock could post a favorite whose WEIGHED read (w_p) was under the price - ½u, then pulled by rule_check = no Lock while the next favorite qualified (sports.backup_lock now needs real_value); (2) dedupe_picks missed the stale PLAY copy of a Dog upgrade_dog had promoted (the 10/13 Kraken bug's mirror) - the team showed twice and the record counted it at ½u; (3) the study-index cache (sports._index) keyed by id(games) + count could serve a stale index to the live watcher's reloaded games. Posted picks untouched; today's picks.json is clean (no double rows, no both-sides, no lean with units).
- OWNER'S CALL: a night / one-game-day pick that's a value DOG sizes up to 2u by its edge while the same dog as a daily play is ½u (PLAY_UNITS). Proposal: PLAY_UNITS for those too.
- Suspected, not reproducible: two concurrent runs posting two different Dogs; the early 3-day window anchored at ready(), not the first fair number's stamp (college ~2 days); no window at all on both teams' season openers.
## 10/16 - how the leans are picked, round 2 (the 🟡 record 17-21) - SPORTS_FINDINGS.md 10/16
- Blind replay 2023-26 (687 board days): today's who-wins rule 52.7% straight-up vs 53.5% market-expected; the market favorite 54.6% (vs 55.0% expected - pricier sides, no skill); own-read / p / blend / 'market and engine agree' 52-54%, none beating its price by more than noise. The spread leans (55.6% vs 52.3% on 340) and the dogs are the only pieces above their price - every 'agree' rule drops them. DEAD, nothing changed in viewer_leans.
- OWNER'S CALL (not built): leans that hit more often only come from pricier favorites (-120..-150 by the engine's p, ~55% blind) at the cost of the dog and spread leans - or leave the leans as who-wins calls and read 17-21 as noise around 53%.
## 10/16 - write-up truth audit 10/8-10/16 (SPORTS_FINDINGS.md 10/16) - worktree, not pushed
- ~190 claims on 36 cards + 16 early plays + 46 reviews checked against the repo's own game files / box scores / line
  history as of post time: 17 false, 5 vague (9 of them the 10/15 fixes). Line moves 24 of 24 right, player numbers 9 of
  9 right, records all right but "Records are close (85-77 vs 98-64)".
- Fixed (8, tests test_truth_audit_10_16_*): another team's headline is never this team's drama (the Byram / Sabres
  line, twice); camp talk needs the team's name in the headline; no "everybody available" next to a questionable list;
  "same kind of record" needs a small win gap; a period line that doesn't add up to the final gives no review fact (the
  Canadiens "5-4" on a 5-3 game); no "never had a chance" review when the other side led at the half; the goalie line
  says "who had their net last time out" until the starter is confirmed (Askarov / Dobes / Dostal didn't start); "they're
  the hotter team" needs a real streak; the pitcher hype line carries his numbers or doesn't print.
- WATCH: a card's text is built at 8 AM while the hurt list refreshes hourly - "Full squad for the Maple Leafs" sat next
  to a 3-name hurt list on 10/15. If it shows again, rebuild the 🚑 / ✅ lines on the hourly pass.
## 10/16 - NHL checkup (walk-forward replay 2023-27 + the live picks audited) - SPORTS_FINDINGS.md 10/16
- Replay at the close (681 board days, 8,436 sides): Lock +6.7% on 224 (3 of 3 seasons up), Dog via the score gate 6+ +17.3% on 146, Dog via best_hockey_dog (score 0-6) -1.6% on 118, value plays +7.8% on 86, regular leans +0.5%, FILL leans -14.3% on 227 (down 4 of 4). Every dog weight points its built way on 2023-27 (ss_pos / ss_neg, both lost, PDO, drift, b2b, +200, goalie form on the last starter, 40-shot, fired coach); third_in_four holds on the favorite (+2.5% vs -5.8%); NHL_EARLY_FAV shows no signal (the owner's rule, untouched); playoff lost_last (+3) is the one wrong-sign weight (97 games, WATCH).
- Live 9/27-10/15: 0 stale flags on 34 hockey picks; 11 of 12 Dogs were best_hockey_dog (score 1-6); the goalie-roles weight never fires at 8 AM (Daily Faceoff confirms after noon).
- FIXED (worktree, test): the 🥅 / 🧱 goalie line named the LAST starter as tonight's goalie - 5 of 7 lines this season named a goalie who didn't play (the last starter starts 45% of the time). Unknown starter = "X, in net last time out for the Sabres, ..."; confirmed / likely = the plain wording.
- OWNER'S CALLS: (1) no hockey FILL leans (-14.3% on 227, 4 of 4 seasons down; the -150..-130 lean favorites -12.5% on 226); (2) keep or cut the "best hockey dog over 0" Dog fill (-1.6% at the close, live 7-16 at 8 AM) - the gate-6 Dog is the money.
## 10/16 - the MLB own read's calibration (study only, nothing built) - SPORTS_FINDINGS.md 10/16
- tools/mlb_read_calibration_study.py (walk-forward 2018-26): the RAW read the early exam / scan use runs +4.2 pts optimistic on the side it likes (every season 2.8-4.9, postseason +4.5); the board's read (ph_own, already shrunk by trust) +1.1. Fitted shrink: keep ~8% of the raw gap (a .09 raw / .075 recent-seasons in 2026; the board read a ~0) = the market.
- Not a bug (a logistic read honest over all games, wrong where it disagrees with a sharper market). OWNER'S CALLS: (1) shrink the MLB early read -> the +8..12 exam band ends (blind +16.7% flat on 252 dogs at the open 2023-26, 3 of 4 seasons; live 2-0 +7.7u); (2) size exam-band plays by the band's record (flat 1u / ½u), not raw Kelly (the Brewers 3u rode on a read 9 points over); (3) the MLB Lock loses blind (70-69, -10.9%; postseason -27%) with or without the fix.
- Fact: the MLB exam band passed 10/1-10/14 and fails since 10/15 (the key-form change moved a few dogs; season 1 -6.4% on 58) - a gate that swings on 2-8 dogs.
## 10/16 - NBA + college hoops readiness, round two - SPORTS_FINDINGS.md 10/16
- The real post_board run on NBA 2025-10-21 / 12-30 / 2026-01-15 and college hoops 2025-11-03 / 11-07 / 2026-01-15 with fake injury feeds: no crash, no forbidden pick, UNKNOWN schools get no pick, a dead feed = no picks, write-ups' records true.
- FIXED (worktree, tests): (1) data_gaps / seen_all took 8 minutes on a college hoops board (27M strptime calls) - cached, 207 s -> 6 s; (2) a lean favorite (no units) hid a gated dog in one_side - the Dog slot sat empty and the dog posted as a ½u play (Grizzlies +103, 12/30/25); (3) the fade line printed a price that didn't move ("-4500 → -4500").
- Blind NBA board 2023-26 (543 days): Lock 59-38 +15%, all unit plays 102-80 +20%, ½u Dog 8-10 +1u (lead), leans 53% flat. College hoops replay PARTIAL (restarted after the speed fix; rows in the scratchpad hr_ncaab_*.jsonl) - finish it before judging; November Locks size big (6u on opening night off last year's ratings).
- OWNER'S CALLS: (1) cap / shrink college hoops Locks in the season's first two weeks; (2) +200..+300 gated dogs: ½u plays (today) or the Dog at ½u; (3) nothing on NBA ml leans (48.8% in 25-26, no units).

## 10/15 - the college own read vs the market (the BYU +300 early play) - SPORTS_FINDINGS.md 10/15
- Fixed (worktree, test): a college read 12+ points over the price counts nothing in the early spots (sports_early.spot_gap / SPOT_TRAP), like the NFL / NBA - blind 2024-26 the market was right in every 10+ bucket (the read ~50%, the sides won 26-38%). BYU's and Old Dominion's posts would not have cleared the bar. The posted picks themselves were not touched.
- OWNER'S CALLS: (1) shrink the college early read to the market by the tune's own trust (0.02) - the 5-10 bucket lost -22% blind too; (2) add ncaaf to sports.OWN_TRAP on the daily board (college dogs 44-80 this season).
- 10/16 BUILT (worktree, test_college_qb_form_skips_fcs_games_the_sam_houston_case): college QB form counts FBS games only - FBS membership read from the game files walk-forward (sports_players.fbs_set, matches the real lists 2018-25); the card says "in his last 3 games against FBS teams". Blind 2021-26 the read's accuracy is unchanged (log loss within 2 bp); the 'better QB' labels that stood on an FCS game were noise (59.2% vs a 59.8% market). Opponent-strength adjust: no gain, not built. Same FCS inflation left alone (rule-level): Elo / form, the paused 'blowout' early spot (104 of 250 FBS blowout wins this season were vs FCS) - SPORTS_FINDINGS.md 10/16.

## 10/10 - the owner's calls + fixes
- Dog price limit raised to +300 (the owner: "I want the new limit to be +300") - the Dog, the dog gate, value-play dogs, lean dogs and the early spots (sports.DAILY_DOG_MAX / DOG_DAY_MAX, sports_early.SPOT_DOG / SPOT_ANY). The studies behind the spots were +100..+220 - the +220..+300 range is new ground, judged live.
- TO FIX NEXT: seen_all blocks a college team with TWO bye weeks (North Carolina 2-2, all 4 games held - the owner confirmed) - before refusing a team's record, confirm the gap weeks against the team's real schedule (ESPN team schedule via the hourly run, public) instead of assuming a missing game.
- Leans: value-picked leans were built then REVERTED the same night - the 10/10 college dog study found all six value-lean rules lost blind vs who-wins. The owner's call: who-wins leans, but no college favorite lean at -150..-130 (red both halves; sports.LEAN_NCAAF_FAV_BAND). College dogs this season: 44-80, -12.6% at the close - not hot; the 4+ gate stays (2+/3+ lost blind). SPORTS_FINDINGS 10/10.
- College hoops dogs ON (the owner: "we need college basketball dogs"): the NBA-style dog-score gate (4+, sports.NCAAB_DOG_RULE = "score") at ½u - the best of the three blind options (flat blind; today's own-read rule lost -15.8%). Its own record; judge it live.
- College hoops injuries: Covers' college basketball page (every D1 school, healthy ones too) read every run (sports_data.WEB_PAGE ncaab) - 364 of 364 schools matched on the 10/10 page, on top of Rotowire + ESPN + the official reports.
- Fixed: a graded 🎯 early row (Iowa) sat on the page past its 2 hours - now it carries the page's own timer (data-gone), and the box goes when its last row does.
- Units (the owner 10/10): Locks keep sizing by edge (½u-10u - recent Locks were pricey favorites with thin edges). The Dog of the Day now sizes by edge 1u-2u (sports.dog_units) - except hockey Dogs, flat 1u (live 4-6, closing at worse prices), and NBA / college hoops Dogs ½u.

## 10/10 - live scores: every game we hold gets one (Wyoming at San José St had none, 10/9 night)
- Cause: the watcher wrote a live score only for a game it could match BY NAME to Action Network's list (sports_live._keep_score -> _match -> sd._same); ESPN's 'San José St' (accent) never matched 'San Jose State ...' - same for 'Hawai'i' and 'FIU' vs 'Florida International'. Those games also could never take a live bet.
- Fixed: sd._same drops accents / apostrophes / periods and tries a book's long name through WEB_ALIAS ('Florida International' = 'FIU'); and ESPN's scoreboard by game id (our ids are ESPN's, no names) now puts a score on every stored regular-season / playoff game that's going or final when Action Network's list missed it (sports_live.espn_backstop, ESPN_LIVE), in every league where our own schedule says a game started in the last 6 hours (sports_live._started_lgs) - not only where Action Network shows one live. live.json carries "espn_only" (how many scores came only from ESPN) and such a score says "src": "espn".
- LIVE CHECK ON THE RUNNER: watch live.json "espn_only" on a college night - a steady count means Action Network's FBS week list drops Mountain West / C-USA games (then its list is the gap, not just the names). Cycle time: one ESPN scoreboard read per league already running, in the same thread pool - took_s should stay ~8s.
## 10/10 - college hoops readiness check (the season opens ~11/3) - SPORTS_FINDINGS.md 10/10
- Pipeline checked end to end on 2025-26 (2026-01-15); two bugs fixed with tests (worktree, not pushed): (1) ncaab missing from INJ_LEAGUES - a dead injury read posted a college hoops Lock WITH UNITS blind; ESPN's college feed failing no longer drops Rotowire's report; (2) the completeness check (seen_all) wiped most of the November hoops board (39 of 39 priced games on 11/7/25, 26 of 33 on 11/26) - a team with a full D1 season last year is complete (v24.NCAAB_D1_GAMES).
- OWNER'S CALL (asked 10/10): the college hoops Dog. Blind replay 2022-26: today's own-read gate 14-22, -15.8% blind; a dog-score 4+ gate flat (-0.1% on 82); nothing cleared the five checks. sports.NCAAB_DOG_RULE = "own" (today) / "score" / "off" - recommended "off" (no units on college hoops dogs) with the score-4+ dog as a lead. Default unchanged.
- INJURIES before 11/3 (report only): a hoops school on no report gets no pick (the rule). Plan: add Covers' college basketball injuries page to WEB_PAGE (every school listed, like football - verify the layout on a GitHub run first), the routine reads the SEC's basketball availability reports (conference games, from January) into injuries_official.json, Rotowire fills the rest. Check Actions -> injury_report on opening night ("NCAAB - the feed lists N teams").

## 10/9 - the owner's calls
- Value plays are MONEYLINE ONLY (sports.PLAY_MARKETS = ("ml",)) - spread value plays become leans (they lost every season, no own read).
- NBA: Locks carry units from day one; an NBA Dog of the Day at ½u when a dog's score is 4+ (sports.NBA_DOG_GATE, DOG_UNITS_BY) - its own record, judge it live.
- Live plus money: the 55% bar stays (the owner: "ok").

## 10/9 - daily studies (10): nothing built
- LEADS (watch live, not wired): NFL road dog after a Thursday game (39-21 ATS), 7+ first-meeting loser as a +100..+220 dog in the division rematch (45-29 ATS), G5 dog vs a Power team at the Tuesday price (92 bets, +20%), ATP indoor-record favorite in the first fall indoor events (paper).
- Timing fact: college dogs Tuesday-Thursday / favorites at game time CONFIRMED; NFL early-dog edge now only +100..+140 and September dogs.
- DEAD: NHL road trips, NHL start times / time zones, college look-ahead, Power-vs-G5 (the 10/1 September watch closed), tennis fatigue, tennis indoor swing / jet lag, G5 'soft lines'. SPORTS_FINDINGS.md 10/9.

## 10/9 - NBA readiness check (the season opens ~10/20; college hoops early November)
- Pipeline checked end to end on 2025-26; three bugs fixed with tests (preseason live bet, preseason 'missing result' holding the board, cover streaks over the summer). SPORTS_FINDINGS.md 10/9.
- Blind NBA board replay 2023-26: Lock 54-32 (63%), +16% over the two graded seasons; leans -4% flat; NO Dog possible (dog_gate has no NBA branch); a dog-score 4+ gate is a LEAD (15-12, +11.5u blind), not built.
- OWNER'S CALL (asked 10/9): units on the NBA Lock from day one (recommended), leans only otherwise; build the NBA dog gate (½u, own record) or wait. Still open: college hoops injury source before November; opening-night hoops rotation comes from last season's last 10 games until new box scores arrive.
- Still running 10/9: the value-play study (why ½u plays lose) and the Bovada live-lines fallback.

## 10/9 - "no college live plus money on Thursday night" check (the owner's question)
- College football IS in the live feature (sports_data.LEAGUES / BOVADA_PATH / KAMBI_PATH all carry ncaaf; the comeback
  curve has 17,661 college games; Kentucky +115 won and Michigan +105 lost live on 10/3). The watcher ran all night
  (a results commit from it every 2-45 min, 22:40Z-07:47Z; 12 chained Actions runs, none failed, crash = None).
- Why nothing posted, any sport, since 10/4: (1) the live self-check raised the bar to its 55% cap on 10/4
  (data/sports/live_tune.json: said 56.9%, hit 52.9% over 17) - a new live bet needs a 55%+ chance AT plus money;
  a trailing favorite never gets there (Arkansas St down 3 at half = 42% on the curve, Cowboys down 7 at half = 54.9%),
  and it eases only when NEW bets grade, so at 55% it is stuck for good (the owner's call - the record backs the bar:
  bets we gave 55%+ went 7-1 +7.8u, under 55% 2-7 -4.6u). (2) Bovada returned no team-sport live lines all night
  ("Bovada has no live lines for mlb, nba, ncaaf, nfl, nhl" in every check) - BetRivers was the only real book, and a
  DraftKings-only price never posts (the 10/4 rule). The repo keeps no live price history, so whether Arkansas St or the
  Cowboys were ever plus money can't be shown - but by the rules above no spot in those games could have fired.
- FIXED (worktree, test_live_never_fades_an_early_play_and_a_dk_only_price_is_not_priced): an OPEN EARLY PLAY now locks
  its game for live plus money like a board pick does (the owner, 10/8: never the other side of our own pick; the 🌍
  under takes no side); a DraftKings-only price no longer counts as 'priced' (live.json: priced / dk_only / min_p; the
  health check names it). LEAD, untestable from the sandbox: the Bovada liveOnly feed went empty 9/27 too - BOVADA_ALL
  (full feed, live=True events) is defined but never used as a fallback.

## 10/9 - live record vs the closing line (report only, nothing changed)
- Every graded pick 9/27-10/8 (34 unit plays, 24 leans, 2 early) checked against the last pre-start price in line_history. Totals match the dashboard: 💰 21-13, +10.2u on 31u, ROI +33%; 🟡 leans 10-14. Every result matches the final score; no pick past -150; no lean with units; no opposite sides.
- CLV (beat the close, win-% pts): all unit plays avg ~0 (beat 7 / same 14 / worse 9 of 30); since the 10/2 unit system -0.5, beat 2 of 17. Winning, but not beating the market yet - mostly favorites hitting.
- By kind: LOCK 6-2 +8.5u CLV +1.0 (North Texas -118 closed -148) - the one kind that looks like skill. DOG 3-7 -2.2u CLV -0.6, beat the close 1 of 10 - all hockey (NHL dogs 4-6, -1.1u, CLV -0.7: Sharks +145->+170, Blackhawks +180->+190); non-NHL dogs 6-3 +1.6u. PLAYS 4-1 +1.4u CLV -0.4 (luck so far). EARLY 1-1 CLV -1.5. LEANS CLV +0.1; every spread lean got a worse number than the close.
- By sport (unit plays): NFL 5-2 +5.7u; college 5-2 +4.6u; MLB 7-2 +1.6u; NHL 4-7 -1.6u.
- Notes: 2 of the 6 Lock wins (Yankees 9/29, 9/30) had the own read below the price (pre-10/1 rule); the 💰 record holds 8 parlay legs from 9/27-9/30 (6-2, +1.9u - the 9/30 rule; without them 15-11 +8.3u); Western KY 10/1 1u and the Kings/Blackhawks ½u Dogs are pre-10/2 sizes.
- Watch: hockey Dogs posted at 8 AM keep closing at a bigger price (the money runs away from them after we post). Re-check at 30 Dogs before any rule change (the owner's call).

## 10/9 - Saturday's data audit (college / NFL / NHL, from the repo's files)
- FIXED (sports_breakdown_v24.seen_all + test_seen_all_counts_football_weeks_not_days_from_the_opener): the
  completeness check counted 7-day slots from a team's own opener, so a Thursday 9/3 opener + one bye + a Saturday 10/10
  game (37 days) read as 'six weeks, four games = a game missing' - Georgia Tech, Utah and Kansas failed it and BOTH
  sides of Duke-Georgia Tech and Kansas-Utah would have had no pick; Ole Miss (Labor Day Sunday opener, 10 days after
  the season's Thursday kickoff) read as 'opener too late'. It now counts football weeks (Tuesday-Monday, Pacific).
- Still flagged after the fix, on purpose: North Carolina (4 games, nothing 9/5 or 9/26 - two byes or a missing game;
  needs a live check of their schedule before they get a record or a pick), the Ivy League (opened 9/19 - no record).
- West Florida @ Abilene Christian (10/3, unpriced) is stuck 'live' with no score - outside the 3-day re-pull window;
  Abilene Christian's record is a game short until 10/3 is re-pulled by hand.
- Injuries: injuries_official.json holds only Friday's 9 teams (Washington St is missing for Wash St @ Utah State);
  none of Saturday's 94 games yet - that's the 5:47 / 11:47 AM routine's job on 10/10 (plus the live Rotowire / Covers
  reads). 48 of the 52 priced Saturday games have no injury data in the repo right now.
- Odds: every priced FBS game has a moneyline and a spread (11 have no total yet); 49 of the 101 college games are
  unpriced FCS / D2 games. NFL week 10/11-10/12: 14 games, all priced, every team's 5-6 games held, box scores for all.
  NHL 10/10: 13 of 14 Saturday games have no price in the file yet (the hourly pull fills them).

## 10/8 - daily studies (10) + early plays graded right away
- Early plays now get graded by the quick results pass the second a game ends (NMSU sat ungraded 10/7), and the game-day 🎯 row shows the live score (🔴 LIVE / FINAL / HIT / MISS) like every card.
- BUILT: NHL "allowed 40+ shots last game, plays again within 2 days" - a weight (-2 dog score / -1½ on a favorite, +1 for the side facing it); its own lead record ("NHL side outshot 40+ last game (fade)"). sports.outshot / sports_form.outshot_states.
- LEADS (not built, re-check): MLB playoff bullpen workload (fresh pen vs a pen with 4+ IP the last 2 days: 61-24, blind 31-12 - only 85 games), NFL winless 0-3+ ATS (55-34-5), college spread-vs-moneyline disagreement, the backup QB's 2nd start after a 2-INT first (fade). DEAD: book outliers, line-move shapes, key-number crossing, NHL cold-start bounce, goalie fatigue, MLB series spots. Details in SPORTS_FINDINGS.md 10/8.
- 🐶 NEW RULE (the owner, 10/8): the best value dog is the Dog - a dog value play found after 8 AM with 3+ points more value than the posted Dog (neither game started) takes the Dog spot at 1u, the old Dog becomes a ½u play (sports.upgrade_dog). 10/8 itself: Predators +11.6% vs Flames +11.1% by the full read - too close, the Flames stayed the Dog (owner: OK). The owner has a $200 parlay: Bucs +8.5 -115 / Predators +145.
- Odds API: 50 credits left of 20,000 (free check 10/7). Nothing more pulled until it refills - and only with the owner's OK.

## 10/7 - the move model as a live early spot? Re-checked blind first: DEAD, not built (the owner: "we need to be on these lines before they move")
- tools/early_move_recheck.py + tools/early_move_live.py; SPORTS_FINDINGS.md (10/7, top). The 10/1 "which dogs the
  money comes to" model (NFL +6.0%, college +5.8% at the first fair price) got its edge from ONE input that looks at
  the week's SECOND price to bet the FIRST - a leak. Honest (first-look facts only, blind read, fit on earlier
  seasons, fixed cutoff): NFL -5.9% (2 of 6 seasons, 2026 -19% on 18), college -2.7% (2025 -26%, 2026 -3%); it calls
  the move only 2-7 points better than any dog. This season's hourly lines: 1 NFL pick (pending), 9 college picks
  6-1 but 7 finals (3 FCS) - no sample. Fails checks 3 and 4 in both leagues -> no seventh spot, no weight, no units,
  no model file; the engine is untouched. The honest version of that leaky input is the 🔨 hammered spot, already live.
- Pinned by sports_test.test_move_model_is_dead_not_an_early_spot (no money/move spot, no look-ahead feature, the
  cents math across +100/-100). The early plays keep doing what the owner asked - posting at the first fair number;
  their own records (30-40 bets each) are the proof, not a model.

## 10/7 - "how often is sharp money right?" (the owner's NMSU +200 vs the FIU move; report only, nothing changed)
- tools/sharp_money_study.py -> results/sharp_money_study.json; SPORTS_FINDINGS.md (10/7, top). The side the line
  moves to wins 55-57% straight up (it's mostly the favorite) and the opener price beats the market (+3% at the open,
  all sports) - but following it at the close loses ~5% in every sport (0 of 4 seasons) and fading it loses ~7%. Every
  money-vs-tickets split signal loses at the close except the NHL sharp dog (+14.5% on 182, the 10/1 lead, already
  wired +1). The engine's side when the money then runs 15+ cents against it: usually a bad side (-16% at our price
  over 2,522, every sport) EXCEPT college football at the first look of the week (coin flip, +5% +/- 8 at our price).
  Found and fixed in the log: the 10/6 night-vs-morning "college dogs the money ran against overnight won" was
  backwards - the code's bucket was the dogs the money came TO; the dogs the money left lost -30% (36 games).
- NMSU +180 -> +195 (the money left, 15 cents) - pending; no rule says pull it, no rule says chase FIU.

## 10/6 - post the unit plays at 8 PM the night before or keep 8 AM? (report only, nothing changed)
- tools/night_vs_morning_study.py -> results/night_vs_morning_study.json; SPORTS_FINDINGS.md (10/6, top). NFL: keep
  8 AM (no price to gain, ±1 cent; a QB ruled out overnight hit 1% of night picks and all of them lost). College:
  favorites get longer by morning (keep 8 AM), the engine's dogs get ~1.5 cents shorter (+0.9% ROI, 5 of 7 seasons,
  this season -0.3%) - pennies, not a rule change. NHL: 3 seasons say ~+1% for a night post, but this season's 27
  hourly games and all 20 of our real picks with an 8 PM price got a BETTER price at 8 AM, and no goalie is confirmed
  at 8 PM - not yet, re-run in November. MLB: the early edge lives in the opener, not 8 PM -> 8 AM; keep 8 AM.
  Caveat: the paid football history has no 8 PM look (NFL 'night' = Saturday 10 AM PT, college = Thursday).

## 10/5-10/6 - session wrap (owner decisions + fixes)
- Owner calls: graded cards stay 2 hours (was 3); a lean never flips sides on a price tick (sports.stick / lean_sides.json,
  viewer leans + night pick + Lock-slot lean; flips only if the own read of that side drops 3+); confirmed NHL goalies
  built (sports_goalies, +2 dog weight, '🥅 IN NET' card line/alert); no logging of our own pick prices for timing ("takes
  years") - bet favorites at 8 AM, dogs can wait; Dr. Bob agreement = no extra units (blind study dead).
- Fixes: football starting QB = last game's starter (Cooper Rush alert); former-player obituary isn't team drama; card
  guard drops 'walking bucket' outside hoops + 'rest is on the field'; a trip both teams made isn't a reason; a hockey
  favorite the weighed read has losing is never a fill lean (Panthers 10/6); Bob tracker total-lean parse + 2 bogus rows.
- Board preview now lists EVERY DOG (price needs vs read, what kept it off).
- Open: survivor pool (Ravens/Bucs/49ers/Jags used, 1 loss of 2); pause daily studies until NBA? (unanswered); question
  box runs until the API credit is gone, then closes itself; 10/11 London Eagles @ Jaguars = first live Europe under.

## 10/6 - bug sweep of the 10/4-10/6 pieces (the owner: "double check everything we've added")
- Read every sports diff since 10/4 (goalies, lean memory, football QB = last game's starter, 2-hour graded cards, trip
  line, every-dog preview, obituary guard, Dr. Bob parse, question-box auto-close, Europe under, fetch_pages WHOLE).
  Two real bugs, both in the goalie build, both fixed with tests (364 -> 366 green): (1) the '🥅 In net' card line was
  skipped whenever the write-up already had any 🥅 line - the slumping-goalie write-up starts with 🥅 too; (2) the daily
  pick audit read a goalie we had 'Confirmed in net' who then started as 'we had him out (false injury data)'.
- Checked and fine: the goalie weight stays inside STUDY_CAP / NHL_FAV_CAP and never double-counts; a stale page
  (8h+) is unknown, never 'off the injury report'; the lean memory writes only the engine's own file (tests redirect
  it); the Europe under never takes a side and never posts on game day (PT); the capper 'break' leaves only the total's
  line; the ask-status read and the intl log are wrapped so the hourly run never fails on them.
- Not changed, worth a look: football's 'starter = last game's QB' (n=1) means a QB1 hurt mid-game last week (the
  backup threw more) is no longer a 'key player' for the card alert / early-play block - the -8 own-read penalty still
  reads 3 games (sports_absences.key_players), so the read is right, only the labeling narrowed; the Lock-slot
  replacement lean (sports.lean) doesn't use the lean memory (only viewer leans / night picks do); Daily Faceoff's two
  goalie slots are read in page order (away first) - if the page ever shows one slot, the home goalie would read as the
  away team's (the watch line "N matched" in the log is the tell).
## 10/6 - when to bet our hockey picks: 8 AM or near puck drop? (report only, nothing built)
- The repo has NO book-by-book hockey price history (the paid odds pull was football only); the study used the NHL
  opener vs close 2023-26 (4,152 games), our own hourly snapshots since 10/1 (35 games) and our 11 posted NHL picks.
  Favorites get bet during the day (bet them at 8 AM); dogs drift longer market-wide and on all 6 of our real dog
  plays, while a blind proxy of the engine's sides says the books come toward us 60% of the time over 3 seasons - a
  LEAD, mixed on the current season. tools/nhl_bet_timing_study.py; SPORTS_FINDINGS.md (10/6). NEXT: journal the
  8 AM / close price on every pick and re-run with 300+ hourly NHL games (early November).
## 10/6 - NHL confirmed starting goalies (BUILT - the owner OK'd it; sports_goalies.py)
- Source: Daily Faceoff's public starting-goalies page, fetched every hourly run on GitHub's servers (plain request,
  fail-soft) -> data/sports/nhl_goalies.json (Confirmed / Likely / Unconfirmed + the time seen; stale after 8 hours =
  unknown). ESPN's summary has no probable goalie; the NHL feed names only the winning goalie after the game.
- Re-check of the 10/1 "goalie roles" finding (tools/goalie_roles_study.py, blind, 2018-27): the dog starting its #1
  (most starts in its last 10 this season) vs a favorite not starting its #1: +1.5% vs -4.0% for every dog, better 7 of
  8 seasons, 2023-26 about +10 pts on 439 - a lead. The reverse: noise. BUILT: +2 on the Dog's score when BOTH starters
  are confirmed / likely (the favorite weighed down through it, inside the caps); reverse 0. The hot / slumping goalie
  and goalie-rating weights now read the confirmed / likely starter when known (sports_players.starter_for). The card
  names the starters only when CONFIRMED (🥅 In net: ... — their #1, 8 of their last 10 starts); a goalie confirmed
  after a hockey pick posts shows on the card like an injury alert (no phone ping; the pick never changes).
- WATCH (first live runs): the engine log's "goalies: N games on the page, M matched, K confirmed" line - 0 matched on
  a hockey night means the page changed its layout (parse falls soft: unknown, no weight). The pick journal carries
  goalie_roles on every hockey pick for the live tally; judge the spot at 150+ dogs.

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
- 10/16 the owner SAID NO to: (a) flat 1u Locks - "if the engine has a strong-ass read on a game, we do more units. It's common sense" - the Lock keeps sizing by its own read; (b) dropping fill-in leans (any sport) - "we always need leans ... sometimes those leans are locks", and leans must be WEIGHED by the engine's full read, never just the bigger favorite. Don't re-propose either.
- 10/16 the owner: every sport's Dog sizes by the engine's read (sports.DOG_BIG_FROM), floor 1u (hoops ½u) up to 5u; Locks by their read up to 5u; 5u = the max play (UNIT_MAX, was 10u). Strong read = more units - never re-propose flat sizing.
- 10/16 the owner: leans are ranked by the engine's own WEIGHED read (sports.lean_rank), never the bigger favorite - regular and fill leans alike (Coastal -102 over App State was his example).
- 10/17 the owner (yes to both): 🔍 big-gap college dogs back on the board as 1u plays with their own record (sports.gap_plays), and the Lock can be an underdog (sports.dog_lock). Live big-gap college dogs were 1-6 (Tulane won) when he decided.
- 10/17 college lock hunt (4 Fable studies): favorites -101..-150 - no combination beats the price blind (DEAD); LEADS: Tuesday-read dog gap 5-8 at the first fair price (+17% pooled, ~1 a Saturday), and the Thursday flat-money dog +150..+300 with the engine 2+ over (+34% blind, 2026 2-4) - paper-track.
- 10/17 the owner: yes to A (🔍 plays only when the ratings back the dog) and units on rule A as a WEIGHT, never automatic (sports.weigh_ncaaf_fav_form_spot, +3 pts, lead tag).
- 10/17 the owner: the dog limit is +350 everywhere (Dog, plays, 🔍, early spots - DAILY_DOG_MAX / DOG_DAY_MAX / SPOT_DOG), was +300.
- 10/17 the owner: NFL 0-2 dog +3 on the dog score (a weight); the 'blew somebody out' early spot OFF in the NFL (college keeps it). And: if a Fable audit finds an early play that should be removed, pull it without asking.
- 10/16 still open (from the 10 Fable jobs): Dog only when its own read beats the price too; drop the hockey "best dog under score 6" fallback Dog; MLB early (exam) plays flat 1u instead of Kelly (Brewers 3u rode a read ~9 pts high); college hoops Locks small the first 2 weeks.
- "No forced locks": a Lock of the Day only when the read really beats the price, else "No Lock today" (CLAUDE.md
  still says ALWAYS a Lock until the owner says the words). The Dog stays real-value only; leans fill to 5+ picks.
- Card labels showing the edge size in words ("BIG EDGE - 3 UNITS" / "SMALL EDGE - ½ UNIT").

**Next builds**
- Stars beyond QB/goalie (NFL lead rusher / receiver, NBA top scorers) - verified from box scores only.
- Re-check the NHL elimination-dog finding before April; college hoops dog fix before November.
- Hockey: the engine has no real edge there yet (-2% on 1,851) - hockey dogs leave the Dog of the Day if the replay
  says they lose.

- 10/14 (the owner): the "blew somebody out" early spot (0-6 live, -3u) and the college "engine likes it" early spot are PAUSED (sports_early.SPOTS_OFF). Pulled before kickoff, never graded: Old Dominion +145, UAB +190, Tulane +220, Air Force +130, Rice +136, Tennessee +240, Georgia Tech +295, E Michigan +190. Still live this week: Boston College +215 (bye, 1u), BYU +300 (hammered, ½u), Brewers +144 (MLB exam, 3u). Turning a spot back on = the owner's call.
- 10/15 (the owner): both early spots back ON (blowout + college engine) - "no risk no reward". The college read now counts at most 5 points in the early spots (NCAAF_GAP_MAX, the middle ground). The 8 plays pulled 10/14 stay pulled.
