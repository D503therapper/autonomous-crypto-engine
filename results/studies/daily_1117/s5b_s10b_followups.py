"""11/17 follow-ups on the two cells that stood out.
S5b - the NHL dog with a BAD record (.400-) built on a TOUGH schedule (opponents' win % to date over .550): every cut -
     the dose (how tough, how bad), the season stage, the price, home / road, a point worse than the close, the whole
     season (games 5-82), and the same idea in the NBA / college hoops as a second check.
S10b - the NFL 'popular' dog (S10) was picked with hindsight (several of the decade's best teams). The honest version:
     last season's GOOD team (.650+ last regular season - known before this season) as a dog this season, NFL / NBA / NHL."""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("rows", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s2_s10_rows.py"))
sys.argv = [sys.argv[0], "none"]
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)                     # (WHICH = {"none"} - only the helpers load)

TRAIN, HELD = R.TRAIN, R.HELD


def worse(o):
    """the American price a point (of win chance) worse than o."""
    p = 1 / lib.dec(o) + 0.01
    return lib.american(1 / p)


o = Out("s5b_nhl_tough_schedule_dog", TRAIN, HELD)
for lg in ("nhl", "nba", "ncaab"):
    for g, st in R.walk(lg):
        s = g["season"]
        for side, t in (("home", g["home"]), ("away", g["away"])):
            r = st[(s, t)]
            n = r["w"] + r["l"]
            if n < 5:
                continue
            ow = [R.wp(st[(s, x)]) for x in r["opps"] if R.wp(st[(s, x)]) is not None]
            if len(ow) < 5:
                continue
            sos = sum(ow) / len(ow)
            me = R.wp(r)
            od, pr = R.ml_prof(g, side)
            if not 100 <= od <= 350:
                continue
            won = pr > 0
            pw = lib.profit(won, lib.dec(worse(od)))
            o.add(f"{lg} dog ALL games 5+", s, pr)
            if n <= 30:
                o.add(f"{lg} dog ALL games 5-30", s, pr)
            if me > 0.4 or sos <= 0.53:
                continue
            tb = ".530-.550" if sos <= 0.55 else (".550-.570" if sos <= 0.57 else ".570+")
            rb = ".350-" if me <= 0.35 else ".351-.400"
            o.add(f"{lg} bad dog, opps {tb} games 5+", s, pr)
            if sos <= 0.55:
                continue
            base = f"{lg} BAD + TOUGH (.550+)"
            o.add(f"{base} games 5+", s, pr)
            if n > 30:
                o.add(f"{base} games 31+", s, pr)
                continue
            o.add(f"{base} games 5-30", s, pr)
            o.add(f"{base} games 5-30 a point WORSE than the close", s, pw)
            o.add(f"{base} games {'5-15' if n <= 15 else '16-30'}", s, pr)
            o.add(f"{base} record {rb}", s, pr)
            o.add(f"{base} {'+100..+150' if od <= 150 else '+151..+350'}", s, pr)
            o.add(f"{base} {'home' if side == 'home' else 'road'}", s, pr)
o.show()
o.placebo("nhl BAD + TOUGH (.550+) games 5-30", "nhl dog ALL games 5-30")
o.placebo("nhl BAD + TOUGH (.550+) games 5+", "nhl dog ALL games 5+")
o.save()

# ---------------- S10b last season's good team as a dog
o2 = Out("s10b_last_seasons_good_team_dog", TRAIN, HELD)
for lg in ("nfl", "nba", "nhl"):
    allf = [g for g in lib.all_finals(lg) if g["stype"] == "2"]
    rec = defaultdict(lambda: [0, 0])
    for g in allf:
        hw = g["hs"] > g["as"]
        rec[(g["season"], g["home"])][0 if hw else 1] += 1
        rec[(g["season"], g["away"])][1 if hw else 0] += 1

    def last_wp(s, t):
        w, lo = rec.get((s - 1, t), (0, 0))
        return w / (w + lo) if w + lo >= 10 else None
    for g in R.reg(lib.finals(lg)):
        s = g["season"]
        for side, t in (("home", g["home"]), ("away", g["away"])):
            od, pr = R.ml_prof(g, side)
            b = R.band(od)
            if not b:
                continue
            lw = last_wp(s, t)
            if lw is None:
                continue
            lb = "last season .650+" if lw >= 0.65 else ("last season .350-" if lw <= 0.35 else "last season mid")
            o2.add(f"{lg} {b} {lb}", s, pr)
            o2.add(f"{lg} {b} ALL", s, pr)
            if b == "dog" and lw >= 0.65:
                o2.add(f"{lg} dog last season .650+ {'home' if side == 'home' else 'road'}", s, pr)
o2.show()
for lg in ("nfl", "nba", "nhl"):
    o2.placebo(f"{lg} dog last season .650+", f"{lg} dog ALL")
o2.save()
