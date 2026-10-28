# PHerc1203 pre-registration (verbatim copy of hires_test/FINDINGS.md §0, §0b, §0c)

Copied unchanged so the hash in the readability card refers to the rule text only. §0 was written 2026-10-27 ~18:55 UTC-3 and §0b ~19:00 UTC-3, before any 2.4 µm output of the zones (first hecate output: 2026-10-27 20:04 UTC-3). §0c (~21:35 UTC-3) adds a ≥ 5-component criterion; its timestamp is not clearly before the first phase-3 output (21:34 UTC-3), so the card applies only the §0 rule.

## 0. Pre-registration (written 2026-10-27 ~18:55 UTC-3, BEFORE looking at any 2.4 µm data of the candidate zones or any texture map)
**Candidate zones (1203).** Rule in `tools/select_zones.py`, output in `zones_selected.json`. A 6×6 mm tile of the phase-2 dn_w7 map qualifies when:
- its stroke-sized component density is above the null p99 (> 22.86 /cm²);
- 0.03 ≤ frac(p>0.5) ≤ 0.30, i.e. not saturated;
- ≥ 95 % of the tile is inside the 2.4 µm scan via T2.

The tiles are ranked by component density, with at most 1 per segment, excluding 223153537. 18 tiles qualify. The 3 picked are:
- 231446965 (y3520, x1600);
- 230830031 (y2240, x320), which is also the mesh-031 test;
- 221856743 (y3520, x1280).

**Model metrics (no reference available on 1203).** All are computed on a common ~9.6 µm grid inside the patch:
- frac(p>0.5);
- stroke-sized components per cm² (0.03–1.5 mm²);
- median stroke width (2×distance transform on the skeleton, at the prediction's native pixel);
- r with the native 9.36 µm prediction;
- line periodicity (no power; reported only).

Nulls are the same model on depth-reversed input. A zone counts as a **candidate** only if both of these hold:
- (i) component density is ≥ 2× the reversed-depth null, and at least 2 checkpoints agree (pairwise r of the maps ≥ 0.3);
- (ii) visually there are stroke-like shapes 0.1–0.5 mm wide.

Anything else is "nothing". **No zone is called "ink"**: without a reference map that cannot be validated.

**Model-free texture (step 3).** Script `tools/texture_feats.py`, with fixed parameters:
- per depth band, *mean* = mean intensity, and *hf* = 'crackle' energy = ⟨(G₁px − G₄px)²⟩, smoothed G₄px;
- both signs are tested, so 8 tests on 343P, and a feature passes only at Bonferroni p < 0.05/8.

These features are **validated first on 343P**:
- the published 2.215 µm surface volume, bands A = layers 44–55 (papyrus side of the papyrus/air transition at ~layer 55–60) and B = 56–63;
- scored with inkcheck against new_canon (same mask, 8.86 µm analysis grid).

A feature is "usable" only if inkcheck gives r_bp > 0.2 and p < 0.006. Only usable features are applied to 1203, using the analogous bands relative to the mesh surface.

### 0b. Addendum to the pre-registration (written ~19:00 UTC-3, before any hecate-2.4 output)
- **New fact: a public native 2.4 µm model exists, and earlier work did not use it.** `scrollprize/hecate`, `hecate_2.4um.pth` (https://huggingface.co/scrollprize/hecate), distilled from the canonical 2 µm model `scrollprize/ink_canonical_2um` (ResNet-152 3D, 1.5 GB). Phase 2 had concluded "there is no 2 µm model". That was wrong.
- **The 343P reference is not ground truth.** `new_canon_autoresearch_recipe` *is* the prediction of the canonical 2 µm model on that volume. Hecate agreeing with it on 343P therefore only proves that the CPU pipeline, orientation and resampling are correct (teacher/student). It does **not** prove that hecate generalizes.
- **Hecate sanity check on 343P.** Crop chosen by the reference's ink density (the densest 1112² px block fully inside the mask: y7784, x3892), resampled 2.215→2.4 µm (×0.923). Both directions are run. The direction with the higher r against the reference is the "correct" one, and it is applied as-is to 1203 (same render order convention). The other direction acts as an orientation null.
- **Hecate 2.4 on 1203** (537 and the 3 zones, at native 2.403 µm, stride 256): same metrics and candidate rule as in §0. Additionally, for each zone, hecate-2.4 vs dn@r9 agreement is reported as Pearson r on the 9.6 µm grid; r ≥ 0.3 counts as "agreement".


### 0c. Phase 3 pre-registration (written ~21:35 UTC-3, after §3 and BEFORE any 2.4 µm data of these tiles)
Extension "every possible effort": the remaining 15 tiles that already qualified in `zones_selected.json`, taken greedily in rank order and skipping any tile that overlaps >50% with one already taken. That leaves **7 tiles** (`zones_phase3.json`: p0_965, p1_031, p2_537, p3_965, p4_031, p5_031, p6_031).

Each tile is rendered at 2.403 µm and run through hecate-2.4 fwd and rev (stride 256). The dn r2/r9 runs are skipped for time, since they were uninformative in §3.

Rule: **candidate** only if all of these hold:
- comps(fwd) ≥ 2× comps(rev);
- ≥ 5 components in the tile;
- r(hecate fwd, native dn_w7 9.36 µm) ≥ 0.3 (a different checkpoint);
- visually, strokes 0.1–0.5 mm wide.

