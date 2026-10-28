"""Build a small, exactly-aligned 9.6 um eval crop for one ink_9um held-out (validation-mask) segment.

Recipe (from the label .zattrs): public 2.399 um surface volume, level 2 (9.596 um XY),
z planes 13..96 mean-pooled by 4 -> 21 slices; annotation lives at channel 10.
Writes OUT/<case>/{volume.zarr (group, array 0, uint8 ZYX), ink.png, valid.png, meta.json}.
Only chunks that intersect the validation mask bbox are downloaded.
usage: python fetch_ink9um_val.py CASE OUTDIR [--margin 64]
"""
import json, sys, os, re, argparse, concurrent.futures as cf
import numpy as np, requests, numcodecs, zarr
from PIL import Image

HF = "https://huggingface.co"
LAB = "ink_9um/labels/aligned-scrollprizeorg-21slices"
S = requests.Session()


def list_chunks(case, kind):
    url = f"{HF}/api/buckets/scrollprize/datasets/tree/{LAB}/{case}/{case}_{kind}.zarr/0?recursive=true"
    keys = []
    while url:
        r = S.get(url, timeout=60); r.raise_for_status()
        keys += [x["path"].rsplit("/", 1)[-1] for x in r.json() if x["type"] == "file"]
        m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("link", ""))
        url = m.group(1) if m else None
    return [tuple(int(v) for v in k.split(".")) for k in keys if re.fullmatch(r"\d+\.\d+\.\d+", k)]


def get_json(case, rel):
    return S.get(f"{HF}/buckets/scrollprize/datasets/resolve/{LAB}/{case}/{rel}", timeout=60).json()


def read_label_plane(case, kind, za, keys, ch=10):
    H, W = za["shape"][1:]; cz, cy, cx = za["chunks"]
    codec = numcodecs.get_codec(za["compressor"])
    out = np.zeros((H, W), np.uint8)
    def f(k):
        b = S.get(f"{HF}/buckets/scrollprize/datasets/resolve/{LAB}/{case}/{case}_{kind}.zarr/0/{k[0]}.{k[1]}.{k[2]}", timeout=120).content
        a = np.frombuffer(codec.decode(b), np.uint8).reshape(cz, cy, cx)
        return k, a[ch]
    with cf.ThreadPoolExecutor(4) as ex:
        for (_, y, x), a in ex.map(f, keys):
            ys, xs = y * cy, x * cx
            out[ys:ys + cy, xs:xs + cx] = a[: H - ys, : W - xs]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("case"); ap.add_argument("out"); ap.add_argument("--margin", type=int, default=64); ap.add_argument("--labels-only", action="store_true")
    a = ap.parse_args(); case = a.case
    od = os.path.join(a.out, case); os.makedirs(od, exist_ok=True)
    attrs = get_json(case, f"{case}_inklabels.zarr/.zattrs")
    za = get_json(case, f"{case}_validation_mask.zarr/0/.zarray")
    vkeys = list_chunks(case, "validation_mask")
    val = read_label_plane(case, "validation_mask", za, vkeys)
    ys, xs = np.nonzero(val)
    y0, y1 = max(0, ys.min() - a.margin), min(val.shape[0], ys.max() + 1 + a.margin)
    x0, x1 = max(0, xs.min() - a.margin), min(val.shape[1], xs.max() + 1 + a.margin)
    # read only ink chunks inside the bbox
    cy, cx = za["chunks"][1:]
    ikeys = [k for k in list_chunks(case, "inklabels") if y0 // cy <= k[1] <= (y1 - 1) // cy and x0 // cx <= k[2] <= (x1 - 1) // cx]
    zi = get_json(case, f"{case}_inklabels.zarr/0/.zarray")
    ink = read_label_plane(case, "inklabels", zi, ikeys)
    skeys = [k for k in list_chunks(case, "supervision_mask") if y0 // cy <= k[1] <= (y1 - 1) // cy and x0 // cx <= k[2] <= (x1 - 1) // cx]
    sup = read_label_plane(case, "supervision_mask", get_json(case, f"{case}_supervision_mask.zarr/0/.zarray"), skeys)
    if a.labels_only:
        Image.fromarray(((sup[y0:y1, x0:x1] > 0) * 255).astype(np.uint8)).save(os.path.join(od, "sup.png"))
        Image.fromarray((((val[y0:y1, x0:x1] > 0) & (sup[y0:y1, x0:x1] == 0)) * 255).astype(np.uint8)).save(os.path.join(od, "heldout.png"))
        return
    # source volume crop (uncompressed zarr v2 on S3, level 2)
    src = attrs["source_surface_volume"].rstrip("/") + f"/{attrs['source_surface_volume_level']}"
    sa = S.get(src + "/.zarray", timeout=60).json()
    assert list(sa["shape"][1:]) == list(val.shape), (sa["shape"], val.shape)
    z0, z1 = attrs["source_z_slice"]; scz, scy, scx = sa["chunks"]; sep = sa.get("dimension_separator", ".")
    codec = numcodecs.get_codec(sa["compressor"]) if sa["compressor"] else None
    vol = np.zeros((sa["shape"][0], y1 - y0, x1 - x0), np.uint8)
    jobs = [(zc, yc, xc) for zc in range(0, (sa["shape"][0] + scz - 1) // scz) if zc * scz < z1 and (zc + 1) * scz > z0
            for yc in range(y0 // scy, (y1 - 1) // scy + 1) for xc in range(x0 // scx, (x1 - 1) // scx + 1)]
    def g(k):
        r = S.get(f"{src}/{sep.join(map(str, k))}", timeout=300)
        if r.status_code == 404: return k, None
        b = r.content; b = codec.decode(b) if codec else b
        return k, np.frombuffer(b, np.uint8).reshape(scz, scy, scx)
    with cf.ThreadPoolExecutor(4) as ex:
        for (zc, yc, xc), c in ex.map(g, jobs):
            if c is None: continue
            Z0, Y0, X0 = zc * scz, yc * scy, xc * scx
            ya, yb = max(Y0, y0), min(Y0 + scy, y1); xa, xb = max(X0, x0), min(X0 + scx, x1)
            zb = min(Z0 + scz, sa["shape"][0])
            vol[Z0:zb, ya - y0:yb - y0, xa - x0:xb - x0] = c[: zb - Z0, ya - Y0:yb - Y0, xa - X0:xb - X0]
    v = vol[z0:z1].astype(np.float32)
    v = v.reshape(-1, 4, *v.shape[1:]).mean(1)
    v = np.clip(np.rint(v), 0, 255).astype(np.uint8)
    assert v.shape[0] == attrs["output_channels"], v.shape
    g_ = zarr.open_group(os.path.join(od, "volume.zarr"), mode="w", zarr_format=2)
    g_.create_array("0", data=v, chunks=(v.shape[0], 128, 128))
    Image.fromarray(ink[y0:y1, x0:x1]).save(os.path.join(od, "ink.png"))
    Image.fromarray(((val[y0:y1, x0:x1] > 0) * 255).astype(np.uint8)).save(os.path.join(od, "valid.png"))
    Image.fromarray(((sup[y0:y1, x0:x1] > 0) * 255).astype(np.uint8)).save(os.path.join(od, "sup.png"))
    held = (val[y0:y1, x0:x1] > 0) & (sup[y0:y1, x0:x1] == 0)
    Image.fromarray((held * 255).astype(np.uint8)).save(os.path.join(od, "heldout.png"))
    meta = dict(case=case, bbox_yx=[int(y0), int(y1), int(x0), int(x1)], um=attrs["output_resolution_um_zyx"][1],
                source=src, z_slice=[z0, z1], valid_px=int((val > 0).sum()),
                ink_px_in_valid=int(((ink > 0) & (val > 0)).sum()), heldout_px=int(held.sum()),
                heldout_ink_px=int((held & (ink[y0:y1, x0:x1] > 0)).sum()), shape=list(v.shape))
    json.dump(meta, open(os.path.join(od, "meta.json"), "w"), indent=1); print(json.dumps(meta))


if __name__ == "__main__":
    main()
