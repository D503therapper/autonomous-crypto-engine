"""🎯 THE 6-COMPOUND CHALLENGE - TRACKING ONLY (the owner, 10/18: "the engine will give me a pick every day, its best
pick that's closest to even money or plus money value or a slight favorite. And our goal is to hit the 6-compound
challenge. But we're going to track it. I'm not going to do this yet.")

Every game day, once the 8 AM board is up, the engine names ONE pick: of the day's posted straight picks (Lock, Dog,
value plays, leans, night football) priced BAND_LO..BAND_HI, the one it gives the best shot to win. Wins ride: $START
on day one, the whole payout on the next pick; a loss resets to $START; a push carries the run to the next day. Six
straight wins = the challenge hit. Paper only - not on the dashboard, not in any record (the owner's call to go live).
File: data/sports/compound.json."""
import json
import os
from datetime import datetime

import sports_data as sd

PATH = os.path.join(sd.DATA, "compound.json")
FROM = "2026-10-18"           # the tracker starts here (the owner, 10/18)
BAND_LO, BAND_HI = -130, 150  # a slight favorite .. plus money ("closest to even money")
START = 500.0                 # the owner's stake (10/17: "if I started with 500")
GOAL = 6
KINDS = ("lock", "dog", "play", "lean", "night", "solo")
PICK_AFTER_HOUR_PT = 8        # the 8 AM board


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"days": []}


def save(st):
    with open(PATH, "w") as f:
        json.dump(st, f, indent=1)


def _win_p(leg):
    try:
        import sports
        return sports.read_of(leg) or leg.get("p") or 0.0
    except Exception:                                        # noqa: BLE001
        return leg.get("p") or 0.0


def choose(picks, day):
    """The day's challenge pick from the posted board: in the band, the best shot to win (ties: the bigger price)."""
    pool = []
    for p in picks:
        legs = p.get("legs") or []
        if p.get("date") != day or p.get("kind") not in KINDS or p.get("status") == "waiting" or len(legs) != 1:
            continue
        if (legs[0].get("market") or "ml") != "ml":         # (10/19: the Commanders SPREAD lean got named - the
            continue                                         # challenge is to WIN the game, moneylines only)
        odds = p.get("american") if p.get("american") is not None else legs[0].get("odds")
        if odds is None or not BAND_LO <= odds <= BAND_HI:
            continue
        pool.append((_win_p(legs[0]), odds, p))
    if not pool:
        return None
    wp, odds, p = max(pool, key=lambda x: (x[0], x[1]))
    l = p["legs"][0]
    return {"date": day, "kind": p.get("kind"), "game_id": l.get("game_id"), "side": l.get("side"),
            "team": l.get("team"), "opp": l.get("opp"), "league": l.get("league"), "odds": odds,
            "win_p": round(wp, 3), "result": None}


def _dec(odds):
    return 1 + (odds / 100 if odds > 0 else 100 / -odds)


def tally(days):
    """The run as it stands: wins in a row now, the bankroll riding, the best run, challenges hit."""
    streak, bank, best, hits = 0, START, 0, 0
    for d in days:
        r = d.get("result")
        if r == "won":
            streak += 1
            bank *= _dec(d["odds"])
            best = max(best, streak)
            if streak == GOAL:
                hits += 1
                streak, bank = 0, START                      # hit: cash it, start a new run
        elif r == "lost":
            streak, bank = 0, START
    return {"streak": streak, "bank": round(bank, 2), "best": best, "hits": hits,
            "record": f"{sum(d.get('result') == 'won' for d in days)}-{sum(d.get('result') == 'lost' for d in days)}"}


def sync(picks, now):
    """Name today's pick once the board is up, grade the open ones from the posted picks' results. Never raises."""
    try:
        import sports
        st = load()
        days = st.setdefault("days", [])
        local = now.astimezone(sports.PT)
        today = local.date().isoformat()
        if today >= FROM and local.hour >= PICK_AFTER_HOUR_PT and not any(d["date"] == today for d in days):
            c = choose(picks, today)
            if c:
                c["named"] = now.strftime("%Y-%m-%dT%H:%MZ")
                days.append(c)
        for d in days:
            if d.get("result"):
                continue
            for p in picks:
                l = (p.get("legs") or [{}])[0]
                if p.get("date") == d["date"] and l.get("game_id") == d["game_id"] and l.get("side") == d["side"] \
                        and l.get("result"):
                    d["result"] = {"void": "push"}.get(l["result"], l["result"])
                    break
        st["now"] = tally(days)
        save(st)
        return st
    except Exception as e:                                   # noqa: BLE001 - a tracker never stops the engine
        print(f"compound tracker failed: {str(e)[:80]}")
        return None
