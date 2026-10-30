"""Exit codes: 0 PASS, 1 WEAK, 2 FAIL, 3 INVALID (quick), 4 ERROR -- a crash or a usage error must not look like a verdict."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from inkcheck import cli
from inkcheck.cli import EXIT_ERROR, main, verdict_exit_code

SRC = str(Path(__file__).resolve().parents[1] / "src")


class TestExitCodes(unittest.TestCase):
    def test_verdict_mapping(self):
        self.assertEqual([verdict_exit_code(v) for v in ("PASS", "WEAK", "FAIL", "INVALID")], [0, 1, 2, 3])
        self.assertEqual(verdict_exit_code("something else"), EXIT_ERROR)
        self.assertEqual(EXIT_ERROR, 4)
        self.assertEqual(len({0, 1, 2, 3, EXIT_ERROR}), 5)

    def test_missing_input_file_is_error_not_weak(self):
        with tempfile.TemporaryDirectory() as d:
            code = main([str(Path(d) / "nope.png"), str(Path(d) / "nope2.png"), "--pred-um", "8", "--ref-um", "4",
                         "--out", str(Path(d) / "o")])
        self.assertEqual(code, EXIT_ERROR)

    def test_uncaught_exception_is_error(self):
        orig = cli.run_check

        def boom(*a, **k):
            raise RuntimeError("synthetic crash")
        cli.run_check = boom
        try:
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "a.png"
                Image.fromarray(np.zeros((64, 64), np.uint8)).save(p)
                code = main([str(p), str(p), "--pred-um", "8", "--ref-um", "8", "--out", str(Path(d) / "o")])
        finally:
            cli.run_check = orig
        self.assertEqual(code, EXIT_ERROR)

    def test_usage_error_is_error_not_fail(self):
        self.assertEqual(main(["a.png"]), EXIT_ERROR)                    # missing REF / --pred-um / --ref-um
        self.assertEqual(main(["a.png", "b.png", "--pred-um", "x", "--ref-um", "4"]), EXIT_ERROR)
        self.assertEqual(main(["report"]), EXIT_ERROR)                   # parser.error()
        self.assertEqual(main(["quick", "no-such-example"]), EXIT_ERROR)  # SystemExit("message")
        self.assertEqual(main(["quick", "a.png", "b.png"]), EXIT_ERROR)   # needs --pred-um/--ref-um

    def test_help_is_zero(self):
        self.assertEqual(main(["--help"]), 0)
        self.assertEqual(main(["quick", "--help"]), 0)

    def test_process_exit_code(self):
        r = subprocess.run([sys.executable, "-m", "inkcheck", "missing_pred.png", "missing_ref.png", "--pred-um", "8",
                            "--ref-um", "4", "--out", "/nonexistent_dir_inkcheck/o"],
                           capture_output=True, text=True, env={"PYTHONPATH": SRC, "PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, EXIT_ERROR, r.stderr)
        self.assertIn("inkcheck: error:", r.stderr)


if __name__ == "__main__":
    unittest.main()
