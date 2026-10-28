"""Compare reference-ink geometry of Paris 4 vs PHerc0343P on a common 19.2 um grid (box-downsampled,
Otsu threshold, components >= 0.02 mm2): ink fraction, stroke count/cm2, median stroke area, and median
stroke width (2 x max inscribed radius from the distance transform)."""
import sys, glob, json, numpy as np
from scipy import ndimage as ndi
from PIL import Image
sys.path.insert(0, "prize_oct/inkcheck/src")
from inkcheck.io import load_map; from inkcheck.metrics import otsu_threshold
Image.MAX_IMAGE_PIXELS = None
def geo(ref, valid, um):
    t = otsu_threshold(ref[valid]); b = (ref > t) & valid
    lab, n = ndi.label(b); area = np.bincount(lab.ravel())[1:] * um * um / 1e6; keep = np.where(area >= 0.02)[0] + 1
    dt = ndi.distance_transform_edt(b) * um; w = ndi.maximum(dt, lab, keep) * 2
    cm2 = valid.sum() * um * um / 1e8
    return dict(ink_frac=float(b[valid].mean()), strokes_per_cm2=float(len(keep) / cm2), median_area_mm2=float(np.median(area[keep - 1])),
                median_width_um=float(np.median(w)), p25_width_um=float(np.percentile(w, 25)))
out = {}
p4 = load_map("control/p4_ref_ds8.jpg")[512:512 + 768, 1536:1536 + 768]; out["Paris4 (19.2um ref crop)"] = geo(p4, np.ones_like(p4, bool), 19.2)
r = load_map(glob.glob("data_raw/PHerc0343P/segments/20250511003658-tifxyz/ink-detection/*new_canon*.tif")[0])
H, W = (r.shape[0] // 8.668) , None
f = 19.2 / 2.215; img = Image.fromarray(r.astype(np.float32)).resize((int(r.shape[1] / f), int(r.shape[0] / f)), Image.BOX); r19 = np.asarray(img)
m = np.asarray(Image.open("prize_oct/results/343P_mask_layer15.png").convert("L").resize(r19.shape[::-1], Image.NEAREST)) > 0
out["343P (2.215um ref, box to 19.2um)"] = geo(r19, m, 19.2)
for k, v in out.items(): print(k, {a: round(b, 3) for a, b in v.items()})
json.dump(out, open("prize_oct/study/results/stroke_geometry.json", "w"), indent=1)
