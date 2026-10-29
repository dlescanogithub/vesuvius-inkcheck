# inkcheck: does a model see *known* ink at this resolution?

`inkcheck` registers a predicted ink map of a Herculaneum papyrus segment to a published reference ink map of the
**same segment** (the two may be at different pixel sizes), then asks whether the agreement is beyond chance **and**
at letter level:

* **band-pass correlation** `r_bp` against **search-matched shift nulls** (the same registration search is run on
  the reference moved to many wrong places, so the search cannot inflate the score),
* **AUC**, break-even F1 and **stroke recall** against its own null,
* a **negative control** (the same prediction in the wrong place) that must FAIL,
* a **saturation warning** for maps where most pixels are "ink".

The verdict is **PASS** (significant and large), **WEAK** (significant, below letter level), **FAIL**, or
**INVALID** when a negative control passes. Every run writes an [ink card](schema.md): a JSON document following the
versioned schema `inkcheck-report-v1.json`, plus a Markdown rendering.

It is node A of the [Ink Recoverability Protocol](protocol.md) (IRP), a CPU-only, pre-registered decision tree for
deciding whether a segment's ink is missing or simply not recovered yet.

```bash
pip install vesuvius-inkcheck        # once published; until then: pip install git+https://github.com/dlescanogithub/vesuvius-inkcheck
inkcheck quick                       # ~2 min on CPU, public data fetched at run time
```

!!! note "Data terms"
    Vesuvius Challenge scroll data are CC BY-NC 4.0 with additional terms ([scrollprize.org/data](https://scrollprize.org/data)).
    inkcheck ships no scroll data and no images drawn from it; inputs are fetched at run time and outputs stay on
    your machine. The public leaderboard and the reference set publish numbers and region coordinates only.
