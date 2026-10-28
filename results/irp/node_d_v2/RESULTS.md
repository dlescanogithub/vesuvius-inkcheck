# Node D v2 held-out validation — RESULTS

**Verdict under PREREG_NODE_D_V2.md (sha256 1bc3423ed79b6bf37918f674433e4720829529bd702af189a14898461fa43d4c, re-checked
unchanged before scoring): v2 is REJECTED.** Node D stays v1 with its caveat ("NOTHING is not informative for tightly
wound regions"). This is a negative result and is reported as such. All numbers are exploratory under deviations D1–D4
(`DEVIATIONS.md`); D5 below concerns a descriptive column only.

Run: one RTX A4500 pod, 2026-10-28 (UTC-3), 6 inference passes per checkpoint (A = Reader V3, B = dense_native 16k;
depth 0, +P/2, −P/2; villa `--direction both`), all exit 0. Scoring on the box with the committed
`score_node_d_v2.py`. Per-region numbers: `RESULTS_TABLES.md`; full output: `results_v2.json`.

## Pass criteria (§6)

| criterion | needed | observed | holds |
|---|---|---|---|
| 1. Sensitivity | CANDIDATE in ≥ 8 of 12 positive regions, in ≥ 4 of 6 segments | 1 region (0500P2-371_pos1), 1 segment | **no** |
| 2. Specificity | ≤ 1 of 4 blank regions | 0 (but 0 of 4 blanks evaluable, see D4) | yes (tests nothing) |
| 3. Controls | 0 of 24 synthetic controls | 0 | yes |

Positive regions: 1 CANDIDATE, 9 NOTHING, 2 NOT EVALUABLE (no winding pitch: 0172-w083_pos0, 0500P2-371_pos0).
Blank 0172-w082_bla0 also has no pitch. Blank regions: 4 of 4 NOT EVALUABLE.

## Side by side (descriptive, §6; does not change acceptance)

| statistic | positives flagged (of 12) | segments | blanks flagged |
|---|---|---|---|
| v2 | 1 | 1 | 0 |
| face-only (PR #2318 statistic: I ≥ 0.10 and S1 ≥ 2.0) | 9 | 5 | 0 |
| v1 (component-density ratio vs other face) | 0 | 0 | 0 |

v2 is **not** more sensitive than face-only; we do not claim it. The face-only count is corrected per D5.

## Why v2 fails here (observation, not a tested claim)

The step that removes almost every positive is the off-winding control. On the face that wins, the two checkpoints
agree about as much with the surface moved ±P/2 as on the surface itself (S2 ≈ 0.7–1.2 in 7 of the 10 evaluable
positives; S2 ≥ 2.0 needed). Two-model agreement at ±P/2 is therefore not ink-free on these segments, the same failure
v1's reversed-depth null had. Possible reasons, none tested: a 17-layer window moved by P/2 still overlaps the
neighbouring sheet surfaces, or the models agree on papyrus structure that persists through depth. The spatial null
behaved as intended (p = 0.0052, the floor, on 8 positives) and none of the 24 synthetic controls was flagged.

## PHerc.343 (Erwin region) under v2 — design data, diagnosis only

v2 says **NOTHING** again, so the node D false negative on 343 is **not** fixed by v2. Reading face (rev):
I = 0.434, p = 0.0052, S1 face asymmetry = 2.33 (PR #2318 reports 3.23 on its own crop), but the off-winding IoUs are
0.296 / 0.438, giving S2 = 0.99. Face-only would flag it (yes). v1 on the same maps: NOTHING. See `RESULTS_TABLES.md`.

## Job 1 (same pod): v1 on 343 with 4 models, GPU rerun of `results/irp/pherc343_erwin/PREREG.md`

Render tree-hash matched the box. Verdict **NOTHING** (0 of 4 models pass; CANDIDATE needs ≥ 2). Null ratios:
dense_native 1.15, seed42 1.24, seed43 0.99, Hecate-9.6 1.28 (needed ≥ 2.0); the other three criteria (≥ 5 components,
r ≥ 0.3 with another model, median stroke 100–500 µm) pass for all four. The CPU villa result (1.15 / 1.26 / 0.99) is
reproduced.

## Deviations added at scoring time

**D5. Face-only column, scorer bug (descriptive only).** `score_node_d_v2.py` stores `face_only` as a NumPy bool, and the
summary counts it with `is True`, so the committed summary reports face-only as 0 / 0. The per-region `face_only` field
(saved as 1.0 / 0.0 in `results_v2.json`) is correct, and the table above counts that field: 9 positives, 0 blanks.
The v2 outcome, the three criteria and the verdict use string and integer comparisons and are not affected. The scorer is left unchanged
so that the committed code is what produced `results_v2.json`.

**D5 update (2026-10-28, after scoring).** The scorer is now fixed (`face_only_flag` / `count_flagged` in
`src/inkcheck/node_d_v2.py`, regression test `tests/test_node_d_scorer_bool.py`). `results_v2.json` is kept as the
output of the committed-at-the-time code; the fixed scorer re-run on the same pod outputs is in `results_v2_rescored.json`.
It confirms face-only 9 / 12 positives and 0 / 4 blanks, and adds one number the old summary never reported:
face-only flags **2 of 24 synthetic controls** (both mismatched-region pairs (b) on PHerc0500P2, p = 0.0052 each).
v2, v1 and the verdict (REJECTED) are unchanged; every other field matches `results_v2.json`.
