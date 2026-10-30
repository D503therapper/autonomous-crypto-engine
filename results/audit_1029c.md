# 10/29 (night) - THIN EDGES

The owner, after 10/29's unit plays went 1-2 (-0.63u; the two ½u thin plays lost - the Blue Jackets +205 Dog 2-3, the
Panthers +164 floor play 19-27; the Mammoth -135 value play won): "Run Fable and fix the thin edge plays." Standing
authorization to fix without asking. The owner's 10/27 order holds throughout: at least ONE unit play per day, ½u fine for
a thin floor play. No posted pick changes.

Tools (scratchpad funnel1030/): `funnel_replay.py` (the 10/27 funnel script run on TODAY's code - the hot hockey dog -2,
the 2-point fallback hockey Dog, the no-thin-Lock rule, the NBA favorite play - with thin / own-gap / hot-dog flags;
1,097 board days 2023-10-01..2026-10-12 + the live tail 10/13..10/29, closing prices, params re-tuned each July, no injury
reports), `floor_sim2.py` / `floor_sim3.py` / `floor_sim4.py` (the variants), `thin_live.py` (the live record). Copies in
results/studies/thin_1029/.

## 1. LIVE - every unit play since 9/27, thin vs real (74 graded: 71 board, 3 early)

Thin = the engine's own read beats the price by under 3 cents on the dollar (sports.thin_edge on the posted leg).

| | W-L | units | ROI | CLV |
|---|---|---|---|---|
| all unit plays | 39-35 | +21.6u on 67.5u | +32.0% | +0.52 |
| **thin** | **22-22** | **-3.9u on 30.0u** | **-13.1%** | +0.31 (beat 15/44) |
| real edge | 17-13 | +25.5u on 37.5u | +68.0% | +0.84 |

Thin by kind: **Dog 4-11 -5.9u (-39%)**, Lock 6-5 -0.3u (-6%), value play 9-4 +1.8u (+26%), floor 2-2 +0.0u, solo 1-0.
Thin by sport: hockey 10-12 -3.1u, college football 6-6 -1.2u, NFL 3-4 -0.8u, MLB 3-0 +1.1u. Thin by price: favorites
-150..-101 **11-4 +2.1u (+27.5%)**, dogs +100..+150 10-11 -3.0u (-17.8%), +151..+199 1-5 -1.5u, +200..+350 0-2. Thin by the
own read over the no-vig market: 0-2 points 12-15 -3.5u (-16.9%), 2-4 points 9-6 -0.4u. Thin by the own read vs the price:
3c+ under 6-6 -0.6u, 0-3c under 7-10 -2.5u, 0-1.5c over 4-5 -2.4u, 1.5-3c over 4-1 +1.1u.

**What's losing: the thin DOG.** 14 of the 15 are hockey (4-10): Kings +160, Blackhawks +180, Flyers +110, Penguins +136 /
+102, Flames +195, Canadiens +105, Sharks +114, Predators +120, Blue Jackets +205 lost; Blues, Mammoth x2, Flames won -
every one the fallback hockey Dog with its own read 0.4-2.1 points over the no-vig market. The 10/29 afternoon rule (the
fallback Dog needs 2+ points over the market) keeps 14 of the 16 live hockey Dogs off. The 15th is Fresno St +250 (10/10).
The thin Lock (6-5) is off since 10/29 (it rides as a ½u value play). The thin favorite value play is fine (11-4), the floor
flat on four: Wild +102 W, Delaware +102 W, Flames +160 L, Panthers +164 L (the Bucks +270 were the NBA floor, not thin).

## 2. THE REPLAY - the floor / thin-Dog versions on today's code (train 2023-25, held out 2025-27)

| version | plays/day | train ROI | held ROI | ALL units (on) | worst | ≥1 play | seasons up |
|---|---|---|---|---|---|---|---|
| **TODAY: floor to 2 by dog score, thin Dog ½u, NBA floor** | 2.32 | +4.7% | +7.7% | +100.2u (1,678u) | -19.4u | 98.2% | 4/4 |
| (a) floor to 1 | 1.70 | +5.4% | +7.8% | +86.4u (1,342u) | -18.5u | 98.2% | 4/4 |
| (a) floor to 3 | 2.97 | +2.6% | +9.2% | +110.9u (2,038u) | -28.5u | 98.2% | 3/4 |
| (b) floor needs the own read at/over the no-vig market | 2.22 | +2.4% | +6.2% | +65.7u | -22.8u | 95.4% | 3/4 |
| (b) 1+ over the market | 1.94 | +3.2% | +5.7% | +63.2u | -17.5u | 87.9% | 4/4 |
| (b) 2+ over the market | 1.65 | +4.1% | +7.2% | +70.0u | -16.0u | 75.2% | 3/4 |
| (c) floor: no hockey +151..+350 | 2.31 | +4.8% | +7.3% | +98.8u | -18.9u | 98.1% | 4/4 |
| (c) no dog past +199 | 2.28 | +2.9% | +7.8% | +83.6u | -21.7u | 97.6% | 4/4 |
| (c) no dog past +150 | 2.24 | +3.2% | +7.7% | +84.1u | -20.1u | 96.5% | 4/4 |
| (c) no NFL | 2.28 | +4.5% | +7.1% | +93.3u | -19.4u | 97.0% | 4/4 |
| (c) no college football | 2.30 | +4.8% | +8.3% | +105.2u | -19.4u | 97.7% | 4/4 |
| (c) no NBA in the general floor (the NBA floor stays) | 2.18 | +4.3% | +8.4% | +97.3u | -21.6u | 96.4% | 3/4 |
| (c) no MLB | 1.68 | +4.4% | +8.4% | +80.3u | -23.2u | 71.1% | 3/4 |
| (c) score 3+ only | 1.72 | +4.7% | +7.1% | +76.6u | -15.6u | 78.3% | 3/4 |
| (c) thin only (own read under 3c over the price) | 2.29 | +5.3% | +7.8% | +106.1u | -22.8u | 97.8% | 4/4 |
| (d) ranked by the own-read gap | 2.32 | +2.6% | +6.2% | +69.8u | -25.0u | 98.2% | 2/4 |
| (d) ranked by dog score + gap | 2.32 | +4.4% | +7.3% | +94.9u | -19.2u | 98.2% | 4/4 |
| (d) ranked by edge_own | 2.32 | +3.1% | +6.9% | +79.8u | -24.3u | 98.2% | 4/4 |
| (e) the thin Dog is no Dog (the floor fills) | 2.24 | +4.2% | +7.2% | +90.5u | -19.6u | 98.2% | 4/4 |
| (e) the thin Dog needs 2+ over the market, else no Dog | 2.26 | +4.4% | +7.3% | +93.5u | -19.6u | 98.2% | 4/4 |
| (e) the thin Dog needs 1+ over the market | 2.27 | +4.5% | +7.3% | +95.0u | -19.6u | 98.2% | 4/4 |
| no NBA / no college football / thin only, NO fallback | 2.13 | +5.1% | +9.7% | +112.4u | -22.4u | 95.3% | 4/4 |
| **BUILT: no NBA / no college football / thin only, fallback to the best dog for 1 a day** | **2.25** | **+6.5%** | **+9.3%** | **+126.3u (1,644u)** | -23.2u | **98.2%** | **4/4** |

The floor plays alone, today vs built (flat ROI, train | held): all 268-343 +3.1% | 246-287 +5.7% -> 257-292 +7.6% |
247-259 +10.6%. The cells that drove it (both halves red): a second NBA dog a night 12-29 -5.0% | 4-15 -41.2%; college
football 7-12 -15.1% | 6-11 -15.0%; the floor dog with a REAL own edge 70-99 -4.6% | 10-20 -12.9% (the thin ones 198-244
+6.0% | 236-267 +6.8%; the own read UNDER the market 62-61 +24.4% | 44-33 +33.7%). The fallback (a skipped dog up only when
the board has no unit play) 10-10 +29.6% on 20. By season, built vs today: 2023-24 +42.5u vs +35.7u, 2024-25 +17.2u vs
+8.6u, 2025-26 +62.4u vs +55.2u, 2026-27 +4.1u vs +0.7u. The live tail 10/13-10/29 replayed at the close: 27-20 +13.8u vs
28-21 +13.9u (noise). Kinds under the built rule: floor 504-551 +9.0%, Dog 127-130 +8.3%, NBA floor 88-125 +14.3%, NBA
favorite 54-22 +22.7%, dog_play 43-49 +15.4%, Lock 94-60 +3.8%, value plays 351-251 +1.2%, fallback 10-10 +29.6%.

**The thin Dog of the Day is NOT the leak in the replay:** thin Dogs 55-59 +10.6% | 38-25 +38.0% vs real-edge Dogs 11-15
-3.8% | 23-31 -5.3% (the own-read-over Dog is a 2u play; the thin one ½u). Dropping it or asking 2 points over the market
lost ground. The live thin-Dog losses were the hockey fallback Dog (14 of 15), fixed 10/29 afternoon.

## 3. Multiple testing, honestly

About 45 versions were scored. The built version's gain over today's rules is +26u on ~1,650u risked (1.6 points of ROI)
with ~1,000 half-unit floor plays in each half - an ROI standard error near 3 points, so the gain is under one s.e. and the
held-out half was looked at while choosing. What carries it is the priors, not the p-value: the #2 side a night loses in
every study that looked (the 10/27 funnel's "every NBA dog -10.6%", the 10/29 opening-line "#2 side -5.4%"); the college
football dog the full read doesn't gate is the 10/23 / 10/28 loser (-7.9% / -8.1%); a dog the raw read loves while the
weighed read says no is the 10/27 finding that every ranking by the own read lost as a filler. Each piece is judged live at
50 floor plays, cut under -5% (the owner's 10/17 bar). The thin cut costs nothing the owner asked for: ≥1 unit play on
98.2% of days, the same as before, 2.25 plays a day vs 2.32.

## 4. Built (sports.py; test test_thin_edges_1029_the_floor_skips_nba_college_football_and_raw_read_dogs_with_a_one_a_day_fallback)

- `FLOOR_V2_FROM` 2026-10-30, `FLOOR_LEAGUES_OFF` ("nba", "ncaaf"), `FLOOR_THIN_ONLY` True, `FLOOR_FALLBACK_MIN` 1.
- `floor_skip(c)`: why a dog sits out the general floor (the NBA has its own floor / college football sits out / our raw read
  likes it more than the full read does), None for a floor dog.
- `floor_plays(cands, avoid, filtered=True)`: the kept dogs by score first, then the skipped ones flagged `floor_fallback`;
  `nba_floor_plays` reads the unfiltered list (the 🏀 floor still takes the best NBA dog at score 0+).
- `post_board`: a flagged dog posts only when `unit_plays_today` is still 0 (the owner's one-a-day floor), printed either way
  ("floor: X sits out - why" / "floor fallback: X - why, but the board has no unit play"); the pick carries
  `floor.fallback`. Units ½u, tag floor, the "VALUE PLAY · THIN EDGE" card, sizing_check / posted_kind unchanged.
- The 10/27 floor test updated to the new order (the NBA dog now comes last, flagged).

## 5. Not changed, with numbers

The floor at 2 (the second play adds +14u on 336u; the owner: "preferably more units"); the thin Dog at ½u (above); the thin
favorite value play (live 11-4, replay plays +1.2%); the no-thin-Lock rule; the NBA floor (+14.3%); the hockey Dog's 2-point
rule (10/29 afternoon). No model names anywhere; no odds re-pulled; no posted pick touched.
