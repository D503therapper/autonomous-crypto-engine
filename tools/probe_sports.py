"""Probe: where can the engine see WHO the public is betting (tickets % / money %)? Action Network first
(the engine already reads its odds), a few URL shapes, today's MNF and a past week (for a history study)."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "application/json"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def hunt(o, path="", out=None, depth=0):
    out = [] if out is None else out
    if depth > 8 or len(out) > 40:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            if any(s in k.lower() for s in ("public", "ticket", "money", "bet_info", "percent", "handle", "consensus")):
                out.append(f"{path}/{k} = {str(v)[:240]}")
            hunt(v, f"{path}/{k}", out, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:4]):
            hunt(v, f"{path}[{i}]", out, depth + 1)
    return out


URLS = [
    "https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&date=20260928",
    "https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&bookIds=15,30,68,69,71,75&date=20260928",
    "https://api.actionnetwork.com/web/v2/scoreboard/nfl?bookIds=15,30&date=20260928",
    "https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&date=20251020",
    "https://api.actionnetwork.com/web/v1/scoreboard/mlb?period=game&date=20260927",
]
gid = None
for u in URLS:
    try:
        d = get(u)
        games = d.get("games") or []
        print(f"\n== {u}\n   games: {len(games)}; top keys: {list(games[0].keys()) if games else list(d.keys())}")
        if games and gid is None and "20260928" in u:
            gid = games[0].get("id")
        for line in hunt(games[:1]):
            print("  ", line)
    except Exception as e:                                   # noqa: BLE001
        print(f"\n== {u}\n   ERR {e}")
for u in ([f"https://api.actionnetwork.com/web/v1/games/{gid}", f"https://api.actionnetwork.com/web/v2/games/{gid}",
           f"https://api.actionnetwork.com/web/v1/games/{gid}/polls"] if gid else []):
    try:
        d = get(u)
        print(f"\n== {u}\n   top keys: {list(d.keys())[:40]}")
        for line in hunt(d):
            print("  ", line)
    except Exception as e:                                   # noqa: BLE001
        print(f"\n== {u}\n   ERR {e}")
for u in ["https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=401872963"]:
    try:
        d = get(u)
        print("\n== ESPN summary pickcenter/predictor")
        for line in hunt({"pickcenter": d.get("pickcenter"), "predictor": d.get("predictor"),
                          "againstTheSpread": d.get("againstTheSpread")}):
            print("  ", line)
        print("   predictor:", str(d.get("predictor"))[:300])
    except Exception as e:                                   # noqa: BLE001
        print("ESPN ERR", e)
