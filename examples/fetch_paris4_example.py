"""Rebuild the Paris 4 worked example from public sources (no scroll data is stored in this repo).

Step 1 (default, ~4 MB, seconds): the published new_canon ink map of PHercParis4 segment 20231005123336
(ds8, 19.2 um) is downloaded from the Vesuvius Challenge open-data bucket and cropped to
examples/data/paris4_ref_crop_19.2um.png.

Step 2 (--with-pred, ~260 MB of scan + 273 MB of weights, several CPU minutes): the 9.6 um input crop is
rebuilt from level 2 of the segment's 2.4 um surface volume (layers 1-108 mean-pooled 4x in depth, rows
1024-2559, cols 3072-4607), Erwin Nieuwlaar's dense_native_016000 weights are downloaded from Hugging Face,
and villa's ink inference CLI writes examples/data/paris4_dn_pred_9.6um.png. Needs a villa checkout
(https://github.com/ScrollPrize/villa, `vesuvius` package) and torch: set VILLA_PY to that Python, and
VILLA_SRC to villa/vesuvius/src if the package is not installed.

Data terms: the scan and ink maps are Vesuvius Challenge data (CC BY-NC 4.0 with additional terms; Paris 4 is
also under a publication reservation until 2027-06-25). See https://scrollprize.org/data and
https://scrollprize.org/data_browser/PHercParis4. Fetch them yourself; do not commit them.

    python examples/fetch_paris4_example.py               # reference only
    VILLA_PY=/path/to/python VILLA_SRC=/path/to/villa/vesuvius/src python examples/fetch_paris4_example.py --with-pred
"""
import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/20231005123336"
REF_URL = (BUCKET + "/ink-detection/downsampled/PHercParis4-20231005123336-2.4um-0.22m-78keV-volume-"
           "20260411134726-20260417190342-new_canon_autoresearch_recipe-tile256-stride128-ds8.jpg")
VOL_URL = BUCKET + "/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr/2"
CKPT_URL = "https://huggingface.co/Nieuwlaar/ink9um-dense-native/resolve/main/weights/dense_native_016000.safetensors"
REF_CROP = (slice(256, 1536), slice(1280, 2560))      # ds8 pixels; the prediction starts at ds8 (512, 1536)
VOL_Y, VOL_X, CH = 1024, 3072, 128                     # level-2 (9.6 um) pixels; 12 x 12 chunks of 128
# sha256 of the decoded uint8 pixels of the files behind the shipped Paris 4 verdict
SHA = {"paris4_ref_crop_19.2um.png": "6021805fc23fa42bfd0a17ba0076635443a9ca27047257ab18eced9855d36703",
       "paris4_dn_pred_9.6um.png": "98f0c52acb629cead043d47da56a2159b9c778011f13b586e05da2f58c145eae"}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise


def sha(p):
    return hashlib.sha256(np.ascontiguousarray(np.array(Image.open(p))).tobytes()).hexdigest()


def check(p):
    ok = sha(p) == SHA[p.name]
    print(f"{p.name}: {'pixels identical to the file behind the shipped Paris 4 verdict' if ok else 'pixels differ from the README file (CPU/GPU or library differences; still usable)'}")


def fetch_ref():
    a = np.array(Image.open(io.BytesIO(get(REF_URL))).convert("L"))
    out = DATA / "paris4_ref_crop_19.2um.png"
    Image.fromarray(a[REF_CROP]).save(out)
    check(out)


def fetch_volume(work):
    zdir = work / "p4_ctrl_9.6um.zarr" / "0"
    zdir.mkdir(parents=True, exist_ok=True)
    (work / "p4_ctrl_9.6um.zarr" / ".zgroup").write_text('{"zarr_format": 2}')
    (work / "p4_ctrl_9.6um.zarr" / ".zattrs").write_text(json.dumps({"multiscales": [{"version": "0.4", "datasets": [{"path": "0"}]}]}))
    (zdir / ".zarray").write_text(json.dumps({"zarr_format": 2, "shape": [27, 1536, 1536], "chunks": [27, CH, CH],
                                              "dtype": "|u1", "compressor": None, "fill_value": 0, "order": "C",
                                              "filters": None, "dimension_separator": "/"}))

    def one(ij):
        i, j = ij
        dst = zdir / "0" / str(i) / str(j)
        if dst.exists():
            return
        raw = np.frombuffer(get(f"{VOL_URL}/0/{VOL_Y // CH + i}/{VOL_X // CH + j}"), np.uint8).reshape(109, CH, CH)
        pooled = np.round(raw[1:109].astype(np.float32).reshape(27, 4, CH, CH).mean(1)).astype(np.uint8)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(pooled.tobytes())

    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(one, [(i, j) for i in range(12) for j in range(12)]))
    return zdir.parent


def fetch_ckpt(work, py):
    pth = work / "dense_native_016000.pth"
    if not pth.exists():
        st = work / "dense_native_016000.safetensors"
        if not st.exists():
            st.write_bytes(get(CKPT_URL))
        code = ("import json,sys,torch; from safetensors.torch import load_file; "
                "torch.save({'model': load_file(sys.argv[1]), 'config': json.load(open(sys.argv[2])), 'step': 0}, sys.argv[3])")
        subprocess.run([py, "-c", code, str(st), str(HERE / "paris4" / "dense_native_016000.config.json"), str(pth)], check=True)
    return pth


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-pred", action="store_true", help="also rebuild the dense_native prediction (slow)")
    ap.add_argument("--work", default=str(HERE / "paris4" / "work"), help="download/cache directory")
    a = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    fetch_ref()
    if not a.with_pred:
        print("reference done; add --with-pred to rebuild the prediction as well")
        return
    py = os.environ.get("VILLA_PY")
    if not py:
        sys.exit("set VILLA_PY to a Python with villa's `vesuvius` package and torch installed")
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    vol = fetch_volume(work)
    ckpt = fetch_ckpt(work, py)
    tif = work / "p4_dn_9.6um.tif"
    env = dict(os.environ)
    if os.environ.get("VILLA_SRC"):
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [os.environ["VILLA_SRC"], env.get("PYTHONPATH")]))
    subprocess.run([py, "-m", "vesuvius.ink_detection.inference.infer", str(vol), str(ckpt), str(tif),
                    "--layer-start", "5", "--layer-end", "22", "--direction", "forward", "--no-compile",
                    "--num-workers", "1"], check=True, env=env)
    out = DATA / "paris4_dn_pred_9.6um.png"
    import tifffile
    Image.fromarray(tifffile.imread(tif)).save(out)
    check(out)


if __name__ == "__main__":
    main()
