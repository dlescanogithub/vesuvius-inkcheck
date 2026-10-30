# Quickstart (5 minutes, CPU)

## Try it in 5 minutes: one command on a real segment

```bash
git clone https://github.com/dlescanogithub/vesuvius-inkcheck && cd vesuvius-inkcheck
python -m venv .venv && . .venv/bin/activate && pip install -e .
inkcheck quick                 # same as: python -m inkcheck.quick
```

What it does: downloads about 1.2 MB (PHerc0343P segment 20250511003658 on its 8.64 µm canvas: the team's canonical
2.2 µm ink map as the "model", the letters the Vesuvius Challenge team traced on an **infrared photograph** of the
fragment as the reference, and the valid-area mask), checks each file's sha256, then runs

* **node A**: does the prediction agree with the known ink better than at 192 random wrong placements, and at letter level?
* **node N**: a built-in negative control, the same prediction moved to the wrong place, which must FAIL.

Measured on 2026-10-28 (ART) on a shared 8-vCPU Linux box, Python 3.13, `--workers 2`, cold cache: **108 s** in total
(download 1 s). Output:

```text
PASS  Team 2.2 um model map vs infrared-traced letters (PHerc0343P)
  node A (known ink?)      PASS: r_bp 0.431 (null mean 0.051, max 0.137), p 0.00518, stroke recall 0.50 vs 0.00 chance, 8 strokes, AUC 0.897
  node N (control fails?)  NO_CONTROL_PASSES: wrong-place control FAIL (r_bp 0.034)

  - Agreement: after removing slow brightness trends, the prediction correlates with the reference at r = 0.43. Moving the
    reference to 192 random wrong places gives r = 0.05 on average (at most 0.14), so the chance of r this high by luck is p = 0.00518.
  - Letters: 8 reference strokes; the prediction covers 50% of them, against 0.0% expected by chance.
  - Verdict PASS: the model sees the known ink at letter level here (significant AND large: r >= 0.20 and >= 50% of strokes, both beating the null).
  - Note: fewer than 10 reference strokes, so the stroke test has little power; PASS is hard to reach.
  - Control: the same prediction moved to the wrong place gives FAIL (r = 0.03), as it must, so the check is not fooled by texture alone.
  ...
```

Exit code 0 = PASS, 1 = WEAK, 2 = FAIL (3 = INVALID: the control passed; 4 = ERROR: bad input or a crash). `out/quick.json`, `out/quick.png` and
`out/quick.summary.json` are written locally.

Other uses:

```bash
inkcheck quick --list                      # built-in examples (343p-ir, 343p-ir-v3)
inkcheck quick 343p-ir-v3                  # Reader V3 on the same segment (trained on it: a pipeline check, not generalisation)
inkcheck quick PRED REF --pred-um 8.64 --ref-um 8.64 --mask MASK   # your own maps: local paths or http(s)/s3:// URLs
inkcheck quick --no-control                # skip the control (about half the time)
```

To test **your own model** on this segment, run it on the official 8.64 µm surface volume
(`s3://vesuvius-challenge-open-data/PHerc0343P/segments/20250511003658-tifxyz/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr`),
save the flat map on that canvas, and pass it as PRED with the reference URL from `inkcheck quick --list`'s example
(see `src/inkcheck/quick.py`, `EXAMPLES`).

Data and licence. No scroll data is in this repo. The example files are downloaded at run time from
[DomRusso2/ir-truth-9um](https://github.com/DomRusso2/ir-truth-9um) at a pinned commit (7e96b96): that repo publishes the
infrared-traced letters registered onto the 8.64 µm canvas; it is a third-party host, not the official server. The data
derive from Vesuvius Challenge data (CC BY-NC 4.0 plus the Challenge's data terms): use them for research, do not commit
or redistribute them. The official open-data bucket carries one ink map per segment and no infrared reference, which is
why the example uses this source. Caveats: 8 reference strokes is a small sample; "PASS" means "agrees with this
reference", not ground truth.

## More: synthetic pair, cards and the full check

Verified on 2026-10-27 (ART) from a fresh `git clone` into /tmp, new Python 3.13.5 venv, 2 threads, at low priority on a
shared 8-vCPU box: `pip install -e .` took 9 s (wheels cached); generating the synthetic pair, the PASS check (exit 0), the
negative check (FAIL, exit 2), regenerating all ten shipped cards (`inkcheck report examples/irp/*.case.json`) and
fetching the Paris 4 reference crop (pixel-identical) took 23 s in total from the clone. Rebuilding the Paris 4 prediction
(`--with-pred`) was verified separately: pixel-identical output, about 530 MB downloaded, a few CPU minutes. With a cold pip
cache the install takes longer (not measured; numpy/scipy wheels are the bulk).

```bash
git clone https://github.com/dlescanogithub/vesuvius-inkcheck && cd vesuvius-inkcheck
python -m venv .venv && . .venv/bin/activate
pip install -e .                      # numpy scipy pillow tifffile imagecodecs; add ".[test]" for pytest and scikit-learn

# 1. A check on a synthetic pair (no scroll data; the repo ships none, see "Data" below)
python examples/make_synthetic_example.py
inkcheck examples/data/synthetic_pred_9.6um.png examples/data/synthetic_ref_19.2um.png \
  --pred-um 9.6 --ref-um 19.2 --ref-origin 128,128 --workers 2 --out out/synthetic
# -> PASS  model sees known ink at 9.6 um: YES (band-pass r=0.67, p=0.00518; 73% of reference strokes recovered vs 5% by chance)
#    exit code 0 = PASS, 1 = WEAK, 2 = FAIL, 4 = ERROR; writes out/synthetic.json and out/synthetic.png
inkcheck examples/data/synthetic_negative_pred_9.6um.png examples/data/synthetic_ref_19.2um.png \
  --pred-um 9.6 --ref-um 19.2 --ref-origin 128,128 --workers 2 --out out/synthetic_neg
# -> FAIL  (band-pass r=0.05, p=0.389): unrelated strokes

# 1b. The real Paris 4 check (held-out segment 20231005123336), fetched from the public Vesuvius Challenge bucket:
#    - reference: a crop of the published new_canon ink map at 19.2 um (~4 MB download, seconds);
#    - prediction: the public dense_native 9 um checkpoint at 9.6 um (--with-pred: ~530 MB and a villa install).
python examples/fetch_paris4_example.py --with-pred      # needs VILLA_PY (and VILLA_SRC), see the script
inkcheck examples/data/paris4_dn_pred_9.6um.png examples/data/paris4_ref_crop_19.2um.png \
  --pred-um 9.6 --ref-um 19.2 --ref-origin 256,256 --workers 2 --out out/paris4
# -> tile bootstrap ... (95% CIs printed locally)
# -> PASS  model sees known ink at 9.6 um: YES (...)   # the Paris 4 scores are not published here (reservation until 2027-06-25)

# 2. An IRP card (nodes A-D) from the shipped case file
inkcheck report examples/irp/paris4.case.json --out out/cards     # out/cards/paris4.{md,png,json}

# 3. With inkbench outputs: ranking and leakage flags, then an IRP case for one segment
inkcheck inkbench $INKBENCH_RESULTS --benchmark p0841
inkcheck inkbench $INKBENCH_RESULTS --benchmark p0841 --segment w00 --sample PHerc0841 \
  --ref REF.png --ref-um 2.4 --pred-um 9.4 --case-out my.case.json && inkcheck report my.case.json --out out/cards
```

- Docker: `docker build -t inkcheck .`, then `docker run --rm -v "$PWD/out:/out" inkcheck <same arguments> --out /out/paris4`. The Dockerfile is written but has not been built here, because there is no docker on the author's machine.
- Notebook: `notebooks/quickstart.ipynb` covers the same steps plus a negative control that must FAIL. Its code was executed end-to-end in a fresh venv.
- Your own model: give `PRED` (your 2D ink map) and `REF` (a published ink map of the same segment), each with its pixel size. Add `--ref-origin y,x` if the prediction is a crop, and `--mask valid.png` for the valid area.

Data: this repository contains no scroll data. Vesuvius Challenge data are CC BY-NC 4.0 with additional terms (no
redistribution without approval; Paris 4 has a publication reservation until 2027-06-25), so the Paris 4 inputs are
fetched by `examples/fetch_paris4_example.py`, which checks that the pixels match the ones behind the shipped Paris 4 verdict.
See "Data and licensing" in the README.
