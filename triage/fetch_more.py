"""Triage step 1b: extend the node-B proxy table to every segment in triage/segments.json (public open-data bucket).
For each segment: download level 3 (1/8 scale) to find the 2048x2048 level-0 box with the most valid surface, fetch
that box at level 0 (bench/fetch_crop.py), then compute the same proxies as triage/proxies.py (strict and relaxed HF).
Resumable; appends to triage/proxies.json. Run from the workspace root, niced."""
import sys, os, json, subprocess, urllib.request, numpy as np
REPO = "prize_oct/publish/vesuvius-inkcheck"
sys.path.insert(0, "tools"); sys.path.insert(0, REPO + "/study"); sys.path.insert(0, REPO + "/triage")
from zread import read_local
from proxies_all_lib import psd_ratio, layer_corr
B = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
D = "data_raw/triage"
WIN = {8.64: (7, 24), 9.362: (5, 22), 9.366: (5, 22), 7.91: (8, 25)}


def lvl3(key, dst):
    za = json.loads(urllib.request.urlopen(B + key + "/3/.zarray", timeout=60).read())
    Z, Y, X = za["shape"]; cz, cy, cx = za["chunks"]; sep = za.get("dimension_separator", ".")
    a = np.zeros((Z, Y, X), np.uint8)
    for i in range((Y + cy - 1) // cy):
        for j in range((X + cx - 1) // cx):
            try:
                b = urllib.request.urlopen(B + key + "/3/" + sep.join(map(str, (0, i, j))), timeout=90).read()
            except Exception:
                continue
            c = np.frombuffer(b, np.uint8).reshape(cz, cy, cx)[:Z]
            yy, xx = min(cy, Y - i * cy), min(cx, X - j * cx)
            a[:, i * cy:i * cy + yy, j * cx:j * cx + xx] = c[:, :yy, :xx]
    return a


def main():
    from hf_relaxed import psd_ratio_relaxed
    segs = json.load(open(f"{REPO}/triage/segments.json"))
    out_p = f"{REPO}/triage/proxies.json"
    for s in segs:
        out = json.load(open(out_p))
        sid = s["segment"][:14]
        if any(k.startswith(s["scroll"] + " " + sid) for k in out):
            print("have", s["scroll"], sid, flush=True); continue
        name = f"{s['scroll']} {s['segment'][:40]}"
        try:
            l3 = lvl3(s["volume"], None)
            Z = l3.shape[0]
            a, b = WIN.get(s["um"], (Z // 2 - 9, Z // 2 + 8))
            if b > Z: a, b = max(0, Z // 2 - 9), min(Z, Z // 2 + 8)
            v3 = l3[a:b].min(0) > 0
            if v3.sum() < 64 * 64:
                print("too small", name, int(v3.sum()), flush=True); continue
            S = 256
            ii = np.pad(v3.astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
            Hh, Ww = v3.shape
            best, by, bx = -1, 0, 0
            for y in range(0, max(1, Hh - S + 1), 16):
                for x in range(0, max(1, Ww - S + 1), 16):
                    y1, x1 = min(Hh, y + S), min(Ww, x + S)
                    n = ii[y1, x1] - ii[y, x1] - ii[y1, x] + ii[y, x]
                    if n > best: best, by, bx = n, y, x
            dst = f"{D}/{s['scroll']}_{sid}.zarr"
            subprocess.run([sys.executable, f"{REPO}/bench/fetch_crop.py", s["volume"], dst, "--yx", f"{by*8},{bx*8}",
                            "--hw", "2048,2048"], check=True)
            v = read_local(dst + "/0"); c = (a + b) // 2
            valid = v[a:b].min(0) > 0
            rec = dict(scroll=s["scroll"], zarr=dst, um=s["um"], window=[a, b], protocol=s["volume"].split("/")[-1],
                       shape=list(v.shape), valid_frac=float(valid.mean()), valid_mm2=float(valid.sum() * (s["um"] * 1e-3) ** 2),
                       has_ink_map=s["has_ink_map"], source="open-data bucket, 2048x2048 level-0 crop with most valid surface")
            try:
                hf, nt = psd_ratio(v[c], s["um"], valid); rec.update(hf_ratio=hf, hf_tiles=nt)
            except Exception as e:
                rec.update(hf_ratio=None, hf_tiles=0)
            hr, nr = psd_ratio_relaxed(v[c], s["um"], valid); rec.update(hf_ratio_relaxed=hr, hf_tiles_relaxed=nr)
            rec["layer_hp_corr"] = layer_corr(v, range(max(0, c - 6), min(v.shape[0], c + 7)), s["um"], valid)
            out = json.load(open(out_p)); out[name] = rec; json.dump(out, open(out_p, "w"), indent=1)
            print(name, {k: rec[k] for k in ("hf_ratio", "hf_ratio_relaxed", "layer_hp_corr", "valid_mm2")}, flush=True)
        except Exception as e:
            print("ERR", name, repr(e)[:200], flush=True)
    print("FETCH_MORE_DONE", flush=True)


if __name__ == "__main__":
    main()
