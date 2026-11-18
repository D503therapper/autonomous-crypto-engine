# 11/18 - CARD QUALITY: does every line on a card make the case for our pick?

The owner, 11/18, on the Nuggets +120 card: "The breakdown for the Nuggets is terrible. Strother is not a key player, and
there's a few things in the breakdown where it doesn't make the Nuggets look good, and the breakdown just sucks." / "This
has been a major problem with these breakdowns ... making mistakes and being stupid and not right. This needs to be fixed
permanently." And the same afternoon, after the knocks were cut off that card: "Now you just took out the lines that I said
were trash, and it's just short and fucking vague and a real shitty fucking breakdown. This is a fucking permanent bug."

The 11/17 sweep (`results/studies/cards_1117`) asked: is every line TRUE and current? This one asks what that sweep
couldn't: every line below was true - and still wrong on a card.

Run it again any time:

    python tools/card_audit.py --since 2026-11-01 --raw     # the cards as they were written + the quality count
    python tools/card_audit.py --since 2026-11-01           # the same cards as the page shows them today
    python tools/card_audit.py                              # the live cards (what the hourly bug check reads)

## 1. What was graded

Every card posted 11/1 - 11/18 (`data/sports/picks.json` + `data/sports/early.json`, read only): 49 board cards (hockey 23, NBA 11,
college football 9, NFL 3, college hoops 3) and 25 early plays (the 🏀 opening-line
play, the spots, the 🌍 under, the ⛰️ over, the 🏀 over, the exam scan). Three ways: (1) as they were posted, (2) the 49
board cards re-written by the morning's code, (3) re-written by tonight's code - plus a dry run of the 11/19 slate (every
moneyline side the engine prices from -150 to +350, its card written and graded). Live plus money's pools were read line
by line (they only exist during a game).

Each line was graded on five questions: does it argue FOR our side (or against theirs)? Is it something a bettor says
and cares about? Does it say anything new? Does it read right? Is the man it names out someone who matters?

## 2. The count

| kind of bad line | as posted (74 cards, 531 lines) | the 49 board cards re-written by the morning's code (424 lines) | by tonight's code | on the page tonight |
|---|---|---|---|---|
| **knocks our own side** in the body or under the pick (our loss, our skid, our losing record, our bad numbers) | **52** | 39 | 0 | 0 |
| **names a man out who doesn't matter** (a bench man, a man out for weeks) | **25** | 14 | 0 | 0 |
| **says nothing** ("1-1 at home", "A wash on the records", "Dead even on the record") | **15** | 13 | 0 | 0 |
| **jargon** ("per 48 minutes", "a +2 team a game", "13 points better than their record") | **14** | 6 | 0 | 0 |
| **argues for THEM** ("The Kraken won their last one too", "Both teams are rolling") | **10** | 9 | 0 | 0 |
| **said twice** (the one-liner's fact again, the same game in two or three lines) | **9** | 14 | 0 | 0 |
| **all** | **125** | **95** | **0** | **0** |

About one line in four on a posted card was one of these. None was false - the 11/17 audit passed every one.

How thin the cards were (fact lines a reader sees, the ⚠️ / bottom / update lines not counted):

| | average | under 6 | under 4 | under 2 |
|---|---|---|---|---|
| the 49 board cards re-written by the morning's code, after the page's cuts | 4.7 | 36 | 17 | 2 |
| by tonight's code (the refill) | 5.6 | 23 | 4 | 0 |

## 3. Real examples, before -> after

| card | the line | what was wrong | now |
|---|---|---|---|
| 11/18 Nuggets +120 (2u Dog, ⭐) | "⚠️ Biggest knock on Nuggets: Nuggets go without Julian Strawther (G)." | a bench guard who hadn't played in the team's last 5 | no line - he doesn't matter by the box scores; the knock is the real one ("Celtics come in 11-3 to Nuggets' 7-5") |
| 11/18 Nuggets | "📋 Nuggets are 7-5 after a 117-105 loss to the Suns." + "📅 The Celtics come in off a 115-105 loss to the Magic; the Nuggets off a 117-105 loss to the Suns." | our own loss, twice, in the body | "📋 Nuggets sit 7-5 so far." + "📅 The Celtics are fresh off a 115-105 loss to the Magic." |
| 11/18 Nuggets | "🧳 ... (1,760-mile trip west)" + "🏔️ Thin air — 5,300 feet up" under a one-liner that said both | the one-liner again | gone; in their place "💯 Jamal Murray is giving Nuggets 26 a night over the last 10 games he's played." + the 🏀 bench line + the 🌟 star line |
| 11/18 Nuggets | "🏀 ... their bench outscored teams by 6.1 per 48 minutes last season" | a stat sheet's unit | "... by 6.1 points for every full game it played last season - deep squad" |
| 11/7 Rangers -135 | "📅 The Kraken won their last one too, a 2-1 win over the Flames." | argues for the other side | their win is the ⚠️ knock or nothing; the body says "📋 Rangers 9-8 on the year - last time out, a 3-2 win over the Flyers." |
| 11/11 Ducks -142 | "🔥 Both teams are rolling: Ducks have won 5 straight, Predators 5." + "⚖️ Ducks 10-8, Predators 9-9. A wash on the records." | half of it is their case; the other says nothing | "🔥 Ducks have won 5 straight (10-8)." + "📋 Ducks sit 10-8; Predators are 9-9. Better record's on our side." |
| 11/5 Flyers +124 | "📊 Last 3: Flyers score 3.3 and give up 4 a game; Rangers score 2.3 and give up 3.7." | our bad numbers in our own case | "📊 Rangers have been outscored 3.7 to 2.3 a game over their last 3." |
| 11/9 Canucks +114 (2u Dog) | "🎲 By goals scored and allowed, Canucks should be about 13 points better than their record." | a formula's answer nobody can check | said only as the real goals for / against, and only when they've scored at least as many as they've allowed |
| 11/15 Packers -142 (Lock) | the 45-27 win over the Patriots in 🚀, 📅 AND 📋; "Vikings are down their starting quarterback" under a one-liner that said it | one game three times | once: the 🚀 line; the record line reads "📋 Packers are 6-3 on the year." |
| 11/17 Trail Blazers +110 | "⚠️ ... Trail Blazers come off a 106-98 loss to the Timberwolves while Timberwolves just took a 106-98 win over the Trail Blazers." | one game said both ways | "Timberwolves beat Trail Blazers 106-98 last time out" |
| 11/9 🏀 Grizzlies +117 (opening line) | "... Grizzlies are 6-3, Raptors 5-4; Grizzlies lost their last by 31." | a knock on our side under the pick | "... Grizzlies are 6-3, Raptors 5-4." (our last game only when we won it, theirs only when they lost it) |
| 11/17, 11/18 ⛰️ overs | "0-1 since we started betting it" | the play's own losing record on its card | off the card (the record lives in the records) |

The Nuggets card, start to finish:

    AS POSTED (11/18, 8 AM)                                        TONIGHT'S CODE
    🧠 The Celtics gotta breathe 5,300 feet up. Nuggets fin to     🧠 (the same one-liner)
       handle that. Plus Celtics flew 1,760 miles for this.
    🧳 The Celtics put in the miles (1,760-mile trip west).        📅 The Celtics are fresh off a 115-105 loss to the Magic.
    🗓️ Nuggets are 3-2 over their last 5.                          📋 Nuggets sit 7-5 so far.
    🏔️ Thin air — 5,300 feet up. ...                               🗓️ Nuggets are 3-2 over their last 5.
    📋 Nuggets are 7-5 after a 117-105 loss to the Suns.           💯 Jamal Murray is giving Nuggets 26 a night over the last
    📅 The Celtics ... loss to the Magic; the Nuggets off a           10 games he's played.
       117-105 loss to the Suns.                                   🏀 Nuggets: their bench outscored teams by 6.1 points for
    🏀 ... bench outscored teams by 6.1 per 48 minutes ...            every full game it played last season - deep squad · the
    ⚠️ Biggest knock on Nuggets: Nuggets go without Julian            coach plays 7 guys real minutes.
       Strawther (G).                                              ⚠️ Biggest knock on Nuggets: Celtics come in 11-3 to
    ✅ Bottom line: Nuggets (+120). We price Nuggets at +103,         Nuggets' 7-5.
       the book's at +120.                                         ✅ Bottom line: Nuggets (+120). We price Nuggets at +103,
    🌟 Nuggets: Jamal Murray (All-NBA 2026) is in the lineup.         the book's at +120.
                                                                   🌟 Nuggets: Jamal Murray (All-NBA 2026) is in the lineup tonight.

(In between, the afternoon's rewrite had left it at three lines: the knocks were cut on the page and nothing came back,
and the 🏀 / 🌟 lines were lost - section 4, items 1 and 2.)

## 4. Root causes and fixes

1. **A cut left a hole.** The card check took the bad lines off the page and the write-up had nothing to put back.
   `sports_breakdown_v24.fill_facts`: a card under its floor (6 fact lines a unit play, 5 a lean) refills from real
   facts for our side - our top scorer with his numbers off the box scores (never a man on the out / questionable
   list), our scoreboard lately and on the year, theirs when it's bad, the last 10, the price in plain words. Never
   filler; when the files hold nothing more the card stays short and the audit calls it thin.
2. **The 🏀 bench line and the 🌟 star line vanished in a rewrite.** The roster read is built only when the NBA board is;
   a rewrite run found none (`sports_nba_roster.cached()` was None) and `card_extras` wrote neither. `add_breakdowns`
   builds it.
3. **The pools wrote both sides of the story.** `more_facts` printed "both last games", "both records", the points
   lately and the goalies whatever they said, tagged the bad ones "neutral" and left them in the body. Now each fact
   builder says its fact for our side or sends it to the knock list (the one ⚠️ line): the record line never carries our
   loss, a losing record of ours is no body line, each last game is said only when it argues for us, their win / heater
   / better numbers are knocks, a .500 home / road record and two even goalies / quarterbacks are no line.
4. **The same fact two or three times.** The one-liner is written from the same facts as the body.
   `sports_breakdown_v24.no_repeats`: the one-liner's sentence, its miles / feet, the men it named, and a game score a
   better line already carries are never said again; a two-game 📅 line keeps the half that is news.
5. **Who's out read the whole report.** `sports_absences.who_matters` / `matters`, every league: NBA a top-3 scorer or a
   starter; college hoops the top-5 minutes men; hockey a top-6 forward / top-4 defenseman by ice time or the #1 goalie;
   football a regular. Never a man who sat the team's last 5 box scores (2 in football). Read by the 🚑 list on the
   card, the ⚠️ knock, the one-liner (`who_plays_only`, `sports.injury_line`, `sports_card_check.absent_matters`).
6. **Stat-sheet words.** "per 48 minutes" -> "a full game"; "a +2.3 team a game" -> "win by 2.3 a game"; the goal-math
   line -> the real goals; "finished +0.9 in point margin" -> "came out 0.9 points a game to the good".
7. **The early rows.** `sports_early.nba_open_why` / `exam_words` say our last game only when we won it and theirs only
   when they lost it; a losing live record is not on the card; "Mavericks's" reads "Mavericks'".
8. **Two spots said as a knock on us** - the revenge game ("took a 27-20 loss") and puck luck ("been snakebit ... only 21
   went in"): now what THEY did and what we owe them; the shots we put on net.
9. Small ones: "Kansas St" no longer reads as "Oklahoma St" in the knock check (a shared last word), "hasn't lost in 3"
   is no knock, a headline about them winning is never their "drama" line, a one-day rest edge in a football week is no
   line, "an 8-game heater", the dome line reads right, live plus money never says our side "been booty cheeks".

## 5. The standing check

- `sports_card_check` - on every render (the page, the brain, the early rows) and before a card posts:
  `for_us` (Q_KNOCK / Q_OPP / Q_NOTHING / Q_JARGON + the one-liner's fact again), `absent_matters` (Q_ABSENT - a
  non-key name comes off the line, a line of only non-key men goes), `said_twice` (Q_REPEAT), `early_for_us`.
- `tools/card_audit.py` - the card-quality score, every page build (`card_audit.json` "quality"): 100 = clean; -15 for
  each bad line the write-up put on the card, -25 for one a reader can still see, -20 for a unit play with under 2 fact
  lines. On the hourly bug check (`tools/health.py`) a QUALITY PROBLEM is: a bad line still on the page; a live card
  whose write-up put 3+ bad lines on it (a pool went bad - fix it at the root); a thin live unit card. The score is
  printed every hour.

## 6. What is still short (honest)

A bad team that is our dog has few real facts for it - 4 of the 49 re-written cards still show under 4 fact lines
(a team on a 9-game skid with a losing record at home and on the road). The refill never pads: the log says
BREAKDOWN SHORT and the audit calls a card under 2 lines thin. Football has no top-scorer line (its fact is the
quarterback line, which is only said when his numbers are good). The trip's miles, the weather line and a quoted
headline are still not re-derived (the 11/17 list).

## 7. Tests

`test_cards_1118_*` in `sports_test.py` (four): the refill + the roster read on a rewrite; every kind of bad line and the
pools at the root + nothing said twice; who matters in every league + old news; the early rows + the quality score and
its PROBLEM lines. `sports_breakdown.VERSION` 67 rewrites the open cards (the pick never changes).
