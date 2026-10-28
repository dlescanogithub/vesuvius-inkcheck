"""Per rendered region: (1) winding pitch P from the mean CT profile over the core tile (prereg §3: ±64 voxels,
autocorrelation peak in 6-60 voxels); (2) depth-0 alignment vs the official surface volume (D2): correlation of each
official layer with each render layer on the core tile. Output align_pitch.json (numbers only)."""
import json, os, sys, numpy as np
sys.path.insert(0, "/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/src"); sys.path.insert(0, "tools")
from inkcheck.node_d_v2 import estimate_winding_pitch
import zfetch
os.environ["ZFETCH_MEM"] = "1"
SEGP = {"0172-w082": "PHerc0172/segments/20250926122938-w082_20250926122938619_flatboi/surface-volumes/7.91um-53keV-volume-20241024131838.zarr/0",
        "0172-w083": "PHerc0172/segments/20250926132117-w083_20250926132117595_flatboi/surface-volumes/7.91um-53keV-volume-20241024131838.zarr/0",
        "0500P2-371": "PHerc0500P2/segments/20250716055229-z_dbg_gen_00371_inp_hr/surface-volumes/9.362um-1.2m-113keV-volume-20250820143440.zarr/0",
        "0500P2-377": "PHerc0500P2/segments/20250716055230-z_dbg_gen_00377_inp_hr/surface-volumes/9.362um-1.2m-113keV-volume-20250820143440.zarr/0",
        "0841-w00": "PHerc0841/segments/20260220213127-w00/surface-volumes/9.366um-1.2m-113keV-volume-20250821151531.zarr/0",
        "0009B-125754": "PHerc0009B/segments/20250919125754-auto_grown_20250919055754487_inp_hr/surface-volumes/8.64um-1.2m-116keV-volume-20250521125136.zarr/0"}
# preliminary per-segment shift (median over that segment's regions, first pass); used to define the window-valid pixels
SHIFT0 = {"0172-w082": 48, "0172-w083": 48, "0500P2-371": 50, "0500P2-377": 50, "0841-w00": 51, "0009B-125754": 49}
CARD = {"0172": (8, 25), "0500P2": (5, 22), "0841": (5, 22), "0009B": (7, 24)}

def load_render(name):
    z = f"renders/{name}.zarr/0"; m = json.load(open(z + "/.zarray")); D, H, W = m["shape"]
    out = np.zeros((D, H, W), np.uint8)
    for yi in range(-(-H // 128)):
        for xi in range(-(-W // 128)):
            p = f"{z}/0/{yi}/{xi}"
            if os.path.exists(p):
                b = np.frombuffer(open(p, "rb").read(), np.uint8).reshape(D, 128, 128)
                out[:, yi*128:(yi+1)*128, xi*128:(xi+1)*128] = b[:, :min(128, H - yi*128), :min(128, W - xi*128)]
    return out

def one(g):
    V = load_render(g["name"]); cy, cx, T = g["core"]
    C = V[:, cy:cy + T, cx:cx + T].astype(np.float32)
    ls, le = CARD[g["seg"].split("-")[0]]
    allv = (C > 0).all(0)
    P_all = estimate_winding_pitch(C[:, allv].mean(1), min_lag=6, max_lag=60) if allv.any() else None
    # primary (D4): pixels valid on the depth-0 card window (the scoring pixels); all 129 samples, zeros included
    valid = (C[ls + SHIFT0[g["seg"]]:le + SHIFT0[g["seg"]]] > 0).all(0)
    prof = C[:, valid].mean(1) if valid.any() else np.zeros(C.shape[0])
    P = estimate_winding_pitch(prof, min_lag=6, max_lag=60)
    y0, x0 = g["rows"][0] + cy, g["cols"][0] + cx
    arr = SEGP[g["seg"]]; m = zfetch.meta(arr)
    O = zfetch.read_region(arr, [0, y0, x0], [m["shape"][0], y0 + T, x0 + T], threads=16, m=m).astype(np.float32)
    v2 = valid & (O > 0).all(0)
    if v2.sum() < 1000: v2 = (O > 0).all(0) & (C[ls + SHIFT0[g["seg"]]:le + SHIFT0[g["seg"]]] > 0).any(0)
    a = (C[:, v2] - C[:, v2].mean(1, keepdims=True)); a /= np.linalg.norm(a, axis=1, keepdims=True) + 1e-9
    b = (O[:, v2] - O[:, v2].mean(1, keepdims=True)); b /= np.linalg.norm(b, axis=1, keepdims=True) + 1e-9
    R = b @ a.T  # [official layer, render layer]
    mid = (ls + le - 1) // 2
    shifts = [int(np.argmax(R[j])) - j for j in range(ls, le)]
    sh = int(np.round(np.median(shifts))); corr_ok = bool(R[mid, mid + sh] >= 0.5)
    if not corr_ok: sh = SHIFT0[g["seg"]]   # no CT overlap to align on: use the segment's shift from its other regions
    return dict(name=g["name"], pitch=P, pitch_allvalid=P_all, valid_px=int(valid.sum()), corr_ok=corr_ok, profile=[round(float(x), 2) for x in prof], valid_frac=float(valid.mean()),
                official_layers=int(O.shape[0]), card_window=[ls, le], render_shift=sh, shifts=shifts,
                corr_at_shift=[round(float(R[j, j + sh]), 3) for j in range(ls, le)],
                corr_mid=round(float(R[mid, mid + sh]), 3))

if __name__ == "__main__":
    regs = json.load(open("regions_render.json")); res = {}

    for g in regs:
        if g["name"] in res or not os.path.exists(f"renders/{g['name']}.zarr.DONE"): continue
        r = one(g); res[g["name"]] = r
        print(r["name"], "P", r["pitch"], "shift", r["render_shift"], r["shifts"], "corr_mid", r["corr_mid"], flush=True)
        json.dump(res, open("align_pitch.json", "w"), indent=1)
