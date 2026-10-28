"""Proxy functions shared by proxies_all.py and triage/proxies.py."""
import numpy as np
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
