"""Robustness / second checks for the two cells that cleared the screen (10/25)."""
import os, sys
sys.argv = ["x"]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "studies.py")).read().split("NC = [x for x")[0])
NC = [x for x in S if x["league"] == "ncaaf"]; NF = [x for x in S if x["league"] == "nfl"]
LINES.append("R1 college dogs +100..+350, line moved AWAY from the dog (open->close no-vig), by Elo gap at the close")
dogs = [x for x in NC if band(x, 100, 350) and x["w"] + x["l"] >= 2 and x["op"] is not None]
for lo in (-1, 0.0, 0.05, 0.10, 0.15, 0.20):
    for mv in (0.02, 0.04):
        cell(f"gap {lo:+.2f}+ moved away {mv:.2f}+", [x for x in dogs if x["elo_p"] - x["mp"] >= lo and x["op"] - x["mp"] >= mv], dogs)
# the gap measured at the OPEN (what the engine saw before the move), then moved away
for lo in (0.10, 0.15):
    cell(f"gap {lo:.2f}+ at the OPEN, then moved away 2+", [x for x in dogs if x["elo_p"] - x["op"] >= lo and x["op"] - x["mp"] >= 0.02], dogs)
    cell(f"gap {lo:.2f}+ at the OPEN, then moved TO 2+", [x for x in dogs if x["elo_p"] - x["op"] >= lo and x["mp"] - x["op"] >= 0.02], dogs)
    cell(f"gap {lo:.2f}+ at the OPEN, home, moved away 2+", [x for x in dogs if x["home"] and x["elo_p"] - x["op"] >= lo and x["op"] - x["mp"] >= 0.02], dogs)
    cell(f"gap {lo:.2f}+ at the OPEN, road, moved away 2+", [x for x in dogs if not x["home"] and x["elo_p"] - x["op"] >= lo and x["op"] - x["mp"] >= 0.02], dogs)
nd = [x for x in NF if band(x, 100, 350) and x["op"] is not None]
cell("NFL dogs gap 10+ moved away 2+ (second check)", [x for x in nd if x["elo_p"] - x["mp"] >= 0.10 and x["op"] - x["mp"] >= 0.02], nd)
LINES.append("\nR2 home favorites -101..-150 by kickoff window")
sun = [x for x in NF if x["et_dow"] == 6 and not x["neutral"] and x["home"]]
for lo, hi in ((-150, -101), (-150, -126), (-125, -101), (-200, -151)):
    cell(f"NFL Sunday 1 PM home fav {lo}..{hi}", [x for x in sun if 12.4 <= x["et_hour"] < 14.5 and band(x, lo, hi)], [x for x in sun if band(x, lo, hi)])
    cell(f"NFL Sunday 4 PM home fav {lo}..{hi}", [x for x in sun if 15.4 <= x["et_hour"] < 17.5 and band(x, lo, hi)], [x for x in sun if band(x, lo, hi)], primary=False)
    cell(f"NFL Sunday 1 PM ROAD dog facing it {abs(hi)}..{abs(lo)}", [x for x in NF if x["et_dow"] == 6 and not x["neutral"] and not x["home"] and 12.4 <= x["et_hour"] < 14.5 and band(x, abs(hi), abs(lo) + 20)], None, primary=False)
sat = [x for x in NC if x["home"] and x["et_dow"] == 5]
for nm, fn in (("noon", lambda x: 11.5 <= x["et_hour"] < 13), ("afternoon 3-4:30", lambda x: 15 <= x["et_hour"] < 17), ("night 7+", lambda x: x["et_hour"] >= 19)):
    cell(f"college Saturday {nm} home fav -101..-150 (second check)", [x for x in sat if fn(x) and band(x, -150, -101)], [x for x in sat if band(x, -150, -101)])
print("\n".join(LINES))
