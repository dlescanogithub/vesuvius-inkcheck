# Pre-registration: node D v2 (winding-aware candidate rule)

Status: written and hashed **before** any held-out region below was rendered or scored with v2. The sha256 of this
file and the time it was fixed are in `PREREG_NODE_D_V2.sha256` (same directory), committed in the same commit.
Nothing in this file may change after hashing; deviations go to `DEVIATIONS.md` with a reason, and any result
affected by a deviation is reported as exploratory.

Code: `src/inkcheck/node_d_v2.py` (`RULE_V2`, `face_stats`, `candidate_rule_v2`, `estimate_winding_pitch`,
`off_winding_offsets`). At hashing time it has been run **only on synthetic data** (`tests/test_node_d_v2.py`).

## 1. Why v2

Node D v1 (`results/irp/pherc343_erwin/PREREG.md`) scored one model's ink-component density on the reading side
against the same model with the depth order reversed (null). On Erwin Nieuwlaar's PHerc.343 region, which contains
known First Letters, the density ratio was 1.15 / 1.26 / 0.99 for dense_native / seed42 / seed43 (needed: 2.0), so v1
said "nothing" where letters are. Our diagnosis: a reversed render of a thin, tightly wound sheet still reaches ink
(the same face seen from behind, or the facing surface of the neighbouring winding), so reversal is not an ink-free
null. v1's caveat ("NO_CANDIDATE is not informative for this kind of region") stands until v2 is validated here.

## 2. Related work this builds on (credit)

ScrollPrize/villa PR #2318, `face_check` by ketchupbyheinz (open, 2026-10-26;
https://github.com/ScrollPrize/villa/pull/2318), runs two checkpoints (`seed42`, `dense_native`) with
`--direction both` and measures, per face, the agreement of the two checkpoints as the IoU of their top-3 % on-sheet
pixels; **face asymmetry** is the ratio between the faces, **face consistency** the share of 768-px tiles where one
face clearly wins. It reports face asymmetry 3.23 / consistency 0.52 on the same PHerc.343 First Letters segment and
medians 1.36 / 0.14 over 78 survey patches. The PR itself notes that a trace a few voxels outward scores flat.

How v2 relates to it:

* v2 **adopts PR #2318's agreement statistic** (top-3 % IoU between two checkpoints) and reports its face asymmetry
  (S1) unchanged, so numbers are comparable. Our v1 statistic (one model, component density) is replaced by it; the
  difference explains why the PR sees 3.23 where v1 saw ~1.0-1.3 on the same text (two-model agreement is
  face-specific; one model's detection count is not). On our own Erwin-343 data, a closer one-model analogue
  (fraction of high-probability pixels, frac_hi) was already 2.3-3x higher on the reading side; we disclose that we
  saw this during design.
* v2 **adds** what face asymmetry alone does not test:
  1. an **off-winding control**: the same face re-rendered with the surface moved half a winding pitch (±P/2) along
     the normal, P estimated from the CT. Ink on the face must lose its two-model agreement there; papyrus or
     scan texture that persists through depth need not. This also covers the PR's "a few voxels outward" limitation.
  2. a **spatial null** with a p-value: the agreement must beat 192 circular shifts of one checkpoint's map.
  3. a **two-faced branch**: writing on both faces (opisthograph, or the neighbouring winding's ink) gives face
     asymmetry ~1 and is missed by face asymmetry alone; v2 accepts it only if *both* faces pass the off-winding test,
     and flags it.
  4. a **held-out validation with pass criteria fixed here**, including blank regions (specificity), which the PR's
     survey (unlabelled patches) cannot provide.
* If v2 does not beat face-only on the held-out set (section 6, comparison), we will say so: then v2's contribution is
  the controls and the calibration, not sensitivity.

## 3. The rule (fixed; `RULE_V2`)

Per region, checkpoints A and B, faces f in {forward, reverse} (villa `--direction both`), on valid pixels:

* I_f = IoU of the top 3 % pixels of A_f and B_f.
* S1 = max(I_fwd, I_rev) / min(I_fwd, I_rev) (floor 0.001); best face f* = argmax.
* Off-winding: P = `estimate_winding_pitch` of the mean CT profile along the normal over the region (surface volume
  re-sampled ±64 voxels, autocorrelation peak in 6-60 voxels). Both checkpoints re-run on face f with the surface
  offset by +round(P/2) and -round(P/2) voxels. C_f = max of the two off-winding IoUs; S2_f = I_f / max(C_f, 0.001).
  No pitch found in range -> region **NOT EVALUABLE** (counted as not-CANDIDATE, listed).
* p_f = (1 + #null >= I_f) / 193 over 192 circular shifts of B's top-3 % mask, toroidal shift >= 150 px.
* **CANDIDATE** iff on f*: I >= 0.10, p <= 0.01, S2 >= 2.0; and either S1 >= 2.0 ("one-faced"), or the other face
  also has I >= 0.10, p <= 0.01, S2 >= 2.0 ("two-faced", flagged for a human look). Otherwise **NOTHING**.
* Thresholds' origin: 0.10 = the PR's "strong tile" IoU; 2.0 = v1's ratio; top 3 % = the PR's definition. None were
  tuned on held-out data. Visual inspection is not part of the v2 decision (it is recorded separately).

Checkpoints: A = Reader V3, B = Erwin Nieuwlaar's dense_native 16k. The cards in `cards/` record that neither was
trained on the held-out segments below. Renders use the same 8-9 µm native surface volumes as those cards; region maps
are cut from whole-segment predictions (no per-region inference).

## 4. Design data (seen; NOT used for validation)

* Erwin's PHerc.343 region (scan 20250509220833, w047/w048, z 9500-11000): v1 results in
  `results/irp/pherc343_erwin/RESULTS_villa3.json`, including frac_hi; the GPU run with a 4th model (Hecate) on that
  region, in progress at hashing time, will be reported for **diagnosis only** (v1 vs v2 statistics side by side). It
  cannot change any threshold here.
* PHerc1203 zones of `results/irp/1203_PREREG.md` (231446965, 230830031, 221856743 and the phase-3 tiles).
* PR #2318's published numbers (above).

## 5. Held-out validation set (listed now; none used in node D design)

| scroll | segment (open-data bucket) | reference used to pick regions | prior use |
|---|---|---|---|
| PHerc0172 | 20250926122938-w082_20250926122938619_flatboi | team ink map on the bucket | node A card (WEAK) |
| PHerc0172 | 20250926132117-w083_20250926132117595_flatboi | team ink map on the bucket | node A card (WEAK) |
| PHerc0500P2 | 20250716055229-z_dbg_gen_00371_inp_hr | team 2.2 µm ink map | node A card (WEAK) |
| PHerc0500P2 | 20250716055230-z_dbg_gen_00377_inp_hr | team 2.2 µm ink map | node A card (WEAK) |
| PHerc0841 | 20260220213127-w00 | team 2.4 µm ink map | node A/R card |
| PHerc0009B | 20250919125754 | team 2.4 µm ink map | node A/R card (PASS) |

The node A cards used these segments' maps against the references (2D agreement); no two-direction, off-winding or
node D statistic was ever computed on them. PHerc0500P2 is a fragment ("P"); the others are rolled scrolls.

**Region selection (mechanical, uses only the reference map, run and committed before any v2 render):** reference
thresholded with Otsu on the segment grid; non-overlapping 5 x 5 mm tiles with >= 80 % valid pixels.
* Positive: the 2 tiles per segment with the highest reference-ink fraction among tiles with >= 3 reference strokes
  (components >= 0.02 mm²), not sharing an edge -> up to 12 positive regions.
* Blank: tiles with no reference ink inside the tile or within 1 mm of it; the 2 per segment farthest from any
  reference ink (ties: raster order) -> up to 12 blank regions. Caveat: the references are model maps, so "blank"
  means "no ink in the reference", not proven blank.
* Synthetic controls, 2 per positive region: (a) B's maps block-shuffled in 0.5 mm blocks (one permutation for all
  faces/offsets); (b) A from positive region i paired with B from positive region i+1 (cyclic).

## 6. Pass criteria (fixed now)

v2 is **ACCEPTED** only if all three hold:

1. Sensitivity: CANDIDATE in >= ceil(2/3 x N_pos) positive regions, and in at least one positive region of >= 4 of the
   6 segments.
2. Specificity: CANDIDATE in <= max(1, floor(0.10 x N_blank)) blank regions.
3. Controls: CANDIDATE in 0 synthetic control regions.

Otherwise v2 is **REJECTED**: node D stays v1 with its caveat, and the result is published as negative.
NOT EVALUABLE regions count as not-CANDIDATE. Reported side by side on the same regions (descriptive; does not change
acceptance): v1 (component-density ratio vs reversed depth), face-only (I >= 0.10 and S1 >= 2.0, PR #2318
statistic), and v2. We claim "v2 more sensitive than face-only" only if its positive count is higher with no more
blank hits.

## 7. Compute and order of work

12 inference runs per segment (2 checkpoints x 2 directions x 3 depths), 72 in total, GPU; to be approved separately
(no spending is authorised by this file). Order: (1) hash this file; (2) run region selection and commit its output;
(3) render; (4) score with the committed code; (5) report all regions, including failures.
