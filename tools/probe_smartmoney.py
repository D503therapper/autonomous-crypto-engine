"""Smart-money feasibility probe + collector (runs on GitHub Actions; the sandbox can't reach market data).

Part A: which free, keyless endpoints give per-trade WALLET addresses (Solana RPC, GeckoTerminal trades, DexScreener,
pump.fun, Birdeye, Helius, Solscan, SolanaFM, Blockscout for Base/Ethereum)? Status, payload shape, rate limits.
Part B: for the entry events in tools/smartmoney_sample.json (the consolidated study's pool-sequential trades, with
their simulated outcome), collect the BUYER wallets of (1) the hour before the +10% trigger and (2) the earliest
trades after launch, where a free source reaches them.  Raw data -> results/smartmoney_raw.json.gz (analysed offline
by the research session); the text log -> results/probe_smartmoney.txt.  Read-only; the live engine is untouched."""
import calendar
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
T_START = time.time()
BUDGET = float(os.environ.get("SM_BUDGET_MIN", "80")) * 60
SOL_RPCS = ["https://api.mainnet-beta.solana.com", "https://solana-rpc.publicnode.com", "https://solana.drpc.org"]
BS = {"base": "https://base.blockscout.com", "eth": "https://eth.blockscout.com"}
V4_PM = {"base": "0x498581ff718922c3f8e6a244956af099b2652b2b", "eth": "0x000000000004444c5dc75cb358380d2e3de08a90"}
STATS = {}
PARTS = set(os.environ.get("SM_PARTS", "probe,evm,sol").split(","))


def left():
    return BUDGET - (time.time() - T_START)


def req(url, data=None, n=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            st, hd = r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        body, st, hd = e.read().decode("utf-8", "replace"), e.code, dict(e.headers or {})
    except Exception as e:
        body, st, hd = repr(e), 0, {}
    host = url.split("/")[2]
    s = STATS.setdefault(host, {"n": 0, "err": 0, "429": 0, "sec": 0.0})
    s["n"] += 1
    s["sec"] += time.time() - t
    s["429"] += st == 429
    s["err"] += st != 200
    return st, (body if n is None else body[:n]), hd


def show(title, url, data=None, n=1500, headers=None):
    st, txt, hd = req(url, data, None, headers)
    rl = {k: v for k, v in hd.items() if "rate" in k.lower() or "limit" in k.lower() or k.lower() in ("retry-after", "server", "cf-ray")}
    print(f"\n--- {title}\n    {url}{'  ' + data.decode()[:300] if data else ''}\n    HTTP {st}  bytes {len(txt)}  {rl}\n    {txt[:n]}")
    sys.stdout.flush()
    time.sleep(1.2)
    return st, txt


def rpc(u, method, params, tries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for k in range(tries):
        st, txt, hd = req(u, body)
        if st == 200:
            try:
                j = json.loads(txt)
            except Exception:
                j = {}
            if "result" in j:
                return j["result"]
            if "error" in j and "429" not in str(j["error"]) and "rate" not in str(j["error"]).lower():
                return {"__error": j["error"]}
        time.sleep(min(20, 2 * 2 ** k) if st in (429, 0, 503, 502) or st == 200 else 1)
    return None


# ============================================================================ Part A: probe
def part_a(sample):
    pools = sample["pools"]
    sol = [p for p in pools.values() if p["net"] == "solana"]
    pump = next((p for p in sol if p["token"].endswith("pump")), sol[0])
    s0 = sol[-1]
    base = next(p for p in pools.values() if p["net"] == "base" and len(p["pool"]) == 42)
    print(f"sample pools: solana {pump['sym']} {pump['pool']} (mint {pump['token']}); base {base['sym']} {base['pool']}")

    print("\n==================== GeckoTerminal trades (tx_from_address)")
    st, txt = show("GT trades solana", f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pump['pool']}/trades", n=1200)
    try:
        d = json.loads(txt)["data"]
        ts = [x["attributes"]["block_timestamp"] for x in d]
        print(f"    -> {len(d)} trades, newest {ts[0] if ts else None}, oldest {ts[-1] if ts else None}; attributes: {sorted(d[0]['attributes'])}")
    except Exception as e:
        print("    parse:", repr(e))
    show("GT trades with before_timestamp (historical?)",
         f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pump['pool']}/trades?before_timestamp={int(time.time()) - 10 * 86400}", n=400)
    show("GT trades base", f"https://api.geckoterminal.com/api/v2/networks/base/pools/{base['pool']}/trades?trade_volume_in_usd_greater_than=0", n=600)
    ok = 0
    t = time.time()
    for i in range(12):
        st, _, hd = req(f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{s0['pool']}/trades")
        ok += st == 200
    print(f"    GT burst: 12 calls in {time.time() - t:.1f}s -> {ok} x 200 (documented free limit ~30/min)")
    time.sleep(5)

    print("\n==================== DexScreener (no documented trader API)")
    show("DexScreener pair", f"https://api.dexscreener.com/latest/dex/pairs/solana/{pump['pool']}", n=700)
    show("DexScreener io trade log (undocumented)", f"https://io.dexscreener.com/dex/log/amm/v4/pumpswap/all/solana/{pump['pool']}?q=So11111111111111111111111111111111111111112", n=400)

    print("\n==================== pump.fun frontend API")
    for u in (f"https://frontend-api-v3.pump.fun/trades/all/{pump['token']}?limit=5&offset=0&minimumSize=0",
              f"https://frontend-api.pump.fun/trades/all/{pump['token']}?limit=5&offset=0&minimumSize=0",
              f"https://frontend-api-v3.pump.fun/coins/{pump['token']}"):
        show("pump.fun", u, n=900)

    print("\n==================== keyed-in-docs APIs, tried WITHOUT a key")
    show("Birdeye txs", f"https://public-api.birdeye.so/defi/txs/token?address={pump['token']}&limit=5", n=300, headers={"x-chain": "solana"})
    show("Helius enhanced txs", f"https://api.helius.xyz/v0/addresses/{pump['pool']}/transactions", n=300)
    show("Solscan public v1", f"https://public-api.solscan.io/token/holders?tokenAddress={pump['token']}&limit=5", n=300)
    show("Solscan pro v2", f"https://pro-api.solscan.io/v2.0/token/defi/activities?address={pump['token']}&page_size=10", n=300)
    show("Solscan web api", f"https://api-v2.solscan.io/v2/token/transfer?address={pump['token']}&page=1&page_size=10", n=300)
    show("SolanaFM", f"https://api.solana.fm/v0/accounts/{pump['pool']}/transfers?limit=5", n=300)
    show("Moralis sol (no key)", f"https://solana-gateway.moralis.io/token/mainnet/{pump['token']}/swaps", n=300)

    print("\n==================== Solana public RPCs")
    for u in SOL_RPCS:
        t = time.time()
        r = rpc(u, "getSignaturesForAddress", [pump["pool"], {"limit": 1000}], tries=1)
        n = len(r) if isinstance(r, list) else r
        span = (r[0].get("blockTime"), r[-1].get("blockTime")) if isinstance(r, list) and r else None
        print(f"\n--- {u} getSignaturesForAddress(pool, 1000): {n if isinstance(n, int) else str(n)[:300]} in {time.time() - t:.1f}s, blockTime span {span}")
        if isinstance(r, list) and r:
            tx = rpc(u, "getTransaction", [r[len(r) // 2]["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}], tries=1)
            if isinstance(tx, dict) and "meta" in tx:
                print(f"    getTransaction ok: keys {sorted(tx)}, signer {tx['transaction']['message']['accountKeys'][0]}, "
                      f"postTokenBalances {json.dumps(tx['meta'].get('postTokenBalances'))[:500]}")
            else:
                print(f"    getTransaction: {str(tx)[:300]}")
        time.sleep(2)
    # rate burst on the main RPC
    u = SOL_RPCS[0]
    t, codes = time.time(), []
    for i in range(25):
        st, txt, hd = req(u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [s0["pool"], {"limit": 1000}]}).encode())
        codes.append(st)
    print(f"\n    RPC burst getSignaturesForAddress x25: {time.time() - t:.1f}s, codes {codes}")
    time.sleep(10)

    print("\n==================== Blockscout (Base / Ethereum), etherscan-style")
    show("Base block by time", f"{BS['base']}/api?module=block&action=getblocknobytime&timestamp={int(time.time()) - 86400}&closest=before", n=300)
    show("Base tokentx asc (earliest transfers)", f"{BS['base']}/api?module=account&action=tokentx&contractaddress={base['token']}&sort=asc&page=1&offset=3", n=1500)
    t, codes = time.time(), []
    for i in range(20):
        st, _, _ = req(f"{BS['base']}/api?module=block&action=getblocknobytime&timestamp={int(time.time()) - 86400 * (i + 2)}&closest=before")
        codes.append(st)
    print(f"    Blockscout burst x20: {time.time() - t:.1f}s, codes {codes}")


# ============================================================================ Part B: collect buyer wallets
def bs_get(url, tries=6):
    """Blockscout allows ~10 calls/s in bursts, then 429: pace ~1.5/s and back off on 429 / errors."""
    txt = ""
    for k in range(tries):
        time.sleep(0.6)
        st, txt, _ = req(url, timeout=60)
        if st == 200:
            try:
                return json.loads(txt)
            except Exception:
                pass
        time.sleep(min(30, 2 * 2 ** k))
    return None


BASE_REF = {}


def bs_block(net, ts):
    if net == "base":                                    # Base: exactly one block per 2 s -> one reference lookup
        if not BASE_REF:
            j = bs_get(f"{BS[net]}/api?module=block&action=getblocknobytime&timestamp={int(time.time()) - 3600}&closest=before")
            b = int(j["result"]["blockNumber"])
            j2 = bs_get(f"{BS[net]}/api/v2/blocks/{b}")
            BASE_REF.update(b=b, t=calendar.timegm(time.strptime(j2["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")))
            print(f"  base block reference {BASE_REF}")
        return BASE_REF["b"] + int((ts - BASE_REF["t"]) // 2)
    j = bs_get(f"{BS[net]}/api?module=block&action=getblocknobytime&timestamp={int(ts)}&closest=before")
    try:
        return int(j["result"]["blockNumber"])
    except Exception:
        return None


def bs_transfers(net, token, b0, b1, sort="asc", pages=3):
    rows = []
    for page in range(1, pages + 1):
        url = (f"{BS[net]}/api?module=account&action=tokentx&contractaddress={token}&startblock={b0}&endblock={b1}"
               f"&sort={sort}&page={page}&offset=1000")
        j = bs_get(url)
        if j is None:
            rows.append(None)
            break
        got = j.get("result") or []
        if not isinstance(got, list):
            got = []
        rows += got
        if len(got) < 1000:
            break
    return rows


def evm_buys(rows, pool_addrs):
    """Per tx: if a known pool (or the v4 PoolManager) loses tokens, the addresses with a net inflow are buyers."""
    by = {}
    for r in rows:
        if r is None:
            continue
        try:
            v = int(r["value"])
        except Exception:
            continue
        h = r["hash"]
        d = by.setdefault(h, {"t": int(r["timeStamp"]), "f": {}})
        d["f"][r["from"].lower()] = d["f"].get(r["from"].lower(), 0) - v
        d["f"][r["to"].lower()] = d["f"].get(r["to"].lower(), 0) + v
    out = []
    zero = "0x0000000000000000000000000000000000000000"
    for h, d in by.items():
        if not any(d["f"].get(p, 0) < 0 for p in pool_addrs):
            continue
        for a, v in d["f"].items():
            if v > 0 and a not in pool_addrs and a != zero and a != "0x000000000000000000000000000000000000dead":
                out.append([d["t"], a, h[:18]])
    out.sort()
    return out


EVM_RPCS = {"base": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.llamarpc.com"],
            "eth": ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com", "https://cloudflare-eth.com"]}
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EVM_REF = {}
ERRS = {}


def evm_rpc(net, method, params):
    for k in range(3):
        if left() < 120:
            return None
        u = EVM_RPCS[net][k % len(EVM_RPCS[net])]
        r = rpc(u, method, params, tries=1)
        if r is not None and not (isinstance(r, dict) and "__error" in r):
            return r
        if isinstance(r, dict) and "__error" in r and method == "eth_getLogs":
            return r                                     # range / size error -> caller splits the range
        ERRS[(net, u.split("/")[2], method)] = str(r)[:160]
        time.sleep(1 + k)
    return None


def block_ts(net, b):
    r = evm_rpc(net, "eth_getBlockByNumber", [hex(b) if isinstance(b, int) else b, False])
    return (int(r["number"], 16), int(r["timestamp"], 16)) if isinstance(r, dict) and "number" in r else (None, None)


def evm_block(net, ts):
    """Block at or before ts: Base = exactly 2 s blocks from one reference; Ethereum = 12 s estimate + refinement."""
    if net not in EVM_REF:
        EVM_REF[net] = block_ts(net, "latest")
        print(f"  {net} reference block {EVM_REF[net]}")
    b0, t0 = EVM_REF[net]
    if b0 is None:
        return None
    if net == "base":
        return b0 + int((ts - t0) // 2)
    b = b0 + int((ts - t0) // 12)
    for _ in range(5):
        bb, tb = block_ts(net, b)
        if tb is None:
            return b
        d = int((ts - tb) // 12)
        if abs(d) <= 1:
            return b if tb <= ts else b - 1
        b += d
    return b


def evm_logs(net, token, b0, b1, depth=0):
    """Transfer logs of the token in [b0, b1], rows shaped like Blockscout tokentx; splits the range on errors."""
    r = evm_rpc(net, "eth_getLogs", [{"fromBlock": hex(b0), "toBlock": hex(b1), "address": token, "topics": [TRANSFER]}])
    if isinstance(r, list):
        rows = []
        for lg in r:
            tp = lg.get("topics") or []
            if len(tp) < 3 or not lg.get("data") or lg["data"] == "0x":
                continue
            try:
                v = int(lg["data"][:66], 16)
            except ValueError:
                continue
            rows.append({"hash": lg["transactionHash"], "block": int(lg["blockNumber"], 16), "from": "0x" + tp[1][-40:],
                         "to": "0x" + tp[2][-40:], "value": str(v)})
        return rows
    ERRS[(net, "getLogs split", depth)] = str(r)[:200]
    if depth >= 3 or b1 <= b0 or left() < 120:
        return [None]
    m = (b0 + b1) // 2
    return evm_logs(net, token, b0, m, depth + 1) + evm_logs(net, token, m + 1, b1, depth + 1)


def stamp(rows, net, b0, t0):
    sec = 2 if net == "base" else 12
    for r in rows:
        if r is not None:
            r["timeStamp"] = str(int(t0 + (r["block"] - b0) * sec))
    return rows


def dump(raw):
    with gzip.open("results/smartmoney_raw.json.gz", "wt") as f:
        json.dump(raw, f, separators=(",", ":"))


def evm_diag():
    """Which public RPC answers eth_getLogs for a busy token over ~1 hour of blocks?"""
    toks = {"base": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "eth": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}
    for net, us in EVM_RPCS.items():
        for u in us:
            t = time.time()
            head = rpc(u, "eth_blockNumber", [], tries=1)
            if not isinstance(head, str):
                print(f"  diag {u}: eth_blockNumber {str(head)[:150]}")
                continue
            b = int(head, 16) - 20
            for span in (50, 300, 1800):
                t = time.time()
                r = rpc(u, "eth_getLogs", [{"fromBlock": hex(b - span), "toBlock": hex(b), "address": toks[net], "topics": [TRANSFER]}], tries=1)
                print(f"  diag {net} {u.split('/')[2]} getLogs {span} blocks: "
                      f"{(str(len(r)) + ' logs') if isinstance(r, list) else str(r)[:200]} in {time.time() - t:.1f}s")
                sys.stdout.flush()
                time.sleep(1)


def collect_evm(sample, raw):
    """Run 3: keyless public RPC eth_getLogs (Blockscout's keyless API allowed ~10 calls per ~20 min in run 2)."""
    evm_diag()
    pools = sample["pools"]
    evs = [e for e in sample["events"] if pools[e["k"]]["net"] in BS]
    done_launch = set()
    for n, e in enumerate(evs):
        if left() < (150 if PARTS == {"evm"} else 0.45 * BUDGET):
            print(f"  EVM: budget stop at {n}/{len(evs)}")
            break
        p = pools[e["k"]]
        net = p["net"]
        pa = {p["pool"].lower()} if len(p["pool"]) == 42 else set()
        pa.add(V4_PM[net])
        b0, b1 = evm_block(net, e["t"] - 3600), evm_block(net, e["t"])
        rec = {"k": e["k"], "t": e["t"], "src": "evm-rpc"}
        if b0 and b1:
            rows = evm_logs(net, p["token"], b0, b1)
            if None in rows:
                rec["err"] = "getLogs failed (part)"
            rows = stamp([r for r in rows if r is not None], net, b0, e["t"] - 3600)
            rec.update(n_transfers=len(rows), buys=evm_buys(rows, pa), blocks=[b0, b1])
        else:
            rec["err"] = "block lookup"
        raw["pre"].append(rec)
        c = p.get("created")
        if e["k"] not in done_launch and c and c < e["t"] - 3600:
            done_launch.add(e["k"])
            l0, l1 = evm_block(net, c), evm_block(net, c + 3600)
            if l0 and l1:
                rows = stamp([r for r in evm_logs(net, p["token"], l0, l1) if r is not None], net, l0, c)
                raw["launch"][e["k"]] = {"n_transfers": len(rows), "first_t": c, "buys": evm_buys(rows, pa)[:400], "src": "evm-rpc"}
        if n % 10 == 0:
            dump(raw)
        if n % 5 == 0:
            print(f"  EVM {n}/{len(evs)} {p['sym']} pre-hour buys {len(rec.get('buys', []))} transfers {rec.get('n_transfers')} "
                  f"err {rec.get('err')} elapsed {(time.time() - T_START) / 60:.1f}m {json.dumps({h: v for h, v in STATS.items() if 'rpc' in h or 'llama' in h or 'base.org' in h})}")
            sys.stdout.flush()


def sol_parse(tx, mint):
    try:
        keys = tx["transaction"]["message"]["accountKeys"]
        signer = keys[0] if isinstance(keys[0], str) else keys[0]["pubkey"]
        pre = {b["accountIndex"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in tx["meta"].get("preTokenBalances") or [] if b.get("mint") == mint}
        post = [(b["accountIndex"], b.get("owner"), float(b["uiTokenAmount"]["uiAmount"] or 0)) for b in tx["meta"].get("postTokenBalances") or [] if b.get("mint") == mint]
        for idx, owner, amt in post:
            if owner == signer and amt - pre.get(idx, 0.0) > 0:
                return signer, True
        return signer, False
    except Exception:
        return None, None


def collect_sol(sample, raw, u=SOL_RPCS[0], max_pages=40, per_window=40):
    """Per pool: one backward walk of getSignaturesForAddress(pool) from now through every event window (newest first),
    capped at max_pages x 1000 signatures; getTransaction for up to per_window signatures per window (even spread)."""
    pools = sample["pools"]
    by_pool = {}
    for e in sample["events"]:
        if pools[e["k"]]["net"] == "solana":
            by_pool.setdefault(e["k"], []).append(e)
    order = sorted(by_pool, key=lambda k: -max(e["t"] for e in by_pool[k]))
    for n, k in enumerate(order):
        if left() < 60:
            print(f"  SOL: budget stop at pool {n}/{len(order)}")
            break
        p = pools[k]
        evs = sorted(by_pool[k], key=lambda e: -e["t"])
        oldest_needed = evs[-1]["t"] - 3600
        sigs, before, pages, reached, ended = [], None, 0, None, False
        while pages < max_pages and left() > 60:
            opt = {"limit": 1000}
            if before:
                opt["before"] = before
            r = rpc(u, "getSignaturesForAddress", [p["pool"], opt])
            pages += 1
            if not isinstance(r, list) or not r:
                break
            sigs += [(x.get("blockTime") or 0, x["signature"]) for x in r if not x.get("err")]
            before = r[-1]["signature"]
            reached = r[-1].get("blockTime")
            if len(r) < 1000:
                ended = True
                break
            if reached and reached < oldest_needed:
                break
            time.sleep(0.25)
        info = {"pages": pages, "reached": reached, "n_sigs": len(sigs), "at_launch_end": ended}
        for e in evs:
            w = sorted(s for s in sigs if e["t"] - 3600 <= s[0] < e["t"])
            rec = {"k": k, "t": e["t"], "src": "solana-rpc", "walk": info, "n_sigs_window": len(w)}
            if not w and reached and reached > e["t"] - 3600:
                rec["err"] = "not reached"
                raw["pre"].append(rec)
                continue
            pick = w if len(w) <= per_window else [w[int(i * len(w) / per_window)] for i in range(per_window)]
            buys, nt = [], 0
            for bt, sg in pick:
                if left() < 60:
                    break
                tx = rpc(u, "getTransaction", [sg, {"encoding": "json", "maxSupportedTransactionVersion": 1}])
                nt += 1
                if isinstance(tx, dict) and "meta" in tx:
                    who, buy = sol_parse(tx, p["token"])
                    if buy:
                        buys.append([bt, who, sg[:16]])
                time.sleep(0.12)
            rec.update(buys=buys, n_tx_fetched=nt)
            raw["pre"].append(rec)
        # earliest trades after launch, when the walk reached the pool's first signature
        if ended and sigs:
            first = sorted(sigs)[:per_window]
            buys = []
            for bt, sg in first:
                if left() < 60:
                    break
                tx = rpc(u, "getTransaction", [sg, {"encoding": "json", "maxSupportedTransactionVersion": 1}])
                if isinstance(tx, dict) and "meta" in tx:
                    who, buy = sol_parse(tx, p["token"])
                    if buy:
                        buys.append([bt, who, sg[:16]])
                time.sleep(0.12)
            raw["launch"][k] = {"first_t": sorted(sigs)[0][0], "buys": buys, "src": "solana-rpc"}
        print(f"  SOL {n + 1}/{len(order)} {p['sym']}: pages {pages}, reached {reached}, sigs {len(sigs)}, events {len(evs)}, "
              f"elapsed {(time.time() - T_START) / 60:.1f}m, rpc {STATS.get(u.split('/')[2])}")
        sys.stdout.flush()


def main():
    sample = json.load(open("tools/smartmoney_sample.json"))
    print(f"probe_smartmoney {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}; budget {BUDGET / 60:.0f} min; "
          f"{len(sample['pools'])} pools, {len(sample['events'])} entry events")
    # Run 1 (2026-09-28 02:39, all parts, git history of results/probe_smartmoney.txt): Blockscout 429'd every block lookup
    # (no retry); Solana RPC walked 40 pages x 1000 signatures per pool = only the last ~1-24 hours of history.
    # Run 2: EVM only (SM_PARTS=evm), paced + retried, Base blocks computed from one reference (2 s blocks).
    # Run 2 result: keyless Blockscout = x-ratelimit-limit 10 per ~20 min window (359 of 400 calls 429): 36/237 events.
    # Run 3 stalled after the eth reference block (no output for 100 min, job timeout; getLogs retries x range splits).
    # Run 4: diag first, fewer retries / splits, budget checks inside every RPC call, raw dumped every 10 events.
    # Run 3: EVM via public RPC eth_getLogs (publicnode / base.org / llamarpc), launch window = first hour after pool creation.
    print(f"parts {sorted(PARTS)}")
    if "probe" in PARTS:
        try:
            part_a(sample)
        except Exception as e:
            print("part A crashed:", repr(e))
    raw = {"made": int(time.time()), "pre": [], "launch": {}}
    try:                                                 # keep the other chain family's records from the last run
        with gzip.open("results/smartmoney_raw.json.gz", "rt") as f:
            old = json.load(f)
        keep = "solana-rpc" if "sol" not in PARTS else ("blockscout" if "evm" not in PARTS else None)
        raw["pre"] = [r for r in old["pre"] if r.get("src") == keep]
        raw["launch"] = {k: v for k, v in old["launch"].items() if v.get("src") == keep}
        print(f"kept {len(raw['pre'])} pre / {len(raw['launch'])} launch records ({keep}) from {old.get('made')}")
    except Exception as e:
        print("no previous raw kept:", repr(e))
    if "evm" in PARTS:
        print("\n==================== Part B: EVM (Blockscout)")
        try:
            collect_evm(sample, raw)
        except Exception as e:
            print("EVM crashed:", repr(e))
    if "sol" in PARTS:
        print("\n==================== Part B: Solana (public RPC)")
        try:
            collect_sol(sample, raw)
        except Exception as e:
            print("SOL crashed:", repr(e))
    dump(raw)
    print("errors seen:", json.dumps({" | ".join(map(str, k)): v for k, v in ERRS.items()})[:3000])
    print(f"\nwrote results/smartmoney_raw.json.gz: {len(raw['pre'])} pre-trigger windows, {len(raw['launch'])} launch windows")
    print("host stats:", json.dumps(STATS))
    print(f"total {(time.time() - T_START) / 60:.1f} min")


if __name__ == "__main__":
    main()
