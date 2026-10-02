"""Where do the conferences post their availability reports? (10/2: ESPN's college feed covered 3 teams.) Fetches each
conference's football pages and lists every link that mentions availability / injury. Read only.
Writes results/injury_probe.txt."""
import os
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
PAGES = {
    "Big Ten": ["https://bigten.org/fb/", "https://bigten.org/fb/availability/", "https://bigten.org/sports/fb/availability-report/"],
    "ACC": ["https://theacc.com/sports/football", "https://theacc.com/sports/2026/9/1/football-availability.aspx",
            "https://theacc.com/news/football"],
    "SEC": ["https://www.secsports.com/football", "https://www.secsports.com/availability-report"],
    "Big 12": ["https://big12sports.com/sports/football", "https://big12sports.com/sports/football/availability"],
    "NCAA": ["https://www.ncaa.com/sports/football/fbs"],
    "SI VT": ["https://www.si.com/college/virginiatech/football/acc-reveals-initial-availability-report-for-virginia-tech-pitt-who-s-in-out-tbd-for-hokies-01m3q9npvztt"],
}
out = []
for conf, urls in PAGES.items():
    for url in urls:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                body = r.read().decode("utf-8", "replace")
            links = sorted(set(m for m in re.findall(r'href="([^"]+)"', body) if re.search(r"availab|injur", m, re.I)))
            out.append(f"{conf} {url}: {r.status} {len(body):,} bytes, {len(links)} links")
            out += [f"    {x}" for x in links[:25]]
            if "si.com" in url:
                i = body.find("Justin Terry")
                out.append(f"    'Justin Terry' at {i}: {re.sub('<[^>]+>', ' ', body[max(0, i - 300):i + 600])[:700] if i >= 0 else '-'}")
        except Exception as e:                               # noqa: BLE001
            out.append(f"{conf} {url}: FAILED {str(e)[:100]}")
txt = "\n".join(out)
os.makedirs("results", exist_ok=True)
open("results/injury_probe.txt", "w").write(txt + "\n")
print(txt)
