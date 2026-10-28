"""Tests for the Ink Recoverability Protocol entry point (`inkcheck report`). Fast: no inference, synthetic JSONs."""
import json
import tempfile
import unittest
from pathlib import Path

from inkcheck import irp
from inkcheck.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[1]


def fake_check(path, verdict, r=0.3, sr=0.2, n=50, auc=0.8):
    path.write_text(json.dumps({"verdict": verdict, "summary": "", "numbers": {
        "r_bandpass": r, "r_bandpass_z": 10.0, "r_bandpass_p": 0.005, "r_bandpass_null_mean": 0.05, "auc_raw": auc,
        "stroke_recall": sr, "n_ref_strokes": n, "overlap_cm2": 1.0, "analysis_um": 9.0,
        "metric_nulls": {"stroke_recall": {"null_mean": 0.07}}}}))
    return {"label": path.stem, "json": path.name}


class TestNodes(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def load(self, entries):
        return [irp.load_check(e, self.d) for e in entries]

    def test_node_a_pass_weak_fail_and_leak(self):
        p = fake_check(self.d / "p.json", "PASS", 0.7, 0.6)
        w = fake_check(self.d / "w.json", "WEAK")
        f = fake_check(self.d / "f.json", "FAIL", 0.02, 0.05)
        self.assertEqual(irp.node_a(self.load([w, p])).verdict, "PASS")
        self.assertEqual(irp.node_a(self.load([w, f])).verdict, "WEAK")
        self.assertEqual(irp.node_a(self.load([f])).verdict, "FAIL")
        # a leaked PASS must not count
        leaked = dict(p, held_out=False)
        self.assertEqual(irp.node_a(self.load([leaked, w])).verdict, "WEAK")
        self.assertEqual(irp.node_a(self.load([leaked])).verdict, "NO_HELD_OUT")

    def test_node_a_withheld_checks_show_verdict_only(self):
        # a withheld check uses the case-file verdict; its numbers must never reach the card
        p = fake_check(self.d / "p.json", "PASS", 0.7123, 0.6111)
        wh = dict(p, withhold="data reservation", verdict="PASS")
        res = irp.node_a(self.load([wh]))
        self.assertEqual(res.verdict, "PASS")
        text = json.dumps(res.__dict__, default=str)
        self.assertIn("withheld", text)
        self.assertNotIn("0.712", text)
        self.assertNotIn("0.61", text)
        # without the JSON the verdict still comes from the case file
        (self.d / "p.json").unlink()
        self.assertEqual(irp.node_a(self.load([wh])).verdict, "PASS")
        # a withheld entry with neither verdict nor JSON is an error
        with self.assertRaises(FileNotFoundError):
            irp.load_check({"label": "x", "json": "missing.json", "withhold": "r"}, self.d)
        # a private JSON that disagrees with the case-file verdict is an error
        fake_check(self.d / "p.json", "WEAK")
        with self.assertRaises(ValueError):
            irp.load_check(wh, self.d)

    def test_node_a_shows_bootstrap_ci_and_expectation(self):
        e = fake_check(self.d / "b.json", "FAIL", 0.05, 0.1)
        d = json.loads((self.d / "b.json").read_text())
        d["numbers"]["bootstrap"] = {"r_ci": [0.01, 0.09], "stroke_recall_ci": [0.0, 0.2], "recall_minus_chance": 0.0,
                                     "recall_minus_chance_ci": [-0.1, 0.1], "n_tiles": 49}
        (self.d / "b.json").write_text(json.dumps(d))
        res = irp.node_a(self.load([dict(e, expect="FAIL")]))
        self.assertIn("[0.01, 0.09]", res.table[1][2])
        self.assertIn("expected FAIL: reproduced", res.table[1][6])
        res = irp.node_a(self.load([dict(e, expect="PASS")]))
        self.assertIn("NOT reproduced", res.table[1][6])

    def test_node_r_reference_agreement(self):
        a = fake_check(self.d / "ra.json", "PASS", 0.7, 0.6)
        b = fake_check(self.d / "rb.json", "PASS", 0.6, 0.9, n=12)
        spec = {"references": [{"name": "map", "kind": "model"}, {"name": "IR", "kind": "camera"}],
                "ref_vs_ref": [{"label": "map vs IR", "metric": "AUC", "value": 0.9, "null_mean": 0.58, "p": 0.0005}],
                "same_pred": [{"label": "rv3", "a": a, "b": b}],
                "ranking": {"metric_a": "AUC map", "metric_b": "AUC IR", "models": [
                    {"label": m, "a": x, "b": y} for m, x, y in
                    [("dn", .77, .74), ("kl", .75, .69), ("soup", .66, .62), ("s43", .65, .67), ("s42", .63, .60)]]}}
        res = irp.node_r(spec, self.d)
        self.assertEqual(res.verdict, "REFS_AGREE")
        self.assertIn("0.90", res.table[3][3])
        c = fake_check(self.d / "rc.json", "FAIL", 0.02, 0.05)
        spec["same_pred"] = [{"label": "rv3", "a": a, "b": c}]
        self.assertEqual(irp.node_r(spec, self.d).verdict, "REFS_PARTIAL")
        rho, p = irp._spearman([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertAlmostEqual(rho, 1.0); self.assertAlmostEqual(p, 1 / 24)

    def test_node_n_negative_controls(self):
        f = dict(fake_check(self.d / "n1.json", "FAIL", 0.05, 0.1), expect="FAIL")
        w = dict(fake_check(self.d / "n2.json", "WEAK", 0.15, 0.2), expect="FAIL")
        p = dict(fake_check(self.d / "n3.json", "PASS", 0.7, 0.6), expect="FAIL")
        self.assertEqual(irp.node_n(self.load([f])).verdict, "CONTROLS_OK")
        self.assertEqual(irp.node_n(self.load([f, w])).verdict, "NO_CONTROL_PASSES")
        self.assertEqual(irp.node_n(self.load([f, p])).verdict, "CONTROL_PASSED")

    def test_node_a_low_power_auc_control(self):
        e = dict(fake_check(self.d / "c.json", "WEAK", n=2, auc=0.935), published_auc=0.93)
        self.assertEqual(irp.node_a(self.load([e])).verdict, "CONTROL_REPRODUCED")
        e["published_auc"] = 0.80
        self.assertEqual(irp.node_a(self.load([e])).verdict, "LOW_POWER")

    def test_node_b_tolerance_edge(self):
        pts = [dict(value=0.05, verdict="PASS"), dict(value=0.02, verdict="PASS"), dict(value=0.005, verdict="WEAK")]
        self.assertEqual(irp.tolerance_edge(pts), 0.02)
        self.assertEqual(irp.tolerance_edge(pts, higher_is_better=False), 0.05)
        spec = dict(curves=[dict(proxy="hf", points=pts)], target={"hf": 0.03})
        self.assertEqual(irp.node_b(spec).verdict, "SCAN_OK")
        spec["target"]["hf"] = 0.01
        self.assertEqual(irp.node_b(spec).verdict, "SCAN_SUSPECT")
        self.assertEqual(irp.node_b(dict(curves=[], target={})).verdict, "NOT_RUN")

    def test_node_c(self):
        a = self.load([fake_check(self.d / "a1.json", "WEAK")])
        b_weak = self.load([fake_check(self.d / "b1.json", "WEAK", 0.4)])
        b_pass = self.load([fake_check(self.d / "b2.json", "PASS", 0.7, 0.6)])
        for x in a + b_weak + b_pass:
            x["label"] = "m"
        self.assertEqual(irp.node_c(dict(name="A", checks=a), dict(name="B", checks=b_weak)).verdict, "SCROLL_SPECIFIC")
        self.assertEqual(irp.node_c(dict(name="A", checks=a), dict(name="B", checks=b_pass)).verdict, "SCAN_LIMITED")

    def test_candidate_rule(self):
        good = dict(comps=30, comps_null=10, n_components=10, r_other=0.4, stroke_width_mm=0.2, visual_strokes=True)
        self.assertTrue(irp.candidate_rule(good)[0])
        self.assertFalse(irp.candidate_rule(dict(good, comps_null=20))[0])          # ratio 1.5 < 2
        self.assertFalse(irp.candidate_rule(dict(good, r_other=0.29))[0])           # agreement too low
        self.assertFalse(irp.candidate_rule(dict(good, stroke_width_mm=0.8))[0])    # too wide for strokes
        self.assertFalse(irp.candidate_rule(dict(good, n_components=3))[0])         # small-number noise
        self.assertIsNone(irp.candidate_rule(dict(good, visual_strokes=None))[0])   # visual still to do
        self.assertFalse(irp.candidate_rule(dict(good, visual_strokes=False))[0])

    def test_prereg_must_come_first(self):
        (self.d / "PREREG.md").write_text("rule")
        z = [dict(zone="z", model="m", comps=30, comps_null=10, n_components=10, r_other=0.4, visual_strokes=True)]
        spec = dict(prereg="PREREG.md", prereg_written="2026-10-27T18:00:00-03:00", first_result="2026-10-27T19:00:00-03:00", zones=z)
        self.assertEqual(irp.node_d(spec, self.d).verdict, "CANDIDATE")
        spec["prereg_written"] = "2026-10-27T20:00:00-03:00"
        self.assertEqual(irp.node_d(spec, self.d).verdict, "EXPLORATORY")
        spec.pop("prereg_written")
        self.assertEqual(irp.node_d(spec, self.d).verdict, "EXPLORATORY")
        spec.update(prereg_written="2026-10-27T18:00:00-03:00", zones=[dict(z[0], r_other=0.1)])
        self.assertEqual(irp.node_d(spec, self.d).verdict, "NO_CANDIDATE")


class TestReportCLI(unittest.TestCase):
    def test_report_writes_card_and_routes(self):
        d = Path(tempfile.mkdtemp())
        fake_check(d / "w.json", "WEAK")
        fake_check(d / "w2.json", "WEAK", 0.35)
        case = dict(name="t", checks=[{"label": "m", "json": "w.json"}],
                    tolerance=dict(curves=[dict(proxy="hf", points=[dict(value=0.02, verdict="PASS")])], target={"hf": 0.03}),
                    two_scan=dict(scan_a=dict(name="a", checks=[{"label": "m", "json": "w.json"}]),
                                  scan_b=dict(name="b", checks=[{"label": "m", "json": "w2.json"}])))
        (d / "t.case.json").write_text(json.dumps(case))
        self.assertEqual(cli_main(["report", str(d / "t.case.json"), "--out", str(d / "cards")]), 0)
        res = json.loads((d / "cards" / "t.json").read_text())
        self.assertEqual(res["path"], ["A", "B", "C"])
        self.assertEqual(res["nodes"][-1]["verdict"], "SCROLL_SPECIFIC")
        md = (d / "cards" / "t.md").read_text()
        self.assertIn("Node C", md)
        self.assertIn("Recommended next step", md)
        self.assertTrue((d / "cards" / "t.png").stat().st_size > 1000)

    def test_pass_stops_at_a(self):
        d = Path(tempfile.mkdtemp())
        fake_check(d / "p.json", "PASS", 0.7, 0.6)
        case = dict(name="p", checks=[{"label": "m", "json": "p.json"}],
                    tolerance=dict(curves=[dict(proxy="hf", points=[dict(value=0.02, verdict="PASS")])], target={"hf": 0.03}))
        res = irp.run_case(case, d)
        self.assertEqual(res["path"], ["A"])

    def test_worked_examples_reproduce(self):
        """The four shipped cards must come out with the verdicts quoted in the README."""
        want = {"paris4": "PASS", "343P": "SCROLL_SPECIFIC", "pherc0814": "CONTROL_REPRODUCED", "pherc1203": "NO_CANDIDATE"}
        for name, v in want.items():
            c = ROOT / "examples" / "irp" / f"{name}.case.json"
            res = irp.run_case(json.loads(c.read_text()), c.parent)
            self.assertEqual(res["nodes"][-1]["verdict"], v, name)

    def test_classic_cli_still_parses(self):
        from inkcheck.cli import build_parser
        a = build_parser().parse_args(["p.tif", "r.tif", "--pred-um", "8", "--ref-um", "2"])
        self.assertEqual(a.pred, "p.tif")


if __name__ == "__main__":
    unittest.main()
