"""Build the one-page PDF for judges (docs/IRP_onepager.pdf) and the headline PNG (figures/headline.png).

Every number comes from cards/*.json, calibration/calibration.json or triage/triage_summary.json, or is quoted
from a card listed next to it. Run after `inkcheck report examples/irp/*.case.json --out cards`,
`python calibration/calibrate.py` and `python triage/build_table.py --fig`. Needs matplotlib.
"""
import json, os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
cal = J("calibration", "calibration.json"); tri = J("triage", "triage_summary.json")
KEYS = ("paris4", "negative_controls", "pherc0009B", "pherc0814", "343P", "pherc0841", "pherc0172", "pherc0500P2",
        "scrollgt_flagship", "pherc1203")
cards = {k: J("cards", k + ".json") for k in KEYS if os.path.exists(os.path.join(ROOT, "cards", k + ".json"))}
COL = {"PASS": "#2e7d32", "WEAK": "#ef6c00", "FAIL": "#c62828"}


def final(k):
    n = cards[k]["nodes"]; return n[-1]["verdict"], n[0]["verdict"]


def sub(k):
    """Node-A verdict shown next to a REFS_AGREE (node R) verdict: the references agree, A says how well the model reads (e.g. A: WEAK)."""
    fv, av = final(k)
    return f"(A: {av})" if fv == "REFS_AGREE" and av in COL else ""


# short evidence per card (numbers checked against the card JSON / Markdown in cards/)
# Paris 4 (incl. the ScrollGT flagship segment) scores are withheld: PHercParis4 publication reservation until 2027-06-25.
SGT_EV = "Reader V3 and seed42 PASS, but the segment is in their training data, so IRP excludes it (scores withheld)"
ROWS = [
    ("paris4", "Paris 4, held out", "5/5 held-out checkpoints PASS (Reader v2, V3, 3 others); scores withheld until the PHercParis4 reservation ends (2027-06-25)"),
    ("pherc0009B", "PHerc0009B, held-out segment", "Reader V3, v2 and dense_native PASS vs team 2.4 µm map (r 0.79 / 0.75 / 0.67) and vs human labels (10/10 strokes)"),
    ("negative_controls", "Negative controls", "wrong region, phase-randomised, shuffled tiles: 0/4 PASS (3 FAIL, 1 WEAK with recall at chance)"),
    ("pherc0814", "PHerc0814 validation mask", "AUC matches the official evaluation within 0.02 for 4/4 checkpoints"),
    ("343P", "PHerc0343P fragment, 3 held-out segs", "Reader v2/V3 WEAK (r 0.18-0.22); 2 refs agree (IR camera letters, ρ 0.90); scan in tolerance; 2.2 µm scan no better. Not the rolled PHerc. 343 (read, Nieuwlaar Oct 2026)"),
    ("pherc0841", "PHerc0841, unseen scroll", "Reader V3 / v2 / dense_native WEAK: best r 0.55, recall 0.34 vs 0.15 chance; human labels: r ≤ 0.30, ≤ 1 of 7 strokes"),
    ("pherc0172", "PHerc0172 w082 + w083, held out", "Reader V3 / v2 / dense_native WEAK on both: r 0.26-0.51, stroke recall 0.21-0.37 vs 0.16-0.20 chance"),
    ("pherc0500P2", "PHerc0500P2 gen_00371 + 00377, held out", "Reader V3 / v2 / dense_native WEAK on both: r 0.21-0.44, stroke recall 0.10-0.32 vs 0.05-0.07 chance"),
    ("scrollgt_flagship", "ScrollGT flagship label (Paris 4), train-exposed", SGT_EV),
    ("pherc1203", "PHerc1203 at 2.4 µm, unlabelled", "0/19 zone/model pairs meet the pre-registered candidate rule"),
]
ROWS = [r for r in ROWS if r[0] in cards]
POSITION = ("Related work: inkbench (inksweep/inkbench) and ScrollGT (jonmarrs/scrollgt) measure models; IRP decides what to do with a "
            "segment (is the scan, the model or the scroll the bottleneck?) and adds pre-registration. villa #2210 (held-out "
            "evaluation) and #2318 (face check: writing vs texture) are complementary checks inside villa.")
HEAD = (f"{tri['n_inside']} of {tri['n']} measurable public segments ({len(tri['scrolls'])} scrolls) are inside the scan tolerance where a ~9 µm model "
        f"still reads Paris 4. On the segments where models are WEAK, the scan is not the bottleneck: model transfer is (per segment, not per scroll).")
TIERS = "   ".join(f"{k.split(' ', 1)[1]}: {v}" for k, v in tri["counts"].items() if v)


def vcol(v):
    return COL.get(v, "#1565c0" if v in ("REFS_AGREE", "NO_CONTROL_PASSES", "CONTROL_REPRODUCED", "NO_CANDIDATE", "SCAN_OK") else
                   "#6a1b9a" if v == "SCROLL_SPECIFIC" else "#607d8b" if v == "NO_HELD_OUT" else "#555")


def onepager(path):
    fig = plt.figure(figsize=(8.5, 11)); W = fig.add_axes([0, 0, 1, 1]); W.axis("off")
    t = lambda x, y, s, **k: W.text(x, y, s, transform=W.transAxes, **k)

    def para(y, s, fs, bold=False, color="#000", x=.05, lead=1.75):
        n = int(1030 / fs * (0.88 if bold else 1.0))          # characters per line that fit 0.90 of the page width
        for line in textwrap.wrap(s, n):
            t(x, y, line, fontsize=fs, weight="bold" if bold else "normal", color=color); y -= fs * lead / 792
        return y
    t(.05, .965, "Ink Recoverability Protocol (IRP)", fontsize=19, weight="bold")
    t(.05, .943, "Is the ink missing, or just not recovered yet?  A CPU-only decision tree with a card per segment.", fontsize=10.5)
    t(.05, .925, "Diego Lescano · Vesuvius Challenge October 2026 progress prize · MIT · tool: inkcheck (pip install -e .)", fontsize=8, color="#555")
    y = .895
    for s in ["Node A: does a held-out model recover the reference strokes? (band-pass r and stroke recall vs search-matched shift nulls)",
              "Node R: do two independent references agree?   Node N: do negative controls fail?",
              "Node B: is the scan inside the blur/noise/voxel tolerance of a ~9 µm model?   Node C: does a second scan change it?",
              "Node D: does an unlabelled segment meet a rule written and hashed before the first look?"]:
        t(.06, y, "• " + s, fontsize=8.2); y -= .016
    y -= .008; t(.05, y, f"Validation: {len(ROWS)} cards, verdicts produced by `inkcheck report`", fontsize=11.5, weight="bold"); y -= .022
    for k, name, ev in ROWS:
        fv, av = final(k)
        W.add_patch(FancyBboxPatch((.05, y - .006), .185, .02, boxstyle="round,pad=0.002", transform=W.transAxes,
                                   fc=vcol(fv), ec="none"))
        lab = fv + (" " + sub(k) if sub(k) else "")
        t(.142, y + .004, lab, fontsize=7.4 if len(lab) < 19 else 6.6, color="w", weight="bold", ha="center", va="center")
        t(.245, y + .004, name, fontsize=8, weight="bold", va="center")
        t(.245, y - .010, ev, fontsize=7.2, va="center", color="#222")
        y -= .034
    y -= .004
    y = para(y, f"Calibration: readable pairs {cal['readable_pass']}/{cal['n_readable']} PASS (min r {cal['readable_r_min']:.2f}); "
                f"controls {cal['controls_pass']}/{cal['n_controls']} PASS (max r {cal['controls_r_max']:.2f}); "
                f"shift nulls max r {cal['null_r_max']:.2f} over {cal['n_null_draws']} draws (PASS needs r ≥ 0.20 and recall ≥ 0.50). "
                "Every check carries 2 mm tile-bootstrap 95% CIs. Thresholds were fixed on synthetic tests before real data; "
                "moving the r threshold (0.10-0.30) changes no verdict.", 7.6)
    y -= .006
    y = para(y, POSITION, 7.6, color="#333")
    y -= .012
    t(.05, y, "Triage of public segments: where is GPU time worth it?", fontsize=11.5, weight="bold"); y -= .010
    img = mpimg.imread(os.path.join(ROOT, "figures", "triage.png")); h = .215; w = h * img.shape[1] / img.shape[0] * 11 / 8.5
    ax = fig.add_axes([.05, y - h, min(w, .9), h]); ax.imshow(img); ax.axis("off"); y -= h + .010
    y = para(y, HEAD, 8.4, bold=True)
    y = para(y, "Tiers: " + TIERS + "   (table: triage/TRIAGE.md)", 8) - .006
    para(y, "Limits: references are model outputs or annotations, not ground truth; the tolerance was measured on Paris 4 only; "
            "the 343P IR reference has 8 strokes; scan proxies come from one crop per segment; ScrollGT label placement is ~0.3 mm, "
            "so scores against it are lower bounds; data licenses of the Vesuvius open data apply. Full list: README, Limitations.",
         7.2, color="#444")
    fig.savefig(path); plt.close(fig)


def headline(path):
    fig = plt.figure(figsize=(16, 9), dpi=100); W = fig.add_axes([0, 0, 1, 1]); W.axis("off")
    t = lambda x, y, s, **k: W.text(x, y, s, transform=W.transAxes, **k)
    t(.03, .93, "Is the ink missing, or just not recovered yet?", fontsize=30, weight="bold")
    t(.03, .875, "Ink Recoverability Protocol: CPU-only checks, one card per segment", fontsize=17, color="#444")
    y = .80
    for k, name, ev in ROWS:
        fv, _ = final(k)
        W.add_patch(FancyBboxPatch((.03, y - .022), .13, .044, boxstyle="round,pad=0.004", transform=W.transAxes, fc=vcol(fv), ec="none"))
        if sub(k):
            t(.095, y + .009, fv.replace("_", " "), fontsize=10.5, color="w", weight="bold", ha="center", va="center")
            t(.095, y - .012, sub(k), fontsize=9, color="w", weight="bold", ha="center", va="center")
        else:
            t(.095, y, fv.replace("_", " "), fontsize=11, color="w", weight="bold", ha="center", va="center")
        t(.17, y, name, fontsize=14, va="center"); y -= .066
    img = mpimg.imread(os.path.join(ROOT, "figures", "triage.png"))
    ax = fig.add_axes([.47, .12, .51, .75]); ax.imshow(img); ax.axis("off")
    HL = (f"{tri['n_inside']} of {tri['n']} measurable public segments ({len(tri['scrolls'])} scrolls) are inside the scan tolerance "
          f"of a ~9 µm model. On WEAK segments, model transfer is the bottleneck, not the scan.")
    for i, s in enumerate(textwrap.wrap(HL, 95)):
        t(.03, .075 - i * .042, s, fontsize=17, weight="bold")
    fig.savefig(path); plt.close(fig)


if __name__ == "__main__":
    onepager(os.path.join(ROOT, "docs", "IRP_onepager.pdf")); onepager("/tmp/onepager_preview.png")
    headline(os.path.join(ROOT, "figures", "headline.png"))
    print("wrote docs/IRP_onepager.pdf, figures/headline.png")
