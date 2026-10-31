"""Public leaderboard: official open-data ink maps scored with the inkcheck protocol against public ink labels.

CPU only, no model inference: every prediction is an official ink-detection map already published on the
open-data server (`<scroll>/segments/<seg>/ink-detection/downsampled/*-ds8.jpg`), and every reference is the public
`scrollprize/ink_9um` label set on Hugging Face (aligned-scrollprizeorg-21slices: ink labels + supervision mask,
9.596 um, annotation plane 10). A map is scored only if it was made from the same scan volume and canvas as the
labels; both are cropped to the supervision bounding box + CROP_MM before scoring, so the shift nulls stay inside the
labelled region. PHercParis4 cases are excluded on purpose. Outputs are numbers only.

    python leaderboard/build_leaderboard.py fetch      # labels (+ maps) into the inkcheck cache (~ few hundred MB)
    python leaderboard/build_leaderboard.py score      # inkcheck per (segment, model) + wrong-place control
    python leaderboard/build_leaderboard.py write      # leaderboard.csv + summary.json from cards/*.json (LEADERBOARD.md is hand-written)
    python leaderboard/build_leaderboard.py all

Environment: INKCHECK_CACHE (default ~/.cache/inkcheck), LB_WORKERS (default 4), LB_NULLS (default 192).
Data: Vesuvius Challenge scroll data and labels are CC BY-NC 4.0; nothing derived from them is written except numbers.
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from inkcheck import __version__, opendata  # noqa: E402
from inkcheck.quick import cache_dir, wrong_place  # noqa: E402

HF = "https://huggingface.co"
LAB = "ink_9um/labels/aligned-scrollprizeorg-21slices"
LABEL_UM = 9.596
CROP_MM = 1.0                 # margin around the supervision bounding box (see _score_one)
ANALYSIS_UM = 19.192          # common grid for every model (the coarser of the two ds8 maps; 2 x label pixel)
POOL_ABOVE_PX = 60_000_000  # pre-pool labels 2x2 for crops larger than this (memory; see _score_one)
PLANE = 10                    # annotation_center_channel in the label .zattrs

# Fixed case list (ink_9um aligned label set, non-Paris-4). Segment folder = the public segment the labels sit on.
CASES = [
    ("pherc0139-w016", "PHerc0139", "20250108000004-w029_2025010827"),
    ("pherc0139-w017", "PHerc0139", "20250108000005-w030_2025010818"),
    ("pherc0139-w028", "PHerc0139", "20260115000000-w044_2026011522"),
    ("pherc0139-w029", "PHerc0139", "20260126000000-w045_2026012619"),
    ("pherc0139-w035", "PHerc0139", "20260317000000-w035_2026031718"),
    ("pherc0139-w039", "PHerc0139", "20260302000000-w039_2026030210"),
    ("pherc0139-w040", "PHerc0139", "20250831000000-w040_2025083102"),
    ("pherc0139-w041", "PHerc0139", "20260108000000-w041_2026010816"),
    ("pherc0139-w043", "PHerc0139", "20260112000000-w043_2026011217"),
    ("pherc0814-46527", "PHerc0814", "20260226000000-46527_2um_try2"),
    ("pherc1667-w013", "PHerc1667", "20240304141531-w013_20240304141531_flatboi"),
    ("pherc1667-w018", "PHerc1667", "20240304144031-w018_20240304144031_flatboi"),
    ("pherc1667-w023", "PHerc1667", "20240304161941-w023_20240304161941_flatboi"),
    ("pherc1667-w028", "PHerc1667", "20251208130119-w028_20251208130119156_flatboi"),
    ("pherc1667-w029", "PHerc1667", "20251212185248-w029_20251212185248662_flatboi"),
    ("pherc1667-w031", "PHerc1667", "20251223230000-w031_2025122323_flatboi"),
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def _get(url, tries=4, timeout=120):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, {}
            if i == tries - 1:
                raise
        except Exception:
            if i == tries - 1:
                raise
        time.sleep(2 * (i + 1))


def _json(url):
    b, _ = _get(url)
    return json.loads(b)


def list_chunks(case, kind):
    url = f"{HF}/api/buckets/scrollprize/datasets/tree/{LAB}/{case}/{case}_{kind}.zarr/0?recursive=true"
    keys = []
    while url:
        b, h = _get(url)
        keys += [x["path"].rsplit("/", 1)[-1] for x in json.loads(b) if x["type"] == "file"]
        m = re.search(r'<([^>]+)>;\s*rel="next"', h.get("Link", "") or h.get("link", ""))
        url = m.group(1) if m else None
    return [tuple(int(v) for v in k.split(".")) for k in keys if re.fullmatch(r"\d+\.\d+\.\d+", k)]


def read_plane(case, kind, plane=PLANE, workers=16, keep=None):
    import numcodecs
    base = f"{HF}/buckets/scrollprize/datasets/resolve/{LAB}/{case}/{case}_{kind}.zarr"
    za = _json(base + "/0/.zarray")
    _, H, W = za["shape"]
    cz, cy, cx = za["chunks"]
    codec = numcodecs.get_codec(za["compressor"])
    out = np.zeros((H, W), np.uint8)
    keys = list_chunks(case, kind)
    if keep is not None:              # only chunks (y, x) in `keep`; the rest stay 0
        keys = [k for k in keys if (k[1], k[2]) in keep]

    def f(k):
        b, _ = _get(f"{base}/0/{k[0]}.{k[1]}.{k[2]}")
        a = np.frombuffer(codec.decode(b), np.uint8).reshape(cz, cy, cx)
        return k, a
    with cf.ThreadPoolExecutor(workers) as ex:
        for (_, y, x), a in ex.map(f, keys):
            ys, xs = y * cy, x * cx
            blk = a[plane] if a[plane].any() or kind != "supervision_mask" else a.max(0)
            out[ys:ys + cy, xs:xs + cx] = blk[: H - ys, : W - xs]
    return out, za["shape"], len(keys)


def label_path(case):
    return cache_dir() / "leaderboard" / f"{case}.labels.npz"


def fetch_labels(case):
    p = label_path(case)
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    attrs = _json(f"{HF}/buckets/scrollprize/datasets/resolve/{LAB}/{case}/{case}_inklabels.zarr/.zattrs")
    sup, shape, n2 = read_plane(case, "supervision_mask")
    # ink labels are only read in chunks within one chunk of supervised pixels (scoring masks everything else;
    # the reference-set margin of 0.5 mm is smaller than one 128-px chunk = 1.23 mm)
    cy = cx = 128
    has = {(y, x) for y in range(-(-sup.shape[0] // cy)) for x in range(-(-sup.shape[1] // cx))
           if sup[y * cy:(y + 1) * cy, x * cx:(x + 1) * cx].any()}
    keep = {(y + dy, x + dx) for y, x in has for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
    ink, _, n1 = read_plane(case, "inklabels", keep=keep)
    np.savez_compressed(p, ink=ink, sup=sup, attrs=json.dumps(attrs))
    log(f"{case}: labels {shape}, {n1}+{n2} chunks, ink px {int((ink > 0).sum())}, supervised px {int((sup > 0).sum())}")
    return p


def maps_for(scroll, segdir):
    keys = opendata.list_predictions(scroll, segdir, downsampled=True)
    return [k for k in keys if re.search(r"-ds8\.(jpg|png)$", k)]


def model_key(meta):
    return f"{meta['model']} ({meta['pixel_um']:g} um {meta['energy_kev']:g} keV)"


def stage_fetch():
    plan = []
    for case, scroll, segdir in CASES:
        fetch_labels(case)
        for k in maps_for(scroll, segdir):
            a, meta = opendata.load_prediction(k, log=log)
            plan.append(dict(case=case, scroll=scroll, segdir=segdir, key=k, shape=list(a.shape)))
    (HERE / "plan.json").write_text(json.dumps(plan, indent=1))
    log(f"plan: {len(plan)} (segment, map) pairs")


def canvas_mismatch(attrs, meta, pred_shape, label_shape):
    """Return a reason string if the map is not on the label canvas, else None.

    The labels are drawn on the canvas of one surface volume (`source_surface_volume` in the label .zattrs). A map
    rendered from another scan of the same segment lives on a different canvas and there is no published transform
    between the two, so such pairs are excluded rather than force-registered. The map's physical extent must also
    match the label canvas within 2 %.
    """
    m = re.search(r"(\d+(?:\.\d+)?um-[\d.]+m-\d+keV)-volume-(\d{14})", attrs.get("source_surface_volume", ""))
    if not m:
        return "label .zattrs names no surface volume"
    if (meta["scan"], meta["volume"]) != (m.group(1), m.group(2)):
        return f"map from scan {meta['scan']} volume {meta['volume']}; labels are on {m.group(1)} volume {m.group(2)}"
    for a, b in zip(pred_shape, label_shape):
        if abs(a * meta["map_pixel_um"] / (b * LABEL_UM) - 1) > 0.02:
            return f"map extent {pred_shape} x {meta['map_pixel_um']} um differs from label canvas {label_shape} x {LABEL_UM} um"
    return None


def _score_one(item, nulls, workers):
    from inkcheck.card import build_card
    from inkcheck.core import CheckConfig, run_check
    from inkcheck.node_d_v2 import saturation_check
    from inkcheck.report import _to_json
    z = np.load(label_path(item["case"]))
    ink, sup = z["ink"], z["sup"]
    attrs = json.loads(str(z["attrs"]))
    pred, meta = opendata.load_prediction(item["key"])
    why = canvas_mismatch(attrs, meta, pred.shape, ink.shape)
    full_shape = pred.shape
    if why:
        return None, why
    eff_um = meta["map_pixel_um"]
    # Crop both maps to the supervision bounding box + CROP_MM so the toroidal shift nulls wrap within the labelled
    # region. On the full canvas most shifts move the narrow supervised strips off the segment and cannot be scored
    # (only ~4% of 576 nulls were usable on pherc0139-w016), which made every check null-limited.
    f = max(1, int(round(eff_um / LABEL_UM)))                          # label px per map px (2 on the 19.192 um maps)
    sb = sup > 0
    ys, xs = np.flatnonzero(sb.any(1)), np.flatnonzero(sb.any(0))
    del sb
    mpx = int(round(CROP_MM * 1000 / LABEL_UM))
    y0, x0 = max(0, (ys[0] - mpx) // f * f), max(0, (xs[0] - mpx) // f * f)
    y1, x1 = min(sup.shape[0], ys[-1] + 1 + mpx), min(sup.shape[1], xs[-1] + 1 + mpx)
    y1, x1 = y0 + (y1 - y0) // f * f, x0 + (x1 - x0) // f * f
    crop = dict(label_px=[int(y0), int(x0), int(y1), int(x1)], map_px=[int(y0 // f), int(x0 // f), int(y1 // f), int(x1 // f)])
    ink, sup = ink[y0:y1, x0:x1] > 0, sup[y0:y1, x0:x1] > 0      # labels are stored as 0/1
    del z
    pred = pred[y0 // f:y1 // f, x0 // f:x1 // f]
    ref_um, pooled = LABEL_UM, False
    if ink.size > POOL_ABOVE_PX and f == 2 and abs(ANALYSIS_UM - 2 * LABEL_UM) < 1e-9:
        # Large crops (> POOL_ABOVE_PX label px) do not fit in memory at label resolution, so the labels are pooled
        # 2 x 2 onto the analysis grid here. This is exactly what run_check's BOX resample does for this integer factor
        # with origin 0 (mean of the 4 pixels; a pooled pixel is valid only if all 4 are valid), so numbers are unchanged.
        h, w = ink.shape[0] // 2, ink.shape[1] // 2
        ref = ink.reshape(h, 2, w, 2).sum((1, 3), dtype=np.uint8).astype(np.float32) * (255.0 / 4)
        del ink
        sup = sup.reshape(h, 2, w, 2).all((1, 3))
        ref_um, pooled = ANALYSIS_UM, True
    else:
        ref = ink.astype(np.float32) * 255.0       # 0/255 scale; threshold 127
        del ink
    cfg = CheckConfig(pred_um=eff_um, ref_um=ref_um, analysis_um=ANALYSIS_UM, ref_threshold=127.0,
                      n_shift_nulls=nulls, workers=workers)
    q = lambda s: None
    res = run_check(pred, ref, cfg, None, sup, log=q)
    ctrl = run_check(wrong_place(pred), ref, cfg, None, sup, log=q)
    sat = saturation_check(pred, pred > 0)
    check = _to_json({"verdict": res.verdict, "summary": res.summary, "warnings": res.warnings,
                      "numbers": res.numbers, "config": res.config})
    card = build_card(
        check,
        segment=dict(scroll=item["scroll"], segment_id=item["segdir"], label=item["case"]),
        model=dict(name=meta["model"], run=meta["run"], tile=meta["tile"], stride=meta["stride"]),
        scan=dict(volume=meta["volume"], pixel_um=meta["pixel_um"], energy_kev=meta["energy_kev"]),
        prediction=dict(source=opendata.to_url(item["key"]), map_pixel_um=meta["map_pixel_um"], ds=meta["ds"],
                        shape=list(full_shape), crop_px=crop["map_px"]),
        reference=dict(source=f"{HF}/buckets/scrollprize/datasets/tree/main/{LAB}/{item['case']}",
                       kind="public ink labels (scrollprize ink_9um, aligned 21-slice, plane 10; label value > 0 = ink), supervision mask > 0 as validity",
                       pixel_um=LABEL_UM, crop_px=crop["label_px"],
                       crop_note=f"both maps cropped to the supervision bounding box + {CROP_MM} mm; shift nulls wrap within it"
                       + ("; labels pre-pooled 2x2 to the analysis grid (identical to the BOX resample, saves memory)" if pooled else "")),
        controls=[dict(name="wrong_place", kind="wrong_place", expected="FAIL", verdict=ctrl.verdict,
                       r_bandpass=float(ctrl.numbers["r_bandpass"]))],
        saturation=sat,
        extra={"online_validation_case": bool(attrs.get("online_validation"))},
    )
    return card, None


def cached_plan():
    """(segment, map) pairs for every case whose labels are already cached (lets scoring overlap a running fetch)."""
    plan = []
    for case, scroll, segdir in CASES:
        if label_path(case).exists():
            plan += [dict(case=case, scroll=scroll, segdir=segdir, key=k) for k in maps_for(scroll, segdir)]
    return plan


def stage_score(only=None):
    pp = HERE / "plan.json"
    plan = json.loads(pp.read_text()) if pp.exists() else cached_plan()
    nulls = int(os.environ.get("LB_NULLS", "192"))
    workers = int(os.environ.get("LB_WORKERS", "4"))
    od = HERE / "cards"
    od.mkdir(exist_ok=True)
    xp = HERE / "excluded.json"
    excluded = json.loads(xp.read_text()) if xp.exists() else {}
    for it in plan:
        meta = opendata.parse_prediction_name(it["key"])
        name = f"{it['case']}__{meta['model']}"
        p = od / f"{name}.json"
        if (only and only not in name) or p.exists() or name in excluded:
            continue
        t0 = time.time()
        card, why = _score_one(it, nulls, workers)
        if card is None:
            excluded[name] = dict(case=it["case"], scroll=it["scroll"], model=meta["model"], scan=meta["scan"],
                                  volume=meta["volume"], reason=why)
            log(f"{name}: excluded ({why})")
            continue
        p.write_text(json.dumps(card, indent=1))
        log(f"{name}: {card['verdict']['final']} r_bp {card['metrics']['r_bandpass']:.3f} "
            f"recall {card['metrics']['stroke_recall']:.2f} AUC {card['metrics']['auc_raw']:.3f} ({time.time() - t0:.0f} s)")
    xp.write_text(json.dumps(excluded, indent=1, sort_keys=True))


def stage_write():
    from inkcheck.card import validate
    from inkcheck.training_overlap import is_in_sample
    cards = []
    for p in sorted((HERE / "cards").glob("*.json")):
        c = json.loads(p.read_text())
        validate(c)
        cards.append(c)
    rows = []
    for c in cards:
        m, pv = c["metrics"], c["provenance"]
        rows.append(dict(
            segment=c["segment"]["label"], scroll=c["segment"]["scroll"], model=pv["model"]["name"],
            scan_um=pv["scan"]["pixel_um"], scan_kev=pv["scan"]["energy_kev"], map_um=pv["prediction"]["map_pixel_um"],
            verdict=c["verdict"]["final"], node_A=c["verdict"]["node_A"],
            r_bp=m["r_bandpass"], p=m["r_bandpass_p"], null_max=m["r_bandpass_null_max"], auc=m["auc_raw"],
            breakeven_f1=m.get("breakeven_f1"), stroke_recall=m["stroke_recall"], stroke_chance=m.get("stroke_recall_chance"),
            n_strokes=m.get("n_ref_strokes"), control=c["controls"][0]["verdict"], saturated=c["saturation"].get("saturated"),
            overlap_cm2=m.get("overlap_cm2"), n_nulls=m["n_shift_nulls"], n_nulls_requested=m.get("n_shift_nulls_requested"),
            null_limited=1.0 / (1 + m["n_shift_nulls"]) > c["thresholds"]["alpha_r"],
            dihedral_warning=any("transformed by" in w for w in c.get("warnings", [])),
            online_validation_case=c.get("extra", {}).get("online_validation_case"),
            # True = in-sample (training overlap), False = stated held out, empty = unknown (inkcheck.training_overlap)
            in_sample=is_in_sample(pv["model"]["name"], c["segment"]["scroll"], c["segment"]["segment_id"],
                                   c["segment"].get("label"))))
    rows.sort(key=lambda r: (r["scroll"], r["segment"], r["model"]))
    with open(HERE / "leaderboard.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    (HERE / "summary.json").write_text(json.dumps(summarise(rows), indent=1))
    log(f"wrote leaderboard.csv ({len(rows)} rows) and summary.json; LEADERBOARD.md is written by hand from them")


def summarise(rows):
    out = {"inkcheck_version": __version__, "n_rows": len(rows), "models": {}}
    for mdl in sorted({r["model"] for r in rows}):
        rs = [r for r in rows if r["model"] == mdl]
        v = [r["verdict"] for r in rs]
        out["models"][mdl] = dict(
            n=len(rs), PASS=v.count("PASS"), WEAK=v.count("WEAK"), FAIL=v.count("FAIL"), INVALID=v.count("INVALID"),
            median_r_bp=float(np.median([r["r_bp"] for r in rs])), median_auc=float(np.median([r["auc"] for r in rs])),
            median_stroke_recall=float(np.median([r["stroke_recall"] for r in rs])),
            controls_failed_as_expected=sum(r["control"] == "FAIL" for r in rs),
            saturated=sum(bool(r["saturated"]) for r in rs),
            null_limited=sum(bool(r["null_limited"]) for r in rs),
            dihedral_warning=sum(bool(r["dihedral_warning"]) for r in rs),
            median_usable_nulls=float(np.median([r["n_nulls"] for r in rs])),
            median_overlap_cm2=float(np.median([r["overlap_cm2"] for r in rs])),
            by_scroll={s: [r["verdict"] for r in rs if r["scroll"] == s] for s in sorted({r["scroll"] for r in rs})})
    segs = sorted({r["segment"] for r in rows})
    head = {}
    for s in segs:
        rs = sorted([r for r in rows if r["segment"] == s], key=lambda r: -r["r_bp"])
        head[s] = rs[0]["model"] if rs else None
    out["best_r_bp_per_segment"] = {m: sum(1 for v in head.values() if v == m) for m in out["models"]}
    return out


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    if st in ("fetch", "all"):
        stage_fetch()
    if st in ("score", "all"):
        stage_score(sys.argv[2] if len(sys.argv) > 2 and st == "score" else None)
    if st in ("write", "all"):
        stage_write()
