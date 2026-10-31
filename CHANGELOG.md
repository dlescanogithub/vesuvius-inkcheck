# Changelog

All notable changes to `inkcheck` / IRP. Versions follow [semantic versioning](https://semver.org/) (0.x: the API may still change).

## [0.3.2] - 2026-10-31

### Added
- **In-sample flags (known training overlap)**: new `inkcheck.training_overlap` (`is_in_sample(model, scroll, segment)`
  -> True / False / None, `lookup()`, `load_registry()`). Ink cards from `inkcheck` and `inkcheck card` record
  `provenance.training_overlap` (optional, additive to schema 1.x) and warn `in-sample (training overlap)` when the
  model trained on the segment; `leaderboard.csv` gains an `in_sample` column. Scores, verdicts and exit codes are
  unchanged; unknown models or segments get no flag. Built-in pairs from @jo-tud on ScrollPrize/villa#2349 (label
  `.zattrs` `source_surface_volume`): PHerc0139 public w030 (= label pherc0139-w017) and w045 (= pherc0139-w029) are
  in-sample for `ink_9um` s42/s43 and `ink9um-dense-native` and held out for `ink-8um-v8in`; v8-in's training cases
  w033/w035/w041/w044 are recorded as stated (naming to be confirmed); PHerc0343P is held out for all three (`ink_9um`, dense-native, v8-in).
  `--training-overlap FILE` adds user pairs. Tests in `tests/test_training_overlap.py`.

## [0.3.1] - 2026-10-30

### Fixed
- **Exit codes**: a crash or a bad input no longer looks like a verdict. Uncaught exceptions, unreadable inputs,
  `SystemExit("message")` and argparse usage errors now exit **4** (ERROR) from every subcommand, with the message on
  stderr; before, a traceback exited 1 (= WEAK) and a usage error 2 (= FAIL). Verdict codes are unchanged: 0 PASS,
  1 WEAK, 2 FAIL, 3 INVALID (`inkcheck quick`). Reported in #1 by @LynnHenry.
  `inkcheck.cli.verdict_exit_code` and `EXIT_*` constants; tests in `tests/test_exit_codes.py`.

### Docs
- `results/rescore/rescore_0841.sh`: comment explaining that `--ref-origin 333.04,333.13` belongs to the cropped
  reference `results/newcases/refs/0841-w00__map.png` (cut by `results/newcases/prep_refs.py` with a 0.8 mm margin)
  paired with the 2560 x 2560 prediction crop at (512, 1536); a full-canvas w00 render against the full map uses
  `0,0` (#1).

## [0.3.0] - 2026-10-29

### Added
- **Ink card v1**: every `inkcheck PRED REF` run (and `inkcheck quick`) writes `PREFIX.card.json` + `PREFIX.card.md`,
  a per-segment report following the versioned JSON Schema `schemas/inkcheck-report-v1.json` (draft 2020-12, also
  shipped in the package): segment, verdict (final / node A / node N), metrics, thresholds, controls, saturation,
  warnings and provenance (inkcheck version, model, scan, prediction, reference, config, pre-registration sha256).
  `inkcheck.card` (`build_card`, `validate`, `render_markdown`, `write_card`); `inkcheck report --validate` /
  `--render`; `inkcheck card CHECK.json [--control ...]`; provenance options `--scroll --segment --model --model-run
  --scan --prereg --prereg-sha256`; `--no-card`. Validation uses `jsonschema` when installed (`[schema]` extra) and a
  built-in validator otherwise. Synthetic example card in `schemas/examples/`.
- **PyPI-ready packaging** as `vesuvius-inkcheck` (import name and command stay `inkcheck`): single-sourced version,
  SPDX license metadata, `README_PYPI.md`, `MANIFEST.in`, `CITATION.cff`, `.zenodo.json`, and a tag-only release
  workflow (`.github/workflows/release.yml`) using PyPI trusted publishing. It stays inert until a PyPI pending
  publisher and a GitHub `pypi` environment exist.
- **Documentation site** (`mkdocs.yml`, mkdocs-material + mkdocstrings): getting started, tutorial, protocol, ink-card
  schema, CI, leaderboard, reference set, API reference and FAQ. `mkdocs build --strict` passes; `[docs]` extra;
  `.github/workflows/docs.yml` deploys to GitHub Pages on `workflow_dispatch` or a version tag only.
- **GitHub Action** (`action.yml`, composite) for model pull requests: runs the check and a wrong-place control,
  validates the ink card, writes it to the job summary, exposes `verdict`/`card` outputs and fails on FAIL/INVALID
  (configurable). It wraps `scripts/inkcheck_ci.sh`, which runs the same steps locally. Example workflow:
  `examples/ci/model-pr.yml`. CI exercises the wrapper on the synthetic pair.
- **Public leaderboard** (`leaderboard/`): official open-data ink maps scored against the public `ink_9um` labels
  with the inkcheck protocol; numbers only (CSV, summary JSON, one ink card per pair), with method and caveats.
  v0: one official model family (`new_canon_autoresearch_recipe`) on 12 labelled segments from 3 scrolls
  (2 PASS, 4 WEAK, 6 FAIL; wrong-place control FAIL 12/12). The 12 pairs whose map is on another scan's canvas are
  listed as excluded, not force-registered. It measures agreement with the public labels, not a held-out test.
- **Reference set v0** (`refset/`): deterministic list of ink and no-ink regions (coordinates, fractions, label
  hashes) from the public `ink_9um` labels, with coverage statistics and limitations. v0: 192 tiles of 0.5 mm
  (96 ink, 96 no-ink) on 12 segments from 3 scrolls (PHerc0139, PHerc0814, PHerc1667); PHercParis4 excluded.

### Changed
- Distribution renamed `inkcheck` -> `vesuvius-inkcheck` (pip extras are now `vesuvius-inkcheck[zarr]` etc.).
- `inkcheck report`: case files are optional when `--validate` / `--render` is given.
- Version 0.2.0 -> 0.3.0.

### Fixed

- Shift nulls that cannot be scored (too little valid overlap after the shift, e.g. a small or fragmented
  reference mask) are no longer counted. `n_shift_nulls` is now the number of usable nulls
  (`n_shift_nulls_requested` is the number drawn), the null mean / sd / max ignore unusable nulls (they were NaN),
  and the "smallest attainable p is above alpha" warning uses the usable count. Verdicts on full-overlap inputs
  are unchanged (p was already computed over usable nulls only); the change makes null-limited checks visible.

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
