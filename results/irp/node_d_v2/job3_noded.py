"""job3_noded.py (pod) — node D v2 held-out inference (PREREG_NODE_D_V2.md, deviations D1-D3).
Re-renders the 16 committed regions (same renderer + params as the box), renders PHerc0343 (Erwin region) with
k=-31..96 for the v2 pitch/off-winding windows, builds one 17-layer mosaic per depth slot (0, +round(P/2), -round(P/2);
window = card window mapped by the box-measured render_shift), runs Reader V3 (A) and dense_native (B) with
--direction both, and crops each region back out. Outputs: out/preds_<name>.npz (uint8 maps, private, never published),
out/job3_meta.json (numbers only)."""
import json, os, sys, subprocess, time, hashlib, numpy as np
N = os.path.dirname(os.path.abspath(__file__)); V = "/workspace/vesuvius"; G = os.environ.get("G_DIR", "/workspace/gpu_oct")
OUT = f"{N}/out"; WK = f"{N}/work"; os.makedirs(OUT, exist_ok=True); os.makedirs(WK, exist_ok=True)
sys.path.insert(0, N); from node_d_v2 import estimate_winding_pitch
PY = sys.executable; NPROC = max(2, min(8, (os.cpu_count() or 4) - 1))
CARD = {"0172": (8, 25), "0500P2": (5, 22), "0841": (5, 22), "0009B": (7, 24)}
VOL = {"0172": "PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0",
       "0500P2": "PHerc0500P2/volumes/20250820143440-9.362um-1.2m-113keV-masked.zarr/0",
       "0841": "PHerc0841/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr/0",
       "0009B": "PHerc0009B/volumes/20250521125136-8.640um-1.2m-116keV-masked.zarr/0"}
CK = {"rv3": f"{V}/checkpoints/reader/reader-v3.pth", "dn": f"{V}/checkpoints/erwin/dense_native_016000.pth"}
E343 = "/tmp/erwin/outputs/concat_w047-w048_R5B2_z9500-11000.tifxyz"
meta = {"t0": time.time(), "nproc": NPROC, "items": {}, "infer": {}}
def log(*a):
    s = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " job3 " + " ".join(map(str, a))
    print(s, flush=True); open(f"{G}/logs/timeline.txt", "a").write(s + "\n")
def save(): json.dump(meta, open(f"{OUT}/job3_meta.json", "w"), indent=1)
def load(z):
    m = json.load(open(z + "/0/.zarray")); D, H, W = m["shape"]; c = m["chunks"]; out = np.zeros((D, H, W), np.uint8)
    for yi in range(-(-H // c[1])):
        for xi in range(-(-W // c[2])):
            p = f"{z}/0/0/{yi}/{xi}"
            if os.path.exists(p):
                b = np.frombuffer(open(p, "rb").read(), np.uint8).reshape(D, c[1], c[2])
                out[:, yi*c[1]:(yi+1)*c[1], xi*c[2]:(xi+1)*c[2]] = b[:, :min(c[1], H - yi*c[1]), :min(c[2], W - xi*c[2])]
    return out
def write_zarr(path, A, ch=128):
    D, H, W = A.shape; os.makedirs(f"{path}/0", exist_ok=True)
    json.dump({"zarr_format": 2}, open(f"{path}/.zgroup", "w"))
    json.dump({"zarr_format": 2, "shape": [D, H, W], "chunks": [D, ch, ch], "dtype": "|u1", "compressor": None, "fill_value": 0,
               "order": "C", "filters": None, "dimension_separator": "/"}, open(f"{path}/0/.zarray", "w"))
    for yi in range(-(-H // ch)):
        for xi in range(-(-W // ch)):
            b = np.zeros((D, ch, ch), np.uint8); s = A[:, yi*ch:(yi+1)*ch, xi*ch:(xi+1)*ch]; b[:, :s.shape[1], :s.shape[2]] = s
            if b.any(): os.makedirs(f"{path}/0/0/{yi}", exist_ok=True); b.tofile(f"{path}/0/0/{yi}/{xi}")
def treehash(z):
    h = hashlib.sha256()
    for r, ds, fs in os.walk(z):
        ds.sort()
        for f in sorted(fs): p = os.path.join(r, f); h.update(os.path.relpath(p, z).encode()); h.update(open(p, "rb").read())
    return h.hexdigest()

regs = json.load(open(f"{N}/regions_render.json")); AP = json.load(open(f"{N}/align_pitch.json"))
# 1) regions
for g in regs:
    out = f"{WK}/{g['name']}.zarr"
    if not os.path.exists(out + ".DONE"):
        cmd = [PY, f"{N}/tools/render_tifxyz.py", f"{N}/meshes/{g['seg']}", VOL[g["seg"].split("-")[0]], out, "--R", "64", "--tile", "256",
               "--procs", str(NPROC), "--rows", "%d:%d" % tuple(g["rows"]), "--cols", "%d:%d" % tuple(g["cols"])]
        r = subprocess.run(cmd, env=dict(os.environ, ZFETCH_MEM="1"), stdout=open(f"{OUT}/render_{g['name']}.log", "w"), stderr=subprocess.STDOUT, timeout=1800)
        if r.returncode: log("render FAILED", g["name"]); continue
        open(out + ".DONE", "w").close()
    meta["items"][g["name"]] = {"render_treehash": treehash(out + "/0")}; log("rendered", g["name"])
save()
# 2) PHerc0343 (Erwin region), k=-31..96 => render index i <-> offset (i-31)-32.5 ; card window k 26..42 => i 57..73
R343 = f"{WK}/r343v2.zarr"
TEST = os.environ.get("JOB3_TEST") == "1"
if not TEST and not os.path.exists(R343 + ".DONE"):
    r = subprocess.run([PY, f"{V}/prize_oct/erwin343/render343.py", E343, "PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr/0", R343,
                        "--vox_um", "8.64", "--out_um", "8.64", "--k0", "-31", "--k1", "97", "--umb", "/tmp/erwin/inputs/umbilicus_PHerc0343.json",
                        "--tile", "256", "--procs", str(NPROC), "--rows", "600:2100", "--cols", "650:5550"],
                       cwd=f"{V}/prize_oct/erwin343", stdout=open(f"{OUT}/render_343v2.log", "w"), stderr=subprocess.STDOUT, timeout=3600)
    if r.returncode == 0: open(R343 + ".DONE", "w").close()
    log("343 v2 render exit", r.returncode)
# 3) windows + mosaics
items = []
for g in regs:
    if g["name"] not in meta["items"]: continue
    a = AP.get(g["name"]); P = a and a["pitch"]; ls, le = CARD[g["seg"].split("-")[0]]
    items.append(dict(name=g["name"], z=f"{WK}/{g['name']}.zarr", base=ls + a["render_shift"], P=P, core=g["core"]))
if os.path.exists(R343 + ".DONE"):
    A = load(R343)
    valid = (A > 0).all(0); prof = A[:, valid].mean(1) if valid.any() else None
    P343 = estimate_winding_pitch(prof, min_lag=6, max_lag=60) if prof is not None else None
    meta["items"]["erwin343"] = {"profile_k": [-31, 97], "profile": [round(float(x), 2) for x in prof], "pitch": P343, "valid_frac": float(valid.mean()),
                                 "render_treehash": treehash(R343 + "/0")}
    L1 = f"{V}/prize_oct/erwin343/render_L.zarr/0"   # job1 render (k=20..46) -> same samples at i=51..77 ?
    if os.path.exists(L1 + "/.zarray"):
        B = load(f"{V}/prize_oct/erwin343/render_L.zarr"); n = min(B.shape[0], A.shape[0] - 51)
        d = np.abs(A[51:51+n].astype(np.int16) - B[:n].astype(np.int16)); meta["items"]["erwin343"]["vs_job1_render"] = {"layers": int(n), "max_abs": int(d.max()), "mean_abs": float(d.mean())}
    del A
    items.append(dict(name="erwin343", z=R343, base=57, P=P343, core=None))
save()
slots = {"d0": 0, "plus": +1, "minus": -1}; WMAX = 5600; place = {}; x = y = rowh = 0
for it in items:
    h, w = json.load(open(it["z"] + "/0/.zarray"))["shape"][1:]
    if x + w > WMAX: x, y, rowh = 0, y + rowh, 0
    place[it["name"]] = (y, x, h, w); x += w; rowh = max(rowh, h)
HM = y + rowh; WM = max(p[1] + p[3] for p in place.values())
mos = {s: np.zeros((17, HM, WM), np.uint8) for s in slots}
for it in items:
    A = load(it["z"]); D = A.shape[0]; y, x, h, w = place[it["name"]]; info = meta["items"][it["name"]]
    hp = int(round(it["P"] / 2)) if it["P"] else None; info["half_pitch"] = hp; info["windows"] = {}
    for s, sg in slots.items():
        if sg and hp is None: continue
        s0 = it["base"] + (sg * hp if sg else 0)
        if s0 < 0 or s0 + 17 > D: info["windows"][s] = None; continue
        mos[s][:, y:y+h, x:x+w] = A[s0:s0+17]; info["windows"][s] = [s0, s0 + 17]
    del A
meta["mosaic"] = {"shape": [HM, WM], "place": place}; save()
for s in slots: write_zarr(f"{WK}/mosaic_{s}.zarr", mos[s]); log("mosaic", s, HM, WM)
valid0 = (mos["d0"] > 0).all(0); del mos
# 4) inference
env = dict(os.environ, PYTHONPATH=f"{V}/villa/vesuvius/src", OMP_NUM_THREADS="4")
import tifffile
preds = {}
for ck, path in CK.items():
    for s in slots:
        t = time.time(); td = f"{WK}/tmp_{ck}_{s}"; os.makedirs(td, exist_ok=True)
        cmd = [PY, "-m", "vesuvius.ink_detection.inference.infer", f"{WK}/mosaic_{s}.zarr", path, "out.tif", "--layer-start", "0", "--layer-end", "17",
               "--direction", "both", "--no-compile", "--num-workers", "4", "--batch-size", "8", "--gpus", "0"]
        if TEST:
            m = load(f"{WK}/mosaic_{s}.zarr"); preds[(ck, s, "fwd")] = m[8]; preds[(ck, s, "rev")] = m[9]; continue
        r = subprocess.run(cmd, cwd=td, env=dict(env, TMPDIR=td), stdout=open(f"{OUT}/infer_{ck}_{s}.log", "w"), stderr=subprocess.STDOUT, timeout=3600)
        meta["infer"][f"{ck}_{s}"] = {"exit": r.returncode, "secs": round(time.time() - t, 1)}; log("infer", ck, s, "exit", r.returncode, round(time.time() - t))
        if r.returncode == 0:
            preds[(ck, s, "fwd")] = tifffile.imread(f"{td}/out.tif"); preds[(ck, s, "rev")] = tifffile.imread(f"{td}/out_reverse.tif")
        save()
# 5) crop back (core tile for the 16 regions, full region for 343); predictions not at mosaic size are resized (logged)
for k in list(preds):
    if preds[k].shape[:2] != valid0.shape:
        from scipy import ndimage as _ndi
        a = preds[k]; meta.setdefault("resized", {})["_".join(k)] = [list(a.shape), list(valid0.shape)]
        preds[k] = _ndi.zoom(a.astype(np.float32), (valid0.shape[0] / a.shape[0], valid0.shape[1] / a.shape[1]), order=1)[:valid0.shape[0], :valid0.shape[1]].clip(0, 255).astype(np.uint8)
for it in items:
    y, x, h, w = place[it["name"]]; cy, cx, T = it["core"] if it["core"] else (0, 0, None)
    ys, xs = (slice(y+cy, y+cy+T), slice(x+cx, x+cx+T)) if T else (slice(y, y+h), slice(x, x+w))
    d = {"valid_d0": valid0[ys, xs]}
    for (ck, s, dr), p in preds.items():
        if meta["items"][it["name"]]["windows"].get(s): d[f"{ck}_{s}_{dr}"] = p[ys, xs]
    np.savez_compressed(f"{OUT}/preds_{it['name']}.npz", **d)
meta["t1"] = time.time(); save(); log("job3 done", round((meta["t1"] - meta["t0"]) / 60, 1), "min")
