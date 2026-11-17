# 11/17 - THE UNDERDOG EDGE: "make the engine better on these picks, especially our edge on our underdog"

The owner, 11/16: *"run Fable, do a full sweep, and make the engine better on sizing, and study, and make the engine
better on these picks, especially our edge that we do on our underdog, since that's the way we profit, I suppose, on
plus money."* This is the plus-money half (a sister study did favorites / the Lock / totals / bugs).

**Short answer. The dog money is real and it is where he thinks it is: on today's code every dog the board posts runs
+13.6% a bet over three replay seasons (394-423, both halves up). Two things earned a change and are wired from the
11/17 games: (1) the college hoops dog slot takes a TRUE ROAD dog at a dog read of 3, half a unit; (2) the college
football Dog of the Day past +150 is 1u, not ½u. Nothing else cleared the bar - no dead weight is provable enough to
pull, no new weight, no other size, and no honest version of the 🔍 college football play earns its way back.**

## The rigs and the bar

- **Live** (`s1_ledger.py`): every graded plus-money moneyline unit play since 10/25, `picks.json` + `early.json`.
- **R3 - NEW** (`funnel6.py`, `run_funnel6.sh`, `dlib.py`): the board re-built on TODAY's code, every 2026 date gate open,
  every board day 2023-10 -> 2026-11 at the closing price (the model re-tuned each July, no injury reports), every
  moneyline side written with its dog score AND what each fact on the side is worth in that score (the score with the
  fact taken off). 50,120 rows in `~/.cache/d503_dogs1117`. Train = to 6/30/2025, held out = after, live apart.
- **The football board** (football_1114 rows): every football board day 2018-26 on the 11/14 code - seven seasons with
  a college board. **The college hoops rows** (maxcol_1116): the board at ESPN's close 2018-26, train 2018-22 / held
  2023-26, the slot built as live. **The raw rig** (max_pro_1116): every NHL / NBA side at the close 2018-26, nothing fit.
- **THE BAR** (the standing rule): wins more vs the price in BOTH halves, up in most seasons, a random same-size set
  matches it under 5% of the time (100 of 2,000), the worst stretch does not blow out, holds a point worse than the
  close. All five = wired, as a weight / a size. Some = a LEAD (a tracker line), never wired.
- **Said once, plainly:** the dog score's weights were fit with these seasons seen. A cell picked BY the score is not a
  clean out-of-sample test anywhere on these rigs; only the model's own params are blind.

## 1. The live dog ledger, 10/25 -> 11/16 (`s1_ledger.out`)

**66 dog unit plays: 23-43, -2.9u on 53.5u.** The board's dogs 19-29, **+2.3u on 41u**; the early dogs 4-14, -5.2u.

| by sport | record | units | | by price | record | units |
|---|---|---|---|---|---|---|
| **hockey** | **12-6** | **+11.5u on 18u** | | +100..+150 | 17-24 | +3.0u on 35.5u |
| NFL | 2-4 | +0.2u | | +151..+250 | 6-15 | -2.9u on 15u |
| college hoops | 1-1 | -0.4u | | +251..+350 | 0-4 | -3.0u |
| NBA | 4-12 | -3.3u on 10.5u | | **by size** | | |
| **college football** | **4-20** | **-11.0u on 18.5u** | | ½u | 12-26 | -5.5u |
| | | | | 1u | 6-15 | -5.5u |
| | | | | 2u | 5-1 | +9.6u |

| by path | record | units | what happened to it |
|---|---|---|---|
| Dog of the Day | 6-4 | +8.5u | hockey 5-2 +9.1u |
| the floor | 8-6 | +2.0u | hockey 7-4 |
| 🔍 college football play | 1-7 | **-5.1u** | paused 11/13 |
| runner-up dog | 1-5 | -1.6u | NBA / college cut 11/13 (hockey / NFL only) |
| NBA floor | 1-4 | -1.2u | its judge is at 20 graded |
| early: hammered | 0-4 | -2.0u | all college; judge at 20 |
| early: blowout | 1-4 | -1.5u | paused 11/11 |
| early: NBA opening line | 1-3 | -1.4u | "one voice" has let none post since 11/11 |
| early: bye | 2-2 | +1.2u | ½u from 11/17 |
| early: exam scan | 0-1 | -1.5u | ½u flat from 11/16 |

**The leaks, named:** college football dogs are the whole hole (-11.0u; without them the dogs are +8.1u) - and 15 of
those 24 plays were kinds that are already paused or cut (the 🔍 play, the blowout spot, the college runner-up). The
other soft spot is the NBA (4-12): the NBA floor and the opening-line play, both small, both with a judge. A dog whose
RAW own read sat 3c+ over the price went 4-15 live; thin-edge and own-read-under dogs went 15-14 and made money - the
replay says the same thing (a bigger own-read margin is not a better bet).

## 2. Where the dog edge lives - R3, today's code (`s2_edge.out`)

**Every dog the board posts: 394-423, +13.6% flat (train +10.8% / held +18.9%), +92.7u on 747u at today's sizes, the
worst stretch -17.1u, 4 of 4 seasons.** Every dog there is, unposted: hockey -3.9%, NBA -3.8%, NFL -8.3%. The engine's
picking is the edge, not the price.

| path (R3) | record | flat | train / held | note |
|---|---|---|---|---|
| hockey Dog of the Day | 113-127 | +7.6% | +3.7% / +14.1% | weaker on today's code than on the older boards (+11% / +18%) |
| hockey runner-up dog | 42-29 | **+34.1%** | +33.1% / +35.6% | 4 of 4 seasons - the best dog kind on the board |
| NBA floor | 81-84 | +19.0% | +25.6% / **+3.4%** | fading; live 4-11 |
| college hoops dog slot | 56-49 | +28.5% | +31.8% / +18.5% | 3 of 3 |
| hockey floor | 32-47 | **-5.5%** | -14.7% / +14.5% | 1 of 4 seasons - a WATCH |
| NFL floor (road) | 23-39 | -1.1% | -18.1% / +27.7% | flips |
| college football Dog | 10-6 | +47.9% | (two seasons) | |
| NBA Dog | 10-8 | +31.3% | +10.6% / +85.0% | 18 plays |

- **Price**: posted +100..+150 +12.4% (both halves), +151..+250 +15.5% (+8.7% / +31.7%, 4 of 4), +251..+350 15 plays.
  On today's code the long dog is NOT the loser the 10/30 rows made it.
- **Home / road**: posted home +16.2%, road +13.3% - no cut. (The NFL home floor dog is already out.)
- **The own read**: among gated hockey dogs the own-read term sorts nothing (0-1 points over the market +14.5%, 2-3
  +19%, 3-5 +14%). The STUDY part does the work - 285 of 342 gated hockey dogs sit at the study cap of 6.
- **The line**: a hockey dog the money LEFT (2+ points, -4 on the score) -8.9% (both halves the right way); the money
  came TO it +4.4%. The weight earns its sign. (At the close the move is already in the price - the 11/2 morning-price
  study is the cleaner test and said the same.)

## 3. The dog score's parts - which weights still earn (`s3_parts.out`)

New on this rig: every weight's own record. For each fact, the dogs it adds points to should beat the sport's other
dogs, the dogs it takes points from should lose more, in both halves.

**Earn their sign in both halves AND beat the placebo** - hockey carries the score: out-shooting the favorite +3
(+7.9% on 896, placebo 0) and being out-shot -3 (-11.3% on 1,673, placebo 1), both off a loss +3.5 (+6.2% on 862),
the save-% edge +1 (placebo 1), the favorite off an OT loss +2 (+12.5% on 261), tired vs rested -3 (-18.4% on 491),
out-shot 40+ last game -2 (-23.2% on 188), the unlucky record +2 (+40.1% on 60), out-hitting +2, the PDO +2. NBA: the
moneyline longer than its spread +2 (+14.9% on 418, placebo 4), the favorite off a comeback win +2 (+38.1% on 77), the
12+ game slate +2 (+5.9% on 447), the market-fade -2 (-12.3% on 676), a fired coach -3. College football: the
interception-unlucky dog +2 (+17.4% on 179), the big-cover fade -2.

**The wrong way in both halves (candidates for dead - LEADS, nothing pulled):**

| weight | the dogs it touches | vs the sport's dogs (train / held) | why not pulled |
|---|---|---|---|
| college football "conservative 4th downs" dog **-2** | 125, **+26.2%** | +24.6 / +26.8 pts the WRONG way | three seasons, 125 dogs; the cleanest dead-weight lead on file |
| NFL "goes for it on 4th more than the other coach" **+1** | 164, -9.8% | -2.5 / -5.3 | a 1-point weight; noise-sized |
| hockey "lost the last game of the series" +3 | 97, -11.2% | -7.9 / -5.3 | playoffs only |
| college hoops turnover-matchup -2 | 59, +3.1% | +13.7 / +3.9 | 59 rows; its own study had 1,802 |

**Flip by half (no verdict):** most of the 10/21 NBA dog weights (the last margin, the rest, the record, the win
streak, the total vs the league - each right in one half, wrong in the other), the NBA rested-vs-b2b +3 (-1.0% on
272: the NBA's b2b spot is priced, the 11/16 finding again), the NFL East-out-West +3 (-4.6% on 55), the NFL / college
"off a 17+ win" +2 (-11.8% / -3.3%), the college bye +2 (+50.8% / -38.5%), the .700 college team +1.5.
**Honest limit:** three seasons, weights fit with them seen. "Earns" here means "has not died"; a flip is not a
verdict. The tracker already carries a line for the big ones; the two real candidates above are written down for the
next look. Nothing is switched off on three seasons of a replay.

**A new weight tried and DEAD** (`s9_slate.out`): the day's 2nd / 3rd gated hockey dog beat the 1st on R3, so the
obvious idea was a hockey big-slate weight like the NBA's. On the raw rig (8,364 hockey dogs at the close 2018-26,
nothing fit): 8+ games -5.6%, 10+ -4.9%, 12+ -5.0% against -5.6% for every dog. Nothing. (The NBA's 12+ slate holds
there: +5.8%, 8 of 9 seasons.)

## 4. Are we leaving good dogs on the table? (`s4_held.out`, `s8_rank.out`)

A dog the engine LIKED = its score at / over its sport's Dog gate. What held the ones that never posted, and how they did:

| | liked | posted | never posted | held by | how the held ones did |
|---|---|---|---|---|---|
| **hockey** (gate 6) | 328, +15.5% | 298, +13.1% | **30** | 25 passed everything (one Dog + one runner-up a day), 5 fought | 18-12, +39.4% (train +64% / held +11%) - 30 dogs in 3 seasons |
| **NBA** (gate 4) | 55, +20.2% | 37 | 18 | 15 passed everything | 4-11, -21.7% - the cap is doing its job |
| **NFL** (gate 8) | 5 | 3 | 2 | no named reason | 0-2 |
| **college football** (gate 4), R3 | 103, +14.5% | 19 | 84 | the own-read rule 23, the 11/14 weighed check 24, passed everything 26 | the weighed check's 24: 9-15 **-10.9%** (it works); passed everything 11-15 +13.2% |
| college football, 2018-26 board | 168 gated, +24.9% | 74 (the Dog) | **92** | one Dog a day | 37-55, +10.5% (+19.4% / **+3.0%**, 4 of 7 seasons) - no |
| **college hoops** (read 4+) | 418 | 374 | 44 | the two-a-night cap | 18-25, +9.9% (the #3 read of a night -5.9%) - the cap is right |

- **Hockey leaves almost nothing**: 9 of 10 liked hockey dogs post. The gates are not keeping winners out.
- **Just under the hockey gate (a score of 4-6, clean, not posted)**: 83 dogs, +36% in both halves on R3. This is the
  11/15 "next hockey dog" again - and on the three seasons no weight ever saw (2020-23, the paid morning prices) the
  same dog ran -7.2% on 140. It stays the lead it was. Not wired.
- **The NFL - the one real LEAD**: the gate of 8 posts almost nothing (27 Dogs in nine seasons, +2.1%), while an NFL
  **ROAD dog at a score of 4+ whose studies beat the price** went 88-101, **+28.3% on 189** (2018-21 +38.2% / 2022-26
  +19.6%, 7 of 9 seasons, placebo 0 of 2,000); the 130 of them that never posted +30.1% in both halves. Why it is NOT
  wired: the score's NFL weights were fit on those seasons (the cell is the fit talking), the same angles hand-counted
  on nflverse's 2006-26 closes are +11.0% at z 1.45, R3's NFL floor road dogs are -2.4% on 58, and live they are 0-2.
  Tracked from 11/17 (`sports_leads.NFL_ROAD_DOG_LEAD_TAG`, judge at 40: +10% or better = lower the NFL gate).
- **Which gated dog should be the Dog?** On days with 2+ gated hockey dogs the top score went 28-37 and the rest 53-35
  - but by half it is -33.8% / +40.9% for the top one. Picking by the study part, the smallest own-read term, the
  shortest price: every rule flips by half. No ranking change earned.

## 5. Dog sizing (`s7_sizing.out`)

| question | R3 says | verdict |
|---|---|---|
| the hockey Dog's 2u short / ½u long split | short +7.5%, long +7.8% - no separation on today's code; 2u/½u +31.0u on 410u (worst -23.2u), 2u/1u +32.8u on 433u | stays: the older boards had the short one better, R3 has them level - no both-boards case either way |
| the 💎 hockey max play (b2b spot, 8+) | 17-14, +19.7% (train -6.8% / held +48.0%); a random 31 Dogs as good 569 of 2,000 | R3 adds NO support. Its case is the 2020-23 rig (34-24). The judge at 25 graded stands - said plainly |
| **the hockey runner-up dog -> 1u** | 42-29, +34.1%, both halves, 4 of 4 seasons; at 1u +24.2u (worst -4.0u) vs +12.1u | **the nearest miss**: against the other gated hockey dogs a random 71 is as good 122 of 2,000 (6%), and the two older boards had it flat (+2.9u / +6.8u). A LEAD - the owner's option |
| the NBA ½u dogs (the NBA floor) | +19.0% on 165 but held +3.4%; live 4-11 | no size up; the judge at 20 |
| the hockey floor | -5.5% on 79 (1 of 4 seasons) | no size up; a WATCH |
| every ½u dog at 1u | +92.7u on 747u (worst -17.1u) -> +136.2u on 1,035u (worst **-30.4u**) | yesterday's answer again: more money by betting more, a hole 78% deeper |
| **the college football Dog past +150** | the 2018-26 football board, below | **WIRED: 1u** |

### WIRED (2) - the college football Dog of the Day at +151..+350 is 1u (was ½u)

The 10/30 price split (2u short / ½u long) was set on a board that was nearly all hockey - 12 college Dogs past +150
on it. On the football board (74 college Dogs, 2018-26):

| | record | won / needs | flat | 2018-21 | 2022-26 | seasons | a point worse |
|---|---|---|---|---|---|---|---|
| short +100..+150 (2u) | 22-17 | 56.4% / 44.8% | +24.9% | +12.8% | +37.7% | 6 of 7 | +22.2% |
| **long +151..+350 (½u -> 1u)** | **18-17** | **51.4% / 32.0%** | **+64.3%** | **+65.7%** | **+62.8%** | **6 of 7** | **+59.1%** |
| every gated college dog past +150 | 41-50 | 45.1% / 31.9% | +40.8% | +43.2% | +38.5% | 6 of 7 | +36.5% |

The five checks: (1) both halves - yes; (2) most seasons - 6 of 7; (3) placebo - a random 35 college dogs at that price
did as well **16 of 2,000**; (4) worst stretch -5.6u -> **-6.0u**; (5) a point worse +59.1%. **Why 1u and not 2u:**
against its OWN kind (a random 35 of the 74 college Dogs) it is as good 230 of 2,000 - it is not provably better than
the short Dog, only provably not the loser the ½u treats it as. 1u is the size the 2022-26 half proves at its 5% end
(a quarter of Kelly: 0.8u). The college Dog's money: **+30.7u on 95.5u -> +41.9u on 113u.** About 5 a season.
The NFL long Dog (4-12, -29.3%) and the hockey long Dog stay ½u.

## 6. College hoops (`s5_cbb.out`, `s5b_cbb_r3.out`)

The slot as live: 374 plays, 190-184, +19.8%, 8 of 8 seasons, +125.8u on 527u. Where it lives: +100..+150 +20.5%, home
+30.2%, road +19.2%; **a neutral-site dog at +151..+250 5-21** (26 plays - a watch); March -3.9%. The cap is right (the
#3 read of a night -5.9%). The early gate is right (a team under 2 games: 32-59).

### WIRED (1) - the dog slot takes a TRUE ROAD dog at a dog read of 3, half a unit

The 11/14 study found the read runs HIGH on a home floor (the home dog reads 1 less since). This is the other side of
the same finding: every dog with a read that clears its price, both teams 4+ games -

| the read | road | home | neutral |
|---|---|---|---|
| 2 | -2.2% (train -10.3%) | +21.2% (held -36%) | +8.3% |
| **3** | **85-82, +21.1%** (train +17.9% / held +24.9%, 6 of 8) | 62-73, **-0.6%** | 13-20, +4.8% (train -13.3%) |
| 4 | +15.6% | +0.5% | -0.3% |
| 5+ | +27.2% | up (57 dogs) | up (32 dogs) |

On the road the read is honest a point sooner. In the slot (two a night, the read-4+ dogs first):

- **122 added plays, 63-59, 51.6% against 42.1% needed, +23.0%** - train +19.5% / held +27.4%, 6 of 8 seasons.
- Placebo: a random 122 road dogs did as well **8 of 2,000**. A point worse than the close: +20.1%.
- The slot: +125.8u on 527u -> **+139.8u on 588u** at ½u; the worst stretch -9.4u -> -10.5u. About 15 a season.
- The second build (R3, the engine's own flags, 2023-26): 39-36, +25.3% with no fade on it; only 2 of 77 carried a fade.
- **Why ½u**: the added plays are no better than the slot's others (a random set of slot plays is as good 738 of
  2,000), the read's weights were fit with these seasons seen, and the held half proves 0.4u at its 5% end.
- **Honest**: 2018 was 3-5 (8 plays) and 2024 +13% only; the non-conference ones are 6-8 (14 plays in the slot - the
  calendar was checked, no month rule is earned); this is the 11/15 lead ("read 3-4") re-cut by venue after the
  11/16 open slot changed what the added plays are - one cell out of an 18-cell grid, the dose on the road is clean
  (3: +21%, 4: +16%, 5+: +27%; 2: -2%). The judge: `sports_leads.ROAD_DOG_READ_3_TAG`, 40 graded, under -5% = back to 4.

Not earned in college hoops: a gate of 3 at home / neutral; the third dog a night; the 🔍 gap play is fine as it is
(72-63, +20.1%; 113 of its 135 are slot dogs anyway).

## 7. The 🔍 college football gap play (paused 11/13) - no honest version earns it back (`s6_gap_ncaaf.out`)

3,528 college dogs 2018-26 with the raw read and the market:

- The road rule as it last ran (15-35 points, road): **66-140, -7.5%** (both halves down, 3 of 9 seasons). Dead.
- The home dog at 15+: +12.6% on 443 in both halves - but split it: the ones the **Dog gate already takes** 45-45,
  **+42.1%**; the ones it does NOT take 132-223, **+5.1%** (a random set is as good 636 of 2,000). The gap adds nothing
  the Dog of the Day does not already have; the 11/11 paid-odds table and the live record (home 3-9) say the home
  version loses. No version holds on two sources.
- "The gap AND the studies beat the price", "the gap AND a study part of 4+": the same dogs with NO gap do as well
  (+16.5% vs +14.5%). It is the studies, never the gap.

**Stays paused.** The college dog money is the Dog of the Day (40-34, +43.5% over seven seasons) - now 1u past +150.

## 8. The early dog spots and the exam scan - not re-run

Studied 11/11 and 11/15 on the paid odds history (`early_1111/`, `sizing_1115/e2-e4`); nothing new to add. What those
say, next to the live 4-14: the NFL bye is an ordinary dog on 21 seasons (½u from today); NFL hammered +11.2% on 147
(z 1.4); **college hammered -0.2% on 354, the halves flip** - live 0-4, a WATCH with its judge at 20; East-out-West
+35% then -11%; the exam band +10.3% on 213 with the halves flipping (½u flat since 11/16). None of them passes the
bar; they are the owner's tests with quit rules, sized ½u.

## 9. Straight answers

1. **Is the dog edge real?** Yes. +13.6% a bet on today's code, both halves, and hockey is most of it - live too
   (12-6, +11.5u).
2. **Where did the live dog money go?** College football: 4-20, -11.0u, 15 of those plays from kinds already off.
3. **What changed today?** Two things, both small and both earned: a road college hoops dog at a read of 3 posts at
   ½u (~15 a season, about +1.8u a season on the replay), and a college football Dog past +150 is 1u (~5 a season,
   about +1.4u a season).
4. **Are good dogs being held back?** In hockey and college hoops, no - nine in ten liked dogs post and the caps hold.
   In the NFL, maybe: the road dog under the gate is the one lead worth a tracker line.
5. **For the owner to decide (not earned, not wired):** the hockey runner-up dog at 1u (+34% on 71, one board, 6% on
   the placebo); the college football "conservative coach" -2 weight looks backwards.
6. **Watches:** the hockey floor on today's code (-5.5% on 79), the NBA floor (held +3.4%, live 4-11), college
   hammered (0-4), the neutral-site slot dog at +151..+250 (5-21).

## Files

`funnel6.py` + `run_funnel6.sh` (R3), `dlib.py`, `s1_ledger`, `s2_edge`, `s3_parts`, `s4_held`, `s5_cbb`,
`s5b_cbb_r3`, `s6_gap_ncaaf`, `s7_sizing`, `s8_rank`, `s9_slate` (.py + .out). Wired: `sports.DOGS_1117_FROM`
("2026-11-17"; None = both off), `NCAAB_ROAD_DOG_GATE_1117` 3 / `NCAAB_ROAD_DOG_UNITS_1117` 0.5 (`ncaab_road_dog`,
`ncaab_road3`, `ncaab_dog_read_gate`; stamped `ncaab_play.road3`), `NCAAF_DOG_LONG_UNITS_1117` 1.0
(`ncaaf_dog_long_1u`, `mark_dogs_1117`; stamped `long_1u`). A posted pick keeps its units. Tests: `test_dogs_1117_*` (two).
