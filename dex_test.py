"""Offline tests for dex.py: canned GoPlus (EVM + Solana), honeypot.is, RugCheck, DexScreener and
GeckoTerminal payloads; the strict screen (pass / every rejection / fail closed), tiers, sizing
caps and costs, exits (take-profit steps + break-even stop, trailing stop, liquidity pull,
sell-simulation failure, re-screen), the rejected-token follow-up, the scam auto-pause and the
run.log / scoreboard lines. No network: every fetch is a canned table.

    python dex_test.py
"""
import csv
import json
import os
import shutil
import tempfile

import config
import dex
from dex import (DexHunter, best_pairs, check_goplus_evm, check_goplus_sol, check_honeypot, check_market,
                 check_rugcheck, lp_locked, parse_ds_pairs, parse_gt_pools, size_for, tier_for, top_holders, trade_cost)
from social import DAY, HOUR

T0 = 1_760_000_000_000                      # 2025-10-09 UTC
EVM = "0xabc0000000000000000000000000000000000001"
SOL = "So1anaMint111111111111111111111111111111111"
DEAD = "0x000000000000000000000000000000000000dead"
INC = "1nc1nerator11111111111111111111111111111111"
GAP0 = {k: 0 for k in dex.DEFAULTS["gap_s"]}
K = "TOK@base:0xabc000"                     # position key of the default EVM token


# ---- canned payloads ------------------------------------------------------------------------
def ds_pair(chain, addr, sym="TOK", liq=600_000, vol=900_000, age_h=48, price=0.01, h1=8, h6=15, h24=30,
            b1=120, s1=60, b24=2000, s24=1500, pair="PAIR1"):
    return {"chainId": chain, "pairAddress": pair, "baseToken": {"address": addr, "symbol": sym, "name": sym},
            "priceUsd": str(price), "txns": {"h1": {"buys": b1, "sells": s1}, "h24": {"buys": b24, "sells": s24}},
            "volume": {"h24": vol}, "priceChange": {"h1": h1, "h6": h6, "h24": h24}, "liquidity": {"usd": liq},
            "fdv": 5e6, "pairCreatedAt": T0 - age_h * HOUR}


def gt_pool(net, addr, sym="GTK", liq=700_000, vol=800_000, age_h=72, price=0.5):
    from datetime import datetime, timezone
    iso = datetime.fromtimestamp((T0 - age_h * HOUR) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"attributes": {"name": f"{sym} / SOL", "address": "POOL1", "base_token_price_usd": str(price),
                           "reserve_in_usd": str(liq), "volume_usd": {"h24": str(vol)}, "fdv_usd": "5000000",
                           "price_change_percentage": {"h1": "6.5", "h6": "12", "h24": "40"},
                           "transactions": {"h1": {"buys": 100, "sells": 50}, "h24": {"buys": 900, "sells": 700}},
                           "pool_created_at": iso},
            "relationships": {"base_token": {"data": {"id": f"{net}_{addr}"}}, "network": {"data": {"id": net}}}}


def gp_evm(addr=EVM, **over):
    d = {"is_honeypot": "0", "cannot_sell_all": "0", "transfer_pausable": "0", "cannot_buy": "0", "is_mintable": "0",
         "is_blacklisted": "0", "is_whitelisted": "0", "hidden_owner": "0", "can_take_back_ownership": "0",
         "owner_change_balance": "0", "selfdestruct": "0", "honeypot_with_same_creator": "0", "is_proxy": "0",
         "is_open_source": "1", "buy_tax": "0.01", "sell_tax": "0.01", "creator_percent": "0.02", "owner_percent": "0",
         "dex": [{"name": "UniswapV2", "pair": "0xpair"}],
         "holders": [{"address": "0xpair", "tag": "UniswapV2", "is_contract": 1, "percent": "0.30", "is_locked": 0},
                     {"address": "0xbinance", "tag": "Binance 14", "is_contract": 0, "percent": "0.20"}]
                    + [{"address": f"0xh{i}", "tag": "", "is_contract": 0, "percent": "0.03"} for i in range(10)],
         "lp_holders": [{"address": DEAD, "tag": "Null Address", "percent": "0.97", "is_locked": 1},
                        {"address": "0xlp2", "tag": "", "percent": "0.03", "is_locked": 0}]}
    d.update(over)
    return {"code": 1, "message": "OK", "result": {addr: d}}


def gp_sol(addr=SOL, **over):
    d = {"mintable": {"status": "0", "authority": []}, "freezable": {"status": "0", "authority": []},
         "closable": {"status": "0"}, "non_transferable": "0", "balance_mutable_authority": {"status": "0"},
         "transfer_fee": {}, "transfer_fee_upgradable": {"status": "0"}, "transfer_hook": [],
         "transfer_hook_upgradable": {"status": "0"}, "creators": [{"address": "Creator1", "malicious_address": 0}],
         "holders": [{"account": "Creator1", "percent": "0.02", "tag": ""}, {"account": "RayPool", "percent": "0.4", "tag": "Raydium"}]
                    + [{"account": f"H{i}", "percent": "0.03", "tag": ""} for i in range(10)],
         "lp_holders": [{"account": INC, "percent": "1.0", "is_locked": 0, "tag": ""}]}
    d.update(over)
    return {"code": 1, "message": "ok", "result": {addr: d}}


HP_OK = {"simulationSuccess": True, "honeypotResult": {"isHoneypot": False},
         "simulationResult": {"buyTax": 0.2, "sellTax": 1.0}}
HP_BAD = {"simulationSuccess": True, "honeypotResult": {"isHoneypot": True, "honeypotReason": "sell reverted"},
          "simulationResult": {"buyTax": 0, "sellTax": 100}}
RC_OK = {"tokenProgram": "Tokenkeg", "tokenType": "", "score": 100, "score_normalised": 5,      # report/summary shape
         "risks": [{"name": "Low amount of LP Providers", "level": "warn"}], "lpLockedPct": 100}


def fake_fetch(table):
    """fetch(url, timeout) -> (status, text) from an ordered {substring: (status, body) | fn(url)}."""
    calls = []

    def fetch(url, timeout):
        assert timeout <= 8, timeout
        calls.append(url)
        for k, v in table.items():
            if k in url:
                st, body = v(url) if callable(v) else v
                return st, body if isinstance(body, str) else json.dumps(body)
        return 404, ""
    fetch.calls = calls
    return fetch


def table_evm(pair=None, gp=None, hp=None, chain="base", addr=EVM):
    return {f"tokens/v1/{chain}/": (200, [pair or ds_pair(chain, addr)]),
            f"token_security/8453?contract_addresses={addr}": (200, gp or gp_evm(addr)),
            f"IsHoneypot?address={addr}&chainID=8453": (200, hp or HP_OK)}


def table_sol(pair=None, gp=None, rc=None, addr=SOL):
    return {"tokens/v1/solana/": (200, [pair or ds_pair("solana", addr)]),
            f"solana/token_security?contract_addresses={addr}": (200, gp or gp_sol(addr)),
            f"rugcheck.xyz/v1/tokens/{addr}/report/summary": (200, rc or RC_OK)}


# The mechanics tests below were written for this entry / exit (the ladder and trailing-stop code stays in
# dex.py); they are pinned here so a config change doesn't silently disable them. test_study_exit covers
# the live config (hold 14 days, runner rule).
LADDER = {"tiers": {"A": {"pct": 0.03}, "B": {"pct": 0.10, "age_d": 7, "liq": 1_000_000, "vol24": 1_000_000, "clean": 2},
                    "C": {"pct": 0.20, "age_d": 30, "liq": 5_000_000, "vol24": 0, "clean": 0, "cex": True}},
          "size": {"liq_pct": 0.005, "max_exposure": 0.60},
          "slots": 4,
          "entry": {"h1": 0.05, "h6": 0.10, "buy_ratio": 1.2},
          "exit": {"trail": 0.30, "tp1": (1.0, 0.5), "ladder": [(4.0, 1 / 3), (9.0, 0.5)],
                   "trail_steps": [(3.0, 0.40), (10.0, 0.50)], "max_hold_days": 14, "runner_at_limit": None,
                   "liq_pull": 0.50, "rug_tax": 0.50, "stake_back": None, "pyramid": None}}


def make(table, **params):
    """Hunter on a temp dir with a canned fetch; discovery endpoints answer empty unless the table says."""
    params = dict(LADDER, **params)
    params.setdefault("scan", {"enabled": False})           # the wide scanner has its own tests (test_scan_*)
    params.setdefault("confirm_ms", 0)                      # crash/rug confirmation has its own test
    params.setdefault("season", None)                       # season restart has its own test
    d = tempfile.mkdtemp()
    table = dict(table)
    table.setdefault("token-boosts/top", (200, []))
    table.setdefault("trending_pools", (200, {"data": []}))
    table.setdefault("search?q=", (200, {"pairs": []}))      # (the repo's real dex_watch.json is read)
    fetch = fake_fetch(table)
    h = DexHunter(params=dict({"dir": d, "gap_s": GAP0}, **params), fetch=fetch, now_ms=T0)
    h._load()
    return h, fetch, d


def run(h, t, n):
    """n one-second ticks from t; asserts at most one request per tick."""
    for i in range(n):
        before = len(h.fetch.calls)
        h.tick(t + i * 1000)
        assert len(h.fetch.calls) - before <= 1, "more than one request in a tick"
    return t + n * 1000


def screen(h, c, t=T0, n=6, fresh=False):
    assert h._enqueue(c, t, fresh=fresh), "not queued"
    return run(h, t, n)


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def cand(chain="base", addr=EVM, **kw):
    return dex.norm_ds(ds_pair(chain, addr, **kw), T0)


# ---- parsers ---------------------------------------------------------------------------------
def test_parsers():
    ps = parse_ds_pairs([ds_pair("base", EVM), ds_pair("base", EVM, liq=10, pair="P2"), {"baseToken": {}}, "x"], T0)
    assert len(ps) == 2 and ps[0]["sym"] == "TOK" and ps[0]["age_h"] == 48 and ps[0]["h1"] == 0.08 and ps[0]["b24"] == 2000
    assert best_pairs(ps, "base")[EVM]["pair"] == "PAIR1"          # deepest pair wins
    assert parse_ds_pairs({"pairs": [ds_pair("solana", SOL)]}, T0)[0]["chain"] == "solana"
    gt = parse_gt_pools({"data": [gt_pool("solana", SOL), {"attributes": {}}, "junk"]}, "solana", T0)
    assert len(gt) == 1 and gt[0]["addr"] == SOL and gt[0]["sym"] == "GTK" and abs(gt[0]["age_h"] - 72) < 0.01
    assert gt[0]["liq"] == 700_000 and gt[0]["h1"] == 0.065 and gt[0]["b1"] == 100 and gt[0]["price"] == 0.5
    assert parse_gt_pools(None, "solana", T0) == [] and parse_ds_pairs("nope", T0) == []
    assert dex._merge({"a": {"x": 1, "y": 2}, "b": 1}, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}, "b": 1}
    print("  parsers (dexscreener, geckoterminal), config merge      ok")


def test_checks():
    S = dex.DEFAULTS["screen"]
    d = gp_evm()["result"][EVM]
    assert check_goplus_evm(d, S) == []
    assert abs(top_holders(d["holders"], {"0xpair"}) - 0.30) < 1e-9        # pool + exchange wallet excluded
    assert abs(lp_locked(d["lp_holders"]) - 0.97) < 1e-9
    assert lp_locked([]) is None and top_holders(None) is None
    for over, want in ((dict(is_honeypot="1"), "is_honeypot"), (dict(cannot_sell_all="1"), "cannot_sell_all"),
                       (dict(sell_tax="0.12"), "sell tax 12%"), (dict(buy_tax="0.04"), "buy tax 4%"),
                       (dict(is_mintable="1"), "is_mintable"), (dict(transfer_pausable="1"), "transfer_pausable"),
                       (dict(is_blacklisted="1"), "is_blacklisted"), (dict(is_whitelisted="1"), "is_whitelisted"),
                       (dict(hidden_owner=1), "hidden_owner"), (dict(can_take_back_ownership="1"), "can_take_back_ownership"),
                       (dict(owner_change_balance="1"), "owner_change_balance"), (dict(selfdestruct="1"), "selfdestruct"),
                       (dict(is_proxy="1"), "is_proxy"), (dict(is_open_source="0"), "not open source"),
                       (dict(creator_percent="0.08"), "creator_percent 8%"), (dict(owner_percent="0.06"), "owner_percent 6%"),
                       (dict(lp_holders=[{"address": "0xlp", "percent": "1.0", "is_locked": 0}]), "lp locked 0%"),
                       (dict(lp_holders=[{"address": DEAD, "percent": "0.9"}, {"address": "0xd", "percent": "0.1"}]), "lp locked 90%"),
                       (dict(lp_holders=[]), "lp holders unknown"),
                       (dict(holders=[{"address": f"0xw{i}", "percent": "0.06"} for i in range(10)]), "top-10 holders 60%")):
        rs = check_goplus_evm(gp_evm(**over)["result"][EVM], S)
        assert any(want in t for t, _ in rs), (over, rs)
    assert ("sell tax 60%", "scam") in check_goplus_evm(gp_evm(sell_tax="0.6")["result"][EVM], S)
    assert ("sell tax 12%", "flag") in check_goplus_evm(gp_evm(sell_tax="0.12")["result"][EVM], S)
    assert check_goplus_evm(gp_evm(buy_tax="")["result"][EVM], S) == [("buy tax unknown", "defer")]   # PEPE-style ""
    s = gp_sol()["result"][SOL]
    assert check_goplus_sol(s, S) == []
    for over, want in ((dict(mintable={"status": "1", "authority": ["X"]}), "mint authority"),
                       (dict(freezable={"status": "1"}), "freeze authority"), (dict(non_transferable="1"), "non_transferable"),
                       (dict(transfer_fee={"fee_rate": "0.1"}), "sell tax 10%"), (dict(transfer_hook=[{"x": 1}]), "transfer hook"),
                       (dict(lp_holders=[{"account": "Dev", "percent": "1.0"}]), "lp locked 0%"),
                       (dict(holders=[{"account": "Creator1", "percent": "0.2"}]), "creator holds 20%")):
        rs = check_goplus_sol(gp_sol(**over)["result"][SOL], S)
        assert any(want in t for t, _ in rs), (over, rs)
    assert ("freeze authority", "scam") in check_goplus_sol(gp_sol(freezable={"status": "1"})["result"][SOL], S)
    assert check_honeypot(HP_OK, S) == [] and any("honeypot" in t for t, _ in check_honeypot(HP_BAD, S))
    assert any("sell tax 8%" in t for t, _ in check_honeypot(dict(HP_OK, simulationResult={"buyTax": 0, "sellTax": 8}), S))
    assert check_honeypot({"simulationSuccess": False, "honeypotResult": {}}, S)[0] == ("sell simulation failed", "scam")
    assert ("sell tax unknown", "flag") in check_honeypot({"honeypotResult": {"isHoneypot": False}}, S)   # no simulation
    assert check_honeypot({}, S) == [("honeypot.is: no data", "flag")]
    assert check_rugcheck(RC_OK, S) == []
    assert any("freezeAuthority" in t for t, _ in check_rugcheck(dict(RC_OK, freezeAuthority="Auth1"), S))
    assert any("mintAuthority" in t for t, _ in check_rugcheck(dict(RC_OK, mintAuthority="Auth1"), S))
    assert any("lp lock unknown" in t for t, _ in check_rugcheck(dict(RC_OK, lpLockedPct=None), S))
    assert any("lp locked 48%" in t for t, _ in check_rugcheck(dict(RC_OK, lpLockedPct=47.7), S))    # probe: BONK-like pool
    assert any("lp locked 50%" in t for t, _ in check_rugcheck(dict(RC_OK, lpLockedPct=None, markets=[{"lp": {"lpLockedPct": 50}}]), S))
    assert any("danger" in t for t, _ in check_rugcheck(dict(RC_OK, risks=[{"name": "Freeze Authority still enabled", "level": "danger"}]), S))
    assert any("rugcheck score 80" in t for t, _ in check_rugcheck(dict(RC_OK, score_normalised=80), S))
    assert ("rugcheck: rugged", "scam") in check_rugcheck(dict(RC_OK, rugged=True), S)
    assert check_rugcheck({"foo": 1}, S) == [("rugcheck: no data", "flag")]
    assert check_market(cand(), S) == []
    for kw, want in ((dict(liq=20_000), "liquidity $20,000"), (dict(age_h=5), "pool age 5.0h < 24h"),
                     (dict(vol=1000), "24h volume"), (dict(s24=0), "no buys or no sells"),
                     (dict(h6=40, h1=-20), "spike-and-fade")):
        assert any(want in t for t, _ in check_market(cand(**kw), S)), (kw, check_market(cand(**kw), S))
    assert check_market(cand(h24=2000), S) == []                                     # no 24h cap by default
    assert check_market(cand(h24=2000), dict(S, max_24h_change=10.0)) != []
    c = cand(); c["age_h"] = None
    assert any("age unknown" in t for t, _ in check_market(c, S))
    print("  scam checks (goplus evm/sol, honeypot.is, rugcheck summary, market)  ok")


# ---- tiers, sizing, costs (pure) --------------------------------------------------------------
def test_tiers_and_sizing():
    P, T = dex.DEFAULTS, dex.DEFAULTS["tiers"]
    assert tier_for(cand(), T) == "A"                                                  # 48h old: new
    assert tier_for(cand(age_h=10 * 24, liq=2e6, vol=2e6), T) == "A"                 # needs 2 clean re-screens...
    assert tier_for(cand(age_h=10 * 24, liq=2e6, vol=2e6), T, clean=2) == "B"        # ...then proven
    assert tier_for(cand(age_h=10 * 24, liq=2e6, vol=5e5), T, clean=2) == "A"        # volume < $1M
    assert tier_for(cand(age_h=40 * 24, liq=6e6, vol=2e6), T, clean=0) == "A"        # blue needs a CEX listing
    assert tier_for(cand(age_h=40 * 24, liq=6e6, vol=2e6), T, clean=0, on_cex=True) == "C"
    assert tier_for(cand(age_h=40 * 24, liq=4e6, vol=2e6), T, clean=2, on_cex=True) == "B"   # liq < $5M
    # owner's examples: $10k equity tier A = $300 (needs >= $250k liquidity: the screen floor);
    # $100k equity tier C = $20k needs >= $4M liquidity (0.5% rule), else capped
    assert size_for(10_000, 250_000, "A", 10_000, 0, P) == 300
    assert size_for(10_000, 50_000, "A", 10_000, 0, P) == 250                         # 0.5% of a $50k pool
    assert size_for(100_000, 4_000_000, "C", 100_000, 0, P) == 20_000
    assert size_for(100_000, 3_000_000, "C", 100_000, 0, P) == 15_000
    assert size_for(100_000, 5_000_000, "B", 100_000, 0, P) == 10_000
    assert size_for(500, 600_000, "A", 500, 0, P) == 15
    assert size_for(500, 600_000, "C", 500, 0, P) == 100
    assert size_for(500, 600_000, "C", 40, 0, P) == 40                                # available cash
    assert size_for(500, 600_000, "C", 500, 250, P) == 50                             # 60% exposure cap: $300 - $250
    assert size_for(500, 600_000, "C", 500, 300, P) == 0
    assert size_for(1e6, 1e6, "A", 1e6, 0, P) == 5000                                 # 0.5% of pool binds before 3%
    assert abs(trade_cost(15, 600_000, P) - (0.01 + 15 / 600_000)) < 1e-12           # 1% slippage + impact
    assert abs(trade_cost(5000, 250_000, P) - 0.03) < 1e-12                           # $5k in a $250k pool: +2%
    assert trade_cost(1, 0, P) == 1.0                                                 # no liquidity: unsellable
    print("  tier assignment, size caps (equity %, 0.5% pool, cash, 60% exposure), price impact   ok")


# ---- screening ------------------------------------------------------------------------------
def test_clean_token_passes_and_buys():
    h, fetch, d = make(table_evm())
    screen(h, cand())
    sc = rows(f"{d}/screen.csv")
    assert sc[-1]["verdict"] == "PASS" and sc[-1]["sources"] == "ds+goplus+honeypot", sc
    assert any("gopluslabs" in u for u in fetch.calls) and any("honeypot.is" in u for u in fetch.calls)
    pos = h.pf.positions[K]
    usd = 500 * 0.03                                             # tier A: 3% of equity = $15
    assert pos["tier"] == "A" and abs(pos["cost0"] - usd) < 1e-9 and pos["liq0"] == 600_000 and pos["tp1"] is False
    t = rows(f"{d}/dex_hunter/trades.csv")[0]
    impact = usd / 600_000
    assert abs(float(t["price"]) - round(0.01 * (1 + 0.01 + impact), 6)) < 1e-9, t   # 1% slippage + impact
    assert abs(float(t["fee"]) - usd * 0.003) < 0.006 and "impact" in t["reason"] and "tier A" in t["reason"]
    assert os.path.exists(f"{d}/dex_hunter/equity.csv") and os.path.exists(f"{d}/dex_hunter/portfolio.json")
    assert abs(h.exposure() - pos["qty"] * 0.01) < 1e-9
    # Solana clean token: goplus solana + rugcheck summary
    h2, fetch2, d2 = make(table_sol(pair=ds_pair("solana", SOL, sym="SOLT")))
    screen(h2, cand("solana", SOL, sym="SOLT"))
    assert rows(f"{d2}/screen.csv")[-1]["sources"] == "ds+goplus+rugcheck" and "SOLT@solana:So1anaMi" in h2.pf.positions
    assert any(u.endswith("/report/summary") for u in fetch2.calls)
    # no momentum -> screened, kept in `passed`, not bought
    h3, _, d3 = make(table_evm(pair=ds_pair("base", EVM, h1=1)))
    screen(h3, cand(h1=1))
    assert rows(f"{d3}/screen.csv")[-1]["verdict"] == "PASS" and not h3.pf.positions and h3.state["passed"]
    # GoPlus cannot read the tax ("" as for PEPE): honeypot.is settles it
    h4, _, d4 = make(table_evm(gp=gp_evm(buy_tax="", sell_tax="")))
    screen(h4, cand())
    assert rows(f"{d4}/screen.csv")[-1]["verdict"] == "PASS" and K in h4.pf.positions
    h5, _, d5 = make(table_evm(gp=gp_evm(buy_tax=""), hp={"honeypotResult": {"isHoneypot": False}}))
    screen(h5, cand())
    r = rows(f"{d5}/screen.csv")[-1]
    assert r["verdict"] == "REJECT" and "buy tax unknown" in r["reasons"] and not h5.pf.positions
    for x in (d, d2, d3, d4, d5):
        shutil.rmtree(x)
    print("  clean token passes -> tier A momentum entry, costs; deferred tax needs the 2nd source   ok")


def test_rejections():
    cases = [("honeypot (goplus)", table_evm(gp=gp_evm(is_honeypot="1")), "is_honeypot", "honeypot.is"),
             ("honeypot (honeypot.is)", table_evm(hp=HP_BAD), "honeypot (sell reverted)", None),
             ("high tax (goplus)", table_evm(gp=gp_evm(sell_tax="0.12")), "sell tax 12%", "honeypot.is"),
             ("high tax (honeypot.is)", table_evm(hp=dict(HP_OK, simulationResult={"buyTax": 0, "sellTax": 8})), "sell tax 8%", None),
             ("mintable", table_evm(gp=gp_evm(is_mintable="1")), "is_mintable", "honeypot.is"),
             ("pausable", table_evm(gp=gp_evm(transfer_pausable="1")), "transfer_pausable", "honeypot.is"),
             ("unlocked LP", table_evm(gp=gp_evm(lp_holders=[{"address": "0xdev", "percent": "1.0", "is_locked": 0}])), "lp locked 0%", None),
             ("whale concentration", table_evm(gp=gp_evm(holders=[{"address": f"0xw{i}", "percent": "0.06"} for i in range(10)])), "top-10 holders 60%", None),
             ("proxy", table_evm(gp=gp_evm(is_proxy="1")), "is_proxy", None)]
    for name, table, want, not_called in cases:
        h, fetch, d = make(table)
        screen(h, cand())
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and want in r["reasons"], (name, r)
        assert not h.pf.positions and "base:" + EVM in h.state["followup"], name
        if not_called:
            assert not any(not_called in u for u in fetch.calls), (name, fetch.calls)   # stops at first failure
        shutil.rmtree(d)
    sol = [("freeze authority", table_sol(gp=gp_sol(freezable={"status": "1", "authority": ["F"]})), "freeze authority"),
           ("mint authority (goplus)", table_sol(gp=gp_sol(mintable={"status": "1"})), "mint authority"),
           ("mint authority (rugcheck)", table_sol(rc=dict(RC_OK, risks=[{"name": "Mint Authority still enabled", "level": "warn"}])), "rugcheck: mintAuthority"),
           ("LP not burned (rugcheck)", table_sol(rc=dict(RC_OK, lpLockedPct=40)), "rugcheck lp locked 40%"),
           ("rugcheck danger", table_sol(rc=dict(RC_OK, risks=[{"name": "Large Amount of LP Unlocked", "level": "danger"}])), "rugcheck danger")]
    for name, table, want in sol:
        h, fetch, d = make(table)
        screen(h, cand("solana", SOL))
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and want in r["reasons"], (name, r)
        shutil.rmtree(d)
    # GoPlus has no holder / LP data on Solana: RugCheck settles it (pass if clean, reject if not)
    for rc, verdict, why in ((RC_OK, "PASS", ""), (dict(RC_OK, lpLockedPct=40), "REJECT", "rugcheck lp locked 40%"),
                             ({k: v for k, v in RC_OK.items() if k != "lpLockedPct"}, "REJECT", "rugcheck: lp lock unknown")):
        h, fetch, d = make(table_sol(gp=gp_sol(holders=[], lp_holders=[]), rc=rc))
        screen(h, cand("solana", SOL))
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == verdict and why in r["reasons"], (verdict, r)
        assert any("rugcheck" in u for u in fetch.calls)
        shutil.rmtree(d)
    # unlocked LP: rejected on a young pool, fine on a 30+ day, $1M+ pool (v3/CLMM positions can't be locked)
    unlocked = gp_evm(lp_holders=[{"address": "0xdev", "percent": "1.0", "is_locked": 0}])
    for age, liq, verdict in ((100, 1_500_000, "REJECT"), (800, 600_000, "REJECT"), (800, 1_500_000, "PASS")):
        h, fetch, d = make(table_evm(gp=unlocked, pair=ds_pair("base", EVM, liq=liq, age_h=age)))
        screen(h, cand(liq=liq, age_h=age))
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == verdict, (age, liq, r)
        shutil.rmtree(d)
    # no pool age from the source: fine on a $1M+ pool, rejected below
    S = dict(dex.DEX["screen"], min_liq=250_000)
    base = {"price": 1.0, "vol24": 500_000, "b24": 10, "s24": 10, "age_h": None}
    assert not dex.check_market(dict(base, liq=1_200_000), S)
    assert "pool age unknown" in dex.check_market(dict(base, liq=400_000), S)[0][0]
    print("  rejections: honeypot, tax, mintable, pausable, freeze, LP, whales, proxy; SOL unknowns -> RugCheck; mature LP; unknown age   ok")


def test_unreachable_fails_closed():
    for name, table in (("goplus 500", {"gopluslabs": (500, ""), **table_evm()}),      # failing entry first wins
                        ("goplus timeout", {"gopluslabs": (0, "timed out"), **table_evm()}),
                        ("honeypot.is 503", {"honeypot.is": (503, ""), **table_evm()}),
                        ("goplus bad json", {"gopluslabs": (200, "<html>"), **table_evm()}),
                        ("rugcheck down", {"rugcheck.xyz": (502, ""), **table_sol()})):
        h, fetch, d = make(table)
        c = cand("solana", SOL) if "rugcheck" in name else cand()
        screen(h, c)
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "UNREACHABLE", (name, r)
        assert not h.pf.positions and not h.state["followup"] and not h.state["passed"], name
        if "goplus" in name:
            assert not any("honeypot.is" in u for u in fetch.calls), name
        key = h.key(c)
        assert key in h.state["seen"] and not h._enqueue(c, T0 + 1000, fresh=False)      # not retried at once
        h.tick(T0 + 2 * HOUR)                                                            # 1h retry ttl passed
        assert key not in h.state["seen"]
        shutil.rmtree(d)
    print("  unreachable security API -> not tradable (fail closed)   ok")


def gp_partial(addr=EVM, code=3, **over):
    """GoPlus "partial data" answer, shaped like the real one for BASECAT (0xb2000..., 2026-09-27 probe):
    code 3, no honeypot / mint / owner / proxy fields, "" taxes, holders + LP present."""
    full = gp_evm(addr)["result"][addr]
    d = {k: full[k] for k in ("dex", "holders", "lp_holders", "is_open_source")}
    d.update(buy_tax="", sell_tax="", owner_address="", is_in_dex="1", holder_count="9092", token_name="Basecat",
             token_symbol="Basecat", total_supply="1000000000")
    d.update(over)
    return {"code": code, "message": "OK", "result": {addr.lower(): d}}


HP_STF = {"simulationSuccess": True, "honeypotResult": {"isHoneypot": True, "honeypotReason": "execution reverted: STF"},
          "simulationResult": {"buyTax": 0, "sellTax": 100, "transferTax": 0},
          "summary": {"risk": "honeypot", "riskLevel": 100}, "holderAnalysis": {"holders": "1334", "failed": "1287"}}


def test_goplus_partial_data():
    """GoPlus code 2/3 partial data (every 0xb2000... Base token) is a real verdict, never "unreachable",
    and never a pass on missing fields."""
    S = dex.DEX["screen"]
    d = gp_partial()["result"][EVM]
    rs = check_goplus_evm(d, S)
    assert ("goplus partial data: is_honeypot/cannot_sell_all/cannot_buy unknown", "defer") in rs, rs
    assert any(t.startswith("goplus partial data: is_mintable/") and s == "unknown" for t, s in rs), rs
    assert ("buy tax unknown", "defer") in rs and ("sell tax unknown", "defer") in rs
    assert check_goplus_evm(gp_evm()["result"][EVM], S) == []                        # full data: unchanged
    # BASECAT as it really answered: GoPlus partial + honeypot.is "STF" honeypot -> REJECT with both reasons
    for code in (3, 2, "3"):
        h, fetch, dd = make(table_evm(gp=gp_partial(code=code), hp=HP_STF))
        screen(h, cand())
        r = rows(f"{dd}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and r["sources"] == "ds+goplus+honeypot", (code, r)
        assert "goplus partial data: is_mintable" in r["reasons"] and "honeypot (execution reverted: STF)" in r["reasons"], r
        assert "unreachable" not in r["reasons"] and not h.pf.positions and "base:" + EVM in h.state["followup"]
        shutil.rmtree(dd)
    # honeypot.is clean is still not enough: nobody confirmed mint / owner / pause / proxy -> REJECT (fail closed)
    h, fetch, dd = make(table_evm(gp=gp_partial(), hp=HP_OK))
    screen(h, cand())
    r = rows(f"{dd}/screen.csv")[-1]
    assert r["verdict"] == "REJECT" and "is_mintable" in r["reasons"] and not h.pf.positions, r
    assert not h.state["passed"]
    shutil.rmtree(dd)
    # only the sell-simulation fields missing: honeypot.is settles them (pass if clean, reject if honeypot)
    powers = {k: "0" for k in dex.GP_POWERS}
    for hp, verdict in ((HP_OK, "PASS"), (HP_STF, "REJECT"), ({"summary": {}}, "REJECT")):   # no simulation
        h, fetch, dd = make(table_evm(gp=gp_partial(owner_address=DEAD, buy_tax="0", sell_tax="0", **powers), hp=hp))
        screen(h, cand())
        r = rows(f"{dd}/screen.csv")[-1]
        assert r["verdict"] == verdict, (verdict, r)
        shutil.rmtree(dd)
    # a partial-data token still gets a verdict when honeypot.is is down: UNREACHABLE (retried), never PASS
    h, fetch, dd = make({"honeypot.is": (503, ""), **table_evm(gp=gp_partial())})
    screen(h, cand())
    assert rows(f"{dd}/screen.csv")[-1]["verdict"] == "UNREACHABLE" and not h.pf.positions
    shutil.rmtree(dd)
    # other GoPlus error codes (rate limit etc.) stay "unreachable"
    for body in ({"code": 4029, "message": "too many requests", "result": {}},
                 {"code": 5000, "message": "error", "result": gp_partial()["result"]}):
        h, fetch, dd = make(table_evm(gp=body))
        screen(h, cand())
        r = rows(f"{dd}/screen.csv")[-1]
        assert r["verdict"] == "UNREACHABLE" and r["reasons"] == "goplus unreachable", r
        shutil.rmtree(dd)
    # held token whose GoPlus answer turns partial: contract powers no longer confirmed -> emergency exit
    h, fetch, dd, px = held()
    h.src["goplus"].fetch = fake_fetch({"token_security": (200, gp_partial())})
    run(h, T0 + 1801_000, 4)
    oc = rows(f"{dd}/outcomes.csv")[-1]
    assert K not in h.pf.positions and oc["outcome"] == "emergency_exit" and "goplus partial data" in oc["reason"], oc
    shutil.rmtree(dd)
    print("  goplus partial data (code 2/3): real verdict, missing fields unknown, honeypot.is must confirm   ok")


def test_market_sanity_and_prefilter():
    h, fetch, d = make({})
    assert not h._enqueue(cand(liq=20_000), T0, fresh=False) and h.state["prefiltered"] == 1   # tiny pool
    assert not h._enqueue(cand(age_h=3), T0, fresh=False)                                       # young pool
    assert not h.queue and not fetch.calls
    shutil.rmtree(d)
    for kw, want in ((dict(liq=20_000), "liquidity $20,000 < $100,000"), (dict(age_h=5), "pool age 5.0h < 6h"),
                     (dict(vol=50_000), "24h volume $50,000"), (dict(b24=0), "no buys or no sells"),
                     (dict(h6=45, h1=-20), "spike-and-fade")):
        h, fetch, d = make(table_evm(pair=ds_pair("base", EVM, **kw)))   # discovery data looked fine...
        screen(h, cand())                                                # ...DexScreener says otherwise
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and want in r["reasons"], (kw, r)
        assert not any("gopluslabs" in u for u in fetch.calls)          # no security call wasted
        shutil.rmtree(d)
    print("  market sanity: tiny / young pool, volume, one-sided, fade   ok")


def test_no_second_coin_with_same_name():
    h, _, d = make(table_evm())
    screen(h, cand())
    assert K in h.pf.positions
    other = "0x" + "9" * 40                                                  # different token, same symbol
    c2 = cand(addr=other)
    k2 = "base:" + other
    h.state["passed"][k2] = dict(c2, screen_t=T0)
    h._try_entry(k2, T0 + 5000)
    assert len(h.pf.positions) == 1, h.pf.positions.keys()
    shutil.rmtree(d)
    print("  same-name copycat not bought while we hold that name   ok")


def test_renounced_owner_powers_ignored():
    S = dex.DEX["screen"]
    pepe = gp_evm(transfer_pausable="1", is_blacklisted="1", owner_address="0x0000000000000000000000000000000000000000")["result"][EVM]
    rs = [t for t, _ in dex.check_goplus_evm(pepe, S)]
    assert "transfer_pausable" not in rs and "is_blacklisted" not in rs, rs          # PEPE: owner renounced
    live = gp_evm(transfer_pausable="1", is_blacklisted="1", owner_address="0xdev0000000000000000000000000000000000001")["result"][EVM]
    rs = [t for t, _ in dex.check_goplus_evm(live, S)]
    assert "transfer_pausable" in rs and "is_blacklisted" in rs                      # owner can still use them
    sneaky = dict(pepe, hidden_owner="1")
    assert "transfer_pausable" in [t for t, _ in dex.check_goplus_evm(sneaky, S)]    # hidden owner: no pass
    proxy = dict(pepe, is_proxy="1")
    assert "is_blacklisted" in [t for t, _ in dex.check_goplus_evm(proxy, S)]       # upgradeable: no pass
    print("  renounced owner: owner-only powers ignored; hidden owner / proxy still blocked   ok")


def test_snapshots_logged_hourly():
    h, _, d = make({})
    c = cand()
    h._enqueue(c, T0, fresh=False)
    h._enqueue(c, T0 + 60_000, fresh=False)                          # same hour: not logged again
    h._enqueue(c, T0 + HOUR + 1, fresh=False)
    r = rows(f"{d}/snapshots.csv")
    assert len(r) == 2 and r[0]["sym"] == "TOK" and r[0]["b1"] == "120", r
    shutil.rmtree(d)
    print("  live-feature snapshots: one row per coin per hour   ok")


def test_queue_screens_movers_first():
    h, _, d = make({})
    slow = cand(addr="0x" + "1" * 40, liq=5_000_000, h1=1)           # big, not moving
    mover = cand(addr="0x" + "2" * 40, liq=150_000, h1=15)           # small, +15% 1h, buyers > sellers
    fading = cand(addr="0x" + "3" * 40, liq=900_000, h1=4)
    for c in (slow, fading, mover):
        h._enqueue(c, T0, fresh=False)
    assert [j["c"]["addr"] for j in h.queue] == [mover["addr"], fading["addr"], slow["addr"]], h.queue
    shutil.rmtree(d)
    print("  screening queue: coins meeting the entry trigger first, then by 1h move   ok")


def test_liquidity_floor_scales_with_account():
    h, _, d = make({})
    assert h.S()["min_liq"] == 100_000                                    # $500: 3% = $15 -> floor binds
    h.pf.cash = 10_000
    assert h.S()["min_liq"] == 100_000                                    # $300 x 50 = $15k < floor
    h.pf.cash = 1_000_000
    assert h.S()["min_liq"] == 1_500_000                                  # $30k x 50
    assert not h._enqueue(cand(liq=600_000), T0, fresh=False)             # too shallow for this account now
    shutil.rmtree(d)
    print("  min liquidity = max($100k, 50 x planned position)   ok")


def test_sizing_caps_in_entries():
    h, _, d = make({})
    c = cand(liq=100_000)                                                  # entry re-checks the liquidity floor
    h.state["passed"][h.key(c)] = dict(c, screen_t=T0, liq=5_000)          # (INUINK: screened $103k, bought at ~$5k)
    h._try_entry(h.key(c), T0)
    assert not h.pf.positions
    h.state["passed"].clear()
    h.p = {**h.p, "screen": {**h.p["screen"], "min_liq": 0}}               # the size caps below use tiny pools
    c = cand(liq=2000)
    h.state["passed"][h.key(c)] = dict(c, screen_t=T0)
    h._try_entry(h.key(c), T0)
    pos = h.pf.positions[K]
    assert abs(pos["cost0"] - 10.0) < 1e-9 and abs(pos["impact"] - 10 / 2000) < 1e-12   # 0.5% of $2k = $10 < $15
    c2 = cand(addr="0xdef", sym="TINY", liq=1000)                          # $5 < MIN_ORDER_USD: skipped
    h.state["passed"][h.key(c2)] = dict(c2, screen_t=T0)
    h._try_entry(h.key(c2), T0)
    assert len(h.pf.positions) == 1
    # tier C at entry: 31-day-old $6M pool that trades on Crypto.com (scanner symbols) -> 20% = $100
    h.cex = {"BLUE"}
    c3 = cand(addr="0xb1ue", sym="BLUE", age_h=31 * 24, liq=6e6, vol=2e6)
    h.state["passed"][h.key(c3)] = dict(c3, screen_t=T0)
    h._try_entry(h.key(c3), T0)
    assert abs(h.pf.positions["BLUE@base:0xb1ue"]["cost0"] - 100) < 0.2 and h.pf.positions["BLUE@base:0xb1ue"]["tier"] == "C"
    c4 = cand(addr="0xb2", sym="BLUE2", age_h=31 * 24, liq=6e6, vol=2e6)   # same pool, not on a CEX: tier A
    h.state["passed"][h.key(c4)] = dict(c4, screen_t=T0)
    h._try_entry(h.key(c4), T0)
    assert h.pf.positions["BLUE2@base:0xb2"]["tier"] == "A" and abs(h.pf.positions["BLUE2@base:0xb2"]["cost0"] - 15) < 0.2
    # 60% exposure cap: $300 of $500 -> the 4th slot gets only what is left, then nothing
    h.cex |= {"BLUE3", "BLUE4"}
    c5 = cand(addr="0xb3", sym="BLUE3", age_h=31 * 24, liq=6e6, vol=2e6)
    h.state["passed"][h.key(c5)] = dict(c5, screen_t=T0)
    h._try_entry(h.key(c5), T0)
    assert len(h.pf.positions) == 4 and h.exposure() <= 300 * 1.0001 and h.pf.positions["BLUE3@base:0xb3"]["cost0"] < 100
    c6 = cand(addr="0xb4", sym="BLUE4", age_h=31 * 24, liq=6e6, vol=2e6)
    h.state["passed"][h.key(c6)] = dict(c6, screen_t=T0)
    h._try_entry(h.key(c6), T0)
    assert len(h.pf.positions) == 4                                        # max 4 open positions
    shutil.rmtree(d)
    print("  entries: 0.5% pool cap, tier C on CEX listing, 60% exposure cap, 4 slots   ok")


# ---- exits -----------------------------------------------------------------------------------
def held(table_extra=None, **pair_kw):
    """A hunter holding TOK bought at 0.01 with a mutable live pair (px['v'], px['liq'])."""
    px = {"v": 0.01, "liq": pair_kw.pop("liq", 600_000), "gone": False}
    table = {"tokens/v1/base/": lambda u: (200, [] if px["gone"] else [ds_pair("base", EVM, price=px["v"], liq=px["liq"], **pair_kw)])}
    table.update(table_extra or {})
    table.update({k: v for k, v in table_evm().items() if k not in table})
    h, fetch, d = make(table)
    screen(h, cand())
    assert K in h.pf.positions
    return h, fetch, d, px


def poll(h, t, px=None, v=None, liq=None, n=3):
    """Advance past the 60 s price interval, poll, run the exit check."""
    if v is not None:
        px["v"] = v
    if liq is not None:
        px["liq"] = liq
    return run(h, t + 61_000, n)


def test_crash_needs_a_second_reading():
    """A single bad tick (XPAD 2026-09-28: 7.1e-05, real price 5x higher 7 min later) must not sell."""
    h, fetch, d, px = held()
    h.p = {**h.p, "confirm_ms": 120_000}
    t = poll(h, T0 + 6000, px, v=0.015)
    t = poll(h, t, px, v=0.0104)                                            # below the stop once
    assert K in h.pf.positions and not h.pf.positions[K].get("exit") and h.pf.positions[K].get("stop_seen")
    t = poll(h, t, px, v=0.0140)                                            # bad tick gone: reset, still held
    assert K in h.pf.positions and "stop_seen" not in h.pf.positions[K]
    t = poll(h, t, px, v=0.0104)                                            # breach again...
    assert K in h.pf.positions
    t = poll(h, t + 60_000, px, v=0.0103)                                   # ...and still there 2+ min later: sold
    assert K not in h.pf.positions and "trailing stop" in rows(f"{d}/outcomes.csv")[-1]["reason"]
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # a rug also needs a second reading
    h.p = {**h.p, "confirm_ms": 120_000}
    t = poll(h, T0 + 6000, px, liq=100_000)
    assert K in h.pf.positions
    t = poll(h, t + 60_000, px, liq=90_000)
    assert K not in h.pf.positions and rows(f"{d}/outcomes.csv")[-1]["outcome"] == "scammed_rug"
    shutil.rmtree(d)
    print("  crash / rug sale needs a second reading >= 2 min later (single bad ticks ignored)   ok")


def test_far_off_tick_needs_15_minutes():
    """AIRPAD 2026-09-30: the feed gave 1/50th of the real price (and $5.7k liquidity) on and off; two such
    readings 2+ min apart sold it at 8e-06. A 20x+ drop now needs 15 min of readings before any sale."""
    h, fetch, d, px = held()
    h.p = {**h.p, "confirm_ms": 120_000}
    t = poll(h, T0 + 6000, px, v=0.0101)
    t = poll(h, t, px, v=0.0101 / 50, liq=5_000)
    t = poll(h, t + 120_000, px, v=0.0101 / 50, liq=5_000)                 # the old rule sold here
    assert K in h.pf.positions and not h.pf.positions[K].get("exit")
    t = poll(h, t, px, v=0.0101, liq=600_000)                              # real price back: reset
    assert K in h.pf.positions and h.pf.positions[K].get("suspect") is False
    t = poll(h, t, px, v=0.0101 / 50, liq=5_000)
    t = poll(h, t + 900_000, px, v=0.0101 / 50, liq=5_000)                 # still there 15+ min later: a real crash
    assert K not in h.pf.positions or h.pf.positions[K].get("exit")
    shutil.rmtree(d)
    print("  a 20x+ drop between readings needs 15 min before a sale (AIRPAD bad feed)   ok")


def test_new_season_restarts_account():
    """A new params['season'] archives the account + outcomes (never deletes) and starts fresh at season_cash."""
    h, fetch, d, px = held()
    h.save()
    with open(f"{d}/outcomes.csv", "w") as f:
        f.write("time,coin,outcome\n2026-09-27 10:35,GENO,scammed_rug\n")
    h.state["scams"] = [T0]
    h.save()
    h2 = DexHunter(params=dict(h.p, season="S2", season_cash=1000.0), fetch=fetch, now_ms=T0)
    h2._load()
    assert h2.pf.cash == 1000.0 and not h2.pf.positions and h2.state["season"] == "S2" and not h2.state["scams"]
    assert os.path.exists(f"{d}/archive/season1/portfolio.json") and os.path.exists(f"{d}/archive/season1/outcomes.csv")
    assert not os.path.exists(f"{d}/outcomes.csv")
    h2.save()
    h3 = DexHunter(params=dict(h.p, season="S2", season_cash=1000.0), fetch=fetch, now_ms=T0)
    h3._load()                                                               # same season: nothing happens again
    assert h3.state["season"] == "S2" and not os.path.exists(f"{d}/archive/S2")
    shutil.rmtree(d)
    print("  new season: account archived (not deleted), fresh $1,000, scam counter reset, once   ok")


def test_trailing_stop():
    h, fetch, d, px = held()
    t = poll(h, T0 + 6000, px, v=0.015)
    pos = h.pf.positions[K]
    assert pos["peak"] == 0.015 and abs(pos["stop"] - 0.015 * 0.7) < 1e-12
    t = poll(h, t, px, v=0.0106)                                            # above the stop: hold
    assert K in h.pf.positions and not h.pf.positions[K].get("exit")
    n_calls = len(fetch.calls)
    t = poll(h, t, px, v=0.0104)                                            # below 0.0105: exit
    assert K not in h.pf.positions
    assert any("IsHoneypot" in u for u in fetch.calls[n_calls:])            # sell simulation ran first
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "normal" and oc["tier"] == "A" and "trailing stop" in oc["reason"] and float(oc["exit"]) == 0.0104
    tr = rows(f"{d}/dex_hunter/trades.csv")[-1]
    usd = float(tr["qty"]) * 0.0104
    assert abs(float(tr["price"]) - round(0.0104 * (1 - 0.01 - usd / 600_000), 6)) < 1e-9   # slippage + impact on the way out
    assert h.pf.cooldown[K] > t
    shutil.rmtree(d)
    print("  trailing stop 30% below peak (after sell simulation)   ok")


def test_evm_address_case():
    # GeckoTerminal sends lowercase EVM addresses, DexScreener checksummed mixed case: must still match
    m = dex.best_pairs([{"chain": "base", "addr": "0xAbC0000000000000000000000000000000000Def", "liq": 5.0}], "base")
    assert m.get("0xabc0000000000000000000000000000000000def") and "0xABC0000000000000000000000000000000000DEF" in m
    s = dex.best_pairs([{"chain": "solana", "addr": "KMNoAbC", "liq": 5.0}], "solana")
    assert s.get("KMNoAbC") and s.get("kmnoabc") is None                # Solana stays case-sensitive
    print("  EVM address case-insensitive matching (Solana case-sensitive)   ok")


def test_take_profit_steps():
    h, fetch, d, px = held()
    q0, entry, cost0 = h.pf.positions[K]["qty"], h.pf.positions[K]["entry"], h.pf.positions[K]["cost0"]
    t = poll(h, T0 + 6000, px, v=0.021)                                     # +110%: sell half, cost recovered
    pos = h.pf.positions[K]
    assert pos["tp1"] and not pos["tp2"] and abs(pos["qty"] - q0 / 2) < 1e-12
    assert pos["stop"] >= entry and pos["realized"] > 0                    # remainder rides free
    assert pos["realized"] + cost0 / 2 >= cost0                            # proceeds (net of costs) >= full cost
    assert "take-profit +100%" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    t = poll(h, t, px, v=0.03)                                              # +200%: nothing new
    assert abs(h.pf.positions[K]["qty"] - q0 / 2) < 1e-12
    t = poll(h, t, px, v=0.051)                                             # 5.1x: sell a third of the rest
    pos = h.pf.positions[K]
    assert abs(pos["qty"] - q0 / 3) < 1e-12 and "+400%" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    assert abs(pos["stop"] - 0.051 * 0.6) < 1e-12                          # peak >= 3x: trail widens to 40%
    t = poll(h, t, px, v=0.12)                                              # 12x: half of what's left
    pos = h.pf.positions[K]
    assert abs(pos["qty"] - q0 / 6) < 1e-12 and abs(pos["stop"] - 0.12 * 0.5) < 1e-12   # moonbag, 50% trail
    t = poll(h, t, px, v=0.5)                                               # 50x: moonbag keeps riding
    assert abs(h.pf.positions[K]["qty"] - q0 / 6) < 1e-12
    t = poll(h, t, px, v=0.24)                                              # < 0.25: stopped out, big net winner
    assert K not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "normal" and float(oc["pnl"]) > cost0 * 1.5, oc
    shutil.rmtree(d)
    # break-even stop: after tp1 a fall back to the entry price closes the rest without a loss overall
    h, fetch, d, px = held()
    cost0 = h.pf.positions[K]["cost0"]
    t = poll(h, T0 + 6000, px, v=0.021)
    t = poll(h, t, px, v=0.0101)                                            # back near entry: stop >= break-even hit
    assert K not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "normal" and float(oc["pnl"]) > 0.4 * cost0, oc
    shutil.rmtree(d)
    print("  take-profit ladder (2x half, 5x third, 10x half) + moonbag with widening trail, break-even stop   ok")


def test_study_exit():
    """Live config (dex_exit_study + dex_legends_study): no stop for 14 days, time limit, a runner at the
    limit keeps riding on a 40% trail."""
    live = {"entry": dex.DEX["entry"], "exit": {**dex.DEX["exit"], "stake_back": 3.0, "pyramid": None}}
    def held(px_path, days_between=1, sb=True):
        h, fetch, d = make(table_evm(pair=ds_pair("base", EVM, h1=12, h6=60)), **live)
        screen(h, cand(h1=12, h6=60))
        pos = h.pf.positions[K]
        pos["sb"] = sb                                    # runner cases: the stake already came back
        out = []
        for i, m in enumerate(px_path):
            pos["px"] = 0.0101 * m
            h._manage(K, pos, T0 + (i + 1) * days_between * DAY)
            out.append(bool(pos.get("exit")))
            if pos.get("exit"):
                break
        shutil.rmtree(d)
        return out, pos
    ex, _ = held([0.6, 0.5, 0.7, 1.3])                   # -50% dip inside the hold: no stop
    assert not any(ex)
    N = dex.DEX["exit"]["max_hold_days"]
    ex, _ = held([1.2] * (N + 2))                         # +20% at the limit (bought seconds after T0): sold
    assert ex[-1] and len(ex) == N + 1
    ex, pos = held([1.5] * (N - 1) + [2.5] * 3)          # 2.5x at the limit: keeps riding (runner)
    assert not any(ex) and pos.get("runner")
    ex, _ = held([2.5] * (N - 1) + [2.6, 2.0, 1.2])       # runner then drops 50% from its high -> sold
    assert ex[-1]
    SB = 3.0                                              # EXPERIMENT 3: at SB x sell the stake (1/m), keep the rest
    m = SB * 1.1
    ex, pos = held([1.5, SB * 0.95, m], sb=False)
    assert ex == [False, False, True] and f"stake back at {m:.1f}x" in pos["exit"]["reason"]
    assert abs(pos["exit"]["frac"] - 1 / m) < 0.01 and pos["sb"]
    ex, _ = held([2.5] * (N - 1) + [2.6, 2.1, 1.6, 1.5])  # runner at the limit, then -42% from its high -> sold
    assert ex[-1] and len(ex) == N + 3
    print("  live exit: 14-day hold without stop, runner at the limit rides a 40% trail   ok")


def test_stake_back_executes():
    # executed end to end: a third is sold, the rest stays, and it never sells the stake twice
    h, fetch, d, px = held()
    h.p = {**h.p, "exit": {**dex.DEX["exit"], "stake_back": 3.0, "pyramid": None}}   # the mechanism when it is on
    q0 = h.pf.positions[K]["qty"]
    m = 3.0 * 1.1
    t = poll(h, T0 + 6000, px, v=0.0101 * m)
    assert K in h.pf.positions and abs(h.pf.positions[K]["qty"] - q0 * (1 - 1 / m)) < q0 * 0.02, h.pf.positions[K]["qty"] / q0
    assert "stake back" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    q1 = h.pf.positions[K]["qty"]
    poll(h, t, px, v=0.0101 * m * 1.3)
    assert h.pf.positions[K]["qty"] == q1
    shutil.rmtree(d)
    print("  stake back: sells the stake once, the rest keeps riding   ok")


def test_pyramid_adds_on_a_proven_runner():
    """EXPERIMENT 11: at 3x of the first buy price (two readings >= 2 min apart) add 10% of the account, once."""
    h, fetch, d, px = held()
    h.p = {**h.p, "confirm_ms": 120_000, "exit": {**dex.DEX["exit"], "pyramid": {"at": 3.0, "pct": 0.10}, "stake_back": None}}
    pos = h.pf.positions[K]
    q0, c0 = pos["qty"], pos["cost0"]
    t = poll(h, T0 + 6000, px, v=0.0101 * 3.2)                         # first reading at 3.2x: wait for a second
    assert h.pf.positions[K]["qty"] == q0
    t = poll(h, t + 120_000, px, v=0.0101 * 3.3)                       # confirmed: added
    pos = h.pf.positions[K]
    assert pos["qty"] > q0 and pos["cost0"] > c0 and pos["pyr"]
    assert "proven runner" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    q1 = pos["qty"]
    poll(h, t + 200_000, px, v=0.0101 * 5)                             # only once
    assert h.pf.positions[K]["qty"] == q1
    shutil.rmtree(d)
    print("  a coin at 3x of its first price gets one bigger add-on (confirmed by two readings)   ok")


def test_entry_needs_a_run():
    # 2026-10-01 (dex_live_replay_study): a +10% hour after a flat or falling 6h lost under every exit
    E = dex.DEX["entry"]
    base = {"h1": 0.12, "b1": 150, "s1": 100}
    assert not dex.entry_trigger({**base, "h6": -0.45}, E)              # SHARTCOIN-style bounce in a fall
    assert not dex.entry_trigger({**base, "h6": 0.15}, E)
    assert dex.entry_trigger({**base, "h6": 0.80}, E)
    assert not dex.entry_trigger({**base, "h1": 2.66, "h6": 4.05}, E)  # SACC 2026-10-02: +266% in one hour -> 0.09x
    print("  entry needs the coin already up >= +50% in 6h   ok")


def test_recycle_stale_for_stronger_coin():
    """EXPERIMENT 7: no cash for a coin that passed -> the weakest holding >= 24h old and below its buy price is sold."""
    h, fetch, d, px = held()
    h.p = {**h.p, "exit": {**h.p["exit"], "recycle": {"min_hold_h": 24, "max_x": 1.0}}, "entry": dex.DEX["entry"]}
    pos = h.pf.positions[K]
    h.pf.cash = 0.0
    new = dict(cand(chain="base", addr="0xabc0000000000000000000000000000000000002", sym="NEW", h1=30, h6=80,
                    pair="PAIR2"), price=0.5)
    h.state["passed"]["NEW"] = new
    pos["px"] = pos["entry"] * 0.8
    h._try_entry("NEW", pos["opened"] + 3_600_000)                    # 1h old: kept
    assert not pos.get("exit")
    h._try_entry("NEW", pos["opened"] + 25 * 3_600_000)               # 25h old, 0.8x: swapped out
    assert pos.get("exit") and "swapped for a stronger coin" in pos["exit"]["reason"]
    pos.pop("exit")
    pos["px"] = pos["entry"] * 1.2                                     # in profit: never swapped
    h._try_entry("NEW", pos["opened"] + 25 * 3_600_000)
    assert not pos.get("exit")
    pos["px"] = pos["entry"] * 0.8
    weak = dict(new, h6=0.1)                                           # the newcomer must meet the entry rule
    h.state["passed"]["NEW"] = weak
    h._try_entry("NEW", pos["opened"] + 25 * 3_600_000)
    assert not pos.get("exit")
    shutil.rmtree(d)
    print("  no cash for a strong coin: the weakest stale holding (24h+, below cost) is swapped out   ok")


def test_scam_coin_never_rebought():
    """CLAUS 2026-10-05: booked as a honeypot, re-bought 7h later in a fresh season when the screen read clean."""
    h, fetch, d, px = held()
    t = poll(h, T0 + 6000, px, v=0.004, liq=100_000)                     # rug -> scammed, sold
    assert K not in h.pf.positions and EVM.lower() in h.blocked
    px.update(v=0.01, liq=600_000)
    h.state["seen"].clear(); h.pf.cooldown.clear(); h.state["paused"] = None
    screen(h, cand(), t=t + 1000)
    assert K not in h.pf.positions                                        # passed again, never bought
    h2 = DexHunter(params=h.p, fetch=fetch, now_ms=t + 2000)              # a restart reads the scam book from disk
    h2._load()
    assert EVM.lower() in h2.blocked
    shutil.rmtree(d)
    print("  a coin booked as a scam is never bought again (survives restarts / new seasons)   ok")


def test_resize_old_small_position():
    h, _, d = make(table_evm())
    screen(h, cand())
    pos = h.pf.positions[K]
    assert abs(pos["cost0"] - 15) < 0.1                                  # bought under the old 3% sizing
    pos.pop("resized", None)                                             # as for a position bought before _resize existed
    h.p = dict(h.p, tiers=dex.DEX["tiers"], size=dex.DEX["size"])       # sizing raised later
    h._housekeep(T0 + 60_000)
    want = 500 * dex.DEX["tiers"]["A"]["pct"]                             # topped up once to the tier-A share of $500
    assert want - 1 < pos["cost0"] < want + 1 and pos["resized"], pos["cost0"]
    n = len(h.pf.trades)
    h._housekeep(T0 + 120_000)
    assert len(h.pf.trades) == n                                          # only once
    h2, _, d2 = make(table_evm())
    screen(h2, cand())
    h2.pf.positions[K]["px"] *= 1.5                                       # already ran +50%: don't chase
    h2.pf.positions[K].pop("resized", None)
    h2.p = dict(h2.p, tiers=dex.DEX["tiers"], size=dex.DEX["size"])
    h2._housekeep(T0 + 60_000)
    assert abs(h2.pf.positions[K]["cost0"] - 15) < 0.1
    shutil.rmtree(d); shutil.rmtree(d2)
    print("  old small position resized once to current sizing (not if it already ran)   ok")


def test_max_hold():
    h, fetch, d, px = held()
    poll(h, T0 + 14 * DAY, px, v=0.012)
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert K not in h.pf.positions and "time limit 14d" in oc["reason"]
    shutil.rmtree(d)
    print("  14-day max hold   ok")


def test_held_coin_follows_its_own_pool():
    """A junk pool for the same token (fake 'deeper' liquidity, ~0 price) must not price our position."""
    junk = {"v": False}

    def tokens(u):
        out = [ds_pair("base", EVM, price=0.0105, liq=600_000)]
        if junk["v"]:
            j = ds_pair("base", EVM, price=0.0000001, liq=50_000_000)
            j["pairAddress"] = "0xjunkpool"
            out.append(j)
        return 200, out
    table = {"tokens/v1/base/": tokens}
    table.update({k: v for k, v in table_evm().items() if k not in table})
    h, fetch, d = make(table)
    screen(h, cand())
    assert K in h.pf.positions
    h.p = {**h.p, "exit": {**h.p["exit"], "trail": 0.95}}
    h.pf.positions[K]["stop"] = 0.0
    junk["v"] = True
    run(h, T0 + 6000, 4)
    assert K in h.pf.positions and abs(h.pf.positions[K]["px"] - 0.0105) < 1e-9, h.pf.positions.get(K)
    shutil.rmtree(d)
    assert dex._same_pool({"pair": "A"}, {"pair": "A"}) and not dex._same_pool({"pair": "A"}, {"pair": "B"})
    assert dex._same_pool({"pair": None}, {"pair": "B"}) and dex._same_pool({}, {})
    print("  held coin priced from the pool we bought in, not a junk 'deeper' pool   ok")


def test_absurd_momentum_is_not_a_buy():
    h, fetch, d = make(table_evm(pair=ds_pair("base", EVM, h1=15101012)))
    screen(h, cand(h1=15101012))
    assert K not in h.pf.positions
    shutil.rmtree(d)
    print("  1h change > +5,000% treated as bad data, no buy   ok")


def test_liquidity_pull_emergency_exit():
    h, fetch, d, px = held()
    t = poll(h, T0 + 6000, px, v=0.009, liq=320_000)                        # -47%: still holding
    assert K in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=120_000)                                # -80% liquidity: rug
    assert K not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "scammed_rug" and "liquidity pulled 68%" in oc["reason"] and float(oc["pnl"]) < 0
    tr = rows(f"{d}/dex_hunter/trades.csv")[-1]
    usd = float(tr["qty"]) * 0.004
    assert abs(float(tr["price"]) - round(0.004 * (1 - 0.01 - usd / 120_000), 6)) < 1e-9   # impact on the thinned pool
    assert h.state["scams"] and not h.paused()
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # pool gone entirely: -100%
    px["gone"] = True
    poll(h, T0 + 6000, px)
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert K not in h.pf.positions and oc["outcome"] == "scammed_rug" and abs(float(oc["ret"]) + 1) < 1e-9, oc
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # GENO: -78% dump, no LP pulled
    h.p = {**h.p, "exit": {**h.p["exit"], "trail": 0.95}}                    # live rule: no price stop
    h.pf.positions[K]["stop"] = 0.0
    t = poll(h, T0 + 6000, px, v=0.00225, liq=600_000 * 0.225 ** 0.5 * 0.99)  # $ liquidity -53% from price alone
    assert K in h.pf.positions, "a price dump alone is not a rug"
    poll(h, t, px, v=0.00225, liq=600_000 * 0.225 ** 0.5 * 0.4)            # then 60% of the pool pulled: rug
    assert K not in h.pf.positions and rows(f"{d}/outcomes.csv")[-1]["outcome"] == "scammed_rug"
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # pumping 5x, pool pulled 60%: rug
    poll(h, T0 + 6000, px, v=0.05, liq=240_000)
    assert K not in h.pf.positions and rows(f"{d}/outcomes.csv")[-1]["outcome"] == "scammed_rug"
    shutil.rmtree(d)
    print("  liquidity pull > 50% -> emergency exit at post-rug price / -100%   ok")
    print("  price dump alone (liquidity falls with sqrt(price)) is not a rug   ok")


def test_sell_simulation_fails_at_exit():
    h, fetch, d, px = held()
    h.src["honeypot"].fetch = fake_fetch({"IsHoneypot": (200, HP_BAD)})     # honeypot.is now says honeypot
    poll(h, T0 + 6000, px, v=0.006)                                         # stop hit; sell sim fails
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert K not in h.pf.positions and oc["outcome"] == "scammed_honeypot" and abs(float(oc["ret"]) + 1) < 1e-9
    assert "SELL SIMULATION FAILED" in oc["reason"] and "trailing stop" in oc["reason"]
    shutil.rmtree(d)
    # Solana: GoPlus freeze authority at exit time
    table, px2 = table_sol(), {"v": 0.01}
    table["tokens/v1/solana/"] = lambda u: (200, [ds_pair("solana", SOL, sym="SOLT", price=px2["v"])])
    h2, f2, d2 = make(table)
    screen(h2, cand("solana", SOL, sym="SOLT"))
    h2.src["goplus"].fetch = fake_fetch({"solana/token_security": (200, gp_sol(freezable={"status": "1"}))})
    px2["v"] = 0.005
    run(h2, T0 + 70_000, 3)
    oc = rows(f"{d2}/outcomes.csv")[-1]
    assert oc["outcome"] == "scammed_honeypot" and "freeze authority" in oc["reason"], oc
    shutil.rmtree(d2)
    print("  exit re-runs the sell simulation; failure books -100% SCAMMED   ok")


def test_exit_check_unreachable_then_market():
    h, fetch, d, px = held()
    h.src["honeypot"].fetch = fake_fetch({"IsHoneypot": (503, "")})
    t = poll(h, T0 + 6000, px, v=0.006, n=5)
    assert K in h.pf.positions and h.pf.positions[K]["exit"]               # waiting for the sell check
    h.tick(t + 700_000)                                                     # 10 min later: booked at market
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert K not in h.pf.positions and oc["outcome"] == "normal" and "sell check unreachable" in oc["reason"]
    shutil.rmtree(d)
    print("  sell check unreachable -> retried, then booked at market   ok")


def test_rescreen_flags_held_token():
    for name, gp, outcome, want in (("sell tax 60%", gp_evm(sell_tax="0.6"), "scammed_honeypot", "sell tax 60%"),
                                    ("trading paused", gp_evm(transfer_pausable="1"), "scammed_honeypot", "transfer_pausable"),
                                    ("newly mintable", gp_evm(is_mintable="1"), "emergency_exit", "is_mintable")):
        h, fetch, d, px = held()
        h.src["goplus"].fetch = fake_fetch({"token_security": (200, gp)})
        run(h, T0 + 10_000, 3)
        assert K in h.pf.positions and not h.pf.positions[K].get("exit")   # < 30 min: no re-screen yet
        run(h, T0 + 1801_000, 4)                                            # re-screen -> flagged -> exit check -> sold
        oc = rows(f"{d}/outcomes.csv")[-1]
        assert K not in h.pf.positions and oc["outcome"] == outcome and want in oc["reason"], (name, oc)
        shutil.rmtree(d)
    # flaky data flag (LP / holders): sold only if the next re-screen flags it again
    unlocked = gp_evm(lp_holders=[{"address": "0xdev", "percent": "1.0", "is_locked": 0}])
    h, fetch, d, px = held()
    h.src["goplus"].fetch = fake_fetch({"token_security": (200, unlocked)})
    run(h, T0 + 1801_000, 4)
    assert K in h.pf.positions and h.pf.positions[K]["flagged"] == 1          # first strike: still held
    h.p = {**h.p, "data_flag_exit": True}                                    # the two-strike rule, when it is on
    run(h, T0 + 3602_000, 4)
    run(h, T0 + 3700_000, 4)
    assert K not in h.pf.positions, "second strike should sell"
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # EXPERIMENT 10: data flags never sell
    h.p = {**h.p, "data_flag_exit": False}
    h.src["goplus"].fetch = fake_fetch({"token_security": (200, unlocked)})
    for t in (T0 + 1801_000, T0 + 3602_000, T0 + 5403_000):
        run(h, t, 4)
    assert K in h.pf.positions and h.pf.positions[K]["flagged"] >= 2 and not h.pf.positions[K].get("exit")
    shutil.rmtree(d)
    h, fetch, d, px = held()                                                # clean re-screen: keep holding, count it
    run(h, T0 + 1801_000, 4)
    assert K in h.pf.positions and h.pf.positions[K]["rescreened"] >= T0 + 1801_000 and h.pf.positions[K]["clean"] == 1
    shutil.rmtree(d)
    print("  periodic re-screen: honeypot/tax/pause -> SCAMMED, other flags -> emergency exit   ok")


def test_tier_upgrade_after_clean_rescreens():
    h, fetch, d, px = held(age_h=10 * 24, liq=2_000_000, vol=2_000_000)    # proven-looking pool, but new to us
    pos = h.pf.positions[K]
    assert pos["tier"] == "A" and abs(pos["cost0"] - 15) < 1e-9
    t = poll(h, T0 + 6000, px, v=0.012)                                     # in profit
    run(h, T0 + 1801_000, 4)                                                # clean re-screen #1
    assert h.pf.positions[K]["clean"] == 1 and h.pf.positions[K]["tier"] == "A"
    run(h, T0 + 3602_000, 4)                                                # clean re-screen #2 -> tier B top-up
    pos = h.pf.positions[K]
    assert pos["clean"] == 2 and pos["tier"] == "B", pos
    assert abs(pos["qty"] * 0.012 - 50) < 1.0 and 45 < pos["cost0"] < 50          # ~10% of equity held now
    tr = rows(f"{d}/dex_hunter/trades.csv")[-1]
    assert tr["side"] == "BUY" and "top-up" in tr["reason"] and abs(float(tr["price"]) - 0.012 * 1.01) < 1e-5   # slip + tiny impact
    assert abs(h.pf.cash - (500 - pos["cost0"])) < 0.5 and pos["entry"] > 0.01   # blended entry: +100% = cost back
    shutil.rmtree(d)
    h, fetch, d, px = held(age_h=10 * 24, liq=2_000_000, vol=2_000_000)    # under water: never averaged down
    poll(h, T0 + 6000, px, v=0.009)
    run(h, T0 + 1801_000, 4)
    run(h, T0 + 3602_000, 4)
    assert h.pf.positions[K]["clean"] == 2 and h.pf.positions[K]["tier"] == "A"
    shutil.rmtree(d)
    print("  tier A -> B top-up after 2 clean re-screens (only in profit)   ok")


# ---- follow-up of rejected tokens, auto-pause, reports ------------------------------------------
def test_rejected_followup():
    live = {EVM: (0.01, 600_000), "0xdef": (0.02, 500_000), "0x999": (0.03, 400_000)}

    def tokens(u):
        addrs = u.split("tokens/v1/base/")[1].split(",")
        return 200, [ds_pair("base", a, sym=a[-3:].upper(), price=live[a][0], liq=live[a][1]) for a in addrs if a in live]
    table = {"tokens/v1/base/": tokens, "token_security/8453": (200, gp_evm(is_honeypot="1"))}
    h, fetch, d = make(table, followup={"per_day": 2})
    for a in (EVM, "0xdef", "0x999"):
        table["token_security/8453"] = (200, gp_evm(a, is_honeypot="1"))
        screen(h, cand(addr=a, sym=a[-3:].upper()), n=3)
    fu = h.state["followup"]
    assert set(fu) == {"base:" + EVM, "base:0xdef"} and h.state["fu_n"] == 2          # sampled: 2 per day
    assert fu["base:" + EVM]["px0"] == 0.01 and fu["base:" + EVM]["liq0"] == 600_000
    live[EVM], live["0xdef"] = (0.0005, 20_000), (0.07, 700_000)                        # one rugs, one runs 3.5x
    run(h, T0 + HOUR + 1000, 8)                                                        # (discovery jobs go first)
    assert fu["base:" + EVM]["liq_min"] == 20_000 and fu["base:0xdef"]["px_max"] == 0.07 and fu["base:0xdef"]["n"] == 1
    live[EVM] = (0.0004, 15_000)
    del live["0xdef"]                                                                   # pair missing: a miss, not $0
    run(h, T0 + 2 * HOUR + 2000, 8)
    assert fu["base:0xdef"]["miss"] == 1 and fu["base:0xdef"]["px"] == 0.07
    run(h, T0 + 3 * HOUR + 3000, 8)
    run(h, T0 + 4 * HOUR + 4000, 8)
    assert fu["base:0xdef"]["miss"] == 3                                                # gone for good -> counted a rug
    run(h, T0 + 7 * DAY + 3000, 8)                                                      # 7 days: finalized
    assert not h.state["followup"]
    r = {x["address"]: x for x in rows(f"{d}/rejected_followup.csv")}
    assert r[EVM]["rugged"] == "1" and r[EVM]["ran_up"] == "0"
    assert r["0xdef"]["rugged"] == "1" and r["0xdef"]["ran_up"] == "1" and float(r["0xdef"]["max_gain"]) == 2.5
    line = h.weekly_line(T0 + 7 * DAY - HOUR)                                          # window covers the screens too
    assert "rejected-that-rugged 2/2" in line and "rejected-that-ran-up 1/2" in line and "screened 3, passed 0" in line
    shutil.rmtree(d)
    # a -80% dump with the pool intact (liquidity ~ sqrt(price)) and a brief API miss is NOT a rug
    live2 = {EVM: (0.01, 600_000)}
    table2 = {"tokens/v1/base/": lambda u: (200, [ds_pair("base", EVM, price=live2[EVM][0], liq=live2[EVM][1])] if live2 else []),
              "token_security/8453": (200, gp_evm(is_honeypot="1"))}
    h, fetch, d2 = make(table2)
    screen(h, cand(), n=3)
    live2[EVM] = (0.002, 600_000 * 0.2 ** 0.5)
    run(h, T0 + HOUR + 1000, 8)
    live2.clear()
    run(h, T0 + 2 * HOUR + 2000, 8)
    live2[EVM] = (0.004, 600_000 * 0.4 ** 0.5)
    run(h, T0 + 3 * HOUR + 3000, 8)
    run(h, T0 + 7 * DAY + 3000, 8)
    r = rows(f"{d2}/rejected_followup.csv")[-1]
    assert r["rugged"] == "0", r
    shutil.rmtree(d2)
    print("  rejected tokens followed 7 days (rug / run-up), sampled per day   ok")
    print("  follow-up rug = pool pulled / price ended collapsed / pair gone for good (not a dump or one API miss)   ok")


def test_auto_pause_after_scams():
    h, fetch, d, px = held()
    h.p = {**h.p, "scam_pause": {"max": None, "days": 30, "reset_after": ""}}   # owner 10-05: breaker off
    h._count_scam(T0)
    h._count_scam(T0 + 1000)
    assert not h.paused() and len(h.state["scams"]) == 2                    # counted, never pauses
    h.state["scams"] = []
    h.p = {**h.p, "scam_pause": {"max": 2, "days": 30, "reset_after": ""}}  # the mechanism, when it is on
    t = poll(h, T0 + 6000, px, v=0.004, liq=100_000)                        # scam #1
    assert K not in h.pf.positions and not h.paused()
    px.update(v=0.01, liq=600_000)
    h.state["seen"].clear()
    h.pf.cooldown.clear()
    h.blocked = set()                                                    # this test re-buys the same token
    t = screen(h, cand(), t=t + 1000)                                       # buys again...
    assert K in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=100_000)                                # scam #2 -> paused
    assert h.paused() == "scam limit" and len(h.state["scams"]) == 2
    px.update(v=0.01, liq=600_000)
    h.state["seen"].clear()
    h.pf.cooldown.clear()
    h.blocked = set()                                                    # this test re-buys the same token
    t = screen(h, cand(), t=t + 1000)
    assert rows(f"{d}/screen.csv")[-1]["verdict"] == "PASS" and K not in h.pf.positions   # screened, not bought
    assert "PAUSED" in h.status_line()
    s = dex.scoreboard_stats(d)
    assert s["scammed"] == 2 and s["lost"] < 0 and s["paused"] == "scam limit" and s["trades"] == 4
    line = dex.scoreboard_line(d=d)
    assert line.startswith("**DEX paused: scam limit** · $") and "Scammed: 2 (-$" in line, line
    assert dex.scoreboard_line(d=d, md=False).startswith("DEX paused: scam limit · $")
    h.p["scam_pause"]["reset_after"] = "2030-01-01 00:00"                   # manual re-enable in config
    h.tick(t + 1000)
    assert not h.paused() and not h.state["scams"]
    h._try_entry("base:" + EVM, t + 2000)
    assert K in h.pf.positions
    # a scam outside the 30-day window does not count
    h2, _, d2 = make({})
    h2.state["scams"] = [T0 - 31 * DAY]
    h2._count_scam(T0)
    assert not h2.paused() and h2.state["scams"] == [T0]
    shutil.rmtree(d)
    shutil.rmtree(d2)
    print("  2 scams in 30 days -> new entries paused until reset_after   ok")


def test_reports_and_scoreboard_line():
    h, fetch, d = make({"gopluslabs": (200, gp_evm()), "honeypot.is": (200, HP_OK), "rugcheck": (500, ""),
                        "dexscreener": (200, []), "geckoterminal": (429, "")})
    line = h.self_check(T0)
    assert line == "dex self-check: goplus 200 | honeypot.is 200 | rugcheck 500 | dexscreener 200 | geckoterminal 429", line
    assert h.state["status"]["rugcheck"]["code"] == 500 and not h.src["geckoterminal"].ready(T0 + 10 * 60_000)
    assert h.weekly_line(T0) == ("dex weekly: screened 0, passed 0, trades 0, closed 0 (P/L $+0.00; by tier A $+0.00/0 "
                                 "B $+0.00/0 C $+0.00/0), scammed 0 (cost $+0.00), rejected-that-rugged 0/0, "
                                 "rejected-that-ran-up 0/0"), h.weekly_line(T0)
    assert dex.scoreboard_stats(d) == {"equity": 500.0, "trades": 0, "scammed": 0, "lost": 0.0, "paused": ""}
    assert dex.scoreboard_line(d=d) == "**DEX: $500.00 (+0.00)** · Scammed: 0"
    # the owner's example line, from files alone
    os.makedirs(f"{d}/dex_hunter", exist_ok=True)
    with open(f"{d}/dex_hunter/equity.csv", "w") as f:
        f.write("time,equity,cash,positions\n2025-10-09 00:00,512.40,400,1\n")
    with open(f"{d}/outcomes.csv", "w") as f:
        f.write("time,coin,tier,pnl,outcome\n2025-10-09 00:00,X,A,-38.00,scammed_rug\n2025-10-09 01:00,Y,B,50.40,normal\n")
    assert dex.scoreboard_line(d=d, md=False) == "DEX: $512.40 (+12.40) · Scammed: 1 (-$38.00)"
    assert dex.scoreboard_line(d=d) == "**DEX: $512.40 (+12.40)** · Scammed: 1 (-$38.00)"
    assert "by tier A $-38.00/1 B $+50.40/1 C $+0.00/0" in h.weekly_line(T0 + DAY)
    shutil.rmtree(d)
    print("  self-check line, weekly line (P/L by tier), scoreboard line   ok")


def test_discovery_sources():
    boosts = [{"chainId": "base", "tokenAddress": "0xboost"}, {"chainId": "bsc", "tokenAddress": "0xno"}]
    table = {"networks/solana/trending_pools": (200, {"data": [gt_pool("solana", SOL), gt_pool("solana", "Thin", liq=1000)]}),
             "token-boosts/top": (200, boosts),
             "tokens/v1/solana/": (200, [ds_pair("solana", SOL, sym="GTK")]),
             "tokens/v1/base/0xboost": (200, [ds_pair("base", "0xboost", sym="BST")]),
             "search?q=WATCHY": (200, {"pairs": [ds_pair("base", "0xwatch", sym="WATCHY"), ds_pair("bsc", "0xw2", sym="WATCHY")]}),
             "gopluslabs": (200, {"code": 1, "result": {}})}                 # no security data: everything is REJECTED
    h, fetch, d = make(table, chains=["solana", "base"])
    sd = tempfile.mkdtemp()
    with open(f"{sd}/dex_watch.json", "w") as f:
        json.dump({"WATCHY": {"chain": "base", "n": 3, "last": "x"}, "ONCE": {"chain": "base", "n": 1}}, f)
    old, dex.SOCIAL = dex.SOCIAL, {"dir": sd}
    try:
        run(h, T0, 14)
    finally:
        dex.SOCIAL = old
    sc = {r["address"]: r for r in rows(f"{d}/screen.csv")}
    assert set(sc) == {SOL, "0xboost", "0xwatch"}, sc                        # bsc tokens ignored; every source fed in
    assert all(r["verdict"] == "REJECT" and "goplus: no data" in r["reasons"] for r in sc.values()) and not h.pf.positions
    assert sc[SOL]["sources"] == "ds+goplus" and sc["0xboost"]["sources"] == "goplus"   # GT data gets a DexScreener refresh
    assert h.state["prefiltered"] == 1                                       # the thin GT pool, silently
    assert sum("trending_pools" in u for u in fetch.calls) == 2              # solana + base (eth not configured)
    assert any("search?q=WATCHY" in u for u in fetch.calls) and "WATCHY" in h.state["watch_done"]
    shutil.rmtree(d)
    shutil.rmtree(sd)
    print("  discovery: geckoterminal trending, dexscreener boosts, social dex_watch   ok")


def test_source_backoff():
    src = dex.Source("x", fake_fetch({"a": (429, "")}), timeout=20, gap_s=2)
    assert src.timeout == 8                                                  # hard cap
    assert src.get("http://a", T0)[0] == 429 and not src.ready(T0 + 14 * 60_000) and src.ready(T0 + 16 * 60_000)
    src.get("http://a", T0 + 16 * 60_000)
    assert not src.ready(T0 + 16 * 60_000 + 29 * 60_000)                     # doubled: 30 min
    src2 = dex.Source("y", fake_fetch({"b": (200, "{}")}), gap_s=2)
    src2.get("http://b", T0)
    assert not src2.ready(T0 + 1000) and src2.ready(T0 + 2000)                # min gap between calls
    print("  per-source min gap + backoff (429 -> 15 min doubling)   ok")


def test_state_persists():
    h, fetch, d = make(table_evm())
    screen(h, cand())
    h2 = DexHunter(params={"dir": d, "gap_s": GAP0, "season": None}, fetch=fetch, now_ms=T0 + 5000)
    h2._load()
    assert K in h2.pf.positions and h2.pf.positions[K]["liq0"] == 600_000 and h2.pf.positions[K]["tier"] == "A"
    assert h2.state["seen"]["base:" + EVM]["v"] == "PASS" and h2.equity() == h.equity()
    shutil.rmtree(d)
    print("  state + portfolio survive a restart   ok")


# ---- wide scanner -------------------------------------------------------------------------------
SCAN = {"enabled": True, "gt_new_pages": 0, "gt_trend_pages": 1, "gt_feed_gap_s": 0, "threaded": False}      # no GeckoTerminal pages unless a test asks


def scan_make(table, scan=None, feeds=False, **params):
    """Hunter with the scanner on; its feed pages stay quiet unless feeds=True."""
    table = dict(table)
    table.setdefault("token-profiles/latest", (200, []))
    table.setdefault("token-boosts/latest", (200, []))
    h, fetch, d = make(table, scan=dict(SCAN, **(scan or {})), **params)
    if not feeds:
        h._feed_t = {f[3]: 10 ** 15 for f in h._feeds}
    return h, fetch, d


def scan_run(h, t, n, step=1000):
    """n ticks; at most one main-job request AND at most one scanner request per tick."""
    for i in range(n):
        before, sb = len(h.fetch.calls), h.scan_calls
        h.tick(t + i * step)
        scan = h.scan_calls - sb
        assert scan <= 1, "scanner made more than one request in a tick"
        assert len(h.fetch.calls) - before - scan <= 1, "more than one main request in a tick"
    return t + n * step


def addr_n(i):
    return "0x" + f"{i:040x}"


def tokens_fn(pairs_for, calls=None):
    """tokens/v1/{chain}/a,b,c -> pairs from pairs_for(addr) (None = no pair returned)."""
    def fn(u):
        addrs = u.split("tokens/v1/")[1].split("/", 1)[1].split(",")
        if calls is not None:
            calls.append(addrs)
        out = []
        for a in addrs:
            p = pairs_for(a)
            out += p if isinstance(p, list) else ([p] if p else [])
        return 200, out
    return fn


def test_scan_bulk_refresh():
    batches = []
    quiet = lambda a: None if a == addr_n(7) else ds_pair("base", a, sym=f"T{int(a, 16)}", h1=1, h6=2, liq=400_000)
    h, fetch, d = scan_make({"tokens/v1/base/": tokens_fn(quiet, batches)}, chains=["base"])
    for i in range(45):
        h._uni_add("base", addr_n(i), T0, "test")
    scan_run(h, T0, 6)
    assert [len(b) for b in batches] == [30, 15], batches                  # <= 30 tokens per call, all covered
    assert sorted(a for b in batches for a in b) == sorted(addr_n(i) for i in range(45))
    e = h.uni[f"base:{addr_n(3)}"]
    assert e["liq"] == 400_000 and e["h1"] == 0.01 and e["sym"] == "T3" and e["seen"] >= T0 and not e["low"]
    assert abs(e["created"] - (T0 - 48 * HOUR)) < 1000
    assert h.uni[f"base:{addr_n(7)}"]["low"] >= T0                         # no pair: counts as no liquidity
    assert h.scan_n["refreshed"] == 45 and h.scan_n["missing"] == 1 and not h.queue   # quiet pools: nothing queued
    n = len(batches)
    scan_run(h, T0 + 6000, 10)                                              # not due again before hot_s (30 s)
    assert len(batches) == n
    scan_run(h, T0 + 40_000, 4)                                             # due again: refreshed
    assert len(batches) > n
    assert "45 pools" in h.scan_line(T0) and "refresh cycle" in h.scan_line(T0)
    shutil.rmtree(d)
    print("  scanner: bulk tokens/v1 refresh (30 per call), missing pair = no liquidity, hot/cold due times   ok")


def test_scan_universe_cap_and_eviction():
    h, fetch, d = scan_make({}, scan={"max_pools": 5}, chains=["base"])
    for i in range(8):                                                     # sightings 1 min apart
        h._uni_add("base", addr_n(i), T0 + i * 60_000, "test")
    h._uni_add("base", addr_n(1), T0 + 20 * 60_000, "test")                  # re-sighted: interesting again
    h._scan_maint(T0 + 30 * 60_000)
    assert sorted(h.uni) == sorted(f"base:{addr_n(i)}" for i in (1, 4, 5, 6, 7)), sorted(h.uni)
    assert h.scan_n["cap"] == 3
    now = T0 + 30 * HOUR
    for i in (4, 5):
        h.uni[f"base:{addr_n(i)}"]["low"] = now - 25 * HOUR                  # below the floor for 25h: dead
    h.uni[f"base:{addr_n(6)}"].update(created=now - 40 * DAY, hit=now - 2 * DAY)   # 40 days old, quiet: stale
    h.uni[f"base:{addr_n(7)}"].update(created=now - 40 * DAY, hit=now - 2 * DAY, move=now - HOUR)   # old but moving
    c = cand(addr=addr_n(5))                                                 # dead-looking but screened & waiting
    h.state["passed"][h.key(c)] = dict(c, screen_t=now)
    h._scan_maint(now)
    assert sorted(h.uni) == sorted(f"base:{addr_n(i)}" for i in (1, 5, 7)), sorted(h.uni)
    assert h.scan_n["dead"] == 1 and h.scan_n["stale"] == 1
    assert not h._uni_add("ethereum", addr_n(99), now, "x")                  # chain not configured
    h._uni_add("base", "0xABCdef0000000000000000000000000000000001", now, "x")
    assert not h._uni_add("base", "0xabcdef0000000000000000000000000000000001", now, "x")   # EVM case ignored
    h._uni_save(now)
    h2 = DexHunter(params={"dir": d, "gap_s": GAP0, "chains": ["base"], "scan": SCAN, "season": None}, fetch=fetch, now_ms=now)
    h2._load()
    assert sorted(h2.uni) == sorted(h.uni) and h2.uni[f"base:{addr_n(7)}"]["move"] == (now - HOUR) // 1000 * 1000
    shutil.rmtree(d)
    print("  scanner universe: cap keeps the most recent sightings, dead / stale pools dropped, saved + reloaded   ok")


def test_scan_mover_front_of_queue_and_buys():
    MOV = addr_n(0xAA)
    live = {"h1": 1}
    def pairs(a):
        if a.lower() == MOV:
            return ds_pair("base", a, sym="MOON", h1=live["h1"], h6=30, b1=400, s1=100)
        return ds_pair("base", a, sym="Q", h1=1, h6=1)
    table = {"tokens/v1/base/": tokens_fn(pairs)}
    table.update({k: v for k, v in table_evm(addr=MOV).items() if "tokens/v1" not in k})
    h, fetch, d = scan_make(table, chains=["base"], gap_s=dict(GAP0, goplus=3600, honeypot=3600, ds_scan=0))
    for i, h1 in ((1, 1), (2, 3), (3, 4)):                                  # discovery already queued three slow coins
        assert h._enqueue(cand(addr=addr_n(i), h1=h1, b1=10, s1=50), T0, fresh=False)
    h._uni_add("base", MOV, T0, "gt_new")
    h.src["dexscreener"].next_at = T0 + HOUR                                 # main jobs idle: only the scanner runs
    t = scan_run(h, T0, 1)
    assert h.queue[0]["key"] != "base:" + MOV and h.uni["base:" + MOV]["seen"] == T0   # quiet: not queued
    live["h1"] = 25                                                          # it starts running
    t = scan_run(h, T0 + 31_000, 1)
    j = h.queue[0]
    assert j["key"] == "base:" + MOV and j["steps"] == ["goplus", "honeypot"], h.queue   # front, no ds step
    assert h.scan_n["movers"] == 1 and h.scan_n["queued"] == 1 and h._nk("base:" + MOV) in h._scan_origin
    h.src["goplus"].next_at = h.src["honeypot"].next_at = 0
    scan_run(h, t, 3)
    assert f"MOON@base:{MOV[:8]}" in h.pf.positions, h.pf.positions         # screened first, then bought
    assert h.scan_n["screened"] == 1 and h.scan_n["passed"] == 1 and h.scan_n["bought"] == 1
    shutil.rmtree(d)
    # already screened & waiting: the refresh that shows the trigger buys at once (no screening calls)
    h, fetch, d = scan_make({"tokens/v1/base/": tokens_fn(pairs)}, chains=["base"])
    c = cand(addr=MOV, sym="MOON", h1=1)
    h.state["passed"][h.key(c)] = dict(c, screen_t=T0)
    h.src["dexscreener"].next_at = T0 + HOUR
    live["h1"] = 25
    h._uni_add("base", MOV.upper().replace("0X", "0x"), T0, "gt_new")         # other letter case: same coin
    scan_run(h, T0, 1)
    assert f"MOON@base:{MOV[:8]}" in h.pf.positions and h.scan_n["bought"] == 1
    assert not any("gopluslabs" in u or "honeypot.is" in u for u in fetch.calls)
    shutil.rmtree(d)
    # warming (1h +7% with buyers, trigger +10%) is queued behind a trigger-ready mover; thin movers are not
    W, THIN = addr_n(0xBB), addr_n(0xCC)
    def pairs2(a):
        return {MOV: ds_pair("base", a, h1=25, b1=400, s1=100), W: ds_pair("base", a, h1=7, b1=300, s1=100),
                THIN: ds_pair("base", a, h1=50, liq=20_000)}.get(a)
    h, fetch, d = scan_make({"tokens/v1/base/": tokens_fn(pairs2)}, chains=["base"],
                            entry={"h1": 0.10, "h6": -1.0, "buy_ratio": 1.2})
    h.src["dexscreener"].next_at = T0 + HOUR
    for a in (W, THIN, MOV):
        h._uni_add("base", a, T0, "t")
    scan_run(h, T0, 1)
    assert [j["key"] for j in h.queue] == ["base:" + MOV, "base:" + W], h.queue
    assert h.scan_n["movers"] == 1 and h.scan_n["warm"] == 1 and h.state["prefiltered"] == 0
    shutil.rmtree(d)
    # a queued coin that stalls while waiting gets the fresh (non-trigger) numbers, so it is not bought on old data
    live["h1"] = 25
    h, fetch, d = scan_make({"tokens/v1/base/": tokens_fn(pairs)}, chains=["base"])
    for n in ("dexscreener", "goplus", "honeypot"):
        h.src[n].next_at = T0 + HOUR                                      # the screen can't start yet
    h._uni_add("base", MOV, T0, "t")
    scan_run(h, T0, 1)
    assert h.queue and h.queue[0]["c"]["h1"] == 0.25
    live["h1"] = -3
    scan_run(h, T0 + 31_000, 1)
    assert h.queue[0]["c"]["h1"] == -0.03 and not dex.entry_trigger(h.queue[0]["c"], h.p["entry"])
    shutil.rmtree(d)
    print("  scanner: mover -> front of the screen queue (fresh data, no ds step) -> bought; passed coin buys on refresh   ok")


def test_scan_rate_limit_and_backoff():
    st = {"code": 200}
    def fn(u):
        return (st["code"], [ds_pair("base", a, h1=1) for a in u.split("tokens/v1/base/")[1].split(",")])
    h, fetch, d = scan_make({"tokens/v1/base/": fn}, chains=["base"], gap_s=dict(GAP0, ds_scan=1.0))
    for i in range(300):
        h._uni_add("base", addr_n(i), T0, "t")
    scan_run(h, T0, 12, step=250)                                             # 3 s of 4 ticks a second
    assert 2 <= h.scan_calls <= 4, h.scan_calls                              # gap 1 s: <= 60 calls/min
    st["code"] = 429
    t = scan_run(h, T0 + 10_000, 2)
    assert h.scan_n["e429"] == 1 and h.state["status"]["ds_scan"]["code"] == 429
    n = h.scan_calls
    h.queue.clear()
    assert h._enqueue(cand(), t, fresh=True)                                 # main jobs keep running meanwhile
    t = scan_run(h, t, 5)
    assert h.scan_calls == n and any("gopluslabs" in u for u in fetch.calls[-3:])
    st["code"] = 200
    scan_run(h, T0 + 10_000 + 16 * 60_000, 2)                                # 15 min backoff over: back
    assert h.scan_calls >= n + 1
    # time budget: a slow main request (6 s) leaves no room for the scanner in that tick
    clock = iter([0.0, 6.0] * 10)
    h.mono = lambda: next(clock)
    n = h.scan_calls
    h.tick(T0 + HOUR)
    assert h.scan_calls == n
    shutil.rmtree(d)
    print("  scanner: own <= 60/min source, 429 -> 15 min backoff (main jobs unaffected), tick time budget   ok")


def test_scan_bad_bodies():
    A = addr_n(5)
    bodies = iter([(200, "not json"), (200, {"pairs": None}), (200, [None, 1, "x", {"chainId": "base", "baseToken": "s"},
                   {"chainId": "base", "baseToken": {"address": A}, "txns": [1], "liquidity": 5, "priceChange": "x"}]),
                   (500, "<html>"), (200, {"error": "x"}), (0, "timed out"), (200, 7)] * 5)
    table = {"tokens/v1/base/": lambda u: next(bodies),
             "new_pools": (200, {"data": [{"attributes": {"name": "A / B", "transactions": [1]},
                                            "relationships": {"base_token": {"data": {"id": "base_0xq"}}}}, 5]}),
             "token-profiles/latest": (200, {"weird": 1}), "token-boosts/latest": (200, 7)}
    h, fetch, d = scan_make(table, chains=["base"], scan={"gt_new_pages": 1, "hot_s": 1, "cold_s": 1}, feeds=True)
    h._uni_add("base", A, T0, "t")
    scan_run(h, T0, 400, step=2000)
    assert not h._scan_err, h._scan_err                                      # nothing raised
    assert list(h.uni) == [f"base:{A}"] and h.scan_calls >= 5 and h.scan_n["err"] >= 1   # errors back off
    assert parse_gt_pools([1, 2], "base", T0) == [] and parse_gt_pools({"data": "x"}, "base", T0) == []
    shutil.rmtree(d)
    print("  scanner: junk / error bodies from every source never crash the tick   ok")


def test_scan_feeds_and_snapshots():
    OTHER = "Other1111111111111111111111111111111111111"
    boosts = [{"chainId": "base", "tokenAddress": "0xfeed"}, {"chainId": "bsc", "tokenAddress": "0xno"}]
    table = {"networks/solana/new_pools?page=1": (200, {"data": [gt_pool("solana", SOL), gt_pool("solana", OTHER)]}),
             "new_pools": (200, {"data": []}),
             "token-profiles/latest": (200, boosts),
             "tokens/v1/": tokens_fn(lambda a: None if a == "0xno" else [ds_pair("solana" if len(a) > 20 else "base", a, h1=1)])}
    h, fetch, d = scan_make(table, chains=["solana", "base"], scan={"gt_new_pages": 2}, feeds=True)
    h.src["dexscreener"].next_at = h.src["geckoterminal"].next_at = 0
    h.p["every_s"] = dict(h.p["every_s"], discover=10 ** 12, watch=10 ** 12)  # the feeds only
    t = scan_run(h, T0, 12)
    assert set(h.uni) == {f"solana:{SOL}", f"solana:{OTHER}", "base:0xfeed"}, set(h.uni)
    assert h.uni[f"solana:{SOL}"]["src"] == "gt_new" and h.uni["base:0xfeed"]["src"] == "ds_profiles"
    assert abs(h.uni[f"solana:{SOL}"]["created"] - (T0 - 48 * HOUR)) < 5000   # GT said 72h; the DS refresh wins
    assert sum("solana/new_pools?page=1" in u for u in fetch.calls) == 1        # page 1 again only after gt_new_s
    scan_run(h, t + 181_000, 8)
    assert sum("solana/new_pools?page=1" in u for u in fetch.calls) == 2
    h2, fetch2, d2 = scan_make(table, chains=["solana", "base"], scan={"gt_new_pages": 10, "gt_feed_gap_s": 20}, feeds=True)
    scan_run(h2, T0, 60)                                                     # 20+ GeckoTerminal pages due at once...
    assert sum("new_pools" in u for u in fetch2.calls) == 3                  # ...paced to one per 20 s
    shutil.rmtree(d2)
    # after a GeckoTerminal 429 (discovery's or the scanner's own) the scanner leaves GT alone for an hour
    t429 = dict({"new_pools": (429, "")}, **{k: v for k, v in table.items() if "new_pools" not in k})
    h3, fetch3, d3 = scan_make(t429, chains=["solana"], scan={"gt_new_pages": 3}, feeds=True)
    h3.src["geckoterminal"].next_at = T0 + 10 * HOUR                         # discovery quiet
    scan_run(h3, T0, 30)
    assert sum("new_pools" in u for u in fetch3.calls) == 1                  # one 429, then hands off
    assert h3.src["geckoterminal"].fails == 0 and h3.src["gt_scan"].fails == 1   # discovery's source not backed off
    h3.src["gt_scan"].fails, h3.src["gt_scan"].next_at = 0, 0                 # even once its own backoff is over...
    scan_run(h3, T0 + 20 * 60_000, 5)
    assert sum("new_pools" in u for u in fetch3.calls) == 1                  # ...the 1 h hold still applies
    scan_run(h3, T0 + 62 * 60_000, 5)
    assert sum("new_pools" in u for u in fetch3.calls) == 2
    h3.src["gt_scan"].fails, h3.src["gt_scan"].next_at, h3._gt_hold = 0, 0, 0
    h3.src["geckoterminal"].status = 429                                     # discovery just got a 429
    scan_run(h3, T0 + 3 * HOUR, 5)
    assert sum("new_pools" in u for u in fetch3.calls) == 2
    shutil.rmtree(d3)
    h._snap_flush(T0)
    import gzip
    day = h._snap_day
    with gzip.open(f"{d}/scan/{day}.csv.gz", "rt") as f:
        snaps = list(csv.DictReader(f))
    assert sorted(r["addr"] for r in snaps) == sorted([SOL, OTHER, "0xfeed"]), snaps   # once per token per hour
    assert snaps[0]["src"].startswith("scan:") and snaps[0]["liq"] == "600000"
    scan_run(h, T0 + HOUR + 1000, 40)
    h._snap_flush(T0 + HOUR)
    with gzip.open(f"{d}/scan/{day}.csv.gz", "rt") as f:                      # appended gzip members read back as one
        assert len(list(csv.DictReader(f))) == 6
    shutil.rmtree(d)
    print("  scanner feeds: GeckoTerminal new_pools pages, DexScreener profiles; hourly scan snapshots (gzip)   ok")


def test_scan_threaded_worker():
    import time as _t
    code = {"v": 200}
    def slow(u):                                                             # a slow DexScreener: 0.3 s per call
        _t.sleep(0.3)
        return code["v"], [ds_pair("base", a, h1=25 if a == addr_n(5) else 1, b1=400, s1=100)
                           for a in u.split("tokens/v1/base/")[1].split(",")]
    h, fetch, d = scan_make({"tokens/v1/base/": slow}, scan={"threaded": True}, chains=["base"],
                            gap_s=dict(GAP0, ds_scan=0.05, goplus=3600, honeypot=3600))
    for n in ("dexscreener", "goplus", "honeypot"):
        h.src[n].next_at = T0 + 10 * HOUR                                   # main jobs idle
    for i in range(90):
        h._uni_add("base", addr_n(i), T0, "t")
    worst, t, end = 0.0, T0, _t.time() + 5
    while h.scan_n["refreshed"] < 90 and _t.time() < end:
        a = _t.time()
        h.tick(t)
        worst = max(worst, _t.time() - a)
        t += 1000
        _t.sleep(0.05)
    assert h.scan_n["refreshed"] == 90, h.scan_n                             # 3 batches of 30 via the worker
    assert worst < 0.2, worst                                                 # the tick never waited on HTTP
    assert h.queue and h.queue[0]["key"] == f"base:{addr_n(5)}"             # the mover reached the screen queue
    assert h.scan_calls == 3 and h._scan_pending <= 2
    code["v"] = 429                                                          # worker backs off on a 429...
    h.uni = {k: dict(e, r=0) for k, e in h.uni.items()}
    end = _t.time() + 3
    while h.scan_n["e429"] < 1 and _t.time() < end:
        h.tick(t)
        t += 1000
        _t.sleep(0.05)
    calls = h.scan_calls
    for _ in range(10):
        h.tick(t)
        t += 1000
        _t.sleep(0.05)
    assert h.scan_n["e429"] == 1 and h.scan_calls == calls                   # ...15 min, not hammering
    assert not h.src["ds_scan"].ready(int(_t.time() * 1000))
    shutil.rmtree(d)
    print("  scanner worker thread: bulk calls off the main loop (tick < 0.2 s with 0.3 s calls), 429 backoff   ok")


if __name__ == "__main__":
    test_parsers()
    test_checks()
    test_tiers_and_sizing()
    test_clean_token_passes_and_buys()
    test_rejections()
    test_unreachable_fails_closed()
    test_goplus_partial_data()
    test_market_sanity_and_prefilter()
    test_no_second_coin_with_same_name()
    test_renounced_owner_powers_ignored()
    test_snapshots_logged_hourly()
    test_queue_screens_movers_first()
    test_liquidity_floor_scales_with_account()
    test_sizing_caps_in_entries()
    test_crash_needs_a_second_reading()
    test_new_season_restarts_account()
    test_trailing_stop()
    test_evm_address_case()
    test_take_profit_steps()
    test_stake_back_executes()
    test_entry_needs_a_run()
    test_far_off_tick_needs_15_minutes()
    test_recycle_stale_for_stronger_coin()
    test_scam_coin_never_rebought()
    test_pyramid_adds_on_a_proven_runner()
    test_resize_old_small_position()
    test_study_exit()
    test_max_hold()
    test_held_coin_follows_its_own_pool()
    test_absurd_momentum_is_not_a_buy()
    test_liquidity_pull_emergency_exit()
    test_sell_simulation_fails_at_exit()
    test_exit_check_unreachable_then_market()
    test_rescreen_flags_held_token()
    test_tier_upgrade_after_clean_rescreens()
    test_rejected_followup()
    test_auto_pause_after_scams()
    test_reports_and_scoreboard_line()
    test_discovery_sources()
    test_source_backoff()
    test_state_persists()
    test_scan_bulk_refresh()
    test_scan_universe_cap_and_eviction()
    test_scan_mover_front_of_queue_and_buys()
    test_scan_rate_limit_and_backoff()
    test_scan_bad_bodies()
    test_scan_feeds_and_snapshots()
    test_scan_threaded_worker()
    print("all dex tests passed")
