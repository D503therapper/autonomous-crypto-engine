"""Offline checks for smartmoney_study.py (no network): wallet reputation uses only earlier, resolved coins."""
import unittest

import smartmoney_study as S

H, D = 3600, 86400


def ev(k, t, lab, exit_t, net="solana"):
    return {"k": k, "t": t, "lab": lab, "exit_t": exit_t, "net": net, "ret": 1.0 if lab == "run" else -0.3}


class T(unittest.TestCase):
    def test_good_wallet_counts_only_after_the_runner_resolved(self):
        a = ev("A", 0, "run", 2 * D)                       # runner, known at day 2
        b = ev("B", 1 * D, "dud", 5 * D)                   # enters before A resolved -> smart wallet unknown
        c = ev("C", 3 * D, "run", 9 * D)                   # enters after A resolved -> smart wallet known-good
        W = {("A", 0): {"smart", "x"}, ("B", 1 * D): {"smart"}, ("C", 3 * D): {"smart", "y"}}
        rows = {r["e"]["k"]: r for r in S.signal_rows([a, b, c], W, {})}
        self.assertEqual(rows["A"]["g_pre"], 0)
        self.assertEqual(rows["B"]["g_pre"], 0)
        self.assertEqual(rows["C"]["g_pre"], 1)

    def test_same_pool_and_other_chain_never_build_reputation(self):
        a = ev("A", 0, "run", 1 * D)
        a2 = ev("A", 3 * D, "run", 9 * D)
        z = ev("Z", 0, "run", 1 * D, net="base")
        W = {("A", 0): {"w"}, ("A", 3 * D): {"w"}, ("Z", 0): {"w"}}
        rows = [r for r in S.signal_rows([a, z, a2], W, {}) if r["e"] is a2]
        self.assertEqual(rows[0]["g_pre"], 0)

    def test_dud_heavy_wallet_is_bad_not_good(self):
        evs = [ev("R", 0, "run", D), ev("D1", 0, "dud", D), ev("D2", 0, "dud", D), ev("N", 2 * D, "dud", 9 * D)]
        W = {(e["k"], e["t"]): {"w"} for e in evs}
        r = [r for r in S.signal_rows(evs, W, {}) if r["e"]["k"] == "N"][0]
        self.assertEqual((r["g_pre"], r["b_pre"]), (0, 1))

    def test_bot_like_wallet_dropped(self):
        evs = [ev(f"P{i}", 0, "run", D) for i in range(8)] + [ev("N", 2 * D, "run", 9 * D)]
        W = {(e["k"], e["t"]): {"bot", f"u{e['k']}"} for e in evs}
        r = [r for r in S.signal_rows(evs, W, {}) if r["e"]["k"] == "N"][0]
        self.assertEqual(r["g_pre"], 0)                    # "bot" is in all 8 prior lists -> dropped


if __name__ == "__main__":
    unittest.main()
