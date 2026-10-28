# Why do ~9 µm ink models work on Paris 4 but not on PHerc0343P? A controlled negative-result study (CPU only)

*All numbers come from runs on one 8-vCPU CPU box (2 threads per job), from the scripts in `study/`, and were evaluated with `inkcheck` using identical settings: 192 search-matched shift nulls plus dihedral nulls, and stroke metrics with their own nulls. The raw JSON/PNG files are in `results/study/` and `results/`.*

## Question
Public ~9 µm ink checkpoints (`ink_9um` seed42/43, Erwin's `dense_native` and `soup`, Klavis's `dense9um`) are meant to run on the cheap native ~8–9 µm scans. On the held-out Paris 4 segment they recover letters (**PASS**). On PHerc0343P they do not (**WEAK**: the signal is significant but not letter-level). Is the cause (a) voxel size or blur, (b) noise, (c) the scan itself (energy and protocol), or (d) the scroll or segment?

*Scope note (Oct 27): newer readers (Reader v2/V3, D. Russo) were trained on PHerc0343P labels from the 2.215 µm teacher map, and that training set includes segment 20250511003658. The 343P result below covers only the five checkpoints listed. It is not a claim about the current best readers. [inkbench](https://github.com/inksweep/inkbench) ranks those readers on 343P.*

## Headline
1. **Blur dose-response on the same held-out segment (Paris 4, dense_native).** Letter-level detection survives an added XY Gaussian blur of FWHM ≈ 23 µm (PASS). It degrades from FWHM ≈ 34 µm (WEAK) and is gone at ≈ 68 µm (stroke recall at chance). 2× binning, i.e. 19.2 µm sampling, already drops the verdict to WEAK. (Paris 4 scores withheld: PHercParis4 publication reservation until 2027-06-25; verdicts only.)
2. **Noise.** Adding Gaussian noise of σ = 0.5× the volume SD is tolerated (PASS). At 1× the SD the verdict drops to WEAK, as on 343P.
3. **343P's native 8.64 µm scan is *not* blurrier or noisier than the working Paris 4 input** by the two proxies we measured:
   - the high-frequency spectral ratio is 0.034, between Paris 4's undegraded 0.048 and its 1 px blur 0.024, i.e. equivalent to a σ ≈ 0.5 px blur that Paris 4 tolerates with no loss;
   - the adjacent-layer high-pass correlation is 0.78 vs 0.53. Caveat: the render's trilinear sampling along the normal raises this.
4. **Same segment, other scan, all 5 checkpoints.** We rendered 343P from the published 2.215 µm / 111 keV surface volume, pooled to 8.86 µm with the Paris 4 recipe:
   - For `dense_native` and `dense9um`, r_bp rises from 0.28 / 0.26 to 0.40 / 0.39. Stroke recall stays at 0.15–0.25 against a null of 0.06.
   - For `ink_9um` s42/s43 and `soup`, r_bp is 0.19–0.23 and stroke recall falls to chance (0.05–0.07).
   - All 7 runs are **WEAK**. The result is insensitive to the depth window: dn w4/5/6 give r_bp 0.400 / 0.396 / 0.397.
   - **The 343P failure is mostly not the native scan or its voxel size.**
5. **Not letter size either.** On a common 19.2 µm grid the two references have similar ink fraction, median stroke area (343P ≈ 0.19 mm²) and stroke width (Paris 4 reference values withheld until 2027-06-25; `results/study/stroke_geometry.json` ships the 343P side).
6. **Conclusion.** For 343P, the ink evidence that the 2.2 µm reference model uses is not available to ~9 µm models, even from the 2.2 µm data once it is averaged to ~9 µm. This looks scroll- or ink-specific: fine-scale (< ~20–30 µm) ink texture or low contrast, beyond what plain resolution can explain. On Paris 4, the same models and the same pooling preserve it. **Practical consequence: validate each scroll with a labelled segment (inkcheck) before spending compute on unlabelled ~9 µm segments of that scroll.**

## 0800 / 1203: what an unvalidated run looks like
dense_native predictions on unlabelled segments from our Phase 2 run (`study/scan_stats.py`, `results/scan_stats.txt`). p is the probability after removing label smoothing; "blobs" are components with p > 0.5 and area ≥ 0.02 mm².

| map | area cm² | mean p | frac p>0.5 | frac p>0.8 | band-pass SD | blobs/cm² |
|---|---|---|---|---|---|---|
| 343P native (known ink, WEAK) | 4.35 | 0.174 | 0.075 | 0.018 | 0.126 | 19.5 |
| PHerc0800, 6 segments (range) | 0.6–3.1 | 0.14–0.25 | 0.027–0.140 | 0.006–0.034 | 0.092–0.132 | 8.9–22.2 |
| PHerc1203, 9 segments (range) | 4.4–13.8 | 0.24–0.42 | 0.095–0.444 | 0.006–0.048 | 0.093–0.123 | 9.4–27.1 |
| **0800 …222030940 forward** | 3.05 | 0.168 | 0.044 | 0.017 | 0.099 | 8.9 |
| 0800 …222030940, **depth-shuffled null** | 3.05 | 0.146 | 0.015 | 0.0035 | 0.098 | 10.8 |
| 0800 …222030940, **depth-reversed null** | 3.05 | 0.164 | 0.017 | 0.0034 | 0.088 | 11.2 |

Correlation of the forward map with its own nulls on 0800 …222030940:
- band-pass r is **0.45** with the shuffled null and **0.53** with the reversed null;
- raw r is 0.35 and 0.44.

Reading:
- The confident tail (p > 0.8) is about 5× larger with the correct depth order. So the model does use depth ordering.
- However, most of the *spatial structure* of the map survives destroying the depth order:
  - the band-pass texture SD is unchanged;
  - there are as many blobs per cm²;
  - the maps correlate r ≈ 0.5 with their own null.
  So blob patterns on an unvalidated 0800 map are mostly papyrus/surface texture, not ink.
- On 1203, 10–44 % of the area has p > 0.5. That is far above what known-ink 343P shows (7.5 %), and it signals a domain shift rather than ink.
- Neither scroll has a public reference map, so inkcheck cannot be applied. Combined with the 343P result, we **do not claim ink on 0800 or 1203**.

**Phase 2 aggregate.** These numbers are taken from `preds/phase2_summary.json`, not recomputed:
- Setup: dense_native, window 7–23, 4 OMP threads.
- Metric: tiles are 6×6 mm. A tile "exceeds null" when its density of stroke-sized components (0.03–1.5 mm², p > 0.5) is above the 99th percentile of 74 null tiles (22.9 /cm²).

| set | segments | analysed cm² | infer s | s/cm² | tiles | tiles > null p99 | tiles with line periodicity p<0.05 |
|---|---|---|---|---|---|---|---|
| 343P control (known ink, illegible) | 1 | 2.75 | 195 | 71 | 19 | **12 (63 %)** | 0 |
| PHerc0800 @ 8.64 µm | 6 | 8.02 | 600 | 75 | 65 | 10 (15 %) | 0 |
| PHerc1203 @ 9.362 µm | 22 | 112.1 | 4803 | 43 | 1133 | 215 (19 %) | 0 |
| depth nulls (343P, 0800) | 4 | – | 108–190 | – | 74 | 1 | 0 |

How to read this:
- Exceeding the null blob density is **necessary but not sufficient**. The known-ink 343P control exceeds it in 63 % of tiles and is still not legible.
- The line-periodicity test has no power: the published 343P letter map itself only reaches p = 0.24.
- So the 19 % of 1203 tiles above the null are *candidate* regions for a high-resolution re-check, not ink detections.


## Tables
Paris 4 degradations (dense_native; verdicts and scan proxy only, scores withheld until 2027-06-25) and the 343P two-scan control. Generated by `study/collect.py` (Paris 4 rows redacted to verdicts); figure `figures/tolerance_curve.png`.

| P4 input variant | XY blur FWHM added (µm) | adj-layer HP corr (scan proxy) | verdict |
|---|---|---|---|
| original 9.6 µm | 0 | 0.53 | PASS |
| Gaussian σ=0.5 px | 11.3 | 0.55 | PASS |
| Gaussian σ=1 px | 22.6 | 0.57 | PASS |
| Gaussian σ=1.5 px | 33.9 | 0.59 | WEAK |
| Gaussian σ=2 px | 45.2 | 0.61 | WEAK |
| Gaussian σ=3 px | 67.8 | 0.64 | WEAK |
| 2× bin (19.2 µm sampling) | – | 0.55 | WEAK |
| Gaussian noise σ=16 | – | 0.32 | PASS |
| Gaussian noise σ=32 | – | 0.15 | WEAK |
| Gaussian noise σ=48 | – | 0.08 | WEAK |

| PHerc0343P 20250511003658 input | model | window | r_bp (null) | raw r | AUC | breakeven F1 | stroke recall (null) | stroke prec. | verdict |
|---|---|---|---|---|---|---|---|---|---|
| native 8.64 µm / 116 keV | dn | 7 | 0.277 (0.054) | 0.40 | 0.770 | 0.31 | 0.16 (0.06) | 0.25 | WEAK |
| native 8.64 µm / 116 keV | kl | 7 | 0.257 (0.053) | 0.37 | 0.753 | 0.29 | 0.18 (0.06) | 0.19 | WEAK |
| native 8.64 µm / 116 keV | s42 | 7 | 0.152 (0.050) | 0.20 | 0.632 | 0.21 | 0.19 (0.09) | 0.14 | WEAK |
| native 8.64 µm / 116 keV | s43 | 7 | 0.162 (0.051) | 0.21 | 0.651 | 0.21 | 0.12 (0.07) | 0.15 | WEAK |
| native 8.64 µm / 116 keV | soup | 7 | 0.178 (0.052) | 0.23 | 0.662 | 0.23 | 0.14 (0.08) | 0.15 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | dn | 4 | 0.400 (0.045) | 0.44 | 0.804 | 0.38 | 0.25 (0.06) | 0.30 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | dn | 5 | 0.396 (0.045) | 0.43 | 0.803 | 0.37 | 0.15 (0.06) | 0.26 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | dn | 6 | 0.397 (0.045) | 0.43 | 0.797 | 0.36 | 0.15 (0.06) | 0.25 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | kl | 5 | 0.389 (0.045) | 0.41 | 0.807 | 0.36 | 0.22 (0.06) | 0.25 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | s42 | 5 | 0.187 (0.045) | 0.19 | 0.643 | 0.21 | 0.07 (0.06) | 0.14 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | s43 | 5 | 0.188 (0.043) | 0.17 | 0.657 | 0.21 | 0.07 (0.06) | 0.14 | WEAK |
| 2.215 µm / 111 keV pooled to 8.86 µm | soup | 5 | 0.229 (0.046) | 0.24 | 0.670 | 0.24 | 0.05 (0.06) | 0.14 | WEAK |


## Key figure: model performance vs scan voxel size on the same segment

This figure is planned, pending the CPU hi-res run (its `summary.json`).
- **Same segment, same reference.** PHerc0343P 20250511003658 is scored by inkcheck against the published new_canon map at these voxel sizes:
  - 2.215 µm, the native high-resolution scan;
  - ≈4.4 µm (2× pool);
  - 8.86 µm (4× pool), measured: r_bp ≈ 0.40;
  - 8.64 µm, the native 116 keV scan, measured: r_bp 0.28.
- **Plotted quantities:** r_bp and stroke recall vs voxel size, with the Paris 4 blur tolerance (verdicts) overlaid on an FWHM axis.
- **PHerc1203:** a 2.4 µm crop vs the 9.362 µm prediction on the same area, a qualitative panel only, since there is no reference map.
- **If hi-res inference also fails:** the conclusion strengthens to "the scroll-specific gap is not resolution".
- **If hi-res succeeds:** voxel size is the lever, and the ~9 µm models need either domain adaptation or a higher-resolution input.

*Status as of Oct 27, 18:35 ART: the CPU-only hires run is in progress and has not yet written its summary. This section will be filled in from that summary; until then, only the two 8.6–8.9 µm points above are measured.*

## PHerc1203 at 2.4 µm: is there more ink signal at higher resolution? (pre-registered, results pending)

A separate CPU-only run renders three PHerc1203 zones from the 2.403 µm / 77 keV scan and compares them with the 9.362 µm / 113 keV prediction on the same area. Its design was written down before any 2.4 µm data was viewed (pre-registration notes, §0):
- **Zones:** three 6×6 mm tiles, chosen by a fixed rule from the phase-2 dn map (`tools/select_zones.py`): 231446965, 230830031 (mesh 031) and 221856743.
- **Metrics** on a common ~9.6 µm grid: stroke-sized components per cm², frac(p>0.5), median stroke width, and r with the native 9.36 µm prediction. The null is the same model on depth-reversed input.
- **Candidate rule:** density ≥ 2× the null, at least two checkpoints agreeing (r ≥ 0.3), and stroke-like shapes 0.1–0.5 mm wide. **No zone is called "ink"**, because 1203 has no reference map.
- **Model-free texture features** are used on 1203 only if they first pass inkcheck on 343P (r_bp > 0.2, p < 0.006).

<!-- HIRES_1203_RESULTS: filled by study/fill_hires.py from the hires run summary.json -->
*Results pending: the run has not written `summary.json` yet.*
<!-- /HIRES_1203_RESULTS -->

## How to use this as a diagnostic ("no ink" vs "not recovered yet")

| Observation on a new segment | What it suggests | Next step |
|---|---|---|
| **FAIL** against a published map: r_bp is not above search-matched nulls | the model sees nothing that the reference sees (wrong placement, wrong surface, or no transfer at all) | check `--ref-origin` and the surface; try another checkpoint |
| **WEAK**: significant r_bp, stroke recall < 0.5 | the ink signal is present but not recovered at letter level, so it is **not** "no ink" | compare scan proxies with the dose-response; run the two-scan test if a second scan exists |
| Scan proxies (HF spectral ratio, inter-layer SNR) are **worse** than the tolerated Paris 4 range (blur FWHM > ~30 µm equivalent, or noise ≥ 1× SD) | scan quality alone can explain the loss | a higher-resolution or less noisy scan should help |
| Proxies are **within** the tolerated range and a second scan of the same segment gives the same verdict (343P) | scroll- or ink-specific domain gap | fine-tune or adapt on that scroll's labels (e.g. Reader v2's 343P labels), then re-check on held-out segments |
| No reference (unlabelled scroll) | inkcheck cannot score it | use depth-reversed and shift nulls. Treat the map as a lead, never as ink |

## Methods
- **Paris 4 control.** Segment 20231005123336 is not among the ink_9um training segments. Input: a 1536² crop at 9.6 µm (level 2 of the 2.4 µm / 78 keV volume, mean-pooled 4× in depth), layers 5–21. Reference: `new_canon` ds8 (19.2 µm).
- **Degradations** (`study/make_degraded_p4*.py`): XY Gaussian blur σ = 0.5–3 px (FWHM = 2.355 σ × 9.6 µm), 2× bin plus nearest upsample, and additive Gaussian noise. All are applied to the uint8 input volume before inference.
- **343P.** Segment 20250511003658.
  - Native input: our trilinear render of the public 8.64 µm mesh on the 116 keV volume, window 7–23.
  - Two-scan input: the published 2.215 µm / 111 keV surface volume, OME-Zarr level 2 (8.86 µm XY), mean-pooled 4× in z. The window was shifted −2 layers to match the depth-intensity profile; windows 4 and 6 were checked for sensitivity.
  - Reference: the published `new_canon` 2.215 µm map. Mask: rendered papyrus.
- **Proxies** (`study/psd_compare.py`, `study/layer_snr.py`): radially averaged power spectra on fully valid 512² tiles, with the 10–25 / 2–10 cycles/mm power ratio. Also the Pearson correlation of adjacent depth layers after subtracting a σ = 60 µm low-pass.
- **Verdict rule (fixed before real data):** PASS needs p(r_bp) ≤ 0.01, p(stroke recall) ≤ 0.05, r_bp ≥ 0.20 and stroke recall ≥ 0.50.

## Limitations
- There are only two labelled controls; a third scroll would strengthen point 6.
- The references are themselves model outputs (`new_canon`), not ground truth.
- Blur and noise are synthetic stand-ins for real scan differences.
- We did not run the 2.2 µm-native models on CPU; that is too slow here.
