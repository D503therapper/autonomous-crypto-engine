"""🧪 THE LEAD TRACKER (the owner, 10/1: "you said the dog rule isn't proven - keep a tracker to see if we can prove
your theory. This tracker is for you, not the dashboard"). Every board run logs, for EVERY side on the day's slate
(picked or not), which of the unproven leads fired and its price at that moment. After the games, each lead is graded
at 1 unit at that price - won-lost, units, ROI - so a lead earns full weight once it proves itself, or gets cut.
Files: data/sports/lead_tracker.json (rows) and data/sports/lead_record.json (the grades)."""
import json
import os

import sports_data as sd

PATH = os.path.join(sd.DATA, "lead_tracker.json")
RECORD = os.path.join(sd.DATA, "lead_record.json")


def tags(c, sports):
    """The leads firing on one candidate side (moneylines)."""
    if c.get("market") != "ml":
        return []
    try:                                                     # the sharp-money signals, any side (the owner, 10/1: "the
        import sports_breakdown                              # smart money looks to be on the Browns - track it")
        sp_ = sports_breakdown.public_split(c)
    except Exception:                                        # noqa: BLE001
        sp_ = None
    sharp = []
    if sp_ and sp_[0] is not None and sp_[1] is not None:
        if sp_[1] - sp_[0] >= 10:
            sharp.append("money 10+ over tickets")
        if sp_[0] >= 70:
            sharp.append("70%+ of tickets")
        if sp_[0] < 50 and (c.get("drift") or 0) <= -0.02:
            sharp.append("reverse line move to it")
    t, lg, mo = [], c.get("league"), c.get("dog_more") or {}
    if c.get("outshot_me"):                                  # 10/8 study (built as a weight): its own live record
        t.append("NHL side outshot 40+ last game (fade)")
    if c.get("outshot_opp"):
        t.append("NHL side vs a team outshot 40+")
    dog = c.get("odds", 0) >= 100
    if dog:
        try:
            sc = round(sports.dog_score(c), 2)
        except Exception:                                    # noqa: BLE001
            sc = None
        if sc is not None:
            if lg == "nfl" and sc >= sports.DOG_GATE:
                t.append("dog score NFL 8+")
            if lg == "nhl" and sc >= sports.NHL_DOG_GATE:
                t.append("dog score NHL 6+")
            if lg == "nhl" and 0 < sc < sports.NHL_DOG_GATE:
                t.append("hockey dog score 0-6")
            if lg == "ncaaf" and sc >= sports.NCAAF_DOG_GATE:
                t.append("dog score college 4+")
        for k, name in (("bye", "off a bye"), ("mnf", "Monday night dog"), ("neutral", "neutral-site dog")):
            if mo.get(k):
                t.append(name)
        if (mo.get("win_pct") or 0) >= 0.70 and lg == "ncaaf":
            t.append(".700 college dog")
        if (mo.get("win_streak") or 0) >= 3 and lg == "nfl":
            t.append("NFL dog 3+ win streak")
        try:
            if sports.sharp_dog(c):
                t.append("sharp dog: line to it + money over tickets")
        except Exception:                                    # noqa: BLE001
            pass
        try:                                             # the owner, 10/1 (the Jaguars): "if the engine's right,
            own = (c["edge_own"] + 1) / c["dec"]         # it beat the line - it should believe in itself." Track every
            if own - (c.get("p_market") or 1) >= 0.12:   # dog the engine's own read likes 12+ pts over the line
                t.append("engine read 12+ over the line (believe it?)")
        except (KeyError, TypeError, ZeroDivisionError):
            pass
        if c.get("dh_game2"):
            t.append("MLB doubleheader game-2 dog")
        if lg == "nfl" and mo.get("last_pts") is not None and mo["last_pts"] <= 10:
            t.append("NFL dog scored 10 or fewer last game")
        if c.get("opp_sv_slump"):
            t.append("NHL dog vs a slumping goalie (fade)")
        if c.get("west_trip_dog"):
            t.append("East home dog vs West favorite (fade)")
        if c.get("key_out_me") and lg in ("nfl", "ncaaf"):
            t.append("football dog, key player out (fade)")
        g4 = mo.get("go4_gap")
        if g4 is not None:
            import sports_go4
            if g4 <= sports_go4.GAP_LO:
                t.append("timid 4th-down dog (fade)")
            elif g4 >= sports_go4.GAP_HI:
                t.append("bold 4th-down dog")
    else:
        if lg == "nhl" and c.get("w_p") is not None:
            t.append("hockey fav weighed UP" if c["w_p"] > (c.get("p_market") or 0) else "hockey fav weighed DOWN (fade)")
        if any("West Coast favorite" in r for r in c.get("reasons") or []):
            t.append("West Coast road fav in the East")
        if c.get("hoops_inside"):
            t.append("hoops fav wins inside")
        if any("12+ innings" in r for r in c.get("reasons") or []):
            t.append("MLB scoring-drought fav")
    return t + sharp


def load():
    try:
        return json.load(open(PATH))
    except (OSError, ValueError):
        return []


def log(day_iso, cands, sports):
    """Add today's firing leads (once per game side per day - the first look the board run took)."""
    rows = load()
    have = {(r["day"], r["game_id"], r["side"]) for r in rows}
    added = 0
    for c in cands:
        key = (day_iso, c.get("game_id"), c.get("side"))
        if key in have:
            continue
        tg = tags(c, sports)
        if not tg:
            continue
        rows.append({"day": day_iso, "game_id": c["game_id"], "league": c.get("league"), "side": c.get("side"),
                     "team": c.get("team"), "odds": c.get("odds"), "tags": tg})
        have.add(key)
        added += 1
    if added:
        with open(PATH + ".tmp", "w") as f:
            json.dump(rows, f)
        os.replace(PATH + ".tmp", PATH)
    return added


def grade(games):
    """Grade every logged row with a final score: per lead, W-L, units at 1u, ROI. Writes lead_record.json."""
    rec = {}
    for r in load():
        g = games.get(r["game_id"]) or {}
        if g.get("status") != "final":
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_:
            continue
        won = (hs > as_) == (r["side"] == "home")
        o = r.get("odds") or 100
        net = (o / 100 if o > 0 else 100 / -o) if won else -1.0
        for t in r["tags"]:
            x = rec.setdefault(t, {"w": 0, "l": 0, "units": 0.0})
            x["w" if won else "l"] += 1
            x["units"] = round(x["units"] + net, 3)
    for x in rec.values():
        n = x["w"] + x["l"]
        x["roi"] = round(x["units"] / n, 3) if n else 0.0
    with open(RECORD + ".tmp", "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    os.replace(RECORD + ".tmp", RECORD)
    return rec
