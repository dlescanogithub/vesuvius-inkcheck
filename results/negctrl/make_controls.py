"""Deliberate negative controls on the Paris 4 PASS case (dense_native prediction). Each MUST come out FAIL.
  wrongregion : the true prediction scored against the same reference image at a different, ink-bearing place
                of the same segment (>= 30 mm away); same model, same scan, wrong labels.
  tileshuffle : reference cut to the scored window and its 2 mm tiles randomly permuted (labels shuffled,
                ink fraction and stroke shapes preserved).
  phasenoise  : prediction replaced by phase-randomised noise with the same power spectrum and histogram range
                (a map with realistic texture but no relation to the ink).
Run from this directory: python make_controls.py  (writes ctrl_*.png/tif and controls.json)."""
import json, numpy as np, tifffile
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = "/workspace/vesuvius"
pred = tifffile.imread(f"{ROOT}/prize_oct/results/p4_ink9_dn.tif").astype(np.float32)
ref = np.array(Image.open(f"{ROOT}/control/p4_ref_ds8.jpg").convert("L"))
oy, ox = 512, 1536                     # true origin of the prediction on the reference grid (ref px, 19.2 um)
h, w = pred.shape[0] // 2, pred.shape[1] // 2   # footprint on the 19.2 um grid
thr = 128
true_frac = float((ref[oy:oy + h, ox:ox + w] > thr).mean())
# wrong region: candidate windows >= 30 mm (1563 px) from the true one, pick the one closest in ink fraction
best = None
for y in range(0, ref.shape[0] - h, 128):
    for x in range(0, ref.shape[1] - w, 128):
        if np.hypot(y - oy, x - ox) * 19.2e-3 < 30: continue
        win = ref[y:y + h, x:x + w]
        if (win == 0).mean() > 0.2: continue
        f = float((win > thr).mean()); d = abs(f - true_frac)
        if best is None or d < best[0]: best = (d, y, x, f)
_, wy, wx, wf = best
# tile shuffle: 2 mm tiles = 104 ref px
rng = np.random.default_rng(0); T = 104
win = ref[oy:oy + h, ox:ox + w].copy(); nty, ntx = h // T, w // T
tiles = [win[i * T:(i + 1) * T, j * T:(j + 1) * T].copy() for i in range(nty) for j in range(ntx)]
perm = rng.permutation(len(tiles))
sh = win.copy()
for k, p in enumerate(perm):
    i, j = divmod(k, ntx); sh[i * T:(i + 1) * T, j * T:(j + 1) * T] = tiles[p]
Image.fromarray(sh).save("ctrl_tileshuffle_ref.png")
# phase-randomised prediction
F = np.fft.rfft2(pred - pred.mean()); ph = np.exp(1j * rng.uniform(0, 2 * np.pi, F.shape))
nz = np.fft.irfft2(np.abs(F) * ph, s=pred.shape) + pred.mean()
lo, hi = np.percentile(pred, [1, 99]); nz = (nz - np.percentile(nz, 1)) / (np.percentile(nz, 99) - np.percentile(nz, 1) + 1e-9) * (hi - lo) + lo
tifffile.imwrite("ctrl_phasenoise_pred.tif", np.clip(np.rint(nz), 1, 255).astype(np.uint8))
json.dump(dict(true_origin=[oy, ox], true_ink_frac=true_frac, wrongregion_origin=[wy, wx], wrongregion_ink_frac=wf,
               wrongregion_distance_mm=float(np.hypot(wy - oy, wx - ox) * 19.2e-3), tile_ref_px=T, n_tiles=len(tiles),
               tileshuffle_origin=[oy, ox]), open("controls.json", "w"), indent=1)
print(open("controls.json").read())
