"""Probe 2 for the 0xb2000... Base tokens that dex.py marked "goplus unreachable" (BASECAT etc.): who creates them?
Run 1 (GoPlus code 3 partial data, honeypot.is STF revert, Blockscout runtime code "0xef") is in git history of
results/probe_goplus.txt. Output: results/probe_goplus.txt."""
import json
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TOKENS = [("BASECAT", "0xB2000000000000000000004c27f6523082f41D01", "0xe0734220e86dd58901fd04c88dee78c9f9db21274c771c3099f8b013613c87d0"),
          ("NVDAC", "0xb20000000000000000000078ee7ce2fE4908108C", None),
          ("BLUECHIP", "0xB200000000000000000000cFbdF64a8706a94a01", None),
          ("BRETT (normal)", "0x532f27101965dd16442E59d40670FaF5eBB142E4", None)]
RPCS = ["https://mainnet.base.org", "https://base-rpc.publicnode.com"]
BS = "https://base.blockscout.com"


def req(url, data=None, n=2500):
    try:
        h = {"User-Agent": UA, "Accept": "application/json"}
        if data is not None:
            h["Content-Type"] = "application/json"
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")[:n]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:n]
    except Exception as e:
        return 0, repr(e)


def show(title, url, data=None, n=2500):
    st, txt = req(url, data, n)
    print(f"\n--- {title}\n    {url}{'  ' + data.decode() if data else ''}\n    HTTP {st}\n    {txt}".replace("\n    {", "\n    {"))
    time.sleep(1.5)
    return txt


def rpc(method, params):
    for u in RPCS:
        show(f"RPC {method}", u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), 1200)


for name, a, pair_tx in TOKENS:
    print(f"\n================ {name} {a}")
    rpc("eth_getCode", [a, "latest"])
    show("Blockscout first token transfers (oldest)", f"{BS}/api?module=account&action=tokentx&contractaddress={a}&sort=asc&page=1&offset=3", n=3000)
    show("Blockscout first logs of the token", f"{BS}/api?module=logs&action=getLogs&address={a}&fromBlock=0&toBlock=latest&page=1&offset=2", n=2500)
    show("GeckoTerminal token info", f"https://api.geckoterminal.com/api/v2/networks/base/tokens/{a}/info", n=2000)
    if pair_tx:
        txt = show("Blockscout pool creation tx", f"{BS}/api/v2/transactions/{pair_tx}", n=3000)
# first mint tx of BASECAT (from the oldest transfer above) is printed there; also look at a few 0xb2 tokens' tx summary
show("Blockscout search 0xb2000000", f"{BS}/api/v2/search?q=0xb2000000000000000000", n=3000)
