#!/usr/bin/env python3
"""Saturation risk table for public Vesuvius Challenge scans (CPU only, small HTTP reads).

Background: results/irp/node_d_faceonly/f1/DIAG_0172.md. On the PHerc0172 53 keV scan the surface-volume CT is
brighter and flatter than on the 113-116 keV scans (window mean 154 vs 75-111), and Reader V3 saturates on it.
This script asks, for every public scan in the open-data metadata: is the CT input closer to 0172 or to the
113-116 keV scans?

Stages (all read-only, public bucket s3://vesuvius-challenge-open-data, anonymous HTTPS):
  1. metadata  - every scan in metadata.json: energy, pixel size, detector distance, volumes, #segments.
  2. surface   - per volume with public surface volumes (layers-zarr): up to N_SEG segments, up to N_CHUNK
                 non-empty 128x128 chunks each; stats over non-zero pixels of the middle half of the layers
                 (the same kind of window as DIAG_0172 section 1).
  3. volume    - per public volume: up to N_VCHUNK non-empty 128^3 chunks near the centre of a coarse pyramid
                 level; stats over non-zero voxels. Coarser and less comparable than stage 2 (see RISK_TABLE.md).
  4. preds     - per volume with official downsampled ink predictions (ds8 JPG): up to N_PRED maps per model,
                 inkcheck.node_d_v2.saturation_check on pixels >= 3. These describe the OFFICIAL models only.
Nothing derived from scroll data except summary numbers is written. No images are saved.

Withheld by policy: PHercParis4 is metadata-only (publication reservation; see cards/). Rows say so.

Usage: python scripts/saturation_risk_table.py --cache /path/to/cache --out results/saturation_risk
"""
import argparse, concurrent.futures as cf, csv, hashlib, io, json, os, re, sys, time, urllib.error, urllib.request

import numpy as np

BASE = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
WITHHELD = {"PHercParis4": "not measured: publication reservation"}
N_SEG, N_CHUNK, N_VCHUNK, N_PRED = 3, 10, 6, 3

# Thresholds fixed from DIAG_0172 before this table was measured (CT 8-bit, non-zero pixels).
# 0172 surface window: mean 154 +- 26, p3-p97 114-206.  113-116 keV segments: mean 75-111.
RISK = dict(high_median=130.0, high_frac=0.50, med_median=112.0, med_frac=0.25,
            low_kev=60.0, ref_kev=(105.0, 120.0))


# ----------------------------------------------------------------------------- pure helpers (unit tested)
def parse_long_id(long_id):
    """'20250720065842-9.362um-1.2m-113keV' -> dict(pixel_um=9.362, distance_m=1.2, energy_kev=113.0)."""
    um = re.search(r"([\d.]+)um", long_id or ""); m = re.search(r"-([\d.]+)m(?:-|$)", long_id or "")
    kev = re.search(r"([\d.]+)keV", long_id or "")
    return dict(pixel_um=float(um.group(1)) if um else None, distance_m=float(m.group(1)) if m else None,
                energy_kev=float(kev.group(1)) if kev else None)


def intensity_stats(v):
    """Summary of a 1-D array of non-zero uint8 CT values (plain floats, JSON safe)."""
    v = np.asarray(v, dtype=np.float64)
    if v.size == 0:
        return dict(n=0, mean=None, sd=None, median=None, p3=None, p97=None, frac_gt128=None)
    p3, med, p97 = np.percentile(v, [3, 50, 97])
    return dict(n=int(v.size), mean=float(v.mean()), sd=float(v.std()), median=float(med), p3=float(p3),
                p97=float(p97), frac_gt128=float((v > 128).mean()))


def measured_level(median, frac, r=RISK):
    if median is None:
        return None
    if median >= r["high_median"] or frac >= r["high_frac"]:
        return "HIGH"
    if median >= r["med_median"] or frac >= r["med_frac"]:
        return "MEDIUM"
    return "LOW"


def metadata_level(kev, r=RISK):
    if kev is None:
        return "UNKNOWN"
    if kev <= r["low_kev"]:
        return "HIGH"
    if r["ref_kev"][0] <= kev <= r["ref_kev"][1]:
        return "LOW"
    return "MEDIUM"


def final_level(meta, surface, volume=None):
    """Surface-volume measurement wins, then the coarse raw-volume measurement (weaker proxy: it includes gaps
    between sheets and is block-averaged), then energy metadata."""
    if surface:
        return surface, "measured (surface volume)"
    if volume:
        return volume, "measured (raw volume, coarse)"
    return meta, "metadata only"


# ----------------------------------------------------------------------------- IO
def _get(url, cache=None, tries=4):
    if cache and os.path.exists(cache):
        return open(cache, "rb").read()
    for t in range(tries):
        try:
            b = urllib.request.urlopen(url, timeout=120).read()
            if cache:
                os.makedirs(os.path.dirname(cache), exist_ok=True)
                open(cache + ".part", "wb").write(b); os.replace(cache + ".part", cache)
            return b
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
        except Exception:
            time.sleep(1 + t)
    return None


def _json(url):
    b = _get(url)
    return json.loads(b) if b else None


def _rng(key):
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8], 16))


def load_metadata(cache):
    p = os.path.join(cache, "metadata.json")
    if not os.path.exists(p):
        import gzip
        b = _get(BASE + "metadata.json")
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        open(p, "wb").write(b)
    return json.load(open(p))


def _window(v):
    md = (v.get("creation") or {}).get("metadata") or {}
    if md.get("window_mode") == "f32":
        return "f32 [%s, %s]" % (md.get("target_window_f32_min"), md.get("target_window_f32_max"))
    if md.get("window_mode") == "u16":
        return "u16 [%s, %s]" % (md.get("window_u16_min"), md.get("window_u16_max"))
    return ""


def _volume_url(v):
    """Full HTTPS URL of a volume's OME-Zarr root (open-data bucket, or the https access root listed for it)."""
    if not v or not v.get("data"):
        return None
    o = v["data"][0]["origins"][0]
    for root in o.get("access_roots") or []:
        if root.get("type") == "https" and root.get("url"):
            return root["url"].rstrip("/") + "/" + o["path"]
    return BASE + o["path"]


def index(meta):
    """One row per public volume export (8-bit windowing is per export), plus scans that have no volume."""
    rows = []
    for sid, s in sorted(meta["samples"].items()):
        vols, segs, scans = s.get("volumes") or {}, s.get("segments") or {}, s.get("scans") or {}
        per_vol = {}
        for g in segs.values():
            for d in g.get("data") or []:
                tv = (d.get("parameters") or {}).get("target_volume")
                path = d["origins"][0]["path"] if d.get("origins") else None
                if tv is None or path is None:
                    continue
                e = per_vol.setdefault(tv, dict(layers=[], preds=[]))
                if d["type"] == "layers-zarr":
                    e["layers"].append((g["id"], path))
                elif d["type"] == "ink-detection-downsampled":
                    e["preds"].append((g["id"], (d.get("parameters") or {}).get("model_id"), path))
        items = [(scans.get(v.get("scan_id")) or {}, v) for v in vols.values()]
        items += [(sc, None) for sc in scans.values() if not any(v.get("scan_id") == sc["id"] for v in vols.values())]
        for sc, v in sorted(items, key=lambda t: ((t[0].get("long_id") or ""), (t[1] or {}).get("id") or "")):
            p = sc.get("properties") or {}; li = parse_long_id(sc.get("long_id") or (v or {}).get("long_id"))
            vp = (v or {}).get("properties") or {}
            vid = (v or {}).get("id")
            e = per_vol.get(vid, dict(layers=[], preds=[])) if vid else dict(layers=[], preds=[])
            rows.append(dict(
                sample=sid, scan=sc.get("long_id") or "", volume_id=vid or "", volume_long_id=(v or {}).get("long_id") or "",
                energy_kev=p.get("energy_keV") or vp.get("energy_keV") or li["energy_kev"],
                pixel_um=p.get("pixel_size_um") or vp.get("pixel_size_um") or li["pixel_um"],
                distance_m=(p["detector_distance_mm"] / 1000.0) if p.get("detector_distance_mm") else li["distance_m"],
                window=_window(v) if v else "",
                volume_path=_volume_url(v),
                layers=sorted(set(e["layers"])), preds=sorted(set(e["preds"]), key=str)))
    return rows


def _spread(items, k):
    items = list(items)
    if len(items) <= k:
        return items
    return [items[int(round(i * (len(items) - 1) / (k - 1)))] for i in range(k)] if k > 1 else items[:1]


def _decoder(za):
    c = za.get("compressor")
    if c is None:
        return lambda b: b
    try:
        import numcodecs
    except ImportError:
        return None
    codec = numcodecs.get_codec(c)
    return lambda b: codec.decode(b)


def surface_stats(path, n_chunk=N_CHUNK, max_try=80):
    za = _json(BASE + path + "0/.zarray")
    if not za:
        return None
    D, H, W = za["shape"]; c = za["chunks"]
    dec = _decoder(za)
    if dec is None or c[0] != D:
        return dict(error="unsupported layout (needs numcodecs)")
    lo, hi = D // 4, max(D // 4 + 1, (3 * D) // 4)
    rng = _rng(path); vals = []; got = 0; tried = 0
    ny, nx = -(-H // c[1]), -(-W // c[2])
    cand = [(int(rng.integers(ny)), int(rng.integers(nx))) for _ in range(max_try)]
    for yi, xi in cand:
        tried += 1
        b = _get(f"{BASE}{path}0/0/{yi}/{xi}")
        b = dec(b) if b is not None else None
        if b is None or len(b) != D * c[1] * c[2]:
            continue
        a = np.frombuffer(b, np.uint8).reshape(D, c[1], c[2])[lo:hi]
        nz = a[a > 0]
        if nz.size < 0.3 * a.size:
            continue
        vals.append(nz[:: max(1, nz.size // 20000)]); got += 1
        if got >= n_chunk:
            break
    st = intensity_stats(np.concatenate(vals) if vals else [])
    st.update(chunks=got, tried=tried, layers=f"{lo}-{hi - 1} of {D}")
    return st


def volume_stats(url, n_chunk=N_VCHUNK):
    """url: full URL of the OME-Zarr root (ending in '/')."""
    path, BASE = url, ""  # noqa: N806 - reuse the f-strings below with an absolute URL
    za0 = _json(BASE + path + ".zattrs")
    if not za0:
        return None
    levels = [d["path"] for d in za0["multiscales"][0]["datasets"]]
    best = None
    for lv in levels:
        za = _json(BASE + path + lv + "/.zarray")
        if za and max(za["shape"]) <= 1600:
            best = (lv, za); break
    if best is None:
        lv = levels[-1]; best = (lv, _json(BASE + path + lv + "/.zarray"))
    lv, za = best
    dec = _decoder(za) if za else None
    if dec is None:
        return dict(error="unsupported layout (needs numcodecs)")
    sh, c = za["shape"], za["chunks"]; n = [-(-s // k) for s, k in zip(sh, c)]
    cen = [x // 2 for x in n]; rng = _rng(path)
    cand = [tuple(int(np.clip(cen[i] + rng.integers(-max(1, n[i] // 4), max(1, n[i] // 4) + 1), 0, n[i] - 1))
                  for i in range(3)) for _ in range(40)]
    cand = list(dict.fromkeys(cand)); vals = []; got = 0
    for z, y, x in cand:
        b = _get(f"{BASE}{path}{lv}/{z}/{y}/{x}")
        if b is None:
            continue
        a = np.frombuffer(dec(b), np.uint8)
        nz = a[a > 0]
        if nz.size < 0.2 * a.size:
            continue
        vals.append(nz[:: max(1, nz.size // 50000)]); got += 1
        if got >= n_chunk:
            break
    st = intensity_stats(np.concatenate(vals) if vals else [])
    st.update(level=lv, chunks=got)
    return st


def pred_stats(path, cache):
    from PIL import Image
    from inkcheck.node_d_v2 import saturation_check
    b = _get(BASE + path, cache=os.path.join(cache, "preds", hashlib.sha1(path.encode()).hexdigest() + ".jpg"))
    if not b:
        return None
    a = np.asarray(Image.open(io.BytesIO(b)).convert("L"))
    r = saturation_check(a, a >= 3)
    r["shape"] = list(a.shape)
    return r


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", default=os.environ.get("SATRISK_CACHE", "./satrisk_cache"))
    ap.add_argument("--out", default="results/saturation_risk")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--skip-volume", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.cache, exist_ok=True); os.makedirs(a.out, exist_ok=True)
    rows = index(load_metadata(a.cache))
    t0 = time.time()

    def work(r):
        r = dict(r); w = WITHHELD.get(r["sample"])
        r["withheld"] = w
        r["surface"], r["volume"], r["pred"] = [], None, []
        if w:
            r["window"] = ""  # withheld: no export details beyond energy and pixel size
            return r
        by_seg = {}
        for sid, p in r["layers"]:
            by_seg.setdefault(sid, p)
        for sid in _spread(sorted(by_seg), N_SEG):
            s = surface_stats(by_seg[sid])
            if s and s.get("n"):
                s["segment"] = sid; r["surface"].append(s)
        if not a.skip_volume and r["volume_path"]:
            r["volume"] = volume_stats(r["volume_path"])
        by_model = {}
        for sid, mid, p in r["preds"]:
            by_model.setdefault(mid, []).append((sid, p))
        for mid, L in sorted(by_model.items(), key=lambda kv: str(kv[0])):
            for sid, p in _spread(sorted(L), N_PRED):
                s = pred_stats(p, a.cache)
                if s:
                    s.update(segment=sid, model_id=mid); r["pred"].append(s)
        return r

    out = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(work, rows):
            out.append(r)
            print(f"[{time.time() - t0:6.0f}s] {r['sample']:<12} {r['volume_id']:<15} {r['scan']:<38} surf={len(r['surface'])} "
                  f"vol={'y' if r['volume'] and r['volume'].get('n') else 'n'} pred={len(r['pred'])}", flush=True)

    table = []
    for r in out:
        sf = [s for s in r["surface"] if s.get("n")]
        if sf:
            pooled_med = float(np.median([s["median"] for s in sf]))
            pooled_frac = float(np.median([s["frac_gt128"] for s in sf]))
        else:
            pooled_med = pooled_frac = None
        v = r["volume"] if r["volume"] and r["volume"].get("n") else None
        ml = metadata_level(r["energy_kev"])
        sl = measured_level(pooled_med, pooled_frac)
        vl = measured_level(v["median"], v["frac_gt128"]) if v else None
        lvl, basis = final_level(ml, sl, vl)
        if r["withheld"]:
            basis = "metadata only (" + r["withheld"] + ")"
        preds = r["pred"]
        models = sorted({str(p["model_id"]) for p in preds})
        table.append(dict(
            sample=r["sample"], scan=r["scan"], volume_id=r["volume_id"], energy_kev=r["energy_kev"],
            pixel_um=r["pixel_um"], distance_m=r["distance_m"], u8_window="" if r["withheld"] else r["window"], n_public_surface_volumes=len({s for s, _ in r["layers"]}),
            n_official_pred_maps=len(r["preds"]), risk=lvl, basis=basis, energy_risk=ml,
            surface_segments_measured=len(sf),
            surface_median=_r(pooled_med), surface_frac_gt128=_r(pooled_frac, 3),
            surface_median_range=(f"{min(s['median'] for s in sf):.0f}-{max(s['median'] for s in sf):.0f}" if sf else ""),
            surface_mean=_r(float(np.median([s['mean'] for s in sf]))) if sf else None,
            surface_risk=sl or "",
            volume_level=(v or {}).get("level", ""), volume_median=_r((v or {}).get("median")),
            volume_frac_gt128=_r((v or {}).get("frac_gt128"), 3), volume_risk=vl or "",
            pred_maps_checked=len(preds), pred_maps_saturated=sum(p["saturated"] for p in preds),
            pred_frac_gt128_max=_r(max((p["frac_high"] for p in preds), default=None), 3),
            pred_models=";".join(models)))
    json.dump(out, open(os.path.join(a.out, "raw_stats.json"), "w"), indent=1, default=str)
    with open(os.path.join(a.out, "risk_table.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0])); w.writeheader(); w.writerows(table)
    print(f"done in {time.time() - t0:.0f}s, {len(table)} scans", flush=True)


def _r(x, nd=1):
    return None if x is None else round(float(x), nd)


if __name__ == "__main__":
    sys.exit(main())
