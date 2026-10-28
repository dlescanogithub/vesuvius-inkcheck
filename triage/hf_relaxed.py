"""Second pass for volumes where no 512 px tile is fully valid (irregular segment crops): HF spectral ratio over tiles
>= 90% valid, invalid pixels filled with the tile's valid mean. Also recomputed on Paris 4 and 343P to show the relaxed
estimate agrees with the strict one there. Updates triage/proxies.json (hf_ratio_relaxed, hf_tiles_relaxed)."""
import sys, json, numpy as np
REPO = "prize_oct/publish/vesuvius-inkcheck"
sys.path.insert(0, "tools")
from zread import read_local


def psd_ratio_relaxed(img, um, valid, T=512, minfrac=0.9):
    H, W = img.shape; w = np.outer(np.hanning(T), np.hanning(T)); acc = []
    for y in range(0, H - T + 1, T // 2):
        for x in range(0, W - T + 1, T // 2):
            v = valid[y:y + T, x:x + T]
            if v.mean() < minfrac: continue
            t = img[y:y + T, x:x + T].astype(np.float64); t[~v] = t[v].mean(); t = (t - t.mean()) / (t.std() + 1e-9)
            acc.append(np.abs(np.fft.fftshift(np.fft.fft2(t * w))) ** 2)
    if not acc: return None, 0
    P = np.mean(acc, 0); yy, xx = np.indices(P.shape) - T // 2; r = np.hypot(yy, xx).astype(int)
    rad = np.bincount(r.ravel(), P.ravel()) / np.bincount(r.ravel()); f = np.arange(len(rad)) / (T * um * 1e-3)
    f, p = f[1:T // 2], rad[1:T // 2]
    return float(p[(f >= 10) & (f < 25)].mean() / p[(f >= 2) & (f < 10)].mean()), len(acc)


if __name__ == "__main__":
    p = f"{REPO}/triage/proxies.json"; out = json.load(open(p))
    for name, r in out.items():
        if "hf_ratio_relaxed" in r: continue
        v = read_local(r["zarr"] + "/0"); a, b = r["window"]; c = (a + b) // 2
        hf, nt = psd_ratio_relaxed(v[c], r["um"], v[a:b].min(0) > 0)
        r.update(hf_ratio_relaxed=hf, hf_tiles_relaxed=nt); print(name, r.get("hf_ratio"), hf, nt, flush=True)
        json.dump(out, open(p, "w"), indent=1)
