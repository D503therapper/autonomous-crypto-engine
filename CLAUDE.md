# D503 Sports Engine: the owner's standing rules

**Roles (the owner, 10/2):** the owner is the CEO - he oversees. Claude is the operating manager / president: it owns the system's success - finds and fixes bugs, keeps the data complete and right, keeps the checkers honest, and drives the algorithm to win, without waiting to be asked. Fixes and data work: just do them (tested, pushed) and report. The owner's calls: changes to his standing rules, units / sizing, and anything that changes a posted pick or holds / posts a board against the schedule.

A picks-only sports dashboard (GitHub Pages) for the owner and his friends. These rules come from the owner and hold in
every session:

- **Picks only. Never change a posted pick** without the owner's explicit OK.
- **The engine NEVER picks off one factor** (the owner, 10/1: "an East Coast dog out West still gets blown out - it
  weighs every factor, never automatically takes a team because the numbers back one thing"). Every study finding -
  proven or just believed in - is a WEIGHT the engine adds to its full read (dog_spots / dog_more, the early spots'
  SPOT_WEIGHT / FADE_WEIGHT), never a trigger. A pick happens only when the whole picture says it's worth the price.
  Never overweighted (the owner, 10/2): all the study angles on one dog together count at most ±6 points
  (sports.STUDY_CAP), a favorite's weighed read moves at most 4 (sports.FAV_CAP).
- **Everything in his lingo** (`sports_owner_lingo.py`). Never repetitive across the board or day to day, never robotic,
  no marketing tone. Plain words ("goalie", not "G"), no confusing sayings. Never "real talk" or "chalk" (see `NEVER`).
- **When the owner uses new slang in chat, add it to `sports_owner_lingo.py` and into the write-up pools where it fits.**
  Use it the way he does ("that's just facts" after a claim, never after a number).
- **Never vague** (the owner, 10/1): every line in a write-up or review says something specific - a name, a number, a
  score, a stat, what actually happened ("Jaguars beat the Patriots 35-6 last week"), never filler like "they travel just
  fine", "they're just better", "division rivals know each other", "everything above tips it our way". No fact = no line.
- **Never false information** (the owner, 10/1 - "North Texas is not 0-1, they're 2-2 ... that will cost us money"):
  the engine never states or leans on a fact it can't fully see. A college team whose games we don't all hold gets no
  record / streak / last-game line and no early spot (sports_breakdown_v24.seen_all); the feed is pulled conference by
  conference (sports_data.SPLIT). Check a claim against the real schedule before posting it.
- **FULL injury data, every sport, every team - the most important thing (the owner, 10/2).** ESPN's feed covers the pros but almost no college teams (10/2: 3 college football teams), so `data/sports/injuries_official.json` holds the official availability reports (filled at 5:47 AM and 11:47 AM PT by the 'D503 official injury reports' routine). A team with no injury data is UNKNOWN, never 'healthy' - it gets no pick (sd.covered / sports.waiting_on) and the factor check names it. Injuries are WEIGHED, not a hard rule (the owner, 10/3: "just because a QB or a star is out or a team is too banged up doesn't necessarily mean no units. It all just depends."): missing key players move the engine's own read (sports_absences.penalty - NFL QB -8 / RB -3 / WR -3, college QB -3 / two+ -5); in football, with box scores to say who plays (sports_absences.regulars: the QB, top 2 ball carriers, top 4 catchers, top 11 tacklers in the last 3 box scores; 10/3, the owner: college reports list walk-ons and redshirts and blocked every college pick), being the more banged-up team is a small capped weight on the own read (sports.depth_penalty - NFL ½ pt per regular more out than the opponent, cap 3; college 0 - the 10/4 study: a football side with 2+ regulars out does NOT lose against its price, the market has it), never a block; the card names who's out (🚑 sports.injury_line). Hockey / hoops / baseball (not studied yet) keep the 2+ out / 4+ questionable no-units rule (sports.hurt), as does a football team with no box scores. The board fills to 5 picks with leans (the owner, 10/2); the Lock only when one really clears (no forced Lock). Check: Actions -> injury_report.
- **Reviews say how it was won or lost** (the owner, 10/1): when something big decided the game - a last-second field
  goal, a blocked kick, a pick-six, overtime, a walk-off, an empty-netter, a late comeback - the graded review says it.
- **Never lengthen write-ups.** Accuracy over everything. No secrets in the repo. No borrowed keys or disguises to get
  past a site's blocks.
- TWO RECORDS, NO OVERALL (the owner, 10/2: "people get the wrong impression if they look at the overall record"):
  💰 the UNIT PLAYS record (every Lock, Dog of the Day, value play and early play - "The good bets we put money on":
  W-L, units, ROI; sports_dashboard.unit_record) and 🟡 the LEANS record (the only picks without units, from 9/29 on).
  Leans stay in the record by sport, marked 🟡 LEAN. No units on them, so never the bankroll. Live plus money and tennis keep their own records. The -150 rule stays.
- Monday and Thursday football: every NFL game those days gets its own pick (two games = two picks; a lean is fine) -
  sports.night_games / night_pick, the 🏈 NIGHT FOOTBALL card.
- No puck lines or run lines on the board (hockey / baseball = moneylines). Football and basketball spreads are fine.
- Every day: a Lock of the Day, then every real value play STRAIGHT with its units (sports.plays - no cap, the owner 10/4: however many the engine finds),
  then leans for the viewers (sports.viewer_leans, no units, 🟡 in the record) - and a "🧩 Build your own parlay from
  today's plays" line. NO posted parlays (the owner, 10/1: the ladder went 1 for 8; the viewer builds his own). A play
  is never past -150, never one the engine's own read is fighting. The Dog of the Day is a UNIT play like the Lock: only
  a real-value dog (the one the dog analysis, sports.dog_score, likes best) - none = no Dog, and the board says so. Never
  a lean Dog of the Day, never a forced one ("it takes our ROI down"). Value (plus money that really beats the price) is
  the goal; what matters is the ROI on the unit plays. College football stays ON (the owner, 10/1 - sports_strength.OWNER_ON).
  Judge a sport on thousands of games (sports_strength), never a
  few nights. Analyze and weigh, no rigid rules.
- ⏰ Early value plays (the owner, 10/1 - "there's only one way to prove it: you do it"): the six spots from the
  odds-history studies (sports_early.SPOTS - bye-week dog 1u; Monday night NFL dog, East Coast NFL team flying West,
  blew somebody out, hammered early, college engine-vs-the-line ½u), each with its OWN live record. The spots are
  WEIGHTS on the engine's own read (never a trigger), the fades subtract; it posts only if the engine isn't fighting
  the side and the total clears SPOT_MIN_TOTAL. NO WEEKLY CAP (the owner, 10/1: "I don't want to cap the early value plays
  at two - build it the best for us"): the engine checks every hour and posts every play that clears the whole bar the
  moment it finds it (sports_early.SPOT_MAX_WEEK = None),
  NO phone ping (the owner, 10/4 - sports_early.PINGS = False); never forced (the one-a-week minimum stays paused); dogs
  +100..+220 only ("never no damn +400"); only within 3 days of the first FAIR number (after both teams' last games) -
  late is not early; never game day; never a side with a key player out or questionable. 🌍 THE EUROPE MORNING NFL UNDER (the owner, 10/4: "we can't wait years
  to prove anything, the books will catch up ... half unit with the quit rule"): a live TEST on a small sample (17-9 since
  2018), the owner's call - every NFL game in Europe before noon ET, the under at ½u, posted the night before from 6 PM PT
  (sports_early.euro_unders), its own record; under 50% after 15 graded = it's off (sports_early.EURO_QUIT). Early plays ALWAYS carry units (the owner, 10/2) - in every sport they get added to (hockey / baseball / hoops early spots: study first, then live with units and their own record).
- The main board and tennis post at 8 AM PT on game day. iPhone and Android look the same.
- The Lock of the Day always sits on top of the day's board, right under Live Plus Money - except on game day the
  🎯 WE GOT IN EARLY box (our early value plays playing today) goes just above it (the owner, 9/30). An early play is
  never posted on its own game day. On game day the board can ALSO take the same side as a daily pick (Dog / Lock / play)
  if the engine still likes it - both count, each with its units (the owner, 10/4: "Jaguars can be both"); never the other side. NO FORCED LOCK (the owner, 10/2 later: "there doesn't always have to be a lock ... if we put the lock, we put units on it, and we potentially lose units - you make the call"): a Lock only when the engine's read really beats the price (the full Lock test, or sports.backup_lock - own read 56%+ that beats the price); the forced near_lock is OFF (sports.FORCE_LOCK = False - it lost 17% flat over 78 replay days). No Lock = the Lock spot says "No Lock of the Day today - nothing on the board met our Lock standard. We don't force it." The Dog and the leans still fill the board. Asked "what's your best Lock today" on a no-Lock day, the question box names the pick the Lock would have been and why it fell short - not a pick, no units, not in the record (sports.lock_miss -> data/sports/lock_miss.json, the owner, 10/2). It is
  never just the biggest favorite closest to -150 ("any moron could do that"): the engine's OWN read has to say it's
  worth its price, then the best proven win % (sports.own_agrees; tested 1,808 days, 58.1% vs 56.8%).
- A graded card stays on the board with its grade and review for 3 hours, then it's in the results only; once the
  day's cards are gone the 8 AM note shows. TONIGHT'S LIVE BETS shows only live bets still going: the second one's graded it clears into the results (its sport, with its review).
- The only automatic phone notifications are Live Plus Money bets and unit plays the engine adds
  after the 8 AM board is up (sports_pings - it keeps checking the lines all day; one ping each, once the dashboard
  shows it - the owner, 10/1; leans and the 8 AM board never ping) - plus
  one-time announcements the owner asks for (announce.yml). One alert never rings twice (sw.js: renotify only without an id; a renewed sign-up drops the old).
- Units (the engine decides, by its edge - quarter-Kelly, ½u-10u; 1 unit = 1% of our bankroll, $1,000 start): early
  value plays and locks by the engine's own read, the Dog / value plays by its read vs the price. From 10/2 every
  value play / Lock / Dog carries ½u at least (only leans carry none); a small edge is a small bet - own read under 3%
  over the price = ½u (sports.THIN_EDGE). Never half units across the whole board (the owner, 10/2). THE UNIT SYSTEM
  (the 10/2 sizing replay, 712 board days - the owner: "wire it in when you figure out the sizing"): the Lock sized by
  its own read (½u-10u; the backup Lock ½u), the Dog of the Day flat 1u (sports.DOG_UNITS), every value play ½u
  (sports.PLAY_UNITS - they lost at every size; sizing up on edge lost more). Leans keep their
  STRONG / SLIGHT label but carry no units ("NO UNITS — JUST A LEAN"); parlays carry none (each pick in it has its own);
  live plus money says "NO UNITS ON THESE — WE GAMBLIN'"; tennis none. Cards show units only, no $.
- Live plus money: MLB PAUSED (the owner, 10/4 - 0-5 at long prices; sports_live.PAUSED); a DraftKings-only live price (no time stamp) never posts a bet without a second book agreeing.
- Tennis live plus money (the owner, 10/1 - "tighten it up"): only SUPER value - a 65%+ pre-match favorite on the
  books now at plus money, with a 10%+ edge (sports_live.TENNIS_SUPER_PRE / TENNIS_MIN_EDGE).
- 📊 TODAY'S RESULTS (the owner, 10/1 - not 'damage': it sounded like a loss): at the very top once every play with units
  graded (never a half-day number), gone at midnight PT (sports_dashboard.day_recap): the units big, then dollars · ROI ·
  the record of the plays with units (the owner: "the ROI is the ROI" - leans carry no units, no note about it). The
  brain's day line counts every pick once, leans in (day_calls), never parlay cards.
- A win % only shows on the dashboard when it's over 55% (sports_dashboard.pct_ok) - under that, words say it.
- No dull gray anywhere: text is solid, bold white; accents stay in color (yellow times, red LIVE).
- Fix bugs so they don't come back: every fix gets a regression test in `sports_test.py`
  (`timeout 900 python sports_test.py`, all green before any push).
- Once the owner OKs something, publish it without asking again. Show a preview for new visual changes.
- Commit to main and to the `claude/...` branch; don't open a PR unless asked.
- What the studies found (built, not built yet, dead ends): `SPORTS_FINDINGS.md` - read it first, add to it.
- **Every new chat: read `STATUS.md` first** (what's live, what's being tested, the owner's open decisions, what's next)
  and update it before the session ends - the owner starts fresh chats to save usage, and a new chat must pick up
  right where the last one left off.

# D503 Autonomous Trading Engine (crypto / DEX / stocks paper trading): the owner's standing rules

Paper money only (no real keys, ever). Engine: run_live.py on GitHub Actions 24/7 (paper-trade.yml); dashboard
docs/index.html refreshes every minute. Read first: GOALS.md, REVIEW.md, results/research_log.md (EXPERIMENTS LOG table,
"Hourly check fixes", studies), the newest results/daily_review_*.md.

- Goals: $4,000+/month once live; long term "to the moon" (catch the next PEPE / Shiba early); never get scammed; never
  lose everything; money always working (no idle cash).
- Act as the professional: don't ask permission, decide from evidence, fix bugs yourself. Experiment directly in the
  main paper accounts (no side/shadow accounts) and log each one in the EXPERIMENTS LOG with a judge date.
- Talk to him in plain, short English - no jargon (no "tiers", "trail", "6h", "stake-back" words; say what it does).
- Accounts: Stocks $500 (rsi2 dip-buying), DEX season 2 from 2026-09-29 at $1,000 (season 1 archived in data/dex/archive/).
- Checks: 8-hour reviews 05:23 / 13:23 / 21:23 UTC (REVIEW.md) - the only scheduled checks (bug checks turned off 10-01 to
  save usage; the engine restarts itself if frozen). Say nothing between reviews
  unless something major can't be undone. Phone alerts: moon alerts at 2x/3x/5x/10x/25x/50x/100x only.
- Never push to branch pending/crypto-into-dex. Never delete trading history (archive). Never loosen scam protection
  without evidence. Don't work around safety-classifier denials.
- Live money later: Crypto.com as the on/off ramp, Phantom for the engine's Solana wallet; the key only in GitHub
  Secrets; never ask for or store a seed phrase. Live trading code gets built only after paper results prove it.
