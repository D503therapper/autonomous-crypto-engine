# 11/22 daily studies

The owner's daily routine: the board check, yesterday's picks, the lead tracker and ten NEW studies. Today's ten read
columns of ESPN's box scores that no study had opened - the paint, points off turnovers, fast-break points, blocked
shots, the skaters' positions, passes defended, penalty first downs - across the NBA, college hoops, the NHL, the NFL
and college football.

**In one line:** one thing clears - the NBA team that SHUTS THE PAINT is underpriced (its dog +8.5% on 707, the dog
facing it -15.5% on 747, both halves) - wired as a HALF weight (+1 / -1 on the NBA dog score) from the 11/23 games with
two tracker tags as its judge; one college football watch (the defense that drops its interceptions); eight dead. Two
card bugs fixed at the root (a celebrity's comment as "camp talk"; a non-D1 tune-up counted as scoreboard form). No
posted pick, price or size changed.

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead). The
team box starts in 2021: train 2021-23 / held out 2024 / 2025 / 2026, each held season shown apart. Placebo = 2,000
random same-size sets from the cell's own pool. **554 cells were cut - about 28 clear |z| 2 by luck, and a placebo of
2 in 2,000 shows up by luck about once in two days like this one.** The paid odds history was not re-read except as
the NBA paint read's second price (the 2020-23 morning look).

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NBA: THE PAINT - the share of a team's points scored / given up in the paint (team box `pointsInPaint`) | **BUILT - a half weight from 11/23** | the team in the league's best fifth at keeping points out of the paint: its DOG +100..+350 **+8.5% on 707** vs -5.3% for every dog (train +4.5%, 3 of 3 seasons / held +16.7%: 2024 +20.5, 2025 +8.8; placebo 2 of 2,000; ESPN's open +7.3% on 385 vs -8.0%; the paid morning +3.3% on 322 vs -7.9%); the dog ACROSS one **-15.5% on 747** (train -19.0%, 0 of 3 / held -10.5%; placebo 20); the soft-paint team ATS -7.8% on 2,149 (every season down, placebo 71) |
| S2 | college hoops: THE PAINT (D1 games only) | DEAD | top fifth gives up the paint: ATS -5.4% on 7,257 vs -4.5%, dog -7.7% vs -7.3%; the inside team vs a soft paint ATS -0.8% on 1,899 (train +3.1% / held -6.0% - flips); ESPN's college paint column drifts (the 2021-23 bottom fifth holds 70 held rows) |
| S3 | points off turnovers (`turnoverPoints`), NBA + college hoops | DEAD (a watch) | NBA top-fifth margin: dog -8.9% on 1,136 vs -5.6% (train -12.9% / held -5.1%); college top-fifth margin as a SMALL favorite +3.3% on 772 vs -4.1% (train +5.4%, 3 of 3 / held +0.3%; placebo 12) - fades to nothing held out |
| S4 | the transition matchup (`fastBreakPoints`) - a running team vs a team that gives up the break | DEAD | NBA: ATS -4.3% on 1,499 (the base), small favorite -12.6% on 206 (placebo 240); the total: over +0.7% on 1,323 (train +6.3% / held -0.8%); college: ATS -5.0% on 3,822, the over -5.1% |
| S5 | NHL: shot ATTEMPTS (shots on net + the other side's blocks) vs the built shots-on-net share | DEAD (the built read confirmed) | bottom-fifth attempt share dog -12.5% on 1,559 (train -14.5% / held -9.8%) vs the built on-net read -11.8% on 1,617 (-14.6% / -8.2%) - the same dogs; the two disagree on 82 / 118 sides, too few to read |
| S6 | NHL: who shoots - the defensemen's share of a team's shots (skater box) | DEAD | top-fifth D share: dog -4.3% on 929 (train -10.7% / held +4.9%); out-shooting on point shots dog +6.1% on 120 (placebo 243); out-shooting with forwards dog -17.1% on 230 (placebo 210) |
| S7 | football: passes defended vs interceptions (the defense that is "due") | **WATCH (college)**, DEAD (NFL) | college: the LUCKY defense (top-fifth interceptions on few deflections) ATS **-11.6% on 565** (train -8.9% / held -12.7%: -13.8 / -14.1 / -11.5; placebo 86); the DUE defense as a small favorite +22.5% on 102 (train +16.2% / held +29.3%, placebo 1), ATS +2.4% on 926 (placebo 11). NFL: due ATS -11.6% on 245 - the wrong way |
| S8 | football: the big-play passing offense (yards per completion) | DEAD (a watch) | NFL dink-and-dunk (bottom fifth) ATS -10.4% on 453 (train -7.3% / held -14.3%, placebo 124); big-play dog -1.2% on 124; college big-play small favorite -12.7% on 147 (placebo 263), dink-and-dunk dog +8.9% on 412 (train +20.8% / held +1.5%) |
| S9 | NFL: first downs by penalty (the flags' gifts) | DEAD | top-fifth margin ATS -7.4% on 412 (train -5.5% / held -9.9%), dog -10.5% on 179 vs -8.0%; bottom fifth dog -18.2% on 179 (train -33.4% / held +2.4% - flips) |
| S10 | football: the run-game mismatch (yards per rush vs yards per rush allowed) | DEAD | NFL top run game vs a bottom run defense: ATS -16.8% on 94 (the wrong way, too few); college: ATS -3.8% on 192, the dog +48.1% on 28 (too few); bad run game vs bad run defense ATS -17.6% on 236 (placebo 45, no reason behind it) |

## S1 - the NBA team that shuts the paint (s_hoops.py -> s1b_nba_paint.py -> s1c_nba_paint_controls.py)

The read: of the points a team's opponents score, the share that comes in the paint - season to date, 10+ box games,
the team's place among the league's current values that night (20+ teams read). Bottom fifth = "shuts the paint",
top fifth = "soft paint". Fixed 2021-23 cut points drift (the paint's share of scoring fell as threes rose), so the
live rule is the league-relative one.

| cell (league-relative) | all | train 2021-23 | held 2024-26 | placebo vs its base |
|---|---|---|---|---|
| every dog +100..+350 (base) | -5.3% on 3,953 | -5.8% | -4.6% | |
| **the dog that shuts the paint** | **+8.5% on 707** | +4.5% on 476 (3 of 3 seasons) | +16.7% on 231 (2024 +20.5, 2025 +8.8, 2026 +43.0 on 6) | 2 of 2,000 |
| ... at +100..+199 | +10.1% on 464 | +6.9% | +16.7% | 1 of 2,000 |
| ... at ESPN's open (2023-26) | +7.3% on 385 (base -8.0%) | 2023 -1.3% | +13.7% | |
| ... at the paid morning look (2021-22 seasons) | +3.3% on 322 (base -7.9%) | 2 of 2 seasons up | - | |
| **the dog ACROSS a paint-shutting team** | **-15.5% on 747** | -19.0% on 438 (0 of 3) | -10.5% on 309 (2024 -9.9, 2025 -14.0, 2026 +21.9 on 14) | 20 of 2,000 |
| the favorite past -150 across one | -8.6% on 532 (base -3.1%) | -7.8% | -10.5% | |
| the soft-paint team, ATS | -7.8% on 2,149 (base -4.4%) | -7.2% (0 of 3) | -8.6% (-10.1 / -7.2 / -7.9) | 71 of 2,000 |
| the soft-paint small favorite | -12.8% on 272 (base -5.8%) | -14.0% | -11.1% | 152 of 2,000 |

The controls (s1c): it is not "a good defense" by another name - the dog in the best fifth of POINTS ALLOWED is -9.4%
on 511 (nothing), and the paint dog whose team is NOT a best-fifth defense is +7.9% on 593 (placebo 12). It is not
three-point luck - a team whose opponents are coldest from three: ATS -3.7% (the base). Part of the "across" fade IS
plain defense (the dog across a best-fifth defense -11.3% on 1,063).

**Honest:** the dog's z against zero is 1.6; its HOME dogs carry it (+20.3% on 259 at home, +1.7% on 448 on the road);
Oct-Dec +19.3% on 233, Jan-Apr +3.2% on 474; 2026 is 6 bets; the dose is flat (bottom tenth +10.3%, 10th-20th +7.0%);
554 cells were read today. The five checks: fair (the close, the season before tonight) / both halves / 5 of 5 full
seasons / this season too thin to read / second reads = ESPN's open, the paid morning, the mirror cell, the controls.

**Wired at HALF the usual NBA dog weight:** `sports.NBA_PAINT_FROM = "2026-11-23"`, `NBA_PAINT_PTS = 1` - `+1` on the
dog score's study points for an NBA moneyline dog whose team shuts the paint, `-1` for one facing such a team (and not
one itself); inside STUDY_CAP; no favorite read, spread or size moves; unread = 0
(`sports_hoops_style.paint_states / paint_shut`, `sports.mark_nba_paint / nba_paint_pts`). Tracker tags
"NBA dog that shuts the paint" / "NBA dog vs a team that shuts the paint (fade)" judge it at 60 graded each. Tonight's
six: Thunder, Celtics, Magic, Lakers, Pacers, Bucks. (Today's posted Wizards +170 ½u floor play faces the Magic - the
weight starts tomorrow and never touches a posted pick.)

## S7 - the college defense that drops its interceptions (s_rest.py ncaaf)

Passes defended a game from the player box, interceptions from the opponents' team box, season to date (4+ box games),
league-relative fifths. LUCKY = top-fifth interceptions on a bottom-fifth share of deflections NOT caught; DUE = the
top fifth of that share with at least a 40th-percentile deflection count. The lucky defense's team ATS -11.6% on 565
in both halves and all three held seasons - the same direction as the 11/21 fumble-luck watch (-11.3% on 724) and the
built interception-luck dog weight. No tag: one regular-season week is left, there is no college spread play to weigh,
and the due small favorite is 102 bets. Re-read in September with the fumble watch, as one "turnover luck" spread read.

## The board check - two bugs fixed at the root

1. **"Camp talk" that was a celebrity's comment.** The Panthers -145 Lock card: `📣 Out of the Ravens' camp this week:
   "Carmelo Anthony calls out Ravens' Humphrey over Baltimore 'criminals' remark"`. The talk tag was read off the
   headline + description and pinned on every team the article touched. Now (`sports_news.camp_talk`): the kind has to
   read off the HEADLINE, the headline names the team, the team isn't the TARGET of somebody else's words, the story
   isn't off the field (a movie, politics, a city's crime) or a league round-up; a filtered headline never hides an
   older true one. Of 71 talk tags in today's file, 61 fail it (the 'Madden' movie, a state attorney general, the
   weekly "trolls" round-ups, game recaps). Test `test_daily_1122_camp_talk_is_the_camp_talking_about_the_game`.
2. **A non-D1 tune-up as form.** The Robert Morris +102 card: "Over their last 3 Robert Morris win by 6 a game (74 for,
   68 against)" - a 94-45 win over Capital (non-D1) and two double-digit losses; on real games it is 62 for, 79
   against. The 11/21 UT Rio Grande and Indiana St cards did the same. The points-lately lines read D1 games only in
   college hoops (`sports_breakdown_v24._real`). Test
   `test_daily_1122_a_tune_up_is_never_form_in_the_points_lately_line`. Breakdown VERSION 81.

## Files

`lib.py` / `h.py` (the shared helpers, cache `~/.cache/d503_daily1122`), `s_hoops.py` (S1-S4), `s1b_nba_paint.py`,
`s1c_nba_paint_controls.py`, `s_rest.py` (S5-S10), `lead_tracker.py`, `view.py`, the `*_out.txt` tables.
