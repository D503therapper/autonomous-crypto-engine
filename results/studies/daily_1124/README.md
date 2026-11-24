# 11/24 daily studies

The owner's daily routine: the board check (with the accuracy layer's first live day), yesterday's picks, the lead
tracker and ten NEW studies.

**In one line:** the board is three plays (Weber St moved to a favorite before 8 AM and never posted); the accuracy
layer's price check worked on all three; four card bugs fixed at the root; of the ten studies ONE is built as a small
weight (the college hoops team that spreads its minutes, on the second day of a back-to-back, misses its number - ±0.02
in the spread stack from the 11/25 games), three are tracker leads (the NHL home side whose home margin lags its road
margin, the NBA home-heavy road dog, the deep team's dog) and the rest are dead. **No posted pick, price or size
changed.**

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead);
every read league-relative (the top / bottom fifth of the league's current values that night). Score and line-score
studies 2018-26 (train 2018-21 / held 2022-26); team-box and player-box studies 2021-26 (train 2021-23 / held 2024-26);
each held season shown apart in the `*_out.txt` files. Placebo = 2,000 random same-size sets from the cell's own pool;
the follow-ups are PRICE-MATCHED (the same number of sides out of each 50-cent price bin). Second prices: ESPN's open
(2023-26) and the paid NHL / NBA game-day morning (2021-23 / 2020-23) - the paid history was read, never pulled.
**About 780 cells were cut - about 39 clear |z| 2 by luck, and a placebo of 3 in 2,000 turns up by luck about once on
a day like this.** `python results/studies/daily_1124/view.py <file>` prints one short line a cell.

**Not re-run (checked first):** the brief's Thanksgiving / rivalry-week / early-tournament list is answered already -
NFL short weeks and Thursday (11/12 b1), the holidays incl. Thanksgiving weekend (10/31), rivalry week (10/31, 11/1,
11/21 s4), the bowl chase and senior day (10/31, 11/2), the events' stakes and the consolation game (11/1, 11/21),
neutral floors (11/3 - 11/21), the hoops back-to-back's second day as a spot (11/1); and everything in the 11/23 and
earlier "Not re-run" lists. NEW reads today: a pro team's home / road split, the swing of its margins, its record
against winning teams, the NFL team box's sacksYardsLost and defensiveTouchdowns, the NBA second quarter, the NHL
second period, a college team's minutes spread over its bench (the player box) on a second day, football's fourth
quarter.

## 1. The board (11/24)

Three unit plays, as the rules post them:

- **⭐ Illinois St +100 2u** (8:00 AM; the college hoops dog slot, dog read 4 = the ratings 2 + "the favorite lost its
  last" 2; a 1u slot play at +150 or shorter carries the ⭐ at 2u - the 11/17 rule the 11/22 study kept). Neutral floor,
  both teams on the second day of the event. Second price at the post: Action Network's consensus -105 - confirmed.
- **Campbell +102 ½u** (9:09 AM; the dog slot's road dog at a read of 3). Second price +100 - confirmed.
- **Magic +114 ½u** (9:50 AM; the NBA floor, dog score 0.35, the paint weight on it). Second price +116 - confirmed.

**Weber St did not post.** The pre-check's +102 was the overnight price; at 7:10 AM PT the book flipped the game
(Weber St -112, Tarleton St -108) - a favorite is no 🔍 dog. Nothing to fix. The slot's cap (two a night), the NBA
floor's +199 cap, one play a side, the ⭐ on the biggest bet: all pass. Slate check: 92 games named and priced, 0
problems.

**The accuracy layer's first live day (11/23's sports_verify / sports_gameday):**
- `price_2nd` is stamped on all three picks, all three confirmed by Action Network's consensus inside 3 points of win
  chance (+100 vs -105, +102 vs +100, +114 vs +116). The health line reads right ("double check: 1 ... claims on 1 live
  cards - 1 confirmed", written when only Illinois St was up).
- The injury half had nothing to settle today: no card carries a questionable man, there is no NFL game (the inactives
  reader has not been asked yet - `source_status.json` has no `espn_gameday_*` row; Thursday's three NFL games are its
  first test). The Magic card's eight OUT men are single-sourced (ESPN alone) - the health line will say so.
- **Could not be checked from here:** the Pistons' Cade Cunningham was day-to-day when the Magic posted (a top-3
  scorer - the NBA hold's man). The pick posts through that only when ESPN's note reads probable
  (sports_questionable.probable_note); ESPN is blocked from this sandbox, so the note could not be re-read. If he was
  plain "questionable", that is a hold that did not hold - worth one look at the run log's 9:50 AM lines.
- The ❓ header had no man to show (it lists OUR game-time men and a man two sources disagree on); it rendered nothing,
  correctly.

**Card bugs, fixed at the root (breakdown VERSION 87 rewrites the open cards - wording only):**
- **The same note three times** - the Campbell card said "(not counting the Tennessee game)" under three lines
  running. The page shows it once, on the first line (`sports_card_sell.note_once`); the stored lines keep it (the
  number check reads it).
- **A tune-up dressed as form** - the ⭐ Illinois St card: "80+ points in 3 of their last 5" and "outscored teams 207 to
  167 in the first half over their last 5" counted a 123-48 win over Eureka (not D1) - 65 of the 207. A college hoops
  team's big nights and halves read Division I games only now (`sports_breakdown_v24._form`), like every other
  "lately" line. The half line no longer clears; the 80+ line still does (3 of its 5 D1 games).
- **No reason line on the ⭐** - "the ratings back this side" had nothing to say (Illinois St had beaten one D1 team).
  New fact: the games we finished within 5 points of a WINNING team - "Illinois St finished within 3 of Santa Clara and
  within 5 of Saint Mary's this year. Those two won 11 of 13 against D1 teams between them." (`close_calls`, the 🧭
  `sched_c` line; said as how close, never as a loss; re-derived on every render by `sched_wrong`). It leads the card.
- **A line written to be cut** - the Magic card's "🚑 Pistons are without Duncan Robinson (F)." was written, counted
  toward the card's floor and then cut on every render (the 🚑 header already names him) - one log line a run. Not
  written any more when it is only the header's names again.
The Illinois St card is still short (4 fact lines + the reason line): the files hold no more for that side.

## 2. Yesterday (11/23): 6-0, +6.83u

| pick | result | how |
|---|---|---|
| 🐶⭐ Kings +130 2u | WON 2-1 at Montreal | 1-0 after one, 2-1 after two, a scoreless third; matched the close (+130) |
| Indiana St +124 1u | WON 77-76 vs East Carolina | **in overtime** (63-63 after regulation, 14-13 in the extra five) - a coin that landed; beat the close (+114) |
| San José St +105 1u | WON 88-79 at UC San Diego | 43-42 at the half, 45-37 after it; the close was better (+120) |
| Washington +11.5 ½u | WON (lost 83-77) | led 39-31 at the half, BYU won the second half 52-38; closed +10.5 - beat it by a point |
| Trail Blazers +139 ½u | WON 128-111 at Philadelphia | won the second half 59-42; closed -110 (Embiid ruled out after the post) - beat the close by a mile |
| Pacers +160 ½u | WON 125-120 vs the Thunder | up 5 at the half and it stayed there; matched the close |

Beat the close 3 of 6, matched 2, worse 1. Pick audit: no flags (six card-check catches, all handled at render).
**Where luck carried it:** Indiana St won by one in overtime; the Pacers were the second NBA floor play the rules
would not have posted (the 11/23 stale-run bug, fixed from 11/24); the Blazers' price ran to our side on news that
came after the post. A good day - not a reason to change anything.

## 3. The lead tracker (lead_tracker.py)

Nothing raised, nothing cut. No tag at 100+ graded is clear and steady: money 10+ over tickets 227-298 +0.0% on 525,
reverse line move -0.8% on 302, 70%+ of tickets -2.3% on 281, NBA spread favorite games 1-20 -4.5% on 130, college
hoops small favorite away from home Nov-Dec -7.0% on 130 (z -1.0), hockey favorite weighed up +0.9% on 119, small
favorite weighed 2+ under the market (college hoops) -7.5% on 113, **the spread side across a three-lucky team / a top
scorer out 47-53 -10.3% on 100 (z -1.1)** - that is a BUILT stack weight's own record reaching 100 on the wrong side
of even; one more week before it is read as a verdict (the stack play's quit rule is its judge). The loudest small
one is still the 4-5 nights' rest spread side 18-30 on 48.

## 4. The ten studies

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NBA: the HOME / ROAD SPLIT (home margin minus road margin a game) | **LEAD (tracker)** | the home-heavy team (top fifth) as a ROAD dog -13.0% on 633 vs -3.8% (same-price placebo 56); with a winning margin overall **-25.3% on 306** (train -28.3% / held -22.7%, placebo 1 of 2,000) - but the paid morning -7.3% on 260 (placebo 1,042) and 2024 was +15% |
| S2 | NHL: the HOME / ROAD SPLIT | **LEAD (tracker)** | the HOME side in the bottom fifth (its home margin lags its road margin) **-11.7% on 1,316** at -200..+350 vs -6.0% (train -12.1% / held -11.4%, 9 of 9 seasons down, same-price placebo 14); the open -11.6% on 589; only the bottom fifth (the others -3.4..-5.0%) |
| S3 | NBA + NHL: the SWING team (the spread of its last 15 margins) | DEAD | NBA swing dog +0.7% on 1,101, vs a steady team +10.7% on 212 (placebo 78); NHL swing dog -3.2% on 1,439 - variance doesn't pay the dog |
| S4 | NBA + NHL: the record against WINNING teams | DEAD (a watch) | NBA "beats the bad ones only" vs a winning team: dog -7.5% on 816; NHL "as good against winners as losers" vs a winning team: dog -12.0% on 914 (train -15.6% / held -8.5%, placebo 83) - a watch, the wrong way round for the idea |
| S5 | NFL: the SACK RATE off the team box | DEAD | its QB gets sacked: ATS -6.2% on 451; top-fifth rush vs a leaky line ATS +3.4% on 94 (train +15.8% / held -14.9%); top-fifth net dog -25.7% on 137 (train -40.2% / held -11.0%, placebo 72) - too few, halves apart |
| S6 | NFL: DEFENSIVE TOUCHDOWNS (last 3 games) | DEAD | scored 2+: ATS -5.4% on 142 (the base -4.3%), dog -15.5% on 53; gave up 2+: ATS -0.3% on 115 |
| S7 | NBA: the SECOND QUARTER (last 10) | DEAD | top fifth dog -6.3% on 894, bottom fifth dog -0.9% on 1,511; top vs bottom ATS -0.9% on 662 (train -8.7% / held +6.1%) |
| S8 | NHL: the SECOND PERIOD (last 15) | DEAD (a watch) | top fifth dog -9.8% on 760 vs -5.7%; bottom fifth with the rest of its game over the league middle, small favorite -13.0% (placebo 19) - one cell of 48 |
| S9 | college hoops: DEPTH on the second day of a back-to-back | **BUILT - ±0.02 in the spread stack from 11/25** | the deep team (bottom fifth share of minutes on its top 5) on its second day: **ATS -27.4% on 276** (train -25.7% / held -29.6%, 5 of 5 seasons down, placebo 0 of 2,000), the side across **+18.4%** |
| S10 | football: the FOURTH QUARTER (season to date) | DEAD | NFL bottom fifth ATS -9.4% on 682 (train -11.3% / held -7.7% - a watch), top-fifth dog +2.5% on 225 (placebo 246); college top-fifth dog -6.6% on 287 (train -20.3% / held +0.9%) |

## S9 - the deep team on its second day (s_today.py s9 -> s_follow.py s9 -> s9c_replay.py / s9d_check.py / s9e_engine_read.py)

The read: the share of a team's minutes this season its five busiest men played (the player box, 4+ boxed games),
ranked among the league that night. Bottom fifth = "deep" (about 59-62% on its top 5; the middle team is at 65-67%).
"Second day" = its last game tipped within 1.3 days - the November events' back-to-backs and the league tournaments.
The idea going in was the old saying (depth helps on short rest). The numbers say the opposite.

| cell (ATS at the close) | all | train 2021-23 | held 2024-26 | placebo |
|---|---|---|---|---|
| every team on a second day | -6.8% on 1,625 | -8.1% | -5.1% | |
| **the deep team on its second day** | **-27.4% on 276** (38% covered, 2.1 points a game under its number) | -25.7% (0 of 3) | -29.6% (-41.2 / -19.1 / -26.8) | **0 of 2,000** |
| **the side across it** | **+18.4% on 276** | +16.4% (3 of 3) | +20.9% (+32.5 / +10.4 / +19.7) | **0 of 2,000** |
| the dose: the other four fifths on a second day | +2.4 / -7.8 / +4.2 / -10.4% | | | |
| depth counted another way (10+ men at 10+ minutes a team game) | -32.4% on 147 | -41.9% | -24.1% | |
| Nov-Dec / Jan-Mar | -20.8% on 106 / -31.6% on 170 | | | |
| laying points / getting points | -26.2% on 124 / -28.5% on 152 | | | |
| off a win / a loss under 15 / a 15+ loss (the 11/1 cell) | -25.9% on 206 / -26.9% on 52 / -47.1% on 18 | | | |
| the other side on its second day too / rested | -27.6% on 200 / -27.1% on 76 | | | |
| CONTROL: the deep team with one day off | +1.0% on 1,094 | +1.3% | +0.4% | |
| CONTROL: the deep team, neutral floor Nov-Dec, NOT a second day | -1.9% on 187 | | | |
| its moneyline dog +100..+350 | -31.7% on 116 | -31.5% | -31.9% | 31 (same price) |
| the game's under | -0.7% on 270 | | | |

The checks: (1) fair price - the close at its own juice (college spreads have no open on file); (2) blind - a
walk-forward league rank, nothing from the game itself; **s9d: is "yesterday's game" a real game or the same game on
file twice (which would leak tonight's box into the minutes)? 0 twins in 1,639 second-day sides**; (3) five of five
seasons down, 192 different team-seasons, no team more than 5 times; (4) this season -26.8% on 8 - nothing yet; (5) a
second look three ways - depth counted by men not minutes, the 11/16 replay rows (a separately built table: across
+29.9% on 152, the deep team -38.4% on 152, both halves), and the ENGINE's own function on every priced game (s9e:
-26.2% on 259, across +17.5%).

**The stack play's replay with it (s9c, the 11/16 rows, ±0.03 tried):** a +0.02..+0.04 stack across a deep second-day
team +20.7% on 38 (train +33.2% / held +6.8%) - the plays the weight adds; a +0.05+ stack ON the deep team -51.9% on
12 - the plays it drops; the play pool +6.6% on 1,373 -> +7.4% on 1,400; the best three a night +4.6% on 924 -> +6.3%
on 943 (train +2.1% -> +4.9%, held +8.2% -> +8.4%). The dog slot's own replay dogs never carried it (0 posted).

**Honest:** nobody predicted this direction, about 780 cells were read today, the margin (2.1 points, z about -3.1) is
less loud than the cover rate (z -4.9), and about 8 plays a season move. So it goes in at the tune-up weight's size
(±0.02), not the 0.03 the cover rate would buy. Wired: `sports.NCAAB_DEEP_FROM` "2026-11-25" ("9999" = off),
`NCAAB_DEEP_W` 0.02, `mark_ncaab_deep`, `ncaab_deep_spread_w` in the spread rank and `ncaab_spread_stack`;
`sports_ncaab_roster.top5_share / deep_cut / second_day / deep_second_day`. Nothing when both teams are deep on a
second day; unknown = nothing. Tracker tags "college hoops spread side across a deep team on its second day" /
"..., the deep team on its second day (fade)" judge it at 40 graded each (the side across under 50% covered = out; 56%+
= 0.03); the dog is a tracker lead only. Test
`test_daily_1124_the_deep_team_on_its_second_day_is_a_stack_weight_from_the_11_25_games`.

## S2 - the NHL home side whose home margin lags its road margin (s_today.py nhl -> s_follow.py nhl -> s2c_board_replay.py)

The read: margin a game at home minus margin a game on the road (a game counts at most 6 goals), season to date, 15+
games with 6+ each way, ranked among the league that night.

| cell (the close, -200..+350) | all | train 2018-21 | held 2022-26 | placebo (same price) |
|---|---|---|---|---|
| every home side | -6.0% on 6,055 | -5.9% | -6.0% | |
| **home side, bottom fifth split** | **-11.7% on 1,316** | -12.1% (0 of 4) | -11.4% (-10.8 / -9.5 / -4.1 / -13.8 / -61.1) | **14 of 2,000** |
| ... as a dog / a favorite -200..-101 | -17.2% on 436 / -9.2% on 874 | -22.7% / -7.0% | -13.4% / -10.9% | 26 / 159 |
| the dose (home side's split, bottom fifth -> top) | -11.8 / -4.6 / -4.9 / -5.0 / -3.4% | | | |
| which half: a top-fifth ROAD margin alone / a bottom-fifth HOME margin alone | -11.4% on 1,067 / -5.6% on 1,543 | | | 26 / 995 |
| at ESPN's open (2023-26) / the paid morning (2021-23) | -11.6% on 589 / -7.4% on 152 | | | 47 / 332 |
| not on a back-to-back | -12.7% on 1,142 | -15.8% | -10.5% | |
| the road side across it | +0.3% on 1,560 (favorite -200..-101 +6.6% on 568) | +0.3% | +0.3% | 83 (27) |
| a home-heavy home side (top fifth) vs a bottom-fifth road team | +11.0% on 326 | +12.4% (4 of 4) | +9.9% | 1 |

It is the team with the rich ROAD margin that is overpriced at home (the price pays for the road record); a poor home
margin alone is nothing. **Why no weight:** against its base the z is about -2.2 (one of ~780 cells), and on the 11/17
replay board the hockey sides the board actually POSTED carried it 20 times in three seasons (+6.7%; the 12 favorites
-28.3%, the 8 dogs +59.3% - nothing to read), while every replay favorite -200..-101 with it ran -10.6% on 382. Two
tracker tags from the 11/25 games: "NHL home side whose home margin lags its road margin (fade) (lead)" and its mirror
"NHL road side at a team whose home margin lags its road margin (lead)" - judge at 60.

## S1 - the NBA home-heavy team on the road (s_today.py nba -> s_follow.py nba)

The road side in the top fifth of the split: -10.8% on 1,010 at -200..+350 (train -9.6% / held -12.1%, same-price
placebo 19), only the top fifth (the others +4.4 / -4.6 / -2.1 / -1.3%); the dog -13.0% on 633 (placebo 56). With a
winning margin overall (top half): the dog **-25.3% on 306** (train -28.3%, 0 of 4 / held -22.7%: -48.1 / -29.3 /
+14.9 / -9.2; placebo 1 of 2,000). It is the rich HOME margin that is overpriced on the road (a top-fifth home margin
alone: dog -17.5% on 401). **Why no weight:** the paid morning price does not confirm (dog -7.3% on 260, placebo
1,042; the open -16.7% on 233, placebo 118), the last two seasons are +14.9% and -9.2% on 61, and the home side across
it is flat (-0.1% on 920). Tracker tag from 11/25: "NBA road dog, home-heavy team with a winning margin (fade) (lead)"
- judge at 40. (`sports_split.py` reads both leagues; `sports.mark_split` stamps, nothing on the board reads the
stamps.) Test `test_daily_1124_the_pros_home_road_split_is_two_tracker_leads_and_moves_nothing`.

## Files

`lib.py` / `h.py` / `core.py` (shared), `s_today.py` (S1-S10), `s_follow.py` (the controls), `s2c_board_replay.py`,
`s9c_replay.py`, `s9d_check.py`, `s9e_engine_read.py`, `lead_tracker.py`, `view.py`, and every `*_out.txt`.
