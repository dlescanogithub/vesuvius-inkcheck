# vesuvius-inkcheck

**Does an ink-detection model see *known* ink at this resolution?** `inkcheck` compares a predicted ink map of a
Herculaneum papyrus segment against a published reference ink map of the same segment (possibly at a different voxel
size), registers them, and scores band-pass correlation, AUC and stroke recall against **search-matched shift nulls**.
It is the node-A check of the **Ink Recoverability Protocol (IRP)**, a CPU-only, pre-registered decision tree for
Vesuvius Challenge ink maps.

```bash
pip install vesuvius-inkcheck          # import name and command: inkcheck; Python >= 3.10, CPU only
inkcheck quick                         # ~2 min: public map vs traced letters -> PASS; wrong-place control -> FAIL
inkcheck PRED.tif REF.png --pred-um 9.6 --ref-um 19.2 --out out/seg   # verdict + JSON + PNG + ink card
inkcheck report --validate out/seg.card.json                          # validate against the v1 report schema
```

Every run writes an **ink card** (`PREFIX.card.json` + `PREFIX.card.md`): verdict (PASS / WEAK / FAIL, or INVALID
when a negative control passes), metrics, controls, a saturation warning and provenance (model, scan,
pre-registration hash, inkcheck version), following the versioned JSON Schema
[`inkcheck-report-v1.json`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/schemas/inkcheck-report-v1.json).

- `inkcheck.opendata` reads official open-data ink maps and `layers-zarr` surface volumes straight from the public bucket.
- A reusable GitHub Action runs the check on model pull requests.
- Extras: `[zarr]` compressed surface volumes, `[schema]` full JSON Schema validation, `[notebook]`, `[docs]`, `[test]`.

Documentation: https://dlescanogithub.github.io/vesuvius-inkcheck/ ·
Source, protocol, results and caveats: https://github.com/dlescanogithub/vesuvius-inkcheck ·
Changelog: https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/CHANGELOG.md

Scroll data are not shipped. Vesuvius Challenge data are CC BY-NC 4.0 (see https://scrollprize.org/data); inkcheck
fetches public inputs at run time. Code: MIT.
