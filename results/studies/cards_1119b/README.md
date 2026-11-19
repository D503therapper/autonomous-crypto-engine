# 11/19 (evening) - EVERY CARD MAKES SENSE AS A WHOLE

The owner, 11/19, on the Warriors +180 half-unit card: "Claude, I fucking told you and told you and told you to fix these
fucking breakdowns, damn it ... You need to run Fable and permanently fix these fucking breakdowns ... The Grizzlies
breakdown on the one-liner, it says like 3 fucking key guys are out for the Grizzlies, but give me the fucking
[Warriors]. Makes no fucking sense. Fucking fix this shit."

The 11/17 sweep made every line true, the 11/18 sweep made every line argue for our side, this morning's pass
(cards_1119) made the card say the matchup. All three judged a card ONE LINE AT A TIME. The Warriors card passed every
one of those checks and was still nonsense, because nothing read the card as a whole.

**No pick, price or unit size changed.** Wording only; `sports_breakdown.VERSION` 75 rewrites the open cards.

## 1. What was wrong - the Warriors card

| on the card | why it's wrong |
|---|---|
| "🚑 Grizzlies gotta play without Ty Jerome (G), Zach Edey (C). Give me Warriors." (the line under the pick), "📉 Ty Jerome was giving Grizzlies 25 points a night ... and he's out.", "Grizzlies are short-handed." (the bottom line) | INCOHERENT - the card sells "they're short-handed" while OUR side sits Stephen Curry, Draymond Green and Jimmy Butler. By the box scores we were every bit as short-handed (4 against 4 on the yardstick below - and that is before Jimmy Butler, ruled out after the card posted). |
| "Stephen Curry is cooking - with him on the floor lately the team's up 14.9 points a full game" | FALSE for tonight - he is out. The roster line read last week's on / off numbers and never looked at the injury report. |
| "Moses Moody on a minutes limit (about 22 tonight)" | FALSE - out. |
| "their bench outscored teams by 8 a game last season - deep squad · 9 guys play real minutes" | fights the card - three of our best men are sitting. |
| "🚑 Warriors out: F Draymond Green ..., G Stephen Curry ..." inside the write-up, "🌟 Warriors: Stephen Curry is out." as the card's last line | BAD FOR US, inside our own case for the pick. |
| header "Half a unit on the best dog we found today. Small swing." / bottom line "Best dog we could find today, not a great one. Half a unit, don't get crazy." | the card running its own pick down. |
| a line under the pick that opens "Grizzlies ..." on a card headed "@ Grizzlies" | he read it as a Grizzlies pick. |

Where each came from (the root):

- the line under the pick fell back to the card's top-ranked body line - a 🚑 line about THEM - with no look at our side;
  `BOTTOM_WHY` then copied "short-handed" into the bottom line off that line's emoji;
- `sports_nba_roster.card_line` (the 🏀 line) is built from the roster's form table and never asked who's out tonight;
- `sports.card_extras` put our own injury line and the 🌟 "is out" part INTO the write-up;
- the floor play's bottom-line pool and `sports_dashboard.FLOOR_WHY` were written to sound humble - 4 of 4 header lines
  and 6 of 11 bottom lines knocked the pick;
- the page's 🚑 header showed only the OTHER team's men ("Grizzlies missing: ...") - so the only place a reader saw
  ours was inside the write-up.

## 2. The rule

A card is judged as a whole - before every post and on every render (`sports_card_check.card_state` / `coherent_line` /
`one_coherent`, inside `check` / `check_one`) - and the write-up asks the same questions before it writes
(`sports_breakdown_v24.inj_ok` / `whole_card`, `sports.card_extras`).

1. **An injury argument only when they are CLEARLY more short-handed than us.** One yardstick, both ways
   (`man_weight`, off the box scores): a top-3 scorer (NBA / hockey) or the #1 goalie = 3, the quarterback = 4, the lead
   back / a top-2 catcher = 2, any other regular = 1, a man who doesn't matter or has been gone for weeks = 0. The
   argument stands when theirs outweigh ours by 2 or more (`HURT_CLEAR`), or nobody who matters is out for us. Otherwise:
   no 🚑 / 📉 line about them, no named-absence lead, no "short-handed" in the bottom line - the best true fact for our
   side leads instead.
2. **A man who is out is never playing.** Never praised, counted or cited in an on / off stat - any line, any part of
   the 🏀 / 🌟 line, either team. It reads the whole report the card knows (its lists, the absence penalty's men, the men
   ruled out after it posted, every name the report has out) - not just the card's short list.
3. **Our own men out are said ONCE, plain, in the card's 🚑 header - both teams, no comment** ("🚑 Grizzlies out: ..." /
   "🚑 Warriors out: ... · questionable: ..."). Never in the write-up, the line under the pick, the bottom line or the
   🌟 line. The owner's FULL injury data rule stands - a bettor always sees who's out - and so does "I don't want bad
   shit in the breakdowns".
4. **The size words never run our own pick down.** A half unit says it's a smaller bet, plain ("Half a unit on
   Warriors."). `SELF_KNOCK` is the list; the pools were rewritten.
5. **Nothing fights its own card.** No "deep squad" / "N guys play real minutes" / "full strength" while our men who
   matter sit.
6. **The line under the pick says OUR side first.** A line that opens on the other team (or never names us) opens on us:
   its own "Give me Warriors" moves up front, or a plain head goes on ("Flyers the side: ...").

A failing line is rewritten or dropped, the card refills from its spare facts, and the catch is logged ("incoherent" in
the run log, `pick_audit.json` "card_check", `tools/card_audit.py`). Never a pick held.

## 3. The counts

Lines classed three ways: **incoherent** (an injury argument we can't make, a line that fights its card, a line under the
pick that opens on the other team), **false** (a man who is out said as playing), **bad for us** (our own men out inside
the write-up, the card knocking its own pick). "Before" = the same code with the whole-card rules switched off.

| what | cards | incoherent | false | bad for us | cards with one or more |
|---|---|---|---|---|---|
| the cards posted 11/5-11/19, **as they were written** | 41 | 27 | 1 | 24 | 29 |
| the same cards, as the page showed them before | 41 | 31 | 1 | 23 | 33 |
| the same cards, **on the page now** | 41 | 0 | 0 | 0 | 0 |
| the same cards, **re-written now** (as written) | 41 | 0 | 0 | 0 | 0 |
| the same cards, re-written now (on the page) | 41 | 0 | 0 | 0 | 0 |
| of those: both teams with men who matter out - before | 5 | 9 | 1 | 6 | 5 |
| of those: both teams with men who matter out - now | 5 | 0 | 0 | 0 | 0 |
| 11/19 slate (every moneyline side -150..+350), before | 53 | 26 | 1 | 3 | 24 |
| 11/19 slate, **now** | 53 | 0 | 0 | 0 | 0 |
| 11/20 slate (every moneyline side -150..+350), before | 7 | 5 | 0 | 0 | 5 |
| 11/20 slate, **now** | 7 | 0 | 0 | 0 | 0 |
| 11/21 slate (every moneyline side -150..+350), before | 45 | 21 | 0 | 0 | 21 |
| 11/21 slate, **now** | 45 | 0 | 0 | 0 | 0 |
| 11/22 slate (every moneyline side -150..+350), before | 8 | 4 | 0 | 0 | 4 |
| 11/22 slate, **now** | 8 | 0 | 0 | 0 | 0 |
| slates: both teams with men who matter out - before | 1 | 3 | 1 | 1 | 1 |
| slates: both teams with men who matter out - now | 1 | 0 | 0 | 0 | 0 |

Fact lines a card on the page (the 41 posted cards): 3.8 before, 3.6 now on the cards as they
were posted (most were written before the 11/18 refill kept spare facts), 6.4 re-written now. The slates: 11/19 300 -> 298, 11/20 48 -> 48, 11/21 250 -> 250, 11/22 45 -> 45 fact lines - taking the bad lines out did not make the cards shorter, the spare facts came in.

Honest about these numbers:

- **Most of the "incoherent" count is rule 6** - a line under the pick that opened on the other team ("🥊 The Senators got
  run in their own building ... Flyers the side."). Those were true and for us; they now say our side first. The lines
  that were flat wrong are the injury arguments, the out man praised, our men out in the write-up and the self-knocks -
  the tables below show which is which.
- **No network in this session** (ESPN's injury feed is blocked here), so the pros' injury reports in the dry run are what
  the posted cards themselves stored (their who's-out lists, the men ruled out later, the report's word on every name).
  The slates' NBA / NHL / NFL candidates that never posted were written with no report at all, so they carry no injury
  lines either way - the both-teams-hurt check on the slates is really the 11/19 games we hold cards for. College
  football has the official reports on file.
- The "now" zeros are counted by the same rules that do the cutting. A second, separate read (plain string checks over all
  195 "after" cards: our own out man named anywhere in the write-up, the knock words, "short-handed" while we're as
  short, a one-liner that names them first) also finds 0.

## 4. Before and after

### Warriors +180 at Grizzlies (11/19, NBA floor, ½u) - the card that set him off

The yardstick: Warriors 4, Grizzlies 4 (live, off the box scores) - not clearly more short-handed, so no injury argument.

As the page showed it (header: "💰 ½ UNIT Half a unit on the best dog we found today. Small swing." · "🚑 Grizzlies missing: Ty Jerome (G), Zach Edey (C), GG Jackson (F), Scotty Pippen Jr. (G)"):

```
WHY: 🚑 Grizzlies gotta play without Ty Jerome (G), Zach Edey (C). Give me Warriors.
  🚑 Warriors out: F Draymond Green (28 min a night last year), G Stephen Curry (31 min a night last year).
  📉 Ty Jerome was giving Grizzlies 25 points a night (11 games) and he's out.
  🔁 Same opponent, two results - Warriors got a 134-114 win over the Nuggets (10/26); Grizzlies took a 123-118 loss to 'em (11/11).
  🚪 120+ points allowed in 3 of the last 5 for Grizzlies. That defense is giving it away.
  🧳 The Grizzlies just got home - 3 road games in the last 6 days.
  🏟️ Grizzlies are 3-4 at home this year. That ain't a fortress.
  🗓️ Warriors won 6 of their last 10.
  ⏱️ Closing time: Warriors took the 4th quarter in 7 of their last 10.
  🏀 Warriors: their bench outscored teams by 8 a game last season - deep squad · 9 guys play real minutes · Gui Santos is cooking - with him on the floor lately the team's up 10.2 points a full game (last season: up 1.4) · Stephen Curry is cooking - with him on the floor lately the team's up 14.9 points a full game (last season: up 2.9) · Moses Moody on a minutes limit (about 22 tonight).
  ✅ Bottom line: Warriors (+180). Grizzlies are short-handed. Best dog we could find today, not a great one. Half a unit, don't get crazy.
  🌟 Warriors: Stephen Curry is out.
```

The same posted card on the page now (nothing re-written yet - the page's check alone):

```
SIZE: 💰  ½ UNIT Half a unit on the best dog on today's board.
WHY: 🔁 Same opponent, two results - Warriors got a 134-114 win over the Nuggets (10/26); Grizzlies took a 123-118 loss to 'em (11/11).
HEADER: 🚑 Grizzlies out: Ty Jerome (G), Zach Edey (C), GG Jackson (F), Scotty Pippen Jr. (G), Richie Saunders
HEADER: 🚑 Warriors out: Draymond Green (F), Brandon Williams (G), Stephen Curry (G), Kristaps Porzingis (C), Jimmy Butler III
  🚪 120+ points allowed in 3 of the last 5 for Grizzlies. That defense is giving it away.
  🧳 The Grizzlies just got home - 3 road games in the last 6 days.
  🏟️ Grizzlies are 3-4 at home this year. That ain't a fortress.
  🗓️ Warriors won 6 of their last 10.
  ⏱️ Closing time: Warriors took the 4th quarter in 7 of their last 10.
  🏀 Warriors: Gui Santos is cooking - with him on the floor lately the team's up 10.2 points a full game (last season: up 1.4).
  ✅ Bottom line: Warriors (+180). Half a unit on Warriors.
```

Re-written by the new writer (what the next run posts - version 75):

```
SIZE: 💰  ½ UNIT Half a unit on the best dog on today's board.
WHY: 🚪 Give me Warriors: 3 of the last 5 teams to play Grizzlies put up 120 or more.
HEADER: 🚑 Grizzlies out: Ty Jerome (G), Zach Edey (C), GG Jackson (F), Scotty Pippen Jr. (G), Richie Saunders
HEADER: 🚑 Warriors out: Draymond Green (F), Brandon Williams (G), Stephen Curry (G), Kristaps Porzingis (C), Jimmy Butler III
  🔁 Same opponent, two results - Warriors got a 134-114 win over the Nuggets (10/26); Grizzlies took a 123-118 loss to 'em (11/11).
  🧳 First game back for the Grizzlies after 3 road games in 6 days.
  🏟️ Grizzlies are 3-4 at home this year. That ain't a fortress.
  💯 Yaxel Lendeborg been cooking for Warriors - 19 a night over his last 10.
  🏁 7 of the last 10 times out, Grizzlies were behind after the 1st quarter.
  🗓️ 6 wins in the last 10 for Warriors.
  ⏱️ Warriors won the 4th quarter in 7 of their last 10 games. They close.
  ✅ Bottom line: Warriors (+180). Plus money on Warriors - half a unit.
```

### Broncos -142 vs Panthers (11/08, nfl) - both teams down two regulars (2 v 2) - the injury line and our own knock go, the header says both [yardstick 2 v 2]

Before:

```
WHY: 💪 Panthers are 3-4. Broncos are 6-2. Panthers fin to get spanked.
  📊 Scoreboard lately - Broncos: 25 scored, 18 allowed a game (last 3). Panthers: 19 and 28.
  🏟️ Panthers at home this season: 1-2.
  🚑 Panthers are down Will Lee III (CB), Bobby Okereke (LB) today.
  🥊 The Panthers got smacked 43-13 by the Buccaneers inside their last 5.
  🧊 Panthers are 3-4 and ice cold — 2 straight L's.
  🧯 Coaching change for the Panthers — "Panthers bring back DeAngelo Hall as CB coach in 1st move since Evero firing"
  🔥 Broncos can't stop winning: 4 straight, 6-2 overall.
  📅 How they came in: Broncos W 28-24 vs Chiefs · Panthers L 19-27 @ Packers.
  🎯 The quarterbacks - Bo Nix (Broncos): 3 TDs, 0 picks and 551 yards in his last 3 games. Bryce Young (Panthers): 4 TDs, 3 picks and 653 yards in his last 3 games.
  ⚠️ Heads up: Broncos go without Kris Abrams-Draine (CB), Brandon Jones (S).
  ✅ Bottom line: Broncos (-142). Easy money.
```

Now:

```
SIZE: 💰  1 UNIT The price is fair — a solid bet.
WHY: 💪 Riding Broncos: Panthers are 3-4. Broncos are 6-2. Panthers fin to get spanked.
HEADER: 🚑 Panthers out: Will Lee III (CB), Bobby Okereke (LB), Damien Lewis (G), Jaelan Phillips (LB)
HEADER: 🚑 Broncos out: Kris Abrams-Draine (CB), Brandon Jones (S)
  📊 Scoreboard lately - Broncos: 25 scored, 18 allowed a game (last 3). Panthers: 19 and 28.
  🏟️ Panthers at home this season: 1-2.
  🥊 The Panthers got smacked 43-13 by the Buccaneers inside their last 5.
  🧊 Panthers are 3-4 and ice cold — 2 straight L's.
  🧯 Coaching change for the Panthers — "Panthers bring back DeAngelo Hall as CB coach in 1st move since Evero firing"
  🔥 Broncos can't stop winning: 4 straight, 6-2 overall.
  📅 How they came in: Broncos W 28-24 vs Chiefs · Panthers L 19-27 @ Packers.
  🎯 The quarterbacks - Bo Nix (Broncos): 3 TDs, 0 picks and 551 yards in his last 3 games. Bryce Young (Panthers): 4 TDs, 3 picks and 653 yards in his last 3 games.
  ✅ Bottom line: Broncos (-142). Easy money.
```

### Boston College +190 vs Florida St (11/07, ncaaf) - 1 v 3 - the argument stands; it says Boston College first [yardstick 1 v 3]

Before:

```
WHY: 🚑 Florida St gotta play without Duce Robinson (WR), Ousmane Kromah (RB).
  🥊 Louisville spanked Florida St 44-20 within their last 5 games.
  🔥 Florida St has lost 3 straight — that coach is on the hot seat.
  🗑️ Florida St is in shambles - 3-5.
  🧳 Florida St on the road this season: 0-3.
  🧳 Travel check on Florida St: 1,100-mile trip east.
  💪 Boston College 4-4, Florida St 3-5 — close on paper, but our ratings have Boston College ahead.
  🏟️ Boston College protects the crib: 3-1 at home.
  ⚠️ Boston College goes without Onye Nwosisi (DL).
  ✅ Bottom line: Boston College (+190). Tap in.
```

Now:

```
SIZE: 💰  1 UNIT Real value here — worth a full unit.
WHY: 🚑 Boston College the side: Florida St gotta play without Duce Robinson (WR), Ousmane Kromah (RB).
HEADER: 🚑 Florida St out: Duce Robinson (WR), Ousmane Kromah (RB), Blake Nichelson (LB), Conor McAneney (K)
HEADER: 🚑 Boston College out: Onye Nwosisi (DL), Evan Dickens (RB), Isaiah Farris (DB), Justin Medlock (LB)
  🥊 Louisville spanked Florida St 44-20 within their last 5 games.
  🔥 Florida St has lost 3 straight — that coach is on the hot seat.
  🗑️ Florida St is in shambles - 3-5.
  🧳 Florida St on the road this season: 0-3.
  🧳 Travel check on Florida St: 1,100-mile trip east.
  💪 Boston College 4-4, Florida St 3-5 — close on paper, but our ratings have Boston College ahead.
  🏟️ Boston College protects the crib: 3-1 at home.
  ✅ Bottom line: Boston College (+190). Tap in.
```

### Packers -142 vs Vikings (11/15, nfl) - 2 v 7 - their QB out against our back: the argument stands, our own man out leaves the write-up [yardstick 2 v 7]

Before:

```
WHY: 🥊 The Vikings are coming off a 23-6 beating from the Bills, Vikings been trash as fuck.
  📊 Last 3: Packers are outscoring teams 30 to 22 a game; Vikings sit at 12 for, 17 against.
  🏟️ The Vikings play indoors at home. Today: 34° outside.
  📊 Packers score 24 points a game this year; Vikings manage 18.
  🚀 Packers just beat the brakes off the Patriots, 45-27.
  🏟️ 3-1 in their own building - Packers win more than they lose there.
  ⏳ Packers come in on 7 days rest; Vikings are on 6 days.
  📋 Packers are 6-3 on the year.
  ⚠️ Packers go without Josh Jacobs (RB).
  ✅ Bottom line: Packers (-142). Free money at this price.
```

Now:

```
SIZE: 💰  1 UNIT Not too expensive — worth a full unit.
WHY: 🥊 Packers the side: the Vikings are coming off a 23-6 beating from the Bills, Vikings been trash as fuck.
HEADER: 🚑 Vikings out: Kyler Murray (QB), Blake Cashman (LB), T.J. Hockenson (TE), Tyrion Ingram-Dawkins (DE)
HEADER: 🚑 Packers out: Josh Jacobs (RB), Sean Rhyan (G), Zaire Franklin (LB), Micah Parsons (DE)
  📊 Last 3: Packers are outscoring teams 30 to 22 a game; Vikings sit at 12 for, 17 against.
  🏟️ The Vikings play indoors at home. Today: 34° outside.
  📊 Packers score 24 points a game this year; Vikings manage 18.
  🚀 Packers just beat the brakes off the Patriots, 45-27.
  🏟️ 3-1 in their own building - Packers win more than they lose there.
  ⏳ Packers come in on 7 days rest; Vikings are on 6 days.
  📋 Packers are 6-3 on the year.
  ✅ Bottom line: Packers (-142). Free money at this price.
```

### Ducks +110 vs Avalanche (11/19, nhl) - 0 v 6 - MacKinnon and Makar out, nobody for us: untouched but for saying Ducks first [yardstick 0 v 6]

Before:

```
WHY: 🚑 The Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
  🔄 Update: Scott Wedgewood is projected in net for the Avalanche now, not Mackenzie Blackwood (not confirmed yet).
  😴 Second night of a back-to-back for Avalanche. Ducks are rested.
  📉 Avalanche loses Nathan MacKinnon - 30 points in his 20 games this year.
  🥊 4-1. That's what the Mammoth did to the Avalanche inside their last 5.
  🔁 They both saw the Senators lately: Ducks got a 6-3 win on 11/1, Avalanche took a 4-3 loss on 11/12.
  🧳 Road game, no problem: Ducks are 7-4 away from home this season.
  💣 3 of the last 5 times out, Ducks put up 4 or more.
  ✅ Bottom line: Ducks (+110). Avalanche is short-handed. Get in.
```

Now:

```
SIZE: 💰  3 UNITS Good value — we bet this one bigger.
WHY: 🚑 We on Ducks: the Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
HEADER: 🚑 Avalanche out: Cale Makar (D), Nathan MacKinnon (C)
  🔄 Update: Scott Wedgewood is projected in net for the Avalanche now, not Mackenzie Blackwood (not confirmed yet).
  😴 Second night of a back-to-back for Avalanche. Ducks are rested.
  📉 Avalanche loses Nathan MacKinnon - 30 points in his 20 games this year.
  🥊 4-1. That's what the Mammoth did to the Avalanche inside their last 5.
  🔁 They both saw the Senators lately: Ducks got a 6-3 win on 11/1, Avalanche took a 4-3 loss on 11/12.
  🧳 Road game, no problem: Ducks are 7-4 away from home this season.
  💣 3 of the last 5 times out, Ducks put up 4 or more.
  ✅ Bottom line: Ducks (+110). Avalanche is short-handed. Get in.
```

### Raptors +160 vs Knicks (11/15, nba) - our own men out and the self-knock leave the write-up [yardstick 0 v 0]

Before:

```
WHY: 🧊 The Knicks have lost 2 straight, Knicks super trash right now. We talking shit, but the tape says it.
  🔄 Update: Scottie Barnes is off the injury report now - expected to play.
  🚑 Raptors out: C Nate Bittle, F Kawhi Leonard · questionable: G Kevin McCullar Jr..
  🧳 2-3 on the road for Knicks.
  📊 Raptors score 114 points a game this year; Knicks manage 110.
  ✅ Bottom line: Raptors (+160). No big edge here - Raptors are just the best dog left on today's slate. Half a unit, keep it light.
```

Now:

```
SIZE: 💰  ½ UNIT Our best dog on the slate today. Half a unit.
WHY: 🧊 Give me Raptors: the Knicks have lost 2 straight, Knicks super trash right now. We talking shit, but the tape says it.
HEADER: 🚑 Raptors out: Nate Bittle (C), Kawhi Leonard (F) · questionable: G Kevin McCullar Jr
  🔄 Update: Scottie Barnes is off the injury report now - expected to play.
  🧳 2-3 on the road for Knicks.
  📊 Raptors score 114 points a game this year; Knicks manage 110.
  ✅ Bottom line: Raptors (+160). Half a unit, keep it light.
```

### Kansas St +200 vs Oklahoma St (11/07, ncaaf) - our quarterbacks out (4 v 1): no argument to make, and none was made - the header now says it [yardstick 4 v 1]

Before:

```
WHY: 🧳 Oklahoma St is 1-3 on the road this year.
  🏟️ 4-1 at home for Kansas St.
  🛡️ Kansas St gives up 22 points a game this year; Oklahoma St gives up 27. Our D is the better one.
  ⚠️ Heads up: Kansas St has dropped 2 straight.
  ✅ Bottom line: Kansas St (+200).
```

Now:

```
SIZE: 💰  1 UNIT Real value here — worth a full unit.
WHY: 🧳 Riding Kansas St: Oklahoma St is 1-3 on the road this year.
HEADER: 🚑 Oklahoma St out: Tate Romney (LB), Carson Kolb (TE), Dayvon Standard (WR), Jaleel Johnson (DE)
HEADER: 🚑 Kansas St out: Jacob Knuth (QB), Avery Johnson (QB)
  🏟️ 4-1 at home for Kansas St.
  🛡️ Kansas St gives up 22 points a game this year; Oklahoma St gives up 27. Our D is the better one.
  ⚠️ Heads up: Kansas St has dropped 2 straight.
  ✅ Bottom line: Kansas St (+200).
```

### Trail Blazers +110 vs Timberwolves (11/17, nba) - the line under the pick opened on the Timberwolves [yardstick 0 v 1]

Before:

```
WHY: 🚑 Timberwolves gotta play without Jonathan Kuminga (F). Riding Trail Blazers.
  🔄 Update: Deni Avdija is questionable now for the Trail Blazers.
  🔄 Update: Donte DiVincenzo is out for the Timberwolves too.
  🧳 6-2 on the road for Trail Blazers.
  ✅ Bottom line: Trail Blazers (+110). The dog angles like it. Trust the algorithm.
```

Now:

```
SIZE: 💰  ½ UNIT Our best dog on the slate today. Half a unit.
WHY: 🚑 Riding Trail Blazers: Timberwolves gotta play without Jonathan Kuminga (F).
HEADER: 🚑 Timberwolves out: Jonathan Kuminga (F), Jaylen Clark (G), Zyon Pullin (G), Anthony Edwards (G), Donte DiVincenzo
HEADER: 🚑 Trail Blazers out: Chris Youngblood (G), Vit Krejci (G), Ja Morant (G), Shaedon Sharpe (G)
  🔄 Update: Deni Avdija is questionable now for the Trail Blazers.
  🧳 6-2 on the road for Trail Blazers.
  ✅ Bottom line: Trail Blazers (+110). The dog angles like it. Trust the algorithm.
```

### Flyers +150 vs Senators (11/19, nhl) - the 2u Flyers card - the line under the pick opened on the Senators [yardstick 0 v 0]

Before:

```
WHY: 🥊 The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
  🔄 Update: Samuel Ersson is the Senators goalie now, not Linus Ullmark.
  ✅ Update: Samuel Ersson is confirmed in net for the Senators.
  ✅ Update: Joseph Woll is confirmed in net for the Flyers.
  🎬 7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by.
  🏹 Flyers put 270 shots on net their last 10 and gave up 241. More looks than the other guys, night after night.
  🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
  💯 Matvei Michkov been producing for Flyers: 9 points over the last 10.
  📅 Flyers come off a 4-3 win over the Sabres.
  ✅ Bottom line: Flyers (+150). Already beat 'em once this year. Ride it.
```

Now:

```
SIZE: 💰  2 UNITS Bigger bet.
WHY: 🥊 Flyers the side: the Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
  🔄 Update: Samuel Ersson is the Senators goalie now, not Linus Ullmark.
  ✅ Update: Samuel Ersson is confirmed in net for the Senators.
  ✅ Update: Joseph Woll is confirmed in net for the Flyers.
  🎬 7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by.
  🏹 Flyers put 270 shots on net their last 10 and gave up 241. More looks than the other guys, night after night.
  🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
  💯 Matvei Michkov been producing for Flyers: 9 points over the last 10.
  📅 Flyers come off a 4-3 win over the Sabres.
  ✅ Bottom line: Flyers (+150). Already beat 'em once this year. Ride it.
```

### Capitals +105 vs Senators (11/10, nhl) - a floor play's bottom line talking its own price down [yardstick 0 v 0]

Before:

```
WHY: 🥊 6-3. That's what the Ducks did to the Senators inside their last 5.
  📋 9-6 for Capitals, last time out a 4-3 win over the Panthers.
  ⚠️ Biggest knock on Capitals: Samuel Ersson (Senators, in net last time out) is at a 0.949 save % over his last 3 starts to Logan Thompson's 0.841 (our guy in net last time out).
  ✅ Bottom line: Capitals (+105). The price is about right - Capitals grade out best of every dog on the slate, that's why it's up. Half a unit.
```

Now:

```
SIZE: 💰  ½ UNIT Half a unit on the best dog on today's board.
WHY: 🥊 Capitals the side: 6-3. That's what the Ducks did to the Senators inside their last 5.
  📋 9-6 for Capitals, last time out a 4-3 win over the Panthers.
  ⚠️ Biggest knock on Capitals: Samuel Ersson (Senators, in net last time out) is at a 0.949 save % over his last 3 starts to Logan Thompson's 0.841 (our guy in net last time out).
  ✅ Bottom line: Capitals (+105). Half a unit.
```

### Heat +160 vs Pistons (11/14, nba) - "don't go crazy" [yardstick 0 v 0]

Before:

```
WHY: 🧠 The Heat hasn't lost in 3. Small bet on Heat - half a unit at about a fair price.
  📊 Scoreboard lately - Heat: 121 scored, 113 allowed a game (last 3). Pistons: 127 and 124.
  📅 The Heat is off a 133-121 win over the Cavaliers, the Pistons off a 144-140 win over the Wizards.
  ⚠️ Heads up: Heat played last night (a 133-121 win over the Cavaliers) and Pistons sat 2 days.
  ✅ Bottom line: Heat (+160). Best dog on the slate by our angles. Half a unit, don't go crazy.
  🌟 Heat: Giannis Antetokounmpo (All-NBA 2025, top-5 MVP) is in the lineup tonight.
```

Now:

```
SIZE: 💰  ½ UNIT Half a unit - the best dog on the board.
WHY: 🧠 The Heat hasn't lost in 3. Small bet on Heat - half a unit at about a fair price.
HEADER: 🚑 Pistons out: Isaiah Joe (G), Jalen Duren (C)
  📊 Scoreboard lately - Heat: 121 scored, 113 allowed a game (last 3). Pistons: 127 and 124.
  📅 The Heat is off a 133-121 win over the Cavaliers, the Pistons off a 144-140 win over the Wizards.
  ⚠️ Heads up: Heat played last night (a 133-121 win over the Cavaliers) and Pistons sat 2 days.
  ✅ Bottom line: Heat (+160). Best dog on the slate by our angles.
  🌟 Heat: Giannis Antetokounmpo (All-NBA 2025, top-5 MVP) is in the lineup tonight.
```

### Ole Miss +145 vs Georgia (11/07, ncaaf) - our own men out in the write-up, twice [yardstick 1 v 0]

Before:

```
WHY: 🗑️ Gunner Stockton has been throwing it to the other team — 3 TDs, 3 picks and 622 yards in his last 3 games.
  🚑 Ole Miss out: RB Kewan Lacy (starter), WR Samari Reed · questionable: DE Kam Franklin (starter), LB Keaton Thomas (starter).
  🚀 Ole Miss just beat the brakes off Auburn, 45-15.
  📋 Ole Miss is 6-2 on the year.
  🎯 Trinidad Chambliss for Ole Miss: 7 TDs, 4 picks and 754 yards in his last 3 games.
  ⚠️ What could fuck this up: Ole Miss goes without Kewan Lacy (RB).
  ✅ Bottom line: Ole Miss (+145).
```

Now:

```
SIZE: 💰  1 UNIT Good value at this price. Full unit.
WHY: 🗑️ Give me Ole Miss: Gunner Stockton has been throwing it to the other team — 3 TDs, 3 picks and 622 yards in his last 3 games.
HEADER: 🚑 Georgia out: Amaris Williams (OLB)
HEADER: 🚑 Ole Miss out: Kewan Lacy (RB), Izaiah Hartrup (WR), Edwin Joseph (S), Nascar McCoy (S) · questionable: DE Kam Franklin (starter), LB Keaton Thomas (starter)
  🚀 Ole Miss just beat the brakes off Auburn, 45-15.
  📋 Ole Miss is 6-2 on the year.
  🎯 Trinidad Chambliss for Ole Miss: 7 TDs, 4 picks and 754 yards in his last 3 games.
  ✅ Bottom line: Ole Miss (+145).
```

### Sharks +120 vs Islanders (11/09, nhl) - "Not a big edge on the price" [yardstick 0 v 0]

Before:

```
WHY: 🥊 The Oilers spanked the Islanders 4-0 within their last 5 games.
  🧳 The Islanders put in the miles to get here (2,560-mile trip west).
  🧳 Islanders on the road this season: 3-4.
  🏒 Islanders got outshot bad last time - 40 or more shots against in that 5-4 loss to the Devils - on a short turnaround.
  ⚠️ Heads up: Sharks have dropped 5 straight.
  ✅ Bottom line: Sharks (+120). Not a big edge on the price - every angle we grade a dog on likes Sharks here. Half a unit, keep it light.
```

Now:

```
SIZE: 💰  ½ UNIT Best dog on the slate by our angles. Half a unit.
WHY: 🥊 We on Sharks: the Oilers spanked the Islanders 4-0 within their last 5 games.
HEADER: 🚑 Islanders out: Ryan Pulock (D)
  🧳 The Islanders put in the miles to get here (2,560-mile trip west).
  🧳 Islanders on the road this season: 3-4.
  🏒 Islanders got outshot bad last time - 40 or more shots against in that 5-4 loss to the Devils - on a short turnaround.
  ⚠️ Heads up: Sharks have dropped 5 straight.
  ✅ Bottom line: Sharks (+120). Half a unit, keep it light.
```

### Avalanche -130 vs Ducks (11/19 candidate, nhl) - the other side of the Ducks game: OUR two best players out (6 v 0) - they leave the write-up, the header has them

Before:

```
WHY: 🥊 The Ducks got run on the road twice already this year - 5-2 by the Rangers and 4-1 by the Devils. Give me Avalanche.
  🚑 Avalanche out: D Cale Makar, C Nathan MacKinnon.
  🚪 4+ goals allowed in 3 of the last 5 for Ducks. That defense is giving it away.
  💪 Avalanche 12-10, Ducks 11-11 — close on paper, but our ratings have Avalanche ahead.
  🏟️ Avalanche protects the crib: 7-3 at home.
  🛡️ Avalanche gives up 3.1 goals a game this year; Ducks give up 3.9. Our D is the better one.
  ⏱️ Avalanche put up 16 goals in the third period over their last 10 and gave up 7.
  📅 Ducks off an 8-6 loss to the Blues last time out.
  🥅 The Ducks' goalie Lukas Dostal has been giving up a lot of goals — a 0.783 save % (15 goals on 69 shots) over his last 3 starts.
  ✅ Bottom line: Avalanche at -130. Fair price, right spot - that's the bet.
```

Now:

```
WHY: 🥊 Give me Avalanche: the Ducks got run on the road twice already this year - 5-2 by the Rangers and 4-1 by the Devils.
HEADER: 🚑 Avalanche out: Cale Makar (D), Nathan MacKinnon (C)
  🚪 4+ goals allowed in 3 of the last 5 for Ducks. That defense is giving it away.
  💪 Avalanche 12-10, Ducks 11-11 — close on paper, but our ratings have Avalanche ahead.
  🏟️ Avalanche protects the crib: 7-3 at home.
  🛡️ Avalanche gives up 3.1 goals a game this year; Ducks give up 3.9. Our D is the better one.
  ⏱️ Avalanche put up 16 goals in the third period over their last 10 and gave up 7.
  📅 Ducks off an 8-6 loss to the Blues last time out.
  🥅 The Ducks' goalie Lukas Dostal has been giving up a lot of goals — a 0.783 save % (15 goals on 69 shots) over his last 3 starts.
  ✅ Bottom line: Avalanche at -130. Fair price, right spot - that's the bet.
```

### Temple -142 vs Rice (11/19 candidate, ncaaf) - college football, our starter out and our QB questionable

Before:

```
WHY: 🧳 Rice on the road this season: 0-5. We on Temple, no hesitation.
  🚑 Temple out: LB Jayvant Brown (starter) · questionable: QB Ajani Sheppard (starter).
  🧊 Rice hasn't won in 9 games.
  📊 Last 3 for Rice: 30 scored a game, 41 given up.
  📊 Rice this season: 33 points a game allowed, 21 scored. They get outscored.
  🛡️ On the year Temple allows 29 a game, Rice 33.
  💸 As the dog this year Rice lost all 6. They don't sneak up on people.
  📅 Last time out Rice took a 20-17 loss to Tulane.
  🕐 Rice is playing off their home time zone. Body clock's off.
  ✅ Bottom line: Temple (-142). This one's up on the spot Temple is in.
```

Now:

```
WHY: 🧳 Give me Temple: Rice on the road this season: 0-5. We on Temple, no hesitation.
HEADER: 🚑 Rice out: Jordan Clark (WR), Ben Grice (WR), Chibby Nwajuaku (DL), Colten Cole (TE)
HEADER: 🚑 Temple out: Jayvant Brown (LB), Brandon Enarusai (DL), Devontae Ward-Grant (CB), Jett White (CB) · questionable: QB Ajani Sheppard (starter)
  🧊 Rice hasn't won in 9 games.
  📊 Last 3 for Rice: 30 scored a game, 41 given up.
  📊 Rice this season: 33 points a game allowed, 21 scored. They get outscored.
  🛡️ On the year Temple allows 29 a game, Rice 33.
  💸 As the dog this year Rice lost all 6. They don't sneak up on people.
  📅 Last time out Rice took a 20-17 loss to Tulane.
  🕐 Rice is playing off their home time zone. Body clock's off.
  ✅ Bottom line: Temple (-142). This one's up on the spot Temple is in.
```

### Titans +308 vs Cowboys (11/22 candidate, nfl) - an NFL candidate - the line under the pick opened on the Cowboys

Before:

```
WHY: 🧳 1-3 at home for the Cowboys this season. Live dog. We got Titans.
  📊 Cowboys have been outscored 34 to 32 a game over their last 3.
  🛡️ On the year Titans allow 27 a game, Cowboys 28.
  📅 The Cowboys come in off a 46-40 loss to the 49ers.
  📋 4-6 for Cowboys this season - more L's than W's.
  💸 Cowboys lost 4 of 7 as the favorite this year. That's a favorite that loses.
  🗓️ Just 4 wins in the last 10 for Cowboys.
  ✅ Bottom line: Titans (+308). Titans are the play because of the spot, and the units say how much.
```

Now:

```
WHY: 🧳 We got Titans: 1-3 at home for the Cowboys this season. Live dog.
  📊 Cowboys have been outscored 34 to 32 a game over their last 3.
  🛡️ On the year Titans allow 27 a game, Cowboys 28.
  📅 The Cowboys come in off a 46-40 loss to the 49ers.
  📋 4-6 for Cowboys this season - more L's than W's.
  💸 Cowboys lost 4 of 7 as the favorite this year. That's a favorite that loses.
  🗓️ Just 4 wins in the last 10 for Cowboys.
  ✅ Bottom line: Titans (+308). Titans are the play because of the spot, and the units say how much.
```

### Georgia St +110 vs Marshall (11/21 candidate, ncaaf) - college football Saturday - the same

Before:

```
WHY: 🎬 4 of Marshall's 5 wins this year came by one score - the last two 36-35 over Gardner-Webb and 20-13 over South Alabama. They been squeaking by. Riding Georgia St.
  🔁 Same opponent, two results - Georgia St got a 39-23 win over App State (11/7); Marshall took a 20-16 loss to 'em (11/14).
  📊 Marshall has been outscored 31 to 22 a game over their last 3.
  📊 Georgia St put up 33 a game on the year; Marshall can only find 22.
  🛡️ Marshall is leaking 31 points a game this season. Georgia St holds teams to 27.
  🏈 Georgia St is one W from a bowl game. Extra motivation.
  🎟️ Marshall failed to cover in 4 of their last 6 games.
  💥 10 sacks in the last 3 games for Georgia St, 6 for Marshall.
  ✅ Bottom line: Georgia St (+110). Marshall been squeaking by. Georgia St is the play because of the spot, and the units say how much.
```

Now:

```
WHY: 🎬 Riding Georgia St: 4 of Marshall's 5 wins this year came by one score - the last two 36-35 over Gardner-Webb and 20-13 over South Alabama. They been squeaking by.
  🔁 Same opponent, two results - Georgia St got a 39-23 win over App State (11/7); Marshall took a 20-16 loss to 'em (11/14).
  📊 Marshall has been outscored 31 to 22 a game over their last 3.
  📊 Georgia St put up 33 a game on the year; Marshall can only find 22.
  🛡️ Marshall is leaking 31 points a game this season. Georgia St holds teams to 27.
  🏈 Georgia St is one W from a bowl game. Extra motivation.
  🎟️ Marshall failed to cover in 4 of their last 6 games.
  💥 10 sacks in the last 3 games for Georgia St, 6 for Marshall.
  ✅ Bottom line: Georgia St (+110). Marshall been squeaking by. Georgia St is the play because of the spot, and the units say how much.
```

## 5. What changed, file by file

- `sports_card_check.py` - the whole-card rules (section "EVERY CARD MAKES SENSE AS A WHOLE"): `out_men`, `man_weight`,
  `hurt`, `inj_ok`, `card_state`, `inj_arg`, `our_outs_line`, `out_plays`, `fights`, `bottom_coherent`, `side_first`,
  `coherent_line`, `one_coherent`, `coherent`, `out_chips`; wired into `check` (every body line + the bottom line + every
  spare fact that refills a card), `check_one` (the line under the pick and its fallback), `early_lines` (an early row
  never runs its own play down) and `quality` (the audit's new "incoherent" kind). Switch `COHERENT`, from
  `COHERENT_FROM` 11/19.
- `sports_breakdown_v24.py` - `inj_ok` read once at the top of the write-up (`leg["inj_ok"]`) and asked by every injury
  pool (the body's 🚑 lines, `more_facts`' who's-out line, `deep_facts`' 📉 line, `named_out_ways`, `BOTTOM_WHY`); no
  "both teams are down their starting QB" line; the floor / fair-price bottom-line pools say the pick and the size;
  `whole_card` - the last step: the card through the same rules, and a line under the pick that can't stand gives way
  to the next best fact.
- `sports.py` `card_extras` - our own 🚑 line is no longer a write-up line (our game-time men ride on `leg["our_q"]`
  for the header); the 🏀 line drops any man the report has out, our man's minutes limit / game-time call, and "deep
  squad" / "N guys play real minutes" while our men who matter sit; the 🌟 line never says our man is out.
- `sports_dashboard.py` - the card's 🚑 header shows BOTH teams ("X out: ..."), ours with its questionable men; the
  size line's pools (`FLOOR_WHY`, `HALF_WHY["early"]`) say the size, and a last stop takes any knock off it.
- `sports_breakdown.py` - `VERSION` 75.
- `sports_test.py` - `test_cards_1119b_every_card_makes_sense_as_a_whole_the_warriors_card` (the live card as a
  fixture), `test_cards_1119b_the_write_up_never_puts_our_men_out_or_an_out_man_cooking_on_the_card` (the root),
  `test_cards_1119b_both_sides_hurt_a_hockey_card_and_a_football_card`; three older tests that asserted the old
  humble wording ("best dog left", "about fair") now assert it is gone.

## 6. Left open

- The yardstick is box-score simple on purpose (points / starts / minutes / the QB). It does not know a defensive
  anchor from a bench big; `sports_absences.matters` decides who counts at all.
- College hoops has no top-scorer table in `sports_absences.key_players`, so every man in the top 5 by minutes
  counts 1 - a star and a fifth starter weigh the same there.
- A card posted before 11/19 keeps its lines on the page's check (the date gate) - those are graded and off the board.
- The first live run should be read once: the pros' reports could not be fetched in this session.

