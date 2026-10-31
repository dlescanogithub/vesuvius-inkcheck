# Public-label leaderboard v0 (inkcheck 0.3.0)

Built Oct 29, 2026 (ART) on CPU with `leaderboard/build_leaderboard.py`. Numbers only: no scroll images or derived pictures are stored.
Per-pair ink cards (schema `ink-card/v1`) are in `leaderboard/cards/`, the table below is `leaderboard/leaderboard.csv`, totals are in `leaderboard/summary.json` and skipped pairs are in `leaderboard/excluded.json`.

## Headline

**This is one model on 12 labelled segments from 3 scrolls (PHerc0139, PHerc0814, PHerc1667), not a ranking of models.** Only one official map family, `new_canon_autoresearch_recipe` (2.399 µm, 78 keV scans), was made on the same scan volume and canvas as the public labels. The other official map on these segments (`mrg20736-1um-s1z2`, 1.129 µm, 59 keV scans) sits on a different canvas with no published transform, so all 12 of those pairs are excluded instead of guessed.

Verdicts: **2 PASS, 4 WEAK, 6 FAIL, 0 INVALID** out of 12. Median band-pass r 0.58, median AUC 0.90, median stroke recall 1.00. The wrong-place control FAILed as expected on 12/12, and 0/12 maps look saturated.

**How to read it honestly:** the agreement is real and high (AUC ≈ 0.86–0.97), but most checks cannot *prove* it against the protocol's nulls, because most segments' supervised area is small (median 0.59 cm² after resampling; 10 of 12 are under 2 cm²) and contains only a handful of strokes (median 6). On such small, line-structured regions, a randomly shifted copy of the labels can also correlate strongly with the map (null maxima up to ≈ 1.0 on the smallest areas), so p stays above 0.01 and the verdict is FAIL or WEAK even when r is 0.5–0.8. FAIL here means "not separable from the nulls on this little label area", not "the model misses the ink". WEAK means the band-pass r beat all 192 shift nulls (p at its floor, 0.0052) but stroke recall did not clear its own, smaller null test (32 shift + dihedral nulls, α = 0.05; card v1 does not store that p). The largest area, PHerc1667 w018 (12.8 cm², 51 strokes), is WEAK for this reason, not FAIL. And because these labels may have been made with, or used to train, the same pipeline, a PASS is agreement with the labels, not a held-out test.

## Method

* **References:** the public `scrollprize/ink_9um` label set on Hugging Face (`ink_9um/labels/aligned-scrollprizeorg-21slices`), zarr v2, 9.596 µm, annotation plane 10. Ink = label value > 0; validity = supervision mask > 0 (ink labelled outside the mask is not scored). PHercParis4 is excluded on purpose.
* **Predictions:** the official ds8 preview maps on the open-data server (`<scroll>/segments/<segment>/ink-detection/downsampled/*-ds8.jpg`), 19.192 µm per pixel. They are 8-bit previews, not the full-resolution maps.
* **Pairing:** a map is scored only if its scan and volume id match the labels' `source_surface_volume` and its extent matches the label canvas within 2 %. Otherwise the pair is listed under Excluded with the reason.
* **Crop:** both maps are cut to the supervision mask's bounding box plus 1 mm, so the toroidal shift nulls wrap inside the labelled region. On the full canvas, most shifts moved the narrow supervised strips off the segment and could not be scored (25 of 576 usable on one case).
* **Check:** `inkcheck` at 19.192 µm with defaults (registration ±0.5 mm, band-pass r, 192 search-matched shift nulls plus dihedral nulls, stroke recall with its own null, PASS / WEAK / FAIL thresholds from `CheckConfig`). Plus a wrong-place control (the map rolled to the wrong place, must FAIL) and `saturation_check`.
* `usable nulls` is how many of the 192 shift nulls had enough overlap to score. `null-limited` means too few remained for p to reach 0.01.

## Results

| segment | scroll | model | verdict | r_bp | p | null max | usable nulls | AUC | stroke recall (chance) | strokes | area cm² | control | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pherc0139-w016 | PHerc0139 | new_canon_autoresearch_recipe | **WEAK** | 0.350 | 0.0052 | 0.260 | 192 | 0.864 | 0.33 (0.16) | 6 | 0.44 | FAIL | online-validation case |
| pherc0139-w017 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.543 | 0.0104 | 0.600 | 192 | 0.890 | 1.00 (0.40) | 6 | 0.68 | FAIL |  |
| pherc0139-w028 | PHerc0139 | new_canon_autoresearch_recipe | **PASS** | 0.701 | 0.0052 | 0.265 | 192 | 0.955 | 1.00 (0.22) | 10 | 1.61 | FAIL |  |
| pherc0139-w029 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.517 | 0.2075 | 0.998 | 105 | 0.897 | 0.75 (0.41) | 4 | 0.43 | FAIL |  |
| pherc0139-w035 | PHerc0139 | new_canon_autoresearch_recipe | **PASS** | 0.555 | 0.0052 | 0.543 | 192 | 0.902 | 0.90 (0.30) | 10 | 0.93 | FAIL |  |
| pherc0139-w039 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.544 | 0.0674 | 0.958 | 192 | 0.901 | 1.00 (0.51) | 6 | 0.49 | FAIL |  |
| pherc0139-w040 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.602 | 0.0833 | 0.936 | 191 | 0.878 | 1.00 (0.70) | 17 | 1.42 | FAIL | dihedral null ≥ r |
| pherc0139-w041 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.545 | 0.1846 | 0.994 | 64 | 0.888 | 1.00 (1.00) | 4 | 0.48 | FAIL | null-limited |
| pherc0139-w043 | PHerc0139 | new_canon_autoresearch_recipe | **FAIL** | 0.619 | 0.1210 | 0.945 | 123 | 0.886 | 1.00 (0.73) | 6 | 0.40 | FAIL |  |
| pherc0814-46527 | PHerc0814 | new_canon_autoresearch_recipe | **WEAK** | 0.757 | 0.0052 | 0.734 | 192 | 0.973 | 1.00 (0.31) | 4 | 0.39 | FAIL | online-validation case |
| pherc1667-w013 | PHerc1667 | new_canon_autoresearch_recipe | **WEAK** | 0.808 | 0.0052 | 0.646 | 192 | 0.970 | 1.00 (0.20) | 18 | 3.04 | FAIL |  |
| pherc1667-w018 | PHerc1667 | new_canon_autoresearch_recipe | **WEAK** | 0.671 | 0.0052 | 0.430 | 192 | 0.927 | 0.96 (0.14) | 51 | 12.75 | FAIL |  |

Null-limited checks: 1/12. Checks where a rotated or flipped reference correlated as well as the real one: 1/12.

**Not scored in v0:** four more PHerc1667 label sets in the case list (w023, w028, w029, w031) had not finished downloading when v0 was cut, so they are absent here and from the reference set. They are not excluded for any result; a later version can add them with `build_leaderboard.py fetch`.

## Excluded pairs

| pair | reason |
|---|---|
| pherc0139-w016__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w017__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w028__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w029__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w035__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w039__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w040__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w041__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0139-w043__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260413113053; labels are on 2.399um-0.22m-78keV volume 20260102150214 |
| pherc0814-46527__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260521123630; labels are on 2.399um-0.22m-78keV volume 20260309142202 |
| pherc1667-w013__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260323082859; labels are on 2.399um-0.22m-78keV volume 20251217075048 |
| pherc1667-w018__mrg20736-1um-s1z2 | map from scan 1.129um-0.22m-59keV volume 20260323082859; labels are on 2.399um-0.22m-78keV volume 20251217075048 |

## Caveats

1. **Agreement, not held-out.** The public labels may have been drawn from, or used to train, the same model family. A PASS shows the map agrees with the labels. It does not show the model generalises. `leaderboard.csv` has an `in_sample` column from `inkcheck.training_overlap` (true = the model trained on that segment, false = stated held out, empty = unknown); it is empty on every row here because `new_canon_autoresearch_recipe`'s training set is not in the registry. Labels pherc0139-w017 (public w030) and pherc0139-w029 (public w045) are training cases of `ink_9um` s42/s43 and `ink9um-dense-native` (jo-tud, villa #2349), so scores of those models on them would be flagged.
2. **One model.** Only one official map family shares the labels' canvas, so this table compares segments, not models. Adding a model means publishing its map on the label canvas, or a transform to it.
3. **Small label areas.** Medians: 0.59 cm² scored and 6 strokes per segment. This is the main reason for FAIL/WEAK here; the CSV keeps r, AUC and the null maxima so readers can see it.
4. **3 scrolls only** (PHerc0139, PHerc0814, PHerc1667), and 9 of 12 rows come from PHerc0139.
5. **8-bit ds8 previews**, not full-resolution maps, so fine strokes are blurred at 19.192 µm.
6. **Labels on one plane** (plane 10 of the 21-slice stack). Ink on other depths is not scored.
7. Some label sets carry an `online_validation` flag in their metadata; it is copied into the CSV (`online_validation_case`) without interpretation.
8. The crop keeps nulls inside the labelled region, which makes them harder to beat than full-canvas nulls (they sample the same text-line structure). That is the conservative choice.
9. PHercParis4 is excluded (publication reservation). No Paris 4 numbers appear here.

Data: Vesuvius Challenge scroll data and labels, CC BY-NC 4.0. This file holds numbers only.
