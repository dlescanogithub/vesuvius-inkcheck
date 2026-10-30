# CI for model pull requests

`inkcheck` ships a composite GitHub Action (`action.yml` at the repository root). In a model repository, regenerate
the ink map of a labelled segment in your own step, then:

```yaml
- id: ink
  uses: dlescanogithub/vesuvius-inkcheck@v0.3.0
  with:
    prediction: predictions/seg.png
    reference: reference/seg_ref.png
    pred-um: "9.6"
    ref-um: "19.2"
    args: "--workers 2"                      # any check option, e.g. --ref-origin, --mask, --ref-mask
    card-args: "--scroll PHerc0139 --segment 20250108000005-w030 --model my-model --model-run ${{ github.sha }}"
    fail-on: FAIL                            # FAIL (default; also INVALID), WEAK, or never
```

What it does:

1. installs inkcheck (the action's own checkout, or `install:` to pin e.g. `vesuvius-inkcheck==0.3.0`);
2. runs the check, then the **wrong-place negative control** (`control: "0"` to skip);
3. builds and validates the ink card (`inkcheck card ... --control ...`, `inkcheck report --validate`);
4. appends the card's Markdown to the job summary and sets outputs `verdict`, `card`, `card-md`;
5. fails the job according to `fail-on`. A passing control makes the card **INVALID**, which always fails
   unless `fail-on: never`.

A complete example workflow is in
[`examples/ci/model-pr.yml`](https://github.com/dlescanogithub/vesuvius-inkcheck/blob/main/examples/ci/model-pr.yml).

## Run the same thing locally

The action is a thin wrapper around `scripts/inkcheck_ci.sh`:

```bash
INKCHECK_PRED=pred.png INKCHECK_REF=ref.png INKCHECK_PRED_UM=9.6 INKCHECK_REF_UM=19.2 \
INKCHECK_ARGS="--workers 4" INKCHECK_CARD_ARGS="--model my-model" bash scripts/inkcheck_ci.sh; echo $?
```

Exit 0 means the gate passed, 1 means it failed, and > 1 means a crash (inkcheck itself exits 4 on any error,
which the script passes through).

!!! warning "Data in CI"
    Do not commit scroll data or reference maps to a public repository; fetch them at run time from their
    official source, within the data terms.
