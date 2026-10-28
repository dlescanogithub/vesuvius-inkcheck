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

Paris 4 scores (r_bp, AUC, F1, stroke recall/precision) withheld: PHercParis4 publication reservation until 2027-06-25.

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
