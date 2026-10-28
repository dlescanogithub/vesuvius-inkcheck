# F1 results — face-only node D on 6 independent open-data segments (pre-registered)

Prereg `../PREREG_NODE_D_FACEONLY.md` (sha256 ba553d03…, commit 22feecb). Selection committed before inference (2df749f);
scorer and pod script committed before inference (22502c6). Inference 2026-10-28 20:38–20:42 ART on one RunPod RTX 3090
(Reader V3 = A, dense_native 16k = B, villa `--direction both`, 17 centred window layers of the official surface volume). Numbers only.

## Verdict: **REJECTED**

1. Sensitivity: **FAIL** — 4/12 positives flagged (need 8); 3/6 segments (need 4). 1 positive not evaluable (< 80 % valid CT).
2. Specificity: **UNTESTED** — only 2 blanks exist (need ≥ 4); 1 of 2 evaluable blanks flagged.
3. Controls: **PASS** — (a) block-shuffle 0/12 flagged; (b) mismatched regions 0/12 flagged.

Node D keeps v1 as the default rule (prereg §6: the default changes only if F1 is ACCEPTED).

## Regions

| region | outcome | I best | face | S1 | valid | p (shift null) |
|---|---|---|---|---|---|---|
| PHerc0009B__20250510172639|pos0 | FLAG | 0.538 | fwd | 14.03 | 0.906 | 0.0052 |
| PHerc0009B__20250510172639|pos1 | FLAG | 0.308 | fwd | 307.77 | 1.000 | 0.0052 |
| PHerc0139__20260206000001|pos0 | FLAG | 0.415 | fwd | 10.23 | 0.998 | 0.0052 |
| PHerc0139__20260206000001|pos1 | NOTHING | 0.579 | fwd | 1.26 | 1.000 | 0.0052 |
| PHerc0139__20260206000001|bla0 | FLAG | 0.428 | fwd | 3.67 | 1.000 | 0.0052 |
| PHerc0139__20260206000001|bla1 | NOTHING | 0.590 | fwd | 1.68 | 1.000 | 0.0052 |
| PHerc0172__20250926145427|pos0 | NOTHING | 0.005 | rev | 1.72 | 1.000 | 0.5233 |
| PHerc0172__20250926145427|pos1 | NOTHING | 0.010 | rev | 1.34 | 1.000 | 0.3627 |
| PHerc0500P2__20250716055231|pos0 | NOT_EVALUABLE | 0.235 | rev | 1.16 | 0.735 | 0.0052 |
| PHerc0500P2__20250716055231|pos1 | NOTHING | 0.322 | rev | 1.30 | 0.929 | 0.0052 |
| PHerc0814__20250928235953|pos0 | FLAG | 0.306 | fwd | 2.95 | 0.990 | 0.0052 |
| PHerc0814__20250928235953|pos1 | NOTHING | 0.221 | rev | 1.06 | 0.897 | 0.0104 |
| PHerc0841__20260220214732|pos0 | NOTHING | 0.394 | fwd | 1.61 | 0.994 | 0.0052 |
| PHerc0841__20260220214732|pos1 | NOTHING | 0.333 | fwd | 1.92 | 1.000 | 0.0052 |

## Controls

| control | outcome | I best | S1 |
|---|---|---|---|
| PHerc0009B__20250510172639|pos0|a_block_shuffle | NOTHING | 0.006 | 5.71 |
| PHerc0009B__20250510172639|pos0|b_A_with_B_of_PHerc0009B__20250510172639|pos1 | NOTHING | 0.063 | 63.27 |
| PHerc0009B__20250510172639|pos1|a_block_shuffle | NOTHING | 0.041 | 4.36 |
| PHerc0009B__20250510172639|pos1|b_A_with_B_of_PHerc0139__20260206000001|pos0 | NOTHING | 0.000 | 0.33 |
| PHerc0139__20260206000001|pos0|a_block_shuffle | NOTHING | 0.013 | 12.51 |
| PHerc0139__20260206000001|pos0|b_A_with_B_of_PHerc0139__20260206000001|pos1 | NOTHING | 0.008 | 7.75 |
| PHerc0139__20260206000001|pos1|a_block_shuffle | NOTHING | 0.039 | 2.60 |
| PHerc0139__20260206000001|pos1|b_A_with_B_of_PHerc0172__20250926145427|pos0 | NOTHING | 0.048 | 48.03 |
| PHerc0172__20250926145427|pos0|a_block_shuffle | NOTHING | 0.043 | 3.29 |
| PHerc0172__20250926145427|pos0|b_A_with_B_of_PHerc0172__20250926145427|pos1 | NOTHING | 0.011 | 4.31 |
| PHerc0172__20250926145427|pos1|a_block_shuffle | NOTHING | 0.017 | 10.58 |
| PHerc0172__20250926145427|pos1|b_A_with_B_of_PHerc0500P2__20250716055231|pos0 | NOT_EVALUABLE | 0.016 | 15.93 |
| PHerc0500P2__20250716055231|pos0|a_block_shuffle | NOT_EVALUABLE | 0.002 | 1.80 |
| PHerc0500P2__20250716055231|pos0|b_A_with_B_of_PHerc0500P2__20250716055231|pos1 | NOT_EVALUABLE | 0.000 | 0.00 |
| PHerc0500P2__20250716055231|pos1|a_block_shuffle | NOTHING | 0.006 | 5.53 |
| PHerc0500P2__20250716055231|pos1|b_A_with_B_of_PHerc0814__20250928235953|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0814__20250928235953|pos0|a_block_shuffle | NOTHING | 0.043 | 1.84 |
| PHerc0814__20250928235953|pos0|b_A_with_B_of_PHerc0814__20250928235953|pos1 | NOTHING | 0.033 | 33.18 |
| PHerc0814__20250928235953|pos1|a_block_shuffle | NOTHING | 0.001 | 1.46 |
| PHerc0814__20250928235953|pos1|b_A_with_B_of_PHerc0841__20260220214732|pos0 | NOTHING | 0.000 | 0.00 |
| PHerc0841__20260220214732|pos0|a_block_shuffle | NOTHING | 0.056 | 56.12 |
| PHerc0841__20260220214732|pos0|b_A_with_B_of_PHerc0841__20260220214732|pos1 | NOTHING | 0.027 | 26.54 |
| PHerc0841__20260220214732|pos1|a_block_shuffle | NOTHING | 0.005 | 1.09 |
| PHerc0841__20260220214732|pos1|b_A_with_B_of_PHerc0009B__20250510172639|pos0 | NOTHING | 0.009 | 8.82 |

## Notes (descriptive, not part of the verdict)

- PHerc0172 (w084 flatboi): A and B barely agree on either face (I 0.005 / 0.010), unlike every other segment (I 0.22–0.59).
- Most NOTHING positives fail on face asymmetry (S1 1.06–1.92), not on agreement: the two models agree on both faces.
- One of the two PHerc0139 blanks is flagged (I 0.43, S1 3.67). "Blank" means no ink in the team map, not proven blank.
- Positives are tiles where the team ink map is densest; they are not ground truth either.
- Cost: one pod, 0.124 h at $0.22/h; RunPod balance $49.219 → $49.200 (≈ $0.02). Pod deleted (API 404).
