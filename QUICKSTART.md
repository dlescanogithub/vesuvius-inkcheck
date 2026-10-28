# Quickstart (5 minutes, CPU)

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
#    exit code 0 = PASS, 1 = WEAK, 2 = FAIL; writes out/synthetic.json and out/synthetic.png
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
