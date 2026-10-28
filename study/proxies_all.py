"""Node-B scan-quality proxies on every Paris 4 degradation volume actually fed to the model (not a 2D re-blur):
HF spectral ratio (10-25 / 2-10 cyc/mm, mid layer 13) and adjacent-layer high-pass correlation (layers 7-19),
on the valid area of the undegraded control. Run from the workspace root. Writes prize_oct/study/results/proxies_all.json."""
import sys, json, numpy as np
sys.path.insert(0, "tools"); sys.path.insert(0, "prize_oct/publish/vesuvius-inkcheck/study")
from zread import read_local
from scipy import ndimage as ndi


def psd_ratio(img, um, valid, T=512):
    H, W = img.shape; w = np.outer(np.hanning(T), np.hanning(T)); acc = []
    for y in range(0, H - T + 1, T // 2):
        for x in range(0, W - T + 1, T // 2):
            if not valid[y:y + T, x:x + T].all(): continue
            t = img[y:y + T, x:x + T].astype(np.float64); t = (t - t.mean()) / (t.std() + 1e-9)
            acc.append(np.abs(np.fft.fftshift(np.fft.fft2(t * w))) ** 2)
    P = np.mean(acc, 0); yy, xx = np.indices(P.shape) - T // 2; r = np.hypot(yy, xx).astype(int)
    rad = np.bincount(r.ravel(), P.ravel()) / np.bincount(r.ravel()); f = np.arange(len(rad)) / (T * um * 1e-3)
    f, p = f[1:T // 2], rad[1:T // 2]
    return float(p[(f >= 10) & (f < 25)].mean() / p[(f >= 2) & (f < 10)].mean()), len(acc)


def layer_corr(v, lays, um, valid):
    hp = [v[l].astype(np.float32) - ndi.gaussian_filter(v[l].astype(np.float32), 60 / um) for l in lays]
    m = ndi.binary_erosion(valid, iterations=int(120 / um))
    return float(np.mean([np.corrcoef(hp[i][m], hp[i + 1][m])[0, 1] for i in range(len(hp) - 1)]))


ctrl = read_local("control/p4_ctrl_9.6um.zarr/0"); V0 = ctrl[5:22].min(0) > 0
out = {}
for n in ["original", "blur0.5", "blur1", "blur1.5", "blur2", "blur3", "blur4", "bin2", "bin3", "bin4",
          "noise_sd8", "noise_sd16", "noise_sd32", "noise_sd48", "noise_sd64"]:
    v = ctrl if n == "original" else read_local(f"prize_oct/study/p4_{n}.zarr/0")
    hf, nt = psd_ratio(v[13], 9.6, V0)
    out[n] = dict(hf_ratio=hf, hf_tiles=nt, layer_hp_corr=layer_corr(v, range(7, 20), 9.6, V0))
    print(n, out[n], flush=True)
json.dump(out, open("prize_oct/study/results/proxies_all.json", "w"), indent=1)
