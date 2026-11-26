# 11/26 daily studies (Thanksgiving)

The owner's daily routine: yesterday's picks, the lead tracker and ten NEW studies (the board check was done by the
operating manager: Chiefs +130 ½u, the floor).

**In one line:** yesterday went 1-2 (-2.04u) and beat the close on 2 of 3; no pick bug - ONE record gap fixed at the
root (a spread play had no closing line on the audit, and a spread whose number moved was on no record at all); of the
ten studies NOTHING clears the five checks - no new weight; ONE tracker lead from the 11/27 games (the hockey dog with
top-fifth special teams), one watch, the rest dead. **No posted pick, price or size changed.**

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead);
every rate league-relative (the top / bottom fifth of the league's current values that night). Line-score studies
2018-26 (train 2018-21 / held 2022-26); team-box / player-box studies 2021-26 (train 2021-23 / held 2024-26); each
held season shown apart in the `*_out.txt` files. Placebo = 2,000 random same-size sets from the cell's own pool; the
follow-ups are PRICE-MATCHED (the same number of sides out of each 50-cent price bin). Second prices: ESPN's open
(2023-26) and the paid football history's first fair spread - read, never pulled. **735 cells were cut - about 37
clear |z| 2 by luck, and a placebo of 3 in 2,000 turns up by luck about once on a day like this.**
`python results/studies/daily_1126/digest.py <file>` prints the cells 5+ points off their base;
`view.py <file>` prints one short line a cell.

**Not re-run (checked first):** everything in the 11/25 and earlier lists. The quarter family had the NBA 2nd / 4th,
the NHL 2nd / 3rd period, football's 3rd / 4th and the hoops halves (11/20-11/25) - today's are the FIRST quarter
(football, NBA) and football's second, never read. **NHL special teams and faceoffs were never run on data:** the 10/1
study was set aside ("no power-play data in the box scores anyway") and every later list carried them as done - the
team box holds powerPlayGoals / powerPlayOpportunities / faceoffPercent / shortHandedGoals now, read here for the
first time. Also new: the college player box's assists and rebounds BY MAN, the skater box's goals by position,
football's second passer in one game. Ideas dropped because they were answered before: total streaks, a team's own
free-throw shooting, the run-heavy side, lineup churn, the in-state neutral floor, spread juice shading, bench /
minutes spread, the look-ahead / letdown, third downs / red zone / possession.

## 1. Yesterday (11/25): 1-2, -2.04u

| pick | result | how | the close |
|---|---|---|---|
| ⭐ Kennesaw St +105 2u (dog slot, read 5) | LOST 91-77 to Charleston (neutral, Cancun) | down 46-36 at the half; Charleston shot 52%, 54 points in the paint, led 90% of the game | opened -102, closed +102 - beat it |
| Providence +2.5 (-115) ½u (spread stack +0.05) | LOST 85-82 to BYU (neutral, Maui) | 43-43 at the half, 9 lead changes; BYU hit 17 of 38 threes | closed +2.5 (-112) - same number, the close had the better juice |
| Texas St -26.5 (-108) ½u (spread stack +0.05, posted 10:32 AM PT) | WON 97-70 vs Alcorn St (neutral, Ruston) | only 50-45 at the half, then 47-25 | closed -27.5 (-112) - beat it by a full point, and that point was the win |

Pick audit: no flags. Card check: no catches. The brief had Providence at +3.5 - the pick file, the card and the
stack stamp all say +2.5 (a 3-point loss; +3.5 would have cashed).

**Why 2u on Kennesaw St.** The dog slot's read was 5.0 = the study weights 3 (the glass: +12 rebounds a game on
Charleston; the favorite lost its last) + the ratings 2 (the efficiency read had Kennesaw the better team on a neutral
floor, 57.8% against the 46.8% no-vig price). A read of 5+ is the slot's 2u (the 11/17 size: 26-19 +35.6%); it was
the board's biggest bet, so it carried the ⭐ at its own size. What happened: the glass never showed (41-40
Charleston), Kennesaw shot 8 of 34 from three and turned it over 18 times, and Tavari Johnson scored 32 on 13 of 19.
The price agreed with us a little (it closed 3 cents shorter). A fair bet that lost by 14 - no bad input, no missed
man (Charleston's E. Ellis was out, as the card said).

**The two stack plays.** Both stood on "their top scorer sat their last game" (+0.03). BYU's Robert Wright III (23.8 a
game) sat again - the read was right and the market knew (BYU opened -205, closed -142); BYU made 17 threes anyway.
Alcorn St's Trey Thomas sat the day before and came BACK: 33 minutes, 24 points - and Texas St still covered by half a
point. That asked a question (S1 below): is a man who sat only yesterday's game different? He is MORE likely out, not
less (he played the next night 30% of the time, against 46% when the game he missed was 2-4 days back) - the built
read stands.

**The gap, fixed (with a test).** The pick audit wrote a closing line for moneylines only, so the board's most common
play - the ½u spread stack - never had one; and the close record keeps a spread only when the number never moved, so
Texas St (-26.5 -> -27.5) was on no record at all. Now `sports_audit.spread_clv_line` says the closing NUMBER first
("Texas St -26.5 (-108) posted, closed -27.5 (-112) - beat the close by 1 point"), the juice only on the same number,
and `clv_record.json` carries `spreads_moved` (points of spread, its own list - the win-% summaries are untouched).
On the live file: three spread plays moved, all three our way by a point (Niagara, Washington, Texas St), all three
won. Report only. On the way: the 11/25 neutral-site test sat BELOW the test runner in `sports_test.py` and never ran
- moved above it (it passes).

## 2. The lead tracker (lead_tracker.py)

Nothing raised, nothing cut. No tag at 100+ graded is clear and steady (the biggest: money 10+ over tickets -0.4% on
554, reverse line move -0.7% on 327, 70%+ of tickets -2.1% on 301, lucky from three (fade) 116-60 +7.9% on 176 with
its dogs carrying it). The built stack weight's own record - the spread side across a three-lucky team / a top scorer
out - went 19-10 since yesterday and is 84-83 -4.0% on 167 (z -0.5): back to even, the stack play's quit rule stays
its judge. Loud and small: the 4-5 nights' rest spread side 22-32 on 54, the NBA dog at a score of -4 or less 11-35
on 46, the tune-up spread side 22-9 on 31 (the built weight doing its job).

## 3. The ten studies

| # | study | verdict | the number |
|---|---|---|---|
| S1 | college hoops: the TOP SCORER WHO SAT, by how long ago the game he missed was (asked by the look-back) | DEAD (the built read stands) | the side across him ATS +1.4% on 1,932 vs -4.5% at any gap (2-4 days +1.0% on 1,233, 5+ days +0.7% on 636); "yesterday" is 63 sides in six seasons (+18.3%, train +40% / held -1.5%) |
| S2 | football: the FIRST-QUARTER team | DEAD | college on the road ATS -12.4% on 749 (placebo 14) - but on FBS-vs-FBS games only -8.1% on 517 (placebo 222) and the THIRD quarter does the same (-10.9%): a good team laying a big road number, not the first quarter; NFL at home -13.2% on 311 (placebo 231) |
| S3 | football: the SECOND-QUARTER team (the points before the half) | DEAD | college bottom-fifth small favorite -21.1% on 129 (placebo 62); NFL bottom-fifth home dog +14.1% on 183 (train +25.4% / held +5.0%) |
| S4 | NBA: the FIRST-QUARTER team | DEAD | top-fifth dog -0.7% on 723 vs -4.5%; small favorite +0.9% on 475 vs -5.5% (placebo 90); slow starter vs fast starter dog -13.7% on 280 (placebo 242) |
| S5 | NHL: SPECIAL TEAMS (power play + penalty kill - the team box, first read) | **LEAD (tracker, from 11/27)** | the top-fifth dog **-13.7% on 687** vs -7.0% (train -16.2% / held -11.6%, same-price placebo 63 of 2,000); a step at the top fifth only; the open -6.5% on 370 vs -2.8% |
| S6 | NHL: the FACEOFF team (first read) | DEAD | top-fifth dog -8.3% on 839 vs -7.0%; bottom-fifth dog -4.5% on 1,281 (train -11.1% / held +2.6%); top vs bottom small favorite -10.0% on 155 (train +1.1% / held -19.3%) |
| S7 | NHL: the BLUE LINE THAT SCORES (defensemen's share of the goals / shots) | DEAD | D-scores dog -9.7% on 1,096 vs -7.0% (train -13.6% / held -5.2%); D-shoots dog -4.7% on 893 |
| S8 | college hoops: the POINT-GUARD TEAM (top assist man's share) | DEAD | ATS -4.3% on 6,837 vs -4.5%; dog -7.5% on 2,103 vs -7.1%; at home as a small favorite -9.5% on 412 vs -4.1% |
| S9 | college hoops: the ONE-MAN GLASS (top rebounder's share) | DEAD | ATS -2.6% on 7,263 (train -6.0% / held +2.0% - flips); dog -7.3% on 2,360 vs -7.1%; the gang-rebounding dog on a neutral floor -17.3% on 259 (placebo 213) |
| S10 | football: the TWO-QUARTERBACK game (two men threw 8+ passes last game) | WATCH (college) | college dog +15.3% on 239 vs -0.3% (train +7.4% / held +21.4%: +8 / -24 / +57; placebo 76); NFL ATS -15.3% on 131 (train -26.9% / held +0.7%) |

## S1 - the top scorer who sat, by the gap (s_today.py s1)

sports_ncaab_roster's own read (the leader in points a game, 3+ games at 20+ minutes, 0 minutes in the team's last
game, a non-D1 tune-up not counted), with the days since that game.

| did he play tonight (ex post) | missed only that game | missed 2+ running |
|---|---|---|
| the game he missed was yesterday | 11 of 37 (30%) | 1 of 62 (2%) |
| 2-4 days ago | 312 of 678 (46%) | 192 of 1,201 (16%) |
| 5+ days ago | 193 of 315 (61%) | 181 of 650 (28%) |

| the spread side ACROSS him | n | ATS | train | held |
|---|---|---|---|---|
| any gap | 1,932 | +1.4% | -0.8% | +4.1% |
| yesterday | 63 | +18.3% | +40.0% on 30 | -1.5% on 33 |
| 2-4 days ago | 1,233 | +1.0% | -5.0% | +8.5% |
| 5+ days ago | 636 | +0.7% | +4.1% | -3.4% |
| every spread side | 40,734 | -4.5% | -4.6% | -4.4% |

His own team: ATS -10.3% on 1,932, the dog -18.6% on 760 (placebo 6 of 2,000) - the built fade, as built. No cut of
the gap earns a different weight; a man who sat yesterday is the LEAST likely to be back. Nothing changed.

## S5 - NHL special teams (s_today.py s5 -> s_follow.py s5)

The read: power-play goals / chances plus (1 - the opponents' power-play goals / chances), season to date, 10+ boxed
games and 20+ chances each way, ranked in the league that night.

| the dog +100..+350, by its special-teams fifth | n | ROI | train | held |
|---|---|---|---|---|
| bottom fifth | 1,546 | -8.7% | -9.4% | -7.5% |
| 2nd | 1,051 | -4.0% | -8.6% | +2.4% |
| 3rd | 926 | -4.3% | -10.8% | +4.4% |
| 4th | 721 | -5.1% | -9.3% | -0.7% |
| **top fifth** | 687 | **-13.7%** | -16.2% (0 of 3) | -11.6% (-18.1 / -9.5 / +0.1) |
| every dog | 4,931 | -7.0% | -10.3% | -2.9% |
| the top fifth at ESPN's open 2023-26 | 370 | -6.5% | | base -2.8% |
| the favorite across a top-fifth dog | 974 | +1.9% | +3.2% (3 of 3) | +0.6% |

Price-matched placebo: 63 of 2,000. +100..+150 -12.4% on 523 (both halves), +151..+350 -18.1% on 164. The KILL alone
does the same at the close (top-fifth dog -13.3% on 799, placebo 72) and nothing at the open (-3.8% on 446); the
power play alone is nothing (top fifth -3.0% on 701). Short-handed goals: nothing that holds (the dog that gives them
up -10.2% on 1,369, train -15.0% / held -3.7%).

**Why a lead and not a weight.** It is a step, not a slope (only the top fifth); the open halves the gap; the
favorite across is +1.9%; the placebo is 3% on a day 735 cells were read; and this season's 44 are flat.

**Wired (a stamp only, from the 11/27 Pacific games):** `sports_puck.states` / `special` (the read),
`sports.NHL_SPECIAL_FROM` -> `mark_nhl_puck` stamps `special_top`, tracker tag "NHL dog with top-fifth special teams
(fade) (lead)" (`sports_leads.daily_1126_tags`). Nothing on the board reads it. Judge at 60 graded: -5% or worse =
bring a -1 on the hockey dog score to the daily review; over +5% = dead.

## S2 - the first-quarter team (s_today.py s2nfl / s2ncaaf -> s_follow.py s2)

| college football, the road side against the spread | n | ATS | train | held |
|---|---|---|---|---|
| first-quarter top fifth | 749 | -12.4% | -13.4% | -11.8% (5 of 5 down) |
| ... the same read on FBS-vs-FBS games only | 517 | -8.1% | -2.0% | -10.6% (placebo 222) |
| ... top fifth by its THIRD quarter instead | 743 | -10.9% | -8.3% | -12.3% |
| ... at the paid history's first fair spread | 374 | -10.2% | | |
| the home side across it | 749 | +3.0% | +4.4% | +2.3% |
| every road side | 3,792 | -4.9% | -6.2% | -4.2% |

The big number is half lower-division first quarters and the rest is any good team laying points on the road (the
top fifth LAYING points -14.2% on 516) - the built road-favorite fades' crowd; betting against it earns 3%. NFL: the
top fifth at home -13.2% on 311 against -7.3% for every home side (placebo 231), -3.6% at the first fair spread.

## Files

`s_today.py` (S1-S10), `s_follow.py` (the controls: s2 / s5), `core.py` / `lib.py` / `h.py` (the cell machinery,
copied from daily_1125), `digest.py`, `view.py`, `lead_tracker.py`, `*_out.txt`. Tests:
`test_daily_1126_a_spread_pick_gets_its_close_line_and_a_moved_number_is_on_the_record`,
`test_daily_1126_the_hockey_dog_with_top_fifth_special_teams_is_a_tracker_lead_and_moves_nothing`.
