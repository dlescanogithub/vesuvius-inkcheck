# Pre-registration: node D "face-only" (two-model face asymmetry, after ScrollPrize/villa PR #2318)

Status: written and hashed **before** any evaluation on the sets in section 5. The sha256 of this file and the time
it was fixed are in `PREREG_NODE_D_FACEONLY.sha256` (same directory), committed in the same commit. Nothing in this
file may change after hashing; deviations go to `DEVIATIONS.md` in this directory with a reason, and any result
affected by a deviation is reported as exploratory.

Code: `src/inkcheck/node_d_v2.py` (`RULE_FACE_ONLY`, `face_only_rule`, `face_only_flag`, `top_iou`, `shift_null_p`)
and `src/inkcheck/irp.py` (`node_d` with `"rule_type": "face_only"`), committed together with this file. At hashing
time this code has been run on synthetic data (`tests/`) and on the already-seen node D v2 numbers (section 4) only.

## 1. What this is, and what it is not

The statistic is **ketchupbyheinz's** (ScrollPrize/villa PR #2318, `face_check`, open, 2026-10-26,
https://github.com/ScrollPrize/villa/pull/2318): run two checkpoints with villa `--direction both`, measure on each
face the agreement of the two checkpoints as the IoU of their top-3 % pixels, and compare the faces. Writing is
one-faced; papyrus texture is not. All credit for the idea goes to that PR. What this file adds is a fixed decision
rule, fixed pass criteria, controls and a held-out evaluation plan, in the IRP style of node D v2.

**This is not a validation.** The rule below was already applied, as a descriptive column, to the node D v2
held-out set (section 4). That set has been seen and cannot validate it. The thresholds were fixed in the v2
pre-registration (`results/irp/node_d_v2/PREREG_NODE_D_V2.md`, sha256 1bc3423e…, section 6, "face-only (I >= 0.10
and S1 >= 2.0, PR #2318 statistic)") before those data were scored, and they are carried over unchanged: nothing
here is tuned. A claim of validation can come only from the unused sets in section 5.

## 2. Why (the v2 negative)

Node D v2 added an off-winding control (surface moved ±P/2) to the face asymmetry and was **REJECTED** on its
pre-registered held-out set: 1 of 12 positive regions. In 7 of the 10 positives where a pitch was found, two-model
agreement at ±P/2 was 0.68–1.22× the agreement on the surface, so the ±P/2 surface is not ink-free on these segments.
The face-only statistic, pre-specified as a descriptive column, flagged 9 of 12 positives in 5 of 6 segments
(`results/irp/node_d_v2/RESULTS.md`, `results_v2_rescored.json`). Node D v2 stays a published negative result.

## 3. The rule (fixed; `RULE_FACE_ONLY`)

Per region, checkpoints A = Reader V3 and B = Erwin Nieuwlaar's dense_native 16k (same as v2, so numbers stay
comparable), both run with villa `--direction both` (two faces), villa defaults otherwise, on the node A cards'
17-layer window of the **official** surface volume (no own renders, so v2's deviation D2 does not apply):

* valid = pixels on the segment mesh with non-zero CT on every layer of the window.
* I_f = IoU of the top 3 % valid pixels of A_f and B_f (`top_iou`, q = 0.03; ties at the floor never count).
* f* = argmax(I_fwd, I_rev); S1 = I_f* / max(I_other, 0.001).
* **FLAG** iff I_f* >= 0.10 **and** S1 >= 2.0. Otherwise **NOTHING**.
* **NOT EVALUABLE** iff fewer than 80 % of the region's pixels are valid (counted as not-FLAG for sensitivity, and
  excluded from N_blank for specificity).
* Reported, not part of the decision: p of I_f* against 192 circular shifts of B (min shift 150 px, seed 0), I_other,
  and PR #2318's face_consistency if `face_check` is run.
* The IoU floor is required: on the seen data, a blank tile had S1 = 35 with I = 0.038. Face asymmetry alone is not a
  rule.

A FLAG is a pointer for compute and a human look, never "ink".

## 4. Seen data (design / diagnosis only; NOT used for validation)

* The 16 node D v2 regions and 24 synthetic controls (`results/irp/node_d_v2/`): face-only flagged 9/12 positives,
  0/4 blanks (only 1 blank had valid CT, so specificity was untested there), 0/12 block-shuffle controls and 2/12
  mismatched-region controls (`0500P2-371_pos1|b_A_with_B_of_0500P2-377_pos0`,
  `0500P2-377_pos0|b_A_with_B_of_0500P2-377_pos1`). Under criterion 3 below, those 2 hits **would fail** the seen
  data; the criterion was not loosened to pass it.
* With this file's evaluability rule (>= 80 % valid CT), the seen set gives **8/12** positives flagged (5 of 6
  segments), not 9/12: `0500P2-371_pos1` has 29 % valid CT on the window and becomes NOT EVALUABLE. Blanks: 0
  flagged, 1 evaluable (`0172-w082_bla0`: I 0.038, S1 35, NOTHING), 3 not evaluable.
* PHerc.343, Erwin's First Letters region: FLAG (I 0.434, S1 2.33). PR #2318 reports 3.23 on its own crop.
* PHerc1203 and every private dataset: excluded from both design and evaluation.

## 5. Evaluation sets (unused at hashing time)

There is **no unused local data** to evaluate on: every local two-direction, two-checkpoint prediction is either the
v2 set or design data (section 4). So the targets below are fixed now and must be generated (GPU inference,
4 runs per segment = 2 checkpoints × 2 directions, to be approved separately; nothing is authorised by this file).

**Set F1 (primary, independent segments).** Open-data segments with a team ink map in the public bucket that are
not among: PHerc0172 w082 / w083, PHerc0500P2 00371 / 00377, PHerc0841 w00, PHerc0009B 20250919125754, PHerc0814
46527, any PHerc.343 segment, any PHerc1203 segment, and any segment the model cards in `cards/` list as training
data of A or B. Mechanical choice: list the bucket on the evaluation day, sort by (scroll, segment ID), take the
first segment per scroll and then the second, up to 6 segments, at most 2 per scroll. The listing and the choice are
committed before any inference. If fewer than 4 segments qualify, F1 is **NOT RUN** and that is reported.

**Set F2 (secondary, same segments as v2, labelled "not independent").** Tiles of the six v2 segments that were
never rendered or inferred: the next 2 positive tiles per segment by the v2 selection rule (`select_regions.py`),
excluding the v2 tiles and their edge neighbours. F2 shares segments, models and references with the seen data, so
it can support but never replace F1.

**Regions, both sets:** 5 × 5 mm tiles, selection as in v2 §5 (Otsu on the team map, positives = 2 per segment with
the highest reference-ink fraction among tiles with >= 3 strokes, not sharing an edge). **Blanks:** no reference ink
inside the tile or within 1 mm, **and** >= 80 % valid CT on the window (fixes v2's D4, where 3 of 4 blanks lay
outside the scan volume), the 2 per segment farthest from reference ink. "Blank" still means "no ink in the
reference", not proven blank.

**Synthetic controls, per positive region (as v2):** (a) B block-shuffled in 0.5 mm blocks; (b) A from positive
region i with B from positive region i+1 (cyclic, in selection order).

## 6. Pass criteria (fixed now; per set)

1. **Sensitivity:** FLAG in >= ceil(2/3 × N_pos) positive regions, and in at least one positive region of
   >= ceil(2/3 × N_segments) segments.
2. **Specificity:** FLAG in <= max(1, floor(0.10 × N_blank)) evaluable blank regions. Tested only if N_blank >= 4;
   otherwise specificity is **UNTESTED**.
3. **Controls:** 0 FLAG among (a) block-shuffle controls, and <= max(1, floor(0.10 × N_b)) among (b)
   mismatched-region controls.

Verdict: **ACCEPTED** if 1, 2 (tested) and 3 hold; **PROVISIONAL** if 1 and 3 hold and 2 is UNTESTED; **REJECTED**
otherwise. Node D's default rule changes from v1 to face-only only if F1 is ACCEPTED. F2 alone can give at most
"PROVISIONAL (same segments)". All regions are reported, including failures, numbers only, no images.

## 7. Order of work

(1) Hash this file and commit; (2) list the bucket, select F1/F2 regions with reference maps and meshes only, commit
the selection; (3) inference (approved separately); (4) score with the committed code; (5) report everything.
