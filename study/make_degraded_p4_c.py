"""Third batch for the node-B tolerance curve: coarser sampling (3x, 4x bin + nearest upsample = 28.8 / 38.4 um),
stronger blur (sigma 4 px) and the two ends of the noise axis (0.25x and 2x volume SD). Run from /workspace/vesuvius."""
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, "tools"); from zread import read_local; from zfetch import write_local_zarr
v = read_local("control/p4_ctrl_9.6um.zarr/0").astype(np.float32); sd = v.std(); rng = np.random.default_rng(2)
Z, H, W = v.shape
def save(n, a): write_local_zarr(f"prize_oct/study/p4_{n}.zarr", np.clip(np.rint(a), 0, 255).astype(np.uint8)); print(n, flush=True)
def binup(k):
    h, w = H // k * k, W // k * k
    b = v[:, :h, :w].reshape(Z, h // k, k, w // k, k).mean((2, 4))
    out = v.copy(); out[:, :h, :w] = np.repeat(np.repeat(b, k, 1), k, 2); return out
save("bin3", binup(3)); save("bin4", binup(4))
save("blur4", ndi.gaussian_filter(v, (0, 4, 4)))
save("noise_sd8", v + rng.normal(0, 0.25 * sd, v.shape)); save("noise_sd64", v + rng.normal(0, 2.0 * sd, v.shape))
