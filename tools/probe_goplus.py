"""Probe GoPlus / honeypot.is / DexScreener / Blockscout from the GitHub runner for the 0xb2000... Base tokens
that dex.py marks "goplus unreachable" (BASECAT etc.) vs normal Base tokens. Output: results/probe_goplus.txt."""
import json
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TOKENS = [
    ("BASECAT", "0xB2000000000000000000004c27f6523082f41D01"),
    ("NVDAC", "0xb20000000000000000000078ee7ce2fE4908108C"),
    ("AAPLC", "0xb200000000000000000000C2e324d24d7eEcd1fb"),
    ("BLUECHIP", "0xB200000000000000000000cFbdF64a8706a94a01"),
    ("BRETT (normal)", "0x532f27101965dd16442E59d40670FaF5eBB142E4"),
    ("DEGEN (normal)", "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed"),
]


def get(url, n=1500):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, repr(e)


def jl(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None


def show(title, url, full=False):
    st, txt = get(url)
    j = jl(txt)
    print(f"\n--- {title}\n    {url}\n    HTTP {st}")
    if isinstance(j, dict):
        print(f"    top keys: {sorted(j)}")
        for k in ("code", "message", "msg", "status"):
            if k in j:
                print(f"    {k}: {j[k]!r}")
    print("    body: " + (txt if full else txt[:1500]).replace("\n", " "))
    time.sleep(2.5)
    return st, j


for name, a in TOKENS:
    print(f"\n================ {name} {a}")
    for label, addr in (("as-is", a), ("lower", a.lower())):
        st, j = show(f"GoPlus token_security 8453 ({label})",
                     f"https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses={addr}")
        res = (j or {}).get("result") if isinstance(j, dict) else None
        if isinstance(res, dict):
            print(f"    result type dict, keys: {list(res)}")
            for k, v in res.items():
                if isinstance(v, dict):
                    print(f"    [{k}] fields ({len(v)}): {sorted(v)}")
                    print(f"    [{k}] values: " + json.dumps({f: v[f] for f in sorted(v) if f not in ('holders', 'lp_holders', 'dex')})[:2500])
                    print(f"    [{k}] holders n={len(v.get('holders') or [])} lp_holders n={len(v.get('lp_holders') or [])} dex={json.dumps(v.get('dex'))[:600]}")
        else:
            print(f"    result: {type(res).__name__} {json.dumps(res)[:300] if res is not None else ''}")
    show("honeypot.is v2 IsHoneypot", f"https://api.honeypot.is/v2/IsHoneypot?address={a}&chainID=8453", full=True)
    show("honeypot.is v1 TopHolders", f"https://api.honeypot.is/v1/TopHolders?address={a}&chainID=8453")
    show("honeypot.is v1 GetContractVerification", f"https://api.honeypot.is/v2/GetContractVerification?address={a}&chainID=8453")
    show("DexScreener tokens", f"https://api.dexscreener.com/tokens/v1/base/{a}")
    show("Blockscout token", f"https://base.blockscout.com/api/v2/tokens/{a}")
    st, j = show("Blockscout address", f"https://base.blockscout.com/api/v2/addresses/{a}")
    if isinstance(j, dict) and j.get("creator_address_hash"):
        c = j["creator_address_hash"]
        show("Blockscout creator address", f"https://base.blockscout.com/api/v2/addresses/{c}")
        if j.get("creation_transaction_hash") or j.get("creation_tx_hash"):
            tx = j.get("creation_transaction_hash") or j.get("creation_tx_hash")
            show("Blockscout creation tx", f"https://base.blockscout.com/api/v2/transactions/{tx}")
    st, j = show("Blockscout smart-contract", f"https://base.blockscout.com/api/v2/smart-contracts/{a}")
    if isinstance(j, dict):
        print(f"    name={j.get('name')!r} verified={j.get('is_verified')} proxy={j.get('proxy_type')} impl={j.get('implementations')}")
        print(f"    abi functions: {sorted({x.get('name') for x in j.get('abi') or [] if isinstance(x, dict) and x.get('type') == 'function'})}")
