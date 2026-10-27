# 10/27 FABLE AUDIT - why the 10/26 and 10/27 boards were all leans, and the fix (the owner: "Run Fable and figure this out. We need to have unit plays, especially basketball. We can't have all leans back-to-back days" / "I don't care why the boards are leans ... at least ONE unit play per day. Preferably more units" / "especially with NBA, we need to start doing NBA plays and put units on them")

Tools (scratchpad funnel1027/): `funnel_replay.py` = tools/value_play_replay.Replay with EVERY moneyline candidate dumped (not just the picks) with every gate flag the live board applies - 1,097 board days 2023-10-01..2026-10-12 (61,231 sides) plus the last 14 live days 2026-10-13..26 (804 sides); closing prices, params re-tuned each July, the fixed hockey read (10/25), no injury reports (sports.hurt / waiting never fire). `funnel_sum.py` (the funnel + 20 loosening scenarios), `floor_sim.py` (12 ways to fill an empty day), `board_combo.py` (today's rules vs the new rules on the same days). Seasons: 2023-24 / 2024-25 train, 2025-26 and 2026-27 blind to the model (the gates were built with every season seen - same caveat as every board replay).

## 0. The verdict in one table

| | today's rules | the new rules together |
|---|---|---|
| unit plays a day (2023-26, 1,097 board days) | 0.88 | 2.3 |
| days with NO unit play | 634 of 1,097 (58%) | 21 of 1,097 (2%) |
| record / units / ROI | 551-418, +28.8u on 859u, +3.4% | 1258-1229, +90.6u on 1,658u, +5.5% |
| by season (net units) | +6.2 / +4.0 / +19.7 / -1.1 | +30.2 / +5.0 / +53.1 / +2.5 (4 of 4 up) |
| worst stretch | -19.3u | -22.4u |
| NBA unit plays | 16 in 634 NBA days (10-6, +4.1u) | 322 (154-168, +27.8u on 202u, +13.8%); 0.51 an NBA day |
| the last 14 live days (10/13-10/26, closing prices) | 14-10 +9.4u, 7 zero days | 22-16 +13.1u, 0 zero days |

## 1. THE FUNNEL - what emptied the board

The as-is board (today's rules replayed): 0.88 unit plays a day, 58% of days none; on non-Saturdays 0.65 a day, 62% none. Live 10/13-10/27: 6 all-lean days of 15 (10/16, 10/18, 10/20, 10/21, 10/26, 10/27); every unit play since 10/13 came from football or hockey; the NBA has had ZERO unit plays since it opened 10/21 (7 board days).

### favorites -150..-101 (12,729 candidate sides; 'alone' = passes every other gate, fails only this one)

| gate | kills | alone |
|---|---|---|
| read beats the real price (real_value / own_beats) | 10,973 | 673 (ncaab 274, mlb 242, **nba 70**, ncaaf 51, nfl 36) |
| win % 56%+ (lock_ok, the blended, calibrated p) | 10,239 | 188 (nhl 130) |
| not fighting (own read 3+ under / money against) | 4,580 | 146 |
| own read agrees | 6,439 | 0 |
| the -119..-101 band (S6) | 5,152 | 31 |
| NBA week one (games 1-5) | 66 | 0 |
| named reason / not a trap | 2,187 | 24 |

- **NBA favorites: 6 of 1,027 passed every gate.** The 10/22 rebuild made the NBA favorite's read (w_p) START at the books' no-vig price and move it by the study weights (-3..+2 points, capped 4). own_beats / real_value then ask w_p x dec > 1 - the no-vig price times the juiced decimal is UNDER 1 by the vig (2.2-2.5 points at -110..-150), so an NBA favorite needs +3 points of positive weights, and the two VALUE weights are +2 each (off a 20+ win; at a home dog in games 31-60). The owner's wired weights could never produce a pick. The week-one rule (games 1-5) then kills the rest of the first week on top (all 26 NBA favorites on the live days 10/21-26 failed BOTH).
- **NHL favorites: 130 killed alone by the 56% bar** (the weighed read w_p beats the price - Panthers -130 on 10/27 at 58.6% vs 56.5% needed - while the blended p sits 53-56%). Tested as ½u plays: 83-70, -2.7% on 153 (B.nhl) - DEAD, the bar is right.

### dogs +100..+350 (22,036 sides)

| gate | kills | alone |
|---|---|---|
| dog score at the sport's gate | 21,396 | 778 (mlb 599 - no MLB gate exists; ncaaf 44, nfl 43, nhl 40, nba 22) |
| own read over the price (DOG_NEEDS_OWN) | 19,421 | **197 (nhl 153, nba 27)** |
| not fighting | 12,004 | 61 |
| named reason / not a trap | 13,493 | 21 |

- **Hockey: the 10/23 plan's own-read rule killed 153 score-6+ dogs that passed every other check - 78-75, +15.6% flat (2023-24 +14.2u, 2024-25 -2.5u, 2025-26 +12.1u); +100..+150 67-57 +19.6% on 124.** All 153 had the own read BETWEEN the no-vig market and the juice; 0 of 153 sat under the no-vig market. The live hockey read is the line plus b2b / rest, so a gated dog's own read can almost never beat the vig - the rule became "never a hockey Dog" (the 10/27 slate: the Devils +100 at score 6.5, own read 48.3% vs 50% needed, no Dog). The rule's evidence ("own under -8% / -11.6% blind on 133") came from the replay whose hockey read the 10/25 sweep found was a different engine. The score gate itself was founded WITHOUT an own-read rule (10/1: 6+ won 48.7%, +12.8% on 542, 7 of 7 seasons). Own-over hockey dogs under today's rule: 28-29 +10.3% on 57.
- **NBA: 27 score-4+ dogs killed by the own-read rule alone - 14-13, +30.6% (2 of 3 seasons); own-over (today's) 4-5 +52.8% on 9.** The NBA gate (10/9 lead: 15-12 +11.5u on 27) was built without an own-read rule too.
- **The NBA home dog games 6-10 (+4 on the score, wired 10/21 "use for picks") can't fire either:** 51 such dogs, 24-27 +14.6% (3 of 3) - 0 pass the own-read rule (the early-season read is pulled to the market, so it never beats the juice), 33 of 51 read as "fighting" and 27 have no named reason. Not fixed here (a one-factor trigger; the owner's call - "not fighting" 8-10 +6.8%, "not fighting with a named reason" 5-8).

## 2. The loosenings replayed (flat 1u, closing prices; up = seasons up)

| scenario | record | ROI | seasons | call |
|---|---|---|---|---|
| A. NBA favorite Lock pool by the OWN read (56%+ over the price, p 56%+, not week one) - the pre-10/22 rule | 25-15 n=40 | +6.4% | 2/3 | not built (thin; A7 - the p alone - -6.7% on 102) |
| A5. NBA favorite with a POSITIVE study weight, good(), not week one | 62-25 n=87 | +23.1% | 3/3 (+5.3 / +2.5 / +12.4u) | **BUILT - the 🏀 NBA favorite play, 1u** (80 new to the board: 56-24 +20.9%; no weight -7.2% on 426, net negative -14.4% on 41) |
| A8. NBA favorite, own read over the price, p 53%+ | 68-44 n=112 | +6.9% | 3/3 | not built - minus A5 it is 37-32 -4.6% |
| B. favorites 53-56% whose read beats the price, ½u (every sport) | 234-194 n=428 | +1.0% | 2/4 | DEAD (nhl -2.7% on 153, ncaab -4.4%; mlb +6.7% on 126 a LEAD) |
| C. Locks at -119..-101 | 19-12 n=31 | +15.0% | 3/4 | not built - the owner's plan, 31 says nothing |
| D. NBA dog score 4+, own read UNDER the price | 14-13 n=27 | +30.6% | 2/3 | **BUILT - no own-read rule in the NBA (½u; own-over 1u)** |
| E2. NHL dog score 6+, own read between the no-vig market and the juice | 78-75 n=153 | +15.6% | 2/3 | **BUILT - hockey's own read is read against the no-vig market** (1u floor -> ½u by the thin rule) |
| E. NHL dog score 3-6, own over | 14-13 n=27 | +20.2% | 2/2 | LEAD, not built |
| D6. NBA home dog games 6-10, any own read | 24-27 n=51 | +14.6% | 3/3 | not built (see above - a trigger; the owner's call) |
| F. NBA week-one favorite Lock | n=0 | - | - | nothing to loosen - no week-one favorite ever had the own read over the price |
| G. every dog with the own read 3+ over, no score gate | 208-326 n=534 | -12.1% | 0/4 | DEAD (confirms the gates) |
| NBA floor: the best clean NBA dog by dog score each NBA day, score 0+ | 84-110 n=194 | +16.5% | 3/3 (+13.5 / +5.4 / +13.1u) | **BUILT - the 🏀 NBA floor, ½u, one a day** (score 2+ alone 38-63 +0.4%; every NBA dog -10.6%) |

### the daily floor - 12 ways to fill the 634 empty days (the ADDED plays, flat ROI; at ½u)

| fill to N | ranking | record | ROI | ½u units | worst | seasons |
|---|---|---|---|---|---|---|
| 1 | **dog score, highest** | 276-337 | **+3.8%** | +11.6u | -16.1u | 3/4 |
| 2 | **dog score, highest** | 635-757 | **+6.4%** | +44.6u | -18.7u | 3/4 (nhl +30, mlb +40, nba +5, nfl +5, ncaab +8, ncaaf +1) |
| 3 | dog score, highest | 979-1193 | +4.8% | +51.6u | -34.6u | 3/4 |
| 1 | weighed read edge, over the price only | 188-221 | +2.8% | +5.7u | -8.1u | 2/4 |
| 1 | own read edge (favorites) | 308-301 | -6.7% | -20.4u | -27.7u | 1/4 |
| 1 | own read edge (dogs) | 247-366 | -3.3% | -10.1u | -21.3u | 1/4 |
| 1 | likeliest winner (rank_p) | 345-287 | -4.1% | -13.1u | -21.7u | 2/4 |
| 1 | likeliest winner, own read over the no-vig market | 331-293 | -5.5% | -17.0u | -20.4u | 0/4 |
| 1 | win % over the market (p - p_market) | 276-356 | -6.2% | -19.5u | -24.3u | 1/4 |
| 1 | the lean the board posted, by rank_p | 323-257 | -3.2% | -9.2u | -16.1u | 2/4 |
| 1 | dog score 3+ else favorite by own edge | 302-315 | +1.0% | +3.0u | -14.6u | 3/4 |

Every ranking by the engine's read, the win % or the posted lean LOSES as a filler; the dog score is the one measure that makes money when forced, and the second play a day still pays (+4.2% on its own); the third adds +0.9% with a -34.6u stretch. **BUILT: the board fills to 2 unit plays a day with the dogs the dog score likes best, ½u each ("VALUE PLAY · THIN EDGE" on the card).**

## 3. What's built (sports.py; tests test_fable_1027_*)
1. `DOG_OWN_RULE` / `dog_own_ok`: hockey's own read is tested against the NO-VIG market (not the juice); the NBA Dog has no own-read rule (the score gate 4+ decides); football / college hoops unchanged. `best_hockey_dog` reads it too. The NBA Dog: 1u with the own read over the price (`NBA_DOG_OWN_UNITS`), ½u otherwise; the hockey own-under Dog sits at its 1u floor and the thin rule makes it ½u.
2. `nba_fav_plays` - the 🏀 NBA FAVORITE PLAY: an NBA moneyline favorite -150..-101 with a net positive study weight, good(), never games 1-5, never fighting, 1u (`NBA_FAV_UNITS`), tag `nba_fav`, own card label.
3. `floor_plays` + `FLOOR_MIN` 2 + `nba_floor_plays`: the opening board fills to 2 unit plays with the dogs the dog score likes best (½u, tag `floor`); an NBA day with no NBA unit play gets the best NBA dog by score at score 0+ (½u, tag `floor` with nba). Never past -150 / +350, never a trap, a named reason, never fighting the own read, never a side the injury rules hold (waiting), never a game we're on or in early, moneyline only. rule_check's money check knows a floor / NBA favorite play rides its tag, not the read (it would have pulled every one); sizing_check and posted_kind read the tags; `unit_plays_today` is the count the floor fills to.

## 4. Not changed, and why
- The NBA week-one no-Lock rule, the 56% Lock bar (hockey favorites 53-56% as plays -2.7% on 153), the -119..-101 Lock band (n 31), value plays favorites-only (dog value plays stay dead), the hoops ½u Dog floor (own-under), the hurt rule (no injury data in history - untestable here; live it holds), spreads (the 10/9 study: spread value plays lost in every season - no own read on a spread; not re-run).
- The NBA home dog games 6-10 as a one-factor play: the owner's call (24-27 +14.6%, 3 of 3 - but 33 of 51 fight the own read).
- From the 10/27 daily run (coordinator note): leans can land on a side whose own raw read is under 50% (the Blue Jackets 10/27 own 48.6% vs weighed 54.1%) - leans carry no units, untouched; the college small-favorite record-vs-points lead (-22% on 112) stays a tracker lead.

## 5. Caveats
Closing prices, not the 8 AM number; no injury reports in history (the floor's "waiting" rule can only cut live plays); the gates and weights were built on these seasons (only the model is blind); 20 scenarios were tried - the built ones pass 3 of 3 seasons (the NBA favorite play, the NBA floor) or stand on a founding study plus the funnel (the hockey Dog's score gate, the NBA dog gate; both 2 of 3 seasons, one season each -2..-3u). Judge each live at 50 plays; cut under -5% (the owner's 10/17 bar).
