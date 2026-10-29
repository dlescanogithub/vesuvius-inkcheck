"""Turn E. Nieuwlaar's published PHerc.343 image (4-model ensemble, d=+1) into a reference map on the render grid
(raw rows 600:2100, cols 650:5550, i.e. render_surface.py's default crop).

Overlay rule from his sidecar JSON: pixel = grey*0.45*(1-o) + (255,235,120)*o, o = 0.9*clip((u-0.35)/0.40, 0, 1).
Grey has R=G=B, so o = (R-B)/135 exactly (up to 8-bit rounding). The image is in the reading frame = raw flipped
left-right and up-down; its data panel sits at x=173, y=182 (5641 x 2455 px) and covers raw rows 105:2560,
cols 380:6021. Cyan row-line pixels (dilated 2 px) are excluded from the valid mask.

Writes to --out: erwin_opacity.png (o*255, 8-bit), valid.png (non-black, non-line pixels), boxes.png (letter boxes).
These are derived from scroll data: keep them local, do not commit them.

    python make_ref.py --erwin-repo pherc343-first-letters --out work/ref
"""
import argparse, json, os, numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

STEM = "concat_w047-w048_R5B2_z9500-11000"
PANEL = (182, 173, 2455, 5641)  # y, x, h, w in the published PNG
RAW_SHAPE, AREA = (2560, 6720), (slice(105, 2560), slice(380, 6021))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--erwin-repo", required=True, help="clone of github.com/Nieuwlaar/pherc343-first-letters @ e8370f1f")
    ap.add_argument("--out", required=True, help="output folder for the reference PNGs")
    ap.add_argument("--rows", default="600:2100", help="raw rows of the render crop (must match render_surface.py)")
    ap.add_argument("--cols", default="650:5550", help="raw cols of the render crop")
    a = ap.parse_args()
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs(a.out, exist_ok=True)
    r0, r1 = map(int, a.rows.split(":")); c0, c1 = map(int, a.cols.split(":"))
    im = np.asarray(Image.open(f"{a.erwin_repo}/outputs/{STEM}.png").convert("RGB")).astype(np.int32)
    y, x, h, w = PANEL; panel = im[y:y + h, x:x + w]
    R, G, B = panel[..., 0], panel[..., 1], panel[..., 2]
    o = np.clip((R - B) / 135.0, 0, 1)
    cyan = binary_dilation((B - R > 3) & (np.abs(G - B) <= 3), iterations=2)  # cyan row lines drawn on the image
    valid = (panel.sum(-1) > 0) & ~cyan
    o_raw = np.full(RAW_SHAPE, np.nan, np.float32); v_raw = np.zeros(RAW_SHAPE, bool)
    o_raw[AREA] = o[::-1, ::-1]; v_raw[AREA] = valid[::-1, ::-1]  # reading frame -> raw frame
    crop = (slice(r0, r1), slice(c0, c1))
    oc, vc = np.nan_to_num(o_raw[crop]), v_raw[crop]
    Image.fromarray((oc * 255).round().astype(np.uint8)).save(f"{a.out}/erwin_opacity.png")
    Image.fromarray((vc * 255).astype(np.uint8)).save(f"{a.out}/valid.png")
    bx = np.zeros_like(vc)
    for L in json.load(open(f"{a.erwin_repo}/inputs/{STEM}_letter_boxes.json"))["letters"]:
        bc0, br0, bc1, br1 = L["box"]  # raw frame (col, row)
        bx[int(br0) - r0:int(np.ceil(br1)) - r0, int(bc0) - c0:int(np.ceil(bc1)) - c0] = True
    Image.fromarray((bx * 255).astype(np.uint8)).save(f"{a.out}/boxes.png")
    print(json.dumps(dict(shape=list(oc.shape), valid_frac=round(float(vc.mean()), 3),
                          ink_frac_o_gt0=round(float((oc[vc] > 0).mean()), 3), box_frac=round(float(bx[vc].mean()), 3),
                          ink_in_boxes=round(float((oc[bx & vc] > 0).mean()), 3),
                          ink_out_boxes=round(float((oc[~bx & vc] > 0).mean()), 3),
                          grey_check_max_abs_RminusG_where_o0=int(np.abs(R - G)[(o == 0) & valid].max()))))


if __name__ == "__main__":
    main()
