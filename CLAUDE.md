# D503 Sports Engine: the owner's standing rules

A picks-only sports dashboard (GitHub Pages) for the owner and his friends. These rules come from the owner and hold in
every session:

- **Picks only. Never change a posted pick** without the owner's explicit OK.
- **Everything in his lingo** (`sports_owner_lingo.py`). Never repetitive across the board or day to day, never robotic,
  no marketing tone. Plain words ("goalie", not "G"), no confusing sayings. Never "real talk" or "chalk" (see `NEVER`).
- **When the owner uses new slang in chat, add it to `sports_owner_lingo.py` and into the write-up pools where it fits.**
  Use it the way he does ("that's just facts" after a claim, never after a number).
- **Never lengthen write-ups.** Accuracy over everything. No secrets in the repo. No borrowed keys or disguises to get
  past a site's blocks.
- Leans keep their OWN record (9/30: no units on leans, so not in ours - they counted 9/29-9/30). Live plus money and tennis keep their own records. The -150 rule stays.
- Monday and Thursday football: every NFL game those days gets its own pick (two games = two picks; a lean is fine) -
  sports.night_games / night_pick, the 🏈 NIGHT FOOTBALL card.
- No puck lines or run lines on the board (hockey / baseball = moneylines). Football and basketball spreads are fine.
- Every day: a Lock of the Day, a Dog of the Day, and a 2-, 3- and 4-leg parlay. Parlay legs: the 56%+ picks
  first (sports.PARLAY_LEG_MIN_P), then the surest plays 52%+ fill the rest (PARLAY_FILL_MIN_P) - never past -150,
  never a leg the engine's own read is fighting. The Dog of the Day: a proven dog first, else the dog the analysis
  likes best (sports.dog_score). Value (plus money that really beats the price) is the goal. Judge a sport on
  thousands of games (sports_strength), never a few nights. Analyze and weigh, no rigid rules.
- The main board and tennis post at 8 AM PT on game day. iPhone and Android look the same.
- The Lock of the Day always sits on top of the day's board, right under Live Plus Money - except on game day the
  🎯 WE GOT IN EARLY box (our early value plays playing today) goes just above it (the owner, 9/30). An early play is
  never posted on its own game day. There's always a Lock. It is
  never just the biggest favorite closest to -150 ("any moron could do that"): the engine's OWN read has to say it's
  worth its price, then the best proven win % (sports.own_agrees; tested 1,808 days, 58.1% vs 56.8%).
- A graded card stays on the board with its grade and review for 3 hours, then it's in the results only; once the
  day's cards are gone the 8 AM note shows. TONIGHT'S LIVE BETS shows only live bets still going: the second one's graded it clears into the results (its sport, with its review).
- The only automatic phone notifications are Live Plus Money bets (no pings for new picks or early value plays) - plus
  the one Patty-vs-the-Algorithm result ping (sports_challenge.final_words) and one-time announcements the owner asks
  for (announce.yml). One alert never rings twice (sw.js: renotify only without an id; a renewed sign-up drops the old).
- Units (the engine decides, by its edge - quarter-Kelly, ½u-10u; 1 unit = 1% of our bankroll, $1,000 start): early
  value plays and locks by the engine's own read, the Dog / value plays by its read vs the price. Leans keep their
  STRONG / SLIGHT label but carry no units ("NO UNITS — JUST A LEAN"); parlays carry none (each pick in it has its own);
  live plus money says "NO UNITS ON THESE — WE GAMBLIN'"; tennis none. Cards show units only, no $.
- A win % only shows on the dashboard when it's over 55% (sports_dashboard.pct_ok) - under that, words say it.
- No dull gray anywhere: text is solid, bold white; accents stay in color (yellow times, red LIVE).
- Fix bugs so they don't come back: every fix gets a regression test in `sports_test.py`
  (`timeout 900 python sports_test.py`, all green before any push).
- Once the owner OKs something, publish it without asking again. Show a preview for new visual changes.
- Commit to main and to the `claude/...` branch; don't open a PR unless asked.
- What the studies found (built, not built yet, dead ends): `SPORTS_FINDINGS.md` - read it first, add to it.
