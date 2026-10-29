"""Read official Vesuvius Challenge open-data products directly, by local path, https URL or s3:// URL.

Supported (layout of s3://vesuvius-challenge-open-data, mirrored at https://vesuvius-challenge-open-data.s3.amazonaws.com/):

* ink-detection maps     <scroll>/segments/<seg>/ink-detection/<scroll>-<segts>-<scan>-volume-<volts>-<runts>-<model>-tile<T>-stride<S>.tif
* downsampled previews   <scroll>/segments/<seg>/ink-detection/downsampled/<same stem>-ds<k>.jpg | .png
* surface volumes        <scroll>/segments/<seg>/surface-volumes/<scan>-volume-<volts>.zarr/   (zarr v2, level "0",
                         shape (layers, H, W), chunks (layers, 128, 128); uncompressed or any numcodecs compressor)

Only the standard library, numpy, Pillow and tifffile are needed; compressed zarr chunks additionally need `numcodecs`
(`pip install "vesuvius-inkcheck[zarr]"`). Nothing is written except the download cache of `inkcheck.quick.fetch`.
Data licence: scroll data are CC BY-NC 4.0 (Vesuvius Challenge); this module only reads them.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

BUCKET = "vesuvius-challenge-open-data"
HTTPS = f"https://{BUCKET}.s3.amazonaws.com/"

_PRED_RE = re.compile(
    r"^(?P<scroll>PHerc[0-9A-Za-z]+)-(?P<segment>\d{14})-(?P<scan>[\d.]+um(?:-[\d.]+m)?-[\d.]+keV)-volume-(?P<volume>\d{14})"
    r"(?P<suffix>-L\d+)?-(?P<run>\d{14})-(?P<model>.+?)-tile(?P<tile>\d+)-stride(?P<stride>\d+)(?:-ds(?P<ds>\d+))?\.(?P<ext>tif|tiff|jpg|jpeg|png)$")


def to_url(src: str) -> str:
    """s3://bucket/key -> https URL; a bare bucket key ('PHerc0172/segments/...') -> URL in the open-data bucket;
    http(s) URLs and local paths are returned unchanged."""
    s = str(src)
    if s.startswith("s3://"):
        b, _, k = s[5:].partition("/")
        return f"https://{b}.s3.amazonaws.com/{k}"
    if s.startswith(("http://", "https://")) or os.path.exists(s):
        return s
    if re.match(r"^PHerc[0-9A-Za-z]+/", s):
        return HTTPS + s
    return s


def parse_prediction_name(name: str) -> dict:
    """Parse an official ink-prediction file name. Returns scroll, segment, scan, pixel_um (of the CT scan),
    energy_kev, volume, run, model, tile, stride, ds (1 for full-resolution maps) and map_pixel_um (= pixel_um x ds).
    Raises ValueError for names that do not follow the convention."""
    m = _PRED_RE.match(Path(urllib.parse.urlparse(str(name)).path).name)
    if not m:
        raise ValueError(f"not an official ink-prediction file name: {name}")
    d = m.groupdict()
    um = float(re.match(r"([\d.]+)um", d["scan"]).group(1))
    kev = float(re.search(r"([\d.]+)keV", d["scan"]).group(1))
    ds = int(d["ds"] or 1)
    return dict(scroll=d["scroll"], segment=d["segment"], scan=d["scan"], pixel_um=um, energy_kev=kev, volume=d["volume"],
                volume_suffix=(d["suffix"] or "").lstrip("-") or None, run=d["run"], model=d["model"], tile=int(d["tile"]),
                stride=int(d["stride"]), ds=ds, map_pixel_um=round(um * ds, 6), ext=d["ext"].lower())


def segment_prefix(scroll: str, segment: str) -> str:
    return f"{scroll}/segments/{segment}/"


def downsampled_key(scroll: str, segment_dir: str, stem: str, ds: int = 8, ext: str = "jpg") -> str:
    """Bucket key of the ds-k preview of a full ink map stem (file name without .tif)."""
    return f"{segment_prefix(scroll, segment_dir)}ink-detection/downsampled/{stem}-ds{ds}.{ext}"


def load_prediction(src: str, cache=None, sha: str | None = None, log=lambda *a: None):
    """Load an official ink map (full .tif or downsampled .jpg/.png) from a path, URL or s3:// URL.
    Returns (map as float32 2-D array, metadata dict). Metadata come from the file name when it follows the
    convention (else {}), plus the array shape."""
    from .io import load_map
    from .quick import fetch
    p = fetch(to_url(src), sha, cache, log)
    try:
        meta = parse_prediction_name(str(src))
    except ValueError:
        meta = {}
    a = load_map(p)
    meta.update(shape=list(a.shape), path=str(p))
    return a, meta


# ----------------------------------------------------------------------------------------------- surface volumes
def _read_bytes(base: str, key: str, timeout: float = 120.0):
    """bytes of base/key, or None if it does not exist (404/403 on the bucket = empty chunk)."""
    if base.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(base.rstrip("/") + "/" + key, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            raise
    p = Path(base) / key
    return p.read_bytes() if p.exists() else None


@dataclass
class SurfaceVolume:
    """Lazy reader for an official surface volume (zarr v2 `layers-zarr`). Use `open_surface_volume`."""
    base: str           # URL or local dir of the array (the directory holding .zarray)
    shape: tuple
    chunks: tuple
    dtype: np.dtype
    fill_value: float
    sep: str
    compressor: dict | None
    filters: list | None

    @property
    def layers(self) -> int:
        return self.shape[0]

    def _decode(self, raw: bytes) -> np.ndarray:
        if self.compressor is not None or self.filters:
            try:
                import numcodecs
            except ImportError as e:  # pragma: no cover - depends on the environment
                raise ImportError('this surface volume is compressed; pip install "vesuvius-inkcheck[zarr]" (numcodecs)') from e
            if self.compressor is not None:
                raw = numcodecs.get_codec(self.compressor).decode(raw)
            for f in reversed(self.filters or []):
                raw = numcodecs.get_codec(f).decode(raw)
        return np.frombuffer(bytes(raw), self.dtype).reshape(self.chunks)

    def chunk(self, iz: int, iy: int, ix: int) -> np.ndarray:
        raw = _read_bytes(self.base, self.sep.join(map(str, (iz, iy, ix))))
        if raw is None:
            return np.full(self.chunks, self.fill_value or 0, self.dtype)
        return self._decode(raw)

    def read(self, z: slice = slice(None), y: slice = slice(None), x: slice = slice(None)) -> np.ndarray:
        """Read a (layers, rows, cols) box. Slices must have step 1; out-of-range parts are clipped."""
        sl = [s.indices(n) for s, n in zip((z, y, x), self.shape)]
        if any(st != 1 for _, _, st in sl):
            raise ValueError("only step-1 slices are supported")
        (z0, z1, _), (y0, y1, _), (x0, x1, _) = sl
        out = np.empty((max(0, z1 - z0), max(0, y1 - y0), max(0, x1 - x0)), self.dtype)
        cz, cy, cx = self.chunks
        for iz in range(z0 // cz, (z1 - 1) // cz + 1 if z1 > z0 else 0):
            for iy in range(y0 // cy, (y1 - 1) // cy + 1 if y1 > y0 else 0):
                for ix in range(x0 // cx, (x1 - 1) // cx + 1 if x1 > x0 else 0):
                    b = self.chunk(iz, iy, ix)
                    a0, a1 = max(z0, iz * cz), min(z1, (iz + 1) * cz)
                    b0, b1 = max(y0, iy * cy), min(y1, (iy + 1) * cy)
                    c0, c1 = max(x0, ix * cx), min(x1, (ix + 1) * cx)
                    out[a0 - z0:a1 - z0, b0 - y0:b1 - y0, c0 - x0:c1 - x0] = \
                        b[a0 - iz * cz:a1 - iz * cz, b0 - iy * cy:b1 - iy * cy, c0 - ix * cx:c1 - ix * cx]
        return out

    def centred_window(self, n: int = 17) -> slice:
        """The n centred layers, start (layers - n) // 2 (the window used by inkcheck's node D runs)."""
        s = (self.layers - n) // 2
        return slice(max(0, s), max(0, s) + n)


def open_surface_volume(src: str, level: str = "0") -> SurfaceVolume:
    """Open an official surface volume (`.../surface-volumes/<name>.zarr/`) from a local dir, URL or s3:// URL.
    Accepts the group (reads level `level`) or the array directory itself."""
    base = to_url(str(src)).rstrip("/")
    meta = _read_bytes(base, ".zarray")
    if meta is None:
        base = base + "/" + level
        meta = _read_bytes(base, ".zarray")
    if meta is None:
        raise FileNotFoundError(f"no zarr v2 array at {src} (looked for .zarray and {level}/.zarray)")
    m = json.loads(meta)
    if m.get("zarr_format") != 2:
        raise ValueError(f"expected zarr v2, got {m.get('zarr_format')}")
    if m.get("order", "C") != "C":
        raise ValueError("only C-order arrays are supported")
    return SurfaceVolume(base=base, shape=tuple(m["shape"]), chunks=tuple(m["chunks"]), dtype=np.dtype(m["dtype"]),
                         fill_value=m.get("fill_value") or 0, sep=m.get("dimension_separator", "."),
                         compressor=m.get("compressor"), filters=m.get("filters"))


def ct_intensity_stats(block: np.ndarray) -> dict:
    """Summary of the non-zero voxels of a CT block (8-bit surface volumes): n, mean, median, p3, p97 and the share
    above 128. On the PHerc0172 53 keV export this median is ~150 (bright, flat CT); on 113-116 keV scans 75-111."""
    v = np.asarray(block)
    v = v[v > 0].astype(np.float64)
    if v.size == 0:
        return dict(n=0, mean=None, median=None, p3=None, p97=None, frac_gt128=None)
    p3, med, p97 = np.percentile(v, [3, 50, 97])
    return dict(n=int(v.size), mean=float(v.mean()), median=float(med), p3=float(p3), p97=float(p97),
                frac_gt128=float((v > 128).mean()))


# Same fixed thresholds as scripts/saturation_risk_table.py (set from the PHerc0172 diagnosis before that table was built).
CT_RISK = dict(high_median=130.0, high_frac=0.50, med_median=112.0, med_frac=0.25)


def ct_saturation_level(stats: dict, r: dict = CT_RISK) -> str | None:
    """HIGH / MEDIUM / LOW saturation risk of a CT block from `ct_intensity_stats` (median and share > 128).
    HIGH means a model trained on darker 113-116 keV scans may saturate on this scan: treat a PASS with suspicion and
    run `inkcheck.node_d_v2.saturation_check` on the prediction itself."""
    if stats.get("median") is None:
        return None
    if stats["median"] >= r["high_median"] or stats["frac_gt128"] >= r["high_frac"]:
        return "HIGH"
    if stats["median"] >= r["med_median"] or stats["frac_gt128"] >= r["med_frac"]:
        return "MEDIUM"
    return "LOW"


def list_keys(prefix: str, delimiter: str | None = None, max_keys: int = 1000) -> list[str]:
    """Anonymous S3 ListObjectsV2 on the open-data bucket (network). Returns keys (and common prefixes when a
    delimiter is given)."""
    import xml.etree.ElementTree as ET
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": str(max_keys)}
        if delimiter:
            q["delimiter"] = delimiter
        if token:
            q["continuation-token"] = token
        with urllib.request.urlopen(HTTPS + "?" + urllib.parse.urlencode(q), timeout=60) as r:
            root = ET.fromstring(r.read())
        ns = {"s": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
        f = (lambda t: f"s:{t}") if ns else (lambda t: t)
        out += [e.text for e in root.findall(f"{f('Contents')}/{f('Key')}", ns)]
        out += [e.text for e in root.findall(f"{f('CommonPrefixes')}/{f('Prefix')}", ns)]
        if (root.findtext(f("IsTruncated"), namespaces=ns) or "false") != "true":
            return out
        token = root.findtext(f("NextContinuationToken"), namespaces=ns)


def list_predictions(scroll: str, segment_dir: str, downsampled: bool = True) -> list[str]:
    """Bucket keys of the official ink maps of one segment (network)."""
    p = f"{segment_prefix(scroll, segment_dir)}ink-detection/" + ("downsampled/" if downsampled else "")
    return sorted(k for k in list_keys(p, delimiter="/") if re.search(r"\.(tif|tiff|jpg|jpeg|png)$", k))
