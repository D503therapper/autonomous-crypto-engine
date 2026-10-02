"""🔎 THE DAILY PICK AUDIT (the owner, 10/2: "we need to put a review on the engine's picks every day to make sure it
made the picks with the right data and the right decisions" - after the Steelers card called two BACKUP QBs the
starters). Every graded pick of a day, checked against what really happened:
  - every player we said was OUT: did he play? (the game's box score)  -> FLAG: false injury data
  - the QB / goalie we read as the starter vs who really started      -> FLAG: wrong starter
  - units: a lean never carries units; a thin edge is ½u              -> FLAG: wrong size
  - the price we posted vs the close (did we beat the market?)        -> the CLV line
Writes data/sports/pick_audit.json; runs every hour on the last 3 days (box scores land a few hours after a game).
No Claude usage - the engine checks itself."""
import csv
import glob
import gzip
import json
import os
import re
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "pick_audit.json")
_ROSTER = {}


def _nm(x):
    return " ".join(str(x or "").lower().replace(".", "").replace(" jr", "").replace(" sr", "").replace(" iii", "")
                    .replace(" ii", "").split())


def played(league, gid):
    """{normalized names} of everyone in the game's box score, or None when we don't hold it yet."""
    key = league
    if key not in _ROSTER:
        rows = {}
        for f in sorted(glob.glob(os.path.join(sd.DATA, "roster", f"{league}_*.csv.gz")))[-1:]:
            try:
                with gzip.open(f, "rt", newline="") as fh:
                    for r in csv.DictReader(fh):
                        rows.setdefault(r.get("gid"), set()).add(_nm(r.get("player")))
            except (OSError, EOFError, ValueError):
                continue
        _ROSTER[key] = rows
    return _ROSTER[key].get(gid)


def _started(league, gid, team):
    """The QB / goalie who really started for `team` in this game (our box scores), or None."""
    import sports_players as sp
    for r in sp.CACHE.get(league) or []:
        if r.get("gid") == gid and str(r.get("team")) == str(team):
            return r.get("player")
    return None


SEEN = re.compile(r"^(.*?) \((.*?)\)$")


def audit_day(picks, games, day):
    """-> {"flags": [...], "clv": [...], "checked": n} for the graded picks of `day` (YYYY-MM-DD)."""
    import sports
    flags, clv, n = [], [], 0
    for pk in picks:
        if pk.get("date") != day or pk.get("status") not in ("won", "lost", "push") or not pk.get("legs"):
            continue
        n += 1
        u = sports.units_for(pk)
        label = f"{pk['kind']} {pk['legs'][0].get('team')} {pk['legs'][0].get('odds')}"
        if pk.get("lean") and u and day >= sports.THIN_FROM:
            flags.append(f"{label}: a lean carried {u}u - leans never carry units")
        if not pk.get("lean") and u > 0.5 and day >= sports.THIN_FROM and sports.thin_edge(pk["legs"][0]):
            flags.append(f"{label}: {u}u on a thin edge (under {sports.THIN_EDGE:.0%}) - should be ½u")
        for leg in pk["legs"]:
            g = games.get(leg.get("game_id")) or {}
            lg = leg.get("league")
            box = played(lg, leg.get("game_id", ""))
            for who, status in (leg.get("key_seen") or {}).items():
                m = SEEN.match(who)
                name = m.group(1) if m else who
                if "out" in str(status).lower() and box is not None and _nm(name) in box:
                    flags.append(f"{label}: we had {name} OUT ({status}) - he played (false injury data)")
            if lg in ("nfl", "ncaaf", "nhl") and box is not None:
                for side in ("home", "away"):
                    real = _started(lg, leg.get("game_id"), g.get(side))
                    said_out = [SEEN.match(w).group(1) for w in (leg.get("key_seen") or {})
                                if SEEN.match(w) and g.get(f"{side}_name", "?") in SEEN.match(w).group(2)]
                    if real and _nm(real) in {_nm(x) for x in said_out}:
                        flags.append(f"{label}: {real} started for the {g.get(f'{side}_name')} - we had him out")
            close = sm._int(g.get(f"ml_{leg.get('side')}")) if leg.get("market") == "ml" else None
            if close is not None and leg.get("odds"):
                a, b = sd.decimal(leg["odds"]), sd.decimal(close)
                line = (f"{leg.get('team')} {sports.fmt_american(leg['odds'])} posted, closed {sports.fmt_american(close)}"
                        f" - {'beat the close' if a > b else 'same as the close' if a == b else 'the close was better'}")
                if line not in clv:
                    clv.append(line)
    return {"flags": flags, "clv": clv, "checked": n}


def run(picks, games, days):
    """Audit each day in `days`, keep the file to the last 30 days, print every flag (the run log + the review)."""
    try:
        with open(PATH) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    for d in days:
        r = audit_day(picks, games, d)
        if r["checked"]:
            r["at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            st[d] = r
            for x in r["flags"]:
                print(f"PICK AUDIT FLAG {d}: {x}", flush=True)
    st = {k: st[k] for k in sorted(st)[-30:]}
    with open(PATH, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    return st
