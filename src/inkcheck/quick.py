"""One-command quickstart: ``inkcheck quick [EXAMPLE | PRED REF]``.

Downloads (or reads) a prediction and a reference ink map, runs the node-A falsification check plus a built-in
negative control (node N: the same prediction moved to the wrong place must FAIL), and prints

    PASS / WEAK / FAIL, the numbers behind it, and a plain-English explanation.

No scroll data ships with this package. The built-in examples are fetched at run time from public sources, pinned
to a commit and checked against a sha256; see ``EXAMPLES``. Vesuvius Challenge data are CC BY-NC 4.0 with
additional terms: do not commit or redistribute the downloaded files.

    inkcheck quick                       # default example (PHerc0343P, team map vs infrared-traced letters)
    inkcheck quick --list                # list the examples
    inkcheck quick PRED REF --pred-um 8.64 --ref-um 8.64 [--mask M]   # your own maps (paths or http(s) URLs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

_IR = "https://raw.githubusercontent.com/DomRusso2/ir-truth-9um/7e96b969d3a1407504db4826543136573bda78b8/"
_SEG_VOL = ("s3://vesuvius-challenge-open-data/PHerc0343P/segments/20250511003658-tifxyz/surface-volumes/"
            "8.64um-1.2m-116keV-volume-20250521134555.zarr")
_IR_NOTE = ("PHerc0343P segment 20250511003658, 8.64 um / 116 keV canvas (3440 x 2060 px). Reference = letters traced by "
            "the Vesuvius Challenge team on an infrared photograph of the fragment (carbon ink is black in IR), placed on the "
            "8.64 um scan by D. Russo (github.com/DomRusso2/ir-truth-9um, pinned commit). The reference comes from a camera, "
            "not from a model or the CT. Scan for your own model: " + _SEG_VOL)

EXAMPLES = {
    "343p-ir": dict(
        title="Team 2.2 um model map vs infrared-traced letters (PHerc0343P)",
        pred=(_IR + "maps/team-2.2um-model-map.png", "2f776f1aeaa28f8019f1213a45cd1fb32f065cfc06589c890a458a2f7468fda8"),
        ref=(_IR + "data/ink_traced_full.png", "fa16f7bfe33b6353c37c5c137bd1969ba5270a9be5bd8b2ae1b75095f376708b"),
        mask=(_IR + "data/valid.png", "2ad405459d0d2a5c2da22bd5c9ba15aef0a0851a0a38c715dee621b32b81e1fa"),
        pred_um=8.64, ref_um=8.64, expect="PASS", download_mb=1.2,
        note=_IR_NOTE + " Prediction = the team's canonical 2.2 um model map of the same segment, resampled onto that canvas."),
    "343p-ir-v3": dict(
        title="Reader V3 (9 um) vs infrared-traced letters (PHerc0343P)",
        pred=(_IR + "maps/reader-v3.png", "d2abe2dc8b0b9d9f646d8e650a21edce02d10bac386b31601dcef34c70c31b52"),
        ref=(_IR + "data/ink_traced_full.png", "fa16f7bfe33b6353c37c5c137bd1969ba5270a9be5bd8b2ae1b75095f376708b"),
        mask=(_IR + "data/valid.png", "2ad405459d0d2a5c2da22bd5c9ba15aef0a0851a0a38c715dee621b32b81e1fa"),
        pred_um=8.64, ref_um=8.64, expect="PASS", download_mb=2.3,
        note=_IR_NOTE + " Prediction = Reader V3 on the 8.64 um scan. Caveat: Reader V3 was trained on this segment "
                        "(with the team's 2.2 um map as labels), so this run checks the pipeline, not generalisation."),
}
DEFAULT_EXAMPLE = "343p-ir"


def cache_dir() -> Path:
    return Path(os.environ.get("INKCHECK_CACHE") or Path.home() / ".cache" / "inkcheck")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(src: str, sha: str | None = None, cache: Path | None = None, log=print) -> Path:
    """Local path -> itself. http(s) URL -> cached download (verified against sha256 when given)."""
    if not src.startswith(("http://", "https://", "s3://")):
        p = Path(src)
        if not p.exists():
            raise FileNotFoundError(src)
        return p
    if src.startswith("s3://"):
        b, _, k = src[5:].partition("/")
        src = f"https://{b}.s3.amazonaws.com/{k}"
    cache = Path(cache or cache_dir())
    u = urllib.parse.urlparse(src)
    dst = cache / hashlib.sha256(src.encode()).hexdigest()[:16] / Path(u.path).name
    if dst.exists() and (sha is None or sha256_file(dst) == sha):
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    log(f"[quick] downloading {src}")
    for i in range(4):
        try:
            with urllib.request.urlopen(src, timeout=120) as r, open(str(dst) + ".part", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            break
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))
    os.replace(str(dst) + ".part", dst)
    if sha is not None and sha256_file(dst) != sha:
        dst.unlink()
        raise RuntimeError(f"{src}: sha256 mismatch (file changed upstream?)")
    return dst


def wrong_place(pred: np.ndarray) -> np.ndarray:
    """Negative control: the same prediction moved by half the canvas in both axes (circularly). Same pixels,
    same texture, wrong place: it must FAIL."""
    h, w = pred.shape
    return np.roll(pred, (h // 2, w // 2), axis=(0, 1))


def explain(res, control=None) -> list[str]:
    """Plain-English lines for a CheckResult (and optional control result)."""
    n = res.numbers
    mn = n.get("metric_nulls", {}).get("stroke_recall", {})
    chance = mn.get("null_mean")
    lines = []
    r, p, nm, nx = n.get("r_bandpass"), n.get("r_bandpass_p"), n.get("r_bandpass_null_mean"), n.get("r_bandpass_null_max")
    lines.append(f"Agreement: after removing slow brightness trends, the prediction correlates with the reference at r = {r:.2f}. "
                 f"Moving the reference to {n.get('n_shift_nulls')} random wrong places gives r = {nm:.2f} on average "
                 f"(at most {nx:.2f}), so the chance of r this high by luck is p = {p:.3g}.")
    if n.get("n_ref_strokes"):
        lines.append(f"Letters: {n.get('n_ref_strokes')} reference strokes; the prediction covers "
                     f"{n.get('stroke_recall', 0):.0%} of them, against {chance:.1%} expected by chance." if chance is not None else
                     f"Letters: {n.get('n_ref_strokes')} reference strokes; recall {n.get('stroke_recall', 0):.0%}.")
    if res.verdict == "PASS":
        lines.append("Verdict PASS: the model sees the known ink at letter level here (significant AND large: r >= 0.20 and "
                     ">= 50% of strokes, both beating the null).")
    elif res.verdict == "WEAK":
        lines.append("Verdict WEAK: the agreement is real (beats the null) but too small to call letters; read it as "
                     "'some ink signal, not readable text'.")
    else:
        lines.append("Verdict FAIL: the prediction does not agree with the reference better than at random wrong places. "
                     "Check placement, orientation and layer order first (a reversed layer order can score at chance).")
    if (n.get("n_ref_strokes") or 0) < 10:
        lines.append("Note: fewer than 10 reference strokes, so the stroke test has little power; PASS is hard to reach.")
    if control is not None:
        ok = control.verdict == "FAIL"
        lines.append(f"Control: the same prediction moved to the wrong place gives {control.verdict} "
                     f"(r = {control.numbers.get('r_bandpass', float('nan')):.2f}), "
                     + ("as it must, so the check is not fooled by texture alone." if ok else
                        "which it should not: do not trust this verdict." if control.verdict == "PASS" else
                        "not FAIL: treat a WEAK main verdict with caution."))
    lines.append("PASS means 'agrees with this reference', not ground truth; the reference here is only as good as its source.")
    return lines


def build_parser():
    ap = argparse.ArgumentParser(prog="inkcheck quick", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="EXAMPLE name (default %s), or PRED REF (paths or URLs)" % DEFAULT_EXAMPLE)
    ap.add_argument("--list", action="store_true", help="list the built-in examples and exit")
    ap.add_argument("--pred-um", type=float); ap.add_argument("--ref-um", type=float)
    ap.add_argument("--mask", help="validity mask on the prediction grid (path or URL)")
    ap.add_argument("--ref-origin", default=None, help="y,x of the prediction's (0,0) in reference pixels")
    ap.add_argument("--no-control", action="store_true", help="skip the wrong-place negative control (halves the runtime)")
    ap.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 2))
    ap.add_argument("--nulls", type=int, default=192, help="shift nulls (>= 192 so p can reach 0.01; default 192)")
    ap.add_argument("--cache", help="download cache (default $INKCHECK_CACHE or ~/.cache/inkcheck)")
    ap.add_argument("--out", default="out/quick", help="output prefix: PREFIX.json, PREFIX.png (local only; do not commit)")
    ap.add_argument("--json", action="store_true", help="also print the summary as JSON")
    return ap


def resolve_inputs(a, log=print):
    if len(a.inputs) >= 2:
        if a.pred_um is None or a.ref_um is None:
            raise SystemExit("inkcheck quick PRED REF needs --pred-um and --ref-um")
        spec = dict(title=f"{Path(a.inputs[0]).name} vs {Path(a.inputs[1]).name}", pred=(a.inputs[0], None),
                    ref=(a.inputs[1], None), mask=(a.mask, None) if a.mask else None, pred_um=a.pred_um, ref_um=a.ref_um,
                    expect=None, note="your own maps", name="custom")
    else:
        name = a.inputs[0] if a.inputs else DEFAULT_EXAMPLE
        if name not in EXAMPLES:
            raise SystemExit(f"unknown example {name!r}; choose from: {', '.join(EXAMPLES)} (or give PRED REF)")
        spec = dict(EXAMPLES[name], name=name)
        if a.pred_um: spec["pred_um"] = a.pred_um
        if a.ref_um: spec["ref_um"] = a.ref_um
    paths = {k: (fetch(spec[k][0], spec[k][1], a.cache, log) if spec.get(k) else None) for k in ("pred", "ref", "mask")}
    return spec, paths


def run(argv=None, log=print) -> int:
    from .core import CheckConfig, run_check
    from .io import load_map, load_mask
    from .report import write_json, write_png
    a = build_parser().parse_args(argv)
    if a.list:
        for k, v in EXAMPLES.items():
            print(f"{k}{' (default)' if k == DEFAULT_EXAMPLE else ''}\t{v['title']}\texpect {v['expect']}\t~{v['download_mb']} MB")
        return 0
    t0 = time.time()
    spec, paths = resolve_inputs(a, log)
    t_dl = time.time() - t0
    pred, ref = load_map(paths["pred"]), load_map(paths["ref"])
    mask = load_mask(paths["mask"]) if paths["mask"] else None
    origin = tuple(float(v) for v in a.ref_origin.split(",")) if a.ref_origin else (0.0, 0.0)
    cfg = CheckConfig(pred_um=spec["pred_um"], ref_um=spec["ref_um"], ref_origin=origin, n_shift_nulls=a.nulls, workers=a.workers)
    quiet = lambda s: None
    log(f"[quick] {spec['title']}: running the check ({a.nulls} shift nulls, {a.workers} workers)...")
    res = run_check(pred, ref, cfg, mask, None, log=quiet)
    ctrl = None
    if not a.no_control:
        log("[quick] running the negative control (same prediction, wrong place)...")
        ctrl = run_check(wrong_place(pred), ref, cfg, wrong_place(mask) if mask is not None else None, None, log=quiet)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(res, str(out) + ".json", {"pred": str(spec["pred"][0]), "ref": str(spec["ref"][0]), "example": spec["name"]})
    write_png(res, str(out) + ".png", spec["title"])
    n = res.numbers
    chance = n.get("metric_nulls", {}).get("stroke_recall", {}).get("null_mean")
    node_n = None if ctrl is None else ("NO_CONTROL_PASSES" if ctrl.verdict != "PASS" else "CONTROL_PASSED")
    final = res.verdict if node_n != "CONTROL_PASSED" else "INVALID"
    summary = dict(example=spec["name"], verdict=final, node_A=res.verdict, node_N=node_n,
                   control_verdict=None if ctrl is None else ctrl.verdict,
                   r_bp=n.get("r_bandpass"), p=n.get("r_bandpass_p"), null_mean=n.get("r_bandpass_null_mean"),
                   null_max=n.get("r_bandpass_null_max"), stroke_recall=n.get("stroke_recall"), stroke_chance=chance,
                   n_strokes=n.get("n_ref_strokes"), auc=n.get("auc_raw"), overlap_cm2=n.get("overlap_cm2"),
                   expect=spec.get("expect"), seconds_total=round(time.time() - t0, 1), seconds_download=round(t_dl, 1))
    (Path(str(out) + ".summary.json")).write_text(json.dumps(summary, indent=1))
    from .card import build_card, saturation_block, write_card
    meta = {}
    try:
        from .opendata import parse_prediction_name
        meta = parse_prediction_name(str(spec["pred"][0]))
    except Exception:
        pass
    controls = [] if ctrl is None else [dict(name="wrong_place", kind="wrong_place", expected="FAIL", verdict=ctrl.verdict,
                                             r_bandpass=ctrl.numbers.get("r_bandpass"))]
    valid = (pred > 0) if mask is None or mask.shape != pred.shape else ((pred > 0) & (mask > 0))
    card = build_card(json.loads(Path(str(out) + ".json").read_text()), controls=controls,
                      saturation=saturation_block(pred, valid),
                      segment=dict(scroll=meta.get("scroll"), segment_id=meta.get("segment"), label=spec["name"]),
                      model=dict(name=meta.get("model"), run=meta.get("run")),
                      scan=dict(volume=(f"{meta['scan']}-volume-{meta['volume']}" if meta.get("volume") else None), pixel_um=meta.get("pixel_um"), energy_kev=meta.get("energy_kev")),
                      prediction=dict(source=str(spec["pred"][0]), map_pixel_um=spec["pred_um"]),
                      reference=dict(source=str(spec["ref"][0]), pixel_um=spec["ref_um"]),
                      extra={"example": spec["name"], "expect": spec.get("expect")})
    card_files = write_card(card, out)
    print("")
    print(f"{final}  {spec['title']}")
    print(f"  node A (known ink?)      {res.verdict}: r_bp {n['r_bandpass']:.3f} (null mean {n['r_bandpass_null_mean']:.3f}, "
          f"max {n['r_bandpass_null_max']:.3f}), p {n['r_bandpass_p']:.3g}, stroke recall {n['stroke_recall']:.2f}"
          + (f" vs {chance:.2f} chance" if chance is not None else "") + f", {n['n_ref_strokes']} strokes, AUC {n['auc_raw']:.3f}")
    if ctrl is not None:
        print(f"  node N (control fails?)  {node_n}: wrong-place control {ctrl.verdict} (r_bp {ctrl.numbers['r_bandpass']:.3f})")
    print("")
    for line in explain(res, ctrl):
        print("  - " + line)
    if spec.get("expect"):
        print(f"  - Expected for this example: {spec['expect']} -> {'reproduced' if res.verdict == spec['expect'] else 'NOT reproduced'}.")
    print(f"  - Data: {spec['note']}")
    print(f"\nwrote {out}.json, {out}.png, {out}.summary.json, {', '.join(Path(f).name for f in card_files)}  ({summary['seconds_total']:.0f} s total, "
          f"{summary['seconds_download']:.0f} s download)")
    if a.json:
        print(json.dumps(summary, indent=1))
    from .cli import verdict_exit_code
    return verdict_exit_code(final)


main = run

if __name__ == "__main__":
    from .cli import main as _cli_main
    sys.exit(_cli_main(["quick", *sys.argv[1:]]))
