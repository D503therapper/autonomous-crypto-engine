"""11/14 STUDY T - COLLEGE HOOPS TOTALS BEYOND ALTITUDE (the owner's priority 3): rest, the trip (time zones), the
conference season and the rematch, the size of the spread, the tip time, the day of the week - the over and the under
at the CLOSE, regular season, priced totals 2018-26. Altitude floors (1,400 m+) are left out of every cell (the built
⛰️ over owns them). Not re-run (dead on file): pace pairs, three-point luck, the over / under chase, early-season totals,
neutral unders, March neutral overs, very high / low totals, a floor's over history, the projection 12+ off the book,
refs, the juice lean."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlib as T

R = [r for r in T.build() if r["stype"] == "2" and r["tot"] is not None and r["season"] >= 2018
     and not (r["el"] is not None and r["el"] >= 1400 and not r["neu"])]
H = [r for r in R if not r["neu"]]
print(f"priced regular-season totals (no altitude floors): {len(R)}, non-neutral {len(H)}")
print("\n0. BASE")
T.cell("every game", R, "over"); T.cell("every game", R, "under")
T.cell("non-neutral", H, "over"); T.cell("non-neutral", H, "under")

print("\nA. REST (days since each team's last game on file)")
def both(r, lo, hi):
    return r["rh"] is not None and r["ra"] is not None and lo <= r["rh"] < hi and lo <= r["ra"] < hi
for lab, f in (("both off 7+ days", lambda r: both(r, 7, 99)),
               ("both off 5-7 days", lambda r: both(r, 5, 7)),
               ("both off 2 days or less", lambda r: both(r, 0, 2.5)),
               ("both off 1 day (back-to-back)", lambda r: both(r, 0, 1.5)),
               ("home off 7+, visitor 4 or less", lambda r: r["rh"] is not None and r["ra"] is not None and r["rh"] >= 7 and r["ra"] <= 4),
               ("visitor off 7+, home 4 or less", lambda r: r["rh"] is not None and r["ra"] is not None and r["ra"] >= 7 and r["rh"] <= 4),
               ("rest gap 4+ days either way", lambda r: r["rh"] is not None and r["ra"] is not None and abs(r["rh"] - r["ra"]) >= 4),
               ("first game back from the holiday (Dec 26-Jan 3), both off 6+", lambda r: (r["start"][5:10] >= "12-26" or r["start"][5:10] <= "01-03") and both(r, 6, 99))):
    rows = [r for r in H if f(r)]
    T.cell(lab, rows, "over", H); T.cell(lab, rows, "under", H)

print("\nB. THE TRIP (non-neutral: tonight's floor's time zone minus the visitor's home floor's)")
for lab, f in (("visitor came WEST 2+ hours", lambda r: r["tz_trip"] is not None and r["tz_trip"] <= -2),
               ("visitor came west 1 hour", lambda r: r["tz_trip"] is not None and -2 < r["tz_trip"] <= -1),
               ("visitor came EAST 2+ hours", lambda r: r["tz_trip"] is not None and r["tz_trip"] >= 2),
               ("visitor came east 1 hour", lambda r: r["tz_trip"] is not None and 1 <= r["tz_trip"] < 2),
               ("visitor same time zone", lambda r: r["tz_trip"] is not None and abs(r["tz_trip"]) < 1),
               ("visitor came west 2+, tip 8 PM local or later", lambda r: r["tz_trip"] is not None and r["tz_trip"] <= -2 and (r["local_hr"] or 0) >= 20),
               ("visitor came east 2+, tip before 2 PM local", lambda r: r["tz_trip"] is not None and r["tz_trip"] >= 2 and r["local_hr"] is not None and r["local_hr"] < 14)):
    rows = [r for r in H if f(r)]
    T.cell(lab, rows, "over", H); T.cell(lab, rows, "under", H)

print("\nC. THE CONFERENCE SEASON (non-neutral)")
for lab, f in (("non-conference Nov", lambda r: not r["conf"] and r["month"] == "11"),
               ("non-conference Dec", lambda r: not r["conf"] and r["month"] == "12"),
               ("conference Dec", lambda r: r["conf"] and r["month"] == "12"),
               ("conference Jan", lambda r: r["conf"] and r["month"] == "01"),
               ("conference Feb", lambda r: r["conf"] and r["month"] == "02"),
               ("conference Mar", lambda r: r["conf"] and r["month"] == "03"),
               ("conference, 1st meeting", lambda r: r["conf"] and r["meet_n"] == 0),
               ("conference, 2nd meeting", lambda r: r["conf"] and r["meet_n"] == 1),
               ("2nd meeting, 1st went 10+ OVER tonight's total", lambda r: r["meet_n"] >= 1 and r["meet_last"] is not None and r["meet_last"] - r["tot"] >= 10),
               ("2nd meeting, 1st went 10+ UNDER tonight's total", lambda r: r["meet_n"] >= 1 and r["meet_last"] is not None and r["meet_last"] - r["tot"] <= -10),
               ("2nd meeting, 1st within 5 of tonight's total", lambda r: r["meet_n"] >= 1 and r["meet_last"] is not None and abs(r["meet_last"] - r["tot"]) < 5),
               ("power league conference game", lambda r: r["conf"] and r["pow_h"]),
               ("non-power conference game", lambda r: r["conf"] and not r["pow_h"]),
               ("non-conf power home vs non-power visitor", lambda r: not r["conf"] and r["pow_h"] and not r["pow_a"]),
               ("non-conf non-power home vs power visitor", lambda r: not r["conf"] and not r["pow_h"] and r["pow_a"])):
    rows = [r for r in H if f(r)]
    T.cell(lab, rows, "over", H); T.cell(lab, rows, "under", H)

print("\nD. THE SPREAD (non-neutral, the closing home spread)")
for lab, f in (("home favored 20+", lambda r: r["sp"] is not None and r["sp"] <= -20),
               ("home favored 12-19.5", lambda r: r["sp"] is not None and -20 < r["sp"] <= -12),
               ("pick'em to 3", lambda r: r["sp"] is not None and abs(r["sp"]) <= 3),
               ("road team favored 7+", lambda r: r["sp"] is not None and r["sp"] >= 7),
               ("home favored 20+, conference", lambda r: r["sp"] is not None and r["sp"] <= -20 and r["conf"]),
               ("home favored 20+, non-conference", lambda r: r["sp"] is not None and r["sp"] <= -20 and not r["conf"])):
    rows = [r for r in H if f(r)]
    T.cell(lab, rows, "over", H); T.cell(lab, rows, "under", H)

print("\nE. THE TIP (local hour, non-neutral) AND THE DAY")
from datetime import datetime
for lab, f in (("tip before 1 PM local", lambda r: r["local_hr"] is not None and r["local_hr"] < 13),
               ("tip 9 PM local or later", lambda r: r["local_hr"] is not None and r["local_hr"] >= 21),
               ("Saturday", lambda r: datetime.strptime(r["start"][:10], "%Y-%m-%d").weekday() == 5),
               ("Sunday", lambda r: datetime.strptime(r["start"][:10], "%Y-%m-%d").weekday() == 6),
               ("Monday-Thursday", lambda r: datetime.strptime(r["start"][:10], "%Y-%m-%d").weekday() <= 3)):
    rows = [r for r in H if f(r)]
    T.cell(lab, rows, "over", H); T.cell(lab, rows, "under", H)

print("\nF. NEUTRAL FLOORS by rest (the event's 2nd / 3rd game in 2-3 days)")
N = [r for r in R if r["neu"]]
for lab, f in (("neutral, both off 1 day", lambda r: both(r, 0, 1.5)),
               ("neutral, both off 1-2 days, Nov-Dec", lambda r: both(r, 0, 2.5) and r["month"] in ("11", "12")),
               ("neutral, conference tournament (Mar), both off 1 day", lambda r: both(r, 0, 1.5) and r["month"] == "03")):
    rows = [r for r in N if f(r)]
    T.cell(lab, rows, "over", N); T.cell(lab, rows, "under", N)
print(f"\ncells read: {T.CELLS[0]} (about {T.CELLS[0] // 20} clear |z| 2 by luck)")
