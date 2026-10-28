"""ScrollGT's primary metric (AP-prevalence-lift) for every prediction in results/scrollgt/preds/ against the
ScrollGT label crop. Writes results/scrollgt/ap_lift.json. numpy-only (inkcheck.scrollgt), CPU, a few seconds.

Usage: python examples/scrollgt/ap_lift.py [results/scrollgt]
Caveats (printed into the JSON): our scores are on a 2048² chunk-aligned sub-crop of ScrollGT's 4096² flagship region,
not the full target, so they are not directly comparable with BASELINES.md; ScrollGT's stated ~0.31 mm (32 level-2 px)
placement uncertainty for this target makes every score a lower bound; both ScrollGT Paris 4 segments are in the training configs of
the checkpoints scored here (phercparis4-w06 = 20231210121321), so these numbers are train-exposed.
"""
import glob, json, os, sys
import numpy as np, tifffile
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from inkcheck import scrollgt as S

d = sys.argv[1] if len(sys.argv) > 1 else "results/scrollgt"
gt = np.asarray(Image.open(os.path.join(d, "gt_crop.png"))) > 127
crop = json.load(open(os.path.join(d, "crop.json")))
out = {"target": "scroll1_20231210121321 (ScrollGT v0.9.1, commit 0f3fa90, MIT)", "crop": crop,
       "exposure": "TRAIN-EXPOSED: 20231210121321 = ink_9um phercparis4-w06, listed in the training configs of rv3/s42/dn",
       "caveats": ["2048² sub-crop of the 4096² ScrollGT region: not directly comparable with ScrollGT BASELINES.md",
                   "ScrollGT placement uncertainty ~0.31 mm (32 level-2 px) for this target: scores are lower bounds",
                   "AP/ROC-AUC on a deterministic 4M-pixel subsample (inkcheck.scrollgt)"],
       "floors": {"all_positive_lift": 1.0, "oracle_lift": round(1 / float(gt.mean()), 3)}, "models": {}}
for f in sorted(glob.glob(os.path.join(d, "preds", "*.tif"))):
    k = os.path.basename(f).rsplit("__", 1)[-1][:-4]
    p = tifffile.imread(f).astype(np.float32)
    if p.shape != gt.shape:
        print("skip", f, p.shape); continue
    m = S.ap_prevalence_lift(p, gt)
    rec = {"as_placed": {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in m.items()}}
    # also at the residual offset inkcheck's registration search found (same score JSON); the sign convention is
    # resolved by keeping whichever of +/- shift gives the higher Pearson r, which is what the search maximised
    sj = os.path.join(d, os.path.basename(f)[:-4] + ".json")
    if os.path.exists(sj):
        su = json.load(open(sj))["numbers"]["shift_um"]; dy, dx = (int(round(v / 9.6)) for v in su)
        best = None
        for sg in (1, -1):
            a, b = sg * dy, sg * dx
            P = p[max(a, 0):p.shape[0] + min(a, 0), max(b, 0):p.shape[1] + min(b, 0)]
            G = gt[max(-a, 0):gt.shape[0] + min(-a, 0), max(-b, 0):gt.shape[1] + min(-b, 0)]
            r = float(np.corrcoef(P.ravel()[::7], G.ravel()[::7].astype(np.float32))[0, 1])
            if best is None or r > best[0]:
                best = (r, a, b, P, G)
        mm = S.ap_prevalence_lift(best[3], best[4])
        rec["at_inkcheck_shift"] = dict({kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in mm.items()},
                                        shift_px_yx=[best[1], best[2]], shift_um=su,
                                        shift_mm=round(float(np.hypot(*su)) / 1000, 3))
    out["models"][k] = rec
    print(k, out["models"][k])
json.dump(out, open(os.path.join(d, "ap_lift.json"), "w"), indent=1)
