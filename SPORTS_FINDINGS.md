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

## 10/25 sweep - THE PRE-SUNDAY BUG SWEEP (the owner: "find all the bugs, run a full sweep, a full audit on everything ... good picks, good sizing, good dogs"): the whole pick path read against CLAUDE.md, four fixes BUILT (tests test_sweep_1025_*), the rest judged and left
- Already fixed earlier today (not redone): own_beats needs the OWN read outside hockey / the NBA favorite read (the Bengals -148 value play rode the weighed read with its own read 1.2% under the price).
- FIXED: (1) **early plays had no units written on them** - the unit record re-read sports_early.SPOTS every time, so a spot's size changing later (bye 1u -> ½u, say) would have re-sized every graded early row and the 💰 record / 📊 day results with it; the board's picks freeze theirs (units_for), the early plays didn't. post() and grade() now stamp `units` on the play, units() reads the stamp first (sports_early.stamp_units). (2) **a one-game day could title a -119..-101 favorite the Lock of the Day** - the 10/23 plan's band held on the board's Lock pool and the backup, not on the solo title (make_board); it stays the game's pick with units, never a Lock, and rule_check pulls any Lock in the band from 10/23 on (never the owner's own post). (3) **the Monday / Thursday night UNIT pick skipped own_beats** - a favorite whose weighed read (w_p) beat the price while its own read sat under went up with units (the Bengals hole, on the night path); it's a value play, so the owner's 10/18 rule holds - OWN read over the price or it's the game's lean (night_pick). (4) **the sizing check still allowed a Lock / night / one-game pick up to 10u** - the owner's max play is 5u since 10/16, the Lock 3u since 10/23; and the bankroll box said a unit is "roughly 1% of the bankroll" - the 10/22 rule is $1,000 flat, up $500 per full $50,000 (sports_dashboard.units_box).
- LOOKED AT, LEFT AS IS (why): own_agrees / real_value take a favorite's weighed read (w_p) in every sport, so a Lock can post with its own read under the price at 2u - that IS the 10/23 plan's "2u when only the weighed read does" (the owner's "yes"); a favorite no study weight touched has no w_p and its Lock is 1u even with a big own edge - the plan's "read alone" bucket (-0.3% / -4.2%), the replay was cut that way, so a change needs a replay first; money_against ignores football by design (tested, the summer open) and sports_sharps says the engine beats the move in the NFL - so the 49ers' price running from -205 (Tuesday) to -142 doesn't block the Lock; a hockey Dog at ½u thin (the Canucks 1-10 at +150, own read ~1.5 points over the price, the dog score carried by the back-to-back / both-lost / puck-luck items) is by the rules - ½u thin, never forced - but the 1-10 team's Elo is last season's regressed, judge the own-read-over hockey Dog at 30 (4-8 live).
- Tomorrow's board (Sunday 10/25, built here from the cached slate - no ESPN in the sandbox): Lock 49ers -142 ½u (thin, own read under 3 points over), no Lock issue by the rules; Dog Canucks +150 ½u thin (above); Browns -130 ½u value play (own read over); the Bengals -148 value play is gone (own_beats) - the Bengals +150 bye early play still rides at its price (the Ravens opened -179, now +124 - the same side, allowed); Seahawks -142 lean (no units). Early plays playing Sunday: Bengals +150 bye 1u, Dolphins +170 bye 1u, Saints-Steelers Paris under 43.5 ½u.

## 10/24 (night) - THE FULL UNIT-PLAY AUDIT (the owner, after Saturday went 5-11 with Illinois +310 the only reason it paid: "Run Fable and assess everything. And don't even ask me, just fix everything accordingly so we can stay a profitable engine and profit the most"): every unit-play type since the unit system began, live + history, judged on one bar - SIX CHANGES BUILT, the money-makers kept
- **THE LIVE RECORD (10/2-10/24, results/audit_1024.md - every unit play from picks.json + early.json through the dashboard's own ledger, the close record, the live log):** 38-41, +23.1u on 67u (+35%), beat the close 13 of 48 (same 24). By type: Dog 7-9 +5.9u (+30%); owner posts 2-0 +4.7u; early EXAM BAND 4-0 +10.8u; value plays 8-3 +3.4u; early bye 1-1 +1.1u; hammered 1-1 +1.0u; Locks 4-4 -1.1u (the ½u Locks 4-4 -0.6u); backup Locks 1-1 +1.6u (UNLV 2.5u); 🔍 gap 3-6 -0.8u (-8%); early blowout 2-7 -2.0u (-44%); early engine 3-6 -1.2u (-27%); dog_plays 0-2 -1.0u; Europe under 1-1. By sport: college 22-26 +17.5u, MLB 3-1 +7.1u, NFL 4-5 +0.1u, NHL 9-9 -1.6u. By price: +250..+350 3-0 +10.8u, +150..+250 7-10 +7.8u, +100..+150 21-26 +3.2u, favorites 7-5 +1.3u. Saturday college 15-24 +10.4u (10/3 3-0 +3.2u, 10/10 1-6 -4.2u, 10/17 7-6 +9.8u, 10/24 4-11 +1.5u) vs weekdays 21-15 +13.3u. Thin edge (own read under 3% over) vs real, board picks: thin 16-18 -4.4u, real 11-6 +18.6u (the 10/23 ½u fix stands). Live plus money 16-17 (+7% flat; NFL 9-4, MLB 0-5 paused, tennis 4-6).
- **WHAT MADE 10/17 (+9.8u on college, the day he wants again) and what made 10/24 bleed:** 10/17 = the Dog (Boston College +195, 2u, +3.9u), three early plays that each had a proven mechanism (BC bye 1u, Kentucky exam band 1u, BYU hammered ½u: +5.6u) and two ½u plays - 10/17's four 🔍 gap plays went 1-3 and the ½u plays 2-2. 10/24 = fourteen college dogs on one card from FOUR rules reading the SAME college own-read gap (the engine early spot x6 2-4, the 🔍 gap plays x4 1-3, dog_plays x2 0-2, the blowout spot x1 0-1) - the market beat that read, as the 10/15-16 recalibration said it would (fitted shrink 0.000 on 6,009 games); Illinois +310 (the Dog, 2u, +6.2u) and Arkansas St carried it. The lesson is not "fewer dogs on Saturday" (the 10/17 sweep: Saturday college dogs are not correlated; the replay's Saturdays with 5+ college dogs +9.2%) - it is ONE bet on the college read, at the band history pays, and no bet on the pieces history says lose.
- **THE HISTORY, same bar for every rule (the 10/23 dog-reason replay rows - 1,375 board days 2023-01..2026-10-21, closing prices, params re-tuned each July, every ml dog +100..+350 candidate dumped with its gate: scratchpad cutoff_study/r_*.jsonl; the 10/9 board replay 2023-26; the 10/17 college gap study):**
  - The Dog of the Day (today's rules, 299 own-over Dogs): 139-160, +5.8% flat, +12.9% at the plan's 2u (3 of 5 seasons; blind +17.7%). Hockey own-over 88-81 +19.9% (3 of 4, blind +30.5%) - the engine's best cell; +100..+150 116-111 +12.0% (4 of 5); +150..+250 23-44 -7.2% (1 of 5); +200..+350 2-13 (-57%, both halves); college 8-16 -22.8% (24; 2026 -6u); college Saturday 5-12 -28% (17); college hoops 40-57 -9.2% (1 of 4). Thin own edge (under 3%) 42-44 +13.8% vs 3%+ 97-116 +2.6% (the 10/9 finding again - edge size says nothing).
  - dog_plays (every other dog that clears the full Dog check, as built 10/24): 69-118, -9.7% flat, 2 of 5 seasons up (blind -3.8%); +100..+150 53-83 -14.9% (1 of 5); college hoops 36-64 -20.6% (0 of 3); hockey 3-7; college football 26-36 +9.8% (blind +11.6%, 2026 -6u). 2.3 a day, 3.2 a Saturday, 11 at most. The ONE best runner-up a day by dog score: 33-48 -1.6% (flat, 3 of 5); without college hoops 19-24 +20.6% on 43 (blind 14-14 +30.2%, 3 of 5); at +150 or longer 9-11 +52.9% (20 - thin).
  - 🔍 gap plays (the 10/17 college gap study, 2,944 college dogs +100..+300 walk-forward): own read 10-15 points over the market LOSES everywhere - train -8.8% (169), blind -13.0% (132), 2026 -16.8% (30) at the close; -11.7 / -17.4 / -23.1% at the first fair price; 15+ runs +7.0% train (377) / -0.5% blind (280) / +7.2% 2026 (53) at the close, and every robust cell that passed (favorite not hot, dog not cold, rating-backed) sat on the 15+ band. The 10/24 daily run's cousin (Elo has the dog better AND +150 or longer): +7.1% on 282, 5 of 7, holdout +9.7%, 2026 -28% on 37. Live: the 15+ plays 2-5, the 10-15 plays 1-1.
  - Locks (616 favorites, today's rules): 378-238 61.4% +6.1%, 5 of 5 seasons; the full test 369-231 +6.2%; the plan's sizing on them +58.3u (blind +7.9%, 3 of 3), the 3u tier 141-88 +6.2% (5 of 5). BACKUP Locks (lock_ok false - the own read 56%+ beating the price, the blended win % under 56%): 16 in four seasons, 9-7, flat (+3.6%); at -119..-101 5-2, at -150..-120 4-5; under the plan's sizing -13.7%, at ½u -19.6% - a sample that says nothing, so the owner's written rule (½u) decides. Full-test Locks at -119..-101 12-10 +3.4% here vs 46% in the 10/23 best-mix rows - the skip stays (the owner's plan).
  - Early spots: the exam band 4-0 live is the walk-forward band test (the honest version of the college read, 10/17); bye held every test (+16% college / +29% NFL fair, live 1-1); hammered is the honest move model (live 1-1); the ENGINE spot = the college own read 4+ over the market + "the line moved away 2+" - the read holds nothing the market lacks (10/15-16: the 5-10 point gap bucket -7.1% train / +5.3% blind / -24% 2026 at the close, -10.1% / +0.1% / -55.7% at the first fair price) and the money-left half loses at the close in every sport (10/7; college's first look a coin flip, +5% +/- 8); live 3-6. The BLOWOUT spot's +4.4% on 610 (10/1) was the spot with the engine liking it; 104 of 250 FBS blowout wins this season were FCS tune-ups (10/16 - "FBS-only before it is ever unpaused", never done); live 2-7, the max-value spots together ~+1..4% the last 3 seasons, 2026 -18% on 31.
- **BUILT (the owner's 10/24 OK to fix without asking; tests test_audit_1024_*):** (1) sports.GAP_MIN 0.10 -> 0.15 - the 🔍 play needs a 15+ point rating-backed gap; 1u and the 50-play judgment stay. (2) dog_plays = the ONE best runner-up a day by dog score, never college hoops (sports.DOG_PLAY_MAX / DOG_PLAY_LEAGUES; post_board counts the day's). (3) the college "engine" early spot PAUSED (sports_early.SPOTS_OFF = {"engine"}) - its game-day twin the 🔍 play is the one bet on that read. (4) the blowout spot counts a college blowout only over an FBS team (sports_early.BLOWOUT_FBS_ONLY / blowout_counts via sports_players.fbs_set; no FBS set on file = counts). (5) the backup Lock is ½u (sports.BACKUP_HALF_FROM 10/25; the leg carries backup_lock) and skips -119..-101 like every Lock - the code had sized it like a full Lock (UNLV 10/3 2.5u). (6) the own-read Dog rule holds on every path (sports.dog_own_ok - the board's Dog pool, the one-game-day Dog, dog_plays): a dog carried by a PROVEN angle walked past it, since good() passes proven(c) without the dog gate. (7) BUG found on the way: post_board's per-day cap counted a 🔍 / dog_play by kind "dogplay" / "gap" while the saved pick carries kind "play" with a tag - the count was always 0, so a cap on either never bit (sports.posted_kind; the one-a-day dog_play would have posted one more every hourly run).
- **CHECKED AND KEPT (written down so they stop reading as mismatches):** the hockey Dog at 2u with its own read over the price (the owner lifted the flat 1u on 10/16; the replay's best cell) - the DOG_UNITS_BY nhl 1.0 is the pre-plan floor, its comment now says so; the 🏀 NBA opening-line early play taking a favorite in -150..+300 (the owner OK'd the band 10/23; favorites-only +19.2% blind on 257, 3 of 3 seasons, dogs-only +5.7%) - the "dogs only" early rule is the six football spots'. The Dog of the Day at 2u up to +350 (the owner's wish today - "a Dog of the Day at +310 and smack for 6 units"): KEPT as the 10/23 plan has it, with a WATCH - own-over Dogs +200..+350 went 2-13 at the close in the replay (both halves) while live they are 2-0 (BC +195, Illinois +310); judge at 30 live, the 2u stays till then (the 10/23 own2_short variant - 2u to +150, 1u longer - made +58.6u vs +61.8u, so the money says nothing yet). College Dogs (replay 8-16, live 2-1 +9.1u) and the exam band, bye, hammered, Europe under, nba_open, the S6 Lock sizing + thin ½u, value plays ½u favorites-only, live plus money: unchanged.
- **WHAT 10/24 LOOKS LIKE UNDER THE NEW RULES (the posted picks are untouched):** the six engine-spot plays don't post (2-4, -0.8u), Ole Miss 🔍 at a 14.6 gap doesn't (-1u), N Illinois dog_play doesn't (-½u; Mississippi St, the best runner-up, still does) - the day goes from 5-11 +1.9u to 4-7 +4.2u on 7.5u fewer bet. 10/17 is unchanged (every 🔍 play that day had an 18+ gap; no engine-spot play, no dog_play) - the +9.8u stays. The Saturday card drops from ~14 college dogs to ~7. EXPECTED EFFECT from the replay: the gap band change turns a -9..-17% band into the only one that paid (+7% train / flat blind); dog_plays from -9.7% to flat / +20% without hoops; the engine spot's -27% live and the money-left fade off the card; the backup Lock ½u costs nothing (flat on 16).
- NOT CHANGED, OWNER'S CALLS IF HE WANTS THEM: a 1u Dog past +200 (own2_short); pausing the blowout spot outright (live 2-7 on 9 - too few against +4.4% on 610); the college hoops Dog at ½u (-9.2% on 97 in the replay, his 10/10 lead).

## 10/25 - DAILY RUN: 10 NEW STUDIES (no Fable): nothing BUILT, two LEADs paper-tracked, eight DEAD (results/studies/daily_1025/)
- Football (close ML 2018-26, train 2018-24 / holdout 2025 / now 2026, ~150 cells, ~7 chance hits):
  - LEAD - the 10/24 gap-dog question: college dogs our Elo has 15+ over the no-vig close split by SITE: HOME +9.2% on 382 (train +2.1% 4/7, 2023+ +8.7%, holdout +40.5% on 47, 2026 +16.5% on 63; base home dogs +4.2%) vs ROAD -14.1% on 207 (train -13.5%, but 2023+ +9.2% on 95, 2026 -44.8% on 29; base road dogs -8.3%). The road cut isn't clean (2023-25 up), so the 🔍 play keeps both sites for now - WATCH: if road 🔍 plays keep losing live, they come off. Also: gap 15+ AND the line moved 2+ away from the dog, bet at the close: +19.4% on 160, up 4 of 4 seasons - open prices only from 2023, ATS -6.3%, NFL fails; paper only.
  - DEAD: college road favorites off a home win (the opp-off-a-loss part = rule A, built); the week after Army/Navy/Air Force; college short week / mini-bye rest; NFL Sunday kickoff window (1 PM home fav -17% on 170 but flips by price band - WATCH).
- NHL / NBA (close ML, train 2016/18-24, holdout 2025-26, ~45 cells):
  - DEAD: what splits the engine-passed hockey dogs (pool +9.1% / +15.7% - no clean split; goalie .905+ season sv% WATCH); NHL very bad teams (<.350) as dogs (-5.9% on 1,236); NHL favorite on night 2 of a road back-to-back (-1.9%; -126..-150 -12.2% on 112 is post-hoc - WATCH); NBA game 2 of a home-and-home.
  - LEAD - NBA: back the HOME team vs a team on its first road game after a 5+ game homestand: +11.4% on 195 (z 2.0, 5 of 7), holdout +13.5% on 26; the team off the homestand failed ATS 8 of 8 seasons. Tracker only; judge on 2026-27.
  - CHECK: the 10/23 board replay's NHL Dogs are all road teams in 2023-24 and all home in 2025-26 (none in 2024-25) - looks like a replay-data or home-edge artifact; look before trusting replay NHL Dog numbers.

## 10/24 - DAILY RUN: 10 NEW STUDIES (no Fable): nothing BUILT, three LEADs paper-tracked, seven DEAD (results/studies/daily_1024/)
- Football (dogs +100..+350 at the close 2018-26, train 2018-24 / holdout 2025 / now 2026, ~100 cells, ~5 chance |z|>2):
  - LEAD - NFL dog whose defense is improving: 5+ games in, allowed 7+ fewer points a game over its last 3 than earlier this season -> ML +10.3% on 210 (train +8.6%, 5 of 7; holdout +22.9% on 26; early fair price +14.1% on 154; ATS 58.1%); the yards version (50+ fewer, last 3) +23% on 141. Window-sensitive (last-2 / last-4 flat, college last-3 flat) - paper only.
  - DEAD: big favorite off a close win / loss (NFL -2.7%, college holdout -16%); the dog out-rushing the favorite (-7% to +4.5%); first time a dog / a favorite this season (flips); college neutral-site regular-season dogs (-5.7% on 58).
  - Can't run yet: the total's move (odds history has no totals), conference-title stakes (no conference field).
- NHL / NBA (close prices, train 2016/18-24, holdout 2025-26, ~50 cells):
  - LEAD - NHL "lucky winner" fade: a team that won its last game while outshot by 15+ -> -16.8% on 591 (1 of 7 up, z -2.7), holdout -12.3% on 80; the favorite facing it (that allowed <40 shots) +17.2% on 110 / +22.5% on 21. Not separated from the built PDO weight - paper only.
  - LEAD - NBA favorite whose last 3 wins were all close (5 or less / OT) as a fade: ATS -15.3% on 192, holdout -47.1% on 36; the dog ATS +7.4% (6 of 7). One-season holdout, no dose-response - a small negative weight on the favorite once 2026-27 confirms it.
  - DEAD: NHL new goalie (team's first start, game 6+: -3.6% / -17.5%); NHL last 3 wins all one-goal (flips); NBA after a 30+ point loss (mixed signs).

## 10/24 - 🐕 THE OWNER'S DOG EYE (the owner: "I have a knack for finding these underdogs where the line just seems way off ... the engine needs to be able to do that too"): STUDIED - every eye we can build from our data is PRICED; nothing wired as a weight, one tracker LEAD
- WHAT WAS TESTED (results/studies/dog_eye_1024/ - build_nba.py / detect_nba.py / detect_nba_open.py / build_fb.py / detect_fb.py, the .out files): NBA dogs +100..+350 at the close 2018-26 (7,143; train 2018-24 flat 1u, HOLDOUT 2025-26 = 869, 'now' 2026-27 = 21), the same eyes at the OPEN 2023-26 (train 2023-24 / holdout 2025), NFL and college dogs 2018-26 (train 2018-24 / holdout 2025 / now 2026). Nothing from after tip-off except the box's who-played (flagged [game-day]). 49 NBA close cells + 18 open + 48 football = 115 cells, ~6 chance hits expected at 5%; survival = up in train AND the holdout, z over 1.
- NBA AT THE CLOSE, his eyes one by one (train ROI / seasons up / holdout ROI): the whole band -3.7% / 0 of 7 / -6.7%. (1) ROSTER TALENT vs the price (last season's plus-minus values on the men who played the last 10 games - the roster so far, no tonight look-ahead; a logistic walk-forward): read 5+ over -3.9% / 1 of 6 / -8.1%; 10+ over -2.8% / 2 of 6 / -10.5%; the dog's roster at least the favorite's -6.0% / 2 of 6 / -11.7%; tonight's men (look-ahead) -2.0% / -17.6%. (2) STARS (honors before, the rotation): 1+ star points more -3.4% / 1 of 7 / -7.4%; 2+ -5.7% / -10.7%. (3) JUST BEAT A GOOD TEAM: won last vs a .600+ team -4.8% / 3 of 7 / +7.4% (92); won last vs an Elo 1560+ team -9.4% / 1 of 7 / -5.3%; beat it by 10+ -9.7%; won last AS A DOG -1.2% / 3 of 7 / +6.1%; upset last game and STILL +180 or longer +7.2% on 538 / 4 of 7 / +1.1% on 73 (z 1.0 - the one cell up both halves, 1 of 49 = chance-grade). (4) LAST SEASON'S RECORD in games 1-15: the dog 10+ pts better last year -2.1% / 2 of 7 / -22.5%; at least as good -5.9% / -11.3%; the favorite 25+ better last year (the brand price) -0.5% / +0.6%; favorite .600+ last year under .400 now -3.3% on 46 / +50% on 7 (n). (5) THE ELO GAP: 5+ over -6.2% / 1 of 7 / 0.0%; 10+ -6.3% / 3 of 7 / -2.8% (the 10/21 #5 again). (6) REST: rested dog vs a b2b favorite -0.9% / 3 of 7 / +5.7% (built +3, holds its shape); 3+ days vs a b2b -1.9% / -20.4%. (7) A COMBINED TALENT-ADJUSTED FAIR LINE (ridge logistic walk-forward: Elo, talent gap, star gap, home, rest, this season's record): 3+ over -2.8% / 1 of 6 / -6.1%; 5+ -2.3% / 2 of 6 / -2.8%; 8+ -6.1% / 0 of 6 / -1.0%. (8) THE OWNER'S EYE as a point score (talent / stars / beat a good team / rest / last year / Elo, +1 each): 2+ -3.6% / 1 of 6 / -0.9%; 3+ -8.5% / 1 of 6 / +0.6%; 0 -3.7% / -10.5% - the score does not sort the dogs. (9) [game-day] THE FAVORITE MISSING 2+ USUAL STARTERS (started 60%+ of its last 10, not in the box): -0.1% / 3 of 7 / +7.2% (77); 2+ of its top-8 by minutes -1.2% / 4 of 7 / +10.0% (172); missing 2+ AND the line moved under 2 points to the dog (2023+) -18.8% on 73 / +3.9% on 42 - the "they didn't move it enough" eye LOSES in train; moved 2+ -1.1% / +14.4% (34). The Hawks angle - a -100..-200 favorite vs a dog missing 2+ starters -5.8% / 2 of 7 / +1.6%; and the favorite whole -3.4% / +3.0% - the books move for the missing men (the 10/22 'vs a team missing its top-2 man' fade says the same). (10) THE MONEY RAN AWAY (the Mavs case, 2023+): dogs that drifted out 3+ points -8.4% / 0 of 2 / -13.1% (292); with eye score 2+ -5.1% / -4.5%; with the talent read 5+ over -6.0% / -2.8% - no eye rescues a drifted dog; the money came TO the dog 3+ -0.9% / +0.9%.
- NBA AT THE OPEN (bet at the opening price, 2023-24 train / 2025 holdout): the band -8.9% / 0 of 2 / -2.6%; Elo 5+ over the open -8.0% / +5.2%; talent 5+ over -8.2% / +0.1%; dog 1+ star points more +8.1% on 416 (2 of 2) / -1.9% on 182; 4+ more +6.4% on 111 / +3.0% on 27 (the 10/23 WATCH, still thin); upset last game, opened +180+ -24.0% / +21.9% (flips); rested vs a b2b +1.2% / +12.2% (1 of 2); eye score 2+ -1.9% / +9.7% (1 of 2). Nothing holds both halves on a real sample - the 🏀 opening-line model (37 inputs, +13.7% blind) already carries what the open misses.
- FOOTBALL (48 cells): NFL dogs - Elo 10+ over -13.6% / 1 of 7 / +32.3% (51 - flips); upset last game -6.6% / -22.5%; still +180 -13.2% / -34.1%; beat a .650+ team -2.3% / -23.3%; the favorite .400- and the dog .500+ +1.5% on 90 / 4 of 7 / +2.7% on 11 / 2026 +63% on 11 (n); won by 14+ and the favorite off a loss +8.4% on 74 / 5 of 7 / +2.9% on 9 (n - two thin cells, ~2.4 chance hits in the batch); eye score 2+ -6.5% / +11.4%. COLLEGE dogs - upset last game -20.2% / 1 of 7 (the built hangover fade, confirmed); beat an Elo 1600+ team last game -30.1% / 0 of 7 / -23.2% (a FADE in train, 0 of 7 - the 10/16 'college dog off a 1-3 pt win' / 10/17 upset-hangover line again, not a new weight); Elo says the dog is better AND +150 or longer +7.1% on 282 / 5 of 7 / +9.7% on 40 / 2026 -28.2% on 37 - the built 🔍 gap play's cousin, red this season; dog 15+ better LAST season early +30.7% on 104 / 6 of 7 / -18.0% on 15 / 2026 -57% on 22 (flips); off a bye vs a team that played +14.3% / 4 of 7 / -54.6% (the paused bye spot's shape); favorite .400- +24.2% holdout on 46 after -0.7% train.
- WHAT IT MEANS, said plainly: with the data we hold - box scores, honors, schedules, records, Elo, the open and the close - the owner's dog eye does not separate from the price at the close. His 10/23 calls (Mavs +210, Rockets +160, Bulls +105, 76ers +155) all WON, and the study says a dog like each of them wins about what its price says over 7,000 of them. What his eye may carry that our files don't: who's REALLY out and how the new men fit (the Pacers without Haliburton / Turner were priced on their brand; the roster prior reads last season's plus-minus, which can't see a team that changed), a coach's rotation plan, how a team looked last night (the eye test). Data that could test that: a player-level source with projected minutes / depth charts, pre-game injury reports BY TIME (ours start 10/2026), per-possession and lineup data (threes / steals / blocks / turnovers land with the box backfill - the player-rating study reopens then).
- BUILT: nothing weighs the read. LEAD (tracker only): "NBA dog off an upset win, still +180 or longer" - sports._nba_dog_facts.last_upset (the last game won at a plus price, from the schedule), sports.NBA_UPSET_DOG_MIN, the sports_leads tag; judge it on 2026-27's live record. Test: test_dog_eye_study_wires_no_weight_and_tracks_the_upset_dog_lead (the dog score does not move on it). DEAD (logged): roster talent vs the price (third time), stars vs the price (second), beat a good team, last season's record vs the price, Elo gap by size (again), the combined fair line, the eye score, the favorite missing 2+ starters with a small move, the drifted dog with any eye; NFL / college versions of each.

## 10/23 (later) - THE DOG'S NAMED-REASON RULE vs THE 10-CENT WOBBLE (the owner, on Wyoming +180: "that doesn't make sense ... fix the cutoff"): the rule STAYS, a buffer BUILT
- What happened: Wyoming's only named reason was "sharp money moving this way" (on at a 0.08 no-vig logit move from the open). +190 open -> +170 had it (the 10/22 preview's 2u Dog); +170 -> +180 at 6:39 AM PT dropped it to ~0.05 and good() (no reason = no play) kept it off the 8 AM Dog. The owner posted it 2u (data/sports/owner_posts.json - his OK'd calls, built like any board pick).
- Replay 2023-01-01..2026-10-21 (tools/value_play_replay, 1,375 board days at 8:35 AM PT, results/studies/dog_reason_1023/): A the current rule 300 Dogs 139-161, flat +16.4u (+5.5%), 10/23-plan units +45.9u; B gated dogs need no reason 314, flat -0.1u, +27.3u (its 22 swapped-in dogs went 8-14 while the 22 they replaced went 16-6); C the reason at 0.04 +43.4u; D B but 1+ over the gate +35.1u. Gated dogs with NO named reason: 84-132, -7.9% (blind -10.3% on 38) - the reason rule filters losers. KEEP A.
- BUILT: a buffer, not a looser bar - the sharp reason turns on at 0.08 and, once on for a game's side, stays on down to 0.04 (sports.SHARP_ON / SHARP_KEEP / sharp_fired, data/sports/sharp_fired.json). The replay can't test it (open + close only); the 0.04-0.08 band ran flat there, so it costs ~nothing and kills the knife-edge.
- LEAD (not clean): gated dogs with a 0.08+ move went +24.7% on 85 - but measured open to CLOSE (look-ahead), fails check 1.

## 10/23 - DAILY RUN: 10 NEW STUDIES (no Fable): nothing BUILT, two LEADs paper-tracked, eight DEAD (results/studies/daily_1023/)
- Football (paid odds history; train 2020-24, holdout 2025; ~170 cells, ~8 chance hits expected). The spread history holds ONE look per game (Tuesday). Loader note: ~30 college events swap home/away between moneyline snapshots - any move study must re-key by team name (lib.py).
  - LEAD - the late reversal: the spread closes 0.5+ shorter for side A than Tuesday's median, while the median no-vig moneyline moved 1+ point toward B (first fair look to the last before kickoff; it swings back to A by the close 95% of the time). Bet A's spread at the close: college +41% on 54 (6/6 seasons), NFL +31% on 25; holdout college +12.5% on 17, 2026 +91% on 8. Neighbor cells flat or red. Fails on sample (60-80 bets) and needs a last-hour price, which the 8 AM board / early plays can't take - paper-track only, no weight.
  - DEAD: move breadth (90%+ of books moving vs 60% or fewer; NFL +1.9%, holdout -33%); quiet week dog (-13% to +2%); the game after being a big dog (college 14+, NFL 10+; flips); a night game, then a noon kickoff vs a rested opponent (college -8% ATS, NFL the other way).
- NHL / NBA (game files' close / open; odds_history is football only; train 2018-24, holdout 2025-26; ~58 cells, ~3 chance hits expected):
  - WATCH - NHL rested team vs a Saturday-to-Sunday back-to-back: +11.1% on 358 (6/7 seasons), holdout -4.8% on 59. The tired team itself is no worse than on any back-to-back (the weight we have covers it). Not built.
  - LEAD (spreads only) - NBA late season (opponent 80%+ through its schedule at under .400, our side .400+): our side's spread +7.7% on 518 (5/7), holdout +2.2% on 107 (about break-even after juice); the tanking dog ATS -14.1% on 623. Moneyline nothing. Leans are who-wins and value plays are moneyline only, so nothing to wire; judge it on 2026-27's last 20% (March).
  - DEAD: NHL late season, out-of-race / clinched (-8.1%, holdout -24%); NHL hot starting goalie, .935+ over 5 starts (dog -5.0% on 499, flips); NBA game after overtime (favorites -22.6% on 133, flips ATS).

## 10/23 - NBA BENCHES (the owner: "a strong bench means a lot, especially with injuries"): DEAD as a weight - the market prices it
11,078 sides 2021-25, bench = men 6-10 (and 6-12) by minutes over the last 15 games (10 / 25 checked), train 2021-22 / blind 2023-25, close + open; 143 cells, 5 positive both halves (~7 by chance), none survived a window change.
- Strong bench alone: dogs -17.8% / -3.5%, favorites -9.9% / -2.4%; the bench weight after the price is zero or negative every season (2023 z -3.4) - if anything the books over-rate deep benches.
- A top-5 man out + strong bench: -6.3% / +1.3% (no value); + weak bench: -2.1% / -4.1% (no fade). 2+ out + strong bench flips with the window. Fatigue x depth: b2b -20.4% / -2.6%, 3-in-4 -21.2% / +1.1%.
- Bench terms in the blended read: worse log loss 2 of 3 seasons; in the opening-line model ~0 weight, better in 1 of 3. Wire nothing new.
- How benches already count (validated 10/20): a missing man's minutes go to the next men up at THEIR value in the roster prior (sports_nba_roster.lineup); bench strength is a card fact at +/-3.

## 10/23 - NBA HOT STREAKS (the owner: "bet the hot streak, especially dogs on a hot streak"): DEAD - the books price it
9,518 games 2018-25 at the close (train 2018-22 / blind 2023-25), opens 2023-25; 130 cells, flat 1u. Scripts: scratchpad streaks1023 (study.out, extra.out).
- Win streaks 2+/3+/4+/5+ win what the price says (3+: 60.3% vs 60.2% blind, -4%); same for ATS streaks, last-5/10 records and margins, hot-vs-cold, blowout streaks, road streaks.
- Hot DOGS are the worst: 3+ streak -9.8% / -5.3%; won 8 of 10 -24.5% / -13.5%; hot road dog on the road -17% / -20%.
- At the OPEN a hot dog is priced HIGHER than at the close (it lengthens 3.3 pts): hot dogs at the open -14.5% (2024 -21%) - betting them early is the worst timing.
- The NBA opening-line model already carries form; adding streak features made it worse walk-forward (+21.0% -> +17.1% / +13.2% / +7.4%). No streak weight, no separate rule.
- WATCHED, unproven: home dog on a 3+ HOME win streak, 349 games, 42.7% vs 37.4%, +13.4% at the close, blind 2023-25 +24% on 130 (3/3) - z 2.1 with 130 cells is noise-grade. Re-check end of 2026-27.
## 10/23 (later) - 🌟 STAR POWER (the owner, on the 76ers +155 at the Knicks, won 106-100: "look at the squad - Jaylen Brown, Maxey, Edgecombe, Embiid, LeBron James ... anyone can look at that and say that line don't make no sense ... the engine needs to know that too"): STUDIED - the close prices the stars; a 🌟 card FACT line built, NO weight
- THE DATA (new, data/sports/nba_stars.json + sports_nba_stars.py): every player's honors by season - All-Star selections (injury replacements too), All-NBA 1st / 2nd / 3rd, MVP top-5, All-Rookie first team, the top-10 picks by draft - 2014-2025 COMPILED FROM CLAUDE'S OWN KNOWLEDGE (tools/nba_stars_compiled.py, every season marked source "claude-knowledge"; 143 of 146 names match our box scores) because the sandbox can't reach Wikipedia / Basketball-Reference / ESPN. The 2025-26 honors (end year 2026) are NOT in the file - never a fact we can't see. tools/nba_stars_fetch.py + nba_stars.yml read Basketball-Reference's public pages on GitHub's servers (plain honest requests, 4 s apart) and REPLACE every season they read whole (source "bbref"); NEEDS A PUSH + DISPATCH (`gh api -X POST repos/D503therapper/autonomous-crypto-engine/actions/workflows/nba_stars.yml/dispatches -f ref=main`). STAR VALUE for a season from the seasons BEFORE it only: All-NBA 1st 4 / 2nd-3rd 3 / All-Star 2 (+1 top-5 MVP), the best of the last three seasons at 1 / 0.7 / 0.5; a top-5 pick 1 (top-10 0.5) in his first three seasons; All-Rookie first team 1.5. A "star" = 2+. Team = the men on the floor.
- THE TEST (results/studies/nba_stars_1023/stars.py / stars.out; box scores say who played: 2021-22 .. 2025-26, train 2021-23 / blind 2023-26, 12,314 sides, flat 1u, no fit anywhere). DOGS +100..+350 AT THE CLOSE (band -4.6% train / -5.3% blind): star gap 0+ -11.6% / -4.9%; gap 2+ (210 / 219) -7.8% / -1.0% (2023 +8 / 2024 -23 / 2025 +20); gap 4+ (39 / 55) -0.9% / +7.5% (+44 / -23 / -17); as many or more stars by count -6.4% / -9.3%; the dog with 3+ stars on the floor -40.9% / -55.0% (15 / 10); the whole roster's gap 2+ +2.3% / -1.6%; games 1-20 gap 2+ +18.6% train (44) -> -10.8% blind (46); by price band nothing holds both halves. A dog that ADDED 2+ stars in the summer: n 0 in five seasons (the 76ers' summer is that rare); added 1+ -8.0% / -18.3%. FAVORITES -150..-100 with the star edge (gap 4+): -12.2% train / +9.3% blind (89 / 84) - flipped; the dog with more stars than the favorite: the favorite -1.6% / -15.7%. The whole market, win % minus the price by star-gap bucket: within ±2 points in every bucket with 500+ sides, both halves. THE CLOSE PRICES THE STARS.
- AT THE OPEN (2023-25): "stars on the floor tonight" gap 2+ at the open +18.5% on 266, gap 4+ +36.7% on 74, up all three seasons - and it's a LEAK: who's on the floor is game-day news the open can't know (the favorite's star SITTING is what won). The honest read - every man on the roster so far, out or not: gap 0+ +1.0% (899), gap 2+ +3.6% on 361 (2023 +18 / 2024 -4 / 2025 -2, 1 of 3), gap 4+ +11.1% on 108 (+34 / +16 / -22); the same sides at the close -4.8%; +250..+350 gap 2+ +48.6% on 35 (n). NOT a lead by the five-check rule (one season carries it, the sample's thin); WATCH the roster gap 4+ at the open with the 🏀 opening-line record.
- HIS GAMES (honors through 2025 only - the 2026 ones wait on the fetch): 76ers +145 at the Knicks: star gap +1.9 the 76ers' way (LeBron James 2.1 - All-NBA 2025 x 0.7 - + Embiid / Maxey / Brown / George 1.0 each at 2024's All-Star x 0.5, Edgecombe 1.0 the #3 pick, 7.1 in all vs Brunson 2.1 + Towns 2.1 = 4.2) - the read pointed his way and they won; the Spurs -102 vs the Thunder: -1.7 (SGA 3.5, Jalen Williams 2.1; the Spurs' Wembanyama 1.4 / Castle 1.5 under the star line) - lost 104-116; the Mavericks +330 at Houston: 0.0 vs 0.0 (Durant 1.4 at 2025's All-Star x 0.7; Kyrie 1.4, Flagg 1.0, Davis out) - lost 110-128. One of three, and the rule's blind record says the one was the price, not the read.
- THE OWNER'S THREE CUTS (10/23 later: "the All-Stars run the offense and decide who wins ... watch when they're cold or hot"; stars.out, the same set). (1) STAR COUNT MATCHUPS: a 0-star dog vs a 2+-star favorite wins 32.6% blind, the price said 32.4% (+0.4% ROI; train +1.2%) - PRICED; the star-heavy favorite in those games -7.6% / -3.2% (any price), -25.9% train / +17.8% blind at -150..-100 (flipped); 0-star teams at every price win 41.4% vs 41.1% priced (train) / 39.7% vs 40.0% (blind) - exactly their number. The belief is right AND already in the price. The one red cell both halves: a 2+-star DOG vs a 2+-star favorite -21.9% / -30.1% (78 / 110, 0 of 3 blind), and 3+-star sides win 3.5 / 5.9 points UNDER their price - the star-heavy side runs overpriced, not underpriced. One cell in ~65 tried (2-3 false positives expected): WATCH, not a weight. (2) STAR FORM (a star's last 5 games' points a minute vs his own baseline, ±20% = hot / cold): a dog facing a favorite with a HOT star +6.6% train / +18.9% blind (210 / 217; 2023 +8 / 2024 +39 / 2025 +6 - 3 of 3); the -150..-100 favorite vs a dog with a hot star -16.4% / -25.9% (0 of 3); every side with a hot star wins 1.6 / 4.0 points UNDER its price; a cold star ±0.5. THE BOOKS OVER-RATE THE HOT STAR - the SAME finding sports_form made 10/1 on the top-2-minutes men (NBA 3 of 4 seasons; sports.HOT_W -3 points on the hot side's read), now on a second, independent definition (the honors list, points a minute) = that weight's fifth check. NOT a second weight (it would count the same man twice - the owner's never-overweighted rule); LEAD: HOT_W's "key man" could read the honors list once it's verified. A dog with its OWN hot star +1.7% / -6.6% (+28 / -8 / -52): nothing. (3) A STAR OUT TONIGHT (a 2+ man who played for them this season, not in the box): the side missing him wins 46.0% vs 46.2% priced / 47.6% vs 46.8% - PRICED; the dog missing a star -4.6% / -0.9%, the favorite -150..-100 missing one -3.3% / -11.2% (the 10/22 "missing its own top-2 man" trap already fades that, built); a dog facing a favorite missing a star -4.4% / -8.7% - the books over-move for the missing star, as the 10/22 study said. Missing 2+ stars +1.9 / -5.1 vs the price - not held.
- YOUNG RISING MEN (the owner: "Edgecombe's a beast - his NBA debut tied Allen Iverson's for a rookie"; results/studies/nba_stars_1023/young.py / young.out - his Iverson fact isn't in any file we hold, so nothing asserts it): weight THIS season's early games more for men in their first three seasons (top-10 picks / last season's All-Rookie). Games 6-20, 2022-25, log loss, a logistic on the talent gap fitted on the season before: the engine's 20-game prior for everyone .6748 / .6109 / .6319 / .5922; young men at a 5-game prior .6603 / .6101 / .6353 / .5902 (better by .001-.015 in three seasons, worse .003 in 2024); at 10 games the same shape smaller; this season ONLY for the young .6479 / .6109 / .6375 / .5908 - a wash. The owner's dog cut (talent read 5+ over the price, games 6-20, +100..+350): every variant red in 3 of 4 seasons (-2 / -14 / +35 / -17 for the engine's; -7 / -18 / +21 / -13 for the young-5). NOT built. ONE LEAD, not young-specific: a 5-GAME prior for EVERYBODY .6446 / .6149 / .6142 / .5708 - better in 3 of 4 by .01-.03 (the market .6305 / .5820 / .6002 / .5600) - the 10/20 form study tried 20 / 40 / 80, never shorter; needs the full prior pipeline's check (sports_nba_roster.G_PRIOR) before anything moves; the prior fades out by game 10 anyway.
- BUILT: (1) sports_nba_stars.card_line - "🌟 76ers: 2 All-Stars on the floor tonight - LeBron James (All-NBA 2026), ... · Paul George is out." on the NBA cards (sports.card_extras) ONLY once last season's honors are source "bbref" (fetched) - the compiled list is a study input, never a card fact; quiet until the fetch runs. (2) THE FULL BOX SCORE from now on (sports_roster.KEEP["nba"]: threes, free throws, offensive / defensive rebounds, steals, blocks, turnovers, fouls) + tools/nba_box_backfill.py / nba_box_backfill.yml (daily, 36 min a run): this season's games fetched again and their rows replaced, then 2016-17 .. 2020-21 downloaded (the games file holds them; the rosters job reaches back to 2021 only), then 2021-25 fetched again for the new stats - ESPN's public summary endpoint, no paid API; NEEDS A PUSH to run. The player-rating study's "6 stats only" dead end reopens once it lands. NO weight anywhere (test_nba_star_power_is_a_fact_line_never_a_weight guards it). Tests: test_nba_star_power_values_team_score_and_the_card_fact_line, test_nba_stars_fetch_parses_the_source_tables_and_merges_whole_seasons_only, test_nba_box_scores_keep_threes_steals_blocks_turnovers_and_the_backfill_replaces_old_rows.

## 10/23 - 🏀 A PLAYER-BASED NBA TEAM RATING (the owner: "the engine needs to know who these players are, how they play ... like a human who follows the NBA"): STUDIED, DEAD - raw plus-minus prior stays, nothing wired
- WHAT WAS TRIED (scratchpad nba player study, study.py / study2.py - walk-forward, every season T built from seasons before T only): (1) raw last-season plus-minus a minute (the 10/20 prior, the control); (2) a BOX-SCORE composite - points, FG made / tried, rebounds, assists a minute, scaled to on-court margin by a minutes-weighted ridge regression fit on the earlier seasons (the box holds no threes / steals / blocks / turnovers - 6 stats only); (3) THREE SEASONS of plus-minus decayed (1 / .5 / .25 by minutes) and regressed to the replacement rate by 400 minutes; (4) a NEXT-SEASON predictor (ridge: next season's on-court rate from this season's shrunk plus-minus, the box rates, minutes a game, total minutes, the two seasons before - the multi-year track record / experience proxy; no birth dates in any file, so no age curve); (5) 50/50 blends of each with raw plus-minus. Team = the first-10-games roster proxy at last season's minutes (the 10/20 study's way), summed and scaled to Elo on the season before, blended 0.7 -> 0 over 10 games into the carried Elo (k 10, home 40 - today's NBA params). Rosters by a 15+ game rule or 100+ minutes.
- GAMES 1-20 (log loss, with a close; n = 292 / 293 / 289 / 291): the carried Elo .6580 / .6216 / .6164 / .5963; the MARKET .6395 / .5906 / .6092 / .5739; the current prior (raw pm) .6571 / .6177 / .6178 / .5949; box composite .6608 / .6158 / .6229 / .5952; 3-season decayed .6567 / .6183 / .6135 / .5951; next-season predictor n/a / .6163 / .6165 / .5947; pm+box .6572 / .6170 / .6177 / .5947. Every candidate sits within .000-.005 of the raw prior, each one up in some seasons and down in others (decayed wins 2022 / 2024 by .0004 / .0043, loses 2023 / 2025 by .0006 / .0002; the predictor wins its 3 seasons by .0014 / .0013 / .0002). Brier the same story (.2325 vs .2324-.2326). The market is .02-.03 better than all of them. No candidate beats the current prior by a clear margin -> NOT WIRED.
- GAMES 21-82 (the LEAD from 10/20 - keep the talent read in all season): tonight's roster = who played the team's last 10 games at their minutes there, values blended with their form (prior worth 20 games, like form_values), mixed into the Elo at a fixed weight. Raw pm: Elo .6455 / .6072 / .6064 / .5979, talent alone .6601 / .6125 / .6194 / .6258 (worse every season - overconfident, its Elo spread ~2x), the best mix (0.2-0.3) .6447 / .6057 / .6033 / .5984 - up .001-.003 in three seasons, down in 2025; the market .6184 / .5782 / .5733 / .5701. The decayed values the same (.6452 / .6065 / .6037 / .5981). Too small to call an edge, not built; the 10/20 lead is closed as a wash.
- THE OWNER'S DOG RULE ("that line don't make no sense - they got so-and-so"): NBA dogs where the TALENT read (the roster strength alone, tonight's men) puts the dog 5 / 8 / 10+ points over the no-vig close, blind, flat 1u at the close, 2022-25. +150..+350 (raw pm): 5 pts n 203 / 236 / 194 / 208 ROI +1.6% / +1.0% / +4.0% / +2.4%; 8 pts +1.0% / +0.4% / +8.8% / -7.9%; 10 pts -5.5% / +4.7% / +3.8% / -7.9%. +100..+150: 5 pts -7.4% / -14.1% / +2.4% / +9.0%; 8 pts -6.7% / -15.0% / +3.0% / +5.2%; 10 pts -3.3% / -15.5% / -4.1% / +3.4%. Through the Elo blend (0.4) and with the decayed values: the same scatter (-8% to +7%, no threshold up in 3 of 4 seasons; the +100..+150 band loses in 2 or 3 of 4 every cut). The talent read calling a dog line "wrong" wins ~31% of the +150..+350 dogs - about what the price says. NOT a weight; the dog score stays as is.
- HIS TWO EXAMPLES THIS SEASON (the saved rosters, last season's values): the Spurs were a slight HOME DOG to the Thunder (-102 / Thunder -118; the open had them -125 favorites) - the talent read 50% vs the no-vig 48%: no "line's wrong" call, and they lost 116-104. The Mavericks at Houston +330 (no-vig 22%): the talent read had them at 16% - it liked the Mavs LESS than the price (Cooper Flagg -5.4 a 48 last season; the roster's best men barely above replacement); lost 110-128. And the 76ers at the Knicks +145 (no-vig 39%): the talent read gave them 23% - WORSE than the market (Maxey +0.7 a 48, LeBron +1.2 last season, every Knick +7 to +12); they won 106-100. The owner's reads were right where ours weren't - but the box scores we hold don't carry it: last season's plus-minus can't see that LeBron / Embiid / Maxey / Brown together are better than their old teams' results (the teammate-adjusted value tested WORSE 10/20; the box composite tested here reads the 76ers the same).
- WHAT THE RATING SAYS NOW (raw pm, this season's saved rosters): top - Thunder 1769, Spurs 1729, Knicks 1692, Celtics 1682, Pistons 1665; bottom - Nets 1309, Kings 1256, Wizards 1213. 76ers 1523 (#16, +0.9 a game: Jaylen Brown 34 min +4.8 a 48, Embiid +3.5, Maxey +0.7, LeBron +1.2); Celtics #4 (+7.3: Derrick White +9.6, Tatum +9.5, Pritchard +8.1); Knicks #3 (+7.7: Anunoby +9.7, Towns +10.3, Brunson +8.2); Blazers #19 (-0.3: Jrue Holiday +3.9, Scoot Henderson +1.8, Camara -0.3). The 3-season decayed values move the Celtics to #2 (1724) and the Spurs to #3 - same picture.
- WHY IT DIDN'T WORK, said plainly: the only player facts we hold are 6 box numbers + plus-minus; the box composite explains ~a third of on-court plus-minus and adds nothing new the next season; multi-season smoothing changes a handful of players; the market already carries every roster move. Leads left: a player-level source with threes / steals / blocks / turnovers / usage / age (none in the repo, no paid APIs); real projected minutes (coach's depth charts). Regression test: test_nba_player_rating_study_keeps_raw_plus_minus_prior.

## 10/23 - 🏀 THE NBA OPENING-LINE EARLY PLAY: BUILT (the owner OK'd it 10/23; sports_nba_open + the "nba_open" spot in sports_early)
- WHAT IT IS: the engine's whole-model read of every NBA side, scored at the FIRST price the books show. A ridge logistic model (37 inputs: the price, home / dog, the stage of the season, rest, back-to-backs, 3-in-4 / 4-in-6, road-trip game, time zones crossed, altitude, the last game's margin, 5- and 10-game form, this season's and last season's records, the Elo gap - NOTHING from the box score or the injury report) fit on the seasons BEFORE the one it plays (sports_nba_open.fit - at the closing prices, lam 300 chosen on the 2020-22 walk-forward log loss), refit once a season and cached (data/sports/nba_open_model.json). Live: the ONE side a night the model likes most over the open's no-vig number by 4+ points, its price -150..+300, both teams 11+ games in (sports_nba_open.best_tonight) - ½u, its own record, posted by the hourly check the hour the first price shows (sports_early.nba_open_scan), never game day.
- THE NUMBERS (the study, scratchpad nba1023/full_model.py, 38 inputs incl. the engine's own-read gap): best side a night, open score >= .04, open -150..+300, flat: 334 bets 170-164, +13.4%, +44.7u, 2023 +9% / 2024 +19% / 2025 +13%, worst stretch -12.7u. THE BUILT MODULE replayed the same way (wf_module.py - 37 inputs, no own-read gap; fit 2023 on 2018-22, 2024 on 2018-23, 2025 on 2018-24, scored at ESPN's open, graded at the open): no games filter 329 bets 166-163 +13.0% +42.6u; WITH the 11-game rule 282 bets 143-139 50.7% (the open said ~41%) +13.7% +38.6u - 2023 106 bets +10.1%, 2024 90 +20.4%, 2025 86 +11.1%; the same sides at the close +11.2%. Dogs and favorites both carry it (favorites-only +14%, dogs-only +11%).
- WHY IT WORKS (and why it's honest under the one-factor rule): the market-only model loses -15% at the open; market + form + records alone makes +10%; the schedule / stage alone loses. It's the recent form and the records the open hasn't priced yet - and the close has: the same model picking at the CLOSE makes +5% on a different set and the same sides graded at the close make less every season. 37 weighed factors, never a trigger. Teams 1-10 games in: -3.4% on 43 blind, so both teams need 11 games (the spot is quiet until mid-November).
- CAVEATS, SAID PLAINLY: (1) only THREE seasons hold an open (2023-25; before that our open = the close), so the blind test is 282-334 bets - a LEAD by the five-check rule's sample, not a proven edge, hence ½u and its own record (the owner's call, like the Europe under); (2) the "open" is ONE source's (ESPN's recorded opening number) - live we bet the first price OUR feed shows, which the line history says is 1-4 days before game day for every NBA game so far this month (regular season 2-4 days), so the early rule holds with no exception; (3) the edge is in the #1 side a night only - the #2 side loses (-10% top-2 at the close, +7% top-2 at the open = half the #1's), so when the night's #1 isn't bettable (its team plays tonight - no fair price yet) NOTHING posts for that night, never the #2; (4) live, a team playing tonight has tonight's game missing from its form / record when tomorrow's slate is scored - the study had it; the ready rule (both teams' last games over) keeps that side from posting, the ranking may still see it; (5) open scores +.08 and up lose (-0.3% on 60) - not cut, the sample's too small, WATCH it; (6) the price-moved rule (MOVED_MAX 15 cents toward us) and the hoops injury rule (sports.hurt - 2+ out / 4+ questionable, no report = no play) are the engine's standing rules, not studied on this set.
- JUDGE: 40 live plays or the end of the 2026-27 season, whichever first; under -5% at 40 = off. The record shows in the ⏰ box as "🏀 NBA opening line W-L (±u)".

## 10/20 (later) - THE ROSTER-AWARE NBA PRIOR (the owner: "with LeBron, Embiid, Maxey, Edgecombe this don't make no sense" / "a full updated roster on all NBA teams ... who's playing, who the teams traded and who they got, at all times" / "the BENCH matters" / "a star in a slump plays like less than a star" / "we always need to look at coaching styles"): BUILT (sports_nba_roster), validated blind on 2022-25 before it touched a pick
- WHAT IT IS: each NBA player's value from LAST season's box scores (data/sports/roster/nba_<season>.csv.gz, every player every game) = his team's plus-minus a minute while he's on the floor, above the replacement rate (the 25th percentile of rotation men), at his minutes a game. Team strength = tonight's lineup's minutes x value (the top 10 by minutes, scaled to 240), turned into Elo points with a scale fitted on the season before (margin a game ~ strength, 25 Elo a point), then blended with the carried Elo: 0.7 roster at game 0, the Elo alone by game 10. The read goes into the NBA features' Elo (sports_nba_roster.adjust in sports.candidates), so own_p / the raw read / the Lock test all see it.
- WHICH VALUE (the pre-check, how well the roster strength knows THIS season's margins, 2022-25): plus-minute 0.60 / 0.59 / 0.65 / 0.55 (beat the carried Elo's 0.53 / 0.61 / 0.57 / 0.45 in 3 of 4); the box-score game score (pts, FG, reb, ast) 0.63 / 0.53 / 0.07 / 0.47 - dead in 2024. Plus-minus it is.
- VALIDATION (games 1-20 of each season with a close, 1,235 games, the roster proxy = who played the team's first 10 games, values from the season before, scale from the season before - no look-ahead): log loss carried Elo 0.6233, roster prior blended (0.7 at game 0, gone by 10) 0.6215 (3 of 4 seasons better), the market 0.6016. GAMES 1-5, where the problem lives: Elo 0.646, roster blend 0.638, market 0.630 - the prior closes half the gap. Roster ALONE (no Elo, held through 20 games) 0.642 - worse than the Elo past game 5; the blend is what works. Blend over 20 / 30 games: worse (0.626 / 0.631). So: it beats the carried Elo and sits close to the market, not AT it -> WIRED INTO THE READ, and early_trust's market pull is now SOFTER for the NBA when the prior is there (half the own read at game 0, all of it by 10 - sports.EARLY_TRUST_ROSTER) instead of the full pull; no rosters saved = the full pull stays (college hoops keeps it). It's a weight on the rating, never a trigger.
- THE BENCH (the owner): a missing man's minutes go to the NEXT MEN UP on the roster (each to ~24 a night) at THEIR value - validated on 3,721 games 2022-25 where a top-2 man (by minutes) sat: log loss flat subtraction 0.6453, redistribution 0.6429 (better all 4 seasons), nobody-out 0.6510. Using the coach's rotation depth to size the redistribution: 0.6430 - a wash, so depth is INFO only (it does set how many men the minutes spread over, 8..11, same result). Bench strength (men 6-10's plus-minus a 48 minutes) exposed per team for the cards (sports_nba_roster.bench_strength; the card says it at +/-3 and up).
- WHO'S PLAYING (the owner): the report by STATUS - probable 0.95 of a player, questionable / game-time 0.5 (and the game flagged: a rotation man still a game-time decision holds a unit play in sports.waiting_on), doubtful 0.25, out / suspended / IR 0; a questionable note saying 'expected to play' = playing; a 'minutes restriction' note caps him at ~22 minutes, the rest to the bench (RESTRICTED_MIN). ESPN's rows drop the notes and the probable men, so sd.INJ_NOTES now keeps every man on the feed with his note (sd.parse_injuries). The report is re-read every hourly run, so the strength is rebuilt with the latest news up to tip-off (the prior is cached an hour at a time).
- FORM / SLUMPS (the owner): once this season's box scores exist, a player's rate = last season's (worth 20 games) blended with his last 10 games' plus-minute. Validated 2022-25 (4,300 games from each team's 11th on, the roster = who played): static last-season values 0.6457, form-blended 0.6195 (better EVERY season; a 40-game prior 0.6246, 80 games 0.6319 - 20 it is). The market 0.5864. 'Hot' / 'in a slump' = his recent plus-minus a 48 minutes 5+ over / under his own baseline, 100+ recent minutes, 20+ a game last season - on the card. Caveat: the recent plus-minus carries the team's results too (the Elo has those) - the roster read fades out by game 10 anyway. LEAD, not built: keep the form-blended roster strength in the read ALL season (needs a head-to-head with the Elo mid-season).
- COACHING STYLE (the owner): per team from the box scores (sports_nba_roster.coach_style - last 10 games this season, else last 20 of last season): rotation depth (men at 15+ minutes), the starters' share of the minutes, pace (a proxy: both teams' points a game - the box holds no possessions), rest (how often a top-3 man sits the second night of a back-to-back vs other nights). INFO ONLY on the card (depth validated as a wash in the lineup math; the rest unstudied as weights - the owner's rule: nothing weighs the board read until it validates).
- ROSTERS: ESPN's team roster pages (site.api.espn.com .../teams/{id}/roster), all 30 teams once a day in the hourly run (sports_nba_roster.refresh), cached in data/sports/rosters/nba_<season>.json; fails soft (a team's page down = its last saved roster; under 8 men = a broken page, never a thin team; nothing saved = no prior, the market pull). Every refresh is diffed against the last: a player on a new team is written to data/sports/rosters/nba_moves.json (who, from, to, the day seen) and counts for his new team right away. This sandbox had no network (the Actions runner does) - the first real save happens on the next run; until then the engine reads the NBA the 10/20 way (the full market pull).
- Caveats, said plainly: the roster-only read is overconfident (its Elo spread is ~2x the carried Elo's) - only the blend validated; rookies / men under 15 games last season count at the replacement rate; a traded man's last-season plus-minus came on his OLD team's floor. The whole thing is a weight on the rating, capped by the blend - never a trigger (the owner's rule).

## 10/22 - NBA FAVORITE STUDIES (daily run, no Fable - the owner's usage call) + the NBA favorite read rebuilt
NBA favorites -150..-100 at the close (band: -5.7% train / -6.5% blind), train 2018-22 / blind 2023-26 (box-score cells 2021+). results/studies/nbadogs_1021/favs10.out.
- TRAPS (red train AND blind, past the band): its top-5 man back after 2+ missed -29.9% / -21.4% (40 / 51, 0 of 3); off an OT game -18.7% / -35.5%; missing its own top-2 man -11.7% / -17.0% (0 of 3); vs a team missing ITS top-2 man -7.1% / -14.4% (0 of 3 - the books over-move); 2+ more days rest -6.8% / -16.1%.
- VALUE: off a 20+ win +7.5% / +14.4% (2 of 3); at a home dog in its games 31-60 +2.8% / +5.7% (3 of 3).
- DEAD / flipped: vs a dog that blew a lead (+20 / -30, n 10), bounce after scoring 95 or less, vs a dog on a 3+ win streak, on road game 4+ (+9.8 / -14.6). Week one -4.3% / -12.4% (the no-Lock rule holds).
- BUILT (sports.mark_nba_favorites / NBA_FAV_W, test test_nba_favorites_read_off_the_books_plus_the_favorite_weights): every NBA ML favorite's weighed read (w_p) = the books' no-vig price (10/21 #5: the own read loses to the close) + these weights (-3 / -3 / -2 / -2 / -2 / +2 / +2, capped FAV_CAP 4). Locks, plays and leans read it (read_of / own_agrees), so an NBA lean now follows the books plus the studies. The top-5-returning fact reads this season's box scores (sports_nba_roster.returning) - none saved yet, so it's quiet until they are. Tracker tags for each.
- Yesterday's picks line + the NHL goalie fix (a confirmed starter settles a questionable goalie - the Sharks sat all day) logged below.

## 10/22 - NHL LONG ROAD TRIPS (the owner, on the Sharks at Ottawa: "this will be the Sharks' fifth straight road game"): DEAD - the books price the trip; one WATCH line, nothing built
NHL 2018-26 regular season at the close (18,968 sides; 9,484 games), train 2018-22 / blind 2023-26. Each team's schedule in order, no look-ahead: trip game number (consecutive away games), days on the road, time zones from home (tzo), back-to-back, first home game after a trip of N, the trip's last game (the next game is home - known from the schedule), the opponent's spot. 54 cells (6 baselines, ~2.4 false positives expected), dogs +100..+300 vs the road-dog band (-5.3% train / -4.8% blind), favorites -150..-100 vs the road-favorite band (+0.6% / -4.8%). results/studies/nhl_trip_1022/trip.out (+ trip.py). Extends the dead b2b / 3-in-4 / travel-miles / first-road-game-after-a-homestand lines (10/12, 10/15).
- **The road team deep in a trip is priced right.** All prices, trip game 4+: win % minus the no-vig number -1.3 (768 sides, z -0.8) train / -0.9 (542, z -0.4) blind; games 1-3: +1.0 / -0.4. Dogs on trip game 4+ -7.7% / -4.7% (458 / 339) = the band; trip game 5+ -5.4% / -9.2% (181 / 134), 2023 +18, 2024 -13, 2025 -18. Favorites on trip game 4+ -5.9% / -7.5% (222 / 147, blind 2023 -9 / 2024 -22 / 2025 +3) - 3-6 points under the band, z under 1, 2025 green. Trip game 6+ +2.8 / -2.9. Days on the road 7+, time zones 2+ (-2.2 / -1.0 vs expected), the trip's last game (dogs -8.7 / -7.2, favorites -7.4 / -4.9 on 128 / 83): all the band. The NBA's "dog on road game 4+ -20%" does NOT carry to hockey.
- **The home team's first game back / the home team facing a tired traveler: FLIPS.** First home game after 3+ / 4+ road games, all prices: -1.5 / -1.8 vs expected train (710 / 390) -> +3.2 / +3.3 blind (533 / 298, z 1.5 / 1.2); as a dog -15.9% / -15.4% train -> +6.5% / +9.5% blind; as a favorite -2.4% / -4.8% -> +6.5% / +5.8% (2023-24 +12-30, 2025 0 / -9). Home team vs a road team on trip game 4+: +0.9 train (z 0.5) -> +2.7 blind (z 1.2); its dogs -9.5% -> +8.0%, favorites +0.2% -> +3.2%. The sign is right only blind, train says nothing - the NBA's "favorite's first home game after a 4+ trip -22%" runs the OTHER way in hockey and holds in neither half. DEAD.
- WATCH (not a lead - n): a FAVORITE on trip game 4+ AND a back-to-back -10.7% on 51 (win-exp -3.9, z -0.6) train, -42.3% on 28 (-21.0, z -2.2) blind, 3 of 3 blind seasons red; the favorite on a b2b in trip games 1-3 is +7.9% / -0.1% (202 / 162), so it's the deep-trip part, not the plain b2b weight (which already carries the night-2 side -4.9 / -5.0, 10/13). 79 sides in 48 cells - re-check at the end of 2026-27, never a weight on this. Not built; no change to dog_score / mark_hockey_favorites / the leads.

## 10/21 - 20 MORE NBA UNDERDOG STUDIES + the weights wired (the owner: "wire weights, 20 more studies, tests and sims, wire everything in as weights")
Same set (6,594 dogs, train 2018-22 / blind 2023-26), 46 cells (~2.3 false positives). results/studies/nbadogs_1021/more20.out, sim2.out.
- HELD (train AND blind): the FAVORITE played OT last game - dogs +13.1% / +4.0% (cell), as the only + in the batch-2 score +22.6% / +18.4% (145 / 79).
- FADES (red train AND blind, beyond the -2.9% / -6.8% all-dog baseline): dog blew a 10+ halftime lead last game -23.3% / -14.2% (0 of 3); dog played OT last game -5.8% / -20.6%; dog scored 130+ last game -11.2% / -7.3%; favorite scored 95 or less last game -11.5% / -26.5% (0 of 3); dog won 3+ straight -7.0% / -11.2% (0 of 3); Elo near even but +200+ -17.1% / -12.1%; favorite 2+ more days rested -11.0% / -18.9%; opening weeks (team games 1-15) a dog that was .550+ last season -12.2% / -9.5%.
- FLIPPED / DEAD: ATS form (covered 0-1 of 5: +9.9% train, -14.7% blind), home dog vs a bad road team, season series, 4-in-6, b2b home-then-road, months, young-season records, fav off a 130-point blowout (+13.9 / -19.8).
- DRIFT CHECK before wiring: NBA totals rose (median 221 in 2018 -> 230 in 2025) and the ML-vs-spread gap drifted, so a fixed total / gap flags almost every 2026 game. Fixed: both are RELATIVE to the league's last 300 games. Relative low total (8+ under) -7.2% / -10.5% kept; relative high total +4.6% / -1.4% dropped; ML 1.5+ pts LONGER than the spread says +14.3% / +25.9% kept as a +; the short side flat in train - dropped.
- SIM (batch 1 + 2 scores together, blind): +2 or more 48.9% vs 34.3% (45); 0: -3.3%; -1: -8.5%; -2: -15.7%; -3 or less -16.2% (0 of 3). Train -2 -11.5%, -3 or less -24.8%.
- BUILT as WEIGHTS (sports.nba_dog_weights, 2 points each, inside the dog score's ±6 STUDY_CAP, never a trigger), lead-tracker tags for score +4 / -4; tests test_nba_underdog_score_weights_from_the_20_studies, test_nba_underdog_second_batch_weights.

## 10/21 - 20 NBA UNDERDOG STUDIES (the owner: "correctly picking the right underdogs"): one LEAD dog-finder, a strong fade list
6,594 NBA dogs +100..+300 with a close 2018-26 (raw win 36.6%, implied 36.6%); train 2018-22 / blind 2023-26; 50 cells (~2.5 false positives). Scripts/output: results/studies/nbadogs_1021/.
- Opening 2 weeks (team games 1-10): dogs win more than their price in both - train 39.6% vs 36.8% (+3.3%), blind 38.6% vs 36.7% (+0.8%); home dogs g1-10 +1.6% / +4.8% (3 of 4). Home dog games 6-10: +3.6% / +11.8% (the built weight).
- TRAPS (red train AND blind): home dog in games 31-60 -11.8% / -11.1% (0 of 5, 0 of 3); ML short for its spread -18% / -31%; low total (<=215) -6% / -13%; dog home after a 4+ trip -10% / -14%; fav off a 20+ win: dog -3.6% / -20.9%.
- No single angle holds blind on its own: money moving, rest vs b2b, form, unlucky record, revenge, stars out (box), travel, totals high, late season, depth, Elo read, calendar - flat or one-sided. No 3-pointers in our box scores (not testable).
- STUDY 20, A DOG SCORE (+1 each: lost last by 15+, home dog games 6-30, total 235+, lost the last meeting by 15+; -1 each: home dog games 31-60, won last by 15+, total <=215, fav on road game 4+, dog home after 4+ trip, fav off a 20+ win): it SORTS dogs blind - score 2+ 38.9% vs 35.2% (+5.6%, 226, 2 of 3); 1: -2.1%; 0: -10.7%; -1: -6.7%; -2 or less 31.7% vs 36.7% (-21.0%, 164, 0 of 3; train -21.5%). The fade end is steady; the top end a LEAD.

## 10/21 - FIVE NBA STUDIES (the owner: "find value plays and locks with NBA, especially the first 2 weeks"): nothing BUILT-worthy
9,521 games with a close 2018-26, train 2018-22 / blind 2023-26, flat 1u at the close; games 1-10 cut in each. Scripts: results/studies/nba5_1021/.
1. LOCK PROFILE - DEAD. Favs -150..-105 blind 52.5% vs 53.4% (-5.8%). 38 cells, none up train AND blind. The engine's Lock proxy (own read 56%+ over the price) blind 48.8% vs 53.8%, -13.2% on 320, 3 of 3 red; games 1-10 -31% on 39. Favs the read likes 10+ over the market -16.5% (196).
2. FATIGUE - DEAD (72 cells). Traps: dog on road game 4+ -20.2% blind (211); fav's first home game after a 4+ trip -22% (55); dogs at Denver/Utah -20.6%. The traveler-fav LEAD: train +5.3% (121), blind +6.8% (70, 1 of 3) - still a LEAD.
3. EARLY SEASON (194 cells) - the BUILT NBA home dog games 6-20 holds: blind 46.0% vs 40.1%, +9.4% on 150, 3 of 3; all from games 6-10 (+14.6% blind on 51). Week 1 (games 1-5): favorites -12.1% blind - no Lock in week 1; away dogs +9.5% on 98 (2 of 3) thin. Roster turnover flips sign - DEAD. Warm-start dogs g6-20 +19.8% on 63, last-year 35-50% teams as dogs g11-20 +6.6% on 80 - thin LEADS.
4. STAR ABSENCE - traps: a favorite facing a team missing its star -15.3% blind (134); a favorite whose top-5 man returns after 2+ missed -19.0% train (72) / -19.7% blind (83), 3 of 3 red - a fade-weight LEAD. Dog missing its star 2-5 straight +13.1% blind (188) but -1.9% train - LEAD.
5. ENGINE vs MARKET - the NBA own read loses to the close every season (log loss .602-.647 vs .571-.623; games 1-10 worst). Siding with it 8+ over the price -11.9% blind (936); every band red. Fitted trust 0.05-0.08 = the market. No NBA value/Lock off the own read.

## 10/20 - NBA ROSTER PRIOR: TEAMMATE-ADJUSTED PLAYER VALUES (the owner: "76ers should be a coin flip, that line is off"): WORSE - raw plus-minus stays
Raw plus-minus credits a player for his team (LeBron on the 25-26 Lakers +0.03 a minute, Maxey / Edgecombe ~0, every Knick high). Tried, blind 2022-25, games 1-20 log loss of the blended read (1,165 games): raw plus-minus 0.7072, half team-adjusted 0.7073, 3/4 0.7092, fully adjusted (on-court minus the team's result) 0.7259, game score 0.7170; market 0.6033. Games 1-5: raw 0.637, market 0.634. The teammate-adjusted value tells the new season WORSE every season - kept raw. 10/20 Knicks -180 / 76ers +150: engine 76ers 34% (own read), books ~36% no-vig, +150 needs 40% - no value; no read we have says coin flip.

## 10/20 - RECORD-CHASE PROPS (the owner: "when a player needs a certain amount to break a record, they always hit it"): DEAD in our data - not built
Box scores 2021-26 (data/sports/roster/*.csv.gz). Player within reach of a round season / in-data career mark: NBA points 2,883 spots hit 62.3% vs 65.7% expected (controls 64.1%); rebounds / assists / career marks the same; NHL points 51.0% vs 61.7%, goals 34.7% vs 56.1%; NFL yards 55-62% vs 61-66%. Beat his own last-10 average in the milestone game 34-46%. Near a mark they hit it a little LESS often. True league / franchise records: too rare to test; no prop odds history (books move milestone props). No record-watch card.

## 10/20 - DAILY STUDIES (with the 4 NBA opening-night studies above = 10): NFL / college QB 3+ interception games, NHL goalie rust (7+ days) and both-backups games, NHL road favorite at a losing home team, NBA first back-to-back, NBA the game after the opener: ALL DEAD; nothing built
- QB turnover game (3+ INT, or 2+ INT under 200 yds) next game: NFL train +2.5 / blind -15.0 (3+ INT), the 'any flag' +7.6 blind is 2025-26 alone; college -13.4 / -9.9 for the 3+ INT team but fading pays nothing. Priced.
- NHL goalie 7+ days since last start: flips (dogs -9.4% -> +1.4%); both backups: nothing (the -130..-200 favorite -13.4% blind, train flat - WATCH).
- NHL road favorite -130..-150 at a losing home team: +4.6% -> -0.2% (n 105 / 62). DEAD.
- NBA first back-to-back of the season: noise on small n; the built rested-vs-b2b weight confirmed. NBA game 2 after the opener: flips (opener losers -20% -> +27%). DEAD.

## 10/20 - NBA OPENING NIGHT AUDIT (the owner: "the engine is tripping - no picks, the 76ers +155 with LeBron is super value"): the engine didn't crash or break a rule - its NBA read was LAST SEASON'S TEAMS. BUILT: early-season trust ramp + an Elo bug fix
- The NBA Elo is team results only (no rosters / trades). Opening night = last season's end rating regressed 1/3: Knicks 1678 vs 76ers 1530 (the Knicks swept them in round 2) - own read 76ers 25.9% vs the market 38.4% (with LeBron, Maxey, Edgecombe, Embiid). 12.5 points under the price = 'fighting the line' - the side forbidden. Same for every team that got better over the summer. Celtics @ Pistons: own read Pistons 56% but the price moved against them (money_against). Spurs: own 56% vs the market 50%, blended to a lean.
- BUILT (sports.early_trust / early_shrink): in an NBA / college hoops season's first 10 games (the fewer games of the two teams), the own read, the board read and the raw read are pulled to the market - fully at 0 games, none by 10. The 10/20 study: Elo never beats the close in games 1-20 (log loss .657 vs the market .635).
- BUG FIXED (sports_model.Elo.rating): the offseason regression ran on EVERY call to a cached Elo (148 -> 99 points on the second call) - once per offseason now.
- Not built: NBA player / roster data for 2026-27 (box scores start with the season); the engine learns the new rosters game by game.

## 10/20 - NBA OPENING NIGHT STUDIES (the owner: "we need to get on top of the NBA now"): ONE BUILT (early-season home dog, a weight), one LEAD, the rest DEAD
9,525 priced regular-season games 2018-26, closing ML, train 2018-22 / blind 2023-26; ~96 cells, ~5 chance hits.
- **BUILT - NBA home dog +100..+200 in a team's games 6-20 (sports.NBA_HOME_DOG_* / season_games):** train 124-140, 47.0% vs 40.2% implied, +13.6% on 264 (5 of 5 seasons); blind 69-80, 46.3% vs 40.1%, +10.1% on 149 (3 of 3). Games 1-5 and 21+ nothing; +200..+300 -8%. +2 on the dog score (a weight). Tracker: "NBA home dog, games 6-20".
- The market is right early otherwise: dogs/favorites by game number = the vig; teams that changed a lot over the summer ('jumpers') +53% train -> -17.5% blind (DEAD); last year's playoff teams nothing.
- Elo carry-over: never beats the close (log loss games 1-5: market .635 vs best Elo .657 at 50% regression; reset .683 the worst). As a weight only - carry 50% regression.
- LEAD - a FAVORITE whose opponent is on its 5th+ road game or its first home game after a 4+ trip: +7.5 / +9.0 edge vs band (blind n 166, 2 of 3) - paper-track.
- DEAD: 3-in-4 / 4-in-6 (the market has it), a dog ending a long road trip (-34% blind), cross-country with no rest (NBA never schedules it), every dog situation (home / road, off a win / loss, vs a streaking favorite, divisional).

## 10/19 - TEN STUDIES (daily run): early long dogs at the first fair number, NHL goalie on back-to-back nights, NHL after scoring 6+, NFL after Monday night, college both off a bye, NFL the week before a Thursday game, college weekday (MACtion) games, NHL favorite on a losing streak, NFL division road favorites, NHL both teams on a back-to-back: ALL DEAD, a few WATCH lines; nothing built
Closing lines unless said, train before 2023, blind 2023-26; ~330 cells, ~16 chance hits expected.
- Early long dogs at the first fair number (+250..+299 / +300..+349, NFL + college 2020-26, 833 sides): the vig, not a money pit (-1.5% / -6.8%; train red, blind green - flips). The +350 limit is fine; no extra weight.
- NHL night 2: the same goalie both nights is rare (~35 sides a season) - nothing beyond the built back-to-back weight. WATCH: the same-goalie b2b favorite (n 39).
- NHL after scoring 6+, as a dog next game: -12.1% train / -13.0% blind vs band -7 / -4 (3 of 3 blind seasons red, pooled z ~-1.8) - WATCH as a fade, not built.
- NFL after Monday night: DEAD. WATCH: the post-Monday home favorite (8 of 9 seasons, n 94, found at split 9).
- College both teams off a bye: DEAD (home dogs only - a late split, WATCH).
- NFL before a Thursday game: ML DEAD; the short-week favorite covers 44% (train doesn't hold) - WATCH.
- College Tue/Wed games: DEAD (n 111 priced).
- NHL favorite on a 4+ losing streak (home / road, and the dog facing it): DEAD (confirms 10/13).
- NFL division road favorites -1..-3.5: DEAD (flips).
- NHL both teams on a back-to-back: DEAD - the edge cancels; the built one-sided weight confirmed (the lone b2b dog -18.6% / -15.7%).
- Fixed: the 6-compound challenge tracker named a SPREAD lean (Commanders) - moneylines only now (regression test).

## 10/18 - TEN STUDIES (daily run): college 3rd straight road game, NFL 2nd road game after a long trip, NHL 4+ days rest, NHL after OT / a shootout, college close-game heartbreak, NFL favorite off a bye, NFL facing a backup QB, NHL division games, college rating vs record, NFL desperate home team: ONE BUILT (NHL OT / shootout endings, a weight), two LEADS, the rest DEAD
Closing lines, train before 2023, blind 2023-26; ~300 cells, ~15 chance hits expected.
- **BUILT - NHL how the last game ended (sports.ot_last / OT_W):** the OT LOSER next game -10.2% on 818 train / -12.6% on 580 blind (as a favorite -9% / -16%, 7 of 8 seasons red); the OT WINNER +0.7% / +6.2% (8 of 8 at or above band); a SHOOTOUT winner as a dog -18.9% / -13.6% (8 of 9 red). Dog score: OT win +1, OT loss -2, shootout win -2, the opponent off an OT loss +2 (inside STUDY_CAP). Tracker: "NHL side off an OT win / OT loss (fade) / shootout win (fade)".
- LEAD - NFL favorite facing a KNOWN backup QB (the backup also started last game): +4.6% train / +8.4% blind vs band, ATS 55.7%; the backup's side -20% blind - the market under-adjusts (same sign as the 10/8 fade). 2 of 4 blind seasons; paper-track.
- LEAD (weak) - college losing-record dog with a top-half rating (+100..+300, 4+ games): +26% train / +12.8% blind on 75, ~8 a season. Same family as the rating-backed-gap lead; paper-track.
- WATCH - NHL rested 4+ days vs a team on 1-2 days: train -6.6% -> blind +7.9% (favorites +11.8% blind, 3/3) - train doesn't hold. NFL traveler's 2nd road game as a dog -45% blind (train flat). College dog off a 1-3 pt WIN -18.9% / -38.5% (z small).
- DEAD: college 3rd+ straight road game (flips), NFL favorite off a bye vs a team off a road game (n 20 / 6, flips), NHL division games (noise; early division favorites +4% both halves - one cell of 42), NFL desperate home team (priced; the 0-2 lead already logged), college heartbreak loss (flips).

## 10/18 - MEDIA EXPERT PICKS as a weight (the owner: should the engine look at everyone's predictions?): NOT BUILT - the owner's call ("the engine is its own entity")
Untested on our data (the archive / CBS / ESPN / Pickwatch hosts are blocked from the cloud session). Published research: media experts don't beat the line (Boulier & Stekler 2003; Song, Boulier & Stekler 2007 - ~31,000 picks, 74 experts; Forrest & Simmons 2000; Spann & Skiera 2009), and our 10/6 Dr. Bob study found no lift from a capper agreeing with us. The owner, 10/18: no predictions in the engine - never re-propose.

## 10/17 night - THE SATURDAY SWEEP (13 unit plays, the most ever; the owner: "are we doing it the right way?"): ON TRACK - the edge is the early plays, the Dog and the big Locks; the leak is plays whose OWN read sits under the price. BUILT (the owner's OK, 10/18): sports.own_beats on value plays + the dog Lock
- The day: board 3-6 +3.0u, early 3-0 +5.6u (BC, Kentucky, BYU - the 10/17 audit ranked Kentucky 1, BC 2). Early + the Dog +9.5u; everything else 2-6 -0.9u. Beat the close 4, same 3, worse 3.
- Since 9/27: 23-22 +10.8u. Locks 8-5 +7.8u (the 2.5-5u Locks +9.0u; ½u Locks 5-4 -0.2u). Dog 6-10 +1.2u. ½u value plays 7-4 +1.3u. Gap 1-3. Early 8-9 +9.9u (MLB exam 2-0 +7.7u; NFL blowout spot 0-6, off).
- The leak: FAU, Troy, Wisconsin (dog Lock) posted on the weighed dog read with the own read under the price (edge_own -4%) - all lost. Blind: that kind -7.4% / -11.6%; with the own read over the price +11.7%. The dog Lock had no own-read test (the favorite Lock needs own_agrees). Built: own_beats (moneyline value plays + the dog Lock). Cost: ~1-2 plays a Saturday.
- Volume: Saturday college dogs are NOT correlated (real day sd 2-5u); 10 x 1u dogs sd ~4u, worst real Saturdays -8..-11u. Volume is fine.
- Checked, not bugs: Indiana "+160 at the open" is this week's first fair price (line history 10/11 04:12Z +160 - the game file's +107 is the summer look-ahead line the cards skip on purpose); BC as the Dog over the 🔍 plays is by design (upgrade_dog skips gap plays - 10/17).
- 🔍 gap rule: keep at 1u, judge at 50 plays, cut under -5% (blind +4% on 260, 2026 -4%).

## 10/17 - TEN STUDIES (daily run): moneyline vs spread mismatch, the game after a big upset, the exchange vs US books, the stale book, NFL primetime, NHL record vs goals, MLB elimination games, long dogs +220..+350, spreads through key numbers, NHL early records: TWO BUILT (weights), the rest DEAD / watch
Train 2018-22 (odds history 2020-22) / blind 2023-26, closing prices unless said; ~600 cells tried in all, ~30 chance hits expected.
- **BUILT - long hockey dogs (sports.NHL_LONG_DOG / NHL_LONG_DOG_W):** NHL dogs +220..+260 -25.7% on 494, 0 of 9 seasons up (z -2.9); +300..+350 blind 4-52. -3 on the dog score (a weight). College +300..+350 = the vig (-6% / -3% blind, no penalty); NFL -10..-15% but flips train/blind (none); MLB too few. Tracker: "NHL dog +220 or longer (fade)".
- **BUILT - NHL record under its goals (sports.pyth_luck, PYTH_W +2):** 5-20 regular-season games in, win % 10+ pts under goals for²/(for²+against²), as a dog: train 59-58 +19.9% (4/5 seasons), blind 33-27 +34.5% on 60 (4/4); holds at 6/8/12 cuts, dies after game 20. Overlaps the built last-10 PDO weight in spirit (the STUDY_CAP holds the sum). Tracker: "NHL dog, record 10+ under its goals". Fading the lucky ones: right sign, thin (34) - not built.
- Moneyline vs spread mismatch at the close (variant of 10/8): DEAD - NFL blind +33% on 76 is 2025 alone; college -25% blind.
- After a big upset: DEAD; WATCH - college: the NEXT opponent of a -300 favorite that just lost outright, as a +100..+350 dog, +39% blind on 49 (train +1.6%). The +250 upset-winner hangover (built -3) re-confirmed.
- Exchange / sharp no-vig vs the best US price: DEAD (NFL -2.8% blind, college -13% to -23%); betfair leaves the feed after 2022.
- Stale book after a big move: DEAD / untestable - snapshots ~48h apart, a top-5 US book lagging 0 NFL / 6 college times.
- NFL primetime (SNF / TNF splits): DEAD - every cell flips train to blind.
- MLB postseason elimination splits: DEAD (facing elimination as a dog 14-25 -18%); WATCH: the team with the opponent on the brink, as a dog, 26-21 +27% (blind 7-8).
- Spreads crossing 3 / 7: DEAD (NFL); college crossed-3 away-from side 25-17 ATS blind on 21 train games - watch only.
- NHL early records (dog with the better points %): DEAD - the hot start fades (blind -12.8% on 145, 0/3).
- (the owner's question, 10/17 night) NFL team the game after its defense gave up 35 / 40 / 45+: DEAD - 40+ was +17.9% ML 2018-22 (162) and -13.7% blind 2023-26 (99), ATS 41%; as a dog +26% -> -16%; 35+ and 45+ the same flip. The bounce-back is in the price.
- Lead tracker: the split signals keep losing live (money 10+ over tickets 43-64 -15.5u, 70%+ of tickets 98-57 -14.5u) - neither is a weight (dead 10/7); the NHL sharp dog (a weight) 3-8 -4.4u on 11 - too few to cut. Fixed: "college dog, engine 10+ over the books" read the market and never fired (now the raw ratings read).

## 10/17 - THE SIX OPEN EARLY PLAYS AUDITED (the owner: "huge underdogs, upper 200s, at two units ... make sure the engine is using its weights correctly"): the 2u plays are the college EXAM BAND sized by raw Kelly on a read the market beats; the band passed at the bare minimum 3 hours after failing; the scan posted two dogs outside the band the exam graded (BUILT: the scan needs the band at the early price too); sizing = OWNER'S CALL

- **What's open (10/17 04:00Z), where the units come from:** two kinds. (1) The SPOTS (fixed size): Boston College +215 vs Pitt (🛌 bye, 1u; score 5.38 = bye 4.0 + rain lead 1.5 - read 0.1; the own read 30.3% sits AT the market 30.4%, it cleared the 5-point bar only through the rain weight on a forecast six days out; price now +195 = the money came to us); BYU +300 vs Notre Dame (🔨 hammered, ½u; score 9.5 under the OLD 12-point cap = gap 12 + hammered 2 - ice cold 4 + .700 team 1.5 - style 2; under today's 5-point cap it scores 2.5 and would NOT post - the 10/15 finding; price now +320 = the money turned back; RB LJ Martin out, not a key spot). (2) THE EXAM BAND "ncaaf +4..8" (sports_early.scan, units = sports.kelly_units on the RAW own read, ½u-5u): Tennessee +270 vs Alabama (own 33.0 / market 25.9 -> 2u), San Diego St +245 vs Fresno St (35.3 / 27.8 -> 2u), Kentucky +195 at Oklahoma (37.2 / 32.5 -> 1u), Marshall +114 vs South Alabama (49.1 / 44.7 -> 1u), all posted 10/16 16:44Z. The two 2u plays ARE the rule as written (quarter-Kelly on the own read, CLAUDE.md), not a bug - but the read they ride on is the one the 10/15-10/16 studies showed holds nothing the market lacks (shrink 0.000; a 5-10 point college gap won 39.4% blind, -26.7%).
- **The band passed on a knife edge:** 13:47Z 10/16 run: 53 dogs, -9.4% (2025-26: 32 dogs -24.2%) = FAIL. 16:38Z run: 60 dogs (PASS_N is 60), +7.4%, 2024-25 20 dogs (PASS_SEASON_N is 20) +16.6%, 2025-26 40 dogs +2.8% (PASS_ROI is 2%). Nothing but the hourly data refresh landed between (the QB-form change was 10:54Z). One 2025-26 winner turned loser = -5.7% = FAIL. Reproduced exactly from the repo (60 / 41.7% / +7.4% / 20-40). Like the MLB band (10/16): a gate that swings on a handful of dogs, now carrying 6u.
- **The scan posts a different population than the exam graded (BUILT - sports_early.exam_band_ok, test_early_exam_scan_posts_only_the_band_the_exam_graded):** the exam grades every dog by the gap at its OPEN price; the scan posted by the gap at the price NOW. Walk-forward like the exam (tune 2021-24, blind 2024-26, 6,009 priced college games): dogs in +4..8 at the close AND bettable = 60 (the exam's own): +7.4% at the open, +19.6% at the close, both seasons up (+35% / +12%). Dogs in +4..8 at the close but NOT at the open = 41: -6.3% (2024-25 -22.4% on 16, 2025-26 +4.0% on 25); 37 of them are dogs the market had moved AWAY from since the open (-2.8%). Tennessee read 14.8 points UNDER its +100 open (the 10/7 look-ahead; the first fair number 10/11 was +210, it ran to +270 while the starting QB stayed questionable) - the band only opened once the market ran away. San Diego St read 8.7 over its +260 open - the "+8+" band, which FAILED the exam (-14.6%, 183) - and slid into +4..8 when the price came in 15 cents. Kentucky (+4.7 at its +195 open) and Marshall (+4.4 at +114) are the band the exam proved. The scan now needs the band at the early price too (no open on record = the price now). Also BUILT in the same place: the exam scan never asked college completeness (v24.seen_all) - the spots did; all twelve teams on the open plays are complete, so nothing changes today.
- **Sizing the exam band (OWNER'S CALL, numbers):** on the exam's own 60 dogs at the open, flat 1u = +4.44u on 60u (+7.4%); quarter-Kelly on the raw read = +3.26u on 111.5u (+2.9%) - the 2u-sized dogs went 9-15 (-14.0% flat), the 1u 3-3 (+54%), the 1.5u 8-10 (+23%), the 2.5u 5-6 (+13%). Kelly on this read sizes UP exactly where the read is most over the market, and that is where it is most wrong (10/16 calibration). Proposal: exam-band plays flat 1u (the band's own record is the only proof there is) - the 10/16 MLB finding asked the same; CLAUDE.md's "quarter-Kelly by the own read" is the owner's rule, so not changed. Live exam band so far: MLB 2-0 (+7.7u at 3u each - the Brewers twice).
- **Injuries at post time:** Tennessee's starting QB Faizon Brandon (started 9/26; the backup MacIntyre started 10/3 and 10/10, 2 picks at Arkansas) is QUESTIONABLE on the SEC's Thursday-night report - filed into injuries_official.json at 17:03Z, 19 minutes AFTER the 16:44Z post; today's scan blocks him (sd.team_unsure, maybe=True). The play stays (the owner's rule); watch() flags only a player ruled OUT after the post, so the card says nothing about it. Kentucky: RB CJ Baxter and 3 more questionable (not key spots); Oklahoma 5 out + WR Livingstone doubtful + 3 OL questionable. BYU: RB LJ Martin out. BC / SDSU / Marshall / South Alabama / Fresno St: no official report in the repo (Rotowire / Covers coverage at run time can't be re-checked from here).
- **Honest ranking, best to worst (what the studies proved, not the raw read):** 1. Kentucky +195 (1u) - the proven band at its own open price, money flat since Tuesday (+210 -> +195 -> +205), fits the 10/17 college LEAD (dog +150..+300 at the Thursday look, engine 2+ over, money flat: blind 42-64 +34%); 5-1, won 4 straight. 2. Boston College +215 (1u) - the one spot that held every honest test (bye: college +16% fair), and the money came to us (+195 now); but the read itself sees no value and the bar was cleared by a week-out rain forecast. 3. Marshall +114 (1u) - the proven band at its open; a short dog, price drifting away 6 cents (+120); 3-3 off two losses. 4. BYU +300 (½u) - the hammered spot (the one honest form of a read over the open, 10/16), but a 24-point read gap the market is right about (blind 32% won in that bucket), an ice-cold fade, and the money has turned back past our price (+320). 5. San Diego St +245 (2u) - at its open it was the FAILED +8+ band; 2-4, lost 14-66 last week (ice cold); 2u on a read the market beats. 6. Tennessee +270 (2u) - outside the band the exam graded (-14.8 at the open), the market ran 60 cents away from it since the first fair number, the starting QB questionable, ice cold, 2u. The NFL blowout spot (blind -12.5%, live 1-8) has no open play; it is still ON in code (SPOTS_OFF empty - the owner's 10/15 call).
- **What the fix would have changed on today's board (the posted picks are untouched - the owner decides):** Tennessee +270 and San Diego St +245 would NOT have posted (4u); Kentucky, Marshall, BC, BYU post as they did. Verdict: BUILT (the scan matches the exam) / OWNER'S CALLS (flat 1u on exam-band plays; whether the knife-edge band should carry 6u this week).

## 10/17 - THE NFL LOCK HUNT (the owner: "do the NFL like we did college"; 4 Fable studies, walk-forward, blind 2023-26): favorites DEAD, the own-read gap DEAD, one dog LEAD
- **Favorites -101..-150 (640 sides):** -6.3% train / -4.4% blind / 2026 11-12 -14%, red 8 of 9 seasons; 85 factors, 29,319 mined cells = chance (shuffle test). The engine's Lock rule in the NFL: train +6.7%, blind 10-12 -22.7% (with the backup Lock -8.5%) - the own-read gate picked the worse half. No weight fixes it.
- **Dogs +100..+350 (1,871):** the own read over the market is noise in the NFL (every gap bucket = the band; the read is ~pure Elo, so the college weights-only split doesn't apply). A dog read 45%+ on the OWN read: blind -4.9% (DEAD as a Lock rule); on dog_p (market + score) 45%+: +1.2% blind (flat). What carries is the ANGLES: dog score 8+ blind +9.7% (101), 10+ +23.9% (71) - matches DOG_GATE 8, but it leans on the drift fade (money ran away = -12.6% / -9.9%) and east-west (+28% / +36% on 27).
- **Paid odds history (first fair number, 1,747 games):** the college Thursday flat-money pattern fails in the NFL (27 versions, all red train and blind); engine gap, early move, sharp-vs-soft: chance. DEAD.
- **Live 2026 NFL:** unit plays 3-4 +3.8u (all the 5u Vikings Lock); leans 3-4-1; early 1-2. Blocks checked: OWN_TRAP, fighting, DOG_GATE 8, the -150 cap each blocked more losers than winners blind.
- **LEAD (closest to a build): the 0-2 team as a dog (+100..+350)** - train 14-14 +28%, blind 11-9 +76%, 2026 3-2; all winless 0-2+ 47-58 +28% pooled, 8 of 9 seasons up, ATS 68% / 59% (independent of the 10/8 ATS lead). ~5 a season, weeks 3-4. Proposed: +3 on the NFL dog score (a weight) - the owner's call. 0-3+ mixed.
- **The NFL "blowout" early spot:** blind -12.5% (94), live 0-6 then 1-2 - proposed off in the NFL (the owner turned it back on 10/15 - his call). Bye +17% (24) and MNF +15% (62) hold; the coach-first-season fade has the wrong sign blind (+5.9%).

## 10/17 - THE COLLEGE LOCK HUNT (the owner: "find the locks in college football - the -120s smack, and there are dog locks"; 4 Fable studies, walk-forward, blind 2023-26): favorites DEAD as a blanket rule; three LEADS; one mechanism to act on
- **Favorites -101..-150 (1,076, 2018-26):** the band loses 7-9% at the close; 88,947 mined combinations do no better than shuffled data. LEAD "rule A": FBS favorite off a WIN, opponent off a LOSS, our Elo rates the favorite higher - 176 picks, 64.2% vs 53.2%, +15.7%, up 9 of 9 seasons, blind 60-29 +21.7%, 2026 10-3 - but it's the best of ~12k cells (what chance makes look 9-for-9). Paper-track. Trusting the own read more (trust 0.1-1.0) never makes college Locks. Known fades confirmed: favorite off a loss -14/-15%, -136..-150 -12/-18%.
- **Big-gap dogs (own read 5+ over, +100..+300):** run AT the market (train -0.1% / blind -1.9% / 2026 -6.7%); every factor flips; 4,828 cells = chance. THE MECHANISM: a gap made only by the WEIGHTS (form / letdown / travel / rest) while the raw Elo + home edge sides with the favorite - gap 10+ train -13.2% (209), blind -15.7% (161), red 8 of 9 seasons, 2026 -28%: BUILT-worthy as a block. Rating-backed gaps (Elo itself has the dog better) 15+: +14.3% / +4.3% - FBS-only blind +3.9% (LEAD). No filter keeps Tulane and drops all six live losers.
- **Paid odds history (first fair number, 4,200 games 2020-26):** favorites - no combination beats the price early in any season; "engine + early money" -10..-17% (DEAD). LEAD: dog +150..+300 at the Thursday look, engine 2+ over Tuesday's market, money FLAT Tue->Thu, sharp and soft books agree - blind 42-64, 42.0% vs 31.5% needed, +34% (z 2.5), ~2 a Saturday, 2026 2-4; the edge moved between gap sizes train vs blind - paper-track.
- **Our live 2026 college board:** unit plays 6-3 +6.5u (Locks 4-1, three won by 1 point); early plays 1-7; pulled 2-2 (Tulane, UAB won). The current blocks (12+ trap, trust 0, dog gate 4) each blocked more losers than winners blind and in 2026. LEAD: Tuesday-read dog gap 5-8 at the first fair price, +17% pooled 2020-26 (161, ~1 a Saturday), up 6 of 7 seasons.
- The owner turned on (10/17) 🔍 big-gap college dog plays at 1u and the underdog Lock - the weights-only block above is the owner's call (it would drop part of the 🔍 plays).

## Yesterday's picks (the daily look-back, from 10/16)
- 10/24: board unit plays 3-5, +3.7u (Illinois +310 2u Dog WON 21-10 at home vs Oregon +6.2u; Arkansas St 🔍 1u won 38-32; Mammoth ½u thin Lock won 5-4; Tennessee 🔍 lost 27-24 at South Carolina, C Michigan 🔍 lost 28-27 to Miami OH, Ole Miss 🔍 lost 34-27 at Texas, the new dog_plays Mississippi St (23-15) and N Illinois (56-21) both lost); early plays 2-6, -1.8u (Arkansas St, Wisconsin won; Ole Miss, Tulane, Auburn, W Michigan, Navy, C Michigan lost) - the day about +1.9u. Lesson: four rules bet the same college own-read gap 14 times (4-11) - the 10/24 audit fixed it (🔍 15+, one dog_play a day, engine spot paused, FBS-only blowouts); the 10/25 study says the road gap dogs are the bleeders.
- 10/23: unit plays 2-0, +4.6u (Wyoming +180 2u Dog WON 28-14 vs Air Force - the owner's call after a +170->+180 wobble kept it off the 8 AM board; Army +100 1u 🔍 WON 38-35 at Tulsa); early plays 2-0 +1.5u (Wyoming +200 ½u, Army +100 ½u) - the day +6.1u. Leans 3-1 (Celtics 107-103, Pistons 128-111, Avalanche 6-3 won; Magic lost 115-93 to the Wolves). Beat the close 3 of 6 (Celtics, Army, Magic); Wyoming closed +210 - the money left and they won. Lessons: the cards were written before the 10/23 write-up rewrite (fixed: v53/v54, the sharp-money buffer, thin edge = ½u). The owner's own calls went 5-0 (D503's Call log).
- 10/22: unit plays 1-1, -0.86u (Sharks +114 1u WON 6-2 at Ottawa - the owner's call, the backup goalie in for the Senators; Predators +120 2u Dog LOST 6-0 at Boston - shut out, the close went to +130 so the market agreed against us, a fair bet that lost big). Leans 2-3 (76ers -148 won 114-106 vs Cleveland, App State +350 won 34-31 vs James Madison; Patriots +130 lost 30-24 at Chicago, Hurricanes -118 lost 6-5 at Edmonton, Kennesaw St +300 lost 34-6 to Liberty). Beat the close 1 of 7 (Hurricanes, -118 vs -135). No audit flags. Lesson: no bug; the Predators were the size-up the 10/23 plan now stops (a Dog needs its own read over the price).
- 10/21: no unit plays (a 12-game NBA slate, opening week - nothing cleared; the owner's homie was mad, the why is in the chat); leans 3-2 (Blazers -142 won 124-83 vs the Suns, Hornets -118 won 110-103 at the Nets, Grizzlies -125 won 123-103 vs the Jazz; Magic -130 lost 132-125 to the Hawks, Panthers -112 lost 5-1 at Ottawa with the backup goalie in). NBA leans 3-1. Fixed that day: the live 'tied and plus money = a bargain' line on a pregame dog (Sam Houston), BY SPORT units, the card rewrite.
- 10/20: no unit plays (NBA opening night + hockey, leans only); leans 3-2 (Blues -148 won 2-1 vs the Jets, Devils -110 won 4-3 vs Colorado, Kraken -115 won 4-3 in a shootout vs Detroit; Spurs -112 lost 116-104 to OKC - outscored 65-44 in the first half, Golden Knights -115 lost 6-2 to Tampa - down 5-2 after two). Beat the close 1 of 5 (Devils; the Kraken drifted to +102). Lesson: the NBA opening-night read (last season's Elo) liked the Spurs ~61% vs a coin-flip market and missed the 76ers (won 106-100 at the Knicks at +150) - led to the 10/21 NBA work: 5 Fable studies + 40 underdog studies, no Lock in a team's games 1-5, dog weights (see 10/21). The 10/21 daily run's 10 studies = those 40 NBA studies (no extra spend - the owner, 10/21: too much Fable use).
- 10/19: unit plays 0-1, -1.5u (Sharks +114 Dog lost 3-1 at Toronto - the own ratings read sat under the price, the weighed read over it: the kind the owner now tracks); leans 2-0 (Commanders covered in a 23-17 loss, Rangers 5-2). Lesson: the own-read-under Dog is now tracked (lead tag).
- 10/18: no unit plays (a leans-only Sunday); leans 3-0 (Packers -115 23-13 - the challenge's first pick, Steelers 26-19 at Tampa vs rookie Jalon Daniels, Rays 3-1). Lesson: none.
- 10/17: unit plays 7-6, +9.8u (board 4-6 +4.2u: BC Dog 2u +195 W 27-21, BYU +310 W, Air Force W, San Diego St +235 W; Wisconsin dog Lock, FAU, Troy, Rice, Indiana, E Michigan lost - early plays 3-0 +5.6u: BC, Kentucky, BYU). Beat the close 4, same 3, worse 3. Lesson: the three losers whose OWN read sat under the price (FAU, Troy, the Wisconsin dog Lock at a 50% read) - built own_beats on value plays; the underdog Lock turned OFF (the owner); the 8 AM double post fixed. Leans: none.
- 10/16: no unit plays (a lean-only Friday); leans 1-1 + 1 void (Bruins -112 won 4-2 at Anaheim, matched the close; Coastal -102 lost 35-32 to App State - led 24-14 at the half, outscored 21-8 after it - beat the close by 10 cents (closed -112): a fair bet, a blown lead, not a bad read; Rays rained out, void). Lesson / fix: none from the games. Found today: the 8 AM board posted twice (8:00 sports run + 8:01 live-watcher pass) - FIXED (one pick per game, one Lock per round, in the engine's load and the git merge, from 10/18); the lead tracker's 'college dog, engine 10+ over the books' never fired (read the market) - FIXED (raw ratings read).
- 10/15: unit plays 1-1, +0.5u (Mammoth +102 Dog 1u won 4-2 at Edmonton; Seahawks -142 Lock ½u lost 17-14 at Denver); leans 2-1 (Guardians, Devils won; Maple Leafs lost 5-4). Beat the close on both unit plays (Mammoth closed -115, Seahawks -155) - the Seahawks was a fair bet that lost a 3-point game, not a bad read. Fixed: the pick audit's false "1u on a thin edge" flag on the Dog (the Dog has its own size).

## 10/16 - TEN STUDIES (daily run): NFL heartbreak / lucky winner, losing-record home favorite, NHL after a shutout, NHL totals after high / low scoring, college cover margin, college first conference road game, the engine's read by month (NHL) / by week (NFL), NFL division stretch, home dog after a road win: ONE BUILT (college dog off a 21+ cover), the rest DEAD / leads
- **College dog off a 21+ cover (beat the closing spread by 21+ last game): BUILT as a fade weight (-2 on the college dog score, sports_form.big_cover / LAST_COVER, lead tag "college dog off a 21+ cover (fade)").** +100..+300 dogs won 27.6% vs 34.8% implied train (-22.6%, n 87, band -1.8%), 22.9% vs 35.3% blind (-40.6%, n 70, band -3.4%), pooled z -2.5, 0 of 8 seasons at break-even, ATS 45.7%. The opponent favorite +7.2% / +14.1% ML. Missed by 21+: ML dead; ATS 54.2% (z 2.2) overlaps the built cover-streak fade - weak lead. 47 cells (~2.4 chance hits).
- **College first conference road game:** dogs ATS 41.0% pooled (z -2.6, 6 of 8 seasons under 50%), ML -13.7% / -27.6% but z -1.5 - LEAD (stay-away), not built alone.
- **NFL heartbreak (lost by 1-3 / OT last game):** they play worse, not better (blind 44.8% vs 50.4%); the fade +4.1% on 426 but z 1.6 and 2025 carries it - WATCH. Lucky winners dead both ways. **Losing-record home favorite vs winning road dog:** DEAD (-3.0% blind, n 30).
- **NHL after a shutout loss / after pitching a shutout:** DEAD (shut-out team -13.4% blind; the shutout team -5.9%). **NHL totals after 8+ / 2-or-fewer goal games:** DEAD - the books price the last scoreline. ~110 cells.
- **The engine's own read by time of season:** NHL October is NOT over-confident blind (slope 0.95; train 0.64 didn't repeat); shrink fits flip sign - DEAD, no early-season shrink. NFL weeks 1-4 calibrated (0.99 / 0.98). LEAD: NFL weeks 14+ the own read is over-confident in both halves (slope 0.82 / 0.72) - the early spots' raw read is the exposure; re-check in December.
- **NFL division stretch (2nd/3rd straight division game; first non-division game after):** DEAD (train and blind flip). **Home dog after a road win:** NFL +6.1% / +12.1% but 2025 carries it (without 2025: -11.0%) - weak LEAD; college +25.5% -> -1.7% DEAD.


## 10/16 - INJURY COVERAGE AUDIT, Saturday 10/17 college + the NFL / NHL weekend (the owner's #1 priority): every team on the slate has box scores, no stale report is read as current, ONE BUILT (the 🚑 line names the players who play first), the rest is the routine's Saturday job

Checked from the repo's files only (the sandbox can't open ESPN / Covers / Rotowire - every one answers 403 through the proxy; the GitHub runner can, and the 10/15 board preview built on the runner showed 0 college teams "not in our data" on a 1-game college night).
- **The slate:** college 107 games 10/17 PT, 50 priced (100 FBS teams); NFL 13 games 10/18-19 (26 teams); NHL 18 games 10/16-18 (16 priced). Box scores (sports_absences.regulars - the QB / 2 backs / 4 catchers / 11 tacklers from the last 3 games) exist for EVERY priced team in all three leagues; the only team without them is West Alabama (D2, unpriced) - so football's weighed-not-blocked rule runs on every priced game, and the hockey 2+ out rule has its "played lately" list.
- **Who covers whom:** NFL / NHL - ESPN's pro feed, read every run (a team missing = nobody hurt; an EMPTY feed = unknown, every game waits - sd.fetch_injuries / covered, pinned by test_empty_pro_injury_feed_is_unknown). College - Covers' page (every FBS school, healthy ones too) + Rotowire + ESPN (~3 teams) every run, plus injuries_official.json (the 5:47 / 11:47 AM PT routine, filed by GAME DAY). A college team on none of them = UNKNOWN = no pick and no early play (sports.waiting_on "X injury report (not in our data)", sports_early covered check).
- **injuries_official.json as of 10/16 10:34 UTC:** 0 of the 100 Saturday teams have a 10/17 entry (the routine fills them Saturday morning - by design); 61 of the 100 carry LAST Saturday's (10/9-10/10) list; 7 Friday-game teams carry 10/16 entries (Memphis 0 listed, Tulane 4, Washington 5 incl. QB D. Williams Jr. questionable, Purdue 1, App State 2 incl. QB M. Singleton out, Coastal 4, Penn 1). The owner's 12: BYU (10/9 entry - 4 players, from its Friday 10/9 game), Air Force (10/10, 2), Tennessee (10/10, 10), Georgia Tech (10/10, 8), E Michigan (10/10, 13) - all stale for 10/17; Boston College, Rutgers, FAU, Wisconsin, West Virginia, Rice - never in the file; Old Dominion - a 10/15 entry (3 players) for Thursday's game (ODU is NOT on Saturday's slate; its early play was pulled 10/14).
- **Stale reports are NOT treated as current (checked):** sd.official reads only the day before / the day / the day after (Pacific), so a 10/10 list never says who's out on 10/17 - pinned by test_official_reports_are_read_for_their_game_day_only_and_covers_names_land. The day-before window is harmless in football (one game a week); it would be stale for a hockey / hoops team on a back-to-back IF the routine ever files pro entries (it doesn't - ESPN covers the pros). LEAD, not built: skip a day-before official entry when our games say that team already played that day.
- **Name matching (checked):** all 19 Covers school slugs the routine has cited (Appalachian State, Florida International, Jacksonville State, Middle Tennessee, Georgia Southern, Western Kentucky, Sam Houston...) land on their own ESPN id through sd._wn / WEB_ALIAS / _DIR / _close - 19 of 19; the owner's 12 schools plus their look-alikes (Tennessee / Tennessee Tech / Tennessee State, Georgia Tech / Georgia Southern, Eastern / Central / Western Michigan / Michigan / Michigan State) all land right in the new test. Official-report short names ('D. Williams Jr.', 'C. Warren III') match the box-score regulars (sports_absences.match).
- **BUILT - the 🚑 line and the card's 'outs' name the players who PLAY first (sports.who_plays_first):** the card named the first four rows the report listed. The 10/10 Minnesota Lock's 🚑 line led with "QB Michael Merdinger" (the backup - Drake Lindsey starts; key_seen rightly showed no starter out), Illinois 10/10 "out: RB Valentine, WR Perry, LB Paris, DL Smith +5 more" with no way to tell whether the five were starters. Now: box-score regulars first (the QB / goalie ahead), the rest in the report's order, nothing dropped; a team with no box scores keeps the report's order (QBs first). Test: test_injury_line_names_the_players_who_play_first. Not a rule change - the card already named who's out; it names the right ones first.
- **What's needed to close the gaps (no paid APIs, no keys, no disguises):** (1) the routine's Saturday 5:47 / 11:47 runs - the SEC / ACC / Big Ten / Big 12 availability reports for the 10/17 conference games (Alabama-Tennessee, Missouri-Ole Miss, Georgia Tech-Virginia Tech, Kentucky-Oklahoma, Notre Dame-BYU is non-conference: Covers only) into injuries_official.json under "2026-10-17"; (2) Actions -> injury_report on Saturday morning to read "NCAAF - the feed lists N teams" (N should be ~130+ with Covers; under 20 = the page read broke and the file is the only coverage); (3) the MAC posts game-day reports ~3h before kickoff (E Michigan, Air Force's opponent UNLV is Mountain West - no official report, Covers only) - the 11:47 run catches the noon-ET ones only if it runs; (4) a Covers snapshot on the runner (tools/fetch_pages.py, URL already in WHOLE) so the reader can be tested against the real page each week - the only Covers samples in the repo predate the reader (samples-2026093*).
## 10/16 - RECALIBRATING THE COLLEGE OWN READ (the root of the BYU 48% / market 24%): the read is NOT overconfident on its own - it is calibrated but blind to what the market knows; every honest recalibration = the market (trust 0). Nothing to wire in; OWNER'S CALL stands. Verdict: LEAD / owner's call, not built

- **Where the read comes from:** sports_model.own_p - a logistic on Elo edge + form + rest + injuries + travel etc.
  (sports_model.FEATURES), refit daily. The DAILY BOARD never shows it raw: sports.candidates uses sm.final_p, the
  market moved toward the own read by the tune's "trust" (college: 0.0 today), so the board's college read is the
  no-vig line. The EARLY SPOTS use the raw own read (sports_early.own_of -> sm.own_p, Tuesday-known inputs), capped at
  5 points over the price since 10/15 (NCAAF_GAP_MAX). That raw read is what said BYU 48%.
- **Walk-forward:** every July 1 the params (K, home edge, weights, trust) re-tuned on the games before it, the
  season's reads from the ratings as they stood (sm.replay) - 6,009 priced college games 2018-26; fits on 2018-22
  (3,325), graded blind 2023-26 (2,684). Four recalibrations fit on 2018-22: shrink toward the market
  (logit p = logit(mkt) + a·(logit(own) - logit(mkt))), shrink + the market's own favorite bias, temperature (c + d·logit(own)),
  isotonic (30 steps).
- **The fits:** shrink a = 0.000 (Tuesday-known read: -0.008) - the market wants NONE of the own read; temperature
  c = -0.017, d = 0.930 (a near no-op); shrink + bias a = 0.027, b = 0.058.
- **Calibration table, blind (the raw read by its own bucket, every side):** said 24.9 won 23.8 · said 35.1 won 35.0 ·
  said 45.1 won 47.7 · said 54.9 won 52.3 · said 64.9 won 65.0 · said 75.1 won 76.2 · said 84.7 won 84.9. Biggest miss
  2.6 points. The read IS calibrated unconditionally - it just doesn't know what the market knows. Conditional on
  disagreeing, the market is right (blind, the side the read likes more, by the gap): 0-2 pts won 56.5 (+7.8%, 345);
  2-5 won 50.8 (read 51.8, market 48.4, -0.4%, 492); 5-10 won 39.4 (read 49.0, market 41.7, -26.7%, 624); 10-15 won
  38.9 (50.4 / 38.0, -8.8%); 15-20 won 31.0 (49.1 / 31.8, -24.0%); 20-25 won 32.4 (54.1 / 31.7, -11.0%); 25+ won 24.0
  (57.0 / 23.9, -19.9%, 292). Temperature and isotonic leave every one of those buckets where it was (they move a 48%
  read to 47.7% / 51.4%): a calibration of the read ALONE cannot fix it - only the market can.
- **Brier / log loss, blind (home side):** market 0.1649 / 0.4929; raw own 0.1885 / 0.5572; shrink (a=0) = the
  market; shrink + bias 0.1648 / 0.4922; temperature 0.1886 / 0.5575; isotonic 0.1894 / 0.5603. The market beats the
  raw read in EVERY season 2018-26 (2023 0.4699 vs 0.5425, 2024 0.5123 vs 0.5697, 2025 0.5006 vs 0.5389, 2026 0.4889
  vs 0.5916). Grid of a: the best is 0.0 in train and blind; a = 0.10 costs 0.001-0.003 of log loss in 6 of 9 seasons
  and gains ≤ 0.002 in three (2018 / 2021 / 2025) - noise around zero.
- **Blind ROI at the close, the sides whose recalibrated read beats the price:** dogs +100..+300 - every side -2.3%
  (1,364); raw read -0.4% (702, by season -7 / +3 / +9 / -9%); temperature +0.7% (737); isotonic +0.4% (680); shrink:
  NO side ever beats the price (a = 0). Favorites -150..-101 - every side -7.1% (529); raw -0.4% (234); temperature
  +1.7% (217); isotonic +0.3% (235) - but 2024 -12..-14% and 2026 -8..-13% on each, and the same rule lost -13.8% /
  -14.3% / -15.4% IN-SAMPLE 2018-22: 2 of 4 blind seasons up, in-sample red = chance, not an edge. The owner's
  middle-ground trusts (Tuesday read): a = 0.1 dogs 89-172 -5.3% / favorites 21-14 +7.8% (35); a = 0.2 dogs -7.0%
  (452) / favorites +7.2% (101); a = 0.3 dogs -3.6% (550) / favorites +1.7% (158); the sides a shrunk read likes 1-5
  points more than the market lose -8% to -24% at every a. Nothing clears the five checks.
- **Against the open (opens exist only 2023-26, so in-sample):** shrink toward the open a = 0.058; a read 10+ points
  over the open does see the close move its way (+1.4 pts; 10+ under: -1.7) - the read holds a little the OPEN
  misses, but the CLOSE already holds it (log loss open 0.5033, close 0.4929, read 0.5572). That is the "hammered"
  spot's honest form, already built.
- **The BYU example:** ratings ND 1881 / BYU 1828 (5th / 9th) + home edge 100 = 57% raw Elo, the weights pull it to
  48%; the market 24%. Shrink (a=0) says 24%; temperature 47.7%; isotonic 51.4%. Blind, a 20-25 point college gap won
  32.4% (the market said 31.7%) - the read's number had no claim on it.
- **Verdict:** NOT BUILT - no code changed. The only recalibration that is clearly better (shrink, a = 0) is the market
  itself: wired into the early spots it zeroes the college gap weight and ends the "engine likes it" college spot and
  every college gap-driven early play - that changes what gets posted, so it stays the OWNER'S CALL (10/15, call 1).
  The 5-point cap (NCAAF_GAP_MAX) STAYS: with the raw read still feeding the spots, 5 is the most any blind bucket
  earned (2-5: -0.4%); with a = 0 it would be moot, not wrong. Temperature / isotonic: DEAD (no-ops).
- **PROPOSAL for the owner (numbers above):** (1) college early spots weigh the read at the tune's trust (a = 0 today):
  the college gap counts 0, the spots stand on their own weights and fades (bye / blowout / hammered / east-west) -
  BYU +300 and Old Dominion +145 would not have posted; the "engine" spot (own 8+ over a line that moved away) goes
  dormant until a read earns trust > 0. (2) Or keep today's 5-point cap and judge the live record (the 10/10 +220..+300
  band is new ground anyway). LEAD, the real fix: the read needs information the market lacks, not a better curve -
  the FCS marker (10/15 lead), QB availability, the official injury reports - each one is a feature the tune can
  then trust by itself.
## 10/16 - THE UNIT PLAYS BY SIZE (live: 2u+ 5-0 +16.7u, 1-2u 5-11 -4.7u, under 1u 21-16 +2.1u): the 1-2u bucket IS the Dog of the Day and its live record is noise; the replay says the real sizing problem is the LOCK's Kelly size (the biggest Locks lose) and a Dog whose own read sits under the price (owner's calls); one data fix built
The live ledger (sports.units_ledger over picks.json + early.json, 58 graded unit plays 9/27-10/15). The 16 plays at
1-2u: 13 Dogs of the Day (10 hockey, 2 NFL, 1 college - 5-8, -1.7u), the Guardians -149 Lock at 1u (own edge 3.1% - just
over THIN_EDGE, Kelly 1.17 -> 1u; lost), Western KY +110 1u (10/1, before the ½u play rule; lost), the Tulane +205 bye
early play at 1u (lost). Not one of the 16 got its size from a big edge - the Dog is a FLAT size (NHL 1u by rule; the 10/10
1u-2u-by-edge rule has sized one non-hockey Dog so far, Fresno St +250 at the 1u floor), so "why does 1-2u lose" =
"why do the Dogs lose". 8 of the 10 live hockey Dogs were the best-hockey-dog fallback (score 1-5 - backed out of dog_p,
the posted leg had no score; the fix below), 2 the 6+ gate (Flyers 6.2, Sharks 5.9->6); 7 of 13 Dogs had the engine's
OWN read under the price (fighting() allows 3 points) and went 4-3; the 6 with the own read over the price went 1-5.
**The replay (tools/sizing_by_bucket.py on results/value_play_replay_2023_26.jsonl - the 10/9 board replay, 2,270 rows,
re-sized under TODAY's rules: Lock by own read ½u-10u, Dog 1u-2u by edge / NHL 1u / hoops ½u, plays ½u; 2023-24 vs
blind 2025-26):**
- By bucket at its size: **under 1u** 884-719 +6.9u on 802u (+0.9%; blind +3.5%); **1-2u** 197-184 +41.7u on 417u
  (**+10.0%; blind +8.7%**, 3 of 5 seasons) - the Dog at 1u +8.6% (289) and hockey Dogs +10.0% on 297 (blind +11.2%);
  **2u+** 148-127 **-59.9u on 869u (-6.9%; blind -2.1%)**, 1 of 5 seasons up - 257 of the 275 are Locks. The same bets
  flat 1u: under 1u +0.9%, 1-2u +10.2%, 2u+ -4.9% (blind -5.3%, 0 of 3). So live is the mirror image of the record:
  the bucket that wins in the replay lost live (13 Dogs, 5-8 - expected ~6 wins at these prices, well inside noise) and
  the bucket that loses in the replay went 5-0 live (3 Locks at 2.5-5u + the two 3u Brewers early plays). VERDICT on
  the question: 16-game NOISE on the Dogs, not a sizing bug - and the replay points at two real things instead:
- **THE LOCK'S SIZE (a sizing problem, the owner's call):** the Lock flat 1u wins +18.4u (+2.7%, blind +3.6%); sized by
  its own read (today) it LOSES -28.7u (-2.6%; blind +0.7%) because the big-edge Locks are the worst ones: Locks sized
  under 1u (thin, ½u) +4.1% flat / blind +8.9% (3 of 3); 1-2u +15.9% / +4.0%; 2u+ -3.7% / -3.7% (0 of 3 blind); 5u+
  17-17 -12.8%. By own edge over the price: under 3% +4.3% (265, 4 of 5), 3-8% +5.4% (261), 8-15% +1.3% (116), 15%+
  14-19 -9.1% (0-6 at 25%+). Calibration: own read 60-65% won 64% (the market said 59%); 65%+ won 59.5% (market 58%) -
  past 65% the read is no better than the price, and that is exactly where Kelly puts 3-10u. Same as 10/2 ("favorites
  8%+ -4.3%") and 10/9 ("edge size says nothing") - now on the Lock itself. Options on the same 675 Locks: flat 1u
  +18.4u; ½u thin / 1u otherwise +11.8u on 512u (+2.3%, 3 of 5); capped 2u +4.1u; capped 3u -3.7u; today -28.7u. Per
  season today vs flat: 2022-23 -42.7u vs -2.3u, 2023-24 +8.5 vs +6.7, 2024-25 +3.1 vs +8.7, 2025-26 +16.3 vs +9.1,
  2026-27 (3 months) -13.9 vs -3.8. Whole board (plays ½u): today's rules -11.4u on 2,088u (blind +13.3u); Lock flat
  1u + Dog flat 1u +38.8u on 1,622u (+2.4%; blind +22.1u); Lock ½u-thin/1u + Dog flat +32.2u (blind +15.5u). The owner
  chose "Locks keep sizing by edge" on 10/10 - PROPOSAL, not built: the Lock flat 1u (or ½u thin / 1u), the live 2u+
  Locks 3-0 (+9u) are luck by these numbers. Caveats: the 10/2 snapshot had the Lock by read beating flat (-3.2% vs
  -6.0%) - the Lock test changed since (own_agrees, the money check); only the model params are blind; 37 of 675 are
  backup Locks (½u here).
- **THE DOG WHOSE OWN READ SITS UNDER THE PRICE (a pick problem, the owner's call):** fighting() lets a Dog through with
  the engine's own read up to 3 points under the price (the dog score carries it over). Those Dogs: 54-79, **-7.4% on
  133 (blind -11.6% on 38, 0 of 2)**, 1 of 4 seasons up; the Dogs whose own read ALSO beats the price 124-130 **+11.7%
  on 254 (blind +8.7% on 112)** - hockey +21.2% on 153 (3 of 3 seasons) vs -8.9% on 123. Same dogs, own-below at ½u:
  +16.9u -> +22.6u (blind +5.5u -> +8.2u); own-below dropped and the rest flat 1u: +29.8u on 214u (+13.9%; blind
  +12.0u, +11.6%). Live the 7 own-below Dogs went 4-3 (noise both ways at 13). It changes what gets posted (the Dog's
  side of the owner's "never one the engine's own read is fighting") - PROPOSAL: the Dog of the Day only when the own
  read beats the price too (or ½u when it doesn't). ~8 Dog cells tried; this one has the mechanism the owner wrote down.
- Dog sizing (the 10/10 1u-2u rule vs flat): on the same 387 Dogs flat 1u +20.0u (+5.8%, 3 of 5) vs by edge +16.9u
  (+4.6%) - the 18 Dogs the edge sizes 2u went 6-12, -22.6% (blind 5-9). The 10/2 finding again (flat best); too few 2u
  Dogs to call, the owner's call stands - WATCH the 2u Dogs live. Dog by score: hockey 4-6 -15.1% on 88 (blind -13.1%,
  0 of 2 - under the NHL 6 gate, so these are fallback best-hockey-dogs), 6-8 +1.1%, 8-12 +22.1% (3 of 3); the score
  0-4 fallback 26-20 +36.7% on 46 (noise-sized). Price: +120..+150 +28.2% on 133 (4 of 5) vs +100..+120 -6.1% and
  +150..+200 -8.6% - a LEAD at most (multiple testing). College hoops Dogs -0.4% / blind -26.8% (the 10/10 verdict).
- **BUILT (sports.dog_gate / best_hockey_dog + test_sizing_audit_10_16_...):** the posted Dog's leg now keeps
  "dog_score" (the points its units rode on) next to dog_p - data completeness, no pick or size changes. Kept:
  tools/sizing_by_bucket.py (re-run after the football season: `python tools/sizing_by_bucket.py <replay.jsonl>`).
- Early plays: not in the replay (no line history before 9/2026); live 2u+ = the two Brewers 3u (own-read Kelly, both
  won), 1u = Tulane (bye spot, flat 1u by rule), ½u = the spots 3-7. Nothing to size there yet.
## 10/16 - COLLEGE QB FORM COUNTED FCS GAMES AT FULL WEIGHT (the Sam Houston case): BUILT - FBS games only; the opponent-strength adjust DEAD
- The case: the 10/14 Sam Houston +100 lean said "our QB's been playing better" off Landyn Locke's 322 yards / 4 TD
  against FCS Nicholls (59-0); his FBS games were 316 / 195 / 138 yards, Sam Houston lost 3-16 and hadn't scored in six
  quarters. sports_players.score took every start at full weight and the game files carry no FBS / FCS marker.
- FBS membership from the games themselves (sports_players.fbs_members / fbs_set, walk-forward: finished games before
  the month only): last season's set is sticky, this season's newcomers join once they have 8+ games whose opponents
  are mostly FBS; the first priced season (2018) seeds on the many-game teams priced in 75%+ of their games. Checked
  against the real lists: 130 teams 2018-21, 131 in 2022 (+James Madison), 133 in 2023 (+Sam Houston, Jax State),
  134 in 2024 (+Kennesaw St), 136 in 2025 (+Delaware, Missouri St) - every change the real one; Nicholls, N Dakota St,
  Idaho (dropped 2018) out. A plain price test can't do it: Delaware's CAA games were priced 11 of 13 in 2022, FIU's
  C-USA games 0 of 12 in 2024. A new FBS member reads as FCS in its first season until it has 8 games (1-2 teams a year).
- THE STUDY (4,234 priced college games 2021-26, each season graded with a weight fit on the seasons before it; the
  edge added on top of the closing line's logit): the QB edge adds almost nothing the market lacks either way -
  log loss 0.4929 (market) -> 0.4922 with every game (+7.0 bp), 0.4924 FBS only (+5.1 bp), 0.4927 FBS only + an
  opponent pass-defense adjust (+2.7 bp). Not hurt, not helped - the read's accuracy is the same.
- THE WRITE-UP LINE ('better QB play lately' = an edge of 0.4+ units): with every game 2,342 sides won 65.6% vs the
  market's 64.1%; FBS only 2,135 sides won 67.0% vs 65.3% (+1.7 points over the market, up every season 2023-26:
  68.1 / 66.5, 66.5 / 64.7, 67.5 / 64.2, 69.4 / 66.8). The 723 labels (2018-26) that stood on an FCS game went 59.2%
  against a market expecting 59.8%, ROI -5.1% at the close - noise; the labels that stand without one beat the market
  by about 2 points in all nine seasons (2021: 66.8 vs 64.2 ... 2025: 67.9 vs 65.1). The opponent adjust cut the labels
  to 1,993 at 67.1 vs 65.8 - no better than dropping FCS games: DEAD, not built.
- BUILT (sports_players.fbs_only, in key_edges and form_line; the breakdowns pass the game files): a college QB's form
  is his starts against FBS teams; the card's numbers drop the FCS game and say "in his last 3 games against FBS teams".
  Sam Houston-Western KY 10/14: the edge 1.09 -> 0.69 (Locke 316 / 195 / 138 still read better than Brock Glenn's
  435 yards and 2 picks over 3 games - the label would still have printed, at a smaller weight). This season 240 of
  488 college 'better QB' labels drop and 18 flip once FCS games are out. Test:
  test_college_qb_form_skips_fcs_games_the_sam_houston_case. The key weight refits daily (model.json ncaaf 0.315).
- THE SAME FCS INFLATION ELSEWHERE (report only - rule-level, the owner's call): (1) the Elo ratings and the
  'form' feature count a win over an FCS team (rated 1500 on its first game) like a win over an average FBS team;
  (2) the letdown flag (21+ win) and the ⏸️ paused 'blew somebody out' early spot (17+): 104 of 250 FBS blowout wins
  this season and 108 of 460 in 2025 came against FCS teams - the spot's study counted them, so its +8 / +9% edge
  includes them; (3) the breakdown's streaks ("won 4 straight") count FCS wins - true facts, left alone. LEAD: re-run
  the blowout spot FBS-only before it is ever unpaused.
## 10/16 - BUG SWEEP of the board-building path (sports.py candidates / read_of / weigh_favorites / dog_score / plays / viewer_leans / lock + backup_lock / units_for + units_ledger / rule_check / dedupe_picks; sports_early post / spot_gap / repost_ok / euro_unders; sports_live never_against_us / paused; grading; the dashboard records) - read rule by rule against CLAUDE.md, every suspect reproduced before a fix. Posted picks untouched.

- **BUILT (fix + test_backup_lock_needs_the_weighed_read_to_beat_the_price): the backup Lock vs the weighed read.** sports.backup_lock passed a favorite on its bare own read (56%+, edge_own > 0) while its units ride on the WEIGHED read (read_of -> w_p, the favorite's read moved by the dog across it, weigh_favorites). Reproduced: a -130 favorite, own read 60%, weighed 55% (the price needs 56.5%) was the backup Lock -> units_for gave ½u -> rule_check pulled it ("units on a price its read doesn't beat") -> NO Lock that day, while the next favorite (own 58%, nothing weighing on it) qualified. backup_lock now needs real_value() too (the same test the main Lock path uses). Picks: 0 affected (the 12 posted Locks checked).
- **BUILT (fix + test_dedupe_drops_the_stale_play_copy_of_an_upgraded_dog): the mirror of the 10/13 Kraken bug.** drop_stale_dogs dropped the stale old Dog next to its was_dog play copy, but not the stale PLAY copy of the play upgrade_dog made the Dog (the saves merge by git rebase -X theirs, hunk by hunk). Reproduced: the same team showed twice (play ½u AND Dog) and units_ledger counted it ONCE AT ½u - the Dog's units (1u-2u) lost from the record. A play (not was_dog) on the same day + game + side as a Dog marked upgraded is now the stale copy and goes. Picks: 0 affected today (no day holds two unit rows on one game).
- **BUILT (fix + test_study_index_cache_holds_the_games_dict): the study-index cache keyed by id(games) + count.** sports._index (context / spots / explorer) could hand a NEW games dict the OLD index when it landed on a freed dict's address with the same game count - the live watcher reloads games every quick pass (the same bug _sched had on 10/1). It now holds the dict itself.
- **CLEAN (checked, nothing wrong):** candidates' sign on absences / depth (the banged-up side's own read goes DOWN), the drift sign (+ = money ran away), dog_score's OWN_CAP / STUDY_CAP, weigh_favorites' one-factor-once (west trip), rule_check's -150 / puck line / one-pick-per-game / Dog cap / moneyline-only play / money check, units_ledger's one-row-per-pick + early rows counting apart (the owner's "Jaguars can be both"), day_pending / day_recap (PT dates, every unit play graded first), unit_record / by-sport = unit plays only, the 🟡 leans record, sports_early.post's have / repost_ok 12h / euro_unders' night-before window and quit rule, spot_gap's college 5-pt cap and the NFL / NBA trap, sports_live.never_against_us + locked_sides (board, early, live, tennis; the 🌍 under takes no side), grade_from_games, the live PAUSED set (MLB), grade / grade_leg / freeze_units (void after 4 days, units frozen). Real picks.json (87 picks): no day with two Locks / Dogs, no game with two unit rows, no both-sides pick, no lean with units.
- **LEAD / the owner's call (not changed - unit sizes):** a 🏈 night pick or a one-game-day pick that is a VALUE DOG sizes by quarter-Kelly on the dog's weighed read up to 2u (units_for -> _sized("value"), DOG_SCORE_MAX_U), while the same dog as a daily value play is ½u (PLAY_UNITS - "they lost at every size"). Example: a +120 night dog with dog_p 50% = 2u as the night pick, ½u as a play. The sizing check accepts ½u-10u for night / solo. Proposal: night / solo value dogs at PLAY_UNITS unless the owner wants the night pick sized on its own.
- **SUSPECTED, not reproducible from the repo (listed, not fixed):** (1) two engine runs at once posting two DIFFERENT Dogs (the 9/30 incident was the same Dog twice - dedupe_picks catches that one; different legs = both stay and both count); (2) sports_early.spot_scan's 3-day window runs from ready() (both teams' last game + 4h), not from the first fair number's time stamp - a college line that comes out Sunday has ~2 days, not 3; (3) ready() is None for both teams' season openers = no 3-day window at all on week 1; (4) sports_early.record() sums units as 1u a play (ignores units(p)) - dead code, used only by two tests; (5) _TOT_STATE keyed by id(games) (totals are unproven, never posted).
## 10/16 - HOW THE LEANS ARE PICKED, round 2 (the 🟡 record 17-21; the goal: leans that WIN more often, not ROI): no rule wins more often than the current one except by picking pricier favorites - DEAD, nothing built
Blind board replay 2023-01 to 2026-10-14 (tools/value_play_replay.Replay re-built every other board day the way the 8:35 AM post would - params re-tuned every July on the seasons before, the day's ratings / form / dog states from the games before it, closing prices; 687 board days, every lean-eligible side dumped with its reads; scratchpad leans2/lean_replay.py + analyze.py). Each rule picks the day's leans the board's way: one side a game, 2 a sport, into the day's room (5 minus the unit plays), never a game we're on, never past -150, never a trap / the pricey hockey favorite / a college favorite -150..-130. "Market-expected" = the no-vig win % of the sides a rule picked - what the price alone says they should hit.
- TODAY'S RULE (who-wins: p 50%+ or an underpriced dog, importance first): 856-767, 52.7% hit vs 53.5% market-expected (-0.7). By year 54.9 / 48.4 / 53.3 / 55.5 (2024 the bad one, every rule's). Its spread leans 189-151, 55.6% vs 52.3% (+3.3 on 340 - the one piece that beats its price); its moneyline leans 667-616, 52.0% vs 53.8%; its dogs 30-32 (48.4% vs 40.7% expected); the FILL leans (the likeliest winner after the regular leans) 21-21 vs 55.7% expected blind, 1-7 live - the fill is the owner's five-picks rule, not changed.
- THE MARKET FAVORITE (the biggest favorite under -150 - "any moron could do that"): 780-648, 54.6% vs 55.0% expected (-0.4), avg -135. It hits 1.9 points more often than today's rule ONLY because it picks pricier sides; against its own price it is no better. 3 of 4 years above today's rule, all within what the price buys.
- THE ENGINE'S OWN MOST-CONFIDENT SIDE (own read, no line move): 772-669, 53.6% vs 54.4% (-0.8). The honest read p (market + ratings): 777-660, 54.1% vs 54.4% (-0.3). The blend (market + own)/2: 744-642, 53.7% vs 55.0% (-1.4).
- MARKET AND ENGINE AGREE (both 50%+, not fighting), importance first: 633-561, 53.0% vs 54.2% (-1.1); ranked by p alone 52.3% (-2.0); ranked by the blend 52.8% (-1.4); own read AT OR OVER the market: 526-485, 52.0% (-1.5), NFL 14-25. Skipping the games the engine and market disagree on does not win more - it loses the spread leans and the dogs that do beat their price. Today's rule with the spreads dropped: 51.8% (-1.5).
- Verdict: DEAD. Ten rules, none beats its market-expected hit rate by more than noise (best +0.0 to -0.4; SE ~1.3 points on 1,400 leans); the only way to raise the straight-up hit rate is to pick bigger favorites, which the price already says and the owner does not want. Today's rule is the one that keeps the spread leans and dogs that run above their price; it stays. For the viewers: a 53% lean hit rate IS what these prices say (avg -117); the live 17-21 (44.7%, SE 8 points) is noise around it, not a broken picker.
- Not touched: viewer_leans (format, count, no units, the per-sport cap, the importance order, LEAN_NCAAF_FAV_BAND). PROPOSAL for the owner (not built - it changes what gets posted): if he wants leans that hit more often, the honest lever is the price - leans from favorites -120..-150 by the engine's p would hit ~55% blind (the market favorite rule above) at the cost of the dogs and spreads; or a 'no fill lean' day stays at 3-4 picks. His call.
## 10/16 - WRITE-UP TRUTH AUDIT, 10/8-10/16 (the owner: "never false information - that will cost us money"; "never vague"): 36 cards (~230 lines), 16 early plays, 46 graded reviews checked against the game files, box scores and line history as of post time - 17 false, 5 vague, 8 generator fixes BUILT

Every factual claim on the cards posted 10/8-10/16 (picks.json breakdown / why lines, early.json why) and every graded
review on the dashboard, checked against what the repo held when it was posted (games csv, players box scores,
line_history, deciders) - no look-ahead. Public-betting splits (30 lines) and the 🚑 names (22 lines) can't be checked
back in time (no stored snapshots) and are left out of the tally.
- Checked ~190 claims: records / home-road records / streaks / last games (~95: all true but 3), back-to-backs (6: 5
  true), line moves - open -> now against line_history's first fair price after both teams' last games (24 of 24 true,
  the Bucs' "+455 at the open" included), QB / goalie / pitcher numbers (9 of 9 right: Milivojevic 434 yds 0 TD 3 INT,
  Brock Glenn 435 / 2 / 2, Misiorowski 2 runs in 12 IP 15 K, Askarov 12 on 88, Dobes 13 on 91, Dostal 8 on 64, Ellis,
  Schmid), early plays' last-game scores and byes (7 of 7), travel miles (3 of 3), review half-time / period facts (36
  of 37).
- FALSE (17): 4 revenge lines on 2023-or-older meetings and the Western KY schedule line, the Golden Knights "short rest"
  (46 hours), the Blue Jackets "on the record. That's just facts" - all 9 fixed on 10/15 (not redone); NEW: "The Sabres
  dealing with some personal stuff: 'Blackhawks' Bowen Byram to miss Buffalo return'" (10/10 AND 10/12 - a Blackhawk's
  news ESPN tagged on the Sabres); "Records are close (Guardians 85-77, Rays 98-64)" (13 wins apart); "we're on the
  Titans, they're the hotter team" (0-4, four straight L's); "The Sharks' goalie Yaroslav Askarov ..." / "The
  Canadiens' goalie Jakub Dobes" / "The Ducks' goalie Lukas Dostal" (right numbers, wrong goalie - Nedeljkovic, Fowler
  and Husso started; the starter wasn't known at 8 AM); "Wild questionable: Bogosian, Foligno" + "Wild have everybody
  available" on one card (the Canadiens' card too); the Canadiens review "tied 3-3 after two periods; Capitals won 5-4"
  on a game graded 5-3 (the stored period line added to 5-4).
- VAGUE (5): "Say what you want, Freddy Peralta is HIM. He lives for spots like this." (no fact); "The Broncos in the
  papers: '15 NFL players, coaches on the hot seat entering Week 6'" and "Out of the Seahawks's camp: 'Seven things
  Solak thinks entering NFL Week 6'" (league round-ups pinned on a team); "The Saints never had a chance. Saints led 7-6
  at the half" (a review that contradicts its own fact); "we're on the Bills, they're the hotter team" (Bills off a loss).
- BUILT (8 fixes, each with a test in sports_test.py, test_truth_audit_10_16_*): (1) sports_breakdown_v24.someone_elses_story
  - a drama headline naming another team of the league and not ours is skipped; a 📣 camp-talk line needs the team's
  name in the headline; (2) the ✅ healthy line never prints with anyone questionable (team_unsure); (3) close_records -
  "same kind of record" needs a small win gap too (2 wins early, ~3% of the games later); (4) sports_dashboard.periods
  refuses a period line that doesn't add up to the graded final (no half-time fact, no comeback / collapse read from it);
  (5) sports_lingo.review(trailed=True) bans the "never had a chance / never close / going away" talk on a win where the
  other side led or it was tied at the checkpoint (DOMINANT_BAN); (6) the 🥅 / 🧱 goalie line says "who had their net
  last time out" / "if he gets the net again" until sports_goalies confirms a starter (goalie_known); (7) the 💸 fade
  line's "they're the hotter team" needs a winning streak on our side and none on theirs; (8) the ⚾ hype line for the
  better arm carries his last starts' numbers (a hot arm's 🔥 line already has them), else the plain matchup line.
- Not fixable from here (noted): "Full squad for the Maple Leafs" (10/15) and "Blues have everybody available" (10/8)
  sat next to a 3-name hurt list - the card text is built at 8 AM and the hurt list is refreshed every hour; the
  injury feed isn't stored back in time, so which one was right can't be checked. The posted picks were not touched.
## 10/16 - NHL CHECKUP: a walk-forward replay of TODAY's hockey engine (Lock / Dog / plays / leans) 2023-27, every weight graded on its own; the live picks audited. ONE FIX (the card's goalie line), TWO PROPOSALS, the weights stay
The machinery: scratchpad nhl_replay.py on top of tools/value_play_replay.Replay - NHL games only, every board day 2023-10-10 ..
2026-10-15 rebuilt as the 8:35 AM PT post would have built it (closing prices, later games gone, params re-tuned each July 1 on
the seasons before, no injury reports, no Daily Faceoff page / public splits in history so the goalie-roles (+2) and sharp-dog (+1)
weights never fire - same caveats as the 10/9 replay). 681 board days, 8,436 moneyline SIDES (every side on the slate, picked or
not), each with the kind the board gave it and every dog-score / favorite weight that fired. Flat 1u. "pts" = win % minus the
no-vig price (the same-price baseline is built in); the plain baseline is every NHL dog -4.2% / every favorite -4.8% (the vig).
- **PICK KINDS (at the close, 1u):** Lock 137-87 +6.7% on 224 (3 of 3 seasons up: +3 / +3 / +9u; thin own edge <3% +10.1% on 138,
  own edge 3%+ +1.3% on 86 - the 10/9 finding again). Dog 126-138 +8.8% on 264 (+12 / -6 / +15 / +3u): via the SCORE GATE 6+
  75-71 +17.3% on 146 (pts +9.3, z 1.8; 3 of 4 up), via best_hockey_dog (score 0-6) 51-67 -1.6% on 118 (pts +1.8, z -0.1, 2 of 4
  up) - the gate earns its keep, the "best dog over 0" fill is break-even at the close (live 'hockey dog score 0-6' 7-16 is the
  same thing at the 8 AM price). Value plays 51-35 +7.8% on 86 (favorites +9.7% on 76, dogs 4-6; rank 1 +15.7%, rank 2+ -12.7% on
  24 - noise-sized). Regular leans 299-288 +0.5%; FILL leans 112-115 -14.3% on 227 (z -2.5, 4 of 4 seasons down).
- **DOG WEIGHTS - with the weight vs every other dog +100..+300, 2023-27 (z on ROI):** every one points the way the engine
  weighs it. Shot share: ss_pos (+3) +8.0% on 900 vs -6.9% (z +2.0); ss_neg (-3) -10.1% on 1,639 vs +2.8% (z -3.4). Both lost
  last (+3.5) +7.5% on 855 vs -6.5% (z +1.8). Puck luck: pdo_bad (+2) +3.0% on 1,139 vs -6.0%; pdo_good (-3) -8.0% on 832 vs
  -1.7% (z -2.0). Money: drift_away (-4) -7.4% on 1,404 vs -0.4% (z -2.3); drift_in (+2) +5.5% on 571 vs -4.8%. Rest: the dog on
  a back-to-back vs a rested favorite (-3) -12.5% on 533 vs -1.5% (z -2.4); rested vs a tired favorite (+3) -0.9% on 281 vs -3.3%
  (pts +1.8 - the weakest, right sign). Hits top quarter (+2) +3.7% on 891 vs -5.4%. Price +200 and up (-2) -14.9% on 419 vs
  -1.6% (z -2.1). Goalies - with the LAST STARTER as the guess (what the 8 AM board has; right 45% of the time): hot_key (-3)
  -11.2% on 287 vs -2.4%; key_edge_lo (+1) +1.6% on 1,268 vs -5.8%; key_edge_hi (-2) -5.9% on 694 vs -2.5%; facing a slumping
  goalie (-2) -9.2% on 569 vs -2.0% (z -1.8). The 10/8 40-shot weight, these are its blind seasons: outshot_me (-2) -20.6% on 182
  vs -2.2% (z -2.3), the side facing it (+1) +36.2% on 87 vs -4.1% (z +2.9) - the live 0-3 'NHL side vs a team outshot 40+' is
  three games. Fired coach (+1) +2.3% on 309 vs -3.7%. Playoff lost_last (+3): -11.2% on 97 vs -2.9% - the one weight with the
  WRONG sign in 2023-26 (the 9/30 study's "NHL +28.7%" bounce; 97 games, z -1.0: a WATCH, not cut).
- **FAVORITE weights (w_p):** weighed UP (facing a bad dog) -0.9% on 2,161 (pts +2.0) vs weighed DOWN -11.9% on 1,401 (pts -4.6,
  z -5.4) - the live 'hockey fav weighed DOWN (fade)' 22-17 is a small sample of a real thing. w_p beats the price: +2.3% on
  1,113 (pts +4.0); w_p under the price -8.6% on 2,451. third_in_four (+1.5 pts): +2.5% on 257 vs -5.8% (pts +4.2 vs -0.9) - it
  holds blind here (the 10/15 "+0.2% blind" was the dog side's bet); keep. sv_slump (+1.5): -0.8% on 569 vs -6.0% - holds.
  NHL_EARLY_FAV (-3 the first 2 weeks): early favorites -4.7% on 268 vs -5.2% for the rest - NO signal either way (the owner's
  10/1 call; it only costs Locks in October). outshot_fav (-1): -32.4% on 87 - holds.
- **Multiple testing:** ~22 weights x 2 sides = 44 cells; about 2 would show |z| 2 by luck. 10 cells clear |z| 2 and EVERY weight
  but lost_last points its built direction - the dog score as a whole is real on these three seasons (the score >0 dogs +3.0%
  on 797 vs score <=0 -8.6% on 2,223; 6+ +8.9% on 183; 9+ +20.2% on 52).
- **Price bands for the Dog (posted):** +100..+129 +9.0% on 141, +130..+159 +16.6% on 72, +160..+199 +16.1% on 40, +200..+300
  1-10 -70.9% on 11. Every gate-6 dog on the slate at +200..+300: 1-3. The 10/10 +300 limit is new ground here too.
- **Caveat on the own read:** the July tune swings - trust 0.31 (2023) / 0.08 (2024) / 0.00 (2025) / 0.15 (2026), hdog -0.20 /
  -0.03 / +0.31 / 0.00 - so 2024-25 had 17 Dogs (the own read hugged the market) and 2025-26's dogs' "own edge" was mostly the
  home-dog term. The dog WEIGHTS carry the hockey Dog; the own read's edge over the price is tune noise season to season.
- **THE LIVE PICKS (9/27-10/15, 34 hockey picks):** every last-game and back-to-back flag matches the real schedule (0 stale);
  Dogs 4-8 -1.9u at the 8 AM price (11 of 12 were best_hockey_dog score 1-6, one cleared the gate), plays 3-1, leans 7-11; CLV
  about even. The goalie-roles weight never fired at 8 AM (Daily Faceoff confirms later: 2 of 34 picks knew our goalie, 4 knew
  theirs) - a weight that lives after noon. BUG (fixed): the 🥅 / 🧱 goalie form line named the LAST starter as "the Sabres' goalie
  Colten Ellis" (10/12 - Luukkonen played), "the Hurricanes' goalie Brandon Bussi" (10/3 - Kochetkov), Askarov 10/8 (Nedeljkovic),
  Dobes 10/8 (Fowler), Dostal 10/10 (Husso): 5 of 7 lines named a goalie who didn't play. The last starter is tonight's starter
  45.5% of the time (3,930 of 8,628 team-games 2023-26). Now: no confirmed / likely starter = "X, in net last time out for the
  Sabres, ..." (true); known = the plain wording (sports_breakdown_v24, test_nhl_checkup_10_16_unconfirmed_goalie_is_said_as_the_last_starter).
  The weight itself (hot_key / key_edge on the last starter) stays - it earns its keep above even with the guess.
  The 9/30 "No Trent Miner for Avalanche - that's their starting goalie" (a third-stringer on IR) was the 10/2 STARTER_OF fix.
- **PROPOSALS (the owner's calls - they change what gets posted):** (1) NO HOCKEY FILL LEANS: the who-wins fill lean in hockey
  (a favorite the engine has at 50%+, the weighed read allowed under its price) went 112-115 -14.3% on 227, down 4 of 4 seasons,
  -15.9% when the weighed read is under the price and -12.4% when it isn't; the -150..-130 lean favorites -12.5% on 226 (the
  regular leans +3.4%). No units on them, but they are the 🟡 record. (2) the "best hockey dog over 0" fill for the Dog of the
  Day (sports.best_hockey_dog): -1.6% on 118 at the close, live 'hockey dog score 0-6' 7-16 -6.4u at the 8 AM price - keep it
  (the owner wants a Dog) or raise NHL_BEST_DOG_MIN to 3 (score 3-6 dogs +3.8% on 503 vs 0-3 +4.8% - no real split; the gate-6
  Dog is the money). Nothing changed on either.
- Verdict: BUILT (the goalie line fix); the weights all LEAD-confirmed on 2023-27 except lost_last (WATCH) and NHL_EARLY_FAV (no
  signal, the owner's rule); fill leans in hockey = PROPOSAL.
## 10/16 - THE MLB OWN READ vs THE PRICE (the "~4 points optimistic" note of 10/15): CONFIRMED for the raw read the early exam / early scan use (+4.2 pts blind, every season), +1.1 for the board's read; the fitted fix is "trust the read 8%" = the market - it would have posted NONE of this month's MLB unit plays (live +7.1u). LEAD / OWNER'S CALL, nothing built

tools/mlb_read_calibration_study.py -> results/mlb_read_calibration_study.json. 20,085 priced, decided MLB games 2018-26 (358
postseason), every read WALK-FORWARD: params tuned on the games before each 3/1 and 7/1 cutoff only (18 tunes), the starter
edge prior-starts-only; blind = 2023-26 (9,869 games). Two reads live in the engine and both were measured:
RAW = sports_model.own_p (ratings + form + the starter's form, no line) - the early-price exam and the early scan use it,
tuned on the last 3 seasons; BOARD = final_p with move_w 0 (the market moved toward the raw read by the tune's trust +
its favorite / home-dog shifts) - what sports.run calls ph_own: own_agrees, the Lock test and every unit size ride on it.
- **The optimism, blind (the side the read liked more than the market):** RAW read 51.2%, won 47.0%, market 47.1% - the read
  +4.2 pts over what happened, the market +0.1. Every season: 2023 +4.6, 2024 +4.5, 2025 +4.9, 2026 +2.8; regular +4.2,
  POSTSEASON +4.5 (163 sides). BOARD read +1.1 (0.9 / 1.9 / 1.3 / 0.3; postseason -0.8) - the tune's trust already takes
  back three quarters of it. Log loss blind: market .6766, board .6775, raw .6814; any calibrated read .6766 = the market.
- **By read bucket (home side, blind regular season):** the raw read's 55-60% bucket won 54.8% (market 56.8), 60-65 won
  61.3 (said 62.2), 65-70 won 65.4 (said 67.0), 70+ won 71.6 (said 72.7); dogs the other way (30-35 said 32.3, won 35.5).
  The board read's buckets sit on the market within a point except 55-60 (said 57.3, market 57.6, won 55.1).
- **By the gap (RAW read, blind regular season, ROI at the close):** 0-2 pts won 48.4% (read 50.2, mkt 49.3) -5.7%; 2-4
  47.9% (51.0 / 48.1) -4.4%; 4-6 47.4% (51.4 / 46.5) -1.9%; 6-8 45.6% (52.2 / 45.3) -3.4%; 8-12 42.9% (52.7 / 43.1) -5.5%;
  12+ 40.8% (54.5 / 40.5) -3.6%. The market's number wins every bucket; favorites and dogs alike (dogs 8-12: read 48.9,
  won 38.4, -7.4%; favorites 8-12: read 62.2, won 54.2, -0.8%). Postseason: 12 dogs in 8-12 won 6, noise. BOARD read:
  2-4 pts -4.6% (1,867), 4-6 -9.4% (467), 6-8 -35% (16). Starter known / unknown: every finished game carries its actual
  starter, so history can't split it - the live scan already refuses a game without both starters named.
- **The fitted fix:** logit(cal) = logit(market) + a x (logit(read) - logit(market)), a fit on every priced game before
  each season (blind): RAW a = .064 (2019) .215 .176 .185 .138 .113 .094 .091 (2026); the early scan's recent-seasons read
  .075 in 2026; BOARD a = .079 (2023) .091 .004 -.019 (2026) - the board read has NO disagreement worth keeping. Keep ~8%
  of the raw read's gap and a 9-point gap becomes 0.7.
- **The bare Lock rule replayed (read 56%+, beats its price and the no-vig number, -150..+125, the most value a day,
  quarter-Kelly):** BOARD read blind regular 70-69, -10.9% flat, -5.6% sized (139 Locks, avg 1.0u); postseason 8-11, -27%
  (19, all 2018-22 - the board read found no postseason Lock 2023-26). RAW read blind 293-303, -9.1% flat, -185u sized at
  avg 2.9u; postseason 20-21 all years, -11%. CALIBRATED read: no Lock at all after 2018 (the read = the market, nothing
  clears the vig). Blind, the MLB Lock loses either way - calibration ends it rather than fixes it.
- **The early exam band (+100..+149 dogs, raw read 8-12 over the OPEN's no-vig number, price not yet moved 15+ cents toward
  them - sports_early BANDS), blind at the open:** 252 dogs 2023-26, 131-121 (52%), +16.7% flat; 2023 +23.8% (55), 2024
  +25.6% (48), 2025 -3.0% (83), 2026 +29.0% (66); postseason 4-1 (5). Sized by the raw read (today's rule, avg 3.45u):
  868u bet, +145u. Sized by the calibrated read: 0 of 252 still in the band, avg 0.15u. The band's own realized edge
  (+16.7% on 252) supports ~3u by Kelly - the raw read's SIZE of the gap is wrong (+4 pts) but WHICH dogs it ranks at the
  open is right in 3 of 4 seasons; at the CLOSE the same dogs lose (-5.5% for 8-12 above; the live exam's game-time row
  -4.3% on 257). The value is the open -> close move, as the 10/1 / 10/6 studies said. CAVEAT not checkable from the
  repo: the stored MLB open may predate the probable starter being named; the read knows the actual starter, the live
  scan waits for both starters (sp_home / sp_away) - so the live record (now 2-0) is the real test of this band.
- **The exam's pass flickers:** the MLB +8..12 band PASSED every exam 10/1-10/14 (151 dogs, +4.7% / +15.8% in its two
  seasons - the Brewers posted 10/12 and 10/13 under it) and has FAILED since 10/15 04:24 (159 dogs, season 1 -6.4%):
  the 10/15 key-form change (sports_players.recent_floor - this season's starts only) moved a few dogs in and out of the
  band. A band that passes or fails on 2-8 dogs is a thin gate; its live record is the proof.
- **The live MLB unit plays since 10/2 under a calibrated read (a from 2026):** Brewers +112 (own 53.7 / market 45.0, gap
  8.7 -> 0.7): no post (was 3u, won +3.4u); Brewers +144 (48.5 / 39.2, 9.3 -> 0.7): no post (3u, won +4.3u); Guardians -149
  Lock (own 61.7 / 57.2 -> 57.1): no Lock (1u, lost); Rays -132 Lock (57.9 / 54.4 -> 54.3): no Lock (½u, won +0.4u). Live
  +7.1u on 7.5u; calibrated: nothing bet.
- **Blind postseason board 2018-25 (bare rules):** Locks 8-11 (board read) / 20-21 (raw), exam-band dogs 4-1, the liked
  side -0.8 pts (board) / +4.5 (raw) - 19-41 plays in eight Octobers, no verdict possible on the postseason alone.
- **VERDICT: LEAD, nothing built - not a bug.** The raw read is a logistic fit on its own inputs: honest over all games
  (its buckets are within 1-2 pts), optimistic exactly where it disagrees with a sharper market - the shrink the tune
  already learns (trust) is the fix, and the board read already carries it. OWNER'S CALLS, with numbers: (1) apply the
  shrink (a ~ 0.08) to the MLB early scan's read: the +8..12 exam band and every MLB early play ends (blind +16.7% on
  252 at the open, live 2-0 +7.7u); (2) size an exam-band play by the band's own record instead of the raw read (flat
  1u, or ½u until 30 live bets) - the 3u Brewers plays rode on a read 9 points over; (3) the MLB Lock (board read):
  70-69, -10.9% blind, -27% postseason - a calibrated read would post none; today's rule keeps posting them. The 10/15
  pattern holds in baseball as in college: the market's number beats the read in every gap bucket at the close.
## 10/16 - NBA (opens ~10/20) + COLLEGE HOOPS (~11/3) READINESS, round two: the real post_board on past 2025-26 days, three bugs fixed, and the blind FULL-board replay (Lock / Dog / plays / leans) 2023-26 - NBA done, college hoops partial
The real board (sports.post_board at 8:35 AM PT, the day's games set back to 'pre' at the closing price, the model fit on the seasons before, fake injury feeds: every team covered / half the schools / the feed dead / 2 out + 4 questionable) on NBA 2025-10-21 (opening night), 2025-12-30, 2026-01-15 and college hoops 2025-11-03 (opening night, 66 priced games), 2025-11-07, 2026-01-15. No crash; the dashboard renders every board; no pick past -150; every value play a moneyline at ½u; every Dog a +100..+300 moneyline at ½u (DOG_UNITS_BY); no lean with units; no win % on the page; the records / home-away splits on the cards match the games we hold. Injuries: the NBA feed dead (None) = every side waits, 0 picks; a college hoops school with no report = UNKNOWN, no pick (11/7/25 with half the schools covered: 31 teams named, 2 leans on covered schools only); 4 questionable on a team = the game waits on them; the opening boards are leans only (nothing clears value with no games played). Scratch tools: scratchpad hoops_ready.py (check / replay), hr_sum.py.
- **BUG 1 (fixed, test_data_gaps_scale_to_a_full_college_hoops_day) - the opening board took 8 MINUTES on a college hoops day.** data_gaps ran seen_all for every side on the slate, and seen_all parsed every final's date again for every side: 488 sides x 56,000 hoops finals = 27 million strptime calls (opening night 2025: 446 s; 11/7: 124 s; 1/15: 207 s of a 220 s board), plus one pass over every game per side for a stuck result (200k games x 488 in production). On the runner that is every hourly run on a hoops day, twice per post_board. Now the parse is cached, the season's counts are computed once a board, the stuck games found in one pass: 1/15 post_board 207 s -> 5.9 s. Same answers (pinned).
- **BUG 2 (fixed, test_a_lean_favorite_never_hides_the_gated_dog_of_the_day) - a lean favorite hid the Dog of the Day.** 2025-12-30: the 76ers -123 (54%, its OWN read under the price = no units, a lean) outranked the gated Grizzlies +103 (dog score 4.3, weighed read beating the price) in one_side, so the Dog slot sat empty and the dog went up as a ½u VALUE PLAY. In the NBA that's the same ½u in the wrong record (3 of the 21 replay 'play dogs' - Bulls +110, Kings +120, Grizzlies +103); in football / hockey it's a 1-2u Dog posted at ½u. A side that's a real unit play (good and its read beats the price) now outranks one that can't carry units; a lock / strong lean WITH value still wins the game as before.
- **BUG 3 (fixed, test_fade_line_never_shows_a_price_that_did_not_move) - a card said "Money's pouring in on Wake Forest (-4500 → -4500)".** The fade line fires on OUR side's price moving (Morehead St +1600 -> +2500) but printed the other side's, capped at the book's -4500 both times - a non-move. It shows the other side's move when it moved, else ours.
- **THE BLIND NBA BOARD 2023-26 (543 board days, NBA alone on the board, closing prices, each season's model fit on the seasons before, no injury reports; today's rules + units; tool: scratchpad hoops_ready.py replay):** LOCK 59-38 (60.8%), +8.9u on 59.5u, **+15.0%** (23-24 6-6 +0.8u; 24-25 34-23 +4.9u; 25-26 19-9 +3.2u) - flat 1u +5.9%, so the own-read sizing adds ROI. DOG (score 4+, ½u) 8-10, +1.0u on 9u, +10.9% (23-24 4-4 +1.6u; 24-25 4-6 -0.6u; 25-26 none - its gated dogs were the 'play dogs' below or +200..+300). VALUE PLAYS (½u ML) 13-8, +9.4u on 10.5u (+89%, 12 of 21 were gated dogs at +200..+300 the BIG_DOG rule keeps off the Dog spot; 1 favorite). SOLO (one-game days, units by rule) 22-24, +1.4u on 23u. ALL UNIT PLAYS 102-80, +20.7u on 102u, **+20.3%** (every season up: +2.6u / +9.9u / +8.2u). LEANS 435-384 (53.1%), -3.0% flat (ml leans 54.2% / -4.6%, spread leans 51.8% / -1.0%; 25-26 ml leans 81-85, -14% - no units, no money). Checks: fair YES (close), blind YES (model), most seasons YES for the Lock (3 of 3 up) and all unit plays (3 of 3), the Dog 2 of 3 on 18 bets = LEAD; current season n/a; second check = the 10/9 replay (Lock 54-32 +16%) agrees. Caveats as 10/9: no injury data in history, NBA alone (live, an NBA Lock posts only as the day's best Lock), the close not the 8 AM number.
- **THE BLIND COLLEGE HOOPS BOARD 2023-26 - PARTIAL (the speed bug ate the run; restarted at ~15 s a day, 440 board days - rows land in the scratchpad hr_ncaab_*.jsonl, summarize with hr_sum.py):** the first 47 board days (the first 2-3 weeks of each November): LOCK 13-8, +7.6u on 42.5u; DOG (score 4+, ½u) 6-3, +2.1u; VALUE PLAYS 6-11, -3.2u on 8.5u (favorites 6-8, dogs 0-3); LEANS 46-45 (ml leans 26-14, spread leans 20-31). Too thin for any verdict - finish the run before judging a kind. One thing to flag now: **the November Lock sizes are big** - 2025-26's 8 Locks carried 25.5u (opening night 2025: South Dakota -132 at 6u, own read 67% vs the price's 57%, lost 81-79 to Utah Tech) on reads that rest on LAST season's ratings (college rosters turn over). The Lock-by-own-read sizing is the owner's rule - a proposal, below.
- **VERDICT:** BUILT (the three fixes). The NBA board is ready: the Lock is the engine's proven NBA unit play (now 3 seasons, +15%), the ½u Dog and the ½u plays are leads with their own records. College hoops: the pipeline is ready (bugs 1-3), the replay verdict waits on the full run.
- **PROPOSALS (the owner's calls, numbers above):** (1) a college hoops Lock in the season's first two weeks sized ½u-1u (or the Lock's own-read trust shrunk until each team has ~5 games) - today's sizing put 6u on an opening-night read off last year's roster; judge on the full replay's November Locks. (2) BIG_DOG (+200..+300 gated dogs need p 22%+ and 5 more points of value than the best regular dog to be the Dog): since the owner's +300 call, 12 of the NBA replay's 21 'value plays' were such dogs (8-4 as ½u plays) - either leave them as ½u plays (today) or let the best-scoring gated dog be the Dog at ½u regardless of price. (3) NBA ml leans ran 48.8% in 2025-26 (81-85) - leans carry no units; nothing to change, watch the 🟡 record.
- **LEADS / TODO:** the "We were here first" / "the engine had this side before the move" line-move pool states a move that happened BEFORE we posted at the moved price (true data, loose words - every sport, not hoops-specific). Opening-night NBA opens read from months back (Warriors +138 -> -148 'the market's coming around') - true, but a stale open; fix_opens only corrects games our line history tracked.

## 10/15 - TEN STUDIES (daily run): favorite flip, in-season coach firing, NFL dogs by total, MLB playoff totals, home plate umpires, travel miles (college + NHL), early-season totals, college lucky winner / unlucky loser by yards, NFL weather, NHL 3-in-4 + college bounce-back home dog: ALL DEAD, three WATCH lines; nothing built
- **The total's move as a side signal:** NOT RUNNABLE - no opening totals anywhere (games files hold the close only; the paid history is moneylines + spreads, no totals). Would need a paid totals pull (the owner's call). Replaced by the NHL 3-in-4 study.
- **The favorite flip (NFL + college, paid history 2020-26, first fair look -> last look):** 159 flips of 5,654 games. Opener's favorite (now the dog) +0.2% train -> -3.8% blind (band -7.6%), z 0.1; sign flips by sport and season; moves toward a pick'em without a flip -5.9% / -4.9%. 60 cells. DEAD - the market prices the flip.
- **In-season coach firing (first 1-3 games under the replacement, 18 NFL / 25 college changes 2018-25):** NFL 15-38, -29.6% (dogs 8-30, -34.7%) - the same direction as the 9/30 fired-coach fade already in the Dog score; college dogs +40.9% is four long shots (z 0.7). DEAD - too small, nothing new to wire.
- **NFL dogs by closing total (<=40 / 40.5-44 / 44.5-48 / 48.5+), ML +100..+300 and ATS, train 2018-22 / blind 2023-26:** every band loses blind (-6% to -17%); ATS 47-52.5% blind. 40 cells. DEAD (matches college + NHL 10/14). WATCH only: +201..+300 dogs at total 40.5-44, +11.3% (75) / +5.9% (65).
- **MLB postseason totals (356 games 2018-26):** 49.6% over vs 50.0%; over -5.3%, under -3.6% - the same as September. Low totals, bullpen games, parks, rounds all flip or are thin (the Wild Card "under" broke with 2026's 7-1 over). ~70 cells. DEAD.
- **Home plate umpire (20,065 MLB games with an ump, prior-only rolling over-rate):** correlation with the over vs the market +0.005 on 8,037 - zero carry; strong-under umps +0.7% / +5.4% then -0.7% at n 100+. ~45 cells. DEAD - the books price the ump.
- **Travel miles (venues.json geocoded; college road teams, NHL one-way + last-4-days miles):** all buckets within noise; NHL 2500+ road favorites +4.9% -> -11.1%. DEAD (like the time zones). WATCH: the college HOME dog hosting a favorite that flew 1,500+ miles - ATS 57% / 61%, ML +28% / +37%, 7 of 9 seasons, but 138 games, train z 1.0, 28 cells.
- **Early-season totals (NFL weeks 1-6, college Sep-Oct, NHL Oct-mid Nov):** every week flips sign between halves; college over 49-52%; NHL over 49-51%. DEAD - the books don't misprice early totals.
- **College lucky winner / unlucky loser (won or lost while outgained 100+ yards, box scores 2021-26):** back the unlucky loser +3.3% -> -16.8% blind; fade the lucky winner -15.1% -> -1.5%; every split flips. 36 cells. DEAD.
- **NFL weather at the close (1,674 outdoor games):** sides dead everywhere (wind / cold / rain dogs all lose). WATCH: the UNDER in wind 15+ mph - 56.9% train / 61.8% blind, 8 of 8 seasons over 50%, BUT 2024-26 is 52.5% (+0.3%) - the edge was 2023; the wind is the after-the-fact reading, not the forecast the close saw; ~86 cells. Not built.
- **NHL 3rd game in 4 nights / 4th in 6:** the tired dog loses, but it's the back-to-back part (not on a b2b: -7.7 -> -1.8) - already wired. Totals nothing. NOTE: the wired third_in_four (+1.5 for the rested favorite) ran +3.0 train -> +0.2 blind, 2025 -13% - fading; re-check before it grows, not cut on this alone.
- **College home dog off 2 straight losses vs a 3+ win-streak team:** 6-11 train, 1-13 blind. DEAD.
- ~470 cells across the ten; ~20 chance "hits" expected at this bar - the three WATCH cells are inside that.

## 10/15 - THE COLLEGE OWN READ vs THE MARKET (the owner: "the game obviously isn't a coin flip - the engine reading BYU 48% means something is wrong"): the market is right when the gap is huge - a 12+ college gap is a TRAP in the early spots (built)

- **The BYU +300 vs Notre Dame early play (ncaaf:401856809, own 48% / market 24%) reproduced from the data:** the ratings
  have Notre Dame 1881 and BYU 1828 (5th and 9th), 53 points apart, plus the college home edge of 100 - Elo alone says
  BYU 57% at home; the fitted weights (travel -0.21, letdown -0.13, revenge, form) pull it DOWN to 48%. The market says
  24% (+10.5). Nothing is broken in the inputs: both teams' 2026 games are all there (ND 6, BYU 5), no FCS gap, the home
  edge grid isn't saturating (120 beats 100 by 0.0005 of log loss). The read is just compressed at the top - 1/3 of a
  rating regresses to 1500 every off-season and 12 games a year can't rebuild the spread between two top-10 teams.
- **Calibration, blind (walk-forward: params learned before 7/2024, graded 7/2024-now, 1,885 priced college games):**
  the side the read liked more than the market, by the gap - 0-5 pts: won 50.4% (read 50.2, market 47.8), +6.2% at the
  close; 5-10: 43.4% (read 51.7, market 44.4), -22%; 10-15: 37.7% (read 49.8, market 37.5), -16%; 15-20: 34.6% (read
  51.2, market 33.9), -8%; 20-25: 29.8% (read 53.4, market 30.8), -21%; 25+: 25.6% (read 56.5, market 23.7), -13%.
  The 2026 season alone (439 games) reads the same (10+ gaps won 16-30%, the market's number). The tune already knows:
  the college trust is 0.0 blind / 0.02 live; log loss own 0.5625 vs market 0.5040. The early-price exam agrees
  ("early +8+" college dogs 181, -11.5%).
- **BUILT (bug-level):** the early spots' gap (sports_early.spot_gap) treats a college read 12+ over the price like the
  NFL's / NBA's (sports.OWN_CAP / OWN_TRAP): nothing, not the cap. BYU's 24-point gap had been capped to 12 and cleared
  SPOT_MIN_TOTAL (5) by itself, through an 'ice cold' fade; it and Old Dominion +145 (own 70% / market 39%) would not
  post now. Gaps under 12 still count in full; hockey / baseball keep the cap (not studied).
- **OWNER'S CALL (not built):** (1) the 5-10 bucket lost too (-22% blind) - the honest form of the college spot path is
  the tune's own trust (shrink the read to the market by 0.02), which would end college gap-driven early plays
  altogether; (2) the daily board's college dog score (sports.dog_score) counts the same capped 12 - college dogs this
  season 44-80, -12.6% - adding ncaaf to sports.OWN_TRAP is the same fix on the board side.
- **The Sam Houston +100 lean (10/14, "our QB's been playing better" + "Brock Glenn looks lost"):** no contradiction -
  Glenn is Western KY's QB (the opponent; he and Tisdale rotate), Landyn Locke is ours. But Locke's edge (7.3 vs 5.1
  adjusted yards per attempt over the last 4 starts) leans on 322 yards / 4 TD against FCS Nicholls (59-0); his other
  three were 316 / 195 / 138 yards and the team scored 3 at Liberty. The college QB form (sports_players.score) counts a
  game against an FCS school at full weight, and the game files carry no FCS / conference marker to discount it by.
  LEAD, not built: weigh college QB form by the opponent's rating, or drop games against teams outside the FBS feed.

## 10/14 - SOCCER ROUND 2 (the owner: "I know people who hit soccer like crazy" - the softer spots): DEAD everywhere in this data
- 34,310 games, 13 leagues 2018-19..2025-26 (top 5, Championship, League One, League Two, National League, Scotland, Netherlands, Belgium, Turkey; Portugal / Greece / MLS / South America not obtained). Train 2018-22, blind 2022-26, Pinnacle close + best price.
- Lower-league plus-money 1X2: -3.2% both halves at Pinnacle (16k / 17k), best price -0.9 / -0.7; 0 of 12 leagues positive both halves.
- Totals O/U 2.5: overs -3.1 / -3.6, unders -4.6 / -3.1; a walk-forward attack/defence goals model reads WORSE than the market (log loss 0.695 vs 0.676) and its picks lose every season. (A first run showed +5-6% blind - a look-ahead bug: season files loaded twice so the model saw the game's own result; caught by a shift test. For any walk-forward study: dedupe and shift-test.)
- Draws: -3.4 / -4.6; model-liked draws -9.0 blind.
- Elo + form on the lower leagues: worse than the market (log loss 1.012 vs 0.985); edge plays lose.
- Late season (last 6 rounds): the market prices motivation. Only near-miss: OVER 2.5 when neither team has anything to play for +3.3% n 325 / +5.0% n 430 (1.4 SE) - noise-level; its mirror -8.2%.
- Verdict: ~250 cells, 'positive both halves' at chance everywhere. Soccer stays off; people who hit it are riding variance or have data we don't (lineups, Asian-handicap steam, in-play).

## 10/14 - SOCCER (the owner: his brother's engine "smacking" soccer plus money - should we add it?): DEAD - the top European leagues price like the NFL / NBA; not built
- Data: football-data.co.uk, EPL / La Liga / Serie A / Bundesliga / Ligue 1, 2018-19..2025-26 = 14,285 games, Pinnacle closing + best closing 3-way odds. Train 2018-22, blind 2022-26 (~7,000 games). The Champions League is NOT in this source (the brother's PSG +200 at Man City kind of bet is untested).
- Every +100..+300 side flat: Pinnacle close -4.9% / -4.1% (6,487 / 5,580); best price on the board -1.9% / -1.8%. Every band negative at Pinnacle; +200..+300 home dogs -12%. Draws -2%; favorites 0 to +1.5% (the vig).
- An engine-style model (walk-forward Elo + home edge + form, calibrated): "own read beats the no-vig price by 3+ / 5+ / 8+ pts" on plus money loses blind at Pinnacle (-4.5 / -3.4 / -1.3%) and at the best price (-2.4 / -2.2 / -0.4%); 0 of 10 league x side cells positive both halves.
- Angles (home dogs, away favorites, early season, big clubs): nothing survives.
- Practical: 3-way moneyline (a draw ~25% of games = a loss); our odds pipeline and injury feeds carry no soccer. Re-check only if the owner wants the Champions League specifically (needs a new data source).

## 10/14 - TEN STUDIES (daily run): the Lock's price band (-101..-150) broken down in all four sports, college QB change / NFL young QB, the game after the first loss, dogs by game total (college + NHL): ONE BUILT (college favorite off a loss), the rest DEAD
Thresholds on 2018-22 (QB data 2021-23; MLB 2018-23), graded blind 2023-26 vs every side at the same price band. ~400 cells - ~20 pass by luck.
- **BUILT - college favorite -101..-150 OFF A LOSS:** -14.2% train (232) / -19.5% blind (223), won 44.4% blind where the price said 53.1%, down 8 of 9 seasons; home favorites off a loss -25.2% / -18.5%, 9 of 9. Wired as a WEIGHT: sports.weigh_ncaaf_fav_off_loss, -3 points on the favorite's weighed read on top of the dog's existing "favorite lost its last" +2 (the whole lift inside FAV_CAP); lead tag "college favorite off a loss (fade)"; test_college_favorite_off_a_loss_weighed_down.
- College favorites in the band overall: -8.7% / -6.9%; least bad off a win -2.3% / -0.3% (break-even, not a winner). LEAD (not built): -136..-150 college favorites -11.9% / -17.5%, at home -15.4% / -21.7%.
- **NFL favorites -101..-150:** DEAD - overall -5.8% / -4.4%; off a loss -9.1% / -5.4% (mild); September favorites -10.2% / -9.7% (84 / 78, small).
- **NHL favorites -101..-150:** DEAD - no subset holds; the rested favorite vs a back-to-back dog (+8.5% / +0.8%, one blind season) is already the engine's back-to-back weight. Postseason favorites -7.4% (332).
- **MLB favorites -101..-150:** DEAD - no subset break-even blind; worst: road favorite with the weaker starter -1.3% / -11.3% (372), -126..-150 +0.1% / -7.2%; postseason -8.9% (205).
- **College QB change (players/ncaaf.csv top passer):** DEAD - the in-game 'change' is look-ahead (benchings in losses); the pregame-knowable version (last game was a change) is noise (dogs ±, ~1 SE, ATS 49.4%).
- **NFL young QB (5 or fewer starts in data from 2016) vs a 20+ start QB:** DEAD - priced (young side -12.3% vs band -13.2% blind; vet side +4 pts both halves, not significant).
- **The game after a team's first loss (college after 3-0+, NFL after 2-0+):** DEAD - college +edge train flips blind (-12.6%); NFL n 48.
- **Dogs by game total (college bands, NHL 5.5 / 6 / 6.5+):** DEAD - no band holds both halves; college under-45 noise (z ~0.5); NHL 6.5+ dogs +2.5 vs band blind only.

## 10/13 - TEN STUDIES (daily run): weeks without a bye (college + NFL), college hot offense, the college turnover-luck WATCH re-checked, NHL back-to-back after OT / streak snaps / goalie first starts, home openers (college + NFL): ALL DEAD; the turnover-luck WATCH closed; nothing built
Thresholds on 2018-22, graded blind 2023-26 vs every side at the same price band. ~180 cells.
- **Weeks without a bye (college 6th-8th straight week, NFL 5th-7th; streaks counted only on observed weeks):** DEAD - college tired dog vs a team off a bye -28% n 92 -> +4.1% n 52; NFL +14.6% n 103 -> -30.6% n 63; ATS flips.
- **College hot offense (35+ in each of the last 3):** DEAD - as a favorite +0.1% / +3.4% vs the band, ATS 48% / 44%; as a dog +3.5% n 47 -> -19.6% n 38.
- **College turnover luck (10/1 WATCH: a dog that lost the turnovers by 2+ with even-or-better yards):** CLOSED - with full box scores (2021-26, ~95% of dogs) +23.8% n 55 -> +1.8% n 103, ATS 50-50, fading by season (2025 -16%, 2026 -19%). The old +25% on 113 was the thin early sample.
- **NHL night 2 of a back-to-back after an OT/shootout game:** DEAD as an add-on (-0.1 / -8.4 vs the band, train shows nothing). The plain back-to-back weight already in the engine re-checked: -4.9 train / -5.0 blind, 6 of 8 seasons - keep.
- **NHL the game after a 5+ win streak ends / a favorite on a 4+ game losing streak:** DEAD (-4.1 / -8.6, 2020-21 carries train; favorites -5.8 -> +9.2, flips).
- **NHL goalie's first start of the season / after 10+ days off / first 5 career starts:** DEAD (players/nhl.csv starters 2016-26). WATCH: a goalie's first start of the season in game 4+ (not the opener goalie) as a dog -3.8% n 115 -> -24.1% n 61 (t -1.7), 2024-25 carry it.
- **Home openers (college after 1+ road games; NFL after a road start; NFL week-1 home teams):** DEAD - college -15.8% n 199 -> +6.2% n 153; NFL -13.9% blind; week-1 NFL home teams -11.0% / -12.7% vs -5.4% / -5.9% (~1 SD), road side +7.4% -> -5.4%.

## 10/12 - TEN STUDIES (daily run): NHL night 1 of a back-to-back / first road game after a homestand / hot home favorite / day of the week / blown leads, NFL home & road stretches / hot favorite vs cold dog / offensive dud / blown leads, college after OT: ALL DEAD, one existing point confirmed; nothing new built
Thresholds on 2018-22, graded blind 2023-26 vs every side at the same price band. ~260 cells - ~13 pass by luck.
- **NHL first night of a back-to-back (opponent not playing tomorrow):** DEAD - 49.1% vs 48.6% (-2.3%) n 1,173 -> 50.7% vs 49.3% (-0.5%) n 870; splits flip. Teams start their #1 goalie on night 1 60% (66% normal, 36% night 2).
- **NHL first road game after a 4+ game homestand:** DEAD - +2.8% n 420 -> +1.2% n 303, z ~1; gone once rest is controlled.
- **NHL hot home favorite (5+ straight wins / 4+ straight home wins):** DEAD - priced right (-3.7% vs band -3.6%; -3.4% vs -2.8%); the dog facing it doesn't beat its price.
- **NHL day of the week (Eastern date):** DEAD - weekend home favorites not overpriced (Sat -1.1 / +1.5 vs band); Sunday favorites +4.0 / +5.1 picked after looking, 2023 carries it.
- **NHL blown 2+ goal lead / comeback, next game:** DEAD; WATCH: the 3+ goal comeback team +5.0% n 45 -> +27.7% n 32 (z ~1.7, the 2-goal version fails).
- **NFL home after 2+ road games / 3rd straight home or road game:** DEAD (-2.5% / -1.6% vs bands -3.8% / -3.5%; seasons -13.9u..+10.6u); home vs a team on its 3rd straight road game 23-16 / 15-6 on 60 games - chance.
- **Hot favorite (3+ wins) vs cold dog (2+ losses):** DEAD - NFL cold dog ML +30% n 37 -> -14% n 38; college ML -24% blind.
- **Offensive dud (NFL 10 or fewer / college 14 or fewer):** NFL DOG off a dud CONFIRMS the existing dog-score point - ATS 56.3% n 197 -> 55.5% n 155 (dogs 52%), ML +2.2% -> +4.3% (band ~-4.8%), 2024 lost; keep the point at its size, don't raise it. NFL favorites off a dud and every college cell DEAD.
- **College after an overtime game:** DEAD - OT losers 63.2% vs 52.4% train -> 42.4% vs 46.1% blind.
- **Football blown 10+ halftime lead / comeback, next game:** DEAD; WATCH: the NFL comeback team next game 46.7% vs 51.2% (-18%) n 75 -> 39.0% vs 50.7% (-37%) n 41, z ~-1.5, 2023 (2-13) carries it. College flat.

## 10/11 - TEN STUDIES (daily run): college after a midweek game / finally home, NHL blowouts / Canadian teams, after scoring 40+, the game before a bye, NFL yards margin, MLB blowouts, the last-day line move, the spread-outlier book: ALL DEAD, two weak LEADs; nothing built
Thresholds picked on older seasons, graded blind on 2023-26 (odds history 2020-23 / 2024-26), vs every side at the same price band. ~300 cells tried - ~15 pass by luck.
- **College after a Tue-Fri game (8-11 days' rest next):** DEAD - dogs +7.3% n 98 -> -23.4% n 87 (every blind season lost); ATS 52.1% -> 49.3%. 4-6 days' rest almost never happens.
- **College home after 2+ straight road games / 3rd straight road game:** DEAD - dogs -7.3% -> -6.9%, ATS 48.7% / 48.8%; 3rd road game n 12/13. Side note: college favorites -150..-101 lost at any rest (-11.4% train, -7.2% blind) - our own college favorite unit plays in that band are 4-1, +4.8u (only taken when the own read backs them) - no change.
- **NHL after winning/losing by 4+ (or scoring/allowing 6+):** DEAD - winners as favorites +1.8 -> -6.3 vs the band; 4+ losers as dogs +5.4 -> +4.9 but ROI ~0 and it shrinks at 5+.
- **NHL Canadian teams (home vs US visitors, US teams' 2nd+ Canadian stop, Leafs/Habs/Oilers hype):** DEAD - the market prices them right (US 2nd+ Canadian stop +11.8 -> -6.6, flips).
- **After scoring 40+ (college 50+), margin controlled:** DEAD - NFL favorites 72.9% vs 69.6% / 72.4% vs 70.2%, ATS under 50%.
- **The game before a bye:** DEAD as a rule (NFL pre-bye +13.4% -> +6.4%, 2024 -25.7%; college flat). WATCH: a college dog before its own bye vs an opponent off a bye 40.0% vs 28.6% n 35 -> 47.8% vs 29.4% n 46 - found after three splits, college gaps can be faked by missing games.
- **NFL lost but outgained by 50+ yards (team box scores 2021-26):** weak LEAD - next game ML +11.6% n 80 -> +11.0% n 128, every season over the band; but the 75+ yard cut the training seasons chose is +0.9% blind, ATS flat (53.6%). Lucky-winner fade DEAD. Not built.
- **MLB after winning/losing by 7+:** DEAD (-0.7 / -1.6, +1.8 / -1.4 vs the band; postseason n 43-56 noise).
- **The last-day move (odds history):** DEAD as a bet - NFL sides that moved 1+ pt in the last 24-48h won ~3 pts over the close's no-vig number but ROI -0.1% / +0.4% (no juice beaten); college flips (+10.5% -> -22.9%); college dogs drift up ~0.4 pt late - too small.
- **Spread-outlier book (1+ pt better than the median at similar juice; 17% of NFL / 23% of college games; FanDuel, BetUS, LowVig, BetRivers, Circa):** DEAD as a pick - beats the close by ~0.85 pt but the same sides at the median number made the same money. A shopping habit: with a spread pick, take the best number on the board.

## 10/11 - NFL 6-POINT "WONG" TEASERS (the owner's brother's engine posts them): BORDERLINE - dogs-only at -120 is a LEAD. THE OWNER SAID NO (10/11) - no teasers on our board
- 2,277 NFL games with closing spreads 2018-26, teased 6 from the close (push = loss). Dogs +1.5/+2/+2.5 -> 77.4% (304/393); favorites -7.5..-8.5 -> 69.8% (113/162); all Wong legs 75.1% vs every non-Wong leg 68.7% (z 3.1). The "low total" filter is noise (<=44 76.2% vs 74.4%). Same-day legs independent.
- Break-even per leg: 2-team -110 72.4%, -120 73.9%, -130 75.2%, -140 76.4%; 3-team +160 72.7%, +150 73.7%. All Wong at -120 +3.5%, at -130 0%; dogs only -120 +9.7%, -130 +5.9%.
- Timing (odds history, 1,712 games): teasing the first fair number does WORSE (dogs 73.1% vs 78.6% at the close); a +2.5 that drifts to +3/+3.5 covers only 62% - bet the game-day number, only if still +1.5..+2.5.
- Walk-forward: the rule picked on 2018-21 (favorites included) went 80-69, -1.1% blind 2022-26 (max 7 straight L). Dogs only (chosen after the fact) 65-39, +14.9% blind, every season -0.2..+9.2u. College: dead (Wong dogs 70.4%, -8%).
- If the owner OKs a test: NFL only, 2-team 6-pt at -120 or better (-125 max), legs = game-day dogs +1.5..+2.5 only, ½u, ~1.2 a week, own record + a quit rule. Risks: dog-only is one cut of six (z 1.6 vs break-even), -130/-140 teaser prices kill it, a move to +3 kills a leg.

## 10/11 - DOG SCORE vs THE PRICE READ (the owner: "which one should trump the other?") + the game after an international game: the SCORE decides; jet lag DEAD
- **Score vs price (Fable, the 10/2 walk-forward dump: 1,197 NFL / 1,883 college / 6,966 NHL dogs +100..+220, 2019-26, closing prices; the read is blind, the angle weights saw every season):** NFL dogs the read had 5+ pts over the price but the angles under 0 (the Giants +145 on 10/11 profile) went 13-33, -29.4% (red in train and blind); 8+ over with negative angles 3-7. Pooled three sports the same cell -7.1% (blind -3.1%). A price edge only helps once the angles are at least neutral (NFL angles 0-4 & 5+ over +49.6% on 64; pooled +12.1%). Both required (edge 0+ AND angles 4+) +12.4%, blind +5.7% on 155. The engine's dog_score 8+ +18.1% on 80 (thin). Verdict: the dog score trumps the price read - the price sizes / breaks ties, never picks alone (how the Dog gate already works). Caveat: today's live NFL read makes bigger edges than the 2023-26 blind read did.
- **First game after an international game (NFL 2016-26, 83 next games, 65 with lines):** no bye (6-10 days) 22-13, 63% vs 58% implied, +9.2%, ATS 52% - no jet-lag drag. After a bye 19-29, -45%, but 2019 alone 1-9 - one season, not a finding. The no-bye team is home 31 of 35 times; no bye + road + dog (the Colts 10/11) n=2, 1-1. DEAD - not weighed.

## 10/10 - TEN STUDIES (daily run): the paid odds history (book first-mover, softest opener, books unsure, spread juice) + college weather / altitude / body clock / kickoff time / FCS tune-up + NHL quick rematch: ALL DEAD, one weak LEAD; nothing built
Thresholds picked on the old seasons, graded blind on the new ones (football odds history: 2020-23 / 2024-26; game files: through 2022 / 2023-26). ~290 cells tried in all - ~15 pass by luck at 5%.
- **Book first-mover (one book's no-vig price moves 2+ points, 75%+ of books haven't):** DEAD. The rest of the market follows ~0.2 points of a 2-point move. Betting the stale price elsewhere: NFL blind n 246, CLV -1.3%, ROI -7.7%; college blind n 395, ROI +8.6% after -2.4% train (flips). The college FanDuel/DraftKings-moves-first cell (+18.5% train n 188, +22.1% blind n 135) has blind CLV -0.3% - noise, watch only.
- **Softest opener by book:** a PRICING FACT, not a bet. Sharpest openers: lowvig / betonlineag / williamhill_us (NFL), williamhill_us / lowvig / betus (college); softest: draftkings / betmgm / betrivers (NFL), betrivers / betmgm / mybookieag (college) - but only 0.1-0.25 points off the median book. A 3-point soft-vs-sharp dog gap almost never happens (blind n 5 NFL, 10 college); at 1.5 points college blind n 87, CLV +3.0%, ROI +10.6% (SE 15) - too thin.
- **Books unsure (high hold / books disagree):** DEAD. 48 cells, 3 held blind (luck says ~5). NFL high-hold dogs +16% train -> -33% blind. Best: college dogs where books disagree most, last look, +5.3% n 489 -> +3.6% n 302 (0.5 SE) - nothing.
- **Spread juice shading (-112/-108 or more):** DEAD as a bet (44 cells, 0 held). A TIMING FACT: the number moves toward the expensive (shaded) side about twice as often as away by the close (NFL 41% vs 20% blind, college 46% vs 27%) - if we ever bet a spread the juice is shading toward, bet it early.
- **College weather (wind / rain / cold):** DEAD. Data caution: wx_* is the whole UTC day from Open-Meteo's archive (after the fact) for past games, a forecast for upcoming ones - the close only had a forecast. Unders in wind 18+ +8.9% n 219 -> -9.6% n 93; rain 10mm+ +7.2% -> -20.1%; all bad weather -14.2% blind n 442. Spread dog in wind 20+ 55% n 105 -> 66% n 41 (seasons 37%-86%) - watch only.
- **College altitude (home at 1,219 m+ = 4,000 ft vs a visitor from under 500 m; elev is METRES, the engine's THIN_AIR_M already uses metres):** DEAD. Home ML +15.4% n 120 -> -0.5% n 82; the reverse (low team at home vs an altitude team) ATS +8.8% -> -11.0%. Altitude home team -150..+300 vs a sea-level visitor +12.8% n 40 -> +11.6% n 34 - too small, watch.
- **College body clock (West team at noon ET or earlier / East team at a 10:30 PM+ body clock out West):** DEAD - 15 and 14 blind games, the East-team cell points the opposite way from the NFL spot. The NFL spot stays as built.
- **College kickoff time (night vs day):** DEAD. Home dogs at day +10.7% -> -3.8%; home dogs at night -4.8% -> -17.8%; road dogs at night -16.7% -> -12.1% (a stay-away, already priced into our dog read, not a weight - z -0.8 blind); Saturday 7:30-8 PM ET home ATS 52.2% / 53.0% (breakeven).
- **College FBS team off an FCS game:** a weak fade LEAD. Favorites -150..-1000 off an FCS game won 67.9% vs 71.5% no-vig (train n 106) and 66.0% vs 71.1% (blind n 106), covered 46.5% / 41.9%; the fade lost 4 of 9 seasons, pooled z ~1.4 (wins) / 1.7 (covers) - not significant, and most of those favorites are past our -150 / their dogs past +300. Not built; recheck after the 2026 season. Dogs off an FCS game: 60% ATS -> 52% DEAD.
- **NHL same-opponent rematch within 3 days:** DEAD - 22-37 a season, the train edge was all 2020 (n 364 of 491); blind n 85.

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
