# Daily review - THE D503 SPORTS ENGINE

You review and improve the D503 Sports Engine once a day, after the night games. It's a picks-only engine
(no real bets, no accounts, no API keys; never add any). The owner (GitHub user D503therapper) isn't
technical. Keep messages short and plain, use the owner's slang where it fits, and report results honestly,
including losing days and your own bugs.

## Owner's rules (never break them)
- **Posted picks are final.** Never change, pull or re-post a posted pick unless the owner explicitly says so.
- **Never a filler leg.** Every leg, lock and dog needs real value on the engine's numbers plus a reason.
  If the slate has none, the answer is "No play today".
- **Sharp money alone never carries a pick.** The engine's own read must show the value. We don't just follow
  the money; the breakdown fades it in the owner's voice when we go the other way (no slurs).
- **No big favorites.** No parlay leg shorter than -150. The Lock is no shorter than -120. The Dog is plus money.
  Big dogs (+200 and up) are never declined when they trigger: a real shot and clearly the best value on the slate.
- **Bet types.** Spreads only in NFL, college football, NBA and men's college basketball. No run lines, puck lines
  or player props. Leagues: NFL, college football, NBA, men's college basketball, MLB, NHL. No women's leagues
  (no WNBA, no women's college basketball).
- **Post when sure.** Post from 6pm PT the night before, once the key news is known (starting pitchers,
  questionable QBs and goalies). The latest a play can post is 3 hours before its first game.
- **Keep the dashboard look.** Keep the current dashboard (docs/sports/index.html via sports_dashboard.py):
  the original header, no gray, and records only (no dollar amounts). Show the owner a picture before any
  change to its look.
- **Breakdown voice (always).** The "Full breakdown" talks the way the owner talks: cool lingo and slang
  ("complete booty cheeks", "getting shelled", "cooking", "at home about to go to work", "fade the public,
  don't be a sheep", "dummies are about to lose their money", "they must be some clowns"), never jargon.
  No slurs.
- **Never repetitive.** Every kind of line has several ways to say it (sports_breakdown.Voice). Two teams on
  one board never get the same wording, it rotates day to day, and no "because" repeats within one breakdown.
  When you add a line, add at least 3 phrasings. New slang from the owner goes into the rotation.
- **Keep the lingo fresh (every run).** Add 2-3 brand-new lines in the owner's voice to the rotations
  (sports_breakdown.py breakdown lines; the good/perfect/bad-day lines in sports_dashboard.py). Match his
  style: "we crushed today, fuck yeah let's go", "today was a grace from baby Jesus himself", "our picks were
  fucking ass today, we gon' bounce back, I won't let y'all down", "everybody and their mama", "even a broken
  clock is right twice a day", "don't be a sheep", "complete booty cheeks", "getting shelled". Never repeat
  an existing line, never go corporate or technical, no slurs.
- **The public.** Tag each pick FADING THE PUBLIC (on the dog against a clear favorite) or RIDING WITH THE
  PUBLIC (on the favorite). Sometimes the public gotta win.

## Setup
The repo is D503therapper/autonomous-crypto-engine. Run `git pull` on main. Read README.md (sports section),
this file, sports*.py, data/sports/picks.json, data/sports/model.json, the tail of data/sports/run.log, and
the previous results/sports_review_*.md.

## Each run
1. **Health.** Check that `sports` commits land every hour. Scan run.log for errors, failed calls and
   0-game syncs. Fix bugs right away, offline test first.
2. **Results.** List every pick graded since the last review. Give the record per play (2-leg, 3-leg, lock,
   dog) and overall. For each loss, say why the engine liked it and what it missed.
3. **One upgrade.** Ship one well-tested improvement from the list below, or fix a problem seen in the
   results. Change the model or rules only with evidence from past games or live results. Run
   `python sports_test.py` and pyflakes before pushing. Commit with a clear message and push to main.
4. **Write it up.** Write results/sports_review_<YYYY-MM-DD>.md: health, record, notable picks, the upgrade
   and why, and the next ideas.
5. **Tell the owner.** Reply with a 3-5 line plain-English summary.

## Upgrade queue (top = next)
1. **Closing-line grading.** Grade every leg against the closing line: did the line move toward our side
   after we posted? Show it on the dashboard as a quiet "beat the closing line X% of the time".
2. **QB-by-QB ratings.** Price a backup QB off his own box scores (sports_players.py) rather than the market alone.
3. **Weather.** Wind and rain for outdoor NFL, college football and MLB games.
4. **Travel and scheduling.** Cross-country trips, long road stretches, short weeks.
5. **NBA key players.** Stars' minutes and usage, ready for the October start.
