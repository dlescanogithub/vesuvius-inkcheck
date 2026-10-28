# Readability card: PHerc1203 at 2.4 µm (unlabelled)

**Scroll / segment:** PHerc1203 zones z965, z743, z031, 1203c (+ phase-3 tile p0_965)
**Verdict path:** D  
**Bottom line:** No candidate in 19 zone/model pairs under the pre-registered rule.  
**Recommended next step:** Extra compute (e.g. GPU) is not justified by this evidence; only an exhaustive pass would change it.

No reference read exists, so node A cannot run. Zones rendered from the 2.403 µm scan; models: native 2.4 µm hecate (scrollprize/hecate) and dense_native at 2.4 and 9.6 µm; null = same model on depth-reversed input.

![decision tree](pherc1203.png)

## Node D: Unlabelled segment: does any zone meet the pre-registered candidate rule?

**NO_CANDIDATE**: No candidate in 19 zone/model pairs under the pre-registered rule.

- Pre-registration: `../../results/irp/1203_PREREG.md` (sha256 ce5fed3555db…).
- Rule written 2026-10-27T18:55:00-03:00, first result viewed 2026-10-27T20:04:15-03:00: rule came first.
- Rule as pre-registered in §0: components ≥ 2× reverse-depth null AND r ≥ 0.3 with a different checkpoint, then visual check (strokes 0.1–0.5 mm). Same-checkpoint agreement (dn@9.6 vs native dn) does not count.
- Visual check (hires_test/fig/*_before_after.png): hecate fires in sparse spots at patch edges, dn@2.4 is uniform speckle; recorded as no stroke-like shapes.
- Phase-3/4 tiles are still running; re-run examples/irp/export_1203.py and this card to include them.
- Compute: A full 1203 pass (≈ 23 cm², stride 128, both directions, plus the r152 teacher) is ≈ 72 h on this CPU box or an ESTIMATED 4–12 GPU-hours (≈ US$4–24); not justified without a candidate (hires_test/gpu_verdict.json).

| zone | model | comps/cm² (null) | n comps | r vs other ckpt | width mm | outcome | why |
|---|---|---|---|---|---|---|---|
| 1203c | hecate-2.4 native | 24.8 (24.8) | 6 | 0.21 | – | nothing | components 24.8 vs reverse-depth null 24.8 (ratio 1.00 < 2.0); agreement with a different checkpoint r = 0.21 (< 0.3) |
| 1203c | dense_native @2.4 iso | 132.1 (144.5) | 32 | 0.21 | – | nothing | components 132.1 vs reverse-depth null 144.5 (ratio 0.91 < 2.0); agreement with a different checkpoint r = 0.21 (< 0.3) |
| 1203c | dense_native @9.6 iso | 0.0 (16.5) | 0 | 0.21 | – | nothing | components 0.0 vs reverse-depth null 16.5 (ratio 0.00 < 2.0); agreement with a different checkpoint r = 0.21 (< 0.3) |
| p0_965 | hecate-2.4 native | 16.7 (27.8) | 6 | 0.06 | – | nothing | components 16.7 vs reverse-depth null 27.8 (ratio 0.60 < 2.0); agreement with a different checkpoint r = 0.06 (< 0.3) |
| p1_031 | hecate-2.4 native | 25.0 (27.8) | 10 | 0.04 | – | nothing | components 25.0 vs reverse-depth null 27.8 (ratio 0.90 < 2.0); agreement with a different checkpoint r = 0.04 (< 0.3) |
| p2_537 | hecate-2.4 native | 13.9 (11.1) | 5 | 0.16 | – | nothing | components 13.9 vs reverse-depth null 11.1 (ratio 1.25 < 2.0); agreement with a different checkpoint r = 0.16 (< 0.3) |
| p3_965 | hecate-2.4 native | 16.7 (16.7) | 6 | 0.15 | – | nothing | components 16.7 vs reverse-depth null 16.7 (ratio 1.00 < 2.0); agreement with a different checkpoint r = 0.15 (< 0.3) |
| p4_031 | hecate-2.4 native | 5.6 (8.3) | 2 | -0.01 | – | nothing | components 5.6 vs reverse-depth null 8.3 (ratio 0.67 < 2.0); agreement with a different checkpoint r = -0.01 (< 0.3) |
| p5_031 | hecate-2.4 native | 8.3 (5.6) | 3 | -0.03 | – | nothing | components 8.3 vs reverse-depth null 5.6 (ratio 1.48 < 2.0); agreement with a different checkpoint r = -0.03 (< 0.3) |
| p6_031 | hecate-2.4 native | 8.3 (22.2) | 3 | -0.03 | – | nothing | components 8.3 vs reverse-depth null 22.2 (ratio 0.37 < 2.0); agreement with a different checkpoint r = -0.03 (< 0.3) |
| z031 | hecate-2.4 native | 16.7 (8.3) | 6 | 0.13 | – | nothing | agreement with a different checkpoint r = 0.13 (< 0.3) |
| z031 | dense_native @2.4 iso | 89.0 (122.3) | 34 | 0.07 | – | nothing | components 89.0 vs reverse-depth null 122.3 (ratio 0.73 < 2.0); agreement with a different checkpoint r = 0.07 (< 0.3) |
| z031 | dense_native @9.6 iso | 19.5 (16.7) | 7 | 0.13 | – | nothing | components 19.5 vs reverse-depth null 16.7 (ratio 1.17 < 2.0); agreement with a different checkpoint r = 0.13 (< 0.3) |
| z743 | hecate-2.4 native | 27.8 (41.7) | 11 | 0.09 | – | nothing | components 27.8 vs reverse-depth null 41.7 (ratio 0.67 < 2.0); agreement with a different checkpoint r = 0.09 (< 0.3) |
| z743 | dense_native @2.4 iso | 150.1 (141.8) | 57 | 0.03 | – | nothing | components 150.1 vs reverse-depth null 141.8 (ratio 1.06 < 2.0); agreement with a different checkpoint r = 0.03 (< 0.3) |
| z743 | dense_native @9.6 iso | 38.9 (22.2) | 15 | 0.09 | – | nothing | components 38.9 vs reverse-depth null 22.2 (ratio 1.75 < 2.0); agreement with a different checkpoint r = 0.09 (< 0.3) |
| z965 | hecate-2.4 native | 22.2 (22.2) | 8 | 0.13 | – | nothing | components 22.2 vs reverse-depth null 22.2 (ratio 1.00 < 2.0); agreement with a different checkpoint r = 0.13 (< 0.3) |
| z965 | dense_native @2.4 iso | 166.8 (144.5) | 63 | 0.00 | – | nothing | components 166.8 vs reverse-depth null 144.5 (ratio 1.15 < 2.0); agreement with a different checkpoint r = 0.00 (< 0.3) |
| z965 | dense_native @9.6 iso | 16.7 (38.9) | 6 | 0.13 | – | nothing | components 16.7 vs reverse-depth null 38.9 (ratio 0.43 < 2.0); agreement with a different checkpoint r = 0.13 (< 0.3) |

*Next:* Extra compute (e.g. GPU) is not justified by this evidence; only an exhaustive pass would change it.  
*Automation:* automatic rule + pre-registration check; visual criterion manual.

---
Generated by `inkcheck report` (Ink Recoverability Protocol, CPU-only). Verdict rules: README → 'The protocol'.
