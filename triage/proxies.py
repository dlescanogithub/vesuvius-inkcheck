"""Triage step 1 (CPU, no model): node-B scan-quality proxies on every public surface volume we have locally.
Same proxies and code as study/proxies_all.py (HF spectral ratio 10-25 / 2-10 cyc/mm on the window's centre layer;
adjacent-layer high-pass correlation over centre +-6 layers), each at the volume's own voxel size, on the area where every
window layer is non-zero. Run from the workspace root. Writes <repo>/triage/proxies.json (resumable)."""
import sys, json, os, numpy as np
REPO = "prize_oct/publish/vesuvius-inkcheck"
sys.path.insert(0, "tools"); sys.path.insert(0, REPO + "/study")
from zread import read_local
from proxies_all_lib import psd_ratio, layer_corr

D = "data_raw"
SEGS = [  # name, scroll, zarr (dir holding 0/), um, model window, protocol
    ("PHercParis4 20231005123336 (control crop)", "PHercParis4", "control/p4_ctrl_9.6um.zarr", 9.6, (5, 22), "2.4 µm scan pooled to 9.6 µm"),
    ("PHerc0343P 20250904233748-0_b2", "PHerc0343P", f"{D}/PHerc0343P/segments/20250904233748-0_b2/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr", 8.64, (7, 24), "8.64 µm 116 keV"),
    ("PHerc0343P 20250905172054-1_b2", "PHerc0343P", f"{D}/PHerc0343P/segments/20250905172054-1_b2/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr", 8.64, (7, 24), "8.64 µm 116 keV"),
    ("PHerc0009B 20250919125754 (labelled crop)", "PHerc0009B", f"{D}/newcases/0009B_125754_lab.zarr", 8.64, (7, 24), "8.64 µm 116 keV"),
    ("PHerc0841 20260220213127-w00", "PHerc0841", f"{D}/newcases/0841_w00.zarr", 9.366, (5, 22), "9.37 µm 113 keV"),
    ("PHerc0172 20250926122938-w082", "PHerc0172", f"{D}/newcases/0172_w082.zarr", 7.91, (8, 25), "7.91 µm 53 keV"),
    ("PHerc0172 20250926132117-w083", "PHerc0172", f"{D}/newcases/0172_w083.zarr", 7.91, (8, 25), "7.91 µm 53 keV"),
    ("PHerc0500P2 20250716055229 (gen_00371)", "PHerc0500P2", f"{D}/newcases/0500P2_371.zarr", 9.362, (5, 22), "9.36 µm 113 keV"),
    ("PHerc0500P2 20250716055230 (gen_00377)", "PHerc0500P2", f"{D}/newcases/0500P2_377.zarr", 9.362, (5, 22), "9.36 µm 113 keV"),
]
for z in sorted(os.listdir(f"{D}/PHerc0800/segments")):
    SEGS.append((f"PHerc0800 {z[:14]}", "PHerc0800", f"{D}/PHerc0800/segments/{z}/surface-volumes/8.64um-1.2m-116keV-volume-20250521135224.zarr",
                 8.64, (7, 24), "8.64 µm 116 keV"))

out_p = f"{REPO}/triage/proxies.json"
out = json.load(open(out_p)) if os.path.exists(out_p) else {}
for name, scroll, z, um, (a, b), prot in SEGS:
    if name in out:
        continue
    v = read_local(z + "/0")
    c = (a + b) // 2
    lays = range(max(0, c - 6), min(v.shape[0], c + 7))
    valid = v[a:b].min(0) > 0
    rec = dict(scroll=scroll, zarr=z, um=um, window=[a, b], protocol=prot, shape=list(v.shape),
               valid_frac=float(valid.mean()), valid_mm2=float(valid.sum() * (um * 1e-3) ** 2))
    try:
        hf, nt = psd_ratio(v[c], um, valid)
        rec.update(hf_ratio=hf, hf_tiles=nt)
    except Exception as e:  # no fully valid 512 tile
        rec.update(hf_ratio=None, hf_tiles=0, hf_error=str(e)[:80])
    rec["layer_hp_corr"] = layer_corr(v, lays, um, valid)
    out[name] = rec
    print(name, {k: rec[k] for k in ("hf_ratio", "hf_tiles", "layer_hp_corr", "valid_mm2")}, flush=True)
    json.dump(out, open(out_p, "w"), indent=1)
    del v
