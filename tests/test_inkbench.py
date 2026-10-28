"""inkbench adapter: read a synthetic inkbench results folder, rank, and build an IRP case that inkcheck can run."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tifffile

from inkcheck import inkbench as ib
from inkcheck.cli import main


def fake_results(root: Path, pred: np.ndarray):
    s = root / "scores" / "p0841"; s.mkdir(parents=True)
    for reader, v, flag in (("readerv3", 0.87, "no"), ("d9v4c", 0.85, "no"), ("hecate", 0.80, "unknown"), ("rv2", 0.81, "yes")):
        s.joinpath(f"{reader}.json").write_text(json.dumps({"human_strict_exact": {
            "per_segment": {"w00": v, "ag896": v - 0.01}, "mean": v - 0.005, "trained_on": {"w00": flag, "ag896": "no"}}}))
    s.joinpath("_external.json").write_text("{}")
    for reader in ("readerv3", "hecate", "rv2"):
        d = root / "preds" / "PHerc0841" / "20250101000000-w00_inp_hr" / "ink" / reader / "raw" / "reading"
        d.mkdir(parents=True); tifffile.imwrite(d / "d0.tif", pred)


class TestInkbench(unittest.TestCase):
    def test_read_rank_and_case(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); rng = np.random.default_rng(0)
            pred = (rng.random((64, 64)) * 255).astype(np.uint8)
            fake_results(root, pred)
            rows = ib.read_scores(root)
            self.assertEqual(len(rows), 8)
            rk = ib.ranking(rows, "p0841")
            self.assertEqual([d["reader"] for d in rk], ["readerv3", "d9v4c", "rv2", "hecate"])
            self.assertEqual(rk[0]["leaked"], [])
            self.assertIn("w00:unknown", rk[-1]["leaked"])
            case = ib.case_from_inkbench(root, "p0841", "w00", "PHerc0841", "ref.png", 9.4, 2.4, root / "checks")
            by = {c["label"]: c for c in case["checks"]}
            self.assertEqual(set(by), {"readerv3", "hecate", "rv2"})
            self.assertEqual(case["inkbench"]["missing_maps"], ["d9v4c"])
            self.assertTrue(by["readerv3"]["held_out"])
            self.assertFalse(by["rv2"]["held_out"])          # trained on it
            self.assertFalse(by["hecate"]["held_out"])       # unknown is not treated as held out
            self.assertAlmostEqual(by["readerv3"]["published_auc"], 0.87)

    def test_cli_table_and_case(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); fake_results(root, np.zeros((8, 8), np.uint8))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["inkbench", str(root)]), 0)
                self.assertEqual(main(["inkbench", str(root), "--benchmark", "p0841", "--segment", "w00", "--sample",
                                       "PHerc0841", "--ref", "r.png", "--ref-um", "2.4", "--pred-um", "9.4",
                                       "--case-out", str(root / "c.json")]), 0)
            self.assertIn("1. readerv3", buf.getvalue())
            self.assertEqual(len(json.loads((root / "c.json").read_text())["checks"]), 3)


if __name__ == "__main__":
    unittest.main()
