"""WHO'S BETTING WHO: the public splits (% of bets and % of money on each side) + THE RIGGED STUDY.

Action Network publishes, for every game, what share of the tickets and what share of the money sits on each side of
the moneyline, the spread and the total (the same numbers Google shows). The engine reads them for today's games
every run, and keeps the history (NBA/MLB/NHL/college hoops from 2024 on, football by week) to answer one question:

  When the public piles on one side, who wins - Vegas or the public?

For every finished game with splits: the public side (70%+ of the bets), did it win / cover, and what betting WITH
them or AGAINST them made at the real price. Also the big-bettor split: when the money % is way higher than the
bet % on a side (fewer bets, bigger bets - the sharps), how does that side do? Learned on older games, checked on
newer ones it never saw. A spot is PROVEN only if it made money on both halves and luck can't explain it.
History: data/sports/public.json (the backfill workflow). Today's games: data/sports/public_live.json (every run).
The study: data/sports/rigged.json."""
import json
import re
import math
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "public.json")
LIVE = os.path.join(sd.DATA, "public_live.json")
STUDY = os.path.join(sd.DATA, "rigged.json")
AN2 = "https://api.actionnetwork.com/web/v2/scoreboard/{lg}?bookIds=15&{q}{extra}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "application/json"}
START = date(2024, 1, 1)                   # splits before this aren't published (checked league by league)
FOOTBALL = {"nfl": (("reg", 18), ("post", 5)), "ncaaf": (("reg", 15), ("post", 1))}
FOOTBALL_FROM = 2019
HEAVY = 70                                 # "the public is all over it" = 70%+ of the bets on one side
SHARP_GAP = 15                             # money % at least 15 points above bet % = the bigger bettors
MIN_N, Z = 150, 1.64


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return json.load(r)


def parse(payload):
    """[{start, home_full, away_full, season, week, splits}] - splits keyed like 'ml_home_t' (tickets %) / '_m' (money %)."""
    out = []
    for g in payload.get("games") or []:
        teams = {t.get("id"): t for t in g.get("teams") or []}
        home, away = teams.get(g.get("home_team_id")), teams.get(g.get("away_team_id"))
        ev = (((g.get("markets") or {}).get("15") or {}).get("event") or {})
        if not home or not away or not g.get("start_time") or not ev:
            continue
        s = {}
        for mk, key in (("moneyline", "ml"), ("spread", "sp"), ("total", "tot")):
            for o in ev.get(mk) or []:
                bi, side = o.get("bet_info") or {}, o.get("side")
                if side not in ("home", "away", "over", "under"):
                    continue
                s[f"{key}_{side}_t"] = (bi.get("tickets") or {}).get("percent")
                s[f"{key}_{side}_m"] = (bi.get("money") or {}).get("percent")
                s[f"{key}_{side}_odds"] = o.get("odds")
                if mk != "moneyline":
                    s[f"{key}_{side}_line"] = o.get("value")
        if not any((s.get(k) or 0) > 0 for k in ("ml_home_t", "ml_away_t", "sp_home_t", "sp_away_t")):
            continue                                        # no splits published for this game
        out.append({"start": g["start_time"][:16] + "Z", "home_full": home.get("full_name") or "",
                    "away_full": away.get("full_name") or "", "season": g.get("season"), "week": g.get("week"),
                    "splits": s})
    return out


YAHOO = {"nfl": "nfl", "ncaaf": "college-football", "nba": "nba", "ncaab": "college-basketball", "mlb": "mlb", "nhl": "nhl"}
YAHOO_URL = "https://sports.yahoo.com/{p}/odds/"


def yahoo_games(html):
    """Yahoo Sports' odds page -> its games (the JSON the page is built from)."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    txt = "".join(json.loads('"' + c + '"') for c in chunks)
    m = re.search(r'\{"games":\s*\[', txt)
    if not m:
        return []
    return json.JSONDecoder().raw_decode(txt[m.start():])[0].get("games") or []


def yahoo_rows(games_json):
    """Yahoo games -> [{home_full, away_full, splits}] - % of BETS only (Yahoo shows no money %), pregame markets.
    (Yahoo's numbers come from Action Network too: a second door to the same splits when Action Network's own
    feed turns us away.)"""
    out = []
    for g in games_json:
        slug = str(((g.get("alias") or {}).get("url") or "")).rstrip("/").split("/")[-1]
        slug = re.sub(r"-\d+$", "", slug)                      # "philadelphia-phillies-atlanta-braves"
        hid, aid = (g.get("homeTeam") or {}).get("teamId"), (g.get("awayTeam") or {}).get("teamId")
        s, home_city = {}, None
        for b in g.get("bets") or []:
            if b.get("eventState") != "PREGAME":
                continue
            key = {"MONEY_LINE": "ml", "POINT_SPREAD": "sp", "SPREAD": "sp", "TOTAL": "tot", "OVER_UNDER": "tot"}.get(b.get("type"))
            for o in b.get("options") or []:
                if o.get("wagerPercentage") in (None, "") or not key:
                    continue
                tid = (o.get("teamIds") or [None])[0]
                side = "home" if tid == hid else "away" if tid == aid else \
                    ("over" if str(o.get("name", "")).lower().startswith("over") else
                     "under" if str(o.get("name", "")).lower().startswith("under") else None)
                if side is None:
                    continue
                if side == "home" and key == "ml":
                    home_city = str(o.get("name") or "")
                s[f"{key}_{side}_t"] = round(float(o["wagerPercentage"]))
                s[f"{key}_{side}_m"] = None
                s[f"{key}_{side}_odds"] = o.get("americanOdds")
        if not home_city or not s.get("ml_home_t"):
            continue
        k = slug.find(home_city.lower().replace(" ", "-"))
        if k <= 0:
            continue
        out.append({"home_full": slug[k:].replace("-", " "), "away_full": slug[:k].strip("-").replace("-", " "),
                    "splits": {**s, "src": "yahoo"}})
    return out


def yahoo_match(games, league, rows, now=None):
    """{our game id: splits} for Yahoo rows - same teams, a game of ours still to start in the next 36 hours."""
    now = now or datetime.now(timezone.utc)
    lo, hi = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"), (now + timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
    out = {}
    for r in rows:
        for g in games.values():
            if g["league"] == league and g.get("status") == "pre" and lo <= (g.get("start") or "")[:16] <= hi and \
                    sd._same(g["home_name"], r["home_full"]) and sd._same(g["away_name"], r["away_full"]):
                out[g["id"]] = r["splits"]
                break
    return out


def yahoo_splits(games, league):
    req = urllib.request.Request(YAHOO_URL.format(p=YAHOO[league]), headers={**UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=25) as r:
        html = r.read().decode("utf-8", "ignore")
    return yahoo_match(games, league, yahoo_rows(yahoo_games(html)))


def fetch_day(league, day):
    return parse(_get(AN2.format(lg=league, q=f"date={day:%Y%m%d}", extra=sd.AN_EXTRA.get(league, ""))))


def fetch_week(league, season, typ, week):
    rows = parse(_get(AN2.format(lg=league, q=f"season={season}&week={week}&seasonType={typ}",
                                 extra=sd.AN_EXTRA.get(league, ""))))
    return [r for r in rows if r["season"] == season]       # the feed hands back the current week if it ignores us


def match(games, league, rows):
    """{our game id: splits} - same teams, start within 3 hours."""
    idx = {}
    for g in games.values():
        if g["league"] == league and g.get("start"):
            idx.setdefault(g["start"][:10], []).append(g)
    out = {}
    for r in rows:
        t = datetime.strptime(r["start"], "%Y-%m-%dT%H:%MZ")
        for g in (g for d in {(t + timedelta(days=k)).strftime("%Y-%m-%d") for k in (-1, 0, 1)} for g in idx.get(d, [])):
            if abs((datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M") - t).total_seconds()) <= 3 * 3600 and \
                    sd._same(g["home_name"], r["home_full"]) and sd._same(g["away_name"], r["away_full"]):
                out[g["id"]] = r["splits"]
                break
    return out


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(path, d):
    with open(path + ".tmp", "w") as f:
        json.dump(d, f, separators=(",", ":"), sort_keys=True)
    os.replace(path + ".tmp", path)


def backfill(games, budget_s=1500, today=None):
    """Walk the history a chunk at a time (a day or a football week per call), remembering what's done."""
    pub = _load(PATH)
    done = set(pub.get("_done") or [])
    data = pub.get("games") or {}
    today = today or datetime.now(timezone.utc).date()
    t0, n = time.time(), 0
    jobs = []
    for lg, weeks in FOOTBALL.items():
        for season in range(FOOTBALL_FROM, today.year + (1 if today.month >= 8 else 0)):
            jobs += [(lg, (season, typ, w)) for typ, top in weeks for w in range(1, top + 1)]
    d = START
    while d < today:
        jobs += [(lg, d) for lg in ("nba", "mlb", "nhl", "ncaab")]
        d += timedelta(days=1)
    for lg, when in jobs:
        key = f"{lg}:{when if isinstance(when, date) else ':'.join(map(str, when))}"
        if key in done:
            continue
        if time.time() - t0 > budget_s:
            break
        try:
            rows = fetch_week(lg, *when) if isinstance(when, tuple) else fetch_day(lg, when)
        except Exception as e:                               # noqa: BLE001 - a bad day never stops the walk
            if "404" not in str(e):
                print(f"   {key}: {str(e)[:80]}")
                continue
            rows = []
        data.update(match(games, lg, rows))
        done.add(key)
        n += 1
        if n % 200 == 0:
            _save(PATH, {"games": data, "_done": sorted(done)})
            print(f"   backfill: {n} pages, {len(data)} games with splits", flush=True)
    _save(PATH, {"games": data, "_done": sorted(done)})
    left = sum(1 for lg, w in jobs if f"{lg}:{w if isinstance(w, date) else ':'.join(map(str, w))}" not in done)
    print(f"backfill: {n} pages this run, {len(data)} games with splits, {left} pages left")
    return left


def refresh_today(games, now=None):
    """Today's + tomorrow's splits for every league with games coming up (every engine run)."""
    now = now or datetime.now(timezone.utc)
    live = _load(LIVE)
    keep = {k: v for k, v in live.items() if k in games and games[k]["status"] == "pre"}
    soon = {g["league"] for g in games.values() if g["status"] == "pre"
            and g["start"][:10] in {(now + timedelta(days=k)).strftime("%Y-%m-%d") for k in (0, 1)}}
    for lg in sorted(soon):
        failed = False
        for k in (0, 1):
            day = (now + timedelta(days=k)).date()
            try:
                if lg in FOOTBALL:
                    rows = parse(_get(AN2.format(lg=lg, q=f"date={day:%Y%m%d}", extra=sd.AN_EXTRA.get(lg, ""))))
                else:
                    rows = fetch_day(lg, day)
                keep.update(match(games, lg, rows))
            except Exception as e:                           # noqa: BLE001
                print(f"   public splits {lg} {day}: {str(e)[:80]}")
                failed = True
            if lg in FOOTBALL:
                break                                        # football pages are by week: one call covers it
        if failed and lg in YAHOO:                           # Action Network turned us away: Yahoo's page instead
            try:
                got = yahoo_splits(games, lg)
                keep.update({k2: v for k2, v in got.items() if k2 not in keep})
                print(f"   public splits {lg}: Action Network down - {len(got)} games from Yahoo")
            except Exception as e:                           # noqa: BLE001
                print(f"   public splits {lg} (Yahoo): {str(e)[:80]}")
    _save(LIVE, keep)
    return keep


def splits_for(game_id, live=None, hist=None):
    live = _load(LIVE) if live is None else live
    if game_id in live:
        return live[game_id]
    hist = _load(PATH) if hist is None else hist
    return (hist.get("games") or {}).get(game_id)


# ---------------------------------------------------------------- the rigged study
def _z(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v / n) if v else 0.0


def events(games, pub):
    """[(start, league, market, spot, profit on $100 betting WITH that spot's side, won)] for every final game."""
    out = []
    for gid, s in pub.items():
        g = games.get(gid)
        if not g or g["status"] != "final":
            continue
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        for mk, sides in (("ml", ("home", "away")), ("sp", ("home", "away")), ("tot", ("over", "under"))):
            t = {x: s.get(f"{mk}_{x}_t") for x in sides}
            m = {x: s.get(f"{mk}_{x}_m") for x in sides}
            if any(v is None for v in t.values()) or sum(t.values()) == 0:
                continue
            for x in sides:
                odds = sm._int(s.get(f"{mk}_{x}_odds")) or (sm._int(g.get(f"ml_{x}")) if mk == "ml" else -110)
                if not odds:
                    continue
                if mk == "ml":
                    if hs == as_:
                        continue
                    won = (hs > as_) == (x == "home")
                elif mk == "sp":
                    line = sm._num(s.get(f"sp_{x}_line"))
                    if line is None:
                        continue
                    diff = (hs - as_ if x == "home" else as_ - hs) + line
                    if diff == 0:
                        continue
                    won = diff > 0
                else:
                    line = sm._num(s.get(f"tot_{x}_line"))
                    if line is None or hs + as_ == line:
                        continue
                    won = (hs + as_ > line) == (x == "over")
                profit = (odds if odds > 0 else 10000 / -odds) if won else -100.0
                spots = []
                if (t[x] or 0) >= HEAVY:
                    spots.append("public 70%+ of bets")
                if (t[x] or 0) >= 80:
                    spots.append("public 80%+ of bets")
                if (t[x] or 0) <= 100 - HEAVY:
                    spots.append("against the public (<=30% of bets)")
                if m[x] is not None and (m[x] or 0) - (t[x] or 0) >= SHARP_GAP:
                    spots.append("big bettors (money way over bets)")
                if mk == "ml" and odds > 0 and (t[x] or 0) <= 100 - HEAVY:
                    spots.append("dog the public is fading")
                for sp_ in spots:
                    out.append((g["start"], g["league"], mk, sp_, profit, won))
    return sorted(out)


def study(games, path=STUDY):
    pub = dict((_load(PATH).get("games") or {}))
    ev = events(games, pub)
    half = ev[len(ev) // 2][0] if ev else ""
    cells = {}
    for start, lg, mk, spot, profit, won in ev:
        for key in (f"all|{mk}|{spot}", f"{lg}|{mk}|{spot}"):
            c = cells.setdefault(key, {"old": [], "new": [], "w": []})
            (c["old"] if start < half else c["new"]).append(profit)
            c["w"].append(won)
    res = {}
    for k, c in sorted(cells.items()):
        a, b = c["old"], c["new"]
        roi_a, roi_b = (sum(a) / (100 * len(a)) if a else 0.0), (sum(b) / (100 * len(b)) if b else 0.0)
        z = _z(a + b)
        res[k] = {"n": len(a) + len(b), "win_rate": round(sum(c["w"]) / len(c["w"]), 3),
                  "roi_old": round(roi_a, 4), "roi_new": round(roi_b, 4), "z": round(z, 2),
                  "proven": len(a) >= MIN_N and len(b) >= MIN_N and roi_a > 0 and roi_b > 0 and z >= Z}
    out = {"cells": res, "games": len(pub), "proven": [k for k, v in res.items() if v["proven"]],
           "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    _save(path, out)
    return out


def load():
    return _load(STUDY)


def summary(st):
    lines = [f"rigged study: {st.get('games', 0)} games with public splits"]
    for k, v in (st.get("cells") or {}).items():
        if k.startswith("all|") or v["proven"]:
            lines.append(f"  {k}: {v['n']} bets, won {v['win_rate']:.0%}, profit {v['roi_old']:+.1%} older / "
                         f"{v['roi_new']:+.1%} newer (z {v['z']}){' PROVEN' if v['proven'] else ''}")
    lines.append("proven: " + (", ".join(st.get("proven") or []) or "none"))
    return lines


if __name__ == "__main__":
    games = sd.load_games()
    if "backfill" in sys.argv:
        backfill(games, budget_s=int(os.environ.get("PUBLIC_BUDGET_S", "1500")))
    print("\n".join(summary(study(games))))
