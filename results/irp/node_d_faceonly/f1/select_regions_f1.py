"""Face-only node D, set F1 region selection (PREREG_NODE_D_FACEONLY.md sha256 ba553d03..., sections 5 and 7).
Mechanical; uses ONLY the team ink maps, the segment meshes, and (for the blank >= 80 % valid-CT condition of section 5)
the raw CT of the official surface volume on the window. No model output exists or is read at selection time.

Same as node D v2 select_regions.py (Otsu on the team map resampled to the canvas with a box filter; 5 x 5 mm
non-overlapping tiles from (0, 0) with >= 80 % mesh-valid pixels; positives = >= 3 strokes, 2 highest ink fractions
not sharing an edge; blanks = no reference ink inside or within 1 mm, farthest from ink), plus, for blanks only, the
section 5 condition ">= 80 % valid CT on the window": candidates are visited in distance order and the first 2 that meet
it are taken (at most 40 visited per segment). Canvas = official surface-volume level 0 (= mesh grid x 20, checked).
Window = 17 layers centred in the surface volume, start (D - 17) // 2 (this reproduces the node A cards' windows:
0172 8-25 of 33, 0500P2/0841 5-22 of 28, 0009B 7-24 of 31). The team map is resampled in row strips (the 0814 map is
4.5 GB as uint8). Valid CT = non-zero on every window layer.
Usage: python select_regions_f1.py <plan.json> <inputs dir> out.json
"""
import json, sys, urllib.request, urllib.error
import numpy as np, tifffile
from PIL import Image
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
Image.MAX_IMAGE_PIXELS = None
BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
UM = {"7.91um": 7.91, "8.64um": 8.64, "9.362um": 9.362, "9.366um": 9.366}

def resample_map(path, H, W, strip=256):
    tf = tifffile.TiffFile(path); z = tf.pages[0].asarray if False else None
    import zarr
    store = tifffile.imread(path, aszarr=True); a = zarr.open(store, mode="r")
    a = a if hasattr(a, "shape") else a[0]
    Hm, Wm = a.shape[:2]; out = np.zeros((H, W), np.uint8)
    for r0 in range(0, H, strip):
        r1 = min(H, r0 + strip); m0, m1 = int(round(r0 * Hm / H)), int(round(r1 * Hm / H))
        s = np.asarray(a[m0:m1]); s = s if s.ndim == 2 else s[..., 0]
        out[r0:r1] = np.asarray(Image.fromarray(s).resize((W, r1 - r0), Image.BOX))
    return out

def ct_valid_frac(sv_key, D, y0, x0, T, ls):
    """fraction of tile pixels with non-zero CT on all 17 window layers (chunks [D,128,128], uncompressed)."""
    c = 128; acc = np.zeros((T, T), bool)
    for yi in range(y0 // c, (y0 + T - 1) // c + 1):
        for xi in range(x0 // c, (x0 + T - 1) // c + 1):
            try:
                b = np.frombuffer(urllib.request.urlopen(f"{BUCKET}{sv_key}0/0/{yi}/{xi}", timeout=90).read(), np.uint8).reshape(D, c, c)
            except urllib.error.HTTPError as e:
                if e.code in (403, 404): continue
                raise
            v = (b[ls:ls + 17] > 0).all(0)
            ya, xa = max(y0, yi * c), max(x0, xi * c); yb, xb = min(y0 + T, (yi + 1) * c), min(x0 + T, (xi + 1) * c)
            acc[ya - y0:yb - y0, xa - x0:xb - x0] = v[ya - yi * c:yb - yi * c, xa - xi * c:xb - xi * c]
    return float(acc.mean())

def select(seg, inp):
    um = UM[seg["sv"].split("surface-volumes/")[1].split("-")[0]]
    D, H, W = json.load(open(f"{inp}/sv_zarray.json"))["shape"]; ls = (D - 17) // 2
    X = tifffile.imread(f"{inp}/mesh_x.tif"); gv = X > 0; s = 20
    assert (X.shape[0] * s, X.shape[1] * s) == (H, W), (X.shape, H, W)
    valid = np.repeat(np.repeat(gv, s, 0), s, 1)
    R = resample_map(f"{inp}/map.tif", H, W)
    v = R[valid]; thr = float(threshold_otsu(v[:: max(1, v.size // 5_000_000)]))
    ink = (R > thr) & valid; del R
    T = int(round(5000 / um)); mm = 1000 / um; min_comp = 0.02 * mm * mm
    f = 8; Hc, Wc = -(-H // f), -(-W // f)
    pad = np.zeros((Hc * f, Wc * f), bool); pad[:H, :W] = ink
    inkc = pad.reshape(Hc, f, Wc, f).any((1, 3)); del pad
    dist_c = ndi.distance_transform_edt(~inkc) * f / mm if inkc.any() else np.full((Hc, Wc), np.inf)
    tiles = []
    for r in range(H // T):
        for c in range(W // T):
            y0, x0 = r * T, c * T
            vf = valid[y0:y0 + T, x0:x0 + T].mean()
            if vf < 0.8: continue
            t_ink = ink[y0:y0 + T, x0:x0 + T]; lab, n = ndi.label(t_ink)
            areas = np.bincount(lab.ravel())[1:] if n else np.array([])
            strokes = int((areas >= min_comp).sum()); m = int(round(mm)); ey0, ex0 = max(0, y0 - m), max(0, x0 - m)
            near = bool(ink[ey0:y0 + T + m, ex0:x0 + T + m].any())
            d = float(dist_c[y0 // f:(y0 + T) // f, x0 // f:(x0 + T) // f].min())
            tiles.append(dict(row=r, col=c, y0=y0, x0=x0, size=T, valid_frac=round(float(vf), 4),
                              ink_frac=float(t_ink.sum() / max(1, valid[y0:y0 + T, x0:x0 + T].sum())),
                              strokes=strokes, ink_within_1mm=near, dist_to_ink_mm=round(d, 3)))
    adj = lambda a, b: abs(a["row"] - b["row"]) + abs(a["col"] - b["col"]) == 1
    pos = []
    for t in sorted([t for t in tiles if t["strokes"] >= 3], key=lambda t: (-t["ink_frac"], t["row"], t["col"])):
        if len(pos) < 2 and not any(adj(t, p) for p in pos): pos.append(t)
    for t in pos: t["ct_valid_frac"] = round(ct_valid_frac(seg["sv"], D, t["y0"], t["x0"], T, ls), 4)  # reported only
    blank, visited = [], []
    for t in sorted([t for t in tiles if not t["ink_within_1mm"]], key=lambda t: (-t["dist_to_ink_mm"], t["row"], t["col"]))[:40]:
        if len(blank) == 2: break
        t["ct_valid_frac"] = round(ct_valid_frac(seg["sv"], D, t["y0"], t["x0"], T, ls), 4); visited.append([t["row"], t["col"], t["ct_valid_frac"]])
        if t["ct_valid_frac"] >= 0.8: blank.append(t)
    return dict(scroll=seg["scroll"], segment=seg["segment"], sv=seg["sv"], ink_map=seg["ink_map"], mesh=seg["mesh"], um=um,
                canvas=[H, W], depth=D, window=[ls, ls + 17], tile_px=T, otsu=thr, n_tiles=len(tiles),
                n_eligible_pos=sum(t["strokes"] >= 3 for t in tiles), n_eligible_blank=sum(not t["ink_within_1mm"] for t in tiles),
                blank_visited=visited, positive=pos, blank=blank)

if __name__ == "__main__":
    plan, inputs, out = sys.argv[1:4]; res = {}
    for seg in json.load(open(plan)):
        key = seg["scroll"] + "__" + seg["segment"][:14]
        r = res[key] = select(seg, f"{inputs}/{key}")
        print(key, "tiles", r["n_tiles"], "pos", [(t["row"], t["col"], round(t["ink_frac"], 3), t["strokes"], t["ct_valid_frac"]) for t in r["positive"]],
              "blank", [(t["row"], t["col"], t["dist_to_ink_mm"], t["ct_valid_frac"]) for t in r["blank"]], "visited", len(r["blank_visited"]), flush=True)
        json.dump(res, open(out, "w"), indent=1)
