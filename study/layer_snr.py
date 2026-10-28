"""SNR / texture proxy per volume: Pearson correlation between adjacent depth layers after removing
low frequencies (subtract Gaussian sigma=60 um).  Independent voxel noise lowers it; shared structure
(fibres, ink, cracks) raises it.  Also reports the HF/LF spectral ratio of a mid layer."""
import sys, json, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, "tools"); from zread import read_local
def proxy(v, lays, um, valid):
    hp = [ndi.gaussian_filter(v[l].astype(np.float32), 0) - ndi.gaussian_filter(v[l].astype(np.float32), 60 / um) for l in lays]
    m = ndi.binary_erosion(valid, iterations=int(120 / um))
    return float(np.mean([np.corrcoef(hp[i][m], hp[i + 1][m])[0, 1] for i in range(len(hp) - 1)]))
out = {}
q = read_local("renders/343P_20250511003658/0"); out["343P native 8.64um (layers 9-21)"] = proxy(q, range(9, 22), 8.64, q[7:24].min(0) > 0)
V0 = read_local("control/p4_ctrl_9.6um.zarr/0")[5:22].min(0) > 0
for n in ["ctrl_9.6um", "blur0.5", "blur1", "blur1.5", "blur2", "blur3", "bin2", "noise_sd16", "noise_sd32", "noise_sd48"]:
    p = "control/p4_ctrl_9.6um.zarr/0" if n == "ctrl_9.6um" else f"prize_oct/study/p4_{n}.zarr/0"
    v = read_local(p); out["P4 " + n] = proxy(v, range(7, 20), 9.6, V0)
for k, x in out.items(): print(f"{k:36s} adjacent-layer HP corr = {x:.3f}")
json.dump(out, open("prize_oct/study/results/layer_snr.json", "w"), indent=1)
