"""🏒 THE PUCK-MANAGEMENT READ (11/23 daily studies S4 / S6; results/studies/daily_1123/s_today.py -> s_follow.py ->
s4c_board_replay.py; ESPN's NHL team box 2021-26 - giveaways / takeaways, columns no study had read).

  SLOPPY ON THE ROAD: a team's takeaways minus giveaways a game in its ROAD games (no home scorer's generous count),
      season to date (10+ box games, 4+ of them on the road), ranked among the league's current values that night
      (20+ teams read). The bottom fifth as a DOG +100..+350: -18.5% on 884 at the close (train 2021-23 -19.9%, 0 of 3
      seasons up / held 2024-26 -17.2%: -21.8 / -7.9 / -46.2; a same-price random set as bad 1 of 2,000) against -6.7%
      for every dog; ESPN's open -18.2% on 454, the paid morning -16.2% on 112; NOT the built out-shot read (with the
      shot share above the bottom fifth -16.0% on 656, placebo 25); not the back-to-back (-13.4% on 702 without one);
      it is the GIVEAWAYS (top fifth of road giveaways alone -17.7% on 958; takeaways alone nothing); a step, not a
      slope (league place 20-40: -4.0%); the favorite across +4.0% on 776 (both halves). BUT the replay board's own
      posted hockey dogs carrying it did fine (+9.0% on 64 against +10.8% on 320 - the dog score's other weights had
      already left the bad ones off), so the weight is HALF (sports.NHL_SLOPPY_PTS 1) until its tracker tag judges it.
  SHELLED: 40+ shots against in the team's last game, playing again within 2 days - that dog -23.6% on 426 (train
      -23.7% / held -23.4%; same-price placebo 4 of 2,000; one night off -21.1% on 308; the open -28.7% on 180) - a
      tracker LEAD only (7 of the replay board's posted dogs carried it).
Unknown (no box file, under the game counts, under 20 teams read, a game we can't place home / road) = no read."""
from datetime import datetime

MIN_G = 10                   # box games this season before the read counts
MIN_ROAD = 4                 # ...and road games among them
MIN_TEAMS = 20               # teams read before anybody is ranked
FIFTH = 0.2
SHELLED_SHOTS = 40           # shots against in the last game
SHELLED_DAYS = 2.2           # ...and tonight is within this many days of it (a back-to-back or one night off)
_ST = {}


def _n(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def states(now_iso, games, rows=None):
    """{team id: {"rnet": takeaways minus giveaways a road game, "rn": road games, "n": box games, "pct": its place in
    the league (0 = the sloppiest), "last": (start of its last boxed game, shots against in it)}} - the NHL this season
    before `now_iso`, regular season only. `games` says who was the road team; a row it can't place is skipped."""
    key = (now_iso[:13], id(rows) if rows is not None else 0, len(games or {}))
    if key in _ST:
        return _ST[key]
    if rows is None:
        import sports_roster as sr
        try:
            rows = sr.team_rows("nhl")
        except Exception:                                    # noqa: BLE001
            rows = []
    y, mo = int(now_iso[:4]), int(now_iso[5:7])
    season0 = f"{y if mo >= 7 else y - 1}-07-01"
    acc = {}
    for r in sorted(rows, key=lambda r: r.get("start") or ""):
        st_ = r.get("start") or ""
        if not (season0 <= st_ < now_iso):
            continue
        g = (games or {}).get(r.get("gid")) or {}
        if not g or str(g.get("stype") or "2") != "2":
            continue
        tm = r.get("teams") or {}
        if len(tm) != 2:
            continue
        (ta, sa), (tb, sb) = tm.items()
        for me, mine, theirs in ((str(ta), sa, sb), (str(tb), sb, sa)):
            gv, tk, shots = _n(mine.get("giveaways")), _n(mine.get("takeaways")), _n(theirs.get("shotsTotal"))
            a = acc.setdefault(me, {"n": 0, "rn": 0, "rnet": 0.0, "last": None})
            if gv is not None and tk is not None:
                a["n"] += 1
                if str(g.get("away")) == me:
                    a["rn"] += 1
                    a["rnet"] += tk - gv
            a["last"] = (st_, shots)
    teams = {}
    for t, a in acc.items():
        v = {"n": a["n"], "rn": a["rn"], "last": a["last"]}
        if a["n"] >= MIN_G and a["rn"] >= MIN_ROAD:
            v["rnet"] = a["rnet"] / a["rn"]
        teams[t] = v
    read = [v["rnet"] for v in teams.values() if "rnet" in v]
    if len(read) >= MIN_TEAMS:
        for v in teams.values():
            if "rnet" in v:
                v["pct"] = sum(1 for x in read if x < v["rnet"]) / (len(read) - 1)
    _ST.clear()
    _ST[key] = teams
    return teams


def sloppy(st, team):
    """True = the league's bottom fifth in takeaways minus giveaways on the road, False = not, None = unread."""
    v = (st or {}).get(str(team))
    if not v or v.get("pct") is None:
        return None
    return v["pct"] <= FIFTH


def shelled(st, team, start_iso):
    """True = gave up SHELLED_SHOTS+ shots in its last game and plays again within SHELLED_DAYS; None = unread."""
    v = (st or {}).get(str(team))
    if not v or not v.get("last") or v["last"][1] is None:
        return None
    try:
        a = datetime.fromisoformat(str(v["last"][0]).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    days = (b - a).total_seconds() / 86400.0
    return v["last"][1] >= SHELLED_SHOTS and 0 < days <= SHELLED_DAYS
