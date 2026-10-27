"""10/27 daily run - 5 NHL / NBA studies. Train 2016-24, HOLDOUT 2025, current 2026. Flat 1u at the closing ML (ATS
shown in the report's rows for hoops only via the robust file). Every feature from EARLIER games only (the team's own
schedule + results this season; the closing total is today's posted number).
S6 NHL THE TOTAL'S SIZE: the closing total 6.5+ / 5.5 or less - dogs / favorites by band.
S7 NHL UPSET HANGOVER: the team won its last game as a +150 or longer dog - next game (the college hangover fade is built;
   the NBA version is a tracker lead) - and the team that LOST its last game as a -150 or shorter favorite.
S8 NHL IN-SEASON REMATCH: today's opponent beat us earlier this season by 3+ goals (or we beat them by 3+).
S9 NBA BLOWN HALFTIME LEAD: led by 10+ at the half last game and LOST - next game; and the mirror (trailed by 10+ at
   the half and WON - the comeback team).
S10 NBA WIN STREAKS: a favorite on a 5+ game win streak, a dog on a 4+ game win streak, a favorite facing a dog on a
    5+ game losing streak - the hot / cold the market may chase."""
from common import *  # noqa: F401,F403
CELLS = []


def cell(rows, f, name, train, hold):
    r = report(rows, f, name, train, hold)
    tr = [x for x in r if x["season"] in train]
    ho = [x for x in r if x["season"] in hold]
    if tr and ho:
        CELLS.append((name, len(tr), sum(x["roi"] for x in tr) / len(tr), len(ho), sum(x["roi"] for x in ho) / len(ho)))


def last_meet(prev, team, opp, s):
    for p in reversed(prev):
        if season(p["start"]) != s:
            return None
        if {p["home"], p["away"]} == {team, opp}:
            ps = "home" if p["home"] == team else "away"
            os_ = "away" if ps == "home" else "home"
            return float(p[f"{ps}_score"]) - float(p[f"{os_}_score"])
    return None


def feat(g, side, prev, s):
    t = g[side]
    o = g["away" if side == "home" else "home"]
    cur = [p for p in prev if season(p["start"]) == s]
    L = cur[-1] if cur else None
    d = dict(gp=len(cur), total=None, meet=last_meet(prev, t, o, s), l_won=None, l_ml=None, l_half=None, streak=0)
    try:
        d["total"] = float(g.get("total")) if g.get("total") not in ("", None) else None
    except ValueError:
        pass
    if L:
        ps = "home" if L["home"] == t else "away"
        os_ = "away" if ps == "home" else "home"
        d["l_won"] = float(L[f"{ps}_score"]) > float(L[f"{os_}_score"])
        try:
            d["l_ml"] = float(L.get(f"ml_{ps}")) if L.get(f"ml_{ps}") not in ("", None) else None
        except ValueError:
            pass
        try:
            a = [int(float(v)) for v in str(L.get(f"ls_{ps}") or "").split(",")][:2]
            b = [int(float(v)) for v in str(L.get(f"ls_{os_}") or "").split(",")][:2]
            d["l_half"] = sum(a) - sum(b) if len(a) == 2 and len(b) == 2 else None
        except ValueError:
            pass
        k = 0
        for p in reversed(cur):
            ps = "home" if p["home"] == t else "away"
            os_ = "away" if ps == "home" else "home"
            w = float(p[f"{ps}_score"]) > float(p[f"{os_}_score"])
            if k == 0:
                k = 1 if w else -1
            elif (k > 0) == w:
                k += 1 if w else -1
            else:
                break
        d["streak"] = k
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
print("\n#### S6 NHL THE TOTAL'S SIZE")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["total"] is not None and x["total"] >= 6.5, f"S6 NHL total 6.5+ - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["total"] is not None and x["total"] <= 5.5, f"S6 NHL total 5.5 or less - {bn}", TR, HO)
print("\n#### S7 NHL UPSET HANGOVER")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["l_won"] and x["l_ml"] is not None and x["l_ml"] >= 150 and x["gp"] >= 3,
         f"S7 NHL won last as a +150+ dog - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["l_won"] is False and x["l_ml"] is not None and x["l_ml"] <= -150 and x["gp"] >= 3,
         f"S7 NHL lost last as a -150+ favorite - {bn}", TR, HO)
print("\n#### S8 NHL IN-SEASON REMATCH")
for bn, b in BANDS:
    cell(NHL, lambda x, b=b: b(x) and x["meet"] is not None and x["meet"] <= -3, f"S8 NHL lost the last meeting by 3+ - {bn}", TR, HO)
    cell(NHL, lambda x, b=b: b(x) and x["meet"] is not None and x["meet"] >= 3, f"S8 NHL won the last meeting by 3+ - {bn}", TR, HO)

# ---------------- NBA ----------------
fin, sched = load("nba")
NBA = sides(fin, sched, feat)
print("\nNBA rows", len(NBA))
for bn, b in BANDS:
    report(NBA, b, f"NBA BASE {bn}", TR, HO)
print("\n#### S9 NBA BLOWN HALFTIME LEAD")
for bn, b in BANDS:
    f1 = lambda x, b=b: b(x) and x["l_half"] is not None and x["l_half"] >= 10 and x["l_won"] is False and x["gp"] >= 3   # noqa: E731
    cell(NBA, f1, f"S9 NBA blew a 10+ halftime lead last game - {bn}", TR, HO)
    ats(NBA, f1, f"S9 NBA blew a 10+ halftime lead last game - {bn}")
    f2 = lambda x, b=b: b(x) and x["l_half"] is not None and x["l_half"] <= -10 and x["l_won"] and x["gp"] >= 3   # noqa: E731
    cell(NBA, f2, f"S9 NBA came back from 10+ down at the half - {bn}", TR, HO)
    ats(NBA, f2, f"S9 NBA came back from 10+ down at the half - {bn}")
print("\n#### S10 NBA WIN STREAKS")
for nm, f in [("S10 NBA fav -100..-150 on a 5+ win streak", lambda x: fav(x) and x["streak"] >= 5),
              ("S10 NBA fav -151..-400 on a 5+ win streak", lambda x: bigf(x) and x["streak"] >= 5),
              ("S10 NBA dog on a 4+ win streak", lambda x: dog(x) and x["streak"] >= 4),
              ("S10 NBA fav vs a dog on a 5+ losing streak", lambda x: (fav(x) or bigf(x)) and x["o_streak"] <= -5),
              ("S10 NBA dog on a 5+ skid vs a team on a 3+ win streak", lambda x: dog(x) and x["streak"] <= -5 and x["o_streak"] >= 3),
              ("S10 NBA ROAD fav -100..-150 on a 5+ win streak", lambda x: fav(x) and x["streak"] >= 5 and not x["home"])]:
    cell(NBA, f, nm, TR, HO)
    ats(NBA, f, nm)

print(f"\nprimary cells {len(CELLS)}")
for c in CELLS:
    if c[1] >= 40 and ((c[2] > 0.03 and c[4] > 0) or (c[2] < -0.05 and c[4] < 0)):
        print("BOTH HALVES SAME SIGN:", c[0], f"train {c[1]}/{c[2]:+.1%} hold {c[3]}/{c[4]:+.1%}")
