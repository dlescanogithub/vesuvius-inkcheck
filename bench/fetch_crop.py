#!/usr/bin/env python
"""Fetch a chunk-aligned crop of level 0 of an open-data surface volume (zarr v2, uncompressed or not).

    python bench/fetch_crop.py <s3 key of the .zarr> <dst.zarr> --yx y0,x0 --hw H,W

Chunks are copied byte-for-byte and renumbered, so the crop is a valid zarr whose (0,0) is canvas pixel
(y0, x0) (both rounded down to the chunk grid; the exact origin is written to crop.json).
Without --yx/--hw the whole level 0 is fetched. Resumable; 4 download threads.
"""
import argparse, concurrent.futures as cf, json, os, urllib.error, urllib.request

B = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"


def get(url, path):
    if os.path.exists(path):
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(5):
        try:
            data = urllib.request.urlopen(url, timeout=90).read()
            with open(path + ".part", "wb") as f:
                f.write(data)
            os.replace(path + ".part", path)
            return len(data)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):        # missing chunk = fill value
                return 0
        except Exception:
            pass
    raise RuntimeError(url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("dst")
    ap.add_argument("--yx", default="0,0"); ap.add_argument("--hw", default="")
    a = ap.parse_args()
    src = B + a.key.rstrip("/") + "/"
    za = json.loads(urllib.request.urlopen(src + "0/.zarray", timeout=60).read())
    Z, Y, X = za["shape"]; cz, cy, cx = za["chunks"]
    sep = za.get("dimension_separator", ".")
    y0, x0 = (int(v) for v in a.yx.split(","))
    H, W = (int(v) for v in a.hw.split(",")) if a.hw else (Y, X)
    i0, j0 = y0 // cy, x0 // cx
    i1, j1 = min((y0 + H + cy - 1) // cy, (Y + cy - 1) // cy), min((x0 + W + cx - 1) // cx, (X + cx - 1) // cx)
    ny, nx = min((i1 - i0) * cy, Y - i0 * cy), min((j1 - j0) * cx, X - j0 * cx)
    os.makedirs(a.dst + "/0", exist_ok=True)
    za2 = dict(za, shape=[Z, ny, nx])
    json.dump(za2, open(a.dst + "/0/.zarray", "w"), indent=1)
    json.dump({"zarr_format": 2}, open(a.dst + "/.zgroup", "w"))
    try:
        get(src + ".zattrs", a.dst + "/.zattrs.src")
    except RuntimeError:
        pass
    json.dump({"source": src, "origin_yx": [i0 * cy, j0 * cx], "shape": [Z, ny, nx], "full_shape": [Z, Y, X]},
              open(a.dst + "/crop.json", "w"), indent=1)
    jobs = []
    for k in range((Z + cz - 1) // cz):
        for i in range(i0, i1):
            for j in range(j0, j1):
                s = sep.join(str(v) for v in (k, i, j)); d = sep.join(str(v) for v in (k, i - i0, j - j0))
                jobs.append((src + "0/" + s, a.dst + "/0/" + d))
    with cf.ThreadPoolExecutor(4) as ex:
        n = sum(ex.map(lambda t: get(*t), jobs))
    print(a.key, "crop origin", (i0 * cy, j0 * cx), "shape", (Z, ny, nx), len(jobs), "chunks", round(n / 1e6), "MB new",
          flush=True)


if __name__ == "__main__":
    main()
