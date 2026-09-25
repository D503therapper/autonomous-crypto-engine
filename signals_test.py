"""Offline tests for signals.py: canned announcement payloads, synthetic candles and ticker
streams (no network; the exchanges are not reachable from the test sandbox anyway).

    python signals_test.py
"""
import json
import os
import random
import tempfile
from collections import deque

from scanner import MinuteScanner
from scanner_test import tick
from signals import (ListingNoticeReactor, PrePumpFootprint, PumpGuard, extract_tickers, is_listing,
                     parse_binance, parse_cryptocom, parse_feed, parse_upbit, score_footprint)

MIN = 60_000
HOUR = 3_600_000
T0 = 1_700_000_000_000
TMP = tempfile.mkdtemp()


def files(tag):
    return {"seen_file": f"{TMP}/{tag}_seen.json", "events_file": f"{TMP}/{tag}_events.csv"}


# ---------------------------------------------------------------------------
# canned payloads (shapes per the notes / public bots; field names to be verified live)
# ---------------------------------------------------------------------------
def cryptocom_json(rows):
    return json.dumps({"code": 0, "result": {"data": rows}}).encode()


CDC_ROW = {"id": "a1", "category": "list", "product_type": "Spot", "announced_at": T0 - 2 * MIN,
           "title": "Crypto.com Exchange lists NEWT", "content": "NEWT/USD trading opens today",
           "instrument_name": "NEWT_USD", "impacted_params": {"spot_trading_impacted": "true"}}
CDC_DERIV = dict(CDC_ROW, id="a2", product_type="Derivative", title="Crypto.com Exchange lists XYZUSD-PERP",
                 instrument_name="XYZUSD-PERP")
CDC_DELIST = dict(CDC_ROW, id="a3", category="delist", title="Delisting of OLD/USD", instrument_name="OLD_USD")

UPBIT_JSON = json.dumps({"success": True, "data": {"total_pages": 1, "notices": [
    {"id": 5001, "title": "에이브(AAVE), 알고랜드(ALGO) 신규 거래지원 안내 (KRW, BTC 마켓)", "category": "Trade",
     "listed_at": "2023-11-14T22:12:20+09:00", "first_listed_at": "2023-11-14T22:12:20+09:00"},
    {"id": 5002, "title": "썬더코어(TT) 거래지원 종료 안내", "category": "Trade",
     "listed_at": "2023-11-14T22:10:00+09:00"},
    {"id": 5003, "title": "Market Support for Sui(SUI) (KRW, BTC Market)", "category": "Trade",
     "listed_at": "2023-11-14T22:13:00+09:00"},
    {"id": 5004, "title": "[투자유의] 골렘(GLM) 유의 종목 지정 안내", "category": "Trade",
     "listed_at": "2023-11-14T22:13:00+09:00"}]}}).encode()

BINANCE_JSON = json.dumps({"code": "000000", "message": None, "data": {"catalogs": [
    {"catalogId": 48, "catalogName": "New Cryptocurrency Listing", "articles": [
        {"id": 1, "code": "c-1", "title": "Binance Will List Tanssi Network (TANSSI) With Seed Tag Applied",
         "releaseDate": T0 - 3 * MIN},
        {"id": 2, "code": "c-2", "title": "Binance Futures Will Launch USDⓈ-M FOO Perpetual Contract",
         "releaseDate": T0 - 4 * MIN},
        {"id": 3, "code": "c-3", "title": "Binance Will Delist ABC (ABC) and DEF (DEF)", "releaseDate": T0 - 5 * MIN},
        {"id": 4, "code": "c-4", "title": "Notice on Trading Halt for Maintenance", "releaseDate": T0 - 6 * MIN}]}]}}).encode()

COINBASE_ATOM = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Coinbase Exchange Status</title>
  <entry>
    <id>tag:status.exchange.coinbase.com,2005:Incident/900</id>
    <title>Trading for ABCD (ABCD) will begin on Coinbase Exchange</title>
    <published>2023-11-14T13:16:00Z</published><updated>2023-11-14T13:16:00Z</updated>
    <content type="html">ABCD-USD trading pair enabled</content>
  </entry>
  <entry>
    <id>tag:status.exchange.coinbase.com,2005:Incident/901</id>
    <title>Degraded performance on ETH-USD order book</title>
    <published>2023-11-14T13:00:00Z</published><updated>2023-11-14T13:20:00Z</updated>
  </entry>
</feed>""".encode()

KRAKEN_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
  <title>Kraken Blog</title>
  <item><title>Aave (AAVE) is available for trading!</title>
    <link>https://blog.kraken.com/product/asset-listings/aave</link>
    <guid isPermaLink="false">https://blog.kraken.com/?p=1</guid>
    <pubDate>Tue, 14 Nov 2023 22:14:00 +0000</pubDate>
    <description>Deposits are open; trading starts today.</description></item>
  <item><title>Staking rewards update for November</title>
    <guid isPermaLink="false">https://blog.kraken.com/?p=2</guid>
    <pubDate>Tue, 14 Nov 2023 20:00:00 +0000</pubDate></item>
</channel></rss>""".encode()


# ---------------------------------------------------------------------------
def test_extract_tickers():
    cases = [
        ("에이브(AAVE), 알고랜드(ALGO) 신규 거래지원 안내 (KRW, BTC 마켓)", ["AAVE", "ALGO"]),
        ("Market Support for Sui(SUI) (KRW, BTC Market)", ["SUI"]),
        ("Binance Will List Tanssi Network (TANSSI) With Seed Tag Applied", ["TANSSI"]),
        ("Binance Will List PEPE", ["PEPE"]),
        ("Crypto.com Exchange lists NEWT/USD", ["NEWT"]),
        ("Crypto.com Exchange lists ONDO_USD and JUP_USD", ["ONDO", "JUP"]),
        ("Aave (AAVE) is available for trading!", ["AAVE"]),
        ("Trading for ABCD (ABCD) will begin on Coinbase Exchange", ["ABCD"]),
        ("Assets added to the roadmap today: XYZ (XYZ)", ["XYZ"]),
        ("New trading pairs: WIF-USD and BONK-USDC", ["WIF", "BONK"]),
        # non-listings
        ("썬더코어(TT) 거래지원 종료 안내", []),
        ("[투자유의] 골렘(GLM) 유의 종목 지정 안내", []),
        ("Binance Will Delist ABC (ABC) and DEF (DEF)", []),
        ("Notice on Trading Halt for Maintenance", []),
        ("Scheduled maintenance for the XYZ-USD trading pair", []),
        ("Degraded performance on ETH-USD order book", []),
        ("Staking rewards update for November", []),
        ("XYZ (XYZ) trading suspended", []),
        ("", []), (None, []),
    ]
    for title, want in cases:
        got = extract_tickers(title)
        assert got == want, (title, got, want)
    assert extract_tickers("Crypto.com Exchange lists a new coin", "Instrument NEWT_USD goes live") == ["NEWT"]
    assert not is_listing("Binance Will Delist XYZ") and is_listing("Binance Will List XYZ (XYZ)")
    print("  ticker extraction                   ok")


def test_parsers():
    got = parse_cryptocom(cryptocom_json([CDC_ROW, CDC_DERIV, CDC_DELIST]))
    assert [r["id"] for r in got] == ["a1", "a3"], got          # derivatives dropped
    assert got[0]["t0"] == T0 - 2 * MIN and "NEWT_USD" in got[0]["title"]
    assert extract_tickers(got[0]["title"]) == ["NEWT"] and extract_tickers(got[1]["title"]) == []
    got = parse_upbit(UPBIT_JSON)
    assert [r["id"] for r in got] == ["5001", "5002", "5003", "5004"]
    assert got[0]["t0"] == 1699967540000                          # KST -> UTC ms
    assert [extract_tickers(r["title"]) for r in got] == [["AAVE", "ALGO"], [], ["SUI"], []]
    got = parse_binance(BINANCE_JSON)
    assert [r["id"] for r in got] == ["c-1", "c-2", "c-3", "c-4"] and got[0]["t0"] == T0 - 3 * MIN
    assert [extract_tickers(r["title"]) for r in got] == [["TANSSI"], [], [], []]
    got = parse_feed(COINBASE_ATOM)
    assert len(got) == 2 and got[0]["id"].endswith("Incident/900") and got[0]["t0"] == 1699967760000
    assert extract_tickers(got[0]["title"], got[0]["content"]) == ["ABCD"] and extract_tickers(got[1]["title"]) == []
    got = parse_feed(KRAKEN_RSS)
    assert [r["id"] for r in got] == ["https://blog.kraken.com/?p=1", "https://blog.kraken.com/?p=2"]
    assert got[0]["t0"] == 1700000040000 and extract_tickers(got[0]["title"], got[0]["content"]) == ["AAVE"]
    # alternative shapes: bare list / data.list / data.articles
    assert parse_cryptocom(json.dumps({"code": 0, "result": {"data": []}}).encode()) == []
    assert [r["id"] for r in parse_upbit(json.dumps({"data": {"list": [{"id": 7, "title": "x"}]}}).encode())] == ["7"]
    assert [r["id"] for r in parse_binance(json.dumps({"data": {"articles": [{"id": 9, "title": "x"}]}}).encode())] == ["9"]
    print("  source parsers                      ok")


def make_reactor(tag, responses, now=T0, **params):
    """Reactor whose fetch returns canned bytes per source url (or raises)."""
    urls = {name: f"https://{name}.test/feed" for name in responses}

    def fetch(url):
        name = url.split("//")[1].split(".")[0]
        r = responses[name]
        if isinstance(r, Exception):
            raise r
        return r() if callable(r) else r
    srcs = {n: {"url": urls.get(n, ""), "every_s": 5} for n in
            ("cryptocom", "upbit", "binance", "coinbase", "coinbase_blog", "kraken")}
    p = dict(files(tag), sources=srcs, max_sources_per_poll=6, backoff_s=(30, 600))
    p.update(params)
    return ListingNoticeReactor(params=p, fetch=fetch, now_ms=now)


def test_poll_and_backoff():
    now = T0
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        raise OSError("HTTP Error 403: Forbidden")
    resp = {"cryptocom": cryptocom_json([CDC_ROW, CDC_DELIST]), "upbit": UPBIT_JSON, "binance": flaky,
            "coinbase": b"<html>503 Service Unavailable</html>", "kraken": b""}
    rx = make_reactor("poll", resp, now=now)
    # first poll primes each source: the Upbit notices (KST 2023) are old -> nothing; the fresh
    # Crypto.com notice (2 min old, has a timestamp) fires even on the priming pass
    ev = rx.poll(now)
    assert [(e["source"], e["coins"]) for e in ev] == [("cryptocom", ["NEWT"])], ev
    assert ev[0]["t0"] == T0 - 2 * MIN and ev[0]["t_detect"] == now
    st = rx.state
    assert st["binance"]["fails"] == 1 and st["binance"]["backoff"] == 30 and st["binance"]["next"] == now + 30_000
    assert st["coinbase"]["fails"] == 1 and st["kraken"]["fails"] == 1   # malformed / empty never raise
    assert st["cryptocom"]["fails"] == 0 and st["cryptocom"]["next"] == now + 5000
    # same notices again: nothing new; failing source not retried before its backoff
    assert rx.poll(now + 6000) == [] and calls["n"] == 1
    rx.poll(now + 31_000)
    assert calls["n"] == 2 and st["binance"]["backoff"] == 60
    for _ in range(12):
        now += 601_000
        rx.poll(now)
    assert st["binance"]["backoff"] == 600 and st["binance"]["fails"] >= 10
    # a new Upbit notice with a fresh timestamp fires once; a repeat of it never fires again
    fresh = json.loads(UPBIT_JSON)
    fresh["data"]["notices"].insert(0, {"id": 6000, "title": "수이(SUI) 신규 거래지원 안내 (KRW 마켓)",
                                        "first_listed_at": (now - 60_000) // 1000})
    resp["upbit"] = json.dumps(fresh).encode()
    ev = rx.poll(now + 6000)
    assert [(e["source"], e["id"], e["coins"]) for e in ev] == [("upbit", "6000", ["SUI"])], ev
    assert rx.poll(now + 12_000) == []
    # only max_sources_per_poll sources are fetched per call; the most overdue go first
    rx2 = make_reactor("poll2", resp, now=now, max_sources_per_poll=1)
    assert len(rx2.due(now)) == 5 and rx2.poll(now) == [] and len([s for s in rx2.state.values() if s["next"]]) == 1
    print("  polling / backoff / dedupe          ok")


def test_dedupe_persistence():
    resp = {"cryptocom": cryptocom_json([CDC_ROW])}
    rx = make_reactor("persist", resp)
    assert [e["coins"] for e in rx.poll(T0)] == [["NEWT"]]
    saved = json.load(open(files("persist")["seen_file"]))
    assert saved == {"cryptocom": ["a1"]}, saved
    # restart: the same notice is remembered, a second one fires
    resp["cryptocom"] = cryptocom_json([CDC_ROW, dict(CDC_ROW, id="a9", title="Crypto.com Exchange lists JUP/USD",
                                                     instrument_name="JUP_USD", announced_at=T0 + 60_000, content="")])
    rx = make_reactor("persist", resp, now=T0 + 90_000)
    assert [e["coins"] for e in rx.poll(T0 + 90_000)] == [["JUP"]]
    assert json.load(open(files("persist")["seen_file"]))["cryptocom"] == ["a1", "a9"]
    # untimestamped notices are only primed on a source's first-ever poll, then fire when new
    resp = {"kraken": KRAKEN_RSS}
    rx = make_reactor("persist2", resp, now=T0 + 2 * HOUR)
    assert rx.poll(T0 + 2 * HOUR) == []                        # notice is 2h old: old news
    rx = make_reactor("persist2b", resp)                       # T0 is 40 s before that pubDate: fresh
    assert [e["coins"] for e in rx.poll(T0)] == [["AAVE"]]
    nots = KRAKEN_RSS.replace(b"<pubDate>Tue, 14 Nov 2023 22:14:00 +0000</pubDate>", b"")
    rx = make_reactor("persist3", {"kraken": nots})
    assert rx.poll(T0) == []                                   # priming: no timestamp -> swallowed
    nots2 = nots.replace(b"?p=1", b"?p=3").replace(b"Aave (AAVE)", b"Sui (SUI)")
    rx.fetch = lambda url: nots2
    assert [e["coins"] for e in rx.poll(T0 + 6000)] == [["SUI"]]
    # a corrupt seen file is ignored, not fatal
    with open(files("persist3")["seen_file"], "w") as f:
        f.write("{not json")
    assert make_reactor("persist3", {"kraken": nots2}).poll(T0) == []
    print("  dedupe persistence                  ok")


def stream_scanner(rows_fn, minutes, now0=T0):
    sc = MinuteScanner(params={"known_file": None}, known=("FLAT",), now_ms=now0)
    for i in range(minutes + 1):
        sc.update({"data": rows_fn(i)}, now_ms=now0 + i * MIN)
    return sc


def test_not_yet_moved_gate():
    # 30 minutes of history; the notice landed at minute 20 (t0). QUIET barely moved since, MOVED
    # is +12% since t0, HOT is only +3% since t0 but +45% in 24h, THIN trades $50k/day.
    t0 = T0 + 20 * MIN

    def rows(i):
        since = max(i - 20, 0) / 10
        return [tick("QUIET", 1.0 + 0.02 * since, 2e6), tick("MOVED", 1.0 + 0.12 * since, 2e6),
                tick("HOT", 1.0 + 0.03 * since, 2e6), tick("THIN", 1.0, 50_000), tick("WIDE", 1.0, 2e6, spread=0.03),
                tick("USDT", 1.0, 2e6)]
    sc = stream_scanner(rows, 30)
    for c in sc.last.values():
        c["c24"] = 0.05
    sc.last["HOT"]["c24"] = 0.45
    now = T0 + 30 * MIN
    rx = make_reactor("gate", {})
    ev = {"source": "upbit", "id": "1", "title": "Market Support for many", "t0": t0, "t_detect": now,
          "coins": ["QUIET", "MOVED", "HOT", "THIN", "WIDE", "NOTHERE", "USDT"]}
    cands = rx.candidates([ev], sc, now)
    assert [c["coin"] for c in cands] == ["QUIET"], cands
    q = cands[0]
    assert abs(q["move"] - 0.02) < 1e-6 and q["c24"] == 0.05 and q["latency_s"] == 600 and q["price"] == 1.02
    assert q["reason"].startswith("listing:upbit") and "QUIET" in q["text"]
    log = open(files("gate")["events_file"]).read().splitlines()
    verdict = {l.split(",")[4]: l for l in log[1:]}
    assert "already +12.0% since notice" in verdict["MOVED"] and "+45% in 24h" in verdict["HOT"]
    assert "thin" in verdict["THIN"] and "spread" in verdict["WIDE"] and "not on Crypto.com" in verdict["NOTHERE"]
    assert "stable" in verdict["USDT"] and verdict["QUIET"].endswith("Market Support for many")
    # per-source limit: Binance/Coinbase notices only tolerate +4%
    ev2 = dict(ev, source="binance", coins=["QUIET"])
    sc.last["QUIET"]["price"] = 1.06
    assert rx.candidates([ev2], sc, now) == []
    sc.last["QUIET"]["price"] = 1.03
    assert [c["coin"] for c in rx.candidates([ev2], sc, now)] == ["QUIET"]
    # notice without a timestamp: move is measured from the price at first detection
    ev3 = dict(ev, source="kraken", id="k1", t0=None, coins=["MOVED"])
    assert [c["coin"] for c in rx.candidates([ev3], sc, now)] == ["MOVED"]
    sc.last["MOVED"]["price"] *= 1.10
    assert rx.candidates([ev3], sc, now) == []
    # notice older than max_age_min is never chased
    ev4 = dict(ev, id="old", t0=now - 50 * MIN, coins=["QUIET"])
    assert rx.candidates([ev4], sc, now) == []
    # notice from before the ring buffer starts (within 2h): oldest snapshot is the reference
    assert ListingNoticeReactor.price_at(sc.hist["QUIET"], T0 - HOUR) == 1.0
    assert ListingNoticeReactor.price_at(sc.hist["QUIET"], T0 - 3 * HOUR) is None
    assert ListingNoticeReactor.price_at(deque(), T0) is None
    print("  not-yet-moved gate                  ok")


# ---------------------------------------------------------------------------
def hourly(hours, base_usd, price_path, vol_path, seed=3, now=T0):
    """Hourly candles; price_path(h)->close multiplier, vol_path(h)->USD volume multiplier."""
    rng = random.Random(seed)
    rows, prev = [], 1.0
    for h in range(hours):
        c = price_path(h) * (1 + rng.gauss(0, 0.002))
        o = prev
        hi, lo = max(o, c) * (1 + abs(rng.gauss(0, 0.001))), min(o, c) * (1 - abs(rng.gauss(0, 0.001)))
        v = base_usd * vol_path(h) * rng.uniform(0.85, 1.15)
        rows.append({"t": now - (hours - 1 - h) * HOUR, "o": o, "h": hi, "l": lo, "c": c, "v": v / c})
        prev = c
    return rows


def accumulation(h, n=240, drift=0.12, hikes=(200, 214, 228, 236)):
    """Flat for 8 days, then +12% drift over the last 48h on quiet volume with 4 volume hikes."""
    return (1.0 if h < n - 48 else 1.0 + drift * (h - (n - 48)) / 48), (
        1.0 if h < n - 48 else (4.0 if h in hikes else 0.6))


def test_footprint_scoring():
    n = 240
    acc = hourly(n, 20_000, lambda h: accumulation(h)[0], lambda h: accumulation(h)[1])
    r = score_footprint(acc)
    assert r.get("score") == 4 and r["max_score"] == 4, r
    assert 0.10 < r["ret48"] < 0.14 and r["hikes"] == 4 and r["quiet"] >= 0.8, r
    # same shape with open interest creeping up scores 5/5; flat OI scores 4/5
    assert score_footprint(acc, oi_change=0.35)["score"] == 5 and score_footprint(acc, oi_change=0.01)["score"] == 4
    # flat coin: no drift, no hikes -> low score
    flat = hourly(n, 20_000, lambda h: 1.0, lambda h: 1.0)
    assert score_footprint(flat)["score"] <= 1, score_footprint(flat)
    # single spike: +20% in one candle on 30x volume -> excluded outright
    spike = hourly(n, 20_000, lambda h: 1.2 if h >= n - 3 else 1.0, lambda h: 30.0 if h == n - 3 else 1.0)
    assert "skip" in score_footprint(spike) and "spike" in score_footprint(spike)["skip"], score_footprint(spike)
    # drift already exploded (+40% in 48h, +35% in 24h) -> excluded
    hot = hourly(n, 20_000, lambda h: 1.0 if h < n - 24 else 1.0 + 0.35 * (h - (n - 24)) / 24, lambda h: 1.0)
    assert "24h" in score_footprint(hot)["skip"]
    # too little history / too big or too thin to be a listing candidate / stables
    assert score_footprint(acc[-100:])["skip"] == "history"
    assert "out of range" in score_footprint(hourly(n, 5_000_000, lambda h: 1.0, lambda h: 1.0))["skip"]
    assert "out of range" in score_footprint(hourly(n, 5_000, lambda h: 1.0, lambda h: 1.0))["skip"]
    assert score_footprint([]) == {"skip": "history"}
    # ranking: best first, min_score respected, stables and broken coins ignored
    fp = PrePumpFootprint(params={"oi_file": None})
    weak = hourly(n, 20_000, lambda h: accumulation(h)[0], lambda h: 1.0 if h < n - 48 else 1.3,
                  seed=5)                                          # drift + rising lows, busy volume
    top = fp.rank({"ACC": acc, "FLAT": flat, "SPIKE": spike, "WEAK": weak, "USDT": acc, "BROKEN": [{"x": 1}] * 300})
    assert [r["coin"] for r in top] == ["ACC"], top
    assert top[0]["reason"].startswith("footprint 4/4") and "ACC:" in top[0]["text"]
    fp.p["min_score"] = 1
    assert [r["coin"] for r in fp.rank({"ACC": acc, "FLAT": flat, "WEAK": weak})][:2] == ["ACC", "WEAK"]
    print(f"  footprint: {top[0]['text']}   ok")


def test_footprint_oi():
    f = f"{TMP}/oi.json"
    fp = PrePumpFootprint(params={"oi_file": f})
    tk = [{"i": "BTCUSD-PERP", "oi": "1000"}, {"i": "SOL_USD-PERP", "oi": "500"}, {"i": "BTC_USD", "a": "1"},
          {"i": "PEPE-PERP", "oi": "abc"}]
    assert fp.note_oi(tk, T0) == 2 and set(fp.oi) == {"BTC", "SOL"}
    assert fp.note_oi(tk, T0 + 10 * MIN) == 0                  # not more often than every 30 min
    assert fp.oi_change("BTC", T0 + HOUR) is None              # no snapshot 22h+ old yet
    fp.note_oi([{"i": "BTCUSD-PERP", "oi": "1300"}], T0 + 24 * HOUR)
    assert abs(fp.oi_change("BTC", T0 + 24 * HOUR) - 0.30) < 1e-9
    fp2 = PrePumpFootprint(params={"oi_file": f})              # persisted across restarts
    assert abs(fp2.oi_change("BTC", T0 + 24 * HOUR) - 0.30) < 1e-9
    print("  footprint open-interest term        ok")


# ---------------------------------------------------------------------------
def buf(prices, now=T0):
    """Minute ring buffer ending at `now`: [(t, price, vv)] oldest first."""
    return deque((now - (len(prices) - 1 - i) * MIN, p, 1e6) for i, p in enumerate(prices))


def test_pump_guard():
    g = PumpGuard()
    now = T0
    assert g.check("A", now) == (True, "ok")                                       # nothing known: allow
    assert g.check("A", now, cur={"price": 1, "c24": 0.29}) == (True, "ok")
    ok, why = g.check("B", now, cur={"price": 1, "c24": 0.45})
    assert not ok and "+45% in 24h" in why
    assert not g.check("B", now + 5 * MIN, cur={"price": 1, "c24": 0.01})[0]       # blocked 30 min
    assert g.check("B", now + 31 * MIN, cur={"price": 1, "c24": 0.01})[0]
    # 24h change from hourly candles when the ticker has no `c`
    cs = [{"t": now - (30 - i) * HOUR, "c": 1.0 if i < 28 else 1.4, "o": 1, "h": 1, "l": 1, "v": 1} for i in range(31)]
    assert not g.check("C", now, candles=cs)[0] and g.check("C2", now, candles=cs[:20])[0]
    # spike-and-fade: +20% then back to +8% (gave back 60% of the move) -> reject
    rise = [1.0 + 0.20 * i / 30 for i in range(31)]
    fade = [1.20 - 0.12 * i / 29 for i in range(1, 30)]
    ok, why = g.check("D", now, cur={"price": 1.08}, buf=buf(rise + fade))
    assert not ok and "spike-and-fade" in why and "+20%" in why, why
    # +20% and still near the top (gave back 10%) -> ok; +8% spike that faded fully -> too small to matter
    assert g.check("E", now, buf=buf(rise + [1.20 - 0.02 * i / 29 for i in range(1, 30)]))[0]
    assert g.check("F", now, buf=buf([1.0 + 0.08 * i / 30 for i in range(31)] + [1.0] * 29))[0]
    # the spike must be inside the last 60 minutes; older history is ignored
    old = buf(rise + fade + [1.08] * 70)
    assert g.check("G", now, buf=old)[0]
    assert not g.check("H", now, buf=old, cur={"c24": 0.5})[0]
    assert g.check("I", now, buf=buf([1.0, 1.3]))[0]                                  # too few points
    print("  pump guard                          ok")


if __name__ == "__main__":
    test_extract_tickers()
    test_parsers()
    test_poll_and_backoff()
    test_dedupe_persistence()
    test_not_yet_moved_gate()
    test_footprint_scoring()
    test_footprint_oi()
    test_pump_guard()
    print("all signals tests passed")
