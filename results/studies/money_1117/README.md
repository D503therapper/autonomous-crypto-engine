# 11/17 - THE MOST-MONEY STUDY: "bigger size units on the winners ... we don't ever want losers"

The owner, 11/17: *"I want what's going to make us the most money and not lose units. We want to make units. We need
bigger size units on the winners. We don't want losers. We don't ever want losers. Run Fable and figure out how to do
this."* and *"when I see a play that has more units on it, that means I'll put more money on it. And none of these
picks can be costing me or my friends money. We're here for winners."*

**The answer, plain.** Nobody can pick only winners - the board wins 53 of every 100 unit plays, and it makes money
because the 53 pay more than the 47 cost: about **+56 units a year at +14.7% on every unit risked**, with a worst losing
stretch of about 22 units, on the board today's code builds. I went looking for the losers to cut and the winners to
size up from four new directions. **(1) There is no kind of play to cut:** of the 31 kinds on the board not one loses in
both halves of the replay, and the ones that lost in the first half made +34 units in the second - cutting them would
have cost money. **(2) Sizing a kind by its own past record does not work:** how a kind did in one half says nothing
about the next (the link is -0.08, zero), and the sizes it hands out do no better than the same sizes dealt at random.
**(3) Fewer, bigger bets lose to the full board:** the plays a "top 1-3 a day" rule would drop win +18% to +29%.
**(4) ONE bigger size earned its place and is wired from the 11/18 games: the hockey runner-up dog at +100..+150 is
1 unit, not a half** - it is the Dog of the Day's twin (same gate, same checks), it won 63% of the time at plus money
on today's code, it is up in both halves on all three replay boards and on the three seasons nothing saw, and the
board's worst stretch gets a little *smaller* with it, not bigger. That is worth about +3 units a year. Everything else
on the table (every half unit at 1u, the ⭐ at 2u, the NBA floor or favorite bigger) is more money only by betting
more, with a deeper hole - your call, numbers below - and none of it is a better bet.

## The rig and the bar

- **The board (R3L, `mlib.py`)**: dogs_1117's R3 rows (the board re-built on TODAY's code, every 2026 date gate open,
  every board day 2023-10 -> 2026-11 at the closing price, the model re-tuned each July) shaped the way the live post
  shapes it: a thin-edge Lock outside football is no Lock (a ½u value play when the value bar clears, else nothing),
  today's sizes (the 11/16-11/17 ones in: the 💎 hockey max play 3u, the college football Dog past +150 1u, the college
  hoops dog slot 2u at a read of 5+), and the ⭐ on the day's best play whose read beats its price (1u at least).
  **1,192 unit plays on 881 board days.** Train = to 6/30/2025, held out = 7/2025 -> 10/12/2026, live (10/13 on) apart.
- **The older boards** (sizing_1114/lib.py: R1 the 10/30 rows, R2 the 11/12 rows), **the seasons nothing saw** (the
  paid 2020-23 hockey prices, nhl_odds_1102), **the long football / college hoops rigs** (dogs_1117, sweep_1117) - used
  to check anything R3L likes.
- **Not on this rig** (no rows): the college hoops spread stack play and the road dog at a read of 3, the totals, the
  ⏰ early spots, mid-day adds, baseball. Their own studies are quoted in section 1.
- **THE BAR**: holds in BOTH halves, up in most seasons, beats a placebo (the same sizes dealt at random to plays of
  the same kind / tier under 5% of the time - 100 of 2,000), the worst stretch within today's x1.5. And the owner's
  11/17 rule on top: **a bigger size has to mean the kind really won more against its price out of sample** - never a
  bigger size on a kind that is flat or losing, even if it adds units by betting more.
- **Said once:** the dog score's weights were fit with these seasons seen. "Held out" here is the later half, not a
  clean blind test - which is why the unseen 2020-23 seasons are the tie-breaker wherever they exist.
- **Days with a unit play**: 70.8% of this rig's board days (the rig has no baseball, totals, early plays or mid-day
  adds; 140 of its 250 empty days are May / June / August / September - the playoffs and the opening weeks - and 113
  have three games or fewer; November through January it is 94%; `look.out`). The number that matters is that **the plan does not change it**.

## 1. Every kind of unit play, ranked (`s1_kinds.out`)

Today's board: **587-521 (53.0%), +169.1u on 1,150u (+14.7%)** - train +71.0u (+10.0%) / held +98.0u (+22.4%), the
worst stretch -22.3u, 4 of 4 seasons up (+32.3, +38.7, +91.8, +6.3 so far), about **+55.8u a year**.

| kind (today's size) | plays | flat vs its price | train | held out | units won | own worst stretch | other rigs / live |
|---|---|---|---|---|---|---|---|
| hockey runner-up dog (½u) | 71 | **+34.1%** | +33.1% | 18-11 **+35.6%** | +12.1u on 35.5u | -2.0u | R1 +13.2% / R2 +22.1% (both halves up); unseen 2020-23 +15.9%, 3 of 3; live: none posted yet |
| NBA favorite play (1u) | 69 | +27.5% | +16.5% | 22-4 +45.7% | +19.0u on 69u | -3.6u | R1 +22.7% / R2 +34.1%; unseen seasons +1.8% (11/15: no 2u); live 1-0 |
| college hoops dog slot, read 5+ (2u) | 37 | +31.2% | +31.1% | 4-3 +31.7% | +23.1u on 74u | -9.8u | 8-season rig 85-68 +33.7%, 8 of 8 |
| college hoops dog slot, read 4 (1u) | 68 | +27.0% | +32.2% | 9-10 +13.6% | +18.4u on 68u | -7.8u | 8-season rig +10.3% (train +3.8%); live 0-1 |
| college football Dog +100..+150 (2u) | 12 | +44.7% | - | 8-4 +44.7% | +10.7u on 24u | -4.0u | 7-season board 22-17 +24.9%, 6 of 7 |
| college football Dog +151..+350 (1u) | 4 | +57.5% | - | 2-2 | +2.3u on 4u | -2.0u | 7-season board 18-17 +64.3%, 6 of 7 |
| college football thin Lock (½u) | 13 | +42.6% | +31.3% | 4-0 | +2.8u on 6.5u | -0.7u | 9-season board 20-5 +35.9%, 8 of 9 |
| 🔍 college hoops gap play (2u) | 11 | +43.2% | +26.7% | 3-1 | +9.5u on 22u | -2.0u | 8-season rig 72-63 +20.1% (1u + 2u) |
| 💎 hockey Dog, b2b spot 8+ (3u) | 31 | +19.7% | **7-9 -6.8%** | 10-5 +48.0% | +18.3u on 93u | **-15.0u** | unseen 2020-23 34-24 (its case); live 3-1; judge at 25 graded |
| NBA Dog (½u) | 18 | +31.3% | +10.6% | 4-1 | +2.8u on 9u | -2.0u | 18 plays |
| NBA floor dog (½u) | 165 | +19.0% | +25.6% | 21-28 **+3.4%** | +15.7u on 82.5u | -3.6u | R1 +24.7% / R2 +22.3%; unseen seasons a third of that; **live 1-4** (replay of the live weeks 4-11); judge at 20 |
| hockey Dog +100..+150 (2u) | 165 | **+6.4%** | +6.5% | 32-34 +6.2% | +21.1u on 330u | **-21.3u** | R1 +20.6% / R2 +11.7% (all sports' short Dogs); unseen 2020-23 89-99 +13.6%, 3 of 3; live 5-2 +9.1u |
| hockey Dog +151..+350 (½u) | 44 | +3.5% | +0.5% | 4-5 +15.6% | +0.8u on 22u | -3.0u | |
| value play, hockey favorite (½u) | 152 | +2.7% | -1.4% | 37-21 +9.4% | +2.0u on 76u | -5.8u | R1 value plays +1.6% (held -6.8%); live 8-0 |
| 🔍 college hoops gap play (1u) | 23 | -4.0% | -12.1% | 4-4 +11.1% | -0.9u on 23u | -5.4u | 8-season rig up (above) |
| floor, NFL dog (½u) | 62 | -1.1% | -18.1% | 11-12 +27.7% | -0.3u on 31u | -4.0u | the 9-season board's road floor dogs +26.5% |
| floor, hockey dog (½u) | 79 | **-5.5%** | -14.7% | 12-13 +14.5% | -2.2u on 39.5u | -7.0u | R1 +8.0% / R2 +5.6% (the old, bigger floor); **unseen 2020-23 -7.0% on 610, 1 of 3**; live 7-4 |
| NFL Lock (½u) | 14 | -3.7% | -3.4% | 4-3 -4.0% | -0.3u on 7u | -1.0u | 14 plays; ½u and never the ⭐ since 11/16 |
| hockey Lock, not thin (2u) | 5 | 2-3 | - | 2-3 | -3.1u on 10u | -4.5u | 5 plays in three years |
| floor, college football / NBA / college hoops dog (½u) | 24 | 9-15 | | | -2.1u on 12u | | the "sits out the floor" fallbacks |

**By path:** the Dog of the Day +56.3u on 487u (+11.2% flat), the college hoops slots +42.6u on 144u, the NBA favorite
play +19.0u, the NBA floor +15.7u, the runner-up dog +12.1u, the gap play +8.6u, value plays +6.7u, the Lock +1.3u,
**the floor -4.5u on 82.5u** (64-101, -5.5%: train -15.9% / held +14.7%, 1 of 4 seasons up).
**By sport:** college hoops +23.8% a bet, college football +27.9%, NBA +22.2%, hockey +7.4% (547 of the 1,108 plays),
NFL -1.2% (80 plays; train -16.1% / held +22.4%).

**The kinds that are not on this rig** (their own studies; nothing re-run here):

| kind | size | its study | live |
|---|---|---|---|
| ⛰️ college hoops altitude over | 1u | 500-342 +13.2%, 9 of 9 seasons, a point worse +8.2% | 0-1 (5-1 this season on the rebuilt rule) |
| 🏀 NBA over, the main guys out | ½u | 110-74 +14.0% (train +16.9% / blind +12.1%) | 1-0 |
| 🏀 college hoops spread stack | ½u | 56% covered, +7.3% on 1,282 (held +11.0% on 798, 3 of 3) | starts late November; judged at 100 |
| college hoops road dog at a read of 3 | ½u | 63-59 +23.0% (train +19.5% / held +27.4%, 6 of 8) | new 11/17; judged at 40 |
| 💎 college hoops Lock-test favorite | 2u | the 11/16 max-play hunt | new 11/16 |
| 🌍 Europe morning NFL under | ½u | 17-11 +16.3% on 28 - does NOT clear a bar (a random 28 NFL unders match it 337 of 2,000) | 3-0; the owner's test, its quit rule |
| ⏰ NFL bye dog | ½u | an ordinary dog at the close over 21 seasons (-7.7% on 184) | 2-2 +1.2u |
| ⏰ hammered early | ½u | the paid-odds tables flip by half | **0-4 -2.0u**, all college; judge at 20 |
| ⏰ NBA opening line | ½u | -6.9% on 361 at the earliest price on the old paid seasons | **3-5 -1.5u**; "one voice" has let none post since 11/11; judge at 20 |
| ⏰ exam scan | ½u flat | +10.3% on 213, the halves flip | 0-1 |
| ⏰ East-out-West / Monday night NFL dog | ½u | +35% then -11% / -2% then +24% | - |
| ⏸️ blowout spot, 🔍 college football gap play | paused | 3-11 live / 1-7 live | paused 11/11, 11/13 |

**The honest read of the early box:** it is the one part of the engine that is down live (10-17, -4.4u) and none of
its dog spots clears a both-halves bar on the paid odds history - they are the owner's "you prove it by doing it"
tests, each ½u with a quit rule or already paused. Nothing there earns a bigger size; nothing new to cut that is not
already paused or on a judge.

## 2. CUT THE LOSERS (`s2_cut.out`) - there is no provable loser to cut

- **No kind is down in both halves** (10+ plays in each): the list is empty.
- **The honest test** - pick the losers on the train half only, take them off, judge on the held half: the five train
  losers (the 💎 3u, the NFL and hockey floor dogs, the hockey favorite value play, the 1u gap play) made **+34.1u on
  117u (+29.1%)** in the held half. The board without them: +98.0u -> +63.9u, a unit play on 68% -> 55% of days. Taking
  the same number of random plays off does as well 1,209 times in 2,000. Mirror it (losers by the held half): there are
  none. **A kind that lost last year is not a kind that loses.**
- **The board without one path** (three replay years): no Dog of the Day -59u; no college hoops slots -43u; no NBA
  favorite play -19u; no NBA floor -16u; no runner-up dog -12u; no value plays -11u; no gap play -9u; no Lock -4u;
  **no floor +4.0u** (ROI +14.7% -> +16.3%, the same worst stretch) **but a unit play on 59.0% of days instead of 70.8%.**
- **The floor is the one soft kind**, and it is exactly what it says on the card: on today's code 64-101, -5.5%
  (train -15.9% / held +14.7%), on the seasons nothing saw its hockey dogs -7.0% on 610, on the two older boards +8.0% /
  +5.6%, live 8-6 +2.0u. On the days it is the board's ONLY play: 44-77, -7.9%. It is the price of "a play every day"
  (the owner, 11/4) - about **1.5 units a year at ½u** on today's code. Not provably a loser (it flips by half and by
  board), so not cut; **never a kind to size up.** Cutting it is the owner's call and breaks his 11/4 rule.

## 3. SIZE BY THE KIND'S PROVEN EDGE (`s3_kind_size.out`) - it does not work, and here is why

Each kind got ONE size from its own record on one half (a quarter of Kelly on the kind's win rate, shrunk toward what
its prices need; ½u floor, 3u cap) and was judged on the other half, against today's sizes on the same plays:

| scheme | sized on train -> judged on held | sized on held -> judged on train | the same sizes dealt at random as good |
|---|---|---|---|
| TODAY (the kind's own size) | +89.0u on 414u (+21.5%), worst -12.3u | +69.1u on 650u (+10.6%), worst -18.7u | |
| Kelly by kind | +119.4u on 578u (+20.7%), worst -15.7u; **at today's risk +85.4u** | +93.5u on 866u (+10.8%), worst -27.0u; at today's risk +70.2u | 932 / 651 of 2,000 |
| ... a kind under ¼u is cut | +106.9u on 509u; at today's risk +86.9u | the same | 894 / 651 |
| a plain ROI ladder | +132.4u on 564u (+23.5%); at today's risk +97.0u | +62.0u on 598u; at today's risk +67.4u | 409 / 802 |
| only bigger | +141.9u on 686u (+20.7%), worst -20.2u | +98.8u on 980u (+10.1%), worst -28.6u | 934 / 878 |
| only smaller | +66.4u on 306u (+21.7%), worst -7.3u | +63.8u on 536u (+11.9%), worst -16.5u | 660 / 380 |

Every scheme that "wins more" does it by risking more: put back on today's total risk they land where today's sizes
land (+85u to +97u against +89u; +66u to +78u against +69u), and none beats the same sizes dealt at random. **Why:**
across the 9 kinds with 15+ plays in each half the link between a kind's train ROI and its held ROI is **-0.08** (rank
-0.17). The train half would have put 3u on the NBA floor (+25.6% -> +3.4% held) and the read-4 slot dogs (+32.2% ->
+13.6%) and cut the 💎, both floors and the hockey favorites - which then won. Two kinds are steady from half to half:
**the hockey runner-up dog (+33.1% / +35.6%)** and the hockey short Dog (+6.5% / +6.2%).

## 4. CONCENTRATION (`s4_concentrate.out`) - fewer, bigger bets lose to the full board

| | units (ROI) | worst stretch | units won per unit of worst stretch |
|---|---|---|---|
| **TODAY, the full board** | **+169.1u on 1,150u (+14.7%)** | **-22.3u** | **7.6** |
| only the day's top play, today's size | +104.2u on 755u (+13.8%) | -24.1u | 4.3 |
| only the top play, flat 2u | +115.7u on 1,200u (+9.6%) | -30.4u | 3.8 |
| only the top play, flat 3u | +173.5u on 1,800u (+9.6%) | -45.5u (x2.04) | 3.8 |
| only the top 2, flat 2u | +213.2u on 1,862u (+11.5%) | -53.4u (x2.39) | 4.0 |
| only the top 3, today's size | +156.0u on 1,107u (+14.1%) | -22.2u | 7.0 |
| the top play 2u at least, the rest as it is | +186.7u on 1,626u (+11.5%) | -37.7u (**x1.69**) | 4.9 |

The plays a top-N rule leaves OFF are winners: left off by top-1 **290-218, +18.5%**; by top-2 110-67, +25.7%; by top-3
36-22, +20.8% - all in both halves. The day's top play by the ⭐'s order is the board's *weakest* slice (+9.6% flat;
train +4.3%) because that order puts the hockey Dog and a thin hockey favorite first. With the order fit on the train
half the top-2 does look good on the held half (+24.4%, worst -9.5u) - and fit on the held half it is the worst thing
on the train half (+10.1%, top-1 +6.5%). No order holds. **The board's edge is spread across many small plays; the
breadth is what keeps the worst stretch at 22 units.**

## 5. THE OPTIONS ON THE TABLE, one frame (`s5_options.out`)

"The added units" = what the extra money itself earns; a size-up is a better bet only when that beats the board's own
+14.7%, in both halves, with a placebo under 100 of 2,000.

| option | the board becomes | the added units earn | worst stretch | placebo | verdict |
|---|---|---|---|---|---|
| **the hockey runner-up dog 1u at +100..+150** | **+179.0u (+15.2%)** | **+10.0u on 27u, +36.9% (train +37.5% / held +36.2%)** | **x0.97** | 3.5-5.1% | **WIRED** (section 6) |
| ... every hockey runner-up 1u | +181.1u (+15.3%) | +35.4% | x0.96 | 2.3-3.9% | the long ones are 2-6 on R1, 3-7 unseen - short only |
| ... the runner-up at 2u (the Dog's size) | +205.3u (+16.4%) | +34.5% | x1.13 | 2.9-4.1% | not provably better than the Dog (unseen: the same +15%) - **the owner's option** |
| every ½u play at 1u | +195.3u (+13.9%) | +26.2u on 252u, **+10.4%** (+8.5% / +13.5%) | x1.31 | - | more money by betting more: the added units earn LESS than the board; it doubles the floor |
| every ½u play at 1u but the floor | +200.3u (+15.1%) | +31.2u on 176u, +17.7% (+20.8% / +12.9%) | x1.07 | 21 | clears as a bundle - but 165 of its 352 plays are the NBA floor (held +3.4%, live 1-4) and 152 the hockey favorites (train -1.4%): a bigger size on kinds that are flat in a half. **No** (the owner's 11/17 rule) |
| the ⭐ at 2u | +196.7u (+14.8%) | +27.6u on 183u, +15.1% (**train +3.7%** / held +40.3%) | x1.41 | 846 | a random 183 plays does as well 42% of the time; a 41% deeper hole. **The owner's option, not earned** |
| the college football thin Lock at 1u | +169.4u | 1 play changes (the ⭐ already has the other 12 at 1u) | x1.00 | - | on the 9-season board +0.5u a season; it does not separate from its own kind. **The owner's option** |
| the NBA favorite play at 2u | +188.1u (+15.4%) | +27.5% (+16.5% / +45.7%) | x1.01 | 444 | the seasons nothing saw keep +1.8% (11/15). No |
| the college hoops read-4 slot dog at 2u | +187.4u (+15.4%) | +27.0% (+32.2% / +13.6%) | x1.00 | 452 | the 8-season rig has the band at +10.3% (train +3.8%). No (11/17) |
| the NBA floor at 1u | +184.7u (+15.0%) | +19.0% (+25.6% / **+3.4%**) | x0.96 | 231 | flat held out, 1-4 live. No |
| *size-downs:* the hockey Dog +100..+150 at 1u | +158.5u (+16.1%) | gives up +6.4% a unit | x0.87 | - | -3.5u a year for a smaller hole - **the owner's option** (below) |
| the 💎 at 2u | +163.0u (+14.6%) | gives up +19.7% (train -6.8% / held +48.0%) | x0.87 | - | its judge at 25 graded decides |
| no ⭐ raise | +158.1u (+14.9%) | gives up +12.7% (train +3.0% / held +38.4%) | x0.84 | - | the owner's 11/4 rule; the raise pays for itself, thinly in train |
| no floor at all | +173.1u (+16.3%) | the floor: -4.0u on 89u | x0.98 | 31 | a play on 59% of days, not 71% - breaks "plays every day"; the owner's call |

## 6. WIRED - the hockey runner-up dog at +100..+150 is 1u (was ½u), from the 11/18 games

**What it is.** The runner-up dog (`sports.dog_plays`) is a hockey dog that clears the FULL Dog of the Day check - the
same gate (a dog score of 6+), the same own-read rule, the same money check - on a day another dog took the Dog spot.
One a day. The Dog carries 2u at +100..+150; its twin carried a quarter of that.

| the short runner-up (+100..+150) | record | won / needs | flat | first half | second half | seasons |
|---|---|---|---|---|---|---|
| **R3L - today's code, 2023-26** | **34-20** | **63.0% / 45.8%** | **+36.9%** | +37.5% | **17-10 +36.2%** | 3 of 4 (every runner-up: 4 of 4) |
| R1 - the 10/30 rows | 28-23 | | +20.7% | +11.7% | +33.6% | 2 of 3 |
| R2 - the 11/12 rows | 29-22 | | +24.4% | +18.1% | +32.0% | 2 of 3 |
| the seasons nothing saw (2020-23, the morning price; `s6_runnerup_oos.out`) | 9-6 (every runner-up 12-13) | | +39.7% (+15.9%) | | | every runner-up 3 of 3 |

- **Both halves**: six half-cells of six up across the three boards.
- **The placebo** (the extra ½u dealt to a random 54, five seeds, 10,000 deals): of the board's ½u plays **3.9%**, of
  every posted hockey dog 3.5%, of the gated hockey dogs at that price 4.5%, of the ½u dogs 4.8%, **of all the gated
  hockey dogs 5.1% - at the line, said plainly.** On the two older boards it does not separate from its siblings at all
  (they win there too). So: it is *provably not a ½u play*; it is **not** provably better than the Dog of the Day.
- **The seasons nothing saw**: 25 runner-ups, +15.9%, 3 of 3 seasons - the gated hockey dog's own +14.4% there, the
  number the Dog's 2u stands on. (At the open price it is +0.6% on 19; the board posts at the morning price.)
- **The worst stretch gets SMALLER**: -22.3u -> -21.7u on R3L (it wins on days the Dog loses: the Dog on a
  runner-up day is 27-36); R1 -13.9u -> -13.6u; R2 the same -25.1u.
- **The board**: +169.1u -> **+179.0u** on R3L (+3.3u a year), ROI +14.7% -> +15.2%; R1 +5.3u, R2 +6.2u.
- **Why 1u and not 2u**: half the Dog's size is what "the same kind, not proven better" earns; at 2u the board's worst
  stretch goes x1.13 and the older boards' gain is thin. **Why short only**: the Dog of the Day's own price split - past
  +150 the runner-up is 2-6 on R1 and 3-7 on the unseen seasons (17 plays on R3L).
- **Honest limits**: about 18 plays a year; the dog score was fit with 2023-26 seen; no hockey runner-up has posted
  live yet (the play's live 1-7 is all NBA / college, cut 11/13). Its judge is the runner-up dog's own quit rule
  (`DOG_PLAY_QUIT`: 20 graded under 35% won = off) - **and that record starts 1-7 from sports that no longer post**, so
  the hockey ones have to win 6 of their first 12 to stay on. Fair to flag: the judge should probably count hockey / NFL
  only; I did not change a quit rule here.

**Wired** (`sports.py`): `MONEY_1118_FROM = "2026-11-18"` (None = off), `DOG_PLAY_SHORT_UNITS_1118 = 1.0`,
`DOG_PLAY_SHORT_LEAGUES_1118 = ("nhl",)`, `dog_play_short_1u(leg, day)` / `dog_play_1u(pk)`; post_board stamps
`pk["dog_play_1u"]` when the runner-up posts and `units_for` / `sizing_check` read the stamp - **a play already up has
no stamp and keeps ½u**. Test: `test_money_1118_the_hockey_runner_up_dog_at_100_to_150_is_1u_stamped_at_the_post_a_posted_play_keeps_its_units`
(end to end through post_board).

## 7. TODAY vs THE PLAN (`s7_plan.out`)

| | TODAY | THE PLAN (11/18) |
|---|---|---|
| units won a year | +55.8u | **+59.1u** |
| units risked a year | 380u | 388u |
| ROI | +14.7% | **+15.2%** |
| unit plays won | 53.0% (587-521) | 53.0% (the same plays) |
| train / held | +71.0u / +98.0u | +76.1u / +102.9u |
| worst stretch | -22.3u | **-21.7u** |
| units won per unit of worst stretch | 7.6 | 8.3 |
| worst season | +6.3u (2026-27 so far) | +6.4u |
| by season | +32.3 +38.7 +91.8 +6.3 | +37.4 +38.7 +96.6 +6.4 |
| board days with a unit play | 70.8% | 70.8% |

## 8. THE SIZE TIERS - did each bigger size earn its place? (`s7_plan.out`)

Under the plan, by the kind's own size (the ⭐ raise left off), on today's code:

| size | what is in it (plays) | all | train | **HELD OUT** |
|---|---|---|---|---|
| **½u** | the NBA floor 165, hockey favorite value plays 152, the floor's dogs 165 (hockey 79, NFL 62, others 24), the hockey Dog past +150 44, the NBA Dog 18, college hoops favorite value plays 18, the long runner-up 17, the NFL Lock 14, the college football thin Lock 13, others 16 | 622: 316-306, +8.7% | +5.0% | **118-92, +16.1%** |
| **1u** | the NBA favorite play 69, the college hoops dog slot at a read of 4 68, **the hockey runner-up dog +100..+150 54**, the 🔍 college hoops gap play 23, the college football Lock (not thin) 5, the college football Dog past +150 4 | 223: 137-86, +27.1% | +23.3% | **58-31, +32.9%** |
| **2u** | the hockey Dog +100..+150 165, the college hoops dog slot at a read of 5+ 37, the college football Dog +100..+150 12, the 🔍 gap play at a read of 6+ 11, the hockey Lock 5, the NFL Dog 2 | 232: 117-115, +13.4% | +13.1% | **49-45, +13.9%** |
| **3u** | the 💎 hockey Dog on the b2b spot at a score of 8+ 31 | 31: 17-14, +19.7% | **7-9, -6.8%** | **10-5, +48.0%** |

As the board shows it (the ⭐'s raise in): ½u 84-79 +9.7% held out; 1u 92-44 +34.8%; 2u 49-45 +13.9%; 3u 10-5 +48.0%.

**Straight about the ladder.** Every tier makes money out of sample. ½u -> 1u is a real step up in both halves
(+5.0% / +16.1% against +23.3% / +32.9%). **The 2u tier does NOT win more than the 1u tier on today's code** - it is
165 hockey Dogs at +6% and 67 others at +30% or better. The hockey Dog's 2u stands on the wider record (+13.6% on the
three seasons nothing saw, +12% / +21% on the older boards, 5-2 live), where it is level with the 1u kinds' long-run
numbers (the read-4 slot dog +10.3% over eight seasons, the NBA favorite play +1.8% on unseen seasons) - so it is not
a bigger size on a flat or losing kind, but on today's code it is the thinnest 2u on the board and it is where the
worst stretch comes from (its own: -21.3u). **The owner's option: the hockey Dog +100..+150 at 1u** = about -3.5u a
year, ROI +14.7% -> +16.1%, the worst stretch -22.3u -> -19.3u, and a ladder where 2u really means the +30% kinds. I
did not wire it: it gives up units, one board says it and three other sources do not, and it is the 10/30 sizing's
main call. **The 3u tier** lost in the first half on today's code (7-9) and won the second (10-5); its case is the
unseen seasons (34-24) and it has a judge at 25 graded - said plainly, it is the size with the least behind it.

## 9. Straight answers

1. **"We don't ever want losers."** Not possible - a +130 dog that wins 55% of the time still loses 45 times in 100.
   The board wins 53% of its unit plays and makes +14.7% on every unit; that is the real thing. What can be done is
   never put a bigger size on a kind that has not earned it - section 8 is that check, tier by tier.
2. **Which kinds lose?** None in both halves. The soft one is the daily floor (about -1.5u a year on today's code) -
   the price of a play every day, ½u, never to be sized up. The early box is down live (10-17) and is all ½u tests on
   judges; the two worst are already paused.
3. **Bigger on the winners?** One: the hockey runner-up dog at +100..+150, 1u from 11/18. Sizing kinds by their past
   record, and betting fewer / bigger, both fail - a kind's last year does not predict its next.
4. **The owner's options, with numbers** (none wired): the runner-up at 2u (+26u more in three years, worst x1.13,
   not provably better than the Dog); every ½u at 1u (+26u, the added units earn 10% against the board's 15%, worst
   x1.31); the ⭐ at 2u (+28u, worst x1.41, luck can't be ruled out); the college football thin Lock at 1u (+0.5u a
   season); the hockey Dog at 1u (-3.5u a year for a 13% smaller worst stretch and an honest ladder); the floor off
   (+1.3u a year, a play on 59% of days instead of 71%).
5. **Watches**: the NBA floor (held +3.4%, live 1-4 - its judge at 20), the 💎 3u (train 7-9 - its judge at 25), the
   hockey floor (-5.5%; unseen -7.0%), the ⭐ on a hockey favorite (train -8.8% on 47), the runner-up dog's quit rule
   counting sports that no longer post.

## Files

`mlib.py` (the rig) · `s1_kinds` (the ranking, the tiers, the ⭐) · `s2_cut` (cut the losers) · `s3_kind_size` (size
by the kind's record) · `s4_concentrate` (fewer / bigger, the ⭐ by kind) · `s5_options` (the options, one frame) ·
`s6_runnerup_oos` (the runner-up on the unseen seasons) · `s7_plan` (today vs the plan, the tiers, the older boards) ·
`look` (the days with no play) - each `.py` with its `.out`.
