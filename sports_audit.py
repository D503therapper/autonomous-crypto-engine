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


STREAK = re.compile(r"(\d+) straight (?:W's|wins|Ws)", re.I)
NAMED_OUT = re.compile(r"(?:no|without|down|out:?)\s+([A-Z][a-z]+(?: [A-Z][a-zA-Z'\.-]+)+)")


def _streak(games, league, team, before):
    """The team's current win streak going into `before` (finals only)."""
    res = []
    for g in sorted((g for g in games.values() if g.get("league") == league and g.get("status") == "final"
                     and team in (g.get("home"), g.get("away")) and (g.get("start") or "") < before),
                    key=lambda g: g["start"]):
        try:
            m = float(g["home_score"]) - float(g["away_score"])
        except (TypeError, ValueError, KeyError):
            continue
        res.append((m if g["home"] == team else -m) > 0)
    n = 0
    for w in reversed(res):
        if not w:
            break
        n += 1
    return n


def card_facts(leg, games):
    """The card's own words vs the real games and the injury report it was posted with (10/2, the owner: "check all
    injury reports ... absolutely everything, no bugs"): a win streak it states, 'road game' / 'at home', and every
    player it names as out. Reports only - never touches a pick."""
    out = []
    g = games.get(leg.get("game_id")) or {}
    lines = list(leg.get("breakdown") or []) + [leg.get("why_line") or ""]
    text = " ".join(lines)
    side, other = leg.get("side"), "away" if leg.get("side") == "home" else "home"
    us, them = leg.get("team") or "", leg.get("opp") or ""
    for ln in lines:
        m = STREAK.search(ln)
        if m and g:
            who = g.get(side) if us and us in ln else g.get(other) if them and them in ln else None
            if who is not None:
                real = _streak(games, leg.get("league"), who, g.get("start") or "")
                if real != int(m.group(1)):
                    out.append(f"the card says {m.group(1)} straight wins, the games say {real}: '{ln[:80]}'")
        if g and str(g.get("neutral")) != "1":
            if re.search(r"road game for " + re.escape(us), ln, re.I) and side == "home":
                out.append(f"the card calls it a road game for {us} - they're at home")
    seen = " ".join(list(leg.get("outs") or []) + list(leg.get("opp_outs") or []) + list((leg.get("key_seen") or {}).keys()))
    for m in NAMED_OUT.finditer(text):
        nm = m.group(1)
        if nm in (us, them) or nm.split()[0] in ("The", "Both", "Backups", "Neither"):
            continue
        if nm not in seen and leg.get("outs") is not None:
            out.append(f"the card names {nm} as out - he's not on the injury report it was posted with")
    return out


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
                    said_out = [SEEN.match(w).group(1) for w, st_ in (leg.get("key_seen") or {}).items()
                                if SEEN.match(w) and g.get(f"{side}_name", "?") in SEEN.match(w).group(2)
                                and str(st_).lower() != "confirmed in net"]   # (10/6: a goalie we had CONFIRMED in net
                    #                                                           starting is the point, not false injury data)
                    if real and _nm(real) in {_nm(x) for x in said_out}:
                        flags.append(f"{label}: {real} started for the {g.get(f'{side}_name')} - we had him out")
            flags += [f"{label}: {x}" for x in card_facts(leg, games)]
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
