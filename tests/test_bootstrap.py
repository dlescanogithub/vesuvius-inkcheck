"""Tile (block) bootstrap of r_bp and stroke recall."""
import unittest

import numpy as np
from scipy import ndimage as ndi

from inkcheck import CheckConfig, run_check
from inkcheck import metrics as M
from test_inkcheck import QUIET, cfg, strokes


class TestTileBootstrap(unittest.TestCase):
    def test_correlated_ci_excludes_zero_and_contains_r(self):
        rng = np.random.default_rng(3)
        x = ndi.gaussian_filter(rng.normal(size=(600, 600)), 3)
        y = x + 0.05 * rng.normal(size=x.shape)
        m = np.ones(x.shape, bool)
        b = M.tile_bootstrap(x, y, m, px_um=10, tile_mm=0.5, n_boot=300)
        self.assertGreater(b["r_ci"][0], 0.5)
        self.assertLessEqual(b["r_ci"][0], b["r"])
        self.assertGreaterEqual(b["r_ci"][1], b["r"])
        self.assertEqual(b["n_tiles"], 144)

    def test_independent_ci_contains_zero(self):
        rng = np.random.default_rng(4)
        x = ndi.gaussian_filter(rng.normal(size=(600, 600)), 3)
        y = ndi.gaussian_filter(rng.normal(size=(600, 600)), 3)
        b = M.tile_bootstrap(x, y, np.ones(x.shape, bool), px_um=10, tile_mm=0.5, n_boot=300)
        self.assertLess(b["r_ci"][0], 0)
        self.assertGreater(b["r_ci"][1], 0)

    def test_stroke_table_matches_stroke_overlap(self):
        rng = np.random.default_rng(5)
        ref = strokes((500, 500), 60, rng) > 100
        pred = ndi.binary_dilation(ref, iterations=1) & (rng.random(ref.shape) < 0.7)
        m = np.ones(ref.shape, bool)
        cy, cx, hit = M.stroke_table(pred, ref, m, 20, 0.5)
        ov = M.stroke_overlap(pred, ref, m, 20, 0.5, tol_px=0)
        self.assertEqual(len(hit), ov["n_ref_strokes"])
        self.assertAlmostEqual(float(hit.mean()), ov["stroke_recall"])
        b = M.tile_bootstrap(pred.astype(float), ref.astype(float), m, 10, 1.0, cy, cx, hit, chance=0.1, n_boot=200)
        self.assertAlmostEqual(b["stroke_recall"], ov["stroke_recall"])
        self.assertGreater(b["recall_minus_chance_ci"][0], 0)

    def test_run_check_reports_bootstrap(self):
        rng = np.random.default_rng(0)
        ref = strokes((1200, 1200), 140, rng)
        lo = ref[100:1100, 100:1100].reshape(500, 2, 500, 2).mean((1, 3))
        pred = 0.6 * lo + 25 * rng.normal(size=lo.shape) + 10
        res = run_check(pred.astype(np.float32), ref, cfg(ref_origin=(100.0, 100.0), boot_tile_mm=0.8, n_boot=200),
                        **QUIET)
        b = res.numbers["bootstrap"]
        self.assertIn("r_ci", b)
        self.assertLess(b["r_ci"][0], b["r_ci"][1])
        self.assertLess(abs(b["r"] - res.numbers["r_bandpass"]), 0.1)
        self.assertAlmostEqual(b["stroke_recall"], res.numbers["stroke_recall"], places=6)


if __name__ == "__main__":
    unittest.main()
