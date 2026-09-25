"""Offline tests for scanner.MinuteScanner with synthetic ticker streams (no network).

    python scanner_test.py
"""
import random

from scanner import MinuteScanner, describe, excluded

MIN = 60_000
HOUR = 3_600_000
T0 = 1_700_000_000_000
DAY_USD = 2_000_000          # a normally-traded coin: $2M / 24h
NORMAL_RATE = DAY_USD / 1440  # USD per minute


def tick(coin, price, vv=DAY_USD, spread=0.002, t=None):
    """One ticker row in Crypto.com's public/get-tickers shape (strings, like the API)."""
    return {"i": f"{coin}_USD", "a": f"{price:.8f}", "b": f"{price * (1 - spread / 2):.8f}",
            "k": f"{price * (1 + spread / 2):.8f}", "v": f"{vv / price:.4f}", "vv": f"{vv:.2f}",
            "c": "0.01", "h": f"{price * 1.02:.8f}", "l": f"{price * 0.98:.8f}", "t": t or 0}


def stream(minutes, coins_fn, known=("FLAT",), params=None):
    """Feed `minutes` one-minute snapshots. coins_fn(i) -> list of ticker rows at minute i."""
    sc = MinuteScanner(params=dict({"known_file": None}, **(params or {})), known=known, now_ms=T0)
    for i in range(minutes + 1):
        sc.update({"data": coins_fn(i)}, now_ms=T0 + i * MIN)
    return sc


def by_coin(sigs):
    return {s["coin"]: s for s in sigs}


def flat(i):
    return 1.0, DAY_USD


def grind(i):          # +3% over 60 minutes, steady volume
    return 1.0 + 0.03 * min(i, 60) / 60, DAY_USD


def pump(i, start=40, length=20, gain=0.10, vol_mult=6.0):
    """Flat until `start`, then +gain over `length` minutes on vol_mult x normal volume."""
    k = min(max(i - start, 0), length)
    price = 1.0 * (1 + gain * k / length)
    vv = DAY_USD + (vol_mult - 1) * NORMAL_RATE * k     # 24h total swells by the extra volume
    return price, vv


def test_flat_and_grind():
    def rows(i):
        return [tick("FLAT", *flat(i)), tick("GRIND", *grind(i))]
    sc = stream(90, rows, known=("FLAT", "GRIND"))
    sigs = sc.signals()
    assert sigs == [], sigs
    assert len(sc.hist["FLAT"]) == 91
    print("  flat / slow grind: no signal        ok")


def test_pump_fires():
    def rows(i):
        return [tick("FLAT", *flat(i)), tick("PUMP", *pump(i))]
    sc = stream(59, rows, known=("FLAT", "PUMP"))
    s = by_coin(sc.signals()).get("PUMP")
    assert s and s["kind"] == "mover", sc.signals()
    assert s["rise"] >= 0.05 and s["vol_ratio"] >= 3, s
    assert s["window_min"] in (15, 30), s
    assert abs(s["spread"] - 0.002) < 1e-6
    # during the pump the 15-min tier should fire once >= 5% is on the board (minute ~50)
    sc2 = stream(52, rows, known=("FLAT", "PUMP"))
    assert "PUMP" in by_coin(sc2.signals())
    sc3 = stream(45, rows, known=("FLAT", "PUMP"))            # only +2.5% so far: too early
    assert "PUMP" not in by_coin(sc3.signals())
    # long after the pump the window no longer contains the rise
    sc4 = stream(59 + 90, rows, known=("FLAT", "PUMP"))
    assert sc4.signals() == [], sc4.signals()
    print(f"  sharp pump: {describe(s)}   ok")


def test_pump_without_volume_is_ignored():
    def rows(i):
        p, _ = pump(i, vol_mult=1.5)                         # price jumps, volume barely moves
        return [tick("QUIET", p, DAY_USD + 0.5 * NORMAL_RATE * min(max(i - 40, 0), 20))]
    sc = stream(59, rows, known=("QUIET",))
    assert sc.signals() == [], sc.signals()
    print("  pump on normal volume: no signal    ok")


def test_thin_and_wide_spread_filtered():
    def rows(i):
        p, vv = pump(i)
        return [tick("WIDE", p, vv, spread=0.03),             # 3% spread
                tick("THIN", p, vv * 0.02),                   # $40k/day
                tick("NOBOOK", p, vv, spread=0.0)]            # bid == ask == last: spread 0 ok
    sc = stream(59, rows, known=("WIDE", "THIN", "NOBOOK"))
    got = by_coin(sc.signals())
    assert "WIDE" not in got and "THIN" not in got, got
    assert "NOBOOK" in got
    # missing bid/ask -> untradable by default, allowed when spread_required=False
    def rows2(i):
        p, vv = pump(i)
        t = tick("NOQUOTE", p, vv)
        del t["b"], t["k"]
        return [t]
    assert stream(59, rows2, known=("NOQUOTE",)).signals() == []
    assert "NOQUOTE" in by_coin(stream(59, rows2, known=("NOQUOTE",), params={"spread_required": False}).signals())
    print("  wide spread / thin volume filtered  ok")


def test_stablecoins_and_wrapped_filtered():
    def rows(i):
        p, vv = pump(i)
        return [tick(c, p, vv) for c in ("USDT", "USDC", "DAI", "FDUSD", "TUSD", "PYUSD", "USDS",
                                         "USD1", "GUSD", "EURC", "WBTC", "WETH", "BTC3L", "ETHUP")]
    sc = stream(59, rows, known=())
    assert sc.signals() == [], sc.signals()
    for c in ("AUDIO", "PEPE", "SOL", "SUI", "USELESS", "EUL", "LUNA"):
        assert not excluded(c), c
    print("  stablecoins / wrapped / leveraged   ok")


def test_new_listing():
    def rows(i):
        out = [tick("FLAT", *flat(i)), tick("OLDCOIN", 2.0, 5_000)]  # thin, present from the start
        if i >= 40:
            out.append(tick("NEWCOIN", 0.5, 10_000))                    # tiny volume, just listed
        return out
    sc = MinuteScanner(params={"known_file": None}, known=("FLAT",), now_ms=T0)
    fired = {}
    for i in range(61):
        new = sc.update({"data": rows(i)}, now_ms=T0 + i * MIN)
        if new:
            fired[i] = new
    assert fired == {40: ["NEWCOIN"]}, fired                       # OLDCOIN was seen at start
    got = by_coin(sc.signals())
    assert set(got) == {"NEWCOIN"} and got["NEWCOIN"]["kind"] == "new_listing", got
    assert got["NEWCOIN"]["window_min"] == 20 and sc.signals()[0]["coin"] == "NEWCOIN"
    # a new stablecoin listing is not a signal; after listing_min it stops being reported
    sc.update({"data": rows(60) + [tick("USDX", 1.0, 100)]}, now_ms=T0 + 61 * MIN)
    assert set(by_coin(sc.signals())) == {"NEWCOIN"}
    assert sc.signals(now_ms=T0 + (40 + 181) * MIN) == []
    # coins listed in data/known_listings.json are not "new"
    import json, tempfile, os
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(["FLAT", "NEWCOIN"], f)
    sc = MinuteScanner(params={"known_file": path}, now_ms=T0)
    sc.update({"data": rows(0)}, now_ms=T0)
    assert sc.update({"data": rows(40)}, now_ms=T0 + 40 * MIN) == []
    os.unlink(path)
    print("  new listing detected                ok")


def candles(hours, hourly_usd, last_gain=0.0, last_vol_mult=1.0, now=None, seed=1):
    """Hourly candles oldest-first, opening on the hour; the final (in-progress) candle
    opened at the last hour boundary before `now` and can carry a jump."""
    rng = random.Random(seed)
    now = now or T0
    rows, price = [], 1.0
    for h in range(hours):
        t = now - now % HOUR - (hours - 1 - h) * HOUR
        o = price
        if h == hours - 1:
            price = o * (1 + last_gain)
            v = hourly_usd * last_vol_mult
        else:
            price = o * (1 + rng.gauss(0, 0.004))
            v = hourly_usd * rng.uniform(0.7, 1.3)
        rows.append({"t": t, "o": o, "h": max(o, price), "l": min(o, price), "c": price, "v": v / price})
    return rows


def test_warm_start():
    now = T0 - T0 % HOUR + 55 * MIN        # 55 minutes into the current hour
    hourly = DAY_USD / 24
    data = {"HOT": candles(8 * 24, hourly, last_gain=0.15, last_vol_mult=5.0, now=now),
            "COLD": candles(8 * 24, hourly, now=now),
            "USDT": candles(8 * 24, hourly, last_gain=0.15, last_vol_mult=5.0, now=now)}
    sc = MinuteScanner(params={"known_file": None}, now_ms=now)
    sc.warm_start(data, now_ms=now)
    assert "USDT" not in sc.hist and 7 <= len(sc.hist["HOT"]) <= 8   # ~6h of history + current
    assert abs(sc.warm["COLD"]["rate"] - hourly / 60) < hourly / 60 * 0.15
    # first ticker after the restart: signal available immediately from the 60-min tier
    def rows():
        return [tick(c, data[c][-1]["c"], DAY_USD) for c in data]
    sc.update({"data": rows()}, now_ms=now)
    got = by_coin(sc.signals())
    assert set(got) == {"HOT"}, got
    s = got["HOT"]
    assert 55 <= s["window_min"] <= 60 and s["rise"] > 0.12 and 3 <= s["vol_ratio"] <= 8, s
    # warm-started coins that were in the candle set are not "new listings"
    assert sc.update({"data": rows()}, now_ms=now + MIN) == []
    # without warm start the same single tick gives nothing (no history yet)
    sc2 = MinuteScanner(params={"known_file": None}, now_ms=now)
    sc2.update({"data": rows()}, now_ms=now)
    assert sc2.signals() == []
    print(f"  warm start: {describe(s)}   ok")


def test_ranking_and_shapes():
    def rows(i):
        return [tick("BIG", *pump(i, gain=0.20, vol_mult=8)), tick("SMALL", *pump(i, gain=0.10)),
                tick("FLAT", *flat(i))] + ([tick("LISTED", 1.0, 1000)] if i >= 58 else [])
    sc = stream(59, rows, known=("BIG", "SMALL", "FLAT"))
    sigs = sc.signals()
    assert [s["coin"] for s in sigs] == ["LISTED", "BIG", "SMALL"], sigs
    keys = {"coin", "kind", "rise", "window_min", "vol_ratio", "price", "spread", "score"}
    assert all(keys <= set(s) for s in sigs)
    # ring buffer bounded to history_min (+ slack); also accepts a bare list of tickers
    sc = MinuteScanner(params={"known_file": None, "history_min": 30}, now_ms=T0)
    for i in range(100):
        sc.update([tick("FLAT", 1.0)], now_ms=T0 + i * MIN)
    assert len(sc.hist["FLAT"]) == 35
    # missing / odd fields never crash
    sc.update([{"i": "X_USD"}, {"i": "Y_USD", "a": "abc"}, {"i": "Z_USDT", "a": "1"}, {"i": "W_USD", "a": "2"}],
              now_ms=T0 + 101 * MIN)
    assert set(sc.last) == {"W"} and sc.signals() == []
    print("  ranking / field shapes / bounds     ok")


if __name__ == "__main__":
    test_flat_and_grind()
    test_pump_fires()
    test_pump_without_volume_is_ignored()
    test_thin_and_wide_spread_filtered()
    test_stablecoins_and_wrapped_filtered()
    test_new_listing()
    test_warm_start()
    test_ranking_and_shapes()
    print("all scanner tests passed")
