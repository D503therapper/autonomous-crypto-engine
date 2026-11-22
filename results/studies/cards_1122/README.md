# 11/22 - THE CARD SELLS THE PICK

The owner, 11/22, after four card passes (cards_1117 every line true, cards_1118 every line for our side, cards_1119 the
story of the game, cards_1119b the card as a whole): **"The breakdowns are short and vague"** and **"Run fable perm fix
this the breakdowns basically need to sell our picks why we taking them and needs to be in our lingo."** Earlier the
same day: "We can't say best dog on the slate but it's a half unit makes no sense. Half unit is a thin edge tread
lightly" (fixed live in VERSION 82).

**No pick, price or unit size changed.** Wording only; `sports_breakdown.VERSION` 83 rewrites the open cards on the next run.

## 1. What was wrong

The two college hoops dog-slot cards of 11/22:

| on the card | why it's wrong |
|---|---|
| Robert Morris +102 1u: "📊 New Mexico St this season: 78 points a game allowed, 66 scored" and, right under it, "📊 New Mexico St have been outscored 72 to 63 a game over their last 3" | THE SAME STAT TWICE - two of the card's three body lines. And the season number counted a win over Western NM, a non-D1 school. |
| Nicholls +195 1u: "Last 3 for Troy: 73 scored a game, 77 given up" under the pick, "On the year Troy gives up 77 points a game and scores 70" in the body, Troy's last game - and nothing else | two lines, one of them the line under the pick said again. |
| both | NOT A WORD OF WHY. The engine was on these two because of a dog read of 4 - how the two teams play, plus a study angle. The card said who lost last. Every line was true and for our side - the four passes before this one all pass these cards. |
| Wizards +170 ½u (the good one, 8 lines) | led with "The Wizards are on a 2-game winning streak" while its body held a 103-94 win over the Magic this year. |

Where it came from:

- **the write-up had no pool for the matchup on the floor.** The files hold both teams' full TEAM box score for every
  game (`data/sports/teamstats/<league>.jsonl` - shooting, threes, free throws, rebounds, turnovers, steals, assists,
  points in the paint, fast-break points; hockey's shots and power plays; football's yards, third downs, sacks,
  giveaways). The engine's weights read them. No card line did - the only box-score lines were three player-box sums
  over the last 4-5 games, and college hoops had one (rebounds).
- **the refill said the scoreboard twice by design** - "lately" and "on the year" were two different keys, so both went on.
- **the line under the pick took the first pool with a fresh wording** - their last loss, or the leg's generic top fact
  (a 2-game streak) - and nothing ranked a real reason above it.
- **college hoops' early-season cards are starved by the rules that keep them honest** (no record / skid / beatdown line
  off losses to teams rated above us - the Oakland rule), so a 1-4 team against a 1-4 team had nothing left.

## 2. The rule

1. **The matchup on the floor, off both teams' box scores** (`sports_card_sell.py`). Each line is a real number, both
   teams' when it's a matchup, said only when it argues for us:
   - hoops: 🧲 the glass, 🧤 turnovers / 🥷 steals, 🛡️ the defense we bring against what they shoot, 🪣 what we shoot against
     what they allow, 👌 three-point luck (their threes running hot, or teams missing everything against them - said as it
     coming back down, never as praise) and our threes against what they give up, 🎁 the free-throw line, 🎨 the paint,
     💨 the break, 🤝 assists;
   - hockey: 🏹 who outshoots who on the year, ⚡ the power play against the kill - as COUNTS ("scored on 16 of 32 power
     plays"), never a rate (the 11/17 layman's-terms rule);
   - football: 🏃 the ground, 🎈 the air, 🧤 giveaways, 🔗 third down, 💥 sacks, 📏 yards;
   - 🏆 our best win this year, when it came over a team rated above tonight's opponent - said as the game it was.
   College hoops reads **D1 games only** (the lines say "against D1 teams" - the season scoreboard line too now), and two
   teams' numbers are set against each other only when their schedules were about as tough (`SCHED_EDGE`: the teams
   they played rated no more than 50 points above the teams we played) - the Oakland 0-5 lesson, applied to stats.
2. **The reason leads.** A line the leg's own reasons point at is tagged reason-backed (`leg["sold"]`), opens the body,
   is never cut past the 9-line cap, and takes the line under the pick whenever that line came out of a fallback pool
   (a streak of 2, a last game, a home record - `WEAK_LEAD`) or was only their last loss. With no reason line, the game
   these two already played this year leads (🆚); else the best matchup stat. A named absence, a back-to-back, a goalie
   or a quarterback reason still leads over all of it (THEIR BEST MEN OUT LEAD THE LINE stands).

   | the reason the leg carries | the line that says it |
   |---|---|
   | the dog read's turnover weight (`to_net`) | 🧤 "New Mexico St cough it up 19 times a game against D1 teams. Robert Morris: 14." |
   | "the glass" (`reb_gap`, `hoops_inside`) | 🧲 "X out-rebound teams by 7 a game. Y get beat on the glass by 4." |
   | the three-point-luck fade on the side across (`opp_tp_net`, `opp_hot_deep`) | 👌 "D1 teams are 45 for 171 from three against Troy - 26%. Nobody guards the arc that good." |
   | a defense-first dog against a bottom-third offense | 🛡️ the shooting we hold teams to / 🥷 our steals |
   | the ratings backing the side (the dog read, the gap play, a favorite) | 🛡️ / 🪣 the shooting matchup, 👌 our threes against theirs |
   | "the favorite lost its last" | 📅 / 🥊 their last game, with the score (was there already) |
   | hockey puck luck (`pdo`) | 🏹 shots on net, both ways |
   | "wins inside" (NBA) | 🧲 the glass / 🎨 the paint |

   Never "our ratings say" (two pool lines that did are gone; the page cuts it - `Q_RATINGS`), never our number against
   the books', never a study's win rate as a line, never the line moving.
3. **No repeats.** The same stat about the same team is one fact (`sports_card_sell.same_stat`): the season's points
   and the last 3's points, two rebound lines. What a team scores and what it allows are two facts; the margin line is
   either one again. The season line stands unless the last 3 are a different story (6+ points better / worse).
   Enforced at the pool (`fill_facts`), in the write-up's last step (`story_close`) and on every render
   (`sports_card_check.check` - `Q_SAME`) - on cards the sell writer wrote (VERSION 83+, `same_on`): a card from an
   older version whose game already started can't be re-written, so the page leaves its lines alone rather than make
   it shorter (today's posted Robert Morris / Nicholls cards stay as they are until they come off the board).
4. **Every box-score number is re-derived on every render** (`sports_card_check.sell_numbers` -> `Q_BOX`): a number the
   two teams' boxes don't hold for that stat cuts the line.
5. **The floor stays 6-9 fact lines** - and when the files truly hold less, the card says fewer. Never padding.

## 3. The counts

"Says why" = a reason-backed line (a reason the leg carries, said as a fact) or a matchup line (a box-score edge, the
game these two played, a common opponent, who each side beats). Counted by `sports_card_sell.reason_backed` - the same
function the standing audit uses. "Yesterday's writer" = today's code with the sell layer switched off (VERSION 82).

| what | cards | fact lines a card | cards under 6 | same-stat repeats | reason-backed lines | lines that say why (reason + matchup) | line under the pick says why | filler |
|---|---|---|---|---|---|---|---|---|
| posted 2026-11-08..11/22, as written | 37 | 7.6 | 9 | 11 | 46 (27 cards) | 60 (31 cards) | 13 | 12 |
| the same cards, re-written by yesterday's writer (v82), on the page | 37 | 7.1 | 6 | 13 | 30 (21 cards) | 69 (35 cards) | 13 | 0 |
| the same cards, re-written now | 37 | 7.3 | 5 | 0 | 38 (24 cards) | 98 (35 cards) | 21 | 0 |
| re-written, as the page shows them | 37 | 7.2 | 5 | 0 | 36 (23 cards) | 95 (35 cards) | 21 | 0 |
| 2026-11-22 candidates, before | 32 | 6.6 | 8 | 9 | 11 (10 cards) | 39 (21 cards) | 9 | 0 |
| 2026-11-22 candidates, now | 32 | 6.7 | 7 | 0 | 16 (15 cards) | 67 (29 cards) | 19 | 0 |
| 2026-11-23 candidates, before | 15 | 7.3 | 2 | 4 | 5 (4 cards) | 28 (12 cards) | 3 | 0 |
| 2026-11-23 candidates, now | 15 | 7.3 | 2 | 0 | 6 (5 cards) | 40 (14 cards) | 7 | 0 |
| 2026-11-24 candidates, before | 2 | 7.0 | 0 | 2 | 0 (0 cards) | 1 (1 cards) | 0 | 0 |
| 2026-11-24 candidates, now | 2 | 7.0 | 0 | 0 | 0 (0 cards) | 3 (2 cards) | 2 | 0 |
| all candidates, before | 49 | 6.8 | 10 | 15 | 16 (14 cards) | 68 (34 cards) | 12 | 0 |
| all candidates, now | 49 | 6.9 | 9 | 0 | 22 (20 cards) | 110 (45 cards) | 28 | 0 |

Honest about these numbers:

- **Fact lines a card barely moved** (7.1 -> 7.2) - the cards were already at their floor after the 11/18-19 passes; the
  change is WHAT the lines say. The short ones that moved: Robert Morris 4 -> 8, Nicholls 3 -> 5.
- **"As written" is not the same writer** - cards from 11/8-11/18 were written by older versions (the ⚠️ risk line, price
  math, public splits). The fair before / after is the "yesterday's writer" row.
- **No network in this session**: the pros' injury reports in the re-writes are the ones each posted card stored; the
  candidate sides were written with no report (no injury lines either way). The NBA roster line (🏀 "8 guys play real
  minutes") is built with the live board and is missing from the re-writes - the live Wizards card keeps it.
- **2 of the 37 re-written cards still have no line that says why** (Heat +160 vs Pistons (11/14); UT Rio Grande +160 vs Austin Peay (11/21)): the boxes held no real
  gap for our side (or the schedule guard kept the comparison off) and there was no meeting / common opponent. They
  are the "no why" class the hourly audit now names on cards posted from 11/22.
- The reason-backed count is conservative: a 🧳 trip or a 📅 last-loss line counts only when the leg carries that reason.

## 4. What changed - at the root

| where | what |
|---|---|
| `sports_card_sell.py` (new) | `profile` (a team's season off the team boxes, both ways), `hoops_lines` / `hockey_lines` / `football_lines` / `best_win`, `sell_facts`, `lead_from`, `same_stat` / `dedupe`, `numbers_wrong`, `reason_backed`; switch `SELL` |
| `sports_breakdown_v24.breakdown` | the sell lines are built before the line under the pick; `lead_upgrade` (two passes: a reason line, then the meeting / the best stat); the lines open the body; `SELL_FROM` "2026-11-22" |
| `sports_breakdown_v24.story_close` | reason-backed lines first and never cut; the same-stat dedupe |
| `sports_breakdown_v24.fill_facts` | one scoreboard line a team; college hoops season lines on D1 games only ("against D1 teams"), 3+ of them; "75 against 76" is no line (a 3-point gap in hoops); "their only win came over a non-D1 school" |
| `sports_breakdown_v24` pools | "our ratings have X ahead" / "the ratings like X" out; the tail "Not us. We got X." out; a non-D1 win is never "last game" under the pick; the 🆚 wording that failed the guard fixed |
| `sports_card_check` | `sell_numbers` (Q_BOX), the same-stat cut (Q_SAME) in `check` / `refill` / `quality`, `RATINGS_TALK` (Q_RATINGS), `says_why`, `d1_only` (the stats check reads the D1-only numbers too), a 🆚 line is the last meeting - not "their last game" |
| `tools/card_audit.py` | counts the lines that say why; a live unit card with none is a PROBLEM ("no why") on the hourly check |
| `sports_owner_lingo.SOURCES` | the new module is under the lingo tests (NEVER / STIFF / the eat ban) |

Bugs found on the way (all pre-existing, all fixed at the pool):

- one of the three 🆚 wordings ("These two met on 11/2 this year and X got a 103-94 win") failed the guard's
  THIS_YEAR_GAME and was dropped every time the Voice picked it - the card lost its best line;
- a 🆚 line that said "took the last one from the Senators this year - a 3-1 win" was read as "the Senators' last game
  ended 3-1" and cut as false on the page;
- "William & Mary just beat Averett 85-39, not us. We got William & Mary." - a tail that answered a public line the
  cards no longer carry, on a win over a non-D1 school that should never have led;
- "🛡️ On the year UT Rio Grande allows 62 a game, Austin Peay 66" - two blowouts of non-D1 schools in ours, three in theirs;
- the 11/22 morning fix made the last-3 line D1-only, but the page's stats check still read every game - a D1-only
  number that differed would have been cut as false. It reads both now.

## 5. The owner should know

1. **The Nicholls +195 "defense-first" fact stands on a tune-up.** `sports_ncaab_box.identity` reads every boxed game,
   so Nicholls' 110-56 win over N American (a non-D1 school) is in it: with it Nicholls allow 7.4 points per 100 trips
   under the D1 average (the cut for "defense-first" is 4.8); on their 5 D1 games it is 0.5. That fact is +2 of the dog
   read of 4 that posted Nicholls (and made it the ⭐). The card no longer claims it - it says the 9 steals a game, which
   is true against D1 teams. **Nothing in the engine was changed**: the 11/21 daily study S2 found the slot's dogs with
   2+ non-D1 games behind them still pay (+23.9% on 115). The open question is narrower - the defense-first cell re-cut
   with the identity on D1 games only - and belongs to the daily studies.
2. **The schedule guard costs lines.** With `SCHED_EDGE` at 50 the Northern Iowa / Oakland card (11/14) and the William &
   Mary card (11/22) get no box-score comparison - Oakland's and Youngstown St's schedules were 60 points tougher. At 75
   they would. 50 is the cautious call after "We can't be looking like some clowns"; it is one constant.
3. **Nicholls is five facts.** Every Troy loss came to a team rated above Nicholls (no record / skid line), Nicholls get
   out-rebounded worse than Troy do (no glass line), their top scorer is under the 14 a game the 💯 line needs. The
   card says what is there.
4. **Not every engine reason has a line.** The NBA dog score's small weights (pace, the size of the slate, the
   favorite's soft next game) and "sharp money moving this way" (never said - the 10/23 rule) have none. The trip, the
   meeting, the men out, the favorite's last loss and the box edges do.
5. `SELL_FROM` is the 11/22 game day: only open cards are re-written, as always.

## 6. Tests

`test_cards_1122_*` (five): the Robert Morris card off the real games and boxes (6+ fact lines on the page, the
turnover reason leads, one scoreboard line, D1 only, the wrong-number and same-stat cuts, the switch); the Nicholls
card (the luck as counts, the steals, the win, five facts, the schedule guard); an NBA floor card (the meeting leads, a
½u says thin edge, the guard passes every 🆚 wording, a named reason is never replaced); a hockey card (shots and the
power play as counts, re-derived); the standing rules (one stat a team, no "our ratings", no tune-up lead, the audit's
count). `timeout 900 python sports_test.py`: 811 tests ok, exit 0, no "FAILED:" line (368 seconds).

## 7. Before -> after, card by card

"As it posted" is the card on the page today / the day it ran. "Yesterday's writer" is that card re-written by VERSION 82.
"Now" is the same card re-written and run through the page's check.

### 2026-11-22 ncaab - Robert Morris +102 vs New Mexico St (play, 1.0u) - the card that set him off

As it posted (4 fact lines, 1 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🥊 Give me Robert Morris: New Mexico St got handled 84-69 by UTEP last time out.
  📊 New Mexico St this season: 78 points a game allowed, 66 scored. They get outscored.
  📊 New Mexico St have been outscored 72 to 63 a game over their last 3.
  ⚖️ Don't let 1-4 fool you — Robert Morris took those L's from Nevada, UIC, Arkansas and Toledo.
  ✅ Bottom line: Robert Morris (+102). Let it ride.
```

Now, on the page (8 fact lines, 0 repeats, 2 reason-backed, 4 matchup):

```
WHY: 🧤 Riding Robert Morris: 19 turnovers a game for New Mexico St against D1 teams, 14 for Robert Morris. Free possessions.
  🎨 New Mexico St gives up 30 a game in the paint against D1 teams and Robert Morris get 24 down there every night.
  💨 D1 teams get 13 fast-break points a game on New Mexico St. New Mexico St gets 5.
  🤝 Only 9 assists a game for New Mexico St against D1 teams - everybody for himself. Robert Morris get 13.
  📊 Against D1 teams New Mexico St gives up 82 points a game and scores 64.
  📋 The one win New Mexico St got this year came in a 73-66 game with Western NM, and that ain't a Division I school.
  📅 New Mexico St off an 84-69 loss to UTEP last time out.
  ⚖️ Don't let 1-4 fool you — Robert Morris took those L's from Nevada, UIC, Arkansas and Toledo.
  ✅ Bottom line: Robert Morris (+102). Give me Robert Morris.
```

### 2026-11-22 ncaab - Nicholls +195 vs Troy (play, 1.0u) - five facts: all the files hold for this side

As it posted (3 fact lines, 1 repeats, 1 reason-backed, 0 matchup):

```
WHY: 📊 We on Nicholls: Last 3 for Troy: 73 scored a game, 77 given up.
  📊 On the year Troy gives up 77 points a game and scores 70.
  📅 Troy comes in off a 77-72 loss to Valparaiso.
  ✅ Bottom line: Nicholls (+195). Get in.
```

Now, on the page (5 fact lines, 0 repeats, 3 reason-backed, 1 matchup):

```
WHY: 👌 Riding Nicholls: D1 teams are 45 for 171 from three against Troy - 26%. Nobody guards the arc that good. Those start falling.
  🥷 Nicholls take it right from you - 9 steals a game against D1 teams, 7 for Troy.
  🏆 A 71-68 win over Louisiana Tech at home is already on the board for Nicholls this year.
  📊 Troy this season: 77 points a game allowed, 70 scored. They get outscored.
  📅 Troy off a 77-72 loss to Valparaiso last time out.
  ✅ Bottom line: Nicholls (+195). We on Nicholls.
```

### 2026-11-22 nba - Wizards +170 vs Magic (play, 0.5u) - the good one - the meeting leads now, not the 2-game streak

As it posted (9 fact lines, 0 repeats, 1 reason-backed, 2 matchup):

```
WHY: 🧠 The Wizards are on a 2-game winning streak. We on Wizards.
  🆚 Wizards already beat the Magic this year - a 103-94 win on the road on 11/2.
  🧳 Travel check on the Magic: 3rd road game in 6 days.
  📊 On the year Magic gives up 113 points a game and scores 110.
  🧾 Magic only got 2 wins in 7 games against winning teams this year.
  📋 7-8 for Magic this season - more L's than W's.
  📅 Fresh off a 98-94 win over the Bulls for Wizards.
  💸 When the book makes Magic the favorite, they lost 4 of 8 this year.
  🏀 Wizards: 8 guys play real minutes.
  ✅ Bottom line: Wizards (+170). The dog angles like it. Ride it.
```

Now, on the page (8 fact lines, 0 repeats, 1 reason-backed, 3 matchup):

```
WHY: 🆚 We on Wizards: These two met this year and Wizards got a 103-94 win on the road on 11/2.
  🎁 Magic put teams on the line 25 times a game this year and Wizards live there (26 a night).
  🧳 The Magic: 3rd road game in 6 days.
  📊 On the year Magic gives up 113 points a game and scores 110.
  📅 Fresh off a 98-94 win over the Bulls for Wizards.
  🧾 Magic won 2 of 7 against teams with a winning record this year.
  📋 Magic sits 7-8. Losing record.
  💸 4 losses in 8 games as the favorite for Magic this season.
  ✅ Bottom line: Wizards (+170). Already beat 'em once this year. The dog angles like it.
```

### 2026-11-22 nfl - Panthers -145 vs Ravens (lock, 0.5u) - the 🧊 skid stays in the body; the passing matchup leads

As it posted (8 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🧊 Panthers the side: 5 straight losses for the Ravens, that's a shit spot for Ravens.
  🥊 The Ravens got smacked 33-10 by the Jaguars inside their last 5.
  🎬 3 of 4 wins by one score for the Ravens this year (the last two: 24-18 over the Titans and 30-23 over the Falcons). That's a team living on the edge.
  📊 Ravens have been outscored 31 to 13 a game over their last 3.
  📅 Last time out: Panthers got a 20-17 win over the Saints · Ravens took a 23-20 loss to the Chargers.
  📋 Ravens sit 4-6. Losing record.
  ⚖️ Same kind of record, tougher schedule: Panthers' L's came against Bears, Browns, Buccaneers, Packers and Broncos.
  📣 Out of the Ravens' camp this week: "Carmelo Anthony calls out Ravens' Humphrey over Baltimore 'criminals' remark"
  ✅ Bottom line: Panthers (-145). Ravens can't buy a win right now. Strongest favorite on the slate.
```

Now, on the page (8 fact lines, 0 repeats, 0 reason-backed, 2 matchup):

```
WHY: 🎈 Panthers throw for 253 yards a game this year and Ravens give up 220 through the air. Panthers the side.
  🥊 The Jaguars put 33-10 on the Ravens in one of their last 5.
  🧊 Losing streak at 5 for the Ravens.
  🎬 The Ravens keep winning by one score: 3 of their 4 wins this year, the last two 24-18 over the Titans and 30-23 over the Falcons.
  📊 Last 3 for Ravens: 13 scored a game, 31 given up.
  📅 Last time out: Panthers got a 20-17 win over the Saints · Ravens took a 23-20 loss to the Chargers.
  📋 Ravens sit 4-6. Losing record.
  ⚖️ Same kind of record, tougher schedule: Panthers' L's came against Bears, Browns, Buccaneers, Packers and Broncos.
  ✅ Bottom line: Panthers (-145). The side we trust most today, at a price that pays. That's money.
```

### 2026-11-22 ncaab - William & Mary -110 vs Youngstown St (play, 0.5u) - the ½u spread stack play

As it posted (8 fact lines, 1 repeats, 0 reason-backed, 0 matchup):

```
WHY: 🥊 Give me William & Mary: Youngstown St just got beat 91-54 by Cincinnati. Tap in.
  📊 William & Mary this season: 86 points a game scored, 78 allowed.
  📊 Last 3 for Youngstown St: 69 scored a game, 84 given up.
  📊 On the year Youngstown St gives up 83 points a game and scores 70.
  💯 William & Mary's top scorer Brian Carter Jr. is putting up 16 a night lately (5 games).
  📋 William & Mary is 4-2 on the year.
  💣 80+ points for William & Mary in 3 of their last 5. They can score.
  🏁 The first half, last 5 games: 214 points for William & Mary, 177 against.
  ✅ Bottom line: William & Mary -2.5 (-110). William & Mary the side today.
```

Now, on the page (6 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 📊 Give me William & Mary: On the year Youngstown St gives up 83 points a game and scores 70.
  🏁 The first half, last 5 games: 214 points for William & Mary, 177 against.
  📋 William & Mary sits 4-2 so far.
  📅 Latest: William & Mary got an 85-39 win over Averett (a non-D1 school) · Youngstown St took a 91-54 loss to Cincinnati.
  💣 80+ points for William & Mary in 3 of their last 5. They can score.
  💯 William & Mary's top scorer Brian Carter Jr. is putting up 16 a night lately (5 games).
  ✅ Bottom line: William & Mary -2.5 (-110). That's the bet.
```

### 2026-11-21 nhl - Flyers +136 vs Canadiens (play, 2.0u)

As it posted (8 fact lines, 0 repeats, 2 reason-backed, 1 matchup):

```
WHY: 🥊 Riding Flyers: Twice this year the Canadiens got blown out in their own building: 5-2 by the Predators and 4-1 by the Avalanche.
  🎬 9 of the Canadiens' 14 wins this year came by one goal - the last two 3-2 over the Devils and 2-1 over the Hurricanes. They been squeaking by.
  🧳 The Canadiens just got home - 3 road games in the last 6 days.
  🧳 Flyers won 2 of their last 3 on the road - a 4-3 win at the Blue Jackets and a 6-5 win at the Senators.
  🏟️ 5-6 at home for Canadiens.
  💣 3 of the last 5 times out, Flyers put up 4 or more.
  ⏱️ Canadiens gave up 14 goals in the third period over their last 10 and only got 7 back.
  📅 Flyers come off a 6-5 win over the Senators.
  ✅ Bottom line: Flyers (+136). We on Flyers.
```

Yesterday's writer, on the page (6 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: 📊 On the year UT Rio Grande scores 78 points a game and gives up 62. UT Rio Grande the side.
  📊 Last 2 for Austin Peay: 64 scored a game, 74 given up.
  ⏱️ The second half, last 5 games: 219 points for UT Rio Grande, 168 against.
  ⚖️ UT Rio Grande 3-2, Austin Peay 3-2 — but UT Rio Grande's L's came against Texas St and UT Arlington.
  📅 UT Rio Grande handled business last time, a 98-40 win over Biblical Stud (a no-name non-D1 school).
  🏁 The first half, last 5 games: 170 points for UT Rio Grande, 143 against.
  ✅ Bottom line: UT Rio Grande (+160). Give me UT Rio Grande.
```

Now, on the page (8 fact lines, 0 repeats, 2 reason-backed, 1 matchup):

```
WHY: 🥊 Riding Flyers: Twice this year the Canadiens got blown out in their own building: 5-2 by the Predators and 4-1 by the Avalanche.
  🎬 9 of the Canadiens' 14 wins this year came by one goal - the last two 3-2 over the Devils and 2-1 over the Hurricanes. They been squeaking by.
  🧳 The Canadiens back home tonight after 3 road games in 6 days.
  🧳 Last 3 on the road for Flyers: 2 wins, a 4-3 win at the Blue Jackets and a 6-5 win at the Senators.
  🏟️ 5-6 at home for Canadiens.
  💣 Flyers scored 4 or more in 3 of their last 5 games.
  ⏱️ The third period, last 10 games: Canadiens gave up 14 goals and scored 7.
  📅 Fresh off a 6-5 win over the Senators for Flyers.
  ✅ Bottom line: Flyers (+136). We on Flyers.
```

### 2026-11-21 ncaaf - Southern Miss +164 vs South Alabama (dog, 1.0u)

As it posted (5 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🧳 Ride Southern Miss — South Alabama on the road this season: 1-4.
  🔁 Same opponent, two results - Southern Miss got a 35-31 win over Louisiana (10/24); South Alabama took a 28-26 loss to 'em (11/7).
  📊 Last 3 for South Alabama: 24 scored a game, 26 given up.
  💣 3 of the last 5 times out, Southern Miss put up 31 or more.
  💯 299 yards on the ground for Steven Robinson in Southern Miss' last 3 games.
  ✅ Bottom line: Southern Miss (+164). Tell the homies.
```

Yesterday's writer, on the page (8 fact lines, 0 repeats, 2 reason-backed, 1 matchup):

```
WHY: 🥊 Riding Flyers: Twice this year the Canadiens got blown out in their own building: 5-2 by the Predators and 4-1 by the Avalanche.
  🎬 9 of the Canadiens' 14 wins this year came by one goal - the last two 3-2 over the Devils and 2-1 over the Hurricanes. They been squeaking by.
  🧳 The Canadiens back home tonight after 3 road games in 6 days.
  🧳 Last 3 on the road for Flyers: 2 wins, a 4-3 win at the Blue Jackets and a 6-5 win at the Senators.
  🏟️ 5-6 at home for Canadiens.
  💣 Flyers scored 4 or more in 3 of their last 5 games.
  ⏱️ The third period, last 10 games: Canadiens gave up 14 goals and scored 7.
  📅 Fresh off a 6-5 win over the Senators for Flyers.
  ✅ Bottom line: Flyers (+136). We on Flyers.
```

Now, on the page (6 fact lines, 0 repeats, 0 reason-backed, 3 matchup):

```
WHY: 🏃 Southern Miss run for 161 yards a game this year and South Alabama gives up 169 on the ground. We on Southern Miss.
  🏆 Southern Miss already beat Louisiana this year, 35-31 at home.
  🔁 They both saw Louisiana lately: Southern Miss got a 35-31 win on 10/24, South Alabama took a 28-26 loss on 11/7.
  🧳 South Alabama is 1-4 on the road this year.
  💣 Southern Miss scored 31 or more in 3 of their last 5 games.
  💯 299 yards on the ground for Steven Robinson in Southern Miss' last 3 games.
  ✅ Bottom line: Southern Miss (+164). Ride it.
```

### 2026-11-21 ncaab - UT Rio Grande +160 vs Austin Peay (play, 2.0u)

As it posted (5 fact lines, 1 repeats, 0 reason-backed, 0 matchup):

```
WHY: 📊 On the year UT Rio Grande scores 78 points a game and gives up 62. UT Rio Grande the side.
  📊 UT Rio Grande put up 80 a game and give up 66 over their last 3. Austin Peay: 71 and 65.
  🏁 UT Rio Grande outscored teams 170 to 143 in the first half over their last 5 games. They come out ready.
  📋 3-2 for UT Rio Grande, fresh off a 98-40 win over Biblical Stud (a no-name non-D1 school).
  ⏱️ The second half, last 5 games: 219 points for UT Rio Grande, 168 against.
  ✅ Bottom line: UT Rio Grande (+160).
```

Yesterday's writer, on the page (4 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 📊 Indiana St this season: 79 points a game scored, 70 allowed. Indiana St the side.
  📅 MTSU off an 85-76 loss to Temple last time out.
  🏁 The first half, last 5 games: 189 points for Indiana St, 154 against.
  💯 Indiana St's top scorer Karmani Gregory is putting up 20 a night lately (4 games).
  ✅ Bottom line: Indiana St (+124). Give me Indiana St.
```

Now, on the page (5 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: 📊 UT Rio Grande the side: Last 2 for Austin Peay: 64 scored a game, 74 given up.
  🏁 The first half, last 5 games: 170 points for UT Rio Grande, 143 against.
  ⏱️ The second half, last 5 games: 219 points for UT Rio Grande, 168 against.
  ⚖️ UT Rio Grande 3-2, Austin Peay 3-2 — but UT Rio Grande's L's came against Texas St and UT Arlington.
  📅 UT Rio Grande handled business last time, a 98-40 win over Biblical Stud (a no-name non-D1 school).
  ✅ Bottom line: UT Rio Grande (+160). Give me UT Rio Grande.
```

### 2026-11-21 ncaab - Indiana St +124 vs MTSU (play, 1.0u)

As it posted (5 fact lines, 1 repeats, 1 reason-backed, 0 matchup):

```
WHY: 📊 79 a game for Indiana St this year, 70 against. They outscore people. Indiana St the side.
  📊 Scoreboard lately - Indiana St: 86 scored, 68 allowed a game (last 3). MTSU: 83 and 79.
  📅 MTSU off an 85-76 loss to Temple last time out.
  💯 Karmani Gregory is giving Indiana St 20 a night over the last 4 games he's played.
  🏁 The first half, last 5 games: 189 points for Indiana St, 154 against.
  ✅ Bottom line: Indiana St (+124).
```

Yesterday's writer, on the page (7 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: (none)
  🧊 Losing streak at 5 for the Ravens.
  🎬 The Ravens keep winning by one score: 3 of their 4 wins this year, the last two 24-18 over the Titans and 30-23 over the Falcons.
  📊 Last 3 for Ravens: 13 scored a game, 31 given up.
  📋 Ravens sit 4-6. Losing record.
  📅 Last time out: Panthers got a 20-17 win over the Saints · Ravens took a 23-20 loss to the Chargers.
  💸 Ravens lost 3 of 4 as the underdog this year.
  ⚖️ Same kind of record, tougher schedule: Panthers' L's came against Bears, Browns, Buccaneers, Packers and Broncos.
  ✅ Bottom line: Panthers (-145). The side we trust most today, at a price that pays. That's money.
```

Now, on the page (4 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 📊 Indiana St the side: Against D1 teams MTSU gives up 79 points a game and scores 73.
  📅 MTSU off an 85-76 loss to Temple last time out.
  🏁 The first half, last 5 games: 189 points for Indiana St, 154 against.
  💯 Indiana St's top scorer Karmani Gregory is putting up 20 a night lately (4 games).
  ✅ Bottom line: Indiana St (+124). Give me Indiana St.
```

### 2026-11-20 ncaab - Niagara -115 vs Delaware St (play, 0.5u)

As it posted (3 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 📊 We on Niagara: Last 3 for Delaware St: 72 scored a game, 75 given up.
  📋 Both of Delaware St's wins came over schools that aren't Division I (Saint Vincent and Cheyney (PA)).
  🎟️ Niagara beat the spread in their last 2 games - the last one getting 39.5 at Iowa State, the game ended 21 apart.
  ✅ Bottom line: Niagara +2.5 (-115). We on Niagara.
```

Yesterday's writer, on the page (4 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🧳 Riding Southern Miss: South Alabama is 1-4 on the road this year.
  🔁 They both saw Louisiana lately: Southern Miss got a 35-31 win on 10/24, South Alabama took a 28-26 loss on 11/7.
  💣 Southern Miss scored 31 or more in 3 of their last 5 games.
  💯 299 yards on the ground for Steven Robinson in Southern Miss' last 3 games.
  ✅ Bottom line: Southern Miss (+164). Ride it.
```

Now, on the page (3 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 📊 We on Niagara: Against D1 teams Delaware St gives up 74 points a game and scores 62.
  📋 Both of Delaware St's wins came over schools that aren't Division I (Saint Vincent and Cheyney (PA)).
  🎟️ 2 straight covers for Niagara. Last time out, getting 39.5 at Iowa State, the game ended 21 apart.
  ✅ Bottom line: Niagara +2.5 (-115). We on Niagara.
```

### 2026-11-19 nhl - Flyers +150 vs Senators (play, 2.0u)

As it posted (7 fact lines, 0 repeats, 1 reason-backed, 2 matchup):

```
WHY: 🆚 Flyers took the last one from the Senators this year - a 3-1 win at home on 10/17. Flyers the side.
  🥊 The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
  🎬 7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by.
  🏹 Flyers put 270 shots on net their last 10 and gave up 241. More looks than the other guys, night after night.
  🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
  💯 Matvei Michkov been producing for Flyers: 9 points over the last 10.
  📅 Flyers come off a 4-3 win over the Sabres.
  ✅ Bottom line: Flyers (+150). Already beat 'em once this year. Ride it.
```

Yesterday's writer, on the page (8 fact lines, 0 repeats, 1 reason-backed, 1 matchup):

```
WHY: 🚪 Give me Warriors: Grizzlies gave up 120 or more points in 3 of their last 5 games.
  🔁 They both saw the Nuggets lately: Warriors got a 134-114 win on 10/26, Grizzlies took a 123-118 loss on 11/11.
  🧳 The Grizzlies just got home - 3 road games in the last 6 days.
  🏟️ 3-4 at home for Grizzlies. Grizzlies' own building ain't saving them.
  💯 Warriors' top scorer Yaxel Lendeborg is putting up 19 a night lately (10 games).
  🏁 7 of the last 10 times out, Grizzlies were behind after the 1st quarter.
  🗓️ Warriors won 6 of their last 10.
  ⏱️ 7 of the last 10 times out, Warriors won the 4th quarter.
  ✅ Bottom line: Warriors (+180). Half a unit. Get in.
```

Now, on the page (7 fact lines, 0 repeats, 1 reason-backed, 2 matchup):

```
WHY: 🆚 Flyers took the last one from the Senators this year - a 3-1 win at home on 10/17. Flyers the side.
  🥊 The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
  🏹 Shots on net the last 10 games: 270 for Flyers, 241 against. That's a team getting the better of it.
  🎬 7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by.
  🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
  💯 Matvei Michkov has 9 points in Flyers' last 10 games.
  📅 Fresh off a 4-3 win over the Sabres for Flyers.
  ✅ Bottom line: Flyers (+150). Already beat 'em once this year. We on Flyers.
```

### 2026-11-19 nhl - Ducks +110 vs Avalanche (dog, 3.0u)

As it posted (8 fact lines, 0 repeats, 3 reason-backed, 1 matchup):

```
WHY: 🚑 We on Ducks: the Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
  😴 Second night of a back-to-back for Avalanche. Ducks are rested.
  📉 Avalanche lose Nathan MacKinnon - 30 points in his 20 games this year.
  🥊 4-1. That's what the Mammoth did to the Avalanche inside their last 5.
  🔁 They both saw the Senators lately: Ducks got a 6-3 win on 11/1, Avalanche took a 4-3 loss on 11/12.
  🧳 Road game, no problem: Ducks are 7-4 away from home this season.
  🥅 Scott Wedgewood — the Avalanche's projected starter, nobody's confirmed yet — has been giving up a lot of goals: a 0.871 save % (13 goals on 101 shots) over his last 3 starts.
  🥅 Mackenzie Blackwood played last night for Avalanche; Scott Wedgewood (projected, not confirmed) is the next man up.
  ✅ Bottom line: Ducks (+110). Avalanche is short-handed. Get in.
```

Yesterday's writer, on the page (7 fact lines, 0 repeats, 1 reason-backed, 2 matchup):

```
WHY: 🆚 Flyers took the last one from the Senators this year - a 3-1 win at home on 10/17. Flyers the side.
  🥊 The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
  🏹 Shots on net the last 10 games: 270 for Flyers, 241 against. That's a team getting the better of it.
  🎬 7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by.
  🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
  💯 Matvei Michkov has 9 points in Flyers' last 10 games.
  📅 Fresh off a 4-3 win over the Sabres for Flyers.
  ✅ Bottom line: Flyers (+150). Already beat 'em once this year. We on Flyers.
```

Now, on the page (8 fact lines, 0 repeats, 3 reason-backed, 2 matchup):

```
WHY: 🚑 Ducks take this one — the Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
  😴 Avalanche played last night; Ducks had 2 days off.
  📉 Avalanche loses Nathan MacKinnon - 30 points in his 20 games this year.
  🥊 The Avalanche got their cheeks clapped 4-1 by the Mammoth inside their last 5.
  🎬 In one-goal games this year Avalanche lost 6 of 7.
  🔁 Same opponent, two results - Ducks got a 6-3 win over the Senators (11/1); Avalanche took a 4-3 loss to 'em (11/12).
  🧳 7-4 on the road for Ducks.
  💣 Ducks scored 4 or more in 3 of their last 5 games.
  ✅ Bottom line: Ducks (+110). Avalanche is short-handed. That's the bet.
```

### 2026-11-19 ncaab - UTEP +102 vs New Mexico St (play, 1.0u)

As it posted (8 fact lines, 0 repeats, 2 reason-backed, 1 matchup):

```
WHY: 🥊 UTEP the side: New Mexico St just got beat 73-61 by San Diego St, UTEP about to spank 'em.
  🆚 New Mexico St already saw UTEP this year and took the L - a 60-58 win for UTEP at home on 11/12.
  🔥 UTEP is on a heater - 3 straight, 3-1 on the year.
  📊 Scoreboard lately - UTEP: 73 scored, 55 allowed a game (last 3). New Mexico St: 62 and 81.
  ⏱️ UTEP outscored teams 141 to 120 in the second half over their last 4 games. They close.
  🏁 The first half, last 4 games: 153 points for UTEP, 128 against.
  🚀 Florida A&M got their cheeks clapped by UTEP last time out, 79-46.
  💯 UTEP's top scorer Cam McDaniels is putting up 20 a night lately (4 games).
  ✅ Bottom line: UTEP (+102). Let it ride.
```

Yesterday's writer, on the page (3 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 📊 We on Niagara: Last 3 for Delaware St: 62 scored a game, 74 given up.
  📋 Both of Delaware St's wins came over schools that aren't Division I (Saint Vincent and Cheyney (PA)).
  🎟️ 2 straight covers for Niagara. Last time out, getting 39.5 at Iowa State, the game ended 21 apart.
  ✅ Bottom line: Niagara +2.5 (-115). We on Niagara.
```

Now, on the page (8 fact lines, 0 repeats, 2 reason-backed, 2 matchup):

```
WHY: 🆚 UTEP already beat New Mexico St this year - a 60-58 win at home on 11/12. We on UTEP.
  🔥 UTEP is on a heater - 3 straight, 3-1 on the year.
  📊 Scoreboard lately - UTEP: 73 scored, 55 allowed a game (last 3). New Mexico St: 62 and 81.
  🚀 Fresh off a 79-46 win over Florida A&M.
  ⏱️ The second half, last 4 games: 141 points for UTEP, 120 against.
  🏁 The first half, last 4 games: 153 points for UTEP, 128 against.
  📅 New Mexico St took a 73-61 loss to San Diego St last time out.
  📋 New Mexico St's only win this year is a 73-66 game with Western NM, a school that ain't even Division I.
  ✅ Bottom line: UTEP (+102). Already beat 'em once this year. Give me that.
```

### 2026-11-19 nba - Warriors +180 vs Grizzlies (play, 0.5u)

As it posted (9 fact lines, 0 repeats, 1 reason-backed, 1 matchup):

```
WHY: 🚪 Give me Warriors: 120+ points allowed in 3 of the last 5 for Grizzlies. That defense is giving it away.
  🔁 Same opponent, two results - Warriors got a 134-114 win over the Nuggets (10/26); Grizzlies took a 123-118 loss to 'em (11/11).
  🧳 The Grizzlies just got home - 3 road games in the last 6 days.
  🏟️ Grizzlies are 3-4 at home this year. That ain't a fortress.
  💯 Yaxel Lendeborg is giving Warriors 19 a night over the last 10 games he's played.
  🏁 7 of the last 10 times out, Grizzlies were behind after the 1st quarter.
  🗓️ Warriors won 6 of their last 10.
  ⏱️ 7 of the last 10 times out, Warriors won the 4th quarter.
  🏀 Warriors: Gui Santos is cooking - with him on the floor lately the team's up 10.2 points a full game (last season: up 1.4).
  ✅ Bottom line: Warriors (+180). Plus money on Warriors - half a unit.
```

Yesterday's writer, on the page (8 fact lines, 0 repeats, 2 reason-backed, 1 matchup):

```
WHY: 🆚 UTEP already beat New Mexico St this year - a 60-58 win at home on 11/12. We on UTEP.
  🔥 UTEP is on a heater - 3 straight, 3-1 on the year.
  📊 Scoreboard lately - UTEP: 73 scored, 55 allowed a game (last 3). New Mexico St: 62 and 81.
  🚀 Fresh off a 79-46 win over Florida A&M.
  🏁 The first half, last 4 games: 153 points for UTEP, 128 against.
  💯 UTEP's top scorer Cam McDaniels is putting up 20 a night lately (4 games).
  📅 New Mexico St took a 73-61 loss to San Diego St last time out.
  ⏱️ The second half, last 4 games: 141 points for UTEP, 120 against.
  ✅ Bottom line: UTEP (+102). Already beat 'em once this year. Give me that.
```

Now, on the page (8 fact lines, 0 repeats, 1 reason-backed, 1 matchup):

```
WHY: 🚪 Give me Warriors: Grizzlies gave up 120 or more points in 3 of their last 5 games.
  🔁 They both saw the Nuggets lately: Warriors got a 134-114 win on 10/26, Grizzlies took a 123-118 loss on 11/11.
  🧳 The Grizzlies just got home - 3 road games in the last 6 days.
  🏟️ 3-4 at home for Grizzlies. Grizzlies' own building ain't saving them.
  💯 Warriors' top scorer Yaxel Lendeborg is putting up 19 a night lately (10 games).
  🏁 7 of the last 10 times out, Grizzlies were behind after the 1st quarter.
  🗓️ Warriors won 6 of their last 10.
  ⏱️ 7 of the last 10 times out, Warriors won the 4th quarter.
  ✅ Bottom line: Warriors (+180). Half a unit. Get in.
```

### 2026-11-18 ncaab - Charleston So +114 vs Wofford (play, 2.0u)

As it posted (7 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧠 Charleston So all day — Charleston So just rolled to a 92-68 win over West Georgia.
  🏟️ 2-0 in their own building - Charleston So wins more than it loses there.
  ✅ Charleston So has everybody available.
  🧳 Wofford is 0-3 on the road this year.
  💯 Anthony Ruffolo been cooking for Charleston So - 21 a night over his last 4.
  💵 We price Charleston So at -104. The book's paying +114.
  📅 Wofford L 92-97 @ Queens last time out.
  ⚠️ Wofford has outscored teams 94 to 70 a game over their last 3; Charleston So sits 81 for, 66 against.
  ✅ Bottom line: Charleston So (+114). Our read beats this price. Trust the algorithm.
```

Yesterday's writer, on the page (8 fact lines, 0 repeats, 3 reason-backed, 2 matchup):

```
WHY: 🚑 Ducks take this one — the Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
  😴 Avalanche played last night; Ducks had 2 days off.
  📉 Avalanche loses Nathan MacKinnon - 30 points in his 20 games this year.
  🥊 The Avalanche got their cheeks clapped 4-1 by the Mammoth inside their last 5.
  🎬 In one-goal games this year Avalanche lost 6 of 7.
  🔁 Same opponent, two results - Ducks got a 6-3 win over the Senators (11/1); Avalanche took a 4-3 loss to 'em (11/12).
  🧳 7-4 on the road for Ducks.
  💣 Ducks scored 4 or more in 3 of their last 5 games.
  ✅ Bottom line: Ducks (+110). Avalanche is short-handed. That's the bet.
```

Now, on the page (7 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 📅 Charleston So just beat West Georgia 92-68, we got Charleston So.
  🧳 Wofford is 0-3 on the road this year.
  🏟️ 2-0 in their own building - Charleston So wins more than it loses there.
  📊 Wofford against D1 teams: 99 points a game allowed, 74 scored. They get outscored.
  ⏱️ Charleston So put up 186 points in the second half over their last 4 and gave up 157.
  💯 Charleston So's top scorer Anthony Ruffolo is putting up 21 a night lately (4 games).
  📋 Wofford got both of their wins off non-Division I schools - Allen and Voorhees.
  ✅ Bottom line: Charleston So (+114). Ride it.
```

### 2026-11-18 nba - Nuggets +120 vs Celtics (dog, 2.0u)

As it posted (9 fact lines, 0 repeats, 2 reason-backed, 0 matchup):

```
WHY: 🧠 The Celtics gotta breathe 5,300 feet up. Nuggets fin to handle that.
  🧳 The Celtics put in the miles to get here (1,760-mile trip west).
  💵 +120 at the book on a side we make +103.
  🏁 Nuggets won the 1st quarter in 7 of their last 10 games. They come out ready.
  🗓️ Nuggets won 3 of their last 5.
  📅 The Celtics are fresh off a 115-105 loss to the Magic.
  💯 Nikola Jokic: 24 a night for Nuggets over his last 10 games.
  💯 Nuggets' top scorer Jamal Murray is putting up 26 a night lately (10 games).
  🏀 Nuggets: their bench outscored teams by 6 a game last season - deep squad · 7 guys play real minutes.
  ⚠️ Biggest knock on Nuggets: Celtics come in 11-3 to Nuggets' 7-5.
  ✅ Bottom line: Nuggets (+120). Our read beats this price. Ride it.
  🌟 Nuggets: Jamal Murray (All-NBA 2026) is in the lineup tonight.
```

Yesterday's writer, on the page (7 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 📅 Charleston So just beat West Georgia 92-68, we got Charleston So.
  🧳 Wofford is 0-3 on the road this year.
  🏟️ 2-0 in their own building - Charleston So wins more than it loses there.
  📊 Last 3 for Wofford: 74 scored a game, 99 given up.
  ⏱️ Charleston So put up 186 points in the second half over their last 4 and gave up 157.
  💯 Charleston So's top scorer Anthony Ruffolo is putting up 21 a night lately (4 games).
  📋 Wofford got both of their wins off non-Division I schools - Allen and Voorhees.
  ✅ Bottom line: Charleston So (+114). Ride it.
```

Now, on the page (5 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧠 Nuggets the side: the Celtics are playing 5,300 feet up. Ride Nuggets. Plus Celtics flew 1,760 miles for this.
  🏁 7 of the last 10 times out, Nuggets took the 1st quarter.
  📅 Celtics off a 115-105 loss to the Magic last time out.
  🗓️ Nuggets won 6 of their last 10.
  💯 Nuggets' top scorer Jamal Murray is putting up 26 a night lately (10 games).
  ✅ Bottom line: Nuggets (+120). Get in.
```

### 2026-11-17 nhl - Capitals +136 vs Lightning (dog, 2.0u)

As it posted (5 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: (none)
  ✅ Nobody on Capitals' injury report. Whole squad's suiting up.
  🥅 Logan Thompson (projected, not confirmed for Capitals): a 0.893 save % (9 goals on 84 shots) over his last 3 starts. Andrei Vasilevskiy (expected in net, not confirmed for Lightning): a 0.896 save % (8 goals on 77 shots) over his last 3 starts.
  📅 Both took an L last time - Capitals a 7-4 loss to the Devils, Lightning a 2-0 loss to the Red Wings.
  📋 10-8 for Capitals, last time out a 7-4 loss to the Devils.
  🧳 3-3 away from home this year for Capitals.
  ⚠️ Not perfect - Capitals have dropped 2 straight.
  ✅ Bottom line: Capitals (+136). Fishy line - Capitals at +136 when we make 'em +112.
```

Yesterday's writer, on the page (8 fact lines, 1 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🚑 Timberwolves are down Jonathan Kuminga (F) tonight. Riding Trail Blazers.
  👌 Trail Blazers been hitting 15 threes a night over their last 5. Timberwolves: 12.
  🧹 Trail Blazers won by 10 or more points in 3 of their last 5 games.
  🧳 Trail Blazers been winning on the road: 6-2.
  📊 Trail Blazers put up 112 a game over their last 3 and gave up 107.
  📊 Trail Blazers this season: 118 points a game scored, 111 allowed.
  🐶 As the dog this year Trail Blazers won 3 of 6.
  ⏱️ 6 of the last 10 times out, Trail Blazers won the 4th quarter.
  ⚠️ Heads up: Timberwolves beat Trail Blazers 106-98 last time out.
  ✅ Bottom line: Trail Blazers (+110). Timberwolves are short-handed. The dog angles like it. Trust the algorithm.
```

Now, on the page (8 fact lines, 0 repeats, 0 reason-backed, 4 matchup):

```
WHY: ⚡ Capitals the side: Lightning gave up 15 power-play goals on 53 kills this year. Take a penalty against Capitals and it costs.
  🎬 In one-goal games this year Capitals won 5 of 6.
  🔁 They both saw the Predators lately: Capitals got a 4-3 win on 10/29, Lightning took a 5-4 loss on 10/31.
  🧳 Last 3 on the road for Capitals: 2 wins, a 4-3 win at the Predators and a 3-2 win at the Senators.
  📅 Last time out the Lightning took a 2-0 loss to the Red Wings.
  🧾 6 wins in 12 games against winning teams for Capitals this year.
  💯 Cole Hutson has 11 points in Capitals' last 10 games.
  💣 Capitals scored 4 or more in 3 of their last 5 games.
  ⚠️ Capitals have dropped 2 straight.
  ✅ Bottom line: Capitals (+136). Riding Capitals.
```

### 2026-11-17 nba - Trail Blazers +110 vs Timberwolves (play, 0.5u)

As it posted (5 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: 🚑 Timberwolves gotta play without Jonathan Kuminga (F), Jaylen Clark (G), Zyon Pullin (G), Anthony Edwards (G). Riding Trail Blazers.
  🚑 Timberwolves gotta play without Jonathan Kuminga (F), Jaylen Clark (G), Zyon Pullin (G), Anthony Edwards (G).
  🧳 6-2 on the road for Trail Blazers.
  🗓️ Last 5 for Trail Blazers: 3-2.
  📋 Trail Blazers are 9-4 after a 106-98 loss to the Timberwolves.
  ⚠️ What scares us a little: Trail Blazers go without Chris Youngblood (G), Vit Krejci (G), Ja Morant (G), Shaedon Sharpe (G).
  ✅ Bottom line: Trail Blazers (+110). The dog angles like it. Trust the algorithm.
```

Yesterday's writer, on the page (5 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧠 Nuggets the side: the Celtics are playing 5,300 feet up. Ride Nuggets. Plus Celtics flew 1,760 miles for this.
  🏁 7 of the last 10 times out, Nuggets took the 1st quarter.
  📅 Celtics off a 115-105 loss to the Magic last time out.
  🗓️ Nuggets won 6 of their last 10.
  💯 Nuggets' top scorer Jamal Murray is putting up 26 a night lately (10 games).
  ✅ Bottom line: Nuggets (+120). Get in.
```

Now, on the page (8 fact lines, 0 repeats, 0 reason-backed, 2 matchup):

```
WHY: 🚑 Timberwolves are down Jonathan Kuminga (F) tonight. Riding Trail Blazers.
  👌 Trail Blazers been hitting 15 threes a night over their last 5. Timberwolves: 12.
  🧹 Trail Blazers won by 10 or more points in 3 of their last 5 games.
  🧳 Trail Blazers been winning on the road: 6-2.
  📊 Trail Blazers this season: 118 points a game scored, 111 allowed.
  ⏱️ 6 of the last 10 times out, Trail Blazers won the 4th quarter.
  🐶 As the dog this year Trail Blazers won 3 of 6.
  🧾 4 wins in 8 games against winning teams for Trail Blazers this year.
  ⚠️ Heads up: Timberwolves beat Trail Blazers 106-98 last time out.
  ✅ Bottom line: Trail Blazers (+110). Timberwolves are short-handed. The dog angles like it. Trust the algorithm.
```

### 2026-11-16 ncaab - UMBC +120 vs Iona (play, 0.5u)

As it posted (5 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧳 UMBC, and it ain't a question — Iona on the road this season: 0-3.
  📊 UMBC put up 73 a game and give up 66 over their last 3. Iona: 65 and 81.
  ✅ Nobody big missing for UMBC.
  🏟️ UMBC takes care of home: 2-0 in their building so far.
  📋 UMBC 2-3, Iona 2-3 - same spot in the standings, not the same team.
  ✅ Bottom line: UMBC at +120. The dog angles like it, the price is about fair. Half a unit and we'll see.
```

Yesterday's writer, on the page (7 fact lines, 0 repeats, 0 reason-backed, 3 matchup):

```
WHY: 🎬 In one-goal games this year Capitals won 5 of 6. Capitals the side.
  🔁 They both saw the Predators lately: Capitals got a 4-3 win on 10/29, Lightning took a 5-4 loss on 10/31.
  🧳 Last 3 on the road for Capitals: 2 wins, a 4-3 win at the Predators and a 3-2 win at the Senators.
  📅 Last time out the Lightning took a 2-0 loss to the Red Wings.
  🧾 6 wins in 12 games against winning teams for Capitals this year.
  💯 Cole Hutson has 11 points in Capitals' last 10 games.
  💣 Capitals scored 4 or more in 3 of their last 5 games.
  ⚠️ Capitals have dropped 2 straight.
  ✅ Bottom line: Capitals (+136). Lightning been squeaking by. Riding Capitals.
```

Now, on the page (7 fact lines, 0 repeats, 3 reason-backed, 0 matchup):

```
WHY: 🧳 Iona is 0-3 on the road this year. UMBC the side.
  🧳 Iona: 3rd road game in 6 days.
  🏟️ UMBC protects the crib: 2-0 at home.
  📊 Last 3 for Iona: 65 scored a game, 81 given up.
  💣 UMBC scored 80 or more in 3 of their last 5 games.
  💯 UMBC's top scorer Devin Ceaser is putting up 15 a night lately (5 games).
  📅 Iona is fresh off a 62-59 loss to Hofstra.
  ⚠️ UMBC comes off a 68-42 loss to Towson.
  ✅ Bottom line: UMBC (+120). The dog angles like it. Let it ride.
```

### 2026-11-15 nfl - Packers -142 vs Vikings (lock, 1.0u)

As it posted (11 fact lines, 1 repeats, 3 reason-backed, 0 matchup):

```
WHY: 🥊 The Vikings are coming off a 23-6 beating from the Bills, Vikings been trash as fuck.
  📊 Last 3: Packers are outscoring teams 30 to 22 a game; Vikings sit at 12 for, 17 against.
  🚑 Vikings are without Kyler Murray (QB), Blake Cashman (LB), T.J. Hockenson (TE).
  🏟️ The Vikings play indoors at home. Today: 34° outside.
  🎯 Our quarterback's been better: Jordan Love has 8 TDs, 2 picks and 934 yards in his last 3 games for Packers; Carson Wentz has 0 TDs, 2 picks and 81 yards in his last 1 game for Vikings.
  📊 Packers score 24 points a game this year; Vikings manage 18.
  🚀 Packers just beat the brakes off the Patriots, 45-27.
  🏟️ 3-1 in their own building - Packers win more than they lose there.
  ⏳ Packers come in on 7 days rest; Vikings are on 6 days.
  📅 Last game for each: Packers W 45-27 @ Patriots · Vikings L 6-23 vs Bills.
  📋 Packers are 6-3 after a 45-27 win over the Patriots.
  ⚠️ Packers go without Josh Jacobs (RB).
  ✅ Bottom line: Packers (-142). Our number on Packers is -197. Free money at this price.
```

Yesterday's writer, on the page (8 fact lines, 0 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🧊 The Knicks haven't won in 2. We'll take the plus money on Raptors.
  🧳 Knicks are 2-3 on the road this year.
  📊 Raptors score 114 points a game this year; Knicks manage 110.
  🎟️ Knicks failed to cover in 6 of their last 10 games.
  🧾 Knicks only got 1 win in 4 games against winning teams this year.
  ⏱️ Closing time: Raptors took the 4th quarter in 6 of their last 10.
  💸 When the book makes Knicks the favorite, they lost 5 of 11 this year.
  📅 The Knicks come in off a 106-104 loss to the Pacers.
  ⚠️ Raptors have dropped 3 straight.
  ✅ Bottom line: Raptors (+160). Knicks can't buy a win right now. Half a unit. Smart side.
```

Now, on the page (7 fact lines, 0 repeats, 1 reason-backed, 2 matchup):

```
WHY: 💥 Packers have 26 sacks in 9 games this year and Vikings already gave up 23. That pocket's collapsing. Packers the side.
  🎬 4 of the Vikings' 6 wins this year came by one score - the last two 15-10 over the Dolphins and 16-10 over the Colts. They been squeaking by.
  🏟️ At home Packers are 3-1.
  🏟️ The Vikings play their home games under a roof. This one's outdoors in 34°.
  📊 Scoreboard lately - Packers: 30 scored, 22 allowed a game (last 3). Vikings: 12 and 17.
  📅 Vikings took a 23-6 loss to the Bills last time out.
  🚀 Packers smacked the Patriots 45-27 last time out.
  ⚠️ Packers go without Josh Jacobs (RB).
  ✅ Bottom line: Packers (-142). Our top play today. Lock it in.
```

### 2026-11-15 nba - Raptors +160 vs Knicks (play, 0.5u)

As it posted (7 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: 🧊 The Knicks have lost 2 straight, Knicks super trash right now. We talking shit, but the tape says it.
  🚑 Raptors out: F Scottie Barnes (33 min a night last year), C Nate Bittle, F Kawhi Leonard (31 min a night last year) · questionable: G Kevin McCullar Jr..
  🧳 2-3 on the road for Knicks.
  📊 Raptors score 114 points a game this year; Knicks manage 110.
  📋 5-7 for Raptors, last time out a 123-112 loss to the 76ers.
  📅 The Knicks come in off a 106-104 loss to the Pacers; the Raptors off a 123-112 loss to the 76ers.
  🏀 Raptors: their bench outscored teams by 3.1 per 48 minutes last season - deep squad · the coach plays 8 guys real minutes.
  ⚠️ Not perfect - Raptors go without Scottie Barnes (F), Nate Bittle (C), Kawhi Leonard (F).
  ✅ Bottom line: Raptors (+160). No big edge here - Raptors are just the best dog left on today's slate. Half a unit, keep it light.
  🌟 Raptors: Kawhi Leonard, Scottie Barnes are out.
```

Yesterday's writer, on the page (8 fact lines, 1 repeats, 3 reason-backed, 0 matchup):

```
WHY: 🧳 Iona is 0-3 on the road this year. UMBC the side.
  🧳 Iona: 3rd road game in 6 days.
  🏟️ UMBC protects the crib: 2-0 at home.
  📊 Last 3 for Iona: 65 scored a game, 81 given up.
  📊 Iona this season: 70 points a game allowed, 65 scored. They get outscored.
  💣 UMBC scored 80 or more in 3 of their last 5 games.
  💯 UMBC's top scorer Devin Ceaser is putting up 15 a night lately (5 games).
  📅 Iona is fresh off a 62-59 loss to Hofstra.
  ⚠️ UMBC comes off a 68-42 loss to Towson.
  ✅ Bottom line: UMBC (+120). The dog angles like it. Let it ride.
```

Now, on the page (8 fact lines, 0 repeats, 0 reason-backed, 3 matchup):

```
WHY: 🧊 The Knicks haven't won in 2. We'll take the plus money on Raptors.
  🥷 Raptors come up with 11 steals a game this year. Knicks: 7.
  🪣 44% shooting this year for Knicks. They struggle to score.
  🎁 Free throws a game this year: 27 for Raptors, 22 for Knicks. Free points.
  🧳 Knicks are 2-3 on the road this year.
  📊 Raptors score 114 points a game this year; Knicks manage 110.
  💸 When the book makes Knicks the favorite, they lost 5 of 11 this year.
  📅 The Knicks come in off a 106-104 loss to the Pacers.
  ⚠️ Raptors have dropped 3 straight.
  ✅ Bottom line: Raptors (+160). Knicks can't buy a win right now. Half a unit. Smart side.
```

### 2026-11-14 nhl - Flyers +114 vs Blue Jackets (dog, 2.0u)

As it posted (7 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧊 3 straight losses for the Blue Jackets. Give me Flyers.
  🍀 Puck luck's been shit for Flyers - shooting plus save % at 97.4 over the last 10 games (100 is average).
  📊 Over the last 3, Flyers are +0 a game (3 for, 3 against); Blue Jackets are -3 (1 for, 4 against).
  📅 Flyers off a 3-2 loss to the Oilers, Blue Jackets off a 3-1 loss to the Lightning.
  ⏳ Flyers got the extra day: 3 days off to Blue Jackets' 2 days.
  🥊 The Panthers spanked the Blue Jackets 4-1 within their last 5 games.
  📋 5-16 for Flyers, last time out a 3-2 loss to the Oilers.
  ⚠️ Cam Talbot (Blue Jackets, projected, not confirmed) is at a 0.929 save % over his last 3 starts to Joseph Woll's 0.893 (our projected guy, not confirmed).
  ✅ Bottom line: Flyers (+114). We make Flyers -106, the book says +114.
```

Yesterday's writer, on the page (7 fact lines, 1 repeats, 2 reason-backed, 0 matchup):

```
WHY: 🥊 Oakland just got beat 111-79 by Boise St, Northern Iowa is the side.
  🥊 Santa Barbara spanked Oakland 90-67 within their last 5 games.
  📊 On the year Oakland gives up 95 points a game and scores 69.
  📊 Last 3 for Oakland: 71 scored a game, 103 given up.
  🏀 Oakland finished 16-16 last season and put up 0.9 more points than they gave up a game; Northern Iowa finished 23-13 and came out 7.7 ahead on the scoreboard most nights.
  💣 3 of the last 4 times out, Northern Iowa put up 80 or more.
  💯 Greyson Uelmen been cooking for Northern Iowa - 19 a night over his last 4.
  ⚠️ Northern Iowa played last night (a 106-72 loss to Michigan St) and Oakland sat 3 days.
  ✅ Bottom line: Northern Iowa (+102). That's the bet.
```

Now, on the page (8 fact lines, 0 repeats, 0 reason-backed, 3 matchup):

```
WHY: 🧊 Blue Jackets ain't ready for this shit — 3 straight losses for the Blue Jackets.
  🥊 4 times this year the Blue Jackets got blown out in their own building: 6-2 by the Maple Leafs and 4-1 by the Panthers.
  ⚡ 12 goals against on 46 kills for Blue Jackets this year. That penalty kill is leaking.
  🎬 5 of the Blue Jackets' 7 wins this year came by one goal - the last two 4-3 over the Flyers and 2-1 over the Stars. They been squeaking by.
  🔁 They both saw the Sabres lately: Flyers got a 3-1 win on 10/21, Blue Jackets took a 5-2 loss on 11/6.
  📊 Blue Jackets are giving up 4 a game and scoring 1.3 over their last 3.
  💸 Blue Jackets lost 3 of 6 as the favorite this year. That's a favorite that loses.
  📋 Blue Jackets sit 7-10. Losing record.
  ⚠️ Flyers are 2-9 on the road this year.
  ✅ Bottom line: Flyers (+114). Blue Jackets can't buy a win right now. That's the bet.
```

### 2026-11-14 ncaab - Northern Iowa +102 vs Oakland (play, 1.0u)

As it posted (6 fact lines, 0 repeats, 2 reason-backed, 0 matchup):

```
WHY: 🥊 Fuck it, Northern Iowa — Oakland got handled 111-79 by Boise St last time out.
  📊 Over the last 3, Northern Iowa is -12 a game (81 for, 93 against); Oakland is -32 (71 for, 103 against).
  🏀 Northern Iowa was 23-13 last year (beat teams by 7.7 per game), Oakland 16-16 (finished +0.9 in point margin).
  🗑️ 0-5. Lame ass team right now, that's Oakland.
  ✅ Northern Iowa has everybody available.
  🥊 109-68. That's what Alabama did to Oakland inside their last 5.
  ⚠️ Biggest knock on Northern Iowa: Northern Iowa played last night (a 106-72 loss to Michigan St) and Oakland sat 3 days.
  ✅ Bottom line: Northern Iowa (+102). We make 'em -106, the book's at +102.
```

Yesterday's writer, on the page (7 fact lines, 1 repeats, 0 reason-backed, 0 matchup):

```
WHY: 🔥 Heat (6-6) won 3 in a row and they ain't done. Give me Heat.
  🏟️ Last 3 at home for Heat: 2 wins, a 145-125 win over the Pacers and a 133-121 win over the Cavaliers.
  📊 Last 3: Heat is outscoring teams 121 to 113 a game; Pistons sit at 127 for, 124 against.
  📊 Heat scores 117 points a game this year; Pistons score 116.
  🗓️ Heat won 6 of their last 10.
  💯 Giannis Antetokounmpo is giving Heat 27 a night over the last 10 games he's played.
  🏁 Heat won the 1st quarter in 7 of their last 10 games. They come out ready.
  ⚠️ Heads up: Heat played last night (a 133-121 win over the Cavaliers) and Pistons sat 2 days.
  ✅ Bottom line: Heat (+160). Heat is rolling. The dog angles like it. Tap in.
```

Now, on the page (6 fact lines, 0 repeats, 2 reason-backed, 0 matchup):

```
WHY: 🥊 Oakland just got beat 111-79 by Boise St, Northern Iowa is the side.
  🥊 Santa Barbara spanked Oakland 90-67 within their last 5 games.
  📊 On the year Oakland gives up 95 points a game and scores 69.
  🏀 Oakland finished 16-16 last season and put up 0.9 more points than they gave up a game; Northern Iowa finished 23-13 and came out 7.7 ahead on the scoreboard most nights.
  💣 3 of the last 4 times out, Northern Iowa put up 80 or more.
  💯 Greyson Uelmen been cooking for Northern Iowa - 19 a night over his last 4.
  ⚠️ Northern Iowa played last night (a 106-72 loss to Michigan St) and Oakland sat 3 days.
  ✅ Bottom line: Northern Iowa (+102). That's the bet.
```

### 2026-11-14 nba - Heat +160 vs Pistons (play, 0.5u)

As it posted (6 fact lines, 0 repeats, 1 reason-backed, 0 matchup):

```
WHY: 🧠 The Heat hasn't lost in 3. Small bet on Heat - half a unit at about a fair price.
  📊 Scoreboard lately - Heat: 121 scored, 113 allowed a game (last 3). Pistons: 127 and 124.
  🚑 Pistons gotta play without Isaiah Joe (G), Jalen Duren (C).
  📅 The Heat is off a 133-121 win over the Cavaliers, the Pistons off a 144-140 win over the Wizards.
  🔥 Heat is 6-6 and on a 3-game heater.
  🏀 Heat: their bench outscored teams by 5.7 per 48 minutes last season - deep squad · the coach plays 8 guys real minutes · Klay Thompson is cooking - the team's +0.9 per 48 with him on the floor lately, -4.3 last season · Pelle Larsson a game-time call.
  ⚠️ Heads up: Heat played last night (a 133-121 win over the Cavaliers) and Pistons sat 2 days.
  ✅ Bottom line: Heat (+160). Best dog on the slate by our angles. Half a unit, don't go crazy.
  🌟 Heat: Giannis Antetokounmpo (All-NBA 2025, top-5 MVP) is in the lineup tonight.
```

Yesterday's writer, on the page (7 fact lines, 1 repeats, 0 reason-backed, 1 matchup):

```
WHY: 🧠 45-27 over the Patriots last time out for the Packers. That's a shit spot for Vikings.
  🎬 4 of the Vikings' 6 wins this year came by one score - the last two 15-10 over the Dolphins and 16-10 over the Colts. They been squeaking by.
  🏟️ The Vikings play their home games under a roof. This one's outdoors in 34°.
  🏟️ At home Packers are 3-1.
  📊 Packers score 24 points a game this year; Vikings manage 18.
  📊 Scoreboard lately - Packers: 30 scored, 22 allowed a game (last 3). Vikings: 12 and 17.
  📅 Vikings took a 23-6 loss to the Bills last time out.
  ⚠️ Packers go without Josh Jacobs (RB).
  ✅ Bottom line: Packers (-142). Our top play today. Lock it in.
```

Now, on the page (6 fact lines, 0 repeats, 0 reason-backed, 0 matchup):

```
WHY: 🔥 Heat (6-6) won 3 in a row and they ain't done. Give me Heat.
  🏟️ Last 3 at home for Heat: 2 wins, a 145-125 win over the Pacers and a 133-121 win over the Cavaliers.
  📊 Last 3: Heat is outscoring teams 121 to 113 a game; Pistons sit at 127 for, 124 against.
  🏁 Heat won the 1st quarter in 7 of their last 10 games. They come out ready.
  💯 Giannis Antetokounmpo is giving Heat 27 a night over the last 10 games he's played.
  🗓️ Heat won 6 of their last 10.
  ⚠️ Heads up: Heat played last night (a 133-121 win over the Cavaliers) and Pistons sat 2 days.
  ✅ Bottom line: Heat (+160). Heat is rolling. The dog angles like it. Tap in.
```


---
The dry run that made these tables: `h.py` (the rig) and `dry.py` in this folder -
`python results/studies/cards_1122/dry.py posted` / `... dry.py cand 2026-11-22 2026-11-23 2026-11-24` (no network,
nothing saved but its own two .md files).
