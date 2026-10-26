"""NBA, 2 studies (10/26). Train 2016-24, HOLDOUT 2025, current 2026. Flat 1u at the closing ML; ATS shown too.
S9 EARLY TIP: games that start before 5 PM ET (weekend matinees / holiday games) vs the normal evening tip - home / road,
   dogs / favorites, and the road team on its body clock (a West team tipping before 5 PM ET in the East).
S10 THE GAME AFTER A DUD ON OFFENSE: scored 15+ under its own season average (before that game) last time out, 10+
    games in - the team the market may sell too hard, and the team facing it. Schedule + results of EARLIER games only."""
from zoneinfo import ZoneInfo
from datetime import timezone
from common import *  # noqa: F401,F403
WEST = {"Lakers", "Clippers", "Warriors", "Kings", "Suns", "Trail Blazers", "Jazz", "Nuggets", "Thunder", "Timberwolves",
        "Mavericks", "Rockets", "Spurs", "Grizzlies", "Pelicans"}
ET = ZoneInfo("America/New_York")
fin, sched = load("nba")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)


def feat(g, side, prev, s):
    t = g[side]
    prev = [p for p in prev if season(p["start"]) == s]
    pts = []
    for p in prev:
        ps = "home" if p["home"] == t else "away"
        pts.append(float(p[f"{ps}_score"]))
    dud = None
    if len(pts) >= 11:
        avg = sum(pts[:-1]) / len(pts[:-1])
        dud = pts[-1] - avg
    et = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(ET)
    return dict(west=g[f"{side}_name"] in WEST, et_hour=et.hour + et.minute / 60, dow=et.weekday(), dud=dud, gp=len(pts))


rows = sides(fin, sched, feat)
R = lambda f, n: report(rows, f, n, TR, HO, CU)


def A(f, n):
    out = [n + " ATS"]
    for part, ss in (("TRAIN", TR), ("HOLD", HO), ("CUR", CU)):
        rs = [x for x in rows if f(x) and x["season"] in ss and x["ats"] is not None]
        if rs:
            w = sum(x["ats"] for x in rs)
            out.append(f"{part} {w}-{len(rs) - w} {w / len(rs) * 100:.1f}% ROI {(w * 100 / 110 - (len(rs) - w)) / len(rs) * 100:+.1f}%")
    print("   " + " | ".join(out))


dog = lambda x: 100 <= x["ml"] <= 350; fav = lambda x: -150 <= x["ml"] <= -100; bigf = lambda x: -400 <= x["ml"] < -150
early = lambda x: x["et_hour"] < 17
print("rows", len(rows), "early-tip sides", sum(1 for x in rows if early(x)))
print("\n#### baselines"); R(dog, "BASE dog +100..+350"); R(fav, "BASE fav -150..-100"); R(bigf, "BASE fav -151..-400")
print("\n#### S9 EARLY TIP (before 5 PM ET)  [8 cells]")
for nm, f in [("early tip HOME dog", lambda x: early(x) and dog(x) and x["home"]), ("early tip ROAD dog", lambda x: early(x) and dog(x) and not x["home"]),
              ("early tip HOME fav -150..-100", lambda x: early(x) and fav(x) and x["home"]),
              ("early tip ROAD fav -150..-100", lambda x: early(x) and fav(x) and not x["home"]),
              ("early tip HOME fav -151..-400", lambda x: early(x) and bigf(x) and x["home"]),
              ("early tip ROAD fav -151..-400", lambda x: early(x) and bigf(x) and not x["home"]),
              ("early tip, West team on the road in the East - dog", lambda x: early(x) and dog(x) and not x["home"] and x["west"] and not x["o_west"]),
              ("early tip, West team on the road in the East - fav", lambda x: early(x) and (fav(x) or bigf(x)) and not x["home"] and x["west"] and not x["o_west"])]:
    R(f, "S9 " + nm); A(f, "S9 " + nm)
R(lambda x: not early(x) and dog(x) and not x["home"], "S9 control: evening ROAD dog")
print("\n#### S10 AFTER A DUD ON OFFENSE (15+ under its season average last game, 10+ games in)  [8 cells]")
d15 = lambda x: x["dud"] is not None and x["dud"] <= -15
d20 = lambda x: x["dud"] is not None and x["dud"] <= -20
od15 = lambda x: x["o_dud"] is not None and x["o_dud"] <= -15
for nm, f in [("dud 15+ - dog", lambda x: d15(x) and dog(x)), ("dud 15+ - fav -150..-100", lambda x: d15(x) and fav(x)),
              ("dud 15+ - fav -151..-400", lambda x: d15(x) and bigf(x)), ("dud 20+ - dog", lambda x: d20(x) and dog(x)),
              ("dud 20+ - fav -150..-400", lambda x: d20(x) and (fav(x) or bigf(x))),
              ("dud 15+ HOME dog", lambda x: d15(x) and dog(x) and x["home"]),
              ("FACING a dud-15 team - dog", lambda x: od15(x) and dog(x)), ("FACING a dud-15 team - fav -150..-400", lambda x: od15(x) and (fav(x) or bigf(x)))]:
    R(f, "S10 " + nm); A(f, "S10 " + nm)
