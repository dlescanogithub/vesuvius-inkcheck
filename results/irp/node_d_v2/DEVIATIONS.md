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
