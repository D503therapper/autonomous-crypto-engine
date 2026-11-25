# 11/25 daily studies

The owner's daily routine: yesterday's picks, the lead tracker and ten NEW studies (the board check was done by the
operating manager: Kennesaw St +105 2u and the Providence spread stack play ½u).

**In one line:** yesterday went 2-1 (+2.01u) and beat the close 3 of 3; ONE real bug fixed at the root (a day-to-day
NBA key man read as "playing" off a bare word in ESPN's note - the Magic +114 posted with Cade Cunningham day-to-day);
of the ten studies NOTHING clears the five checks - no new weight; ONE tracker lead from the 11/26 games (the college
hoops second-half team as a road favorite), four watches, the rest dead. **No posted pick, price or size changed.**

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead);
every rate league-relative (the top / bottom fifth of the league's current values that night). Line-score / schedule
studies 2018-26 (train 2018-21 / held 2022-26); team-box / player-box studies 2021-26 (train 2021-23 / held 2024-26);
each held season shown apart in the `*_out.txt` files. Placebo = 2,000 random same-size sets from the cell's own pool;
the follow-ups are PRICE-MATCHED (the same number of sides out of each 50-cent price bin). Second prices: ESPN's open
(2023-26) and the paid football history's first fair look - read, never pulled. **737 cells were cut - about 37 clear
|z| 2 by luck, and a placebo of 3 in 2,000 turns up by luck about once on a day like this.**
`python results/studies/daily_1125/digest.py <file>` prints the cells 5+ points off their base;
`view.py <file>` prints one short line a cell.

**Not re-run (checked first):** everything in the 11/24 and earlier lists; the brief's Thanksgiving list (short weeks
and Thursday 11/12 b1, the holidays 10/31, rivalry week 10/31 + 11/1 + 11/21, the game after an event 11/3); and the
ones today's first ideas ran into - the defense's snap load, the opponents' free-throw luck, the star's 40-point game,
the game after a streak ends, the 3rd straight road game, the game after an international game, the pulled goalie,
Canadian teams, the unbeaten / winless start, the dome team in the cold, the home streak.

## 1. Yesterday (11/24): 2-1, +2.01u

| pick | result | how | the close |
|---|---|---|---|
| ⭐ Illinois St +100 2u (dog slot, read 4) | WON 79-67 vs Tulsa (neutral) | 37-35 at the half, 42-32 after it | opened -115, closed -108 - beat it |
| Campbell +102 ½u (dog slot's road dog, read 3) | WON 70-66 at Coastal | up 32-21 at the half, lost the second half 45-38, held on | opened +124, closed -102 - beat it |
| Magic +114 ½u (NBA floor, score 0.35) | LOST 104-86 vs the Pistons | 22-16 after one, then a 32-14 second quarter | closed -141 after Cunningham was ruled out - beat it by 12 points |

Pick audit: no flags. Card check: four catches - one of them ("Tulsa's last game ended 69-66 - the games say L 99-102 vs
Santa Clara") was the checker reading the wrong team while the leg sat on the flipped side; with 11/24's side fix
today's checker passes the line. Three fair bets at better numbers than the close.

**The bug (fixed, with a test).** The Magic posted with Cade Cunningham - the Pistons' top scorer - day-to-day. A
day-to-day key man holds an NBA pick unless he plays through the tag (he doesn't: 10 of 35) or ESPN's note says he
plays; that note test was a bare substring - "available" sits inside "unavailable", "will play" inside "unclear
whether he will play". Now the phrase must be whole words in an un-hedged clause (`sports_nba_roster.says_playing`),
and the post's log line + the leg's `through` say WHY a day-to-day key man did not hold (`sports.nba_through`). The
note itself is not stored, so the exact words can't be shown - it is the only way through the hold for him.

## 2. The lead tracker (lead_tracker.py)

Nothing raised, nothing cut. No tag at 100+ graded is clear and steady (the biggest: money 10+ over tickets -0.3% on
542, reverse line move -0.2% on 315, 70%+ of tickets -2.4% on 291). The built stack weight's own record - the spread
side across a three-lucky team / a top scorer out - is 65-73 -10.1% on 138 (z -1.2): the wrong side of even for a
second day, still inside luck; the stack play's quit rule stays its judge.

## 3. The ten studies

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NBA: the PARTY CITY (a visitor's free night in Miami / LA / New York / New Orleans) | DEAD | its dog +2.3% on 641 vs -4.3% for a free night anywhere else - no hangover; small favorite -11.2% on 208 (placebo 112) |
| S2 | NHL: the PARTY CITY (Vegas / Nashville / Sunrise / Tampa / LA / New York / Montreal / Tempe) | DEAD | dog -4.2% on 1,002 vs -2.2%; small favorite -7.2% on 400 (train +8.9% / held -19.5% - flips) |
| S3 | football: the COLD SHOCK (20+ F under the team's own Nov-Jan home norm, 40 F or colder) | WATCH (NFL) | NFL ATS -15.3% on 147 (placebo 164), outdoor teams -25.7% on 75; college -2.4% on 109 |
| S4 | football: the ONE-MAN PASSING GAME (top receiver's share of the yards) | WATCH (NFL) | NFL "spreads it" dog +11.8% on 210 (placebo 23), one-man dog -21.2% on 157 (placebo 134) - the middle fifths are no line; college nothing |
| S5 | football: the WORKHORSE BACK / the committee | WATCH (NFL) | NFL committee dog -26.1% on 214 (train -24.7% / held -27.5%, same-price placebo 15, first fair -22.5%) - 2024 carries it; 25+ carries last week ATS -0.3% on 161 |
| S6 | college football: off a NON-FBS TUNE-UP vs a team off an FBS game | DEAD | ATS -3.6% on 429 vs -4.6% (train +5.5% / held -7.1%) |
| S7 | football: last week's TURNOVER BATTLE (by 3+) | DEAD | NFL won it ATS +0.5% on 208, lost it +2.0% on 210; college won it ATS -5.0% on 660 (base -4.7%) |
| S8 | college hoops: the ONE-MAN TEAM (top scorer's share of the points) | DEAD | ATS -2.9% on 6,828, dog -6.7% on 2,325 (base -7.2%); the balanced team vs one ATS -10.0% on 1,305 but the other side only +0.9% |
| S9 | college hoops: the SECOND-HALF TEAM (2nd-half margin minus 1st-half margin) | **LEAD (tracker, from 11/26)** | as a ROAD favorite past -150: -9.4% on 730 vs -3.2% (placebo 5); the home side getting points across it **ATS +6.8% on 1,122** vs -3.0% (train +3.0% / held +10.3%, 7 of 8 seasons up, placebo 0 of 2,000); the home dog +4.7% on 915 vs -5.9% |
| S10 | college hoops + NBA: the GUARD-HEAVY TEAM (guards' share of the minutes) | WATCH (college) | guard-heavy road dog +0.7% on 1,339 vs -7.6% (placebo 14) - a break-even, no dose; big road small favorite -15.0% on 362 (placebo 24); NBA nothing |

## S9 - the second-half team on the road (s_today.py s9 -> s_follow.py s9 / s9c)

The read: a team's second-half margin minus its first-half margin a game (each half capped at 20), season to date,
5+ line scores, ranked in the league that night; the top fifth trails or sits level at the break and wins after it.

| cell (true road / home floors, 2018-26) | n | ROI | train | held | placebo |
|---|---|---|---|---|---|
| the road favorite past -150 (top fifth) | 730 | -9.4% | -5.8% | -13.1% (4 of 4 down) | 5 / 2,000 same-price |
| every road favorite past -150 | 4,831 | -3.2% | -3.4% | -3.1% | |
| the home dog +100..+350 across it | 915 | +4.7% | +2.5% | +6.9% | 5 / 2,000 same-price |
| ... +100..+199 | 679 | +9.1% | +12.1% (4/4) | +6.1% (4/4) | |
| ... +200..+350 | 236 | -7.9% | -22.3% | +9.4% | |
| every home dog | 5,393 | -5.9% | -5.6% | -6.1% | |
| ... at ESPN's open 2023-26 | 326 | +3.3% | | | base -8.6% |
| ATS: the home side getting points across it | 1,122 | +6.8% | +3.0% (3/4) | +10.3% (4/4) | 0 / 2,000 |
| ATS: every home side getting points | 6,799 | -3.0% | -3.0% | -3.1% | |

**Why a lead and not a weight.** The dose is broken: the home dog across the road team's read by fifth runs -9.6 /
-2.3 / -7.8 / -12.9 / +4.7 - only the top fifth, and the fifth under it is the worst (inside the top fifth it does
climb: 80th-90th ATS +4.2%, top tenth +9.9%). A second definition fails: the same read over a team's LAST 10 games
is flat (ATS +0.5% on 1,172; the home dog -0.3% on 974). A second-half team laying points at HOME is the base (-6.3%
on 2,607 vs -5.2%) and on a neutral floor nothing - a team the books over-rate would be over-rated everywhere. This
season is 3-4 games. And 737 cells were read today.

**Wired (stamps only, from the 11/26 Pacific games):** `sports_second_half.py` (the read), `sports.HALVES_FROM` /
`mark_halves` (second_half_road / vs_second_half_road - nothing on the board reads them), three tracker tags in
`sports_leads.daily_1125_tags`: "college hoops home spread side getting points across a second-half road team (lead)",
"college hoops home dog across a second-half road favorite (lead)", "college hoops second-half road team laying points
(fade) (lead)". Judge at 60 graded each: the home side covering 55%+ and the dog over +5% = bring a ±0.02 spread-stack
weight / a +1 dog-read fact to the daily review; either under even = dead.

## Files

`s_today.py` (S1-S10), `s_follow.py` (the controls), `core.py` / `lib.py` / `h.py` (the cell machinery, copied from
daily_1124), `digest.py`, `view.py`, `lead_tracker.py`, `*_out.txt`. Tests: `test_daily_1125_a_note_says_he_plays_only_in_whole_words_and_the_post_says_why_a_key_man_did_not_hold`,
`test_daily_1125_the_second_half_road_team_is_a_tracker_lead_and_moves_nothing`.
