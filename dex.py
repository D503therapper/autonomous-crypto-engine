"""DEX (on-chain) PAPER trader with a scam screen: the "dex_hunter" $500 account.
Paper only: no wallet, no keys, no transactions. Fills are simulated from public DEX price data.

Discovery (config.DEX["chains"]: solana / base / ethereum):
    GeckoTerminal /networks/{net}/trending_pools?duration=1h   (organic; 20 pools per chain)
    DexScreener  /token-boosts/top/v1 -> /tokens/v1/{chain}/{addrs}   (paid boosts; data lookup)
    data/social/dex_watch.json (social.py's DEX watchlist: symbols seen trending that are NOT on
    Crypto.com) -> DexScreener /latest/dex/search?q=SYMBOL to resolve the contract address
Scam screen (every check must pass; verdict + reasons -> data/dex/screen.csv; fail closed):
    market sanity from DexScreener (liquidity, pool age, volume, buys AND sells, spike-and-fade)
    GoPlus token_security   (EVM: honeypot, taxes, mintable, pausable, black/whitelist, hidden owner,
                             proxy, source, owner/creator %, top-10 holders, LP locked share;
                             Solana: mint/freeze/close authority, transfer fee/hook, holders, LP)
    honeypot.is IsHoneypot  (EVM second opinion: simulated sell, taxes)
    RugCheck report/summary (Solana second opinion: "danger" risks, normalised score)
Trading: momentum entry (1h/6h change + buys > sells), size = min(10% equity, 1% pool liquidity),
costs = 0.3% DEX fee + price impact (usd / liquidity) + 1% slippage per side, trailing stop 30%,
take-profit 1/3 at +100% and 1/3 at +300%, 14-day max hold, emergency exit when a re-screen
(every 30 min) flags the token or liquidity drops > 50%. Every exit re-runs the sell simulation
first; if it fails the trade is booked as SCAMMED at -100%. Outcomes -> data/dex/outcomes.csv.
Rejected tokens are followed for 7 days (data/dex/rejected_followup.csv: rugged? ran up?).

    hunter = DexHunter()          # markets.py registers it so it shows in LAB.md
    hunter.self_check()           # once per run: HTTP status per source -> run.log
    hunter.tick()                 # every second: bookkeeping + AT MOST ONE HTTP request
    python dex.py [--check]       # self-check, or one screening round

None of the endpoints could be reached from the build sandbox: URLs, field names and rate limits
are from the public docs / research notes and must be verified live (see DEFAULTS["urls"]).
"""
import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timezone

import config
from engine import Portfolio, append_csv, ts
from social import DAY, HOUR, MIN, SOCIAL, _f, _json, http_get, parse_dex_list

DEFAULTS = {
    "chains": ["solana", "base", "ethereum"],
    "chain_ids": {"ethereum": "1", "base": "8453"},                 # GoPlus / honeypot.is EVM chain ids
    "gt_networks": {"solana": "solana", "base": "base", "ethereum": "eth"},   # GeckoTerminal network ids
    "urls": {                                                        # {..} placeholders filled at call time
        "goplus_evm": "https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={addr}",
        "goplus_sol": "https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={addr}",
        "honeypot": "https://api.honeypot.is/v2/IsHoneypot?address={addr}&chainID={chain_id}",
        "rugcheck": "https://api.rugcheck.xyz/v1/tokens/{addr}/report/summary",
        "ds_tokens": "https://api.dexscreener.com/tokens/v1/{chain}/{addrs}",            # <= 30 addresses
        "ds_search": "https://api.dexscreener.com/latest/dex/search?q={q}",
        "ds_boosts": "https://api.dexscreener.com/token-boosts/top/v1",
        "gt_trending": "https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools?duration=1h",
    },
    "ref": {"ethereum": "0x6982508145454ce325ddbe47a25d4ec3d2311933",      # PEPE: self-check probe
            "solana": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"},     # BONK
    "timeout": 6,                                                    # seconds per request (cap 8)
    "gap_s": {"goplus": 3, "honeypot": 3, "rugcheck": 3, "dexscreener": 1.5, "geckoterminal": 2.5},
    "every_s": {"discover": 300, "watch": 600, "prices": 60, "rescreen": 1800, "followup": 3600},
    "screen": {
        "max_tax": 0.05, "reject_proxy": True, "max_creator_pct": 0.10, "max_top10_pct": 0.50,
        "min_lp_locked": 0.80, "rugcheck_max_score": 50,             # score_normalised (0-100, higher = worse)
        "min_liq": 100_000, "min_age_h": 6, "min_vol24": 200_000,
        "max_24h_change": None,                                      # owner: no cap on runners
        "fade_h6": 0.30, "fade_h1": -0.15,                           # +30% in 6h but -15% in the last hour
        "ttl_h": 6, "reject_ttl_h": 24, "unreach_ttl_h": 1,          # how long a verdict stands
    },
    "entry": {"h1": 0.05, "h6": 0.10, "buy_ratio": 1.2},            # +5% 1h, +10% 6h, 1h buys >= 1.2x sells
    "size": {"equity_pct": 0.10, "liq_pct": 0.01},
    "cost": {"fee": 0.003, "slip": 0.01},                            # + price impact usd/liquidity per side
    "exit": {"trail": 0.30, "tp1": (1.0, 1 / 3), "tp2": (3.0, 0.5),  # tp2: half of the remaining 2/3
             "max_hold_days": 14, "liq_pull": 0.50, "rug_tax": 0.50, "check_wait_s": 600},
    "followup": {"days": 7, "per_day": 50, "rug_liq": 0.80, "rug_px": 0.90, "runup": 1.0},
    "slots": 5, "queue": 20, "dir": "data/dex", "name": "dex_hunter",
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = dict(base[k], **v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


DEX = _merge(DEFAULTS, getattr(config, "DEX", {}))
BURN = {"0x0000000000000000000000000000000000000000", "0x000000000000000000000000000000000000dead",
        "1nc1nerator11111111111111111111111111111111"}
_LP_TAG = re.compile(r"burn|dead|null|lock|\blp\b|pool|uniswap|pancake|raydium|orca|meteora|pumpswap|vault",
                     re.I)
_LOCK_TAG = re.compile(r"burn|dead|null|lock", re.I)
PRIO = {"scammed_rug": 4, "scammed_honeypot": 4, "emergency_exit": 3, "stop": 2, "tp": 1}


def _pct(x):
    """'12.5' (percent, as DexScreener/GeckoTerminal report) -> 0.125."""
    v = _f(x)
    return None if v is None else v / 100


def _iso_ms(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def _one(d, k):
    return str(d.get(k, "")).strip() == "1"        # GoPlus flags: "1"/"0"/"" (str) or 1/0 (int)


def _txn(tx, w, side):
    v = _f(((tx or {}).get(w) or {}).get(side))
    return None if v is None else int(v)


# ---- parsers (pure) -------------------------------------------------------------------------
def norm_ds(p, now):
    """DexScreener pair -> candidate {chain, addr, sym, pair, price, liq, vol24, fdv, age_h, b1, s1,
    b24, s24, h1, h6, h24 (fractions), ...} or None."""
    bt = p.get("baseToken") if isinstance(p, dict) else None
    if not isinstance(bt, dict) or not bt.get("address") or not p.get("chainId"):
        return None
    tx, pc, created = p.get("txns") or {}, p.get("priceChange") or {}, _f(p.get("pairCreatedAt"))
    return {"chain": p["chainId"], "addr": bt["address"], "sym": str(bt.get("symbol") or "?").upper(),
            "name": str(bt.get("name") or ""), "pair": p.get("pairAddress"), "price": _f(p.get("priceUsd")),
            "liq": _f((p.get("liquidity") or {}).get("usd")) or 0.0,
            "vol24": _f((p.get("volume") or {}).get("h24")) or 0.0, "fdv": _f(p.get("fdv")),
            "age_h": (now - created) / HOUR if created else None,
            "b1": _txn(tx, "h1", "buys"), "s1": _txn(tx, "h1", "sells"),
            "b24": _txn(tx, "h24", "buys"), "s24": _txn(tx, "h24", "sells"),
            "h1": _pct(pc.get("h1")), "h6": _pct(pc.get("h6")), "h24": _pct(pc.get("h24")),
            "src": "dexscreener", "t": now}


def parse_ds_pairs(body, now):
    """tokens/v1 (bare list), search / pairs ({"pairs": [...]}) -> [candidate]."""
    body = _json(body) if isinstance(body, str) else body
    if isinstance(body, dict):
        body = body.get("pairs") or []
    out = [norm_ds(p, now) for p in (body if isinstance(body, list) else [])]
    return [c for c in out if c]


def best_pairs(cands, chain=None):
    """{addr: deepest pair} (optionally one chain only)."""
    out = {}
    for c in cands:
        if (chain is None or c["chain"] == chain) and c["liq"] >= out.get(c["addr"], {}).get("liq", -1):
            out[c["addr"]] = c
    return out


def parse_gt_pools(body, chain, now):
    """GeckoTerminal trending_pools -> [candidate] (same shape as norm_ds, src 'geckoterminal')."""
    body = _json(body) if isinstance(body, str) else body
    out = []
    for p in (body or {}).get("data") or []:
        a = p.get("attributes") if isinstance(p, dict) else None
        tid = str((((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", ""))
        if not isinstance(a, dict) or "_" not in tid or not a.get("name"):
            continue
        tx, pc, created = a.get("transactions") or {}, a.get("price_change_percentage") or {}, _iso_ms(a.get("pool_created_at"))
        sym = re.sub(r"\s+\d+(\.\d+)?%$", "", str(a["name"]).split("/")[0].strip()).upper()
        out.append({"chain": chain, "addr": tid.split("_", 1)[1], "sym": sym, "name": "", "pair": a.get("address"),
                    "price": _f(a.get("base_token_price_usd")), "liq": _f(a.get("reserve_in_usd")) or 0.0,
                    "vol24": _f((a.get("volume_usd") or {}).get("h24")) or 0.0, "fdv": _f(a.get("fdv_usd")),
                    "age_h": (now - created) / HOUR if created else None,
                    "b1": _txn(tx, "h1", "buys"), "s1": _txn(tx, "h1", "sells"),
                    "b24": _txn(tx, "h24", "buys"), "s24": _txn(tx, "h24", "sells"),
                    "h1": _pct(pc.get("h1")), "h6": _pct(pc.get("h6")), "h24": _pct(pc.get("h24")),
                    "src": "geckoterminal", "t": now})
    return out


# ---- scam checks (pure; each returns [(reason, severity)], severity 'scam' | 'flag') ------------
def top_holders(hs, exclude=()):
    """Top-10 share (fraction of supply) excluding LP pools / burn addresses; None if unknown."""
    shares = []
    for h in hs or []:
        if not isinstance(h, dict):
            continue
        a = str(h.get("address") or h.get("account") or "").lower()
        if a in BURN or a in exclude or _LP_TAG.search(str(h.get("tag") or "")):
            continue
        p = _f(h.get("percent"))
        if p is not None:
            shares.append(p)
    return sum(sorted(shares, reverse=True)[:10]) if shares else None


def lp_locked(lps):
    """Share of LP tokens locked or burned (GoPlus lp_holders[].percent is of total LP); None if empty."""
    if not lps:
        return None
    lock = 0.0
    for h in lps:
        if not isinstance(h, dict):
            continue
        a = str(h.get("address") or h.get("account") or "").lower()
        if _one(h, "is_locked") or a in BURN or _LOCK_TAG.search(str(h.get("tag") or "")):
            lock += _f(h.get("percent")) or 0.0
    return min(1.0, lock)


def _tax(r, v, what, S):
    """Tax as a fraction (GoPlus '0.05'); None = unknown -> fail closed."""
    if v is None:
        r.append((f"{what} unknown", "flag"))
    elif v > S["max_tax"]:
        r.append((f"{what} {v:.0%}", "scam" if what == "sell tax" and v > DEX["exit"]["rug_tax"] else "flag"))


def check_goplus_evm(d, S):
    r = []
    for k, sev in (("is_honeypot", "scam"), ("cannot_sell_all", "scam"), ("transfer_pausable", "scam"),
                   ("cannot_buy", "flag"), ("is_mintable", "flag"), ("is_blacklisted", "flag"),
                   ("is_whitelisted", "flag"), ("hidden_owner", "flag"), ("can_take_back_ownership", "flag"),
                   ("owner_change_balance", "flag"), ("selfdestruct", "flag"), ("honeypot_with_same_creator", "flag")):
        if _one(d, k):
            r.append((k, sev))
    if _one(d, "is_proxy") and S["reject_proxy"]:
        r.append(("is_proxy", "flag"))
    if not _one(d, "is_open_source"):
        r.append(("not open source", "flag"))
    _tax(r, _f(d.get("buy_tax")), "buy tax", S)
    _tax(r, _f(d.get("sell_tax")), "sell tax", S)
    for k in ("creator_percent", "owner_percent"):
        v = _f(d.get(k))
        if v is not None and v > S["max_creator_pct"]:
            r.append((f"{k} {v:.0%}", "flag"))
    pools = {str(x.get("pair", "")).lower() for x in d.get("dex") or [] if isinstance(x, dict)}
    t10 = top_holders(d.get("holders"), pools)
    if t10 is None:
        r.append(("holders unknown", "flag"))
    elif t10 > S["max_top10_pct"]:
        r.append((f"top-10 holders {t10:.0%}", "flag"))
    lp = lp_locked(d.get("lp_holders"))
    if lp is None:
        r.append(("lp holders unknown", "flag"))
    elif lp < S["min_lp_locked"]:
        r.append((f"lp locked {lp:.0%} < {S['min_lp_locked']:.0%}", "flag"))
    return r


def _auth(d, k):
    """GoPlus Solana authority fields: {"status": "1", "authority": [...]} (or a bare "1")."""
    v = d.get(k)
    return _one(v, "status") if isinstance(v, dict) else str(v or "").strip() == "1"


def check_goplus_sol(d, S):
    r = []
    for k, sev in (("freezable", "scam"), ("non_transferable", "scam"), ("mintable", "flag"), ("closable", "flag"),
                   ("balance_mutable_authority", "flag"), ("transfer_fee_upgradable", "flag")):
        if _auth(d, k):
            r.append((k.replace("able", " authority") if k in ("freezable", "mintable", "closable") else k, sev))
    hook = d.get("transfer_hook")
    if (isinstance(hook, list) and hook) or _auth(d, "transfer_hook") or _auth(d, "transfer_hook_upgradable"):
        r.append(("transfer hook", "flag"))
    fee = d.get("transfer_fee") or {}
    fee = _f(fee.get("fee_rate") if "fee_rate" in fee else (fee.get("current") or {}).get("fee_rate")) if isinstance(fee, dict) else _f(fee)
    if fee:
        _tax(r, fee, "sell tax", S)                 # Token-2022 transfer fee hits every sell
    creators = {str(c.get("address", "")).lower() for c in d.get("creators") or [] if isinstance(c, dict)}
    if any(str(c.get("malicious_address", "")) == "1" for c in d.get("creators") or [] if isinstance(c, dict)):
        r.append(("malicious creator", "flag"))
    own = sum(_f(h.get("percent")) or 0 for h in d.get("holders") or [] if isinstance(h, dict)
              and str(h.get("account") or h.get("address") or "").lower() in creators)
    if own > S["max_creator_pct"]:
        r.append((f"creator holds {own:.0%}", "flag"))
    t10 = top_holders(d.get("holders"))
    if t10 is None:
        r.append(("holders unknown", "flag"))
    elif t10 > S["max_top10_pct"]:
        r.append((f"top-10 holders {t10:.0%}", "flag"))
    lp = lp_locked(d.get("lp_holders"))
    if lp is None:
        r.append(("lp holders unknown", "flag"))
    elif lp < S["min_lp_locked"]:
        r.append((f"lp locked {lp:.0%} < {S['min_lp_locked']:.0%}", "flag"))
    return r


def check_honeypot(j, S):
    """honeypot.is v2: honeypotResult.isHoneypot, simulationSuccess, simulationResult.buyTax/sellTax (percent)."""
    r, hr, sr = [], (j or {}).get("honeypotResult"), (j or {}).get("simulationResult")
    if not isinstance(hr, dict) and not isinstance(sr, dict):
        return [("honeypot.is: no data", "flag")]
    if j.get("simulationSuccess") is False:
        r.append(("sell simulation failed", "scam"))
    if isinstance(hr, dict) and hr.get("isHoneypot"):
        r.append((f"honeypot ({hr.get('honeypotReason') or 'honeypot.is'})", "scam"))
    if isinstance(sr, dict):
        _tax(r, _pct(sr.get("buyTax")), "buy tax", S)
        _tax(r, _pct(sr.get("sellTax")), "sell tax", S)
    return r


def check_rugcheck(j, S):
    """RugCheck summary: risks[{name, level: warn|danger, ...}], score_normalised (0-100)."""
    if not isinstance(j, dict) or ("risks" not in j and "score" not in j):
        return [("rugcheck: no data", "flag")]
    r = []
    for k in j.get("risks") or []:
        if isinstance(k, dict) and str(k.get("level", "")).lower() == "danger":
            name = str(k.get("name") or "risk")
            r.append((f"rugcheck danger: {name}", "scam" if re.search(r"freeze|honeypot|transfer", name, re.I) else "flag"))
    sc = _f(j.get("score_normalised"))
    if sc is not None and sc > S["rugcheck_max_score"]:
        r.append((f"rugcheck score {sc:.0f}", "flag"))
    return r


def check_market(c, S):
    r = []
    if not c.get("price") or c["price"] <= 0:
        r.append(("no price", "flag"))
    if c["liq"] < S["min_liq"]:
        r.append((f"liquidity ${c['liq']:,.0f} < ${S['min_liq']:,}", "flag"))
    if c.get("age_h") is None:
        r.append(("pool age unknown", "flag"))
    elif c["age_h"] < S["min_age_h"]:
        r.append((f"pool age {c['age_h']:.1f}h < {S['min_age_h']}h", "flag"))
    if c["vol24"] < S["min_vol24"]:
        r.append((f"24h volume ${c['vol24']:,.0f} < ${S['min_vol24']:,}", "flag"))
    if not c.get("b24") or not c.get("s24"):
        r.append(("no buys or no sells in 24h", "flag"))
    h1, h6, h24 = c.get("h1"), c.get("h6"), c.get("h24")
    if S["max_24h_change"] is not None and h24 is not None and h24 > S["max_24h_change"]:
        r.append((f"already up {h24:+.0%} in 24h", "flag"))
    if h6 is not None and h1 is not None and h6 >= S["fade_h6"] and h1 <= S["fade_h1"]:
        r.append((f"spike-and-fade (6h {h6:+.0%}, 1h {h1:+.0%})", "flag"))
    return r


# ---- HTTP source with rate limit + backoff ---------------------------------------------------------
class Source:
    """Min gap between calls + backoff on failure (as social.Collector: 429/403 -> 15 min doubling
    to 6 h; other failures -> 2 min doubling to 1 h). get() never raises."""

    def __init__(self, name, fetch=None, timeout=6, gap_s=2):
        self.name, self.fetch, self.timeout, self.gap = name, fetch, min(timeout, 8), gap_s * 1000
        self.next_at, self.fails, self.status, self.calls = 0, 0, None, 0

    def ready(self, now):
        return now >= self.next_at

    def get(self, url, now):
        try:
            st, txt = (self.fetch or http_get)(url, self.timeout)
        except Exception as e:
            st, txt = 0, str(e)
        self.status, self.calls = st, self.calls + 1
        if st == 200:
            self.fails, self.next_at = 0, now + self.gap
        else:
            self.fails += 1
            base, cap = (15 * MIN, 6 * HOUR) if st in (429, 403) else (2 * MIN, HOUR)
            self.next_at = now + min(cap, base * 2 ** (self.fails - 1))
        return st, _json(txt)


_EMPTY = {"seen": {}, "passed": {}, "followup": {}, "last": {}, "watch_done": {}, "fu_day": "", "fu_n": 0,
          "status": {}, "week": None, "month": None, "hour": None, "swept": 0.0, "prefiltered": 0}
_STEP_SRC = {"ds": "dexscreener", "goplus": "goplus", "honeypot": "honeypot", "rugcheck": "rugcheck"}


class DexHunter:
    """The dex_hunter paper account. Listed in markets.MARKETS["dex"] for LAB.md only (it is never
    fed candles); run_live drives it with tick() once a second."""
    name = "dex_hunter"
    universe, min_candles, weekly = [], 0, False

    def __init__(self, params=None, fetch=None, now_ms=None):
        self.p = _merge(DEX, params or {})
        self.name, self.dir = self.p["name"], self.p["dir"]
        self.acct = f"{self.dir}/{self.name}"
        self.clock, self.fetch = now_ms, fetch
        self.src = {n: Source(n, fetch, self.p["timeout"], g) for n, g in self.p["gap_s"].items()}
        self.state, self.pf, self.queue, self.jobs, self.lookup = None, None, [], {}, []
        self._n_saved, self.dirty = 0, False

    # ---- plumbing ----
    def _now(self):
        return self.clock or int(time.time() * 1000)

    def _load(self):
        if self.state is not None:
            return
        self.state = json.loads(json.dumps(_EMPTY))
        try:
            if os.path.exists(f"{self.dir}/state.json"):
                with open(f"{self.dir}/state.json") as f:
                    self.state.update(json.load(f))
        except Exception as e:
            print(f"   dex: could not read state: {e}")
        C = self.p["cost"]
        self.pf = Portfolio.load(f"{self.acct}/portfolio.json", fee=C["fee"], slippage=C["slip"])

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(f"{self.dir}/state.json.tmp", "w") as f:
                json.dump(self.state, f)
            os.replace(f"{self.dir}/state.json.tmp", f"{self.dir}/state.json")
        except Exception as e:
            print(f"   dex: save failed: {e}")
        self.dirty = False

    def _save_pf(self, now):
        """Portfolio + new trades.csv rows + an equity.csv row (LAB.md reads the last one)."""
        new = self.pf.trades[self._n_saved:]
        append_csv(f"{self.acct}/trades.csv", new)
        self.pf.save(f"{self.acct}/portfolio.json")
        self._n_saved = len(self.pf.trades)
        for t in new:
            pnl = "" if t["pnl"] is None else f", P/L ${t['pnl']:+.2f}"
            print(f"   >> dex/{self.name}: {t['side']} ${t['usd']:.2f} of {t['coin']} @ {t['price']:g}{pnl} ({t['reason']})")
        self._equity_row(now)

    def prices(self):
        return {k: (p.get("px") if p.get("px") is not None else p["entry"]) for k, p in self.pf.positions.items()}

    def equity(self):
        return self.pf.equity(self.prices())

    def _equity_row(self, now):
        append_csv(f"{self.acct}/equity.csv", [{"time": ts(now), "equity": round(self.equity(), 2),
                                                "cash": round(self.pf.cash, 2), "positions": len(self.pf.positions)}])

    def _get(self, name, url, now):
        st, obj = self.src[name].get(url, now)
        self.state["status"][name] = {"code": st, "t": ts(now)}
        self.dirty = True
        return st, obj

    def _url(self, k, **kw):
        return self.p["urls"][k].format(**kw)

    @staticmethod
    def key(c):
        return f"{c['chain']}:{c['addr']}"

    @staticmethod
    def pkey(c):
        return f"{c['sym']}@{c['chain']}:{c['addr'][:8]}"      # position name in trades.csv

    def _steps(self, chain, fresh):
        sec = ["goplus", "honeypot"] if chain in self.p["chain_ids"] else ["goplus", "rugcheck"]
        return ([] if fresh else ["ds"]) + sec

    # ---- main entry points ----
    def self_check(self, now=None):
        """Once per run: one probe per source -> HTTP status line for run.log."""
        now = now or self._now()
        self._load()
        R, ids = self.p["ref"], self.p["chain_ids"]
        probes = [("goplus", self._url("goplus_evm", chain_id=ids["ethereum"], addr=R["ethereum"])),
                  ("honeypot", self._url("honeypot", addr=R["ethereum"], chain_id=ids["ethereum"])),
                  ("rugcheck", self._url("rugcheck", addr=R["solana"])),
                  ("dexscreener", self._url("ds_tokens", chain="solana", addrs=R["solana"])),
                  ("geckoterminal", self._url("gt_trending", network=self.p["gt_networks"]["solana"]))]
        parts = []
        for name, url in probes:
            st, _ = self._get(name, url, now)
            parts.append(f"{'honeypot.is' if name == 'honeypot' else name} {st}")
        line = "dex self-check: " + " | ".join(parts)
        print(f"   {line}")
        self.save()
        return line

    def tick(self, now=None):
        """Bookkeeping, then at most ONE HTTP request (first job whose source is ready)."""
        now = now or self._now()
        self._load()
        self._housekeep(now)
        for job in (self._exit_job, self._price_job, self._rescreen_job, self._screen_job,
                    self._discover_job, self._followup_job):
            if job(now):
                break
        if self.dirty:
            self.save()

    def status_line(self):
        self._load()
        return (f"dex hunter: equity ${self.equity():,.2f}, {len(self.pf.positions)} open, "
                f"{len(self.state['passed'])} screened & waiting, {len(self.queue)} queued, "
                f"{len(self.state['followup'])} rejected in follow-up, {self.state['prefiltered']} prefiltered")

    # ---- housekeeping (no HTTP) ----
    def _housekeep(self, now):
        st, S, X = self.state, self.p["screen"], self.p["exit"]
        for k, pos in list(self.pf.positions.items()):        # sell check unreachable for too long
            ex = pos.get("exit")
            if ex and now - ex["t"] > X["check_wait_s"] * 1000:
                self._execute_exit(k, [], now, " (sell check unreachable, booked at market)")
        ttl = {"REJECT": S["reject_ttl_h"], "UNREACHABLE": S["unreach_ttl_h"], "PASS": S["ttl_h"]}
        st["seen"] = {k: v for k, v in st["seen"].items() if now - v["t"] <= ttl.get(v["v"], 24) * HOUR}
        for k, c in list(st["passed"].items()):
            if now - c["screen_t"] > S["ttl_h"] * HOUR:
                del st["passed"][k]
                self.dirty = True
        hour = time.strftime("%Y%m%d%H", time.gmtime(now / 1000))
        if st["hour"] != hour:
            st["hour"], self.dirty = hour, True
            self._equity_row(now)
        week = time.strftime("%G-%V", time.gmtime(now / 1000))
        if st["week"] != week:
            st["week"], self.dirty = week, True
            print(f"   {self.weekly_line(now)}")
        month = time.strftime("%Y-%m", time.gmtime(now / 1000))
        if st["month"] != month:
            if st["month"]:                                    # a full month has passed since the last sweep
                print(f"   {self.sweep_line(now)}")
            st["month"], self.dirty = month, True

    def weekly_line(self, now):
        """Screen precision report for run.log (last 7 days, from the CSV logs)."""
        since = now - 7 * DAY
        sc = self._rows(f"{self.dir}/screen.csv", since)
        tr = self._rows(f"{self.acct}/trades.csv", since)
        oc = self._rows(f"{self.dir}/outcomes.csv", since)
        fu = self._rows(f"{self.dir}/rejected_followup.csv", since)
        scam = [r for r in oc if r["outcome"].startswith("scammed")]
        cost = sum(_f(r["pnl"]) or 0 for r in scam)
        return (f"dex weekly: screened {len(sc)}, passed {sum(r['verdict'] == 'PASS' for r in sc)}, "
                f"trades {sum(r['side'] == 'BUY' for r in tr)}, scammed {len(scam)} (cost ${cost:+.2f}), "
                f"rejected-that-rugged {sum(r['rugged'] == '1' for r in fu)}/{len(fu)}, "
                f"rejected-that-ran-up {sum(r['ran_up'] == '1' for r in fu)}/{len(fu)}")

    def sweep_line(self, now):
        """Monthly profit sweep to USDC, simulated only: what would have been moved (no action)."""
        eq, st = self.equity(), self.state
        sweep = max(0.0, eq - config.STARTING_CASH_USD - st["swept"])
        st["swept"] += sweep
        append_csv(f"{self.dir}/sweeps.csv", [{"time": ts(now), "equity": round(eq, 2), "sweep_usd": round(sweep, 2),
                                               "swept_total": round(st["swept"], 2)}])
        return (f"dex sweep sim: equity ${eq:,.2f}, would sweep ${sweep:,.2f} profit to USDC "
                f"(cumulative ${st['swept']:,.2f}); no action taken")

    @staticmethod
    def _rows(path, since):
        if not os.path.exists(path):
            return []
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        out = []
        for r in rows:
            try:
                t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000
            except (KeyError, ValueError):
                continue
            if t >= since:
                out.append(r)
        return out

    # ---- discovery ----
    def _discover_job(self, now):
        E, st = self.p["every_s"], self.state
        ds, gt = self.src["dexscreener"], self.src["geckoterminal"]
        if self.lookup and ds.ready(now):                      # phase 2: boosts / watch addresses -> data
            chain = self.lookup[0][0]
            addrs = [a for c, a in self.lookup if c == chain][:30]
            self.lookup = [(c, a) for c, a in self.lookup if not (c == chain and a in addrs)]
            st_, obj = self._get("dexscreener", self._url("ds_tokens", chain=chain, addrs=",".join(addrs)), now)
            if st_ == 200:
                for c in best_pairs(parse_ds_pairs(obj, now), chain).values():
                    self._enqueue(c, now, fresh=True)
            return True
        for chain in self.p["chains"]:
            k = f"gt_{chain}"
            if now - st["last"].get(k, 0) >= E["discover"] * 1000 and gt.ready(now):
                st["last"][k] = now
                st_, obj = self._get("geckoterminal", self._url("gt_trending", network=self.p["gt_networks"][chain]), now)
                if st_ == 200:
                    for c in parse_gt_pools(obj, chain, now):
                        self._enqueue(c, now, fresh=False)
                return True
        if now - st["last"].get("boosts", 0) >= E["discover"] * 1000 and ds.ready(now):
            st["last"]["boosts"] = now
            st_, obj = self._get("dexscreener", self._url("ds_boosts"), now)
            if st_ == 200:
                self.lookup += [(c, a) for c, a in parse_dex_list(obj) if c in self.p["chains"]
                                and f"{c}:{a}" not in st["seen"] and (c, a) not in self.lookup][:60]
            return True
        if now - st["last"].get("watch", 0) >= E["watch"] * 1000 and ds.ready(now):
            st["last"]["watch"] = now
            sym = self._watch_pick(now)
            if sym:
                st["watch_done"][sym] = now
                st_, obj = self._get("dexscreener", self._url("ds_search", q=sym), now)
                if st_ == 200:
                    for c in parse_ds_pairs(obj, now):
                        if c["sym"] == sym and c["chain"] in self.p["chains"]:
                            self._enqueue(c, now, fresh=True)
                return True
        return False

    def _watch_pick(self, now):
        """Most-sighted symbol from social.py's DEX watchlist not resolved in the last 24h."""
        path = f"{SOCIAL['dir']}/dex_watch.json"
        try:
            with open(path) as f:
                w = json.load(f)
        except Exception:
            return None
        wd = self.state["watch_done"]
        self.state["watch_done"] = {s: t for s, t in wd.items() if now - t <= DAY}
        cands = [(v.get("n", 0), s) for s, v in w.items() if isinstance(v, dict) and v.get("chain") in self.p["chains"]
                 and v.get("n", 0) >= 2 and s not in self.state["watch_done"] and re.fullmatch(r"[A-Z0-9]{2,12}", s)]
        return max(cands)[1] if cands else None

    def _enqueue(self, c, now, fresh):
        """Queue a candidate for the full screen unless known; cheap market prefilter first (not logged)."""
        k, st = self.key(c), self.state
        if c["chain"] not in self.p["chains"] or k in st["seen"] or k in st["passed"] \
                or any(j["key"] == k for j in self.queue) or self.pkey(c) in self.pf.positions:
            return False
        if check_market(c, self.p["screen"]):
            st["prefiltered"] += 1
            self.dirty = True
            return False
        self.queue.append({"key": k, "c": c, "steps": self._steps(c["chain"], fresh), "i": 0, "reasons": [],
                           "mode": "screen"})
        self.queue.sort(key=lambda j: -j["c"]["liq"])
        del self.queue[self.p["queue"]:]
        return True

    # ---- screening state machine (one request per call) ----
    def _screen_job(self, now):
        for job in self.queue:
            if self.src[_STEP_SRC[job["steps"][job["i"]]]].ready(now):
                self._run_step(job, now)
                if job["i"] >= len(job["steps"]):
                    self.queue.remove(job)
                    self._finish(job, now)
                return True
        return False

    def _run_step(self, job, now):
        c, S, step = job["c"], self.p["screen"], job["steps"][job["i"]]
        ids, reasons = self.p["chain_ids"], []
        if step == "ds":
            st, obj = self._get("dexscreener", self._url("ds_tokens", chain=c["chain"], addrs=c["addr"]), now)
            pairs = parse_ds_pairs(obj, now) if st == 200 else None
            if pairs is None:
                reasons = [("dexscreener unreachable", "unreach")]
            else:
                best = best_pairs(pairs, c["chain"]).get(c["addr"])
                if not best:
                    reasons = [("no dexscreener pair", "flag")]
                else:
                    c.update(best)
                    reasons = check_market(c, S)
        elif step == "goplus":
            evm = c["chain"] in ids
            url = self._url("goplus_evm", chain_id=ids[c["chain"]], addr=c["addr"]) if evm else self._url("goplus_sol", addr=c["addr"])
            st, obj = self._get("goplus", url, now)
            res = (obj or {}).get("result") if st == 200 and isinstance(obj, dict) and str(obj.get("code")) == "1" else None
            if not isinstance(res, dict):
                reasons = [("goplus unreachable", "unreach")]
            else:
                d = res.get(c["addr"]) or res.get(c["addr"].lower()) or next((v for k, v in res.items() if k.lower() == c["addr"].lower()), None)
                reasons = (check_goplus_evm(d, S) if evm else check_goplus_sol(d, S)) if isinstance(d, dict) else [("goplus: no data", "flag")]
        elif step == "honeypot":
            st, obj = self._get("honeypot", self._url("honeypot", addr=c["addr"], chain_id=ids[c["chain"]]), now)
            reasons = check_honeypot(obj, S) if st == 200 and isinstance(obj, dict) else [("honeypot.is unreachable", "unreach")]
        elif step == "rugcheck":
            st, obj = self._get("rugcheck", self._url("rugcheck", addr=c["addr"]), now)
            reasons = check_rugcheck(obj, S) if st == 200 and isinstance(obj, dict) else [("rugcheck unreachable", "unreach")]
        job["reasons"] += reasons
        job["i"] = len(job["steps"]) if reasons else job["i"] + 1    # first failure ends the screen

    def _finish(self, job, now):
        c, rs, st = job["c"], job["reasons"], self.state
        why = "; ".join(t for t, _ in rs)
        if job["mode"] == "rescreen":
            pos = self.pf.positions.get(job["key"])
            if not pos:
                return
            pos["rescreened"] = now
            if any(s == "unreach" for _, s in rs):
                print(f"   dex re-screen: {job['key']} unreachable ({why}); holding")
            elif rs:
                outcome = "scammed_honeypot" if any(s == "scam" for _, s in rs) else "emergency_exit"
                self._request_exit(job["key"], 1.0, f"re-screen flagged: {why}", outcome, now)
            return
        verdict = "UNREACHABLE" if any(s == "unreach" for _, s in rs) else ("REJECT" if rs else "PASS")
        append_csv(f"{self.dir}/screen.csv", [{
            "time": ts(now), "chain": c["chain"], "symbol": c["sym"], "address": c["addr"], "pair": c.get("pair") or "",
            "verdict": verdict, "reasons": why, "price": c.get("price"), "liq_usd": round(c["liq"]),
            "vol24_usd": round(c["vol24"]), "age_h": None if c.get("age_h") is None else round(c["age_h"], 1),
            "fdv": c.get("fdv"), "buys_h1": c.get("b1"), "sells_h1": c.get("s1"), "h1": c.get("h1"), "h6": c.get("h6"),
            "h24": c.get("h24"), "sources": "+".join(job["steps"][:max(1, job["i"])])}])
        print(f"   dex screen: {verdict} {c['sym']}@{c['chain']} liq ${c['liq']:,.0f}{' - ' + why if why else ''}")
        st["seen"][job["key"]] = {"t": now, "v": verdict}
        self.dirty = True
        if verdict == "PASS":
            st["passed"][job["key"]] = dict(c, screen_t=now)
            self._try_entry(job["key"], now)
        elif verdict == "REJECT":
            self._enroll(job["key"], c, now)

    # ---- entries ----
    def _try_entry(self, key, now):
        c, E, st = self.state["passed"].get(key), self.p["entry"], self.state
        if not c or self.pf.halted or len(self.pf.positions) >= self.p["slots"]:
            return
        pk = self.pkey(c)
        if pk in self.pf.positions or self.pf.cooldown.get(pk, 0) > now or not c.get("price"):
            return
        h1, h6, b1, s1 = c.get("h1"), c.get("h6"), c.get("b1") or 0, c.get("s1") or 0
        if h1 is None or h6 is None or h1 < E["h1"] or h6 < E["h6"] or b1 < max(1, s1 * E["buy_ratio"]):
            return
        eq, Z, C, X = self.equity(), self.p["size"], self.p["cost"], self.p["exit"]
        usd = min(eq * Z["equity_pct"], c["liq"] * Z["liq_pct"], self.pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd < config.MIN_ORDER_USD:
            return
        impact = usd / c["liq"]
        self.pf.slippage = C["slip"] + impact
        self.pf.buy(now, pk, usd, c["price"], c["price"] * (1 - X["trail"]),
                    reason=f"dex momentum 1h {h1:+.0%} 6h {h6:+.0%} buys/sells {b1}/{s1} impact {impact:.2%}")
        self.pf.positions[pk].update(chain=c["chain"], addr=c["addr"], sym=c["sym"], pair=c.get("pair"), liq0=c["liq"],
                                     liq=c["liq"], px=c["price"], tp1=False, tp2=False, realized=0.0, cost0=usd,
                                     rescreened=now, impact=impact)
        del st["passed"][key]
        self.dirty = True
        self._save_pf(now)                        # no phone alert: owner wants daily P/L only

    # ---- prices, stops, take-profits (every ~60 s per chain, one batch request) ----
    def _price_job(self, now):
        st, ds = self.state, self.src["dexscreener"]
        if not ds.ready(now):
            return False
        want = {}
        for pos in self.pf.positions.values():
            want.setdefault(pos["chain"], set()).add(pos["addr"])
        for c in st["passed"].values():
            want.setdefault(c["chain"], set()).add(c["addr"])
        for chain, addrs in want.items():
            if now - st["last"].get(f"px_{chain}", 0) < self.p["every_s"]["prices"] * 1000:
                continue
            st["last"][f"px_{chain}"] = now
            addrs = sorted(addrs)[:30]
            st_, obj = self._get("dexscreener", self._url("ds_tokens", chain=chain, addrs=",".join(addrs)), now)
            pairs = parse_ds_pairs(obj, now) if st_ == 200 else []
            if not pairs:
                return True
            best = best_pairs(pairs, chain)
            for k, pos in list(self.pf.positions.items()):
                if pos["chain"] != chain or pos["addr"] not in addrs:
                    continue
                c = best.get(pos["addr"])
                if c and c.get("price"):
                    pos.update(px=c["price"], liq=c["liq"], seen_px=now)
                else:                                          # no pair left: liquidity gone
                    pos.update(px=0.0, liq=0.0, seen_px=now)
                self._manage(k, pos, now)
            for key, c in list(st["passed"].items()):
                if c["chain"] == chain and c["addr"] in best:
                    c.update(best[c["addr"]], screen_t=c["screen_t"])
                    self._try_entry(key, now)
            self.dirty = True
            return True
        return False

    def _manage(self, k, pos, now):
        if pos.get("exit"):
            return
        X, p, liq = self.p["exit"], pos["px"], pos["liq"]
        if liq <= pos["liq0"] * (1 - X["liq_pull"]):
            return self._request_exit(k, 1.0, f"liquidity pulled {1 - liq / pos['liq0']:.0%} (${liq:,.0f} of ${pos['liq0']:,.0f})",
                                      "scammed_rug", now)
        pos["peak"] = max(pos["peak"], p)
        pos["stop"] = max(pos["stop"], pos["peak"] * (1 - X["trail"]))
        if p <= pos["stop"]:
            return self._request_exit(k, 1.0, f"trailing stop (peak {pos['peak']:g})", "normal", now, "stop")
        if now - pos["opened"] >= X["max_hold_days"] * DAY:
            return self._request_exit(k, 1.0, f"time limit {X['max_hold_days']}d", "normal", now, "stop")
        if not pos["tp1"] and p >= pos["entry"] * (1 + X["tp1"][0]):
            pos["tp1"] = True
            return self._request_exit(k, X["tp1"][1], f"take-profit +{X['tp1'][0]:.0%}", "normal", now, "tp")
        if pos["tp1"] and not pos["tp2"] and p >= pos["entry"] * (1 + X["tp2"][0]):
            pos["tp2"] = True
            return self._request_exit(k, X["tp2"][1], f"take-profit +{X['tp2'][0]:.0%}", "normal", now, "tp")

    def _request_exit(self, k, frac, reason, outcome, now, kind=None):
        """Queue an exit; it executes after the sell simulation (_exit_job). Higher priority replaces."""
        pos, prio = self.pf.positions[k], PRIO.get(kind or outcome, 3)
        if pos.get("exit") and pos["exit"]["prio"] >= prio:
            return
        pos["exit"] = {"frac": frac, "reason": reason, "outcome": outcome, "prio": prio, "t": now}
        self.dirty = True

    # ---- exits: sell simulation first ----
    def _exit_job(self, now):
        ids = self.p["chain_ids"]
        for k, pos in list(self.pf.positions.items()):
            if not pos.get("exit"):
                continue
            evm = pos["chain"] in ids
            src = "honeypot" if evm else "goplus"
            if not self.src[src].ready(now):
                continue
            if evm:
                st, obj = self._get(src, self._url("honeypot", addr=pos["addr"], chain_id=ids[pos["chain"]]), now)
                rs = check_honeypot(obj, self.p["screen"]) if st == 200 and isinstance(obj, dict) else None
            else:
                st, obj = self._get(src, self._url("goplus_sol", addr=pos["addr"]), now)
                res = (obj or {}).get("result") if st == 200 and isinstance(obj, dict) else None
                d = (res or {}).get(pos["addr"]) if isinstance(res, dict) else None
                rs = check_goplus_sol(d, self.p["screen"]) if isinstance(d, dict) else None
            if rs is None:                                    # unreachable: retry; _housekeep books at market later
                return True
            self._execute_exit(k, [t for t, s in rs if s == "scam"], now)
            return True
        return False

    def _execute_exit(self, k, scam, now, note=""):
        pos = self.pf.positions[k]
        ex = pos.pop("exit")
        if scam:
            self._sell(k, 1.0, 0.0, 0.0, f"{ex['reason']} | SELL SIMULATION FAILED: {'; '.join(scam)}", "scammed_honeypot", now)
        else:
            self._sell(k, ex["frac"], pos["px"] if pos.get("px") is not None else pos["entry"], pos.get("liq") or 0.0,
                       ex["reason"] + note, ex["outcome"], now)

    def _sell(self, k, frac, price, liq, reason, outcome, now):
        """Simulated fill: fee + (1% slippage + usd / liquidity) impact; price 0 / no liquidity = -100%."""
        pos, C = self.pf.positions[k], self.p["cost"]
        usd = pos["qty"] * frac * price
        impact = min(1.0, usd / liq) if liq > 0 else 1.0
        self.pf.slippage = min(1.0, C["slip"] + impact)
        keep = dict(pos)
        pnl = self.pf.sell(now, k, frac, price, reason)
        realized = keep["realized"] + pnl
        if k in self.pf.positions:
            self.pf.positions[k]["realized"] = realized
        else:
            self.pf.cooldown[k] = now + DAY
            append_csv(f"{self.dir}/outcomes.csv", [{
                "time": ts(now), "coin": k, "chain": keep["chain"], "address": keep["addr"], "opened": ts(keep["opened"]),
                "hold_h": round((now - keep["opened"]) / HOUR, 1), "cost_usd": round(keep["cost0"], 2),
                "pnl": round(realized, 2), "ret": round(realized / keep["cost0"], 4), "entry": keep["entry"],
                "exit": round(price, 10), "liq_entry": round(keep["liq0"]), "liq_exit": round(liq),
                "outcome": outcome, "reason": reason}])
            print(f"   dex outcome: {outcome} {k} P/L ${realized:+.2f} ({reason})")
        self.dirty = True
        self._save_pf(now)

    # ---- periodic re-screen of held tokens (security sources only) ----
    def _rescreen_job(self, now):
        every = self.p["every_s"]["rescreen"] * 1000
        for k, pos in self.pf.positions.items():
            if k not in self.jobs and not pos.get("exit") and now - pos.get("rescreened", 0) >= every:
                c = {"chain": pos["chain"], "addr": pos["addr"], "sym": pos["sym"]}
                self.jobs[k] = {"key": k, "c": c, "steps": self._steps(pos["chain"], True), "i": 0, "reasons": [],
                                "mode": "rescreen"}
        for k, job in list(self.jobs.items()):
            if k not in self.pf.positions:
                del self.jobs[k]
            elif self.src[_STEP_SRC[job["steps"][job["i"]]]].ready(now):
                self._run_step(job, now)
                if job["i"] >= len(job["steps"]):
                    del self.jobs[k]
                    self._finish(job, now)
                return True
        return False

    # ---- fate of rejected tokens (screen precision) ----
    def _enroll(self, key, c, now):
        st, F = self.state, self.p["followup"]
        day = time.strftime("%Y-%m-%d", time.gmtime(now / 1000))
        if st["fu_day"] != day:
            st["fu_day"], st["fu_n"] = day, 0
        if st["fu_n"] >= F["per_day"] or not c.get("price") or not c["liq"] or key in st["followup"]:
            return
        st["fu_n"] += 1
        st["followup"][key] = {"chain": c["chain"], "addr": c["addr"], "sym": c["sym"], "t0": now, "px0": c["price"],
                               "liq0": c["liq"], "px": c["price"], "liq": c["liq"], "px_max": c["price"],
                               "px_min": c["price"], "liq_min": c["liq"], "last": now, "n": 0}

    def _followup_job(self, now):
        st, F, ds = self.state, self.p["followup"], self.src["dexscreener"]
        every = self.p["every_s"]["followup"] * 1000
        for key, e in list(st["followup"].items()):           # finalize first (no HTTP)
            if now - e["t0"] >= F["days"] * DAY:
                self._finalize(key, e, now)
        if not ds.ready(now):
            return False
        for chain in self.p["chains"]:
            due = sorted((e for e in st["followup"].values() if e["chain"] == chain and now - e["last"] >= every),
                         key=lambda e: e["last"])[:30]
            if not due:
                continue
            addrs = [e["addr"] for e in due]
            st_, obj = self._get("dexscreener", self._url("ds_tokens", chain=chain, addrs=",".join(addrs)), now)
            pairs = parse_ds_pairs(obj, now) if st_ == 200 else []
            if pairs:
                best = best_pairs(pairs, chain)
                for e in due:
                    c = best.get(e["addr"])
                    px, liq = (c["price"] or 0.0, c["liq"]) if c else (0.0, 0.0)
                    e.update(px=px, liq=liq, px_max=max(e["px_max"], px), px_min=min(e["px_min"], px),
                             liq_min=min(e["liq_min"], liq), last=now, n=e["n"] + 1)
            elif st_ == 200:
                for e in due:
                    e.update(last=now, n=e["n"] + 1)
            self.dirty = True
            return True
        return False

    def _finalize(self, key, e, now):
        F = self.p["followup"]
        rugged = e["liq_min"] <= e["liq0"] * (1 - F["rug_liq"]) or e["px_min"] <= e["px0"] * (1 - F["rug_px"])
        ran_up = e["px_max"] >= e["px0"] * (1 + F["runup"])
        append_csv(f"{self.dir}/rejected_followup.csv", [{
            "time": ts(now), "chain": e["chain"], "symbol": e["sym"], "address": e["addr"], "rejected": ts(e["t0"]),
            "days": round((now - e["t0"]) / DAY, 1), "checks": e["n"], "px0": e["px0"], "px_max": e["px_max"],
            "px_min": e["px_min"], "px_last": e["px"], "liq0": round(e["liq0"]), "liq_min": round(e["liq_min"]),
            "liq_last": round(e["liq"]), "max_gain": round(e["px_max"] / e["px0"] - 1, 3),
            "rugged": int(rugged), "ran_up": int(ran_up)}])
        del self.state["followup"][key]
        self.dirty = True


_HUNTER = None


def hunter(**kw):
    """Process-wide instance (markets.py and run_live share it)."""
    global _HUNTER
    if _HUNTER is None:
        _HUNTER = DexHunter(**kw)
    return _HUNTER


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="self-check only (one probe per source)")
    ap.add_argument("--ticks", type=int, default=120, help="seconds to run the tick loop")
    a = ap.parse_args()
    h = hunter()
    h.self_check()
    if not a.check:
        for _ in range(a.ticks):
            h.tick()
            time.sleep(1)
        print(h.status_line())
