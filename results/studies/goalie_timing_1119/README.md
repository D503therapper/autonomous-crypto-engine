# 11/19 - HOCKEY GOALIES x WHEN THE PRICE IS BEST

The owner, 11/19: *"We are bleeding units we need a profitable week"* / *"the sizing is where the profits are"* /
*"Run fable and improve the engine"* / *"Fable needs to be an expert on sizing and edges ... And wire the engine."*
Two levers nobody had studied: the goalie under our biggest hockey bets, and the hour we post.

**The answer, plain.**

1. **The goalie is not a leak and not an edge. Nothing about who is in net clears the bar, so no pick, weight or size
   changes.** A #1 and the other guy stop the puck almost the same (.9096 against .9074 on 657,000 shots), the books
   move about one point of win chance when a backup goes in, and against the price it washes out: a hockey dog with
   its #1 in is -1.4% and with its backup in is -1.3% (every dog 2018-26, the close). The 8 AM goalie guess is wrong
   on 1 side in 6 (the goalie page) to 2 in 5 (our own projection) - and the plays we made off a wrong guess did NOT do
   worse: posted hockey dogs whose own 8 AM goalie didn't start went +14.0% on 153 in the replay and 7-6 live.
2. **Waiting for the confirmed goalie does not pay.** The starter is confirmed on the goalie page at 11 AM Pacific on
   the median night (11% by the 8 AM board, 61% by noon, a third not until the afternoon), the price of a team whose
   8 AM goalie turned out wrong moved a quarter of a point by the close, and nothing we could know at the
   confirmation sorts our plays in a way that holds up (next line). The hockey board keeps posting at 8 AM.
3. **One thing moved, and it is a LEAD, not a rule: our hockey dogs win when the favorite's backup is in.** On the
   replay board 2023-26 the posted hockey dogs went 51-44 **+24.2%** when the favorite started somebody other than
   its #1 and 52-74 **-5.1%** when it started the #1 - both halves. It fails the bar three ways: every hockey dog
   2018-23 shows no gap at all, the same split on the 2020-23 rig's engine dogs runs the other way, and read off
   what 8 AM actually knows (the projection) the posted dogs don't split. It goes on the tracker with its control
   from the 11/20 games; judged at 100 graded.
4. **No size follows the goalie.** The 3u 💎 spot, the 2u Dog and the 2u runner-up do not win more with our #1
   projected, with their backup projected, or with our #1 actually in. The tiers stay exactly as the 11/17 plan left
   them (table in section 6).
5. **When the price is best: at the post. No kind of play gets a better number later.** Our 120 graded moneyline unit
   plays since 10/1 closed a cent SHORTER than they posted on average (54 never moved, 40 got shorter, 26 longer):
   +4.1% a bet at the posted price, +3.4% two hours before the start, +3.4% at the close. Hockey dogs: flat (+0.6
   cents, 11 longer / 10 shorter / 16 the same). Locks and favorites get bet: 9 of 14 Locks closed shorter (-7.6
   cents). NBA dogs get bet too (8 of 14 of ours shorter; the whole NBA market since 10/1: dogs half a dime shorter
   by the tip, +0.9 points). Posting later would have cost a little everywhere and made nothing anywhere.

**Wired:** the tracker lead (`sports_leads.goalie_1119_tags` - "NHL dog, the favorite's goalie tonight is NOT its #1
(lead)" and its control, from the 11/20 games; `GOALIE_1119_FROM`, None = off) and the regression test
`test_goalie_1119_the_other_net_is_a_tracker_lead_and_nothing_on_the_board_reads_it`. Nothing else: no weight, no
size, no later post, no loud alert.

## The rigs and the bar

- **The goalie table** (`glib.py`, cache `~/.cache/d503_goalie1119`): every NHL team-game in our box scores 2016-26
  (27,028) - who started, the team's clear #1 (`sports_goalies.number_one`), the engine's own 8 AM projection
  (`sports_players.projected_starter`), the back-to-back, each man's save % form.
- **Three prices**: the CLOSE (ESPN, 2018-26, 19,318 game sides - the starter is known and priced), the paid
  **MORNING** look (15:00Z, 2021-23, 6,536 sides - the 8 AM board's hour, the starter mostly not known), ESPN's
  **OPEN** (2023-26 - the night before).
- **R3**: the board re-built on today's code, 2023-10 -> 2026-11 at the close (dogs_1117 / money_1117 - 540 hockey
  unit plays), train to 6/30/2025, held out after. **The second rig**: the 2020-23 paid-odds rig (nhl_odds_1102 - the
  hockey dog score rebuilt from history at the morning price), seasons R3 never saw.
- **Live**: every commit of the goalie page in this repo (1,642 looks, 10/6 -> 11/19), our line tape (every price
  change since 10/1), picks.json.
- **THE BAR**: both halves, most seasons, a random same-size set matches it under 5% of the time, a point worse than
  the close, and it has to hold on a rig the cell was not found on.
- **THE HINDSIGHT TRAP, said once** (`s3_leak.py`): our box scores keep ONE goalie a team-game - the man who faced
  the most shots. When a starter is chased early his reliever can face more, and the file calls the reliever "the
  starter": "the favorite's backup started" then holds games the favorite's #1 started and got run - dog wins by
  construction. Every "who started" number below that matters is also shown with the trap out (the man on file faced
  24+ shots - a reliever almost never does), for #1s and backups alike.

## 1. (a) How much does a hockey bet depend on the goalie who started? (`s1_starter.out`, `s3_leak.out`)

The 8 AM projection (ours, no page) names the right starter 63.5% of the time 2023-26 (61% rested nights, 76% on the
second night of a back-to-back); the #1 starts 64% of rested nights and 33% of back-to-back second nights.

| every dog +100..+350, the close 2018-26 (trap out: 24+ shots) | record | vs the price | train 2018-23 | held 2023-26 |
|---|---|---|---|---|
| OUR #1 started | 1322-1893 | **-1.4%** | -3.2% | +1.5% |
| OUR backup started | 990-1509 | **-1.3%** | -0.7% | -2.1% |
| THEIR #1 started | 1181-2034 | -12.1% | -10.6% | -14.4% |
| THEIR backup started | 682-1083 | -5.5% | **-9.3%** | +0.9% |

Favorites -101..-250: our #1 in +0.8%, our backup in -0.5%; their #1 in -7.7%, their backup in -7.0%. Nothing.

- **Our own goalie: no dependence at all**, at any price, in either half.
- **Their goalie: a gap that is all in three seasons.** By season (their backup minus their #1, points of ROI):
  2018-19 +2.0, 2019-20 -1.5, 2020-21 +1.2, 2021-22 -2.3, 2022-23 +7.5, **2023-24 +22.0, 2024-25 +17.9**, 2025-26
  +3.7, 2026-27 +18.0 (43 games). Train half: 1.3 points. It is not a both-halves fact.
- **At the price before the news** (the same dogs): the paid morning 2021-23 - their #1 -14.6%, their backup -9.9%
  (the market moved +0.26 points to the dog by the close); ESPN's open 2023-26 - their #1 -12.5%, their backup +2.6%
  (+1.10 points). The books move about a point for a backup; the rest of the 2023-26 gap is not the price.
- **No hindsight - what the 8 AM projection said**: projected their backup -2.5% on 877 vs projected their #1 -6.8%
  on 5,950 (train -0.5% / -8.0%, **held -5.6% / -5.2%** - gone). Most of it is the favorite on a back-to-back, which
  the Dog score already reads (+3) and the 💎 max play sizes.

## 2. (b) Did the plays made off a WRONG projection do worse? No. (`s2_plays.out`, `s4_weights.out`)

| the posted hockey dogs (Dog / runner-up / floor), R3 at the close | record | flat | train | held |
|---|---|---|---|---|
| every one | 184-199 | +10.2% | +4.0% | +16.6% |
| both goalies as projected | 69-93 | -4.1% | -11.7% | +14.8% |
| OUR projection wrong | 74-79 | **+14.0%** | +8.6% | +17.9% |
| THEIR projection wrong | 61-55 | +20.4% | +21.7% | +5.6% |

(The trap pushes "our projection wrong" DOWN - our starter chased - and it is still the better half. A random
same-size set of posted dogs is as bad as "our projection wrong" 1,366 times in 2,000.)

**The two goalie weights on the dog score that read the projection** - the save % form gap ("the books overpay for
the other goalie's hot run", +1; our man much better lately, -2) and the hot goalie (-3) - on every hockey dog row:

| the form gap as the board read it (projected men) | every dog | both projections RIGHT | a projection WRONG |
|---|---|---|---|
| +1 (our man much worse lately) | 537-723 **+4.3%** (train +3.8% / held +6.3%) | -7.5% | +12.6% |
| 0 | 496-820 -9.6% | -17.9% | -4.1% |
| -2 (our man much better lately) | 273-430 -8.7% | -11.0% | -7.1% |

The weight sorts dogs the same way whether the projection was right or wrong (10 points over the no-gap dogs when
right, 17 when wrong), and re-read off the men who actually started it sorts the same again (+1.0% / -4.6% / -11.1%).
The gated dogs that cleared the gate only because of the +1 went 80-71 +21.7% (train +25.4% / held +10.3%). **So
"the goalie weights read only a confirmed starter" would throw away a weight that works** - at 8 AM three sides in
four have no confirmed man, the weight would simply be off. Not wired. The built roles weight (+2, a KNOWN starter
only) is untouched.

## 3. (c) Would waiting for the confirmed starter have made money? No. (`s8_live_page.out`, `s7_history.out`)

Live, 604 game sides 10/6 -> 11/18:

| what the goalie page said at the 8 AM PT board | sides | the name started |
|---|---|---|
| confirmed | 89 (15%) | 87 / 89 = 97.8% |
| likely / expected | 60 (10%) | 58 / 60 = 96.7% |
| a guess (unconfirmed / projected) | 453 (75%) | 360 / 453 = **79.5%** |
| our own projection on the same sides | | 371 / 602 = 61.6% |

- **When it is confirmed**: 530 of 604 sides before the puck; the Pacific clock of the first confirmation - median
  11:06 AM; 11% by the 8 AM board, 36% by 10 AM, 61% by noon, 67% by 2 PM. A confirmed name started 97.7% of the time.
- **What the price did**: a team whose 8 AM name started moved +0.09 points 8 AM -> close; a team whose 8 AM name did
  NOT start moved **-0.27 points** (19 of 95 moved 2+ points either way - the same share as when the name was right).
  The goalie news is a quarter of a point.
- **Our 43 hockey plays matched to the page**: both 8 AM names started 16-10; OUR 8 AM name did not start 7-6 (+14%
  flat); THEIR 8 AM name did not start 7-1. Nothing to wait for.
- **What waiting costs**: the paid morning 2021-23, the rested dog vs a back-to-back favorite (the hockey Dog's own
  cell) - +18.6% at the morning price, +16.4% at the close (3 of 3 seasons the morning is better); the dogs in it that
  got SHORTER by the close (112 of 205) were the winners (+24.9% at the morning, +18.7% at the close).

## 4. (d) The backup on the other side - the one cell that moved (`s2_plays.out`, `s4_weights.out`, `s5_backup.out`, `s10_older.out`)

| who the FAVORITE started (trap out: 24+ shots) | their #1 | their backup |
|---|---|---|
| **the posted hockey dogs, R3 2023-26** | 52-74 **-5.1%** (train -5.9% / held +0.5%) | 51-44 **+24.2%** (train +17.0% / held +24.4%, 3 of 3 seasons) |
| every gated hockey dog (score 6+), posted or not | 46-64 -5.7% | 46-37 +27.6% (train +17.6% / held +37.3%) |
| ...the favorite NOT on a back-to-back | 41-59 -7.0% | 32-21 +41.4% |
| every hockey dog, R3 2023-26 | 446-803 -14.7% | 275-383 +1.0% (train +2.4% / held -1.0%) |
| every hockey dog 2018-23 (the close) | -10.6% on 1,958 | **-9.3% on 1,106** |
| **the 2020-23 rig: every gated dog (morning price)** | 31-36 +7.2% | 28-31 +14.9% |
| ...the favorite NOT on a back-to-back | 20-24 +4.4% | 8-12 **-6.0%** |
| **the 2020-23 rig: dogs at a score of 0-6 (the floor's kind)** | 109-149 +1.7% | 61-111 **-16.3%** |
| no hindsight: the posted hockey dogs by the 8 AM projection | 116-122 +12.5% | 36-37 +11.7% |

With the trap in, the posted dogs are 77-65 +25.2% against a backup (a random same-size set of posted dogs is as good
57 times in 2,000) - it reads like an edge on the board it was found on. It is not wired because: (1) the population
gap is zero before 2023; (2) on the second rig - seasons this board never saw - the engine's dogs under the gate run
the OTHER way and the gated ones show a third of it; (3) nothing 8 AM knows carries it; (4) the hockey favorites on the
board show the same shape (their #1 31-34, their backup 50-23) where the whole market shows none - the mark of a
replay-era pattern, not a goalie fact. **A LEAD**: tracked from the 11/20 games with its control
(`sports_leads.NHL_VS_BACKUP_TAG` / `NHL_VS_N1_TAG`), judged at 100 graded - 10+ points of ROI apart = the five checks
as a weight on the hockey dog score at the confirmation (which would also mean hockey dogs posting at the
confirmation, not 8 AM).

## 5. No loud alert when our own goalie flips

A hockey play whose own goalie turns out to be the backup is not a worse bet (section 1: -1.3% vs -1.4% on every dog;
the posted dogs with our backup in went 50-45 +24.8% trap out; live 7-6 when our 8 AM name didn't start). A red ⚠️
would tell the owner to back off bets that paid. The quiet 🔄 Update line that keeps the card's goalie right (11/13,
11/17) stays; the early card's ⚠️ INJURY ALERT is for a man ruled OUT, and stays.

## 6. Size x the goalie, and the tiers as they stand (`s9_tiers.out`)

| hockey tier | all | projected: their #1 / their backup | started (24+): our #1 / our backup |
|---|---|---|---|
| **3u** - the 💎 b2b spot (35, live weeks in) | 17-14 +19.7% (train -6.8% / held +48.0%) | 5-4 +19.9% / 9-9 +7.8% | 8-5 +31.5% / 4-4 +5.2% |
| **2u** - the Dog +100..+150, the runner-up, the hockey Lock (212) | 102-98 +12.4% (+14.7% / +9.4%) | +16.0% / +14.8% | 42-37 +15.4% (+20.7% / +8.7%) / 28-28 +11.9% (+4.2% / +23.1%) |
| **1u** - the ⭐ on a favorite value play / a long Dog (105) | 53-50 +5.3% | -7.3% on 71 / +27.5% on 18 | -6.0% / +24.5% |
| **½u** - favorite value plays, the floor's dogs (188) | 84-86 -1.4% | -5.5% on 102 / +24.2% on 33 | +2.2% / +41.8% |

No tier wins more with our #1 in net in both halves (the 2u tier flips between the halves; the small tiers run the
other way), and "their backup projected" helps only the two small tiers on 18 and 33 plays. **No size follows the
goalie.** The 3u spot is 12-8 with both goalies as projected and 8-7 otherwise - 35 plays, no cut.

**The size tiers after this study (unchanged - the 11/17 max-profit plan; R3, every sport, the ⭐ raise in):**

| size | what's in it | train + held | train | HELD OUT |
|---|---|---|---|---|
| **3u** | the 💎 hockey Dog on the b2b spot at a score of 8+ | 17-14 +19.7%, +18.3u | 7-9 -6.8% | **10-5 +48.0%** |
| **2u** | the hockey Dog +100..+150, the hockey runner-up dog, the college hoops dog slot at a read of 5+, the ⭐ on a Lock / Dog, the college football Dog +100..+150, the 2u 🔍 college hoops play | 174-141 +20.7%, +130.4u | 97-85 +18.8% | **77-56 +23.3%** |
| **1u** | the college hoops dog slot at a read of 4, the NBA favorite play, the ⭐ on a favorite value play / a long Dog, the 1u 🔍 college hoops play | 178-135 +15.6%, +48.9u | 113-102 +8.8% | **65-33 +30.7%** |
| **½u** | the NBA floor dog, hockey favorite value plays, the floor's hockey / NFL dogs, the NFL Lock | 218-231 +7.1%, +15.9u | 135-152 +5.8% | **83-79 +9.3%** |

The board: +70.5u a year, +16.9% on every unit, train +92.3u / held +121.2u, worst stretch -24.3u, 4 of 4 seasons.

## 7. When the price is best (`s6_tape.out`, `s7_history.out`)

**Our own plays, 10/1 -> 11/18 (120 graded moneyline unit plays with a tape price 2 hours out and at the close):**

| | plays | post -> 2h before | post -> close | longer / shorter / same | flat ROI at the post / 2h before / close |
|---|---|---|---|---|---|
| every play | 120 (57-63) | -0.7 cents | -0.9 cents | 26 / 40 / 54 | **+4.1%** / +3.4% / +3.4% |
| hockey dogs | 37 (20-17) | -1.0 | +0.6 | 11 / 10 / 16 | +20.3% / +18.9% / +18.7% |
| hockey favorites | 11 (9-2) | +0.5 | -2.3 | 2 / 5 / 4 | +39.6% / +39.9% / +38.9% |
| NBA dogs | 14 (4-10) | +1.9 | -2.0 | 2 / 8 / 4 | -31.1% / -32.1% / -32.9% |
| college football dogs | 37 (13-24) | -0.4 | +1.2 | 10 / 7 / 20 | -4.9% / -5.0% / -3.8% |
| the Lock (every sport) | 14 (7-7) | -3.4 | **-7.6** | 1 / 9 / 4 | -12.4% / -13.6% / -14.7% |
| the Dog of the Day | 30 (15-15) | +0.5 | +2.3 | 9 / 6 / 15 | +21.9% / +21.5% / +22.6% |
| the floor | 21 (10-11) | -1.6 | -0.8 | 6 / 9 / 6 | +8.2% / +6.0% / +5.9% |
| value plays | 30 (20-10) | -0.9 | -2.3 | 4 / 10 / 16 | +32.7% / +32.8% / +32.2% |

In units: +15.3u at the posted prices, +14.5u two hours out, +14.9u at the close, on 107.5u. Only 3 college hoops
moneyline plays so far (2 got shorter) - too few to say.

**The whole market since 10/1 (8 AM PT on game day -> the close; + = the market came TO the side):**

| | dogs +100..+350 | favorites -101..-150 |
|---|---|---|
| hockey (338 games) | -0.06 points; 32% longer / 25% shorter | -0.09 |
| NBA (286) | **+0.86 points**; 50% shorter / 37% longer; ROI +4.2% at 8 AM vs +1.1% at the close | -0.53 |
| college hoops (738) | +0.56 (home dogs +1.02) | -0.10 |
| NFL (95) | -0.27 | +0.38 |
| college football (789) | +0.09 | -0.06 |

**History**: the paid NHL morning look 2021-23 - every dog -10.8% at the morning vs -11.0% at the close; the Dog's
own cell (rested vs a back-to-back favorite) +18.6% vs +16.4%. "Bet it only if it got longer" is not a rule: in the
Dog's cell the ones that got longer are 52 plays that flip season to season (2021-22 -15%, 2022-23 +60%).

**What the replay board cannot say, said once**: on R3 the market "comes toward" our hockey and NBA plays by 2-3
points from the night-before number to the close and "runs away from" our college hoops dogs by 4 - but R3 picks its
sides AT the close (the hockey dog score reads the move itself, the college hoops read is measured against the
closing price), so that is the picking, not the clock. The real 8 AM picks are the tape above.

**Verdict**: no kind gets a better number later in a way that would have made money; posting later loses the Locks'
and the NBA dogs' number and gains nothing on hockey. The 8 AM post stays. No "best time to bet" note is wired - six
weeks of tape cannot show two halves.

## The owner's options (not wired - each needs his word)

1. **A plain "this number usually gets shorter - bet it now" note under the Lock and NBA dog cards.** Live: 9 of 14
   Locks and 8 of 14 NBA dogs closed shorter than we posted. It is his ticket, not the engine's record, and six weeks
   is thin - a note, never a rule.
2. **Post hockey dogs at the goalie confirmation instead of 8 AM** - only if the tracker lead proves out at 100 graded.
   Today it would move the hockey post to around 11 AM-2 PM Pacific for a split that fails on the older seasons.

## Files

`glib.py` (the rig), `s0_build` (the projection's accuracy), `s1_starter` (who started x three prices), `s2_plays`
(the engine's plays x the goalie), `s3_leak` (the hindsight trap, the projection cells), `s4_weights` (no-hindsight
cells, the goalie weights), `s5_backup` (the favorite's backup by season), `s6_tape` (the line tape), `s7_history`
(open / morning vs the close), `s8_live_page` (the goalie page's history x the tape x our plays), `s9_tiers` (size x
the goalie, the tiers), `s10_older` (the second rig) + `*.out`.
