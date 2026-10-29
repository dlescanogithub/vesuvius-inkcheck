# Changelog

All notable changes to `inkcheck` / IRP. Versions follow [semantic versioning](https://semver.org/) (0.x: the API may still change).

## [0.2.0] - 2026-10-29

### Added
- `inkcheck.opendata`: read official Vesuvius Challenge open-data products by local path, `https://` URL, `s3://` URL or
  bare bucket key: ink maps (full `.tif`, downsampled `-ds8.jpg/.png`), file-name metadata (`parse_prediction_name`, map
  pixel size = scan pixel x ds), bucket listing (`list_keys`, `list_predictions`), lazy chunk-wise reads of `layers-zarr`
  surface volumes (zarr v2, uncompressed or any numcodecs codec), `ct_intensity_stats` and `ct_saturation_level`
  (same fixed thresholds as `scripts/saturation_risk_table.py`). Offline tests on synthetic data: `tests/test_opendata.py`.
- 5-minute tutorial: `notebooks/tutorial_5min.ipynb` + `docs/TUTORIAL.md` (official map -> verdict; PASS-like and
  saturation-WARN examples; public data fetched at run time, no outputs or images shipped).
- `network` pytest marker (`pytest.ini`); network tests also need `INKCHECK_NETWORK_TESTS=1`.
- Optional extras: `[zarr]` (numcodecs), `[notebook]` (nbformat, nbclient, ipykernel); numcodecs added to `[test]`.
- Node D face-only, fresh set **F2** (specificity, >= 4 blanks): prereg `results/irp/node_d_faceonly/f2/PREREG_F2.md`
  (sha256 `a92e1169…`), selection, pod script and scorer committed before any F2 data; results in
  `results/irp/node_d_faceonly/f2/RESULTS.md`. Outcome: **SPECIFICITY_FAILED** (3 of 8 blanks flagged, allowed 1;
  sensitivity 10/30; controls 2/30 + 2/30; parent label REJECTED). Face-only stays a non-default research rule.
- `CHANGELOG.md`; README install one-liner, tutorial link and CI badge.

### Changed
- CI runs the unit tests offline on CPU with `-m "not network"`; can be started by hand (`workflow_dispatch`).
- Version 0.1.0 -> 0.2.0 (`pyproject.toml`, `inkcheck.__version__`).

## [0.1.0] - 2026-10-28

Public repository state up to (commit `0df1128`): `inkcheck` node A check with search-matched shift nulls,
IRP readability cards (`inkcheck report`), `inkcheck quick` 5-minute quickstart, calibration and triage tables, node D
v1/v2 and the pre-registered face-only option with its F1 validation (REJECTED), saturation check and saturation risk table.
