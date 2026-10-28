"""Node D v2 on toy data only (no held-out data is touched before the pre-registration is evaluated)."""
import unittest

import numpy as np
from scipy import ndimage as ndi

from inkcheck import node_d_v2 as d2

S = (240, 240)


def smooth(rng, sigma=3.0):
    x = ndi.gaussian_filter(rng.normal(size=S), sigma)
    return x / x.std()


def ink(rng, n=25):
    img = np.zeros(S, bool)
    for _ in range(n):
        y, x, a, L = rng.uniform(0, S[0]), rng.uniform(0, S[1]), rng.uniform(0, np.pi), rng.uniform(10, 30)
        t = np.linspace(-L / 2, L / 2, 80)
        img[np.clip((y + t * np.sin(a)).astype(int), 0, S[0] - 1), np.clip((x + t * np.cos(a)).astype(int), 0, S[1] - 1)] = 1
    return ndi.binary_dilation(img, iterations=2).astype(float)


def model_pair(rng, signal, noise=0.6):
    return signal + noise * rng.normal(size=S), signal + noise * rng.normal(size=S)


def region(rng, ink_fwd, ink_rev, texture_in_gap):
    T = 0.5 * smooth(rng)                       # papyrus texture of this sheet, seen from both faces
    T_gap = T if texture_in_gap else 0.5 * smooth(rng)
    K = 2.0 * ink(rng)
    faces = {}
    for f, has_ink in (("fwd", ink_fwd), ("rev", ink_rev)):
        A, B = model_pair(rng, T + (K if has_ink else 0))
        off = [model_pair(rng, T_gap) for _ in range(2)]
        faces[f] = d2.face_stats(A, B, [o[0] for o in off], [o[1] for o in off], np.ones(S, bool))
    return faces


class TestNodeDv2(unittest.TestCase):
    def test_pitch_recovered(self):
        rng = np.random.default_rng(0)
        k = np.arange(160)
        prof = np.cos(2 * np.pi * k / 23.0) + 0.3 * rng.normal(size=k.size)
        p = d2.estimate_winding_pitch(prof)
        self.assertAlmostEqual(p, 23.0, delta=1.0)
        self.assertEqual(d2.off_winding_offsets(p), (p / 2, -p / 2))
        self.assertIsNone(d2.estimate_winding_pitch(np.zeros(50)))

    def test_one_faced_ink_is_candidate(self):
        f = region(np.random.default_rng(1), True, False, texture_in_gap=False)
        out, why, nums = d2.candidate_rule_v2(f["fwd"], f["rev"])
        self.assertEqual(out, "CANDIDATE", why)
        self.assertIn("one-faced", why[0])
        self.assertGreaterEqual(nums["s1_face_asym"], 2.0)

    def test_two_faced_ink_v1_misses_v2_flags(self):
        rng = np.random.default_rng(2)
        f = region(rng, True, True, texture_in_gap=False)
        out, why, nums = d2.candidate_rule_v2(f["fwd"], f["rev"])
        self.assertEqual(out, "CANDIDATE", why)
        self.assertIn("two-faced", why[0])
        self.assertLess(nums["s1_face_asym"], 2.0)              # face asymmetry alone (PR #2318 statistic) misses it
        self.assertFalse(d2.v1_rule_numbers(13.0, 11.3))        # and so does v1 at Erwin-343-like numbers

    def test_texture_only_is_nothing(self):
        for seed, gap in ((3, True), (4, False)):
            f = region(np.random.default_rng(seed), False, False, texture_in_gap=gap)
            out, why, _ = d2.candidate_rule_v2(f["fwd"], f["rev"])
            self.assertEqual(out, "NOTHING", (seed, why))

    def test_depth_persistent_texture_with_ink_on_both_faces_is_nothing(self):
        # texture (and anything else) that survives a half-pitch shift is not evidence of ink on the face
        rng = np.random.default_rng(5)
        T = 0.5 * smooth(rng) + 2.0 * ink(rng)    # "ink-like" structure that persists through depth
        faces = {}
        for f in ("fwd", "rev"):
            A, B = model_pair(rng, T)
            off = [model_pair(rng, T) for _ in range(2)]
            faces[f] = d2.face_stats(A, B, [o[0] for o in off], [o[1] for o in off], np.ones(S, bool))
        out, why, _ = d2.candidate_rule_v2(faces["fwd"], faces["rev"])
        self.assertEqual(out, "NOTHING", why)

    def test_pure_noise_is_nothing_and_null_is_calibrated(self):
        rng = np.random.default_rng(6)
        A, B = rng.normal(size=S), rng.normal(size=S)
        obs, p, null = d2.shift_null_p(A, B, np.ones(S, bool), n=99, min_shift_px=40)
        self.assertGreater(p, 0.01)
        self.assertEqual(null.size, 99)


if __name__ == "__main__":
    unittest.main()
