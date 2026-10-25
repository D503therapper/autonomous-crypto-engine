# 10/24 LIVE AUDIT - every unit play since the unit system began (2026-10-02), graded through 2026-10-24

From data/sports/picks.json + early.json (sports.units_ledger - the dashboard's own ledger), the close record (data/sports/clv_record.json - 'beat the close' = our price better than the last pre-start price; blank = no close on file), and the live plus-money log (no units - its own record). Leans carry no units and are not here. Early plays are dated by game day (the ledger's rule). 'lock (backup)' = a Lock whose blended win % sat under 56% (sports.backup_lock - the own read 56%+ beating the price) or a near-price Lock.

## 0. The verdicts (the owner, 10/24: "Run Fable and assess everything. And don't even ask me, just fix everything accordingly")

One bar for every rule: its live record AND its history (the 2023-26 board replays at the close, the 10/17 college gap
study, the early-spot studies). Never killed off a handful of live bets when a thousand games back it; never kept when
both say it loses. Full evidence in SPORTS_FINDINGS.md (10/24 night); the regression tests are test_audit_1024_*.

| rule | live (10/2-10/24) | history | call |
|---|---|---|---|
| Dog of the Day (own read over the price, 2u) | 7-9 +5.9u | 139-160 +5.8% flat / +12.9% at 2u, 3 of 5 seasons; hockey +19.9% on 169; +200..+350 2-13 (WATCH) | KEEP - and the own-read rule now holds on every path to it (a proven-angle dog had walked past it) |
| Lock (10/23 plan sizing, thin ½u) | 4-4 -1.1u (½u Locks 4-4) | 378-238 +6.1%, 5 of 5; the plan's sizing +58u blind +7.9% | KEEP |
| backup Lock | 1-1 +1.6u (UNLV 2.5u) | 16 in four seasons, 9-7 flat | FIX - ½u (the owner's rule since 10/2), never -119..-101 |
| value plays (½u, favorites only since 10/23) | 8-3 +3.4u | favorites ml +3.8% / +4.9% blind | KEEP |
| 🔍 gap plays (college own read 10+ over, rating-backed, 1u) | 3-6 -0.8u | the 10-15 band -8.8% / -13.0% / -16.8% (train / blind / 2026); 15+ +7.0% / -0.5% / +7.2% | TIGHTEN - 15+ points (GAP_MIN 0.15); judge at 50 |
| dog_plays (every gated runner-up, ½u - built 10/24) | 0-2 -1.0u | 69-118 -9.7%, 2 of 5; hoops -20.6% on 100 | RESIZE - the ONE best runner-up a day, never college hoops (flat / +20.6% on 43 without hoops) |
| early: exam band | 4-0 +10.8u | the walk-forward band test | KEEP |
| early: bye | 1-1 +1.1u | +16% college / +29% NFL at fair prices, every cutoff | KEEP |
| early: hammered | 1-1 +1.0u | the honest move model | KEEP |
| early: blowout (college) | 2-7 -2.0u | +4.4% on 610 with the engine; 104 of 250 FBS blowout wins vs FCS this season | TIGHTEN - FBS blowouts only |
| early: engine (college) | 3-6 -1.2u | the read holds nothing the market lacks (10/15-16); the money-left half loses (10/7) | PAUSE (SPOTS_OFF) |
| early: Europe under, NBA opening line | 1-1 / none yet | the owner's live tests, own quit rules | KEEP (the 🏀 play takes either side in -150..+300 - favorites were the better half blind) |
| owner posts | 2-0 +4.7u | - | his calls |
| live plus money | 16-17 +7% flat | - | unchanged (MLB paused, tennis 4-6) |

What 10/17 (+9.8u) had that 10/24 (+1.5u on 11u) lacked: one bet per read. 10/24 bet the same college own-read gap 14
times through four rules (engine spot x6, 🔍 x4, dog_plays x2, blowout x1) and went 4-11 on them; the Dog (Illinois
+310, 2u) and the exam band made the day. Under the new rules 10/24 is 4-7 +4.2u on 7.5u less bet; 10/17 is unchanged.

## 1. The headline - by type

### by type

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| dog | 7-9 | 19.5u | +5.9u | +30% | 4/16 |
| dog_play | 0-2 | 1u | -1.0u | -100% | 0/2 |
| early:best | 1-0 | 0.5u | +0.6u | +120% | - |
| early:blowout | 2-7 | 4.5u | -2.0u | -44% | - |
| early:bye | 1-1 | 2u | +1.1u | +57% | - |
| early:engine | 3-6 | 4.5u | -1.2u | -27% | - |
| early:euro_under | 1-1 | 1u | -0.0u | -4% | - |
| early:exam | 4-0 | 8u | +10.8u | +135% | - |
| early:hammered | 1-1 | 1u | +1.0u | +100% | - |
| gap 🔍 | 3-6 | 9u | -0.8u | -8% | 3/8 |
| lock | 4-4 | 4.5u | -1.1u | -24% | 3/7 |
| lock (backup) | 1-1 | 3u | +1.6u | +53% | 1/2 |
| owner post | 2-0 | 3u | +4.7u | +158% | 0/2 |
| value play | 8-3 | 5.5u | +3.4u | +62% | 2/11 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

### by type x sport

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('dog', 'ncaaf') | 2-1 | 5u | +9.1u | +182% | 0/3 |
| ('dog', 'nfl') | 1-0 | 1u | +1.2u | +120% | 0/1 |
| ('dog', 'nhl') | 4-8 | 13.5u | -4.4u | -33% | 4/12 |
| ('dog_play', 'ncaaf') | 0-2 | 1u | -1.0u | -100% | 0/2 |
| ('early:best', 'nfl') | 1-0 | 0.5u | +0.6u | +120% | - |
| ('early:blowout', 'ncaaf') | 2-5 | 3.5u | -1.0u | -29% | - |
| ('early:blowout', 'nfl') | 0-2 | 1u | -1.0u | -100% | - |
| ('early:bye', 'ncaaf') | 1-1 | 2u | +1.1u | +57% | - |
| ('early:engine', 'ncaaf') | 3-6 | 4.5u | -1.2u | -27% | - |
| ('early:euro_under', 'nfl') | 1-1 | 1u | -0.0u | -4% | - |
| ('early:exam', 'mlb') | 2-0 | 6u | +7.7u | +128% | - |
| ('early:exam', 'ncaaf') | 2-0 | 2u | +3.1u | +154% | - |
| ('early:hammered', 'ncaaf') | 1-1 | 1u | +1.0u | +100% | - |
| ('gap 🔍', 'ncaaf') | 3-6 | 9u | -0.8u | -8% | 3/8 |
| ('lock (backup)', 'ncaaf') | 1-1 | 3u | +1.6u | +53% | 1/2 |
| ('lock', 'mlb') | 1-1 | 1.5u | -0.6u | -41% | 1/2 |
| ('lock', 'ncaaf') | 1-1 | 1u | -0.2u | -16% | 0/2 |
| ('lock', 'nfl') | 1-2 | 1.5u | -0.6u | -42% | 2/3 |
| ('lock', 'nhl') | 1-0 | 0.5u | +0.4u | +70% | - |
| ('owner post', 'ncaaf') | 1-0 | 2u | +3.6u | +180% | 0/1 |
| ('owner post', 'nhl') | 1-0 | 1u | +1.1u | +114% | 0/1 |
| ('value play', 'ncaaf') | 5-2 | 3.5u | +2.1u | +61% | 1/7 |
| ('value play', 'nhl') | 3-1 | 2u | +1.3u | +64% | 1/4 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

### by type x price band

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('dog', '+100..+150') | 4-7 | 12.5u | -3.7u | -30% | 4/11 |
| ('dog', '+150..+250') | 2-2 | 5u | +3.4u | +69% | 0/4 |
| ('dog', '+250..+350') | 1-0 | 2u | +6.2u | +310% | 0/1 |
| ('dog_play', '+100..+150') | 0-2 | 1u | -1.0u | -100% | 0/2 |
| ('early:best', '+100..+150') | 1-0 | 0.5u | +0.6u | +120% | - |
| ('early:blowout', '+100..+150') | 1-3 | 2u | -1.0u | -50% | - |
| ('early:blowout', '+150..+250') | 1-4 | 2.5u | -1.0u | -40% | - |
| ('early:bye', '+150..+250') | 1-1 | 2u | +1.1u | +57% | - |
| ('early:engine', '+100..+150') | 3-5 | 4u | -0.7u | -18% | - |
| ('early:engine', '+150..+250') | 0-1 | 0.5u | -0.5u | -100% | - |
| ('early:euro_under', 'fav') | 1-1 | 1u | -0.0u | -4% | - |
| ('early:exam', '+100..+150') | 3-0 | 7u | +8.8u | +126% | - |
| ('early:exam', '+150..+250') | 1-0 | 1u | +2.0u | +195% | - |
| ('early:hammered', '+100..+150') | 0-1 | 0.5u | -0.5u | -100% | - |
| ('early:hammered', '+250..+350') | 1-0 | 0.5u | +1.5u | +300% | - |
| ('gap 🔍', '+100..+150') | 2-4 | 6u | -1.9u | -31% | 2/5 |
| ('gap 🔍', '+150..+250') | 0-2 | 2u | -2.0u | -100% | 1/2 |
| ('gap 🔍', '+250..+350') | 1-0 | 1u | +3.1u | +310% | 0/1 |
| ('lock (backup)', '+100..+150') | 0-1 | 0.5u | -0.5u | -100% | 1/1 |
| ('lock (backup)', 'fav') | 1-0 | 2.5u | +2.1u | +83% | 0/1 |
| ('lock', 'fav') | 4-4 | 4.5u | -1.1u | -24% | 3/7 |
| ('owner post', '+100..+150') | 1-0 | 1u | +1.1u | +114% | 0/1 |
| ('owner post', '+150..+250') | 1-0 | 2u | +3.6u | +180% | 0/1 |
| ('value play', '+100..+150') | 6-3 | 4.5u | +1.9u | +42% | 1/9 |
| ('value play', '+150..+250') | 1-0 | 0.5u | +1.2u | +235% | 1/1 |
| ('value play', 'fav') | 1-0 | 0.5u | +0.4u | +70% | 0/1 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

### by sport

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| mlb | 3-1 | 7.5u | +7.1u | +94% | 1/2 |
| ncaaf | 22-26 | 37.5u | +17.5u | +47% | 5/25 |
| nfl | 4-5 | 5u | +0.1u | +3% | 2/4 |
| nhl | 9-9 | 17u | -1.6u | -10% | 5/17 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

### by price band

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| +100..+150 | 21-26 | 39.5u | +3.2u | +8% | 8/29 |
| +150..+250 | 7-10 | 15.5u | +7.8u | +50% | 2/8 |
| +250..+350 | 3-0 | 3.5u | +10.8u | +309% | 0/2 |
| fav | 7-5 | 8.5u | +1.3u | +16% | 3/9 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

## 2. Saturday college vs the rest

### Saturday (PT) college football vs everything else

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| SAT college | 15-24 | 30.5u | +10.4u | +34% | 4/22 |
| SAT other | 2-2 | 2.5u | -0.6u | -23% | 0/3 |
| weekday | 21-15 | 34u | +13.3u | +39% | 9/23 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

### Saturday college by type

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| dog | 2-1 | 5u | +9.1u | +182% | 0/3 |
| dog_play | 0-2 | 1u | -1.0u | -100% | 0/2 |
| early:blowout | 0-3 | 1.5u | -1.5u | -100% | - |
| early:bye | 1-1 | 2u | +1.1u | +57% | - |
| early:engine | 2-6 | 4u | -1.8u | -45% | - |
| early:exam | 1-0 | 1u | +2.0u | +195% | - |
| early:hammered | 1-1 | 1u | +1.0u | +100% | - |
| gap 🔍 | 2-6 | 8u | -1.8u | -22% | 2/7 |
| lock | 0-1 | 0.5u | -0.5u | -100% | 0/1 |
| lock (backup) | 1-1 | 3u | +1.6u | +53% | 1/2 |
| value play | 5-2 | 3.5u | +2.1u | +61% | 1/7 |
| **all** | 15-24 | 30.5u | +10.4u | +34% | 4/22 |

### by Saturday (college unit plays, every type)

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| 2026-10-03 | 3-0 | 3.5u | +3.2u | +91% | 0/3 |
| 2026-10-10 | 1-7 | 5u | -4.1u | -83% | 0/3 |
| 2026-10-17 | 7-6 | 11u | +9.8u | +89% | 4/10 |
| 2026-10-24 | 4-11 | 11u | +1.5u | +14% | 0/6 |
| **all** | 15-24 | 30.5u | +10.4u | +34% | 4/22 |

### by day (all unit plays)

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| 2026-10-02 | 1-0 | 1u | +1.5u | +154% | 0/1 |
| 2026-10-03 | 4-1 | 5u | +2.8u | +55% | 0/5 |
| 2026-10-04 | 2-1 | 2u | +1.3u | +65% | 0/2 |
| 2026-10-05 | 0-2 | 2u | -2.0u | -100% | 1/2 |
| 2026-10-06 | 1-0 | 1u | +1.1u | +110% | 1/1 |
| 2026-10-07 | 1-2 | 2u | -1.2u | -58% | 0/2 |
| 2026-10-08 | 1-1 | 1.5u | -0.3u | -20% | 0/2 |
| 2026-10-09 | 1-2 | 2u | -0.9u | -45% | 1/1 |
| 2026-10-10 | 1-8 | 5.5u | -4.6u | -85% | 0/4 |
| 2026-10-11 | 2-2 | 2u | -0.2u | -9% | 1/1 |
| 2026-10-12 | 1-0 | 3u | +3.4u | +112% | - |
| 2026-10-13 | 3-0 | 2u | +2.3u | +117% | 1/3 |
| 2026-10-14 | 1-1 | 4u | +3.3u | +83% | 1/1 |
| 2026-10-15 | 1-1 | 1.5u | +0.5u | +35% | 2/2 |
| 2026-10-17 | 7-6 | 11u | +9.8u | +89% | 4/10 |
| 2026-10-18 | 0-1 | 0.5u | -0.5u | -100% | - |
| 2026-10-19 | 0-1 | 1.5u | -1.5u | -100% | 0/1 |
| 2026-10-20 | 1-0 | 1u | +1.1u | +114% | - |
| 2026-10-22 | 1-1 | 3u | -0.9u | -29% | 0/2 |
| 2026-10-23 | 4-0 | 4u | +6.1u | +152% | 1/2 |
| 2026-10-24 | 5-11 | 11.5u | +1.9u | +16% | 0/6 |
| **all** | 38-41 | 67u | +23.1u | +35% | 13/48 |

## 3. Thin edge vs real edge (board picks with an own read)

### thin edge (own read under 3% over the price) vs real

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| real | 11-10 | 23.5u | +16.0u | +68% | 6/20 |
| thin | 14-15 | 22u | -3.2u | -15% | 7/28 |
| **all** | 25-25 | 45.5u | +12.8u | +28% | 13/48 |

### thin vs real, by type

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('dog', 'real') | 3-1 | 6u | +10.3u | +172% | 0/4 |
| ('dog', 'thin') | 4-8 | 13.5u | -4.4u | -33% | 4/12 |
| ('dog_play', 'real') | 0-2 | 1u | -1.0u | -100% | 0/2 |
| ('gap 🔍', 'real') | 3-6 | 9u | -0.8u | -8% | 3/8 |
| ('lock (backup)', 'real') | 1-0 | 2.5u | +2.1u | +83% | 0/1 |
| ('lock (backup)', 'thin') | 0-1 | 0.5u | -0.5u | -100% | 1/1 |
| ('lock', 'real') | 0-1 | 1u | -1.0u | -100% | 1/1 |
| ('lock', 'thin') | 4-3 | 3.5u | -0.1u | -2% | 2/6 |
| ('owner post', 'real') | 2-0 | 3u | +4.7u | +158% | 0/2 |
| ('value play', 'real') | 2-0 | 1u | +1.7u | +168% | 2/2 |
| ('value play', 'thin') | 6-3 | 4.5u | +1.7u | +39% | 0/9 |
| **all** | 25-25 | 45.5u | +12.8u | +28% | 13/48 |

## 4. The Dog of the Day - own read over / under the price, by sport and price

### Dog by own read vs the price

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| own over | 4-3 | 10u | +11.9u | +119% | 0/7 |
| own under / none | 4-6 | 11.5u | -2.4u | -21% | 4/10 |
| **all** | 8-9 | 21.5u | +9.5u | +44% | 4/17 |

### Dog by sport x own read

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('ncaaf', 'own over') | 3-0 | 6u | +13.7u | +228% | 0/3 |
| ('ncaaf', 'own under / none') | 0-1 | 1u | -1.0u | -100% | 0/1 |
| ('nfl', 'own over') | 1-0 | 1u | +1.2u | +120% | 0/1 |
| ('nhl', 'own over') | 0-3 | 3u | -3.0u | -100% | 0/3 |
| ('nhl', 'own under / none') | 4-5 | 10.5u | -1.4u | -13% | 4/9 |
| **all** | 8-9 | 21.5u | +9.5u | +44% | 4/17 |

### Dog by price band

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| +100..+150 | 4-7 | 12.5u | -3.7u | -30% | 4/11 |
| +150..+250 | 3-2 | 7u | +7.0u | +101% | 0/5 |
| +250..+350 | 1-0 | 2u | +6.2u | +310% | 0/1 |
| **all** | 8-9 | 21.5u | +9.5u | +44% | 4/17 |

### Dog by units

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| 1.0 | 5-7 | 12u | -0.7u | -6% | 4/12 |
| 1.5 | 0-1 | 1.5u | -1.5u | -100% | 0/1 |
| 2.0 | 3-1 | 8u | +11.7u | +146% | 0/4 |
| **all** | 8-9 | 21.5u | +9.5u | +44% | 4/17 |

## 5. Locks by size and kind

### Locks by units

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| 0.5 | 4-4 | 4u | -0.6u | -14% | 3/7 |
| 1.0 | 0-1 | 1u | -1.0u | -100% | 1/1 |
| 2.5 | 1-0 | 2.5u | +2.1u | +83% | 0/1 |
| **all** | 5-5 | 7.5u | +0.5u | +7% | 4/9 |

### Locks: backup vs full test, w_p over the price

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('lock (backup)', 'w_p none/under') | 0-1 | 0.5u | -0.5u | -100% | 1/1 |
| ('lock (backup)', 'w_p over') | 1-0 | 2.5u | +2.1u | +83% | 0/1 |
| ('lock', 'w_p none/under') | 2-1 | 2u | -0.3u | -13% | 2/3 |
| ('lock', 'w_p over') | 2-3 | 2.5u | -0.8u | -32% | 1/4 |
| **all** | 5-5 | 7.5u | +0.5u | +7% | 4/9 |

## 6. Early plays by spot

### early by spot x sport

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('early:best', 'nfl') | 1-0 | 0.5u | +0.6u | +120% | - |
| ('early:blowout', 'ncaaf') | 2-5 | 3.5u | -1.0u | -29% | - |
| ('early:blowout', 'nfl') | 0-2 | 1u | -1.0u | -100% | - |
| ('early:bye', 'ncaaf') | 1-1 | 2u | +1.1u | +57% | - |
| ('early:engine', 'ncaaf') | 3-6 | 4.5u | -1.2u | -27% | - |
| ('early:euro_under', 'nfl') | 1-1 | 1u | -0.0u | -4% | - |
| ('early:exam', 'mlb') | 2-0 | 6u | +7.7u | +128% | - |
| ('early:exam', 'ncaaf') | 2-0 | 2u | +3.1u | +154% | - |
| ('early:hammered', 'ncaaf') | 1-1 | 1u | +1.0u | +100% | - |
| **all** | 13-16 | 21.5u | +10.3u | +48% | - |

### early by spot x price band

| cut | W-L | units bet | net units | ROI | beat the close |
|---|---|---|---|---|---|
| ('early:best', '+100..+150') | 1-0 | 0.5u | +0.6u | +120% | - |
| ('early:blowout', '+100..+150') | 1-3 | 2u | -1.0u | -50% | - |
| ('early:blowout', '+150..+250') | 1-4 | 2.5u | -1.0u | -40% | - |
| ('early:bye', '+150..+250') | 1-1 | 2u | +1.1u | +57% | - |
| ('early:engine', '+100..+150') | 3-5 | 4u | -0.7u | -18% | - |
| ('early:engine', '+150..+250') | 0-1 | 0.5u | -0.5u | -100% | - |
| ('early:euro_under', 'fav') | 1-1 | 1u | -0.0u | -4% | - |
| ('early:exam', '+100..+150') | 3-0 | 7u | +8.8u | +126% | - |
| ('early:exam', '+150..+250') | 1-0 | 1u | +2.0u | +195% | - |
| ('early:hammered', '+100..+150') | 0-1 | 0.5u | -0.5u | -100% | - |
| ('early:hammered', '+250..+350') | 1-0 | 0.5u | +1.5u | +300% | - |
| **all** | 13-16 | 21.5u | +10.3u | +48% | - |

### the ⏰ box's own spot records (every graded early play, from 9/30)
| spot | W-L | units |
|---|---|---|
| best | 1-0 | +0.6u |
| blowout | 2-7 | -2.0u |
| bye | 1-1 | +1.1u |
| engine | 3-6 | -1.2u |
| euro_under | 1-1 | -0.0u |
| hammered | 1-1 | +1.0u |
| exam band (no spot) | 4-0 | +10.8u |

Pulled before kickoff, never graded: 10 (Delaware +220, Old Dominion +145, Tulane +220, UAB +190, Air Force +130, Rice +136, Tennessee +270, Georgia Tech +295, E Michigan +190, San Diego St +245).

## 7. Live plus money (no units - its own record, flat 1u for the ROI)
| sport | W-L | flat ROI |
|---|---|---|
| mlb | 0-5 | -100% |
| ncaaf | 3-2 | +25% |
| nfl | 9-4 | +58% |
| tennis | 4-6 | -14% |
| **all** | 16-17 | +7% |

## 8. Every unit play, one line each
| date | type | sport | team | price | units | result | net | own edge | close pts |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-02 | dog | nhl | Blues | +154 | 1u | won | +1.54u | -2.6% | 0.0 |
| 2026-10-03 | dog | nhl | Flyers | +110 | 1u | lost | -1.00u | +0.4% | -0.9 |
| 2026-10-03 | lock (backup) | ncaaf | UNLV | -120 | 2.5u | won | +2.08u | +5.5% | 0.0 |
| 2026-10-03 | value play | ncaaf | Kentucky | +120 | 0.5u | won | +0.60u | -3.0% | 0.0 |
| 2026-10-03 | value play | nhl | Predators | +114 | 0.5u | won | +0.57u | +0.5% | -1.3 |
| 2026-10-03 | value play | ncaaf | Fresno St | +102 | 0.5u | won | +0.51u | -1.0% | -1.9 |
| 2026-10-04 | dog | nfl | Jaguars | +120 | 1u | won | +1.20u | +3.0% | 0.0 |
| 2026-10-04 | early:best | nfl | Jaguars | +120 | 0.5u | won | +0.60u |  |  |
| 2026-10-04 | lock | nfl | Cardinals | -135 | 0.5u | lost | -0.50u | -1.4% | 0.0 |
| 2026-10-05 | dog | nhl | Sharks | +145 | 1u | lost | -1.00u | +11.9% | -3.8 |
| 2026-10-05 | lock | mlb | Guardians | -149 | 1u | lost | -1.00u | +3.1% | 1.3 |
| 2026-10-06 | dog | nhl | Mammoth | +110 | 1u | won | +1.10u | -2.9% | 1.2 |
| 2026-10-07 | dog | nhl | Penguins | +136 | 1u | lost | -1.00u | -3.0% | 0.0 |
| 2026-10-07 | early:blowout | ncaaf | New Mexico St | +180 | 0.5u | lost | -0.50u |  |  |
| 2026-10-07 | lock | ncaaf | Jax State | -148 | 0.5u | won | +0.34u | +1.5% | 0.0 |
| 2026-10-08 | dog | nhl | Flames | +195 | 1u | lost | -1.00u | +0.7% | 0.0 |
| 2026-10-08 | value play | nhl | Predators | +140 | 0.5u | won | +0.70u | -2.8% | 0.0 |
| 2026-10-09 | dog | nhl | Penguins | +102 | 1u | lost | -1.00u | -3.5% | 1.0 |
| 2026-10-09 | early:blowout | ncaaf | Florida St | +215 | 0.5u | lost | -0.50u |  |  |
| 2026-10-09 | early:engine | ncaaf | Iowa | +120 | 0.5u | won | +0.60u |  |  |
| 2026-10-10 | dog | ncaaf | Fresno St | +250 | 1u | lost | -1.00u | -1.4% | 0.0 |
| 2026-10-10 | early:blowout | ncaaf | Alabama | +130 | 0.5u | lost | -0.50u |  |  |
| 2026-10-10 | early:blowout | ncaaf | Fresno St | +205 | 0.5u | lost | -0.50u |  |  |
| 2026-10-10 | early:bye | ncaaf | Tulane | +205 | 1u | lost | -1.00u |  |  |
| 2026-10-10 | early:engine | ncaaf | NC State | +124 | 0.5u | lost | -0.50u |  |  |
| 2026-10-10 | early:engine | ncaaf | UMass | +120 | 0.5u | lost | -0.50u |  |  |
| 2026-10-10 | lock | ncaaf | Minnesota | -142 | 0.5u | lost | -0.50u | -0.1% | 0.0 |
| 2026-10-10 | value play | ncaaf | Illinois | -142 | 0.5u | won | +0.35u | +0.0% | 0.0 |
| 2026-10-10 | value play | nhl | Flames | +102 | 0.5u | lost | -0.50u | +0.5% | 0.0 |
| 2026-10-11 | early:blowout | nfl | Colts | +124 | 0.5u | lost | -0.50u |  |  |
| 2026-10-11 | early:blowout | nfl | Falcons | +120 | 0.5u | lost | -0.50u |  |  |
| 2026-10-11 | early:euro_under | nfl | Under 41.5 | -109 | 0.5u | won | +0.46u |  |  |
| 2026-10-11 | lock | nfl | Vikings | -135 | 0.5u | won | +0.37u | +2.5% | 1.2 |
| 2026-10-12 | early:exam | mlb | Brewers | +112 | 3u | won | +3.36u |  |  |
| 2026-10-13 | dog | nhl | Flames | +145 | 1u | won | +1.45u | -2.8% | 0.0 |
| 2026-10-13 | lock | mlb | Rays | -132 | 0.5u | won | +0.38u | +1.7% | -0.2 |
| 2026-10-13 | value play | nhl | Kraken | +102 | 0.5u | won | +0.51u | +8.9% | 2.4 |
| 2026-10-14 | dog | nhl | Canadiens | +105 | 1u | lost | -1.00u | -3.1% | 1.2 |
| 2026-10-14 | early:exam | mlb | Brewers | +144 | 3u | won | +4.32u |  |  |
| 2026-10-15 | dog | nhl | Mammoth | +102 | 1u | won | +1.02u | -3.3% | 4.0 |
| 2026-10-15 | lock | nfl | Seahawks | -142 | 0.5u | lost | -0.50u | +2.7% | 1.0 |
| 2026-10-17 | dog | ncaaf | Boston College | +195 | 2u | won | +3.90u | +3.4% | -0.6 |
| 2026-10-17 | early:bye | ncaaf | Boston College | +215 | 1u | won | +2.15u |  |  |
| 2026-10-17 | early:exam | ncaaf | Kentucky | +195 | 1u | won | +1.95u |  |  |
| 2026-10-17 | early:hammered | ncaaf | BYU | +300 | 0.5u | won | +1.50u |  |  |
| 2026-10-17 | gap 🔍 | ncaaf | Indiana | +130 | 1u | lost | -1.00u | +47.3% | 2.0 |
| 2026-10-17 | gap 🔍 | ncaaf | E Michigan | +210 | 1u | lost | -1.00u | +56.2% | -2.0 |
| 2026-10-17 | gap 🔍 | ncaaf | Rice | +164 | 1u | lost | -1.00u | +62.2% | 1.5 |
| 2026-10-17 | gap 🔍 | ncaaf | BYU | +310 | 1u | won | +3.10u | +69.9% | -0.6 |
| 2026-10-17 | lock (backup) | ncaaf | Wisconsin | +114 | 0.5u | lost | -0.50u | -4.0% | 2.8 |
| 2026-10-17 | value play | ncaaf | FAU | +110 | 0.5u | lost | -0.50u | -4.2% | 0.0 |
| 2026-10-17 | value play | ncaaf | Air Force | +102 | 0.5u | won | +0.51u | +2.2% | 0.0 |
| 2026-10-17 | value play | ncaaf | Troy | +124 | 0.5u | lost | -0.50u | -4.0% | 0.0 |
| 2026-10-17 | value play | ncaaf | San Diego St | +235 | 0.5u | won | +1.18u | +3.7% | 1.4 |
| 2026-10-18 | early:euro_under | nfl | Under 42.5 | -111 | 0.5u | lost | -0.50u |  |  |
| 2026-10-19 | dog | nhl | Sharks | +114 | 1.5u | lost | -1.50u | -3.0% | 0.0 |
| 2026-10-20 | early:exam | ncaaf | Marshall | +114 | 1u | won | +1.14u |  |  |
| 2026-10-22 | dog | nhl | Predators | +120 | 2u | lost | -2.00u | -2.7% | -2.0 |
| 2026-10-22 | owner post | nhl | Sharks | +114 | 1u | won | +1.14u | +3.0% | 0.0 |
| 2026-10-23 | early:blowout | ncaaf | Wyoming | +200 | 0.5u | won | +1.00u |  |  |
| 2026-10-23 | early:blowout | ncaaf | Army | +100 | 0.5u | won | +0.50u |  |  |
| 2026-10-23 | gap 🔍 | ncaaf | Army | +100 | 1u | won | +1.00u | +16.4% | 1.2 |
| 2026-10-23 | owner post | ncaaf | Wyoming | +180 | 2u | won | +3.60u | +10.2% | -3.5 |
| 2026-10-24 | dog | ncaaf | Illinois | +310 | 2u | won | +6.20u | +18.1% | 0.0 |
| 2026-10-24 | dog_play | ncaaf | N Illinois | +124 | 0.5u | lost | -0.50u | +8.2% | 0.0 |
| 2026-10-24 | dog_play | ncaaf | Mississippi St | +102 | 0.5u | lost | -0.50u | +6.3% | 0.0 |
| 2026-10-24 | early:blowout | ncaaf | Ole Miss | +190 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | early:engine | ncaaf | Auburn | +200 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | early:engine | ncaaf | W Michigan | +150 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | early:engine | ncaaf | C Michigan | +102 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | early:engine | ncaaf | Navy | +114 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | early:engine | ncaaf | Arkansas St | +110 | 0.5u | won | +0.55u |  |  |
| 2026-10-24 | early:engine | ncaaf | Wisconsin | +130 | 0.5u | won | +0.65u |  |  |
| 2026-10-24 | early:hammered | ncaaf | Tulane | +114 | 0.5u | lost | -0.50u |  |  |
| 2026-10-24 | gap 🔍 | ncaaf | C Michigan | +140 | 1u | lost | -1.00u | +36.4% | -0.9 |
| 2026-10-24 | gap 🔍 | ncaaf | Tennessee | +114 | 1u | lost | -1.00u | +36.7% | 0.0 |
| 2026-10-24 | gap 🔍 | ncaaf | Arkansas St | +114 | 1u | won | +1.14u | +35.1% | 0.0 |
| 2026-10-24 | gap 🔍 | ncaaf | Ole Miss | +130 | 1u | lost | -1.00u | +29.6% |  |
| 2026-10-24 | lock | nhl | Mammoth | -142 | 0.5u | won | +0.35u | +0.2% |  |
