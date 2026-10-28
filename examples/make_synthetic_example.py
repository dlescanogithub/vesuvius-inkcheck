"""Write a synthetic prediction/reference pair so the quickstart needs no scroll data.

The reference is a 19.2 um map of random pen strokes ("letters"). The prediction covers part of it on a
9.6 um grid, starting at reference pixel (128, 128): it is a blurred, noisy copy with 30 % of the strokes
missing (a positive case). The negative prediction is made the same way from unrelated strokes.

    python examples/make_synthetic_example.py            # writes examples/data/synthetic_*.png
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

OUT = Path(__file__).resolve().parent / "data"


def stroke_list(rng, n, H, W):
    out = []
    for _ in range(n):
        y, x, ang, L = rng.uniform(0, H), rng.uniform(0, W), rng.uniform(0, np.pi), rng.uniform(15, 45)
        out.append((y, x, ang, L))
    return out


def render(strokes, shape, scale=1.0, width=2):
    img = np.zeros(shape, bool)
    H, W = shape
    for y, x, ang, L in strokes:
        t = np.linspace(-L / 2, L / 2, int(4 * L * scale)) * scale
        yy = np.clip((y * scale + t * np.sin(ang)).astype(int), 0, H - 1)
        xx = np.clip((x * scale + t * np.cos(ang)).astype(int), 0, W - 1)
        img[yy, xx] = True
    return ndi.binary_dilation(img, iterations=max(1, int(round(width * scale)))).astype(np.float32)


def main(seed=0):
    rng = np.random.default_rng(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    R, oy, ox, P = 640, 128, 128, 768                       # ref size, pred origin (ref px), pred size (9.6 um px)
    strokes = stroke_list(rng, 260, R, R)
    ref = 20 + 220 * ndi.gaussian_filter(render(strokes, (R, R)), 0.8)
    Image.fromarray(ref.clip(0, 255).astype(np.uint8)).save(OUT / "synthetic_ref_19.2um.png")

    def pred_from(strk, rng):
        keep = [s for s in strk if rng.uniform() > 0.3]                     # model misses 30 % of strokes
        local = [(y - oy, x - ox, a, L) for y, x, a, L in keep]
        img = render(local, (P, P), scale=2.0)
        img = ndi.gaussian_filter(img, 3.0) + 0.35 * ndi.gaussian_filter(rng.normal(size=(P, P)), 2.0)
        img = (img - img.min()) / (img.max() - img.min())
        return (40 + 180 * img).astype(np.uint8)

    Image.fromarray(pred_from(strokes, rng)).save(OUT / "synthetic_pred_9.6um.png")
    other = stroke_list(np.random.default_rng(seed + 1), 260, R, R)
    Image.fromarray(pred_from(other, rng)).save(OUT / "synthetic_negative_pred_9.6um.png")
    print(f"wrote {OUT}/synthetic_ref_19.2um.png, synthetic_pred_9.6um.png, synthetic_negative_pred_9.6um.png")


if __name__ == "__main__":
    main()
