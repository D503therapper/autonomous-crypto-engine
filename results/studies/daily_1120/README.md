# 11/20 daily studies

The owner's daily routine: the board check, yesterday's picks, the lead tracker and ten NEW studies. Two of the ten
were asked by today's board check (the Niagara +2.5 play stood on a star who sat a non-D1 tune-up).

**In one line:** a college hoops team coming off a non-D1 tune-up covers against a team coming off a real game (a new
±0.02 spread-rank weight - it moves no pick while leans are off), a top scorer who sat a tune-up no longer counts as "missed the last game", a
spread card now says its covers, three tracker lines, no posted pick or size changed.

Prices: ESPN's close at its own juice, regular season, a team's games THIS season before tonight (no look-ahead);
ESPN's open (2023-26) as the second price where it exists. Train 2018-21 / held out 2022-26, each held season shown
apart (the box-score studies: train 2021-23 / held 2024-26). Placebo = 2,000 random same-size sets from the cell's own
band. **About 530 cells were cut - about 25 clear |z| 2 by luck.** The paid odds history was not re-read: its
book-by-book / line-shape / steam / timing questions are all answered (10/8-11/17) and nothing new is in the files.

Most of today's ten are facts the CARDS print that had never been set against a price - the third period, the 4th
quarter, "120+ allowed in 3 of the last 5", who a team beats.

| # | study | verdict | the number |
|---|---|---|---|
| S1 | college hoops: the top scorer "missed the last game" - when the game he missed was a non-D1 tune-up | **BUILT (a definition fix)** | the spread side across him: a D1 game missed +1.6% on 1,821 (held +4.2%, placebo 5 of 2,000); a tune-up missed -11.9% on 91 (train -2.9% / held -23.4%) |
| S2 | NHL the third period (goals for minus against, last 10) | DEAD (a watch) | +5 or better as a dog -6.4% on 960 vs -5.6%; the dog that LOST the third in 7+ of 10 +6.8% on 442 (train +0.3% / held +11.1%) |
| S3 | the closers elsewhere - NBA 4th quarter, football / college hoops 2nd half | **LEAD** | the closer against a fader ATS: NBA -15.0% on 522 (train -21.3% / held -9.6%, placebo 9), college football -24.2% on 161 (placebo 8), NFL -17.5% on 88; college hoops -4.9% (the vig) |
| S4 | the record against winning teams, every league | DEAD (two watches) | NHL dog .600+ vs winners -8.6% on 633 vs -5.6%; NBA small favorite .300 or worse vs winners -12.7% on 404 (placebo 77) |
| S5 | scoring bursts (NHL 4+ goals / NBA 120+ in 3 of the last 5) | DEAD (a watch) | NHL dog that scored 4+ in 3 of 5 -6.6% vs -5.6%; NBA dog facing a team that allowed 120+ in 3 of 5 -4.1% vs -4.2%; the small favorite facing it -11.4% on 483 (both halves, placebo 101) |
| S6 | NHL how hard the back-to-back team was worked last night (ice time, overtime) | DEAD | rested dog vs a b2b team whose top D pair played 25:00+ -11.3% on 75, under 23:00 +16.0% on 171 (placebo 145) - the wrong way for "tired" |
| S7 | NHL the game after giving up 6+ / scoring 6+ | DEAD (a watch) | gave up 6+: dog -2.9% on 901; scored 6+: dog -12.6% on 629 (train -19.0% / held -8.4%, placebo 153) |
| S8 | the total after both teams' last games sailed over / under | DEAD (a watch) | NBA both 15+ under -> the over -14.0% on 435 (placebo 14), the under +5.1% (train +0.4%); college hoops both 12+ over -> the over -10.1% on 1,219, the under +1.1% |
| S9 | college hoops: the game after a non-D1 tune-up | **BUILT (a spread-rank weight) + a LEAD (the dog)** | vs a team off a D1 game: ATS +5.4% on 1,944 (train +3.9% / held +6.4%, 5 of 5 held seasons, placebo 0); dog +100..+350 +15.0% on 570 (placebo 0), the open +4.1% on 233 |
| S10 | NHL the rested side's real rest against a back-to-back team | DEAD | 1 night off +6.8% on 255, 2+ nights off +5.0% on 133 - no step |

## S9 + S1 - the non-D1 tune-up (s_game.py ncaab -> fA_tuneup.py)

A Division I team (`sports_model.ncaab_d1`: 20+ games in a season on file) whose LAST game was against a non-D1
school. That game carries no price and never moves the ratings. Tonight it plays a D1 team.

Against a team whose own last game was a D1 game (the cell that was wired):

| price | all | train 2018-21 | held 2022-26 | 2022 | 2023 | 2024 | 2025 | 2026 | placebo |
|---|---|---|---|---|---|---|---|---|---|
| the spread | **+5.4% on 1,944** (z 2.5) | +3.9% (3 of 4 seasons) | +6.4% | +9.5 | +0.6 | +2.4 | +6.3 | +17.3 | 0 of 2,000 (November sides) |
| dog +100..+350 | **+15.0% on 570** (z 2.5) | +19.1% (4 of 4) | +12.4% | +9.7 | +4.3 | +36.5 | +6.7 | -3.1 | 0 of 2,000 (same month, same price) |
| the dog at ESPN's open | +4.1% on 233 | - | +4.1% | - | -11.0 | +27.4 | +0.7 | -8.0 | - |
| favorite -150..-101 | -3.6% on 178 | -10.3% | +0.5% | | | | | | 880 |
| the side across, the spread | -14.5% on 1,944 | | | | | | | | 0 (as badly) |

Cuts: at a neutral site the sign flips (-11.7% on 110) - never wired there. Won the tune-up by 30+ ATS +5.3% on 1,328,
by less +7.1% on 583. The opponent off a D1 loss ATS +7.1% / dog +22.3% on 264; off a D1 win +4.0% / +8.6%. On 1-2
days' rest ATS +23.1% on 126; 3-4 days +3.9%; 5+ days +4.7%. Any plus price at all is -17.6% on 1,280 - past +350 a
tune-up team is a buy-game long shot and loses like every one of them.

Five checks, the spread cell: (1) the close at its own juice, the team's own schedule before tonight - fair; (2) both
halves up; (3) 8 of 9 seasons up; (4) 2026 +17.3% on 163; (5) the second read is the moneyline dog (the same side
beats its price) - there is no opening spread on file. Passes as a small weight. The dog: both halves at the close
and a clean placebo, but the open is +4.1% with two of four seasons down and 2026 is down at both prices - a LEAD.

**Wired** (`sports.NCAAB_TUNEUP_FROM = "2026-11-21"`, the game's Pacific day; "9999" = off):
`sports.mark_ncaab_tuneup` stamps `tuneup` / `vs_tuneup` on college hoops sides (true home / road floor only);
`sports.ncaab_tuneup_spread_w` is +0.02 / -0.02 inside `rank_p`. So a college hoops spread LEAN has a studied reason
for the side. It is NOT in `ncaab_spread_stack` (the ½u stack play's replay never saw it) and nothing is picked off it
alone. **Honest about today:** leans are off (11/16), so the weight changes no pick - it orders two equal stacks on a
night with more stack plays than the cap, and runs on the tracker. The money step is the stack: the ½u stack play's
own replay with the tune-up flag added, once the tracker line has graded rows.

**S1 - the built "top scorer missed the last game" weight** (`sports_ncaab_roster.top_out`, box scores 2021-26;
train 2021-23 / held 2024-26). The side ACROSS that team on the spread:

| the game he missed | all | train | held | placebo |
|---|---|---|---|---|
| a D1 game | +1.6% on 1,821 | -0.5% | +4.2% | 5 of 2,000 as well (base -4.6%) |
| a non-D1 tune-up | -11.9% on 91 | -2.9% | -23.4% | 442 of 2,000 as badly |

Ninety-one games say nothing alone. Set beside S9 they say one thing: a team off a tune-up is under-priced, and a star
who sat the tune-up was resting. **Wired** (`sports_ncaab_roster.TUNE_FROM = "2026-11-21T12"`, the game's UTC start;
None = off): `top_out` answers "not out" (with `tune: True`) when the last game was a tune-up, so the dog fade, the
favorite's weight, the spread rank and the stack's "across" +0.03 stop firing there. No D1 set to read = the old
answer. Tonight's Niagara play (start 11/21 00:00Z) keeps its reason and its units.

## S3 - the closers (s_game.py)

The card prints "won the 4th quarter in 7 of the last 10". Against the number it runs the other way. A side at +25 or
better in the 4th quarter over its last 10 (football: the 2nd half over its last 4, +21 NFL / +28 college) against a
team at the same margin the wrong way:

| league | the closer ATS | train | held | placebo | the fader ATS |
|---|---|---|---|---|---|
| NBA | -15.0% on 522 (z -3.6) | -21.3% (0 of 4) | -9.6% (0 of 5) | 9 of 2,000 | +6.1% (train +12.4% / held +0.9%); its dog +13.7% on 239 (placebo 41) |
| college football | -24.2% on 161 (z -3.3) | -27.6% | -21.9% | 8 | +14.6% (placebo 11) |
| NFL | -17.5% on 88 | -22.3% | | 171 | +9.1% (placebo 159) |
| college hoops (2nd half, last 5, 20) | -4.9% on 2,103 | -6.8% | | - | the vig |
| NHL (3rd period, last 10, 5) | +1.1% on 622 | | | 221 | nothing |

The late scoreboard is the bench's minutes and the number over-reads it. Three leagues agree and two clear the
placebo, but there is no second price and the fader's side fades to the vig in the NBA's held half - a **LEAD**:
`sports_leads.LATE_CLOSER_TAG` on the closer's spread side (NBA / NFL / college football) from the 11/21 games. Judge
at 60: under 45% covered = the five checks as a -0.02 spread-rank weight.

## Dead (do not re-run)

- S2: NHL third-period margin by itself nothing; "won the third in 7+ of 10" on the puck line -11.9% on 742 (both
  halves, placebo 24) - no puck lines on the board. The dog that lost the third in 7+ of 10 is a watch (train flat).
- S4: who a team beats is in the price. NFL dog .600+ vs winners -28.9% on 110 (placebo 39, train -14.9%) - thin.
  College hoops "flat-track bully" favorite -12.8% on 193 (placebo 185).
- S5: the card's "💣 4 or more in 3 of the last 5" / "120+ allowed in 3 of the last 5" lines argue nothing against a
  price. The one cell off its base is the NBA small favorite FACING a leaky defense (-11.4% on 483) - a watch.
- S6: the ice-time load reads the wrong way (a team that leans on its top pair is a good team). Overtime last night:
  the b2b dog -12.1% on 207 vs -19.0% for every b2b dog; the rested dog across +5.1% on 77 vs +6.2%.
- S7: the hockey dog off a 6+ goal game -12.6% on 629 sits with the built hot-dog and blowout reads (placebo 153).
- S8: totals keep going the way they went in the NBA and snap back in college hoops, but the paying side is +5.1% /
  +1.1% - nothing to bet. The NBA "both sailed under -> never the over" is a watch (-14.0% on 435, placebo 14).
- S10: the rested side's extra night adds nothing against a back-to-back team.

## The board check (11/20)

- **Niagara +2.5 (-115) ½u, the college hoops spread stack play:** passes every posting rule (stack +0.05 on two
  weights, ½u, -115 inside the juice limit, one of at most three, injuries / D1 / price checks pass, no ⭐). Two
  things wrong around it: (1) **the card had no fact line at all** - one line under the pick and the bottom line
  (card audit: SHORT, 0 of 6); (2) its +0.03 weight is Delaware St's top scorer sitting a 90-70 win over Cheyney
  (PA), a non-D1 school - S1 above. The pick, the price and the ½u stay.
- **Fixed for the card:** `sports_breakdown_v24.fill_facts` gives a spread play its own facts - our covers running
  ("Niagara beat the spread in their last 2 games - the last one getting 39.5 at Iowa State, the game ended 21
  apart") and a record of theirs built on non-D1 schools ("Both of Delaware St's wins came over schools that aren't
  Division I"). Breakdown VERSION 78 rewrites the open cards (wording only). The Niagara card goes from 0 fact lines
  to 2 - still short; the files hold nothing more for a winless side.
- **In the early box, playing tonight (both known to the owner, both rules already fixed 11/19, both still open):**
  Wyoming +245 ½u (now +280; QB Tyler Hughes out on this week's official report - the reason it was pulled once on
  11/16) and the Raptors @ Pistons over 227.5 ½u (posted two days early; Cade Cunningham is off the report and the
  number on file is 216.5).

## The lead tracker (lead_tracker.py)

Nothing at 100+ graded is a clear steady winner or loser - no raise, no cut. "money 10+ over tickets" 201-264 -0.2%
on 465; "reverse line move to it" 115-148 +3.3% on 263; "70%+ of tickets" 131-112 -4.5% on 243; "hockey fav weighed
UP" 72-41 +0.6% on 113; "NBA spread fav 3.5-12.5, games 1-20 (fade)" the faded side 55-50 +0.0% on 105. Under 100:
"college hoops spread side on 4-5 nights rest vs a team on 2 (fade)" 13-26 on 39 runs with its fade; "college
favorite off a loss (fade)" 26-12 +23.4% on 38 still runs against its fade; "college hoops road dog, games 1-3
(fade)" 28-45 +15.3% on 73 against it. The Ducks carried two fade LEADS at the post ("NHL dog, 4th game in 6 nights"
5-8 on 13; "NHL rested dog, its #1 goalie sat the last 2+" 2-3 on 5) - far too few to weigh. The NBA floor is 1-6
live (its judge: 20 graded under 35%).

## Files

lib.py / h.py (the 11/19 helpers), s_game.py (S2-S5, S7-S9; one run a league) and
s_game_<league>_out.txt, fA_tuneup.py (S9's follow-up + S1), s6_nhl_ice_load.py (S6, S10), lead_tracker.py and their
*_out.txt. Tests: test_daily_1120_* (three) in sports_test.py.
