# 10/30 - THE WEEKEND SWEEP (code + data + board)

The owner (10/30): "Do a full sweep audit of the engine ... get everything in order so we can win a bunch of money this
weekend." This is the code / data / board half (the college, NFL and NBA studies ran in parallel). Standing
authorization to fix bugs without asking; no posted pick changed; no paid odds re-pulled.

Tools (scratchpad): `stub_preview.py` (the 8:35 AM board for a day with the injury feeds stubbed - the sandbox can't
reach ESPN / Rotowire / Covers - every pro side and every priced college side read as healthy, so it shows the MOST the
board could post; the real 8 AM run reads the reports), `slate_dump.py` (the weekend slates, the odds feed's freshness,
the official-report coverage), `tools/board_preview.py` for both days unstubbed.

## 1. The code since 10/27 - what was checked, what held

Read end to end: `post_board` (the kinds loop, the floor / NBA floor / dog_play / nba_fav / gap / owner_posts / night
paths, the early-side lock, the fallback floor), `units_for` / `dog_units` / `lock_units` / `sizing_check` /
`rule_check` / `posted_kind` / `play_tier` / `upgrade_dog`, `floor_plays` / `floor_skip` / `nba_floor_plays` /
`unit_plays_today`, `sports_early.post` / `watch` / `grade` / `units` / `nba_open_scan` / `nba_key_hole` /
`pick_spots`, `sports_pings`, the dashboard's unit record / TODAY'S RESULTS / the no-Lock and no-Dog notes / the
card labels, the question box (`lock_miss`), `data_gaps`.

Rule interactions, each traced:
- Two picks on one game: `rule_check` pulls a second pick on a game already carrying one (the `seen` map); the kinds
  loop skips `used` games; a lean / floor / NBA floor never lands on a game we're in early (`early_gids`); a value play /
  gap / dog_play / NBA favorite CAN take the SAME side as an early play (the owner, 10/4: "Jaguars can be both") and
  never the other side (`cands` are filtered to our side of every early game - `early_sides`). Held on both previews:
  the Rams (vs our Chargers +285) and the Marshall / Southern Miss / Louisiana Tech / Texas Tech / Oregon sides never
  entered the pools.
- Floor vs NBA floor vs Dog vs dog_play: the general floor skips NBA (the NBA floor is the NBA's one a day), college
  football and the raw-read dog, posts the skipped one only when the day has no unit play at all; the NBA floor posts
  only when the day has no NBA unit play; `upgrade_dog` never promotes a floor / gap / owner play. A dog_play passed the
  full Dog gate, so an upgrade to the Dog sizes at the Dog's own-read rule (2u) - by the 10/8 "best value dog is the
  Dog" rule and the 10/23 plan together.
- Sizing: `units_for` and `sizing_check` agree on every kind (floor ½u, NBA floor ½u, dog_play ½u, gap 1u, NBA favorite
  1u, value ½u, thin Lock / Dog ½u, backup Lock ½u, the owner's units kept). Both previews: `RULE CHECK: []`,
  `SIZING: []`.
- Pings: `midday` is set only on unit plays posted after the opening board (`not opening`), leans never, one queue
  entry per play keyed by game + side, sent once the live page shows the card. A floor play added at the 9 AM run
  before the first game is a unit play added after 8 AM - it pings, correctly.
- The question box: on a thin-Lock day it names the dropped favorite (Lightning -141 on 10/31, "a thin edge is never
  the Lock"); on a no-value day the near-miss (Buccaneers -142 on 11/01, "1.4 points under what the price needs").
- The dashboard: the no-Dog note reads "half-unit plays" only when every dog up is ½u; the no-Lock note only when no
  Lock / solo is up; TODAY'S RESULTS counts unit plays only; the labels (🔍 / 🏀 NBA FAVORITE PLAY / VALUE PLAY · THIN
  EDGE) read the pick's tag.

No sizing, rule or ping bug found in the 10/27-10/30 code. What was wrong was on the CARDS (section 3).

## 2. Weekend readiness

**Saturday 10/31** (103 college games, 47 priced; 7 NBA; 10 NHL; 1 MLB). At today's prices with everyone healthy the
8 AM board would carry: 🐶 Dog of the Day **Iowa State +280 vs Oklahoma St, 2u** (own read 30.5% vs 26.3% needed, dog
score +5.3 over the college gate of 4, the ratings' side, not thin); 🔍 **Fresno St +185 vs Oregon St, 1u** (the gap
play - the raw read 22 points over the market, the ratings back it); **Lightning -141 ½u value play** (the thin-Lock
rule took it off the Lock spot: own read 60% vs 58.5% needed - 1.6 points); leans Senators -120, Sabres -116; no Lock.
No NBA pick: the books have no Saturday NBA price yet (the 7 games have no line at 06:34Z; the NBA opening-line scan
picks them up hourly once they post - the 🏀 play, ½u, fires the night before when a side clears 4 points with the key
men in). Hockey: no fallback Dog (every hockey dog sits 0.5 points or less over the no-vig market; the rule needs 2+);
the floor had nothing to add (the two unit plays meet FLOOR_MIN). Cards: Iowa State's and Fresno St's breakdowns run
5 fact lines (floor 6) - the facts for the OTHER side (Oklahoma St's and Oregon St's heaters, the points lately) are
knocks by the 10/27 rule and only the biggest posts as the risk line; the log says the facts ran out, not padding.
The real board depends on the injury reads (section 4): a college side with no report gets no pick.

**Sunday 11/01** (12 NFL, 4 NBA, 5 NHL, 2 college hoops). At today's prices: nothing clears the value bar (the
Buccaneers -142 the nearest, 1.4 points short); the floor fills with **Vikings +142 at the Lions, ½u** (dog score +1.5)
and **Dolphins +260 at the Patriots, ½u** (score -1.9 - the best dog left; its closer now says so); leans Buccaneers
-142, Eagles +6 (-108). The Chargers +285 early play rides into game day (now +225 - the number came to us); the Rams
side is locked out of every pool. NBA / NHL Sunday lines were not posted yet at 06:34Z (normal - they come the day
before).

## 3. Bugs fixed (tests in `test_weekend_sweep_1030_team_verbs_agree_on_every_line_and_the_floor_closer_tells_the_truth`)

1. **Team verbs on the body lines** (the owner's 10/27 rule - "Wild holds"): the 10/29 sweep fixed the tails, the risk
   line and the closers at the pool, but ~70 body pools still say "{us} are / have / take" - right for the Bruins,
   wrong for a school: the Saturday preview read "Iowa State are healthy", "Iowa State take care of home", "Fresno St
   have dropped 2 straight", "the Lightning are healthy". A Saturday board is mostly school names. FIX: the card guard
   (the last stop every card line passes, at post AND at render - so already-posted cards get it too) makes the verb
   agree with the name, ours and the opponent's (`sports_card_guard.agree`; v24 and the dashboard pass both names).
   "been" stays ("Iowa State been the better team" is his lingo). The school names that end in s (Texas, Kansas,
   Arkansas, Illinois, Ole Miss, UMass) read as plurals in `vb` - now singular.
2. **"Senators's the side" / "Sabres's the side"** - the coin-flip lean closer glued a possessive onto a plural name.
   Now "Senators are the side" / "Wild is the side" (`sports_breakdown._lean_pool`).
3. **The floor closer on a dog the score has UNDER zero** - the Dolphins +260 (score -1.9) closed with "the dog angles
   back it, our read calls it about even" - false on both counts (the angles net negative; the read sits 3 points
   under the price). The floor is allowed to take it (the 10/29 replay: the "score 0+ only" cut did not hold), but the
   card can't lie: a new closer pool for score < 0 says it's the best dog left on the slate, half a unit, nothing
   loud (`bottom_floor_low`). VERSION 61 - open cards re-render.

## 4. Data for Saturday

- Box scores / games: every priced side on both slates reads complete (`seen_all` True for all 206 college sides,
  the 10/28 two-bye fix holding); no "no result" gap except the Flames' Friday game, which is simply unplayed as of the
  10/30 pull and will be in by the 06:40Z Saturday pull (not a bug - the preview's clock is ahead of the data).
- Odds: every priced college / NHL / NFL game carries a line from the 10/30 06:34Z pull (one NFL game, Falcons @
  Buccaneers, from 10/29 12:24Z - the feed refreshes hourly). 56 college games have no price (FCS / small schools - the
  slate check names them, "not held"). NBA Saturday and Sunday, NHL Sunday: no line yet (the books post them the day
  before).
- Injury coverage (the thing that blocks picks): college coverage on game day = Covers' page (every FBS school,
  healthy ones too) + Rotowire + ESPN live + `injuries_official.json` (filled 5:47 / 11:47 AM PT by the routine; 88
  teams last Saturday, 6 today for the weeknight games - NOTHING for 10/31 yet, which is normal before game day; the
  reader takes ±1 day). If Covers' page fails Saturday morning, every college side without an official report is
  UNKNOWN and gets no pick. Of the 94 priced college sides on Saturday's slate, 57 had an official report last
  Saturday and 37 did not - those 37 ride on Covers / Rotowire alone unless the routine files them 10/31: Air Force,
  App State, Arkansas, Army, Coastal, Duke, East Carolina, FIU, Florida, Florida St, Fresno St, GA Southern, Georgia,
  Liberty, Louisville, Marshall, Maryland, Memphis, Missouri, NC State, Nebraska, Notre Dame, Ohio State, Oregon St,
  Penn State, Purdue, South Alabama, South Florida, Stanford, Temple, UAB, UConn, UNLV, UTEP, Virginia, Wake Forest,
  Washington. Two of the preview's three college unit plays sit in that set (Fresno St / Oregon St; the Iowa State
  game is covered both sides). The 8 AM factor check names every uncovered team ("no injury report for N teams - no
  pick on their games") - read it Saturday.
- Pro: the ESPN feeds (NFL / NBA / NHL) - a feed that fails = the sport waits (never a blind pick).

## 5. The open early plays for the weekend, by the rules

| play | spot | posted at | now | key man out? | by the rules |
|---|---|---|---|---|---|
| Arizona +215 at Texas Tech (10/31 16:00Z) | 💥 blowout (over Iowa State 39-3, FBS) ½u | +215 | +145 | none flagged | valid - the number came to us 70 cents |
| Northwestern +230 at Oregon (10/31 19:30Z) | 💥 blowout (over Rutgers 42-14, FBS) ½u | +230 | +145 | none flagged | valid |
| Old Dominion +120 vs Marshall (10/31 17:00Z) | 🧠 engine ½u | +120 | +120 | none flagged | **a PAUSED spot's play** - the "engine" spot was paused 10/24 (SPOTS_OFF); it posted 10/25 through the spot_scan path that didn't check the pause (fixed 10/26). The 10/26 note left it as the owner's call; by the 10/24 rule it should come off |
| UL Monroe +130 vs Southern Miss (10/31 19:30Z) | 🧠 engine ½u | +130 | +145 | none flagged | same - a paused spot's play |
| South Alabama +180 vs Louisiana Tech (10/31 19:00Z) | 🧠 engine ½u | +180 | +185 | none flagged | same - a paused spot's play |
| Chargers +285 at Rams (11/01 21:05Z) | 🛌 bye 1u | +285 | +225 | none flagged (the hourly watch flags a NEW key man out - `key_out`) | valid |
| Wizards -107 vs Hornets (10/30 23:00Z) | 🏀 opening line ½u | -107 | - | none | today's game, not the weekend |

None is past +350; none carries a `key_out`. The three "engine" plays are the only ones the rules say should come off
(not pulled here - the owner's call, as the 10/26 note left it). The Chargers' key men (Herbert) can only be checked
by the live feed - the hourly `watch` does it; the sandbox has no feed.

## 6. Not touched (by design, noted)

- A floor dog can carry a negative dog score (the 10/29 replay kept it); the card now says so.
- College unit cards at 5 lines when the other side holds the facts - the 10/27 "never argue for the other side" rule;
  the log line BREAKDOWN SHORT marks each.
- The 10/28 "deadline fallback for a dog whose KEY man is still unknown 3 hours before tip" stays not built.
