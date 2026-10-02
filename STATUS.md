# D503 Sports Engine - where things stand (read this first in every new chat)

Kept up to date at the end of every working session, so a fresh chat knows what the last one did. The owner's standing
rules are in CLAUDE.md; what the studies found is in SPORTS_FINDINGS.md. Newest notes on top.

## 10/2 (overnight session)

**Live on main tonight**
- Live bets: never a 3-way / regulation-only / period line as the moneyline (the Devils +145 came from a backup book's
  3rd-period line - voided with the owner's OK); two books far apart = no price; a pregame favorite tied or ahead at
  plus money needs a second book; every live bet logs which book priced it; one box at a time (BET IT NOW, then
  TONIGHT'S LIVE BETS).
- Injuries: a QB / goalie on the report is only "the starter" if our box scores show he started lately - unknown is
  never claimed or weighed (the Steelers card called two BACKUP QBs starters). Re-run: the engine still had the
  Steelers (59%, a lean) with the right data.
- Daily pick audit (sports_audit.py -> data/sports/pick_audit.json), read by the 1 AM daily review routine.
- Units: every value play / Lock / Dog ½u+, leans 0; own read under 3% over the price = ½u. (The 8% line and
  "favorites ½u" were tried and rolled back - "no half units across the board".)
- Every factor weighed for both sides (weigh_favorites); study angles on a dog capped at ±6 (STUDY_CAP) - BEING TESTED.
- Thursday-night fade removed; momentum leads wired (NBA comeback-win fade, MLB late-rally dog); "washed" = an old QB
  (career by 2012) who's cold.
- Five audits' bug fixes (live, data merge of college games, early-play pings, board rules, grading). College games
  restored (316 had been wiped by the hourly job; game files now merge by id).
- Daily board dry run: tools/board_preview.py / Actions -> board_preview.

**Running / waiting on results**
- Unit-sizing replay (current Kelly vs flat vs tiers vs confidence buckets) -> pick the unit system.
- Five point-system studies: cap size, learned angle points, stacking, overlap / double counting, points by price and
  sport -> set STUDY_CAP / FAV_CAP and the angle points by the data.

**Open decisions (the owner's call)**
- "No forced locks": a Lock of the Day only when the read really beats the price, else "No Lock today" (CLAUDE.md
  still says ALWAYS a Lock until the owner says the words). The Dog stays real-value only; leans fill to 5+ picks.
- Card labels showing the edge size in words ("BIG EDGE - 3 UNITS" / "SMALL EDGE - ½ UNIT").

**Next builds**
- Stars beyond QB/goalie (NFL lead rusher / receiver, NBA top scorers) - verified from box scores only.
- Re-check the NHL elimination-dog finding before April; college hoops dog fix before November.
- Hockey: the engine has no real edge there yet (-2% on 1,851) - hockey dogs leave the Dog of the Day if the replay
  says they lose.
