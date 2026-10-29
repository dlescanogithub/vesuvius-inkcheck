# inkcheck reference set v0

A fixed, reproducible list of **192 public regions** (96 ink, 96 no-ink) on 12 segments from 3 scrolls, taken from the public `scrollprize/ink_9um` aligned label set. It gives every tool the same small set of labelled places to report on. It holds coordinates, fractions and hashes only, with **no image data**.

Files: [`refset_v0.json`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/refset/refset_v0.json) (the regions), [`coverage_v0.json`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/refset/coverage_v0.json) (per-case counts), [`build_refset.py`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/refset/build_refset.py) (the generator).

## Coverage

| Scroll | Segments | Ink tiles | No-ink tiles | Area (cm²) |
|---|---:|---:|---:|---:|
| PHerc0139 | 9 | 72 | 72 | 0.358 |
| PHerc0814 | 1 | 8 | 8 | 0.040 |
| PHerc1667 | 2 | 16 | 16 | 0.080 |

| Label case | Segment | Supervised (cm²) | Ink fraction | Eligible tiles | Candidates ink / no-ink | Selected ink / no-ink |
|---|---|---:|---:|---:|---:|---:|
| pherc0139-w016 | `20250108000004-w029_2025010827` | 0.461 | 0.233 | 152 | 67 / 47 | 8 / 8 |
| pherc0139-w017 | `20250108000005-w030_2025010818` | 0.701 | 0.311 | 232 | 127 / 54 | 8 / 8 |
| pherc0139-w028 | `20260115000000-w044_2026011522` | 1.618 | 0.249 | 586 | 233 / 203 | 8 / 8 |
| pherc0139-w029 | `20260126000000-w045_2026012619` | 0.441 | 0.256 | 134 | 57 / 54 | 8 / 8 |
| pherc0139-w035 | `20260317000000-w035_2026031718` | 0.938 | 0.316 | 294 | 151 / 71 | 8 / 8 |
| pherc0139-w039 | `20260302000000-w039_2026030210` | 0.503 | 0.320 | 158 | 82 / 38 | 8 / 8 |
| pherc0139-w040 | `20250831000000-w040_2025083102` | 1.426 | 0.444 | 426 | 301 / 40 | 8 / 8 |
| pherc0139-w041 | `20260108000000-w041_2026010816` | 0.485 | 0.417 | 159 | 101 / 19 | 8 / 8 |
| pherc0139-w043 | `20260112000000-w043_2026011217` | 0.399 | 0.447 | 123 | 89 / 16 | 8 / 8 |
| pherc0814-46527 | `20260226000000-46527_2um_try2` | 0.395 | 0.296 | 134 | 74 / 27 | 8 / 8 |
| pherc1667-w013 | `20240304141531-w013_20240304141531_flatboi` | 3.093 | 0.301 | 1077 | 556 / 268 | 8 / 8 |
| pherc1667-w018 | `20240304144031-w018_20240304144031_flatboi` | 12.799 | 0.228 | 4520 | 1692 / 2065 | 8 / 8 |
| pherc1667-w023 | not fetched | | | | | |
| pherc1667-w028 | not fetched | | | | | |
| pherc1667-w029 | not fetched | | | | | |
| pherc1667-w031 | not fetched | | | | | |

## Method

- The label canvas (9.596 µm, annotation plane 10) is cut into a fixed grid of 0.5 mm tiles (52 px), anchored at pixel (0, 0).
- A tile is **eligible** if at least 90% of its pixels are supervised (supervision mask > 0).
- **Ink** tile: eligible, and at least 15% of its supervised pixels are labelled ink (label > 0).
- **No-ink** tile: eligible, with no ink pixel inside the tile or within 0.15 mm of it.
- Up to 8 tiles per class are kept for each case. They are ranked by `sha256('refset-v0|case|class|ty|tx') ascending`, an order that is fixed and does not depend on content. No random seed is used.
- Each region records its pixel box and µm box on the label canvas, its supervised and ink fractions, the label volume, and a sha256 of the label and mask bytes inside the box. A user can check the hash to confirm they hold the same labels.

Rebuild: `python leaderboard/build_leaderboard.py fetch` and then `python refset/build_refset.py`. The output is deterministic.

## Limitations

- Only 3 scrolls are covered, and PHerc0139 has most of the tiles (144 of 192).
- Four PHerc1667 label sets (w023, w028, w029, w031) had not finished downloading when v0 was cut and are marked "not fetched" above. They were not dropped for any result; v1 can add them.
- PHercParis4 is excluded on purpose.
- "No-ink" means *not labelled as ink* inside the supervision mask. That is the annotators' call, not ground truth; faint ink may be missed.
- Only one annotation plane (10) is used; depth is not considered.
- The tiles are small (0.5 mm), so a region shows local agreement, not legibility.
- Ink labels were fetched only for label chunks within one chunk (1.23 mm) of a supervised pixel. That is more than the 0.15 mm no-ink margin, so the margin test is complete for eligible tiles.
- v0 is a fixed snapshot of the labels. If the upstream labels change, the hashes will no longer match, and a new version should be cut.

License: the labels are CC BY-NC 4.0 under the Vesuvius Challenge data terms. This file and the JSON contain derived coordinates and numbers only.
