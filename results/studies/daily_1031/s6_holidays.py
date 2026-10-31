"""Study 6 (10/31): HOLIDAY SCHEDULING - Halloween, Thanksgiving week, Christmas, New Year's - every sport in season.
The idea: holiday games are played by distracted / travelling teams in front of a different crowd and bet by a
different (more casual, bigger) public - does the price miss anything?
Cells (US date = the start in UTC minus 5 hours; closing moneylines; dogs +100..+350, favorites -101..-150, home side):
  - Halloween night (10/31) - NFL / college football / NBA / NHL / college hoops,
  - Thanksgiving Day + the weekend after (Thu-Sun) - NFL Thanksgiving games, college RIVALRY WEEK, NBA / NHL Black
    Friday, college hoops feast week (the neutral-site November tournaments 11/18-11/30),
  - Christmas Day (12/25) - NBA / NFL; the NHL's FIRST game after its 12/24-12/26 break (every team rested 3+ days),
  - New Year's Eve / Day (12/31, 1/1) - every sport.
Train 2018-22, held out 2023 / 2024 / 2025 (+ 2026 for Halloween so far)."""
import json, os, sys
from collections import defaultdict
from datetime import date, datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2018, 2022), (2023, 2024, 2025, 2026)


def us_day(start):
    return (datetime.fromisoformat(start.replace("Z", "+00:00")) - timedelta(hours=5)).date()


def thanksgiving(y):
    d = date(y, 11, 1)
    first_thu = d + timedelta(days=(3 - d.weekday()) % 7)
    return first_thu + timedelta(days=21)


def holiday(lg, d, g, last_game_gap):
    t = []
    if d.month == 10 and d.day == 31:
        t.append("Halloween night")
    tg = thanksgiving(d.year)
    if d == tg:
        t.append("Thanksgiving Day")
    if tg <= d <= tg + timedelta(days=3):
        t.append("Thanksgiving Thu-Sun")
    if lg == "ncaab" and date(d.year, 11, 18) <= d <= date(d.year, 11, 30) and g["neutral"]:
        t.append("feast week neutral site")
    if d.month == 12 and d.day == 25:
        t.append("Christmas Day")
    if lg == "nhl" and d.month == 12 and 27 <= d.day <= 29 and last_game_gap is not None and last_game_gap >= 3:
        t.append("NHL first game after the Christmas break")
    if (d.month == 12 and d.day == 31) or (d.month == 1 and d.day == 1):
        t.append("New Year's Eve / Day")
    return t


out, lines = {}, []
for lg in ("nfl", "ncaaf", "nba", "nhl", "ncaab"):
    cells = defaultdict(list)
    last = {}
    for g in lib.finals(lg):
        d = us_day(g["start"])
        s = g["season"]
        gaps = {}
        for t in (g["home"], g["away"]):
            gaps[t] = (d - last[t]).days if t in last else None
        for side, team, opp, o, won, home in lib.sides(g):
            tags = holiday(lg, d, g, gaps[team])
            if not tags:
                continue
            pr = lib.profit(won, lib.dec(o))
            for tg in tags:
                if lib.dog_band(o):
                    cells[f"{tg} | dog +100..+350"].append((s, pr))
                    cells[f"{tg} | {'home' if home else 'road'} dog"].append((s, pr))
                elif -150 <= o <= -101:
                    cells[f"{tg} | fav -101..-150"].append((s, pr))
                if home and not g["neutral"]:
                    cells[f"{tg} | home side, any price"].append((s, pr))
                a = lib.ats(g, side)
                if a is not None and o > 0:
                    cells[f"{tg} | dog ATS"].append((s, a))
        for t in (g["home"], g["away"]):
            last[t] = d
    r = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
    out[lg] = r
    lines.append(f"== {lg}")
    lines += [lib.fmt(k, v) for k, v in r.items()]
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, "s6_out.txt"), "w").write(txt + "\n")
json.dump(out, open(os.path.join(lib.OUT, "s6_out.json"), "w"), indent=1)
