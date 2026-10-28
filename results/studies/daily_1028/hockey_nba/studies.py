"""10/28 daily run - 6 NHL / NBA studies (the 10/27 harness). Train 2016-24 (closing ML from 2018), HOLDOUT 2025,
current 2026. Flat 1u at the closing ML; ATS on the same games for hoops (a second look, not independent). Every feature
from EARLIER games only (the team's own schedule + results this season).
S5 NHL THE GOALIE GOT SHELLED: allowed 6+ goals last game - bounce-back or a leaky team? (scoring 6+ was 10/19, dead)
S6 NHL THE LONG HOMESTAND: the 4th+ / 6th+ straight home game (the first road game after a homestand was 10/12, dead;
   the long ROAD trip was 10/9 + 10/22, dead) - comfortable at home, or stale?
S7 NHL SLOW STARTS: outscored in the 1st period in each of the last 3 games (football slow starters were 10/27)
S8 NBA SLOW STARTS: lost the 1st quarter in each of the last 3 games
S9 NBA THE HOT SHOOTING NIGHT: scored 15+ over its season average last game, 5+ games in (the 15+ UNDER dud was 10/26,
   priced) - does the market chase the hot night?
S10 NBA QUICK REMATCH: the same two teams met in the last 4 days (the two-game sets) - the loser of game one, the
    winner of game one (the NHL quick rematch was 10/10 and the home-and-home 10/26, both dead)."""
from common import *  # noqa: F401,F403
from datetime import timedelta  # noqa: F811
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


def first(p, side):
    try:
        return int(float(str(p.get(f"ls_{side}") or "").split(",")[0]))
    except ValueError:
        return None


def feat(g, side, prev, s):
    t = g[side]
    o = g["away" if side == "home" else "home"]
    cur = [p for p in prev if season(p["start"]) == s]
    d = dict(gp=len(cur), ga_last=None, gf_last=None, l_won=None, homes=0, p1_3=None, avg=None, rematch=None)
    if cur:
        L = cur[-1]
        ps, os_ = me(L, t)
        d["gf_last"], d["ga_last"] = float(L[f"{ps}_score"]), float(L[f"{os_}_score"])
        d["l_won"] = d["gf_last"] > d["ga_last"]
        if len(cur) >= 2:
            d["avg"] = sum(float(p[f"{me(p, t)[0]}_score"]) for p in cur[:-1]) / (len(cur) - 1)
        if (dt(g["start"]) - dt(L["start"])) <= timedelta(days=4) and {L["home"], L["away"]} == {t, o}:
            d["rematch"] = d["gf_last"] - d["ga_last"]
    if side == "home":                                      # straight home games INCLUDING today
        k = 1
        for p in reversed(cur):
            if p["home"] == t:
                k += 1
            else:
                break
        d["homes"] = k
    if len(cur) >= 3:
        diffs = []
        for p in cur[-3:]:
            ps, os_ = me(p, t)
            a, b = first(p, ps), first(p, os_)
            diffs.append(None if a is None or b is None else a - b)
        d["p1_3"] = None if None in diffs else diffs
    return d


dog = lambda x: 100 <= x["ml"] <= 350           # noqa: E731
fav = lambda x: -150 <= x["ml"] <= -100         # noqa: E731
bigf = lambda x: -400 <= x["ml"] < -150         # noqa: E731
BANDS = (("dog +100..+350", dog), ("fav -100..-150", fav), ("fav -151..-400", bigf))
TR = tuple(range(2016, 2025))
HO = (2025,)


def ats(rows, f, name):
    out = [name + " ATS"]
    for part, ss in (("TRAIN", TR), ("HOLD", HO), ("CUR", (2026,))):
        rs = [x for x in rows if f(x) and x["season"] in ss and x["ats"] is not None]
        if rs:
            w = sum(x["ats"] for x in rs)
            out.append(f"{part} {w}-{len(rs) - w} {w / len(rs) * 100:.1f}%")
    print("   " + " | ".join(out))


# ---------------- NHL ----------------
fin, sched = load("nhl")
NHL = sides(fin, sched, feat)
print("NHL rows", len(NHL))
for bn, b in BANDS:
    report(NHL, b, f"NHL BASE {bn}", TR, HO)
print("\n#### S5 NHL THE GOALIE GOT SHELLED (allowed 6+ last game)")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["ga_last"] is not None and x["ga_last"] >= 6, f"S5 NHL allowed 6+ last game - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["o_ga_last"] is not None and x["o_ga_last"] >= 6, f"S5 NHL OPPONENT allowed 6+ last game - {bn}", TR, HO)
print("\n#### S6 NHL THE LONG HOMESTAND (home team's straight home games, today included)")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["home"] and x["homes"] >= 4, f"S6 NHL 4th+ straight home game - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["home"] and x["homes"] >= 6, f"S6 NHL 6th+ straight home game - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and not x["home"] and x["o_homes"] >= 4, f"S6 NHL road team at a 4th+ straight home game - {bn}", TR, HO)
print("\n#### S7 NHL SLOW STARTS (outscored in the 1st period in each of the last 3)")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["p1_3"] is not None and max(x["p1_3"]) < 0, f"S7 NHL lost the 1st period 3 straight - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["p1_3"] is not None and min(x["p1_3"]) > 0, f"S7 NHL WON the 1st period 3 straight - {bn}", TR, HO)

# ---------------- NBA ----------------
fin, sched = load("nba")
NBA = sides(fin, sched, feat)
print("\nNBA rows", len(NBA))
for bn, b in BANDS:
    report(NBA, b, f"NBA BASE {bn}", TR, HO)
print("\n#### S8 NBA SLOW STARTS (lost the 1st quarter in each of the last 3)")
for bn, b in BANDS:
    f1 = lambda x, b=b: b(x) and x["p1_3"] is not None and max(x["p1_3"]) < 0   # noqa: E731
    cell(NBA, f1, f"S8 NBA lost the 1st quarter 3 straight - {bn}", TR, HO)
    ats(NBA, f1, f"S8 NBA lost the 1st quarter 3 straight - {bn}")
    f2 = lambda x, b=b: b(x) and x["p1_3"] is not None and min(x["p1_3"]) > 0   # noqa: E731
    cell(NBA, f2, f"S8 NBA WON the 1st quarter 3 straight - {bn}", TR, HO)
    ats(NBA, f2, f"S8 NBA WON the 1st quarter 3 straight - {bn}")
print("\n#### S9 NBA THE HOT SHOOTING NIGHT (scored 15+ over its season average last game, 5+ games in)")
for bn, b in BANDS:
    f1 = lambda x, b=b: b(x) and x["gp"] >= 5 and x["avg"] is not None and x["gf_last"] - x["avg"] >= 15   # noqa: E731
    cell(NBA, f1, f"S9 NBA scored 15+ over its average last game - {bn}", TR, HO)
    ats(NBA, f1, f"S9 NBA scored 15+ over its average last game - {bn}")
    f2 = lambda x, b=b: b(x) and x["o_gp"] >= 5 and x["o_avg"] is not None and x["o_gf_last"] - x["o_avg"] >= 15   # noqa: E731
    cell(NBA, f2, f"S9 NBA OPPONENT scored 15+ over its average last game - {bn}", TR, HO)
    ats(NBA, f2, f"S9 NBA OPPONENT scored 15+ over its average last game - {bn}")
print("\n#### S10 NBA QUICK REMATCH (same two teams met in the last 4 days)")
for bn, b in BANDS:
    f1 = lambda x, b=b: b(x) and x["rematch"] is not None and x["rematch"] < 0   # noqa: E731
    cell(NBA, f1, f"S10 NBA lost game one of the set - {bn}", TR, HO)
    ats(NBA, f1, f"S10 NBA lost game one of the set - {bn}")
    f2 = lambda x, b=b: b(x) and x["rematch"] is not None and x["rematch"] <= -15   # noqa: E731
    cell(NBA, f2, f"S10 NBA lost game one by 15+ - {bn}", TR, HO)
    ats(NBA, f2, f"S10 NBA lost game one by 15+ - {bn}")

print(f"\nprimary cells {len(CELLS)}")
for c in CELLS:
    if c[1] >= 40 and ((c[2] > 0.03 and c[4] > 0) or (c[2] < -0.05 and c[4] < 0)):
        print("BOTH HALVES SAME SIGN:", c[0], f"train {c[1]}/{c[2]:+.1%} hold {c[3]}/{c[4]:+.1%}")
