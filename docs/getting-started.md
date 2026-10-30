# Getting started

## Install

```bash
pip install vesuvius-inkcheck                    # distribution name; import name and command are `inkcheck`
pip install "vesuvius-inkcheck[zarr]"            # + compressed layers-zarr surface volumes (numcodecs)
pip install "vesuvius-inkcheck[schema]"          # + full JSON Schema validation (jsonschema); a built-in validator is used otherwise
# before the first PyPI release:
pip install git+https://github.com/dlescanogithub/vesuvius-inkcheck
```

Python ≥ 3.10, CPU only. Dependencies: numpy, scipy, pillow, tifffile, imagecodecs.

## First run (about 2 minutes)

```bash
inkcheck quick
```

downloads about 1.2 MB of public data (a PHerc0343P team ink map and letters traced on an infrared photograph of the
fragment), runs the check and a wrong-place control, and prints a plain-English verdict. It writes
`out/quick.json` (all numbers), `out/quick.png`, `out/quick.summary.json` and the ink card
`out/quick.card.json` / `out/quick.card.md`.

## Your own maps

```bash
inkcheck PRED.tif REF.png --pred-um 9.6 --ref-um 19.2 --out out/seg \
    --scroll PHerc0139 --segment 20250108000005-w030 --model my-model --prereg PREREG.md
```

* `PRED` is your model's 2-D ink map, `REF` a published ink map of the same segment (tif/png/jpg/npy).
* `--pred-um` / `--ref-um` are their pixel sizes in µm; the comparison runs on the coarser grid unless `--analysis-um`.
* If the prediction is a crop of the reference canvas, give its origin with `--ref-origin y,x` (reference pixels).
* `--mask` / `--ref-mask` restrict the comparison to valid pixels.
* Exit codes: 0 PASS, 1 WEAK, 2 FAIL, 3 INVALID (`inkcheck quick` only: the wrong-place control passed),
  4 ERROR (unreadable input, bad arguments, any crash; message on stderr). Usage errors exit 4 as well, not
  argparse's usual 2, so 2 always means a FAIL verdict.
* Provenance options (`--scroll --segment --model --model-run --scan --prereg/--prereg-sha256`) go into the ink card.
  For official open-data map file names, model, run and scan are parsed automatically.

## Ink cards

```bash
inkcheck report --validate out/seg.card.json       # exit 1 if invalid
inkcheck report --render out/seg.card.json         # Markdown to stdout
inkcheck card out/seg.json --control out/ctrl.json # build a card from an existing check JSON (+ controls)
```

## Official open-data maps

```python
from inkcheck import opendata
keys = opendata.list_predictions("PHerc0139", "20250108000005-w030_2025010818", downsampled=True)
pred, meta = opendata.load_prediction(keys[0])     # meta: model, run, scan, map_pixel_um, ...
```

See the [tutorial](TUTORIAL.md) for a complete walk-through.
