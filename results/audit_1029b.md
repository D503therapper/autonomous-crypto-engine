# 10/29 (afternoon) - NBA / HOCKEY / LINGO SWEEP

The owner: "We need to get better with NBA - more NBA units, win more NBA. We need to win more hockey. The lingo needs to
get better - the lingo still sucks, the breakdowns and the lingo. Run Fable, do a full sweep, fix everything, add any
plays, whatever's necessary." Standing authorization (10/24-10/25). Today's posted board untouched (the Blue Jackets +205
Dog stays - the owner bet it).

## A. NBA - where the NBA units come from, checked against the data

**The NBA favorite play (10/27, tag nba_fav) is not broken - it has had zero chances.** It needs a favorite -150..-101 whose
10/22 weights net positive: off a 20+ win, or at a home dog in its games 31-60 (December on) - and never a team's games 1-5.
This season through 10/29: 34 NBA favorites in the band, ZERO with 6+ games played AND a 20+ win last time out. `dog_more`
(the last margin) is set on every candidate (sports.candidates line 679), mark_nba_favorites runs on every board. The
replay cell is 87 plays in three seasons - about 0.17 a night once the season is a few weeks in. Nothing to fix; judge at 50.

**The 🏀 NBA opening-line play (sports_nba_open, live from 10/29 - the Wizards -107 is the first) re-checked blind at the
OPEN** (scratchpad nba_open_bar.py: each season 2023-27 fit on the seasons before it, the best side a slate night at the
opening prices, graded at the open, 499 slate nights):

| bar (points over the open's no-vig number) | record | ROI | units | seasons up |
|---|---|---|---|---|
| 2 | 207-228 | +7.7% | +33.7u | 4 of 4 |
| 3 | 196-207 | +9.9% | +39.7u | 4 of 4 |
| **4 (live)** | **168-164** | **+13.5%** | **+44.7u** | **4 of 4 (+13.1 / +19.9 / +7.0 / +4.7)** |
| 5 | 129-127 | +11.9% | +30.4u | 4 of 4 |
| 6 | 84-79 | +10.8% | +17.6u | 3 of 4 |

Dogs only at 4: 76-127 +12.0% (2 of 4); favorites only at 4: 127-82 +9.9% (4 of 4) - both sides stay in. Games 1-10 at 4:
25-26 +10.1% (3 of 4); 11+ 143-139 +13.7%. **The #2 side a night loses** (bar 4: 65-93 -5.4%; bar 5: 37-46 +2.3%, 1 of 3)
- one play a night stays. **The 4-point bar is the right one; untouched.** It should make about 0.67 NBA plays a slate
night (332 on 499 nights) - that is the NBA unit engine now that it fires from game one.

**The NBA floor (best dog by score 0+, ½u, 84-110 +16.5% on 194):** score 2+ alone was flat (+0.4% on 101), so there is no
better cut inside it; ½u stays (judge at 50). NBA spreads: dead 10/9, not revisited. NBA totals: no totals read exists for
the NBA (never built) - a study, not a sweep item; noted for a daily run.

**Sizing (the owner's call, not changed):** the opening-line play is ½u (sports_early.SPOTS "nba_open"). At 1u the same
plays would have been +89u over four seasons, 4 of 4 up - the strongest NBA cell we hold. Recommended: 1u once the first
20 live plays are graded and the live ROI is positive; the owner decides.

## B. HOCKEY - the fallback Dog rule (the owner: pick whichever replays best held out)

The 10/29 ten-study table (9,533 NHL finals 2018-27, the live hockey read fit on train 2018-23 only, held out 2023-27;
dogs +100..+350 not on a back-to-back with the own read not under the no-vig market - the fallback Dog's rules as of
10/28; scratchpad nhl_rule.py):

| rule | train | held out |
|---|---|---|
| today (any band, own read not under the market) | 957-1521 -5.6%, 1 of 5 up | 746-1097 -2.2%, 1 of 4 |
| B: never past +199 | 858-1263 -5.4%, 0 of 5 | 682-923 -1.1%, 2 of 4 |
| **A: own read 2+ points over the no-vig market** | **135-174 +5.0%, 4 of 5** | **99-132 +0.5%, 2 of 4** |
| A and B together | 124-156 +3.1%, 3 of 5 | 91-120 -2.3%, 1 of 4 |
| A at +100..+150 | 102-121 +2.9% | 77-87 +2.9%, 3 of 4 |
| A at +151..+199 | 22-35 +3.9% | 14-33 -20.3%, 1 of 4 (the WATCH stands) |
| A at +200..+350 | 11-18 +22.6% | 8-12 +30.1% |
| over by UNDER 2 at +200..+350 (the Blue Jackets' cell) | 88-240 -9.5% | 56-162 -13.2% |

**BUILT: sports.NHL_FALLBACK_OWN_GAP = 2.0 / hockey_own_gap / hockey_own_gap_ok** - the fallback hockey Dog
(best_hockey_dog) needs its own read 2+ points over the no-vig market; the only version up in both halves. The +199 cap
alone loses both halves, and adding it to A throws out the 8-12 +200..+350 cell. In the live read "2+ over the market"
IS the rested dog against a favorite on a back-to-back (540 of 540 in the table) - so the fallback Dog is now that spot plus
the 3+ score (10/28). The gated Dog (score 6+) keeps the 10/27 "not under the market" rule. Live hockey Dogs 9/30-10/29:
14 of 16 sat under 2 points over (3-10 and the open Jackets); the two over went 0-2 (Flyers +110 10/3, Sharks +145 10/5) -
too few to read. The board preview names the gap when it keeps a dog off. Test
test_sweep_1029b_the_fallback_hockey_dog_needs_the_own_read_2_points_over_the_market. Expect FEWER hockey Dogs (most
nights none; the ½u floor plays still fill the board - the floor's hockey plays +15.5% in the 10/28 replay).

Data note: the study table's goalie names come from players/nhl.csv's G rows; the 10/28 Kraken-Maple Leafs row carries
"Sergei Bobrovsky" as the Leafs' goalie - a box-score team label worth a look in a daily run (it does not touch the
read, only the goalie cells).

## C. LINGO - the 10/27-10/29 cards graded line by line

19 posted cards (data/sports/picks.json). What was wrong, with the fix:

- **Stat-head jargon:** "🍀 Shooting plus save % for Blue Jackets, last 10: 98.4" (and the pool's "98.4 PDO") - now "Puck
  luck's been shit for the Blue Jackets - shooting plus save % at 98.4 over the last 10 games (100 is average). That snaps
  back." "The dog check backs it" / "the dog check likes X" (four floor closers, the dashboard's thin-edge line and the
  no-Dog note) - now plain: "every angle we grade a dog on", "the best dog on the slate by our angles". The card guard
  (sports_card_guard.JARGON) now drops PDO / dog check / dog score / Corsi / xG / the vig before they post.
- **Wrong grammar:** "Warriors is the side, that's just facts", "{us} gets it done", "{us} take this one", "{us} is the
  side / is our side", "{us} is still the side" - every one through vb() (Warriors are / Heat is). "Cam Talbot — The Blue
  Jackets' last starter in net —" (a capital The mid-sentence) - _possm.
- **False / weak claims:** "🔥 Both teams are rolling: Blue Jackets have won 2 straight, Hurricanes 2" - a heater is 3+
  now (HOT_MIN); at 2 the record line says the last score instead. "We price X at +120 - +150 is extra money. That's just
  facts" - the owner's rule is never "facts" after a number; now "We'll take it."
- **The same fact twice on a card:** "📋 Blue Jackets are 5-5 after a 4-3 win over the Flyers" + "📅 Both coming off W's -
  Blue Jackets a 4-3 win over the Flyers, Hurricanes a 2-1 win" - the W-W line now says only THEIR score when the record
  line already said ours ("The Hurricanes come in off a 2-1 win over the Bruins themselves - two winners walk in, one
  walks out").
- **Filler at the end of the risk line:** "Everything above is why we take it anyway" (next door to the banned "everything
  above tips it our way") - replaced, two new risk wordings, the guard's FILLER catches it.
- **Samey closers:** every floor card ended "Thin edge, half a unit, tread light" / "keep it light" / "small bet - thin
  edge" - seven ways now, with the owner's lines where they fit ("scared money don't make no money", "you can't win if you
  don't play", "small money, real shot"); four new one-liner tails ("We on X, no hesitation", "Give me X", "X. Done
  talking.").
- **The early card's "we beat the line"** (the Wizards -107, now -110): the three wordings all say it plain - "we got the
  better number" / "our price was the better one, and it's locked in".
- Fine as posted (left alone): "The Timberwolves are holding 77% of the action", "the Avalanche had the night off",
  "A 62-20 team last year against a 22-60 one. We tilt Spurs", "83% of the crowd is on the Packers. Ride Panthers".

sports_breakdown.VERSION 59 -> 60: every open card re-renders with the new wording (the picks never change). Test
test_sweep_1029b_lingo_no_stat_jargon_real_verbs_and_a_heater_is_3_straight.

## Bugs fixed

1. The fallback hockey Dog took a dog whose own read sat a hair over the market (the losing cell) - the 2-point rule.
2. The "both rolling" line fired at 2 straight wins.
3. The same last-game score printed on two lines of one card.
4. "The" capitalized mid-sentence in the goalie line.
5. Plural team names with singular verbs in four pools.
6. "That's just facts" after a number in a play closer.
7. Jargon (PDO / dog check) on cards and in the dashboard's thin-edge and no-Dog notes.

NOT changed: NBA sizing (the owner's call - the 1u recommendation above), the NBA open bar (4 is right), the NBA favorite
play (no chance yet), the NBA floor, the 12+ slate weight (3-8 live, judge at 50), today's posted picks.
