# Ink card: PHercXXXX / synthetic example

**Verdict: PASS** — known ink reproduced

| node | result |
|---|---|
| A — known ink reproduced beyond search-matched nulls? | PASS |
| N — negative controls fail? | NO_CONTROL_PASSES |
| saturation | ok |

## Metrics

| metric | value |
|---|---|
| band-pass r | 0.410 |
| p (shift nulls) | 0.005 |
| null mean / max | 0.010 / 0.120 |
| shift nulls | 192 |
| r 95% CI (tile bootstrap) | [0.300, 0.500] |
| raw r | 0.300 |
| AUC | 0.810 |
| break-even F1 | 0.420 |
| stroke recall (chance) | 0.71 (0.20) |
| stroke precision | 0.50 |
| reference strokes | 40 |
| overlap | 3.20 cm² |
| analysis grid | 19.20 µm |

Thresholds: alpha_r = 0.01, min_r_bp = 0.2, min_stroke_recall = 0.5

## Controls

| control | expected | verdict | band-pass r |
|---|---|---|---|
| wrong_place | FAIL | FAIL | 0.012 |

Saturation: median 41, fraction above 128: 0.07 → ok (8-bit map: saturated if >= 50% of valid pixels are above 128 (node_d_v2.saturation_check)).

## Provenance

| field | value |
|---|---|
| model | example-model (run 20260101000000) |
| scan | 2.399um-0.22m-78keV-volume-EXAMPLE · 2.399 µm · 78 keV |
| prediction | example_pred.tif |
| reference | example_ref.png |
| pre-registration sha256 | none (not pre-registered) |
| inkcheck | 0.2.0 · card schema 1.0 · 2026-10-29T00:00:00Z |
