# 11/21 daily studies

The owner's daily routine: the board check, yesterday's picks, the lead tracker and ten NEW studies. Four of the ten
came out of today's board check (UT Rio Grande +160 2u went up on "out-rebounding people by +7.2 a game" with two of its
five box games against non-D1 schools) and the 11/20 run's open money step (the tune-up weight inside the stack play).

**In one line:** the non-D1 tune-up weight goes INTO the ½u college hoops spread stack from the 11/22 games (about 7 more
½u spread plays a season, 2 fewer); the non-D1 games do NOT spoil the glass weight or the dog slot (nothing to fix on
today's board); one new tracker lead (the dog that has won less than its prices said, against a team that has won more);
no posted pick, price or size changed.

Prices: ESPN's close at its own juice, regular season, a team's games THIS season before tonight (no look-ahead). Train
2018-21 / held out 2022-26, each held season shown apart (box-score studies: train 2021-23 / held 2024-26; the replay
rows: train 2018-22 / held 2023-26). Placebo = 2,000 random same-size sets from the cell's own pool. **343 cells were
cut - about 17 clear |z| 2 by luck.** The paid odds history was not re-read: its book-by-book / line-shape / steam /
timing questions are answered (10/8-11/17) and nothing new is in the files.

| # | study | verdict | the number |
|---|---|---|---|
| S1 | college hoops: the glass weight when the rebound margin holds non-D1 games (asked by the board check) | DEAD - nothing to fix | the glass dog as built +0.0% on 847 vs -7.2% for every dog (placebo 89 of 2,000); its margin with 0 / 1 / 2+ non-D1 games in it +4.0% on 254 / -0.1% on 240 / -2.8% on 353 (as badly by luck 970 / 609 of 2,000); the margin on D1 games only still 6+ -0.9% on 676, under 6 +1.9% on 169 |
| S2 | college hoops: the dog slot's "both teams 4+ games" gate counted in D1 games | DEAD - nothing to tighten | the slot +19.8% on 374; both 4+ D1 games +18.6% on 354; a team under 4 D1 games +42.7% on 20; the dog with 2+ non-D1 games behind it +23.9% on 115 (train +21.7% / held +26.6%) |
| S3 | college hoops: the ½u spread stack play's replay with the 11/20 tune-up weight added | **BUILT - in the stack from 11/22** | a +0.03..+0.04 stack off a tune-up (lifted to the bar): ATS +45.4% on 42 (train +48.7% / held +42.9%, placebo 1 of 2,000); the mirror across -27.0% on 68; the play pool +7.9% on 1,401 (train +2.5% / held +11.4%) vs +6.6% on 1,373 |
| S4 | college hoops: the favorite with no Division I win (the card's "their wins came over non-D1 schools") | DEAD (a watch) | its own spread +9.7% on 89 (train +34.8% / held -5.9%), the dog across -7.4% on 65; the padded SMALL favorite -150..-101 +45.6% on 31 - too few |
| S5 | football: fumble luck (the team box's fumbles lost - a column no study had read) | WATCH (college), DEAD (NFL) | the college side +0.4 fumbles a game to the good: ATS -11.3% on 724 (train -11.2% / held -11.6%, as badly by luck 47 of 2,000), its dog -14.6% on 202 (train -23.4% / held +6.3%); the NFL nothing (245 / 222 sides) |
| S6 | NFL: defensive touchdowns (the game after a win with one, the season's count) | DEAD (a watch) | won last week with a defensive TD: ATS -6.8% on 226, its dog -21.5% on 93 (train -14.6% / held -31.8%, as badly by luck 227 of 2,000) |
| S7 | NHL: the puck line's price against the moneyline (the books' margin shape) | DEAD | the fifth priced for a BIG margin: dog -6.9% on 2,046 vs -5.4% in the middle, small favorite +0.2% on 1,455 (train -5.9% / held +4.9%); the fifth priced SMALL: small favorite +8.1% on 134 (train +22.5% / held +0.3%) - both ends beat the middle, no dose |
| S8 | the home team blown out twice in its own building (the card's 🥊 line) - NHL / NBA / college hoops | DEAD | NHL visiting dog -7.0% on 1,894 vs -4.4% at a team never blown out; NBA +5.0% on 856 (train +16.3% / held -7.4%); college hoops -2.5% on 583 (placebo 320); the blown-out college HOME dog -12.1% on 954 (both halves) |
| S9 | wins against what the closing prices expected, last 10 priced games - every league | **LEAD (tracker)** | the dog 2.0+ wins UNDER its prices against a team 2.0+ OVER: NBA +40.6% on 54 (train +49.4% / held +33.0%), NHL +7.8% on 96, college hoops +11.0% on 84; the mirror dog NBA -27.6% on 33, college hoops -51.2% on 40 |
| S10 | NBA: the starters' plus-minus against the scoreboard, last 10 | DEAD (a watch) | starters +3 over the team margin: ATS -5.3% on 2,826, dog -4.2% on 1,308; starters 3+ under: dog +6.3% on 484 (train +7.7% / held +4.8%, placebo 58) |

## S3 - the tune-up weight inside the stack (s_cbb.py s3)

Rows: the 11/16 max-play hunt's cached replay (`~/.cache/d503_maxcol1116/cbb_rows.pkl` - the board re-built at ESPN's
close every college hoops day 2018-26, every spread side with its stack as `sports.ncaab_spread_stack` added it up).
The tune-up flag is re-built here from the game files: a D1 team whose last game was against a non-D1 school, on a true
home / road floor, against a D1 team whose last game was a D1 game (+0.02), the side across (-0.02).

| cell | all | train 2018-22 | held 2023-26 | placebo |
|---|---|---|---|---|
| stack +0.05+ (today's play pool) | +6.6% on 1,373 | +0.6% on 539 | +10.4% on 834 | |
| the pool with the tune-up weight in | **+7.9% on 1,401** | +2.5% on 551 | +11.4% on 850 | |
| ADDED: stack +0.03..+0.04, off a tune-up | **+45.4% on 42** (z 3.6) | +48.7% on 18 (4 of 4 seasons) | +42.9% on 24 (2023 +33.1 / 2024 -2.4 on 4 / 2025 +68.7) | 1 of 2,000 (+0.03..+0.04 sides) |
| the mirror: stack +0.03..+0.04, ACROSS a tune-up team | -27.0% on 68 | -45.4% on 28 | -14.1% on 40 | |
| every other +0.03..+0.04 side | -0.8% on 5,668 | -0.3% | -1.8% | |
| DROPPED: stack +0.05..+0.06, across a tune-up team | -10.0% on 14 | -36.4% on 6 | +9.7% on 8 | 546 as badly - too few alone |
| the best three a night, the stack with the weight in | +5.5% on 945 | -0.2% on 368 | +9.0% on 577 | |
| the best three a night, today's stack | +4.6% on 924 | -2.5% on 361 | +9.1% on 563 | |

THE FIVE CHECKS: (1) fair - the closing spread at its juice, the schedule before tonight; (2) both halves - the added
cell +48.7% / +42.9%, the pool better in both; (3) seasons - 4 of 4 train, 2023 / 2025 up, 2024 flat on 4 bets; (4) this
season - one bet (it won) - the stack only starts firing in late November; (5) the second read - the weight itself was
found WITHOUT the stack on 1,944 games (11/20: ATS +5.4%, placebo 0 of 2,000) and the mirror cell here points the same
way on 68. HONEST: 42 added bets on the replay - about 7 more ½u plays a season since the box scores start (2021); the test was fixed by the 11/20 run
before these rows were read (one question, not a search), and the play's own quit rule (100 graded, under 52.4%
covered) judges it. One wrinkle: the replay's stack pre-dates the 11/20 "a star who sat a tune-up did not miss the last
game" fix, so its "across a tune-up" rows include sides that today's code no longer lifts by +0.03 - those are the
losing mirror cell, already out.

WIRED: `sports.NCAAB_STACK_TUNEUP_FROM = "2026-11-22"` (Pacific day; "9999" = out again) - `ncaab_spread_stack` adds
`ncaab_tuneup_spread_w`, and `mark_ncaab_tuneup` gives the SPREAD side off the tune-up its named reason. A tune-up
alone is +0.02 - never the +0.05 a play needs. Test `test_daily_1121_the_tune_up_weight_is_in_the_spread_stack_from_the_11_22_games`.

## S1 / S2 - do the non-D1 games spoil what the college hoops unit plays stand on? (s_cbb.py s1 s2)

No. The glass (a season rebound margin 6+ better than the opponent's, `sports.NCAAB_REB_GAP`) with the margin as the
engine reads it - every box game - against the same margin on D1 games only (both teams 3+ D1 box games):

| the glass dog +100..+350 | all | train 2021-23 | held 2024-26 |
|---|---|---|---|
| as built | +0.0% on 847 | -2.0% | +3.1% |
| every dog (the base) | -7.2% on 11,148 | -8.7% | -4.9% |
| 0 non-D1 games in its margin | +4.0% on 254 | +3.6% | +5.2% |
| 1 | -0.1% on 240 | -10.5% | +14.0% |
| 2+ | -2.8% on 353 | -1.4% | -4.3% |
| D1-only margin still 6+ | -0.9% on 676 | -0.9% | -0.8% |
| D1-only margin under 6 (padded) | +1.9% on 169 | -9.1% | +11.7% |
| Nov-Dec, 2+ non-D1 games | +2.4% on 115 | -9.0% | +17.2% |

A random same-size set of glass dogs did as badly as the 1-game / 2+-game / padded cells 970 / 609 / 1,186 times in
2,000. On the spread: glass 6+ -2.0% on 5,060 vs the -4.5% base; D1-only still 6+ -2.0% on 4,415, under 6 -1.8% on 640.
The glass 8+ dog +8.8% on 435 (train +8.0% 3 of 3 / held +10.2%).

The dog slot (the 11/16 replay rows, the slot as it runs live): +19.8% on 374 (train +17.0% / held +25.0%); both teams
4+ D1 games +18.6% on 354; a team under 4 D1 games (4+ only with tune-ups) +42.7% on 20; the dog with no non-D1 game
behind it +18.3% on 164, one +17.7% on 95, two or more +23.9% on 115. Nothing to tighten - today's UT Rio Grande and
Indiana St plays stand on what the replay tested.

## S9 - wins against what the prices expected (s_pro.py s9)

A team's wins minus the sum of its closing no-vig chances over its last 10 priced games this season (football: the
last 5). UNDER = -2.0 or worse, OVER = +2.0 or better.

| the dog +100..+350 that is UNDER, against a team that is OVER | all | train | held | the dog base |
|---|---|---|---|---|
| NBA | **+40.6% on 54** (z 2.2) | +49.4% on 25 (4 of 4) | +33.0% on 29 | -4.7% |
| NHL | +7.8% on 96 | +13.3% on 40 | +3.9% on 56 | -5.5% |
| college hoops | +11.0% on 84 | +5.4% on 33 | +14.6% on 51 | -8.5% |
| the mirror (the OVER dog against an UNDER team) | NBA -27.6% on 33 · NHL -8.3% on 45 · college hoops **-51.2% on 40** (both halves, z -3.3) | | | |

Alone (whoever the opponent) it is nothing: the NBA UNDER dog +4.2% on 595 (train +16.4% / held -7.5%), the NHL -1.2% on
840, college hoops -13.7% on 964 (the built cold-dog crowd). The NBA UNDER small favorite +8.7% on 174 (train +1.4% /
held +16.0%, placebo 30) - a watch. Football: 22 / 15 spread sides - unread. Three leagues one way, every cell under
100: a LEAD. `sports_leads.UNDER_PRICES_DOG_TAG` / `price_surplus` / `under_prices_dog` from the 11/22 games (NBA / NHL
/ college hoops). Judge at 60: +10% or better = the five checks as a +1 dog weight.

## The dead ones, in a line each

- **S4** the favorite with no D1 win (Nov-Dec, 2+ wins all over non-D1, 1+ D1 loss): its own spread +9.7% on 89 (train
  +34.8% / held -5.9%), the spread across -18.6% (train -44.3% / held -2.7%), the dog across -7.4% on 65 (placebo
  1,220). The card's 📋 line is a true fact; it is not an argument against a price.
- **S5** fumble luck (fumbles lost by the opponents minus ours, a game, 4+ box games): the college LUCKY side fails to
  cover in both halves (-11.3% on 724; 2024 -24.9 / 2025 -0.5 / 2026 -10.3) but its dog flips and the UNLUCKY side is
  not a bet-on (ATS -5.1%, dog +6.6% on 234, placebo 401). The NFL: the team that won with 2+ fumbles recovered covers
  the NEXT week +11.0% on 166 (placebo 42; train +2.4% / held +24.9%) - the wrong way for "luck". A WATCH with no tag:
  no football spread play or lean exists to weigh, the team box holds about half of 2024-26's college games, and the
  regular season has two weeks left - re-read in September.
- **S6** NFL defensive touchdowns: 3+ in a season ATS +1.2% on 282 (train -5.5% / held +11.6%); the dog off a win with
  one -21.5% on 93 (both halves down, placebo 227) - thin, a watch.
- **S7** the NHL puck line's price against the moneyline (a line fit on earlier seasons only, 9,400 games): nothing
  moves with the shape - dogs -6.9% / -6.7% at the two ends vs -5.4% in the middle, totals inside the vig.
- **S8** blown out twice at home: NHL 1,894 visiting dogs at such a team -7.0% against -4.4% on 1,137 at a team never blown out - the 🥊 line under today's
  Flyers pick is a fact, not a reason. NBA flips by half; the college home dog that has been blown out twice at home
  -12.1% on 954 (train -14.8% / held -9.6%, as badly by luck 14 of 2,000) is the built cold-dog fade's crowd.
- **S10** NBA starters' net: the starters winning their minutes by 3+ more than the scoreboard shows is nothing on
  either price; the reverse dog +6.3% on 484 (placebo 58) - a watch.

## Files

`lib.py` / `h.py` (copied from 11/20), `s_cbb.py` (S1-S4), `s_fb.py` (S5-S6), `s_pro.py` (S7-S10), `view.py` (one
short line a cell), `lead_tracker.py`, `*_out.txt`.
