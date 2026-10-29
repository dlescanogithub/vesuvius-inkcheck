"""inkcheck.opendata on synthetic data (no network). Network checks are marked `network` and skipped in CI."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from inkcheck import opendata as od  # noqa: E402

try:
    import pytest
    network = pytest.mark.network
except ImportError:  # pragma: no cover
    network = lambda f: f

DS8 = ("PHerc0172-20250917143559-7.91um-53keV-volume-20241024131838-20250713185324-"
       "timesformer_scroll5_july_retreat-tile64-stride16-ds8.jpg")
FULL = ("PHerc0009B-20250510172639-2.401um-0.35m-77keV-volume-20250820154339-20260417190342-"
        "new_canon_autoresearch_recipe-tile256-stride128.tif")


def write_zarr(root: Path, data: np.ndarray, chunks, sep="/", compressor=None, group=True, skip=()):
    arr = root / "0" if group else root
    arr.mkdir(parents=True)
    if group:
        (root / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
    meta = dict(zarr_format=2, shape=list(data.shape), chunks=list(chunks), dtype=data.dtype.str, compressor=compressor,
                fill_value=0, order="C", filters=None, dimension_separator=sep)
    (arr / ".zarray").write_text(json.dumps(meta))
    n = [-(-s // c) for s, c in zip(data.shape, chunks)]
    for iz in range(n[0]):
        for iy in range(n[1]):
            for ix in range(n[2]):
                if (iz, iy, ix) in skip:
                    continue
                blk = np.zeros(chunks, data.dtype)
                src = data[iz * chunks[0]:(iz + 1) * chunks[0], iy * chunks[1]:(iy + 1) * chunks[1], ix * chunks[2]:(ix + 1) * chunks[2]]
                blk[:src.shape[0], :src.shape[1], :src.shape[2]] = src
                raw = blk.tobytes()
                if compressor is not None:
                    import numcodecs
                    raw = numcodecs.get_codec(compressor).encode(raw)
                p = arr / sep.join(map(str, (iz, iy, ix)))
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)


class TestNames(unittest.TestCase):
    def test_parse_ds8(self):
        m = od.parse_prediction_name(DS8)
        self.assertEqual((m["scroll"], m["segment"], m["ds"], m["model"], m["tile"], m["stride"]),
                         ("PHerc0172", "20250917143559", 8, "timesformer_scroll5_july_retreat", 64, 16))
        self.assertAlmostEqual(m["pixel_um"], 7.91)
        self.assertAlmostEqual(m["map_pixel_um"], 63.28)
        self.assertEqual(m["energy_kev"], 53.0)

    def test_parse_full_with_distance(self):
        m = od.parse_prediction_name("s3://vesuvius-challenge-open-data/PHerc0009B/segments/x/ink-detection/" + FULL)
        self.assertEqual((m["ds"], m["scan"], m["volume"], m["run"]), (1, "2.401um-0.35m-77keV", "20250820154339", "20260417190342"))
        self.assertEqual(m["map_pixel_um"], 2.401)

    def test_parse_rejects(self):
        with self.assertRaises(ValueError):
            od.parse_prediction_name("my_map.png")

    def test_to_url(self):
        self.assertEqual(od.to_url("s3://vesuvius-challenge-open-data/PHerc0172/a.jpg"),
                         "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0172/a.jpg")
        self.assertEqual(od.to_url("PHerc0172/segments/a/b.jpg"), od.HTTPS + "PHerc0172/segments/a/b.jpg")
        self.assertEqual(od.to_url("https://example.org/x.png"), "https://example.org/x.png")
        self.assertEqual(od.to_url("relative/not_a_key.png"), "relative/not_a_key.png")

    def test_keys(self):
        k = od.downsampled_key("PHerc0172", "20250917143559-w062", DS8[:-8])
        self.assertEqual(k, "PHerc0172/segments/20250917143559-w062/ink-detection/downsampled/" + DS8)


class TestLoadPrediction(unittest.TestCase):
    def test_local_png_jpg_tif(self):
        from PIL import Image
        import tifffile
        rng = np.random.default_rng(0)
        a = (rng.random((40, 60)) * 255).astype(np.uint8)
        with tempfile.TemporaryDirectory() as d:
            for ext in ("png", "tif"):
                p = Path(d) / DS8.replace(".jpg", "." + ext)
                (tifffile.imwrite(p, a) if ext == "tif" else Image.fromarray(a).save(p))
                m, meta = od.load_prediction(str(p))
                self.assertEqual(m.shape, (40, 60))
                np.testing.assert_allclose(m, a.astype(np.float32))
                self.assertEqual(meta["ds"], 8)
            rgb = np.stack([a] * 3, -1)
            p = Path(d) / "other.jpg"
            Image.fromarray(rgb).save(p, quality=95)
            m, meta = od.load_prediction(str(p))
            self.assertEqual(m.shape, (40, 60))
            self.assertNotIn("ds", meta)


class TestSurfaceVolume(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.data = rng.integers(1, 255, size=(7, 300, 290), dtype=np.uint8)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_group_slash_uncompressed(self):
        write_zarr(self.d / "sv.zarr", self.data, (7, 128, 128))
        sv = od.open_surface_volume(str(self.d / "sv.zarr"))
        self.assertEqual((sv.shape, sv.layers), ((7, 300, 290), 7))
        np.testing.assert_array_equal(sv.read(), self.data)
        np.testing.assert_array_equal(sv.read(slice(2, 5), slice(100, 270), slice(5, 260)), self.data[2:5, 100:270, 5:260])
        np.testing.assert_array_equal(sv.read(y=slice(-10, None)), self.data[:, -10:])
        self.assertEqual(sv.centred_window(3), slice(2, 5))

    def test_array_dir_dot_separator_and_missing_chunk(self):
        write_zarr(self.d / "a", self.data, (7, 128, 128), sep=".", group=False, skip={(0, 1, 1)})
        sv = od.open_surface_volume(str(self.d / "a"))
        got = sv.read()
        exp = self.data.copy()
        exp[:, 128:256, 128:256] = 0
        np.testing.assert_array_equal(got, exp)

    def test_compressed(self):
        try:
            import numcodecs  # noqa: F401
        except ImportError:
            self.skipTest("numcodecs not installed")
        write_zarr(self.d / "c.zarr", self.data, (7, 128, 128), compressor={"id": "zlib", "level": 1})
        np.testing.assert_array_equal(od.open_surface_volume(str(self.d / "c.zarr")).read(), self.data)

    def test_errors(self):
        with self.assertRaises(FileNotFoundError):
            od.open_surface_volume(str(self.d))
        write_zarr(self.d / "s.zarr", self.data, (7, 128, 128))
        with self.assertRaises(ValueError):
            od.open_surface_volume(str(self.d / "s.zarr")).read(slice(0, 7, 2))

    def test_ct_stats(self):
        b = np.zeros((2, 10, 10), np.uint8)
        b[0, :5] = 200
        b[1, :5] = 100
        s = od.ct_intensity_stats(b)
        self.assertEqual(s["n"], 100)
        self.assertAlmostEqual(s["frac_gt128"], 0.5)
        self.assertEqual(od.ct_intensity_stats(np.zeros((3, 3)))["n"], 0)
        self.assertEqual(od.ct_saturation_level(dict(median=149.0, frac_gt128=0.81)), "HIGH")
        self.assertEqual(od.ct_saturation_level(dict(median=115.0, frac_gt128=0.20)), "MEDIUM")
        self.assertEqual(od.ct_saturation_level(dict(median=77.0, frac_gt128=0.17)), "LOW")
        self.assertIsNone(od.ct_saturation_level(dict(median=None, frac_gt128=None)))


@network
class TestNetwork(unittest.TestCase):
    """Real bucket. Run with `pytest -m network` (skipped by default and in CI)."""

    def test_list_and_open(self):
        if os.environ.get("INKCHECK_NETWORK_TESTS") != "1":
            self.skipTest("set INKCHECK_NETWORK_TESTS=1 to run network tests")
        keys = od.list_predictions("PHerc0172", "20250917143559-w062_20250917143559205_flatboi")
        self.assertTrue(any(k.endswith(DS8) for k in keys))
        sv = od.open_surface_volume("s3://vesuvius-challenge-open-data/PHerc0172/segments/"
                                    "20250917143559-w062_20250917143559205_flatboi/surface-volumes/"
                                    "7.91um-53keV-volume-20241024131838.zarr/")
        self.assertEqual(sv.chunks[1:], (128, 128))
        self.assertEqual(sv.read(slice(16, 17), slice(0, 4), slice(0, 4)).shape, (1, 4, 4))


if __name__ == "__main__":
    unittest.main()
