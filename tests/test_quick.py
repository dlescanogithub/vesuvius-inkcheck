"""`inkcheck quick`: input resolution, sha check, control, explanation, end-to-end on synthetic local files (offline)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from inkcheck import CheckConfig, run_check
from inkcheck import quick
from test_inkcheck import QUIET, cfg, strokes


class TestQuick(unittest.TestCase):
    def test_examples_are_pinned(self):
        for name, ex in quick.EXAMPLES.items():
            for k in ("pred", "ref", "mask"):
                url, sha = ex[k]
                self.assertIn("/7e96b969d3a1407504db4826543136573bda78b8/", url, name)
                self.assertEqual(len(sha), 64, name)
            self.assertIn(ex["expect"], ("PASS", "WEAK", "FAIL"))
        self.assertIn(quick.DEFAULT_EXAMPLE, quick.EXAMPLES)

    def test_fetch_local_and_file_url_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.bin"
            p.write_bytes(b"hello")
            self.assertEqual(quick.fetch(str(p)), p)
            with self.assertRaises(FileNotFoundError):
                quick.fetch(str(Path(d) / "missing.png"))
            self.assertEqual(quick.sha256_file(p), hashlib.sha256(b"hello").hexdigest())

    def test_wrong_place_is_a_permutation(self):
        a = np.arange(60, dtype=float).reshape(6, 10)
        b = quick.wrong_place(a)
        self.assertEqual(sorted(a.ravel()), sorted(b.ravel()))
        self.assertEqual(b[3, 5], a[0, 0])

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        cls.ref = strokes((2400, 2400), 500, rng)  # 9.6 mm at 4 um (as in test_inkcheck.TestVerdicts)
        lo = cls.ref[200:2200, 300:2300].reshape(1000, 2, 1000, 2).mean((1, 3))
        cls.pred = (0.6 * lo + 25 * rng.normal(size=lo.shape) + 10).astype(np.float32)

    def test_explain_pass_and_control(self):
        res = run_check(self.pred, self.ref, cfg(), **QUIET)
        ctrl = run_check(quick.wrong_place(self.pred), self.ref, cfg(), **QUIET)
        self.assertEqual(res.verdict, "PASS")
        self.assertEqual(ctrl.verdict, "FAIL")
        txt = " ".join(quick.explain(res, ctrl))
        self.assertIn("Verdict PASS", txt)
        self.assertIn("as it must", txt)

    def test_end_to_end_local_files(self):
        with tempfile.TemporaryDirectory() as d:
            pp, rp = Path(d) / "pred.png", Path(d) / "ref.png"
            Image.fromarray(np.clip(self.pred, 0, 255).astype(np.uint8)).save(pp)
            Image.fromarray(np.clip(self.ref, 0, 255).astype(np.uint8)).save(rp)
            out = Path(d) / "q"
            code = quick.run([str(pp), str(rp), "--pred-um", "8", "--ref-um", "4", "--ref-origin", "200,300",
                              "--workers", "1", "--out", str(out)], log=lambda s: None)
            s = json.loads(Path(str(out) + ".summary.json").read_text())
            self.assertEqual(s["verdict"], "PASS")
            self.assertEqual(code, 0)
            self.assertEqual(s["node_N"], "NO_CONTROL_PASSES")
            self.assertEqual(s["control_verdict"], "FAIL")
            self.assertTrue(Path(str(out) + ".png").exists())

    def test_list(self):
        self.assertEqual(quick.run(["--list"]), 0)


if __name__ == "__main__":
    unittest.main()
