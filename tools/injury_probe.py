"""Which public sources have college football availability data? (10/2: ESPN's feed covered 3 teams.) Tries each and
reports whether today's known names show up. Read only. Writes results/injury_probe.txt."""
import os
import urllib.request

NAMES = ["Terry", "Koby Howard", "Crothers", "Laws", "Granville", "Minicucci", "Dixson", "Lagg"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
URLS = {
    "espn league feed": "https://site.api.espn.com/apis/site/v2/sports/football/college-football/injuries",
    "espn game summary (Pitt@VT)": "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=401858245",
    "espn team VT": "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/259/injuries",
    "espn core VT": "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/teams/259/injuries",
    "cbs ncaaf injuries": "https://www.cbssports.com/college-football/injuries/",
    "covers ncaaf injuries": "https://www.covers.com/sport/football/ncaaf/injuries",
    "rotowire cfb": "https://www.rotowire.com/cfootball/injury-report.php",
    "acc availability": "https://theacc.com/news/2026/10/1/football-acc-football-availability-reports.aspx",
    "acc site search": "https://theacc.com/sports/football",
    "big ten availability": "https://bigten.org/fb/availability-report/",
    "ncaa availability": "https://www.ncaa.com/news/football/article/2025-08-01/college-football-availability-reports",
    "action network cfb injuries": "https://www.actionnetwork.com/ncaaf/injury-report",
    "fox game (Pitt@VT)": "https://www.foxsports.com/college-football/pittsburgh-panthers-vs-virginia-tech-hokies-oct-02-2026-game-boxscore-43426",
}
out = []
for name, url in URLS.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            body = r.read().decode("utf-8", "replace")
        hits = [n for n in NAMES if n in body]
        out.append(f"{name}: {r.status} {len(body):,} bytes - names found: {hits or 'none'}")
    except Exception as e:                                   # noqa: BLE001
        out.append(f"{name}: FAILED {str(e)[:100]}")
txt = "\n".join(out)
os.makedirs("results", exist_ok=True)
open("results/injury_probe.txt", "w").write(txt + "\n")
print(txt)
