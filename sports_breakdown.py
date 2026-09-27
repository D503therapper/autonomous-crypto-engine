"""The full breakdown behind a pick: the facts the engine weighed, in plain words, frozen at posting time.
Shown on the dashboard behind a "Full breakdown" tap."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_model as sm

PT = ZoneInfo("America/Los_Angeles")


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _team_games(fin, tid):
    return [g for g in fin if tid in (g["home"], g["away"])]


def _line(g, tid):
    """'W 27-20 vs Lions' from tid's point of view."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    res = "W" if us > them else "L" if us < them else "T"
    return f"{res} {us}-{them} {'vs' if home else '@'} {opp}"


def _season(games_of_team, before):
    """This season's games: walk back until a break of 75+ days (the off-season)."""
    out = []
    last = before
    for g in reversed(games_of_team):
        t = _t(g["start"])
        if (last - t).days > sm.BREAK_DAYS:
            break
        out.append(g)
        last = t
    return list(reversed(out))


def _record(gs, tid):
    w = sum(1 for g in gs if _line(g, tid).startswith("W"))
    lo = sum(1 for g in gs if _line(g, tid).startswith("L"))
    t = len(gs) - w - lo
    return f"{w}-{lo}" + (f"-{t}" if t else "")


def _streak(gs, tid):
    """'won 5 straight' / 'lost 3 straight' / ''."""
    if not gs:
        return ""
    last = _line(gs[-1], tid)[0]
    n = 0
    for x in reversed(gs):
        if _line(x, tid)[0] != last:
            break
        n += 1
    if n < 2 or last == "T":
        return ""
    return f"{'won' if last == 'W' else 'lost'} {n} straight"


def _names(rows, k=3):
    names = [n for n, _, _ in rows[:k]]
    more = len(rows) - len(names)
    return ", ".join(names) + (f" +{more} more" if more > 0 else "")


def breakdown(leg, games, elo, injuries):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
    ours, theirs = _team_games(fin, tid), _team_games(fin, oid)
    s_ours, s_theirs = _season(ours, start), _season(theirs, start)
    out = []

    # form
    rec_us = f"{us} are {_record(s_ours, tid)}" if s_ours else f"{us} are just getting started"
    heat_us = _streak(ours, tid)
    if heat_us.startswith("won"):
        rec_us += f" and on a {heat_us.split()[1]}-game heater"
    line = rec_us + "."
    if s_theirs:
        heat_them = _streak(theirs, oid)
        line += f" {them} are {_record(s_theirs, oid)}" + (f" and ice cold (lost {heat_them.split()[1]} straight)"
                                                              if heat_them.startswith("lost") else "") + "."
    out.append("🔥 " + line)

    # strength
    e = elo.get(lg)
    if e is not None:
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0)
        if gap > 60:
            out.append(f"💪 {us} are straight up the better team right now.")
        elif gap > 15:
            out.append(f"💪 {us} are the better squad, even if it's closer than it looks.")
        elif gap < -15:
            out.append(f"🐺 {them} look better on paper — that's exactly why we're getting this juicy price on {us}.")
        else:
            out.append("⚖️ Pretty even matchup, so we're riding the better number.")

    # talk our talk when the other side's been bad (only when the numbers back it up)
    if s_theirs:
        w = sum(1 for x in s_theirs if _line(x, oid).startswith("W"))
        cold = _streak(theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        if (len(s_theirs) >= 3 and w / len(s_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420:
            rec = _record(s_theirs, oid)
            lines = [f"🗑️ {them} have been complete ass lately — {rec} and it ain't getting prettier.",
                     f"🗑️ Straight up, {them} are trash right now ({rec}).",
                     f"🗑️ {them} can't get out of their own way" + (f" — lost {n_cold} straight." if n_cold >= 2 else f" ({rec}).")]
            out.append(lines[sum(map(ord, g["id"])) % len(lines)])

    # last games
    if ours:
        last_us = _line(ours[-1], tid)
        txt = f"📅 Last time out: {us} {'took care of business' if last_us[0] == 'W' else 'took an L'} ({last_us})"
        if theirs:
            last_them = _line(theirs[-1], oid)
            txt += f", {them} {'won' if last_them[0] == 'W' else 'took an L'} ({last_them})"
        out.append(txt + ".")

    # head to head
    h2h = [x for x in ours if oid in (x["home"], x["away"])]
    if h2h:
        last3 = h2h[-3:]
        w = sum(1 for x in last3 if _line(x, tid).startswith("W"))
        if 2 * w >= len(last3):
            out.append(f"🆚 {us} own this matchup — won {w} of the last {len(last3)}." if len(last3) > 1
                       else f"🆚 {us} got 'em last time: {_line(h2h[-1], tid)}.")

    # home / road
    out.append(f"🏟️ Home cookin' for {us}." if side == "home" else f"🧳 {us} on the road — doesn't scare us.")

    # rest
    if ours and theirs:
        d_us, d_them = (start - _t(ours[-1]["start"])).days, (start - _t(theirs[-1]["start"])).days
        if d_them <= 1 < d_us:
            out.append(f"😴 {them} played yesterday — tired legs. {us} are fresh.")
        elif d_us - d_them >= 2:
            out.append(f"🛌 {us} are the more rested squad.")

    # pitchers
    if lg == "mlb" and (g.get("sp_home") or g.get("sp_away")):
        out.append(f"⚾ On the bump: {g.get('sp_' + side) or 'TBA'} for {us}, {g.get('sp_' + other) or 'TBA'} for {them}.")

    # injuries
    inj = (injuries or {}).get(lg)
    if inj:
        ours_out, theirs_out = sd.team_injuries(inj, tid, us), sd.team_injuries(inj, oid, them)
        key_them = sd.team_key_out(inj, oid, them, lg)
        if key_them:
            out.append(f"🚑 {them} are rolling without their starting {key_them[0][1]} ({key_them[0][0]}).")
        if theirs_out and len(theirs_out) > len(ours_out):
            out.append(f"🚑 {them} are hella banged up ({_names(theirs_out)}).")
        elif not ours_out:
            out.append(f"✅ {us} are healthy — nobody important sitting.")

    # sharp money
    op, now = sm._int(g.get(f"ml_{side}_open")), sm._int(g.get(f"ml_{side}"))
    if op is not None and now is not None and op != now and sd.implied(now) > sd.implied(op):
        out.append(f"💰 Sharp money is on us: {us} opened {_am(op)}, now {_am(now)}. The pros are hammering this side.")

    # bottom line
    need, have = 1 / leg["dec"], leg["p"]
    bet = f"{us} {leg['line']:+g}" if leg["market"] == "spread" else us
    if _odds_words(need) != _odds_words(have):
        out.append(f"✅ Bottom line: Vegas has {bet} ({_am(leg['odds'])}) priced like {_odds_words(need)}. "
                   f"The engine sees {_odds_words(have)}. That's the value — trust the algorithm.")
    else:
        out.append(f"✅ Bottom line: Vegas has {bet} ({_am(leg['odds'])}) priced like {_odds_words(need)}, "
                   f"but everything above tips it our way. Small edge, real edge — trust the algorithm.")
    return out


def _odds_words(p):
    """0.5 -> 'a coin flip', 0.62 -> 'about 6 in 10', 0.3 -> 'about 3 in 10'."""
    if abs(p - 0.5) < 0.03:
        return "a coin flip"
    n = round(p * 10)
    if n <= 1:
        return f"about 1 in {round(1 / p)}"
    return f"about {n} in 10"
