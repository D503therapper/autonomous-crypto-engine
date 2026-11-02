"""Readiness: the FULL BREAKDOWN card for every college hoops moneyline side on a day's slate (offline, injuries
stubbed as an empty report for every team). Prints each card and flags lines that lean on a 0-game season: a record
like 0-0 / 0-1, 'last game' facts from last season, 'None' / 'nan' / empty lines, too-short cards.
Usage: python cards.py YYYY-MM-DD [N]"""
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402
import sports_breakdown         # noqa: E402

day = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
games = sd.load_games()
ids = {}
for g in games.values():
    for s in ("home", "away"):
        ids.setdefault(g["league"], set()).add(g[s])
inj = {lg: {t: [] for t in ids.get(lg, ())} for lg in sd.LEAGUES}
model = sports._load("model.json", {"params": {}, "log": []})
sp.CACHE = sp.load()
sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
sports.load_states(games)
now = datetime(day.year, day.month, day.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
cands = [c for c in sports.candidates(games, model, now, day, inj) if c["league"] == "ncaab" and c["market"] == "ml"
         and -300 <= c["odds"] <= 350]
elo = sm.ratings(games, model)
BAD = [(re.compile(r"\b0-0\b"), "0-0 record"), (re.compile(r"\bNone\b|\bnan\b"), "None/nan"),
       (re.compile(r"last (game|time out|outing)", re.I), "last-game line"), (re.compile(r"\b0-[1-9]\b|\b[1-9]-0\b"), "tiny record"),
       (re.compile(r"(March|April|last season|NCAA Tournament)", re.I), "last-season fact")]
flags = {}
nlines = []
for c in cands[:N]:
    g = games[c["game_id"]]
    leg = dict(c)
    other = "away" if c["side"] == "home" else "home"
    leg["outs"], leg["opp_outs"] = [], []
    leg["is_lean"] = False
    try:
        bd = sports_breakdown.breakdown(leg, games, elo, inj, set())
    except Exception as e:                                   # noqa: BLE001
        print(f"!! {c['team']} vs {c['opp']}: breakdown CRASHED {type(e).__name__}: {e}")
        flags.setdefault("crash", []).append(c["team"])
        continue
    nlines.append(len(bd))
    print(f"\n== {c['team']} ({c['odds']:+}) vs {c['opp']} - {len(bd)} lines")
    for ln in bd:
        print("   ", ln)
        for rx, what in BAD:
            if rx.search(ln):
                flags.setdefault(what, []).append(f"{c['team']}: {ln[:140]}")
        if not ln.strip():
            flags.setdefault("empty line", []).append(c["team"])
print("\n\nSUMMARY:", len(nlines), "cards; lines per card min", min(nlines or [0]), "max", max(nlines or [0]))
for k, v in flags.items():
    print(f"\n{k}: {len(v)}")
    for x in v[:12]:
        print("   ", x)
