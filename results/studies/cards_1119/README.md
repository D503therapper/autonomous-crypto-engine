# 11/19 - THE STORY OF THE GAME: a card says why THIS team wins THIS game

The owner, 11/19, on the Flyers +150 2u card: "I still don't like the breakdown for the flyers. It's like, oh, this guy's
in gold and this guy's in gold. Don't tell us shit. It's like, oh, we price flyers at this. Don't tell us shit. Like, the
breakdowns are just trash." / "run Fable and fucking permanently fix these fucking breakdowns." The same day, on the Ducks
card's "-166 on our sheet": "we can't say that we're better at pricing the lines than the fucking line makers." And:
"That's just facts sounds retarded."

The 11/17 sweep made every line true. The 11/18 sweep made every line argue for our side and filled short cards. Both
left the real hole: the refill reached for a scorer's points and the price said two more ways, so a card could be all
true, all "for us", six lines long - and say nothing about the matchup. This pass is about WHAT a card says.

**No pick, price or unit size changed.** Wording only; `sports_breakdown.VERSION` 74 rewrites the open cards.

## 1. What was wrong

The Flyers card, line by line:

| the line | what it is |
|---|---|
| 💯 Matvei Michkov been producing for Flyers: 9 points over the last 10. Flyers the side. | a scorer's points as the reason for the bet |
| 💵 Plus money: at +150, Flyers winning about 4 times in 10 is all we need. | the price, as arithmetic |
| ✅ Flyers are at full strength. | nobody out on either side - says nothing about the game |
| 💯 Jamie Drysdale has 9 points in his last 10 games for Flyers. | a second scorer |
| 💵 We price Flyers at +123. The book's paying +150. | the price again - and our number against the line makers' |
| 📅 Flyers come off a 4-3 win over the Sabres. | a fact (a one-goal win) |
| 🗓️ Flyers are 3-2 over their last 5. | a record up by one |
| ✅ Bottom line: Flyers (+150). Our read beats this price. Ride it. | our read against the book's again |

One real fact in eight lines. Meanwhile the game files held the story of this game and the card said none of it: the
Flyers beat the Senators 3-1 on 10/17; 7 of the Senators' 14 wins came by one goal; the Senators got run 7-2 (Blues) and
6-2 (Sharks) in their own building; the Flyers won 2 of their last 3 on the road (3-1 at the Canucks, 4-3 at the Blue
Jackets) and outshot teams 270 to 241 over their last 10 - which is the engine's actual reason (the puck luck) in plain
counts. The head-to-head line was even written - and dropped by the 10/5 guard rule every time.

(Checked against `data/sports/games/nhl`: the two meetings were Senators 2-1 in Ottawa on 10/8 and Flyers 3-1 in
Philadelphia on 10/17 - so the card says "a 3-1 win at home", never "in Ottawa".)

## 2. The count

Every line classed: (a) a fact that argues our side, (b) filler - price math, a second scorer line, a weak line under
the pick, "full strength" alone, a record up by one, a repeat, jargon, a man out who doesn't matter - (c) bad for us,
(d) praise for the other side, (e) false / stale by the fact check. "Before" = the 11/18 writer (the switches off) on
the same legs; "after" = this code; "page" = after the page's check. The slates are every moneyline side the engine
prices from -150 to +350 at 8 AM - candidates, not picks.

| what | cards | lines written | good | filler | bad for us | praise for them | false / stale | filler on the page | fact lines a card (page) | under 6 | under 4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| the unit cards posted 11/5-11/19, **as written at the time** | 40 | 402 | 262 | **96** | **32** | **9** | **3** | - | - | - | - |
| the same 40, re-written by the 11/18 writer | 40 | 390 | 323 | 67 | 0 | 0 | 0 | 0 | 5.7 | 10 | 4 |
| the same 40, **re-written now** | 40 | 383 | 379 | **4** | 0 | 0 | 0 | **0** | **6.4** | **6** | **2** |
| 11/19 slate (hockey 19, college hoops 28, NBA 3, college football 2), before | 52 | 441 | 342 | 98 | 1 | 0 | 0 | 0 | 4.9 | 18 | 14 |
| 11/19 slate, now | 52 | 409 | 408 | 1 | 0 | 0 | 0 | 0 | 5.6 | 17 | 13 |
| 11/20 slate (NBA 4, college football 3), before | 7 | 67 | 55 | 12 | 0 | 0 | 0 | 0 | 6.1 | 0 | 0 |
| 11/20 slate, now | 7 | 67 | 65 | 2 | 0 | 0 | 0 | 0 | 6.9 | 0 | 0 |
| 11/21 slate (college football Saturday), before | 44 | 358 | 254 | 103 | 1 | 0 | 0 | 0 | 4.8 | 17 | 12 |
| 11/21 slate, now | 44 | 335 | 333 | 1 | 1 | 0 | 0 | 0 | 5.5 | 15 | 7 |
| 11/22 slate (NFL), before | 8 | 68 | 50 | 18 | 0 | 0 | 0 | 0 | 5.5 | 3 | 0 |
| 11/22 slate, now | 8 | 62 | 62 | 0 | 0 | 0 | 0 | 0 | 5.6 | 3 | 0 |

(The "before" rows on the page column read 0 because today's check already cuts the filler the old writer wrote - which
is why those cards came out thin: 4.8-4.9 fact lines a card on the two big slates. The one "bad for us" on 11/21 is the
counter misreading "looks lost out there" - said of the OTHER team's quarterback - as our loss; the line is fine.)

On the 40 unit cards posted 11/5-11/19 as they were written at the time: 402 lines - 262 good, 96 filler, 32 bad for
us, 9 praise for the other side, 3 false / stale. Re-written now: 4 filler lines written, 0 on the page.

What still writes a filler line (4 on the posted replay, 4 across the four slates): a one-liner from `why_line` that is a
close last result on a game dated before 11/19 (the close-win rule is date-gated at `CLOSE_WIN_FROM`), and a 🔁 line
whose score another line already carried. The page cuts all of them.

Honest about length: taking the padding out makes some cards shorter. The posted cards went UP (5.7 -> 6.4 fact lines a
card, 10 -> 6 under the floor) because the matchup pool found more than the padding it replaced. The college hoops
candidates in their first 4-5 games stay thin (13 of 52 on today's slate under 4 lines, 14 before): a team we don't
hold every game for gets no record / streak / last-game line (never false information), and there is no season yet to
count one-score wins or a head to head in. Those cards say fewer lines instead of price math.

## 3. What changed - at the root

`sports_breakdown_v24.py`:

- **`matchup_facts`** (new, switch `STORY`) - runs first in `more_facts`, so its lines are first-hand body lines that
  can lead the card. Each is a real game with its score or a count off the season's game files, said only when it
  argues for us:

  | the fact | when | a real line |
  |---|---|---|
  | 🆚 these two already met this year | we won the last meeting | "Flyers already beat the Senators this year - a 3-1 win at home on 10/17." |
  | 🎬 how THEY have been winning | 4+ wins, 3+ and half or more by one goal / one score / 5 points | "7 of the Senators' 14 wins this year came by one goal - the last two 4-3 over the Avalanche and 2-1 over the Jets. They been squeaking by." |
  | 🥊 where THEY got run | 2+ beatdown losses at tonight's kind of site (never vs a team rated above us in college) | "The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks." |
  | 🧳 / 🏟️ what WE did there lately | 2+ wins in our last 3 at tonight's kind of site, when the season record there isn't already a winning one | "Flyers won 2 of their last 3 on the road - a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets." |
  | 🔁 a common opponent | inside 45 days we beat them and they lost to them | "They both saw the Senators lately: Ducks got a 6-3 win on 11/1, Avalanche took a 4-3 loss on 11/12." |
  | 🏹 hockey: the puck-luck reason as shots | the luck has run against us and we outshot teams by 15+ over the last 10 | "Flyers outshot teams 270 to 241 over their last 10 games." |

- **Price math is out of the pools**: `fill_price` ("We price X at +123"), `fill_need` ("4 times in 10 is all we need").
- **One scorer line a card** (`STAR_ONE`), ranked LAST in the refill - football's back and catcher included.
- **"At full strength" alone is no line**; **a record up by one is no line** (the last 5 needs 4+).
- **`lead_line` / `LEAD_RANK`**: the line under the pick, when no reason maps to a fact, is the strongest matchup fact -
  their tired legs, their men out, the game these two played, where they got run, then form, then the scoreboard. Never
  the price, never a close last result, never a record up by one; a scorer's points only when the card holds no
  team-level fact at all.
- **`story_close`** - the end of every write-up: no line and no one-liner with a price claim; the bottom line is the
  pick and its price + the matchup reason read off the one-liner (`BOTTOM_WHY`: "Already beat 'em once this year.",
  "Avalanche is short-handed.") + the size words or a short closer; past 9 fact lines (`CARD_MAX`) the weakest ride
  along as spares.
- **`NO_OUR_NUMBER`**: `OWNER_LOCK` / `OWNER_PLAY` / the same-number closer / the lean one-liner no longer print our
  number; `sports_dashboard._units_line` says the size, never "We make 'em X, the book's at Y";
  `sports_breakdown.lean_ends` the same; the early rows' read sentence (`sports_early.EXAM_READS`, `NO_PCT_READS`,
  `NBA_OPEN_READS`, the spot reads) says the pick and the price it was taken at; the altitude card no longer says "the
  books only price in about 1.5 of it"; the question box's "why it's not the Lock" says the edge is thin.
- **"that's just facts"**: off `sports_owner_lingo.OWNER`, on `NEVER`, out of every pool (the write-ups, the max-play
  lines, tennis).

## 4. The standing check - so it can't creep back

- `sports_owner_lingo.PRICE_CLAIM` - the one list of ways a line claims our price or says the book has it wrong.
- `sports_card_guard.scrub` - takes the claim SENTENCE out and keeps the fact beside it ("🧠 +280 undersells Utah State
  on our read. Utah State had last week off; Oregon St played." -> "🧠 Utah State had last week off; Oregon St
  played."); a bottom line keeps its pick and price. `no_facts_tail` takes "that's just facts" off an older card and
  keeps its fact.
- `sports_card_check` - on EVERY render (the page, the brain, the audit, the pre-post check), each catch in the run log
  and `pick_audit.json`:
  - `Q_FILLER` - price math in the body, "full strength" alone, a record up by one;
  - `Q_STAR2` - a second scorer line;
  - `Q_PRICE` - a price claim (body, bottom line, one-liner, early rows);
  - `Q_LEAD` (`weak_lead`) - a one-liner that is the price / a close last result / a record up by one, or a scorer's
    points while the card holds a matchup fact: it falls, and the page's fallback takes the strongest line (`lead_rank`).
  - the fact check reads a matchup line's scores against the whole season, not the last 6 games.
- `tools/card_audit.py` counts all four as the quality kind "filler" - a bad line the write-up puts on a card costs
  score and is a QUALITY PROBLEM on the hourly check, like the 11/18 kinds.

## 5. Judgment calls - the owner should know

1. **Head to head is back, in one form only.** The 10/5 rule dropped every 🆚 line ("they own this matchup" made picks
   sound stronger - the head-to-head study was dead). That still never posts. What posts now is a game these two
   played THIS season, with its score and its day, and only when we won the last one - a fact of the matchup, not a
   history claim (`sports_card_guard.THIS_YEAR_GAME`). His 10/25 thorough-card rule lists head to head; the 11/18
   write-up had kept it off. If he wants it off again: `matchup_facts` section 1.
2. **The over cards keep their scoring line** ("Lakers should score about 116 ... - 223 with everybody, the number's
   221.5"). It is points against the total, added 11/14 after he asked why "neither team averages what that over is" -
   not a price of ours against the book's. The two lines that DID say the book has it wrong are gone. His call if the
   scoring line should go too.
3. **A card with no team-level fact and no scorer has no line under the pick** rather than a close result or a 3-2.
4. The question box (the JS on the page) was read for "our number" talk - none found; it says "the books got this one
   priced about right", which is the opposite claim.

## 5b. Tests

`sports_test.py`: `test_cards_1119_the_story_of_the_game_the_flyers_card` (the Flyers' and Senators' real results as a
fixture: the 🆚 / 🎬 / 🥊 / 🧳 lines with their scores, no 💵, no scorer lead, the guard still drops "own this matchup"),
`test_cards_1119_the_page_cuts_filler_and_a_matchup_fact_leads` (the posted card through the page's check),
`test_cards_1119_no_card_says_our_price_against_the_line_makers` (16 real wordings, every pool, the bottom line, the
early rows), `test_cards_1119_thats_just_facts_is_a_never_word`. The older tests that pinned the old wording (our number
on the bottom line / the units line, the 💵 refill, "that's just facts", the healthy line) were updated to the new rule.

## 6. Before -> after, card by card

"AS POSTED" is the card as it was written at the time; "NOW" is the same pick re-written by this code off the files in the repo and put through the page's check (no network in this box: who's out is what the leg held when it posted; the NBA bench / star lines need the live roster read and are not in these replays). The pick, price and units never change.

### 2026-11-19 nhl - Flyers +150 vs Senators (play, u)

AS POSTED:

    💯 Matvei Michkov been producing for Flyers: 9 points over the last 10. Flyers the side.
    💵 Plus money: at +150, Flyers winning about 4 times in 10 is all we need.
    ✅ Flyers are at full strength.
    💯 Jamie Drysdale has 9 points in his last 10 games for Flyers.
    💵 We price Flyers at +123. The book's paying +150.
    📅 Flyers come off a 4-3 win over the Sabres.
    🗓️ Flyers are 3-2 over their last 5.
    ✅ Bottom line: Flyers (+150). Our read beats this price. Ride it.

NOW:

    🆚 The last time these two met this year Flyers got a 3-1 win at home, on 10/17. Flyers the side.
    🥊 The Senators got run in their own building twice already this year - 7-2 by the Blues and 6-2 by the Sharks.
    🎬 7 of 14 wins by one goal for the Senators this year (the last two: 4-3 over the Avalanche and 2-1 over the Jets). That's a team living on the edge.
    🏹 Flyers outshot teams 270 to 241 over their last 10 games. They been carrying the play - keep that up and the wins come.
    🧳 Last 3 on the road for Flyers: 2 wins, a 3-1 win at the Canucks and a 4-3 win at the Blue Jackets.
    💯 Matvei Michkov been producing for Flyers: 9 points over the last 10.
    📅 Fresh off a 4-3 win over the Sabres for Flyers.
    ✅ Bottom line: Flyers (+150). Already beat 'em once this year. Put the homies on Flyers.

### 2026-11-19 nhl - Ducks +110 vs Avalanche (dog, u)

AS POSTED:

    🚑 The Avalanche gotta play without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night. Fuck it, Ducks.
    🥅 Scott Wedgewood — the Avalanche's projected starter, nobody's confirmed yet — has been giving up a lot of goals: a 0.871 save % (13 goals on 101 shots) over his last 3 starts.
    🧳 Road game, no problem: Ducks are 7-4 away from home this season.
    💯 Cutter Gauthier has 22 points in Ducks' last 10 games.
    🥅 Mackenzie Blackwood played last night for Avalanche; Scott Wedgewood (projected, not confirmed) is the next man up.
    📉 Avalanche lose Nathan MacKinnon - 30 points in his 20 games this year.
    🥊 4-1. That's what the Mammoth did to the Avalanche inside their last 5.
    😴 Second night of a back-to-back for Avalanche. Ducks are rested.
    ✅ Bottom line: Ducks (+110). Our read beats this price. Get in.

NOW:

    🚑 The Avalanche is without Cale Makar and Nathan MacKinnon, two of their three best players, and they played last night.
    😴 Second night of a back-to-back for Avalanche. Ducks are rested.
    📉 Avalanche loses Nathan MacKinnon - 30 points in his 20 games this year.
    🥊 4-1. That's what the Mammoth did to the Avalanche inside their last 5.
    🔁 They both saw the Senators lately: Ducks got a 6-3 win on 11/1, Avalanche took a 4-3 loss on 11/12.
    🧳 Ducks are 7-4 on the road this year.
    ⏱️ Ducks put up 21 goals in the third period over their last 10 and gave up 16.
    ✅ Bottom line: Ducks (+110). Avalanche is short-handed. Tell the homies.

The two college hoops games the owner asked about, as today's candidate cards (the 8 AM slate in this box priced Louisiana Tech -135 / UTEP -102; "AS POSTED" here = the 11/18 writer on the same leg):

### 2026-11-19 ncaab - Louisiana Tech -135 vs Tulane (candidate, 1.0u)

AS POSTED:

    🏟️ 3-0 at home for Louisiana Tech this season, Louisiana Tech, and it ain't a question.
    ⏱️ Louisiana Tech put up 189 points in the second half over their last 5 and gave up 172.
    📋 Louisiana Tech sits 3-2 so far.
    📊 69 a game for Louisiana Tech this year, 63 against. They outscore people.
    💯 Louisiana Tech's top scorer Braylon Wenger is putting up 18 a night lately (5 games).
    ✅ Louisiana Tech has everybody available.
    💯 Jaylen Fenner: 12 a night for Louisiana Tech over his last 5 games.
    📅 Last outing: Louisiana Tech got a 68-63 win over Jax State · Tulane took a 65-63 loss to Akron.
    ✅ Bottom line: Louisiana Tech at -135. Fair price, right spot - that's the bet.

NOW:

    🏟️ 3-0 at home for Louisiana Tech this season, Louisiana Tech, and it ain't a question.
    📊 69 a game for Louisiana Tech this year, 63 against. They outscore people.
    ⏱️ Louisiana Tech put up 189 points in the second half over their last 5 and gave up 172.
    💯 Louisiana Tech's top scorer Braylon Wenger is putting up 18 a night lately (5 games).
    ✅ Bottom line: Louisiana Tech at -135. Fair price, right spot - that's the bet.

### 2026-11-19 ncaab - UTEP -102 vs New Mexico St (candidate, 1.0u)

AS POSTED:

    🥊 New Mexico St just got beat 73-61 by San Diego St, UTEP about to spank 'em.
    💯 Cam McDaniels is giving UTEP 20 a night over the last 4 games he's played.
    🏦 When the book makes UTEP the favorite they won 3 of 4 this year.
    📊 UTEP put up 73 a game and give up 55 over their last 3. New Mexico St: 62 and 81.
    🔥 UTEP (3-1) won 3 in a row and they ain't done.
    🚀 Florida A&M got their cheeks clapped by UTEP last time out, 79-46.
    ✅ Nobody big missing for UTEP.
    ⏱️ The second half, last 4 games: 141 points for UTEP, 120 against.
    ✅ Bottom line: UTEP (-102). No gift in the number. UTEP is the play because of the spot, and the units say how much.

NOW:

    🥊 New Mexico St just got beat 73-61 by San Diego St, UTEP about to spank 'em.
    🆚 UTEP already beat New Mexico St this year - a 60-58 win at home on 11/12.
    🔥 UTEP (3-1) won 3 in a row and they ain't done.
    📊 UTEP put up 73 a game and give up 55 over their last 3. New Mexico St: 62 and 81.
    🏦 When the book makes UTEP the favorite they won 3 of 4 this year.
    ⏱️ The second half, last 4 games: 141 points for UTEP, 120 against.
    🚀 Florida A&M got their cheeks clapped by UTEP last time out, 79-46.
    🏁 UTEP outscored teams 153 to 128 in the first half over their last 4 games. They come out ready.
    ✅ Bottom line: UTEP (-102). No gift in the number. UTEP is the play because of the spot, and the units say how much.

### 2026-11-18 nba - Nuggets +120 vs Celtics (dog, 2.0u)

AS POSTED:

    🧠 The Celtics gotta breathe 5,300 feet up. Nuggets fin to handle that.
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

NOW:

    🧠 The Celtics gotta breathe 5,300 feet up. Nuggets fin to handle that. Plus Celtics flew 1,760 miles for this.
    🏁 Nuggets won the 1st quarter in 7 of their last 10 games. They come out ready.
    📅 The Celtics are fresh off a 115-105 loss to the Magic.
    🗓️ Nuggets won 6 of their last 10.
    💯 Jamal Murray is giving Nuggets 26 a night over the last 10 games he's played.
    ✅ Bottom line: Nuggets (+120). Put the homies on Nuggets.

### 2026-11-18 ncaab - Charleston So +114 vs Wofford (play, 2.0u)

AS POSTED:

    🧠 Charleston So all day — Charleston So just rolled to a 92-68 win over West Georgia.
    🏟️ 2-0 in their own building - Charleston So wins more than it loses there.
    ✅ Charleston So has everybody available.
    🧳 Wofford is 0-3 on the road this year.
    💯 Anthony Ruffolo been cooking for Charleston So - 21 a night over his last 4.
    💵 We price Charleston So at -104. The book's paying +114.
    📅 Wofford L 92-97 @ Queens last time out.
    ⚠️ Wofford has outscored teams 94 to 70 a game over their last 3; Charleston So sits 81 for, 66 against.
    ✅ Bottom line: Charleston So (+114). Our read beats this price. Trust the algorithm.

NOW:

    🧠 92-68 over West Georgia last time out for Charleston So, tap in.
    🧳 0-3 on the road for Wofford.
    🏟️ 2-0 in their own building - Charleston So wins more than it loses there.
    📊 Last 3 for Charleston So: 81 scored a game, 66 allowed.
    ⏱️ Charleston So put up 186 points in the second half over their last 4 and gave up 157.
    💯 Charleston So's top scorer Anthony Ruffolo is putting up 21 a night lately (4 games).
    📅 Wofford took a 97-92 loss to Queens last time out.
    ✅ Bottom line: Charleston So (+114). Trust the algorithm.

### 2026-11-17 nhl - Capitals +136 vs Lightning (dog, 2.0u)

AS POSTED:

    (no line under the pick)
    ✅ Nobody on Capitals' injury report. Whole squad's suiting up.
    🥅 Logan Thompson (projected, not confirmed for Capitals): a 0.893 save % (9 goals on 84 shots) over his last 3 starts. Andrei Vasilevskiy (expected in net, not confirmed for Lightning): a 0.896 save % (8 goals on 77 shots) over his last 3 starts.
    📅 Both took an L last time - Capitals a 7-4 loss to the Devils, Lightning a 2-0 loss to the Red Wings.
    📋 10-8 for Capitals, last time out a 7-4 loss to the Devils.
    🧳 3-3 away from home this year for Capitals.
    ⚠️ Not perfect - Capitals have dropped 2 straight.
    ✅ Bottom line: Capitals (+136). Fishy line - Capitals at +136 when we make 'em +112.

NOW:

    🎬 In one-goal games this year Capitals won 5 of 6. Capitals the side.
    🔁 They both saw the Predators lately: Capitals got a 4-3 win on 10/29, Lightning took a 5-4 loss on 10/31.
    🧳 Capitals won 2 of their last 3 on the road - a 4-3 win at the Predators and a 3-2 win at the Senators.
    📅 The Lightning comes in off a 2-0 loss to the Red Wings.
    🧾 6 wins in 12 games against winning teams for Capitals this year.
    💯 Capitals' top scorer lately is Cole Hutson - 11 points in the last 10 games.
    💣 3 of the last 5 times out, Capitals put up 4 or more.
    ⚠️ Not perfect - Capitals have dropped 2 straight.
    ✅ Bottom line: Capitals (+136). Lightning been squeaking by. Easy money.

### 2026-11-17 nba - Trail Blazers +110 vs Timberwolves (play, 0.5u)

AS POSTED:

    🚑 Timberwolves gotta play without Jonathan Kuminga (F), Jaylen Clark (G), Zyon Pullin (G), Anthony Edwards (G). Riding Trail Blazers.
    🚑 Timberwolves gotta play without Jonathan Kuminga (F), Jaylen Clark (G), Zyon Pullin (G), Anthony Edwards (G).
    🧳 6-2 on the road for Trail Blazers.
    🗓️ Last 5 for Trail Blazers: 3-2.
    📋 Trail Blazers are 9-4 after a 106-98 loss to the Timberwolves.
    ⚠️ What scares us a little: Trail Blazers go without Chris Youngblood (G), Vit Krejci (G), Ja Morant (G), Shaedon Sharpe (G).
    ✅ Bottom line: Trail Blazers (+110). The dog angles like it. Trust the algorithm.

NOW:

    🏟️ The Trail Blazers are 6-2 on the road, we riding Trail Blazers.
    🚑 Timberwolves gotta play without Jonathan Kuminga (F).
    🧹 Trail Blazers ain't squeaking by: 3 wins by 10+ in their last 5 games.
    📊 118 a game for Trail Blazers this year, 111 against. They outscore people.
    📊 Trail Blazers put up 112 a game over their last 3 and gave up 107.
    👌 Threes a night, last 5 games: Trail Blazers 15, Timberwolves 12.
    🐶 Trail Blazers won 3 of 6 as the underdog this year. They cash plus money.
    ⏱️ Trail Blazers won the 4th quarter in 6 of their last 10 games. They close.
    ⚠️ What scares us a little: Timberwolves beat Trail Blazers 106-98 last time out.
    ✅ Bottom line: Trail Blazers (+110). The price is about right - Trail Blazers grade out best of every dog on the slate, that's why it's up. Half a unit.

### 2026-11-15 nfl - Packers -142 vs Vikings (lock, 1.0u)

AS POSTED:

    🥊 The Vikings are coming off a 23-6 beating from the Bills, Vikings been trash as fuck.
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

NOW:

    🚑 Tap in — Kyler Murray, the Vikings' starting quarterback, is out.
    🎬 The Vikings keep winning by one score: 4 of their 6 wins this year, the last two 15-10 over the Dolphins and 16-10 over the Colts.
    🏟️ 3-1 in their own building - Packers win more than they lose there.
    🏟️ The Vikings play their home games under a roof. This one's outdoors in 34°.
    📊 Packers put up 24 a game on the year; Vikings can only find 18.
    📊 Last 3: Packers are outscoring teams 30 to 22 a game; Vikings are getting outscored 17 to 12.
    📅 Vikings took a 23-6 loss to the Bills last time out.
    🚀 Packers just beat the brakes off the Patriots, 45-27.
    ⚠️ The other side's best argument: Packers go without Josh Jacobs (RB).
    ✅ Bottom line: Packers (-142). Vikings are short-handed. Strongest favorite on the slate. Free money.

### 2026-11-15 nba - Raptors +160 vs Knicks (play, 0.5u)

AS POSTED:

    🧊 The Knicks have lost 2 straight, Knicks super trash right now. We talking shit, but the tape says it.
    🚑 Raptors out: F Scottie Barnes (33 min a night last year), C Nate Bittle, F Kawhi Leonard (31 min a night last year) · questionable: G Kevin McCullar Jr..
    🧳 2-3 on the road for Knicks.
    📊 Raptors score 114 points a game this year; Knicks manage 110.
    📋 5-7 for Raptors, last time out a 123-112 loss to the 76ers.
    📅 The Knicks come in off a 106-104 loss to the Pacers; the Raptors off a 123-112 loss to the 76ers.
    🏀 Raptors: their bench outscored teams by 3.1 per 48 minutes last season - deep squad · the coach plays 8 guys real minutes.
    ⚠️ Not perfect - Raptors go without Scottie Barnes (F), Nate Bittle (C), Kawhi Leonard (F).
    ✅ Bottom line: Raptors (+160). No big edge here - Raptors are just the best dog left on today's slate. Half a unit, keep it light.
    🌟 Raptors: Kawhi Leonard, Scottie Barnes are out.

NOW:

    🧊 The Knicks have lost 2 straight, we got Raptors.
    🧳 2-3 on the road for Knicks.
    📊 Raptors score 114 points a game this year; Knicks manage 110.
    🎟️ Knicks didn't cover the spread in 6 of their last 10. The book keeps asking too much of 'em.
    🧾 Knicks only got 1 win in 4 games against winning teams this year.
    ⏱️ 6 of the last 10 times out, Raptors won the 4th quarter.
    💸 Knicks lost 5 of 11 as the favorite this year. That's a favorite that loses.
    📅 The Knicks are fresh off a 106-104 loss to the Pacers.
    ⚠️ Not perfect - Raptors have dropped 3 straight.
    ✅ Bottom line: Raptors (+160). Knicks can't buy a win right now. No big edge here - Raptors are just the best dog left on today's slate. Half a unit, keep it light.

### 2026-11-14 nhl - Flyers +114 vs Blue Jackets (dog, 2.0u)

AS POSTED:

    🧊 3 straight losses for the Blue Jackets. Give me Flyers.
    🍀 Puck luck's been shit for Flyers - shooting plus save % at 97.4 over the last 10 games (100 is average).
    📊 Over the last 3, Flyers are +0 a game (3 for, 3 against); Blue Jackets are -3 (1 for, 4 against).
    📅 Flyers off a 3-2 loss to the Oilers, Blue Jackets off a 3-1 loss to the Lightning.
    ⏳ Flyers got the extra day: 3 days off to Blue Jackets' 2 days.
    🥊 The Panthers spanked the Blue Jackets 4-1 within their last 5 games.
    📋 5-16 for Flyers, last time out a 3-2 loss to the Oilers.
    ⚠️ Cam Talbot (Blue Jackets, projected, not confirmed) is at a 0.929 save % over his last 3 starts to Joseph Woll's 0.893 (our projected guy, not confirmed).
    ✅ Bottom line: Flyers (+114). We make Flyers -106, the book says +114.

NOW:

    🧊 3 straight losses for the Blue Jackets. Give me Flyers.
    🥊 4 times this year the Blue Jackets got blown out in their own building: 6-2 by the Maple Leafs and 4-1 by the Panthers.
    🎬 5 of 7 wins by one goal for the Blue Jackets this year (the last two: 4-3 over the Flyers and 2-1 over the Stars). That's a team living on the edge.
    🔁 They both saw the Sabres lately: Flyers got a 3-1 win on 10/21, Blue Jackets took a 5-2 loss on 11/6.
    📊 Blue Jackets are giving up 4 a game and scoring 1.3 over their last 3.
    💸 When the book makes Blue Jackets the favorite, they lost 3 of 6 this year.
    🥅 Jet Greaves — the Blue Jackets' last starter in net — has been giving up a lot of goals: a 0.877 save % (10 goals on 81 shots) over his last 3 starts.
    📋 Blue Jackets come in 7-10 on the year.
    ⚠️ Flyers are 2-9 on the road this year.
    ✅ Bottom line: Flyers (+114). Blue Jackets can't buy a win right now. Tap in.

### 2026-11-14 ncaab - Northern Iowa +102 vs Oakland (play, 1.0u)

AS POSTED:

    🥊 Fuck it, Northern Iowa — Oakland got handled 111-79 by Boise St last time out.
    📊 Over the last 3, Northern Iowa is -12 a game (81 for, 93 against); Oakland is -32 (71 for, 103 against).
    🏀 Northern Iowa was 23-13 last year (beat teams by 7.7 per game), Oakland 16-16 (finished +0.9 in point margin).
    🗑️ 0-5. Lame ass team right now, that's Oakland.
    ✅ Northern Iowa has everybody available.
    🥊 109-68. That's what Alabama did to Oakland inside their last 5.
    ⚠️ Biggest knock on Northern Iowa: Northern Iowa played last night (a 106-72 loss to Michigan St) and Oakland sat 3 days.
    ✅ Bottom line: Northern Iowa (+102). We make 'em -106, the book's at +102.

NOW:

    🥊 Fuck it, Northern Iowa — Oakland got handled 111-79 by Boise St last time out.
    🥊 90-67. That's what Santa Barbara did to Oakland inside their last 5.
    📊 Oakland this season: 95 points a game allowed, 69 scored. They get outscored.
    📊 Last 3 for Oakland: 71 scored a game, 103 given up.
    🏀 Northern Iowa was 23-13 last year (beat teams by 7.7 per game), Oakland 16-16 (came out 0.9 points a game to the good).
    💣 Northern Iowa scored 80 or more in 3 of their last 4 games.
    💯 Northern Iowa's top scorer Greyson Uelmen is putting up 19 a night lately (4 games).
    ⚠️ Biggest knock on Northern Iowa: Northern Iowa played last night (a 106-72 loss to Michigan St) and Oakland sat 3 days.
    ✅ Bottom line: Northern Iowa (+102). Tap in.

### 2026-11-12 nhl - Blackhawks +130 vs Sabres (dog, 2.0u)

AS POSTED:

    😮‍💨 The Sabres played yesterday, the Blackhawks rested, Blackhawks take this one.
    🥅 Colten Ellis, projected to start for the Sabres (not confirmed yet), can't keep the puck out lately: a 0.868 save % (12 goals on 91 shots) over his last 3 starts.
    🚑 Sabres are down Konsta Helenius (C) tonight.
    🍀 The bounces have been going against Blackhawks: their shooting and save % together sit at 93.4 over the last 10, and 100 is normal. That evens out.
    🥊 The Lightning spanked the Sabres 8-3 within their last 5 games.
    📊 94% of the moneyline bets on the Sabres. Let the public have 'em.
    📅 Blackhawks off a 9-2 loss to the Hurricanes, Sabres off a 8-3 loss to the Lightning. One of 'em gets right tonight.
    📋 Blackhawks are 4-14 after a 9-2 loss to the Hurricanes.
    ⚠️ Blackhawks have dropped 6 straight. We see it. Ain't scared of it.
    ✅ Bottom line: Blackhawks (+130). We make Blackhawks -101 - the book's paying +130. Tap in.

NOW:

    😮‍💨 The Sabres played yesterday, the Blackhawks rested, Blackhawks take this one.
    🥊 The Sabres got embarrassed 8-3 by the Lightning in one of their last 5.
    🎬 5 of 8 wins by one goal for the Sabres this year (the last two: 7-6 over the Ducks and 3-2 over the Kings). That's a team living on the edge.
    📊 On the year Sabres give up 3.6 goals a game and score 2.9.
    📋 Sabres come in 8-10 on the year.
    ⏱️ The third period, last 10 games: Sabres gave up 14 goals and scored 8.
    🧾 Sabres won 3 of 11 against teams with a winning record this year.
    ⚠️ What could fuck this up: Blackhawks have dropped 6 straight.
    ✅ Bottom line: Blackhawks (+130). Sabres played last night. The whole hood eating with this one.

### 2026-11-11 nhl - Ducks -142 vs Predators (play, 1.0u)

AS POSTED:

    😮‍💨 Ducks all day — the Predators played last night and the Ducks didn't.
    ✅ Ducks are healthy — nobody important sitting.
    🧳 3-4 on the road for Predators. Road trips been rough on 'em.
    📊 Ducks score 3.8 goals a game this year; Predators manage 3.1.
    🔥 Both teams are rolling: Ducks have won 5 straight, Predators 5.
    📅 Last time out: Ducks a 5-2 win over the Penguins, Predators a 3-0 win over the Kings. Both feeling good, one leaves pissed.
    📊 Ducks average 5 for / 3 against over their last 3; Predators 3 for / 1 against.
    ⚖️ Ducks 10-8, Predators 9-9. A wash on the records.
    📊 The Ducks got 88% of the tickets on the moneyline (88% of the money). The whole hood eating with this one.
    ⚠️ Gotta keep it honest - Justus Annunen (Predators, projected, not confirmed) is at a 0.899 save % over his last 3 starts to Laurent Brossoit's 0.881 (our guy in net last time out). Still riding Ducks.
    ✅ Bottom line: Ducks (-142). Our number's -162; they're giving us -142. Say less.

NOW:

    😮‍💨 Ducks all day — the Predators played last night and the Ducks didn't.
    🔥 Ducks have won 5 straight (10-8).
    🔁 They both saw the Penguins lately: Ducks got a 5-2 win on 11/8, Predators took a 3-2 loss on 10/24.
    🧳 3-4 on the road for Predators.
    🏟️ Ducks won 2 of their last 3 at home - a 6-3 win over the Senators and a 5-2 win over the Penguins.
    📊 Ducks score 3.8 goals a game this year; Predators manage 3.1.
    ⏱️ Ducks outscored teams 18 to 15 in the third period over their last 10 games. They close.
    📋 Ducks sit 10-8; Predators are 9-9. Better record's on our side.
    ⚠️ Gotta keep it honest - Justus Annunen (Predators, projected, not confirmed) is at a 0.899 save % over his last 3 starts to Laurent Brossoit's 0.881 (our guy in net last time out).
    ✅ Bottom line: Ducks (-142). Easy money.

### 2026-11-10 nba - Celtics -124 vs 76ers (play, 1.0u)

AS POSTED:

    🧠 The Celtics smacked the Bucks 117-97 last time out, Celtics all day.
    📊 Last 3: Celtics are outscoring teams 115 to 93 a game; 76ers sit at 111 for, 115 against.
    🧯 Legal mess around the 76ers this week: "Man arrested on stalking charges at LeBron James' home in Los Angeles"
    🥊 The Cavaliers put 119-95 on the 76ers in one of their last 5.
    🔥 Celtics are rolling — 3 wins in a row, 8-2 on the year.
    🧳 Celtics are 3-2 on the road this year. They win in other people's houses.
    🛡️ Celtics give up 104 points a game this year; 76ers give up 108. Our D is the better one.
    🚑 76ers are without Adem Bona (C), Dominick Barlow (F), Ariel Hukporti (C).
    ⚖️ 8-2 against 9-2 - nothing in it on paper.
    📅 And the 76ers? A 127-121 win over the Bulls last time out.
    🏀 Celtics: their bench outscored teams by 10.2 per 48 minutes last season - deep squad · the coach plays 9 guys real minutes · Paul George is cooking - the team's +14.3 per 48 with him on the floor lately, +1.2 last season · Sam Hauser is cooking - the team's +22.9 per 48 with him on the floor lately, +8.1 last season.
    ⚠️ The other side's best argument: 76ers are 4-1 at home this year.
    ✅ Bottom line: Celtics (-124). Could go either way. Celtics by a nose - a lean.
    🌟 Celtics: Jayson Tatum (All-NBA 2025, top-5 MVP) is in the lineup tonight.

NOW:

    🧠 The Celtics smacked the Bucks 117-97 last time out, Celtics all day.
    🥊 The Cavaliers put 119-95 on the 76ers in one of their last 5.
    🔥 Celtics are rolling — 3 wins in a row, 8-2 on the year.
    🧳 Celtics are 3-2 on the road this year.
    📊 Celtics put up 115 a game on the year; 76ers can only find 111.
    📊 Last 3: Celtics are outscoring teams 115 to 93 a game; 76ers are getting outscored 115 to 111.
    🛡️ Celtics give up 104 points a game this year; 76ers give up 108. Our D is the better one.
    ⚠️ The other side's best argument: 76ers are 4-1 at home this year.
    ✅ Bottom line: Celtics at -124. Fair price, right spot - that's the bet.

### 2026-11-09 nhl - Canucks +114 vs Flyers (dog, 2.0u)

AS POSTED:

    😮‍💨 The Flyers played yesterday, the Canucks rested, give me Canucks.
    🍀 Puck luck's been shit for Canucks - shooting plus save % at 97.1 over the last 10 games (100 is average). That don't last.
    🥅 Pucks keep getting past the Flyers' goalie, Joseph Woll — a 0.854 save % (12 goals on 82 shots) over his last 3 starts.
    🎲 By goals scored and allowed, Canucks should be about 13 points better than their record. The books are sleeping on that.
    📊 Canucks at 2.9 goals a game this year. Flyers at 2.2. Ours scores more, that's just facts.
    🧳 Travel check on the Flyers: 3rd road game in 6 days.
    🧳 1-8 on the road for Flyers. Road trips been rough on 'em.
    🥊 The Capitals spanked the Flyers 5-2 within their last 5 games.
    📅 Both took an L last time - Canucks a 4-2 loss to the Oilers, Flyers a 4-3 loss to the Flames.
    📊 81% of the bets and 67% of the money on the Flyers on the moneyline. We on the other side.
    📊 Last 3 games: Canucks scored 3 and gave up 5 goals a game; Flyers 2 and 4.
    📋 Canucks are 3-16 after a 4-2 loss to the Oilers.
    ⚠️ Not perfect - Canucks have dropped 5 straight. We'll take our chances.
    ✅ Bottom line: Canucks (+114). -115 on our sheet, +114 at the book. Trust the algorithm.

NOW:

    😮‍💨 The Flyers played yesterday, the Canucks rested, give me Canucks.
    🥊 3 times this year the Flyers got blown out on the road: 5-1 by the Bruins and 5-2 by the Capitals.
    🔁 They both saw the Flames lately: Canucks got a 4-1 win on 10/3, Flyers took a 4-3 loss on 11/8.
    🧳 1-8 on the road for Flyers this season.
    🧳 Travel check on the Flyers: 3rd road game in 6 days.
    📊 Canucks at 2.9 goals a game this year. Flyers at 2.2. Ours scores more.
    📋 Flyers come in 4-15 on the year.
    🥅 Joseph Woll — the Flyers' projected starter, nobody's confirmed yet — has been giving up a lot of goals: a 0.854 save % (12 goals on 82 shots) over his last 3 starts.
    ⚠️ Not perfect - Canucks have dropped 5 straight.
    ✅ Bottom line: Canucks (+114). Flyers played last night. Trust the algorithm.

### 2026-11-08 nfl - Broncos -142 vs Panthers (lock, 1.0u)

AS POSTED:

    💪 Panthers are 3-4. Broncos are 6-2. Panthers fin to get spanked.
    📊 Scoreboard lately - Broncos: 25 scored, 18 allowed a game (last 3). Panthers: 19 and 28. We been better.
    🏟️ Panthers at home this season: 1-2. Their own crowd's been watching 'em lose.
    🚑 Panthers are down Will Lee III (CB), Bobby Okereke (LB) today.
    🥊 The Panthers got smacked 43-13 by the Buccaneers inside their last 5. That's who we're going against.
    🧊 Panthers are 3-4 and ice cold — 2 straight L's.
    🧯 Coaching change for the Panthers — "Panthers bring back DeAngelo Hall as CB coach in 1st move since Evero firing"
    🔥 Broncos can't stop winning: 4 straight, 6-2 overall.
    📅 How they came in: Broncos W 28-24 vs Chiefs · Panthers L 19-27 @ Packers.
    🎯 The quarterbacks - Bo Nix (Broncos): 3 TDs, 0 picks and 551 yards in his last 3 games. Bryce Young (Panthers): 4 TDs, 3 picks and 653 yards in his last 3 games.
    📊 Everybody and they mama on the Broncos: 89% of the bets, 94% of the money.
    🧳 Broncos are 2-2 on the road so far.
    ⚠️ Heads up: Broncos go without Kris Abrams-Draine (CB), Brandon Jones (S). Still Broncos.
    ✅ Bottom line: Broncos (-142). We'd lay -165 on Broncos - getting -142. Easy money.

NOW:

    💪 Panthers are 3-4. Broncos are 6-2. Panthers fin to get spanked.
    🚑 Panthers gotta play without Will Lee III (CB), Bobby Okereke (LB).
    🥊 The Panthers got run in their own building twice already this year - 59-37 by the Bears and 43-13 by the Buccaneers.
    🧊 Panthers are 3-4 and ice cold — 2 straight L's.
    🔥 Broncos can't stop winning: 4 straight, 6-2 overall.
    🧳 Last 3 on the road for Broncos: 2 wins, a 23-17 win at the Chargers and a 30-16 win at the Cardinals.
    🏟️ Panthers are 1-2 at home this year. That ain't a fortress.
    📊 Scoreboard lately - Broncos: 25 scored, 18 allowed a game (last 3). Panthers: 19 and 28.
    🧯 Coaching change for the Panthers — "Panthers bring back DeAngelo Hall as CB coach in 1st move since Evero firing"
    ⚠️ The other side's best argument: Broncos go without Kris Abrams-Draine (CB), Brandon Jones (S).
    ✅ Bottom line: Broncos (-142). The side we trust most today. Tap in.

### 2026-11-08 nhl - Jets +124 vs Lightning (dog, 2.0u)

AS POSTED:

    😮‍💨 That's a shit spot for Lightning — the Lightning played last night and the Jets didn't.
    🍀 Jets been unlucky, not bad: add their shooting % and save % over the last 10 and you get 95.4, under the 100 a normal team runs.
    📅 Lightning is off a 4-3 win over the Wild themselves. One of 'em takes an L tonight.
    🧯 The Lightning got a guy wanting out: "Back on home ice after trade request, Kucherov has two assists in Lightning wins"
    🧳 3-5 on the road for Lightning this season. They hate leaving the house.
    📋 Jets are 6-11 after a 6-2 win over the Canucks.
    📊 90% of the bets on the Lightning. Let the public have 'em.
    ⚠️ Biggest knock on Jets: Andrei Vasilevskiy (Lightning, projected, not confirmed) is at a 0.912 save % over his last 3 starts to Stuart Skinner's 0.831.
    ✅ Bottom line: Jets (+124). Line makers ain't showing no respect to Jets at +124 - we make 'em +111.

NOW:

    😮‍💨 That's a shit spot for Lightning — the Lightning played last night and the Jets didn't.
    🥊 3 times this year the Lightning got blown out on the road: 4-1 by the Rangers and 6-3 by the Avalanche.
    🔁 They both saw the Avalanche lately: Jets got a 3-2 win on 10/7, Lightning took a 6-3 loss on 10/23.
    🧳 3-5 on the road for Lightning this season.
    💯 Mark Scheifele been producing for Jets: 9 points over the last 10.
    📅 Fresh off a 6-2 win over the Canucks for Jets.
    💣 4+ goals for Jets in 3 of their last 5. They can score.
    ⚠️ Andrei Vasilevskiy (Lightning, projected, not confirmed) is at a 0.912 save % over his last 3 starts to Stuart Skinner's 0.831 (our guy in net last time out).
    ✅ Bottom line: Jets (+124). Tap in.

### 2026-11-07 ncaaf - Ole Miss +145 vs Georgia (play, 1.0u)

AS POSTED:

    📊 Ole Miss all day — 82% of the crowd is on Georgia.
    🚑 Ole Miss out: RB Kewan Lacy (starter), WR Samari Reed · questionable: DE Kam Franklin (starter), LB Keaton Thomas (starter).
    🗓️ Ole Miss won 3 of their last 5.
    🏟️ Home cooking for Ole Miss - 5-0 in their own building this season.
    🗑️ Gunner Stockton has been throwing it to the other team — 3 TDs, 3 picks and 622 yards in his last 3 games.
    🚀 Ole Miss just beat the brakes off Auburn, 45-15.
    📅 And Georgia? A 27-8 win over Florida last time out.
    📋 6-2 for Ole Miss, last time out a 45-15 win over Auburn.
    🎯 Trinidad Chambliss for Ole Miss: 7 TDs, 4 picks and 754 yards in his last 3 games.
    ⚠️ What could fuck this up: Ole Miss goes without Kewan Lacy (RB).
    ✅ Bottom line: Ole Miss (+145). We price Ole Miss at +106 - +145 is extra money. We'll take it.

NOW:

    🧠 Give me Ole Miss — Auburn got their cheeks clapped 45-15 by Ole Miss last time out.
    🗑️ Gunner Stockton has been throwing it to the other team — 3 TDs, 3 picks and 622 yards in his last 3 games.
    🔁 They both saw Auburn lately: Ole Miss got a 45-15 win on 10/31, Georgia took a 27-24 loss on 10/17.
    🧹 Ole Miss ain't squeaking by: 3 wins by 14+ in their last 5 games.
    🏟️ Home cooking for Ole Miss - 4-0 in their own building this season.
    📊 Scoreboard lately - Ole Miss: 34 scored, 17 allowed a game (last 3). Georgia: 24 and 17.
    ⏱️ The second half, last 5 games: 97 points for Ole Miss, 65 against.
    💣 Ole Miss scored 31 or more in 3 of their last 5 games.
    ⚠️ What could fuck this up: Ole Miss goes without Kewan Lacy (RB).
    ✅ Bottom line: Ole Miss (+145). Tap in.

### 2026-11-07 ncaaf - UConn +240 vs North Carolina (play, 1.0u)

AS POSTED:

    📊 93% of the cash is on North Carolina, not us. We got UConn.
    🧊 North Carolina dropped 2 in a row (4-4). They fin to make it 3.
    📅 UConn off a 35-26 loss to Air Force, North Carolina off a 38-35 loss to Miami. One of 'em gets right today.
    🏟️ 2-2 at home this year for UConn.
    📋 UConn 4-4, North Carolina 4-4 - same spot in the standings, not the same team.
    ⚠️ What scares us a little: Billy Edwards Jr. (North Carolina) has 7 TDs, 0 picks and 803 yards in his last 3 games to Kalieb Osborne's 4 TDs, 0 picks and 693 yards in his last 3 games.
    ✅ Bottom line: UConn (+240). +137 on our sheet, +240 at the book. Trust the algorithm.

NOW:

    🎬 3 of 4 wins by one score for North Carolina this year (the last two: 21-17 over Pitt and 24-20 over Duke). That's a team living on the edge. Riding UConn.
    📊 UConn put up 34 a game on the year; North Carolina can only find 26.
    📊 Last 3: UConn is outscoring teams 32 to 24 a game; North Carolina sits at 30 for, 30 against.
    💣 31+ points for UConn in 3 of their last 5. They can score.
    🎟️ 4 covers in the last 6 for UConn. They been better than the book thinks.
    🏃 On the ground the last 3 games: UConn 206 yards a game, North Carolina 101.
    📅 Last time out North Carolina took a 38-35 loss to Miami.
    💥 Sacks over the last 3: UConn 7, North Carolina 3. Our front gets home.
    ⚠️ What scares us a little: Billy Edwards Jr. (North Carolina) has 7 TDs, 0 picks and 803 yards in his last 3 games to Kalieb Osborne's 4 TDs, 0 picks and 693 yards in his last 3 games.
    ✅ Bottom line: UConn (+240). North Carolina been squeaking by. Trust the algorithm.

### 2026-11-06 nba - Bucks +136 vs Raptors (dog, 1.0u)

AS POSTED:

    📊 Not us. We got Bucks — 89% of the crowd is on the Raptors.
    🥊 The Raptors got their cheeks clapped 128-109 by the Nuggets inside their last 5.
    🗓️ 2-3 in their last 5 - Raptors been sliding.
    🧳 2-3 on the road for Raptors. Road trips been rough on 'em.
    🚑 Raptors are down Scottie Barnes (F), Immanuel Quickley (G), Kawhi Leonard (F), Nate Bittle (C) tonight.
    🧳 The Raptors put in the miles to get here (4th road game in 6 days).
    📋 1-7 for Bucks, last time out a 109-102 loss to the Celtics.
    📅 The Raptors come in off a 128-109 loss to the Nuggets; the Bucks off a 109-102 loss to the Celtics.
    🏀 Bucks: the coach plays 9 guys real minutes.
    ⚠️ Gotta keep it honest - Bucks have dropped 4 straight. Still riding Bucks.
    ✅ Bottom line: Bucks (+136). Line makers ain't showing no respect to Bucks at +136 - we make 'em -108.

NOW:

    🥊 Not touching Raptors — the Raptors are coming off a 128-109 beating from the Nuggets.
    🚑 Raptors are down Scottie Barnes (F), Immanuel Quickley (G) tonight.
    📉 No Scottie Barnes means 24 points a night gone for Raptors.
    🚪 Raptors gave up 120 or more points in 3 of their last 5 games.
    🧳 The Raptors put in the miles to get here (4th road game in 6 days).
    🧳 2-3 on the road for Raptors.
    📊 Raptors have been outscored 126 to 120 a game over their last 3.
    🧲 49 rebounds a night for Bucks over their last 5. Raptors get 40.
    ⚠️ Gotta keep it honest - Bucks have dropped 4 straight.
    ✅ Bottom line: Bucks (+136). Trust the algorithm.

