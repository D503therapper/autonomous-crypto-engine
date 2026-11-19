"""11/19 daily - nflverse's public games file (the 11/19 offensive-line study's download, ~/.cache/d503_oline1119/dl/games.csv -
a plain download under our own name; read-only here): every NFL regular-season game 2006-26 with its closing moneyline,
spread and total, the roof / surface, the kickoff in ET, both coaches. Time zones are said on STANDARD time (ET -5,
CT -6, MT -7, PT -8); Arizona keeps no daylight time, so while the rest of the country is on it (the season up to the
first Sunday of November) Phoenix's clock reads as Pacific."""
import csv
import os
from datetime import date

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_oline1119", "dl")

ZONE = {}
for z, ts in ((-5, "BUF MIA NE NYJ NYG PHI WAS BAL PIT CLE CIN ATL CAR TB JAX IND DET"),
              (-6, "CHI GB MIN DAL HOU TEN KC NO STL"),
              (-7, "DEN ARI"),
              (-8, "SEA SF LA LAC SD OAK LV")):
    for t in ts.split():
        ZONE[t] = z
NAME = {-5: "ET", -6: "CT", -7: "MT", -8: "PT"}


def dst(d):
    """US daylight time on calendar day d (second Sunday of March .. first Sunday of November, 2007 on; 2006: first
    Sunday of April .. last Sunday of October)."""
    y = d.year
    if y >= 2007:
        mar = [date(y, 3, k) for k in range(8, 15) if date(y, 3, k).weekday() == 6][0]
        nov = [date(y, 11, k) for k in range(1, 8) if date(y, 11, k).weekday() == 6][0]
        return mar <= d < nov
    apr = [date(y, 4, k) for k in range(1, 8) if date(y, 4, k).weekday() == 6][0]
    octo = [date(y, 10, k) for k in range(25, 32) if date(y, 10, k).weekday() == 6][0]
    return apr <= d < octo


def clock(team, d):
    """The team's home clock on day d as a standard-time offset: its zone, except Arizona on daylight-time days (-8)."""
    return -8 if team == "ARI" and dst(d) else ZONE[team]


def raw(team, d):
    """What our game files' 'tzo' says for a game in this team's building on day d (the wall clock's UTC offset)."""
    return ZONE[team] + (1 if dst(d) and team != "ARI" else 0)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def games(lo=2006, hi=2026):
    out = []
    with open(os.path.join(DL, "games.csv")) as f:
        for r in csv.DictReader(f):
            s = int(r["season"])
            if r["game_type"] != "REG" or not lo <= s <= hi or r["home_score"] in ("", "NA") or r["away_score"] in ("", "NA"):
                continue
            mh, ma = num(r["home_moneyline"]), num(r["away_moneyline"])
            if mh is None or ma is None or mh == 0 or ma == 0:
                continue
            y, m, dd = (int(x) for x in r["gameday"].split("-"))
            hs, as_ = int(r["home_score"]), int(r["away_score"])
            try:
                hh = int(r["gametime"].split(":")[0]) + int(r["gametime"].split(":")[1]) / 60
            except (ValueError, IndexError):
                hh = None
            out.append({"id": r["game_id"], "season": s, "week": int(r["week"]), "day": date(y, m, dd), "home": r["home_team"],
                        "away": r["away_team"], "hs": hs, "as": as_, "neutral": r["location"] != "Home", "mlh": mh, "mla": ma,
                        "sp": num(r["spread_line"]),          # (nflverse: + = the HOME team is favored by that many)
                        "sho": num(r["home_spread_odds"]), "sao": num(r["away_spread_odds"]),
                        "total": num(r["total_line"]), "ovo": num(r["over_odds"]), "uno": num(r["under_odds"]),
                        "roof": r["roof"], "surface": (r["surface"] or "").strip(), "et": hh, "weekday": r["weekday"],
                        "hrest": num(r["home_rest"]), "arest": num(r["away_rest"]), "div": r["div_game"] == "1",
                        "hcoach": r["home_coach"], "acoach": r["away_coach"], "espn": r["espn"], "stadium": r["stadium_id"]})
    out.sort(key=lambda g: (g["day"], g["id"]))
    return out


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def ml_profit(g, side):
    won = (g["hs"] > g["as"]) if side == "home" else (g["as"] > g["hs"])
    if g["hs"] == g["as"]:
        return None
    o = g["mlh"] if side == "home" else g["mla"]
    return (dec(o) - 1) if won else -1.0


def ats_profit(g, side):
    if g["sp"] is None:
        return None
    m = g["hs"] - g["as"] - g["sp"]          # the home side's cover margin
    if m == 0:
        return None
    if side == "home":
        return (dec(g["sho"] or -110) - 1) if m > 0 else -1.0
    return (dec(g["sao"] or -110) - 1) if m < 0 else -1.0


def tot_profit(g, over):
    if g["total"] is None or g["hs"] + g["as"] == g["total"]:
        return None
    o = (g["ovo"] if over else g["uno"]) or -110
    return (dec(o) - 1) if ((g["hs"] + g["as"] > g["total"]) == over) else -1.0
