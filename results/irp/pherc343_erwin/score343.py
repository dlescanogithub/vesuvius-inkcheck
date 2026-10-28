"""Score per PREREG.md (sha256 4a1ba702...). Node D rule verbatim from hires_test/tools/score.py metrics() + verdict.py,
reading side = villa/hecate 'reverse', null = opposite direction. Secondary: circular letter-box AUC with shift null."""
import sys, json, numpy as np, tifffile, zarr
from PIL import Image
from scipy import ndimage as ndi
from scipy.stats import rankdata
sys.path.insert(0, '/workspace/vesuvius/hires_test/tools'); sys.path.insert(0, '/workspace/vesuvius/tools')
from score import metrics, stroke_width
UM = 9.612; NAT = 8.64; R0, C0 = 600, 650
def villa(p):
    a = tifffile.imread(p).astype(np.float32); a = a / 255. if a.max() > 1.5 else a
    return ndi.zoom(a, NAT / UM, order=1)
def hec(p):
    a = np.asarray(Image.open(p).convert('L'), np.float32) / 255.; return ndi.zoom(a, 9.6 / UM, order=1)
L = np.asarray(zarr.open('render_L.zarr/0', mode='r')[13]) > 0
M = {}
for m in ('dnative', 's42', 's43'):
    M[m] = (villa(f'out/{m}_reverse.tif'), villa(f'out/{m}.tif'))
import os
if os.path.exists('out/hecate.DONE'): M['hecate'] = (hec('out/hecate_reverse.png'), hec('out/hecate.png'))
OUTF = 'RESULTS.json' if 'hecate' in M else 'RESULTS_villa3_interim.json'
valid = ndi.zoom(L.astype(np.float32), NAT / UM, order=0) > 0
h = min([valid.shape[0]] + [v.shape[0] for p in M.values() for v in p]); w = min([valid.shape[1]] + [v.shape[1] for p in M.values() for v in p])
valid = ndi.binary_erosion(valid[:h, :w], iterations=3); M = {k: (a[:h, :w], b[:h, :w]) for k, (a, b) in M.items()}
out = dict(grid_um=UM, valid_cm2=round(float(valid.sum() * (UM / 1e4) ** 2), 3), shape=[h, w], models={})
ks = list(M); pr = {}
for i, a in enumerate(ks):
    for b in ks[i + 1:]: pr[f'{a}~{b}'] = round(float(np.corrcoef(M[a][0][valid], M[b][0][valid])[0, 1]), 3)
out['pairwise_r_reading'] = pr
npass = 0
for k, (rd, nl) in M.items():
    mr, mn = metrics(rd, valid), metrics(nl, valid); sw = stroke_width(np.where(valid, rd, 0), UM)
    c, cn = mr['comps_per_cm2'], mn['comps_per_cm2']; ncomp = round(c * out['valid_cm2'])
    others = [v for kk, v in pr.items() if k in kk.split('~')]
    crit = dict(i_ratio=bool((cn == 0 and c > 0) or (cn and c / cn >= 2)), ii_min5=bool(ncomp >= 5), iii_r=bool(max(others) >= 0.3),
                iv_width=bool(sw is not None and 100 <= sw['median_um'] <= 500))
    ok = all(crit.values()); npass += ok
    out['models'][k] = dict(reading=mr, null=mn, ratio=round(c / cn, 2) if cn else None, n_comps=ncomp, stroke_width=sw, max_r_other=max(others), criteria=crit, passes=ok)
out['node_D_verdict'] = 'CANDIDATE' if npass >= 2 else 'NOTHING'; out['n_checkpoints_passing'] = npass
# secondary: circular letter boxes
B = json.load(open(sys.argv[1])); boxes = B['letters']
bm = np.zeros((h, w), bool); s = NAT / UM
for bx in boxes:
    x0, y0, x1, y1 = bx['box'] if isinstance(bx, dict) else bx
    bm[max(0, int((y0 - R0) * s)):int((y1 - R0) * s), max(0, int((x0 - C0) * s)):int((x1 - C0) * s)] = True
def z(a): return (a - a[valid].mean()) / a[valid].std()
ens_r = np.mean([z(v[0]) for v in M.values()], 0); ens_n = np.mean([z(v[1]) for v in M.values()], 0)
rng = np.random.default_rng(343); shifts = [(int(rng.integers(h)), int(rng.integers(w))) for _ in range(2000)]
f = 2; vs = valid[::f, ::f]; bs = bm[::f, ::f]
def auc_null(a):
    a = a[::f, ::f]; r = np.zeros(a.shape); r[vs] = rankdata(a[vs])
    def auc(mask):
        m = mask & vs; n1 = m.sum(); n0 = vs.sum() - n1; return (r[m].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    a0 = auc(bs); nul = np.array([auc(np.roll(bs, (dy // f, dx // f), (0, 1))) for dy, dx in shifts])
    return round(float(a0), 4), round(float((1 + (nul >= a0).sum()) / (1 + len(nul))), 4), round(float(np.percentile(nul, 95)), 4)
sec = {}
for k, (rd, nl) in list(M.items()) + [('ensemble', (ens_r, ens_n))]:
    a, p, q = auc_null(rd); ab = auc_null(nl)[0]
    sec[k] = dict(auc_reading=a, p_shift=p, null95=q, auc_blind=ab, label='CONSISTENT' if p < 0.05 and a > ab else 'NOT_CONSISTENT')
out['secondary_letterbox_circular'] = sec; out['box_px_frac'] = round(float((bm & valid).sum() / valid.sum()), 4)
out['models_scored'] = list(M); json.dump(out, open(OUTF, 'w'), indent=1); print(json.dumps(out, indent=1))
