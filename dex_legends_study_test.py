"""Offline checks for dex_legends_study.py (no network): the live exit, the add-ons, entry and holder replay."""
import unittest

import dex_legends_study as S
from dex_exit_study import DAY, HOUR

T0 = 1_700_000_000 // HOUR * HOUR


def ser(closes, vol=1e6, rug=None, dead=False):
    b = [[T0 + i * HOUR, c, c, c, c, vol] for i, c in enumerate(closes)]
    for i in range(1, len(b)):
        b[i][1] = closes[i - 1]
        b[i][2], b[i][3] = max(closes[i - 1], closes[i]), min(closes[i - 1], closes[i])
    return S.Ser(b, HOUR, "T", "legend", "T", launch=T0, rug=rug, dead_end=dead)


def rule(prot=(3.0, 0.60), rt=0.50, cap=None, tps=()):
    return {"prot": prot, "rt": rt, "cap": cap, "tps": tps}


H14 = 14 * 24


class T(unittest.TestCase):
    def test_live_rule_matches_config(self):
        self.assertEqual(S.LIVE_RULE["prot"], (3.0, 0.60))
        self.assertEqual(S.LIVE_RULE["rt"], 0.50)

    def test_protection_trail_after_3x(self):
        c = [1.0] + [1.0 + 3.0 * i / 50 for i in range(1, 51)] + [4.0 - 0.1 * i for i in range(1, 30)]
        x = S.simulate(ser(c), 0, rule(), log=True)
        self.assertAlmostEqual(x["sells"][-1][2], 1.6, delta=0.11)     # 60% below the 4x peak
        self.assertIn("protection", x["sells"][-1][4])
        y = S.simulate(ser(c), 0, rule(prot=None), log=True)            # no protection: holds to day 14 (series ends) -> open
        self.assertTrue(y["open"])

    def test_time_limit_and_runner(self):
        flat = [1.0] * (H14 + 50)
        x = S.simulate(ser(flat), 0, rule(), log=True)
        self.assertEqual(x["sells"][-1][4], "time limit 14d")
        self.assertAlmostEqual((x["exit_t"] - (T0 + HOUR)) / DAY, 14, delta=0.05)
        up = [1.0] + [2.5] * (H14 + 10) + [2.5 - 0.02 * i for i in range(1, 100)]
        y = S.simulate(ser(up), 0, rule(), log=True)
        self.assertTrue(y["runner"])
        self.assertEqual(y["sells"][-1][4], "runner trail")
        self.assertAlmostEqual(y["sells"][-1][2], 1.25, delta=0.03)    # 50% below 2.5
        z = S.simulate(ser(up), 0, rule(rt=0.40), log=True)
        self.assertAlmostEqual(z["sells"][-1][2], 1.5, delta=0.03)

    def test_take_profit_skips_clock_like_dex_py(self):
        c = [1.0, 11.0] + [11.0] * (H14 + 30)
        x = S.simulate(ser(c), 0, rule(prot=None, tps=((10, 0.25),)), log=True)
        self.assertEqual(x["sells"][0][4], "take-profit 10x")
        self.assertAlmostEqual(x["sells"][0][3], 0.25, delta=1e-9)
        self.assertTrue(x["open"])                                        # no time limit after a take-profit
        self.assertFalse(x["runner"])

    def test_cap_banks_gains(self):
        c = [1.0] + [1.0 + i * 0.1 for i in range(1, 100)]
        x = S.simulate(ser(c), 0, rule(cap=0.25), log=True)
        caps = [s for s in x["sells"] if s[4].startswith("cap")]
        self.assertTrue(caps)
        pos_end = (1 + x["ret"]) * S.STAKE
        self.assertLess(pos_end, S.STAKE * c[-1])                          # banked, so less upside than holding

    def test_rug(self):
        c = [1.0] * 30
        x = S.simulate(ser(c, rug={10}), 0, rule(), log=True)
        self.assertAlmostEqual(x["ret"], S.RUG_LOSS * 1.0, delta=0.02)

    def test_entry(self):
        c = [1.0] * 10 + [1.2] + [1.2] * 5
        s = ser(c)
        self.assertEqual(S.find_entry(s), 10)
        self.assertIsNone(S.find_entry(ser(c, vol=10.0)))                 # volume floor
        early = [1.0, 1.5] + [1.5] * 10
        self.assertIsNone(S.find_entry(ser(early)))                       # +50% in hour 1 is before the 6h age floor

    def test_holders_replay(self):
        a, b, v = "0x" + "11" * 20, "0x" + "22" * 20, S.VITALIK
        tr = [(1, 0, S.ZERO, a, 1000), (2, 0, a, v, 500), (3, 0, a, b, 100)] + [(4, k, a, "0x%040x" % (k + 5), 10) for k in range(30)]
        (lab, s), = S.holders_timeline(tr, [("d1", 10)], set())
        self.assertAlmostEqual(s["top10"], (500 + 100 + 100 + 70) / 1000, delta=1e-9)   # vitalik, a (100 left), b, 7 x 10
        self.assertLess(s["top10_famous"], s["top10"])
        self.assertAlmostEqual(s["top10_fix"], 0.1, delta=1e-9)            # only `a` ever sent tokens


if __name__ == "__main__":
    unittest.main()
