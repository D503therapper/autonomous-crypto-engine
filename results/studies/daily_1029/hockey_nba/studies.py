"""10/29 daily run - 5 NHL / NBA studies (the 10/28 harness). Train 2016-24 (closing ML from 2018), HOLDOUT 2025,
current 2026. Flat 1u at the closing ML; ATS on the same games for hoops (a second look, not independent). Every feature
from EARLIER games only (the team's own schedule + results this season), or from tonight's closing board.
S6 NBA DOGS BY THE CLOSING TOTAL: a low total (fewer possessions = more variance) vs the season's median so far
   (NFL dogs by total were 10/15, college / NHL dogs by total 10/14 - the NBA was never run).
S7 NBA THE BOOK'S FIRST-HALF SHARE: the 1st-half spread / the full spread - the twin of football S1 (a cross-sport check).
S8 NBA THE BAD CLOSER: lost the 4th quarter in each of its last 3 (the 1st-quarter slow starters were 10/28) - and the
   team that won the 4th in each of its last 3.
S9 NHL THE 3RD-PERIOD TEAM: its 3rd-period goal difference over the last 5 games, +4 or better / -4 or worse
   (blown leads were 10/12, the 1st period 10/28).
S10 NHL THE TOTAL'S JUICE: the over juiced to -125 or more (the book leans goals) vs the under juiced -125 or more -
   does a high-event board help the dog? (dogs by the total number were 10/14, dead)."""
from common import *  # noqa: F401,F403
CELLS = []


def cell(rows, f, name, train, hold):
    r = report(rows, f, name, train, hold)
    tr = [x for x in r if x["season"] in train]
    ho = [x for x in r if x["season"] in hold]
    if tr and ho:
        CELLS.append((name, len(tr), sum(x["roi"] for x in tr) / len(tr), len(ho), sum(x["roi"] for x in ho) / len(ho)))


def me(p, t):
    ps = "home" if p["home"] == t else "away"
    return ps, ("away" if ps == "home" else "home")


def periods(p, side):
    try:
        return [int(float(v)) for v in str(p.get(f"ls_{side}") or "").split(",") if v != ""]
    except ValueError:
        return None


def ff(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


TOT = collections.defaultdict(list)       # (league, season) -> closing totals of EARLIER games (running median)


def make_feat(league):
    q = 3 if league == "nba" else 2           # index of the 4th quarter / the 3rd period

    def feat(g, side, prev, s):
        t = g[side]
        cur = [p for p in prev if season(p["start"]) == s]
        d = dict(gp=len(cur), late3=None, late5=None)
        lates = []
        for p in cur[-5:]:
            ps, os_ = me(p, t)
            a, b = periods(p, ps), periods(p, os_)
            if a and b and len(a) > q and len(b) > q:
                lates.append(a[q] - b[q])
            else:
                lates.append(None)
        if len(lates) >= 3 and None not in lates[-3:]:
            d["late3"] = lates[-3:]
        if len(lates) == 5 and None not in lates:
            d["late5"] = sum(lates)
        tot = ff(g.get("total"))
        sp = ff(g.get("spread_home")); h1 = ff(g.get("h1_spread_home"))
        d["tot"] = tot
        ts = sorted(TOT[(league, s)])
        d["tot_med"] = ts[len(ts) // 2] if len(ts) >= 60 else None
        d["pts"] = None if sp is None else (sp if side == "home" else -sp)
        d["h1"] = None if h1 is None else (h1 if side == "home" else -h1)
        d["over_odds"], d["under_odds"] = ff(g.get("over_odds")), ff(g.get("under_odds"))
        return d
    return feat


def build(league, start):
    fin, sched = load(league, start)
    feat = make_feat(league)
    rows = []
    # sides() walks games in order; feed the running total median as we go (a game's own total joins AFTER it)
    by_id = {}
    for g in fin:
        by_id[g["id"]] = g
    rs = []
    idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
    for g in fin:
        one = sides([g], {t: sched[t] for t in (g["home"], g["away"])}, feat) if g.get("ml_home") else []
        for r in one:
            r["gid"] = g["id"]
        rs.extend(one)
        tt = ff(g.get("total"))
        if tt is not None:
            TOT[(league, season(g["start"]))].append(tt)
    return rs


print("building ...", flush=True)
NBA = build("nba", "2016-09-01")
NHL = build("nhl", "2016-09-01")
TR = tuple(range(2016, 2025)); HO = (2025,)
dog = lambda x: 100 <= x["ml"] <= 350
favb = lambda x: -150 <= x["ml"] <= -101


def both(rows, f, name):
    cell(rows, lambda x: dog(x) and f(x), name + " - dog +100..+350", TR, HO)
    cell(rows, lambda x: favb(x) and f(x), name + " - fav -101..-150", TR, HO)


print("\nBASES"); both(NBA, lambda x: True, "NBA all"); both(NHL, lambda x: True, "NHL all")

print("\nS6 NBA DOGS BY THE CLOSING TOTAL (vs the season's running median, 60+ games in)")
rel = lambda x: None if x["tot"] is None or x["tot_med"] is None else x["tot"] - x["tot_med"]
both(NBA, lambda x: rel(x) is not None and rel(x) <= -8, "NBA total 8+ under the median")
both(NBA, lambda x: rel(x) is not None and -8 < rel(x) < 8, "NBA total within 8 of the median")
both(NBA, lambda x: rel(x) is not None and rel(x) >= 8, "NBA total 8+ over the median")
cell(NBA, lambda x: dog(x) and x["ml"] >= 200 and rel(x) is not None and rel(x) <= -8, "NBA dog +200..+350, total 8+ under the median", TR, HO)
cell(NBA, lambda x: dog(x) and x["ml"] >= 200 and rel(x) is not None, "  (base: NBA dog +200..+350, with a median)", TR, HO)

print("\nS7 NBA THE BOOK'S FIRST-HALF SHARE (1st-half spread / full spread, full spread 2.5+; the h1 line holds 2018-24 + 2026)")
shr = lambda x: None if x["h1"] is None or x["pts"] is None or abs(x["pts"]) < 2.5 else x["h1"] / x["pts"]
both(NBA, lambda x: shr(x) is not None and shr(x) < 0.45, "NBA share under 0.45")
both(NBA, lambda x: shr(x) is not None and 0.45 <= shr(x) < 0.60, "NBA share 0.45-0.60")
both(NBA, lambda x: shr(x) is not None and shr(x) >= 0.60, "NBA share 0.60+")
NBA_H1_HO = (2023,)        # the h1 line is thin in 2024-25 (5 games) - use the last full season as a second look
for nm, f_ in (("under 0.45", lambda s_: s_ < 0.45), ("0.60+", lambda s_: s_ >= 0.60)):
    cell(NBA, lambda x, f_=f_: dog(x) and shr(x) is not None and f_(shr(x)), f"NBA dog share {nm} (train 2018-22 / look 2023-24)",
         tuple(range(2016, 2023)), (2023, 2024))

print("\nS8 NBA THE BAD CLOSER / THE CLOSER (the 4th quarter, last 3 games)")
both(NBA, lambda x: x["late3"] is not None and max(x["late3"]) < 0, "NBA lost the 4th in each of its last 3")
both(NBA, lambda x: x["late3"] is not None and min(x["late3"]) > 0, "NBA won the 4th in each of its last 3")
both(NBA, lambda x: x["o_late3"] is not None and max(x["o_late3"]) < 0, "NBA OPPONENT lost the 4th in each of its last 3")

print("\nS9 NHL THE 3RD-PERIOD TEAM (3rd-period goal diff over the last 5)")
both(NHL, lambda x: x["late5"] is not None and x["late5"] >= 4, "NHL 3rd periods +4 or better, last 5")
both(NHL, lambda x: x["late5"] is not None and x["late5"] <= -4, "NHL 3rd periods -4 or worse, last 5")
both(NHL, lambda x: x["late5"] is not None and x["o_late5"] is not None and x["late5"] - x["o_late5"] >= 6,
     "NHL 3rd periods 6+ better than the opponent's, last 5")

print("\nS10 NHL THE TOTAL'S JUICE (the closing over / under price)")
both(NHL, lambda x: x["over_odds"] is not None and x["over_odds"] <= -125, "NHL over juiced -125 or more")
both(NHL, lambda x: x["under_odds"] is not None and x["under_odds"] <= -125, "NHL under juiced -125 or more")
both(NHL, lambda x: x["over_odds"] is not None and x["under_odds"] is not None and x["over_odds"] > -125 and x["under_odds"] > -125,
     "NHL total priced near even")
cell(NHL, lambda x: dog(x) and x["tot"] == 5.5 and x["over_odds"] is not None and x["over_odds"] <= -125,
     "NHL dog, total 5.5 with the over -125+ (a 6 in disguise)", TR, HO)
cell(NHL, lambda x: dog(x) and x["tot"] == 6.5 and x["under_odds"] is not None and x["under_odds"] <= -125,
     "NHL dog, total 6.5 with the under -125+ (a 6 in disguise)", TR, HO)

print(f"\nprimary cells {len(CELLS)}")
for c in CELLS:
    if c[1] >= 100 and c[2] > 0.02 and c[4] > 0:
        print(f"SURVIVOR train {c[1]} {c[2]:+.1%} / hold {c[3]} {c[4]:+.1%}: {c[0]}")
    if c[1] >= 100 and c[2] < -0.06 and c[4] < 0:
        print(f"FADE train {c[1]} {c[2]:+.1%} / hold {c[3]} {c[4]:+.1%}: {c[0]}")
