"""S6. NBA SPREADS - the schedule against the CLOSING spread (game files 2016-26, the spread at its own juice), then
the same spots at the day-before OPEN and the game-morning number (the paid history, 2020-23, -110), and the star's
night off (box scores: the team's minutes leader - 10+ team games, in 60%+ of them - not in tonight's box).
Not re-run: the engine's own margin vs the close (11/11 B3: -5.6% on 4,630), a box-score number vs the close (B2 / S8),
the moneyline rest cells (10/22, 11/2), the 3P-luck fade (11/10).  TRAIN = seasons to 2021, HELD = 2022-26.
   python s6_nba.py"""
import importlib.util, os
from collections import defaultdict
import lib2 as L

o = L.Out("s6")
B = L.B
FIN = [g for g in B.finals("nba") if g["sp"] is not None and g["stype"] == "2"]
ALL = B.all_finals("nba")
TL = B.team_log(ALL)
CO = B.coords("nba")
SPLIT = 2021


def hrs(a, b):
    return B.days_between(a, b) * 24


def sched(team, g):
    """rest facts for `team` going into game g: days since the last game, b2b, 3-in-4, 4-in-6, miles from the last
    game's floor, road-trip game number."""
    prev = B.before(TL, team, g["start"], 6)
    if not prev or prev[-1]["season"] != g["season"]:
        return None
    gaps = [hrs(p["start"], g["start"]) for p in prev]
    b2b = gaps[-1] <= 30
    n4 = sum(1 for x in gaps if x <= 78)          # games in the 3 nights before tonight
    n6 = sum(1 for x in gaps if x <= 126)
    a, b = CO.get(prev[-1]["id"]), CO.get(g["id"])
    mi = B.miles(a, b) if a and b else None
    trip = 0
    for p in reversed(prev):
        if p["away"] == team:
            trip += 1
        else:
            break
    return {"days": gaps[-1] / 24, "b2b": b2b, "t34": n4 >= 2, "f46": n6 >= 3, "miles": mi, "trip": trip,
            "last_home": prev[-1]["home"] == team}


def ats(g, side):
    return B.ats(g, side) or 0.0


T = defaultdict(list)
ROWS = []
for g in FIN:
    sh, sa = sched(g["home"], g), sched(g["away"], g)
    if not sh or not sa:
        continue
    for side, me, op in (("home", sh, sa), ("away", sa, sh)):
        p = B.ats(g, side)
        if p is None:
            continue
        s = g["season"]
        line = g["sp"] if side == "home" else -g["sp"]
        home = side == "home"
        ROWS.append((g, side, me, op, p))

        def add(k):
            T[k].append((s, p))
        add("base: every side")
        if me["b2b"] and not op["b2b"]:
            add("on a back-to-back vs a team that isn't")
            add("   ... at home" if home else "   ... on the road")
            add("   ... as a dog" if line > 0 else "   ... as a favorite")
            if op["days"] >= 2.5:
                add("   ... vs a team with 2+ days off")
            if me["miles"] is not None and me["miles"] >= 500:
                add("   ... after flying 500+ miles overnight")
            if me["t34"]:
                add("   ... and it's the 3rd game in 4 nights")
        if not me["b2b"] and op["b2b"]:
            add("RESTED vs a team on a back-to-back")
            if line < 0:
                add("   rested FAVORITE vs a b2b team")
            if line > 0:
                add("   rested DOG vs a b2b team")
            if home:
                add("   rested HOME team vs a b2b visitor")
        if me["b2b"] and op["b2b"]:
            add("both on a back-to-back: the home side" if home else "both on a back-to-back: the road side")
        if me["t34"] and not op["t34"] and not me["b2b"]:
            add("3rd game in 4 nights (not a b2b) vs a team that isn't")
        if me["f46"] and not op["f46"]:
            add("4th game in 6 nights vs a team that isn't")
        if me["days"] >= 3.5 and op["days"] < 2.5:
            add("3+ days off vs a team with 1 or fewer (rust or rest?)")
        if me["days"] - op["days"] >= 1.5 and not op["b2b"]:
            add("2+ more days of rest, the other side not on a b2b")
        if me["miles"] is not None and me["miles"] >= 1500:
            add("flew 1,500+ miles since its last game")
            if not home:
                add("   ... and on the road tonight")
        if home and me["trip"] >= 4:
            add("first home game after a 4+ game road trip")
        if not home and me["trip"] >= 4:
            add("road game 5+ of a trip")
        if home and me["last_home"] and me["days"] <= 1.3 and not op["b2b"]:
            add("home-home back-to-back vs a rested visitor")

o(f"== A. NBA schedule spots vs the CLOSING spread ({len(FIN)} regular-season games 2016-26; train to {SPLIT}, held 2022-26) ==")
for k in sorted(T, key=lambda k: (k.startswith("   "), k)) if False else list(T):
    r = T[k]
    tr = [(s, p) for s, p in r if s <= SPLIT]
    he = [(s, p) for s, p in r if s > SPLIT]
    ut, uh = L.by_season(tr), L.by_season(he)
    o(f"   {k[:56]:56s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% ({ut[0]}/{ut[1]}) | HELD {L.st([p for _, p in he])} ({uh[0]}/{uh[1]} up: {uh[2]})")
o(f"   cells: {len(T)}")

# ---------------- B. the open / the morning (paid history 2020-23) ----------------
spec = importlib.util.spec_from_file_location("nbaodds", os.path.join(L.ROOT, "results/studies/nba_odds_1102/lib.py"))
m = importlib.util.module_from_spec(spec)
here = os.getcwd()
spec.loader.exec_module(m)
os.chdir(here)
m.OUT = B.CACHE
games = m.load_games()
lk = m.looks(games)
prev = m.prev_tips(games)
o("\n== B. THE SAME SPOTS AT THE DAY-BEFORE OPEN / THE GAME MORNING / THE CLOSE (paid history 2020-23, -110 at the open and the morning) ==")
P110 = L.dec(-110) - 1
TB = defaultdict(lambda: {"open": [], "morn": [], "close": [], "mv": []})
for g, side, me, op, p in ROWS:
    sop, smo = m.sp_looks(lk, prev, g["id"])
    if not sop or not smo or sop.get("pt") is None or smo.get("pt") is None:
        continue
    mg = g["hs"] - g["as"]

    def bet(pt):
        r = (mg + pt) if side == "home" else -(mg + pt)
        return 0.0 if r == 0 else (P110 if r > 0 else -1.0)
    gain = (sop["pt"] - g["sp"]) if side == "home" else (g["sp"] - sop["pt"])       # points the open gave over the close
    ks = ["every side"]
    if me["b2b"] and not op["b2b"]:
        ks.append("on a back-to-back vs a team that isn't")
    if not me["b2b"] and op["b2b"]:
        ks.append("RESTED vs a team on a back-to-back")
    line = sop["pt"] if side == "home" else -sop["pt"]
    ks.append("dog at the open" if line > 0 else "favorite at the open")
    if side == "home":
        ks.append("home side")
    if me["miles"] is not None and me["miles"] >= 1500:
        ks.append("flew 1,500+ miles since its last game")
    for k in ks:
        TB[k]["open"].append(bet(sop["pt"]))
        TB[k]["morn"].append(bet(smo["pt"]))
        TB[k]["close"].append(p)
        TB[k]["mv"].append(gain)
for k, v in TB.items():
    o(f"   {k[:44]:44s} n {len(v['open']):5d} | the open {L.roi(v['open']):+5.1f}% | the morning {L.roi(v['morn']):+5.1f}% | the close {L.roi(v['close']):+5.1f}% | the open beat the close by {sum(v['mv']) / len(v['mv']):+.2f} pts")

# ---------------- C. the star's night off ----------------
o("\n== C. THE MINUTES LEADER NOT IN TONIGHT'S BOX (10+ team games, he played 60%+ of them, 28+ minutes a game) - the closing spread ==")
BOX = B.box_rows("nba")


def mins(r):
    v = B.num((r["st"] or {}).get("minutes"))
    return v or 0.0


tot = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))      # (season, team) -> pid -> [games, minutes]
ng = defaultdict(int)
TC = defaultdict(list)
last_out = {}
for g in sorted(FIN, key=lambda x: x["start"]):
    bx = BOX.get(g["id"])
    if not bx:
        continue
    flags = {}
    for side, t in (("home", g["home"]), ("away", g["away"])):
        key = (g["season"], t)
        star = None
        if ng[key] >= 10:
            c = [(v[1] / v[0], pid) for pid, v in tot[key].items() if v[0] >= 0.6 * ng[key] and v[1] / v[0] >= 28]
            if c:
                star = max(c)[1]
        played = {r["pid"] for r in bx.get(t, []) if mins(r) > 0}
        flags[side] = (star is not None and star not in played, star is not None)
    for side, t, oside in (("home", g["home"], "away"), ("away", g["away"], "home")):
        p = B.ats(g, side)
        if p is None:
            continue
        s = g["season"]
        out_me, has_me = flags[side]
        out_op, has_op = flags[oside]
        key = (s, t)
        if has_me and has_op:
            if out_me and not out_op:
                TC["its minutes leader is out, the other side's plays"].append((s, p))
                sc = sched(t, g)
                if sc and sc["b2b"]:
                    TC["   ... on a back-to-back (the rest night)"].append((s, p))
                if last_out.get(key):
                    TC["   ... and he was out last game too (old news)"].append((s, p))
                else:
                    TC["   ... the FIRST game he misses (fresh news)"].append((s, p))
            if not out_me and last_out.get(key) and not out_op:
                TC["its minutes leader is BACK after missing the last game"].append((s, p))
    for side, t in (("home", g["home"]), ("away", g["away"])):
        key = (g["season"], t)
        if flags[side][1]:
            last_out[key] = flags[side][0]
        ng[key] += 1
        for r in bx.get(t, []):
            mm = mins(r)
            if mm > 0:
                tot[key][r["pid"]][0] += 1
                tot[key][r["pid"]][1] += mm
for k, r in TC.items():
    tr = [(s, p) for s, p in r if s <= SPLIT]
    he = [(s, p) for s, p in r if s > SPLIT]
    uh = L.by_season(he)
    o(f"   {k[:56]:56s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% | HELD {L.st([p for _, p in he])} ({uh[0]}/{uh[1]} up: {uh[2]})")
o(f"\ncells read: {len(T)} + {len(TB)} x 3 + {len(TC)} = ~{len(T) + 3 * len(TB) + len(TC)}")
o.save()
