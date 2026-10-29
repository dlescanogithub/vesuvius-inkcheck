# Ink card schema (report v1)

Every `inkcheck` run writes `PREFIX.card.json`, a per-segment **ink card** that follows
[`schemas/inkcheck-report-v1.json`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/schemas/inkcheck-report-v1.json)
(JSON Schema draft 2020-12; also shipped inside the package as `inkcheck/schemas/inkcheck-report-v1.json`).

| block | content |
|---|---|
| `schema_version`, `kind`, `created_utc` | `"1.x"`, `"inkcheck.ink-card"`, UTC timestamp |
| `segment` | `scroll`, `segment_id`, optional `label`, `region` |
| `verdict` | `final` (PASS / WEAK / FAIL / INVALID), `node_A`, `node_N` (NO_CONTROL_PASSES / CONTROL_PASSED / null), `summary` |
| `metrics` | `r_bandpass`, `r_bandpass_p`, null mean / sd / max, `n_shift_nulls` (usable) and `n_shift_nulls_requested`, `r_raw`, `auc_raw`, `breakeven_f1`, `stroke_recall` (+ `stroke_recall_chance`), `stroke_precision`, `n_ref_strokes`, `overlap_cm2`, `analysis_um`, `shift_um`, `r_bandpass_ci95` |
| `thresholds` | `alpha_r`, `min_r_bp`, `min_stroke_recall` used |
| `controls` | list of `{name, kind, expected, verdict, r_bandpass}` |
| `saturation` | `checked` (false if the map is not 8-bit), `saturated`, `median`, `frac_high`, `threshold`, `n`, `rule` |
| `warnings` | free-text warnings (low power, saturation, ...) |
| `provenance` | `inkcheck_version`, `prereg_sha256` (64-hex or null), `model`, `scan`, `prediction`, `reference`, full `config` |
| `extra` | producer-specific, free-form |

Rules beyond the schema (checked by `inkcheck report --validate`): `final` equals `node_A` unless a control passed,
in which case `final` must be `INVALID`.

**Versioning.** `1.x` is additive: new optional fields may appear; existing fields keep their meaning. Consumers must
accept any `1.x`. A breaking change gets a new file (`inkcheck-report-v2.json`).

## Validate and render

```bash
inkcheck report --validate out/*.card.json               # uses jsonschema if installed, else the built-in validator
inkcheck report --render out/seg.card.json > seg.md
```

```python
from inkcheck.card import build_card, validate, render_markdown
```

## Example (illustrative numbers)

```json
--8<-- "schemas/examples/example.card.json"
```

## The schema

```json
--8<-- "schemas/inkcheck-report-v1.json"
```
