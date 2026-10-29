# F2 results — face-only node D, specificity set (pre-registered)

Prereg `PREREG_F2.md` (sha256 a92e1169…, committed in 35463e0 with `select_f2.py`, `job_f2_pod.py`, `score_f2.py`).
Selection committed before inference (3faaa89: 8 blanks, 30 positives, 16 segment visits; `regions_f2.json` sha256 b69aa74b…).
Inference 2026-10-28 22:54–23:02 ART on one RunPod community RTX A4500 (USD 0.19/h; 0.19 h wall; balance delta USD 0.04;
pod deleted, API GET → 404). Reader V3 = A, dense_native 16k = B, villa `--direction both`, 17 centred window layers of the
official surface volume. Scored with the committed `score_f2.py`, unchanged. Numbers only, no images.

## Verdict (primary): **SPECIFICITY_FAILED**

1. **Specificity (primary): FAILED** — 3/8 evaluable blanks flagged (allowed ≤ 1).
2. Sensitivity (secondary): **FAIL** — 10/30 positives flagged (need 20); 8/15 segments with a flagged positive (need 10); 1 positive not evaluable.
3. Controls (secondary): **FAIL** — (a) block-shuffle 2/30 flagged (need 0); (b) cyclic mismatch 2/30 flagged (allowed ≤ 3).
4. F2 label (parent §6 formula, reported only): **REJECTED**. The default rule stays node D v1 (F2 cannot change it).

Pre-stated reading (prereg §4): SPECIFICITY_FAILED → face-only flags no-ink regions too, so a face-only FLAG is not
evidence of ink on these data. Together with F1 (sensitivity 4/12), face-only node D is neither sensitive nor specific
enough on public segments; it stays a research rule, not the default.

Exploratory (prereg §5, no verdict change): 8 regions are saturation-risk on A; excluding saturated positives, 10/24 flagged.

## Limitations

* All 8 blanks come from PHerc0139 (the mechanical selection found blank tiles only in PHerc0139 segments),
  so specificity is tested on one scroll only.
* "Blank" = no ink in the reference (official) map, not proven ink-free. The flagged blanks (I up to 0.87) could be
  ink the reference map misses or two-model agreement on non-ink structure; F2 cannot tell which, and under the
  prereg both count as FLAG on a blank.
* S1 is a ratio and explodes when the other face has near-zero IoU (values in the hundreds below); the rule only uses S1 ≥ 2.

## Regions

| region | outcome | I best | face | S1 | valid | p (shift null) | sat |
|---|---|---|---|---|---|---|---|
| PHerc0009B__20250919133208\|pos0 | FLAG | 0.157 | fwd | 156.81 | 1.000 | 0.0052 | |
| PHerc0009B__20250919133208\|pos1 | FLAG | 0.310 | fwd | 3.55 | 1.000 | 0.0052 | |
| PHerc0139__20260215000000\|pos0 | NOTHING | 0.175 | rev | 1.03 | 0.996 | 0.0104 | sat |
| PHerc0139__20260215000000\|pos1 | NOTHING | 0.188 | rev | 1.91 | 1.000 | 0.0052 | sat |
| PHerc0139__20260215000000\|bla0 | NOTHING | 0.254 | fwd | 1.65 | 0.998 | 0.0052 | |
| PHerc0139__20260215000000\|bla1 | NOTHING | 0.489 | rev | 1.63 | 0.929 | 0.0052 | sat |
| PHerc0172__20250926150345\|pos0 | NOTHING | 0.130 | fwd | 1.29 | 1.000 | 0.0311 | |
| PHerc0172__20250926150345\|pos1 | FLAG | 0.127 | fwd | 14.36 | 1.000 | 0.0311 | |
| PHerc0500P2__20250716055232\|pos0 | NOTHING | 0.167 | fwd | 1.27 | 0.943 | 0.0052 | |
| PHerc0500P2__20250716055232\|pos1 | FLAG | 0.264 | fwd | 2.47 | 0.988 | 0.0052 | |
| PHerc0841__20260221022814\|pos0 | FLAG | 0.486 | fwd | 3.70 | 0.999 | 0.0052 | |
| PHerc0841__20260221022814\|pos1 | FLAG | 0.420 | fwd | 2.32 | 0.829 | 0.0052 | |
| PHerc0009B__20250919140325\|pos0 | NOTHING | 0.392 | fwd | 1.86 | 1.000 | 0.0052 | |
| PHerc0009B__20250919140325\|pos1 | NOT_EVALUABLE | 0.438 | fwd | 3.63 | 0.762 | 0.0052 | |
| PHerc0139__20260220000000\|pos0 | FLAG | 0.305 | rev | 2.53 | 0.997 | 0.0052 | |
| PHerc0139__20260220000000\|pos1 | NOTHING | 0.570 | fwd | 1.59 | 1.000 | 0.0052 | |
| PHerc0139__20260220000000\|bla0 | FLAG | 0.865 | fwd | 4.46 | 1.000 | 0.0052 | |
| PHerc0139__20260220000000\|bla1 | NOTHING | 0.236 | rev | 1.54 | 1.000 | 0.0052 | |
| PHerc0172__20250926153406\|pos0 | NOTHING | 0.013 | fwd | 3.90 | 1.000 | 0.3264 | sat |
| PHerc0172__20250926153406\|pos1 | NOTHING | 0.039 | fwd | 17.73 | 1.000 | 0.0933 | sat |
| PHerc0500P2__20250716055233\|pos0 | NOTHING | 0.133 | fwd | 1.30 | 0.977 | 0.0674 | |
| PHerc0500P2__20250716055233\|pos1 | NOTHING | 0.133 | rev | 1.41 | 1.000 | 0.0311 | |
| PHerc0814__20250929040153\|pos0 | FLAG | 0.236 | rev | 3.56 | 1.000 | 0.0052 | |
| PHerc0814__20250929040153\|pos1 | NOTHING | 0.633 | fwd | 1.73 | 0.997 | 0.0052 | |
| PHerc0139__20260306000000\|pos0 | NOTHING | 0.367 | rev | 1.41 | 0.995 | 0.0052 | |
| PHerc0139__20260306000000\|pos1 | FLAG | 0.441 | rev | 3.73 | 1.000 | 0.0052 | |
| PHerc0139__20260306000000\|bla0 | NOTHING | 0.237 | rev | 1.23 | 0.818 | 0.0052 | sat |
| PHerc0139__20260306000000\|bla1 | NOTHING | 0.612 | rev | 1.56 | 1.000 | 0.0052 | |
| PHerc0172__20251106133152\|pos0 | NOTHING | 0.073 | rev | 5.21 | 1.000 | 0.0207 | sat |
| PHerc0172__20251106133152\|pos1 | NOTHING | 0.022 | rev | 6.85 | 1.000 | 0.3109 | sat |
| PHerc0500P2__20250716055234\|pos0 | FLAG | 0.487 | fwd | 487.14 | 0.806 | 0.0052 | |
| PHerc0500P2__20250716055234\|pos1 | NOTHING | 0.378 | fwd | 1.07 | 0.954 | 0.0052 | |
| PHerc0814__20250930083742\|pos0 | NOTHING | 0.402 | fwd | 1.90 | 0.941 | 0.0052 | |
| PHerc0814__20250930083742\|pos1 | NOTHING | 0.141 | rev | 1.45 | 0.999 | 0.0155 | |
| PHerc0139__20260306000001\|pos0 | NOTHING | 0.389 | fwd | 1.74 | 0.990 | 0.0052 | |
| PHerc0139__20260306000001\|pos1 | NOTHING | 0.467 | fwd | 1.08 | 0.996 | 0.0052 | |
| PHerc0139__20260306000001\|bla0 | FLAG | 0.814 | fwd | 2.20 | 0.966 | 0.0052 | |
| PHerc0139__20260306000001\|bla1 | FLAG | 0.437 | fwd | 436.91 | 1.000 | 0.0052 | |

## Controls

| control | outcome | I best | S1 |
|---|---|---|---|
| PHerc0009B__20250919133208\|pos0\|a_block_shuffle | NOTHING | 0.024 | 8.86 |
| PHerc0009B__20250919133208\|pos0\|b_A_with_B_of_PHerc0009B__20250919133208\|pos1 | NOTHING | 0.044 | 44.31 |
| PHerc0009B__20250919133208\|pos1\|a_block_shuffle | NOTHING | 0.065 | 50.57 |
| PHerc0009B__20250919133208\|pos1\|b_A_with_B_of_PHerc0139__20260215000000\|pos0 | FLAG | 0.134 | 11.01 |
| PHerc0139__20260215000000\|pos0\|a_block_shuffle | FLAG | 0.105 | 10.87 |
| PHerc0139__20260215000000\|pos0\|b_A_with_B_of_PHerc0139__20260215000000\|pos1 | NOTHING | 0.056 | 56.36 |
| PHerc0139__20260215000000\|pos1\|a_block_shuffle | NOTHING | 0.009 | 9.49 |
| PHerc0139__20260215000000\|pos1\|b_A_with_B_of_PHerc0172__20250926150345\|pos0 | NOTHING | 0.032 | 10.78 |
| PHerc0172__20250926150345\|pos0\|a_block_shuffle | NOTHING | 0.047 | 46.54 |
| PHerc0172__20250926150345\|pos0\|b_A_with_B_of_PHerc0172__20250926150345\|pos1 | NOTHING | 0.003 | 3.13 |
| PHerc0172__20250926150345\|pos1\|a_block_shuffle | NOTHING | 0.022 | 21.88 |
| PHerc0172__20250926150345\|pos1\|b_A_with_B_of_PHerc0500P2__20250716055232\|pos0 | NOTHING | 0.036 | 35.89 |
| PHerc0500P2__20250716055232\|pos0\|a_block_shuffle | NOTHING | 0.015 | 7.42 |
| PHerc0500P2__20250716055232\|pos0\|b_A_with_B_of_PHerc0500P2__20250716055232\|pos1 | NOTHING | 0.000 | 0.00 |
| PHerc0500P2__20250716055232\|pos1\|a_block_shuffle | NOTHING | 0.002 | 2.39 |
| PHerc0500P2__20250716055232\|pos1\|b_A_with_B_of_PHerc0841__20260221022814\|pos0 | NOTHING | 0.038 | 2.20 |
| PHerc0841__20260221022814\|pos0\|a_block_shuffle | NOTHING | 0.021 | 5.25 |
| PHerc0841__20260221022814\|pos0\|b_A_with_B_of_PHerc0841__20260221022814\|pos1 | NOTHING | 0.021 | 21.44 |
| PHerc0841__20260221022814\|pos1\|a_block_shuffle | NOTHING | 0.021 | 21.14 |
| PHerc0841__20260221022814\|pos1\|b_A_with_B_of_PHerc0009B__20250919140325\|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0009B__20250919140325\|pos0\|a_block_shuffle | NOTHING | 0.003 | 2.72 |
| PHerc0009B__20250919140325\|pos0\|b_A_with_B_of_PHerc0009B__20250919140325\|pos1 | NOT_EVALUABLE | 0.000 | 0.00 |
| PHerc0009B__20250919140325\|pos1\|a_block_shuffle | NOTHING | 0.007 | 1.47 |
| PHerc0009B__20250919140325\|pos1\|b_A_with_B_of_PHerc0139__20260220000000\|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0139__20260220000000\|pos0\|a_block_shuffle | NOTHING | 0.064 | 22.50 |
| PHerc0139__20260220000000\|pos0\|b_A_with_B_of_PHerc0139__20260220000000\|pos1 | NOTHING | 0.000 | 0.33 |
| PHerc0139__20260220000000\|pos1\|a_block_shuffle | NOTHING | 0.030 | 30.46 |
| PHerc0139__20260220000000\|pos1\|b_A_with_B_of_PHerc0172__20250926153406\|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0172__20250926153406\|pos0\|a_block_shuffle | NOTHING | 0.073 | 49.16 |
| PHerc0172__20250926153406\|pos0\|b_A_with_B_of_PHerc0172__20250926153406\|pos1 | NOTHING | 0.029 | 1.58 |
| PHerc0172__20250926153406\|pos1\|a_block_shuffle | NOTHING | 0.005 | 4.96 |
| PHerc0172__20250926153406\|pos1\|b_A_with_B_of_PHerc0500P2__20250716055233\|pos0 | NOTHING | 0.000 | 0.11 |
| PHerc0500P2__20250716055233\|pos0\|a_block_shuffle | NOTHING | 0.000 | 0.06 |
| PHerc0500P2__20250716055233\|pos0\|b_A_with_B_of_PHerc0500P2__20250716055233\|pos1 | NOTHING | 0.001 | 0.52 |
| PHerc0500P2__20250716055233\|pos1\|a_block_shuffle | NOTHING | 0.028 | 28.40 |
| PHerc0500P2__20250716055233\|pos1\|b_A_with_B_of_PHerc0814__20250929040153\|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0814__20250929040153\|pos0\|a_block_shuffle | NOTHING | 0.077 | 77.31 |
| PHerc0814__20250929040153\|pos0\|b_A_with_B_of_PHerc0814__20250929040153\|pos1 | NOTHING | 0.043 | 43.17 |
| PHerc0814__20250929040153\|pos1\|a_block_shuffle | NOTHING | 0.032 | 5.40 |
| PHerc0814__20250929040153\|pos1\|b_A_with_B_of_PHerc0139__20260306000000\|pos0 | NOTHING | 0.032 | 4.69 |
| PHerc0139__20260306000000\|pos0\|a_block_shuffle | NOTHING | 0.000 | 0.10 |
| PHerc0139__20260306000000\|pos0\|b_A_with_B_of_PHerc0139__20260306000000\|pos1 | NOTHING | 0.009 | 8.94 |
| PHerc0139__20260306000000\|pos1\|a_block_shuffle | FLAG | 0.173 | 43.78 |
| PHerc0139__20260306000000\|pos1\|b_A_with_B_of_PHerc0172__20251106133152\|pos0 | NOTHING | 0.023 | 22.58 |
| PHerc0172__20251106133152\|pos0\|a_block_shuffle | NOTHING | 0.025 | 1.62 |
| PHerc0172__20251106133152\|pos0\|b_A_with_B_of_PHerc0172__20251106133152\|pos1 | NOTHING | 0.001 | 0.78 |
| PHerc0172__20251106133152\|pos1\|a_block_shuffle | NOTHING | 0.017 | 7.40 |
| PHerc0172__20251106133152\|pos1\|b_A_with_B_of_PHerc0500P2__20250716055234\|pos0 | NOTHING | 0.021 | 20.56 |
| PHerc0500P2__20250716055234\|pos0\|a_block_shuffle | NOTHING | 0.001 | 0.73 |
| PHerc0500P2__20250716055234\|pos0\|b_A_with_B_of_PHerc0500P2__20250716055234\|pos1 | NOT_EVALUABLE | 0.000 | 0.00 |
| PHerc0500P2__20250716055234\|pos1\|a_block_shuffle | NOTHING | 0.013 | 13.05 |
| PHerc0500P2__20250716055234\|pos1\|b_A_with_B_of_PHerc0814__20250930083742\|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0814__20250930083742\|pos0\|a_block_shuffle | NOTHING | 0.089 | 89.10 |
| PHerc0814__20250930083742\|pos0\|b_A_with_B_of_PHerc0814__20250930083742\|pos1 | NOTHING | 0.019 | 19.17 |
| PHerc0814__20250930083742\|pos1\|a_block_shuffle | NOTHING | 0.071 | 1.76 |
| PHerc0814__20250930083742\|pos1\|b_A_with_B_of_PHerc0139__20260306000001\|pos0 | NOTHING | 0.077 | 76.99 |
| PHerc0139__20260306000001\|pos0\|a_block_shuffle | NOTHING | 0.000 | 0.06 |
| PHerc0139__20260306000001\|pos0\|b_A_with_B_of_PHerc0139__20260306000001\|pos1 | FLAG | 0.102 | 101.93 |
| PHerc0139__20260306000001\|pos1\|a_block_shuffle | NOTHING | 0.030 | 30.15 |
| PHerc0139__20260306000001\|pos1\|b_A_with_B_of_PHerc0009B__20250919133208\|pos0 | NOTHING | 0.025 | 25.01 |

## Summary (from `results_f2.json`)

```json
{
 "N_pos": 30,
 "N_pos_segments": 15,
 "N_blank": 8,
 "N_blank_evaluable": 8,
 "blank_flagged": 3,
 "blank_flag_allowed": 1,
 "specificity": "SPECIFICITY_FAILED",
 "pos_flagged": 10,
 "pos_needed": 20,
 "pos_not_evaluable": 1,
 "segments_flagged": 8,
 "segments_needed": 10,
 "sensitivity_pass": false,
 "controls_a_flagged": 2,
 "controls_a": 30,
 "controls_b_flagged": 2,
 "controls_b": 30,
 "controls_pass": false,
 "f2_label_parent_formula": "REJECTED",
 "exploratory_unsaturated_pos": 24,
 "exploratory_unsaturated_pos_flagged": 10,
 "saturated_regions": 8
}
```

Files: `results_f2.json` (all numbers), `job_f2_meta.json` (pod job metadata), `run_log_f2.txt` (launcher log: GPU attempts, timings, deletion, balance), `DEVIATIONS.md`.
