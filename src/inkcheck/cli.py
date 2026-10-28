"""Command line interface.

  inkcheck PRED REF --pred-um .. --ref-um .. [options]   one falsification check (node A of the protocol)
  inkcheck report CASE.json [CASE2.json ...] --out DIR    Ink Recoverability Protocol readability card(s)
  inkcheck inkbench RESULTS [--benchmark B] [--case-out CASE.json ...]   read inkbench outputs (ranking table / IRP case)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import CheckConfig, run_check
from .io import load_map, load_mask
from .report import write_json, write_png


def _pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def build_parser():
    ap = argparse.ArgumentParser(
        prog="inkcheck",
        description="Check whether a predicted ink map reproduces a published reference ink map of the same "
                    "segment (possibly at a different resolution). Prints a verdict and writes JSON + PNG.")
    ap.add_argument("pred", help="predicted ink map (tif/png/jpg/npy)")
    ap.add_argument("ref", help="reference ink map (tif/png/jpg/npy)")
    ap.add_argument("--pred-um", type=float, required=True, help="prediction pixel size in micrometres")
    ap.add_argument("--ref-um", type=float, required=True, help="reference pixel size in micrometres")
    ap.add_argument("--ref-origin", type=_pair, default=(0.0, 0.0),
                    help="y,x position (in REFERENCE pixels) of the prediction's pixel (0,0). Default 0,0")
    ap.add_argument("--mask", help="validity mask on the prediction grid (nonzero = valid)")
    ap.add_argument("--ref-mask", help="validity mask on the reference grid")
    ap.add_argument("--analysis-um", type=float, help="common grid pixel size (default: the coarser input)")
    ap.add_argument("--pred-scale", choices=["raw", "ink9um"], default="raw")
    ap.add_argument("--keep-zero", action="store_true", help="do not treat prediction==0 as invalid")
    ap.add_argument("--ref-threshold", default="otsu", help="reference ink threshold in raw units, or 'otsu'")
    ap.add_argument("--bp-fine-um", type=float, default=0.0)
    ap.add_argument("--bp-coarse-um", type=float, default=500.0)
    ap.add_argument("--search-mm", type=float, default=0.5)
    ap.add_argument("--nulls", type=int, default=192, help="number of shift nulls")
    ap.add_argument("--metric-nulls", type=int, default=32)
    ap.add_argument("--min-shift-mm", type=float, default=3.0)
    ap.add_argument("--min-stroke-mm2", type=float, default=0.02)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--min-r", type=float, default=0.20)
    ap.add_argument("--min-stroke-recall", type=float, default=0.50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("OMP_NUM_THREADS", "2")))
    ap.add_argument("--out", default="inkcheck_out", help="output prefix (writes PREFIX.json, PREFIX.png)")
    ap.add_argument("--title", default="")
    return ap


def build_report_parser():
    ap = argparse.ArgumentParser(
        prog="inkcheck report",
        description="Ink Recoverability Protocol: run the per-segment decision tree (A labelled check, B scan tolerance, "
                    "C scan vs scroll, D pre-registered unlabelled rule) on a case file and write a one-page "
                    "readability card (Markdown + PNG + JSON).")
    ap.add_argument("cases", nargs="+", help="case JSON file(s); see examples/irp/*.case.json")
    ap.add_argument("--out", default="cards", help="output directory (one NAME.md/.png/.json per case)")
    return ap


def report_main(argv):
    from .irp import write_card
    a = build_report_parser().parse_args(argv)
    for c in a.cases:
        name = Path(c).name.replace(".case.json", "").replace(".json", "")
        res = write_card(c, str(Path(a.out) / name))
        print(f"{res['name']}\tpath {'>'.join(res['path'])}\t{res['nodes'][-1]['verdict'] if res['nodes'] else '-'}\t{res['headline']}")
        print("wrote " + ", ".join(res["_files"]))
    return 0


def build_inkbench_parser():
    ap = argparse.ArgumentParser(
        prog="inkcheck inkbench",
        description="inkbench ranks models; IRP decides what to do with a segment. Print inkbench's ranking with leakage "
                    "flags, or (with --case-out) write an IRP case whose node-A checks are inkcheck runs on inkbench's maps.")
    ap.add_argument("results", help="inkbench results folder ($INKBENCH_RESULTS)")
    ap.add_argument("--benchmark")
    ap.add_argument("--protocol")
    ap.add_argument("--segment", help="segment tag as in inkbench's per_segment (needed with --case-out)")
    ap.add_argument("--sample", help="open-data sample, e.g. PHerc0841")
    ap.add_argument("--segment-folder", help="prediction folder prefix if it differs from --segment")
    ap.add_argument("--preds", help="inkbench prediction folder (default RESULTS/preds)")
    ap.add_argument("--ref"); ap.add_argument("--ref-um", type=float); ap.add_argument("--pred-um", type=float)
    ap.add_argument("--mask"); ap.add_argument("--ref-origin")
    ap.add_argument("--readers", help="comma-separated subset")
    ap.add_argument("--case-out", help="write an IRP case JSON here (then: inkcheck report CASE --out cards)")
    ap.add_argument("--checks-dir", default="inkbench_checks", help="where the inkcheck JSONs of the case go")
    return ap


def inkbench_main(argv):
    import json as _json
    from . import inkbench as ib
    a = build_inkbench_parser().parse_args(argv)
    rows = ib.read_scores(a.results)
    if not a.case_out:
        for b in sorted({r["benchmark"] for r in rows if a.benchmark in (None, r["benchmark"])}):
            rk = ib.ranking(rows, b, a.protocol)
            print(f"## {b} ({rk[0]['protocol'] if rk else '-'})")
            for i, d in enumerate(rk, 1):
                m = "–" if d["mean"] is None else f"{d['mean']:.3f}"
                print(f"{i}. {d['reader']}\t{m}\t" + ("leak/unknown: " + ", ".join(d["leaked"]) if d["leaked"] else "held out on all segments"))
        return 0
    need = [k for k in ("benchmark", "segment", "sample", "ref", "ref_um", "pred_um") if getattr(a, k) is None]
    if need:
        raise SystemExit("--case-out needs " + ", ".join("--" + k.replace("_", "-") for k in need))
    case = ib.case_from_inkbench(a.results, a.benchmark, a.segment, a.sample, a.ref, a.pred_um, a.ref_um, a.checks_dir,
                                 readers=a.readers.split(",") if a.readers else None, protocol=a.protocol,
                                 segment_folder=a.segment_folder, mask=a.mask, ref_origin=a.ref_origin, preds=a.preds)
    Path(a.case_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.case_out).write_text(_json.dumps(case, indent=1))
    print(f"wrote {a.case_out}: {len(case['checks'])} checks, missing maps: {case['inkbench']['missing_maps'] or 'none'}")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "report":
        return report_main(argv[1:])
    if argv and argv[0] == "inkbench":
        return inkbench_main(argv[1:])
    a = build_parser().parse_args(argv)
    pred = load_map(a.pred)
    ref = load_map(a.ref)
    pm = load_mask(a.mask) if a.mask else None
    rm = load_mask(a.ref_mask) if a.ref_mask else None
    thr = a.ref_threshold if a.ref_threshold == "otsu" else float(a.ref_threshold)
    cfg = CheckConfig(pred_um=a.pred_um, ref_um=a.ref_um, ref_origin=a.ref_origin, analysis_um=a.analysis_um,
                      pred_scale=a.pred_scale, pred_zero_invalid=not a.keep_zero, ref_threshold=thr,
                      bp_fine_um=a.bp_fine_um, bp_coarse_um=a.bp_coarse_um, search_mm=a.search_mm,
                      n_shift_nulls=a.nulls, n_metric_nulls=a.metric_nulls, min_shift_mm=a.min_shift_mm,
                      min_stroke_mm2=a.min_stroke_mm2, alpha_r=a.alpha, min_r_bp=a.min_r,
                      min_stroke_recall=a.min_stroke_recall, seed=a.seed, workers=a.workers)
    res = run_check(pred, ref, cfg, pm, rm, log=lambda s: print(s, flush=True))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(res, str(out) + ".json", {"pred": a.pred, "ref": a.ref, "mask": a.mask,
                                         "pred_shape": list(pred.shape), "ref_shape": list(ref.shape)})
    write_png(res, str(out) + ".png", a.title or f"{Path(a.pred).name} vs {Path(a.ref).name}")
    for w in res.warnings:
        print("[inkcheck] WARNING:", w)
    b = res.numbers.get("bootstrap") or {}
    if b.get("r_ci"):
        print(f"[inkcheck] tile bootstrap ({b['n_tiles']} x {b['tile_mm']} mm tiles, {b['n_boot']} draws, conditional on the "
              f"registration): r_bp 95% CI [{b['r_ci'][0]:.3f}, {b['r_ci'][1]:.3f}]"
              + (f"; stroke recall - chance {b['recall_minus_chance']:+.2f} [{b['recall_minus_chance_ci'][0]:+.2f}, "
                 f"{b['recall_minus_chance_ci'][1]:+.2f}]" if b.get("recall_minus_chance_ci") else ""))
    print(f"{res.verdict}\t{res.summary}")
    print(f"wrote {out}.json and {out}.png")
    return 0 if res.verdict == "PASS" else (1 if res.verdict == "WEAK" else 2)


if __name__ == "__main__":
    sys.exit(main())
