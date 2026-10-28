"""Node D v2 held-out region selection (PREREG_NODE_D_V2.md section 5). Mechanical; uses ONLY the reference maps
and the segment meshes (validity). Run before any v2 render; output regions.json (numbers only, no images).

Grid: the segment's native surface-volume canvas (mesh grid x 20). Reference = team ink map, resampled to the canvas
with a box filter, Otsu threshold on valid pixels. Tiles: non-overlapping 5 x 5 mm from (0, 0), >= 80 % valid.
Positive: >= 3 strokes (connected components of the thresholded reference inside the tile, area >= 0.02 mm^2),
the 2 highest ink fractions not sharing an edge. Blank: no reference ink inside the tile or within 1 mm of it; the 2
with the largest distance to any reference ink (ties: raster order). Distances are computed on a /8 max-pooled grid
(documented approximation; the 1 mm exclusion is checked at full resolution).
Usage: python select_regions.py <data_dir with *_map.tif> <mesh_root> out.json
"""
import json, sys
import numpy as np, tifffile
from PIL import Image
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu

Image.MAX_IMAGE_PIXELS = None
SEGS = {  # key: (map tif, native um)
    "0172-w082": ("0172_w082_map.tif", 7.91), "0172-w083": ("0172_w083_map.tif", 7.91),
    "0500P2-371": ("0500P2_371_map.tif", 9.362), "0500P2-377": ("0500P2_377_map.tif", 9.362),
    "0841-w00": ("0841_w00_map.tif", 9.366), "0009B-125754": ("0009B_125754_map.tif", 8.64)}


def select(key, data, meshes):
    tif, um = SEGS[key]
    X = tifffile.imread(f"{meshes}/{key}/x.tif"); gv = X > 0
    s = 20; H, W = X.shape[0] * s, X.shape[1] * s
    valid = np.repeat(np.repeat(gv, s, 0), s, 1)
    ref = tifffile.imread(f"{data}/{tif}"); ref = ref if ref.ndim == 2 else ref[..., 0]
    R = np.asarray(Image.fromarray(ref).resize((W, H), Image.BOX)); del ref
    v = R[valid]; thr = float(threshold_otsu(v[:: max(1, v.size // 5_000_000)]))
    ink = (R > thr) & valid; del R
    T = int(round(5000 / um)); mm = 1000 / um; min_comp = 0.02 * mm * mm
    f = 8; Hc, Wc = -(-H // f), -(-W // f)
    pad = np.zeros((Hc * f, Wc * f), bool); pad[:H, :W] = ink
    inkc = pad.reshape(Hc, f, Wc, f).any((1, 3)); del pad
    dist_c = ndi.distance_transform_edt(~inkc) * f / mm if inkc.any() else np.full((Hc, Wc), np.inf)  # mm
    tiles = []
    for r in range(H // T):
        for c in range(W // T):
            y0, x0 = r * T, c * T
            vf = valid[y0:y0 + T, x0:x0 + T].mean()
            if vf < 0.8:
                continue
            t_ink = ink[y0:y0 + T, x0:x0 + T]
            lab, n = ndi.label(t_ink)
            areas = np.bincount(lab.ravel())[1:] if n else np.array([])
            strokes = int((areas >= min_comp).sum())
            m = int(round(mm)); ey0, ex0 = max(0, y0 - m), max(0, x0 - m)
            near = bool(ink[ey0:y0 + T + m, ex0:x0 + T + m].any())
            d = float(dist_c[y0 // f:(y0 + T) // f, x0 // f:(x0 + T) // f].min())
            tiles.append(dict(row=r, col=c, y0=y0, x0=x0, size=T, valid_frac=round(float(vf), 4),
                              ink_frac=float(t_ink.sum() / max(1, valid[y0:y0 + T, x0:x0 + T].sum())),
                              strokes=strokes, ink_within_1mm=near, dist_to_ink_mm=round(d, 3)))
    adj = lambda a, b: abs(a["row"] - b["row"]) + abs(a["col"] - b["col"]) == 1
    pos = []
    for t in sorted([t for t in tiles if t["strokes"] >= 3], key=lambda t: (-t["ink_frac"], t["row"], t["col"])):
        if len(pos) < 2 and not any(adj(t, p) for p in pos):
            pos.append(t)
    blank = sorted([t for t in tiles if not t["ink_within_1mm"]], key=lambda t: (-t["dist_to_ink_mm"], t["row"], t["col"]))[:2]
    return dict(um=um, canvas=[H, W], tile_px=T, otsu=thr, n_tiles=len(tiles), ref=tif,
                n_eligible_pos=sum(t["strokes"] >= 3 for t in tiles), n_eligible_blank=sum(not t["ink_within_1mm"] for t in tiles),
                positive=pos, blank=blank)


if __name__ == "__main__":
    data, meshes, out = sys.argv[1:4]
    res = {}
    for k in SEGS:
        res[k] = select(k, data, meshes)
        r = res[k]; print(k, "tiles", r["n_tiles"], "pos", [(t["row"], t["col"], round(t["ink_frac"], 3), t["strokes"]) for t in r["positive"]],
                          "blank", [(t["row"], t["col"], t["dist_to_ink_mm"]) for t in r["blank"]], flush=True)
    json.dump(res, open(out, "w"), indent=1)
