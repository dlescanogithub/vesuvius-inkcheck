# IRP on Erwin Nieuwlaar's PHerc. 343 First-Letters region: pre-registration

Written 2026-10-28 ~10:30 UTC-3 (13:30 UTC), BEFORE any render, CT read or ink-model output of this region
was produced or viewed by us. The only inputs seen so far are text/JSON: Erwin's README, mesh meta.json, the
letter-box coordinates (inputs/*_letter_boxes.json, locations only) and the public Substack post (which shows his
ensemble image; we did not download or analyse it).

## Data
- Scroll PHerc. 343 (rolled), volume 20250521140437-8.640um-1.2m-116keV-masked.zarr level 0 (open-data bucket).
- Mesh: github.com/Nieuwlaar/pherc343-first-letters outputs/concat_w047-w048_R5B2_z9500-11000.tifxyz
  (sha256 of x/y/z.tif as in that repo's SHA256SUMS), 20 px per node.
- Render convention copied from Erwin: layer k samples the CT at (k - 32.5) voxels along the mesh normal,
  + = away from the scroll axis; d = k - 33. We render only layers needed for d = +1 (his image depth).
- Crop L (letters): raw-frame rows 600:2100, cols 650:5550 (contains all 18 letter boxes, ~1.5 mm margin).

## Models (none trained on PHerc. 343)
dense_native-016000, ink_9um hybrid_3d2d seed42 / seed43 step 75000 (villa infer, layers 26..42 = d+1 window,
overlap 0.5), Hecate 9.6 um (16 planes at 9.6 um centred on layer 33.5). Reading side = the direction Erwin calls
"reverse"; the OPPOSITE direction (his "blind side") is our depth-reversed null. Ensemble = mean of the four
per-model z-scores (Erwin's definition), z-scores pooled over valid pixels of the crop, reading side.

## Primary test: node D candidate rule (copied from results/irp/1203_PREREG.md §0 + §0c, no new thresholds)
On the common ~9.6 um grid inside crop L, per model, with p = map probability:
- (i) stroke-sized components (p>0.5, 0.03-1.5 mm^2) per cm^2 on the reading side >= 2x the depth-reversed null;
- (ii) >= 5 such components in the crop;
- (iii) r(map, another checkpoint's map) >= 0.3 for at least one other checkpoint;
- (iv) the 1203 rule's visual criterion "strokes 0.1-0.5 mm wide" is replaced by the automatic proxy already
  computed in score.py: median stroke width (2 x distance transform on the skeleton) within 100-500 um.
Region verdict: CANDIDATE if >= 2 checkpoints satisfy (i)-(iv); otherwise NOTHING.
Prediction (stated in advance): CANDIDATE, because papyrologists confirmed letters here. If the result is NOTHING,
the node D rule has a false negative on a confirmed-text region, and that must be reported against our
PHerc1203 NO_CANDIDATE card.

## Secondary (descriptive, NOT an independent reference)
The letter boxes were drawn by Erwin while looking at the 4-model ensemble, so they are not independent of these
models. We report, per model and ensemble, the AUC of reading-side p inside vs outside the boxes within crop L, with
a null of 2000 random translations of the whole box set (wrapped inside crop L) and the null AUC of the blind side.
Verdict label: CONSISTENT / NOT_CONSISTENT only; never PASS, because node A requires an independent reference.

## Publication / licence
No CT renders, ink maps or images of this region go into the public repo; only numbers and verdicts.
