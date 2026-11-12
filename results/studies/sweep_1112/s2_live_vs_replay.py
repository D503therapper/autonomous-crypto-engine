"""11/12 FULL SWEEP, part 2 - LIVE vs REPLAY, BY KIND (every graded unit play 9/27 -> 11/10, s1_rows.json): the live
record against (a) the PRICE (a coin weighted at the price we bet) and (b) what the kind's REPLAY / blind number says it
should win at those prices - z = (live wins - predicted wins) / sd. A kind is "leaking" only when the live record is
unlikely EVEN IF the replay is right (z under -2) AND there is a reason; under ~20 plays a z says little either way.
The replay numbers: s3_replay.out (today's builder on the 10/30 funnel rows, train + held out, flat 1u); the early
spots' blind numbers: the 11/11 early study (s5b, first fair price, held out). The last two weeks alone beside it.
Usage: python results/studies/sweep_1112/s2_live_vs_replay.py > results/studies/sweep_1112/s2_live_vs_replay.out"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "s1_rows.json")))
FROM = "2026-10-29"
# kind: (the replay's / blind flat ROI %, its n, the name, where the number comes from)
REF = {"dog": (17.2, 286, "the Dog of the Day", "replay"), "lock": (4.8, 154, "the Lock", "replay"),
       "value play": (1.6, 328, "value plays", "replay"), "floor": (8.0, 918, "the floor", "replay"),
       "nbafloor": (24.7, 128, "the NBA floor", "replay - its rule was chosen on these rows"),
       "dogplay": (18.3, 90, "the runner-up dog", "replay - 59 of the 90 are hockey; live it posted 4 college + 2 NBA"),
       "nbafav": (22.7, 76, "the NBA favorite play", "replay - chosen on these rows"),
       "gap": (0.0, 0, "the 🔍 college gap play", "no replay row - against the price"),
       "early:blowout": (-7.4, 182, "early: blew somebody out", "held out 2023-26 (train +21.4%)"),
       "early:bye": (6.4, 63, "early: off a bye", "college +6.4% on 63 / NFL +40.3% on 28"),
       "early:hammered": (23.0, 48, "early: hammered", "the 4+ move, both halves +23%, z 1.3"),
       "early:engine": (0.0, 0, "early: the college engine spot", "paused 10/24"),
       "early:nba_open": (12.6, 333, "early: the NBA opening line", "walk-forward at the open 2023-26"),
       "early:euro_under": (20.0, 26, "early: the Europe under", "17-9 since 2018"),
       "early:exam": (7.3, 70, "early: the exam band", "the rolling exam, college +4..8")}


def z(rs, roi):
    w = sum(r["won"] for r in rs)
    k = 1 + roi / 100
    ps = [min(0.97, k / r["dec"]) for r in rs]
    e = sum(ps)
    s = math.sqrt(sum(p * (1 - p) for p in ps))
    return w, e, (w - e) / s if s else 0.0


def line(name, rs, roi, note=""):
    if not rs:
        return
    w, e0, z0 = z(rs, 0.0)
    _, e1, z1 = z(rs, roi)
    net = sum(r["net"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs) / len(rs) * 100
    two = [r for r in rs if r["date"] >= FROM]
    w2 = sum(r["won"] for r in two)
    print(f"  {name:32s} live {w:2d}-{len(rs) - w:<2d} {net:+6.2f}u flat {fl:+6.1f}% | vs the price: {e0:4.1f} wins, z {z0:+.2f} | vs its replay ({roi:+.1f}%): {e1:4.1f} wins, z {z1:+.2f}"
          f" | last two weeks {w2}-{len(two) - w2} {sum(r['net'] for r in two):+.2f}u | {note}")


print("LIVE vs THE REPLAY, BY KIND (z under -2 = running under what its own replay says)")
for k, (roi, n, name, src) in REF.items():
    line(name, [r for r in rows if r["kind"] == k], roi, f"{src}" + (f", n {n}" if n else ""))
print("\nGROUPS")
bd = [r for r in rows if not r["kind"].startswith("early")]
line("ALL board unit plays", bd, 10.3, "the replay's flat +10.3%")
line("   favorites", [r for r in bd if r["am"] < 0], 5.6, "")
line("   dogs", [r for r in bd if r["am"] > 0], 12.1, "")
line("   hockey Dogs", [r for r in bd if r["lg"] == "nhl" and r["kind"] == "dog"], 15.6, "replay n 232")
line("   hockey, every unit play", [r for r in bd if r["lg"] == "nhl"], 12.0, "")
line("   NBA dogs, every board kind", [r for r in bd if r["lg"] == "nba" and r["am"] > 0], 28.0, "replay n 161 (in-sample rules)")
line("   NBA dogs incl. the opening line", [r for r in rows if r["lg"] == "nba" and r["am"] > 0], 20.0, "")
line("   college football board dogs", [r for r in bd if r["lg"] == "ncaaf" and r["am"] > 0], 23.1, "replay n 47 (no 🔍 / early in it)")
line("   ...without the 🔍 play", [r for r in bd if r["lg"] == "ncaaf" and r["am"] > 0 and r["kind"] != "gap"], 23.1, "")
line("   runner-up dog: college football", [r for r in bd if r["kind"] == "dogplay" and r["lg"] == "ncaaf"], 35.8, "replay n 20 (15 of them held out)")
line("   runner-up dog: NBA", [r for r in bd if r["kind"] == "dogplay" and r["lg"] == "nba"], 25.3, "replay n 10")
line("   runner-up dog: hockey", [r for r in bd if r["kind"] == "dogplay" and r["lg"] == "nhl"], 13.2, "replay n 59 - never posted live")
line("   adds from 2 PM PT on", [r for r in bd if r["slot"] == "2 PM on"], 10.3, "")
line("   NBA dog adds from 2 PM on", [r for r in bd if r["slot"] == "2 PM on" and r["lg"] == "nba" and r["am"] > 0], 28.0, "")
line("   mid-day adds (9 AM-2 PM)", [r for r in bd if r["slot"] == "mid-day"], 10.3, "")
line("   the 8 AM board", [r for r in bd if r["slot"] == "8 AM"], 10.3, "")
line("early plays, every spot", [r for r in rows if r["kind"].startswith("early")], 5.0, "")
line("plays sized 2u or more", [r for r in rows if r["u"] >= 2], 17.5, "today's 2u plays in the replay +17.5% on 285")
line("Saturdays, every unit play", [r for r in rows if r["dow"] == "Sat"], 11.7, "replay Saturdays +11.7% on 436 (no 🔍 / early)")
line("   Saturday college dogs", [r for r in rows if r["dow"] == "Sat" and r["lg"] == "ncaaf" and r["am"] > 0], 23.9, "replay n 39")
print("\nTHE 🔍 GAP PLAY, live, by where the dog played")
line("   at home", [r for r in rows if r["kind"] == "gap" and r["home"]], 0.0, "cut 11/11")
line("   on the road", [r for r in rows if r["kind"] == "gap" and not r["home"]], 0.0, "what the 11/11 cut kept")
print("\nTHE SAME DOG TWICE (the board took the side of an open early play - 'both count'): by game")
seen = {}
for r in rows:
    seen.setdefault((r["date"], r["team"]), []).append(r)
tw = [v for v in seen.values() if len(v) > 1]
print(f"   {len(tw)} games carried two bets on one dog: {sum(v[0]['won'] for v in tw)}-{sum(not v[0]['won'] for v in tw)}, {sum(r['net'] for v in tw for r in v):+.2f}u on {sum(r['u'] for v in tw for r in v):.1f}u")
for v in tw:
    print(f"      {v[0]['date'][5:]} {v[0]['team']:16s} " + " + ".join(f"{r['kind']} {r['am']:+d} {r['u']}u" for r in v) + f" -> {'WON' if v[0]['won'] else 'lost'} {sum(r['net'] for r in v):+.2f}u")
