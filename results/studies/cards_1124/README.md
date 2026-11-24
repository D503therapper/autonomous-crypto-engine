# 11/24 - THE CASE BUILDER (the seventh card pass - and why it is a different kind of fix)

The owner, 11/24: **"I don't know how many times I gotta tell you that Fable needs to permanently fix this. These
breakdowns have been so fucking bad and been a fucking issue."** His friend Victor on the ⭐ Illinois St +100 (2u) card:
"Ur algo had terrible breakdown on the game lol" / "he said Illinois state good becuz it lost to st Mary's and Santa Clara
who are average teams lol" / "Tulsa a low scoring defensive team tho, Illinois just shoots hella 3's" / "by the reasoning
of the algo, he should have liked Tulsa".

**No pick, price or unit size changed.** Wording only (`sports_breakdown.VERSION` 88 rewrites the open cards) - plus one
grading bug found on the way (section 5), which keeps a pick on its TEAM.

**The owner declined the paid API writer (11/24: "No, we're not doing the $10 a month, whatever crap").** A first draft
of this pass had Claude write each card from a verified fact sheet through the Anthropic API (about $10-20 a month). It
was dropped the same day and nothing of it is in the repo: no key, no workflow change, no module. **Do not re-propose
it.** The permanent fix is in the template writer, below.

## 1. The diagnosis

Six passes (cards_1117, 1118, 1119, 1119b, 1122, 1123) each fixed symptoms: a pool picks facts ONE AT A TIME and can't
build an argument. The 11/23 pass made it worse on this card - when no box-score line cleared a bar it reached for a
schedule line, and the 11/24 morning board check added "the close ones": *"Illinois St finished within 3 of Santa Clara
and within 5 of Saint Mary's ... Those two won 11 of 13"*. Two losses, sold as the reason for a 2-unit bet.

## 2. The fix

1. **No moral victories, ever** (`sports_card_sell.CLOSE` / `LOSS_LINES` False, `MORAL`, `lost_to`;
   `sports_card_check.moral_victory`, `Q_MORAL`). A close loss is a loss. The "finished within N of" line is off for
   good; so is its long form, "the teams that beat us are winning teams" (the 11/23 🧭 who-beat-us line). A card already
   posted with one loses it on every render - the body and the line under the pick - and the catch is logged. Who THEY
   beat ("the one D1 team Coastal beat is SC Upstate, who won 0 of 6") stays: that is about the opponent.
2. **The case builder** (`sports_card_sell.case_edges`, switch `CASE`; basketball - college and the NBA). The case is
   the MATCHUP: what our side does well against what their side does badly **on the same thing**:

   | the edge | our half | their half |
   |---|---|---|
   | shooting | our field-goal % | the field-goal % they allow |
   | defense | the field-goal % we allow | their field-goal % |
   | threes | our three-point % (with the makes a game) | the three-point % they allow |
   | the arc | the three-point % we allow | their three-point % |
   | turnovers | the turnovers we force a game | the turnovers they commit |
   | the glass | our rebound margin | theirs |
   | the line | our free throws a game | the free throws they give up |
   | the paint | our points in the paint | the paint points they give up |
   | the break | our fast-break points | the fast-break points they give up |

   Each half is measured the same way - how far the number sits on the right side of an ordinary team's, in that
   stat's own spread (`CASE_BASE`: college 44% from the field ± 3, 33.5% from three ± 3.5, 12.5 turnovers ± 2, ...) -
   so the edges can be **ranked**. An edge needs BOTH halves real (`CASE_HALF` 0.25 each) and a real size together
   (`CASE_MIN` 1.25). The biggest leads the card, the next three back it up (`CASE_MAX` 4), **each line both teams'
   numbers in one sentence**. A ranked edge takes the place of the pool's one-sided line on the same stat. When the
   leg carries the dog read ("the ratings back this side") the edges ARE the reason and take the line under the pick;
   on any other card they open the body and lead only when nothing stronger does (a named absence, the game these two
   already played).
3. **A strength that meets a strength is no edge.** Illinois St shoot 51% from the field against D1 teams; Tulsa hold
   D1 teams to 41%. The old pools would say the 51%. The case builder says nothing - and the card is shorter.
4. **No edge = fewer lines, never filler.** Nothing pads a card that has no matchup edge.
5. **The schedule guard covers the fill lines too.** When THEIR schedule ran clearly tougher (`SCHED_EDGE`, 50 rating
   points) the card never sets the two teams' season scoring side by side ("we score 80, they score 74") - the sell
   lines already kept quiet; the refill's `fill_o` / `fill_d` lines now do too (`sports_breakdown_v24.fill_facts`).
   College hoops reads D1 games only, as before; a schedule that can be made level by leaving their two toughest games
   out still is, and says so (`fair_trim`).
6. **Who beat us never takes the line under the pick** (`sports_breakdown_v24.NO_LEAD`).

## 3. Illinois St +100 vs Tulsa - before and after

As it posted (11/24, 8 AM):

```
🧭 Illinois St finished within 3 of Santa Clara and within 5 of Saint Mary's this year. Those two won 11 of 13 against D1 teams between them.
  📊 Illinois St scores 80 points a game against D1 teams; Tulsa scores 74.
  📅 Tulsa is fresh off a 69-66 loss to Oregon St.
  💣 80+ points for Illinois St in 3 of their last 5. They can score.
  💯 Malik Messina-Moore been cooking for Illinois St - 17 a night over his last 5.
  ✅ Bottom line: Illinois St (+100). Tap in.
```

Now:

```
📊 Illinois St scores 80 points a game against D1 teams; Tulsa scores 74. Illinois St the side.
  💯 Malik Messina-Moore been cooking for Illinois St - 17 a night over his last 5.
  📅 Last time out Tulsa took a 69-66 loss to Oregon St.
  💣 80+ points for Illinois St in 3 of their last 5. They can score.
  ✅ Bottom line: Illinois St (+100). Trust the algorithm.
```

**It is short, and that is the honest card.** Every matchup category for this game (`python
results/studies/cards_1124/halves.py 2026-11-24`, D1 games only, 5 a side):

| the edge | Illinois St | Tulsa | an edge? |
|---|---|---|---|
| shooting | shoot 51% | hold teams to 41% | no - their strength |
| threes | 9 a game at 32% (half their shots are threes) | allow 32% | no - they guard the arc, and we don't shoot it well |
| the arc | allow 39% | hit 29% | no - ours is the weakness |
| turnovers | force 11 | commit 15 | no - we don't take it away |
| the glass | -3 a game | +6 a game | no - theirs |
| the line | 20 a game | give up 20 | no |
| the paint | 32 a game | give up 30 | no |
| defense | allow 48% | shoot 43% | no - ours is the weakness |

Victor was right about the styles ("Tulsa a low scoring defensive team, Illinois just shoots hella 3's": 74 a game and
41% allowed; half of Illinois St's shots are threes) and the box scores hold **no two-sided edge for Illinois St**. The
card can't invent one. What it can say is true and for us: they score 80 a game against D1 teams, Tulsa lost its last
game, their scorer's hot. The cards that do hold an edge now lead with it - the same day's rewrite of the week:

```
🧤 Niagara force 13 turnovers a game against D1 teams. Delaware St already give it away 17 times a night. Riding Niagara.
🎨 William & Mary score 43 a game in the paint against D1 teams and Youngstown St gives up 38 in the paint.
   🪣 Youngstown St let teams hit 47% of their shots against D1 teams. William & Mary shoot 49%. Buckets.
   🎁 Youngstown St put teams on the line 30 times a game against D1 teams. William & Mary gets to the line 25 times a night.
🪣 San José St shoot 50% from the field against D1 teams and UC San Diego let teams shoot 47%. Give me San José St.
   🧲 San José St out-rebound teams by 3 a game against D1 teams and UC San Diego gets out-rebounded by 2.
🎁 Trail Blazers get to the line 28 times a game this year and 76ers put teams on the line 24 times a night. Give me Trail Blazers.
   🧲 The glass is ours: Trail Blazers plus 3 rebounds a game this year, 76ers minus 2.
```

## 4. The counts

`python results/studies/cards_1124/dry.py` -> `dry.md` (every unit card posted 11/17-11/24, as posted and re-written now
as the page shows it, with its ranked edges):

| what | count |
|---|---|
| unit cards | 27 |
| with a "finished within" moral-victory line, as posted / now | 1 / 0 |
| basketball cards the case builder could read | 16 |
| ... with at least one ranked matchup edge | 7 |
| ... with none (the card stays as short as its facts) | 9 |
| of the 7, the line under the pick is the matchup edge | 5 (the other two lead with a named absence / the game they already won) |
| fact lines a card, now | 7.0 |

Honest about it: 9 of 16 basketball cards hold no two-sided edge. Those picks came from the price, a study weight or
who's out - the card says those facts and no made-up matchup. Hockey and football cards are untouched by the case
builder (their matchup lines are the 11/22 ones); the moral-victory cut covers every league.

## 5. Victor's real question - a fact check of the ENGINE

*"Tulsa ... has way better strength of schedule ... by the reasoning of the algo, he should have liked Tulsa ... it
liked Illinois who are 3-4."*

`python results/studies/cards_1124/engine_check.py` (`engine_check_out.txt`):

- **Yes, the college efficiency read is schedule-adjusted** (`sports_cbb_eff`): points per 100 possessions solved
  against every opponent's own offense and defense, the floor (home / road / neutral), with three-point and
  free-throw luck partly taken out, last season as the starting point. Nothing to fix there, so no replay was run.
- **It did not have Illinois St as the better team. It had a coin flip.** Illinois St 101st of 378, Tulsa 102nd -
  0.2 points apart on a neutral floor, a 50.6% read against a price that needed 50%.
- **Illinois St's schedule was the tougher one in our files, not Tulsa's.** Illinois St: at Saint Mary's (54th), at
  Purdue (28th), at N Dakota St, Bellarmine, Santa Clara (95th) - average opponent 23.4. Tulsa: N Illinois, Oral
  Roberts and Western KY at home, Mississippi St (44th) and Oregon St (98th) on a neutral floor - average 21.4. The
  card's Elo guard says the same (1632 against 1545).
- **Half of each rating is still last season.** After 5 D1 games the preseason prior counts as 6 games. Illinois St's
  number was 23.6 from last year and 24.6 now; Tulsa's 24.0 and 24.4.
- **Against D1 teams Illinois St were 1-4, not 3-4** - two of the three wins were over non-D1 schools.
- **Why it posted:** the dog read was 4.0, exactly the gate - 2 points because the adjusted numbers have the dog at
  least level, 2 points because the favorite lost its last game (a studied spot). No matchup edge was part of it.
- **Why it was 2 units:** the ⭐ rule, not the read. A dog read of 4 is a 1-unit play in the dog slot (the leg's own 2u bar was a read of 5); the ⭐ stamp
  (`best_2u`) made it 2u. **That is the owner's open decision** (sizing is his call): should a ⭐ on a college hoops dog
  read under 6 stay at its own 1u? Nothing changed here.

So Victor's instinct about the card was right and his instinct about the schedule was not: the engine did not pick
Illinois St off a moral victory - it priced a coin flip at even money and a studied spot tipped it. The CARD then
explained a thin pick with a bad argument.

## 6. A grading bug found on the way - 🔀 the pick is the team

The Illinois St leg said side "home" with team id 2287. After it posted, ESPN re-listed the neutral-floor game with
**Tulsa as the home team**. Everything that reads `g[leg["side"]]` then read Tulsa: the card check, a rewrite - and the
**grade**: an Illinois St win would have graded a loss on the ⭐ 2u play (`sports.grade_leg`). It was the only such leg
in the file (checked every posted leg). `sports.sync_sides` now runs before every grade (the board's and the early
plays') and before a card is written again: when the game file holds our team on the other side, the leg's side
follows the team (team id first, the two names when a play keeps no id); totals, graded legs and a game where neither
side is ours are left alone, and it says what it did in the run log. The pick, the price and the units never move.

## 7. Files

`sports_card_sell.py` (case_edges, CASE_*, MORAL / moral / lost_to, CLOSE and LOSS_LINES off), `sports_card_check.py`
(moral_victory, Q_MORAL), `sports_breakdown_v24.py` (NO_LEAD, the fill-line schedule guard), `sports_breakdown.py`
(VERSION 88), `sports.py` / `sports_early.py` (sync_sides). Tests: `test_cards_1124_*` (four) +
`test_the_pick_is_the_team_when_the_game_file_flips_home_and_away`; the two 11/23 card tests and the 11/24 board-check
test updated to the new rules. Here: `dry.py` / `dry.md`, `halves.py`, `engine_check.py` / `engine_check_out.txt`,
`fixture.py`.
