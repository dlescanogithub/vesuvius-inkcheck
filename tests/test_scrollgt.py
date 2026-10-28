import unittest
import numpy as np
from inkcheck import scrollgt as S


class TestScrollGT(unittest.TestCase):
    def test_ap_lift_matches_sklearn(self):
        rng = np.random.default_rng(1)
        y = rng.random(5000) < 0.2
        p = np.round(rng.random(5000) * 0.5 + y * 0.3, 2)   # ties on purpose
        r = S.ap_prevalence_lift(p, y)
        try:
            from sklearn.metrics import average_precision_score, roc_auc_score
        except ImportError:
            self.skipTest("sklearn not installed")
        self.assertAlmostEqual(r["average_precision"], average_precision_score(y, p), places=10)
        self.assertAlmostEqual(r["roc_auc"], roc_auc_score(y, p), places=10)
        self.assertAlmostEqual(r["ap_prevalence_lift"], r["average_precision"] / y.mean(), places=10)

    def test_floors(self):
        y = np.zeros(1000, bool); y[:180] = True
        r = S.ap_prevalence_lift(np.ones(1000), y)          # all-positive floor: AP = prevalence, lift 1
        self.assertAlmostEqual(r["ap_prevalence_lift"], 1.0)
        self.assertAlmostEqual(r["roc_auc"], 0.5)
        r = S.ap_prevalence_lift(y.astype(float), y)        # oracle: lift = 1 / prevalence
        self.assertAlmostEqual(r["ap_prevalence_lift"], 1 / 0.18)

    def test_status_and_exposure(self):
        meta = {"segment": "20231210121321", "registration": {"placement": {"passed": True, "offset_mm": 0.31}}}
        st = S.target_status(meta)
        self.assertTrue(st["scoreable"]); self.assertIn("0.31 mm", st["note"])
        self.assertFalse(S.target_status({"scoring": {"enabled": False}})["scoreable"])
        self.assertEqual(S.exposure(meta, ["Paris4:w06", "phercparis4-w06"]), "train_exposed")
        self.assertEqual(S.exposure(meta, ["phercparis4-w00"]), "held_out")


if __name__ == "__main__":
    unittest.main()
