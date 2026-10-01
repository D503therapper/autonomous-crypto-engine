"""One-off (10/1 data audit): college football 2024 and 2025 have ~500 finished games each vs ~930 a season before.
Re-read both seasons from ESPN - day by day AND week by week (whichever gives more) - then attach Action Network's
closing / opening odds. Prints what it finds so the gap's cause shows in the log. Runs in GitHub Actions."""
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")
import sports_data as sd  # noqa: E402

WEEK = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
        "?dates={y}&seasontype={t}&week={w}&groups=80&limit=1000")


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return sd.parse_scoreboard("ncaaf", json.load(r))
    except Exception as e:                               # noqa: BLE001
        print(f"   miss {url[-70:]}: {str(e)[:80]}")
        return None


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    games = sd.load_games()
    before = {y: sum(1 for g in games.values() if g["league"] == "ncaaf" and g.get("status") == "final"
                     and g["start"][:4] == str(y) and g.get("stype") == "2") for y in (2023, 2024, 2025)}
    print("finished regular-season games before:", before)
    probe = date(2025, 9, 6)
    print("probe 2025-09-06 by day:", len(sd.fetch_day("ncaaf", probe) or []),
          "| 2025 week 2 by week:", len(get(WEEK.format(y=2025, t=2, w=2)) or []))
    rows = []
    for y in (2024, 2025):
        d = date(y, 8, 20)
        while d <= date(y + 1, 1, 25):
            rows += sd.fetch_day("ncaaf", d) or []
            d += timedelta(days=1)
        for t, n in ((2, 16), (3, 1)):
            for w in range(1, n + 1):
                rows += get(WEEK.format(y=y, t=t, w=w)) or []
    added = 0
    for r in rows:
        if r["id"] not in games:
            added += 1
        games[r["id"]] = sd.merge(games.get(r["id"]), r, now)
    print(f"ESPN rows read: {len(rows)}, new games: {added}")
    filled = 0
    for y in (2024, 2025):
        for typ, n in sd.AN_WEEKS["ncaaf"]:
            for w in range(1, n + 1):
                an = sd.fetch_an_day("ncaaf", (y, typ, w))
                if an:
                    filled += sd.attach_an(games, "ncaaf", an)
    print(f"games that got odds: {filled}")
    sd.save_games({k: g for k, g in games.items() if g["league"] == "ncaaf"})
    after = {y: sum(1 for g in games.values() if g["league"] == "ncaaf" and g.get("status") == "final"
                    and g["start"][:4] == str(y) and g.get("stype") == "2") for y in (2023, 2024, 2025)}
    print("finished regular-season games after:", after)


if __name__ == "__main__":
    main()
