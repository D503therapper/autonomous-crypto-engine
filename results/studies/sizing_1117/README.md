# 11/17 - SIZING: "the half a units is just retarded ... I feel like we could do better with the sizing"

The owner, 11/16: *"We also need to run Fable and figure out how we can make more money. The half a units is just
retarded. Like, that basketball today pick was a lock. We should have had fucking 3 units on that shit. But I understand
the whole half a unit thing, because a lot of the times when the engine has a thin edge and says half a unit, it loses
... I feel like we could do better with the sizing."* and *"the engine should have had 2 units on the chargers all day."*

**Short answer: ONE size earned it and is wired - the college hoops dog slot is 2u at a dog read of 5+ (was 6+), from
the 11/17 games. Nothing else clears the bar: 30 size-up cells on the two replay boards, the slot's read-4 band at 2u,
3u at a read of 6+, the ⭐ at 2u, and the Chargers' shape all fail it. The ½u plays are NOT the leak - in the replay and
live they make money; the thin-edge ones are the best of them.**

## The rigs and the bar

- **The boards** (`s1_board.py`): the two replay boards of the 11/14 / 11/15 sizing studies (`sizing_1114/lib.py` - R1 =
  the 10/30 funnel rows, 1,991 unit plays; R2 = the 11/12 deep-program rows on today's code, 1,664; 2023-10 -> 2026-11,
  closing prices; train = to 6/30/2025, held out = after; live apart), today's sizes + the ⭐ raise.
- **The college hoops dog slot** (`s2_cbb_slot.py`, `s2b_read5.py`): the 11/16 max-play hunt's cached college hoops
  rows (the board re-built at ESPN's close every college hoops day 2018-26; train = seasons 2018-22, held out =
  2023-26), the slot as it runs today - the 11/16 open slot (a trap / a fought side posts) and the 11/14 home-dog -1.
- **Live** (`s3_live.py`): `data/sports/picks.json` + `early.json` since 10/25 - the sanity check, never the judge.
- **The Chargers** (`s4_chargers.py`, `look_chargers.py`): the 11/16 row + nflverse's closes 2006-26 + the 11/14
  football replay board's NFL rows 2018-26.
- **THE BAR**: a bigger size only where the bigger-size cell wins MORE vs the price than the rest of its kind in BOTH
  halves, a random same-size set of its kind does as well under 5% of the time (100 of 2,000), and the worst stretch
  does not blow out. Never Kelly on the raw read; the -150 rule stands; 5u is the cap.
- Not re-run (done 11/15-11/16, nothing new to add): the exam scan (½u flat since 11/16), the bye spot (½u from 11/17),
  the spread stack (its judge at 100 graded comes first; yesterday's three 1u candidates stand as candidates), the
  hockey b2b Dog 3u and the college hoops Lock-test favorite 2u (wired 11/16).

## 1. The two picks he named

**UMBC +120 (Monday 11/16, won 75-67) was not the dog slot and not a lock by any read the engine has.** `look_1116.py`:
its dog read was 3.0 (weights 2 + knowledge 2 - 1 for the 11/14 home-dog rule; the slot's gate is 4), its own read
44.9% against the 45.5% the price needs, the efficiency read 46.3%. It went up as the day's **floor fallback** - the one
½u play on a board that had no unit play ("college hoops sits out the floor ... but the board has no unit play"). Every
college hoops dog in that shape on the rows (`s2b_read5.out`): a home dog at a read of 3, +100..+150: **59-67, -0.1%**
(train +0.1% / held -1.1%, 4 of 8 seasons). A coin at its price. 3u on that kind is 3u on a coin; ½u was the right size
and it happened to win.

**The Chargers +185 at the Ravens (won 23-20; the board leaned Ravens -4.5, no units).** The 11/16 board re-run offline
(`plays_every_day_1104/dryrun.py --all-leagues`): Chargers - the blend 31.9%, the OWN read 34.2% against 35.1% needed
(under the price), the raw ratings read 37.4% against a no-vig 33.6%, **dog score +1.53 against the NFL Dog gate of 8**,
no named reason; 0-8, lost 8 straight, last game a 44-22 loss; the price went Ravens -118 -> -225 in the week (the
money left the Chargers - a studied fade). What held it off: the Dog gate (1.5 of 8), the own-read rule, no named
reason - three real rules, each doing its job. No bad input on the Chargers' row: the record, the streak, the last
score, the injuries (McConkey out) and the Ravens' QB (Lamar Jackson on injured reserve - on the card, weighed) are all
what the files say. The one soft spot was on the OTHER side: the Ravens -4.5 lean was a 50.4% cover read against 52.8%
needed with a backup QB the engine could not name - a coin flip lean, no units (leans are coming off the board).
**Is an NFL road dog in that shape a cell that should carry units? No** (`s4_chargers.out`):

| the cell (NFL road dog) | record | flat | train / held | placebo |
|---|---|---|---|---|
| +151..+250, every one (nflverse 2006-26) | 415-738 | +4.2% | +7.9% / -0.5% | 330 |
| ... on Monday night | 28-54 | -2.7% | -3.2% / -2.1% | 1,342 |
| ... on a 5+ game losing streak | 20-39 | +1.2% | -10.9% / +14.6% | 1,112 |
| ... winless at 0-5 or worse (any +100..+350) | 7-20 | -22.6% | -44.2% / +8.8% | 1,625 |
| ... the favorite on a backup QB | 44-59 | +21.8% | +42.7% / **-1.3%** | 167 |
| ... the favorite a backup QB, the dog its regular QB | 34-34 | +42.2% | +74.8% / **-1.6%** | 18 |
| ... 3+ losing streak AND the favorite on a backup | 13-21 | +13.2% | +18.4% / +9.2% (34 bets) | 656 |
| the engine's rows 2018-26: score 0-4, own read under, raw read 3+ over | 25-45 | +3.6% | +10.2% / -0.9% | 849 |
| the same, any road price | 56-96 | +0.7% | -11.7% / +7.7% | 865 |
| the spread: road dog +3..+6.5, the favorite under .500 on a backup QB | 51-28 | +23.2% ATS | +33.2% / +11.4% (3 of 9 held seasons) | 42 |

The one thing in the Chargers' shape that ever paid is "the favorite is on a backup QB" - and it paid 2006-16 only
(+43% / +75%), flat since 2017 (-1%): the books price a backup now. The spread version (a road dog getting 3 to 6.5
against a sub-.500 favorite on a backup QB) is up in both halves but only 3 of 9 held-out seasons - a WATCH, not a play,
not a size. The engine's own "under the gate" NFL road dogs run -1.3% on 1,118. Nothing to wire; the win was the one
time in three a fair +185 dog wins.

## 2. Are the ½u plays the problem? No - and the thin-edge ones are the best of them (`s1_board.out` (1), `s3_live.out`)

Every ½u play on the boards, by the OWN read's edge over the price (flat 1u ROI; share of the ½u plays' lost units):

| | R1 (the 10/30 rows) | R2 (today's code) | live since 10/25 |
|---|---|---|---|
| own read UNDER the price (dog-score plays: the floor, NBA floor, runner-up dog) | 423-481 **+7.9%** (+7.6% / +8.2%), 63% of the lost units | 617-699 **+8.5%** (+6.9% / +10.6%), 97% | 16-11 +3.0u |
| own read 0-3c over (THIN) | 207-185 **+13.5%** (+14.8% / +11.2%), 24% | 20-13 +18.6%, 2% | 3-1 +0.6u |
| own read 3c+ over (a "real" edge) | 131-101 +2.5% (+9.9% / **-5.8%**), 13% | 7-6 (13 plays) | 0-5 -2.5u |

- The ½u plays make money as a group in both halves on both boards (+8% to +13% a unit). Where they "lose a lot" is
  only that there are a lot of them at plus money: they win 47-53% of the time.
- The thin-edge ½u plays are the BEST ½u cell, not the worst (the 10/29 funnel said the same of the floor's thin dogs).
  The cell that does NOT hold is the opposite one - a ½u play whose raw own read is 3c+ over the price (held out -5.8%,
  live 0-5): a bigger own-read margin is not a better bet (the 11/12 calibration program's finding, a fourth time).
- By kind at today's size (R1 / R2): the floor +50.8u on 562u / +29.5u on 536u; the NBA floor +17.1u / +15.5u; the
  runner-up dog +2.9u / +6.8u; value plays -0.1u on 190u / +3.3u on 16u; the long Dog -5.0u / +3.9u.
- **Live since 10/25 by the size posted: ½u 19-17, +1.1u on 18u (+6.0%); 1u 6-15, -7.1u on 21u (the 🔍 gap play 1-7);
  2u 5-1, +9.6u on 12u.** The ½u plays are up live; the 1u plays are what lost. ½u hockey 15-5 +4.8u, ½u NBA 1-7 -2.7u.
  Early plays 10-17 -4.4u on 17.5u (½u 8-12, 1u 2-4).

## 3. What "no more half units" would do (`s1_board.out`, the same plays)

| the board | R1: units (ROI), worst stretch | R2: units (ROI), worst stretch |
|---|---|---|
| **TODAY** | **+194.0u on 1,643u (+11.8%), -16.9u**, 4 of 4 seasons | **+129.2u on 1,178u (+11.0%), -25.1u**, 4 of 4 |
| every ½u play at 1u | +244.0u on 2,242u (+10.9%), -20.9u | +184.2u on 1,815u (+10.1%), **-44.2u** |
| every ½u play OFF | +144.1u on 1,044u (+13.8%), -18.0u | +74.2u on 542u (+13.7%), -20.7u |
| every play one step up (½->1, 1->2, 2->3) | +338.3u on 3,001u (+11.3%), -29.0u | +237.8u on 2,162u (+11.0%), -47.2u |
| the ⭐ at 2u (today 1u at least) | +222.9u on 2,043u (+10.9%), -23.4u | +142.3u on 1,270u (+11.2%), -25.1u |
| the ⭐ at 3u | +303.5u on 2,676u (+11.3%), -35.0u | +177.9u on 1,554u (+11.5%), -29.9u |
| live since 10/25: as posted +3.5u (worst -7.1u) | every ½u at 1u +4.6u (-8.1u) | every ½u at 2u -0.4u (-20.4u) |

Every ½u play at 1u makes +50u / +55u more over three replay years - on 600+ more units risked, at +8.3% / +8.6% a
unit, LESS than the board earns now, with the worst stretch 24% / 76% deeper. That is more money by betting more, not a
better bet - and the 11/15 study's seasons nothing saw (2020-23) put the biggest ½u kind, the floor's hockey dogs, at
-7.0% on 610 and the NBA floor at a third of its replay rate. **It is the owner's option, not something the plays
earned.** If he wants it anyway, the honest version is "the floor and the NBA floor at 1u": about +12u a replay year
for a worst stretch up to three quarters deeper, and about break-even on the seasons nothing saw.

**The ⭐ / "both reads over the price"**: the ⭐ pick is +12.7% / +12.6% flat but a random eligible play a day does as
well 556 / 1,227 times in 2,000 (the 11/14 answer again); the ⭐ with the OWN read over the price too is no better than
without (+9.4% vs +23.5% on R1, +11.6% vs +13.0% on R2). The ⭐ at 2u adds +29u / +13u on +400u / +92u more risk (+7% /
+14% a unit) and R1's worst stretch goes -16.9u -> -23.4u. Not earned.

## 4. The 30 size-up cells on the boards (`s1_board.out` (2)) - none clears

Named before looking; "the cell vs the rest of its kind". A cell must win more than its siblings in both halves on BOTH
boards with a placebo under 100 of 2,000. **0 of 30 clear both boards; 0 clear even one.** The verdict table is at the
bottom of `s1_board.out`. The nearest misses:

| cell | R1 | R2 | why not |
|---|---|---|---|
| the 2u short Dog at a dog score of 8+ -> 3u | wins more in both halves, placebo 314 | the same, placebo 437 | luck can't be ruled out (16% / 22%); its hockey b2b core IS the 3u max play wired 11/16 |
| any ½u play with both reads over the price -> 1u | +10.1% on the added units, placebo 776 | 46 plays, placebo 553 | no separation from its siblings |
| the NBA floor at +100..+150 -> 1u | held -0.3u | +10.3u | flips on R1; the unseen seasons cut the NBA floor to a third |
| the floor's hockey dogs -> 1u | +5.3u, placebo 677 | +3.0u, placebo 1,286 | no separation; -7.0% on the unseen seasons |
| value play with the own read 3c+ over -> 1u | held -3.4u | 6 plays | the bigger own-read margin loses held out |
| the 2u Lock with both reads over -> 3u | held -1.1u, placebo 1,608 | 4 Locks | the fourth "no 3u Lock" |
| any 1u+ play with both reads over -> +1u | placebo 1,833 | placebo 1,551 | worse than a random set |

## 5. THE ONE THAT EARNED IT - the college hoops dog slot: 2u at a dog read of 5+ (was 6+) - WIRED

The slot as it runs today (the 11/16 open slot, the 11/14 home-dog -1 in; `s2b_read5.out`): 374 plays 2018-26, about 47
a season, **190-184, +19.8%** (train +17.0% / held +25.0%, 8 of 8 seasons). The read takes whole values (4, 5, 6, 7+):

| the dog read | record | won / needs | flat | train | held | seasons up |
|---|---|---|---|---|---|---|
| 4 (1u) | 105-116 | 47.5% / 43.0% | +10.3% | +3.8% | +22.6% | 6 of 8 |
| **5 (1u today -> 2u)** | **26-19** | **57.8% / 42.8%** | **+35.6%** | **+35.3%** | **14-11 +35.9%** | **7 of 8** |
| 6+ (2u) | 59-49 | 54.6% / 41.9% | +32.9% | +37.4% | +22.2% | 7 of 8 |
| 5+ together (the 2u cell after) | 85-68 | 55.6% / 42.1% | +33.7% | +36.9% | +28.2% | 8 of 8 |

- **Wins more than the size under it in both halves**: read 5 +35.3% / +35.9% against read 4 +3.8% / +22.6%.
- **The placebo**: the 2u cell after the change (read 5+) against a random 153 slot plays: as good **71 of 2,000**
  (3.6%). The read-5 band is the 6+ band's twin (a random 45 of the 6+ plays did as BADLY 1,159 of 2,000 times) and not
  the read-4 band's (a random 45 of the read-4 plays did as well **106 of 2,000**, 5.3%).
- **The worst stretch does not move**: -9.2u -> -9.4u.
- **The size the held-out half can prove** (a quarter of Kelly on the low end of the held-out win rate): read 5+ 2.6u
  at one standard error, 0.8u at the 5% end - the same footing the 6+ band's 2u already stands on (1.1u / 0u).

| the slot's sizes (the same 374 plays) | units (ROI) | worst stretch | held out | by season 2018 -> 2025 |
|---|---|---|---|---|
| TODAY: 1u, 2u at 6+ | +109.7u on 482u (+22.8%) | -9.2u | +40.3u on 165u | +7.7 +11.1 +7.7 +32.6 +10.3 +21.2 +8.7 +10.5 |
| **WIRED: 1u, 2u at 5+** | **+125.8u on 527u (+23.9%)** | **-9.4u** | **+49.3u on 190u** | +8.2 +10.1 +9.3 +36.9 +11.9 +24.8 +12.0 +12.5 |
| flat 2u (the read-4 band at 2u too) | +148.4u on 748u (+19.8%) | -22.5u | +66.5u on 266u | +8.3 +8.1 +14.9 +36.8 +13.9 +30.2 +19.4 +16.9 |
| 1u, 3u at 6+ | +145.2u on 590u (+24.6%) | -15.2u | +47.4u on 197u | +11.1 +18.2 +7.9 +46.9 +13.7 +27.2 +7.7 +12.6 |
| 1u at 4, 2u at 5, 3u at 6+ | +161.3u on 635u (+25.4%) | -13.8u | +56.4u on 222u | |

**Honest limits.** (1) It is 45 plays - about 6 a season; the money is about +2u a season. (2) Judged alone against
the read-4 plays the band sits AT the 5% line (106 of 2,000), not clear of it; it clears as part of the 5+ cell and as
the 6+ band's twin. (3) The dog read's weights were fit with these seasons seen (the 11/16 caveat) - the size is the
size the 6+ band already carries, nothing new. (4) Every season is up or level but 2019 (-1.0u).

**NOT earned in the slot:**
- **The read-4 band at 2u** (the brief's "should 4-6 be 2u"): the read-4 dogs are +3.8% in train (6 of 8 seasons) and a
  random set of slot plays beats them 1,937 times in 2,000 - they are the slot's weak band. Flat 2u makes +38.7u more on
  266u more (+14.5% a unit) and the worst stretch goes -9.2u -> -22.5u. No.
- **3u at 6+**: +35u more over eight seasons, but the held-out 6+ win rate (17-15) sizes it 1.1u on its low end and the
  worst stretch goes -9.2u -> -15.2u; the 11/16 hunt said the same. No (a third time).
- **The own read over the price / the efficiency read 15+ over / the price band** inside either band: no separation
  (`s2_cbb_slot.out`). The 4-band's long dogs (+151..+350) are -4.8% (train -21.7%) - a watch, not a cut.
- **The 🔍 college hoops gap play at 5+**: no dose by the read in the gap's own pool (read 0-4 +25.1%, 4 +4.6%, 5
  +27.0% on 33, 6+ +35.4%) - its ladder stays at 6+.

**Wired** (`sports.py`): `SIZE_1117_FROM = "2026-11-17"` (None = 6+ again), `NCAAB_SLOT_2U_READ_1117 = 5`,
`ncaab_slot_2u_read(day)`; post_board stamps the read that earns 2u on the pick when it posts
(`pk["ncaab_play"]["two_at"]`) and `ncaab_play_units` reads the stamp - **a play posted before the change has no stamp
and keeps 6+, so a posted pick keeps its units**. Never 3u. Test:
`test_sizing_1117_the_college_hoops_dog_slot_is_2u_at_a_dog_read_of_5_stamped_at_the_post_a_posted_play_keeps_its_units`
(end to end through post_board).

## 6. Straight answers

1. **"The half units are retarded."** They are where the engine is least sure, and they still make money: +8% to +13%
   a unit in the replay, 19-17 and up live since 10/25. Doubling all of them is +50u more in three replay years for a
   losing stretch a quarter to three quarters deeper and a thinner return on every unit - your call, not something the
   plays earned. I would not.
2. **"When it says thin edge, it loses."** The numbers say the opposite: the thin-edge ½u plays are the best ½u plays
   (+13.5% on 392; live 3-1). The ½u plays that lose are the ones the raw read loves (3c+ over: held out -5.8%, live 0-5).
3. **UMBC**: a ½u fallback on a day with no unit play, a dog read of 3 - a coin at +120 over eight seasons. Not a lock.
4. **The Chargers**: the engine had them as a fair +185 dog (34% against 35% needed), score 1.5 against a gate of 8. No
   bad input. No NFL road dog cell in that shape pays in both halves. A fair dog wins one time in three.
5. **Where bigger IS earned**: the college hoops dog slot at a read of 5+ -> 2u, from today's games. With yesterday's
   two (the hockey b2b Dog 3u, the college hoops Lock-test favorite 2u) that is three bigger sizes in two days, each on
   a cell that won more than its siblings in both halves.
6. **For the owner to decide** (not wired): every ½u play at 1u (above); the ⭐ at 2u (+29u / +13u for a deeper hole on
   R1); the dog slot's 6+ band at 3u (+35u in eight seasons, the held-out half says no).
