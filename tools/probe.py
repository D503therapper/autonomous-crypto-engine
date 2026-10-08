"""Probe DexScreener tokens/v1 from the GitHub runner (10-07 20:00: held-coin price answers came back empty)."""
import json
import urllib.request

UA = "Mozilla/5.0"
pf = json.load(open("data/dex/dex_hunter/portfolio.json"))["positions"]
st = json.load(open("data/dex/state.json"))["passed"]


def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
            b = r.read().decode("utf-8", "replace")
            try:
                j = json.loads(b)
                n = len(j) if isinstance(j, list) else (len(j.get("pairs") or []) if isinstance(j, dict) else "?")
            except ValueError:
                n = "not json"
            return f"{r.status} n={n} {b[:160]!r}"
    except Exception as e:
        return f"ERR {e}"


for chain in ("solana", "ethereum"):
    held = sorted({p["addr"] for p in pf.values() if p["chain"] == chain})
    want = sorted(set(held) | {c["addr"] for c in st.values() if c["chain"] == chain})[:30]
    print(f"{chain} all {len(want)}:", get(f"https://api.dexscreener.com/tokens/v1/{chain}/{','.join(want)}"))
    for a in held:
        print(f"  {a}:", get(f"https://api.dexscreener.com/tokens/v1/{chain}/{a}"))
    for a in want:
        if a not in held:
            r = get(f"https://api.dexscreener.com/tokens/v1/{chain}/{a}")
            if not r.startswith("200 n=1") and "n=0" not in r[:12]:
                print(f"  passed {a}:", r[:120])
print("pairs endpoint:", get("https://api.dexscreener.com/latest/dex/pairs/solana/" + next(p["pair"] for p in pf.values() if p["chain"] == "solana")))
