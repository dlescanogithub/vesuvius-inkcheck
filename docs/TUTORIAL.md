# Tutorial: from an official open-data ink map to a verdict (5 minutes, CPU)

Notebook: [`notebooks/tutorial_5min.ipynb`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/notebooks/tutorial_5min.ipynb) (ships without outputs; run it top to bottom).
Everything is fetched at run time from public sources (~15 MB, cached in `$INKCHECK_CACHE` or `~/.cache/inkcheck`).

```bash
pip install "vesuvius-inkcheck[notebook] @ git+https://github.com/dlescanogithub/vesuvius-inkcheck"
jupyter execute notebooks/tutorial_5min.ipynb      # or open it in Jupyter / VS Code
```

> **Data terms.** Scroll data are CC BY-NC 4.0 with additional Vesuvius Challenge terms. Do not commit or redistribute the
> downloaded maps, volumes, or images drawn from them. The notebook draws no images.

## What it does

| Step | Input (public) | Check | Expected result |
|---|---|---|---|
| 1 | `PHerc0172/segments/20250917143559-w062…/ink-detection/downsampled/*-ds8.jpg` | `opendata.list_predictions`, `load_prediction`, `parse_prediction_name` | map (1575 x 1718 px) on a 63.28 um grid (7.91 um x ds8) |
| 2 | PHerc0343P: team 2.2 um map vs letters traced on an **infrared photograph** (built-in `343p-ir` example, pinned + sha256) | `inkcheck quick`: node A (band-pass r and stroke recall vs 192 shift/rotation nulls) + node N (wrong-place control) | **PASS**, control FAIL |
| 3 | Two official PHerc0172 models (`july_retreat`, `november19`) on the same segment | `run_check` of one against the other + wrong-place control | significant but **WEAK** (r_bp ~0.59, p ~0.005, stroke recall ~40%); control FAIL |
| 4 | Official surface volumes: PHerc0172 53 keV vs PHerc0343P 116 keV | `open_surface_volume`, `ct_intensity_stats`, `ct_saturation_level`; `saturation_check` on the map | 0172 **HIGH** risk (CT median ~149, 81% > 128) -> **WARN**; 0343P **LOW** (median ~77) |

Step 3 is deliberately not a PASS: agreement between two models is not ground truth, and at ds8 a stroke is only a few
pixels wide. Step 4 is a warning about the *scan*, not a verdict on the map: on PHerc0172, Reader V3 at 9 um saturated (56-67%
of valid pixels above the high level, against 0-26% elsewhere), so any PASS on that scan should be confirmed with
`saturation_check` on your model's own map.

## Reading official products with `inkcheck.opendata`

```python
from inkcheck import opendata as od

# ink maps: local path, https URL, s3:// URL or bare bucket key; .tif (full) or -ds8.jpg/.png (preview)
keys = od.list_predictions("PHerc0172", "20250917143559-w062_20250917143559205_flatboi")       # network listing
m, meta = od.load_prediction(keys[0])            # float32 array, metadata from the file name
meta["map_pixel_um"]                             # 63.28 = 7.91 um scan x ds8

# surface volumes (zarr v2, `layers-zarr`): group or array dir; uncompressed or numcodecs (pip install "vesuvius-inkcheck[zarr]")
sv = od.open_surface_volume("s3://vesuvius-challenge-open-data/PHerc0172/segments/<seg>/surface-volumes/<scan>-volume-<ts>.zarr/")
block = sv.read(sv.centred_window(17), slice(0, 512), slice(0, 512))     # (17, 512, 512) uint8, chunk-wise reads only
od.ct_saturation_level(od.ct_intensity_stats(block))                    # HIGH / MEDIUM / LOW
```

Conventions (as published in the open-data bucket, checked on its listing in Oct 2026; villa's `vesuvius.ink_detection` reads
surface volumes as `.zarr` the same way):

* prediction name `<scroll>-<segment ts>-<pixel>um[-<distance>m]-<energy>keV-volume-<volume ts>-<run ts>-<model>-tile<T>-stride<S>[-ds<k>].<ext>`;
  the map's pixel size is the scan's pixel size times `k` (1 for the full `.tif`);
* surface volumes are zarr v2, `dimension_separator "/"`, chunks `(layers, 128, 128)`, `fill_value 0`; missing chunks read as 0;
* `centred_window(n)` = the `n` middle layers, start `(layers - n) // 2`, the window used by inkcheck's node D runs.

Unit tests: `tests/test_opendata.py` (synthetic data, offline). The one network test is marked `network` and is skipped
unless `INKCHECK_NETWORK_TESTS=1 pytest -m network`.
