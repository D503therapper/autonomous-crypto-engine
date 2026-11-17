# 11/17 - THE BREAKDOWN SWEEP: is every line on a card true, current, and does it make sense?

The owner, 11/17: "My buddy keeps complaining about the breakdowns and says they make no sense and false, outdated
information of injuries and stuff. Fable needs to run a sweep and make sure that these breakdowns are always accurate and
up to date." / "false information and outdated bullshit is costing people a lot of money. And this cannot happen."

Run it again any time:

    python tools/card_audit.py --since 2026-11-01 --with-leans --raw     # the cards as they were WRITTEN
    python tools/card_audit.py --since 2026-11-01 --with-leans           # the same cards as the page shows them today
    python tools/card_audit.py                                           # the live cards, with the injury report

## 1. What was tested

Every card posted 11/1 - 11/16: the 45 board cards in `data/sports/picks.json`, the 46 leans that came off the board on
11/16 (`leans_removed.json` - they were posted cards too) and the 22 early plays in `early.json`. **113 cards, 888 lines.**
Each line was re-derived from the files: the game files (records, scores, streaks, points a game, who played last night,
the road trip, the last meeting), the box scores (who really started in net / at quarterback, who really played), the
45 graded reviews (the final and the score after each period). Nothing in `data/sports` was changed.

## 2. The count - the cards as they were written

| | lines | what |
|---|---|---|
| **OUTDATED** | **22** | 17 goalie lines + 2 quarterback lines giving numbers for a man who did **not** start; 3 men listed OUT who played |
| **MAKES NO SENSE** | **33** | 9 rest talk with no back-to-back, 4 garbled last-meeting lines, 3 "+0 a game", 1 "4 for / 4 against ... 3 for / 3 against", 3 line-move talk under an early pick, 5 bottom-line numbers that weren't ours, 8 wrong words for the bet (a lean's words on a unit play, hype on a half unit, a sure-thing call on a long dog) |
| **FALSE** | **5** | 3 home / road records that counted a neutral-site game, 2 "bye week" lines for a team that played the week before |
| lingo only | 89 | banned frames and canned tails the page already rewrites ("let's eat", "Still riding Suns") - not facts |

**60 lines on 44 of the 113 cards were outdated, senseless or false as written.** Plus what the 11/12 freshness check had
already caught live on those cards (Scottie Barnes, Colten Ellis, Carter Hart, Cam Skattebo, J.J. McCarthy).

The same 113 cards **as the page shows them after this sweep: 0** (`--since 2026-11-01 --with-leans`, no `--raw`).
Before this sweep the page still showed 17 of the 22 outdated lines and 17 of the 33 senseless ones (the rest the 11/13 card
check already rewrote).

### The big one: goalie lines

| how the card said it | goalie lines with a save % | named a man who did NOT start |
|---|---|---|
| "in net last time out" / "last starter" / "if he goes again" | 26 | **11 (42%)** |
| "projected to start (not confirmed yet)" | 13 | **3 (23%)** |
| said flat, as tonight's goalie | 12 | **4 (33%)** |
| **all** | **51** | **18 (35%)** |

One in three. "In net last time out" is a true sentence and a bad guess: the Flames card argued the Sharks' Alex
Nedeljkovic can't stop a puck - Yaroslav Askarov started. The Stars card's one risk line compared Cam Talbot to Jake
Oettinger - Casey DeSmith started for us. The Flyers card (11/14, a 2u Dog) compared Cam Talbot to Joseph Woll - Jet
Greaves started. Quarterbacks: 2 of 22 (Carson Wentz the day Kirk Cousins started, Gardner Minshew II the day Carson
Beck did - both 11/15, the class the 11/16 depth-chart work closed).

### Real examples

| card | the line | what was wrong |
|---|---|---|
| 11/2 Flames +105 (2u Dog) | "🥅 Pucks keep getting past Alex Nedeljkovic, who was in net last time out for the Sharks — a 0.882 save %" | Yaroslav Askarov started |
| 11/5 Stars -130 (1u) | "⚠️ Cam Talbot (Blue Jackets, in net last time out) is at a 0.931 save % ... to Jake Oettinger's 0.857 (our guy in net last time out)" | Casey DeSmith started for the Stars |
| 11/12 Red Wings +142 | "🚑 Panthers gotta play without Sandis Vilmanis (LW)." | he played |
| 11/2 Heat +105 | "🚑 Out for Lakers: Ziaire Williams (F), Adou Thiero (F). That's real depth gone." | Williams played |
| 11/7 Devils -148 | "⚠️ Not perfect - Islanders got Devils last time these two met, a 6-0 loss to the Islanders." | garbled - who lost to whom |
| 11/14 Flyers +114 (2u Dog) | "📊 Over the last 3, Flyers are +0 a game (3 for, 3 against)" | "+0 a game" says nothing |
| 11/5 Stars -130 | "📊 Stars average 4 for / 4 against over their last 3; Blue Jackets 3 for / 3 against." | whole-goal rounding: says nothing |
| 11/14 Flyers +114 | "⏳ Flyers got the extra day: 3 days off to Blue Jackets' 2 days." | rest talk, no back-to-back ("Both teams rested lol") |
| 11/2 Bears | "🛌 Bears are fresh off a bye — rested and game-planned up." | they played 11 days earlier, the week before |
| 11/7 Ole Miss +145 | "🏟️ Home cooking for Ole Miss - 5-0 in their own building this season." | 4-0 - one was in Atlanta |

Before / after, the 11/14 Flyers 2u Dog as the page shows it:

    BEFORE                                                              AFTER
    📊 Over the last 3, Flyers are +0 a game (3 for, 3 against); ...     (gone - "+0 a game")
    ⏳ Flyers got the extra day: 3 days off to Blue Jackets' 2 days.      (gone - no back-to-back)
    ⚠️ Cam Talbot (Blue Jackets, projected, not confirmed) is at a       (gone - Jet Greaves started; from 11/18 the line
       0.929 save % ... to Joseph Woll's 0.893 (our projected guy)        shows only once the goalie page confirms him)
    🧊 / 🍀 / 📅 / 🥊 / 📋 / ✅ Bottom line                                 unchanged

## 3. The audit table - every line a card can carry

"Fresh at the post" = how old the source is when the card is written. "Later" = what keeps it right while the card sits on
the page. "Checked" = the card check (`sports_card_check`) verifies it on every page build.

| line | source | fresh at the post | later in the day | checked before 11/17 | gap found -> the fix |
|---|---|---|---|---|---|
| the line under the pick | `sports_breakdown_v24.why_line` - the game files + the pick's reasons | this run | frozen text | wording, lingo, records / scores, no line-move talk | its other numbers went unchecked -> the same derived checks as the body |
| 📋 records · 🏟️ home · 🧳 road · 🔥 🧊 streaks · 📅 last game · 🥊 beatdown · 🗓️ last 5 | `data/sports/games` | this run (a game-day card: nothing can move before the game) | frozen, still true | yes (`facts`) | 3 neutral-site records and 2 false byes on old cards - both fixed 11/13 / 11/16; one true line was being dropped (a score read for the wrong team) - fixed |
| 📊 points a game lately / on the year · 🛡️ | the game files (`_pts3`, `_per_game`) | this run | frozen, still true | **no** | never re-read; "+0 a game"; whole goals in hockey -> `stats` + `sense`; hockey says one decimal; a zero margin is never said |
| 😮‍💨 😴 back-to-back · ⏳ 🛌 rest | the game files | this run | frozen | rest DAYS only | who played last night never re-read; rest talk with no back-to-back still on older cards -> `played_last_night`, `rest_talk` |
| 🧳 the trip ("3rd road game in 6 days") | `sports_context` (the schedule + the venue table) | this run | frozen | **no** | -> `road_trip` re-counts it off the schedule. The MILES are not re-derived (still a gap - it needs the venue table) |
| 🆚 / "last time these two met" | the game files | this run | frozen | **no** (skipped on purpose) | garbled wording on 4 cards -> `last_meeting` (score + who won) and the pool rewritten |
| 🚑 who's out · the "missing" chip · ⚠️ "go without" · ✅ "full squad" | ESPN's injury feed + `injuries_official.json` (5:47 AM / 11:47 AM PT) | the 8 AM run | **the report moves all day** | only the who's-out LISTS, only a man who came OFF the report | (a) a status that moved (questionable -> out, out -> questionable) (b) a man named only in a line (c) "full squad" after the report lists someone (d) a man the card has PLAYING who is ruled out (e) "full squad" for a team we hold no data on (f) after the game, a man who played still "missing" -> `card_report_status` / `fresh_card_facts`, the "full squad" gate, `played_anyway` |
| 🥅 🧱 goalie lines · the ⚠️ goalie knock | box scores + Daily Faceoff's starters page (stale after 8 hours) | a PROJECTION at 8 AM | the 11/12 check swapped a changed projection | a flat "tonight's goalie" needed a confirmation; a hedged line stood | **18 of 51 wrong** -> from the 11/18 games a goalie's numbers show only once he's CONFIRMED (`GOALIE_SURE_FROM`); a graded card keeps only the man who started |
| 🎯 🗑️ quarterback lines | box scores + `qb_depth.json` + the report | this run | re-checked every run since 11/16 | yes (11/16) | a graded card kept the wrong man -> the box-score rule (`started`) |
| 🏀 the roster line ("a game-time call") · 🌟 the stars "in the lineup" | `sports_nba_roster` / `nba_stars.json` + the report's flags | the 8 AM run | frozen | **no** | a star ruled out at 4 PM stayed "in the lineup" -> every name re-read each run; only the part about the man comes off |
| 🍀 puck luck · 🎲 goal luck | the box scores (10 games) | this run | frozen, still true | no | not re-derived by the audit (a game-day number can't move) - left as a known gap |
| 📊 the public's split | `public.json` | hours old, moves all day | - | off every card since 11/12 (the guard drops it) | none |
| 🧯 news · 📣 talk | `news.json` (10 days) - the headline quoted | this run | frozen | whose story it is (11/15, 11/16) | the quote can't be re-derived; a story can age inside the day - a known gap |
| 🏟️ weather / dome · 🚨 stakes · 🏈 bowl | the forecast on the game file · the standings | this run | the forecast can move | no | not re-read - a known gap (football only) |
| ✅ the bottom line · the units line | the pick, its price, `card_fair` | - | the posted price, by design | yes | none new |
| ⏰ 🎯 early plays - the why line + fact lines | the early model + the game files, written **days ahead** | the post | **frozen for days** | wording and line-move talk only | a record / last-game margin / "week off" could sit there after the teams played again -> `early_fact`, re-read every page build |
| 📝 the review | rebuilt from the final score and the period scores every build | always current | always current | the guard | the audit now checks the score in it - 45 of 45 right |

## 4. Root causes and fixes

1. **A goalie's numbers for a man who doesn't start (18 of 51).** The card was written at 8 AM off a projection and a
   hedge was treated as good enough. Fix: `sports_card_check.who_plays` - from the 11/18 games the line shows only once
   the goalie page has confirmed him (it is kept on the card and appears the minute he is); `fresh_card_facts` now
   watches goalies named in a risk line too; a graded card keeps only the man the box score says started (goalies and
   quarterbacks). For the dog code's owner: the hockey dog score's "hot goalie" angle reads the same projection.
2. **The injury news on a card only moved one way.** The 11/12 check re-read the card's lists for a man who came off
   the report. Fix: every man a card names anywhere is stamped with the report's word at posting
   (`sports.card_report_status` -> `rep_status`) and re-read every run: questionable -> OUT, out -> questionable, a star
   "in the lineup" who is out now, a "game-time call" that got decided, "full squad" once the report lists anyone -
   each with a 🔄 Update line; a 🏀 / 🌟 line loses only the part about that man. "Full squad" is never written for a
   team the injury data doesn't cover. On a graded card a man who played is no longer "missing".
3. **Numbers nobody re-read.** Points a game, who played last night, the road-trip count, the last meeting: now
   re-derived on every build (`stats`, `played_last_night`, `road_trip`, `last_meeting`).
4. **Lines that say nothing.** "+0 a game", "4 for / 4 against", the garbled last meeting, another sport's word, rest talk
   with no back-to-back, a card contradicting itself: `sense`, `rest_talk`, `card_sense` - and the pools fixed
   (`sports_breakdown_v24.more_facts`: one decimal in hockey / baseball, no zero margin, "X beat Y 6-0 the last time
   these two met").
5. **An early play's line frozen for days.** `early_fact` / `early_lines` re-read it every build.
6. **Nothing was watching.** `tools/card_audit.py`: every live card, as the page shows it, re-derived each page build ->
   `data/sports/card_audit.json`; a bad line is a `CARD AUDIT:` line in the run log and a PROBLEM on the hourly bug check
   (`tools/health.py`).

## 5. What is still not re-derived (honest)

The trip's miles, the weather line, a quoted headline, puck luck / goal luck. The injury feed itself can lag (a man still
listed "out" who plays - 3 times in 16 days): the card follows the report the minute it moves, and the graded card drops
him, but nothing we hold can know sooner than the report does.

## 6. Tests

`test_cards_1117_*` in `sports_test.py` (six): the derived checks, the card that fights itself / the man who played, the
goalie rule, every name re-read, the early line, the standing audit + the real 11/1 - 11/16 cards (0 problems as shown).
