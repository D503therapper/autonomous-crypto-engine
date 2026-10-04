"""🌍 THE EUROPE MORNING UNDER - tracked, no units (the owner, 10/4: "track it and see if we can prove something").
The 10/4 look at every NFL game played abroad (SPORTS_FINDINGS): Europe 18-10 under, 9:30 AM ET kickoffs 16-9 - a
pattern, but 25 games (a coin would do 16-9 about 1 time in 9). So the engine takes the UNDER in every NFL game in
Europe that kicks off before noon ET, at the number it sees the night before (the first look from 6 PM PT the day
before - nobody moves these lines overnight), and grades it. Its own record; never on the board, never units, never
in the unit plays or leans records until the owner says so.

Writes data/sports/intl_unders.json."""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd

PATH = os.path.join(sd.DATA, "intl_unders.json")
ET = ZoneInfo("America/New_York")
PT = ZoneInfo("America/Los_Angeles")
EUROPE = {"England", "Germany", "Spain", "Ireland", "France", "Italy", "Scotland", "Wales", "Netherlands"}
MORNING_ET = 12                                  # kicks off before noon ET
LOOK_FROM_PT = 18                                # the night-before number: the first look from 6 PM PT the day before


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def fits(g):
    """An NFL game in Europe that kicks off before noon ET."""
    try:
        return (g.get("league") == "nfl" and str(g.get("intl")) == "1" and g.get("country") in EUROPE
                and _t(g["start"]).astimezone(ET).hour < MORNING_ET)
    except (KeyError, ValueError, TypeError):
        return False


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def update(st, games, now):
    """Log each fitting game's total once (the night-before number), then grade it off the final."""
    for g in games.values():
        if not fits(g):
            continue
        st_ = _t(g["start"])
        row = st["games"].get(g["id"])
        if row is None and g.get("status") == "pre" and _f(g.get("total")) is not None:
            eve = datetime.combine((st_.astimezone(PT) - timedelta(days=1)).date(), datetime.min.time(),
                                   tzinfo=PT).replace(hour=LOOK_FROM_PT)
            if eve <= now < st_:
                row = st["games"][g["id"]] = {
                    "date": st_.astimezone(PT).date().isoformat(), "game": f"{g.get('away_name')} @ {g.get('home_name')}",
                    "city": g.get("city"), "total": _f(g["total"]), "odds": int(_f(g.get("under_odds")) or -110),
                    "logged": now.strftime("%Y-%m-%dT%H:%MZ"), "result": None}
        if row and row["result"] is None and g.get("status") == "final" and g.get("home_score", "") != "" \
                and g.get("away_score", "") != "":
            pts = float(g["home_score"]) + float(g["away_score"])
            row["points"] = pts
            row["result"] = "won" if pts < row["total"] else "lost" if pts > row["total"] else "push"
    rows = list(st["games"].values())
    w = sum(r["result"] == "won" for r in rows)
    l_ = sum(r["result"] == "lost" for r in rows)
    units = sum((100 / -r["odds"] if r["odds"] < 0 else r["odds"] / 100) if r["result"] == "won" else
                -1 if r["result"] == "lost" else 0 for r in rows)
    st["record"] = {"won": w, "lost": l_, "push": sum(r["result"] == "push" for r in rows),
                    "units_if_1u": round(units, 2)}
    return st


def run(games, now=None, path=None):
    now = now or datetime.now(timezone.utc)
    try:
        st = json.load(open(path or PATH))
    except (OSError, ValueError):
        st = {}
    st.setdefault("games", {})
    update(st, games, now)
    with open(path or PATH, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    return st
