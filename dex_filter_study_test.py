"""Offline checks for dex_filter_study.py (no network): the filters, the variant trade loop, the pool cache."""
import os
import tempfile
import unittest

import dex_filter_study as S
import dex_runner_study_test as RT
from dex_exit_study import HOUR

V = {name: allow for name, _, allow in S.VARIANTS}
GENO = {"age_h": 6.9, "liq": 104_465, "ch6": 2.58, "ch24": 18.3}


class T(unittest.TestCase):
    def test_geno_is_skipped_by_every_filter_but_base(self):
        self.assertTrue(V[S.VARIANTS[0][0]](GENO))
        for name, _, allow in S.VARIANTS[1:]:
            self.assertEqual(allow(GENO), name == "a) skip 6h > +300%", name)      # GENO's 6h was +258%

    def test_unknown_values_pass(self):
        f = {"age_h": None, "liq": None, "ch6": None, "ch24": float("nan")}
        for name, _, allow in S.VARIANTS:
            self.assertTrue(allow(f), name)

    def test_thresholds(self):
        self.assertTrue(V["a) skip 6h > +200%"]({"ch6": 2.0}))
        self.assertFalse(V["a) skip 6h > +200%"]({"ch6": 2.01}))
        young = V["d) skip age<24h & 6h>+150%"]
        self.assertFalse(young({"age_h": 10, "ch6": 1.6}))
        self.assertTrue(young({"age_h": 30, "ch6": 5.0}))
        self.assertTrue(young({"age_h": 10, "ch6": 1.4}))
        self.assertFalse(V["e) liq floor $150k"]({"liq": 149_000}))

    def test_variant_loop_delays_instead_of_blacklisting(self):
        # young pool: +300% in 6h at hour 8 (skipped by 'a) 6h > +200%'), then +10% hours later on a calm 6h window
        closes = [1.0] * 5 + [3.5] + [3.5] * 10 + [3.9] + [4.0] * 400
        b = RT.bars(closes, vol=20_000.0)
        p = {"net": "solana", "pool": "x", "token": "xpump", "created": b[0][0], "sym": "T", "ref_reserve": 2e6,
             "ref_price": 1.0, "fdv": 1e6, "price_now": closes[-1]}
        P = S.Pool(p, S.hourly_grid(b), b[-1][0] + 400 * HOUR, False)
        P.derive()
        P.key = "solana:x"
        tr, rs = S.run_variants([P], 0, P.now)
        base, a200 = tr[S.VARIANTS[0][0]], tr["a) skip 6h > +200%"]
        self.assertTrue(base and a200)
        self.assertGreater(a200[0]["t0"], base[0]["t0"])
        self.assertLessEqual(a200[0]["ch6"], 2.0)

    def test_cache_roundtrip(self):
        closes = [1.0, 1.2, 1.5, 1.4] * 20
        P = RT.pool(closes)
        P.key = "solana:abcpump"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json.gz")
            S.dump_pools(path, [P])
            Q = S.load_pools(path)[0]
        self.assertEqual((Q.n, Q.key, Q.dead), (P.n, P.key, P.dead))
        self.assertAlmostEqual(Q.C[5], P.C[5], 5)

    def test_live_fires(self):
        self.assertTrue(S.live_fires({"ch1": 0.22, "b1": 1573, "s1": 648}))
        self.assertFalse(S.live_fires({"ch1": 0.22, "b1": 100, "s1": 90}))
        self.assertFalse(S.live_fires({"ch1": 0.05, "b1": 100, "s1": 1}))


if __name__ == "__main__":
    unittest.main()
