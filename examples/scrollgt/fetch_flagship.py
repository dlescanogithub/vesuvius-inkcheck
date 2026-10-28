"""Fetch a 2048x2048 sub-crop of the ScrollGT held-out flagship region (Paris 4 segment 20231210121321) and
build the ~9.6 um input the ink_9um-family checkpoints expect: XY pyramid level 2 of the public 2.4 um / 78 keV
surface volume, then 4x mean-pooling in z (109 -> 27 layers). Also writes the matching crop of ScrollGT's
registered human label (gt_ink.png, binarised at 127 as ScrollGT does).

    python examples/scrollgt/fetch_flagship.py <scrollgt checkout> <out dir>

ScrollGT's region is level-2 y0=4000, x0=2500, 4096x4096. We score the chunk-aligned 2048x2048 box at level-2
y0=5120, x0=3584 (region-relative y 1120..3168, x 1084..3132) to keep CPU inference bounded. Run from the
workspace root (needs tools/zfetch.py)."""
import sys, os, json, numpy as np
from PIL import Image
sys.path.insert(0, "tools")
from zfetch import read_region, write_local_zarr

KEY = "PHercParis4/segments/20231210121321/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr/2"
RY0, RX0 = 4000, 2500          # ScrollGT region origin (level 2)
Y0, X0, S = 5120, 3584, 2048   # our sub-crop (level 2, chunk aligned)


def main(sgt, out):
    os.makedirs(out, exist_ok=True)
    meta = json.load(open(os.path.join(sgt, "data/scroll1_20231210121321/meta.json")))
    assert meta["region"]["y0"] == RY0 and meta["region"]["x0"] == RX0 and meta["region"]["pyramid_level"] == "2"
    gt = np.asarray(Image.open(os.path.join(sgt, "data/scroll1_20231210121321/gt_ink.png")).convert("L")) > 127
    ry, rx = Y0 - RY0, X0 - RX0
    g = gt[ry:ry + S, rx:rx + S]
    Image.fromarray((g * 255).astype(np.uint8)).save(os.path.join(out, "gt_crop.png"))
    dst = os.path.join(out, "flagship_9.6um.zarr")
    if not os.path.exists(dst + "/0/.zarray"):
        v = read_region(KEY, [0, Y0, X0], [109, Y0 + S, X0 + S], threads=4)
        p = v[:108].reshape(27, 4, S, S).astype(np.float32).mean(1)
        write_local_zarr(dst, np.clip(np.rint(p), 0, 255).astype(np.uint8))
    json.dump(dict(source="s3://vesuvius-challenge-open-data/" + KEY, level2_yx=[Y0, X0], size=S,
                   scrollgt_region_rel_yx=[ry, rx], z_pool=4, layers=27, gt_ink_fraction=float(g.mean()),
                   scrollgt_commit="see README", note="gt_crop.png is ScrollGT's registered human label, cropped"),
              open(os.path.join(out, "crop.json"), "w"), indent=1)
    print("ok", dst, "gt ink fraction", round(float(g.mean()), 4))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
