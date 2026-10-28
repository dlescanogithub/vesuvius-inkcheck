"""Export the PHerc1203 zone metrics (hires_test/preds/eval/verdict_*.json) into the node-D zone list.

r_other = best Pearson r between this model's forward map and a map from a DIFFERENT checkpoint
(hecate vs dense_native), as the pre-registration requires; same-checkpoint agreement does not count.
Usage: python examples/irp/export_1203.py HIRES_TEST_DIR results/irp/1203_zones.json
"""
import glob, json, os, sys

src, dst = sys.argv[1], sys.argv[2]
CKPT = {"hec_f": "hecate", "hec_r": "hecate", "native_dn": "dn", "dn2_f": "dn", "dn2_r": "dn", "dn9_f": "dn", "dn9_r": "dn"}
AREA = {"1203c": (2048 * 2.403e-4) ** 2}  # cm2; other tiles are 641 px at 9.612 um
zones = []
for p in sorted(glob.glob(os.path.join(src, "preds/eval/verdict_*.json"))):
    for name, z in json.load(open(p)).items():
        area = AREA.get(name, (641 * 9.612e-4) ** 2)
        pr = z.get("pairwise_r", {})
        for mdl in ("hec", "dn2", "dn9"):
            f, r = f"{mdl}_f", f"{mdl}_r"
            if f not in z or r not in z:
                continue
            others = [v for k, v in pr.items() if f in k.split("~")
                      and CKPT[[x for x in k.split("~") if x != f][0]] != CKPT[f]
                      and not [x for x in k.split("~") if x != f][0].endswith("_r")]
            c, cn = z[f]["comps_per_cm2"], z[r]["comps_per_cm2"]
            zones.append(dict(zone=name, model={"hec": "hecate-2.4 native", "dn2": "dense_native @2.4 iso", "dn9": "dense_native @9.6 iso"}[mdl],
                              comps=c, comps_null=cn, n_components=round(c * area, 1),
                              r_other=max(others) if others else None, stroke_width_mm=None,
                              visual_strokes=False, source=os.path.relpath(p, src)))
json.dump(dict(source="hires_test/preds/eval/verdict_*.json (tools/verdict.py)", zones=zones), open(dst, "w"), indent=1)
print(len(zones), "zone/model rows ->", dst)
