# 11/23 - EVERY REASON ON THE CARD

The owner, 11/23, the day after cards_1122 ("the card sells the pick"): **"I'm reading through the full breakdowns, and
they're really short and vague on some of them. We need to be more thorough on these breakdowns, on why we're choosing
them, and sell our picks, basically."**

**No pick, price or unit size changed.** Wording only; `sports_breakdown.VERSION` 86 rewrites the open cards on the next run.

## 1. What was wrong - measured

The three cards of 11/23 (VERSION 85):

| the card | what it said | what was missing |
|---|---|---|
| San José St +105 1u (the dog slot - the read: the ratings back them on this floor, the favorite lost its last) | 3 lines: UC San Diego's last loss, the last 3 on the scoreboard, a scorer | everything the read stands on |
| Indiana St +124 1u (the dog slot, the same read) | their last loss + "East Carolina been trash as fuck", the SECOND half of the last 5, the FIRST half of the last 5, a scorer | the two halves are one fact said twice; nothing on why |
| Washington +11.5 ½u (the spread stack: BYU's top scorer Robert Wright III, 23.8 a game, sat their last game + BYU lucky from three) | 8 lines about Washington - the same record twice, both halves | the ONE named reason was nowhere on the card |

Why, on all 13 college hoops unit cards posted 11/12-11/23, re-written by VERSION 85's writer:

| cause | cards |
|---|---|
| the sell layer wrote NO line at all | 11 of 13 |
| - the schedule guard went quiet (`SCHED_EDGE`: their schedule 50+ rating points tougher than ours) and nothing took its place | 8 (Northern Iowa, UMBC, Charleston So, UTEP, UT Rio Grande, William & Mary, Washington, San José St) |
| - the schedules were level but no box gap cleared a bar | 3 (Niagara, Indiana St twice) |
| the reason "the ratings back this side" (the dog read) had no fact pool | 9 dog-slot cards |
| the stack's reason "their top scorer sat" had no line - the posted leg never kept his name (`opp_top_out_who` came in on 11/23, after these posted) | 3 (Niagara, William & Mary, Washington) |
| "lucky from three" had a line only when teams MISS against them or their last 5 ran hot - not when their own threes fall all year | Washington, Indiana St (11/21) |
| both halves on the scoreboard / the same record twice | 4 repeats on these 13 as re-written, 10 as they posted |
| the page cut a TRUE line: "won 3 of their last 5 games by 10 or more" read as a record ("the games say 4-1") | 4 candidate cards on 11/24 |

It was not missing box scores (every one of these teams' games has both box lines), and it was not the card check
cutting sell lines. The D1-only rule cost two cards their comparison (Austin Peay and Delaware St had 2-3 D1 games on
file) - those two stay short, honestly.

## 2. The fix - at the root

1. **Every reason a college hoops leg carries has its fact line** (`sports_card_sell.sell_facts`):

   | the reason on the leg | the line |
   |---|---|
   | the stack / the dog weight: their top scorer missed their last game | 🪑 "BYU's top scorer Robert Wright III (23.8 a game) sat out their last game." - off the mark, or off the reason text when the leg was posted before the mark kept the name (`top_out_who`) |
   | lucky from three across (`opp_tp_net` +5 or more) | 👌 the real makes / attempts: teams missing against them ("45 for 171 against Troy - 26%") or their own threes running hot ("BYU are 64 for 151 from three - 42%"), said as it coming back down - never praise |
   | the glass (the study weight, the stack's `reb_gap` 6+) | 🧲 both margins against D1 teams, whenever the gap is still 3+ there |
   | the hot-ATS side across (`ats_gap`) | 🧭 a COUNT: "BYU beat the spread in 7 of their 10 games this year. Nobody keeps that up." - never a price claim |
   | the top-25 team on the road in Nov-Dec | 🧭 their true road games: "haven't played a true road game yet this year" / "haven't won one" |
   | the tune-up | 📅 (was there) |
   | the dog read: "the ratings back this side" | 🧭 THE SCHEDULE IT STANDS ON - below |
   | the dog read: "the favorite lost its last" | 📅 / 🥊 their last game with the score (was there) |

2. **🧭 The schedule, said as the schedule** (`sched_lines`). What an opponent-adjusted rating sees and a record
   doesn't - D1 games only, every team named, a count never a rate:
   - **who they beat**: "The D1 teams UC San Diego beat this year (Fresno St and Texas Southern) won 3 of 11 against
     D1 teams between them." (4 teams at most, those teams at 40% or less - `SOFT_WINS`);
   - **who beat us**: "The teams that beat Northern Iowa this year (Furman and Michigan St) won 7 of 7 against D1 teams
     between them." (every one a winning team, 60%+ together - `TOUGH_LOSSES`; it replaces the ⚖️ line);
   - **the night they were a big favorite and it was a game**: "UC San Diego went off as an 18.5-point favorite against
     Texas Southern this year and won by 5." (favored by 7+, 10+ points short of it and at least 0.6 of it, last 4 games).
   When the leg carries "the ratings back this side" the first two are reason-backed: they open the body and take the
   line under the pick. Never "our ratings say".

3. **The schedule guard never leaves a card empty** (`fair_trim`). When their schedule ran 50+ rating points tougher,
   the comparison leaves THEIR toughest games out - 2 at most, 3 left - until the schedules are level, and the line
   says it: "🧲 San José St plus 3 rebounds a game against D1 teams, UC San Diego minus 2. (not counting the Utah State
   game)". Leaving their worst nights out only makes their numbers better, so a gap that is still there is real. A
   schedule that can't be made level still gets no comparison (Washington: three D1 games against nobody) - the Oakland
   rule stands.

4. **Two lines about the same stat are one fact**: the first half and the second half for the same team (the better
   one is said - at the pool, `sports_breakdown_v24.one_half`, and in the same-stat cut, `stat_of` "half"); the same
   record twice (🔥 "4-0 overall" + 📋 "sits 4-0"). On cards written by VERSION 86+ (`HALF_BV`) - a started card from
   before keeps its lines rather than get shorter on the page.

5. **The line under the pick is the biggest reason**: a reason line now takes it from a streak, the records and their
   last loss too (`REASON_OVER`); a named absence, a back-to-back, a goalie, a quarterback still lead. A 🧭 line is
   never cut to half a sentence - a short wording goes under the pick ("The four D1 teams Seattle U beat this year won
   6 of 21 against D1 teams between them").

6. **Every new number is re-derived on every render** (`sports_card_check.sched_numbers` ->
   `sports_card_sell.sched_wrong`): the teams named are the teams the game files hold, the count is theirs (it may
   trail the files by a game a team since the card was written - never lead them), a trimmed line is checked with the
   named games left out, a 🪑 line against the leg. A wrong one is cut and the spares refill.

7. **One more box line**: 🎁 "East Carolina put teams on the line 28 times a game against D1 teams. Indiana St gets
   there 23 times a night." (they foul 25+ a game and we get there 20+).

8. **A page bug**: "won 3 of their last 5 games by 10 or more" counts the BIG wins; the record check no longer reads it
   as the last-5 record.

Switches: `sports_card_sell.TRIM`, `SCHED_FACTS`, `REASONS_1123` (all three off = the VERSION 85 card).

## 3. The counts

`python results/studies/cards_1123/dry.py posted ncaab` / `posted` / `cand 2026-11-23 2026-11-24 2026-11-25`. A
"reason line" = a line that says a reason the leg carries (`sports_card_sell.reason_backed` == "reason"); "says why" =
that or a matchup line. A repeat is counted by today's rule in every row.

| what | cards | fact lines a card | cards under 6 | cards with no reason line | cards with no line that says why | same-stat repeats | line under the pick says why |
|---|---|---|---|---|---|---|---|
| college hoops unit cards posted 11/12-11/23, as they posted | 13 | 5.3 | 8 | 4 | 3 | 10 | 6 |
| the same, re-written by VERSION 85's writer, on the page | 13 | 5.5 | 7 | 4 | 3 | 4 | 5 |
| the same, re-written now, on the page | 13 | 6.5 | 3 | 0 | 0 | 0 | 13 |
| every league's unit cards posted 11/12-11/23, as they posted | 33 | 6.8 | 11 | 10 | 6 | 11 | 13 |
| the same, VERSION 85's writer | 33 | 6.7 | 8 | 11 | 3 | 4 | 17 |
| the same, now | 33 | 7.1 | 4 | 8 | 1 | 0 | 25 |
| 11/23 college hoops candidates, before | 16 | 5.8 | 6 | 8 | 2 | 4 | 14 |
| 11/23 college hoops candidates, now | 16 | 6.6 | 3 | 6 | 0 | 0 | 16 |
| 11/24 college hoops candidates, before | 13 | 7.5 | 1 | 5 | 3 | 4 | 8 |
| 11/24 college hoops candidates, now | 13 | 7.8 | 0 | 2 | 0 | 0 | 13 |
| 11/25 college hoops candidates | 0 | | | | | | |
| all three days, NBA / NHL / NFL / college football candidates (24), before and now | 24 | unchanged | 2 | 14 | 0 | 0 | 13 |

Honest about these numbers:

- **Three college hoops cards are still under 6** - Indiana St vs East Carolina (5), Niagara (4), UT Rio Grande (4).
  Indiana St's box numbers are worse than East Carolina's in every column but fouls; Delaware St and Austin Peay have
  2-3 D1 games on file. The files hold no more for those sides and the card never pads.
- **The candidates are every side on the slate, not picks** - a side the engine has no reason on has no reason line
  (8 of the 29). On the 13 cards that actually posted, every one now has a reason line.
- **No games with a price on 11/25 are on file yet**, so that day has no candidates.
- The other leagues did not move (four cards changed a wording); this pass was the college hoops pools. The NBA / NHL
  cards with no reason line carry reasons that have none by rule ("sharp money moving this way" - the 10/23 rule) or
  small dog-score weights (pace, the size of the slate) - cards_1122 section 5.4.
- No network in this session: the re-writes use the injury lists each posted card stored.

## 4. The three cards

### San José St +105 vs UC San Diego (1u) - 3 lines -> 7

Posted:

```
WHY: 🥊 San José St the side: UC San Diego got handled 90-64 by Seattle U last time out. Tap in.
  📊 Scoreboard lately - San José St: 78 scored, 75 allowed a game (last 3). UC San Diego: 81 and 101.
  💯 San José St's top scorer Mekhi Mason is putting up 18 a night lately (5 games).
  ✅ Bottom line: San José St (+105). Tap in.
```

Now, on the page:

```
WHY: 🧭 Give me San José St: The D1 teams UC San Diego beat this year (Fresno St and Texas Southern) won 3 of 11 against D1 teams between them.
  🧲 The glass is ours: San José St plus 3 rebounds a game against D1 teams, UC San Diego minus 2. (not counting the Utah State game)
  🧭 UC San Diego went off as an 18.5-point favorite against Texas Southern this year and won by 5.
  📊 Against D1 teams UC San Diego gives up 92 points a game and scores 81.
  📊 81 a game for San José St this year, 78 against. They outscore people.
  💯 San José St's top scorer Mekhi Mason is putting up 18 a night lately (5 games).
  📅 UC San Diego off a 90-64 loss to Seattle U last time out.
  ✅ Bottom line: San José St (+105). Get in.
```

### Indiana St +124 vs East Carolina (1u) - 4 lines, one of them a repeat -> 5, no repeat (graded: won 77-76; the posted card stays as it was)

Posted:

```
WHY: 🥊 We on Indiana St: East Carolina is coming off an 85-69 beating from S Illinois. East Carolina been trash as fuck.
  ⏱️ The second half, last 5 games: 197 points for Indiana St, 181 against.
  🏁 Indiana St outscored teams 189 to 159 in the first half over their last 5 games. They come out ready.
  💯 Karmani Gregory is giving Indiana St 14 a night over the last 4 games he's played.
  ✅ Bottom line: Indiana St (+124).
```

Now, on the page:

```
WHY: 🧭 Riding Indiana St: The D1 teams East Carolina beat this year (SC Upstate, NC A&T and Delaware St) won 1 of 13 against D1 teams between them.
  🎁 East Carolina foul: 28 free throws a game for the other team against D1 teams. Indiana St shoot 23 a night.
  📅 East Carolina off an 85-69 loss to S Illinois last time out.
  🏁 The first half, last 5 games: 189 points for Indiana St, 159 against.
  💯 Karmani Gregory been cooking for Indiana St - 14 a night over his last 4.
  ✅ Bottom line: Indiana St (+124). Riding Indiana St.
```

### Washington +11.5 vs BYU (½u) - 8 lines, none the reason -> 7, the reason leads

Posted:

```
WHY: 🧹 Washington ain't squeaking by: 4 straight wins by 10+. We on Washington.
  🔥 Washington hasn't lost in 4 - 4-0 overall.
  📊 Washington put up 83 a game over their last 3 and gave up 70.
  🏁 The first half, last 4 games: 188 points for Washington, 133 against.
  📋 Washington sits 4-0; their last one was a 82-69 win over Utah Tech.
  ⏱️ Washington put up 157 points in the second half over their last 4 and gave up 135.
  💣 Washington scored 80 or more in 3 of their last 4 games.
  💯 Steele Venters been cooking for Washington - 17 a night over his last 4.
  ✅ Bottom line: Washington +11.5 at -112. That's the bet.
```

Now, on the page:

```
WHY: 🪑 Riding Washington: BYU's top scorer Robert Wright III (23.8 a game) sat out their last game.
  👌 BYU been living on the three: 64 for 151 against D1 teams, 42%.
  🔥 Washington hasn't lost in 4 - 4-0 overall.
  🧹 Washington ain't squeaking by: 4 straight wins by 10+.
  📊 Washington put up 83 a game over their last 3 and gave up 70.
  🏁 The first half, last 4 games: 188 points for Washington, 133 against.
  💣 Washington scored 80 or more in 3 of their last 4 games.
  ✅ Bottom line: Washington +11.5 at -112. That's the bet.
```

Every other card, before / after: `dry_posted_ncaab.md` (the 13 posted) and `dry_cand.md` (the candidates).

## 5. The owner should know

1. **The Washington card is still thin on the matchup.** Its two reasons are on it now. Everything else is Washington
   beating Colgate, Miss Valley St and Utah Tech - there is no honest comparison against a BYU team that played Ohio
   State. The stack play is a ½u bet on two study weights and the card says those two things.
2. **"Sat out their last game" is what the files know.** The box scores say Robert Wright III didn't play BYU's last
   game; they don't say he's out tonight, and the card doesn't claim it.
3. **The "who they beat" line is a count on a small sample** - "won 3 of 11" in November. It is a fact, and it is the
   honest way to say what the ratings see; it is not a study finding.
4. **The schedule guard's trim is one constant** (`TRIM_MAX` 2 games, 3 left). `SCHED_EDGE` 50 stays.
5. Only OPEN cards are re-written (the Indiana St card is graded - it stays as it posted).

## 6. Tests

`test_cards_1123_the_*` (four), off the real games and team boxes going into 11/23: the San José St card (6+ facts,
the schedule line leads and is reason-backed, the trimmed glass line, every number re-derived and a wrong one cut, the
switches); the Indiana St card (who they beat, the fouls, one half - the better one, a started card from before keeps
its lines, the record once); the Washington card (the man who sat off the reason text, BYU's threes as counts, no box
comparison that can't be made fair, the hot-ATS count and the road line, the reason takes the line under the pick but
never from a back-to-back / an absence / a goalie / a quarterback); the standing rules (VERSION 86, the count of big
wins, the trim's limits). `timeout 900 python sports_test.py`: 824 tests ok, exit 0, no "FAILED:" line.
