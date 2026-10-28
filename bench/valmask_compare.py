"""Compare inkcheck AUC on the ink_9um held-out validation masks with published per-checkpoint AUCs.

Usage: python bench/valmask_compare.py RESULTS_DIR [--readme README.md]
Reads RESULTS_DIR/<segment>__<tag>.json (written by bench/score.py) and prints a Markdown table;
with --readme, replaces the <!-- VALMASK_ROWS --> ... <!-- /VALMASK_ROWS --> block.
"""
import argparse, glob, json, os, re

# Published held-out AUCs (same validation masks). Sources:
#  s42/soup: Erwin Nieuwlaar's soup README, "On the official validation masks" (released s42-75k, soup42; single window)
#  kl-*: DomRusso2/ink9um-dense README, Results table (BA / AUC; AUC used)
PUBLISHED = {
    ("pherc0139-w016", "s42"): 0.7740, ("pherc0814-46527", "s42"): 0.8744, ("pherc1667-w029", "s42"): 0.8702,
    ("pherc0139-w016", "soup"): 0.8359, ("pherc0814-46527", "soup"): 0.8810, ("pherc1667-w029", "soup"): 0.8933,
    ("pherc0139-w016", "kl-all7"): 0.8962, ("pherc0814-46527", "kl-all7"): 0.9350, ("pherc1667-w029", "kl-all7"): 0.9044,
    ("pherc0139-w016", "kl-w016ex"): 0.9070, ("pherc0814-46527", "kl-w016ex"): 0.9298, ("pherc1667-w029", "kl-w016ex"): 0.8853,
}
NAMES = {"s42": "ink_9um seed42 75k", "s43": "ink_9um seed43 75k", "soup": "Erwin soup42_last4",
         "dn": "Erwin dense_native 16k", "kl-all7": "dense9um all7", "kl-w016ex": "dense9um w016-excluded"}


def rows(results_dir):
    out = []
    for f in sorted(glob.glob(os.path.join(results_dir, "*__*.json"))):
        seg, tag = os.path.basename(f)[:-5].split("__", 1)
        d = json.load(open(f)); n = d.get("numbers", d)
        pub = PUBLISHED.get((seg, tag))
        out.append((seg, tag, n["auc_raw"], pub, n["r_bandpass"], n.get("stroke_recall"), n.get("n_ref_strokes"), d.get("verdict")))
    return out


def table(rs):
    lines = ["| segment (held-out px) | checkpoint | inkcheck AUC | published AUC | Δ | r_bp | strokes recalled | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for seg, tag, auc, pub, r, sr, ns, v in rs:
        pubs = f"{pub:.3f}" if pub is not None else "–"
        dl = f"{auc - pub:+.3f}" if pub is not None else "–"
        srs = f"{sr:.2f} of {ns}" if sr is not None else "–"
        lines.append(f"| {seg} | {NAMES.get(tag, tag)} | {auc:.3f} | {pubs} | {dl} | {r:.2f} | {srs} | {v} |")
    return "\n".join(lines)


INTRO = ("Before trusting the diagnostic, check that it measures the same thing as the official evaluation. "
         "Same crops and held-out pixels as the `ink_9um` validation masks (`bench/fetch_ink9um_val.py`); predictions "
         "from villa inference on CPU (`bench/score.py`, layers 2–19, one z window); AUC over held-out pixels only.")
OUTRO = ("Published AUCs used other z-window choices, so differences of about ±0.01–0.02 are expected. The label crops hold only a few "
         "strokes each, so the stroke test has almost no power here (verdicts are WEAK at best): on these masks AUC is the "
         "number to compare, and the PASS/WEAK verdict is meant for full segments.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("results"); ap.add_argument("--readme")
    a = ap.parse_args(); t = table(rows(a.results)); print(t)
    if a.readme:
        s = open(a.readme).read()
        block = ("<!-- VALMASK_ROWS -->\n" + INTRO + "\n\n" + t + "\n\n" + OUTRO + "\n<!-- /VALMASK_ROWS -->")
        s = re.sub(r"<!-- VALMASK_ROWS -->.*?(<!-- /VALMASK_ROWS -->|$(?![\s\S]))", lambda m: block, s, count=1, flags=re.S) \
            if "<!-- /VALMASK_ROWS -->" in s else s.replace("<!-- VALMASK_ROWS -->", block, 1)
        open(a.readme, "w").write(s)

