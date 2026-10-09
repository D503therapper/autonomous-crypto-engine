"""📰 Read public news / conference pages on GitHub's servers (10/2: Claude's sandbox can't open them, only see search
snippets - and a snippet can't prove which week an injury report is from). Usage: python tools/fetch_pages.py URL [URL ...]
or one URL per line in results/pages/urls.txt. Saves each page's readable text to results/pages/<n>.txt (the part with
the injury / availability words first) plus results/pages/index.txt. Public pages only - a plain request, nothing that
gets around a site's blocks. Read only."""
import html
import os
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
OUT = "results/pages"
KEY = re.compile(r"(availab|injur|questionable|doubtful|\bout\b|probable|game-time)", re.I)
# 10/2: Dr. Bob's free analysis (the capper benchmark - tracked, never copied): keep his leans, plays and margins.
PICKS = re.compile(r"(\blean|best bet|strong opinion|\bplay\b|predict|\bover\b|\bunder\b|[+-]\d+(\.5)?\b|\bATS\b)", re.I)


WHOLE = ("web.archive.org", "dailyfaceoff.com", "api-web.nhle.com", "site.api.espn.com/apis/site/v2/sports/hockey", "sportsoddshistory.com", "sports.core.api.espn.com", "cbssports.com/college", "rotowire.com/cfootball/injury-report", "rotowire.com/cbasketball/injury-report")   # (10/3: odds tables - a betting
#   ad's "not available in your state" tripped the injury filter and the whole futures table was dropped)


def key_for(url):
    if any(h in url for h in WHOLE):
        return None                                          # keep the whole page
    return PICKS if "drbobsports.com" in url else KEY


def text_of(body):
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", body)
    body = re.sub(r"(?s)<!--.*?-->", " ", body)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.split("\n")]
    return [x for x in lines if x]


def main(urls):
    os.makedirs(OUT, exist_ok=True)
    idx = []
    for n, url in enumerate(urls):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                raw = r.read().decode("utf-8", "replace")
                lines = text_of(raw)
            links = sorted({h for h in re.findall(r'href="([^"]+)"', raw) if re.search(r"availab|injur", h, re.I)})[:40]
            title = next((x for x in lines if len(x) > 25), "")[:150]
            hits = [i for i, x in enumerate(lines) if key_for(url) and key_for(url).search(x)]
            keep = sorted({j for i in hits for j in range(max(0, i - 3), min(len(lines), i + 4))}) \
                or range(len(lines))                         # (10/3: no injury / pick words - an odds table, a
            #                                                  futures board: keep the whole page)
            body = "\n".join(lines[j] for j in keep)[:30000]
            dates = sorted(set(re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2},? 20\d\d", " ".join(lines))))[:6]
            with open(os.path.join(OUT, f"{n:03d}.txt"), "w") as f:
                f.write(f"URL: {url}\nTITLE: {title}\nDATES SEEN: {dates}\n\n{body}\n")
                if links:                                    # (10/9: a team's news index - the links to its injury / availability posts)
                    f.write("\nLINKS:\n" + "\n".join(links) + "\n")
            idx.append(f"{n:03d} OK {len(body):,} chars  {url}")
        except Exception as e:                               # noqa: BLE001
            idx.append(f"{n:03d} FAILED {str(e)[:80]}  {url}")
    with open(os.path.join(OUT, "index.txt"), "w") as f:
        f.write("\n".join(idx) + "\n")
    print("\n".join(idx))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args and os.path.exists(os.path.join(OUT, "urls.txt")):
        args = [x.strip() for x in open(os.path.join(OUT, "urls.txt")) if x.strip().startswith("http")]
    main(args)
