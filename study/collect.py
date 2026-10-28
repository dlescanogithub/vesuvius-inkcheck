"""Collect all inkcheck JSONs of the study into markdown tables + a dose-response plot.

NOTE: the full output contains Paris 4 (PHercParis4) scores, which are under a publication reservation until
2027-06-25. Keep its output private; the shipped results/study/tables.md is the redacted (verdict-only) version and
the public verdict figure is figures/tolerance_curve.png (study/tolerance_curve.py).
"""
import json, glob, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "prize_oct/study/results"; snr = json.load(open(f"{R}/layer_snr.json"))
def row(f):
    d = json.load(open(f)); n = d["numbers"]; mn = n["metric_nulls"]
    return dict(v=d["verdict"], r=n["r_bandpass"], rn=n["r_bandpass_null_mean"], raw=n["r_raw"], auc=n["auc_raw"],
                f1=n["breakeven_f1"], sr=n["stroke_recall"], srn=mn["stroke_recall"]["null_mean"], sp=n["stroke_precision"], ns=n["n_ref_strokes"])
fwhm = {"none": 0, "blur0.5": 11.3, "blur1": 22.6, "blur1.5": 33.9, "blur2": 45.2, "blur3": 67.8}
lines = ["| P4 input variant | XY blur FWHM added (µm) | adj-layer HP corr | r_bp (null) | raw r | AUC | breakeven F1 | stroke recall (null) | stroke prec. | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
var = [("none", "prize_oct/results/paris4_dn_9.6um.json", "P4 ctrl_9.6um")] + [(v, f"{R}/paris4_{v}_dn.json", "P4 " + v) for v in ["blur0.5", "blur1", "blur1.5", "blur2", "blur3", "bin2", "noise_sd16", "noise_sd32", "noise_sd48"]]
pts = []
for v, f, k in var:
    if not os.path.exists(f): continue
    x = row(f); lab = {"none": "original 9.6 µm", "bin2": "2× bin (19.2 µm sampling)"}.get(v, v.replace("noise_sd", "Gaussian noise σ=") if "noise" in v else f"Gaussian σ={v[4:]} px")
    lines.append(f"| {lab} | {fwhm.get(v, '–')} | {snr.get(k, float('nan')):.2f} | {x['r']:.3f} ({x['rn']:.3f}) | {x['raw']:.2f} | {x['auc']:.3f} | {x['f1']:.2f} | {x['sr']:.2f} ({x['srn']:.2f}) | {x['sp']:.2f} | {x['v']} |")
    if v in fwhm: pts.append((fwhm[v], x["r"], x["sr"]))
lines += ["", "| PHerc0343P 20250511003658 input | model | window | r_bp (null) | raw r | AUC | breakeven F1 | stroke recall (null) | stroke prec. | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
for m in ["dn", "kl", "s42", "s43", "soup"]:
    f = f"prize_oct/results/343P_{m}_8.64um.json"
    if os.path.exists(f): x = row(f); lines.append(f"| native 8.64 µm / 116 keV | {m} | 7 | {x['r']:.3f} ({x['rn']:.3f}) | {x['raw']:.2f} | {x['auc']:.3f} | {x['f1']:.2f} | {x['sr']:.2f} ({x['srn']:.2f}) | {x['sp']:.2f} | {x['v']} |")
for f in sorted(glob.glob(f"{R}/343P_from2um_*_w*.json")):
    m, w = os.path.basename(f)[:-5].split("_")[2:4]; x = row(f)
    lines.append(f"| 2.215 µm / 111 keV pooled to 8.86 µm | {m} | {w[1:]} | {x['r']:.3f} ({x['rn']:.3f}) | {x['raw']:.2f} | {x['auc']:.3f} | {x['f1']:.2f} | {x['sr']:.2f} ({x['srn']:.2f}) | {x['sp']:.2f} | {x['v']} |")
open(f"{R}/tables.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
pts.sort(); fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", label="band-pass r"); ax.plot([p[0] for p in pts], [p[2] for p in pts], "s-", label="stroke recall")
d = row("prize_oct/results/343P_dn_8.64um.json"); ax.axhline(d["r"], color="C0", ls=":", label="343P native 8.64 µm: r_bp"); ax.axhline(d["sr"], color="C1", ls=":", label="343P native: stroke recall")
ax.axhline(0.5, color="0.6", lw=0.8); ax.set_xlabel("added XY Gaussian blur on Paris-4 input, FWHM (µm)"); ax.set_ylabel("inkcheck metric (dense_native)")
ax.set_title("Paris 4 held-out: ink signal vs input blur"); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(f"{R}/dose_response.png", dpi=110)
