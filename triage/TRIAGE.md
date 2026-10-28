# Recoverability triage (CPU only, no GPU)

**34 of 34 measurable public segments (10 scrolls) are inside the scan tolerance where a 9 µm model still reads Paris 4 letters.** Tiers: 2 read, 14 test, 18 transfer-limited, 0 scan-limited; 1 more had too little valid surface to measure. Wherever a segment got a WEAK verdict the scan is inside the tolerance, so on those segments the gap is model transfer, not scan quality. A WEAK verdict covers the segments measured, not the whole scroll or object: PHerc0343P is a detached fragment, and on the rolled PHerc. 343 the same public 9 µm models read letters (E. Nieuwlaar, First Letters Prize, Oct 2026).

Tolerance (node B, Paris 4 dense_native curve): voxel ≤ 9.6 µm (PASS at 9.6, WEAK at 19.2; nothing tested in between), HF spectral ratio ≥ 0.024, adjacent-layer high-pass correlation ≥ 0.32. Applying a Paris 4 tolerance to other scrolls assumes the proxies mean the same thing across scrolls and beam energies; this is not validated.

Tier rules (fixed before the table was built):
- **1 read**: the scroll has a node-A PASS with a held-out model, and the scan is inside the tolerance → run that model on the whole segment.
- **2 test**: no conclusive node-A result on the scroll, scan inside the tolerance → worth a small GPU test; if a team ink map exists, score it with inkcheck first (CPU, free).
- **3 transfer-limited**: node A is WEAK on this scroll although its scan is inside the tolerance → more GPU with the same models is not justified; labels or fine-tuning are needed.
- **4 scan-limited**: a proxy outside the tolerance → do not spend GPU on this volume.
- **5 not measured**: the fetched crop has too little valid surface for the HF proxy (no complete tile) → no call; fetch a larger crop.
Segments already in Reader V3's training set are marked: their ink was already labelled, so they are low priority for new reading.

| tier | scroll | segment | µm | area mm² | HF ratio | layer corr | node A | in Reader V3 training | ink map on the bucket |
|---|---|---|---|---|---|---|---|---|---|
| 1 read | PHerc0009B | 20250919125754 (labelled crop) | 8.64 | 374 | 0.0549 (relaxed) | 0.807 | PASS (this segment) | no | yes |
| 1 read | PHercParis4 | 20231005123336 (control crop) | 9.6 | 217 | 0.0480 | 0.534 | PASS (this segment) | no | yes |
| 2 test | PHerc0800 | 20251028213516-auto_grown_20251028213516 | 8.64 | 169 | 0.0598 | 0.834 | none | no | no |
| 2 test | PHerc0800 | 20251028220042 | 8.64 | 158 | 0.0337 | 0.825 | none | no | no |
| 2 test | PHerc0800 | 20251028220955 | 8.64 | 153 | 0.0355 | 0.816 | none | no | no |
| 2 test | PHerc0800 | 20251028222030 | 8.64 | 234 | 0.0599 | 0.839 | none | no | no |
| 2 test | PHerc0800 | 20251028225813 | 8.64 | 183 | 0.0502 | 0.838 | none | no | no |
| 2 test | PHerc0800 | 20251029010146 | 8.64 | 36 | 0.0393 (relaxed) | 0.842 | none | no | no |
| 2 test | PHerc0814 | 20251001060526-auto_grown_20251001060526 | 9.362 | 278 | 0.0367 (relaxed) | 0.738 | LOW_POWER (same scroll) | no | yes |
| 2 test | PHerc1447 | 20250502183421-auto_grown_20250502161744 | 8.64 | 156 | 0.0756 (relaxed) | 0.898 | none | no | no |
| 2 test | PHerc1447 | 20250502205333-auto_grown_20250502181030 | 8.64 | 247 | 0.0851 (relaxed) | 0.942 | none | no | no |
| 2 test | PHerc0139 | 20250108000000-w025_2025010863 | 9.362 | 368 | 0.0416 (relaxed) | 0.712 | none | yes | yes |
| 2 test | PHerc0139 | 20260126000000-w045_2026012619 | 9.362 | 367 | 0.0286 (relaxed) | 0.722 | none | yes | yes |
| 2 test | PHerc0139 | 20260227000000-w052_2026022705 | 9.362 | 367 | 0.0320 (relaxed) | 0.784 | none | yes | yes |
| 2 test | PHerc0814 | 20250925161630-auto_grown_20250925161630 | 9.362 | 315 | 0.0315 (relaxed) | 0.752 | LOW_POWER (same scroll) | yes | yes |
| 2 test | PHerc0814 | 20250926165636-auto_trace_20250926165636 | 9.362 | 325 | 0.0409 (relaxed) | 0.794 | LOW_POWER (same scroll) | yes | yes |
| 3 transfer-limited | PHerc0172 | 20250926122938-w082 | 7.91 | 590 | 0.0547 | 0.853 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0172 | 20250926132117-w083 | 7.91 | 590 | 0.0506 | 0.855 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0172 | 20251110135803-w067_20251110135803677_fl | 7.91 | 262 | 0.0487 | 0.867 | WEAK (same scroll) | no | yes |
| 3 transfer-limited | PHerc0172 | 20251115002747-auto_grown_20251115002740 | 7.91 | 262 | 0.0502 | 0.849 | WEAK (same scroll) | no | yes |
| 3 transfer-limited | PHerc0343P | 20250904233748-0_b2 | 8.64 | 432 | 0.0325 | 0.776 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0343P | 20250905172054-1_b2 | 8.64 | 324 | 0.0315 | 0.769 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0500P2 | 20250716055229 (gen_00371) | 9.362 | 461 | 0.0313 (relaxed) | 0.755 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0500P2 | 20250716055230 (gen_00377) | 9.362 | 857 | 0.0381 (relaxed) | 0.780 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0500P2 | 20250825181928-2 | 9.362 | 367 | 0.0536 (relaxed) | 0.779 | WEAK (same fragment) | no | yes |
| 3 transfer-limited | PHerc0841 | 20260220213127-w00 | 9.366 | 574 | 0.0393 (relaxed) | 0.746 | WEAK (this segment) | no | yes |
| 3 transfer-limited | PHerc0841 | 20260220214732-auto_grown_20260220144552 | 9.366 | 367 | 0.0416 (relaxed) | 0.747 | WEAK (same scroll) | no | yes |
| 3 transfer-limited | PHerc0841 | 20260221022814-auto_grown_20260220174252 | 9.366 | 368 | 0.0347 (relaxed) | 0.744 | WEAK (same scroll) | no | yes |
| 3 transfer-limited | PHerc0172 | 20250917143559-w062_20250917143559205_fl | 7.91 | 262 | 0.0443 | 0.861 | WEAK (same scroll) | yes | yes |
| 3 transfer-limited | PHerc0343P | 20250511003658-tifxyz | 8.64 | 257 | 0.0282 | 0.777 | WEAK (this segment) | yes | yes |
| 3 transfer-limited | PHerc0343P | 20250902170441--4_b2 | 8.64 | 288 | 0.0443 | 0.779 | WEAK (same fragment) | yes | yes |
| 3 transfer-limited | PHerc0343P | 20250902171204--1_b2 | 8.64 | 294 | 0.0375 (relaxed) | 0.779 | WEAK (same fragment) | yes | yes |
| 3 transfer-limited | PHerc0500P2 | 20250609204953-z_dbg_gen_00612 | 9.362 | 220 | 0.0535 (relaxed) | 0.782 | WEAK (same fragment) | yes | yes |
| 3 transfer-limited | PHerc0500P2 | 20250628074500-500P2_front | 9.362 | 367 | 0.0383 (relaxed) | 0.768 | WEAK (same fragment) | yes | yes |
| 5 not measured | PHerc1447 | 20250502180708-auto_grown_20250502160708 | 8.64 | 18 | n/a | 0.898 | none | no | no |

Proxies are computed on one 2048×2048 crop (or the labelled crop) per segment, centre layer of the model window; 'relaxed' = no fully valid 512 px tile, so tiles ≥ 90% valid were used with the gaps filled (this tends to read slightly high). Node-A evidence: PHercParis4: 5/5 held-out 9 µm checkpoints PASS (cards/paris4); PHerc0009B: Reader V3, Reader v2, dense_native PASS vs 2.4 µm map and vs human labels (cards/pherc0009B); PHerc0343P: no held-out model at letter level; IR camera letters agree (cards/343P); PHerc0841: Reader V3, Reader v2, dense_native WEAK vs human labels and vs 2.4 µm map (cards/pherc0841); PHerc0172: Reader V3, Reader v2, dense_native WEAK vs team map on w082 and w083 (cards/pherc0172); PHerc0500P2: Reader V3, Reader v2, dense_native WEAK vs 2.2 µm map on gen_00371 and gen_00377 (cards/pherc0500P2); PHerc0814: official 46527 validation mask: AUC reproduced but only 2 strokes (cards/pherc0814).
