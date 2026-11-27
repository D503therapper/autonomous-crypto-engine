# 11/27 daily studies

The owner's daily routine: yesterday's pick, the lead tracker and ten NEW studies (the board check was done by the
operating manager: ⭐ Senators +120 2u, Liberty +100 1u, Colgate -108 ½u, Heat +130 ½u, Wichita St +170 ½u).

**In one line:** yesterday went 0-1 (-0.5u; Chiefs +130 ½u lost 13-10 on a 57-yard field goal at the gun, the close
+132 - a fair bet, the read was right on the quarterbacks and the turnovers); TWO card bugs fixed at the root (the
page cut the card's best true line as "price math", and the card sold a defense that had stopped leaking); of the ten
studies NOTHING clears the five checks - no new weight; ONE pair of tracker leads from the 11/28 games (a college
hoops team beat up on the glass in its last game, on a neutral floor, and the side across it), four watches, the rest
dead. **No posted pick, price or size changed.**

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead).
Team-box / player-box studies 2021-26 (train 2021-23 / held 2024-26), the title game 2018-25 (train 2018-21 / held
2022-25), the paid football history 2020-26 (train 2020-22 / held 2023-26 - read, never pulled); each held season
shown apart in the `*_out.txt` files. Placebo = 2,000 random same-size sets from the cell's own pool; the follow-ups
are PRICE-MATCHED (the same number of sides out of each 50-cent price bin) or drawn from the cell's own floor (neutral
sides against neutral sides). Second price: ESPN's open (2023-26). **About 830 cells were cut - about 40 clear |z| 2
by luck, and a placebo of 6 in 2,000 turns up by luck about twice on a day like this.**
`python results/studies/daily_1127/digest.py <file>` prints the cells 5+ points off their base; `view.py <file>` one
short line a cell; `seen.py "<regex>"` checks SPORTS_FINDINGS.md for an idea before it is run.

**Not re-run (checked first with seen.py):** everything in the 11/26 and earlier lists. Ideas dropped today because
they were answered before: the book's first-half number against its share of the full spread (10/29 -
`sports_leads.h1_share`; a first pass was run here before the check caught it and is NOT kept), the soft recent
schedule (11/3 the Elo-adjusted last 5, 11/24 the record against winning teams, the NHL schedule lead), the puck
line's price against the moneyline (11/20), the hot / cold star (the 11/8 NBA build, its college twin), NFL wind
(10/15, 11/11 - yesterday's game blew 25 mph), three-point attempt share (11/10), the league opener, the service
academies' totals. **Could not be run:** the see-saw team (ESPN's leadChanges exists from 2025 only - no train half),
anything on futures (on file from 10/2 only), the total's move (the paid history holds no totals). **The paid
history:** its spread file holds ONE look a game (the early one), so "the line that sat still" (S10) is the first fair
spread against ESPN's close - the one shape the 10/8-11/17 work never cut; nothing else new is in those files.
**New reads today:** ONE game's box as a spot (rushing yards allowed, sacks taken, the option, a night from three, the
rebound margin), the skater box's plusMinus / timeOnIce, the conference title game, the top scorer's drought.

## 1. Yesterday (11/26, Thanksgiving): 0-1, -0.5u

| pick | result | how | the close |
|---|---|---|---|
| Chiefs +130 ½u (the daily floor - an NFL road dog, dog score 1.74) | LOST 13-10 at the Bills | Chiefs led 10-7 after three; the Bills kicked two field goals in the 4th, the winner Tyler Bass from 57 yards as time ran out; 40 degrees, 25 mph wind, rain | opened +125, posted +130 (Action Network +133 beside it), closed +132 - flat, the close two cents better |

**What the engine read.** Its own read 45.4%, the weighed read 42.4% against a no-vig market of 41.8%; +130 needs
43.5%. A dog score of 1.74 where the Dog of the Day's gate is 8 - never the Dog, the floor's one play of the day (an
NFL road dog on a thin edge, the group that pays: 51-54 +26.5%). Named reasons, both true: "better QB play lately"
(Mahomes 10 touchdowns, 0 picks, 914 yards in his last 3; Allen 3, 4 and 734) and "revenge game" (Bills 28-21 on
11/2/2025 - 390 days back, inside the 400-day truth rule). The Chiefs were one regular more short-handed (Kenneth
Walker III, Jaylon Moore, Omarr Norman-Lott - all three inactive on the game-day list, as the card said): -1 on the
read.

**Why it lost.** Not the read. The quarterbacks went the way it said (Allen 10 of 21 for 81 yards and 2 picks;
Mahomes 16 of 29, 174, no picks) and the Chiefs won the turnovers 2-0. The Bills won it on the ground and on third
down in the wind: 43 runs for 166 yards (James Cook 32 for 117), 9 of 16 on third down to the Chiefs' 2 of 11, the
ball for 36:55 - and a 57-yard kick at 0:00. The total closed 46 and they scored 23. A fair-price ½u that lost at
the gun; nothing to change in the pick.

**Pick audit:** no pick flags; the close line above; two card-check catches - and both were bugs:

1. **The page cut the card's best true line as "price math" (fixed, with a test).** "🧤 Chiefs gave it away 7 times
   in 10 games this year. Bills: 16 in 10." is the turnover matchup - the card's strongest fact, and exactly what
   happened. The price-math rule (`sports_card_check.PRICE_MATH`, written for "winning about 4 times in 10 is all we
   need") matched "times in 10", so the line was cut as the line under the pick AND as a body line. Every football
   turnover / sack line of a team 3, 4 or 10 games in went the same way - the whole NFL this week. Now
   `sports_card_check.price_math`: a line that counts something over a team's GAMES is a fact; the 💵 line and the
   price wordings still go.
2. **The card sold a defense that had stopped leaking (fixed, with a test).** With the 🧤 line gone the card leaned on
   "🛡️ Bills are leaking 21 points a game this season. Chiefs hold teams to 16." (the audit's second catch: it was on the card twice). True on the year
   (20.8) - and the Bills had given up 6, 12 and 9 in their last three. The game ended 13-10. Now
   `sports_breakdown_v24.season_still`: the season scoreboard comparison (their defense, their offense) is written
   only while the other team's last 3 games are not 6+ points (a goal in hockey / baseball) BETTER than its own
   season number; under 6 games the season line stands. Ours is untouched.

Neither touches a pick, a price or a size - the words on a card only.

## 2. The lead tracker (lead_tracker.py)

Nothing raised, nothing cut. No tag at 100+ graded is clear and steady: money 10+ over tickets -0.9% on 557, reverse
line move -1.0% on 330, 70%+ of tickets -1.9% on 304, lucky from three (fade) 126-70 +6.2% on 196 (10-10 since
yesterday), the stack weight's own record 88-87 -4.0% on 175 (z -0.6 - even), the small college favorite away from
home -2.7% on 169, the out-rebounded spread side 60-66 -9.1% on 126 (z -1.1 - the fade is doing its job, slowly).
"Hockey fav weighed DOWN (fade)" reached 100 graded at 62-39 +1.2% on 101 - flat, no case either way. Loud and
small, left alone: the 4-5 nights' rest spread side 22-33 on 55, the NBA dog at a score of -4 or less 11-35 on 46,
the college dog off a win over a winning team 8-25 on 33, the tune-up spread side 22-9 on 31 (z +2.1 - the built
weight; its size is judged at 40).

## 3. The ten studies

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NHL: the TOP LINE'S PLUS-MINUS (the skater box's plusMinus / timeOnIce - first read) | WATCH (two cells) | the small favorite CARRIED by its top line -10.5% on 710 vs -3.0% (train -11.4% / held -9.4%; price-matched placebo 12 of 2,000) - a step at the top fifth only (the fifth below it is +4.3%), this season +20.5% on 33; the dog whose top pair is winning its minutes -14.5% on 629 vs -7.0% (placebo 45) |
| S2 | college hoops: the game after getting BEAT UP ON THE GLASS (out-rebounded by 12+, one game as a spot) | **LEAD (tracker, from 11/28)** | on a NEUTRAL floor ATS **-17.7% on 318** vs -4.4% for every neutral side (train -11.8% / held -23.3%, 6 of 6 seasons down; placebo 6 of 2,000); the side across +11.7% on 281; home / road floors nothing; no slope in the dose |
| S3 | college football: the CONFERENCE TITLE GAME | WATCH (the under) | 52 priced games 2018-25: the under +17.1% (train +11.7% / held +19.7%; placebo 133), the favorite's moneyline -16.7% on 56, favorites ATS -8.5%; the rematch loser ATS 0.0% on 23 |
| S4 | football: the game after getting RUN ON (200+ / 275+ rushing yards allowed) | DEAD | NFL ATS -6.4% on 191 vs -4.3%, dog +0.3% on 89; college dog -11.3% on 193 (train -37.0% / held +11.3% - flips); the team that RAN for 275+ on the road ATS -12.7% on 400 (placebo 88 - the road favorite again) |
| S5 | football: the game after the QB got SACKED 5+ | DEAD (a watch: the NFL road dog) | NFL dog +12.2% on 161 (train +26.4% / held -1.8%), on the road +23.4% on 89 (both halves); college dog +0.2% on 182; the college favorite past -150 that got sacked 5+ and lost +11.6% on 115 - a price we don't play |
| S6 | college football: the WEEK AFTER THE OPTION | DEAD | ATS -7.8% on 275 (train -17.2% / held +1.6%), dog -0.8% on 79, the side across -4.0% on 230 |
| S7 | NHL: the TOP SCORER'S DROUGHT (no point in 3+ games) | DEAD | dog +2.4% on 216 vs -6.7% (train +10.1% / held -9.4%), small favorite +7.1% on 77; the dog across him -19.1% on 122 (placebo 241) |
| S8 | NBA: the NIGHT FROM THREE (the last game) | WATCH (the spread, the total) | off a hot night (50%+ on 25+) ATS -10.5% on 617 vs -4.4% (both halves; placebo 93), the dog -10.3% on 219; a side off a COLD night: the over +4.9% on 473 / the under -13.9% (placebo 36) |
| S9 | college hoops: the NIGHT FROM THREE (D1 games) | WATCH | the dog off a hot night (50%+ on 18+) -16.7% on 586 vs -7.7% (train -10.9% / held -24.5%; price-matched placebo 104 - over the line); a step at 50% only; the open -17.8% on 355 vs -8.8% |
| S10 | football: the LINE THAT SAT STILL (the paid history's first fair spread = ESPN's close) | DEAD | NFL dog ATS +2.1% on 234 (train +18.8% / held -11.7%); the small favorite on a still line -29.3% on 49 NFL / -18.4% on 57 college - too few |

## S2 - beat up on the glass, on a neutral floor (s_today.py s2 -> s_follow.py s2)

The read: a Division I team's rebound margin in its LAST game (a D1 game, inside 8 days), the team box's
totalRebounds. The season-long glass is built (the dog slot, the stack); one game as a spot had never been read.

| on a NEUTRAL floor, against the spread, by the last game's rebound margin | n | ATS | train | held |
|---|---|---|---|---|
| -18 or worse | 64 | +10.5% | +33.6% | -9.8% |
| -12..-17 | 254 | -24.8% | -22.7% (0 of 3) | -26.9% (-23.6 / -8.5 / -58.5) |
| **-12 or worse (the cell)** | 318 | **-17.7%** | -11.8% (0 of 3) | -23.3% (-24 / -12 / -41) |
| -6..-11 | 550 | -3.4% | -6.2% | +0.3% |
| -5..+5 | 1,870 | -0.9% | +1.2% | -3.5% |
| +6..+11 | 773 | -2.2% | -3.3% | -0.9% |
| +12 or more | 592 | -12.4% | -21.1% | -2.7% |
| every neutral side with a last-game box | 4,103 | -4.4% | -4.7% | -4.1% |
| the side ACROSS a -12 team (itself not one) | 281 | **+11.7%** | +6.4% (3 of 3) | +16.9% (+17.9 / +4.0 / +38.1) |
| the same -12..-17 team on a HOME floor | 1,180 | -5.0% | -1.1% | -9.8% |
| ... on a ROAD floor | 1,274 | -5.7% | -6.5% | -4.7% |

Placebo against neutral sides: 6 of 2,000. Back within 2 days -22.4% on 133 (every neutral side back within 2 days
-5.2%), 3+ days later -14.3% on 185. Lost that game -16.2% on 228 (every neutral side off a loss -6.4%; placebo 98),
won it -21.4% on 90.

**Why a lead and not a stack weight.** It lives on a neutral floor only (a home or road floor is at its base); the
dose is no slope (-18 or worse goes the other way on 64, and the team that WON the glass by 12+ is -12.4% too); a
placebo of 6 in 2,000 is what a day of 830 cells produces about twice; and nobody predicted it. What argues for it:
six seasons of six down, the side across up six of six, and it is the event floors the ½u stack plays on in
November-December (Providence, Kennesaw St and Texas St were all neutral-floor games this week).

**Wired (stamps only, from the 11/28 Pacific games):** `sports_glass_night.py` (`margin` / `beat_up`),
`sports.GLASS_NIGHT_FROM` -> `mark_glass_night` stamps `glass_beat_up` on the neutral-floor SPREAD side and
`vs_glass_beat_up` on the side across; tracker tags "college hoops neutral-floor spread side beat up on the glass
last game (fade) (lead)" and "... spread side across a team beat up on the glass last game (lead)"
(`sports_leads.daily_1127_tags`). Nothing on the board reads them. Judge at 40 graded each: the fade side under 46%
covered AND the side across over 54% = bring -/+0.02 in the spread stack to the daily review with the stack play's
replay; either one at a coin = dead.

## S1 - the top line's plus-minus (s_today.py s1 -> s_follow.py s1)

Each game's three forwards with the most ice time and its top two defensemen; their plus-minus a game over the
team's last 10 boxed games, ranked in the league that night. CARRIED = the top line's plus-minus minus the other
forwards'.

| the small favorite -150..-101 by its CARRIED fifth | n | ROI | train | held |
|---|---|---|---|---|
| bottom fifth (the depth is better) | 633 | -0.7% | +5.0% | -7.3% |
| 2nd | 621 | -0.7% | +2.7% | -4.0% |
| 3rd | 619 | -6.5% | -4.6% | -8.6% |
| 4th | 636 | +4.3% | +4.6% | +4.0% |
| **top fifth** | 710 | **-10.5%** | -11.4% (0 of 3) | -9.4% (-5.3 / -18.7 / +20.5 on 33) |
| top fifth, at home | 373 | -13.8% | -12.6% | -15.7% |
| top fifth at ESPN's open | 514 | -9.5% | | base -6.0% |
| every small favorite | 3,219 | -3.0% | -1.1% | -5.1% |

Price-matched placebo 12 of 2,000; the dog across it earns +0.7% on 415. The dog +100..+350 whose TOP PAIR is winning
its minutes (top fifth): -14.5% on 629 against -7.0% (train -14.8% / held -14.2%; price-matched placebo 45; the open
-6.5% on 394 against -2.7%) - and the fifth below it is -14.0% while the middle fifth is +6.6%: no slope there
either.

**A watch, not wired.** Both are steps at one fifth, the open closes most of the favorite's gap, this season's 33
went the other way, and the engine's hockey favorite plays are ½u value plays the 11/17 plan refuses to size. The
live read needs the skater box in the board run (it is not loaded there today) - not built for a watch. If the
Monday review wants a hockey favorite fade, this is the first one to test on the replay board.

## S9 / S8 - the night from three (s_today.py s9 / s8 -> s_follow.py s9)

| the college dog +100..+350 by its LAST game's three-point % (18+ attempts) | n | ROI | train | held |
|---|---|---|---|---|
| 22% or less | 989 | -7.1% | -4.5% | -10.0% |
| 22-30% | 2,072 | -9.8% | -14.7% | -3.2% |
| 30-40% | 3,431 | -7.3% | -10.4% | -3.3% |
| 40-50% | 1,907 | -7.4% | -8.5% | -6.1% |
| 50-60% | 532 | -15.7% | -10.6% | -23.0% |
| 60%+ | 54 | -26.2% | -15.2% | -35.7% |
| every dog with a last-game box | 11,767 | -7.7% | -9.4% | -5.3% |

The 50%+ dog: -16.7% on 586, the long ones carry it (+151..+350 -25.7% on 341; +100..+150 -4.2% on 245); a team
shooting 36%+ on the year -27.5% on 244, under 36% -6.5% on 323; the favorite across earns -0.1%; price-matched
placebo 104 of 2,000 - over the 5% line. A watch: the built three-point-luck read already fades the season's lucky
shooters, and one night adds a step, not a slope. NBA: the team off a hot night against the spread -10.5% on 617
(train -10.4% / held -10.6%; placebo 93), playing the next day -19.1% on 111; no NBA spread play exists to weigh it
on. A side off a cold night: the over +4.9% on 473 (train +3.4% / held +7.3%), the under -13.9% - a fade of the
under, not a bet on the over.

## S3 - the conference title game (s_today.py s3)

FBS vs FBS on championship weekend (the first Saturday of December, the Thursday before through that night; never
Army-Navy), 52 priced games 2018-25. The under +17.1% (2022 -13.6 / 2023 +27.1 / 2024 -4.5 / 2025 +90.4), the over
-26.7%; favorites -16.7% on the moneyline and -8.5% against the spread (a field goal or less: -41.4% on 13; 10+:
+46.0% on 13); on a campus the home side +14.1% on 20; the team that lost the first meeting 0.0% ATS on 23. Fifty-two
games and one big season - a watch for the Monday review, no football total is played.

## Files

`s_today.py` (S1-S10), `s_follow.py` (the controls: s1 / s2 / s9), `core.py` / `lib.py` / `h.py` (the cell machinery,
copied from daily_1126), `digest.py`, `view.py`, `seen.py` (the repeat check), `cols.py` / `peek.py` / `peek2.py`
(what the files hold), `yday.py` - `yday4.py` (yesterday's pick, the game, the card), `lead_tracker.py`, `*_out.txt`.
Tests: `test_daily_1127_a_count_over_games_is_never_price_math`,
`test_daily_1127_a_season_line_is_not_said_of_a_team_that_is_not_that_team_any_more`,
`test_daily_1127_beat_up_on_the_glass_on_a_neutral_floor_is_a_tracker_lead_and_moves_nothing`.
