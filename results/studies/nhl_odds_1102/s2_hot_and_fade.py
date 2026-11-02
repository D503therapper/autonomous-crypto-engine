"""STUDY 2 - THE HOT HOCKEY DOG -2 (sports.hot_dog / NHL_HOT_DOG_W: a dog on a 3+ game win streak) and THE MARKET-FADE -2
(sports.market_faded / MKT_FADE_W: the team's last 3 priced games moved 8+ no-vig points AGAINST it, open -> close) on
NHL dogs +100..+350, 2020-21..2022-23, graded at the MORNING price, the OPEN and the close. Both weights were built on the
close (hot: 2018-23 train / 2023-27 held; fade: ESPN opens 2023-26 only) - the morning / open prices here are new, and
for the fade 2021-23 is the first time the open -> close move exists at all (the paid next-day line; the morning look
where no next-day line was up)."""
from collections import defaultdict
import json
import lib

D = lib.build()
ALL = D["rows"]
ROWS = [r for r in ALL if lib.in_seasons(r)]
out = []


def P(s):
    print(s); out.append(s)


# market trend variants per team: open->close with OPEN only / MORNING only (2021-23 rows)
seq = defaultdict(list)          # (team, season) -> [(start, move_open or None, move_morning or None)]
trend = {}
for r in ALL:
    if not lib.in_seasons(r):
        continue
    for side, team in (("h", r["home"]), ("a", r["away"])):
        k = (team, r["season"])
        prev = seq[k]
        def tsum(i):
            xs = [p[i] for p in prev[-3:]]
            return sum(xs) if len(prev) >= 3 and all(x is not None for x in xs) else None
        trend[(r["id"], side)] = (tsum(1), tsum(2))
    mo = (r["p_close"] - r["open"]["p"]) if r["open"] else None
    mm = (r["p_close"] - r["morning"]["p"]) if r["morning"] else None
    seq[(r["home"], r["season"])].append((r["start"], mo, mm))
    seq[(r["away"], r["season"])].append((r["start"], -mo if mo is not None else None, -mm if mm is not None else None))


def dogs(at):
    xs = []
    for r in ROWS:
        for x in (lib.sides(r, at) or []):
            if 100 <= x["am"] <= 350:
                x["t_open"], x["t_morn"] = trend[(r["id"], x["side"])]
                xs.append(x)
    return xs


def S(xs):
    return lib.st([(x["r"]["season"], x["profit"], 1) for x in xs])


for at in ("morning", "open", "close"):
    P(f"\n===== {at.upper()} =====")
    xs = dogs(at)
    P(lib.line("every dog", S(xs)))
    P("-- HOT DOG (3+ game win streak)")
    P(lib.line("hot dog 3+", S([x for x in xs if x["stk"] >= 3])))
    P(lib.line("not hot (streak < 3)", S([x for x in xs if x["stk"] < 3])))
    P(lib.line("hot dog 2 straight", S([x for x in xs if x["stk"] == 2])))
    P(lib.line("hot dog 4+", S([x for x in xs if x["stk"] >= 4])))
    for lo, hi in ((100, 150), (151, 350)):
        P(lib.line(f"  hot +{lo}..+{hi}", S([x for x in xs if x["stk"] >= 3 and lo <= x["am"] <= hi])))
        P(lib.line(f"  not hot +{lo}..+{hi}", S([x for x in xs if x["stk"] < 3 and lo <= x["am"] <= hi])))
    P(lib.line("hot dog, rested vs a b2b fav", S([x for x in xs if x["stk"] >= 3 and x["ob2b"] and not x["b2b"]])))
    P(lib.line("not hot, rested vs a b2b fav", S([x for x in xs if x["stk"] < 3 and x["ob2b"] and not x["b2b"]])))
    # what the -2 does inside the Dog's range: dogs whose score WITHOUT the hot weight is 6..8 and the weight drops below 6
    if at == "morning":
        inn = []
        for x in xs:
            s0 = lib.dog_score(x, hot_w=0)
            s1 = lib.dog_score(x, hot_w=2)
            fight = x["own"] < 1 / x["dec"] - 0.03
            if not fight and x["own"] >= x["pm"] and s0 >= 6 > s1:
                inn.append(x)
        P(lib.line("  dogs the hot -2 KEEPS OFF the gated Dog (6+ -> under 6)", S(inn)))
    P("-- MARKET FADE (last 3 priced games, open->close, 8+ against)")
    for nm, key in (("open (next-day line) -> close", "t_open"), ("morning -> close", "t_morn")):
        ys = [x for x in xs if x[key] is not None]
        P(lib.line(f" [{nm}] dogs with a trend", S(ys)))
        P(lib.line(f"   faded 8+", S([x for x in ys if x[key] <= -0.08])))
        P(lib.line(f"   faded 4-8", S([x for x in ys if -0.08 < x[key] <= -0.04])))
        P(lib.line(f"   middle", S([x for x in ys if -0.04 < x[key] < 0.04])))
        P(lib.line(f"   backed 4-8", S([x for x in ys if 0.04 <= x[key] < 0.08])))
        P(lib.line(f"   backed 8+ (the mirror LEAD)", S([x for x in ys if x[key] >= 0.08])))
    ys = [x for x in xs if x["mt"] is not None]
    P(lib.line(" [as the engine would see it: open where up, else morning] faded 8+", S([x for x in ys if x["mt"] <= -0.08])))
    P(lib.line("   not faded", S([x for x in ys if x["mt"] > -0.08])))
    P(lib.line("   backed 8+", S([x for x in ys if x["mt"] >= 0.08])))

json.dump(out, open(f"{lib.OUT}/s2_out.json", "w"), indent=0)
open(f"{lib.OUT}/s2_out.txt", "w").write("\n".join(out) + "\n")
