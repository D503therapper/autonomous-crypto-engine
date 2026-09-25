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


def make(table, **params):
    """Hunter on a temp dir with a canned fetch; discovery endpoints answer empty unless the table says."""
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
    print("  rejections: honeypot, tax, mintable, pausable, freeze, LP, whales, proxy   ok")


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


def test_market_sanity_and_prefilter():
    h, fetch, d = make({})
    assert not h._enqueue(cand(liq=20_000), T0, fresh=False) and h.state["prefiltered"] == 1   # tiny pool
    assert not h._enqueue(cand(age_h=3), T0, fresh=False)                                       # young pool
    assert not h.queue and not fetch.calls
    shutil.rmtree(d)
    for kw, want in ((dict(liq=20_000), "liquidity $20,000 < $250,000"), (dict(age_h=5), "pool age 5.0h < 24h"),
                     (dict(vol=100_000), "24h volume $100,000"), (dict(b24=0), "no buys or no sells"),
                     (dict(h6=45, h1=-20), "spike-and-fade")):
        h, fetch, d = make(table_evm(pair=ds_pair("base", EVM, **kw)))   # discovery data looked fine...
        screen(h, cand())                                                # ...DexScreener says otherwise
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and want in r["reasons"], (kw, r)
        assert not any("gopluslabs" in u for u in fetch.calls)          # no security call wasted
        shutil.rmtree(d)
    print("  market sanity: tiny / young pool, volume, one-sided, fade   ok")


def test_liquidity_floor_scales_with_account():
    h, _, d = make({})
    assert h.S()["min_liq"] == 250_000                                    # $500: 3% = $15 -> floor binds
    h.pf.cash = 10_000
    assert h.S()["min_liq"] == 250_000                                    # $300 x 50 = $15k < floor
    h.pf.cash = 1_000_000
    assert h.S()["min_liq"] == 1_500_000                                  # $30k x 50
    assert not h._enqueue(cand(liq=600_000), T0, fresh=False)             # too shallow for this account now
    shutil.rmtree(d)
    print("  min liquidity = max($250k, 50 x planned position)   ok")


def test_sizing_caps_in_entries():
    h, _, d = make({})
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
    t = poll(h, t, px, v=0.051)                                             # +410%: half of the remainder
    pos = h.pf.positions[K]
    assert pos["tp2"] and abs(pos["qty"] - q0 / 4) < 1e-12 and "+400%" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    assert abs(pos["stop"] - 0.051 * 0.7) < 1e-12                          # the rest rides the trailing stop
    t = poll(h, t, px, v=0.035)                                             # < 0.0357: stopped out, net winner
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
    print("  take-profit steps (+100% half, +400% half of rest), break-even stop on the free ride   ok")


def test_max_hold():
    h, fetch, d, px = held()
    poll(h, T0 + 14 * DAY, px, v=0.012)
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert K not in h.pf.positions and "time limit 14d" in oc["reason"]
    shutil.rmtree(d)
    print("  14-day max hold   ok")


def test_liquidity_pull_emergency_exit():
    h, fetch, d, px = held()
    t = poll(h, T0 + 6000, px, v=0.009, liq=320_000)                        # -47%: still holding
    assert K in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=120_000)                                # -80% liquidity: rug
    assert K not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "scammed_rug" and "liquidity pulled 80%" in oc["reason"] and float(oc["pnl"]) < 0
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
    print("  liquidity pull > 50% -> emergency exit at post-rug price / -100%   ok")


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
    run(h, T0 + HOUR + 1000, 2)
    assert fu["base:" + EVM]["liq_min"] == 20_000 and fu["base:0xdef"]["px_max"] == 0.07 and fu["base:0xdef"]["n"] == 1
    live[EVM] = (0.0004, 15_000)
    del live["0xdef"]                                                                   # pair gone: liq 0
    run(h, T0 + 2 * HOUR + 2000, 2)
    assert fu["base:0xdef"]["liq"] == 0
    run(h, T0 + 7 * DAY + 3000, 2)                                                      # 7 days: finalized
    assert not h.state["followup"]
    r = {x["address"]: x for x in rows(f"{d}/rejected_followup.csv")}
    assert r[EVM]["rugged"] == "1" and r[EVM]["ran_up"] == "0"
    assert r["0xdef"]["rugged"] == "1" and r["0xdef"]["ran_up"] == "1" and float(r["0xdef"]["max_gain"]) == 2.5
    line = h.weekly_line(T0 + 7 * DAY + 3000)
    assert "rejected-that-rugged 2/2" in line and "rejected-that-ran-up 1/2" in line and "screened 3, passed 0" in line
    shutil.rmtree(d)
    print("  rejected tokens followed 7 days (rug / run-up), sampled per day   ok")


def test_auto_pause_after_scams():
    h, fetch, d, px = held()
    t = poll(h, T0 + 6000, px, v=0.004, liq=100_000)                        # scam #1
    assert K not in h.pf.positions and not h.paused()
    px.update(v=0.01, liq=600_000)
    h.state["seen"].clear()
    h.pf.cooldown.clear()
    t = screen(h, cand(), t=t + 1000)                                       # buys again...
    assert K in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=100_000)                                # scam #2 -> paused
    assert h.paused() == "scam limit" and len(h.state["scams"]) == 2
    h.state["seen"].clear()
    h.pf.cooldown.clear()
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
    table = {"trending_pools": (200, {"data": [gt_pool("solana", SOL), gt_pool("solana", "Thin", liq=1000)]}),
             "token-boosts/top": (200, boosts),
             "tokens/v1/base/0xboost": (200, [ds_pair("base", "0xboost", sym="BST")]),
             "search?q=WATCHY": (200, {"pairs": [ds_pair("base", "0xwatch", sym="WATCHY"), ds_pair("bsc", "0xw2", sym="WATCHY")]})}
    h, fetch, d = make(table, chains=["solana", "base"])
    sd = tempfile.mkdtemp()
    with open(f"{sd}/dex_watch.json", "w") as f:
        json.dump({"WATCHY": {"chain": "base", "n": 3, "last": "x"}, "ONCE": {"chain": "base", "n": 1}}, f)
    old, dex.SOCIAL = dex.SOCIAL, {"dir": sd}
    try:
        for i in range(8):
            h.tick(T0 + i * 1000)
    finally:
        dex.SOCIAL = old
    keys = {j["key"] for j in h.queue}
    assert keys == {"solana:" + SOL, "base:0xboost", "base:0xwatch"}, keys
    assert h.state["prefiltered"] == 1                                       # the thin GT pool, silently
    assert any("trending_pools" in u for u in fetch.calls) and any("search?q=WATCHY" in u for u in fetch.calls)
    assert sum("trending_pools" in u for u in fetch.calls) == 2              # solana + base (eth not configured)
    assert "WATCHY" in h.state["watch_done"]
    gt = next(j for j in h.queue if j["key"].startswith("solana"))
    assert gt["steps"] == ["ds", "goplus", "rugcheck"]                       # GT data gets a DexScreener refresh
    assert next(j for j in h.queue if j["key"] == "base:0xboost")["steps"] == ["goplus", "honeypot"]
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
    h2 = DexHunter(params={"dir": d, "gap_s": GAP0}, fetch=fetch, now_ms=T0 + 5000)
    h2._load()
    assert K in h2.pf.positions and h2.pf.positions[K]["liq0"] == 600_000 and h2.pf.positions[K]["tier"] == "A"
    assert h2.state["seen"]["base:" + EVM]["v"] == "PASS" and h2.equity() == h.equity()
    shutil.rmtree(d)
    print("  state + portfolio survive a restart   ok")


if __name__ == "__main__":
    test_parsers()
    test_checks()
    test_tiers_and_sizing()
    test_clean_token_passes_and_buys()
    test_rejections()
    test_unreachable_fails_closed()
    test_market_sanity_and_prefilter()
    test_liquidity_floor_scales_with_account()
    test_sizing_caps_in_entries()
    test_trailing_stop()
    test_take_profit_steps()
    test_max_hold()
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
    print("all dex tests passed")
