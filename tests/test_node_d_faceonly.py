"""Node D face-only option (PR #2318 statistic; rule pre-registered in results/irp/node_d_faceonly/). Synthetic data
plus a recount of the already-seen v2 numbers (design data, not validation)."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from inkcheck import irp
from inkcheck.node_d_v2 import face_only_from_maps, face_only_rule

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "irp" / "node_d_v2" / "results_v2_rescored.json"


class TestFaceOnlyRule(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(face_only_rule(0.30, 0.05)[0], "FLAG")
        self.assertEqual(face_only_rule(0.05, 0.30)[2]["best_face"], "rev")
        self.assertEqual(face_only_rule(0.038, 0.001)[0], "NOTHING")     # high asymmetry, IoU floor fails
        self.assertEqual(face_only_rule(0.40, 0.25)[0], "NOTHING")       # two-faced / texture-like
        self.assertEqual(face_only_rule(0.40, 0.0, valid_frac=0.29)[0], "NOT_EVALUABLE")
        self.assertEqual(face_only_rule(0.10, 0.05)[0], "FLAG")          # boundaries inclusive

    def test_maps_one_faced_ink_vs_texture(self):
        rng = np.random.default_rng(1)
        S = (200, 200)
        tex = ndi.gaussian_filter(rng.normal(size=S), 3); tex /= tex.std()
        ink = np.zeros(S); ink[40:160:20, 30:170] = 3.0; ink = ndi.gaussian_filter(ink, 1) * 3
        noisy = lambda x: x + 0.5 * rng.normal(size=S)
        A = {"fwd": noisy(0.3 * tex + ink), "rev": noisy(0.3 * tex)}
        B = {"fwd": noisy(0.3 * tex + ink), "rev": noisy(0.3 * tex)}
        self.assertEqual(face_only_from_maps(A, B, np.ones(S, bool))[0], "FLAG")
        T = {"fwd": noisy(tex), "rev": noisy(tex)}; U = {"fwd": noisy(tex), "rev": noisy(tex)}
        self.assertEqual(face_only_from_maps(T, U, np.ones(S, bool))[0], "NOTHING")

    def test_node_d_option(self):
        d = Path(tempfile.mkdtemp()); (d / "PREREG.md").write_text("rule")
        z = [dict(zone="z1", iou_fwd=0.43, iou_rev=0.19), dict(zone="z2", iou_fwd=0.01, iou_rev=0.0)]
        spec = dict(rule_type="face_only", prereg="PREREG.md", prereg_written="2026-10-28T18:00:00-03:00",
                    first_result="2026-10-29T10:00:00-03:00", zones=z)
        r = irp.node_d(spec, d)
        self.assertEqual(r.verdict, "CANDIDATE"); self.assertIn("z1", r.answer); self.assertNotIn("z2", r.answer)
        spec["zones"] = z[1:]
        self.assertEqual(irp.node_d(spec, d).verdict, "NO_CANDIDATE")
        spec.update(zones=z, first_result="2026-10-28T17:00:00-03:00")
        self.assertEqual(irp.node_d(spec, d).verdict, "EXPLORATORY")

    def test_v1_default_unchanged(self):
        d = Path(tempfile.mkdtemp()); (d / "PREREG.md").write_text("rule")
        z = [dict(zone="z", model="m", comps=50, comps_null=10, n_components=20, r_other=0.5, stroke_width_mm=0.3, visual_strokes=True)]
        spec = dict(prereg="PREREG.md", prereg_written="2026-10-27T18:00:00-03:00", first_result="2026-10-27T19:00:00-03:00", zones=z)
        self.assertEqual(irp.node_d(spec, d).verdict, "CANDIDATE")

    @unittest.skipUnless(RES.exists(), "rescored v2 results not present")
    def test_seen_v2_recount(self):
        R = json.loads(RES.read_text())
        tile = {"0172": 632, "0500P2": 534, "0841": 534, "0009B": 579}
        out = {}
        for n, s in R["regions"].items():
            t = tile[n.split("-")[0]]
            out[n] = (s["kind"], face_only_rule(s["faces"]["fwd"]["iou"], s["faces"]["rev"]["iou"], s["valid_px"] / t / t)[0])
        pos = [k for k, (kind, o) in out.items() if kind == "positive" and o == "FLAG"]
        self.assertEqual(len(pos), 8)
        self.assertEqual(out["0500P2-371_pos1"][1], "NOT_EVALUABLE")
        self.assertEqual([k for k, (kind, o) in out.items() if kind == "blank" and o == "FLAG"], [])
        self.assertEqual(R["verdict"]["side_by_side"]["face_only"], [9, 0])
        self.assertEqual(R["verdict"]["side_by_side"]["face_only_controls"], [2, 24])


if __name__ == "__main__":
    unittest.main()
