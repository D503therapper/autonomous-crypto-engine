"""Probe candidate public endpoints from the GitHub runner; print HTTP status and a snippet.
Used to pick working listing/announcement sources (the sandbox can't reach them)."""
import json
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CANDIDATES = [
    ("cryptocom v1 announcements", "https://api.crypto.com/v1/public/get-announcements", {}),
    ("cryptocom v1 announcements list/spot", "https://api.crypto.com/v1/public/get-announcements?category=list&product_type=Spot", {}),
    ("cryptocom exchange announcements list", "https://api.crypto.com/exchange/v1/public/get-announcements?category=list", {}),
    ("upbit announcements (browser headers)", "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade",
     {"Origin": "https://upbit.com", "Referer": "https://upbit.com/"}),
    ("upbit notices", "https://api-manager.upbit.com/api/v1/notices?page=1&per_page=20&thread_name=general",
     {"Origin": "https://upbit.com", "Referer": "https://upbit.com/"}),
    ("upbit markets (KRW list diff)", "https://api.upbit.com/v1/market/all", {}),
    ("kraken blog feed", "https://blog.kraken.com/feed", {}),
    ("kraken assets api (list diff)", "https://api.kraken.com/0/public/Assets", {}),
    ("kraken asset pairs api (list diff)", "https://api.kraken.com/0/public/AssetPairs", {}),
    ("coinbase products api (list diff)", "https://api.exchange.coinbase.com/products", {}),
    ("coinbase status atom", "https://status.exchange.coinbase.com/history.atom", {}),
    ("binance exchangeInfo (list diff)", "https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT", {}),
    ("binance announcements catalog 48", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20", {}),
    ("binance.us exchangeInfo", "https://api.binance.us/api/v3/exchangeInfo", {}),
    ("gemini symbols (list diff)", "https://api.gemini.com/v1/symbols", {}),
    ("okx instruments (list diff)", "https://www.okx.com/api/v5/public/instruments?instType=SPOT", {}),
    ("bybit instruments (list diff)", "https://api.bybit.com/v5/market/instruments-info?category=spot", {}),
    ("reddit json", "https://www.reddit.com/r/CryptoMoonShots/new.json?limit=5", {}),
    ("reddit old json", "https://old.reddit.com/r/CryptoMoonShots/new.json?limit=5", {}),
    ("goplus", "https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses=0x6982508145454ce325ddbe47a25d4ec3d2311933", {}),
    ("honeypot.is", "https://api.honeypot.is/v2/IsHoneypot?address=0x6982508145454ce325ddbe47a25d4ec3d2311933&chainID=1", {}),
    ("rugcheck", "https://api.rugcheck.xyz/v1/tokens/EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm/report/summary", {}),
]

for name, url, extra in CANDIDATES:
    h = {"User-Agent": UA, "Accept": "application/json, text/xml, */*"}
    h.update(extra)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=15) as r:
            body = r.read(400).decode("utf-8", "replace")
            print(f"{r.status} {name}\n    {url}\n    {body[:300]!r}")
    except Exception as e:
        print(f"ERR {name}\n    {url}\n    {e}")
