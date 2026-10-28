"""Node D v2: winding-aware candidate rule for unlabelled regions (pre-registered in
results/irp/node_d_v2/PREREG_NODE_D_V2.md; that file fixes every threshold below).

Why v2. Node D v1 compared one model's component density on the reading side against the same model run with the
depth order reversed. On PHerc.343 (Erwin's region, known First Letters) that ratio was ~1.0-1.3 although letters
are there: a reversed render of a thin sheet still reaches ink (the same face from behind, or the facing surface of
the neighbouring winding), so "reversed" is not an ink-free null.

What v2 measures (per region, two checkpoints A and B, both run in both depth directions = two faces):

* I_f   agreement of A and B on face f: IoU of their top-3 % pixels inside the valid mask. Same definition and the
        same face-asymmetry statistic as ScrollPrize/villa PR #2318 (`face_check`, ketchupbyheinz), credited there.
* S1    face asymmetry = max(I_fwd, I_rev) / min(I_fwd, I_rev)                         (PR #2318 compatible)
* S2_f  off-winding contrast = I_f / max(I_f at depth offset +P/2, I_f at -P/2), where P is the winding pitch
        estimated from the CT profile along the normal. A half-pitch shift lands in the gap / the other face of the
        sheet: ink drawn on this face must lose its two-model agreement there, papyrus texture need not.  (new in v2)
* p_f   spatial null: I_f against 192 circular shifts of B relative to A (min shift `min_shift_px`).        (new)

CANDIDATE when the best face has I >= 0.10, p <= 0.01, S2 >= 2, and either S1 >= 2 (one-faced writing) or the other
face passes the same three tests (two-faced: opisthograph or neighbour-winding ink; flagged). Otherwise NOTHING.
A CANDIDATE is a pointer for compute and a human look, never "ink".
"""
from __future__ import annotations

import numpy as np

RULE_V2 = dict(top_q=0.03, min_iou=0.10, alpha=0.01, min_offwinding_ratio=2.0, min_face_asym=2.0,
               n_shift_nulls=192, min_shift_px=150, seed=0)


def top_mask(a: np.ndarray, valid: np.ndarray, q: float = 0.03) -> np.ndarray:
    v = a[valid]
    if v.size == 0:
        return np.zeros_like(valid)
    thr = np.quantile(v, 1.0 - q)
    return (a >= thr) & valid & (a > np.min(v))  # ties at the floor never count as "top"


def top_iou(a, b, valid, q=0.03) -> float:
    ta, tb = top_mask(a, valid, q), top_mask(b, valid, q)
    u = (ta | tb).sum()
    return float((ta & tb).sum() / u) if u else 0.0


def shift_null_p(a, b, valid, q=0.03, n=192, min_shift_px=150, seed=0):
    """One-sided p of top_iou(a, b) against circular shifts of b (and its mask) by >= min_shift_px (toroidal)."""
    H, W = a.shape
    obs = top_iou(a, b, valid, q)
    rng = np.random.default_rng(seed)
    ta = top_mask(a, valid, q)
    tb = top_mask(b, valid, q)
    null = []
    tries = 0
    while len(null) < n and tries < 100 * n:
        tries += 1
        dy, dx = int(rng.integers(0, H)), int(rng.integers(0, W))
        ty, tx = min(dy, H - dy), min(dx, W - dx)
        if (ty * ty + tx * tx) < min_shift_px ** 2:
            continue
        tbs = np.roll(tb, (dy, dx), axis=(0, 1))
        u = (ta | tbs).sum()
        null.append((ta & tbs).sum() / u if u else 0.0)
    null = np.asarray(null)
    p = (1 + int((null >= obs).sum())) / (1 + null.size)
    return obs, p, null


def estimate_winding_pitch(profile: np.ndarray, min_lag: int = 4, max_lag: int | None = None) -> float | None:
    """Winding pitch (in samples) from a CT intensity profile along the surface normal (averaged over the region):
    lag of the highest autocorrelation peak in [min_lag, max_lag], refined by a parabola. None when there is no peak."""
    x = np.asarray(profile, float)
    x = x - x.mean()
    n = x.size
    if n < 2 * min_lag + 2 or not np.any(x):
        return None
    ac = np.correlate(x, x, "full")[n - 1:]
    ac = ac / ac[0]
    max_lag = min(max_lag or n // 2, n - 2)
    best, bi = -np.inf, None
    for k in range(max(min_lag, 1), max_lag + 1):
        if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1] and ac[k] > best:
            best, bi = ac[k], k
    if bi is None or best <= 0:
        return None
    y0, y1, y2 = ac[bi - 1], ac[bi], ac[bi + 1]
    d = y0 - 2 * y1 + y2
    return float(bi + (0.5 * (y0 - y2) / d if d else 0.0))


def off_winding_offsets(pitch: float) -> tuple[float, float]:
    """Depth offsets (same units as pitch) of the two off-winding controls: half a pitch either side."""
    return (pitch / 2.0, -pitch / 2.0)


def face_stats(A, B, A_off, B_off, valid, rule=None) -> dict:
    """A, B: the two checkpoints' maps on one face. A_off/B_off: lists of their maps at the off-winding offsets."""
    r = dict(RULE_V2, **(rule or {}))
    i, p, null = shift_null_p(A, B, valid, r["top_q"], r["n_shift_nulls"], r["min_shift_px"], r["seed"])
    offs = [top_iou(a, b, valid, r["top_q"]) for a, b in zip(A_off, B_off)]
    c = max(offs) if offs else None
    s2 = (i / max(c, 1e-3)) if c is not None else None
    return dict(iou=i, p=p, null_mean=float(null.mean()) if null.size else None,
                null_max=float(null.max()) if null.size else None, iou_offwinding=offs, s2=s2)


def _face_ok(s, r):
    return s["iou"] >= r["min_iou"] and s["p"] <= r["alpha"] and s["s2"] is not None and s["s2"] >= r["min_offwinding_ratio"]


def candidate_rule_v2(fwd: dict, rev: dict, rule=None) -> tuple[str, list[str], dict]:
    """fwd/rev: face_stats of the two faces. Returns (outcome, reasons, numbers); outcome CANDIDATE or NOTHING."""
    r = dict(RULE_V2, **(rule or {}))
    best, other = (fwd, rev) if fwd["iou"] >= rev["iou"] else (rev, fwd)
    bname = "fwd" if best is fwd else "rev"
    s1 = best["iou"] / max(other["iou"], 1e-3)
    nums = dict(best_face=bname, s1_face_asym=s1, iou_best=best["iou"], iou_other=other["iou"], p_best=best["p"],
                s2_best=best["s2"], s2_other=other["s2"])
    why = []
    if best["iou"] < r["min_iou"]:
        why.append(f"two-model agreement IoU {best['iou']:.3f} < {r['min_iou']}")
    if best["p"] > r["alpha"]:
        why.append(f"agreement not above spatial-shift null (p {best['p']:.3g} > {r['alpha']})")
    if best["s2"] is None or best["s2"] < r["min_offwinding_ratio"]:
        why.append(f"off-winding contrast {best['s2'] if best['s2'] is None else round(best['s2'], 2)} < {r['min_offwinding_ratio']}")
    if why:
        return "NOTHING", why, nums
    if s1 >= r["min_face_asym"]:
        return "CANDIDATE", [f"one-faced: face asymmetry {s1:.2f}, off-winding contrast {best['s2']:.2f}"], nums
    if _face_ok(other, r):
        return "CANDIDATE", [f"two-faced (face asymmetry {s1:.2f}; both faces pass the off-winding test): "
                             "opisthograph or neighbour-winding ink, check by eye"], nums
    return "NOTHING", [f"face asymmetry {s1:.2f} < {r['min_face_asym']} and the other face fails the off-winding test "
                       "(texture-like)"], nums


def v1_rule_numbers(comps_reading: float, comps_reversed: float, min_ratio: float = 2.0) -> bool:
    """Node D v1 core test (component density vs reversed-depth null), kept for side-by-side reporting."""
    return (comps_reading / comps_reversed if comps_reversed else float("inf")) >= min_ratio


def face_only_flag(iou_best: float, s1_face_asym: float, valid_px: int, rule=None) -> bool:
    """Face-only statistic (PR #2318 face asymmetry with v2's IoU floor): best-face I >= min_iou and S1 >= min_face_asym,
    on a region with valid pixels. Always returns a plain Python bool (never numpy.bool_), so `is True` / JSON are safe."""
    r = dict(RULE_V2, **(rule or {}))
    return bool(float(iou_best) >= r["min_iou"] and float(s1_face_asym) >= r["min_face_asym"] and int(valid_px) > 0)


def count_flagged(regions: dict, kind: str, key: str = "outcome") -> list[str]:
    """Names of regions of `kind` that are flagged: outcome == "CANDIDATE" for key="outcome", otherwise the truthiness
    of a boolean field (numpy bools, 1.0/0.0 from JSON and Python bools all count correctly)."""
    out = []
    for n, s in regions.items():
        if s["kind"] != kind:
            continue
        v = s[key]
        if (v == "CANDIDATE") if key == "outcome" else bool(v):
            out.append(n)
    return out


# ------------------------------------------------------------------ node D "face-only" (PR #2318 statistic, fixed rule)
# Pre-registered in results/irp/node_d_faceonly/PREREG_NODE_D_FACEONLY.md. Thresholds are those of the v2 prereg's
# descriptive face-only column (fixed before the v2 data were scored); nothing tuned. Statistic credit: ScrollPrize/villa
# PR #2318 (`face_check`, ketchupbyheinz).
RULE_FACE_ONLY = dict(top_q=0.03, min_iou=0.10, min_face_asym=2.0, min_valid_frac=0.80, n_shift_nulls=192,
                      min_shift_px=150, seed=0)


def face_only_rule(iou_fwd: float, iou_rev: float, valid_frac: float = 1.0, p_best: float | None = None,
                   rule=None) -> tuple[str, list[str], dict]:
    """Face-only decision for one region. Returns (outcome, reasons, numbers); outcome FLAG, NOTHING or NOT_EVALUABLE.
    p_best (spatial null) is reported only; it is not part of the decision."""
    r = dict(RULE_FACE_ONLY, **(rule or {}))
    iou_fwd, iou_rev = float(iou_fwd), float(iou_rev)
    best = "fwd" if iou_fwd >= iou_rev else "rev"
    ib, io = (iou_fwd, iou_rev) if best == "fwd" else (iou_rev, iou_fwd)
    s1 = ib / max(io, 1e-3)
    nums = dict(best_face=best, iou_best=ib, iou_other=io, s1_face_asym=s1, valid_frac=float(valid_frac), p_best=p_best)
    if float(valid_frac) < r["min_valid_frac"]:
        return "NOT_EVALUABLE", [f"valid fraction {float(valid_frac):.2f} < {r['min_valid_frac']}"], nums
    why = []
    if ib < r["min_iou"]:
        why.append(f"two-model agreement IoU {ib:.3f} < {r['min_iou']}")
    if s1 < r["min_face_asym"]:
        why.append(f"face asymmetry {s1:.2f} < {r['min_face_asym']} (texture-like or two-faced)")
    if why:
        return "NOTHING", why, nums
    return "FLAG", [f"one-faced agreement: IoU {ib:.3f} on {best}, face asymmetry {s1:.2f}"], nums


def face_only_from_maps(A: dict, B: dict, valid, rule=None) -> tuple[str, list[str], dict]:
    """A, B: {'fwd': map, 'rev': map} of the two checkpoints on one region; valid: boolean mask (region pixels)."""
    r = dict(RULE_FACE_ONLY, **(rule or {}))
    valid = np.asarray(valid, bool)
    ious = {f: top_iou(A[f], B[f], valid, r["top_q"]) for f in ("fwd", "rev")}
    best = "fwd" if ious["fwd"] >= ious["rev"] else "rev"
    _, p, _ = shift_null_p(A[best], B[best], valid, r["top_q"], r["n_shift_nulls"], r["min_shift_px"], r["seed"]) \
        if valid.any() else (0.0, 1.0, None)
    return face_only_rule(ious["fwd"], ious["rev"], float(valid.mean()) if valid.size else 0.0, p, rule)
