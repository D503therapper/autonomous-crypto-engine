"""Offline checks for tools/wallet_tracker.py (fake fetches, fake clock; no network)."""
import gzip
import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import wallet_tracker as W  # noqa: E402

NOW = 1790600000
TOK = "8J69rbLTzWWgUJziFY8jeu5tDwEPBwUz4pKBMr5rpump"
SOL = "So11111111111111111111111111111111111111112"


def trade(i, ts, kind="buy", wallet="w1", tok=TOK):
    buy = kind == "buy"
    return {"id": f"solana_1_tx{i}_0_{ts}", "type": "trade", "attributes": {
        "block_timestamp": W.utc(ts), "tx_hash": f"tx{i}", "tx_from_address": wallet, "kind": kind,
        "from_token_address": SOL if buy else tok, "to_token_address": tok if buy else SOL,
        "price_from_in_usd": "120.0" if buy else "0.0025", "price_to_in_usd": "0.0025" if buy else "120.0",
        "volume_in_usd": "12.5"}}


def sid(i, ts):
    return hashlib.sha1(f"solana_1_tx{i}_0_{ts}".encode()).hexdigest()[:12]


def body(trades):
    return json.dumps({"data": trades})


def cand(pool="P1", chain="solana", held=False, passed_t=None, token=TOK):
    return {"chain": chain, "pool": pool, "token": token, "sym": "X", "held": held, "passed_t": passed_t, "seen_t": NOW}


class Clock:
    def __init__(self, t=NOW):
        self.t = t
        self.sleeps = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


class T(unittest.TestCase):
    def test_parse_buy_and_sell(self):
        rows = W.parse_trades(body([trade(1, NOW, "buy"), trade(2, NOW + 5, "sell", "w2")]), cand())
        self.assertEqual([(r["side"], r["wallet"], r["token"], r["price"], r["usd"]) for _, _, r in rows],
                         [("buy", "w1", TOK, "0.0025", "12.50"), ("sell", "w2", TOK, "0.0025", "12.50")])
        self.assertEqual(rows[0][2]["time"], W.utc(NOW))
        self.assertEqual(rows[0][2]["tx"], "tx1")

    def test_side_follows_screened_token_when_it_is_the_quote(self):
        t = trade(1, NOW, "buy")                   # GT says "buy" of the other token: we SOLD ours
        a = t["attributes"]
        a["from_token_address"], a["to_token_address"] = TOK, SOL
        a["price_from_in_usd"], a["price_to_in_usd"] = "0.003", "120"
        (_, _, r), = W.parse_trades(body([t]), cand())
        self.assertEqual((r["side"], r["token"], r["price"]), ("sell", TOK, "0.003"))

    def test_dust_not_logged_and_tx_cut(self):
        small = trade(1, NOW)
        small["attributes"]["volume_in_usd"] = "3.2"
        long_tx = trade(2, NOW + 1)
        long_tx["attributes"]["tx_hash"] = "x" * 88
        clk = Clock()
        state = {}
        rows, st = W.run({"solana:P1": cand("P1")}, state, lambda u: (200, body([small, long_tx])), clk.sleep, clk)
        self.assertEqual((st["new"], st["logged"]), (2, 1))
        self.assertEqual(rows[0]["tx"], "x" * W.TX_CHARS)
        self.assertEqual(len(state["seen"]), 2)                            # the dust trade is still deduped

    def test_rotate_big_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "wallet_trades.csv.gz")
            self.assertIsNone(W.rotate(p, NOW))
            with open(p, "wb") as f:
                f.write(b"x" * 2000)
            self.assertIsNone(W.rotate(p, NOW, max_mb=0.01))
            dst = W.rotate(p, NOW, max_mb=0.001)
            self.assertTrue(dst.endswith("wallet_trades_20260928.csv.gz") and os.path.exists(dst))
            self.assertFalse(os.path.exists(p))
            with open(p, "wb") as f:
                f.write(b"x" * 2000)
            self.assertTrue(W.rotate(p, NOW, max_mb=0.001).endswith("_20260928_2.csv.gz"))

    def test_parse_skips_malformed(self):
        bad = trade(1, NOW)
        del bad["attributes"]["tx_from_address"]
        self.assertEqual(W.parse_trades(body([bad, {"attributes": {}}]), cand()), [])
        self.assertEqual(W.parse_trades("not json", cand()), [])

    def test_dedupe_across_polls(self):
        c, st, seen = cand(), {}, {}
        first = W.new_trades(W.parse_trades(body([trade(1, NOW), trade(2, NOW + 10)]), c), st, seen)
        self.assertEqual(len(first), 2)
        second = W.new_trades(W.parse_trades(body([trade(1, NOW), trade(2, NOW + 10), trade(3, NOW + 10),
                                                   trade(4, NOW + 20)]), c), st, seen)
        self.assertEqual([r["tx"] for r in second], ["tx3", "tx4"])
        # after the seen list is lost, the high-water mark still drops trades older than it
        third = W.new_trades(W.parse_trades(body([trade(1, NOW), trade(4, NOW + 20)]), c), st, {})
        self.assertEqual([r["tx"] for r in third], ["tx4"])

    def test_candidates_from_screen_and_portfolio(self):
        screen = [
            {"time": "2026-09-28 08:42", "chain": "solana", "symbol": "A", "address": "ta", "pair": "pa", "verdict": "REJECT"},
            {"time": "2026-09-28 09:00", "chain": "solana", "symbol": "A", "address": "ta", "pair": "pa", "verdict": "PASS"},
            {"time": "2026-09-20 09:00", "chain": "base", "symbol": "OLD", "address": "to", "pair": "po", "verdict": "PASS"},
            {"time": "2026-09-28 09:00", "chain": "tron", "symbol": "T", "address": "tt", "pair": "pt", "verdict": "PASS"},
            {"time": "2026-09-28 09:00", "chain": "ethereum", "symbol": "E", "address": "te", "pair": "pe", "verdict": "UNREACHABLE"},
        ]
        port = {"positions": {"H@base": {"chain": "base", "pair": "ph", "addr": "th", "sym": "H"}}}
        now = W.parse_iso("2026-09-28 10:00")
        c = W.candidates(screen, port, now)
        self.assertEqual(sorted(c), ["base:ph", "ethereum:pe", "solana:pa"])
        self.assertEqual(c["solana:pa"]["passed_t"], W.parse_iso("2026-09-28 09:00"))
        self.assertTrue(c["base:ph"]["held"])

    def test_selection_prioritises_held_passed_and_stale(self):
        cands = {"s:held": cand("held", held=True), "s:pass": cand("pass", passed_t=NOW - 3600),
                 "s:new": cand("new"), "s:fresh": cand("fresh")}
        state = {"pools": {"s:held": {"polled": NOW - 1800}, "s:pass": {"polled": NOW - 1800},
                           "s:new": {"polled": NOW - 5 * 3600}, "s:fresh": {"polled": NOW - 600}}}
        order = [c["key"] for c in W.select(cands, state, NOW, n=4)]
        self.assertEqual(order, ["s:new", "s:held", "s:pass", "s:fresh"])
        self.assertEqual([c["key"] for c in W.select(cands, {"pools": {}}, NOW, n=2)], ["s:held", "s:pass"])
        self.assertEqual(len(W.select({f"s:{i}": cand(str(i)) for i in range(40)}, {}, NOW)), W.MAX_POOLS)

    def test_run_spaces_calls_backs_off_on_429_and_logs(self):
        clk = Clock()
        replies = {"P1": [(429, ""), (200, body([trade(1, NOW - 60)]))], "P2": [(200, body([trade(2, NOW - 30, "sell")]))]}
        calls = []

        def get(url):
            pool = url.split("/pools/")[1].split("/")[0]
            calls.append((pool, clk()))
            clk.t += 0.5
            return replies[pool].pop(0)

        state = {}
        rows, st = W.run({"solana:P1": cand("P1", held=True), "solana:P2": cand("P2")}, state, get, clk.sleep, clk)
        self.assertEqual((st["polled"], st["429"], st["new"], st["calls"]), (2, 1, 2, 3))
        self.assertIn(W.BACKOFF[0], clk.sleeps)
        self.assertGreaterEqual(calls[2][1] - calls[1][1], W.GAP)         # gap between different pools
        self.assertEqual(state["pools"]["solana:P1"]["polled"], int(calls[1][1] + 0.5))
        self.assertIn(sid(1, NOW - 60), state["seen"])
        self.assertEqual(st["codes"], "429,200,200")
        self.assertEqual(st["gap"], W.GAP * 1.5)                           # later calls spaced wider after a 429

    def test_run_gives_up_after_repeated_429(self):
        clk = Clock()
        rows, st = W.run({"solana:P1": cand("P1")}, {}, lambda u: (429, ""), clk.sleep, clk)
        self.assertEqual((st["polled"], st["429"], st["calls"]), (0, len(W.BACKOFF) + 1, len(W.BACKOFF) + 1))
        self.assertEqual(rows, [])

    def test_run_stops_at_time_budget(self):
        clk = Clock()

        def slow(url):
            clk.t += 60
            return 200, body([])

        cands = {f"solana:P{i}": cand(f"P{i}") for i in range(20)}
        rows, st = W.run(cands, {}, slow, clk.sleep, clk, budget=300)
        self.assertTrue(st["budget_stop"])
        self.assertLess(st["polled"], 20)
        self.assertLessEqual(clk.t - NOW, 300 + 60)

    def test_append_rows_multi_member_gzip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.csv.gz")
            _, _, r1 = W.parse_trades(body([trade(1, NOW)]), cand())[0]
            _, _, r2 = W.parse_trades(body([trade(2, NOW + 1)]), cand())[0]
            W.append_rows(p, [r1])
            size1 = os.path.getsize(p)
            with open(p, "rb") as f:
                head = f.read()
            W.append_rows(p, [r2])
            W.append_rows(p, [])
            with open(p, "rb") as f:
                self.assertTrue(f.read().startswith(head))                 # earlier bytes never change
            self.assertGreater(os.path.getsize(p), size1)
            lines = gzip.open(p, "rt").read().splitlines()
            self.assertEqual(lines[0], ",".join(W.COLS))
            self.assertEqual(len(lines), 3)

    def test_state_roundtrip_and_seen_cap(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            self.assertEqual(W.load_state(p), {"pools": {}, "seen": []})
            clk = Clock()
            state = {"seen": [f"x{i}" for i in range(W.SEEN_CAP)]}
            W.run({"solana:P1": cand("P1")}, state, lambda u: (200, body([trade(9, NOW)])), clk.sleep, clk)
            self.assertEqual(len(state["seen"]), W.SEEN_CAP)
            self.assertEqual(state["seen"][-1], sid(9, NOW))
            W.save_state(p, state)
            self.assertEqual(W.load_state(p)["seen"][-1], state["seen"][-1])


if __name__ == "__main__":
    unittest.main()
