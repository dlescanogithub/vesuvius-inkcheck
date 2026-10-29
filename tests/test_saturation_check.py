"""saturation_check: diagnostic warning for saturated 8-bit maps (post hoc, f1/DIAG_0172.md). Synthetic data only."""
import json
import unittest

import numpy as np

from inkcheck.node_d_v2 import saturation_check


class TestSaturationCheck(unittest.TestCase):
    def test_normal_map_not_saturated(self):
        rng = np.random.default_rng(0)
        a = np.clip(rng.normal(80, 20, (100, 100)), 0, 255).astype(np.uint8)
        r = saturation_check(a, np.ones_like(a, bool))
        self.assertFalse(r["saturated"])
        self.assertLess(r["frac_high"], 0.05)
        self.assertIs(type(r["saturated"]), bool)
        json.dumps(r)

    def test_saturated_plateau(self):
        rng = np.random.default_rng(1)
        a = np.clip(rng.normal(160, 6, (100, 100)), 0, 255).astype(np.uint8)
        r = saturation_check(a, np.ones_like(a, bool))
        self.assertTrue(r["saturated"])
        self.assertGreater(r["median"], 128)
        self.assertGreater(r["tie_frac"], 0.05)

    def test_mask_and_empty(self):
        a = np.full((10, 10), 200, np.uint8); a[:, :5] = 50
        valid = np.zeros((10, 10), bool); valid[:, :5] = True
        self.assertFalse(saturation_check(a, valid)["saturated"])
        r = saturation_check(a, np.zeros((10, 10), bool))
        self.assertEqual(r["n"], 0); self.assertFalse(r["saturated"])

    def test_threshold_override(self):
        a = np.full((10, 10), 130, np.uint8)
        self.assertTrue(saturation_check(a, np.ones((10, 10), bool))["saturated"])
        self.assertFalse(saturation_check(a, np.ones((10, 10), bool), warn=dict(high_level=140))["saturated"])


if __name__ == "__main__":
    unittest.main()
