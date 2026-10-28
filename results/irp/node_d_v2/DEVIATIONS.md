# Node D v2 held-out validation: deviations from PREREG_NODE_D_V2.md

Written 2026-10-28 ~14:10 UTC-3, after region selection and BEFORE any v2 render, inference or score.
The prereg file is unchanged (sha256 1bc3423ed79b6bf37918f674433e4720829529bd702af189a14898461fa43d4c re-checked).

**D1. Padded-region inference instead of whole-segment predictions (§3, last sentence).** The off-winding control
needs surfaces moved ±round(P/2) voxels, i.e. new renders from the CT volume; rendering and inferring the six whole
segments at three depths would need tens of GB of CT chunks per PHerc0172 segment, beyond the approved USD 5 GPU
budget and the box disk. Each selected 5 x 5 mm tile is therefore rendered and inferred with a 384 px margin on every
side (= one full Reader V3 patch; dense_native patch is 128 px), and only the core tile is scored. villa normalises
per patch, so every patch that touches a core pixel sees only real data; what differs from a whole-segment run is the
patch-grid phase of the Hann blending. Per the prereg header, all v2 numbers are labelled "exploratory under D1".

**D2. Renders come from our own tifxyz renderer, not the official surface volumes.** The ±P/2 offsets need layers
outside the official 28-33-layer surface volumes, so all three depths are rendered with the same code
(`tools/render_tifxyz.py` normal convention = official VC layer order) for consistency. The depth-0 render is checked
against the official surface volume of the same tile (best-matching layer and correlation, reported in RESULTS.md);
the 17-layer window equals the node A cards' window (layer-start/end as in the cards), located through that match.

**D3. Selection implementation details not fixed in §5** (in `select_regions.py`, committed before rendering):
reference resampled to the segment canvas with a box filter; Otsu on valid pixels; strokes counted as connected
components inside the tile; "distance from any reference ink" measured on a /8 max-pooled grid; validity from the
mesh (x > 0). Selection found 12 positive regions (6/6 segments) but only 4 blank regions (w082: 1, w083: 0,
371: 0, 377: 1, 0841: 0, 0009B: 2), so N_blank = 4 and the blank allowance is max(1, floor(0.4)) = 1.

**D4. Pitch, alignment and window details, fixed after rendering and before any model inference**
(`check_align_pitch.py`, `align_pitch.json`):
- The CT profile for P averages the core-tile pixels that are valid on the depth-0 card window (the scoring pixels), over
  all 129 samples (±64). Samples outside the masked volume count as 0. P with the stricter "valid on all 129 samples"
  pixel set is recorded as `pitch_allvalid`; it differs in 2 of 16 regions (0841-w00_pos1: 11.6 vs none; 371_pos1:
  15.7 vs 17.3).
- Alignment: the depth-0 render matches the official surface volume at a constant layer shift of 48-51 per segment
  (correlation 0.91-0.98 at the window centre, 13/16 regions). The card window is mapped through that shift.
- Three blank regions (377_bla0, 0009B_bla0, 0009B_bla1) have **no valid CT pixels** on the card window: they lie
  outside the masked scan volume. They are NOT EVALUABLE, so they cannot be false-flagged. The specificity test
  therefore rests on one effective blank (0172-w082_bla0), which is reported as a limitation.
- Regions with no pitch peak in 6-60 voxels are NOT EVALUABLE under §3 (3 of 12 positives: 0172-w083_pos0,
  0500P2-371_pos0; and 0172-w082_bla0 among blanks). The v1 and face-only columns still score them.
- One mosaic per depth slot (all regions side by side, each padded by 384 px, so no patch that touches a core
  pixel crosses into another region) replaces per-region runs. Model calls are villa defaults plus `--direction both`.
