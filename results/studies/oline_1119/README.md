# 11/19 - FABLE: THE OFFENSIVE LINE, THE SECONDARY, THE PASS RUSH

The owner, 11/19, on Thursday's Colts +525 at the Texans (both starting tackles out, a starting corner out, another
questionable - and the engine counted the Colts as the HEALTHIER side, because an offensive lineman is in no box score):
"The starting fucking edges are key because then there's no pass protection. There are backups on pass protection, and
teams could get eat up. Like, these are very key things for the engine. Fable needs to run studies on this as well and
get this all sorted out. This is not okay that we're not looking at this."

## THE ANSWER, IN PLAIN WORDS

1. **The engine was blind to them. That is fixed.** Who starts at every spot a box score can't show - the offensive
   line, the corners and safeties, the men up front on defense - now comes off the NFL's snap counts
   (`sports_starters.py`). The cards name them in plain words ("OT Bernhard Raimann (starting tackle)", "Both starting
   tackles out - backups protecting the QB.") and the banged-up count counts them.
2. **One missing starter is already in the price - any of them.** A starting lineman out, a starting corner, a safety, a
   defensive end, a tackle out against a team that gets to the quarterback: the team with the hole wins exactly as often
   as the closing line says it will. The books know. Betting against those teams loses the vig.
3. **Two linemen MORE than the other side is not in the price - when that team is the dog.** An NFL underdog with two or
   more starting offensive linemen more out than the favorite won **21.5%** of the time where the closing line said
   **34.2%** (135 games, 2016-26). Betting on those dogs lost **40.9%** (first half of the years -23.8%, second half
   -56.5%, 10 of 11 seasons down, 4 of 2,000 random sets of dogs did as badly). The favorite across from them made
   +15.9% on the moneyline, +14.2% even a point worse than the close. The market does move against the thin line (about
   a point of win chance from the first fair price to the close) - not far enough.
4. **"Both tackles" is not the magic. The count is.** Both tackles out, a tackle plus a guard, two inside men: what
   matters is how many linemen more than the other side, and whether the team is the dog. A FAVORITE with the thin line
   is fine (won 66.3% vs 63.7% priced).
5. **The secondary and the pass rush: nothing past the price.** Two starting corners out, two of the secondary out
   against a top passing offense, a starting pass rusher out, "our line is down and their rushers are all healthy" -
   none of it beats the closing line in both halves. If anything the books mark a team DOWN too far when it is missing
   men up front on defense (the bet against those teams lost).
6. **College: we cannot see it.** No snap counts exist for college and ESPN keeps a depth chart for almost no college
   team. A college offensive line stays UNKNOWN (never "healthy", never a claim); the code reads a college depth chart
   the day ESPN has one.

## WHAT WAS WIRED (games from 11/20 - `sports.OLINE_FROM`, None = off)

| | |
|---|---|
| The count sees them | `sports.out_count` (the banged-up count behind the depth weight, the stamped injury count, the tracker's depth gap) counts a starting offensive lineman and a starting corner / safety the snap counts name, beside the box score's regulars. One man, one count. The men up front on defense are named on the card but left out of the weight (their number flips - see table D). |
| The thin line | An NFL **dog** with 2+ more starting linemen out than the favorite reads **2 points less** on its own read (`sports.OL_GAP_PTS`), on top of the depth weight (1 point a regular), the two together capped at **4** (`DEPTH_OL_CAP` - inside FAV_CAP / STUDY_CAP). The study's gap is 9-13 points; it is taken at well under half. A weight, never a block, never a trigger. |
| The tracker | "NFL dog, 2+ more starting linemen out than the favorite (fade)" - the weight's forward record. |
| The cards (from the first run, no date) | `sports.who_matters` tags a man by what he is ("starting tackle", "starting corner", "starting defensive end"); `sports.card_outs` leads the who's-out list with the men behind a hole and adds a starter who went on injured reserve this week; a lineup more than one starter short at a spot is said with the names - theirs on the 🚑 line, ours only as the ⚠️ knock; `sports_card_check` takes the claim off with the men. |

Not wired (looked at, did not clear): any weight for one lineman, both tackles by themselves, the secondary, the pass
rush, the pass-rush / passing-offense match-ups, a favorite with the thin line, a spread play (the bet against the thin
line against the spread is +9.8% on 250 at the close but +2.4% a point worse - too thin to be a play).

## THE DATA AND THE RULES (fixed before the tables were read)

nflverse's public files (`fetch.py` - plain downloads under our own name): snap counts, the final injury reports, the
schedules file's closing moneylines / spreads, the weekly team stats (sacks, QB hits, passing yards), 2016-26. The first
fair price is our paid odds history (2020-26): the first snapshot 20+ hours after both teams' last games, the median book.

* **4,870 team-games** (a team's game 3+, both teams' starters known), 11 seasons. Train 2016-21, held out 2022-26.
* **A starter**: played 70%+ of the offense's snaps (T / G / C) or the defense's (CB / S / LB) in 2+ of his team's last 4
  games; 50%+ for DE / DT / NT (they rotate). The 3-4 edge men are listed LB by the source - "edge" below is DE.
* **Out**: the final report lists him Out / Doubtful (study 8: such a man plays 0.2% of the time), or he has no game
  status and does not dress (injured reserve / a suspension - public before the game).
* **The other side's pass rush / passing game**: sacks (and QB hits) per drop-back / net passing yards a game, this
  season before the game, top third of the week.
* **The bar**: both halves the same way, most seasons, a placebo under 5% (2,000 random sets the same size), a point
  worse than the close, the first fair price where we hold it. 74 cells a pass - about 4 clear |z| 2 by luck.

**Two passes.** The first pass called a starter "2+ of the last 3 games, 70%+ on AVERAGE" (`s1_first_rule.out`,
`s2_first_rule.out`). The Colts' own tackles broke that rule: Raimann went down 10% into his last game and Travis 41%
into his, so the average called neither one a starter. A game a man leaves hurt must not unmake him - the rule became
"70%+ in 2+ of the last 4 games" and every table was re-run (`s1_cells.out`, `s2_ol_gap.out`). Both passes say the same
thing; the numbers below are the second pass, the first pass beside the headline cell.

## THE TABLES (the side WITH the hole: won % vs what the no-vig close said; then the bet AGAINST it at the close)

### A. Starting offensive linemen out

| the side has... | games | won | the close said | z | fade ML | fade ATS (train / held) |
|---|---|---|---|---|---|---|
| exactly 1 starting lineman out | 1,583 | 49.7% | 49.4% | +0.3 | -4.3% | -2.9% (-1.5 / -4.7) |
| 2+ starting linemen out | 430 | 40.6% | 43.6% | -1.4 | +2.7% | +2.3% (+4.9 / -0.5) |
| 3+ starting linemen out | 68 | 32.4% | 39.5% | -1.3 | +10.0% | +19.5% (+26.7 / +14.2) |
| 1+ starting tackle out | 934 | 47.1% | 48.4% | -0.9 | - | - |
| BOTH starting tackles out | 69 | 37.7% | 41.0% | -0.6 | +0.7% | -4.5% (+6.1 / -14.2) |
| a tackle + an inside man out | 229 | 38.9% | 43.7% | -1.6 | +9.0% | +10.9% (+7.7 / +14.6) |
| two inside men out, tackles in | 101 | 44.6% | 44.9% | -0.1 | -7.2% | -9.0% |
| **2+ MORE linemen out than the opponent** | 250 | **35.3%** | **41.8%** | **-2.2** | +6.4% (+7.4 / +5.4) | **+9.8% (+13.6 / +6.0)**, 9 of 11 seasons, placebo 24 / 2,000 |
| ...the same, first-pass rule | 189 | 33.5% | 40.7% | -2.2 | +10.5% (+14.9 / +6.5) | +14.4% (+17.1 / +12.0), placebo 5 / 2,000 |

The dose (the gap in starting linemen out, ours minus theirs): **0** 50.0% vs 50.0% · **+1** 48.3% vs 47.5% (1,035) ·
**+2** 35.7% vs 42.2% (207, 2 points short of the spread) · **+3 or more** 33.3% vs 39.6% (42).

Against the other side's pass rush: 1+ lineman out vs a top-third pass rush 46.2% vs 45.1% (664); 1+ tackle out vs a
top-third pass rush 46.7% vs 46.1% (302), vs a top-third QB-hit rate the same; 2+ linemen out vs a top-third rush 37.0%
vs 40.5% (138) - the same size as 2+ out against anybody. The pass rush across adds nothing the gap doesn't already say.

### B. THE CELL THAT CLEARS: the dog +100..+350 with 2+ more starting linemen out than the favorite

| | all | train 2016-21 | held 2022-26 | seasons |
|---|---|---|---|---|
| it won | 21.5% vs the close's 34.2% on 135 (z -3.2) | | | |
| the bet ON it, moneyline at the close | **-40.9% on 136** (z -4.1) | -23.8% on 65 | -56.5% on 71 | 10 of 11 down |
| ...placebo | 4 of 2,000 random sets of 136 dogs as bad | | | |
| the bet ON it, the first fair price (2020-26) | -44.7% on 91 | -30.8% on 30 | -51.5% on 61 | 6 of 7 down |
| the FAVORITE across, moneyline at the close | +15.9% | +5.7% | +25.1% | 8 of 11 up |
| the FAVORITE across, a point worse | +14.2% | +4.2% | +23.3% | 8 of 11 up |
| the FAVORITE across, the spread at the close | +14.6% | +17.3% | +12.2% | 8 of 11 up |
| the FAVORITE across, the spread a point worse | +6.7% | +5.4% | +7.9% | 7 of 11 up |
| first-pass rule: the bet ON the dog | -29.8% on 96 | -20.1% | -39.6% | 9 of 11 down, placebo 70 / 2,000 |

Beside it: the dog ONE lineman short 38.1% vs 35.8% (459, nothing); the dog level 35.2% vs 35.6%; the dog whose
FAVORITE is 1+ linemen short 35.3% vs 36.3% (no edge in backing the dog there); a FAVORITE 2+ linemen short 66.3% vs
63.7% (83 - nothing). The dog's price moved 1.0 point of win chance against it from the first fair price to the close.

Weeks 1-16 only (no rested starters): the side 2+ linemen short 37.5% vs 42.7% (208), fade ATS +9.4% (+13.6 / +5.3).
The report's men only (no injured-reserve kind): 38.7% vs 45.4% on 62 - the same size, too few to stand alone.
Season by season the thin-line side won less than its price in 8 of 11 (2016, 2017, 2019 flat, 2025 the one bad year).

### C. Starting corners / safeties out

| the side has... | games | won | the close said | z | fade ML | fade ATS (train / held) |
|---|---|---|---|---|---|---|
| exactly 1 starting DB out | 1,364 | 47.5% | 47.8% | -0.3 | -4.7% | +0.6% (+0.2 / +1.1) |
| 1+ starting corner out | 1,109 | 45.7% | 46.8% | -0.8 | -2.5% | +2.2% (-1.4 / +6.4) |
| 2+ starting corners out | 115 | 44.3% | 46.9% | -0.6 | +5.2% | +1.6% (-5.5 / +11.9) |
| 2+ of the secondary out | 352 | 44.3% | 45.7% | -0.6 | +4.8% | -5.1% (-11.6 / +3.6) |
| 1+ starting safety out | 791 | 47.5% | 47.2% | +0.2 | - | - |
| 1+ corner out vs a top-third passing offense | 382 | 36.6% | 38.5% | -0.8 | - | - |
| 2+ of the secondary out vs a top-third passing offense | 114 | 34.2% | 37.9% | -0.9 | flips: first fair price +31.8% train / -18.5% held | |

Nothing holds in both halves. The market has the secondary.

### D. The men up front on defense out (DE / DT / NT, 50%+ of the snaps)

| the side has... | games | won | the close said | z | fade ATS (train / held) |
|---|---|---|---|---|---|
| 1+ starting defensive lineman out | 860 | 47.4% | 47.0% | +0.3 | -7.1% (-6.0 / -8.4), 2 of 11 seasons up |
| 2+ starting defensive linemen out | 95 | 46.3% | 45.8% | +0.1 | -22.5% (-30.0 / -14.4) |
| 1+ starting defensive end out | 458 | 46.3% | 46.7% | -0.2 | - |
| linemen level, 2+ more DB / DL out than the opponent | 166 | 47.6% | 43.6% | +1.1 | -21.9% (-23.7 / -19.6) |

The team missing men up front on defense is no worse than its price - and the bet against it against the spread LOSES
in both halves. The books mark those teams down too far if anything. No weight; and it is why the front is named on
the card but kept out of the banged-up count.

### E. The combination: our line down + their rush healthy

| | games | won | the close said | z |
|---|---|---|---|---|
| 1+ lineman out, the other side's starting DL all in | 1,624 | 46.9% | 47.6% | -0.6 |
| 1+ lineman out, the other side missing a starting DL | 383 | 51.7% | 50.6% | +0.5 |
| 1+ tackle out, their starting edge all in, a top-third rush | 270 | 46.7% | 46.1% | +0.2 |
| 2+ linemen out, their DL all in, a top-third rush | 108 | 35.2% | 39.8% | -1.1 |
| 2+ more linemen out AND the rest of the lineup worse too | 88 | 27.3% | 35.9% | -1.8 |
| 2+ more linemen out, the rest level or better | 161 | 39.8% | 44.9% | -1.4 |

The healthy rush across adds nothing to the lineman count. The thin line hurts whether or not the rest of the roster is
hurt too (it is not just "the more banged-up side").

### F. On top of the closing line (a logistic fit: the close + the gap in starters out; points of win chance a starter)

| group | train 2016-21 | held 2022-26 |
|---|---|---|
| offensive line | +1.0 (z +0.6) | +1.9 (z +1.2) |
| corners / safeties | +0.7 (z +0.5) | +1.1 (z +0.6) |
| defensive line | -2.7 (z -1.2) | +2.7 (z +1.1) |
| all of them, one number | +0.2 (z +0.2) | +1.7 (z +1.6) |

A straight line through the count is small (a point or two a man, the size of the depth weight the 11/11 book study
set) - the effect lives in the gap of TWO, in the dog.

## COLTS AT TEXANS (nfl:401873066, Thursday 11/19, 5:15 PM PT) - `colts_texans.out`

The week-11 report: Colts OUT - OT Bernhard Raimann, OT Jalen Travis, CB Charvarius Ward, DT Jerry Tillery, TE Will
Mallory; questionable - CB Sauce Gardner, OT Charlie Heck. Texans OUT - DE Danielle Hunter, WR Marvin Harrison Jr., RB
Woody Marks, TE Brevin Jordan.

| | before | after |
|---|---|---|
| Colts starters out the engine sees | Ward (he makes tackles) | Raimann (starting tackle), Travis (starting tackle), Ward (starting corner) |
| the banged-up count, Colts to Texans | 1 to 1 | **3 to 1** (under the 11/20 rule) |
| starting linemen out | not known | Colts 2, Texans 0 |
| Colts +525 own read (the no-vig close 15.3%) | **18.0% - OVER the price** | **14.0% - under it** (4 points off: 2 the count, 2 the thin line, the cap) |
| Texans -750 own read (84.7%) | 82.0% | 86.0% |
| the Texans' named reasons | - | + "opponent the more banged-up side: 3 regulars out to 1 for us", "opponent's offensive line is short: 2 starting linemen out to 0 for us" |
| 🚑 Colts line | "Colts out: CB Charvarius Ward (starter) · questionable: CB Sauce Gardner (starter)." - **no tackle on it** | "Colts out: CB Charvarius Ward (starting corner), OT Bernhard Raimann (starting tackle), OT Jalen Travis (starting tackle) · questionable: CB Sauce Gardner (starting corner)." |
| the Colts' who's-out list on a card | Ward, Tillery, Raimann, Mallory (the card check then dropped Raimann as a man who "doesn't matter") | Raimann, Travis, Ward lead it; a Texans card says "Both starting tackles out - backups protecting the QB." |
| 🚑 Texans line | (none) | "Texans out: DE Danielle Hunter (starting defensive end), RB Woody Marks (starter)." |

No pick changes: the Colts are +525 (the board takes dogs to +350) and the Texans -750 (never past -150). Tillery and
Mallory are depth men by the snap counts (33% and 34% of the snaps) and are not called starters. Tonight's game is a
Pacific 11/19 game, so live it gets the CARDS (the names) and not the weight - the weight starts with the 11/20 games.

## FILES

`fetch.py` (the downloads) · `olib.py` (the table: who starts, who's out, the prices, the bets) · `s1_cells.py` /
`s1_cells.out` (every question, 55 cells) · `s2_ol_gap.py` / `s2_ol_gap.out` (the one family that showed, pushed 19 more
ways) · `s1_first_rule.out` / `s2_first_rule.out` (the first pass) · `colts_texans.py` / `colts_texans.out`.
