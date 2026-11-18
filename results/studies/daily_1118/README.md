# 11/18 daily studies - ten new angles, nothing weighed, two tracker leads

The owner's daily routine: the board check, yesterday's picks, the lead tracker, then 10 NEW studies on the sports
in season. Every fact was known before the game (this season's finals before tonight, the line scores of games
already played). Prices: ESPN's close at its own juice (the game files), the paid football history's first FAIR look
(`tools/early_football_study.ready_at / fair`, no look-ahead), the paid NBA (2020-23) and NHL (2021-23) game-day
morning looks and ESPN's open (2023-26) as the second prices. Regular season only. Train = the seasons through 2021
(paid football 2020-22), each newer season held out apart, 2026 = now. Placebo = 2,000 random same-size sets from the
cell's own pool; the follow-ups use a PRICE-MATCHED placebo (drawn bin for bin from the same 50-cent price bins).
About 420 cells in all - about 20 would clear |z| 2 by luck and a couple |z| 3.

Files: `lib.py` / `h.py` (the 11/17 helpers, cache `~/.cache/d503_daily1118`), `s1_s10.py` (the ten studies),
`s_followups.py` (A-D), `s_followup_b2.py` (B2 - the NHL cheap-win dog against the built weights),
`lead_tracker.py`, `*_out.txt`.

| # | study | verdict |
|---|---|---|
| S1 | NHL: the OT-prone team (share of games past regulation, 10+ games) | DEAD - the 30%+ dog -6.7% on 1,130 vs -5.5% (placebo 1,272); both teams OT-prone -9.6% on 234; one-goal-game share no dose |
| S2 | The closing hold (overround) by the league-season's fifths - NBA / NHL / college hoops (+ football at the close) | DEAD (a pricing fact) - dogs in the tight fifth lose less in 4 of 5 leagues (NBA +0.6% vs -4.3%, placebo 129; college hoops -3.4% vs -6.6%) because the juice is smaller; college football flips (-11.1%); nothing past the vig |
| S3 | NBA / college hoops: the game after a 1-2 point game | NBA DEAD (dog off a 1-2 loss -10.6% on 264, placebo 415; fav off a 1-2 win -14.7% on 113). College hoops: the dog vs a favorite off a 1-2 point WIN -18.0% on 992 -> follow-up C -> a LEAD |
| S4 | NHL / NBA: the season games-played gap (games 10+) | DEAD - the NHL dog that has played 3+ more -15.1% on 545 is the back-to-back (on a b2b -41.0% on 138, rested -6.4% on 407 = the base); the dose is U-shaped (3+ fewer -13.5%); the paid morning +7.0% on 52 |
| S5 | NHL / NBA: the venue split (home / road record vs the overall) | DEAD - NBA home dog .200+ better at home +23.4% on 116 (placebo 27) and NBA road dog .200+ worse on the road -23.6% on 252 (placebo 11) - but the NBA road dog .200+ BETTER on the road is -29.5% too, and the NHL runs the other way (road dog .200+ worse +12.9% on 113) |
| S6 | Football (paid first fair look): the season's extreme price - the biggest dog / shortest favorite a team has been, the first time a dog | DEAD - the NFL dog at its biggest price by 30c+ +13.2% on 109 at the first fair (placebo 86) but -1.7% at the close; the first-time dog +3.0% on 40; college nothing |
| S7 | NBA / NHL / college hoops: the season's extreme price at the close | DEAD - the NHL dog at its biggest price by 30c+ -18.6% on 199 is the long price (price-matched placebo 414 of 2,000); NBA -14.6% on 203 (placebo 258) |
| S8 | College hoops: the in-state game, Nov-Dec, a true home floor | DEAD - the in-state home dog +3.8% on 363 (placebo 630); the in-state road favorite -23.2% on 168 vs -13.3% for every Nov-Dec road favorite (the built road-favorite fade already takes them); ATS -13.6% vs -10.9% |
| S9 | NHL / NBA: the pro letdown (the favorite off a win over a .650+ team) / the bounce (off a loss to a .350- team) | DEAD as asked (NBA fav off a big win -11.8% on 131, placebo 382; NHL fav off a loss to a bad team +6.5% on 172, placebo 155) - but the NHL DOG off a win over a .350- team -17.3% on 448 -> follow-ups B / B2 -> a LEAD (the residual) |
| S10 | Football: the shutout (shut out last game / pitched one) | DEAD - tiny cells (NFL 30-ish a cell; the college dog shut out last game +24.7% on 34) |

## The follow-ups (s_followups.py, s_followup_b2.py)
- **A - the NHL dog that played 3+ more games:** the back-to-back (above). Dead.
- **D - the NHL dog at its biggest price:** price-matched placebo 414 of 2,000. Dead.
- **C - the college hoops dog vs a favorite off a 1-2 point win:** -18.0% on 992 (train -10.8%, 3 of 4 seasons down / held -24.9%, 4 of 4 down), ESPN's open -27.9% on 330, ATS -6.6% vs -3.9%, price-matched placebo 4 of 2,000 - but NO dose (off a 3-5 win -4.1%, 6-10 -10.2%, 11+ -8.8%); the general split (any win -9.2% on 10,519 vs any loss -2.5% on 7,389) is what the dog slot already reads ("the favorite lost its last"); November +2.2% on 71 - it lives in December-March; the NBA twin +2.3%. **LEAD - tracker tag "college hoops dog vs a favorite off a 1-2 point win (lead)" from the 11/19 games, judge at 60.**
- **B / B2 - the NHL dog off a cheap win:** a clean dose by the beaten team's record (wins over .650+ -1.1%, .550-.650 -1.3%, .450-.550 -2.8%, .350-.450 -14.7%, .350- -17.3%; the mirror - a LOSS to a bad team - +2..+4%); off a win over a sub-.450 team -15.3% on 1,262 (train -15.3% / held -15.2%, 8 of 9 seasons down, price-matched placebo 7 of 2,000). **But the engine's built weights carry it:** with the hot dog (3+ win streak, -2), the dog on a back-to-back and the long dog (+220, -3) taken out it is -6.8% on 723 (z -1.6; ESPN's open -4.7% on 254; the paid morning -5.8% on 69) against +0.1% on 1,150 for the same dogs off a win over a .450+ team; the NBA (-2.5%) and college hoops (-7.8% vs -7.4% off any win) twins say nothing. **LEAD - tracker tag "NHL dog off a win over a sub-.450 team, rested, no 3+ streak, under +220 (lead)" from the 11/19 games (the residual), judge at 60: -10% or worse = the five checks as a -1 / -2 weight.**

## Five checks on the two leads
- C: fair YES (the close; ESPN's open agrees), blind YES (no model), seasons YES (7 of 8 down), this season NO (November +2.2%; 2026 +59.3% on a handful), second check NO (no dose; the NBA twin +2.3%).
- B2 residual: fair YES, blind YES, seasons PARTLY (2025 +17.7%), this season -35.0% on a handful, second check NO (z -1.6; the open / morning are weak; the NBA / college hoops twins nothing).

Nothing weighed; no sizing constant, gate or rule touched.
