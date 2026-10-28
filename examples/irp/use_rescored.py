"""Point every case file at the re-scored result (same settings and seed, plus tile-bootstrap CIs) where one exists.

results/rescore/<group>/<name>.json re-runs inkcheck on the same prediction/reference as results/<group>/<name>.json;
the point estimates are identical, only the 'bootstrap' block is added. Run: python examples/irp/use_rescored.py
"""
import glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def swap(obj, changed):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "json" and isinstance(v, str) and v.startswith("../../results/") and "/rescore/" not in v:
                new = v.replace("../../results/", "../../results/rescore/", 1)
                if os.path.exists(os.path.join(HERE, new)):
                    old_n = json.load(open(os.path.join(HERE, v)))["numbers"]["r_bandpass"]
                    new_n = json.load(open(os.path.join(HERE, new)))["numbers"]["r_bandpass"]
                    assert abs(old_n - new_n) < 1e-6, (v, old_n, new_n)
                    obj[k] = new; changed.append(new)
            else:
                swap(v, changed)
    elif isinstance(obj, list):
        for v in obj: swap(v, changed)


for f in sorted(glob.glob(os.path.join(HERE, "*.case.json"))):
    c = json.load(open(f)); ch = []; swap(c, ch)
    if ch:
        json.dump(c, open(f, "w"), indent=1, ensure_ascii=False); open(f, "a").write("\n")
    print(os.path.basename(f), len(ch), "paths swapped")
