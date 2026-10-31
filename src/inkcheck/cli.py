"""Command line interface.

  inkcheck PRED REF --pred-um .. --ref-um .. [options]   one falsification check (node A of the protocol)
  inkcheck report CASE.json [CASE2.json ...] --out DIR    Ink Recoverability Protocol readability card(s)
  inkcheck report --validate CARD.json [...]              validate ink cards against schemas/inkcheck-report-v1.json
  inkcheck report --render CARD.json [...]                print ink card(s) as Markdown
  inkcheck card CHECK.json [--out PREFIX] [provenance]    turn an existing check JSON into a v1 ink card
  inkcheck inkbench RESULTS [--benchmark B] [--case-out CASE.json ...]   read inkbench outputs (ranking table / IRP case)
  inkcheck quick [EXAMPLE | PRED REF ...]                 5-minute quickstart: fetch, check, control, plain-English verdict

Exit codes (all subcommands): 0 PASS, 1 WEAK, 2 FAIL, 3 INVALID (`inkcheck quick` only: the wrong-place control
passed), 4 ERROR (bad arguments, unreadable input, any uncaught exception). `inkcheck report --validate` exits 1 if
a card is invalid. Python's own default (1 for a traceback, 2 for an argparse usage error) would collide with WEAK
and FAIL, so `main` maps both to 4.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import CheckConfig, run_check
from .io import load_map, load_mask
from .report import write_json, write_png

EXIT_PASS, EXIT_WEAK, EXIT_FAIL, EXIT_INVALID, EXIT_ERROR = 0, 1, 2, 3, 4
EXIT_CODES = {"PASS": EXIT_PASS, "WEAK": EXIT_WEAK, "FAIL": EXIT_FAIL, "INVALID": EXIT_INVALID}


def verdict_exit_code(verdict):
    """Exit code for a verdict string; anything unknown is an error."""
    return EXIT_CODES.get(verdict, EXIT_ERROR)


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
    add_provenance_args(ap)
    ap.add_argument("--no-card", action="store_true", help="do not write PREFIX.card.json / PREFIX.card.md")
    return ap


def add_provenance_args(ap):
    g = ap.add_argument_group("ink card provenance (written to PREFIX.card.json, schema inkcheck-report-v1)")
    g.add_argument("--scroll", help="scroll / sample id, e.g. PHerc0139")
    g.add_argument("--segment", help="segment id or folder")
    g.add_argument("--model", help="model name (default: parsed from an official map file name, if it is one)")
    g.add_argument("--model-run", help="model run / checkpoint id")
    g.add_argument("--scan", help="scan / volume id (default: parsed from an official map file name)")
    g.add_argument("--prereg", help="pre-registration file; its sha256 goes into the card")
    g.add_argument("--prereg-sha256", help="sha256 of the pre-registration (if the file is not at hand)")
    g.add_argument("--training-overlap", metavar="JSON", help="extra known model/segment training pairs (list of "
                   "entries as in inkcheck.training_overlap.BUILTIN); the card flags in-sample pairs, scores unchanged")


def provenance_kwargs(a, pred_src=None, ref_src=None, pred_um=None, ref_um=None):
    """build_card keyword arguments from the provenance options (+ what an official file name tells us)."""
    from .card import sha256_file
    meta = {}
    if pred_src:
        try:
            from .opendata import parse_prediction_name
            meta = parse_prediction_name(str(pred_src))
        except Exception:
            meta = {}
    from .training_overlap import load_registry, lookup
    pre = a.prereg_sha256.lower() if a.prereg_sha256 else (sha256_file(a.prereg) if a.prereg else None)
    scroll, segment, model = a.scroll or meta.get("scroll"), a.segment or meta.get("segment"), a.model or meta.get("model")
    overlap = lookup(model, scroll, segment, registry=load_registry(getattr(a, "training_overlap", None)))
    return dict(
        segment=dict(scroll=scroll, segment_id=segment),
        model=dict(name=model, run=a.model_run or meta.get("run")),
        scan=dict(volume=a.scan or (f"{meta['scan']}-volume-{meta['volume']}" if meta.get("volume") else None), pixel_um=meta.get("pixel_um"), energy_kev=meta.get("energy_kev")),
        prediction=dict(source=str(pred_src) if pred_src else None, map_pixel_um=pred_um),
        reference=dict(source=str(ref_src) if ref_src else None, pixel_um=ref_um),
        prereg_sha256=pre, training_overlap=overlap)


def build_report_parser():
    ap = argparse.ArgumentParser(
        prog="inkcheck report",
        description="Ink Recoverability Protocol: run the per-segment decision tree (A labelled check, B scan tolerance, "
                    "C scan vs scroll, D pre-registered unlabelled rule) on a case file and write a one-page "
                    "readability card (Markdown + PNG + JSON).")
    ap.add_argument("cases", nargs="*", help="case JSON file(s); see examples/irp/*.case.json")
    ap.add_argument("--out", default="cards", help="output directory (one NAME.md/.png/.json per case)")
    ap.add_argument("--validate", nargs="+", metavar="CARD", help="validate ink card JSON(s) against the v1 schema; "
                    "exit 1 if any is invalid")
    ap.add_argument("--render", nargs="+", metavar="CARD", help="print ink card(s) as Markdown")
    ap.add_argument("--builtin-validator", action="store_true", help="ignore jsonschema even if installed")
    return ap


def report_main(argv):
    import json as _json
    from .irp import write_card
    a = build_report_parser().parse_args(argv)
    if a.validate or a.render:
        from .card import render_markdown, validation_errors
        bad = 0
        for f in a.validate or []:
            errs = validation_errors(_json.loads(Path(f).read_text()), False if a.builtin_validator else None)
            bad += bool(errs)
            print(f"{'OK' if not errs else 'INVALID'}\t{f}" + "".join("\n  " + e for e in errs))
        for f in a.render or []:
            print(render_markdown(_json.loads(Path(f).read_text())))
        return 1 if bad else 0
    if not a.cases:
        build_report_parser().error("give case file(s), or --validate / --render card file(s)")
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


def build_card_parser():
    ap = argparse.ArgumentParser(prog="inkcheck card",
                                 description="Turn an inkcheck check JSON (PREFIX.json) into a v1 ink card "
                                             "(PREFIX.card.json + PREFIX.card.md), validated against the schema.")
    ap.add_argument("check", help="check JSON written by `inkcheck PRED REF ...`")
    ap.add_argument("--out", help="output prefix (default: the check JSON path without .json)")
    ap.add_argument("--control", action="append", default=[], metavar="CHECK.json",
                    help="check JSON of a negative control (expected FAIL); repeatable")
    add_provenance_args(ap)
    return ap


def card_main(argv):
    import json as _json
    from .card import build_card, write_card
    a = build_card_parser().parse_args(argv)
    d = _json.loads(Path(a.check).read_text())
    inp = d.get("inputs") or {}
    kw = provenance_kwargs(a, inp.get("pred"), inp.get("ref"), (d.get("config") or {}).get("pred_um"),
                           (d.get("config") or {}).get("ref_um"))
    ctrls = []
    for c in a.control:
        cd = _json.loads(Path(c).read_text())
        ctrls.append(dict(name=Path(c).stem, kind="user", expected="FAIL", verdict=cd["verdict"],
                          r_bandpass=(cd.get("numbers") or {}).get("r_bandpass")))
    card = build_card(d, controls=ctrls, **kw)
    out = a.out or str(Path(a.check)).removesuffix(".json")
    files = write_card(card, out)
    print(f"{card['verdict']['final']}\twrote " + ", ".join(files))
    return 0


def main(argv=None):
    """Entry point of the `inkcheck` command. Returns the exit code (see the module docstring)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return _dispatch(argv)
    except SystemExit as e:
        # argparse --help / --version exit 0; argparse usage errors exit 2 (= FAIL) and SystemExit("message")
        # exits 1 (= WEAK): both are errors here
        if e.code is None or e.code == 0:
            return 0
        if isinstance(e.code, str):
            print(f"inkcheck: error: {e.code}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("inkcheck: interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001 - any crash must not look like a verdict
        import traceback
        traceback.print_exc()
        print(f"inkcheck: error: {type(e).__name__}: {e} (exit {EXIT_ERROR})", file=sys.stderr)
        return EXIT_ERROR


def _dispatch(argv):
    if argv and argv[0] == "card":
        return card_main(argv[1:])
    if argv and argv[0] == "report":
        return report_main(argv[1:])
    if argv and argv[0] == "inkbench":
        return inkbench_main(argv[1:])
    if argv and argv[0] == "quick":
        from .quick import run as quick_main
        return quick_main(argv[1:])
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
    card_files = []
    if not a.no_card:
        import json as _json
        from .card import build_card, saturation_block, write_card
        check = _json.loads(Path(str(out) + ".json").read_text())
        valid = (pred > 0) if pm is None or pm.shape != pred.shape else ((pred > 0) & (pm > 0))
        card = build_card(check, saturation=saturation_block(pred, valid), **provenance_kwargs(a, a.pred, a.ref, a.pred_um, a.ref_um))
        card_files = write_card(card, out)
    for w in res.warnings:
        print("[inkcheck] WARNING:", w)
    b = res.numbers.get("bootstrap") or {}
    if b.get("r_ci"):
        print(f"[inkcheck] tile bootstrap ({b['n_tiles']} x {b['tile_mm']} mm tiles, {b['n_boot']} draws, conditional on the "
              f"registration): r_bp 95% CI [{b['r_ci'][0]:.3f}, {b['r_ci'][1]:.3f}]"
              + (f"; stroke recall - chance {b['recall_minus_chance']:+.2f} [{b['recall_minus_chance_ci'][0]:+.2f}, "
                 f"{b['recall_minus_chance_ci'][1]:+.2f}]" if b.get("recall_minus_chance_ci") else ""))
    print(f"{res.verdict}\t{res.summary}")
    print(f"wrote {out}.json and {out}.png" + (" and " + ", ".join(card_files) if card_files else ""))
    return verdict_exit_code(res.verdict)


if __name__ == "__main__":
    sys.exit(main())
