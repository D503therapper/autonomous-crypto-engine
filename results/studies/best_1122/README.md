# 11/22 - FABLE: WHY THE ⭐ ENGINE'S BEST PICK HAS LOST

The owner, 11/22: *"I'm trying to figure out why the engine's best picks are so bad"* ... *"Run fable this needs
fixed."* The day before: *"the engine's best pick should obviously be the largest bet. Or if we have multiple bets that
are like 2-unit plays, the engine's best pick will be the most confident one ... we can't say put 2 units on this and 2
units on this but this is our best pick, put 1 unit on our best pick."*

**The answer, plain.** Mostly bad luck, plus one real flaw.

- **The luck.** Live the ⭐ is 5-10, -4.4u on 22u. At the prices it took, 6.9 wins were expected: z -1.0, a run that
  happens about one time in six. The ⭐ is the board's biggest bet, so a bad run on it costs the most - three hockey Dogs
  at 2-3u (Canucks, Capitals, the Ducks max play) are -7u of it. The other plays ran hot at the same time (23-16, nine
  favorites 9-0, z +1.7).
- **What is real.** On the replay the ⭐ is a normal winning play (+12% flat on 389 days), but it is NOT a better bet
  than the rest of the board - and no other way of choosing it is either. Every choice tried lands inside what a random
  play of the day's pool does. So the ⭐ earns no size of its own.
- **The flaw.** On a day with nothing bigger, the ⭐ lifted a half-unit thin-edge play to a full unit - doubling the very
  groups the 11/17 sizing plan refused to size up (the hockey favorite value play, the floor, the long dog). Those added
  half units made +2.2% in the replay's first half (a random half-unit play does as well a third of the time) and went
  1-4 live.

**Wired, from the 11/24 Pacific games** (`sports.BEST_HONEST_FROM`; a posted pick keeps its units):

1. The ⭐ is a label on the board's **biggest** unit play, at the size the engine's own sizing gave it. A half-unit play
   that carries the ⭐ **stays a half unit**; its note says it is a thin day.
2. The 11/17 **2u ⭐ stays** (a Lock / a Dog of the Day / a play 1u+ by its own size, at +150 or shorter) - the one cell
   of the raise that is up in both halves.
3. The ⭐ is **never smaller than another play on the board**: when a bigger unit play is up that the ⭐ can't sit on (its
   read doesn't beat its price, the engine's own read fights it, the NFL Lock), there is no ⭐ that day.
4. Between plays the same size, the bigger edge on its read decides (unchanged from 11/22).

The replay board: **+69.9u a year (+17.0%, worst stretch -23.8u) -> +67.2u a year (+17.3%, -22.1u)**, both halves and 4
of 4 seasons up.

## The rig (`blib.py`)

profit_1117's board (money_1117's R3L: the board the 11/17 code builds, every board day 2023-10 -> 2026-11 at the
closing price, the live post's shape, the 11/17 max-profit sizes in): 1,108 unit plays on 600 board days (train to
6/30/2025, held out 7/2025 -> 10/12/2026; the live weeks apart). The ⭐'s pool is `sports.best_pool`'s: -150..+350, the
own read not fighting, the read over the price, never the NFL Lock - a pool on 389 days, 2+ plays to choose from on 137.
**Limits:** no injury reports, the close (not the 8 AM price); the dog score's weights were fit with these seasons seen,
so "held out" is the later half, not a clean blind test; the early box, the totals, the spread stack play and plays
added after the 8 AM board are not on it. The rows live in `~/.cache/d503_dogs1117/rows` (never the repo).

## 0. Live (`s0_live.out`, from data/sports/picks.json)

| | record | units | flat 1u | the prices expect | z |
|---|---|---|---|---|---|
| the ⭐ as graded | 5-10 | -4.4u on 22u (-20%) | -4.1u | 6.9 wins | -1.02 |
| the ⭐ at its own size (the raise off) | 5-10 | -5.0u on 18u | | | |
| the raise alone (the added units) | 2-4 | +0.6u on 4u | | | |
| ... the ½u -> 1u lifts (Suns, Stars, Illinois, Boston College, Ducks -142) | 1-4 | -1.2u on 2.5u | | | |
| every other unit play | 23-16 | +9.1u on 32.5u | +9.3u | 17.8 wins | +1.70 |
| ... the other favorites | 9-0 | | | 5.1 wins | +2.61 |

The ⭐ by sport: hockey 2-5 (-4.1u), college 1-3, NBA / NFL 2-2. A 15-pick sample decides nothing by itself.

## 1. (a) the ⭐ as it was chosen, (c) the 11/22 choice, (d) every other choice (`s1_star.out`)

Flat 1u, one ⭐ a day. The placebo: a random play of the day's pool as the ⭐, 2,000 deals - how many do as well.

| the ⭐ chosen by | record | flat | train | held out | placebo all / train / held |
|---|---|---|---|---|---|
| **kind-first (11/4 -> 11/21)** | 207-182 | **+12.0%** | +3.8% | +25.4% | 1,382 / 1,923 / 223 |
| the rest of the board (not the ⭐) | 380-339 | +14.7% | +13.0% | +17.6% | |
| **the biggest, then the bigger edge (11/22)** | 208-181 | **+13.2%** | +6.7% | +23.9% | 1,004 / 1,520 / 396 |
| a random play of the pool expects | | +13.3% | +8.9% | +20.5% | |
| the biggest edge on its read | 204-185 | +11.8% | +6.1% | +21.0% | 1,438 / 1,659 / 897 |
| the weighed read over the no-vig price | 204-185 | +11.6% | +3.3% | +25.3% | 1,476 / 1,945 / 228 |
| the biggest own-read edge | 210-179 | +12.3% | +7.8% | +19.7% | 1,302 / 1,290 / 1,132 |
| the surest (the highest win chance) | 223-166 | +13.0% | +7.8% | +21.5% | 1,075 / 1,269 / 818 |
| the shortest price | 221-168 | +11.9% | +7.1% | +19.9% | 1,395 / 1,435 / 1,112 |
| a favorite first | 213-176 | +8.6% | +6.7% | +11.7% | 1,945 / 1,522 / 1,961 |
| the best dog score | 202-187 | +10.7% | +3.3% | +22.9% | 1,712 / 1,945 / 554 |
| the biggest, then the weighed read over the no-vig | 209-180 | +13.8% | +5.1% | +28.2% | 793 / 1,809 / 64 |
| the SMALLEST play first (the mirror) | 215-174 | +13.6% | +13.2% | +14.3% | 866 / 143 / 1,866 |
| the smallest edge (the mirror) | 222-167 | +13.4% | +10.5% | +18.1% | 959 / 545 / 1,423 |

- **(a)** Kind-first's ⭐ is not a worse bet than the rest in a way that holds: on the 137 days it had a choice it made
  +10.0% against +18.0% for the pool plays it passed over - train -9.3% vs +18.8%, held out +33.9% vs +17.1%. The halves
  flip. It is not a better bet either.
- **(c)** The 11/22 choice (the biggest, then the edge) is level with kind-first: they differ on 37 days, 19-18 +14.9%
  against 18-19 +2.0%. No gap that means anything; nothing lost by it.
- **(d)** No choice clears the bar (a placebo under 100 of 2,000 in BOTH halves). The mirrors do as well as the real
  rules. Bars that leave some days with no ⭐ (both reads over the price; the edge 3+ / 5+; the weighed read 4+ / 6+ over
  the no-vig; 1u+ / 2u+ by its own size; +150 or shorter; a Lock / Dog only) - none makes the kept ⭐s beat the dropped
  ones in both halves.
- The ⭐ is a hockey pick 313 days of 389 (+6.5%; train +0.2% / held +17.4%) - the hockey Dog is the board's biggest play
  most days. Outside hockey it is 76 picks (+36% to +47% by sport, small samples).

## 2. (b) the raise (`s1_star.out` (b), `s2_fix.out` (ii))

The board's money with the ⭐ chosen the 11/22 way:

| the raise | units a year | ROI | train | held out | worst stretch | the added units: train / held |
|---|---|---|---|---|---|---|
| none - a label | +63.0u | +16.6% | +85.7u | +105.0u | -21.0u | |
| 1u at least (11/4) | +66.6u | +16.5% | +88.1u | +113.7u | -21.8u | +2.3u on 53.5u (+4.3%) / +8.7u on 20u (+43.3%) |
| 1u at least + the 2u cell (11/17, as it ran) | +69.9u | +17.0% | +91.7u | +120.0u | -23.8u | +6.0u (+8.7%) / +15.0u (+55.4%) |
| 2u always | +75.9u | +16.6% | +94.0u | +136.1u | -27.2u | +8.2u on 169.5u (+4.9%) / +31.0u (+45.6%) |
| **the 2u cell only - WIRED** | **+67.2u** | **+17.3%** | **+90.6u** | **+113.1u** | **-22.1u** | +4.9u on 19.5u (+25.1%) / +8.1u on 8.5u (+94.9%) |

The raise cut by what it sits on (the added units; the placebo = the same units dealt to a random same-size set):

| the piece | plays | the added units | train | held out | 1 pt worse | seasons | placebo |
|---|---|---|---|---|---|---|---|
| the whole raise | 160 | +21.0u on 96.5u (+21.7%) | +8.7% | +55.4% | +19.3% | 4/4 | 248 of 2,000 |
| **a ½u play lifted to 1u** | 137 | +8.0u on 68.5u (+11.7%) | **+2.2%** (50-50) | +37.3% (27-10) | +9.4% | 2/3 | **659** |
| ... a ½u favorite value play | 83 | +5.0u | **-0.2%** | +36.5% | | 2/3 | 692 |
| ... a ½u hockey favorite value play | 68 | +1.2u | **-8.8%** | +31.7% | | 2/3 | 1,253 |
| ... a ½u dog (floor / NBA floor / long Dog) | 54 | +3.0u | +5.2% | +39.7% (5-4) | | 2/3 | 847 |
| **a play raised to 2u (the 11/17 cell)** | 23 | +13.0u on 28u (+46.3%) | +25.1% (10-6) | +94.9% (7-0) | +43.4% | 4/4 | 161 (kind-first: 29 plays, 63) |

- The raise as a whole makes money in both halves - because the board does. It is not a better bet: a random set of
  plays does as well one time in eight.
- **The ½u -> 1u lift** is the weak piece: flat in the first half every way it is cut, its biggest group (the hockey
  favorite value play) down in the first half - the same group the 11/17 plan left at ½u for the same reason. The ½u ⭐
  on a day with nothing bigger: 56-43, +11.4% flat, **train 35-37 -1.9%**, held 21-6. Live 1-4. It fails the 11/17
  plan's own rule (no bigger number on a group that is flat-to-losing in a half). **Off.**
- **The 2u cell** holds in both halves and every season on a small sample (23 plays the 11/22 way, 29 kind-first). It
  was wired six days ago on the owner's max-profit OK; nothing here speaks against it. **Kept.** (Its ½u Lock / Dog to
  2u part is 10 plays, 7-3 - the Monday review watches it.)

## 3. The tie-break and "never the smaller bet" (`s2_fix.out` (i), (iii))

**The tie-break** only matters on the 60 days the pool's biggest size is shared (every tied play: +17.9% flat):

| between plays the same size | record | flat | train | held out |
|---|---|---|---|---|
| **the bigger edge on its read (11/22 - kept)** | 31-29 | +17.8% | +22.7% | +12.1% |
| the weighed read over the no-vig price | 32-28 | +21.9% | +10.9% | +34.6% |
| the bigger own-read edge | 29-31 | +4.0% | +11.4% | -4.5% |
| the surest | 32-28 | +2.0% | -13.9% | +20.3% |
| the shortest price | 32-28 | +2.3% | -19.4% | +27.2% |
| the longest price (the mirror) | 33-27 | +28.1% | +27.4% | +28.9% |

None beats a random tied play (the best placebo 288 of 2,000). The edge is up in both halves and all four seasons; the
surest / the shortest price are the two that lose a half. It stays.

**The ⭐ smaller than another play.** Kind-first with the raise: 20 of 389 ⭐ days - those ⭐s 8-12, **-12.8%, both
halves down**, the bigger play beside them 13-7 +53%. The 11/22 rule cut that to 8 days. With the lift off, a ½u ⭐ would
sit beside a bigger play on about 40 days (38 under the wired plan) - each time because the biggest play is outside the ⭐'s pool (the own read fights
it: 21; its read is under its price: 20). The owner's rule is never, so on those days there is no ⭐ (the dropped ⭐s:
21-17 +12.5% flat, at ½u - about a unit and a half of label a year, no units moved).

## 4. What the ⭐ looks like from 11/24 (`s2_fix.out` (v))

| the day | share of ⭐ days | the ⭐ | replay record (flat) |
|---|---|---|---|
| a 💎 hockey max play | 1 in 12 | the max play, 3u | 17-14 +19.7% (train -6.8% / held +48.0%) |
| a 2u play on the board (a short hockey / football Dog, the short hockey runner-up) | half | that play, 2u - two of them: the bigger edge | 95-99 +8.7% (+10.3% / +6.6%) |
| the biggest is a Lock / a thin Dog / a 1u play at +150 or shorter | 1 in 17 | raised to 2u | 17-6 +43.4% (+23.1% / +90.0%) |
| the biggest is a 1u dog past +150 | rare | that play, 1u | 2-2 |
| every play is ½u (a thin day) | 1 in 4 | the best ½u play - **still ½u**, the note says a thin day | 56-43 +11.4% (**-1.9%** / +46.7%) |
| the biggest play can't carry the ⭐ | 1 in 10 | **no ⭐** | |

The ⭐ at the units it carries: 187-164, +80.1u on 580.5u, **+13.8%** (train +7.8% / held +22.1%), 4 of 4 seasons, a
point worse than the close +11.4%.

## The owner's options (not wired)

- **The full-unit lift back** (`sports.BEST_HONEST_FROM = None`): +2.7u a year in the replay (+1.1u of it in the first
  half, +6.9u in the later half), live 1-4. It is his 11/4 ask ("always sized at least one full unit"); the numbers say
  the plays it doubles are the engine's thin ones.
- **The ⭐ a pure label, no 2u either**: -4.2u a year; the 2u cell is 23 plays.

## Dead ends (do not re-run)

A ⭐ chosen by the most confident read, the own read, both reads over the price, the surest side, the price, the kind,
or behind a bar (an edge of 3+ / 5+, a 1u+ / 2u+ play, a Lock / Dog only): none finds a better bet than a random play of
the day. A tie-break by anything but the edge. A 2u ⭐ on every play (11/17: the worst stretch x1.3-1.4 for units that
are flat in the first half).

## Files

`blib.py` the rig · `s0_live.py` the live record · `s1_star.py` the choices and the raise · `s2_fix.py` the tie-break,
the raise by piece, the never-smaller rule, the plans · `*.out` their output.
