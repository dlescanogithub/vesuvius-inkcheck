"""Second batch: intermediate blur (sigma 1.5 px) and stronger noise (1.0x, 1.5x volume SD), plus blur 0.5px."""
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, "tools"); from zread import read_local; from zfetch import write_local_zarr
v = read_local("control/p4_ctrl_9.6um.zarr/0").astype(np.float32); sd = v.std(); rng = np.random.default_rng(1)
def save(n, a): write_local_zarr(f"prize_oct/study/p4_{n}.zarr", np.clip(np.rint(a), 0, 255).astype(np.uint8)); print(n)
save("blur0.5", ndi.gaussian_filter(v, (0, .5, .5))); save("blur1.5", ndi.gaussian_filter(v, (0, 1.5, 1.5)))
save("noise_sd32", v + rng.normal(0, sd, v.shape)); save("noise_sd48", v + rng.normal(0, 1.5 * sd, v.shape))
