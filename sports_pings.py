"""💰 Mid-day value plays (the owner, 10/1: "yes"): the board drops at 8 AM PT, the engine keeps checking the lines all
day, and a UNIT play it adds after the board is up gets ONE phone ping - sent only once the live dashboard shows it
(tools/early_ping.py). Leans never ping. The queue is written by the hourly run: every unit play marked `midday` that
went up since the last run's queue, so nothing rings twice and nothing gets missed between runs."""
import json
import os
from datetime import datetime, timedelta, timezone

import sports_data as sd

PATH = os.path.join(sd.DATA, "play_pings.json")
FRESH_MIN = 50                       # a queue older than this is a past run's: never re-sent
LOOKBACK = timedelta(hours=3)        # never a ping for a play that went up long ago (a first run / a missed push)


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _load(path):
    try:
        with open(path or PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def text(pk):
    """The push: the play, its price, its units, when it starts. Plain words."""
    import sports
    leg = pk["legs"][0]
    u = sports.units_for(pk)
    n = f"{int(u)}½" if u % 1 else f"{int(u)}"
    size = "½ unit" if u == 0.5 else f"{n} unit" + ("" if u == 1 else "s")      # (the cards' way: 1½ units, not 1.5u)
    t = _t(leg["start"]).astimezone(sports.PT)
    when = t.strftime("%-I:%M %p").replace(":00 ", " ")
    label = f"{sports.leg_label(leg)} {sports.fmt_american(leg['odds'])}"
    return (f"💰 NEW VALUE PLAY: {label}",
            f"{label} vs the {leg['opp']}, {size}. Starts at {when} PT. It's on the dashboard now.")


def queue(picks, now, path=None):
    """-> this run's pings: the `midday` unit plays posted since the last queue (at most LOOKBACK ago), written for
    tools/early_ping.py. Written every run, empty when there's nothing."""
    import sports
    last = _load(path).get("at")
    since = max(_t(last), now - LOOKBACK) if last else now - LOOKBACK
    out = []
    for pk in picks:
        if not pk.get("midday") or pk.get("lean") or pk.get("status") != "open" or len(pk.get("legs") or []) != 1:
            continue
        if not since < _t(pk["posted"]) <= now or sports.units_for(pk) <= 0:
            continue
        leg = pk["legs"][0]
        title, body = text(pk)
        out.append({"gid": leg["game_id"], "side": leg["side"], "title": title, "body": body,
                    "ref": f"play:{pk['date']}:{leg['game_id']}"})
    with open(path or PATH, "w") as f:
        json.dump({"at": now.strftime("%Y-%m-%dT%H:%MZ"), "pings": out}, f)
    return out


def pending(now, path=None):
    q = _load(path)
    return (q.get("pings") or []) if q.get("at") and now - _t(q["at"]) <= timedelta(minutes=FRESH_MIN) else []


def send_queued(page, now=None, path=None, send_fn=None):
    """-> the pings sent: a fresh queue only, and only once the live `page` shows every one of them (its card)."""
    now = now or datetime.now(timezone.utc)
    q = pending(now, path)
    if not q or not all(f'data-gid="{p["gid"]}" data-side="{p["side"]}"' in page for p in q):
        return []                    # not live yet: wait (the caller checks again)
    send_fn = send_fn or (lambda p: sd.web_push(None, p["title"], p["body"], ref=p["ref"]))
    for p in q:
        send_fn(p)
    return q
