# 11/17 - THE MAX-PROFIT SIZING PLAN: the biggest sizes the replay will pay for, wired

The owner, 11/17 (his OK on the options the most-money study left as his): *"whatever Fable recommends for the biggest
returns on the best bets, the largest sizes, whatever. We're going to wire that into the engine. We're going to wire
everything into the engine to make the engine better and maximize profits. And tomorrow's board or today's board will
reflect this. Go now."* Earlier the same day: *"when I see a play that has more units on it, that means I'll put more
money on it. And none of these picks can be costing me or my friends money."*

**The answer, plain.** Every option on the table was run TOGETHER on the same three replay years (they interact - the
⭐ goes on the day's biggest play). Three bigger sizes are wired from today's games (11/17): **the hockey runner-up dog
at +100..+150 is 2 units** (the Dog of the Day's twin, now at the Dog's own size), **the college football thin Lock is
1 unit** (was a half), and **the ⭐ best pick is 2 units when it sits on a Lock, a Dog of the Day or a play that is
already a full unit, at +150 or shorter**. Together: **+59 units a year becomes +70.5 units a year**, the return on every
unit risked goes UP (+15.2% -> +16.9%), both halves of the replay and all four seasons are up, and the worst losing
stretch goes from about 22 units to about 24 (x1.12 - the limit was x1.5). Every unit this plan adds earned +41% in
the replay, and each of the three pieces is up in both halves on its own. **What stays small, on purpose:** the daily
floor, the NBA floor, the half-unit hockey favorite value plays and the NFL Lock - each of them is flat or losing in
the later half, and a bigger number never goes on a group like that because you bet more when you see it. A 2-unit ⭐ on
*every* play would have added about 4 more units a year, but those extra units sit on half-unit value plays, floor
plays and long dogs that LOST in the first half of the replay and it makes the worst stretch a third deeper - left out.

## The rig and the rule

- **The board**: money_1117's R3L (`../money_1117/mlib.py` - the board today's code builds, every board day 2023-10 ->
  2026-11 at the closing price, the live post's shape; 1,192 unit plays on 881 board days; train = to 6/30/2025, held
  out = 7/2025 -> 10/12/2026, the live weeks apart). `plib.py` makes each size a switchable PIECE and re-picks the ⭐ on
  the new sizes. TODAY = the 11/17 code with the most-money study's one change in (the short hockey runner-up at 1u).
- **THE RULE**: the bundle with the most units won, subject to - up in both halves and every season; the worst stretch
  within today's x1.5; no bigger size on a group whose held-out ROI is negative; and inside a bundle no piece whose
  ADDED units lose (or are flat-to-losing in a half - a bigger number has to be earned in both).
- **Said once (the same limits as money_1117):** the dog score's weights were fit with these seasons seen - "held out"
  is the later half, not a clean blind test. Not on this rig: the college hoops spread stack, the totals, the early
  spots, mid-day adds, baseball - none of them changes size here.

## 1. Every piece alone (`s1_pieces.out`)

| piece | the group (flat) | train | HELD OUT | the added units earn | the board with it | verdict |
|---|---|---|---|---|---|---|
| **the hockey runner-up dog +100..+150 at 2u** (1u) | 54: 34-20 +36.9% | 17-10 +37.5% | **17-10 +36.2%** | +19.9u on 54u (+37.5% / +36.2%) | +65.7u/yr, worst x1.03 | **IN** |
| **the college football thin Lock at 1u** (½u) | 13: 11-2 +42.6% | 7-2 +31.3% | **4-0 +67.8%** | 1 play changes without the ⭐ (the ⭐ had the other 12 at 1u) | +59.2u/yr, x1.00 | **IN** (9-season football board 20-5 +35.9%, 8 of 9) |
| the ⭐ at 2u, on every play | 183 change | +3.7% | +40.3% | +27.6u on 183u | +68.2u/yr, **x1.42** | cut down - section 3 |
| the NBA floor dog at 1u | 165: 81-84 +19.0% | 60-56 +25.6% | 21-28 **+3.4%** | +15.7u (+25.6% / +3.4%) | +64.3u/yr, x1.03 | **OUT**: held out + the live-replay weeks 25-39 **-6.4%**, every season worse than the last (+19.2u, +10.6u, +1.7u, -5.7u), live 1-4 |
| the hockey favorite value play at 1u | 152: +2.7% | **-1.4%** | +9.4% | +0.4u on 41.5u (+4.6% / **-3.3%**) | +59.2u/yr | **OUT**: the added half unit loses held out (the ⭐ already has the good ones) |
| the other favorite value plays at 1u | 32: +36.2% | +19.1% | +47.8% | +1.2u (**-30.9%** / +39.6%) | +59.5u/yr | out: 19 plays, the added units lose in train; +0.4u a year |
| the hockey runner-up past +150 at 1u | 17: 8-9 +25.4% | 7-8 | 1-1 | +2.1u | +59.8u/yr | out: 2 held-out plays; 2-6 on the oldest board, 3-7 on the unseen seasons (money_1117) |
| the hockey Dog past +150 at 1u | 44: +3.5% | +0.5% | 4-5 +15.6% | 1 play changes | | out: nothing to gain; the 10/30 price split |
| the NFL Lock at 1u | 14: 8-6 -3.7% | -3.4% | **4-3 -4.0%** | -0.3u | | **OUT**: loses held out |
| the floor's dogs at 1u | 165: 64-101 -5.5% | **-15.9%** | +14.7% | -5.0u on 76u | +57.4u/yr, x1.19 | **OUT**: loses money at the bigger size; never sized up (money_1117) |
| the NBA favorite play at 2u | 69: +27.5% | +16.5% | 22-4 +45.7% | +19.0u | +65.4u/yr, x1.01 | not on the table: the seasons nothing saw keep +1.8% (11/15 - "no 2u") |
| the college hoops read-4 slot dog at 2u | 68: +27.0% | +32.2% | 9-10 +13.6% | +18.4u | +65.1u/yr, x1.00 | not on the table: the 8-season rig has the band at +10.3%, train +3.8% (11/17 sizing) |

**"Every ½u play at 1u" comes apart when it is opened up.** Its 352 plays (the floor left out) are 165 NBA floor dogs
and 152 hockey favorite value plays - the two groups above that fail the rule - plus a handful of others. What is left
of it that passes is the college football thin Lock.

## 2. The bundles, together (`s2_bundles.out`)

| bundle | units a year | ROI | train | held out | worst stretch | worst season | seasons up | the rule |
|---|---|---|---|---|---|---|---|---|
| TODAY | +59.1u | +15.2% | +76.1u (+10.5%) | +102.9u (+22.8%) | -21.7u | +6.4u | 4/4 | |
| A every ½u at 1u (floor in) | +64.4u | +13.9% | +84.4u | +110.8u | -29.3u (x1.35) | +5.3u | 4/4 | sizes up the floor (-5.0u added), the NBA floor, the NFL Lock |
| B every ½u at 1u but the floor | +66.1u | +15.1% | +93.5u | +106.8u | -23.8u (x1.10) | +6.3u | 4/4 | sizes up the NBA floor and the hockey favorites (section 1) |
| C the runner-up 2u | +65.7u | +16.2% | +86.2u | +112.7u | -22.3u (x1.03) | +6.6u | 4/4 | ok |
| D the ⭐ 2u on every play | +68.2u | +15.2% | +80.7u | +125.9u | -30.7u (x1.42) | +10.3u | 4/4 | the added units +3.7% in train |
| E the college football thin Lock 1u | +59.2u | +15.2% | +76.1u | +103.3u | -21.7u | +6.4u | 4/4 | ok |
| B+C | +72.7u | +16.0% | +103.6u | +116.6u | -25.8u (x1.19) | +6.5u | 4/4 | as B |
| B+C+D | +81.8u | +15.9% | +108.3u | +139.5u | -32.2u (x1.49) | +10.5u | 4/4 | as B and D - at the x1.5 line |
| A+C+D (everything) | +80.1u | +14.8% | +99.2u | +143.6u | -37.7u (**x1.74**) | +9.5u | 4/4 | FAILS the worst-stretch limit |
| C+D+E | +74.9u | +16.0% | +90.9u | +136.0u | -29.4u (x1.36) | +10.5u | 4/4 | the ⭐ piece: section 3 |
| **C+E + the ⭐ 2u on a Lock / Dog / 1u+ play at +150 or shorter - WIRED** | **+70.5u** | **+16.9%** | **+92.3u (+12.0%)** | **+121.2u (+24.7%)** | **-24.3u (x1.12)** | **+10.5u** | **4/4** | **every piece up in both halves** |

The most units on paper is B+C+D (+81.8u a year). It is not wired: 11 of its extra units a year come from the NBA
floor at 1u (held out + live 25-39, -6.4%), the hockey favorites at 1u (the added units lose held out) and a 2u ⭐ on
plays that lost in the first half - bigger numbers on groups that are not winning, with a worst stretch half again as
deep as today's. The wired bundle keeps 11.4 of B+C+D's 22.7 extra units a year for a quarter of its extra hole.

## 3. The ⭐ at 2u - where it is earned and where it is not (`s3_star.out`)

A 2u ⭐ on every play adds +27.6u in three years - **+3.7% in the first half**, +40.3% in the second - and a random
183 plays does as well a third of the time. Cut by standing rules (not by records picked off this board):

| the ⭐ under 2u, by where it sits | plays | flat | train | held out |
|---|---|---|---|---|
| a dog past +150 (the long dog - the 10/30 price split's ½u dog) | 63 | +1.0% | 16-32 **-7.9%** | 7-8 +29.5% |
| a floor play (never sized up) | 13 | +7.5% | 5-6 | 1-1 |
| a ½u hockey favorite value play ("value plays lose at every size") | 68 | +3.7% | 25-22 **-8.8%** | 16-5 +31.7% |
| **everything the wired rule leaves at 1u** (a ½u value play, a floor play, a dog past +150) | 154 | +8.7% | 52-57 **-1.3%** | 30-15 +32.9% |
| **the wired rule's 2u ⭐s** (a Lock, a Dog of the Day, a play 1u+ by its own size, at +150 or shorter) | 29 | **+49.2%** | **+35.7%** | **+68.3%** |

The wired 2u ⭐s on this board: the college football thin Lock 12 (10-2), the NBA Dog 10 (+59.4%), the college
football Lock 5 (4-1), the NBA favorite play 2. Their extra unit: **+14.3u on 29u**; a random 29 of the ⭐s under 2u
does as well about 2.7% of the time (five seeds: 54 / 62 / 50 / 47 / 57 of 2,000), of every unit play under 2u 3.5%.
A thin edge is NOT the dividing line (the thin-edge ⭐s did better than the real-edge ones in both halves) - the
price and the kind are. **Honest limits:** 29 plays in three years (about ten a year), most of them college football
Locks and NBA Dogs; the live board also has kinds this rig has no rows for (a Lock-grade night pick, the 🔍 play, the
college hoops dog slot as the ⭐) - the rule treats them the same way: 2u only if the play is 1u+ by its own size.

## 4. THE PLAN vs TODAY (`s4_plan.out`)

| | TODAY | THE PLAN (11/17) |
|---|---|---|
| units won a year | +59.1u | **+70.5u** (+11.4u) |
| units risked a year | 388u | 416u |
| ROI | +15.2% | **+16.9%** |
| the units the plan adds | | +34.5u on 83.5u in three years = **+41.3%** a unit added |
| train / held out | +76.1u / +102.9u | **+92.3u / +121.2u** |
| worst stretch | -21.7u | -24.3u (x1.12; train -24.3u / held -14.9u) |
| units won per unit of worst stretch | 8.3 | 8.8 |
| worst season | +6.4u | +10.5u |
| by season | +37.4 +38.7 +96.6 +6.4 | +51.8 +40.5 +110.7 +10.5 |
| the live-replay weeks (10/13 on, today's code replayed) | +16.2u on 78u | +21.2u on 89u |
| board days with a unit play | 70.8% | 70.8% (no play added or taken off) |

Each piece inside the plan (the plan vs the plan without it): the runner-up at 2u +19.9u on 54u (+37.5% / +36.2%); the
college football thin Lock at 1u +0.3u on its own (it is the ⭐ 12 times in 13 - its money is in the ⭐ row); the ⭐ at
2u +14.3u on 29u (+35.7% / +68.3%).

## 5. THE SIZE TIERS after the change (`s4_plan.out`)

By the kind's own size (the ⭐ raise left off), on today's code:

| size | what is in it (plays) | all | train | **HELD OUT** |
|---|---|---|---|---|
| **½u** | the NBA floor 165, hockey favorite value plays 152, the floor's dogs 165, the hockey Dog past +150 44, the NBA Dog 18, college hoops favorite value plays 18, the long runner-up 17, the NFL Lock 14, others 16 | 609: 305-304, +8.0% | +4.4% | **114-92, +15.1%** |
| **1u** | the NBA favorite play 69, the college hoops dog slot at a read of 4 68, the 🔍 college hoops gap play 23, **the college football thin Lock 13**, the college football Lock (not thin) 5, the college football Dog past +150 4 | 182: 114-68, +25.4% | +20.6% | **45-21, +33.7%** |
| **2u** | the hockey Dog +100..+150 165, **the hockey runner-up dog +100..+150 54**, the college hoops dog slot at a read of 5+ 37, the college football Dog +100..+150 12, the 🔍 gap play at a read of 6+ 11, the hockey Lock 5, the NFL Dog 2 | 286: 151-135, +17.8% | +17.1% | **66-55, +18.8%** |
| **3u** | the 💎 hockey Dog on the b2b spot at a score of 8+ 31 | 31: 17-14, +19.7% | 7-9, -6.8% | **10-5, +48.0%** |

As the board shows it (the ⭐'s raise in): **½u 83-79 +9.3% held out; 1u 65-33 +30.7%; 2u 77-56 +23.3%; 3u 10-5 +48.0%.**

**Straight about the ladder.** ½u -> 1u is a real step in both halves. The 2u tier is better than it was (+13.9% ->
+18.8% held out by the kind, +23.3% as shown) because the runner-up joined it at +36% - but it is still carried by the
165 hockey Dogs at +6%, which is where the worst stretch comes from (money_1117, section 8: the Dog at 1u is the
owner's option and gives up units - not asked for). Two things on the board that this plan did NOT touch and that are
weak on today's code, said plainly: the hockey Lock at 2u (2-3 on five plays) and the 💎 3u (7-9 in the first half,
10-5 in the second; its judge is at 25 graded).

## 6. WIRED (`sports.py`, from the 11/17 Pacific games)

`PROFIT_1117_FROM = "2026-11-17"` (None = off - no NEW stamp; a stamped pick keeps its size).

| piece | constant | the stamp (set when the pick posts) | read by |
|---|---|---|---|
| the hockey runner-up dog +100..+150, 2u | `DOG_PLAY_SHORT_UNITS_1117 = 2.0` | `pk["dog_play_2u"]` (post_board, the dogplay branch) | `dog_play_2u` -> `_units_base`, `sizing_check` |
| the college football thin Lock, 1u | `NCAAF_THIN_LOCK_UNITS_1117 = 1.0` | `pk["thin_lock_1u"]` (`mark_profit_1117`, before the ⭐ is picked) | `thin_lock_1u` -> `_units_base`, `sizing_check` |
| the ⭐ at 2u | `BEST_UNITS_1117 = 2.0`, `BEST_2U_MAX_ODDS = 150` | `pk["best_2u"]` (`mark_best`, only when it puts a NEW ⭐ on and `best_2u_ok`) | `best_min_units` -> `units_for`, `sizing_check` |

- A pick already up has no stamp and keeps the units it posted at. A ⭐ that went up before the change stays 1u.
- `best_2u_ok`: a Lock (never the backup Lock; the NFL Lock is never the ⭐ at all), a Dog of the Day, or a play whose
  own size is 1u or more - at +150 or shorter. Never a floor play, a ½u value play, a forced pick, a dog past +150.
- The 💎 3u stays 3u; the -150 rule, the 5u cap, a play every day, no leans: untouched. No play is added or removed.
- **The words** (`sports_card_check.SMALL_TALK`): a card that carries 1u or more never says a small bet's words ("half
  a unit", "small bet", "thin edge", "keep it light", "not a big one") - the card is written before the stamp goes on;
  the fact in the sentence stays, the small-bet clause goes, and a bottom line left empty is rebuilt from the numbers.
  The units line and the ⭐ line read the real size (the ⭐'s closer says "2 units").
- Test: `test_profit_1117_runner_up_2u_college_thin_lock_1u_and_the_star_2u_stamped_at_the_post_a_posted_pick_keeps_its_units`
  (end to end through post_board: a hockey runner-up at +130 / +190 on an 11/17 board, a college football and an NFL
  thin Lock, the switch off, a play already up).

## 7. Left out, and why

| option | units a year it would add | why not |
|---|---|---|
| every ½u at 1u incl. the floor | +5.4u alone | doubles the floor (it loses 5u more at 1u) and the NFL Lock (loses held out) |
| the NBA floor at 1u | +5.2u | 25-39, -6.4% since the train half ended, live 1-4, each season worse - a bigger number on a group that is losing now |
| the hockey favorite value play at 1u | +0.1u | the added half unit loses held out (-3.3%); the group lost in train |
| the ⭐ at 2u on a ½u value play / floor play / long dog | +4.4u | 52-57, -1.3% in the first half; the worst stretch x1.36 instead of x1.12 |
| the NBA favorite play / the read-4 college hoops dog at 2u | +6.3u / +6.1u | not the owner's options: both pass on this board, but the wider record is thin (+1.8% on the unseen seasons; +10.3% over eight seasons with train +3.8%) - the next ones to earn it if they keep winning live |
| the floor off | +1.3u | breaks "plays every day" (the owner, 11/4) |
| the hockey Dog +100..+150 at 1u | -3.5u | gives up units |

## Files

`plib.py` (the pieces, the ⭐ re-picked on the new sizes) · `s1_pieces` (every piece alone, the ⭐ by kind) ·
`s2_bundles` (the bundles together, each piece inside, the NBA floor after train) · `s3_star` (the ⭐ at 2u cut the
a-priori ways, the placebo) · `s4_plan` (today vs the plan, each piece's share, the tiers before / after) - each `.py`
with its `.out`.
