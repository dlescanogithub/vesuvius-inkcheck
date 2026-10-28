"""Render a tifxyz mesh (coords in the 9.362um volume, A0) from ANOTHER volume via an affine registration
pX0 = Mi (pA0 - t)  (T.json holds M,t with pA0 = M pX0 + t, order z,y,x). Output pixel size --out_um, layer spacing = target voxel.
Resumable per tile. Usage: render_reg.py mesh arr out --T T2.json --vox_um 2.403 --out_um 2.403 --R 40 --rows r0:r1 --cols c0:c1 (rows/cols in A0 render px)"""
import os, sys, json, argparse, time, numpy as np
sys.path.insert(0, '/workspace/vesuvius/tools'); import zfetch
zfetch.CACHE='/workspace/vesuvius/prize_oct/erwin343/cache'
from render_tifxyz import load_mesh, coarse_normals
from scipy.ndimage import map_coordinates
G = {}
def do_tile(t):
    g = G; a = g['a']; ty, tx = t; T = a.tile; Hh, Ww = g['Hh'], g['Ww']
    done = f"{a.out}/0/.done_{ty}_{tx}"
    if os.path.exists(done): return 0
    h = min(T, Hh - ty); w = min(T, Ww - tx); D = g['D']
    # output px -> A0 render px -> mesh grid units
    rr, cc = np.meshgrid((g['r0'] + (ty + np.arange(h)) * g['f']) / g['s'], (g['c0'] + (tx + np.arange(w)) * g['f']) / g['s'], indexing='ij')
    rr = np.clip(rr, 0, g['gh'] - 1); cc = np.clip(cc, 0, g['gw'] - 1); co = np.stack([rr.ravel(), cc.ravel()])
    vm = map_coordinates(g['vf'], co, order=1, mode='nearest').reshape(h, w) > 0.999
    out = np.zeros((D, h, w), np.uint8); nf = 0
    if vm.any():
        P = [map_coordinates(np.where(g['valid'], g[c], 0), co, order=1, mode='nearest').reshape(h, w)[vm] for c in 'ZYX']
        Nn = [map_coordinates(g['N'][..., i], co, order=1, mode='nearest').reshape(h, w)[vm] for i in (2, 1, 0)]
        pA = np.stack(P, 0); nA = np.stack(Nn, 0)
        pB = g['Mi'] @ (pA - g['t'][:, None]); nB = g['Mi'] @ nA; nB /= np.linalg.norm(nB, axis=0, keepdims=True) + 1e-12
        S = pB[:, None, :] + g['offs'][None, :, None] * nB[:, None, :]  # [3, D, n]
        lo = [max(0, int(np.floor(S[d].min()))) for d in range(3)]; hi = [min(g['shp'][d], int(np.ceil(S[d].max())) + 2) for d in range(3)]
        cs = 128; sub = S[:, :, ::7].reshape(3, -1).T
        e = np.concatenate([np.floor((sub + np.array(dd)) / cs).astype(np.int64) for dd in [(a_, b_, c_) for a_ in (-2, 2) for b_ in (-2, 2) for c_ in (-2, 2)]])
        idxs = sorted(set(map(tuple, e.tolist())))
        idxs = [ix for ix in idxs if all(0 <= ix[d] and ix[d] * cs < g['shp'][d] for d in range(3))]
        zfetch.fetch_chunks(a.arr, idxs, 8); nf = len(idxs)
        if all(h_ > l_ for l_, h_ in zip(lo, hi)):
            vol = np.zeros([h_ - l_ for l_, h_ in zip(lo, hi)], np.uint8)
            for ix in idxs:
                c = zfetch.read_chunk(a.arr, g['m'], ix); so, sc = [], []; ok = True
                for d in range(3):
                    c0 = ix[d] * cs; A_ = max(lo[d], c0); B_ = min(hi[d], c0 + cs)
                    if B_ <= A_: ok = False; break
                    so.append(slice(A_ - lo[d], B_ - lo[d])); sc.append(slice(A_ - c0, B_ - c0))
                if ok: vol[tuple(so)] = c[tuple(sc)]
            vals = map_coordinates(vol, (S.reshape(3, -1) - np.array(lo)[:, None]), order=1, cval=0)
            out[:, vm] = np.clip(np.round(vals), 0, 255).astype(np.uint8).reshape(D, -1)
    for yy in range(0, h, 128):
        for xx in range(0, w, 128):
            sub_ = out[:, yy:yy + 128, xx:xx + 128]
            if not sub_.any(): continue
            blk = np.zeros((D, 128, 128), np.uint8); blk[:, :sub_.shape[1], :sub_.shape[2]] = sub_
            d_ = f"{a.out}/0/0/{(ty + yy) // 128}"; os.makedirs(d_, exist_ok=True)
            open(f"{d_}/{(tx + xx) // 128}", 'wb').write(blk.tobytes())
    open(done, 'w').close(); return nf
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mesh'); ap.add_argument('arr'); ap.add_argument('out')
    ap.add_argument('--T', default=None); ap.add_argument('--vox_um', type=float, required=True); ap.add_argument('--out_um', type=float, required=True)
    ap.add_argument('--k0', type=int, default=20); ap.add_argument('--k1', type=int, default=47); ap.add_argument('--umb', required=True); ap.add_argument('--tile', type=int, default=256); ap.add_argument('--procs', type=int, default=3)
    ap.add_argument('--rows', required=True); ap.add_argument('--cols', required=True); ap.add_argument('--flip', action='store_true')
    a = ap.parse_args()
    X, Y, Z, valid, meta = load_mesh(a.mesh); s = int(round(1 / meta['scale'][0]))
    N = coarse_normals(X, Y, Z, valid)
    U = json.load(open(a.umb))['control_points']; uz = np.array([p['z'] for p in U]); o = np.argsort(uz)
    ux = np.interp(Z, uz[o], np.array([p['x'] for p in U])[o]); uy = np.interp(Z, uz[o], np.array([p['y'] for p in U])[o])
    rad = np.stack([X - ux, Y - uy, np.zeros_like(X)], -1); dot = (N * rad).sum(-1)[valid]
    sgn = 1 if np.mean(dot > 0) >= 0.5 else -1; N = N * sgn
    print('[normals] frac pointing outward before sign fix', round(float(np.mean(dot > 0)), 4), 'sign', sgn, flush=True)
    json.dump(dict(normal_sign=sgn, frac_out=float(np.mean(dot > 0))), open(a.out + '_normals.json', 'w'))
    if a.T: T = json.load(open(a.T)); M = np.array(T['M']); t = np.array(T['t'])
    else: M = np.eye(3); t = np.zeros(3)
    r0, r1 = map(int, a.rows.split(':')); c0, c1 = map(int, a.cols.split(':'))
    f = 1.0
    Hh = r1 - r0; Ww = c1 - c0; K = np.arange(a.k0, a.k1); D = len(K)
    m = zfetch.meta(a.arr); os.makedirs(f"{a.out}/0", exist_ok=True)
    json.dump({"zarr_format": 2}, open(f"{a.out}/.zgroup", 'w'))
    json.dump({"multiscales": [{"version": "0.4", "datasets": [{"path": "0"}]}], "render": vars(a)}, open(f"{a.out}/.zattrs", 'w'))
    json.dump({"zarr_format": 2, "shape": [D, Hh, Ww], "chunks": [D, 128, 128], "dtype": "|u1", "compressor": None, "fill_value": 0, "order": "C", "filters": None, "dimension_separator": "/"}, open(f"{a.out}/0/.zarray", 'w'))
    G.update(dict(a=a, s=s, gh=X.shape[0], gw=X.shape[1], Hh=Hh, Ww=Ww, D=D, vf=valid.astype(float), valid=valid, X=X, Y=Y, Z=Z, N=N,
                  Mi=np.linalg.inv(M), t=t, offs=K - 32.5, shp=m['shape'], m=m, r0=r0, c0=c0, f=f))
    tiles = [(ty, tx) for ty in range(0, Hh, a.tile) for tx in range(0, Ww, a.tile)]; t0 = time.time(); nf = 0
    import multiprocessing as mp
    with mp.get_context('fork').Pool(a.procs) as pool:
        for i, k in enumerate(pool.imap_unordered(do_tile, tiles)):
            nf += k
            if (i + 1) % 10 == 0: print(f"[render_reg] {i+1}/{len(tiles)} chunks={nf} t={time.time()-t0:.0f}s", flush=True)
    print(f"[render_reg] DONE {a.out} shape={[D,Hh,Ww]} t={time.time()-t0:.0f}s chunks={nf}", flush=True)
if __name__ == '__main__': main()
