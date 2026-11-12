"""11/12 - THE LIVE CODE REPLAYED (the second check): python s13_live_replay.py 2025 - walks one past season (the start
year) day by day through the WIRED marks (sports.mark_ncaab_identity -> to_net, sports.mark_ncaab_cbb10 -> rust_home /
leader_road) with only the games BEFORE each day in the file, and grades what they flag at ESPN's close. It should
land on the study's cells for that season (lib.py's own walk): the proof the live code reads what the study read."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                 # (sports_data reads data/sports relative to the repo root)
from collections import defaultdict
import sports_data as sd
import sports
import sports_ncaab_knowledge as nk

season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
sports.CBB10_FROM = "2000-01-01"
OLD = os.environ.get("OLD_LEAGUES")                        # OLD_LEAGUES=1: the pre-11/12 league table (an older
if OLD:                                                    # season's schedule mixed in) - to show what the fix changed
    _conf = nk.conferences
    nk.conferences = lambda games, season, last=True: _conf(games, season, True)
games = {k: g for k, g in sd.load_games("ncaab").items() if g.get("league") == "ncaab"}
d = sd.decimal
lo, hi = f"{season}-10-01", f"{season + 1}-05-01"
days = defaultdict(list)
for gid, g in games.items():
    s = str(g.get("start") or "")
    if lo <= s < hi and g.get("status") == "final" and str(g.get("stype") or "2") == "2":
        days[sports.pt_day(g)].append(gid)
res = defaultdict(list)
t0 = time.time()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


for day in sorted(days):
    first = min(games[g]["start"] for g in days[day])
    view = {k: g for k, g in games.items() if g["start"] < first and g.get("status") == "final"}
    cands = []
    for gid in days[day]:
        g = games[gid]
        mh, ma, sp = num(g.get("ml_home")), num(g.get("ml_away")), num(g.get("spread_home"))
        hs, as_ = num(g.get("home_score")), num(g.get("away_score"))
        if not mh or not ma or hs is None or as_ is None or hs == as_:
            continue
        view[gid] = {**g, "status": "pre", "home_score": "", "away_score": ""}
        for side, odds in (("home", mh), ("away", ma)):
            cands.append({"league": "ncaab", "market": "ml", "odds": odds, "dec": d(odds), "p": 0.5, "side": side,
                          "game_id": gid, "start": g["start"], "reasons": [], "dog_ctx": {}, "edge_own": 0.0})
            if sp is not None:
                so = num(g.get("spread_home_odds" if side == "home" else "spread_away_odds")) or -110
                cands.append({"league": "ncaab", "market": "spread", "odds": so, "dec": d(so), "p": 0.5, "side": side,
                              "line": sp if side == "home" else -sp, "game_id": gid, "start": g["start"], "reasons": [],
                              "dog_ctx": {}, "edge_own": 0.0})
    if not cands:
        continue
    nk._MEMO.clear()
    nk._MEMO_NOW.clear()
    sports.mark_ncaab_identity(view, cands)
    sports.mark_ncaab_race(view, cands)                    # (the built 11/3 race dog - the same standings code)
    sports.mark_ncaab_cbb10(view, cands)
    for c in cands:
        g = games[c["game_id"]]
        m = float(g["home_score"]) - float(g["away_score"])
        if c["side"] == "away":
            m = -m
        if c["market"] == "ml":
            if sports.ncaab_to_match_dog(c) and c["odds"] <= 350:
                res["W1 the dog losing the turnover matchup by .05+ (ML)"].append((c["dec"] - 1) if m > 0 else -1.0)
            if c.get("race_dog") and 100 <= c["odds"] <= 350:
                res["(built 11/3) the race dog, Feb-Mar (ML)"].append((c["dec"] - 1) if m > 0 else -1.0)
        else:
            r = m + c["line"]
            if r == 0:
                continue
            p = (c["dec"] - 1) if r > 0 else -1.0
            for k, name in (("rust_home", "W2 the rusty home side (ATS)"), ("vs_rust_home", "W2 its visitor (ATS)"),
                            ("leader_road", "W3 the leader with a cushion on the road (ATS)"),
                            ("vs_leader_road", "W3 the home side across (ATS)")):
                if c.get(k):
                    res[name].append(p)
lines = [f"THE LIVE CODE REPLAYED, season {season}-{str(season + 1)[2:]}{' - OLD league table' if OLD else ''} ({time.time() - t0:.0f}s)"]
for k in sorted(res):
    v = res[k]
    lines.append(f"{k:52s} {sum(1 for x in v if x > 0)}-{sum(1 for x in v if x < 0)}  {sum(v) / len(v) * 100:+.1f}% on {len(v)}")
print("\n".join(lines))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"s13_live_replay_{season}{'_old' if OLD else ''}_out.txt"), "w").write("\n".join(lines) + "\n")
