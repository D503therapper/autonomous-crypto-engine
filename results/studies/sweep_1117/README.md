# 11/17 - THE FULL SWEEP, the favorites / totals / pipeline half

The owner, 11/16: *"run Fable, do a full sweep, and make the engine better on sizing, and study, and make the engine
better on these picks, especially our edge that we do on our underdog."* A second Fable run has the underdog paths. This
half: the favorites (the Lock, the backup Lock, value plays, the NBA favorite play, the college hoops favorite slot, the
⭐), the totals (⛰️ altitude over, 🏀 NBA over, 🌍 Europe under), the pipeline's health - and the lean removal, end to end.

**Short answer: no new size and no new gate cleared the bar - the favorites side is small and already tight. What this
sweep changed is the plumbing: SIX bugs fixed (three of them from the lean removal), each under a test. Eleven studies,
the nearest misses and the leads are below.**

## 1. The live ledger - every non-dog unit play since 10/25 (`s0_ledger.out`)

90 graded unit plays (board + early): 40-50, -0.95u on 68.5u. **The non-dog plays are the part that is up: 17-7, +1.97u
on 15.0u (+13.2%)**; the dogs 23-43, -2.93u on 53.5u.

| the non-dog plays | record | units | note |
|---|---|---|---|
| value plays (favorites) | 9-2 | +1.21u on 6.5u | hockey ½u 8-0 +2.82u; the two raised to 1u by the ⭐ (Stars -130, Ducks -142) 0-2 -2.0u |
| the Lock | 1-2 | -0.80u on 2.5u | all NFL: 49ers -142 ½u L, Broncos -142 1u ⭐ W, Packers -142 1u ⭐ L |
| 🏀 NBA favorite play | 1-0 | +0.81u on 1u | Celtics -124 |
| 🏀 NBA opening-line favorites (early) | 2-2 | -0.07u on 2u | |
| 🌍 Europe under | 3-0 | +1.37u on 1.5u | |
| ⛰️ altitude over | 0-1 | -1.00u on 1u | |
| 🏀 NBA over, the main guys out | 1-0 | +0.45u on 0.5u | |
| by sport | NHL 8-2 +0.82u · NFL 5-2 +0.96u · NBA 4-2 +1.19u · college hoops 0-1 -1.0u | | |
| **by size** | **½u 15-3 +4.46u on 9u · 1u 2-4 -2.49u on 6u** | | |
| the ⭐ on a non-dog | 1-3 | -2.30u on 4u | (the ⭐ on any side 4-6 +0.18u) |

The leak by name: **the 1u non-dog plays (2-4), three of the four losses a favorite the ⭐ raised to 1u.** 24 plays - the
prices expected 13.5 wins and they won 17; nothing here is outside luck either way. Since the 11/12 one-point edge rule
no hockey favorite value play has posted (none in 5 days).

## 2. The eleven studies

Rigs: the two replay boards of the 11/14-11/17 sizing studies (`sizing_1114/lib.py` - R1 = the 10/30 funnel rows, R2 =
the 11/12 rows on TODAY's code; 2023-10 -> 2026-11, closes; train to 6/30/2025, held out after), the 11/14 football
replay rows (2018-26; train to 6/2023), the 11/12 totals table (every close 2018-26; train to 2021), nflverse's closes.
`slib.py` prints the five checks on every cell: both halves and better than its siblings, most seasons up, a placebo
(a random same-size draw of its kind as good under 100 of 2,000), the worst stretch, a point worse than the close.

| # | study | what it found | verdict |
|---|---|---|---|
| S1 | the Lock on the boards (`s1_favs`) | R1 (the old read) 96-60 +5.8%; R2 (today's code) posts 6 Locks in three years - the honest dials leave almost no not-thin Lock outside football. No sport / price / size / gap cell separates | nothing to wire |
| S2 | value plays, favorites ½u | R1 190-138 +1.6% (held -6.8%); R2 16-7. -150..-135 +9.5% vs -134..-120 -10.9% on R1 (train +0.4% / held -30.8% - not both halves) | LEAD: the -134..-120 band |
| S3 | 🏀 NBA favorite play 1u | 54-22 +22.7% / 49-14 +34.1%, both halves, 3 of 3 seasons on both boards. 2u was answered 11/15: on the seasons nothing saw it keeps +1.8% - no 2u | stays 1u |
| S4 | every posted favorite: price x site x sport | the home favorite at -134..-120 is the one losing cell (R1 49-47 -8.6%, -8.3% / -8.9%, as bad by luck 78 of 2,000) - R1 only, R2 has 6 | LEAD |
| S5 | the ⭐ on a favorite vs a dog | R1: the ⭐ on a favorite 122-85 +1.6% (held -3.2%) vs on a dog 217-209 +18.1% (both halves, placebo 69). R2: 16 favorite stars, +9.9%. The ⭐'s order (Lock first) was answered 11/14 - no order beats a random eligible play | no change; live 1-3 is the R1 picture |
| S6 | the thin Lock rows (`s2_thin_lock`) | on today's code 225 days have a thin Lock-grade favorite and 204 of them never post (131-73 +9.9%, train +2.6% / held +22.7%). Hockey at home 40-15 +23.6% (train +11.5% / held +40.6%, placebo 190); hockey on the road 36-32 -9.4% | LEAD (R1: +9.5%, train -0.1%) - not both boards |
| S7 | ⛰️ altitude over 1u (`s3_totals`) | the rule rebuilt a fourth time: 500-342 +13.2%, 9 of 9 seasons, a point worse +8.2%, this season 5-1. No cell earns more: 1,800 m+ +18.0% (placebo 306), the price -111..-130 +21.8% (placebo 152) | stays 1u |
| S8 | 🏀 NBA over, the main guys out ½u | 110-74 +14.0% (train +16.9% / blind +12.1%), 2024 on +7.2% on 59. 4+ out +21.8% on 47 (placebo 531); "2+ of them played the last game" +17.6% (placebo 213) | stays ½u |
| S9 | 🌍 Europe morning under ½u | 28 games since 2014: 17-11, +16.3%; a random 28 NFL unders does as well 337 of 2,000. It does NOT clear a bar - it is the owner's live test with its quit rule, and stays that | stays ½u, the quit rule judges |
| S10 | the football Lock (`s4_football_lock`) | 106 Lock-grade favorites 2018-26. THIN 47-18 +23.5% (train +17.6% / held +33.7%, 8 of 9, placebo 23); NOT thin 20-21 -15.1%. The college thin Lock 20-5 +35.9% (+19.0% / +54.2%, 8 of 9) | the 11/16 call holds; the size-up is the nearest miss (below) |
| S11 | the ⭐ on a floor fallback (`s5_star_fallback`) | the kind (the day's best sit-out floor dog whose read beats its price): R1 133-228 -8.6% (-9.0% / -7.6%, as bad by luck 3 of 2,000); R2 28-29 +15.2% | not both boards - LEAD; the card bug it showed is fixed |

Not re-run (done 11/14-11/17, nothing new): the sizing ladder, the ⭐ order, the college hoops slots and the 💎 max
play, the spread stack (its judge at 100 graded comes first), the exam scan, the bye spot.

**Rules that no longer do their job / dead paths** (no change made, the owner should know):
- **The college hoops favorite slot** (-120..-150, own read over the price) fires about 3 times in eight replay seasons
  on today's code - since the 11/12 honest dials a college hoops favorite's own read sits at the price. The 💎 Lock-test
  favorite (11/16, on the weighed read) is what posts in its place.
- **The Lock outside football**: on today's code 4 hockey and 1 college hoops not-thin Lock in three years. "No Lock of
  the Day" is the normal day; the football thin Lock (11/16) and the 💎 are the live Lock paths.
- **Hockey favorite value plays** stopped with the 11/12 one-point edge rule (live 8-0 at ½u before it). The replay does
  not back bringing them back (the under-a-point hockey favorites: +3.8%, train -3.1% / held +15.6% - S6's lead).

## 3. The nearest miss - the college football thin Lock at 1u (`s4_football_lock.out`)

| the football Lock's sizes (the same 106 rows) | units (ROI) | train / held | worst stretch |
|---|---|---|---|
| TODAY (11/16): thin ½u, the NFL ½u, a not-thin college Lock 1u | +4.1u on 65.5u (+6.3%) | -1.0u / +5.1u | -5.5u |
| the college thin Lock 1u too | +8.6u on 78.0u (+11.0%) | +0.3u / +8.4u | -5.0u |
| every thin football Lock 1u | +11.8u on 98.0u (+12.0%) | +2.6u / +9.1u | -6.1u |
| the not-thin college Lock ½u | +4.5u on 53.0u (+8.6%) | +0.1u / +4.5u | -4.0u |

The college thin Lock clears four of the five checks (both halves, 8 of 9 seasons, a point worse +33.6%, the worst
stretch flat) and the placebo against every football Lock (68 of 2,000) - but against its OWN kind it does not separate:
a random 25 thin football Locks did as well 401 of 2,000 times, a random 25 college Locks 129. 25 plays in nine seasons,
found on the same rows the 11/16 call came from. **Not wired - the owner set ½u on 11/16; 1u on the college thin Lock is
his option** (about +0.5u a season). It answers the question the 11/16 note left open: a college thin Lock carrying the
⭐ at 1u is fine - it is the best football Lock cell, never bar it.

## 4. Bugs fixed (each with a test in `sports_test.py`, `test_sweep_1117_*`)

**The lean removal, end to end** - what still works: the page shows no lean card / record / row, the brain's sheet says
"NONE", the merge drops them, a night football game with no unit play gets no pick, the day recap / records / day_calls
read zero leans fine, picks.json holds none (132 rows, 137 archived, the two detectors agree on every row). What broke:

1. **An empty board looked like no board.** With no leans a day can post NOTHING, and nothing recorded that the board
   ran: (a) the page said "Picks drop at 8 AM PT" all day; (b) the bug check re-started the engine on every pass ("main
   board not up") and the pacer every 9 minutes through the 8 AM hour; (c) the day's first play, found at 11 AM, counted
   as "the 8 AM board" - no phone ping. Now the build stamps the day (`model["board_ran"]`, `sports.board_ran` /
   `note_board_ran`), the page says "No plays on today's board yet ... the engine checks the lines every hour" (a
   different wording each day, `sports_lingo.noplay_note`), the brain's sheet says it, the pacer and the bug check count
   it as up, and a play added after an empty opening board pings like any mid-day add.
2. **A replacement lean was still built** (the card written, the day's wording used up, possibly a "waiting on news"
   slot) and then thrown away - skipped outright now.
3. **A stale lean row in another job's copy of picks.json still locked a live side** - `sports_live.locked_sides` skips it.

**Stale / false card info:**

4. **The 🏀 NBA over's card kept saying a man was out after he came off the out list** (the owner, 11/12: "outdated
   information ... needs to be updated always"). Every hourly run now re-checks its names (`sports_nba_out.back`): a man
   listed questionable / probable again, or off the report he was on, comes off the "X without ..." line and a
   🔄 Update line says so. The play never changes.
5. **A long dog's line called a blowout.** The dry run's one play - Ball State +350, a 23% read, lost 2 straight, "the
   dog angles are mixed" - read "Ball State about to beat the brakes off 'em". A moneyline dog at +150 or longer under a
   40% read is a price play: the pool writes no blowout / sure-thing tail for it (`sports_breakdown_v24.long_dog`) and
   the card check cuts one off a posted card (`sports_card_check.SURE`).
6. **The ⏰ early pool wrote line-move talk** ("The books moved Wyoming shorter early - the money's on 'em") that the
   card check cut on every build (Wyoming +245, open now). Fixed at the root; the paused college "engine" spot's three
   facts were all line-move talk too - gone.

## 5. Leads (not wired, not on the tracker - a WATCH each)

- a favorite unit play at **-134..-120** (R1 value plays -10.9%, football Locks 16-17 -13.2%, the home ones -8.6% both
  halves on R1) against -150..-135 (+9.5% / +18.4%) - the cheap favorite is the weak one, the opposite of "closest to
  -150 is a moron's Lock". Not both boards.
- **a hockey thin Lock-grade favorite AT HOME** (left off the board since 11/12): 40-15 +23.6% on today's code.
- **the ⭐ on a floor fallback** - R1 says it doubles a losing kind, R2 says no.
- **the NFL not-thin Lock** 6-10 -33.5% (4 held-out plays - can't be judged; already ½u and never the ⭐).

## Files

`s0_ledger` (live) · `slib.py` (the five checks) · `s1_favs` (S1-S5) · `s2_thin_lock` (S6) · `s3_totals` (S7-S9) ·
`s4_football_lock` (S10) · `s5_star_fallback` (S11) - each `.py` with its `.out`.
