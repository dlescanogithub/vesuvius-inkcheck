# Saturation risk table for public Vesuvius scans

**What this is:** a rough, CPU-only screen of every scan volume listed in the public open-data metadata
(`s3://vesuvius-challenge-open-data/metadata.json`). For each one it asks the same question:
*is the 8-bit CT that ink models see on this scan as bright and flat as PHerc0172 (53 keV), where we saw a
reader saturate, or is it like the 113-116 keV scans where things behaved normally?*

It is a triage aid, not a verdict. A HIGH row means "check `saturation_check` on your predictions for this
scan before trusting a score", nothing more.

Reproduce: `PYTHONPATH=src python scripts/saturation_risk_table.py --cache /tmp/satrisk --out results/saturation_risk`
(needs numpy; numcodecs for the blosc-compressed volumes; about 1-2 minutes and a few hundred MB of HTTP reads).
Machine-readable version with all columns: [`risk_table.csv`](risk_table.csv). Raw per-segment numbers: `raw_stats.json`.

## Summary

- **74 volume rows** (39 samples, 67 scans; one row per public volume export).
- **67 measured**: 20 on public surface volumes (best), 47 only on a coarse raw-volume pyramid level (weaker).
- **7 metadata-only**: all PHercParis4, withheld by policy (publication reservation), not measured.
- **HIGH**: 1 measured — **PHerc0172 volume 20241024131838** (53 keV, 7.91 µm): surface median 149
  (3 segments, range 145-153), 79% of non-zero pixels > 128; raw coarse median 148. Plus 2 metadata-only
  HIGH rows (PHercParis4 54 keV scans) that are flagged on energy alone and were not measured.
- **MEDIUM**: 16 (12 measured, 4 metadata-only). **LOW**: 55.
- Official ds8 ink prediction maps were checked on 12 volumes (39 maps): **0 saturated** by `saturation_check`
  (largest fraction > 128 was 0.26). These maps come from the official models, not from any model in this repo.

## Main findings

1. **PHerc0172 is the only measured outlier.** No other public scan with surface volumes comes close
   (next highest surface median 122).
2. **Energy alone is a poor predictor.** The other 53 keV scans (PHerc0332 and PHerc1667, 2023, 3.24/7.91 µm)
   measure LOW on the raw volume (medians 48-67), and the 1.129 µm 59 keV scans measure LOW on surface volumes.
   The energy rule would have flagged all of them.
3. **The 8-bit export matters as much as the beam.** PHerc0172 has two exports of the same scan:
   `20241024131838` (the one the public surface volumes are rendered from) is bright (raw median 148), while
   the re-export `20241024131839` is not (raw median 72, LOW). So "risk" belongs to a specific volume export,
   not to a scroll or a beam energy. Always say which volume your segments come from.

## Method

Thresholds were fixed from `results/irp/node_d_faceonly/f1/DIAG_0172.md` **before** measuring and were not
tuned afterwards. That diagnosis found the 0172 surface window had CT mean 154 ± 26 (p3-p97 114-206); the
113-116 keV segments had means of 75-111.

Measured level (on non-zero uint8 voxels):
- **HIGH**: median ≥ 130 or fraction > 128 ≥ 0.50
- **MEDIUM**: median ≥ 112 or fraction > 128 ≥ 0.25
- **LOW**: otherwise

Energy-only level (used only when nothing could be measured): ≤ 60 keV HIGH, 105-120 keV LOW, else MEDIUM.

Which number decides `risk` (precedence):
1. **surface**: up to 3 public surface volumes (`layers-zarr`) per volume; up to 10 non-empty 128×128 chunks
   each; middle half of the layers (same kind of window as DIAG_0172). Median of per-segment values.
2. **raw (coarse)**: up to 6 non-empty 128³ chunks near the centre of the first pyramid level ≤ 1600 voxels
   per side. Used only when no surface volume exists.
3. **metadata only**: the energy rule.

Prediction check: up to 3 official `ink-detection-downsampled` JPG maps per model and volume,
`inkcheck.node_d_v2.saturation_check` with default settings, on pixels ≥ 3 (to skip JPEG background noise).

## Why MEDIUM is weak

MEDIUM includes scans that behaved normally in our F1 evaluation (e.g. PHerc0841 9.37 µm, surface fraction
0.253, and PHerc0814 9.36 µm, surface median 115). Read MEDIUM as "a bit brighter than typical", not as a
warning. Only HIGH matched an actual failure.

## Caveats

- **Small samples.** At most 3 segments × 10 chunks per volume; values can shift a few grey levels with
  different segments. The surface median range column in the CSV shows the spread.
- **Raw-volume numbers are a weaker proxy.** They are block-averaged coarse levels, include space between
  sheets, and only calibrate against surface numbers when the export is the one surface volumes are rendered
  from (see the 0172 two-export example). The 47 raw-only rows should be read as indicative.
- **Window metadata can be misleading.** The bright 0172 export `20241024131838` is listed as
  `u16 [0, 65535]`, the same as the dark re-export, so the metadata probably does not describe the original
  8-bit conversion. The `u8_window` column is reported as-is.
- **Prediction checks describe official models only.** "0 saturated" says nothing about a different model on
  the same CT; run `saturation_check` on your own predictions.
- **Old 2023 volumes** for PHerc0332 and PHerc1667 are read from the `https://data.aws.ash2txt.org` access root
  given in the metadata (they are not in the open-data bucket itself).
- **PHercParis4** rows are metadata-only on purpose; no intensity numbers and no window are given for them.
- Only summary numbers are stored. No scroll images or crops are written (scan data is CC BY-NC).

## Table

surface / raw = median and fraction > 128 of non-zero 8-bit CT voxels. preds = saturated/checked official
ds8 prediction maps.

| sample | volume | keV | µm | u8 window | risk | basis | surf med | surf >128 | raw med | raw >128 | preds sat |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PHerc0009B | 20250521125136 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | surface | 110.0 | 0.18 | 102.0 | 0.117 | – |
| PHerc0009B | 20250820154339 | 77 | 2.401 | f32 [-0.03, 0.145] | **MEDIUM** | surface | 122.0 | 0.447 | 117.0 | 0.345 | 0/3 |
| PHerc0009B | 20260319104112 | 77 | 2.401 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 94.0 | 0.034 | – |
| PHerc0125 | 20250821151825 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 109.0 | 0.045 | – |
| PHerc0139 | 20250728140407 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | surface | 74.0 | 0.161 | 87.0 | 0.011 | – |
| PHerc0139 | 20251107132835 | 113 | 9.362 | u16 [0, 65535] | **LOW** | raw (coarse) | – | – | 58.0 | 0.0 | – |
| PHerc0139 | 20251107135911 | 113 | 9.362 | u16 [0, 65535] | **LOW** | raw (coarse) | – | – | 54.0 | 0.0 | – |
| PHerc0139 | 20250822062710 | 77 | 2.403 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 95.0 | 0.175 | – |
| PHerc0139 | 20260319133050 | 77 | 2.403 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 70.0 | 0.007 | – |
| PHerc0139 | 20250820105138 | 77 | 2.403 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 71.0 | 0.066 | – |
| PHerc0139 | 20260319133554 | 77 | 2.403 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 63.0 | 0.003 | – |
| PHerc0139 | 20260413113053 | 59 | 1.129 | u16 [0, 23140] | **LOW** | surface | 90.0 | 0.175 | 65.0 | 0.092 | 0/3 |
| PHerc0139 | 20260102150214 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | surface | 46.0 | 0.108 | 75.0 | 0.007 | 0/3 |
| PHerc0139 | 20260930100252 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | raw (coarse) | – | – | 79.0 | 0.007 | – |
| PHerc0172 | 20241024131838 | 53 | 7.91 | u16 [0, 65535] | **HIGH** | surface | 149.0 | 0.791 | 148.0 | 0.995 | 0/6 |
| PHerc0172 | 20241024131839 | 53 | 7.91 | u16 [0, 65535] | **LOW** | raw (coarse) | – | – | 72.0 | 0.0 | 0/2 |
| PHerc0175A | 20250521115057 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 104.0 | 0.075 | – |
| PHerc0175B | 20250521125822 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 114.0 | 0.164 | – |
| PHerc0191 | 20250821151635 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 107.0 | 0.075 | – |
| PHerc0211 | 20250821151803 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 111.0 | 0.097 | – |
| PHerc0257 | 20250821151750 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 109.0 | 0.061 | – |
| PHerc0268 | 20251110183117 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 123.0 | 0.363 | – |
| PHerc0306B | 20250521133212 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 106.0 | 0.069 | – |
| PHerc0332 | 20231027191953 | 53 | 3.24 | u16 [11464, 53384] | **LOW** | raw (coarse) | – | – | 67.0 | 0.003 | – |
| PHerc0332 | 20231117143551 | 53 | 7.91 | u16 [12160, 56960] | **LOW** | raw (coarse) | – | – | 66.0 | 0.003 | – |
| PHerc0332 | 20231201141544 | 70 | 3.24 | u16 [11784, 63304] | **LOW** | raw (coarse) | – | – | 61.0 | 0.0 | – |
| PHerc0332 | 20251211183505 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | raw (coarse) | – | – | 78.0 | 0.012 | – |
| PHerc0343 | 20250521140437 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 109.0 | 0.116 | – |
| PHerc0343P | 20250521134555 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | surface | 106.0 | 0.216 | 92.0 | 0.121 | – |
| PHerc0343P | 20260304131111 | 111 | 2.215 | f32 [-0.03, 0.145] | **LOW** | surface | 107.0 | 0.178 | 98.0 | 0.062 | 0/3 |
| PHerc0358 | 20250821151737 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 107.0 | 0.126 | – |
| PHerc0483A | 20250521140913 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 111.0 | 0.074 | – |
| PHerc0483B | 20251124083638 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 107.0 | 0.127 | – |
| PHerc0490A | 20250521151210 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 112.0 | 0.153 | – |
| PHerc0490B | 20250521151215 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 120.0 | 0.307 | – |
| PHerc0500P2 | 20250528085330 | 111 | 4.317 | f32 [-0.03, 0.145] | **LOW** | surface | 80.0 | 0.106 | 80.0 | 0.017 | – |
| PHerc0500P2 | 20250526151718 | 111 | 2.215 | f32 [-0.03, 0.145] | **LOW** | surface | 75.0 | 0.051 | 80.0 | 0.003 | 0/4 |
| PHerc0500P2 | 20250820143440 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | surface | 76.0 | 0.151 | 74.0 | 0.013 | – |
| PHerc0500P2 | 20250821110041 | 65.35 | 0.55 | – | **LOW** | raw (coarse) | – | – | 102.0 | 0.066 | – |
| PHerc0800 | 20250521135224 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | surface | 104.0 | 0.146 | 104.0 | 0.049 | – |
| PHerc0813 | 20250821151723 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 107.0 | 0.094 | – |
| PHerc0814 | 20250804134230 | 113 | 9.362 | f32 [-0.03, 0.145] | **MEDIUM** | surface | 115.0 | 0.381 | 106.0 | 0.098 | – |
| PHerc0814 | 20260521123630 | 59 | 1.129 | u16 [3000, 23000] | **LOW** | surface | 87.0 | 0.174 | 88.0 | 0.087 | 0/3 |
| PHerc0814 | 20260309142202 | 78 | 2.399 | f32 [-0.03, 0.22] | **MEDIUM** | surface | 89.0 | 0.251 | 97.0 | 0.039 | 0/3 |
| PHerc0826 | 20250821151701 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 98.0 | 0.027 | – |
| PHerc0841 | 20250821151531 | 113 | 9.366 | f32 [-0.03, 0.145] | **MEDIUM** | surface | 104.0 | 0.253 | 97.0 | 0.01 | – |
| PHerc0841 | 20260319124803 | 77 | 2.403 | f32 [-0.03, 0.19] | **LOW** | surface | 86.0 | 0.178 | 90.0 | 0.008 | 0/3 |
| PHerc0846A | 20250728152254 | 113 | 9.362 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 119.0 | 0.258 | – |
| PHerc0846A | 20260319102732 | 77 | 2.403 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 96.0 | 0.032 | – |
| PHerc0846B | 20250804142305 | 113 | 9.362 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 119.0 | 0.225 | – |
| PHerc1203 | 20250820131727 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 109.0 | 0.115 | – |
| PHerc1203 | 20260319130212 | 77 | 2.403 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 103.0 | 0.07 | – |
| PHerc1218 | 20250521120456 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | raw (coarse) | – | – | 118.0 | 0.245 | – |
| PHerc1299 | 20260309130042 | 78 | 2.399 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 77.0 | 0.002 | – |
| PHerc1447 | 20250521151220 | 116 | 8.64 | f32 [-0.03, 0.145] | **MEDIUM** | surface | 122.0 | 0.371 | 99.0 | 0.024 | – |
| PHerc1451 | 20250521151225 | 116 | 8.64 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 94.0 | 0.038 | – |
| PHerc1451 | 20260319101107 | 78 | 2.399 | f32 [-0.03, 0.2] | **LOW** | raw (coarse) | – | – | 84.0 | 0.05 | – |
| PHerc1545 | 20250821151648 | 113 | 9.362 | f32 [-0.03, 0.145] | **LOW** | raw (coarse) | – | – | 107.0 | 0.083 | – |
| PHerc1667 | 20231107190228 | 88 | 3.24 | u16 [12460, 61260] | **LOW** | raw (coarse) | – | – | 50.0 | 0.0 | – |
| PHerc1667 | 20231117161658 | 53 | 7.91 | u16 [12240, 59440] | **LOW** | raw (coarse) | – | – | 48.0 | 0.002 | – |
| PHerc1667 | 20251217075048 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | surface | 53.5 | 0.132 | 53.0 | 0.003 | 0/3 |
| PHerc1667 | 20260323082859 | 59 | 1.129 | u16 [1344, 29664] | **LOW** | surface | 40.0 | 0.102 | 40.0 | 0.066 | 0/3 |
| PHercMAN5 | 20260311104824 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | raw (coarse) | – | – | 86.0 | 0.204 | – |
| PHercMANB | 20260323091048 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | raw (coarse) | – | – | 83.0 | 0.007 | – |
| PHercMANBp | 20251216152116 | 78 | 2.399 | f32 [-0.03, 0.21] | **LOW** | raw (coarse) | – | – | 59.0 | 0.023 | – |
| PHercMANBp | 20260427100434 | 59 | 1.129 | u16 [16980, 51380] | **LOW** | raw (coarse) | – | – | 48.0 | 0.003 | – |
| PHercParis3 | 20260427095331 | 78 | 2.4 | f32 [-0.03, 0.19] | **LOW** | raw (coarse) | – | – | 92.0 | 0.026 | – |
| PHercParis4 | 20230205180739 | 54 | 7.91 | – | **HIGH** | metadata only | – | – | – | – | – |
| PHercParis4 | 20230206171837 | 54 | 7.91 | – | **HIGH** | metadata only | – | – | – | – | – |
| PHercParis4 | 20260310170716 | 74 | 45.532 | – | **MEDIUM** | metadata only | – | – | – | – | – |
| PHercParis4 | 20260310173927 | 110 | 45.532 | – | **LOW** | metadata only | – | – | – | – | – |
| PHercParis4 | 20260411134726 | 78 | 2.4 | – | **MEDIUM** | metadata only | – | – | – | – | – |
| PHercParis4 | 20260323153942 | 137 | 2.4 | – | **MEDIUM** | metadata only | – | – | – | – | – |
| PHercParis4 | 20260608103018 | 78 | 1.129 | – | **MEDIUM** | metadata only | – | – | – | – | – |
