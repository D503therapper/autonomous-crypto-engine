# 11/23 - DOUBLE-CHECKED, EVERY SOURCE: how right were the cards?

The owner, 11/23: "I just want to make sure we're always getting the accurate information across lines, injuries,
everything, and double checking sources always." His friend Victor: "It's been wrong on a lot on injuries and starters
tho. It said Darren Waller was out for Panthers and he was playing."

`python results/studies/accuracy_1123/measure.py --list` (no request goes out; output in `measure_out.txt`, every row in
`measure.json`). Every posted pick (picks.json) and early play (early.json) from 11/2 to 11/23 - 66 board cards (53 of
them make an injury / starter claim), 21 early plays - each claim against what happened: the box scores (who played, who
started in net, who threw the passes) and, for prices, our own time-stamped line tape at the post minute.

## Injuries and starters

| claim on the card | n | right | wrong / stale, the card said so before the start | wrong / stale, the card NEVER said so |
|---|---|---|---|---|
| a man listed OUT (138 with a box score to check; 13 more with none) | 138 | 134 (97.1%) | 1 (Scottie Barnes, 11/15) | 3 (Ziaire Williams 11/2; Patrick Kane and Sandis Vilmanis 11/12) |
| a man listed QUESTIONABLE / a game-time call | 15 | - (6 played, 9 sat) | 0 | **15 - the card never said how one of them ended** |
| a star "in the lineup" | 5 | 5 | 0 | 0 |
| a goalie the card gave numbers for | 32 | 22 started | 4 | 6 (all 11/2-11/14; none since the 11/16 fix) |
| a quarterback the card gave numbers for | 15 | 14 | 0 | 1 (Carson Wentz, 11/15 - fixed 11/16) |

The update lines the cards showed after posting:

| update | n | right |
|---|---|---|
| "is OUT now" / "is out too" | 14 | 14 |
| a goalie confirmed / changed | 10 | 10 |
| **"is off the injury report" (the alert) / "expected to play" (the 🔄 line)** | 10 | **3 - seven of those men SAT** |

What was wrong:

1. **The questionable men were never settled (0 of 15).** The 11/22 Panthers card had Tommy Tremble and Darren Waller
   questionable - true when it posted. Both played, and the card never said another word. Two causes: (a) the header's
   game-time men (`our_q`) were not among the names the injury watch re-reads at all; (b) ESPN's report keeps
   "Questionable" on a man straight through a game he plays in - the report alone can never settle him. Nothing read the
   NFL's game-day inactives or the live box score.
2. **"Off the injury report" was said of men who had been ruled OUT (5 of the 7 misses, all on the 11/23 NBA cards:
   Joel Embiid, Jaylen Brown, Shai Gilgeous-Alexander, Pascal Siakam, Aday Mara).** The watch's key list carries an NBA
   man only while he is questionable (`sd.team_key_out` leaves the NBA out); ruled out, he left the list, and two runs
   later the alert said "off the injury report" - on the same card as a 🔄 line saying he was out. The Avdija class
   (11/17) was still alive through this door. The other two: Avdija himself (11/17, before the two-run rule) and Adem
   Bona (11/23 - really off ESPN's list for two runs, "expected to play", and he sat: the words were stronger than the
   source).
3. **Three men listed out who played, never said** - all before 11/13 (two were box-score guesses the report never
   made - fixed 11/12). Zero since.
4. **Six goalies and one quarterback named who didn't start, never said** - all on or before 11/15; zero since the
   11/13 / 11/16 fixes.

## Prices

| check | board moneylines (63) | early moneylines (13) |
|---|---|---|
| the posted price is the number on our own line tape at the post minute | 62 of 62 (1 game had no tape row) | 13 of 13 |
| the posted price sits inside the game's open-to-close range (3 points of slack) | 62 of 63 (Broncos -142 on 11/8: on the tape at the post, the game opened and closed -162) | - |
| **a second source's number was saved beside the posted price** | **0 of 63** | **0 of 13** |

Every posted price was really the feed's number - but the tape IS the source (ESPN's scoreboard, DraftKings' line). No
posted price had been looked up anywhere else. The paid odds history does not overlap these three weeks (football ends
9/29, the NBA / NHL files in 2023), and no second-source pregame number was kept at post time, so "would a second source
have confirmed it" cannot be answered for the past - only from here on.

## What was fixed (no pick, price or size logic changed - facts and flags only)

- **The game-day read** (`sports_gameday.py`): inside the game-day window every man a card has questionable or out is
  looked up on (1) the NFL per-game roster - active / inactive once the inactives are filed, read only when the answer
  looks like a real inactives list - and (2) the live box score once the game is on (a man with minutes / a stat line
  is playing). The card says what the source shows: "🔄 Update: Darren Waller is active for the Panthers." / "is
  playing" / "is OUT now"; he leaves the ❓ line. No source says = he stays a game-time call - never "out", never
  "playing". The game-day word outranks the report from then on. The live watch keeps re-reading a started game while a
  man is still on its ❓ line (`sports_live.card_news_due`, 150 minutes).
- **The header's ❓ men are watched** (`sports.card_report_status` reads `our_q` / `opp_q`): questionable -> OUT and off
  the report now make their update line like every other name on the card.
- **"Off the injury report" asks the report first** (`sports.injury_watch` / `_report_word`): a man still on it is said
  by his real status ("is now out"), never "off".
- **"Off the injury report now." - no more "expected to play"** (board and early cards): what the source says, never
  stronger.
- **Every source's own word is kept** (`sd.INJ_SRC`, `sd.said_as`): ESPN / Rotowire / Covers / the official reports.
  Two that disagree (one out, one questionable) = the cautious word on the card - off the 🚑 OUT list, on the ❓ line
  (`sports.source_check`, `sd.cautious_rows`) - and a health-check PROBLEM names him. The engine's own read keeps the
  merged rows.
- **Every posted price gets a second look** (`sports_verify.py`): Action Network's consensus line (the plain v2
  scoreboard the odds history is built from), BetRivers' pregame list when Action Network gives nothing. Stamped on the leg as it posts
  (`price_2nd`: confirmed inside 3 points of win chance / the same number on a spread or total, NOT confirmed with both
  numbers, or single-sourced), printed loud in the run log and the pick check. Never a pick held for it.
- **The standing health line** (`tools/card_audit.py` "double_check" -> `tools/health.py`): every hour, every injury /
  starter / price claim on the live cards with what backs it. Sources that disagree or a price a second source doesn't
  show = a PROBLEM that names the card; single-sourced claims and men still waiting on a game-day word are named on the
  line.

## Still single-sourced, and why

- **Pro injury statuses (NFL / NBA / NHL / MLB): ESPN's injury feed alone.** No second plain reader exists for the
  leagues' own reports (the NBA's official report is a PDF, the NFL's sits behind its own site). The game-day read is
  their second check; before game day a pro "out" is one source's word and the health line says so.
- **The NFL inactives list is not verified from here.** The sandbox this was built in can't reach ESPN, so the per-game
  roster's shape was coded from the documented fields and guarded hard (40-80 men, 2-14 inactive, or it says nothing).
  If the first live Sunday shows `espn_gameday_roster` quiet in source_status.json, a questionable NFL man is still
  settled by the box score minutes after kickoff, not 90 minutes before. `tools/capture_sources.py` now captures the
  11/22 Panthers roster so the shape can be checked.
- **An NBA starting five is not claimed before the tip** - a starter flag before the game may be last game's. Settled
  by the box score once the game is on.
- **A man who SITS is only ever settled by the report or the inactives list** - a box score shows who played, never
  who won't.
- **Spreads and totals have one second source** (Action Network); BetRivers is read for moneylines only. Action
  Network's consensus is a blend that includes DraftKings - a second look, not a fully independent one.
- **College injuries** stand on whichever of ESPN / Covers / Rotowire / the official report lists the school; many
  schools are on one.

Tests: `test_accuracy_1123_*` (five) in sports_test.py.
