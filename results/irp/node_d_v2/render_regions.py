"""Render the committed node D v2 regions (core tile + 384 px margin) with R=64 along the normal (D2 in DEVIATIONS)."""
import json, os, subprocess, sys
REG = "/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/results/irp/node_d_v2/regions.json"
HERE = os.path.dirname(os.path.abspath(__file__))
VOL = {"0172": "PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0",
       "0500P2": "PHerc0500P2/volumes/20250820143440-9.362um-1.2m-113keV-masked.zarr/0",
       "0841": "PHerc0841/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr/0",
       "0009B": "PHerc0009B/volumes/20250521125136-8.640um-1.2m-116keV-masked.zarr/0"}
M = 384
def regions():
    r = json.load(open(REG)); out = []
    for seg, v in r.items():
        H, W = v["canvas"]
        for kind in ("positive", "blank"):
            for i, t in enumerate(v[kind]):
                y0, x0, T = t["y0"], t["x0"], t["size"]
                ry0, rx0 = max(0, y0 - M), max(0, x0 - M); ry1, rx1 = min(H, y0 + T + M), min(W, x0 + T + M)
                out.append(dict(name=f"{seg}_{kind[:3]}{i}", seg=seg, kind=kind, i=i, rows=[ry0, ry1], cols=[rx0, rx1],
                                core=[y0 - ry0, x0 - rx0, T], um=v["um"]))
    return out
if __name__ == "__main__":
    regs = regions(); json.dump(regs, open(f"{HERE}/regions_render.json", "w"), indent=1)
    only = sys.argv[1:]
    for g in regs:
        if only and g["name"] not in only: continue
        out = f"{HERE}/renders/{g['name']}.zarr"
        if os.path.exists(out + ".DONE"): continue
        cmd = [sys.executable, f"{HERE}/tools/render_tifxyz.py", f"{HERE}/meshes/{g['seg']}", VOL[g["seg"].split("-")[0]], out,
               "--R", "64", "--tile", "256", "--procs", "5", "--rows", "%d:%d" % tuple(g["rows"]), "--cols", "%d:%d" % tuple(g["cols"])]
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, check=True, env=dict(os.environ, ZFETCH_MEM="1"))
        open(out + ".DONE", "w").close()
