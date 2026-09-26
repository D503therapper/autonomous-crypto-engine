"""DEX (on-chain) PAPER trader with a STRICT scam screen: the "dex_hunter" $500 account.
Paper only: no wallet, no keys, no transactions. Fills are simulated from public DEX price data.

Discovery (config.DEX["chains"]: solana / base / ethereum):
    GeckoTerminal /networks/{net}/trending_pools?duration=1h   (organic; 20 pools per chain)
    DexScreener  /token-boosts/top/v1 -> /tokens/v1/{chain}/{addrs}   (paid boosts; data lookup)
    data/social/dex_watch.json (social.py's DEX watchlist: symbols trending but NOT on Crypto.com)
    -> DexScreener /latest/dex/search?q=SYMBOL to resolve the contract address
Scam screen (EVERY check must pass; fail closed when a required source is unreachable; every
verdict + reasons -> data/dex/screen.csv):
    market sanity from DexScreener: liquidity >= max($250k, 50 x planned position), pool age >= 24h,
        24h volume >= $300k, buys AND sells in 24h, no spike-and-fade (+30% 6h, -15% 1h)
    EVM (base, ethereum): GoPlus token_security AND honeypot.is IsHoneypot must both pass
    Solana: GoPlus solana/token_security AND RugCheck report/summary must both pass
    rejected: honeypot / cannot sell all / sell simulation failed, buy or sell tax > 3%, mintable /
        mint authority, freeze authority, transfer pausable, black/whitelist, hidden owner, can take
        back ownership, owner can change balance, selfdestruct, not open source, proxy, creator or
        owner > 5%, top-10 holders > 40% (LP / burn / exchange addresses excluded), LP locked or
        burned < 95%, RugCheck "danger" risks / rugged / score > 50
Trading:
    entry   momentum on a screened token: 1h >= +5%, 6h >= +10%, 1h buys >= 1.2 x sells (no cap
            on prior gains); at most 4 open, DEX exposure <= 60% of equity, paused after 2 scams/30d
    size    tier A "new" 3% of equity (passes the screen, age < 7d or liquidity < $1M)
            tier B "proven" 10% (age >= 7d, liq >= $1M, vol24 >= $1M, 2 consecutive clean re-screens)
            tier C "blue" 20% (age >= 30d, liq >= $5M, trades on a major CEX: Crypto.com tickers
            or config.DEX["cex_list"]); every size is capped at 0.5% of pool liquidity, liquidity/50
            and available cash. A held tier-A token that earns tier B/C is topped up (never averaged
            down, never after the first take-profit).
    costs   0.3% DEX fee + price impact (usd / liquidity) + 1% slippage, per side
    exits   +100%: sell 50% (cost recovered; stop moves to break-even for the free ride);
            then scale out: +400% (5x) sell a third of the rest, +900% (10x) half of what's left; the last
            ~17% (moonbag) rides with no price cap: trailing stop 30% below peak (40% once the peak is 3x,
            50% once 10x); 14-day max hold only for trades that never doubled
    scams   held tokens re-screened every 30 min (security sources); liquidity -50%, honeypot,
            sell tax > 50% or trading paused -> exit at the realistic post-rug price (no pair left =
            -100%), outcome scammed_rug / scammed_honeypot; EVERY exit first re-runs the sell
            simulation (honeypot.is EVM, GoPlus Solana) and books -100% when it fails
    files   data/dex/screen.csv, outcomes.csv (per trade, with tier), rejected_followup.csv (rejected
            tokens followed 7 days, <= 50 enrolled per day: rugged? ran up > 100%?), state.json,
            data/dex/dex_hunter/{portfolio.json,trades.csv,equity.csv} (shared Portfolio; LAB.md row)

    hunter = dex.hunter()         # run_live shares one instance
    hunter.self_check()           # once per run: HTTP status per source -> run.log
    hunter.tick()                 # every second: bookkeeping + AT MOST ONE HTTP request (<= 8 s)
    hunter.cex = set(scanner.last)   # Crypto.com symbols, for tier C
    python dex.py [--check]       # self-check, or a short live round

GoPlus (EVM), honeypot.is, RugCheck summary, DexScreener and GeckoTerminal were verified reachable
from the GitHub runner (results/probe.txt). The GoPlus Solana path is unverified; all URLs and
field names are config values (config.DEX overrides DEFAULTS, nested keys merge).
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
        "rugcheck": "https://api.rugcheck.xyz/v1/tokens/{addr}/report/summary",   # risks, score_normalised, lpLockedPct
        "ds_tokens": "https://api.dexscreener.com/tokens/v1/{chain}/{addrs}",            # <= 30 addresses
        "ds_search": "https://api.dexscreener.com/latest/dex/search?q={q}",
        "ds_boosts": "https://api.dexscreener.com/token-boosts/top/v1",
        "gt_trending": "https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools?duration=1h",
    },
    "ref": {"ethereum": "0x6982508145454ce325ddbe47a25d4ec3d2311933",      # PEPE: self-check probe
            "solana": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"},     # BONK
    "timeout": 6,                                                    # seconds per request (hard cap 8)
    "gap_s": {"goplus": 3, "honeypot": 3, "rugcheck": 3, "dexscreener": 1.5, "geckoterminal": 2.5},
    "every_s": {"discover": 300, "watch": 600, "prices": 60, "rescreen": 1800, "followup": 3600},
    "screen": {                                                      # STRICT by owner's choice
        "max_tax": 0.03, "reject_proxy": True, "max_creator_pct": 0.05, "max_top10_pct": 0.40,
        "min_lp_locked": 0.95, "rugcheck_max_score": 50,             # score_normalised (0-100, higher = worse)
        "min_liq": 250_000, "liq_x_size": 50,                        # liquidity >= max($250k, 50 x position)
        "min_age_h": 24, "min_vol24": 300_000,
        "mature": {"age_h": 720, "liq": 1_000_000},                  # 30+ days with $1M+: LP lock not required
        "age_unknown_liq": 1_000_000,                                # no pool age from the source: OK if $1M+ liquidity
        "max_24h_change": None,                                      # owner: no cap on runners
        "fade_h6": 0.30, "fade_h1": -0.15,                           # +30% in 6h but -15% in the last hour
        "ttl_h": 6, "reject_ttl_h": 24, "unreach_ttl_h": 1,          # how long a verdict stands
    },
    "entry": {"h1": 0.05, "h6": 0.10, "buy_ratio": 1.2},            # +5% 1h, +10% 6h, 1h buys >= 1.2x sells
    "tiers": {                                                       # sizing by safety (share of equity)
        "A": {"pct": 0.03},                                          # "new": passes the screen
        "B": {"pct": 0.10, "age_d": 7, "liq": 1_000_000, "vol24": 1_000_000, "clean": 2},   # 2 clean re-screens
        "C": {"pct": 0.20, "age_d": 30, "liq": 5_000_000, "vol24": 0, "clean": 0, "cex": True},
    },
    "cex_list": [],                                                  # symbols known to trade on a major CEX
    "size": {"liq_pct": 0.005, "max_exposure": 0.60},                # <= 0.5% of the pool; DEX <= 60% of equity
    "cost": {"fee": 0.003, "slip": 0.01},                            # + price impact usd/liquidity per side
    "exit": {"trail": 0.30, "tp1": (1.0, 0.5), "ladder": [(4.0, 1 / 3), (9.0, 0.5)],   # 2x: half; 5x: a third
             "trail_steps": [(3.0, 0.40), (10.0, 0.50)],   # of the rest; 10x: half again; ~17% moonbag rides
             "max_hold_days": 14, "liq_pull": 0.50, "rug_tax": 0.50,
             "check_wait_s": 600},                                   # sell check unreachable this long -> book at market
    "followup": {"days": 7, "per_day": 50, "rug_liq": 0.80, "rug_px": 0.90, "runup": 1.0},
    "scam_pause": {"max": 2, "days": 30, "reset_after": ""},         # 2 scams in 30 days -> no new entries until
    "slots": 4, "queue": 20, "dir": "data/dex", "name": "dex_hunter",   # reset_after "YYYY-MM-DD HH:MM" > pause time
}


def _merge(base, over):
    """Recursive dict merge (config.DEX overrides DEFAULTS key by key)."""
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


DEX = _merge(DEFAULTS, getattr(config, "DEX", {}))
BURN = {"0x0000000000000000000000000000000000000000", "0x000000000000000000000000000000000000dead",
        "1nc1nerator11111111111111111111111111111111"}
# holder tags that are NOT whales: pools, lockers, burn, known exchanges / market makers
_LP_TAG = re.compile(r"burn|dead|null|lock|\blp\b|pool|uniswap|pancake|raydium|orca|meteora|pumpswap|vault|"
                     r"exchange|binance|coinbase|okx|bybit|kraken|gate|kucoin|bitget|htx|mexc|wintermute|\bcex\b", re.I)
_LOCK_TAG = re.compile(r"burn|dead|null|lock", re.I)
PRIO = {"scammed_rug": 4, "scammed_honeypot": 4, "emergency_exit": 3, "stop": 2, "tp": 1}
SOL_AUTH = {"freezable": "freeze authority", "mintable": "mint authority", "closable": "close authority"}


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


def _ak(addr):
    """Address key: EVM addresses are case-insensitive (GeckoTerminal sends lowercase, DexScreener
    checksummed mixed case); Solana addresses are case-sensitive and kept as-is."""
    a = str(addr or "")
    return a.lower() if a.startswith("0x") else a


class AddrMap(dict):
    """dict keyed by token address that matches EVM addresses regardless of letter case."""
    def __setitem__(self, k, v):
        super().__setitem__(_ak(k), v)

    def __getitem__(self, k):
        return super().__getitem__(_ak(k))

    def __contains__(self, k):
        return super().__contains__(_ak(k))

    def get(self, k, default=None):
        return super().get(_ak(k), default)


def best_pairs(cands, chain=None):
    """{addr: deepest pair} (optionally one chain only); lookups ignore EVM address case."""
    out = AddrMap()
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
        if not isinstance(a, dict) or not a.get("name"):
            continue
        tid = str((((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", ""))
        if "_" not in tid:
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


# ---- scam checks (pure; each returns [(reason, severity)]) ---------------------------------------
# severity: 'scam' (also fatal for a held token: SCAMMED), 'flag' (reject / emergency exit),
# 'defer' (GoPlus could not read the tax; the second source must confirm it), 'unreach'.
def top_holders(hs, exclude=()):
    """Top-10 share (fraction of supply) excluding LP pools / burn / exchange addresses; None if unknown."""
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


def _tax(r, v, what, S, unknown="flag"):
    """Tax as a fraction (GoPlus '0.05'); None = unknown -> `unknown` severity (fail closed by default)."""
    if v is None:
        r.append((f"{what} unknown", unknown))
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
    # GoPlus reports "" when it could not simulate the tax (e.g. PEPE): honeypot.is must then confirm it
    _tax(r, _f(d.get("buy_tax")), "buy tax", S, unknown="defer")
    _tax(r, _f(d.get("sell_tax")), "sell tax", S, unknown="defer")
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
            r.append((SOL_AUTH.get(k, k), sev))
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
    # GoPlus often has no holder / LP data for Solana pools: missing data is not a scam, so RugCheck
    # (always the next step) must settle it - its LP-lock check and score (which counts holder
    # concentration) still fail closed. Seen 2026-09-26: PAID +247% and ELON +68% rejected on this alone.
    t10 = top_holders(d.get("holders"))
    if t10 is None:
        r.append(("holders unknown", "defer"))
    elif t10 > S["max_top10_pct"]:
        r.append((f"top-10 holders {t10:.0%}", "flag"))
    lp = lp_locked(d.get("lp_holders"))
    if lp is None:
        r.append(("lp holders unknown", "defer"))
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
    sr = sr if isinstance(sr, dict) else {}
    _tax(r, _pct(sr.get("buyTax")), "buy tax", S)
    _tax(r, _pct(sr.get("sellTax")), "sell tax", S)
    return r


def check_rugcheck(j, S):
    """RugCheck report/summary: risks[{name, level: warn|danger}], score_normalised (0-100), lpLockedPct;
    the full report adds rugged, mintAuthority / freezeAuthority (null = renounced), markets[].lp."""
    if not isinstance(j, dict) or ("risks" not in j and "score" not in j):
        return [("rugcheck: no data", "flag")]
    r = []
    if j.get("rugged"):
        r.append(("rugcheck: rugged", "scam"))
    names = [str(k.get("name") or "") for k in j.get("risks") or [] if isinstance(k, dict)]
    for k in j.get("risks") or []:
        if isinstance(k, dict) and str(k.get("level", "")).lower() == "danger":
            name = str(k.get("name") or "risk")
            r.append((f"rugcheck danger: {name}", "scam" if re.search(r"freeze|honeypot|transfer", name, re.I) else "flag"))
    for k, sev in (("mintAuthority", "flag"), ("freezeAuthority", "scam")):
        if j.get(k) or any(re.search(k[:4], n, re.I) and re.search("enabled|authority", n, re.I) for n in names):
            if not any(k[:4] in t.lower() for t, _ in r):
                r.append((f"rugcheck: {k} enabled", sev))
    lps = [_f(j.get("lpLockedPct"))] + [_f(((m.get("lp") or {}) if isinstance(m, dict) else {}).get("lpLockedPct"))
                                       for m in j.get("markets") or []]
    lps = [x for x in lps if x is not None]
    if not lps:
        r.append(("rugcheck: lp lock unknown", "flag"))
    elif max(lps) / 100 < S["min_lp_locked"]:
        r.append((f"rugcheck lp locked {max(lps):.0f}% < {S['min_lp_locked']:.0%}", "flag"))
    sc = _f(j.get("score_normalised"))
    if sc is not None and sc > S["rugcheck_max_score"]:
        r.append((f"rugcheck score {sc:.0f}", "flag"))
    return r


# The LP-lock rule guards against a new pool's creator pulling the liquidity. Uniswap v3/v4 and CLMM
# positions can't be "locked" at all, so an old deep pool reads 0% locked; after 30+ days with $1M+ in it,
# unlocked LP is normal (the liquidity-pull emergency exit still watches every held pool).
_LP_REASON = re.compile(r"^(lp locked|lp holders unknown|rugcheck lp locked|rugcheck: lp lock unknown|rugcheck danger: .*lp unlocked)", re.I)


def _mature(c, S):
    M = S.get("mature") or {}
    return (c.get("age_h") or 0) >= M.get("age_h", float("inf")) and (c.get("liq") or 0) >= M.get("liq", float("inf"))


def check_market(c, S):
    r = []
    if not c.get("price") or c["price"] <= 0:
        r.append(("no price", "flag"))
    if c["liq"] < S["min_liq"]:
        r.append((f"liquidity ${c['liq']:,.0f} < ${S['min_liq']:,.0f}", "flag"))
    if c.get("age_h") is None:
        if c["liq"] < S["age_unknown_liq"]:          # missing data on a deep pool is not a red flag
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


# ---- tiered sizing (pure) --------------------------------------------------------------------------
def tier_for(c, T, clean=0, on_cex=False):
    """'C' / 'B' / 'A' from pool age (age_h), liquidity, 24h volume, consecutive clean re-screens
    and (tier C) a major-CEX listing. Anything that merely passed the screen is tier A."""
    age_d = (c.get("age_h") or 0) / 24
    for name in ("C", "B"):
        t = T[name]
        if age_d >= t["age_d"] and c["liq"] >= t["liq"] and (c.get("vol24") or 0) >= t.get("vol24", 0) \
                and clean >= t.get("clean", 0) and (on_cex or not t.get("cex")):
            return name
    return "A"


def size_for(eq, liq, tier, cash, exposure, P):
    """USD to hold: tier % of equity, capped at 0.5% of pool liquidity, liquidity / 50 (the screen's
    50x rule), available cash and the room left under the 60% DEX exposure cap."""
    return max(0.0, min(eq * P["tiers"][tier]["pct"], liq * P["size"]["liq_pct"], liq / P["screen"]["liq_x_size"],
                        cash, eq * P["size"]["max_exposure"] - exposure))


def trade_cost(usd, liq, P):
    """Per-side cost of a simulated fill: 1% slippage + price impact usd / liquidity (fee 0.3% is separate)."""
    return min(1.0, P["cost"]["slip"] + (usd / liq if liq > 0 else 1.0))


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
          "status": {}, "week": None, "hour": None, "prefiltered": 0, "scams": [], "paused": None}
_STEP_SRC = {"ds": "dexscreener", "goplus": "goplus", "honeypot": "honeypot", "rugcheck": "rugcheck"}


class DexHunter:
    """The dex_hunter paper account. run_live drives it with tick() once a second and adds its
    balance to LAB.md / the scoreboard from data/dex/dex_hunter (it is never fed candles)."""

    def __init__(self, params=None, fetch=None, now_ms=None):
        self.p = _merge(DEX, params or {})
        self.name, self.dir = self.p["name"], self.p["dir"]
        self.acct = f"{self.dir}/{self.name}"
        self.clock, self.fetch = now_ms, fetch
        self.src = {n: Source(n, fetch, self.p["timeout"], g) for n, g in self.p["gap_s"].items()}
        self.state, self.pf, self.queue, self.jobs, self.lookup = None, None, [], {}, []
        self.cex = set()                              # run_live: Crypto.com symbols (tier C)
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

    def exposure(self):
        """USD currently in DEX positions (marked at the last price)."""
        px = self.prices()
        return sum(p["qty"] * px[k] for k, p in self.pf.positions.items())

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

    def S(self):
        """Screen thresholds; min liquidity = max($250k, 50 x the planned tier-A position)."""
        S = self.p["screen"]
        return dict(S, min_liq=max(S["min_liq"], S["liq_x_size"] * self.equity() * self.p["tiers"]["A"]["pct"]))

    def on_cex(self, sym):
        return sym in self.cex or sym in set(self.p["cex_list"])

    def paused(self):
        p = self.state.get("paused")
        return p["why"] if p else ""

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
                f"{len(self.state['followup'])} rejected in follow-up, {self.state['prefiltered']} prefiltered"
                f"{'  [PAUSED: ' + self.paused() + ']' if self.paused() else ''}")

    # ---- housekeeping (no HTTP) ----
    def _housekeep(self, now):
        st, S, X = self.state, self.p["screen"], self.p["exit"]
        for k, pos in list(self.pf.positions.items()):        # sell check unreachable for too long
            ex = pos.get("exit")
            if ex and now - ex["t"] > X["check_wait_s"] * 1000:
                self._execute_exit(k, [], now, " (sell check unreachable, booked at market)")
        reset = self.p["scam_pause"]["reset_after"]
        if st["paused"] and reset and ts(st["paused"]["t"]) < reset:   # manual re-enable via config
            print(f"   dex: pause lifted (reset_after {reset})")
            st["paused"], st["scams"], self.dirty = None, [], True
        if st.get("rules") != S.get("rules"):          # screen rules changed: old rejections get a fresh look
            st["seen"] = {k: v for k, v in st["seen"].items() if v["v"] != "REJECT"}
            st["rules"], self.dirty = S.get("rules"), True
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

    def weekly_line(self, now):
        """run.log summary of the last 7 days: screen counts, trades, scams, P/L by tier, rejected fates."""
        since = now - 7 * DAY
        sc = self._rows(f"{self.dir}/screen.csv", since)
        tr = self._rows(f"{self.acct}/trades.csv", since)
        oc = self._rows(f"{self.dir}/outcomes.csv", since)
        fu = self._rows(f"{self.dir}/rejected_followup.csv", since)
        scam = [r for r in oc if r["outcome"].startswith("scammed")]
        by_tier = {t: [_f(r["pnl"]) or 0 for r in oc if r.get("tier") == t] for t in self.p["tiers"]}
        tiers = " ".join(f"{t} ${sum(v):+.2f}/{len(v)}" for t, v in by_tier.items())
        return (f"dex weekly: screened {len(sc)}, passed {sum(r['verdict'] == 'PASS' for r in sc)}, "
                f"trades {sum(r['side'] == 'BUY' for r in tr)}, closed {len(oc)} (P/L ${sum(_f(r['pnl']) or 0 for r in oc):+.2f}; "
                f"by tier {tiers}), scammed {len(scam)} (cost ${sum(_f(r['pnl']) or 0 for r in scam):+.2f}), "
                f"rejected-that-rugged {sum(r['rugged'] == '1' for r in fu)}/{len(fu)}, "
                f"rejected-that-ran-up {sum(r['ran_up'] == '1' for r in fu)}/{len(fu)}")

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
        if check_market(c, self.S()):
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
        c, S, step = job["c"], self.S(), job["steps"][job["i"]]
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
        if _mature(c, S):
            reasons = [x for x in reasons if not _LP_REASON.search(x[0])]
        job["reasons"] += reasons
        job["done"] = job.get("done", 0) + 1
        hard = [r for r in reasons if r[1] != "defer"]         # a deferred check needs the second source's word
        job["i"] = len(job["steps"]) if hard else job["i"] + 1    # first hard failure ends the screen

    def _finish(self, job, now):
        c, rs, st = job["c"], job["reasons"], self.state
        if not any(s not in ("defer",) for _, s in rs):        # every step passed: the 2nd source settled it
            rs = []
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
            else:
                pos["clean"] = pos.get("clean", 0) + 1
                self._upgrade(job["key"], pos, now)
            return
        verdict = "UNREACHABLE" if any(s == "unreach" for _, s in rs) else ("REJECT" if rs else "PASS")
        append_csv(f"{self.dir}/screen.csv", [{
            "time": ts(now), "chain": c["chain"], "symbol": c["sym"], "address": c["addr"], "pair": c.get("pair") or "",
            "verdict": verdict, "reasons": why, "price": c.get("price"), "liq_usd": round(c["liq"]),
            "vol24_usd": round(c["vol24"]), "age_h": None if c.get("age_h") is None else round(c["age_h"], 1),
            "fdv": c.get("fdv"), "buys_h1": c.get("b1"), "sells_h1": c.get("s1"), "h1": c.get("h1"), "h6": c.get("h6"),
            "h24": c.get("h24"), "sources": "+".join(job["steps"][:job.get("done", 0)])}])
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
        if not c or self.pf.halted or self.paused() or len(self.pf.positions) >= self.p["slots"]:
            return
        pk = self.pkey(c)
        if pk in self.pf.positions or self.pf.cooldown.get(pk, 0) > now or not c.get("price"):
            return
        h1, h6, b1, s1 = c.get("h1"), c.get("h6"), c.get("b1") or 0, c.get("s1") or 0
        if h1 is None or h6 is None or h1 < E["h1"] or h6 < E["h6"] or b1 < max(1, s1 * E["buy_ratio"]):
            return
        eq, X = self.equity(), self.p["exit"]
        tier = tier_for(c, self.p["tiers"], 0, self.on_cex(c["sym"]))
        usd = size_for(eq, c["liq"], tier, self.pf.cash, self.exposure(), self.p)
        if usd < config.MIN_ORDER_USD:
            return
        impact = usd / c["liq"]
        self.pf.slippage = trade_cost(usd, c["liq"], self.p)
        self.pf.buy(now, pk, usd, c["price"], c["price"] * (1 - X["trail"]),
                    reason=f"dex tier {tier} momentum 1h {h1:+.0%} 6h {h6:+.0%} buys/sells {b1}/{s1} impact {impact:.2%}")
        self.pf.positions[pk].update(chain=c["chain"], addr=c["addr"], sym=c["sym"], pair=c.get("pair"), liq0=c["liq"],
                                     liq=c["liq"], vol24=c["vol24"], age_h0=c.get("age_h") or 0, px=c["price"],
                                     tp1=False, tp2=False, realized=0.0, cost0=usd, rescreened=now, impact=impact,
                                     tier=tier, clean=0)
        del st["passed"][key]
        self.dirty = True
        self._save_pf(now)                        # no phone alert: owner wants daily P/L only

    def _upgrade(self, k, pos, now):
        """After a clean re-screen: a held token that now earns a higher tier is topped up to that
        tier's size (only while in profit and before the first take-profit; never averaging down)."""
        T, px = self.p["tiers"], pos.get("px") or pos["entry"]
        c = {"liq": pos["liq"], "vol24": pos.get("vol24", 0), "age_h": pos["age_h0"] + (now - pos["opened"]) / HOUR}
        tier = tier_for(c, T, pos.get("clean", 0), self.on_cex(pos["sym"]))
        if T[tier]["pct"] <= T[pos["tier"]]["pct"] or pos["tp1"] or px < pos["entry"] or self.paused():
            return
        add = size_for(self.equity(), pos["liq"], tier, self.pf.cash, self.exposure(), self.p) - pos["qty"] * px
        if add < config.MIN_ORDER_USD:
            return
        slip = trade_cost(add, pos["liq"], self.p)
        fill, fee = px * (1 + slip), add * self.pf.fee
        qty = (add - fee) / fill
        pos["entry"] = (pos["entry"] * pos["qty"] + fill * qty) / (pos["qty"] + qty)   # blended: +100% = cost back
        pos["qty"], pos["cost"], pos["cost0"], pos["tier"] = pos["qty"] + qty, pos["cost"] + add, pos["cost0"] + add, tier
        pos["peak"] = max(pos["peak"], fill)
        self.pf.cash -= add
        self.pf._record(now, "BUY", k, qty, fill, fee, f"dex tier {pos['tier']} -> {tier} top-up after {pos['clean']} clean re-screens")
        self._save_pf(now)

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
            if st_ != 200 or not isinstance(obj, list):        # (tokens/v1 answers a bare list)
                return True
            best = best_pairs(parse_ds_pairs(obj, now), chain)
            for k, pos in list(self.pf.positions.items()):
                if pos["chain"] != chain or pos["addr"] not in addrs:
                    continue
                c = best.get(pos["addr"])
                if c and c.get("price"):
                    pos.update(px=c["price"], liq=c["liq"], vol24=c["vol24"], seen_px=now)
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
        trail = X["trail"]                             # the stop gets more room as the coin multiplies,
        for mult, t in X.get("trail_steps", []):       # so normal shakeouts don't end a 10x-100x runner
            if pos["peak"] >= pos["entry"] * mult:
                trail = t
        if pos.get("runner"):                          # past the time limit up >= 2x: rides its own trail
            trail = min(trail, X["runner_at_limit"][1])
        pos["stop"] = max(pos["stop"], pos["peak"] * (1 - trail))
        if p <= pos["stop"]:
            return self._request_exit(k, 1.0, f"trailing stop (peak {pos['peak']:g})", "normal", now, "stop")
        if not pos["tp1"] and not pos.get("runner") and now - pos["opened"] >= X["max_hold_days"] * DAY:
            R = X.get("runner_at_limit")
            if R and p >= pos["entry"] * (1 + R[0]):   # never sell a runner on the clock (owner rule)
                pos["runner"] = True
                pos["stop"] = max(pos["stop"], pos["peak"] * (1 - R[1]))
                self.dirty = True
                return
            return self._request_exit(k, 1.0, f"time limit {X['max_hold_days']}d", "normal", now, "stop")
        if not pos["tp1"] and p >= pos["entry"] * (1 + X["tp1"][0]):
            pos["tp1"] = True
            return self._request_exit(k, X["tp1"][1], f"take-profit +{X['tp1'][0]:.0%}", "normal", now, "tp")
        # after the first half: scale out in steps (e.g. 5x, 10x) and keep a moonbag riding the wide trail
        n = pos.get("tpn", 0)
        ladder = X.get("ladder", [])
        if pos["tp1"] and n < len(ladder) and p >= pos["entry"] * (1 + ladder[n][0]):
            pos["tpn"] = n + 1
            return self._request_exit(k, ladder[n][1], f"take-profit +{ladder[n][0]:.0%}", "normal", now, "tp")

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
        self.pf.slippage = trade_cost(usd, liq, self.p)
        keep = dict(pos)
        pnl = self.pf.sell(now, k, frac, price, reason)
        realized = keep["realized"] + pnl
        if k in self.pf.positions:
            pos = self.pf.positions[k]
            pos["realized"] = realized
            if pos["tp1"]:                                     # remainder rides free: stop >= break-even
                pos["stop"] = max(pos["stop"], pos["entry"] * (1 + C["slip"] + 2 * C["fee"]))
        else:
            self.pf.cooldown[k] = now + DAY
            append_csv(f"{self.dir}/outcomes.csv", [{
                "time": ts(now), "coin": k, "chain": keep["chain"], "address": keep["addr"], "tier": keep.get("tier", "A"),
                "opened": ts(keep["opened"]), "hold_h": round((now - keep["opened"]) / HOUR, 1),
                "cost_usd": round(keep["cost0"], 2), "pnl": round(realized, 2), "ret": round(realized / keep["cost0"], 4),
                "entry": keep["entry"], "exit": round(price, 10), "liq_entry": round(keep["liq0"]), "liq_exit": round(liq),
                "outcome": outcome, "reason": reason}])
            print(f"   dex outcome: {outcome} {k} tier {keep.get('tier', 'A')} P/L ${realized:+.2f} ({reason})")
            if outcome.startswith("scammed"):
                self._count_scam(now)
        self.dirty = True
        self._save_pf(now)

    def _count_scam(self, now):
        """Owner's circuit breaker: `max` scams within `days` -> pause new entries (latched)."""
        st, P = self.state, self.p["scam_pause"]
        st["scams"] = [t for t in st["scams"] if now - t <= P["days"] * DAY] + [now]
        if len(st["scams"]) >= P["max"] and not st["paused"]:
            st["paused"] = {"t": now, "why": "scam limit"}
            print(f"   dex PAUSED: {len(st['scams'])} scams in {P['days']} days; new entries off until "
                  f"config.DEX['scam_pause']['reset_after'] is set past {ts(now)}")

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


# ---- scoreboard helpers (files only: no HTTP, no state; safe from run_live.scoreboard) ------------------
def scoreboard_stats(d=None, name=None):
    """{equity, trades, scammed, lost, paused} for run_live.scoreboard / the daily summary."""
    d, name = d or DEX["dir"], name or DEX["name"]
    eq, n = config.STARTING_CASH_USD, 0
    try:
        with open(f"{d}/{name}/equity.csv") as f:
            lines = f.read().strip().splitlines()
        if len(lines) > 1:
            eq = float(lines[-1].split(",")[1])
        with open(f"{d}/{name}/trades.csv") as f:
            n = max(0, len(f.read().strip().splitlines()) - 1)
    except (OSError, ValueError):
        pass
    scam, lost = 0, 0.0
    if os.path.exists(f"{d}/outcomes.csv"):
        with open(f"{d}/outcomes.csv", newline="") as f:
            for r in csv.DictReader(f):
                if str(r.get("outcome", "")).startswith("scammed"):
                    scam, lost = scam + 1, lost + (_f(r.get("pnl")) or 0.0)
    paused = ""
    try:
        with open(f"{d}/state.json") as f:
            p = json.load(f).get("paused")
        paused = p["why"] if p else ""
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return {"equity": eq, "trades": n, "scammed": scam, "lost": lost, "paused": paused}


def scoreboard_line(start=config.STARTING_CASH_USD, md=True, d=None):
    """ONE line for SCOREBOARD.md (md=True: bold head) / docs/index.html / the daily summary:
    DEX: $512.40 (+12.40) · Scammed: 1 (-$38.00)      or      DEX paused: scam limit · $462.00 (-38.00) · ..."""
    s, b = scoreboard_stats(d), "**" if md else ""
    bal = f"${s['equity']:,.2f} ({s['equity'] - start:+,.2f})"
    line = f"{b}DEX paused: {s['paused']}{b} · {bal}" if s["paused"] else f"{b}DEX: {bal}{b}"
    line += f" · Scammed: {s['scammed']}"
    if s["scammed"]:
        line += f" (-${-s['lost']:,.2f})" if s["lost"] < 0 else f" (+${s['lost']:,.2f})"
    return line


_HUNTER = None


def hunter(**kw):
    """Process-wide instance (run_live shares it)."""
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
