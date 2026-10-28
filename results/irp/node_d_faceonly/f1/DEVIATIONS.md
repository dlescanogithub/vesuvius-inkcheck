# F1 — implementation choices and deviations (written and committed BEFORE any inference)

Prereg: `../PREREG_NODE_D_FACEONLY.md` (sha256 ba553d03…, commit 22feecb). Rule, thresholds and pass criteria are unchanged.

1. **Listing.** Public bucket `vesuvius-challenge-open-data` crawled 2026-10-28 (`crawl_f1.py`, `crawl2_f1.py`);
   segments with ink-detection map + surface volume + mesh. Exclusions as in prereg §5 (`list_and_pick_f1.py`):
   seen six, PHerc0814 46527, all PHerc0343/0343P, Reader V3 training timestamps, dense_native training tags
   (wNNN / 5-digit ids from `train_dense_native.json`). Two scrolls that are private scouting / private training
   targets of this project are dropped from the listing entirely (not named here). Pick: first eligible per scroll in
   (scroll, segment id) order → 7 scrolls qualify, cap 6 → PHerc1667 not used; no second round.
2. **Inputs per segment** (`fetch_sel_inputs_f1.py`): surface volume = the ~8–9 µm one (7.91/8.64/9.362/9.366 µm);
   mesh = the tifxyz "-on-<that volume>"; team ink map = newest model-run timestamp in `ink-detection/`.
   Maps made on finer volumes are box-resampled onto the surface-volume canvas (shared UV; aspect ratios checked
   equal to 3 decimals), in 256-row strips (one map is 4.5 GB as uint8).
3. **Window.** 17 layers centred: start (D−17)//2 (reproduces node A card windows for 0172, 0500P2, 0841, 0009B).
4. **Blank CT condition** (prereg §5 "≥ 80 % valid CT on the window") is checked with raw CT only, in distance
   order, first 2 passing (≤ 40 visited). Only 2 blanks exist in total (PHerc0139); the other segments have no tile
   ≥ 1 mm from reference ink (0009B: one candidate, 0.0 valid CT). **N_blank = 2 < 4 → specificity is UNTESTED by
   construction; the best attainable verdict for F1 is PROVISIONAL.**
5. **Inference geometry.** Each 5 mm tile is inferred with a 384 px CT margin on every side (clipped at the volume
   edge, zero beyond), tiles laid out in one mosaic per segment run, then cropped back to the tile (as node D v2 D1).
   Both checkpoints, `--direction both`, `--layer-start 0 --layer-end 17` on the window-extracted 17-layer zarr.
6. **Valid pixels** for the rule = non-zero CT on all 17 window layers inside the tile (prereg §2). Positive
   PHerc0500P2 r9c5 has 0.735 valid CT at selection → it will be NOT_EVALUABLE (counts as not FLAG in §6.1).
7. Controls exactly as prereg §5: (a) B block-shuffled in 0.5 mm blocks (seed 0); (b) A of positive i with B of
   positive i+1, cyclic over the 12 positives in `regions_f1.json` order (segment order, then positive order).
