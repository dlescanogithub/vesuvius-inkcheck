"""Cut the reference maps / human labels of the new held-out cases to each prediction crop (+ margin).

Writes refs/<case>__<refname>.png (uint8) [+ refs/<case>__<refname>_mask.png] and cases.json with the
inkcheck geometry (pred_um, ref_um, ref_origin). ref_um is the *effective* canvas pixel size,
pred_um * n_pred_canvas / n_ref_canvas (the two canvases come from one mesh; plain-scale pairing leaves a
~7 coarse-px offset, villa#2243, which the +-0.5 mm translation search absorbs and reports as shift_um).
"""
import json, os, sys
import numpy as np, tifffile, zarr
from PIL import Image

D = "/workspace/vesuvius/data_raw/newcases"
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUT}/refs", exist_ok=True)
Image.MAX_IMAGE_PIXELS = None

# case: volume zarr, pred_um, crop origin (pred px), crop shape, full pred canvas (Y, X), layers, refs
CASES = {
    "0841-w00": dict(vol="0841_w00.zarr", um=9.366, canvas=(4220, 4760), layers="5:22",
                     refs={"map": ("0841_w00_map.tif", 1), "human": ("0841_w00_labels", 4)}),
    "0009B-125754": dict(vol="0009B_125754_lab.zarr", um=8.64, canvas=(7040, 5700), layers="7:24",
                         refs={"map": ("0009B_125754_map.tif", 1), "human": ("0009B_125754_labels", 4)}),
    "0172-w082": dict(vol="0172_w082.zarr", um=7.91, canvas=(14320, 11520), layers="8:25",
                      refs={"teamTS": ("0172_w082_map.tif", 1)}),
    "0172-w083": dict(vol="0172_w083.zarr", um=7.91, canvas=(13940, 11620), layers="8:25",
                      refs={"teamTS": ("0172_w083_map.tif", 1)}),
    "0500P2-371": dict(vol="0500P2_371.zarr", um=9.362, canvas=(5120, 1880), layers="5:22",
                       refs={"map": ("0500P2_371_map.tif", 1)}),
    "0500P2-377": dict(vol="0500P2_377.zarr", um=9.362, canvas=(5160, 3340), layers="5:22",
                       refs={"map": ("0500P2_377_map.tif", 1)}),
}
MARGIN_MM = 0.8


def main(only=None):
    meta = {}
    for case, c in CASES.items():
        if only and case not in only:
            continue
        crop = json.load(open(f"{D}/{c['vol']}/crop.json"))
        (y0, x0), (_, H, W) = crop["origin_yx"], crop["shape"]
        meta[case] = dict(volume=f"{D}/{c['vol']}", pred_um=c["um"], crop_origin=[y0, x0], crop_shape=[H, W],
                          layers=c["layers"], source=crop["source"], refs={})
        for rname, (src, level) in c["refs"].items():
            if src.endswith(".tif"):
                full = tifffile.imread(f"{D}/{src}")
                full = full if full.ndim == 2 else full[..., 0]
                masks = None
            else:
                ink, sup, val = (zarr.open_array(f"{D}/{src}/{n}.zarr/{2 if level == 4 else 0}", mode="r")[:] > 0
                                 for n in ("inklabels", "supervision", "validation"))
                full = (ink * 255).astype(np.uint8)
                masks = ink | sup | val                       # labelled region (Reader v2's union rule)
            # effective ref pixel size from the canvas ratio (level-0 fine canvas = level * shape)
            fy = full.shape[0] * (level if level > 1 else 1)
            ref_um0 = c["um"] * c["canvas"][0] / fy        # level-0 fine px size
            ref_um = ref_um0 * level
            sc = c["um"] / ref_um                          # ref px per pred px
            m = int(round(MARGIN_MM * 1000 / ref_um))
            ry0 = max(0, int(np.floor(y0 * sc)) - m); rx0 = max(0, int(np.floor(x0 * sc)) - m)
            ry1 = min(full.shape[0], int(np.ceil((y0 + H) * sc)) + m)
            rx1 = min(full.shape[1], int(np.ceil((x0 + W) * sc)) + m)
            out = f"{OUT}/refs/{case}__{rname}.png"
            Image.fromarray(np.ascontiguousarray(full[ry0:ry1, rx0:rx1])).save(out)
            r = dict(ref=out, ref_um=ref_um, ref_origin=[y0 * sc - ry0, x0 * sc - rx0], src=src, level=level)
            if masks is not None:
                mo = f"{OUT}/refs/{case}__{rname}_mask.png"
                Image.fromarray((masks[ry0:ry1, rx0:rx1] * 255).astype(np.uint8)).save(mo)
                r["ref_mask"] = mo
                r["labelled_frac"] = float(masks[ry0:ry1, rx0:rx1].mean())
            meta[case]["refs"][rname] = r
            print(case, rname, r, flush=True)
    old = json.load(open(f"{OUT}/cases.json")) if os.path.exists(f"{OUT}/cases.json") else {}
    old.update(meta)
    json.dump(old, open(f"{OUT}/cases.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
