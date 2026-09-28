"""Probe: where can the runner get tennis odds history? (tennis-data.co.uk blocks servers)"""
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
URLS = [
    "https://archive.org/wayback/available?url=tennis-data.co.uk/2024/2024.xlsx",
    "https://archive.org/wayback/available?url=www.tennis-data.co.uk/2019/2019.xlsx",
    "https://web.archive.org/cdx/search/cdx?url=tennis-data.co.uk/20*&limit=40&filter=statuscode:200&collapse=urlkey",
    "https://web.archive.org/web/20250701id_/http://www.tennis-data.co.uk/2024/2024.xlsx",
    "https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/172-2024/competitions/145649/odds",
    "https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/172-2019/competitions/98391/odds",
    "https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta/events/811-2026/competitions/184060/odds",
    "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/summary?event=145649",
    "https://www.kaggle.com/api/v1/datasets/download/hakeem/atp-and-wta-tennis-data",
    "https://huggingface.co/api/datasets?search=tennis&limit=20",
    "https://www.valuebetennis.com/en/guide/base-de-donnees-tennis.htm",
]
for u in URLS:
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
            b = r.read()
            print(f"== {u}\n{r.status} {len(b)}B {time.time() - t0:.1f}s {r.headers.get('Content-Type')}\n{b[:1500]!r}\n")
    except Exception as e:                                   # noqa: BLE001
        print(f"== {u}\nERR {time.time() - t0:.1f}s {e}\n")
