# FAQ

**Is PASS ground truth?**
No. References are model outputs or human annotations. PASS means the prediction agrees with that reference beyond
search-matched chance *and* at letter level (r_bp ≥ 0.20, stroke recall ≥ 0.50).

**Why shift nulls instead of a plain p-value of r?**
Registration searches for the best offset, which inflates any correlation. Each null re-runs the same search with the
reference moved to a wrong place, so the null distribution includes the search.

**What does WEAK mean?**
The agreement is significant but below letter level: something ink-like is found, but not enough strokes to read.

**When is a card INVALID?**
When a negative control (e.g. the prediction moved to the wrong place) PASSes: the check cannot discriminate on that
segment, so its node-A verdict is not trusted.

**What is the saturation warning?**
On 8-bit maps where most valid pixels are bright, correlation and AUC can look fine while the map carries little
information. The card warns; inspect the map before trusting a PASS.

**Different resolutions?**
Give both pixel sizes (`--pred-um`, `--ref-um`); maps on the same segment canvas share origin (0,0) after scaling.
Crops need `--ref-origin`.

**Does it need a GPU?**
No. inkcheck only scores existing maps. The leaderboard and the reference set are built on CPU from maps and labels
already published.

**Which data can I publish?**
Numbers and verdicts. Do not redistribute scroll images or maps; see the data terms at scrollprize.org/data. Some
datasets carry publication reservations; respect them.

**Is the ink-card schema stable?**
`1.x` only adds optional fields. Validate with `inkcheck report --validate`.

**How do I cite it?**
See `CITATION.cff` in the repository.
