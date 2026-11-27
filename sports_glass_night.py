"""🏀 BEAT UP ON THE GLASS LAST GAME, ON A NEUTRAL FLOOR TONIGHT (11/27 daily studies S2; results/studies/daily_1127/
s_today.py s2 -> s_follow.py s2; ESPN's college team box 2021-26 - the season-long glass is built, ONE game as a spot
had never been read).

  A Division I team out-rebounded by 12 or more in its LAST game (a D1 game, inside 8 days) playing on a NEUTRAL floor:
  against the spread -17.7% on 318 at the close (train 2021-23 -11.8%, 0 of 3 seasons up / held 2024-26 -23.3%:
  -23.6 / -8.5 / -41 this season) where every neutral-floor side with a last-game box is -4.4% on 4,103 (a random set
  of neutral sides as bad 6 of 2,000); the side ACROSS it (itself not one) +11.7% on 281 (train +6.4% / held +16.9%,
  6 of 6 seasons up). NOT a weight: on a home or a road floor the same team is at its base (-5.0% / -5.7%), the dose
  is no slope (-12..-17 is -24.8% on 254, -18 or worse +10.5% on 64, and the team that WON the glass by 12+ is -12.4%
  on 592 on a neutral floor too), and about 750 cells were read that day. Two tracker LEADS (sports.GLASS_NIGHT_FROM,
  sports_leads.NCAAB_GLASS_NIGHT_TAG / NCAAB_VS_GLASS_NIGHT_TAG) - judged at 40 graded each, never read by the board.
Unknown (no box for the last game, a non-D1 team on either side of it, more than 8 days back) = no read."""
from datetime import datetime

GAP = -12                    # out-rebounded by this many or more in the last game
DAYS = 8.0                   # ...and tonight is within this many days of it
_ROWS = {}


def _box(gid, rows=None):
    if rows is not None:
        return next((r.get("teams") for r in rows if r.get("gid") == gid), None)
    if "by" not in _ROWS:
        import sports_roster as sr
        try:
            _ROWS["by"] = {r["gid"]: r.get("teams") for r in sr.team_rows("ncaab")}
        except Exception:                                    # noqa: BLE001 - no box file = unread
            _ROWS["by"] = {}
    return _ROWS["by"].get(gid)


def _n(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def margin(games, team, start, rows=None):
    """The team's rebound margin in its last finished game this season before `start` - a D1 team against a D1 team,
    inside DAYS - or None (unknown)."""
    import sports_ncaab_roster as nr
    d1 = nr.d1_set(games)
    last = nr._last_final(games, team, str(start or ""))
    if d1 is None or not last or str(team) not in d1:
        return None
    g = (games or {}).get(last[1]) or {}
    opp = g.get("away") if str(g.get("home")) == str(team) else g.get("home")
    if not opp or str(opp) not in d1:
        return None
    try:
        a = datetime.fromisoformat(str(last[0]).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
    except ValueError:
        return None
    if not 0 < (b - a).total_seconds() / 86400.0 <= DAYS:
        return None
    tm = _box(last[1], rows) or {}
    me, op = _n((tm.get(str(team)) or {}).get("totalRebounds")), _n((tm.get(str(opp)) or {}).get("totalRebounds"))
    if me is None or op is None:
        return None
    return me - op


def beat_up(games, team, start, rows=None):
    """True = out-rebounded by 12+ in its last game (a D1 game inside 8 days), False = not, None = unread."""
    m = margin(games, team, start, rows)
    return None if m is None else m <= GAP
