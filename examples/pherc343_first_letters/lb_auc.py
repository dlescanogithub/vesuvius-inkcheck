"""Secondary check: circular letter-box AUC. Each villa map is resampled to a 9.612 um grid; the AUC of the map
inside E. Nieuwlaar's public letter boxes vs outside is compared with 2000 random circular translations of the box
mask (seed 343), inside the render's papyrus mask (layer 13 > 0) eroded 3 px. Also reports pairwise Pearson r
between the reading-side maps.

    python lb_auc.py --render work/render_L.zarr --maps work/maps \
        --boxes pherc343-first-letters/inputs/concat_w047-w048_R5B2_z9500-11000_letter_boxes.json \
        --out work/results/letterbox_auc.json

Expects <maps>/<model>.tif (forward = blind side) and <maps>/<model>_reverse.tif (reading side) for each --models entry.
"""
import argparse, json, os, numpy as np, tifffile
from scipy import ndimage as ndi
from scipy.stats import rankdata

UM, NAT = 9.612, 8.64


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", required=True, help="render_surface.py output (OME-Zarr folder)")
    ap.add_argument("--maps", required=True, help="folder with <model>.tif and <model>_reverse.tif")
    ap.add_argument("--boxes", required=True, help="Erwin's *_letter_boxes.json (raw frame)")
    ap.add_argument("--models", default="dnative,rv3,rv2")
    ap.add_argument("--rows", default="600:2100"); ap.add_argument("--cols", default="650:5550")
    ap.add_argument("--out", default=None, help="write the JSON here as well")
    a = ap.parse_args()
    import zarr
    R0 = int(a.rows.split(":")[0]); C0 = int(a.cols.split(":")[0]); s = NAT / UM

    def villa(p):
        return ndi.zoom(tifffile.imread(p).astype(np.float32) / 255., s, order=1)

    L = np.asarray(zarr.open(os.path.join(a.render, "0"), mode="r")[13]) > 0
    M = {m: (villa(f"{a.maps}/{m}_reverse.tif"), villa(f"{a.maps}/{m}.tif")) for m in a.models.split(",")}
    valid = ndi.zoom(L.astype(np.float32), s, order=0) > 0
    h = min([valid.shape[0]] + [v.shape[0] for p in M.values() for v in p])
    w = min([valid.shape[1]] + [v.shape[1] for p in M.values() for v in p])
    valid = ndi.binary_erosion(valid[:h, :w], iterations=3); M = {k: (x[:h, :w], y[:h, :w]) for k, (x, y) in M.items()}
    bm = np.zeros((h, w), bool)
    for bx in json.load(open(a.boxes))["letters"]:
        x0, y0, x1, y1 = bx["box"] if isinstance(bx, dict) else bx
        bm[max(0, int((y0 - R0) * s)):int((y1 - R0) * s), max(0, int((x0 - C0) * s)):int((x1 - C0) * s)] = True
    rng = np.random.default_rng(343); shifts = [(int(rng.integers(h)), int(rng.integers(w))) for _ in range(2000)]
    f = 2; vs = valid[::f, ::f]; bs = bm[::f, ::f]

    def auc_null(x):
        x = x[::f, ::f]; r = np.zeros(x.shape); r[vs] = rankdata(x[vs])

        def auc(mask):
            m = mask & vs; n1 = m.sum(); n0 = vs.sum() - n1
            return (r[m].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        a0 = auc(bs); nul = np.array([auc(np.roll(bs, (dy // f, dx // f), (0, 1))) for dy, dx in shifts])
        return round(float(a0), 4), round(float((1 + (nul >= a0).sum()) / (1 + len(nul))), 4), round(float(np.percentile(nul, 95)), 4)

    out = {}
    for k, (rd, nl) in M.items():
        x, p, q = auc_null(rd); out[k] = dict(auc_reading=x, p_shift=p, null95=q, auc_blind=auc_null(nl)[0])
    ks = list(M)
    pr = {f"{x}~{y}": round(float(np.corrcoef(M[x][0][valid], M[y][0][valid])[0, 1]), 3) for i, x in enumerate(ks) for y in ks[i + 1:]}
    res = dict(letterbox_auc=out, pairwise_r_reading=pr); print(json.dumps(res, indent=1))
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True); json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
