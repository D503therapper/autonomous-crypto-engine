"""STUDY 5 - HOME COURT BY VENUE: a true home floor vs a NEUTRAL floor, and the early-season tournament (Thanksgiving
week events: neutral floors Nov 18 - Dec 2) vs other neutral games. (a) How much the home floor is worth in points
(the home side's margin vs its spread - the market's home edge should leave it at 0), (b) the home / 'home-listed'
side's ATS and moneyline by venue x phase (opening week, games 1-5, Nov, Dec+), (c) on a neutral floor, the team
whose CAMPUS is closer (the event in its own state) - from the game file's state vs each team's home-game state.
Train 2018-22, held out 2023 / 24 / 25 apart."""
import lib
from collections import defaultdict, Counter

rows = [r for r in lib.annotate(lib.load())]
home_state = defaultdict(Counter)
for r in rows:
    if str(r["neutral"]) != "1" and r.get("state"):
        home_state[r["home"]][r["state"]] += 1
hs_of = {t: c.most_common(1)[0][0] for t, c in home_state.items() if c}
cells = defaultdict(lib.Cell)
mg = defaultdict(list)
for r in rows:
    s = r["season"]
    if s < 2018:
        continue
    sp = lib.fnum(r["spread_home"])
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except (TypeError, ValueError):
        mh = ma = None
    neutral = str(r["neutral"]) == "1"
    d = r["dt"]
    tg = neutral and ((d.month == 11 and d.day >= 18) or (d.month == 12 and d.day <= 2))
    venue = "neutral-Thanksgiving" if tg else ("neutral-other" if neutral else "true home")
    early = max(r["gn_home"], r["gn_away"]) <= 5
    ph = "opening week" if r["day_in_season"] <= 7 else ("games 1-5" if early else ("Nov" if d.month == 11 else "Dec+"))
    margin = r["hs"] - r["as_"]
    if sp is not None:
        mg[(venue, ph, "held" if s in lib.HELD else "train")].append(margin + sp)
        so = lib.fnum(r.get("spread_home_odds")) or -110.0
        ao = lib.fnum(r.get("spread_away_odds")) or -110.0
        if abs(so) < 100:
            so = ao = -110.0
        cells[f"HOME-listed ATS | {venue} | {ph}"].add(s, lib.ats_profit(margin + sp, so))
        cells[f"AWAY-listed ATS | {venue} | {ph}"].add(s, lib.ats_profit(-margin - sp, ao))
        if neutral and r.get("state"):
            near = [x for x in ("home", "away") if hs_of.get(r[x]) == r["state"]]
            if len(near) == 1:
                x = near[0]
                line = sp if x == "home" else -sp
                m = margin if x == "home" else -margin
                cells[f"NEUTRAL, the in-state team ATS | {'Thanksgiving' if tg else 'other'} | {'early' if early or d.month == 11 else 'Dec+'}"].add(
                    s, lib.ats_profit(m + line, -110.0))
                if mh is not None and abs(mh) >= 100 and abs(ma) >= 100:
                    o = mh if x == "home" else ma
                    if -400 <= o <= 350:
                        cells[f"NEUTRAL, the in-state team ML | {'Thanksgiving' if tg else 'other'} | {'early' if early or d.month == 11 else 'Dec+'}"].add(
                            s, lib.ml_profit(o, (margin > 0) == (x == "home")))
    if mh is not None and abs(mh) >= 100 and abs(ma) >= 100 and -400 <= mh <= 350:
        cells[f"HOME-listed ML -400..+350 | {venue} | {ph}"].add(s, lib.ml_profit(mh, margin > 0))
    if mh is not None and abs(mh) >= 100 and abs(ma) >= 100 and -400 <= ma <= 350:
        cells[f"AWAY-listed ML -400..+350 | {venue} | {ph}"].add(s, lib.ml_profit(ma, margin < 0))
print(__doc__)
print("(a) the home-listed side's margin + its spread (0 = the market prices the floor right):")
for k in sorted(mg):
    xs = mg[k]
    print(f"  {k[0]:21} {k[1]:13} {k[2]:5} n={len(xs):6} mean {sum(xs) / len(xs):+.2f}")
for k in sorted(cells):
    print(cells[k].line(k))
