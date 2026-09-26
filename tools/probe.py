"""Probe candidate public URLs from the GitHub runner; print HTTP status, content-type and a snippet."""
import urllib.request

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
R = "D503therapper/autonomous-crypto-engine"
CANDIDATES = [
    ("githack", f"https://raw.githack.com/{R}/main/docs/index.html"),
    ("githack cdn", f"https://rawcdn.githack.com/{R}/main/docs/index.html"),
    ("statically", f"https://cdn.statically.io/gh/{R}/main/docs/index.html"),
    ("jsdelivr", f"https://cdn.jsdelivr.net/gh/{R}@main/docs/index.html"),
    ("htmlpreview", f"https://htmlpreview.github.io/?https://github.com/{R}/blob/main/docs/index.html"),
    ("github pages", "https://d503therapper.github.io/autonomous-crypto-engine/"),
]
for name, url in CANDIDATES:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
            body = r.read(300).decode("utf-8", "replace")
            print(f"{r.status} {name} type={r.headers.get('Content-Type')} csp={r.headers.get('Content-Security-Policy','')[:80]!r}\n    {url}\n    {body[:120]!r}")
    except Exception as e:
        print(f"ERR {name}\n    {url}\n    {e}")
