"""Offline tests for social.py: canned payloads per source (normal / empty / malformed / 429),
mention extraction, heat scoring, the social_heat strategy on synthetic prices, file rolling.

    python social_test.py
"""
import json
import os
import shutil
import tempfile

import config
import social
from engine import Portfolio, step
from social import (Collector, HeatTracker, SocialHeat, extract_mentions, parse_coingecko, parse_dex_list,
                    parse_dex_tokens, parse_geckoterminal, parse_reddit, tag)

MIN, HOUR, DAY = social.MIN, social.HOUR, social.DAY
T0 = 1_760_000_000_000                      # 2025-10-09 UTC
UNI = ["BTC", "ETH", "SOL", "PEPE", "BONK", "WIF", "ONE", "GAS", "AI", "FLOKI", "PNUT", "SUI", "USDT", "ARB"]

# ---- canned payloads --------------------------------------------------------------------
CG = {"coins": [{"item": {"id": "pepe", "name": "Pepe", "symbol": "PEPE", "score": 0}},
                {"item": {"id": "bonk", "name": "Bonk", "symbol": "bonk", "score": 1}},
                {"item": {"id": "x", "name": "Nowhere", "symbol": "NOWH", "score": 2}},
                {"item": {"id": "peanut", "name": "Peanut the Squirrel", "symbol": "PNUT"}}],   # no score
      "nfts": [], "categories": []}
GT = {"data": [{"attributes": {"name": "WIF / SOL", "reserve_in_usd": "2500000", "volume_usd": {"h24": "9e6"},
                               "price_change_percentage": {"h24": "12.5"}},
                "relationships": {"network": {"data": {"id": "solana"}}, "base_token": {"data": {"id": "solana_abc"}}}},
               {"attributes": {"name": "DEXONLY / WETH 0.3%"}, "relationships": {"base_token": {"data": {"id": "eth_0x1"}}}},
               {"attributes": {}}, "junk"]}
DS_LIST = [{"chainId": "solana", "tokenAddress": "A1", "amount": 10}, {"chainId": "solana", "tokenAddress": "A2"},
           {"chainId": "base", "tokenAddress": "B1"}, {"chainId": "solana", "tokenAddress": "A1"}, {"nope": 1}]
DS_TOKENS = [{"chainId": "solana", "baseToken": {"address": "A1", "symbol": "bonk", "name": "Bonk"},
              "liquidity": {"usd": 100}, "volume": {"h24": 5}, "priceChange": {"h24": -3}},
             {"chainId": "solana", "baseToken": {"address": "A1", "symbol": "BONK", "name": "Bonk"},
              "liquidity": {"usd": 5000}},                                        # deeper pair wins
             {"chainId": "solana", "baseToken": {"address": "A2", "symbol": "RUGME", "name": "Rug Me"}},
             {"baseToken": {}}, {}]


def reddit_body(posts, t=T0):
    return {"data": {"children": [{"data": {"id": f"p{i}", "title": p, "selftext": "", "created_utc": t / 1000}}
                                  for i, p in enumerate(posts)]}}


def fake_fetch(table):
    """fetch(url, timeout) -> (status, text) from {substring: (status, payload)}; counts calls."""
    calls = []

    def fetch(url, timeout):
        assert timeout <= 8, timeout
        calls.append(url)
        for k, (st, body) in table.items():
            if k in url:
                return st, body if isinstance(body, str) else json.dumps(body)
        return 404, ""
    fetch.calls = calls
    return fetch


def make(table, universe=UNI, **params):
    d = tempfile.mkdtemp(prefix="social_")
    tr = HeatTracker(params=dict({"dir": d}, **params), universe=universe, fetch=fake_fetch(table), now_ms=T0)
    return tr, d


# ---- parsers ------------------------------------------------------------------------------
def test_parsers():
    s = parse_coingecko(json.dumps(CG))
    assert [(x["coin"], x["rank"]) for x in s] == [("PEPE", 1), ("BONK", 2), ("NOWH", 3), ("PNUT", 4)], s
    assert s[3]["name"] == "peanut the squirrel"
    assert parse_coingecko("") == [] and parse_coingecko("{not json") == [] and parse_coingecko('{"coins": "x"}') == []
    assert parse_coingecko('{"coins": [1, {"item": 5}, {"item": {"symbol": ""}}]}') == []
    r = parse_reddit(json.dumps(reddit_body(["$PEPE to the moon", "hello"])))
    assert [x["id"] for x in r] == ["p0", "p1"] and r[0]["t"] == T0 and "$PEPE" in r[0]["text"]
    assert parse_reddit("") == [] and parse_reddit('{"data": {"children": [{"data": {}}, 3]}}') == []
    g = parse_geckoterminal(json.dumps(GT))
    assert [(x["coin"], x["rank"], x["chain"]) for x in g] == [("WIF", 1, "solana"), ("DEXONLY", 2, "eth")], g
    assert g[0]["liq"] == 2.5e6 and g[0]["chg24"] == 12.5
    assert parse_geckoterminal("[]") == [] and parse_geckoterminal(None) == []
    assert parse_dex_list(json.dumps(DS_LIST)) == [("solana", "A1"), ("solana", "A2"), ("base", "B1")]
    assert parse_dex_list("{}") == [] and parse_dex_list("oops") == []
    t = parse_dex_tokens(json.dumps(DS_TOKENS))
    assert set(t) == {"A1", "A2"} and t["A1"]["coin"] == "BONK" and t["A1"]["liq"] == 5000, t
    assert parse_dex_tokens('{"pairs": []}') == {} and parse_dex_tokens("nope") == {}
    print("  parsers: normal / empty / malformed     ok")


# ---- mention extraction ------------------------------------------------------------------
def test_mentions():
    uni = UNI
    f = lambda t: extract_mentions(t, uni)
    assert f("$PEPE is pumping, $pepe $Bonk!!") == {"PEPE", "BONK"}
    assert f("PEPE and BONK are running") == {"PEPE", "BONK"}          # bare, uppercase, >= 4 chars
    assert f("pepe and bonk are running") == set()                     # 4-letter names too ambiguous in lower case
    assert f("Ethereum vs Solana debate") == {"ETH", "SOL"}             # names, any case
    assert f("BTC ETH SOL") == set()                                    # short bare tickers need $ or name
    assert f("$BTC $eth") == {"BTC", "ETH"}
    assert f("bitcoin is king") == {"BTC"}
    assert f("ONE more thing, GAS fees, AI hype, the ARB") == set()    # common words
    assert f("$ONE $GAS $AI $ARB") == {"ONE", "GAS", "AI", "ARB"}
    assert f("Sui network is fast") == {"SUI"}                          # 3-letter ticker via full name
    assert f("Sui is fast") == set()
    assert f("PNUT $PNUT peanut the squirrel") == {"PNUT"}              # counted once
    assert f("xPEPEx PEPE2 $PEPE2") == set()                            # no partial / suffixed matches
    assert f("$USDT is stable") == {"USDT"}                             # extraction is neutral; tracker filters
    assert f("") == set()
    assert extract_mentions("moo deng day", ["MOODENG"]) == {"MOODENG"}                  # built-in name
    assert extract_mentions("zebra coin day", ["ZBR"], {"ZBR": "zebra coin"}) == {"ZBR"}   # learned name
    assert extract_mentions("zebra coin day", ["ZBR"], {}) == set()
    print("  mention extraction edge cases          ok")


# ---- collectors: statuses and backoff -----------------------------------------------------
def test_collector_backoff():
    class Boom(Collector):
        def run(self, now, tracker):
            st, body = self.get("u")
            if st == 200 and body == "boom":
                raise ValueError("parser bug")
            return st, [], ""
    for code, first, cap in ((429, 15 * MIN, 6 * HOUR), (403, 15 * MIN, 6 * HOUR), (500, 2 * MIN, HOUR),
                             (0, 2 * MIN, HOUR)):
        c = Boom("x", 15, fetch=lambda u, t: (code, "err"), timeout=99)
        assert c.timeout == 8
        st, s, _ = c.poll(T0, None)
        assert st == code and s == [] and c.next_at == T0 + first, (code, c.next_at - T0)
        for i in range(12):                                     # doubling, capped
            c.poll(c.next_at, None)
        last = c.next_at
        c.poll(last, None)
        assert c.next_at - last == cap, (code, c.next_at - last)
    c = Boom("x", 15, fetch=lambda u, t: (200, "boom"))
    st, s, note = c.poll(T0, None)                          # parser exception -> logged, not raised
    assert st == -1 and s == [] and "parser bug" in note
    c = Boom("x", 15, fetch=lambda u, t: (200, "ok"))
    assert c.poll(T0, None)[0] == 200 and c.next_at == T0 + 15 * MIN and c.fails == 0
    assert not c.due(T0 + 14 * MIN) and c.due(T0 + 15 * MIN)
    print("  collector backoff 429/403/5xx/network   ok")


# ---- tracker / heat ------------------------------------------------------------------------
def test_tracker_heat():
    table = {"search/trending": (200, CG), "duration=1h": (200, GT), "duration=5m": (200, {"data": []}),
             "token-boosts/top": (200, DS_LIST), "tokens/v1/solana": (200, DS_TOKENS),
             "CryptoMoonShots": (200, reddit_body(["$PEPE moon", "PEPE frog season", "$pepe again", "BTC"])),
             "SatoshiStreetBets": (429, ""), "CryptoCurrency": (403, ""), "memecoins": (200, reddit_body([]))}
    tr, d = make(table)
    polled = tr.poll(T0, all_due=True)
    assert len(polled) == len(tr.collectors) == 8, polled
    codes = {k: v["code"] for k, v in tr.state["status"].items()}
    assert codes["reddit/SatoshiStreetBets"] == 429 and codes["reddit/CryptoCurrency"] == 403 and codes["coingecko"] == 200
    h = {x["coin"]: x for x in tr.heat(T0)}
    # PEPE: coingecko #1 (40) + 3 reddit mentions vs baseline 1/h -> 3x of 8x = 15
    assert h["PEPE"]["trend"] == 40 and h["PEPE"]["reddit"] == 15 and h["PEPE"]["score"] == 55, h["PEPE"]
    assert abs(h["BONK"]["trend"] - 37.3) < 0.1, h["BONK"]                     # coingecko #2
    assert h["BONK"]["dex"] == 5 and "boosted" in h["BONK"]["srcs"]          # dexscreener boosted
    assert h["WIF"]["dex"] == 15 and h["WIF"]["trend"] == 0                  # geckoterminal #1
    assert "PNUT" in h and h["PNUT"]["trend"] == 32                          # rank 4
    assert "BTC" not in h and "NOWH" not in h                                # 1 mention < min; not on Crypto.com
    assert tr.state["names"]["PNUT"] == "peanut the squirrel"                # learned from CoinGecko
    assert set(tr.dex_watch) == {"DEXONLY", "RUGME"} and tr.dex_watch["RUGME"]["chain"] == "solana"
    assert [x["coin"] for x in tr.heat(T0)][:2] == ["PEPE", "BONK"]
    # CSV rows and state on disk
    rows = open(f"{d}/heat.csv").read().splitlines()
    assert rows[0] == "time,coin,source,rank,mentions" and any(",PEPE,reddit/CryptoMoonShots,,3" in r for r in rows)
    assert any(",WIF,geckoterminal_1h,1," in r for r in rows), rows
    assert os.path.exists(f"{d}/state.json") and json.load(open(f"{d}/dex_watch.json"))["DEXONLY"]["n"] == 1
    # one poll per call, most overdue first; nothing due right after
    assert tr.poll(T0 + MIN) == []
    assert tr.poll(T0 + 5 * MIN) == ["dexscreener"] and tr.poll(T0 + 5 * MIN) == []
    # reddit: the same posts are not counted twice
    tr.poll(T0 + 16 * MIN, all_due=True)
    assert tr.components("PEPE", T0 + 16 * MIN)["m24"] == 3
    # sightings expire after ttl; mentions decay; last_hot / cold_hours
    assert tr.cold_hours("PEPE", T0 + 16 * MIN) == 0
    later = T0 + 3 * HOUR
    tr2 = HeatTracker(params={"dir": d, "coingecko": False, "reddit": False, "dex": False}, universe=UNI,
                      fetch=fake_fetch({}), now_ms=later)                     # reload from disk, no polling
    c = tr2.components("PEPE", later)
    assert c["trend"] == 0 and c["reddit"] == 0 and c["m24"] == 3, c
    assert abs(tr2.cold_hours("PEPE", later) - (3 - 16 / 60)) < 0.01
    # reddit velocity: 8x baseline saturates at 40; a 24h baseline lowers the ratio
    tr3, _ = make({})
    te = T0 - T0 % HOUR + HOUR - 1000                # one second before the hour ends (1h ~= this bucket)
    tr3.state["mentions"]["WIF"] = {str(te // HOUR): 8}
    assert tr3.components("WIF", te)["reddit"] == 40
    tr3.state["mentions"]["WIF"].update({str(te // HOUR - k): 4 for k in range(1, 24)})   # steady 4/h
    c = tr3.components("WIF", te)
    assert abs(c["reddit"] - 40 * (8 / 4) / 8) < 0.1 and c["m24"] == 8 + 23 * 4, c      # 2x baseline
    # excluded (stablecoin) and non-universe coins never score
    tr3.state["mentions"]["USDT"] = {str(T0 // HOUR): 50}
    assert "USDT" not in {x["coin"] for x in tr3.heat(T0)}
    print("  tracker: heat components, files, ttl    ok")


def test_self_check_and_disabled():
    tr, _ = make({"search/trending": (200, CG)}, coingecko=True, reddit=False, dex=False, cmc=True, cmc_url="")
    assert [c.name for c in tr.collectors] == ["coingecko"]                    # cmc off without a verified URL
    line = tr.self_check(T0)
    assert line == "social self-check: coingecko 200", line
    tr, _ = make({}, coingecko=False, reddit=False, dex=False)
    assert tr.self_check(T0).endswith("all sources disabled") and tr.heat(T0) == []
    tr, _ = make({"reddit.com": (0, "timed out")}, coingecko=False, dex=False)
    assert "reddit/memecoins 0" in tr.self_check(T0)
    print("  self-check line / disabled sources      ok")


# ---- strategy ---------------------------------------------------------------------------
def candles(n, price=1.0, path=None, t0=T0 - 30 * HOUR):
    """n hourly candles ending at t0 + n h; path(i) -> close multiplier."""
    out = []
    for i in range(n):
        c = price * (path(i) if path else 1.0)
        out.append({"t": t0 + i * HOUR, "o": c, "h": c * 1.01, "l": c * 0.99, "c": c, "v": 1000})
    return out


def heat_for(tr, coin, score, now):
    """Plant a CoinGecko sighting whose rank yields ~score (0..40)."""
    tr.state["sightings"][coin] = {"coingecko": {"rank": 1 + round(15 * (1 - score / 40)), "t": now}}
    tr._mark_hot(now)


def test_strategy_entries_exits():
    tr, d = make({}, enter=30, floor=20)
    st = SocialHeat(tracker_=tr, enter=30, floor=20)
    assert st.trail == 0.25 and st.max_positions == 5 and hasattr(st, "trail")   # fast_check compat
    now = T0
    st.clock = now
    data = {"PEPE": candles(30), "BONK": candles(30, path=lambda i: 0.8 if i >= 10 else 1.0),   # -20% in 24h
            "SOL": candles(30), "USDT": candles(30)}
    heat_for(tr, "PEPE", 40, now)
    heat_for(tr, "BONK", 40, now)
    heat_for(tr, "USDT", 40, now)
    heat_for(tr, "SOL", 10, now)                     # lukewarm
    sigs = {c: st.analyze(cs) for c, cs in tag(data).items()}
    assert sigs["PEPE"]["buy"] and sigs["PEPE"]["heat"] == 40 and sigs["PEPE"]["stop"] == 0.75
    assert not sigs["BONK"]["buy"] and sigs["BONK"]["change_24h"] < -0.1      # spike-and-fade guard
    assert not sigs["SOL"]["buy"] and not sigs["USDT"]["buy"]
    assert st.analyze(data["PEPE"]) and not st.analyze(data["PEPE"])["buy"]  # untagged: never buys
    assert st.analyze(candles(10, t0=T0))["change_24h"] is None
    # engine.step: buys PEPE only, sized by slot
    pf = Portfolio()
    step(pf, tag(data), st)
    assert set(pf.positions) == {"PEPE"} and abs(pf.positions["PEPE"]["cost"] - 90) < 1e-6, pf.positions
    assert pf.positions["PEPE"]["stop"] == 0.75
    # live entry between cycles from a ticker
    assert st.entry("PEPE", {"a": "1.0", "c": "0.05"}, now)[0] == 1.0
    assert st.entry("BONK", {"a": "1.0", "c": "-0.2"}, now) is None
    assert st.entry("PEPE", {"a": "abc"}, now) is None and st.entry("PEPE", {}, now) is None
    assert st.entry("PEPE", {"a": "1.0"}, now) is None                      # no 24h change -> no buy
    # trailing stop: rally to 2.0 then fall through 1.5
    up = candles(30, path=lambda i: 1 + i / 29)                              # ends at 2.0
    step(pf, tag({"PEPE": up}), st)
    assert "PEPE" in pf.positions and abs(pf.positions["PEPE"]["stop"] - 2.02 * 0.75) < 1e-9
    down = up + [dict(up[-1], t=up[-1]["t"] + HOUR, l=1.4, c=1.45)]
    step(pf, tag({"PEPE": down}), st)
    sells = [t for t in pf.trades if t["side"] == "SELL"]
    assert sells[-1]["reason"] == "trailing stop" and sells[-1]["pnl"] > 0, sells
    assert "PEPE" in pf.positions                                            # still hot: re-entered at 1.45
    # time limit: 10 days
    pf = Portfolio()
    step(pf, tag({"PEPE": candles(30)}), st)
    late = candles(30, t0=T0 + 10 * DAY)
    step(pf, tag({"PEPE": late}), st)
    assert pf.trades[-1]["reason"] == "time limit"
    # heat collapse: below floor for 12h -> sell; 11h -> hold
    pf = Portfolio()
    step(pf, tag({"PEPE": candles(30)}), st)
    tr.state["sightings"] = {}
    tr.state["last_hot"]["PEPE"] = now
    st.clock = now + 11 * HOUR
    step(pf, tag({"PEPE": candles(30, t0=T0 - 19 * HOUR)}), st)
    assert "PEPE" in pf.positions
    st.clock = now + 12 * HOUR
    step(pf, tag({"PEPE": candles(30, t0=T0 - 18 * HOUR)}), st)
    assert pf.trades[-1]["reason"].startswith("heat collapsed"), pf.trades[-1]
    assert pf.cooldown.get("PEPE", 0) > 0 or pf.trades[-1]["pnl"] >= 0
    print("  strategy: entries / trail / time / cold  ok")


# ---- file rolling -----------------------------------------------------------------------
def test_csv_rolling():
    tr, d = make({}, csv_cap_mb=0.0001)
    row = [{"time": "x", "coin": "PEPE", "source": "coingecko", "rank": 1, "mentions": ""}]
    sep = 1_764_547_200_000                          # 2025-12-01 00:00 UTC
    tr._csv(row, sep - DAY)                          # November
    tr._csv(row, sep - HOUR)
    assert tr.state["csv_month"] == "2025-11" and len(open(f"{d}/heat.csv").read().splitlines()) == 3
    tr._csv(row, sep)                                # December: November rolled aside
    assert os.path.exists(f"{d}/heat_2025-11.csv") and len(open(f"{d}/heat.csv").read().splitlines()) == 2
    for _ in range(5):                               # size cap (100 bytes here): rolled with a timestamp suffix
        tr._csv(row, sep + HOUR)
    rolled = [f for f in os.listdir(d) if f.startswith("heat_2025-12_")]
    assert rolled, os.listdir(d)
    tr.save()
    tr2 = HeatTracker(params={"dir": d, "coingecko": False, "reddit": False, "dex": False}, fetch=fake_fetch({}))
    assert tr2.state["csv_month"] == "2025-12"      # state survives reload
    shutil.rmtree(d)
    print("  heat.csv monthly / size rolling         ok")


if __name__ == "__main__":
    test_parsers()
    test_mentions()
    test_collector_backoff()
    test_tracker_heat()
    test_self_check_and_disabled()
    test_strategy_entries_exits()
    test_csv_rolling()
    print("all social tests passed")
