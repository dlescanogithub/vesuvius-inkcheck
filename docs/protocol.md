# The Ink Recoverability Protocol (IRP)

IRP is a decision tree applied per segment. Each node has fixed, pre-registered thresholds (node A's are the defaults of
`inkcheck.core.CheckConfig` and are quoted on every card) and returns a verdict plus a recommended next step.

```
                      ┌─────────────── labelled segment? ───────────────┐
                     yes                                                no
                      │                                                  │
 A  Does the model see known ink?                     D  Does any zone meet the PRE-REGISTERED candidate rule?
    inkcheck vs search-matched shift nulls               rule file hashed and timestamped before the first look
      │ PASS → stop: "readable"                            CANDIDATE → spend more (finer scan / GPU / expert)
      │ WEAK/FAIL                                          NO_CANDIDATE → extra compute not justified
      ▼
 B  Do the scan's quality proxies fall outside what a ~9 µm model tolerates?
      │ SCAN_SUSPECT → rescan / denoise / higher-res model          SCAN_OK ↓
      ▼
 C  Same segment, two scans: does any checkpoint PASS on one scan but not the other?
      SCAN_LIMITED → a better scan helps      SCROLL_SPECIFIC → change the model or labels, not the scan
```

Side nodes: **R** (does the verdict survive a second, independent reference?) and **N** (do negative controls
fail as they must?).

## Node A in detail (what `inkcheck` computes)

1. **Resample** prediction and reference onto a common analysis grid (`--analysis-um`, default the coarser input).
2. **Register**: masked normalised cross-correlation over ±`search_mm` (default 0.5 mm).
3. **Band-pass** both maps (removes slow brightness trends) and compute Pearson `r_bp` at the best offset.
4. **Search-matched nulls**: move the reference to `n_shift_nulls` (default 192) random places at least
   `min_shift_mm` away (plus rotations), re-run the *same* registration search each time and record the best `r`.
   `p` is the rank of the real `r_bp` among the nulls.
5. **Strokes**: connected components of the thresholded reference ≥ `min_stroke_mm2`; stroke recall = fraction
   of reference strokes the prediction covers, compared with its own null (`stroke_recall_chance`).
6. **Verdict**: PASS if `p(r) ≤ 0.01`, `p(stroke recall) ≤ 0.05`, `r_bp ≥ 0.20` and stroke recall ≥ 0.50;
   WEAK if `r_bp` is significant but below letter level; FAIL otherwise.
7. **Tile bootstrap** (2 mm tiles) gives a 95 % CI for `r_bp`, conditional on the registration.

## Controls and saturation (node N)

* `wrong_place`: the same prediction rolled to another part of the canvas. It must FAIL; if it PASSes the check
  cannot discriminate and the card's final verdict is **INVALID**.
* Saturation: on 8-bit maps, if ≥ 50 % of valid pixels are above 128 the card warns that correlation/AUC can pass
  on an uninformative map.

## What PASS means

The references are themselves model outputs or human annotations, so PASS means "agrees with the community read of
this segment beyond chance and at letter level", not ground truth. Leaked checkpoints (trained on the segment) must
be excluded or flagged.

## Pre-registration

For unlabelled segments (node D) write the rule first (template: `PREREG_TEMPLATE.md` in the repository), hash it
(`sha256sum`), and pass the file with `--prereg`: the hash goes into the ink card's `provenance.prereg_sha256`.
