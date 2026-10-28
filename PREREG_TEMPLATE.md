# Pre-registration template: hunting for ink on an unlabelled segment (IRP node D)

Copy this file, fill it in, and **save it before you look at any model output on the target segment**.
Then record its write time and sha256 in the case file (see the end). The hash lets anyone check the rule
was not changed later. The timestamps let them check it came first.

Worked example: `results/irp/1203_PREREG.md`. That is the rule we used on PHerc1203 at 2.4 µm, copied word for word from `hires_test/FINDINGS.md`.

---

## 0. Identity

| field | value |
|---|---|
| Scroll / segment(s) / zones | e.g. PHerc1203, zones z965, z743, z031 |
| Scan (voxel size, energy, source) | e.g. 2.4 µm, … keV |
| Checkpoints (≥ 2, trained independently) | e.g. A = …, B = … |
| Who wrote this rule, when (ISO 8601 with time zone) | |
| Have you seen any prediction on these zones? | **must be "no"** |

## 1. Null (what "nothing here" looks like)

The null has to be the same pipeline on the same zone with the ink signal destroyed. A generic baseline will not do.

- [ ] **Reverse-depth null** (default): run the same checkpoint on the same zone with the layer order flipped. Ink lies on the
  recto surface, so flipping the layers keeps texture and noise statistics but breaks the ink geometry.
- [ ] Other (describe, and say why it keeps the noise but kills ink): ………

## 2. Candidate rule (all must hold; thresholds fixed now)

| # | criterion | default | your value |
|---|---|---|---|
| 1 | connected ink components (after the fixed threshold below) vs the null | ≥ **2×** null | |
| 2 | minimum component count (guards against "2 vs 1") | ≥ 5 (set 0 to disable, and say why) | |
| 3 | agreement with a **different** checkpoint on the same zone (Pearson r of band-passed maps) | r ≥ **0.3** | |
| 4 | stroke width (if measurable) | **0.1–0.5 mm** | |
| 5 | visual check by a person: stroke-like shapes, not fibres, cracks or layer edges | yes / no | |

Fixed processing: threshold = ………, band-pass = ………, minimum component area = ………, analysis voxel = ……… µm.
You may not change these after the first look.

## 3. Interpretation, fixed in advance

- A zone that meets 1–4 is a **candidate**. Criterion 5 still has to be checked by a person.
- **A candidate is never "ink found".** It is a reason to spend more effort on that zone: more compute, a finer
  scan, or expert review. Nothing more.
- No zone meeting the rule = **NO_CANDIDATE**. That covers these zones and checkpoints only. It says nothing about the whole scroll.

## 4. Stop and compute rules (fixed now)

- Zones to test, in this order: ……… (no adding zones after you see results, unless you write an addendum, see §6).
- Stop when: ……… (e.g. all listed zones are scored, or N CPU-hours are used).
- Extra compute (GPU, full-segment pass) is justified **only** if at least one candidate passes 1–5. Write the budget here: ………

## 5. What you will report regardless of outcome

Every zone/model pair: components, null components, ratio, r with the other checkpoint, width, visual check. Negative results too.

## 6. Addenda

Changes after the first look are allowed **only** as dated addenda (ISO time with zone, before the outputs they
govern). Results judged under a late addendum are labelled *exploratory*. In our 1203 run the "≥ 5 components" addendum
(§0c) could not be shown to come before one phase-3 output, so the card applies only the original §0 rule (`min_components = 0`).

---

## How to use it with `inkcheck report`

```json
"unlabeled": {
  "prereg": "path/to/YOUR_PREREG.md",
  "prereg_written": "2026-10-27T18:55:00-03:00",
  "first_result":   "2026-10-27T20:04:15-03:00",
  "rule": {"min_ratio": 2.0, "min_components": 5, "min_r_other": 0.3, "width_mm": [0.1, 0.5]},
  "zones_file": "path/to/zones.json"
}
```

`zones.json` is a list of `{zone, model, comps, comps_null, n_components, r_other, stroke_width_mm, visual_strokes}`.
`visual_strokes` is `true`, `false` or `null` (not yet checked). `inkcheck report` hashes the prereg file, checks that
`prereg_written < first_result`, and labels the verdict EXPLORATORY if it cannot verify that order.
