"""Regression test for D5: the node D v2 scorer counted face-only hits with `x is True`, which is False for numpy.bool_,
so the face-only column of results_v2.json read 0 / 0 while the per-region flags said 9 positives."""
import json
import unittest
from pathlib import Path

import numpy as np

from inkcheck.node_d_v2 import count_flagged, face_only_flag

RES = Path(__file__).resolve().parents[1] / "results" / "irp" / "node_d_v2" / "results_v2.json"


class TestFaceOnlyBool(unittest.TestCase):
    def test_numpy_bool_is_not_true(self):
        self.assertFalse(np.bool_(True) is True)  # the root cause, kept as documentation

    def test_flag_returns_python_bool(self):
        f = face_only_flag(np.float64(0.2), np.float64(3.0), np.int64(10))
        self.assertIs(f, True)
        self.assertIs(face_only_flag(0.05, 30.0, 10), False)   # IoU floor
        self.assertIs(face_only_flag(0.5, 1.5, 10), False)     # asymmetry
        self.assertIs(face_only_flag(0.5, 3.0, 0), False)      # no valid pixels

    def test_count_numpy_python_and_json_bools(self):
        regs = {"a": dict(kind="positive", face_only=np.bool_(True), outcome="NOTHING"),
                "b": dict(kind="positive", face_only=True, outcome="CANDIDATE"),
                "c": dict(kind="positive", face_only=1.0, outcome="NOTHING"),
                "d": dict(kind="positive", face_only=np.bool_(False), outcome="NOTHING"),
                "e": dict(kind="blank", face_only=np.bool_(True), outcome="CANDIDATE")}
        self.assertEqual(count_flagged(regs, "positive", "face_only"), ["a", "b", "c"])
        self.assertEqual(count_flagged(regs, "blank", "face_only"), ["e"])
        self.assertEqual(count_flagged(regs, "positive"), ["b"])

    @unittest.skipUnless(RES.exists(), "results_v2.json not present")
    def test_committed_results_recount(self):
        R = json.loads(RES.read_text())
        self.assertEqual(len(count_flagged(R["regions"], "positive", "face_only")), 9)
        self.assertEqual(len(count_flagged(R["regions"], "blank", "face_only")), 0)
        self.assertEqual(R["verdict"]["VERDICT"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
