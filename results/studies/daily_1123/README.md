# 11/23 daily studies

The owner's daily routine: a bug to fix first (the college hoops "defense-first" fact counted non-D1 tune-ups), the
board check, yesterday's picks, the lead tracker and ten NEW studies.

**In one line:** the dog-read bug is fixed from the 11/24 games (the identity's offense / defense numbers and the
shooting form read Division I games only - the slot's replay goes +24.9% -> +28.8%); the board check found a second
NBA floor play posted by a stale run (fixed in the merge from 11/24; the posted pick stays) and three card bugs (all
fixed at the root); of the ten studies ONE is built as a HALF weight (the hockey dog that gives the puck away on the
road, -1 on the dog score from 11/24), one is a tracker lead (the hockey dog that got shelled), one is a watch (an NBA
star's 40-minute night) and seven are dead. **No posted pick, price or size changed.**

Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead);
every read league-relative (the top / bottom fifth of the league's current values that night). Line-score studies
2018-26 (train 2018-21 / held 2022-26); team-box and player-box studies 2021-26 (train 2021-23 / held 2024-26); each
held season shown apart in the `*_out.txt` files. Placebo = 2,000 random same-size sets from the cell's own pool; the
follow-ups are PRICE-MATCHED (the same number of dogs out of each 50-cent price bin). Second prices: ESPN's open
(2023-26) and the paid NHL / NBA game-day morning (2021-23 / 2020-23) - the paid history was read, never pulled.
**About 450 cells were cut - about 22 clear |z| 2 by luck, and a placebo of 4 in 2,000 turns up by luck about once
on a day like this.** `python results/studies/daily_1123/view.py <file>` prints one short line a cell.

## 0. The bug: the "defense-first" fact counted tune-ups (s0_identity_d1.py, s0b_three_net_d1.py)

`sports_ncaab_box.identity` read every boxed game. Nicholls, the 11/22 ⭐ +195, read 7.4 points per 100 trips better
than the average on defense with a 110-56 win over a non-D1 school in it; on its five D1 games 1.4 (the cut is 4.8).
That fact was +2 of the dog read of 4 that posted it.

| the read | as built (every boxed game) | D1 games only | what the re-cut drops | what it adds |
|---|---|---|---|---|
| defense-first dog vs a poor offense (+2 on the dog read) | +14.7% on 328 (train +10.0% / held +22.1%) | **+20.4% on 215** (train +20.1%, 3 of 3 / held +21.3%; placebo 3 of 2,000) | +11.4% on 184 (train -0.7%) | +23.5% on 71 |
| offense-first dog, Jan-Mar (-1) - D1 thirds | -14.5% on 1,302 | **-17.1% on 1,206** (train -17.6% / held -16.3%) | -5.9% on 375 (the base) | -14.0% on 279 |
| THE DOG SLOT's own replay (the 11/16 funnel rows, 2021-26) | +24.9% on 235 (train +25.6% / held +23.6%) | **+28.8% on 210** (train +26.2% / held +34.7%) | -9.9% on 39 (held -33.2% on 17) | -13.2% on 14 |
| cold-shooting dog, Jan-Mar (-1) | -15.1% on 972 | -18.1% on 749 | -9.9% on 251 (the base) | -48.7% on 28 |
| hot-from-three road dog (-1) | -25.4% on 320 | -27.5% on 307 | -7.5% on 62 (the base) | -15.4% on 49 |

- The tune-ups lifted every built number (a D1 team's offense averaged about +2.5, its defense -2.5); D1-only they sit
  around 0. Two cuts were tried for defense-first: the built NUMBERS on D1 games (4.8 under / 5.5 / 0.5 - the table)
  and the same THIRDS re-cut on the D1 numbers (-3.0 / 3.3 / -3.0: +5.1% on 198, placebo 215 - worse). The edge is the
  really good defense, so the numbers stay. Offense-first takes the D1 thirds (3.3 over, the defense not 3.0 under):
  with the old numbers on D1 games it kept only 830 and let 506 real fades (-14.7%) go.
- **Left as built on purpose:** the turnover fields (the turnover-prone favorite, the turnover matchup) - a D1-only
  read drops 274 matchup dogs that still lose -17.5% and adds 188 at +2.0%; the three-point NET - the dog reads cleaner
  D1-only (-15.5% on 1,104 vs -12.2% on 1,433, the 378 dropped -2.6%) but the favorites / spread sides it would drop
  are still fades (-7.4% on 409 / -7.4% on 1,356), so one read for both stays. The glass and the slot's games gate were
  settled 11/21 (not re-read); the efficiency ratings are opponent-adjusted.
- Wired: `sports_ncaab_box.D1_FROM = "2026-11-24T12"` (None = as before), `identity` / `shooting`, the helpers
  `def_first` / `off_first` / `off_low`; under 5 D1 games the efficiency read is unknown (no fact); can't tell who is
  D1 = every game, as before. Test `test_daily_1123_the_hoops_identity_reads_division_i_games_only_from_the_11_24_games`.

## 1. The board (11/23)

Six unit plays, not four. At 8:00 AM, as pre-checked: 🐶⭐ Kings +130 2u (hockey Dog, dog score 6.46 over the gate of
6, +100..+150 = 2u; the ⭐ on the board's biggest bet), Indiana St +124 1u and (8:21) San José St +105 1u (the college
hoops dog slot, both a read of 4 - the ratings +2, "the favorite lost its last" +2; neither stands on an identity
fact), Washington +11.5 (-112) ½u (the spread stack +0.05 - BYU's top scorer missed its last game), Trail Blazers
+139 ½u (the NBA floor, score 2.11). Every posting rule passed on those five.

**The bug:** the sixth, Pacers +160 ½u at 8:21 AM, is a SECOND NBA floor play (the floor is one a day). The live
watcher's grader ("results 16:20: 0 graded, 5 new") ran on a copy without the 8 AM board and posted its own: the Kings,
Indiana St and Washington again, San José St (priced by then) and the Pacers (its copy held the Blazers on the Embiid
news). The 11/2 rule spots a second board by a Dog that LOST to an earlier one - here the stale Dog was the same Kings
pick, the copies folded into one and the two new picks merged in. **Fixed from the 11/24 picks**
(`tools/merge_json.STALE_FROM`): a run that re-posts a pick already up with a later stamp never saw the board - none of
its other new picks merge in. The Pacers and San José St are posted and stay (San José St is inside the slot's cap of
two; the Pacers would not have posted). Why the watcher's copy was stale is not known - its log is not kept.

Card bugs, fixed at the root (breakdown VERSION 85 rewrites the open cards - wording only):
- **A unit card written in a lean's words** - "Lean only" / "A lean" on the hoops slot cards three days running
  (Robert Morris, Nicholls, Indiana St), rewritten by the card check to a bare bottom line: the card was written
  before the play got its VALUE label. Every tagged unit play is a value play when its card is written
  (`sports.UNIT_PLAY_KINDS`).
- **No "why" on the Pacers card** - the 11/22 paint weight moved the dog score and no line said so. The card says it:
  "Only 38% of what teams score on Pacers comes in the paint this year - one of the lowest shares in the league."
- **No "why" on the Washington card** - the stack play's one reason was nowhere on it. Now: "BYU's top scorer Robert
  Wright III (23.8 a game) sat out their last game."
- **"Andrew Nembhard is cooking - with him on the floor lately the team's down 4.8 points"** - nobody is cooking while
  his team gets outscored with him out there; no line.
- Found on the way: the college hoops league map read the league play of the season BEFORE last (five schools that
  changed leagues a summer ago sat in their old ones) - fixed.
Still short: San José St (2 fact lines) and Indiana St (3) - the files hold no more for those sides.

## 2. Yesterday (11/22): 4-1, +1.67u

🔒 Panthers -145 ½u WON 35-33 (Ryan Fitzgerald's 37-yard field goal with 1:44 left); Robert Morris +102 1u WON 84-79
in overtime at New Mexico St; William & Mary -2.5 ½u WON 75-63; Wizards +170 ½u WON 116-96; ⭐ Nicholls +195 1u LOST
78-77 to Troy, decided in the last 10 seconds. Beat the close 1 of 5 (Wizards +170 vs +164; Robert Morris and William
& Mary matched; the Panthers closed -142, Nicholls +200). Pick audit: no flags. Nicholls was the one play the engine
should not have had (section 0).

## 3. The lead tracker (lead_tracker.py)

Nothing raised, nothing cut. No tag at 100+ graded is clear and steady: money 10+ over tickets 222-295 -0.5% on 517,
reverse line move 124-169 -0.1% on 293, 70%+ of tickets -3.4% on 275, NBA spread favorite games 1-20 -3.8% on 121,
college hoops small favorite away from home Nov-Dec -8.9% on 121 (z -1.2), hockey favorite weighed up +0.6% on 118,
small favorite weighed 2+ under the market -9.7% on 104 (z -1.1). The loudest small one: the college hoops spread side
on 4-5 nights' rest 18-30 -28.4% on 48 (z -2.1) - 48 bets, not a verdict.

## 4. The ten studies

| # | study | verdict | the number |
|---|---|---|---|
| S1 | NBA: the THIRD QUARTER (the margin out of halftime, last 10) | DEAD (a watch) | top fifth as a dog -10.2% on 957 (train -11.8% / held -8.8%) vs -4.6% - under the bar; "wins the third, loses the first half" dog -15.2% on 512 (placebo 71); bottom fifth vs a top fifth ATS -10.4% on 664 (placebo 107) |
| S2 | football: the third quarter (season to date) | DEAD | NFL: top vs bottom ATS -11.4% on 147 (placebo 357); college: top-fifth dog -14.5% on 248 (train -35.1% / held -4.8%), bottom-fifth small favorite -21.9% on 110 (placebo 74 - too few) |
| S3 | college hoops: a CONFERENCE's non-league form (how the rest of a team's league has covered outside it) | DEAD | league covers 55%+: ATS -4.4% on 2,345 vs -4.5%; 10+ points more than the other league: ATS -4.2% on 1,649, dog -0.7% on 481 (2022 -35%, 2024 +32%); league wins over its prices: dog +1.3% on 727 (train -4.9% / held +4.5%) |
| S4 | NHL: GIVEAWAYS / TAKEAWAYS (the team box) | **BUILT - a half weight from 11/24** | bottom fifth of takeaways minus giveaways in ROAD games, as a dog: **-18.5% on 884** vs -6.7% (train -19.9%, 0 of 3 / held -17.2%: -21.8 / -7.9 / -46.2; same-price placebo 1 of 2,000) |
| S5 | NHL: the PENALTY DIFFERENTIAL (power plays drawn minus given) and penalty minutes | DEAD (a watch) | gives more than it draws (bottom fifth): small favorite -9.3% on 628 vs -3.1% (train -12.1% / held -6.8%, placebo 67), dog -7.2% on 1,220 (the base); penalty minutes top fifth dog -1.8% on 1,088 |
| S6 | NHL: the game after getting SHELLED (40+ shots against) | **LEAD (tracker)** | playing again within 2 days, as a dog: **-23.6% on 426** (train -23.7% / held -23.4%; same-price placebo 4 of 2,000); one night off -21.1% on 308; ESPN's open -28.7% on 180 |
| S7 | NBA: the star's 40-MINUTE night (a top-2 minutes man played 40+ last game) | WATCH | dog -15.7% on 809 (train -15.0% / held -16.4%, same-price placebo 9) - but it is the SHORT-HANDED team (a top-5 man sat that game: -22.6% on 552; everyone played: -0.9% on 257) at a LONG price (+100..+150 -2.1%, +221..+350 -40.9%), and the paid morning does not confirm (-10.3% on 292, placebo 608) |
| S8 | college hoops: the FOUL-PRONE team on the road (D1 games) | DEAD | top fifth fouls, road: dog -8.7% on 1,097 vs -7.3%, ATS -4.6% vs -4.5%; at a team that lives at the line: dog -17.1% on 278 (placebo 200); fewest fouls on the road: dog -13.1% on 1,329 (train -15.8% / held -8.7%) |
| S9 | NFL: POINTS PER DRIVE (the team box's totalDrives) | DEAD | top fifth net: ATS -3.3% on 461; bottom fifth -5.0% on 464; drive count on the total: nothing in both halves |
| S10 | football: the RUNNING QUARTERBACK (the top passer's rushing yards) | DEAD | NFL top fifth: dog -6.1% on 179, ATS -3.4%; vs a team without one, dog -17.8% on 144 (too few); college top fifth dog -2.5% on 378 (train -17.8% / held +7.6%); both run, the under -11.7% on 423 (train -16.1% / held -6.9% - a watch) |

## S4 - the hockey dog that gives the puck away on the road (s_today.py nhl -> s_follow.py nhl -> s4c_board_replay.py)

The read: takeaways minus giveaways a game in a team's ROAD games (giveaways are a home scorer's count - on the road
31 different scorers count them), season to date, 10+ box games with 4+ on the road, ranked among the league that
night. Bottom fifth = "sloppy".

| cell (dog +100..+350, the close) | all | train 2021-23 | held 2024-26 | placebo (same price) |
|---|---|---|---|---|
| every dog | -6.7% on 5,772 | -9.5% | -3.2% | |
| **sloppy dog** | **-18.5% on 884** | -19.9% (0 of 3) | -17.2% (-21.8 / -7.9 / -46.2) | **1 of 2,000** |
| ... NOT out-shot (the built shot-share read off) | -16.0% on 656 | -18.3% | -13.3% | 25 |
| ... not on a back-to-back | -13.4% on 702 | -9.8% | -16.8% | 96 |
| ... home / road dog | -13.0% on 287 / -21.2% on 597 | | | |
| ... +100..+150 / +151..+350 | -16.7% on 570 / -22.0% on 314 | | | |
| ... at ESPN's open (2023-26) / the paid morning (2021-23) | -18.2% on 454 / -16.2% on 112 | | | 10 / 423 |
| the dose: league place bottom tenth / 10-20 / 20-40 / 40-60 / 60-80 / top fifth | -19.5% / -17.5% / -4.0% / -6.5% / -0.8% / -6.4% | | | |
| the parts: top fifth road GIVEAWAYS alone / bottom fifth road takeaways alone | -17.7% on 958 / -6.8% on 1,061 | -20.1% / -15.2% | -15.1% / +2.3% | |
| the same read off HOME games (the home scorer's count) | -11.4% on 1,110 | -8.8% | -15.1% | 167 |
| the built read alone (bottom fifth shot share, last 10) | -11.6% on 1,601 | -14.8% | -7.7% | 142 |
| the favorite -200..-101 ACROSS a sloppy team | +4.0% on 776 vs -3.7% | +5.2% (3 of 3) | +2.8% | 8 (as well) |

The five checks: fair prices (the close, the open, the morning); blind (no model, a walk-forward league rank); six of
six seasons down; this season -46.2% on 28; a second look (the favorite across, the open, the sloppy small favorite
-6.8% on 720).

**Why it is HALF:** on the 11/17 replay board (2023-26), the hockey dogs the board actually POSTED that carried the
read went +9.0% on 64 against +10.8% on 320 without it (placebo 869) - the dog score's other weights had already left
the bad ones off, so the weight cannot be shown to help the board itself. And ~450 cells were read. Wired at -1 on the
hockey dog's study points (`sports.NHL_SLOPPY_FROM` "2026-11-24", `NHL_SLOPPY_PTS` 1, `sports_puck.py`); the tracker
tag "NHL dog that gives the puck away on the road (fade)" judges it at 60 graded: -5% or worse = the full 2, over +5%
= off. Test `test_daily_1123_the_hockey_dog_that_gives_the_puck_away_on_the_road_is_a_half_weight_and_the_shelled_dog_a_lead`.

## S6 - the shelled dog (the same files)

40+ shots against in the last game, playing again within 2 days: dog -23.6% on 426 (train -23.7% / held -23.4%; 2026
+46% on 11), same-price placebo 4 of 2,000; on a back-to-back -30.3% on 118, one night off -21.1% on 308 (placebo 54);
an out-shot team -24.2% on 188, not one -20.0% on 173 (placebo 143); the open -28.7% on 180, the morning -41.4% on 89;
home -39.6% on 147 / road -15.2% on 279; the dose steps at 40 (35-39 -6.4%, 40-44 -23.9%, 45+ -23.0%); the shelled
favorite -200..-101 -14.7% on 275. Against the base the z is about -2.9 - one of ~450 cells - and 7 of the replay
board's posted dogs carried it. A tracker LEAD, no weight: "NHL dog that gave up 40+ shots last game, within 2 days
(fade)", judge at 40.

## S7 - the star's 40-minute night (s_today.py s7 -> s_follow.py nba)

Looks like fatigue, is not: off overtime -19.3% on 243, off regulation -14.2% on 566; two nights ago -16.0% on 506; a
dog off a close game with nobody at 40+ +3.5% on 1,241. What separates is whether a top-5 minutes man SAT that game
(-22.6% on 552 against -0.9% on 257) and the price (+221..+350 -40.9% on 188). That is the short-handed long dog - the
injuries the engine already weighs, at prices the board's ½u NBA dogs don't reach (+199). Not built, not tagged.

## Files

`lib.py` / `h.py` (shared), `s0_identity_d1.py`, `s0b_three_net_d1.py`, `s_today.py` (S1-S10), `s_follow.py` (the
controls), `s4c_board_replay.py`, `lead_tracker.py`, `view.py`, and every `*_out.txt`.
