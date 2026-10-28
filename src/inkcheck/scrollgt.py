"""Adapter for ScrollGT (github.com/jonmarrs/scrollgt, MIT) ink targets.

ScrollGT ships human ink labels for Scroll 1 (PHerc. Paris 4) registered onto the re-flattened 2026 geometry, with
per-target placement gates, and scores models with average precision and AP-prevalence-lift (AP / ink fraction).
ScrollGT measures models; IRP decides what to do with a segment. This module, without importing scrollgt:

  load_target(dir)              -> (gt bool array, valid mask, meta) exactly as scrollgt.score.load_target does
  target_status(meta)           -> whether ScrollGT itself allows scoring the target, its placement and lower-bound note
  ap_prevalence_lift(p, y, m)   -> ScrollGT's headline metric (AP / positive rate), plus AP, positive rate and ROC-AUC
  exposure(meta, train_ids)     -> "held_out" or "train_exposed" for a checkpoint, from the segment id and the
                                   checkpoint's training list (ScrollGT's own "held-out" role is about the models it
                                   knows; it is not a statement about yours)

AP and ROC-AUC use a rank-based implementation so the module needs only numpy; it matches scikit-learn's
average_precision_score / roc_auc_score (tested)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# ink_9um's public label table names Paris 4 segments w00..w09; these are the two ScrollGT segments.
INK9_PARIS4_IDS = {"20230702185753": "phercparis4-w01", "20231210121321": "phercparis4-w06"}


def load_target(target_dir: str | Path):
    from PIL import Image
    d = Path(target_dir)
    meta = json.loads((d / "meta.json").read_text())
    gt = np.asarray(Image.open(d / "gt_ink.png").convert("L")) > 127
    mp = d / "mask.png"
    mask = (np.asarray(Image.open(mp).convert("L")) > 127) if mp.exists() else np.ones_like(gt, bool)
    return gt, mask, meta


def target_status(meta: dict) -> dict:
    reg = meta.get("registration", {}) or {}
    pl = reg.get("placement", {}) or {}
    sc = meta.get("scoring", {}) or {}
    scoreable = sc.get("enabled", True) is not False and pl.get("passed", True) is not False
    return dict(target_id=meta.get("target_id"), segment=meta.get("segment"), scoreable=bool(scoreable),
                scoring_enabled=sc.get("enabled", True), placement_passed=pl.get("passed"),
                placement_mm=pl.get("offset_mm"), median_residual_vx=reg.get("median_residual"),
                role=meta.get("role", ""),
                note=(f"scores are lower bounds; the target resolves to ~{pl['offset_mm']} mm"
                      if pl.get("offset_mm") else "scores are lower bounds (registration residual)"))


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    r = np.empty(len(x), np.float64)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        r[order[i:j + 1]] = 0.5 * (i + j) + 1
        i = j + 1
    return r


def _average_precision(p: np.ndarray, y: np.ndarray) -> float:
    """scikit-learn's step-wise AP: sum over distinct thresholds of (R_k - R_{k-1}) * P_k."""
    order = np.argsort(-p, kind="mergesort")
    ps, ys = p[order], y[order]
    tp = np.cumsum(ys)
    last = np.r_[np.nonzero(np.diff(ps))[0], len(ps) - 1]   # last index of each distinct score
    tp_k = tp[last].astype(np.float64)
    prec = tp_k / (last + 1)
    rec = tp_k / tp[-1]
    return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


def ap_prevalence_lift(prob, label, mask=None, max_pixels: int = 4_000_000, seed: int = 0) -> dict:
    p = np.asarray(prob, np.float64)
    y = np.asarray(label).astype(bool)
    m = np.ones_like(y, bool) if mask is None else np.asarray(mask, bool)
    p, y = p[m], y[m]
    ok = np.isfinite(p)
    p, y = p[ok], y[ok]
    if len(p) > max_pixels:   # deterministic subsample for very large maps
        idx = np.random.default_rng(seed).choice(len(p), max_pixels, replace=False)
        p, y = p[idx], y[idx]
    n, pos = len(y), int(y.sum())
    if pos == 0 or pos == n:
        return dict(n_pixels=n, positive_rate=pos / n if n else float("nan"), average_precision=float("nan"),
                    ap_prevalence_lift=float("nan"), roc_auc=float("nan"))
    ap = _average_precision(p, y.astype(np.int64))
    r = _ranks(p)
    auc = (r[y].sum() - pos * (pos + 1) / 2) / (pos * (n - pos))
    return dict(n_pixels=n, positive_rate=pos / n, average_precision=ap, ap_prevalence_lift=ap / (pos / n),
                roc_auc=float(auc))


def exposure(meta: dict, train_ids) -> str:
    seg = str(meta.get("segment", ""))
    names = {seg, INK9_PARIS4_IDS.get(seg, "\0")}
    tags = {t.lower() for t in train_ids}
    hit = any(n.lower() in tags or any(n.lower() in t for t in tags) for n in names if n and n != "\0")
    return "train_exposed" if hit else "held_out"
