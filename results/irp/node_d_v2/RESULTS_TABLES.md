# Node D v2 held-out validation — numbers-only tables

Generated from `results_v2.json` (scorer `score_node_d_v2.py`, rule `RULE_V2`, prereg sha256 1bc3423e…). No images.

## Regions

| region | seg | kind | pitch (vox) | valid px | best face | I_best | p_best | S1 face asym | I_off (+P/2, -P/2) | S2 | v2 | face-only | v1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0172-w082_pos0 | 0172-w082 | positive | 38.62 | 399424 | rev | 0.0067 | 0.5026 | 4.146 | 0.003, 0.0069 | 0.9832 | NOTHING | no | NOTHING |
| 0172-w082_pos1 | 0172-w082 | positive | 48.01 | 399424 | rev | 0.1194 | 0.0052 | 40.38 | 0.0982, 0.0574 | 1.216 | NOTHING | yes | NOTHING |
| 0172-w082_bla0 | 0172-w082 | blank | — | 399424 | rev | 0.0384 | 0.1762 | 34.97 | — | — | NOT_EVALUABLE | no | NOTHING |
| 0172-w083_pos0 | 0172-w083 | positive | — | 399424 | rev | 0.0147 | 0.228 | 14.73 | — | — | NOT_EVALUABLE | no | NOTHING |
| 0172-w083_pos1 | 0172-w083 | positive | 40.12 | 399424 | fwd | 0.007 | 0.3938 | 6.972 | 0.0988, 0.0909 | 0.0706 | NOTHING | no | NOTHING |
| 0500P2-371_pos0 | 0500P2-371 | positive | — | 267389 | fwd | 0.376 | 0.0052 | 16.51 | — | — | NOT_EVALUABLE | yes | NOTHING |
| 0500P2-371_pos1 | 0500P2-371 | positive | 15.73 | 82234 | fwd | 0.6495 | 0.0052 | 4.97 | 0.0853, 0.0053 | 7.618 | CANDIDATE | yes | NOTHING |
| 0500P2-377_pos0 | 0500P2-377 | positive | 9.865 | 267201 | fwd | 0.2325 | 0.0052 | 2.38 | 0.1182, 0.1237 | 1.879 | NOTHING | yes | NOTHING |
| 0500P2-377_pos1 | 0500P2-377 | positive | 12.69 | 257120 | rev | 0.1281 | 0.0104 | 18.98 | 0.0422, 0.1304 | 0.9822 | NOTHING | yes | NOTHING |
| 0500P2-377_bla0 | 0500P2-377 | blank | — | 0 | fwd | 0 | 1 | 0 | — | — | NOT_EVALUABLE | no | NOT_EVALUABLE |
| 0841-w00_pos0 | 0841-w00 | positive | 14.16 | 285057 | fwd | 0.3322 | 0.0052 | 11.39 | 0.3101, 0.4897 | 0.6784 | NOTHING | yes | NOTHING |
| 0841-w00_pos1 | 0841-w00 | positive | 11.61 | 285063 | fwd | 0.4664 | 0.0052 | 2.521 | 0.4007, 0.3292 | 1.164 | NOTHING | yes | NOTHING |
| 0009B-125754_pos0 | 0009B-125754 | positive | 53.39 | 335210 | fwd | 0.4042 | 0.0052 | 404.2 | 0.5653, 0.3868 | 0.7149 | NOTHING | yes | NOTHING |
| 0009B-125754_pos1 | 0009B-125754 | positive | 54.18 | 335222 | fwd | 0.4726 | 0.0052 | 11.03 | 0.6031, 0.5402 | 0.7837 | NOTHING | yes | NOTHING |
| 0009B-125754_bla0 | 0009B-125754 | blank | — | 0 | fwd | 0 | 1 | 0 | — | — | NOT_EVALUABLE | no | NOT_EVALUABLE |
| 0009B-125754_bla1 | 0009B-125754 | blank | — | 0 | fwd | 0 | 1 | 0 | — | — | NOT_EVALUABLE | no | NOT_EVALUABLE |

## Synthetic controls (24)

| control | v2 outcome | I_best |
|---|---|---|
| 0172-w082_pos0|a_block_shuffle | NOTHING | 0.0316 |
| 0172-w082_pos0|b_A_with_B_of_0172-w082_pos1 | NOTHING | 0.0003 |
| 0172-w082_pos1|a_block_shuffle | NOTHING | 0.0102 |
| 0172-w082_pos1|b_A_with_B_of_0172-w083_pos0 | NOT_EVALUABLE | 0.0539 |
| 0172-w083_pos0|a_block_shuffle | NOT_EVALUABLE | 0.0535 |
| 0172-w083_pos0|b_A_with_B_of_0172-w083_pos1 | NOT_EVALUABLE | 0.0181 |
| 0172-w083_pos1|a_block_shuffle | NOTHING | 0.0593 |
| 0172-w083_pos1|b_A_with_B_of_0500P2-371_pos0 | NOT_EVALUABLE | 0.0003 |
| 0500P2-371_pos0|a_block_shuffle | NOT_EVALUABLE | 0.0162 |
| 0500P2-371_pos0|b_A_with_B_of_0500P2-371_pos1 | NOT_EVALUABLE | 0 |
| 0500P2-371_pos1|a_block_shuffle | NOTHING | 0.024 |
| 0500P2-371_pos1|b_A_with_B_of_0500P2-377_pos0 | NOTHING | 0.1083 |
| 0500P2-377_pos0|a_block_shuffle | NOTHING | 0.0016 |
| 0500P2-377_pos0|b_A_with_B_of_0500P2-377_pos1 | NOTHING | 0.1278 |
| 0500P2-377_pos1|a_block_shuffle | NOTHING | 0.002 |
| 0500P2-377_pos1|b_A_with_B_of_0841-w00_pos0 | NOTHING | 0.045 |
| 0841-w00_pos0|a_block_shuffle | NOTHING | 0.0905 |
| 0841-w00_pos0|b_A_with_B_of_0841-w00_pos1 | NOTHING | 0.1299 |
| 0841-w00_pos1|a_block_shuffle | NOTHING | 0.0303 |
| 0841-w00_pos1|b_A_with_B_of_0009B-125754_pos0 | NOTHING | 0.0667 |
| 0009B-125754_pos0|a_block_shuffle | NOTHING | 0.0012 |
| 0009B-125754_pos0|b_A_with_B_of_0009B-125754_pos1 | NOTHING | 0.0003 |
| 0009B-125754_pos1|a_block_shuffle | NOTHING | 0.0004 |
| 0009B-125754_pos1|b_A_with_B_of_0172-w082_pos0 | NOTHING | 0 |

## PHerc.343 (Erwin region) under v2 — design data, diagnosis only

| face | I (top-3 % IoU) | p (192 shifts) | null mean | I_off (+P/2, -P/2) | S2 |
|---|---|---|---|---|---|
| fwd | 0.1863 | 0.0052 | 0.0127 | 0.219, 0.1932 | 0.851 |
| rev | 0.4342 | 0.0052 | 0.0119 | 0.2955, 0.438 | 0.991 |

Pitch P = 13.87 voxels; S1 face asymmetry = 2.3304 (best face: rev); v2 outcome **NOTHING**; face-only (I ≥ 0.10 and S1 ≥ 2): **yes**; v1 on the same maps: NOTHING.

## D2 render check (depth-0 render vs official surface volume)

| region | corr. with official surface volume (window centre) | layer shift |
|---|---|---|
| 0172-w082_pos0 | 0.969 | 48 |
| 0172-w082_pos1 | 0.969 | 48 |
| 0172-w082_bla0 | 0.945 | 48 |
| 0172-w083_pos0 | 0.966 | 48 |
| 0172-w083_pos1 | 0.96 | 48 |
| 0500P2-371_pos0 | 0.945 | 50 |
| 0500P2-371_pos1 | 0.946 | 50 |
| 0500P2-377_pos0 | 0.907 | 51 |
| 0500P2-377_pos1 | 0.93 | 50 |
| 0500P2-377_bla0 | 0.0 | 50 |
| 0841-w00_pos0 | 0.929 | 50 |
| 0841-w00_pos1 | 0.943 | 51 |
| 0009B-125754_pos0 | 0.975 | 49 |
| 0009B-125754_pos1 | 0.973 | 49 |
| 0009B-125754_bla0 | 0.0 | 49 |
| 0009B-125754_bla1 | 0.0 | 49 |
