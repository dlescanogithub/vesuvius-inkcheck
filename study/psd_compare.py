"""Radially averaged power spectra of a mid-depth layer: Paris-4 control (9.6 um, from a 2.4 um scan)
vs PHerc0343P native 8.64 um render, plus P4 blurred copies. Spectra are taken on fully valid 512x512 tiles,
z-scored per tile, Hann-windowed, and plotted against physical frequency (cycles/mm).
'Equivalent blur' = the P4 blur variant whose high-frequency (>=10 cyc/mm) power ratio to the 2-10 cyc/mm band best matches 343P."""
import sys, json, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, "tools"); from zread import read_local
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def psd(img, um, T=512):
    H, W = img.shape; w = np.outer(np.hanning(T), np.hanning(T)); acc = []; 
    for y in range(0, H - T + 1, T // 2):
        for x in range(0, W - T + 1, T // 2):
            t = img[y:y+T, x:x+T].astype(np.float64)
            if (t == 0).mean() > 0.001: continue
            t = (t - t.mean()) / (t.std() + 1e-9)
            acc.append(np.abs(np.fft.fftshift(np.fft.fft2(t * w))) ** 2)
    P = np.mean(acc, 0); yy, xx = np.indices(P.shape) - T // 2; r = np.hypot(yy, xx).astype(int)
    rad = np.bincount(r.ravel(), P.ravel()) / np.bincount(r.ravel()); f = np.arange(len(rad)) / (T * um * 1e-3)
    return f[1:T//2], rad[1:T//2], len(acc)
def band(f, p): lo = p[(f >= 2) & (f < 10)].mean(); return float(p[(f >= 10) & (f < 25)].mean() / lo)
p4 = read_local("control/p4_ctrl_9.6um.zarr/0")[13].astype(np.float32)
q = read_local("renders/343P_20250511003658/0"); q = q[15]
out = {}; plt.figure(figsize=(7, 5))
f, p, n = psd(q, 8.64); out["343P 8.64um native (116 keV)"] = band(f, p); plt.loglog(f, p / p[(f>=2)&(f<10)].mean(), "k", lw=2, label=f"343P native 8.64um (n={n})")
for s in (0, 1, 2, 3):
    img = ndi.gaussian_filter(p4, s) if s else p4
    f, p, n = psd(img, 9.6); k = f"P4 9.6um" + (f" blur s={s}px" if s else " (from 2.4um scan)"); out[k] = band(f, p)
    plt.loglog(f, p / p[(f>=2)&(f<10)].mean(), label=k + f" (n={n})")
plt.xlabel("spatial frequency (cycles/mm)"); plt.ylabel("power (norm. to 2-10 cyc/mm)"); plt.axvspan(10, 25, color="0.9")
plt.title("Mid-layer power spectra: high-frequency ratio (10-25 / 2-10 cyc/mm)"); plt.legend(fontsize=8); plt.tight_layout()
plt.savefig("prize_oct/study/results/psd_compare.png", dpi=110)
json.dump(out, open("prize_oct/study/results/psd_compare.json", "w"), indent=1)
for k, v in out.items(): print(f"{k:40s} HF/LF = {v:.4f}")
