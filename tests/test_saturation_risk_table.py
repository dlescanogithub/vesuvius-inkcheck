"""Pure helpers of scripts/saturation_risk_table.py (synthetic data, no network)."""
import importlib.util
import os
import unittest

import numpy as np

_P = os.path.join(os.path.dirname(__file__), "..", "scripts", "saturation_risk_table.py")
_spec = importlib.util.spec_from_file_location("saturation_risk_table", _P)
srt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srt)


class TestSaturationRiskTable(unittest.TestCase):
    def test_parse_long_id(self):
        d = srt.parse_long_id("20250720065842-9.362um-1.2m-113keV")
        self.assertEqual(d, dict(pixel_um=9.362, distance_m=1.2, energy_kev=113.0))
        d = srt.parse_long_id("20241024131838-7.910um-53keV")
        self.assertEqual((d["pixel_um"], d["distance_m"], d["energy_kev"]), (7.91, None, 53.0))
        self.assertIsNone(srt.parse_long_id(None)["energy_kev"])

    def test_intensity_stats(self):
        s = srt.intensity_stats(np.r_[np.full(30, 100), np.full(70, 200)].astype(np.uint8))
        self.assertEqual(s["n"], 100)
        self.assertAlmostEqual(s["frac_gt128"], 0.7)
        self.assertEqual(s["median"], 200.0)
        self.assertEqual(srt.intensity_stats([])["n"], 0)

    def test_measured_level_matches_diag_0172(self):
        rng = np.random.default_rng(0)
        bright = srt.intensity_stats(np.clip(rng.normal(154, 26, 20000), 1, 255))  # 0172-like
        normal = srt.intensity_stats(np.clip(rng.normal(90, 26, 20000), 1, 255))   # 113-116 keV-like
        self.assertEqual(srt.measured_level(bright["median"], bright["frac_gt128"]), "HIGH")
        self.assertEqual(srt.measured_level(normal["median"], normal["frac_gt128"]), "LOW")
        self.assertEqual(srt.measured_level(115, 0.1), "MEDIUM")
        self.assertEqual(srt.measured_level(100, 0.3), "MEDIUM")
        self.assertIsNone(srt.measured_level(None, None))

    def test_metadata_level(self):
        self.assertEqual(srt.metadata_level(53), "HIGH")
        self.assertEqual(srt.metadata_level(113), "LOW")
        self.assertEqual(srt.metadata_level(78), "MEDIUM")
        self.assertEqual(srt.metadata_level(None), "UNKNOWN")

    def test_final_level_precedence(self):
        self.assertEqual(srt.final_level("HIGH", "LOW", "HIGH"), ("LOW", "measured (surface volume)"))
        self.assertEqual(srt.final_level("HIGH", None, "LOW"), ("LOW", "measured (raw volume, coarse)"))
        self.assertEqual(srt.final_level("HIGH", None, None), ("HIGH", "metadata only"))


if __name__ == "__main__":
    unittest.main()
