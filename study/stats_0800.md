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
