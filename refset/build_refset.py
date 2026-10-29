"""Reference set v0: a deterministic list of public ink / no-ink regions across scrolls.

Source: the public `scrollprize/ink_9um` aligned label set on Hugging Face (ink labels + supervision mask at
9.596 um, annotation plane 10), the same cases as `leaderboard/build_leaderboard.py` (PHercParis4 excluded).
The label arrays are read from the leaderboard cache (run `python leaderboard/build_leaderboard.py fetch` first).

Selection (no randomness; every choice is a pure function of the labels):
  * the label canvas is cut into a fixed grid of TILE_MM x TILE_MM tiles anchored at pixel (0, 0);
  * a tile is eligible if >= MIN_SUP of its pixels are supervised (supervision mask > 0);
  * INK tile: eligible and >= MIN_INK of its supervised pixels are ink (label > 0);
  * NO-INK tile: eligible, zero ink pixels inside the tile AND within MARGIN_MM of it (ink anywhere, supervised or not);
  * per case, at most PER_CASE tiles of each class are kept, ranked by sha256("refset-v0|case|class|ty|tx")
    (a fixed pseudo-random but reproducible order, independent of content).
Each region records its pixel box on the label canvas, its box in micrometres, ink and supervision fractions and a
sha256 of the label bytes inside it, so anyone can verify they are looking at the same labels.

    python refset/build_refset.py          # writes refset/refset_v0.json and refset/coverage_v0.json

Outputs are coordinates and numbers only (no image data). Labels: CC BY-NC 4.0, Vesuvius Challenge data terms.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "leaderboard"))
sys.path.insert(0, str(HERE.parent / "src"))

import build_leaderboard as LB  # noqa: E402

VERSION = "0"
TILE_MM = 0.5
MIN_SUP = 0.90
MIN_INK = 0.15
MARGIN_MM = 0.15
PER_CASE = 8


def rank_key(case, cls, ty, tx):
    return hashlib.sha256(f"refset-v{VERSION}|{case}|{cls}|{ty}|{tx}".encode()).hexdigest()


def select(case, ink, sup):
    um = LB.LABEL_UM
    t = int(round(TILE_MM * 1000 / um))
    mg = int(round(MARGIN_MM * 1000 / um))
    near_ink = ndi.maximum_filter(ink.astype(np.uint8), size=2 * mg + 1) > 0
    H, W = ink.shape
    cand = {"ink": [], "no_ink": []}
    n_elig = 0
    for ty in range(H // t):
        for tx in range(W // t):
            ys, xs = slice(ty * t, (ty + 1) * t), slice(tx * t, (tx + 1) * t)
            s = sup[ys, xs]
            fs = float(s.mean())
            if fs < MIN_SUP:
                continue
            n_elig += 1
            i = ink[ys, xs]
            fi = float(i[s].mean())
            if fi >= MIN_INK:
                cls = "ink"
            elif not near_ink[ys, xs].any():
                cls = "no_ink"
            else:
                continue
            box = [ty * t, tx * t, (ty + 1) * t, (tx + 1) * t]
            h = hashlib.sha256(np.ascontiguousarray(i).tobytes() + np.ascontiguousarray(s).tobytes()).hexdigest()
            cand[cls].append(dict(case=case, cls=cls, tile=[ty, tx], box_px_yxyx=box,
                                  box_um_yxyx=[round(v * um, 1) for v in box], sup_frac=round(fs, 4),
                                  ink_frac=round(fi, 4), label_sha256=h))
    out = []
    for cls, lst in cand.items():
        lst.sort(key=lambda r: rank_key(case, cls, *r["tile"]))
        out += lst[:PER_CASE]
    return out, {k: len(v) for k, v in cand.items()}, n_elig, t


def main():
    regions, cov = [], {}
    for case, scroll, segdir in LB.CASES:
        p = LB.label_path(case)
        if not p.exists():
            print(f"{case}: labels not cached, skipped (run leaderboard fetch)")
            cov[case] = dict(scroll=scroll, cached=False)
            continue
        z = np.load(p)
        ink, sup = z["ink"] > 0, z["sup"] > 0
        attrs = json.loads(str(z["attrs"]))
        sel, ncand, n_elig, t = select(case, ink, sup)
        for r in sel:
            r.update(scroll=scroll, segment=segdir, label_volume=attrs.get("source_surface_volume"))
        regions += sel
        cov[case] = dict(scroll=scroll, segment=segdir, cached=True, canvas_px=list(ink.shape),
                         supervised_cm2=round(float(sup.sum()) * LB.LABEL_UM ** 2 / 1e8, 4),
                         supervised_ink_frac=round(float(ink[sup].mean()) if sup.any() else 0.0, 4),
                         eligible_tiles=n_elig, candidates=ncand,
                         selected={c: sum(r["cls"] == c for r in sel) for c in ("ink", "no_ink")})
        print(f"{case}: eligible {n_elig}, candidates {ncand}, selected {cov[case]['selected']}")
    by_scroll = {}
    for r in regions:
        d = by_scroll.setdefault(r["scroll"], {"ink": 0, "no_ink": 0, "segments": set()})
        d[r["cls"]] += 1
        d["segments"].add(r["segment"])
    tile_cm2 = (int(round(TILE_MM * 1000 / LB.LABEL_UM)) * LB.LABEL_UM) ** 2 / 1e8
    summary = {s: dict(ink=d["ink"], no_ink=d["no_ink"], segments=len(d["segments"]),
                       area_cm2=round((d["ink"] + d["no_ink"]) * tile_cm2, 4)) for s, d in sorted(by_scroll.items())}
    doc = dict(
        name="inkcheck reference set", version=VERSION,
        source=f"{LB.HF}/buckets/scrollprize/datasets/tree/main/{LB.LAB}",
        label_pixel_um=LB.LABEL_UM, annotation_plane=LB.PLANE,
        rule=dict(tile_mm=TILE_MM, tile_px=int(round(TILE_MM * 1000 / LB.LABEL_UM)), min_supervised=MIN_SUP,
                  min_ink=MIN_INK, no_ink_margin_mm=MARGIN_MM, per_case_per_class=PER_CASE,
                  rank="sha256('refset-v0|case|class|ty|tx') ascending",
                  ink="label > 0", supervised="supervision_mask > 0"),
        excluded=["PHercParis4 (all cases)"],
        n_regions=len(regions), by_scroll=summary, regions=regions)
    (HERE / "refset_v0.json").write_text(json.dumps(doc, indent=1))
    (HERE / "coverage_v0.json").write_text(json.dumps(dict(by_scroll=summary, by_case=cov), indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
