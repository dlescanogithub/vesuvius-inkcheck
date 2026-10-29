"""Render a tifxyz mesh into a surface volume [k1-k0, H, W] (uint8 OME-Zarr v2, chunks [D,128,128]) by trilinear
sampling of the public, uncompressed 128^3-chunked OME-Zarr scan along the outward mesh normal.

Layer k samples the CT at (k - 32.5) voxels along the normal (+ = away from the scroll axis), as in E. Nieuwlaar's
pherc343-first-letters renders; d = k - 33. Defaults reproduce the IRP crop: raw render rows 600:2100, cols 650:5550,
k = 20..46 (27 layers, so his d=+1 window k = 26..42 is layers 6..22 here). Chunks are cached on disk; tiles are resumable.

    python render_surface.py $ERWIN_REPO/outputs/concat_w047-w048_R5B2_z9500-11000.tifxyz \
        --umb $ERWIN_REPO/inputs/umbilicus_PHerc0343.json --out work/render_L.zarr --cache work/cache

Self-contained (numpy, scipy, tifffile); no scroll data ships with this file.
"""
import os, json, argparse, time, threading, itertools, urllib.request, urllib.error, numpy as np, tifffile
from concurrent.futures import ThreadPoolExecutor
from scipy.ndimage import map_coordinates

BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
DEFAULT_ARR = "PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr/0"
CACHE = "cache"


# ---- remote zarr v2 chunks (uncompressed uint8) ---------------------------------------------------------------
def zmeta(arr):
    m = json.loads(urllib.request.urlopen(BUCKET + arr + "/.zarray", timeout=60).read())
    if m.get("compressor") is not None or m.get("dtype") != "|u1":
        raise SystemExit(f"expected an uncompressed uint8 array, got compressor={m.get('compressor')} dtype={m.get('dtype')}")
    return m


def _get(url, dst, tries=6):
    if os.path.exists(dst):
        return True
    for i in range(tries):
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp = dst + f".part{os.getpid()}_{threading.get_ident()}"
            open(tmp, "wb").write(data); os.replace(tmp, dst)
            return True
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):  # missing chunk = fill value 0
                os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, "wb").close(); return False
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError("failed " + url)


def chunk_path(arr, idx):
    return os.path.join(CACHE, arr, "/".join(map(str, idx)))


def fetch_chunks(arr, idxs, threads=8):
    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(lambda ix: _get(BUCKET + arr + "/" + "/".join(map(str, ix)), chunk_path(arr, ix)), idxs))


def read_chunk(arr, m, idx):
    p = chunk_path(arr, idx)
    raw = open(p, "rb").read() if os.path.exists(p) else b""
    return np.zeros(m["chunks"], np.uint8) if not raw else np.frombuffer(raw, np.uint8).reshape(m["chunks"])


# ---- mesh -----------------------------------------------------------------------------------------------------
def load_mesh(d):
    X, Y, Z = (tifffile.imread(f"{d}/{c}.tif").astype(np.float64) for c in "xyz")
    valid = (X > 0) & (Y > 0) & (Z > 0)
    return X, Y, Z, valid, json.load(open(f"{d}/meta.json"))


def coarse_normals(X, Y, Z, valid):
    P = np.stack([X, Y, Z], -1); P[~valid] = np.nan
    du = np.full_like(P, np.nan); dv = np.full_like(P, np.nan)
    du[:, 1:-1] = (P[:, 2:] - P[:, :-2]) / 2; du[:, 0] = P[:, 1] - P[:, 0]; du[:, -1] = P[:, -1] - P[:, -2]
    m = np.isnan(du[..., 0])
    fwd = np.full_like(P, np.nan); fwd[:, :-1] = P[:, 1:] - P[:, :-1]
    bwd = np.full_like(P, np.nan); bwd[:, 1:] = P[:, 1:] - P[:, :-1]
    du[m] = np.where(np.isnan(fwd[m]), bwd[m], fwd[m])
    dv[1:-1] = (P[2:] - P[:-2]) / 2; dv[0] = P[1] - P[0]; dv[-1] = P[-1] - P[-2]
    m = np.isnan(dv[..., 0])
    fwd = np.full_like(P, np.nan); fwd[:-1] = P[1:] - P[:-1]
    bwd = np.full_like(P, np.nan); bwd[1:] = P[1:] - P[:-1]
    dv[m] = np.where(np.isnan(fwd[m]), bwd[m], fwd[m])
    N = np.cross(du, dv); N /= np.linalg.norm(N, axis=-1, keepdims=True) + 1e-12; N[np.isnan(N)] = 0
    return N


# ---- render ---------------------------------------------------------------------------------------------------
G = {}


def do_tile(t):
    g = G; a = g["a"]; ty, tx = t; T = a.tile; Hh, Ww, D = g["Hh"], g["Ww"], g["D"]
    done = f"{a.out}/0/.done_{ty}_{tx}"
    if os.path.exists(done):
        return 0
    h = min(T, Hh - ty); w = min(T, Ww - tx)
    rr, cc = np.meshgrid((g["r0"] + ty + np.arange(h)) / g["s"], (g["c0"] + tx + np.arange(w)) / g["s"], indexing="ij")
    rr = np.clip(rr, 0, g["gh"] - 1); cc = np.clip(cc, 0, g["gw"] - 1); co = np.stack([rr.ravel(), cc.ravel()])
    vm = map_coordinates(g["vf"], co, order=1, mode="nearest").reshape(h, w) > 0.999
    out = np.zeros((D, h, w), np.uint8); nf = 0
    if vm.any():
        P = [map_coordinates(np.where(g["valid"], g[c], 0), co, order=1, mode="nearest").reshape(h, w)[vm] for c in "ZYX"]
        Nn = [map_coordinates(g["N"][..., i], co, order=1, mode="nearest").reshape(h, w)[vm] for i in (2, 1, 0)]
        pB = np.stack(P, 0); nB = np.stack(Nn, 0); nB /= np.linalg.norm(nB, axis=0, keepdims=True) + 1e-12
        S = pB[:, None, :] + g["offs"][None, :, None] * nB[:, None, :]  # [3 (z,y,x), D, n]
        lo = [max(0, int(np.floor(S[d].min()))) for d in range(3)]; hi = [min(g["shp"][d], int(np.ceil(S[d].max())) + 2) for d in range(3)]
        cs = 128; sub = S[:, :, ::7].reshape(3, -1).T
        e = np.concatenate([np.floor((sub + np.array(dd)) / cs).astype(np.int64) for dd in itertools.product((-2, 2), repeat=3)])
        idxs = [ix for ix in sorted(set(map(tuple, e.tolist()))) if all(0 <= ix[d] and ix[d] * cs < g["shp"][d] for d in range(3))]
        fetch_chunks(a.arr, idxs, 8); nf = len(idxs)
        if all(h_ > l_ for l_, h_ in zip(lo, hi)):
            vol = np.zeros([h_ - l_ for l_, h_ in zip(lo, hi)], np.uint8)
            for ix in idxs:
                c = read_chunk(a.arr, g["m"], ix); so, sc = [], []; ok = True
                for d in range(3):
                    c0 = ix[d] * cs; A_ = max(lo[d], c0); B_ = min(hi[d], c0 + cs)
                    if B_ <= A_:
                        ok = False; break
                    so.append(slice(A_ - lo[d], B_ - lo[d])); sc.append(slice(A_ - c0, B_ - c0))
                if ok:
                    vol[tuple(so)] = c[tuple(sc)]
            vals = map_coordinates(vol, (S.reshape(3, -1) - np.array(lo)[:, None]), order=1, cval=0)
            out[:, vm] = np.clip(np.round(vals), 0, 255).astype(np.uint8).reshape(D, -1)
    for yy in range(0, h, 128):
        for xx in range(0, w, 128):
            sub_ = out[:, yy:yy + 128, xx:xx + 128]
            if not sub_.any():
                continue
            blk = np.zeros((D, 128, 128), np.uint8); blk[:, :sub_.shape[1], :sub_.shape[2]] = sub_
            d_ = f"{a.out}/0/0/{(ty + yy) // 128}"; os.makedirs(d_, exist_ok=True)
            open(f"{d_}/{(tx + xx) // 128}", "wb").write(blk.tobytes())
    open(done, "w").close(); return nf


def main():
    global CACHE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", help="tifxyz mesh folder (x.tif, y.tif, z.tif, meta.json)")
    ap.add_argument("--arr", default=DEFAULT_ARR, help=f"array path in the open-data bucket (default {DEFAULT_ARR})")
    ap.add_argument("--out", required=True, help="output OME-Zarr folder")
    ap.add_argument("--umb", required=True, help="umbilicus JSON (control_points with x, y, z) used to orient normals outward")
    ap.add_argument("--cache", default=os.environ.get("RENDER_CACHE", "cache"), help="chunk cache folder (env RENDER_CACHE)")
    ap.add_argument("--k0", type=int, default=20); ap.add_argument("--k1", type=int, default=47)
    ap.add_argument("--rows", default="600:2100", help="raw render rows r0:r1 (mesh grid / scale)")
    ap.add_argument("--cols", default="650:5550", help="raw render cols c0:c1")
    ap.add_argument("--tile", type=int, default=256); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args(); CACHE = a.cache
    X, Y, Z, valid, meta = load_mesh(a.mesh); s = int(round(1 / meta["scale"][0]))
    N = coarse_normals(X, Y, Z, valid)
    U = json.load(open(a.umb))["control_points"]; uz = np.array([p["z"] for p in U]); o = np.argsort(uz)
    ux = np.interp(Z, uz[o], np.array([p["x"] for p in U])[o]); uy = np.interp(Z, uz[o], np.array([p["y"] for p in U])[o])
    dot = (N * np.stack([X - ux, Y - uy, np.zeros_like(X)], -1)).sum(-1)[valid]
    sgn = 1 if np.mean(dot > 0) >= 0.5 else -1; N = N * sgn
    print("[normals] frac pointing outward before sign fix", round(float(np.mean(dot > 0)), 4), "sign", sgn, flush=True)
    r0, r1 = map(int, a.rows.split(":")); c0, c1 = map(int, a.cols.split(":"))
    Hh, Ww = r1 - r0, c1 - c0; K = np.arange(a.k0, a.k1); D = len(K)
    m = zmeta(a.arr); os.makedirs(f"{a.out}/0", exist_ok=True)
    json.dump({"zarr_format": 2}, open(f"{a.out}/.zgroup", "w"))
    json.dump({"multiscales": [{"version": "0.4", "datasets": [{"path": "0"}]}], "render": vars(a)}, open(f"{a.out}/.zattrs", "w"))
    json.dump({"zarr_format": 2, "shape": [D, Hh, Ww], "chunks": [D, 128, 128], "dtype": "|u1", "compressor": None, "fill_value": 0,
               "order": "C", "filters": None, "dimension_separator": "/"}, open(f"{a.out}/0/.zarray", "w"))
    G.update(dict(a=a, s=s, gh=X.shape[0], gw=X.shape[1], Hh=Hh, Ww=Ww, D=D, vf=valid.astype(float), valid=valid,
                  X=X, Y=Y, Z=Z, N=N, offs=K - 32.5, shp=m["shape"], m=m, r0=r0, c0=c0))
    tiles = [(ty, tx) for ty in range(0, Hh, a.tile) for tx in range(0, Ww, a.tile)]; t0 = time.time(); nf = 0
    import multiprocessing as mp
    with mp.get_context("fork").Pool(a.procs) as pool:
        for i, k in enumerate(pool.imap_unordered(do_tile, tiles)):
            nf += k
            if (i + 1) % 10 == 0:
                print(f"[render] {i + 1}/{len(tiles)} chunks={nf} t={time.time() - t0:.0f}s", flush=True)
    print(f"[render] DONE {a.out} shape={[D, Hh, Ww]} t={time.time() - t0:.0f}s chunks={nf}", flush=True)


if __name__ == "__main__":
    main()
