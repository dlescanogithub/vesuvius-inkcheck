# F2 — implementation notes and deviations

Written **after** inference (2026-10-28 ART). None of these touches the prereg rule, thresholds, region set or scorer;
the scorer (`score_f2.py`) and selection (`regions_f2.json`) are the committed files, unchanged.

1. **GPU type.** Prereg §6 names "RTX 3090/4090 community, ≤ USD 0.50/h". At launch RTX 4090 and RTX 3090 community had
   no instances (see `run_log_f2.txt`); the launcher's fallback list was used and gave an **RTX A4500 community at
   USD 0.19/h**, within the price cap. Same checkpoints and inference code; GPU model affects speed, not the rule.
2. **Villa bundle.** The villa code shipped to the pod was re-packed from a read-only clone of the same fork commit
   (39a8cf3) used for F1; content identical.
3. **Selection interpreter.** `select_f2.py` was run with the project's Python 3.14 venv (numpy/zarr), not the package
   dev venv; output hashes are in `SHA256SUMS_selection_f2.txt`.
4. **Budget guard.** Launcher hard budget USD 3 (prereg §6). Actual: 0.19 h wall, balance delta USD 0.04.
5. **Blanks from one scroll.** The mechanical selection (prereg §2) reached 8 blanks, all on PHerc0139 segments. This
   follows the prereg; it is a limitation on generality, reported in `RESULTS.md`.
