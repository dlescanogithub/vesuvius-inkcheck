"""Summary statistics of dense_native predictions on unlabelled PHerc0800 / PHerc1203 surfaces
versus the 343P control and the depth-shuffled / reversed nulls (same model, same settings).
Probabilities: p = clip((v/255-0.25)/0.5, 0, 1); valid = v > 0."""
import glob, json, sys
import numpy as np, tifffile
from scipy import ndimage as ndi
sys.path.insert(0, "prize_oct/inkcheck/src")
from inkcheck.metrics import bandpass
from inkcheck.register import pearson

def load(p):
    v = tifffile.imread(p).astype(np.float32)
    m = v > 0
    return np.clip((v / 255 - 0.25) / 0.5, 0, 1), m

def stats(p, m, um=8.64):
    x = p[m]
    bp = bandpass(p, m, um, 0, 500)
    # structure: fraction of valid area covered by confident blobs >= 0.02 mm2
    lab, n = ndi.label((p > 0.5) & m)
    area = np.bincount(lab.ravel())[1:] * um * um / 1e6
    return {"area_cm2": float(m.sum() * um * um / 1e8), "mean_p": float(x.mean()),
            "frac_p>0.5": float((x > 0.5).mean()), "frac_p>0.8": float((x > 0.8).mean()),
            "p99": float(np.percentile(x, 99)), "bp_sd": float(bp[m].std()),
            "blobs>=0.02mm2_per_cm2": float((area >= 0.02).sum() / (m.sum() * um * um / 1e8))}

rows = {}
rows["343P_ctrl dn (known ink)"] = stats(*load("preds/343P_ctrl/dn_w7_forward.tif"))
for f in sorted(glob.glob("preds/PHerc0800/*/dn_w7_forward.tif")) + sorted(glob.glob("preds/PHerc1203/*/dn_w7_forward.tif")):
    rows[f.split("/")[1] + " " + f.split("/")[2].replace("auto_grown_", "")] = stats(*load(f))
fw, m1 = load("preds/PHerc0800/auto_grown_20251028222030940/dn_w7_forward.tif")
sh, m2 = load("preds/null_shuf_0800_222030/dn_w7_forward.tif")
rv, m3 = load(glob.glob("preds/null_rev_0800_222030/*.tif")[0])
rows["NULL 0800 222030 depth-shuffled"] = stats(sh, m2)
rows["NULL 0800 222030 reversed"] = stats(rv, m3)
m = m1 & m2 & m3
b = {k: bandpass(a, m, 8.64, 0, 500) for k, a in (("fw", fw), ("sh", sh), ("rv", rv))}
pair = {"r_bp(forward, shuffled)": pearson(b["fw"], b["sh"], m), "r_bp(forward, reversed)": pearson(b["fw"], b["rv"], m),
        "r_raw(forward, shuffled)": pearson(fw, sh, m), "r_raw(forward, reversed)": pearson(fw, rv, m)}
json.dump({"rows": rows, "pairs_0800_222030": pair}, open("prize_oct/results/scan_stats.json", "w"), indent=1)
print(f"{'map':45s} {'cm2':>6s} {'mean_p':>7s} {'p>0.5':>7s} {'p>0.8':>7s} {'p99':>5s} {'bp_sd':>6s} {'blobs/cm2':>9s}")
for k, r in rows.items():
    print(f"{k:45s} {r['area_cm2']:6.2f} {r['mean_p']:7.3f} {r['frac_p>0.5']:7.4f} {r['frac_p>0.8']:7.4f} {r['p99']:5.2f} {r['bp_sd']:6.3f} {r['blobs>=0.02mm2_per_cm2']:9.1f}")
print(pair)
