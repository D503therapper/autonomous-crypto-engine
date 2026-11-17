"""11/17 - THE CHARGERS QUESTION (the owner, 11/16: "the engine should have had 2 units on the chargers all day" -
Monday night, Chargers +185 at the Ravens, won 23-20; the board leaned Ravens -4.5, no units).

THE ROW (look_chargers.py + the 11/4 dry run of the 11/16 board, plays_every_day_1104/dryrun.py --all-leagues):
  Chargers +185 (needs 35.1%; the books' no-vig 33.6%): the blend 31.9%, the OWN read 34.2% (under the price), the raw
  ratings read 37.4%, dog score +1.53 against the NFL Dog gate of 8, NO named reason, 0-8, lost 8 straight, last game a
  44-22 loss; the Ravens: Lamar Jackson on injured reserve, a backup at QB (the engine could not call which one), 4-5.
  The price went Ravens -118 (11/8) -> -225: the money LEFT the Chargers all week.
IS AN NFL ROAD DOG IN THAT SHAPE A CELL THAT SHOULD CARRY UNITS? Named before looking, the same bar (both halves, a
placebo of 2,000 random same-size sets of NFL road dogs in the band, most seasons):
  A. nflverse's closing moneylines 2006-26 (ten_1115/nfl_lib; train 2006-16 / held 2017-26)
  B. the 11/14 football replay board's NFL rows 2018-26 (football_1114/flib.replay - the engine's own reads on today's
     code; train 2018-22 / held 2023-26)
Usage: python results/studies/sizing_1117/s4_chargers.py > results/studies/sizing_1117/s4_chargers.out"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ten_1115"))
sys.path.insert(0, os.path.join(HERE, "..", "football_1114"))
import nfl_lib as N  # noqa: E402

R = N.sides()
# the season's regular QB before each game (the most starts so far, 3+), from the rows themselves
starts = defaultdict(Counter)
reg_before = {}
for r in sorted(R, key=lambda r: (r["date"], r["gid"])):
    for team, qb in ((r["team"], r["qb"]),):
        c = starts[(r["season"], team)]
        top = c.most_common(1)
        reg_before[(r["gid"], team)] = top[0][0] if top and top[0][1] >= 3 else None
        c[qb] += 1
for r in R:
    reg = reg_before.get((r["gid"], r["opp"]))
    r["opp_backup"] = reg is not None and r["oqb"] != reg
    mine = reg_before.get((r["gid"], r["team"]))
    r["my_backup"] = mine is not None and r["qb"] != mine
    r["ats"] = None if r["line"] is None or r["margin"] + r["line"] == 0 else (0.9091 if r["margin"] + r["line"] > 0 else -1.0)

ROAD = [r for r in R if not r["home"] and not r["neutral"] and 100 <= r["odds"] <= 350]
BAND = [r for r in ROAD if 151 <= r["odds"] <= 250]
print("A. NFLVERSE'S CLOSES 2006-26 - the NFL ROAD dog")


def go(name, rs, pool, key="prof"):
    o = N.cell(name, rs, key=key)
    if o and o["n"] >= 15:
        pb = N.placebo(rs, pool, key=key)
        print(f"        placebo: a random {o['n']} from the pool did as well {pb} of 2,000")
    return o


go("every road dog +100..+350", ROAD, ROAD)
go("road dog +151..+250 (the Chargers' band)", BAND, ROAD)
go("  ... on Monday night", [r for r in BAND if r["wd"] == "Monday"], BAND)
go("  ... winless (0-5 or worse)", [r for r in BAND if r["w"] == 0 and r["l"] >= 5], BAND)
go("  ... on a 5+ game losing streak", [r for r in BAND if r["streak"] <= -5], BAND)
go("  ... on a 3+ game losing streak", [r for r in BAND if r["streak"] <= -3], BAND)
go("  ... off a loss by 17+", [r for r in BAND if (r["prev_m"] or 0) <= -17], BAND)
go("  ... the favorite starts a BACKUP QB (not its regular)", [r for r in BAND if r["opp_backup"]], BAND)
go("  ... the favorite a backup QB, the dog its regular QB", [r for r in BAND if r["opp_backup"] and not r["my_backup"]], BAND)
go("  ... the favorite off a loss by 17+", [r for r in BAND if (r["oprev_m"] or 0) <= -17], BAND)
go("  ... the favorite under .500 (3+ games)", [r for r in BAND if r["ow"] < r["ol"] and r["ow"] + r["ol"] >= 3], BAND)
go("  ... THE SHAPE: 3+ losing streak, the favorite under .500", [r for r in BAND if r["streak"] <= -3 and r["ow"] < r["ol"]], BAND)
go("  ... THE SHAPE: 3+ losing streak, the favorite a backup QB", [r for r in BAND if r["streak"] <= -3 and r["opp_backup"]], BAND)
go("  ... THE SHAPE: the favorite under .500 AND on a backup QB", [r for r in BAND if r["ow"] < r["ol"] and r["opp_backup"]], BAND)
go("any road dog +100..+350, the favorite on a backup QB", [r for r in ROAD if r["opp_backup"]], ROAD)
go("any road dog, the favorite under .500 on a backup QB", [r for r in ROAD if r["opp_backup"] and r["ow"] < r["ol"]], ROAD)
go("any road dog winless at 0-5 or worse", [r for r in ROAD if r["w"] == 0 and r["l"] >= 5], ROAD)
print("  -- the same dogs on the SPREAD (the closing line at -110; the Chargers were +4.5)")
SP = [r for r in R if not r["home"] and not r["neutral"] and r["line"] is not None and 3 <= r["line"] <= 6.5]
go("road dog getting 3 to 6.5", SP, SP, key="ats")
go("  ... the favorite on a backup QB", [r for r in SP if r["opp_backup"]], SP, key="ats")
go("  ... on a 3+ losing streak", [r for r in SP if r["streak"] <= -3], SP, key="ats")
go("  ... winless (0-5 or worse)", [r for r in SP if r["w"] == 0 and r["l"] >= 5], SP, key="ats")
go("  ... on Monday night", [r for r in SP if r["wd"] == "Monday"], SP, key="ats")
go("  ... the favorite under .500 on a backup QB", [r for r in SP if r["opp_backup"] and r["ow"] < r["ol"]], SP, key="ats")

print("\nB. THE FOOTBALL REPLAY BOARD'S NFL ROWS 2018-26 (the engine's own reads, today's code)")
import flib as F  # noqa: E402

rows = [r for r in F.replay(leagues=("nfl",)) if r["result"] in ("won", "lost")]
rd = [r for r in rows if not r["home"] and not r.get("neutral") and 100 <= r["odds"] <= 350]
bd = [r for r in rd if 151 <= r["odds"] <= 250]
om = lambda r: None if r.get("own") is None else 100 * (r["own"] - 1 / r["dec"])      # noqa: E731
rg = lambda r: None if r.get("raw_own") is None or r.get("p_market") is None else 100 * (r["raw_own"] - r["p_market"])   # noqa: E731


def rgo(name, rs, pool):
    o = F.rline(name, rs)
    if o["n"] >= 15:
        print(f"        placebo: {F.rplacebo(rs, pool)} of 2,000")


print(f"  NFL road dogs +100..+350 on the rows: {len(rd)}; +151..+250: {len(bd)}")
rgo("every NFL road dog +100..+350", rd, rd)
rgo("road dog +151..+250", bd, rd)
rgo("  ... the raw ratings read 3+ over the no-vig (Chargers: +3.8)", [r for r in bd if (rg(r) or -99) >= 3], bd)
rgo("  ... raw read 3+ over AND the own read under the price", [r for r in bd if (rg(r) or -99) >= 3 and (om(r) or 0) < 0], bd)
rgo("  ... the own read within 2 pts under the price (Chargers: -0.9)", [r for r in bd if om(r) is not None and -2 <= om(r) < 0], bd)
rgo("  ... dog score 0 to 4 (Chargers: +1.5)", [r for r in bd if r.get("dog_score") is not None and 0 <= r["dog_score"] < 4], bd)
rgo("  ... dog score 0 to 4, no named reason", [r for r in bd if r.get("dog_score") is not None and 0 <= r["dog_score"] < 4 and not r.get("reasons")], bd)
rgo("  ... THE ROW'S SHAPE: score 0-4, own read under, raw read 3+ over", [r for r in bd if r.get("dog_score") is not None and 0 <= r["dog_score"] < 4 and (om(r) or 0) < 0 and (rg(r) or -99) >= 3], bd)
rgo("any NFL road dog, score 0-4, own read under, raw read 3+ over", [r for r in rd if r.get("dog_score") is not None and 0 <= r["dog_score"] < 4 and (om(r) or 0) < 0 and (rg(r) or -99) >= 3], rd)
rgo("any NFL road dog at the Dog gate (score 8+)", [r for r in rd if (r.get("dog_score") or -99) >= 8], rd)
rgo("any NFL road dog under the gate (score under 8)", [r for r in rd if r.get("dog_score") is not None and r["dog_score"] < 8], rd)
