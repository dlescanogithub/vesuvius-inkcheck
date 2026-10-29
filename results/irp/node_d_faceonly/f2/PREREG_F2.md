# Pre-registration: face-only node D, set F2 (specificity: ≥ 4 blank regions)

Status: written, hashed (`PREREG_F2.sha256`) and committed **before** any F2 region is selected and before any F2
model output exists. Nothing in this file may change after hashing; deviations go to `DEVIATIONS.md` in this
directory with a reason, and anything they affect is reported as exploratory.

Parent prereg: `../PREREG_NODE_D_FACEONLY.md` (sha256 ba553d03…). Rule, thresholds, checkpoints, window, valid-pixel
definition, region size and controls are **unchanged** from it (§3, §5). F1 (`../f1/RESULTS.md`) was **REJECTED**
on sensitivity (4/12 positives) and left specificity **UNTESTED** (only 2 blanks existed). This set exists to test the
one thing F1 could not: does the rule FLAG regions with no reference ink?

This F2 replaces the "F2 (same segments as v2)" sketched in parent §5, which could not reach 4 blanks either
(it reuses seen segments, so it is not independent, and they are not known to contain ≥ 4 blanks). That change is made here, before any data, and is the reason for this file.

## 1. What F2 can and cannot decide

* F2 **cannot** make face-only the default rule. F1 is REJECTED; parent §6 allows a default change only if F1 is
  ACCEPTED. F2 is a characterisation, not a rescue.
* Primary outcome: **specificity** (§4.1). Secondary: sensitivity replication and controls on fresh segments (§4.2,
  §4.3). Descriptive only: `saturation_check` per region.

## 2. Segment pool and order (mechanical, from the committed F1 listing)

* Pool: segments marked eligible in `../f1/eligibility_f1.json` (committed in 2df749f; same exclusions as F1:
  seen v2 segments, PHerc0343/0343P, Reader V3 training timestamps, dense_native training tags, private targets),
  **minus the 6 F1 segments** (`../f1/pick_f1.json`), minus segments without both an ~8–9 µm surface volume
  (7.91 / 8.64 / 9.362 / 9.366 µm) and a mesh `-on-<that volume>` in the 2026-10-28 listing.
* Order: round robin over scrolls in sorted order; round k takes each scroll's k-th remaining segment in segment-ID
  order (the F1 rule, continued past round 2).
* Inputs per segment as F1 (`../f1/DEVIATIONS.md` item 2): that surface volume, its mesh, and the team ink map with
  the newest model-run timestamp.

## 3. Regions (selection code = `../f1/select_regions_f1.py`, unchanged)

* Visit segments in order. Each visit runs `select()` unchanged: up to 2 positives (≥ 3 strokes, highest reference-ink
  fraction, not sharing an edge) and up to 2 blanks (no reference ink in the tile or within 1 mm, ≥ 80 % valid CT on
  the window at selection, farthest from ink first, ≤ 40 visited).
* A visit that errors (missing file, canvas ≠ mesh × 20, unreadable map) is logged and skipped; it does not count.
* **Stop** after the first visit at which the cumulative number of blanks is ≥ 8, or after 18 successful visits,
  or after 30 attempts, whichever comes first.
* F2 regions = all positives and all blanks of all successful visits.
* **If fewer than 4 blanks are found, F2 is NOT RUN** (no GPU) and that is reported as "specificity cannot be tested
  on public data with this blank definition".

## 4. Decision rules (fixed now)

Per region, the parent rule: **FLAG** iff I_f* ≥ 0.10 and S1 ≥ 2.0; NOT_EVALUABLE iff < 80 % of the tile is valid
CT at inference. Inference exactly as F1: Reader V3 (A) and dense_native 16k (B), villa `--direction both`,
17 centred window layers of the official surface volume, 384 px margin, mosaic, crop back.

1. **Specificity (primary).** N_be = evaluable blanks. If N_be < 4: **UNTESTED**. Otherwise **SPECIFICITY_OK** iff
   FLAG in ≤ max(1, floor(0.10 × N_be)) of them, else **SPECIFICITY_FAILED**.
2. **Sensitivity (secondary).** Parent §6.1 on the F2 positives: FLAG in ≥ ceil(2/3 × N_pos) positives and in at
   least one positive of ≥ ceil(2/3 × N_seg_pos) segments that have positives. NOT_EVALUABLE counts as not FLAG.
3. **Controls (secondary).** Parent §6.3: 0 FLAG among (a) B block-shuffled in 0.5 mm blocks (seed 0, one per
   positive); ≤ max(1, floor(0.10 × N_b)) among (b) A of positive i with B of positive i+1 (cyclic, selection order).
4. **F2 label** = parent §6 formula applied to F2 (ACCEPTED / PROVISIONAL / REJECTED), reported for completeness
   only; it does not change the default (§1).

Pre-stated reading: SPECIFICITY_FAILED → face-only flags no-ink regions too, so a FLAG is not evidence of ink on these
data. SPECIFICITY_OK with sensitivity FAIL → "specific but insensitive on public segments". Both, OK → still not the
default (F1), but worth a fresh independent set.

## 5. Descriptive (no verdict change)

`inkcheck.node_d_v2.saturation_check` on A (both faces) per region; a sensitivity count excluding saturated regions is
reported as **exploratory**. "Blank" means "no ink in the reference map", not proven blank.

## 6. Cost and safety

One RunPod pod (RTX 3090/4090 community, ≤ USD 0.50/h), the F1 pod workflow, a box watchdog and a pod self-delete
deadline. F1 took 0.124 h (USD 0.02) for 14 regions; F2 (≤ 72 regions) is expected below 0.5 h, **< USD 1**. Hard
budget for the run: USD 3. Pods are deleted when done or on any error.

## 7. Order of work

(1) Hash and commit this file with the selection driver, pod job and scorer; (2) select, commit the selection;
(3) inference; (4) score with the committed scorer; (5) report all regions, numbers only, no images.
