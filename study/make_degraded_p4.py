"""Build degraded copies of the Paris-4 9.6 um control volume to isolate the effect of
effective resolution on the same held-out segment (same scan, same ink, same model).
Variants: XY Gaussian blur sigma 1/2/3 px (FWHM ~ 23/45/68 um at 9.6 um/px),
2x bin + nearest upsample (19.2 um sampling), and additive Gaussian noise (SNR stress)."""
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, "tools")
from zread import read_local
from zfetch import write_local_zarr
v = read_local("control/p4_ctrl_9.6um.zarr/0").astype(np.float32)
print("vol", v.shape, v.mean(), v.std())
def save(name, a):
    write_local_zarr(f"prize_oct/study/p4_{name}.zarr", np.clip(np.rint(a), 0, 255).astype(np.uint8)); print("wrote", name)
for s in (1, 2, 3):
    save(f"blur{s}", ndi.gaussian_filter(v, (0, s, s)))
Z, H, W = v.shape
b = v.reshape(Z, H // 2, 2, W // 2, 2).mean((2, 4))
save("bin2", np.repeat(np.repeat(b, 2, 1), 2, 2))
rng = np.random.default_rng(0)
save("noise_sd%d" % round(v.std() * 0.5), v + rng.normal(0, v.std() * 0.5, v.shape))
