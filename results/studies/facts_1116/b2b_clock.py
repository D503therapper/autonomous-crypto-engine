"""11/16 FABLE - EVERY FACT TRUE: the back-to-back the WEIGHTS read (sports_form.played_yesterday) counted UTC calendar
dates - a 7 PM Pacific game (03:00Z, 'tomorrow' in UTC) and a 1 PM Pacific game two days later sit one UTC date apart and
read as a back-to-back 42 hours apart; a 2 PM Pacific game and the next night's 4:30 PM Pacific game sit two UTC dates
apart and were missed. How often, NBA / NHL regular seasons 2021-26, against the clock (29 hours - the card's rule,
sports_breakdown_v24.B2B_HOURS)?  python results/studies/facts_1116/b2b_clock.py -> b2b_clock_out.txt"""
import os
import sys
from collections import Counter
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports_data as sd            # noqa: E402

G = sd.load_games()
T = lambda s: datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")           # noqa: E731
out = []
for lg in ("nba", "nhl"):
    by = {}
    for g in sorted(G.values(), key=lambda g: g["start"]):
        if g["league"] == lg and g.get("status") == "final" and str(g.get("stype") or "2") in ("2", "3", "5") and g["start"] >= "2021-09-01":
            for s in ("home", "away"):
                by.setdefault(g[s], []).append(g["start"])
    c = Counter()
    for t, ss in by.items():
        for a, b in zip(ss, ss[1:]):
            hrs = (T(b) - T(a)).total_seconds() / 3600
            if hrs > 24 * 120:
                continue
            by_date = (T(b[:10] + "T00:00") - T(a[:10] + "T00:00")).days == 1
            by_clock = hrs <= 29
            c[(by_date, by_clock)] += 1
            if by_date and not by_clock:
                c["false gap hours " + str(int(hrs // 6 * 6))] += 1
    n = sum(v for k, v in c.items() if isinstance(k, tuple))
    out.append(f"{lg.upper()} team-games 2021-26: {n}")
    out.append(f"  a back-to-back by both rules              {c[(True, True)]}")
    out.append(f"  the UTC-date rule says b2b, the clock no   {c[(True, False)]}  ({c[(True, False)] / max(1, c[(True, True)] + c[(True, False)]):.1%} of the weights' 'played last night' were 2 nights apart)")
    out.append(f"  a real b2b the UTC-date rule missed        {c[(False, True)]}  ({c[(False, True)] / max(1, c[(True, True)] + c[(False, True)]):.1%} of real back-to-backs)")
    out.append("  the false ones' gaps: " + ", ".join(f"{k.split()[-1]}-{int(k.split()[-1]) + 6}h {v}" for k, v in sorted(c.items(), key=str) if isinstance(k, str)))
txt = "\n".join(out)
print(txt)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "b2b_clock_out.txt"), "w").write(txt + "\n")
