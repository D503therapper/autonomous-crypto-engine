# 11/18 - Early plays x the week's injury news

The complaint (Victor, forwarded by the owner with "These bugs are unacceptable"): "That's what's wrong with some of
the early plays too, especially in football. It gives out plays hella early but we don't even know injuries yet."

Two questions. (1) Does posting a football early play BEFORE the week's injury news cost money - would waiting pay?
(2) Does a posted early play's card keep up with the injury news? (That one is a bug: fixed, no bar needed.)

**The short answer: waiting does not pay. The same dogs win just as often later and cost 1-3% more a bet. A key man
going down after the number is real bad news for that one bet, but nothing we can see at the post sorts those dogs, and
the hold that skips them is a wash. The timing stays. The early card now alerts loud when a key man of ours goes out
or questionable after the post.**

## The data

- The paid odds history (data/sports/odds_history, the median book, FAIR looks only - a look counts only after both
  teams' last games + 4h; tools/early_football_study.ready_at / fair): NFL 3,474 sides / college 8,226, 2020-25 +
  September 2026. Its looks sit right on the injury clock: for a Sunday NFL game **Tuesday noon ET (before
  Wednesday's first practice report)**, **Thursday noon (after it)**, **Saturday noon (after Friday's final
  statuses)**, Sunday morning, the close. College: Tuesday noon, Thursday noon (after the SEC / Big 12
  Wednesday-night availability reports, 2024 on), Saturday morning, the close.
- The NFL injury history: nflverse's weekly FINAL reports (Out / Doubtful / Questionable) + snap counts + starters
  (the 11/11 book study's files, ~/.cache/d503_book1111/dl - plain public downloads).
- College has NO injury-report history (the availability reports started 2023-25, league by league, nobody archives
  them). The college news is read off Saturday's box score instead (sports_absences._games, 2021-26) - hindsight,
  used only to say what late news does.
- The live book: data/sports/early.json (read-only).
- Train 2020-22, held out 2023-26. "The spot dogs" = dogs +100..+350 with a spot that is ON (bye / Monday night /
  East-West; hammered needs an earlier look, so it never fires at the first one) under the live bar (the read not
  fighting, the weighed total 5+). What the history can't see, said plainly: we really post Saturday night / Sunday,
  5-7 days out - before even the Tuesday look. The fades / lead weights / the injury block at the post are not in the
  history either.

## S1 - the same dogs at four prices (s1_timing.py)

NFL, dogs picked at the pre-report look:

| the dogs | n | at the pre-report price | same dogs after the FIRST report | after the FINAL statuses | at the close |
|---|---|---|---|---|---|
| every dog +100..+350 | 1,378 | 488-890, -4.9% | -5.8% (waiting **-0.88% a bet**, t -3.2, paid 1 of 7 seasons) | -4.4% on 1,308 (waiting **-1.02%**, t -2.7, 1 of 7) | -6.7% (waiting -1.74%, t -3.6) |
| the spot dogs (on) | 93 | 42-51, **+23.1%** (train +22.4% / held +23.8%, 5 of 6 seasons) | +21.1% (waiting **-2.06% a bet**, t -1.6; train -3.3% / held -0.9%; paid 1 of 6) | +21.6% (waiting -2.82%, t -1.5) | +19.4% (waiting -3.69%) |
| bye | 28 | 14-14, +40.3% | +35.6% (waiting -4.71%, t -1.9, both halves, 1 of 6) | +35.9% (-4.46%, t -2.6, 0 of 6) | +33.4% |
| Monday night | 37 | 16-21, +19.0% | +16.0% (-2.99%) | +15.7% (-3.25%) | +15.5% |
| East team out West | 44 | 21-23, +29.3% | +29.2% (-0.05%) | +31.4% on 43 (-0.92%) | +29.7% |
| the read 4+ over the price (the exam kind) | 638 | 219-419, -6.8% | -8.1% (-0.89%, t -2.5) | -6.9% (-1.18%, t -2.4) | -8.6% |

The win-loss record is the SAME at every price (it is the same dogs) - only the price gets worse: the money comes to
the dog +0.2 to +1.0 points of win chance between Tuesday and the close. Placebo: the spot dogs' waiting cost is no
different from a random dog's (as bad or worse 258 of 2,000).

The rule RE-RUN at each look's own price (a dog has to still be +100..+350 and still clear the bar there):

| NFL: post only... | n | record | train | held out | by season |
|---|---|---|---|---|---|
| before the first report (today) | 93 | 42-51 **+23.1%** | +22.4% | **+23.8%** | +28 / +24 / +12 / +54 / -26 / +21 |
| after the first report | 91 | 41-50 +24.4% | +39.3% | **+6.9%** | +42 / +37 / +37 / +33 / -43 / +19 |
| after the final statuses | 86 | 40-46 +26.2% | +42.5% | **+9.2%** | +29 / +36 / +79 / +45 / -42 / +12 |

Looks the same overall, and the held-out half drops from +23.8% to +6.9% / +9.2%. Posting later does not pick better
dogs: the dogs that only clear later ran +18.5% on 22, the early ones that no longer clear +10.5% on 24.

College, dogs picked at the Tuesday look:

| the dogs | n | Tuesday price | Thursday (after the Wed-night reports) | Saturday morning | the close |
|---|---|---|---|---|---|
| every dog | 2,313 | 821-1,492, -1.2% | -2.3% (waiting **-0.35% a bet**, t -2.0; paid 2 of 7) | -2.4% (**-1.05%**, t -4.2, 0 of 7) | -3.4% (**-2.17%**, t -6.0) |
| the bye-spot dogs | 63 | 23-40, +6.4% | +5.5% (-0.98%) | +4.1% (-2.26%) | +2.5% (-3.85%) |
| the paused blowout spot | 286 | +5.1% | 0.0% (-0.31%) | +3.9% (-1.90%, t -2.8) | +1.9% (-3.21%, t -3.4) |
| the read 4+ over the price | 1,093 | -0.2% | -1.4% (-0.16%) | -1.5% (-1.29%, t -3.4) | -2.6% (-2.40%, t -4.4) |
| every dog, 2024-26 (the availability-report seasons) | 924 | -4.1% | -7.3% (**-0.78%**, t -3.0, 0 of 3) | -5.3% (-1.24%) | -5.8% (-1.72%) |

The rule re-run Thursday: 26-41 +11.1% on 67 vs 23-40 +6.4% on 63 Tuesday (57 of the 67 are the same dogs; z 0.6 and
0.3 - no difference you can stand on). Waiting cost the college dog MORE in the seasons that have availability
reports, not less.

**Verdict S1: in both leagues the early number is the better number, and the injury reports that land after it do not
turn the later bet into a better one.** (The 11/11 study's S5 said the same from the other side: first fair beats the
close by 2.2% a bet in college.)

## S2 - the key man who goes down after the number (s2_keyman.py, the NFL)

1,121 early dogs at the pre-report look (weeks 3 on). A man's role = his average snap share over his last 4 games. KEY
MAN = the quarterback or a skill starter (RB / WR / TE), role 50%+. NEWS = he PLAYED the last game and is on this
week's FINAL report.

| after our number... | how often | the price then | the bet at OUR number | waiting for the final statuses | placebo (a random set as bad) |
|---|---|---|---|---|---|
| every early dog | - | +0.28 pts to the dog | 397-724, -5.3% | -1.01% a bet | - |
| QB out / doubtful | 5.1% | **-1.62 pts** (33% run 3+ away) | 16-41, -24.6% (train -63.6% / held +13.2%) | +2.30% a bet (t +1.6) | 255 of 2,000 |
| QB questionable | 3.9% | -1.16 pts | 13-31, -30.1% (train -5.3% / held -47.2%) | -1.02% | - |
| QB on the final report at all | 9.0% | -1.42 pts | 29-72, **-27.0%** (train -40.8% / held -15.4%, 3 of 7 seasons up) | +0.82% (t +0.8) | 89 of 2,000 |
| a skill starter out / doubtful | 14.2% | +0.48 pts | 55-104, -5.6% | -1.20% | - |
| KEY MAN out / doubtful | 18.3% | +0.05 pts | 68-137, -9.8% (both halves) | -0.55% | 565 of 2,000 |
| key man questionable only | 21.4% | -0.22 pts | 87-153, -4.7% | -1.61% | 1,076 of 2,000 |
| no key man on the final report | 60.3% | +0.53 pts | 242-434, -4.1% | -0.93% | - |
| 1 regular newly out | 33.3% | +0.18 | -13.4% | -0.66% | - |
| 2+ regulars newly out | 15.9% | -1.12 | **+8.6%** (the wrong way - no dose) | +1.85% | - |
| the FAVORITE's key man out / doubtful | 15.3% | **+1.25 pts** to our dog | 69-102, +8.7% (both halves) | **-2.99% a bet** (t -3.0) | - |

A questionable key man played 77% of the time (265 of 342).

What it says: (1) a key man of ours goes out after the number on about 1 early dog in 5, a quarterback on 1 in 20;
(2) only the QUARTERBACK moves the price against us (-1.4 to -1.6 points) and only the quarterback cell looks like a
real loser (-27% on 101, placebo 89 of 2,000 = z about -1.7, the halves uneven) - the 10/1 and 11/11 finding again;
(3) a skill man or "a regular" going out is noise (-5.6%, and 2+ regulars out ran +8.6%); (4) waiting buys almost
nothing back even on the QB dogs (+0.8% to +2.3% a bet on a bet that still loses 22-25% at the later price) - the
later price takes the news out of the dog's price, it does not make the dog win; (5) half the time the news is on the
OTHER side, and then waiting gives away 3% a bet.

Can a scan see it coming on Tuesday? No: a key man who played through last week's report -> a key man ruled out this
week 21% of the time vs 17% without the flag, and the flagged dogs did no worse (-2.7% vs -6.3%).

The spot dogs (85 with both files): key man out / doubtful after the number 3-9, -35.8% on 12 (a random 12 of the 85
as bad 119 of 2,000); questionable only 6-4 +71.0% on 10; none 29-34 +26.3% on 63.

**The hold, as it would run** - hold every NFL early play until Saturday (after the final statuses), take it only if no
key man of ours is out / doubtful, at the Saturday price:

| | today's timing | the hold | by season (today / the hold) | placebo |
|---|---|---|---|---|
| the spot dogs | 38-46 +24.3%, **+20.4u** on 84 (train +26.2% / held +22.5%) | 31-35 +31.5%, **+20.8u** on 66 (+36.0% / +26.7%) | +3.4 / +6.2, +3.8 / +3.0, +3.3 / +3.1, +9.8 / +11.3, -3.1 / -3.3, +3.1 / +0.6 | skipping a RANDOM 12 made as much 234 of 2,000 |
| every early dog | -39.8u on 1,072 | **-49.5u** on 816 (held -11.8% vs -7.1%) | 2 of 7 seasons better | 1,007 of 2,000 |

+0.4u in six seasons on the spot dogs, worse on every dog, and it turns an early play into a day-before play.

## S2b - college, off Saturday's box (s2b_college.py; hindsight)

1,913 early dogs at the Tuesday look, 2021-26.

| | how often | the price after our number | at OUR number | waiting till Thursday | at the close |
|---|---|---|---|---|---|
| every early dog | - | +0.72 pts to the dog | 666-1,247, -3.2% | -0.48% a bet | -5.4% |
| a DIFFERENT quarterback than last game | 15.9% | **+0.10 pts** | 77-228, **-26.9%** (train -28.6% / held -25.9%, 0 of 6 seasons up; a random 305 as bad 0 of 2,000) | -0.35% a bet | **-27.9%** |
| the same quarterback | 84.1% | +0.84 pts | 589-1,019, +1.3% | -0.50% | -1.2% |
| the lead ball carrier didn't play | 8.2% | -0.01 pts | 45-112, -21.8% (train -40.5% / held -8.9%) | -0.59% | -21.0% |
| neither | 77.6% | +0.89 pts | 552-932, +3.0% (train +7.4% / held +0.7%) | -0.49% | +0.4% |

This is the real cost of late news in college: a dog that ends up playing a different quarterback loses 27 cents on
the dollar. But read the price column: the books barely move on it (+0.10 points against +0.84 for the rest) and the
bet loses just as much AT THE CLOSE (-27.9%). The market does not have this news on Thursday or at kickoff either -
waiting for it buys nothing (-0.35% a bet). Part of the cell is the game itself (a quarterback hurt or benched DURING
the game makes the backup the top passer) - it is hindsight, never a rule. A scan cannot see it on Tuesday: a team
that already changed quarterbacks inside its last 3 games changes again 28% of the time vs 13% - and those flagged
dogs ran +2.2% on 401 against -6.7% for the settled ones (the wrong way).

## S3 - the live book (s3_live.py)

- Early plays, games from 10/25 on: 10-16, -3.9u (the plus-money sides 4-13, -4.7u).
- The injury watch ran on 70 early plays: **a key player was ruled out after the post on 0 of them**; none had one out
  at the post. The live losses are not injury news. (The watch only read a starting QB / goalie OUT before the
  kickoff until today - see the fix.)
- Football: 61 early sides (kept + pulled). NFL posted a median 6.8 days before the game, college 5.9 - 56 of the 61
  before any injury news of the week. Posted before: NFL 2-4 (+0.2u), college 9-21 (-3.4u); posted after: 2-0. Two
  plays - nothing to read.
- By spot (kept): blowout 3-11 (paused 11/12), engine 3-6 (paused 10/24), hammered 1-4, bye 3-3, exam 2-1. The 11/11
  and 11/15 studies already hold the reasons: a stale number, spots with no held-out edge, the old read's home tilt.

## The five checks

1. FAIR - yes: fair looks only; the final report is out by Friday 4:30 PM ET and the "after" price is Saturday noon.
   (College S2b is hindsight and labeled so.)
2. BLIND - yes: the read is walk-forward (3 seasons before), the spots and the bar are the live ones.
3. SEASONS - waiting paid in 1 of 7 NFL seasons (every dog), 1 of 6 (the spot dogs), 0-2 of 7 in college. The hold
   on the spot dogs: better in 2 of 6 seasons, worse in 4.
4. THIS SEASON - live: 0 key men ruled out after 70 posts. Nothing to judge a hold on.
5. SECOND CHECK / PLACEBO - the waiting cost is the same for the spot dogs as for a random dog (258 of 2,000); the
   hold's gain is matched by skipping random dogs 234 of 2,000 times; on every early dog the hold LOSES. The college
   twin says the same.

About 110 cells read. **Nothing clears. No timing rule wired** - no "NFL only after Wednesday's report", no "college
only in game week", no hold. It would give away 1-3% a bet on every play to dodge a risk that hits a quarterback on 1
dog in 20 and that the later price does not fix.

## What IS wired (the bug side)

- sports_early.watch: every run until the game ENDS (WATCH_STATUS = the board's), our side's key men
  (key_men_now: the verified starting QB, the box scores' lead back and top two catchers; the NBA's top-3 scorers /
  starters; the goalie; baseball's best bats) are read against the report. Out OR questionable since the post = a
  loud red **⚠️ INJURY ALERT** line on the early card and the game-day row (news_lines / news_html). The newest word
  on a man replaces the old; a clean word from the report clears him at once; a man missing from the feed needs two
  runs in a row before the game and never clears after the start; a feed with nobody on it for either team never
  clears anyone; a report that didn't come back changes nothing. The pick, its price and its units never change.
- The 🏀 main-guys-sit over: a man off the report comes off its card only after two runs in a row before the tip
  (sports_nba_out.back_how), never after it.
- The run pulls the injury report for every league with an open early side play (sports_early.open_leagues).
- Every alert is logged on the play (key_log) and sports_early.news_record keeps the alert's own record - the
  tracker line for "early dog, a key man out after the post".

Tests: test_early_injury_1118_the_early_card_alerts_loud_on_a_key_man_out_or_questionable_after_the_post,
test_early_injury_1118_the_nba_over_card_waits_two_runs_before_a_man_off_the_report_plays.

## Files

ilib.py (helpers: the injury clock, the live bar, the placebo) · s1_timing.py · s2_keyman.py · s2b_college.py ·
s3_live.py + *_out.txt. They reuse results/studies/early_1111/elib.py + base.py (the football base table).
