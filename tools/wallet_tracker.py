"""Live wallet tracker (smart-money forward test; own workflow wallet_tracker.yml, never touches the live engine).

Each run picks up to MAX_POOLS pools the DEX hunter screened (any verdict) in the last 48 h (data/dex/screen.csv) or
holds now (data/dex/dex_hunter/portfolio.json), highest priority first: held > recent PASS > the rest, weighted by how
long since the pool was last polled here.  For each pool it reads GeckoTerminal /networks/{net}/pools/{pool}/trades
(keyless; the last 300 trades only, so pools must be polled regularly), >= GAP seconds between calls with a backoff on
429, and appends the trades it has not seen yet to data/dex/wallet_trades.csv.gz.

Output columns: time, chain, pool, token, sym, side, wallet, usd, price, tx
  time   block time UTC (ISO), chain = engine chain name (solana/base/ethereum/bsc), token = the pool token that the
  hunter screened (base token of the trade), side = buy/sell, wallet = tx_from_address, usd = volume_in_usd,
  price = token price in USD, tx = transaction hash.
Each run appends ONE new gzip member (gzip readers concatenate members transparently), so earlier bytes of the file
never change and git stores each version as a small delta.
State (data/dex/wallet_tracker_state.json): per pool the last poll time and the newest trade time seen; plus a capped
list of recently seen trade ids (dedupe of trades at/after the per-pool high-water mark).
Analysed later offline by smartmoney_study.py (research_log.md: re-run after ~4 weeks)."""
import calendar
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEX = os.path.join(ROOT, "data", "dex")
SCREEN = os.path.join(DEX, "screen.csv")
PORTFOLIO = os.path.join(DEX, "dex_hunter", "portfolio.json")
OUT = os.path.join(DEX, "wallet_trades.csv.gz")
STATE = os.path.join(DEX, "wallet_tracker_state.json")
COLS = ["time", "chain", "pool", "token", "sym", "side", "wallet", "usd", "price", "tx"]

GT = "https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pool}/trades"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NET = {"solana": "solana", "base": "base", "ethereum": "eth", "eth": "eth", "bsc": "bsc", "arbitrum": "arbitrum"}
MAX_POOLS = int(os.environ.get("WT_MAX_POOLS", "25"))
BUDGET = float(os.environ.get("WT_BUDGET_MIN", "8")) * 60
GAP = 2.1                        # seconds between GeckoTerminal calls (free limit ~30/min)
BACKOFF = (15, 30, 60)           # sleeps after successive 429s on one call
MAX_429 = 8                      # give up the run after this many 429s in total
LOOKBACK_H = 48
SEEN_CAP = 40000
POOL_TTL_H = 72                  # forget pools not selected for this long


def utc(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def parse_iso(s):
    """'2026-09-28T02:39:31Z' / '2026-09-28 08:42[:00]' (UTC) -> epoch seconds, or None."""
    s = (s or "").strip().replace("T", " ").rstrip("Z")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return calendar.timegm(time.strptime(s, fmt))
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------------------------- pool selection
def candidates(screen_rows, portfolio, now, lookback_h=LOOKBACK_H):
    """{key: {chain, pool, token, sym, held, passed_t, seen_t}} for pools screened in the last lookback_h or held."""
    out = {}
    for r in screen_rows:
        t = parse_iso(r.get("time"))
        chain, pool = (r.get("chain") or "").strip(), (r.get("pair") or "").strip()
        if t is None or now - t > lookback_h * 3600 or chain not in NET or not pool:
            continue
        c = out.setdefault(f"{chain}:{pool}", {"chain": chain, "pool": pool, "token": r.get("address", ""),
                                               "sym": r.get("symbol", ""), "held": False, "passed_t": None, "seen_t": t})
        c["seen_t"] = max(c["seen_t"], t)
        if (r.get("verdict") or "").upper() == "PASS":
            c["passed_t"] = max(c["passed_t"] or 0, t)
    for p in (portfolio or {}).get("positions", {}).values():
        chain, pool = p.get("chain", ""), p.get("pair", "")
        if chain not in NET or not pool:
            continue
        c = out.setdefault(f"{chain}:{pool}", {"chain": chain, "pool": pool, "token": p.get("addr", ""),
                                               "sym": p.get("sym", ""), "held": True, "passed_t": None, "seen_t": now})
        c["held"] = True
    return out


def priority(c, last_poll, now):
    """Hours since last poll (never polled = 48 h), times 4 if held, 2 if passed within 12 h, 1.5 if passed at all."""
    stale = min(LOOKBACK_H, (now - last_poll) / 3600) if last_poll else LOOKBACK_H
    w = 4 if c["held"] else 2 if c["passed_t"] and now - c["passed_t"] < 12 * 3600 else 1.5 if c["passed_t"] else 1
    return stale * w


def select(cands, state, now, n=MAX_POOLS):
    pools = state.get("pools", {})
    ranked = sorted(cands.items(), key=lambda kv: (-priority(kv[1], pools.get(kv[0], {}).get("polled"), now), kv[0]))
    return [dict(c, key=k) for k, c in ranked[:n]]


# ---------------------------------------------------------------------------------------------- fetch + parse
def http_get(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}),
                                    timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, repr(e)


def parse_trades(body, c):
    """GeckoTerminal trades JSON -> list of (trade_id, block_ts, row dict).  Skips malformed trades."""
    try:
        data = json.loads(body).get("data") or []
    except Exception:
        return []
    out = []
    tok = (c.get("token") or "").lower()
    for d in data:
        a = d.get("attributes") or {}
        side = a.get("kind")
        ts = parse_iso(a.get("block_timestamp"))
        tx = a.get("tx_hash") or ""
        wallet = a.get("tx_from_address") or ""
        if side not in ("buy", "sell") or ts is None or not tx or not wallet:
            continue
        to_a, from_a = a.get("to_token_address") or "", a.get("from_token_address") or ""
        if tok and to_a.lower() == tok:          # side from the screened token's point of view
            side = "buy"
        elif tok and from_a.lower() == tok:
            side = "sell"
        tok_addr = to_a if side == "buy" else from_a
        price = a.get("price_to_in_usd") if side == "buy" else a.get("price_from_in_usd")
        try:
            usd = float(a.get("volume_in_usd") or 0)
            px = float(price or 0)
        except ValueError:
            continue
        out.append((d.get("id") or f"{tx}:{side}:{wallet}", ts, {
            "time": utc(ts), "chain": c["chain"], "pool": c["pool"], "token": tok_addr or c.get("token", ""),
            "sym": c.get("sym", ""), "side": side, "wallet": wallet, "usd": f"{usd:.2f}", "price": f"{px:.6g}", "tx": tx}))
    return out


def new_trades(parsed, pstate, seen):
    """Keep trades at/after the pool's high-water mark whose id is unseen.  Mutates pstate['hw'] and seen."""
    hw = pstate.get("hw", 0)
    rows = []
    for tid, ts, row in sorted(parsed, key=lambda x: x[1]):
        if ts < hw or tid in seen:
            continue
        seen[tid] = 1
        rows.append(row)
    if parsed:
        pstate["hw"] = max(hw, max(ts for _, ts, _ in parsed))
    return rows


def fetch_pool(c, get, sleep, stats):
    """One trades call with 429 backoff.  Returns body or None."""
    url = GT.format(net=NET[c["chain"]], pool=c["pool"])
    for k in range(len(BACKOFF) + 1):
        st, body = get(url)
        stats["calls"] += 1
        if st == 200:
            return body
        if st == 429:
            stats["429"] += 1
            if k < len(BACKOFF) and stats["429"] < MAX_429:
                sleep(BACKOFF[k])
                continue
            return None
        stats["err"] += 1
        return None
    return None


# ---------------------------------------------------------------------------------------------- run
def run(cands, state, get=http_get, sleep=time.sleep, clock=time.time, budget=BUDGET, n=MAX_POOLS):
    """Poll selected pools; returns (rows, stats).  state is updated in place."""
    t0 = clock()
    stats = {"selected": 0, "polled": 0, "calls": 0, "429": 0, "err": 0, "trades": 0, "new": 0, "budget_stop": False}
    seen = dict.fromkeys(state.get("seen", []), 1)
    pools = state.setdefault("pools", {})
    chosen = select(cands, state, t0, n)
    stats["selected"] = len(chosen)
    rows = []
    last_call = None
    for c in chosen:
        if clock() - t0 > budget - 30 or stats["429"] >= MAX_429:
            stats["budget_stop"] = clock() - t0 > budget - 30
            break
        if last_call is not None:
            wait = GAP - (clock() - last_call)
            if wait > 0:
                sleep(wait)
        last_call = clock()
        body = fetch_pool(c, get, sleep, stats)
        last_call = clock()
        ps = pools.setdefault(c["key"], {})
        if body is None:
            continue
        parsed = parse_trades(body, c)
        got = new_trades(parsed, ps, seen)
        ps["polled"] = int(clock())
        ps["sym"] = c.get("sym", "")
        stats["polled"] += 1
        stats["trades"] += len(parsed)
        stats["new"] += len(got)
        rows += got
    # forget pools not polled for a long time; cap seen ids (dict keeps insertion order: drop the oldest)
    for k in [k for k, v in pools.items() if t0 - v.get("polled", t0) > POOL_TTL_H * 3600]:
        del pools[k]
    state["seen"] = list(seen)[-SEEN_CAP:]
    state["last_run"] = utc(t0)
    state["last_stats"] = stats
    return rows, stats


def append_rows(path, rows):
    """Append rows as a new gzip member (header written only when the file is new)."""
    if not rows:
        return
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    if new:
        w.writeheader()
    w.writerows(rows)
    with gzip.open(path, "ab") as f:
        f.write(buf.getvalue().encode())


def load_state(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"pools": {}, "seen": []}


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, separators=(",", ":"))
    os.replace(tmp, path)


def main():
    now = time.time()
    try:
        with open(SCREEN, newline="") as f:
            screen = list(csv.DictReader(f))
    except FileNotFoundError:
        screen = []
    try:
        with open(PORTFOLIO) as f:
            portfolio = json.load(f)
    except Exception:
        portfolio = {}
    cands = candidates(screen, portfolio, now)
    state = load_state(STATE)
    rows, stats = run(cands, state)
    append_rows(OUT, rows)
    save_state(STATE, state)
    held = sum(c["held"] for c in cands.values())
    print(f"{utc(now)} wallet_tracker: {len(cands)} candidate pools ({held} held), polled {stats['polled']}/{stats['selected']}, "
          f"trades returned {stats['trades']}, new {stats['new']}, calls {stats['calls']}, 429s {stats['429']}, "
          f"other errors {stats['err']}, budget stop {stats['budget_stop']}, {time.time() - now:.0f}s")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
