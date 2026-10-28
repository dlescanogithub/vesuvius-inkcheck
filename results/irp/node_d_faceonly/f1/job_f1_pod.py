"""job_f1.py (pod) — face-only node D, set F1 inference (prereg 22feecb, selection commit 2df749f).
For every committed region: fetch the official surface-volume CT (public bucket, uncompressed [D,128,128] chunks) for the
5 mm tile plus a 384 px margin (zero beyond the volume), keep the 17 centred window layers, lay all regions out in one
mosaic, run Reader V3 (A) and dense_native (B) with --direction both, crop each tile back.
Outputs out/preds_<id>.npz (uint8 maps + valid; private, never published) and out/job_f1_meta.json (numbers only)."""
import json, os, sys, time, subprocess, urllib.request, urllib.error, concurrent.futures as cf, numpy as np
N = os.path.dirname(os.path.abspath(__file__)); V = "/workspace/vesuvius"; G = os.environ.get("G_DIR", "/workspace/gpu_oct")
OUT, WK = f"{N}/out", f"{N}/work"; os.makedirs(OUT, exist_ok=True); os.makedirs(WK, exist_ok=True)
BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"; M = 384; PY = sys.executable
CK = {"rv3": f"{V}/checkpoints/reader/reader-v3.pth", "dn": f"{V}/checkpoints/erwin/dense_native_016000.pth"}
meta = {"t0": time.time(), "regions": {}, "infer": {}}
def log(*a):
    s = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " f1 " + " ".join(map(str, a)); print(s, flush=True)
    open(f"{G}/logs/timeline.txt", "a").write(s + "\n")
def save(): json.dump(meta, open(f"{OUT}/job_f1_meta.json", "w"), indent=1)
def chunk(key, D, yi, xi):
    for t in range(6):
        try: return np.frombuffer(urllib.request.urlopen(f"{BUCKET}{key}0/0/{yi}/{xi}", timeout=120).read(), np.uint8).reshape(D, 128, 128)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404): return None
            time.sleep(5 * (t + 1))
        except Exception: time.sleep(5 * (t + 1))
    raise RuntimeError(f"chunk {key} {yi} {xi} failed")
def fetch(key, D, H, W, y0, x0, h, w, ls):
    """CT[ls:ls+17, y0:y0+h, x0:x0+w] with zeros outside the volume"""
    out = np.zeros((17, h, w), np.uint8); c = 128
    ya, yb, xa, xb = max(0, y0), min(H, y0 + h), max(0, x0), min(W, x0 + w)
    jobs = [(yi, xi) for yi in range(ya // c, (yb - 1) // c + 1) for xi in range(xa // c, (xb - 1) // c + 1)]
    with cf.ThreadPoolExecutor(16) as ex:
        for (yi, xi), b in zip(jobs, ex.map(lambda j: chunk(key, D, *j), jobs)):
            if b is None: continue
            gy0, gy1 = max(ya, yi * c), min(yb, (yi + 1) * c); gx0, gx1 = max(xa, xi * c), min(xb, (xi + 1) * c)
            out[:, gy0 - y0:gy1 - y0, gx0 - x0:gx1 - x0] = b[ls:ls + 17, gy0 - yi * c:gy1 - yi * c, gx0 - xi * c:gx1 - xi * c]
    return out
def write_zarr(path, A, ch=128):
    D, H, W = A.shape; os.makedirs(f"{path}/0", exist_ok=True); json.dump({"zarr_format": 2}, open(f"{path}/.zgroup", "w"))
    json.dump({"zarr_format": 2, "shape": [D, H, W], "chunks": [D, ch, ch], "dtype": "|u1", "compressor": None, "fill_value": 0,
               "order": "C", "filters": None, "dimension_separator": "/"}, open(f"{path}/0/.zarray", "w"))
    for yi in range(-(-H // ch)):
        for xi in range(-(-W // ch)):
            b = np.zeros((D, ch, ch), np.uint8); s = A[:, yi*ch:(yi+1)*ch, xi*ch:(xi+1)*ch]; b[:, :s.shape[1], :s.shape[2]] = s
            if b.any(): os.makedirs(f"{path}/0/0/{yi}", exist_ok=True); b.tofile(f"{path}/0/0/{yi}/{xi}")
SEL = json.load(open(f"{N}/regions_f1.json")); items = []
for seg, s in SEL.items():
    D, (H, W), ls = s["depth"], s["canvas"], s["window"][0]
    for kind in ("positive", "blank"):
        for i, t in enumerate(s[kind]):
            rid = f"{seg}|{kind[:3]}{i}"; T = t["size"]
            crop = fetch(s["sv"], D, H, W, t["y0"] - M, t["x0"] - M, T + 2 * M, T + 2 * M, ls)
            core = crop[:, M:M + T, M:M + T]; v = (core > 0).all(0)
            items.append(dict(id=rid, crop=crop, T=T)); meta["regions"][rid] = dict(seg=seg, kind=kind, idx=i, y0=t["y0"], x0=t["x0"], T=T,
                window=s["window"], valid_frac=float(v.mean()), crop_mean=float(crop.mean())); log("fetched", rid, T, round(float(v.mean()), 4))
save()
WMAX = 5600; place = {}; x = y = rowh = 0
for it in items:
    h = w = it["T"] + 2 * M
    if x + w > WMAX: x, y, rowh = 0, y + rowh, 0
    place[it["id"]] = (y, x, it["T"]); x += w; rowh = max(rowh, h)
HM = y + rowh; WM = max(p[1] + p[2] + 2 * M for p in place.values()); mos = np.zeros((17, HM, WM), np.uint8)
for it in items:
    y, x, T = place[it["id"]]; mos[:, y:y + T + 2 * M, x:x + T + 2 * M] = it["crop"]; it["crop"] = None
meta["mosaic"] = {"shape": [HM, WM], "place": place}; write_zarr(f"{WK}/mosaic.zarr", mos); valid0 = (mos > 0).all(0); del mos
save(); log("mosaic", HM, WM)
TEST = os.environ.get("F1_TEST") == "1"; env = dict(os.environ, PYTHONPATH=f"{V}/villa/vesuvius/src", OMP_NUM_THREADS="4")
import tifffile; preds = {}
for ck, path in CK.items():
    t = time.time(); td = f"{WK}/tmp_{ck}"; os.makedirs(td, exist_ok=True)
    if TEST:
        import zarr; m = np.asarray(zarr.open(f"{WK}/mosaic.zarr/0", mode="r")); preds[(ck, "fwd")] = m[8]; preds[(ck, "rev")] = m[9]; continue
    cmd = [PY, "-m", "vesuvius.ink_detection.inference.infer", f"{WK}/mosaic.zarr", path, "out.tif", "--layer-start", "0", "--layer-end", "17",
           "--direction", "both", "--no-compile", "--num-workers", os.environ.get("INFER_NW", "4"), "--batch-size", "8", "--gpus", "0"]
    r = subprocess.run(cmd, cwd=td, env=dict(env, TMPDIR=td), stdout=open(f"{OUT}/infer_{ck}.log", "w"), stderr=subprocess.STDOUT, timeout=5400)
    meta["infer"][ck] = {"exit": r.returncode, "secs": round(time.time() - t, 1)}; log("infer", ck, "exit", r.returncode, round(time.time() - t))
    if r.returncode == 0: preds[(ck, "fwd")] = tifffile.imread(f"{td}/out.tif"); preds[(ck, "rev")] = tifffile.imread(f"{td}/out_reverse.tif")
    save()
for k in list(preds):
    if preds[k].shape[:2] != valid0.shape:
        from scipy import ndimage as _ndi
        a = preds[k]; meta.setdefault("resized", {})["_".join(k)] = [list(a.shape), list(valid0.shape)]
        preds[k] = _ndi.zoom(a.astype(np.float32), (valid0.shape[0] / a.shape[0], valid0.shape[1] / a.shape[1]), order=1)[:valid0.shape[0], :valid0.shape[1]].clip(0, 255).astype(np.uint8)
for rid, (y, x, T) in place.items():
    ys, xs = slice(y + M, y + M + T), slice(x + M, x + M + T); d = {"valid": valid0[ys, xs]}
    for (ck, dr), p in preds.items(): d[f"{ck}_{dr}"] = p[ys, xs]
    np.savez_compressed(f"{OUT}/preds_{rid.replace('|', '__')}.npz", **d)
meta["t1"] = time.time(); save(); log("job_f1 done", round((meta["t1"] - meta["t0"]) / 60, 1), "min")
