"""Stricter label shuffle (added after the plain 2 mm tile shuffle came out WEAK, see README in this folder):
the same 49 tiles, a derangement (no tile stays in place) AND each tile rotated by 90 or 270 degrees, which breaks
the horizontal text-line layout that a plain shuffle preserves. Writes ctrl_tileshuffle_rot_ref.png."""
import json, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ref = np.array(Image.open("/workspace/vesuvius/control/p4_ref_ds8.jpg").convert("L"))
oy, ox, h, w, T = 512, 1536, 768, 768, 104
win = ref[oy:oy + h, ox:ox + w].copy(); nty, ntx = h // T, w // T
tiles = [win[i * T:(i + 1) * T, j * T:(j + 1) * T].copy() for i in range(nty) for j in range(ntx)]
rng = np.random.default_rng(1)
while True:
    perm = rng.permutation(len(tiles))
    if not np.any(perm == np.arange(len(tiles))): break
out = win.copy()
for k, p in enumerate(perm):
    i, j = divmod(k, ntx); out[i * T:(i + 1) * T, j * T:(j + 1) * T] = np.rot90(tiles[p], k=int(rng.choice([1, 3])))
Image.fromarray(out).save("ctrl_tileshuffle_rot_ref.png")
fp = int(np.sum(np.random.default_rng(0).permutation(len(tiles)) == np.arange(len(tiles))))
c = json.load(open("controls.json")); c.update(tileshuffle_fixed_points=fp, tileshuffle_rot_seed=1); json.dump(c, open("controls.json", "w"), indent=1)
print("fixed points in plain shuffle:", fp)
