# 11/19 - BUG + BREAKDOWN SWEEP

The owner, 11/19: *"sweep on bugs and breakdowns."* The three sweeps before this one (`sweep_1117` - the pipeline,
`cards_1117` - every fact true and current, `cards_1118` - the case for our side, the refill, the floor) fixed what he
caught. This one went looking for what nobody had caught yet: the last 48 hours of the run log and the checker files,
the code that shipped 11/17-11/19, and a dry run of the 11/19-11/22 slates read line by line (2 picks + 49 candidate
cards for 11/19, 34 college football cards for 11/21, 2 picks + 6 NFL cards for 11/22 - every card as written AND as
the page's check shows it).

**No pick, price, size or weight on a posted play changed.** Two fixes touch the engine's read (the time-zone factor,
which was wrong; the altitude *reason*, which is a label - the weight is untouched). Breakdown VERSION 69 rewrites the
open cards. Tests: `test_sweep_1119_*` in `sports_test.py` (six). The phone layout check (`tools/layout_check.js`) was
run on the page built from today's files and on a stressed early box (two injury alerts and an update line on every
early row, a game-day total with extra fact lines): clean at 320 / 360 / 390 / 430px.

How it was read (no network in the sweep's box - the injury report was the official files only, so who's-out lines in
the dry run are not the real thing; goalie lines and football line / secondary injuries belong to the two other runs):

    python tools/card_audit.py                # the live cards
    # the dry run: sports.post_board for a day + sports_breakdown.breakdown on every priced moneyline side
    # -150..+350, each card then put through sports_card_check.check / check_one the way the page does

## 1. Bugs - worst first

| # | what | root cause | fix | test |
|---|---|---|---|---|
| 1 | **The 🏀 NBA over posted two days early.** Raptors @ Pistons over 227.5 went up Wednesday 6:21 PM PT for FRIDAY's game. Both teams were playing that night - "out" on the report meant out for that night. | `sports_nba_out.candidates` had no game-day rule (its own doc says "a game-day total"); any `pre` game with 3+ of the six listed out posted after the 50-minute clock. | `GAME_DAY_ONLY`: made on the game's own Pacific day or not at all. The posted play stays (a posted play is never pulled) - its card already drops a man who comes off the report. | `..._the_nba_over_posts_on_its_own_game_day_only_...` |
| 2 | **The read called home teams "off their home time zone".** 41 of 141 college football games the week of 11/19 (and Colts @ Texans): the travel factor gave the HOME team an hour of jet lag. Card: "Body-clock problems for Florida St" - in Tallahassee, on an NC State card. | A game's `tzo` is the venue's clock offset on game day, so it moves an hour when the clocks change (11/1). `sports_model.Elo` compared it raw with the offset of the team's last home game - October -4 vs November -5. It happens every November and March until each team has played at home again. Size: about 1 point of win chance in college football, 2 in the NFL (the travel weights 0.112 / -0.266). | `sports_model.std_tz` / `us_dst`: offsets are read on standard time; a team in its own building never crossed anything. A real trip still counts in full. | `..._a_home_team_is_never_off_its_own_clock_...` |
| 3 | **"Altitude edge" as a named reason on nothing.** "UTEP gotta breathe 3,900 feet up" at New Mexico St (El Paso sits 3,700 feet up); the Vikings floor play in Mexico City read "Mile-high problems for the 49ers" - a neutral site, both teams climb. | `sports._reasons` named it at a 0.05 feature (50 meters more than the visitor's own home) and at neutral sites (Minneapolis is 750 feet higher than San Francisco). A named reason counts toward the floor's "named reason" rule, so it could hold a play up alone. | `sports.ALT_REASON_MIN`: a named reason (and a card line) only when the other team climbs 300+ meters above its home, never at a neutral site. The weight in the own read is untouched. | `..._altitude_is_a_named_reason_only_on_a_real_climb_...` |
| 4 | **The page's fact check cut TRUE lines** (a cut line is a thinner card). (a) "Knicks about to get their ass beat — 7-2 at home for the Timberwolves" pinned 7-2 on the Knicks ("the games say 4-3") and dropped the one-liner; (b) "It's 12-10 (the Avalanche) against 11-11 (the Ducks)" the same; (c) "Don't let 5-5 fool you — Iowa State took those L's from ..." - "took" made the record a score "that isn't in their last 6 games"; (d) "The Steelers got their cheeks clapped 38-18 by the Bengals" cut off a long dog's card as a "sure-thing call". | `sports_card_check.facts` took the nearest team name BEFORE a record; the "for the X" / "(the X)" after it only counted when it followed at once. The long-dog rule matched the phrase, not the tense. | The team named after the record ("7-2 at home for the ...", "(the ...)") owns it; "don't let N-N fool you" is a record; a blowout phrase with a final score and no call word is a fact (`_past_game`). A wrong number is still caught. | `..._the_fact_check_reads_whose_number_it_is_...` |
| 4b | **Rivalry cards lost their best lines.** Oregon vs Oregon St, Texas vs Texas Tech / Texas A&M, Florida vs Florida St, Iowa vs Iowa State, Miami vs Miami OH, New Mexico vs New Mexico St, Washington vs Washington St: on the SHORTER-named team's card, "Oregon St have lost 5 straight" read as a knock on Oregon and came off - every line about the other side's losses, and the one-liner with it. | `knocks_us` looked for our name anywhere in the clause; "oregon" sits inside "oregon st" (the 11/18 "st in lost" bug's cousin). | A hit inside the other team's longer name is not us. Both directions under a test, eight rivalries. | same |
| 5 | **A one-liner whose tail was rewritten skipped every other check.** "The Blues had 3 fewer days off than the Penguins" stayed up in hockey (rest is talked about only on a back-to-back). | `check_one` ran the fact / who-plays / rest / jargon checks only `if not w` - once the wording check had cut "Close to 50-50 ..." nothing else ran. | Every check, every time. `REST_TALK` also reads "more days to rest". | same |
| 6 | **A check that fired every run for three days.** `CARD CHECK (render): Wyoming 245: line-move talk` - 56 lines in the log; "0-1 since we started betting it" on the altitude over the same. | The page was right (it cut the sentence), but the row was SAVED with the bad wording before the pool was fixed, so the catch came back on every build and filled `pick_audit.json`. | `sports_early.heal`: an open early row's wording slips (line-move talk, a losing live record, a knock on our side) are fixed once, in the file. The pick, price and units never change. | `..._an_early_row_is_healed_once_...` |
| 7 | **Early plays vanished from the page after midnight.** From 12 AM PT until the board's day rolls (1 AM, or 8 AM when a game from yesterday is still open) a play whose game is "today" was in neither box. | The ⏰ box used the clock's date ("game day = not early"); the 🎯 box used the board's day (still yesterday). | `sports_early.html(day=)`: the play stays in the early box until the board's day reaches its game day. | same |
| 8 | **The newest injury word could lose a merge.** Two jobs write `early.json`; the copy that was "ours" won every field - a job that loaded the file before the other stamped "ruled out" wrote its empty alert back over it (the ⚠️ line gone until the next hourly run). | `merge_early` had no rule for the watch's fields. | `_newest_watch`: the watch's fields come from the copy whose injury log has the newest entry; the log is the union. | same |
| 9 | **An early play kept the start time it posted with.** A game the league moves (a flexed kickoff, a time set on a TBD game) kept the old day and hour on the row - the wrong box, the wrong "game starts at". | Nothing re-read the schedule for a posted early row. | `sports_early.sync_starts`: an open row takes the schedule's start as it reads now (never a TBD time); the old one is kept. | same |
| 10 | Tennis could post 20 minutes before a match (the board's rule since 11/18 is 35 - a run takes ~12 minutes to reach the page). | `sports_tennis.MIN_LEAD_MIN = 20`. | 35. | same |
| 11 | An early play's grade was stamped with the wall clock, not the run's clock (the rest of `grade` uses the run's). | `datetime.now()` in `sports_early.grade`. | `now`. | same |

## 2. Breakdowns - what read wrong, fixed at the pool

| what the card said | why it's wrong | now |
|---|---|---|
| 🧠 Tulane got 3 more days to rest than Louisiana Tech did. | Rest talk in college hoops / hockey / the NBA / baseball is only for a back-to-back (11/15). The why-map still handed the one-liner the rest gap. | No rest words in those leagues (`why_map`); football keeps them. |
| 💪 4-0 vs 3-1 looks even. Who they've played says Charleston. | Names nobody. Never vague. | 💪 4-0 vs 3-1 looks even - but Charleston beat Liberty 80-70, a better team than anybody Drake beat. (only when the ratings back it; else no line - `_best_win_line`) |
| 🔥 The Ravens have lost 5 straight — that coach is on the hot seat. / Jobs on the line over there. / are in a fishbowl right now. | The engine holds a losing streak. Nobody told it about a coach's job, and nobody says "fishbowl". | 🧊 The Ravens have lost 5 straight. - and never twice on one card (the same streak under the pick and again in the body: `no_repeats` rule (f)). |
| 📣 The Ravens in the papers: "Ravens' Flowers 'super frustrated' by latest late-game fumble" - on a RAVENS card | Our own team's bad press is a knock on our pick. | Never on our card (`TALK_KNOCKS_US`); the other side's still is. |
| 📣 Out of the Ravens's camp this week | "Ravens's" | the Ravens' camp |
| 📅 Last game for each: Charleston So W 92-68 vs West Georgia · Wofford L 92-97 @ Queens. | A box-score line, the loser's score first. Never robotic. | 📅 Last game for each: Charleston So got a 92-68 win over West Georgia · Wofford took a 97-92 loss to Queens. |
| ⚖️ Same kind of record, tougher schedule: Panthers lost to Bears, Browns, Buccaneers, Packers and Broncos. | Reads as a knock on our own side - the page's check cut it every time (a pool writing a line the check kills). | ... tougher schedule: Panthers' L's came against Bears, Browns ... (passes; the "·" in a two-game line no longer makes their loss read as ours) |
| NBA over: "Pistons should score about 114 ... - 225 with everybody, the number's 227.5" | On an OVER card that argues the under. | The projection is a line only at or over the number; "7 of the Pistons' last 10 games went over 227.5" is said when the files back it (6+ of the last 10). The posted card loses the line on the page. |
| NBA over: "2-0 since we started betting it" | A line with no subject (the record clause before it was already in the line above). | We're 2-0 on this play since we started betting it (a losing live record is never a line) |
| NBA over: "Cavaliers without Donovan Mitchell (33 minutes a night) and James Harden (33 minutes a night) and Evan Mobley (32 minutes a night)" | "and ... and" | Cavaliers without Donovan Mitchell (33 minutes a night), James Harden (33 minutes a night) and Evan Mobley (32 minutes a night) |
| 📅 How they came in: Stars got a 4-3 win over the Golden Knights · Golden Knights took a 4-3 loss to the Stars. | These two just played each other - one game said twice. | The game once: 📅 How they came in: Stars got a 4-3 win over the Golden Knights. |

## 3. Left for the owner / next

- **The Raptors @ Pistons over 227.5 (½u, Friday 4:30 PM PT) is up two days early.** It stays posted (his 11/16 rule).
  If Cunningham / Robinson / Barrett come off the report the card says so. His call if he wants it down.
- **The question box still says "lean"** ("The engine's numbers lean X", "Slight lean our way") for games that are not
  on the board. Leans are out of existence on the board, the records and the results; the question box's read on an
  off-board game was left as it was. If he wants the word gone there too it is one pool in `sports_dashboard.py`.
- **The NFL "East Coast team flying West" early spot** reads time zones raw as well (`sports_early.spot_scan`: home
  offset -5 or more, game -7 or less). On daylight time that makes a Central team "East" and leaves Denver out; on
  standard time it is the other way round. It is a studied spot's definition - a Fable study should say which one the
  study meant before it is touched. Same for `sports_totals` / `sports_nba_open`'s travel inputs (the same raw read;
  small, inside fitted models).
- **Mexico City (Vikings +136 vs 49ers, 11/22):** the read still carries a small altitude weight for the Vikings (the
  factor is the difference in each team's climb - 750 feet). About 1.5 points of win chance. The label is gone; the
  weight is a model question.
- **The head-to-head line** is written on almost every card and dropped by the card guard every time (by design since
  10/5). It costs nothing on the page but it is log noise on every write.
- Not looked at here (the two other runs): hockey goalie lines / price timing, football line and secondary injuries.
  In the dry run every unconfirmed-goalie line was cut by the page as designed - which is why a morning hockey card
  shows no goalie line and no ⚠️ line until the starters are confirmed.
