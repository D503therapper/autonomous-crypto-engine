"""Builds funnel_replay.py (the 10/30 funnel: the 10/27 script on today's code, plus thin / own_gap / hot_dog / the NBA
favorite play flags)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "funnel1027", "funnel_replay.py")).read()
src = src.replace("agent-a0088bb44e53199be", "agent-ae23cc9a369e50331")
src = src.replace('UNITS_DAY = "2026-10-27"', 'UNITS_DAY = "2026-10-30"')
src = src.replace('''    if c.get("odds", 0) >= 100:
        try:
            out["dog_score"]''', '''    try:
        out["thin"] = bool(sports.thin_edge(dict(d)))
    except Exception:               # noqa: BLE001
        out["thin"] = None
    try:
        out["own_gap"] = sports.hockey_own_gap(d)
    except Exception:               # noqa: BLE001
        out["own_gap"] = None
    try:
        out["hot_dog"] = bool(sports.hot_dog(dict(d))) if c.get("odds", 0) >= 100 else False
    except Exception:               # noqa: BLE001
        out["hot_dog"] = None
    try:
        sports.score_reason(d)
        out["n_reasons2"] = len(d.get("reasons") or [])
    except Exception:               # noqa: BLE001
        out["n_reasons2"] = None
    if c.get("odds", 0) >= 100:
        try:
            out["dog_score"]''')
src = src.replace('''            for c in sports.dog_plays(cands, avoid):
                chosen.setdefault((c["game_id"], c["side"], c["market"]), ("dogplay", c))
                avoid.add(c["game_id"])''', '''            for c in sports.dog_plays(cands, avoid):
                chosen.setdefault((c["game_id"], c["side"], c["market"]), ("dogplay", c))
                avoid.add(c["game_id"])
            try:
                for c in sports.nba_fav_plays(cands, avoid):
                    chosen.setdefault((c["game_id"], c["side"], c["market"]), ("nbafav", c))
                    avoid.add(c["game_id"])
            except Exception as e:  # noqa: BLE001
                print("nbafav failed", str(e)[:80], flush=True)''')
src = src.replace('''        if kind:
            u = units({"dogplay": "play"}.get(kind, kind), c)''', '''        if kind:
            u = units({"dogplay": "play", "nbafav": "play"}.get(kind, kind), c)
            if kind == "nbafav":
                u = sports.NBA_FAV_UNITS''')
assert src.count("thin") >= 2 and "nbafav" in src and "agent-ae23cc9a369e50331" in src
open(os.path.join(HERE, "funnel_replay.py"), "w").write(src)
print("ok")
