"""Offline tests for dex.py: canned GoPlus (EVM + Solana), honeypot.is, RugCheck, DexScreener and
GeckoTerminal payloads; the screen (pass / every rejection / fail closed), sizing and costs, exits
(trailing stop, take-profit tiers, liquidity pull, sell-simulation failure, re-screen), the
rejected-token follow-up, the scam auto-pause and the run.log / scoreboard lines.

    python dex_test.py
"""
import json
import os
import shutil
import tempfile

import config
import dex
from dex import (DexHunter, best_pairs, check_goplus_evm, check_goplus_sol, check_honeypot, check_market,
                 check_rugcheck, lp_locked, parse_ds_pairs, parse_gt_pools, top_holders)
from social import DAY, HOUR

T0 = 1_760_000_000_000                      # 2025-10-09 UTC
EVM = "0xabc0000000000000000000000000000000000001"
SOL = "So1anaMint111111111111111111111111111111111"
DEAD = "0x000000000000000000000000000000000000dead"
INC = "1nc1nerator11111111111111111111111111111111"
GAP0 = {k: 0 for k in dex.DEFAULTS["gap_s"]}


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
         "holders": [{"address": "0xpair", "tag": "UniswapV2", "is_contract": 1, "percent": "0.30", "is_locked": 0}]
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
RC_OK = {"score": 100, "score_normalised": 5, "rugged": False, "mintAuthority": None, "freezeAuthority": None,
         "risks": [{"name": "Low amount of LP Providers", "level": "warn"}], "markets": [{"lp": {"lpLockedPct": 100}}]}


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
            f"rugcheck.xyz/v1/tokens/{addr}/report": (200, rc or RC_OK)}


def make(table, **params):
    d = tempfile.mkdtemp()
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
    import csv
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
    print("  parsers (dexscreener, geckoterminal)      ok")


def test_checks():
    S = dex.DEFAULTS["screen"]
    d = gp_evm()["result"][EVM]
    assert check_goplus_evm(d, S) == []
    assert abs(top_holders(d["holders"], {"0xpair"}) - 0.30) < 1e-9 and abs(lp_locked(d["lp_holders"]) - 0.97) < 1e-9
    assert lp_locked([]) is None and top_holders(None) is None
    for over, want in ((dict(is_honeypot="1"), "is_honeypot"), (dict(sell_tax="0.12"), "sell tax 12%"),
                       (dict(buy_tax="0.04"), "buy tax 4%"), (dict(buy_tax=""), "buy tax unknown"),
                       (dict(is_mintable="1"), "is_mintable"), (dict(transfer_pausable="1"), "transfer_pausable"),
                       (dict(is_proxy="1"), "is_proxy"), (dict(is_open_source="0"), "not open source"),
                       (dict(hidden_owner=1), "hidden_owner"), (dict(creator_percent="0.08"), "creator_percent 8%"),
                       (dict(lp_holders=[{"address": "0xlp", "percent": "1.0", "is_locked": 0}]), "lp locked 0%"),
                       (dict(lp_holders=[]), "lp holders unknown"),
                       (dict(holders=[{"address": f"0xw{i}", "percent": "0.06"} for i in range(10)]), "top-10 holders 60%")):
        rs = check_goplus_evm(gp_evm(**over)["result"][EVM], S)
        assert any(want in t for t, _ in rs), (over, rs)
    assert ("sell tax 60%", "scam") in check_goplus_evm(gp_evm(sell_tax="0.6")["result"][EVM], S)
    assert ("sell tax 12%", "flag") in check_goplus_evm(gp_evm(sell_tax="0.12")["result"][EVM], S)
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
    assert check_honeypot({"simulationSuccess": False, "honeypotResult": {}}, S) == [("sell simulation failed", "scam")]
    assert check_honeypot({}, S) == [("honeypot.is: no data", "flag")]
    assert check_rugcheck(RC_OK, S) == []
    assert any("freezeAuthority" in t for t, _ in check_rugcheck(dict(RC_OK, freezeAuthority="Auth1"), S))
    assert any("mintAuthority" in t for t, _ in check_rugcheck(dict(RC_OK, mintAuthority="Auth1"), S))
    assert any("lp lock unknown" in t for t, _ in check_rugcheck(dict(RC_OK, markets=[]), S))
    assert any("lp locked 50%" in t for t, _ in check_rugcheck(dict(RC_OK, markets=[{"lp": {"lpLockedPct": 50}}]), S))
    assert any("danger" in t for t, _ in check_rugcheck(dict(RC_OK, risks=[{"name": "Freeze Authority still enabled", "level": "danger"}]), S))
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
    print("  scam checks (goplus evm/sol, honeypot.is, rugcheck, market)  ok")


# ---- screening ------------------------------------------------------------------------------
def test_clean_token_passes_and_buys():
    h, fetch, d = make(table_evm())
    screen(h, cand())
    sc = rows(f"{d}/screen.csv")
    assert sc[-1]["verdict"] == "PASS" and sc[-1]["sources"] == "ds+goplus+honeypot", sc
    assert any("gopluslabs" in u for u in fetch.calls) and any("honeypot.is" in u for u in fetch.calls)
    pos = h.pf.positions["TOK@base:0xabc000"]
    usd = min(500 * 0.05, 600_000 * 0.005)                       # 5% of equity binds: $25
    assert abs(pos["cost0"] - usd) < 1e-9 and pos["liq0"] == 600_000 and pos["tp1"] is False
    t = rows(f"{d}/dex_hunter/trades.csv")[0]
    impact = usd / 600_000
    assert abs(float(t["price"]) - 0.01 * (1 + 0.01 + impact)) < 1e-9, t   # 1% slippage + impact
    assert abs(float(t["fee"]) - usd * 0.003) < 1e-9 and "impact" in t["reason"]
    assert os.path.exists(f"{d}/dex_hunter/equity.csv") and os.path.exists(f"{d}/dex_hunter/portfolio.json")
    # Solana clean token: goplus solana + rugcheck
    h2, fetch2, d2 = make(table_sol())
    screen(h2, cand("solana", SOL, sym="SOLT"))
    assert rows(f"{d2}/screen.csv")[-1]["sources"] == "ds+goplus+rugcheck" and "SOLT@solana:So1anaMi" in h2.pf.positions
    # no momentum -> screened, kept in `passed`, not bought
    h3, _, d3 = make(table_evm(pair=ds_pair("base", EVM, h1=1)))
    screen(h3, cand(h1=1))
    assert rows(f"{d3}/screen.csv")[-1]["verdict"] == "PASS" and not h3.pf.positions and h3.state["passed"]
    for x in (d, d2, d3):
        shutil.rmtree(x)
    print("  clean token passes -> momentum entry, costs   ok")


def test_rejections():
    cases = [("honeypot (goplus)", table_evm(gp=gp_evm(is_honeypot="1")), "is_honeypot", "honeypot.is"),
             ("honeypot (honeypot.is)", table_evm(hp=HP_BAD), "honeypot (sell reverted)", None),
             ("high tax (goplus)", table_evm(gp=gp_evm(sell_tax="0.12")), "sell tax 12%", "honeypot.is"),
             ("high tax (honeypot.is)", table_evm(hp=dict(HP_OK, simulationResult={"buyTax": 0, "sellTax": 8})), "sell tax 8%", None),
             ("mintable", table_evm(gp=gp_evm(is_mintable="1")), "is_mintable", "honeypot.is"),
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
           ("mint authority (rugcheck)", table_sol(rc=dict(RC_OK, mintAuthority="M")), "rugcheck: mintAuthority"),
           ("LP not burned (rugcheck)", table_sol(rc=dict(RC_OK, markets=[{"lp": {"lpLockedPct": 40}}])), "rugcheck lp locked 40%"),
           ("rugcheck danger", table_sol(rc=dict(RC_OK, risks=[{"name": "Large Amount of LP Unlocked", "level": "danger"}])), "rugcheck danger")]
    for name, table, want in sol:
        h, fetch, d = make(table)
        screen(h, cand("solana", SOL))
        r = rows(f"{d}/screen.csv")[-1]
        assert r["verdict"] == "REJECT" and want in r["reasons"], (name, r)
        shutil.rmtree(d)
    print("  rejections: honeypot, tax, mintable, freeze, LP, whales, proxy   ok")


def test_unreachable_fails_closed():
    for name, table in (("goplus 500", dict(table_evm(), **{"gopluslabs": (500, "")})),
                        ("goplus timeout", dict(table_evm(), **{"gopluslabs": (0, "timed out")})),
                        ("honeypot.is 503", dict(table_evm(), **{"honeypot.is": (503, "")})),
                        ("goplus bad json", dict(table_evm(), **{"gopluslabs": (200, "<html>")})),
                        ("rugcheck down", dict(table_sol(), **{"rugcheck.xyz": (502, "")}))):
        t = {k: v for k, v in table.items()}
        # put the failing entry first so it wins the substring match
        t = dict(sorted(t.items(), key=lambda kv: kv[1][0] == 200))
        h, fetch, d = make(t)
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


def test_liquidity_scales_with_account():
    h, _, d = make({})
    assert h.S()["min_liq"] == 250_000                                    # $500: 5% = $25 -> floor binds
    h.pf.cash = 10_000
    assert h.S()["min_liq"] == 250_000                                    # $500 position: 200x = $100k < floor
    h.pf.cash = 100_000
    assert h.S()["min_liq"] == 1_000_000                                  # $5k position: <= 0.5% of pool -> $1M
    assert not h._enqueue(cand(liq=600_000), T0, fresh=False)             # too shallow for this account now
    shutil.rmtree(d)
    print("  min liquidity scales with position size ($10k -> $250k, $100k -> $1M)   ok")


def test_sizing_capped_by_liquidity():
    h, _, d = make({})
    c = cand(liq=3000)
    h.state["passed"][h.key(c)] = dict(c, screen_t=T0)
    h._try_entry(h.key(c), T0)
    pos = h.pf.positions["TOK@base:0xabc000"]
    assert abs(pos["cost0"] - 15.0) < 1e-9, pos["cost0"]                   # 0.5% of $3k = $15 < $25
    assert abs(pos["impact"] - 15 / 3000) < 1e-12
    c2 = cand(addr="0xdef", sym="TINY", liq=1000)                          # $5 < MIN_ORDER_USD: skipped
    h.state["passed"][h.key(c2)] = dict(c2, screen_t=T0)
    h._try_entry(h.key(c2), T0)
    assert len(h.pf.positions) == 1
    shutil.rmtree(d)
    print("  position size capped by pool liquidity   ok")


# ---- exits -----------------------------------------------------------------------------------
def held(table_extra=None, **pair_kw):
    """A hunter holding TOK bought at 0.01 with a mutable live pair (px['v'], px['liq'])."""
    px = {"v": 0.01, "liq": 600_000, "gone": False}
    table = {"tokens/v1/base/": lambda u: (200, [] if px["gone"] else [ds_pair("base", EVM, price=px["v"], liq=px["liq"], **pair_kw)])}
    table.update(table_extra or {})
    table.update({k: v for k, v in table_evm().items() if k not in table})
    h, fetch, d = make(table)
    screen(h, cand())
    assert "TOK@base:0xabc000" in h.pf.positions
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
    k, t = "TOK@base:0xabc000", T0 + 6000
    t = poll(h, t, px, v=0.015)
    pos = h.pf.positions[k]
    assert pos["peak"] == 0.015 and abs(pos["stop"] - 0.015 * 0.7) < 1e-12
    t = poll(h, t, px, v=0.0106)                                            # above the stop: hold
    assert k in h.pf.positions and not h.pf.positions[k].get("exit")
    n_calls = len(fetch.calls)
    t = poll(h, t, px, v=0.0104)                                            # below 0.0105: exit
    assert k not in h.pf.positions
    assert any("IsHoneypot" in u for u in fetch.calls[n_calls:])            # sell simulation ran first
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "normal" and "trailing stop" in oc["reason"] and float(oc["exit"]) == 0.0104
    tr = rows(f"{d}/dex_hunter/trades.csv")[-1]
    usd = float(tr["qty"]) * 0.0104
    assert abs(float(tr["price"]) - 0.0104 * (1 - 0.01 - usd / 600_000)) < 1e-9   # slippage + impact on the way out
    assert h.pf.cooldown[k] == t - 1000 + DAY - 2000 or h.pf.cooldown[k] > t - 5000
    shutil.rmtree(d)
    print("  trailing stop 30% below peak (after sell simulation)   ok")


def test_take_profit_tiers():
    h, fetch, d, px = held()
    k, t = "TOK@base:0xabc000", T0 + 6000
    q0, entry = h.pf.positions[k]["qty"], h.pf.positions[k]["entry"]
    t = poll(h, t, px, v=0.021)                                             # +110%: sell half, cost recovered
    pos = h.pf.positions[k]
    assert pos["tp1"] and not pos["tp2"] and abs(pos["qty"] - q0 / 2) < 1e-12
    assert pos["stop"] >= entry and pos["realized"] > 0                    # remainder rides free
    assert "take-profit +100%" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    t = poll(h, t, px, v=0.03)                                              # +200%: nothing new
    assert abs(h.pf.positions[k]["qty"] - q0 / 2) < 1e-12
    t = poll(h, t, px, v=0.051)                                             # +410%: half of the remainder
    pos = h.pf.positions[k]
    assert pos["tp2"] and abs(pos["qty"] - q0 / 4) < 1e-12 and "+400%" in rows(f"{d}/dex_hunter/trades.csv")[-1]["reason"]
    assert abs(pos["stop"] - 0.051 * 0.7) < 1e-12                          # the rest rides the trailing stop
    t = poll(h, t, px, v=0.035)                                             # < 0.0357: stopped out, net winner
    assert k not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "normal" and float(oc["pnl"]) > 25 * 1.5, oc
    shutil.rmtree(d)
    print("  take-profit tiers (+100% half, +400% half of rest), break-even stop   ok")


def test_liquidity_pull_emergency_exit():
    h, fetch, d, px = held()
    k, t = "TOK@base:0xabc000", T0 + 6000
    t = poll(h, t, px, v=0.009, liq=320_000)                                # -47%: still holding
    assert k in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=120_000)                                # -80% liquidity: rug
    assert k not in h.pf.positions
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert oc["outcome"] == "scammed_rug" and "liquidity pulled 80%" in oc["reason"] and float(oc["pnl"]) < 0
    tr = rows(f"{d}/dex_hunter/trades.csv")[-1]
    usd = float(tr["qty"]) * 0.004
    assert abs(float(tr["price"]) - 0.004 * (1 - 0.01 - usd / 120_000)) < 1e-9   # impact on the thinned pool
    assert h.state["scams"] and not h.paused()
    # pool gone entirely (no pair left): booked at -100%
    h, fetch, d, px = held()
    px["gone"] = True
    t = poll(h, T0 + 6000, px)
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert k not in h.pf.positions and oc["outcome"] == "scammed_rug" and abs(float(oc["ret"]) + 1) < 1e-9, oc
    shutil.rmtree(d)
    print("  liquidity pull > 50% -> emergency exit at post-rug price / -100%   ok")


def test_sell_simulation_fails_at_exit():
    h, fetch, d, px = held()
    k, t = "TOK@base:0xabc000", T0 + 6000
    fetch_table_hp = h.fetch                        # swap honeypot.is to "honeypot" for the exit check
    h.fetch = h.src["honeypot"].fetch = fake_fetch({"IsHoneypot": (200, HP_BAD)})
    t = poll(h, t, px, v=0.006)                                             # stop hit; sell sim says honeypot
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert k not in h.pf.positions and oc["outcome"] == "scammed_honeypot" and abs(float(oc["ret"]) + 1) < 1e-9
    assert "SELL SIMULATION FAILED" in oc["reason"] and "trailing stop" in oc["reason"]
    # Solana: GoPlus freeze authority at exit time
    table = table_sol()
    px2 = {"v": 0.01}
    table["tokens/v1/solana/"] = lambda u: (200, [ds_pair("solana", SOL, sym="SOLT", price=px2["v"])])
    h2, f2, d2 = make(table)
    screen(h2, cand("solana", SOL, sym="SOLT"))
    h2.src["goplus"].fetch = fake_fetch({"solana/token_security": (200, gp_sol(freezable={"status": "1"}))})
    px2["v"] = 0.005
    run(h2, T0 + 70_000, 3)
    oc = rows(f"{d2}/outcomes.csv")[-1]
    assert oc["outcome"] == "scammed_honeypot" and "freeze authority" in oc["reason"], oc
    shutil.rmtree(d)
    shutil.rmtree(d2)
    print("  exit re-runs the sell simulation; failure books -100% SCAMMED   ok")


def test_exit_check_unreachable_then_market():
    h, fetch, d, px = held()
    k, t = "TOK@base:0xabc000", T0 + 6000
    h.src["honeypot"].fetch = fake_fetch({"IsHoneypot": (503, "")})
    t = poll(h, t, px, v=0.006, n=5)
    assert k in h.pf.positions and h.pf.positions[k]["exit"]               # waiting for the sell check
    h.tick(t + 700_000)                                                     # 10 min later: booked at market
    oc = rows(f"{d}/outcomes.csv")[-1]
    assert k not in h.pf.positions and oc["outcome"] == "normal" and "sell check unreachable" in oc["reason"]
    shutil.rmtree(d)
    print("  sell check unreachable -> retried, then booked at market   ok")


def test_rescreen_flags_held_token():
    for name, gp, outcome, want in (("sell tax 60%", gp_evm(sell_tax="0.6"), "scammed_honeypot", "sell tax 60%"),
                                    ("trading paused", gp_evm(transfer_pausable="1"), "scammed_honeypot", "transfer_pausable"),
                                    ("newly mintable", gp_evm(is_mintable="1"), "emergency_exit", "is_mintable")):
        h, fetch, d, px = held()
        k = "TOK@base:0xabc000"
        h.src["goplus"].fetch = fake_fetch({"token_security": (200, gp)})
        run(h, T0 + 10_000, 3)
        assert k in h.pf.positions and not h.pf.positions[k].get("exit")   # < 30 min: no re-screen yet
        run(h, T0 + 1801_000, 4)                                            # re-screen -> flagged -> exit check -> sold
        oc = rows(f"{d}/outcomes.csv")[-1]
        assert k not in h.pf.positions and oc["outcome"] == outcome and want in oc["reason"], (name, oc)
        shutil.rmtree(d)
    h, fetch, d, px = held()                                                # clean re-screen: keep holding
    run(h, T0 + 1801_000, 4)
    assert "TOK@base:0xabc000" in h.pf.positions and h.pf.positions["TOK@base:0xabc000"]["rescreened"] >= T0 + 1801_000
    shutil.rmtree(d)
    print("  periodic re-screen: honeypot/tax/pause -> SCAMMED, other flags -> emergency exit   ok")


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
    k, t = "TOK@base:0xabc000", T0 + 6000
    t = poll(h, t, px, v=0.004, liq=100_000)                                # scam #1
    assert k not in h.pf.positions and not h.paused()
    px.update(v=0.01, liq=600_000)
    h.state["seen"].clear()
    h.pf.cooldown.clear()
    t = screen(h, cand(), t=t + 1000)                                       # buys again...
    assert k in h.pf.positions
    t = poll(h, t, px, v=0.004, liq=100_000)                                # scam #2 -> paused
    assert h.paused() == "scam limit" and len(h.state["scams"]) == 2
    h.state["seen"].clear()
    h.pf.cooldown.clear()
    t = screen(h, cand(), t=t + 1000)
    assert rows(f"{d}/screen.csv")[-1]["verdict"] == "PASS" and k not in h.pf.positions   # screened, not bought
    assert "PAUSED" in h.status_line()
    s = dex.scoreboard_stats(d)
    assert s["scammed"] == 2 and s["lost"] < 0 and s["paused"] == "scam limit" and s["trades"] == 4
    cwd = os.getcwd()
    os.chdir(d)                                                             # scoreboard_line reads data/dex by default
    try:
        os.makedirs("data", exist_ok=True)
        os.symlink(d, "data/dex")
        line = dex.scoreboard_line()
    finally:
        os.chdir(cwd)
    assert line.startswith("**DEX: $") and "Scammed: 2 (-" in line and line.endswith("DEX paused: scam limit"), line
    h.p["scam_pause"]["reset_after"] = "2030-01-01 00:00"                   # manual re-enable in config
    h.tick(t + 1000)
    assert not h.paused() and not h.state["scams"]
    h._try_entry("base:" + EVM, t + 2000)
    assert k in h.pf.positions
    # a scam outside the 30-day window does not count
    h2, _, d2 = make({})
    h2.state["scams"] = [T0 - 31 * DAY]
    h2._count_scam(T0)
    assert not h2.paused() and h2.state["scams"] == [T0]
    shutil.rmtree(d)
    shutil.rmtree(d2)
    print("  2 scams in 30 days -> new entries paused until reset_after   ok")


def test_reports_and_self_check():
    h, fetch, d = make({"gopluslabs": (200, gp_evm()), "honeypot.is": (200, HP_OK), "rugcheck": (500, ""),
                        "dexscreener": (200, []), "geckoterminal": (429, "")})
    line = h.self_check(T0)
    assert line == "dex self-check: goplus 200 | honeypot.is 200 | rugcheck 500 | dexscreener 200 | geckoterminal 429", line
    assert h.state["status"]["rugcheck"]["code"] == 500 and not h.src["geckoterminal"].ready(T0 + 10 * 60_000)
    assert h.weekly_line(T0) == "dex weekly: screened 0, passed 0, trades 0, scammed 0 (cost $+0.00), rejected-that-rugged 0/0, rejected-that-ran-up 0/0"
    h.pf.cash = 560.0
    assert h.sweep_line(T0) == "dex sweep sim: equity $560.00, would sweep $60.00 profit to USDC (cumulative $60.00); no action taken"
    h.pf.cash = 570.0
    assert "would sweep $10.00" in h.sweep_line(T0) and rows(f"{d}/sweeps.csv")[-1]["swept_total"] == "70.0"
    assert dex.scoreboard_stats(d)["equity"] == 500.0 and dex.scoreboard_stats(d)["scammed"] == 0
    assert dex.scoreboard_line().startswith("**DEX: $") and "Scammed: 0" in dex.scoreboard_line()
    shutil.rmtree(d)
    print("  self-check line, weekly line, monthly sweep simulation   ok")


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
    assert h.state["watch_done"] == {"WATCHY": T0 + 5000} or "WATCHY" in h.state["watch_done"]
    gt = next(j for j in h.queue if j["key"].startswith("solana"))
    assert gt["steps"] == ["ds", "goplus", "rugcheck"]                       # GT data gets a DexScreener refresh
    assert next(j for j in h.queue if j["key"] == "base:0xboost")["steps"] == ["goplus", "honeypot"]
    shutil.rmtree(d)
    shutil.rmtree(sd)
    print("  discovery: geckoterminal trending, dexscreener boosts, social dex_watch   ok")


def test_state_persists():
    h, fetch, d = make(table_evm())
    screen(h, cand())
    h2 = DexHunter(params={"dir": d, "gap_s": GAP0}, fetch=fetch, now_ms=T0 + 5000)
    h2._load()
    assert "TOK@base:0xabc000" in h2.pf.positions and h2.pf.positions["TOK@base:0xabc000"]["liq0"] == 600_000
    assert h2.state["seen"]["base:" + EVM]["v"] == "PASS" and h2.equity() == h.equity()
    shutil.rmtree(d)
    print("  state + portfolio survive a restart   ok")


if __name__ == "__main__":
    test_parsers()
    test_checks()
    test_clean_token_passes_and_buys()
    test_rejections()
    test_unreachable_fails_closed()
    test_market_sanity_and_prefilter()
    test_liquidity_scales_with_account()
    test_sizing_capped_by_liquidity()
    test_trailing_stop()
    test_take_profit_tiers()
    test_liquidity_pull_emergency_exit()
    test_sell_simulation_fails_at_exit()
    test_exit_check_unreachable_then_market()
    test_rescreen_flags_held_token()
    test_rejected_followup()
    test_auto_pause_after_scams()
    test_reports_and_self_check()
    test_discovery_sources()
    test_state_persists()
    print("all dex tests passed")
