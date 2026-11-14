"""11/14 STUDY T2 - THE ⛰️ ALTITUDE OVER'S LEAKS (it is 1u now): every regular-season game on a home floor 1,400 m+,
not neutral, the over at the close - split by conference / non-conference, month, the visitor's trip, rest, power,
the spread, the total band. A cut needs the slice down in both halves with the rest up in both."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlib as T

A = [r for r in T.build() if r["stype"] == "2" and r["tot"] is not None and r["season"] >= 2018 and not r["neu"]
     and r["el"] is not None and r["el"] >= 1400]
T.cell("every 1,400 m+ home game", A, "over")
SPL = (("conference", lambda r: "conference" if r["conf"] else "non-conference"),
       ("month", lambda r: r["month"]),
       ("visitor trip", lambda r: "?" if r["tz_trip"] is None else "same zone" if abs(r["tz_trip"]) < 1 else "came west 1" if r["tz_trip"] > -2 and r["tz_trip"] < 0 else "came west 2+" if r["tz_trip"] <= -2 else "came east"),
       ("visitor rest", lambda r: "?" if r["ra"] is None else "0-2" if r["ra"] < 2.5 else "3-4" if r["ra"] < 4.5 else "5+"),
       ("power home", lambda r: "power home" if r["pow_h"] else "not power"),
       ("home spread", lambda r: "?" if r["sp"] is None else "home fav 10+" if r["sp"] <= -10 else "home fav 0.5-9.5" if r["sp"] < 0 else "home dog"),
       ("total", lambda r: "<140" if r["tot"] < 140 else "140-150" if r["tot"] < 150 else "150-160" if r["tot"] < 160 else "160+"),
       ("meeting", lambda r: "2nd+ meeting" if r["meet_n"] else "1st meeting"))
for nm, f in SPL:
    g = {}
    for r in A:
        g.setdefault(f(r), []).append(r)
    print(f" -- by {nm}")
    for k in sorted(g):
        T.cell(f"{nm}: {k}", g[k], "over", A, min_n=25)
print(f"cells read: {T.CELLS[0]}")
