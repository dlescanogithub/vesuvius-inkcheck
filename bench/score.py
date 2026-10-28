#!/usr/bin/env python
"""One command: score one or more ink checkpoints on one labelled segment.

    python bench/score.py --name pherc0814-46527 --scroll PHerc0814 \
        --volume valset/pherc0814-46527/volume.zarr --ref valset/pherc0814-46527/ink.png \
        --mask valset/pherc0814-46527/heldout.png --um 9.596 \
        --ckpt dn=checkpoints/erwin/dense_native_016000.pth --ckpt s42=.../step-075000.pth \
        --out results/scores

For each checkpoint it runs inference (villa `vesuvius.ink_detection.inference.infer`,
or `hecate.py` when the tag starts with `hecate`) unless the prediction already exists,
then runs inkcheck and appends one row to OUT/scores.jsonl.
Render the table with `python bench/table.py OUT/scores.jsonl`.

The reference may be on a different grid: pass --ref-um and --ref-origin (y,x in reference
pixels of the prediction's (0,0)). Inference is CPU-friendly: --threads (default 2), nice 15.
Environment: VILLA_PY (python with villa installed, default `python`), HECATE_PY, HECATE_SCRIPT.
"""
from __future__ import annotations

import argparse, json, os, subprocess, sys, time
from pathlib import Path

from inkcheck import CheckConfig, run_check
from inkcheck.io import load_map, load_mask
from inkcheck.report import write_json, write_png


def infer(tag, ckpt, volume, out_tif, a):
    env = dict(os.environ, OMP_NUM_THREADS=str(a.threads), MKL_NUM_THREADS=str(a.threads))
    if tag.startswith("hecate"):
        cmd = [os.environ.get("HECATE_PY", sys.executable), os.environ.get("HECATE_SCRIPT", "hecate.py"),
               "--checkpoint", ckpt, "--input", volume, "--spacing-um", "9.6", "--output", str(out_tif.with_suffix(".png")),
               "--device", "cpu"]
    else:
        ls, le = a.layers.split(":")
        cmd = [os.environ.get("VILLA_PY", "python"), "-m", "vesuvius.ink_detection.inference.infer", volume, ckpt, str(out_tif),
               "--layer-start", ls, "--layer-end", le, "--direction", "forward", "--no-compile", "--num-workers", "1"]
    t0 = time.time()
    with open(out_tif.with_suffix(".log"), "w") as log:
        subprocess.run(["nice", "-n", "15", *cmd], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    return time.time() - t0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="segment id, used in file names and the table")
    ap.add_argument("--scroll", default="")
    ap.add_argument("--volume", help="9.6 um-ish ZYX uint8 zarr (needed unless predictions exist)")
    ap.add_argument("--ref", required=True, help="reference ink map (labels or a published read)")
    ap.add_argument("--mask", help="scoring mask on the prediction grid (e.g. held-out pixels)")
    ap.add_argument("--ref-mask", help="labelled region on the reference grid (e.g. human-label supervision area)")
    ap.add_argument("--um", type=float, required=True, help="prediction pixel size (um)")
    ap.add_argument("--ref-um", type=float, help="reference pixel size (default: --um)")
    ap.add_argument("--ref-origin", default="0,0")
    ap.add_argument("--ref-threshold", default="otsu")
    ap.add_argument("--ckpt", action="append", default=[], metavar="TAG=PATH")
    ap.add_argument("--pred", action="append", default=[], metavar="TAG=PATH", help="score an existing prediction")
    ap.add_argument("--pred-scale", default="raw", choices=["raw", "ink9um"])
    ap.add_argument("--layers", default="2:19", help="villa infer z window start:end (17 of 21 by default)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--held-out", default="", help="free text recorded in the row, e.g. 'val-mask pixels'")
    ap.add_argument("--note", action="append", default=[], metavar="TAG=TEXT", help="per-checkpoint caveat")
    ap.add_argument("--nulls", type=int, default=192)
    ap.add_argument("--out", default="results/scores")
    a = ap.parse_args(argv)
    out = Path(a.out); (out / "preds").mkdir(parents=True, exist_ok=True)
    notes = dict(n.split("=", 1) for n in a.note)
    jobs = [(t, p, None) for t, p in (c.split("=", 1) for c in a.ckpt)] + [(t, None, p) for t, p in (c.split("=", 1) for c in a.pred)]
    ref = load_map(a.ref); mask = load_mask(a.mask) if a.mask else None
    ref_mask = load_mask(a.ref_mask) if a.ref_mask else None
    y, x = (float(v) for v in a.ref_origin.split(","))
    for tag, ckpt, pred in jobs:
        secs = None
        if pred is None:
            tif = out / "preds" / f"{a.name}__{tag}.tif"
            pred = tif.with_suffix(".png") if tag.startswith("hecate") else tif
            if not Path(pred).exists():
                secs = infer(tag, ckpt, a.volume, tif, a)
        thr = a.ref_threshold if a.ref_threshold == "otsu" else float(a.ref_threshold)
        cfg = CheckConfig(pred_um=a.um, ref_um=a.ref_um or a.um, ref_origin=(y, x), pred_scale=a.pred_scale,
                          ref_threshold=thr, n_shift_nulls=a.nulls, workers=a.threads)
        res = run_check(load_map(str(pred)), ref, cfg, pred_mask=mask, ref_mask=ref_mask)
        stem = out / f"{a.name}__{tag}"
        write_json(res, str(stem) + ".json"); write_png(res, str(stem) + ".png", title=f"{a.name}: {tag}")
        n = res.numbers
        row = dict(segment=a.name, scroll=a.scroll, checkpoint=tag, ckpt_file=Path(ckpt).name if ckpt else Path(pred).name,
                   verdict=res.verdict, r_bp=n.get("r_bandpass"), auc=n.get("auc_raw"), f1=n.get("breakeven_f1"),
                   stroke_recall=n.get("stroke_recall"), stroke_recall_chance=n["metric_nulls"]["stroke_recall"]["null_mean"],
                   r_bp_z=n.get("r_bandpass_z"), auc_p=n["metric_nulls"]["auc_raw"]["p"], n_strokes=n.get("n_ref_strokes"),
                   area_cm2=n.get("overlap_cm2"), held_out=a.held_out, note=notes.get(tag, ""), infer_s=None if secs is None else round(secs),
                   json=str(stem) + ".json")
        with open(out / "scores.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"{a.name}\t{tag}\t{res.verdict}\t{res.summary}", flush=True)


if __name__ == "__main__":
    main()
