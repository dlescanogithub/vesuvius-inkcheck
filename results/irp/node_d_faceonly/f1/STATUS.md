# F1 status
- 2026-10-28 ART: listing + pick + region selection committed (this commit). No inference run yet. 12 positives, 2 blanks.
- 2026-10-28 23:36 ART: scorer (score_f1.py) and pod inference script (job_f1_pod.py) committed before inference; dry run on CT-layer stand-in maps OK (valid fractions on the pod fetch path match selection).
- 2026-10-28 20:45 ART: inference done (1 pod, RTX 3090, 0.124 h, ≈ $0.02; pod deleted, API 404). Scored with score_f1.py: **REJECTED** (4/12 positives, 3/6 segments; specificity UNTESTED, 1/2 blanks flagged; controls 0/12 + 0/12). See RESULTS.md, results_f1.json.
