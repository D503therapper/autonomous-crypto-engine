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
        "?dates={y}&seasontype={t}&week={w}&groups={grp}&limit=1000")
DAY = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
       "?dates={d}&groups={grp}&limit=1000")
# Run 1 (10/1): groups=80 (all of FBS) gives only ~25 games a Saturday now - so ask conference by conference:
# ACC, Big 12, Big Ten, SEC, Pac-12, C-USA, MAC, Mountain West, Sun Belt, American, FBS independents.
CONFS = (1, 4, 5, 8, 9, 12, 15, 17, 37, 151, 18)


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
    for grp in (80, 90) + CONFS:
        print(f"probe 2025 week 2, groups={grp}:", len(get(WEEK.format(y=2025, t=2, w=2, grp=grp)) or []))
    rows = []
    for y in (2024, 2025):
        for t, n in ((2, 16), (3, 1)):
            for w in range(1, n + 1):
                for grp in CONFS:
                    rows += get(WEEK.format(y=y, t=t, w=w, grp=grp)) or []
        print(f"{y}: {len(rows)} rows so far", flush=True)
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
