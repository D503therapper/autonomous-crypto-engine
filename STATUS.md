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
- The factor check before the 8 AM board (sports.factor_check) now also checks the data is FRESH: most of the slate
  priced 12h+ ago (odds pull failed), recent games with no final score, the QB / pitcher / goalie stats missing - each
  holds the board until the last try; a game or two the books stopped listing is only a note. The daily pick audit
  also checks the cards' own words (streaks, home/road, players named out vs the injury report).

**Studies done overnight (all in SPORTS_FINDINGS.md 10/2)**
- Unit system BUILT: the Lock by its own read, the Dog flat 1u, value plays ½u (712-day replay: since 7/2023 +10.5u
  vs the old sizing -15.2u; value plays lose at any size).
- Point system BUILT: NBA overreaction +5, NHL both-lost +3.5, MLB +200..+249 -4, NHL road-opener off, no double
  counting (NHL hot key / key edge; college ice cold + losing streak), college bye only within 30 days. STUDY_CAP 6,
  linear stacking and the favorites' weighing confirmed (no change). Per-sport point scaling = a LEAD (re-check).
- The backup near_lock loses (-17% flat) - kept at ½u because the owner wants a Lock every day.

**10/2 morning**
- Units: unchanged (value plays ½u, Dog 1u, Lock by read, backup Lock ½u). Claude's recommendation: keep them and
  reassess on OUR live results after 100-200 graded unit plays, not the replay - the owner was ASKING, not deciding
  (his words: "I'm not telling you anything. I'm asking you"); value plays -> no units is still open (the replay ran the current engine over 2023-26:
  -1.1% overall, +1.2% since 7/2023 - roughly break-even, and partly flattered by peeking; the owner doesn't trust it
  as proof). Live so far: Lock 4-0 +7.61u, Dog 0-3 -2u, plays 0-1.
- Backup Lock: titled LOCK with its own box above ("nothing met our Lock of the Day standard").
- The full pre-board check: data freshness (prices, finals, opening lines, models, player stats, weather, injuries),
  a sizing check, and a checker self-test (12 broken inputs, each must be caught).
- NEXT (offered, not built): a "beat the closing price" record on the dashboard - the fastest real test of an edge.

**10/2 later morning - INJURY DATA (the owner: "the most important thing in sports")**
- Found: ESPN's college injury feed listed 3 teams - Virginia Tech, Pitt, Penn State, Northwestern... were read as
  "nobody hurt". Fixed: official reports file (injuries_official.json) + a twice-daily routine that fills it; a team
  with no injury data gets no pick; 2+ out / 4+ questionable = no units, card names who's out; the 10/2 board was held
  until the owner said post (HOLD_DAYS).
- NEXT (big): weigh every position from box scores (RB / WR / OL / defense in football, top scorers in hockey, NBA
  starters) instead of the blunt no-units rule; automate the conference reports (their pages are script-built).
- Dylan Larkin (Red Wings captain) out 2 games; Hellebuyck (Jets) suspended to 10/17 - both were on the feed but
  skaters / suspensions weren't weighed.

**10/2 afternoon**
- NO FORCED LOCK (the owner's call): a Lock only when the read beats the price; the Lock spot says so otherwise.
- Missing key players now move the engine's own read (sports_absences, the 10/2 absence studies - SPORTS_FINDINGS).
- Injury data pipeline for college: workers find the official reports -> GitHub reads the pages (Actions ->
  fetch_pages, results/pages) -> verified lists go into injuries_official.json (10/3: 29 teams so far). Snippets alone
  are never trusted (several were 2024/2025 articles). A game with no injury report is off the table (not 'waiting').
- Fixed today: duplicate picks (merge keyed by post time), board posts at 8:00 sharp (7:44/7:47 runs), stale summer
  opens, 'running on fumes' on rested teams, both-teams-hot streak lines, report jobs failing to save, Cloudflare CPU.
- Waiting on the owner: the 8 AM note rewrite (on the claude/ branch, not main).
- 10/2 evening: Dr. Bob tracker LIVE (sports_capper -> data/sports/capper_drbob.json): his free NFL Leans from
  drbobsports.com/nfl-analysis, logged the first time seen with his number, graded off the final next to our pick on
  the same game (with_us / against_us). Record only - never moves a pick. First lean: Cleveland +3 -115 (won, 27-24).
  His site confirms: NO college football this year (NFL only).
- 10/2 evening: early hockey / baseball study done (SPORTS_FINDINGS) - NOTHING built: every spot either dead or a lead
  under 2 SE. Best lead: NHL rested team vs a back-to-back, engine 3+ over the open - log it live before any units.
- Waiting on the owner: the beat-the-close box on the dashboard (preview sent; code sits uncommitted on the claude/
  branch checkout - sports_dashboard.close_box + its test).
- 10/2 night: GitHub skipped the engine's hourly runs 3 hours - the hourly bug check now restarts it after 80 min.
- College injury coverage, the hard truth (10/2 night, 10/3 slate): 52 of ~200 lined-game teams verified. NO official
  report exists for non-conference games (UNC-Notre Dame, Syracuse-UConn, Cal-UNLV...) or for the Sun Belt / CUSA /
  AAC; the MAC posts game-day reports only (~3h before kickoff, getsomemaction.com). Those games stay off the board
  (no pick off blind data). The 5:47 / 11:47 routine knows all this now (prompt updated 10/2).
- 10/3: futures study (SPORTS_FINDINGS) - preseason longshots never beat their price; daily futures price log LIVE
  (sports_futures); the owner's call: a no-units 🏆 FUTURES WATCH card or wait for the mid-season study. Patty vs the
  Algorithm removed for good (the owner). No-Lock days: the question box names what the Lock would have been
  (sports.lock_miss).
- NEXT: capper studies (1)-(5) below; NHL rested-vs-back-to-back live log (no units); weigh OL / defense absences.

**Capper studies (the owner, 10/2 - "find the clowns and the actual cappers ... what the best are doing right")**
- Benchmark: Dr. Bob (Bob Stoll, drbobsports.com) - the owner's pick as THE proven capper. Self-published: NFL best
  bets 514-379-12 (57.6%) in 10 seasons (play-by-play model), college football best bets 55.1% since 1999, his
  releases move lines worldwide (outside proof of beating the close). Not doing college football in 2026.
- Five studies planned: (1) claimed vs graded records, (2) beat the close, (3) do max plays win more, (4) do hot
  cappers stay hot, (5) what the real ones do that we don't (spreads, play-by-play model, early timing, star sizing).
  Data: public pages only (SuperContest / Circa contest picks, dated expert picks) - no logins, no tricks.
- Compare: our engine's early NFL spread read (3.5+ pts off the Tuesday number) covered 58.5% on 554 (findings 10/1)
  - Dr. Bob-level, but a study, not live; build the early NFL spread play and track it live vs his 57.6%.

**Open decisions (the owner's call)**
- "No forced locks": a Lock of the Day only when the read really beats the price, else "No Lock today" (CLAUDE.md
  still says ALWAYS a Lock until the owner says the words). The Dog stays real-value only; leans fill to 5+ picks.
- Card labels showing the edge size in words ("BIG EDGE - 3 UNITS" / "SMALL EDGE - ½ UNIT").

**Next builds**
- Stars beyond QB/goalie (NFL lead rusher / receiver, NBA top scorers) - verified from box scores only.
- Re-check the NHL elimination-dog finding before April; college hoops dog fix before November.
- Hockey: the engine has no real edge there yet (-2% on 1,851) - hockey dogs leave the Dog of the Day if the replay
  says they lose.
