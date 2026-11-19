# 11/19 daily studies

The owner's daily routine: the board check, yesterday's picks, the lead tracker and ten NEW studies - two of them asked
by the 11/19 bug sweep (the NFL East-to-West spot's raw time zones; the altitude weight at a neutral site).

**In one line:** the East-to-West spot now reads the real clock (an Eastern team 3 hours west - the only part of the old
rule that ever paid), three cities the geocoder put on a mountain are fixed (Maui, Vancouver, Santo Domingo), two
tracker leads, nothing new weighed, no pick or size changed.

Prices: nflverse's closes 2006-26 (the offensive-line study's download), the paid football history's first FAIR number
2020-26 (ready_at / fair, no look-ahead), ESPN's close at its own juice for the other leagues, ESPN's open (2023-26)
and the paid NBA / NHL morning as second prices. Train / held-out halves each shown apart; placebo = 2,000 random
same-size sets from the cell's own pool. About 500 cells were cut - about 25 clear |z| 2 by luck.

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NFL East-to-West: which teams did the study mean? | **BUILT (a definition fix)** | Eastern team, 3 clock-hours west: first fair +19.1% on 64 (train +25.0% / held +14.8%), close +15.0% on 163 over 21 seasons. Everything else the raw read let in: first fair -3.1% on 37 (held -64.3%), close +0.4% on 97 |
| S1b | the West Coast road favorite in the East | **BUILT (the same fix)** | Eastern venue +8.7% on 50; Central venue -9.6% on 34 (the raw read took Central venues until the clocks changed) |
| S1c | the same raw read inside the NBA opening-line and totals models | **BUILT (harmless)** | NBA open log loss 0.60070 vs 0.60071, 570 of 592 plays the same; "travel" is in no league's totals fit either way |
| S2 | the altitude weight at a neutral site | **NOT WIRED; a data bug FIXED** | 4 NFL + 12 NBA games ever (Mexico City): the weight's side won 7 of 16. College hoops: 71 of 108 vs 59 expected. Nothing to stand a change on. Found on the way: Maui 1,619 m, Vancouver 1,128 m, Santo Domingo 1,459 m in the venue file |
| S3 | NFL surface / roof (grass team on turf, dome team outdoors) | DEAD (a watch) | grass team on turf ATS -5.3% on 1,287 (both halves, placebo 26 of 2,000) - the live files hold no surface |
| S4 | NFL the defense's snap load last game | DEAD | D 78+ snaps: dog -9.5% on 228 (placebo 544), ATS -3.8% vs -3.1% |
| S5 | NFL the quarterback's career starts | DEAD (a watch) | a new QB vs a 100-start veteran ATS +8.1% on 358 (train +1.9% / held +15.0%); the moneyline nothing |
| S6 | football: the team the market moved to / against week after week | DEAD | NFL dog moved TO 6+ points over 2 games -24.4% on 116; college the opposite, +29.7% on 55 |
| S7 | NHL scoring depth (top 3 scorers' share of the goals) | DEAD | top-heavy dog -6.5%, deep dog -10.6% vs -6.8% (placebo 237) |
| S8 | the week the clocks change, every league | DEAD | NBA road side ATS -13.1% on 394 in the fall week (placebo 91), -3.9% in the spring one |
| S9 | wire to wire (led / trailed at every break last game) | **LEAD** (NHL) | NHL dog off a wire win vs a team that never led: -19.4% on 314, 0 of 9 seasons; built weights out -13.0% on 187 |
| S10 | hoops scoring concentration (top 2 scorers' share) | **LEAD** | the two-scorer dog vs a balanced team: NBA -25.1% on 111, college hoops -15.2% on 378, both halves in both |

## S1 - the East-to-West spot (s1_east_west.py)

The live rule compared two raw wall-clock offsets. The road team's "home offset" was the most common `tzo` of its home
games on file:

- **-4:** Browns, Buccaneers, Colts, Commanders, Dolphins, Falcons, Giants, Jaguars, Jets, Lions, Panthers, Patriots, Steelers
- **-5:** Bears, Bengals, Bills, Eagles, Packers, Ravens, Texans, Titans, Vikings
- **-6:** Broncos, Chiefs, Cowboys, Saints

So "East Coast team" (offset -5 or more) took five Central teams and left three out - by which half of the season had
more home games on file. The venue's offset (-7 or less) was Pacific + Arizona until the clocks changed and Pacific +
Arizona + Denver after.

Road dogs +100..+350, the first fair number (median book, 2020-26; train 2020-22 / held 2023-26):

| cell | all | train | held | seasons up |
|---|---|---|---|---|
| every road dog | -1.0% on 813 | +1.3% | -3.0% | 3 of 7 |
| the live rule | +11.0% on 101 | +33.1% | -9.1% | 4 of 7 |
| KEPT - Eastern team, the venue's clock 3 hours behind | **+19.1% on 64** | +25.0% | +14.8% | 5 of 7 |
| DROPPED - in the live rule, not a 3-hour gap | -3.1% on 37 | +43.5% | **-64.3%** | 1 of 6 |
| Central team at a Pacific venue | -11.6% on 31 | +43.8% | -70.7% | 1 of 6 |

The close, nflverse 2006-26 (train 2006-16 / held 2017-26):

| cell | all | train | held | seasons up |
|---|---|---|---|---|
| every road dog | +1.3% on 2,603 | +3.0% | -0.7% | 12 of 21 |
| the live rule | +9.6% on 260 (z 1.1) | -0.9% | +17.8% | 12 of 21 |
| KEPT | **+15.0% on 163 (z 1.4)** | +4.5% | +23.6% | 13 of 21 |
| DROPPED | +0.4% on 97 | -10.4% | +8.4% | 7 of 21 |
| Central team at a Pacific venue | -7.2% on 92 | +5.4% | -17.4% | 9 of 21 |
| clock gap 2 hours west | -0.4% on 150 | -8.2% | +6.1% | 8 of 21 |
| clock gap 1 hour west | -8.9% on 474 | +6.9% | -26.4% | 9 of 21 |

Honest: at the close over 21 seasons the kept spot is z 1.4 and flat in 2006-16 - it lives from 2017 on. That is the
spot's own judge (its live record), not this study's question. Against the spread the trip is nothing (-1.5%).
By kickoff: 2+ hours west in the late-afternoon window +12.1% on 234, at night -4.3% on 78.

**Wired** (sports_early.EW_STD_FROM = "2026-11-20", by the game's UTC day; None = the raw read): `home_tz_std`,
`east_to_west`, `west_to_east`; the spot scan, sports._dog_more's east_west flag (+3 on the dog score) and
sports.weigh_west_coast_road_fav (+2 points) read them. About 8 plays a season instead of 12; the weight and the ½u
size are unchanged; a posted play keeps everything.

S1b (s1b_west_fav.py): the West road favorite -150..-101 at an Eastern venue +8.7% on 50 (train -45.8% on 17 / held
+36.8% on 33 - a lead, as it was built); at a Central venue -9.6% on 34; the Central piece the raw read took before
the clocks changed -31.8% on 16 (any favorite -25.3% on 42, both halves down).

S1c (s1c_models_std.py): sports_nba_open.TZ_STD / sports_totals.TZ_STD. In the NBA model a team's home offset was the
winter one, so in October and from mid-March every road team read one zone off. Refit both ways walk-forward: log loss
0.60070 raw / 0.60071 standard; plays at ESPN's open 592 / 593, 570 the same (the 22 only-raw 0.0u, the 23
only-standard +5.5u). Totals: "travel" is not a kept factor in the NFL / NBA / NHL / college fits either way. A saved
NBA open model fit on the raw read is refit once on the next live run (no file in this commit).

## S2 - the altitude weight at a neutral site (s2_neutral_altitude.py)

The read's "alt" = each team's climb above its own building, visitors minus home, only at 1,000 m+. At a neutral site
both teams climbed; what is left is the gap between two home elevations. Mexico City 11/22: the 49ers live at 23 m,
the Vikings at 253 m - alt 0.23 km for the Vikings = 1.5 points of win chance on the own read.

| league | true home games in thin air (b on top of the ratings) | neutral, thin air | the weight's side at a neutral site |
|---|---|---|---|
| NFL | 87 games, +0.18 (z 1.2) | 4 games | won 3 of 4 (2.3 expected) |
| NBA | 863, +0.16 (z 2.8) | 12 games | won 4 of 12 (5.9 expected) |
| college football | 576, +0.12 (z 1.6) | 23 games, b -0.99 (z -1.5) | won 11 of 23 (11.6 expected) |
| college hoops | 2,184, +0.24 (z 5.5) | 108 games, b +0.64 (z 2.0) | won 71 of 108 (59.1 expected); two lowland teams 49 of 70 (41.4) |

The pros say nothing (16 games ever). College hoops says the weight's side has done WELL at neutral sites - most
likely the nearer school at a regional site (El Paso, Reno, Salt Lake City, Denver), not the air. Nothing holds a
change in either direction: **not wired**. The label is already off neutral-site cards (the 11/19 sweep).

**The bug found on the way (fixed):** `venues.json` had Maui at 1,619 m (the island's middle - the Maui Invitational
is at sea level; 70 college hoops games read as thin air), Vancouver at 1,128 m (the middle of Vancouver Island -
every Canucks home game since 2016, 445 of them) and Santo Domingo at 1,459 m. `sports_data.VENUE_FIX` corrects them
where the games are read (`load_games`), where the venue file is read (`sports_context.venues`) and where it is
written (`sports_weather.sync` heals the file and the game rows on the next live run). No card ever said "thin air"
in Vancouver (the hockey fit's altitude weight is -0.06, under the named-reason bar; hockey's final read has no
altitude term).

## The leads (tracked only, from the 11/20 games - sports_leads.daily_1119_tags)

- **"NHL dog off a wire-to-wire win vs a team that never led and lost, rested, no 3+ streak, under +220 (lead)"**
  (s9 -> fA_nhl_wire_dog.py): the pair -19.4% on 314 (train -25.3% / held -12.3%, 0 of 9 seasons up, price-matched
  placebo 25 of 2,000). With the built hot-dog / back-to-back / long-dog cells out: -13.0% on 187 (train -19.5% /
  held -5.9%, placebo 200) against -1.8%. Either half alone is the base. ESPN's open -7.7% on 98. Judge at 60.
- **"hoops dog riding its top 2 scorers vs a balanced team (lead)"** (s10): NBA -25.1% on 111 (train -31.3% / held
  -19.9%, placebo 90), college hoops -15.2% on 378 (train -14.9% / held -15.6%, placebo 251); the balanced favorite
  across +10.2% on 63 / +7.9% on 147. Judge at 60.

## Dead (do not re-run)

- S3: turf team on grass ATS +2.4%; dome team outdoors dog -3.3% on 536 (train -12.6% / held +5.6% - flips); outdoor
  team under a roof +3.9%; the over on a surface switch -4.7% (the vig). The grass-team-on-turf ATS fade is a watch.
- S4: D 75+ snaps on a short week ATS -10.0% on 135 (placebo 429); a fresh D vs a tired one ATS +11.6% train / -6.0%
  held; the -150..-101 favorite that owned the ball last week -15.4% on 161 (a watch on 161).
- S5: a QB's first start ATS +0.3% on 201; starts 2-4 +1.3%; under 32 starts at night as a favorite -17.6% on 74.
- S6: moved AGAINST two and three weeks running - nothing in either league; the "moved to" cells flip by league.
- S7: top-heavy vs deep favorite +13.7% on 73; deep road dog -10.5% on 657.
- S8: NHL overs lose in both clock weeks (-8.9% / -11.3%) and the unders don't win (+0.8% / +1.1%); college hoops'
  fall week is opening week.
- S9: NBA the wire-to-wire winner ATS -5.3% vs -4.4%; NFL nothing; the college favorite that never led and lost
  -19.6% on 182 (train -35.5% / held -10.9%, placebo 51 - a watch).

## The lead tracker (lead_tracker.py)

Nothing at 100+ graded is a clear steady winner or loser - no raise, no cut. "money 10+ over tickets" 194-256 -0.7%
on 450; "reverse line move to it" 109-143 +3.0% on 252; "70%+ of tickets" 127-107 -4.0% on 234; "hockey fav weighed
UP" 71-38 +2.8% on 109; "NBA spread fav 3.5-12.5, games 1-20 (fade)" the faded side 54-49 +0.1% on 103 (its weight
has been off since 11/14). Under 100: "college favorite off a loss (fade)" 26-11 +26.7% on 37 still runs against its
fade; "college hoops spread side on 4-5 nights rest vs a team on 2 (fade)" 11-24 on 35 runs with it.

## Files

lib.py / h.py (the 11/18 helpers), nflv.py (nflverse's games file), brief.py (one line a cell), s1_east_west.py,
s1b_west_fav.py, s1c_models_std.py, s2_neutral_altitude.py, s3_s10.py, fA_nhl_wire_dog.py, lead_tracker.py and
their *_out.txt. Tests: test_daily_1119_* (four) in sports_test.py.
