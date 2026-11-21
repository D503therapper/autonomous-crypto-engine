# 11/20 - FABLE: THE EARLY PLAYS + THE THIN BOARD DAYS

The owner, 11/20: *"I think it's ridiculous. We don't really have any plays today besides the early plays. When early
plays have been trash, and we have that one value play on the college basketball."* (Board 11/20: Niagara +2.5 ½u.)

**The answer, plain.** (1) One early spot comes off: **the 🔨 hammered spot is paused** from the 11/22 games - it was
never betting the thing its study found. Every other spot that is on stays, at the size it has. (2) Thin days: on the
replay board nothing next in line makes money in both halves - **a thin day is the price of not betting losers**.
Nothing was loosened. No posted pick, price or size changed; nothing was pulled.

## 1. The early plays, spot by spot (live = data/sports/early.json, graded through 11/21 morning)

All early plays: 25-35. By spot at the units posted:

| spot | live | what its history says | does the live bet match the study? | verdict |
|---|---|---|---|---|
| 🔨 hammered (½u) | **1-5, -1.0u**, all college; 5 of 6 closed worse than we paid (Wyoming +245 closed +310) | 25-23 +23.0% on 48 (NFL 26, college 22; z 1.3) | **NO** - see below | **PAUSED** from the 11/22 games |
| ⛰️ altitude over (1u) | 1-2, -1.1u; beat the close 3 of 3 (+1.7 points) | 499-342 +13.1%, 9 of 9 seasons; a point worse than the close +8.2% | yes - 4,600 ft floors, a better number than the close | keep 1u (1 of 3 at a 59% bet happens 37% of the time) |
| 🏀 main-guys-sit over (½u) | 2-1, +0.4u | 354-254 +11.0%, 8 of 8 seasons | the two game-day posts matched the close; the loss was the one posted two days early (227.5, closed 216) - fixed 11/19 (4 hours to the tip) | keep ½u |
| 🏀 NBA opening line (½u) | 3-5, -1.5u (3.7 wins expected); beat the close +1.8 on 7 | +13.7% on 282 at the open 2023-25; -6.9% on 361 on the unseen 2020-23 seasons; with one voice 20-14 on 34 | all 8 posted BEFORE one voice (11/12); none has posted since (one voice lets about 1 in 10 through) | keep ½u, its judge (20 graded under 40%) |
| 🛌 bye (½u since 11/17) | 3-3, +2.3u (NFL 2-2, college 1-1) | NFL +15.6% on 52 (both halves) but 21 seasons of closes -7.7% on 184; college +6.0% on 186, the halves flip | the price is right (first fair number). A WATCH: of the replay's bye dogs, the ones one voice lets through went 3-12, the ones it stops 20-27 | keep ½u (live is not under its study) |
| 🌍 Europe under (½u) | 4-1, +1.3u | 17-9 since 2018; its quit rule | yes | keep |
| exam scan (½u flat since 11/16) | 4-1, +9.3u (all on the old Kelly sizes) | flips by half (-0.4% / +10.3%) | ½u + the honest check since 11/16 | keep ½u |
| Monday night / East-West (½u) | no play yet | +12.7% on 112 / +11.2% on 103, the halves flip | - | keep ½u; nothing live to judge |
| blowout, engine | 3-11, 3-6 | - | - | already paused |

**Why hammered is paused (`e1_hammered_tape.py`).** The study (10/1 study 4; early_1111 s3 / s6d, the paid odds
history) is a dog the money came 4+ points to between **Tuesday's** first fair look and a look **two days later**. The
owner's 3-day rule has the live spot fire Saturday night to Tuesday - a stretch the paid history cannot see. On our own
line tape all 11 live fires came 2 to 27 hours after the book's **first number of the week**, 7 of the 11 measured off
that opener itself: Tulane "came 14.2 points" = +425 at 8:41 AM Sunday, +195 by 4:31 PM; Boston College +240 -> +195 in
8 hours; Wyoming +360 -> +285 in under 3 hours. That is an opening number settling, not money. The only record of that
window is one season of our own tape (10-14, +13.0% on 24, z 0.45 - our own plays are in it). Live it is 1-5 and it buys
after the move: 5 of 6 closed worse than we paid. Its judge (20 graded) would not read before next season. Back on = the
owner's call, or a study of the Sunday window once the tape holds a second season.

Wired: `sports_early.SPOTS_OFF_FROM["hammered"] = "2026-11-22"` (dated by the game's Pacific day - the open Tulane
+195 and Arizona St +142 stay as posted; a paused spot adds no weight to another spot's total).

## 2. The thin days (`s1_thin_days.py`, `s2_floor_deeper.py`)

The rig: the 11/17 replay board (dogs_1117 R3 rows through money_1117's live shape - every board day 2023-10 to
2026-11 on today's code at the close; 1,192 unit plays on 881 days). Not on it: baseball, the spread stack play, the
totals, the early plays - a real in-season day carries a little more.

**How often.** In season (10/15 - 4/15): **no unit play on 14% of days, exactly one on 32%, two or more on 54%**
(train 13 / 34 / 52, held 16 / 28 / 56). Of 50 in-season days with no hockey game (11/20 was one), 41 were thin.
11/20 itself: no hockey; all seven NBA dogs scored under 0 (best -0.21, no named reason); no college hoops dog read 4.

**The day's only play** made +11.0% on its units (train +1.8% / held +27.2%); days with 3+ plays +18.8% in both
halves. Thin days are the weaker days - the slate has less to like.

**The next side in line on a thin day (the best one a day), flat:**

| candidate | record | train / held | random as good (of 2,000) | every such side, every day |
|---|---|---|---|---|
| best dog in the floor's pool the rules hold back | 124-165, +0.7% on 289 | -0.2% / +2.4% | 498 | -1.8% on 2,889 |
| a floor dog under a score of 0 (the second play) | 37-48, +11.2% on 85 | +1.4% / +30.1% | 100 | **-10.7% on 323** |
| a college hoops floor dog | 65-76, +1.3% on 141 | +1.8% / +0.1% | 577 | -2.7% on 1,003 |
| a college football floor dog | 20-37, -12.4% on 57 | -24.1% / -1.1% | | -1.7% on 598 |
| a second NBA dog / an NBA dog under the floor's score | 53-92, **-11.4% on 145** | -12.7% / -9.0% | | |
| an NFL home floor dog | 9-16, -8.9% | +3.8% / -41.6% | | -13.3% on 101 |
| a hockey pool dog under 0 | 32-35, +13.7% on 67 | +15.5% / +9.5% | 187 | **-11.6% on 247** |
| a hockey dog with no named reason, score 3-6 | 39-37, +19.9% on 76 | +14.2% / +37.0% | 379 | +2.2% on 204 (train -0.5%) |
| a college hoops dog at a read of 3-4 / 2-3 | up on these 3 seasons | | 1,114 / 1,727 | settled 11/17 on 8 seasons: read 2-3 +0.2% on 1,490 (train -6.6%); the road dog at 3 is already in |
| a favorite under the 1-point edge bar (college hoops) | 4-6 | | | -13.7% on 40 |
| a small favorite with the own read just under the price | hockey +5.2% on 189, NBA -6.0%, hoops -5.2% | | 171 | -2.4% / -3.8% / -3.8% |
| a no-play day: the best dog left by score | 84-115, +1.2% on 199 | +2.1% / 0.0% | 327 | |

Nothing clears the standing bar (both halves, a placebo under 100 of 2,000, a point worse than the close, a real
sample, and the same rule not losing on every other day).

**The one cell that looked like something (`s2_floor_deeper`)**: a hockey dog in the floor's pool at a score of 0+
that the floor left because the board already had its two - 124-119, +16.8% on 243, both halves. It is not a thin-day
fix (by build it only shows up on days that already have plays), the floor's own POSTED hockey dogs at 0+ on the same
rig are 28-43 (-7.9%), and what carries it is the score 4+ dogs - the "next hockey dog" the 11/15 and 11/17 studies
already ran on the seasons no weight saw (2020-23: -7.2% on 140). It stays the tracker lead it is. Not wired.

## Wired / not wired

- WIRED: the hammered spot paused from the 11/22 games (test
  `test_early_thin_1120_the_hammered_spot_is_paused_and_nothing_is_loosened_for_a_thin_day`).
- NOT wired: any new play or looser gate for a thin day; any size change.
- WATCH: the bye spot under one voice (3-12 in the replay for the dogs one voice passes - 15 bets, not a rule).
