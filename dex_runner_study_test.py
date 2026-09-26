"""Small offline checks for dex_runner_study.py (no network): rolling windows, grid, labels, engine-exit simulation."""
import math
import random
import unittest
from array import array

import dex_runner_study as S
from dex_exit_study import HOUR


def brute_max(a, w, fwd):
    out = []
    for i in range(len(a)):
        seg = a[i + 1:i + 1 + w] if fwd else a[max(0, i - w + 1):i + 1]
        out.append(max(seg) if seg else float("nan"))
    return out


def bars(closes, t0=472_222 * HOUR, vol=1000.0):
    return [[t0 + i * HOUR, c, c * 1.02, c * 0.98, c, vol] for i, c in enumerate(closes)]


def pool(closes, dead=False, created=None, **kw):
    b = bars(closes)
    p = {"net": "solana", "pool": "x", "token": "abcpump", "created": created or b[0][0], "sym": "T", "ref_reserve": 500_000.0,
         "ref_price": closes[0], "fdv": 1e6, "price_now": closes[-1]}
    p.update(kw)
    P = S.Pool(p, S.hourly_grid(b), b[-1][0] + 400 * HOUR, dead)
    P.derive()
    return P


class T(unittest.TestCase):
    def test_rolling(self):
        rng = random.Random(1)
        a = array("d", [rng.random() for _ in range(300)])
        for w in (1, 5, 24):
            for fwd in (False, True):
                got, exp = S.roll_max(a, w, fwd), brute_max(list(a), w, fwd)
                for g, e in zip(got, exp):
                    self.assertTrue((g != g and e != e) or abs(g - e) < 1e-12, (w, fwd))
                got = S.roll_min(a, w, fwd)
                exp = [-x for x in brute_max([-x for x in a], w, fwd)]
                for g, e in zip(got, exp):
                    self.assertTrue((g != g and e != e) or abs(g - e) < 1e-12)

    def test_grid_fills_gaps(self):
        b = bars([1, 2, 3, 4, 5] * 8)
        del b[3:6]                                   # three missing hours
        t0, O, H, L, C, V = S.hourly_grid(b)
        self.assertEqual(len(C), 40)
        self.assertEqual((C[3], C[4], C[5], V[4]), (3.0, 3.0, 3.0, 0.0))

    def test_labels_and_features(self):
        closes = [1.0] * 30 + [1.0 + 0.1 * i for i in range(30)] + [4.0] * 20 + [12.0] + [4.0] * 250
        P = pool(closes)
        lab = P.labels(29)
        self.assertAlmostEqual(lab["m1"], (1.0 + 0.1 * 23) * 1.02, 6)     # highs are close * 1.02
        self.assertGreaterEqual(lab["m3"], 4.0)
        self.assertAlmostEqual(lab["m7"], 12.0 * 1.02, 6)
        self.assertEqual(lab["rug7"], 0.0)
        f = P.features(29)
        self.assertEqual(f["pump"], 1.0)
        self.assertAlmostEqual(f["age_h"], 30.0)
        self.assertAlmostEqual(f["ch1"], 0.0)
        self.assertAlmostEqual(f["vol24"], 24 * 1000.0)
        self.assertAlmostEqual(f["v1_rel"], 1.0)
        self.assertAlmostEqual(f["mcap"], 1e6 / 4.0 * 1.0)
        self.assertIsNone(P.labels(len(closes) - 100))                  # window cut short, pool alive

    def test_rug_label_and_dead_pool(self):
        closes = [1.0] * 40 + [0.05] * 200                                 # -95% crash, no recovery
        P = pool(closes)
        self.assertEqual(P.labels(30)["rug7"], 1.0)
        self.assertEqual(P.labels(10)["rug7"], 1.0)
        D = pool([1.0] * 60, dead=True)
        self.assertEqual(D.labels(50)["rug7"], 1.0)                        # trades stop for good
        self.assertIsNotNone(D.labels(58))

    def test_simulate_engine_exit(self):
        # pinned to the exit these cases were written for (config.DEX["exit"] changed on 2026-09-26)
        old = dict(S.EXIT)
        S.EXIT.update({"trail": 0.95, "trail_steps": [(3.0, 0.60)], "max_hold_days": 14, "runner_at_limit": (1.0, 0.50)})
        try:
            self._cases()
        finally:
            S.EXIT.clear()
            S.EXIT.update(old)

    def _cases(self):
        liq = 500_000.0
        # 1. flat for 14 days -> time exit near entry
        P = pool([1.0] * 400)
        r, t, pk, opn, rug = S.simulate(P, 5, liq)
        self.assertAlmostEqual((t - (P.t0 + 6 * HOUR)) / HOUR, 14 * 24)
        self.assertLess(r, 0)
        self.assertGreater(r, -0.05)
        # 2. 3x then a slide: the 60% trail from the peak (3.06 * 0.4 = 1.22) sells at the 1.2 open
        P = pool([1.0] * 5 + [3.0] * 5 + [2.0, 1.5, 1.3, 1.2] + [0.9] * 400)
        r, t, pk, opn, rug = S.simulate(P, 2, liq)
        self.assertGreater(r, 0.1)
        self.assertLess(t, P.t0 + 20 * HOUR)
        # 3. runner at the 14-day limit (>= 2x) keeps riding, then sells on the 50% trail
        P = pool([1.0] * 5 + [2.5] * 400 + [2.0, 1.6, 1.3, 1.2] + [1.0] * 100)   # 50% trail from 2.55 = 1.275
        r, t, pk, opn, rug = S.simulate(P, 2, liq)
        self.assertGreater((t - P.t0) / HOUR, 14 * 24 + 5)
        self.assertGreater(r, 0.2)
        # 4. rug -> -95%
        P = pool([1.0] * 5 + [0.03] * 300)
        r, t, pk, opn, rug = S.simulate(P, 2, liq)
        self.assertTrue(rug)
        self.assertAlmostEqual(r, -0.95 * (1 - S.cost(S.SIZE, liq)) - S.cost(S.SIZE, liq), 3)

    def test_score_and_auc(self):
        self.assertAlmostEqual(S.auc([1, 2, 3, 4], [0, 0, 1, 1]), 1.0)
        self.assertAlmostEqual(S.auc([1, 1, 1, 1], [0, 0, 1, 1]), 0.5)
        pts = [{"k": str(i % 7), "f": float(i), "run2": float(i >= 50), "run5": 0.0, "run10": 0.0, "rug7": 0.0, "m1": 1.0} for i in range(100)]
        S.FEATS, S.LIVE = ["f"], {"f": "x"}
        rules, tables = S.build_score(pts, pts[:50] + pts[50:], pts, min_n=5)
        self.assertEqual(len(rules), 1)
        self.assertEqual(S.score_of({"f": 90.0}, rules), 1)
        self.assertEqual(S.score_of({"f": 1.0}, rules), 0)


if __name__ == "__main__":
    unittest.main()
