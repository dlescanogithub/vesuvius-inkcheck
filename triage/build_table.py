"""Recoverability triage table: which public segments are worth GPU time?
Joins triage/proxies.json (node B scan proxies, CPU, no model) with the node-A verdicts in cards/ and results/newcases,
and with Reader V3's training-segment list (triage/reader_v3_train_segments.json, read from the config embedded in
reader-v3.pth). Writes triage/TRIAGE.md, triage/triage.csv, figures/triage.png. Rules are fixed in RULES below."""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
P = json.load(open(os.path.join(HERE, "proxies.json")))
TRAIN = json.load(open(os.path.join(HERE, "reader_v3_train_segments.json")))
# Node-B tolerance edges, from the Paris 4 tolerance curve (results/tolerance/tolerance_table.md): last PASS level of each series.
HF_EDGE = 0.024     # Gaussian blur: PASS at FWHM 22.6 µm (HF 0.0240), WEAK at 33.9 µm (HF 0.0118)
CORR_EDGE = 0.32    # added noise: PASS at sigma 0.5 SD (layer HP corr 0.320), WEAK at 1 SD (0.148)
UM_EDGE = 9.6       # binning: PASS at 9.6 µm, WEAK at 19.2 µm (HF does not catch binning: 0.034 at 19.2 µm)
# Node-A verdicts measured in this repo (scroll -> (verdict, evidence, segment ids measured)).
NODE_A = {
    "PHercParis4": ("PASS", "5/5 held-out 9 µm checkpoints PASS (cards/paris4)", ["20231005123336"]),
    "PHerc0009B": ("PASS", "Reader V3, Reader v2, dense_native PASS vs 2.4 µm map and vs human labels (cards/pherc0009B)", ["20250919125754"]),
    "PHerc0343P": ("WEAK", "no held-out model at letter level; IR camera letters agree (cards/343P)", ["20250904233748", "20250905172054", "20250511003658"]),
    "PHerc0841": ("WEAK", "Reader V3, Reader v2, dense_native WEAK vs human labels and vs 2.4 µm map (cards/pherc0841)", ["20260220213127"]),
    "PHerc0172": ("WEAK", "Reader V3, Reader v2, dense_native WEAK vs team map on w082 and w083 (cards/pherc0172)", ["20250926122938", "20250926132117"]),
    "PHerc0500P2": ("WEAK", "Reader V3, Reader v2, dense_native WEAK vs 2.2 µm map on gen_00371 and gen_00377 (cards/pherc0500P2)", ["20250716055229", "20250716055230"]),
    "PHerc0814": ("LOW_POWER", "official 46527 validation mask: AUC reproduced but only 2 strokes (cards/pherc0814)", ["46527"]),
}
RULES = """Tier rules (fixed before the table was built):
- **1 read**: the scroll has a node-A PASS with a held-out model, and the scan is inside the tolerance → run that model on the whole segment.
- **2 test**: no conclusive node-A result on the scroll, scan inside the tolerance → worth a small GPU test; if a team ink map exists, score it with inkcheck first (CPU, free).
- **3 transfer-limited**: node A is WEAK on this scroll although its scan is inside the tolerance → more GPU with the same models is not justified; labels or fine-tuning are needed.
- **4 scan-limited**: a proxy outside the tolerance → do not spend GPU on this volume.
- **5 not measured**: the fetched crop has too little valid surface for the HF proxy (no complete tile) → no call; fetch a larger crop.
Segments already in Reader V3's training set are marked: their ink was already labelled, so they are low priority for new reading."""


def in_train(scroll, seg):
    key = {"PHerc0009B": "p009b", "PHerc0139": "0139", "PHerc0814": "0814", "PHerc0500P2": "0500P2", "PHerc0343P": "0343P",
           "PHerc0172": "0172"}.get(scroll)
    if key is None: return False
    sid = seg.split(" ")[0]
    for n in TRAIN.get(key, []):
        if n[:14] == sid[:14] and (len(n) <= 14 or len(sid) <= 14 or n[14:19] == sid[14:19]):
            return True
    return False


rows = []
for name, r in P.items():
    scroll = r["scroll"]; seg = name[len(scroll) + 1:]
    hf, hf_note = r.get("hf_ratio"), ""
    if hf is None and r.get("hf_ratio_relaxed") is not None:
        hf, hf_note = r["hf_ratio_relaxed"], "relaxed"
    inside = (hf is not None and hf >= HF_EDGE) and r["layer_hp_corr"] >= CORR_EDGE and r["um"] <= UM_EDGE
    a = NODE_A.get(scroll)
    measured = bool(a) and any(seg.startswith(s) for s in a[2])
    if hf is None: tier = "5 not measured"   # too little valid surface for the HF proxy (no 2 mm tile)
    elif not inside: tier = "4 scan-limited"
    elif a and a[0] == "PASS": tier = "1 read"
    elif a and a[0] == "WEAK": tier = "3 transfer-limited"
    else: tier = "2 test"
    tr = in_train(scroll, seg)
    rows.append(dict(scroll=scroll, segment=seg, um=r["um"], valid_mm2=round(r["valid_mm2"]), hf_ratio=None if hf is None else round(hf, 4),
                     hf_note=hf_note, layer_hp_corr=round(r["layer_hp_corr"], 3), inside_tolerance=inside,
                     node_a=(a[0] + (" (this segment)" if measured else (" (same fragment)" if scroll.endswith("P") or scroll.endswith("P2") else " (same scroll)"))) if a else "none",
                     node_a_evidence=a[1] if a else "", in_reader_v3_training=tr, team_ink_map=("yes" if r.get("has_ink_map", scroll not in ("PHerc0800", "PHerc1447")) else "no"), tier=tier))
rows.sort(key=lambda d: (d["tier"], d["in_reader_v3_training"], d["scroll"], d["segment"]))
with open(os.path.join(HERE, "triage.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
n_all = len(rows); n_unm = sum(d["tier"] == "5 not measured" for d in rows)
n = n_all - n_unm; n_in = sum(d["inside_tolerance"] for d in rows); scrolls = sorted({d["scroll"] for d in rows})
cnt = {t: sum(d["tier"] == t for d in rows) for t in ("1 read", "2 test", "3 transfer-limited", "4 scan-limited", "5 not measured")}
head = (f"**{n_in} of {n} measurable public segments ({len(scrolls)} scrolls) are inside the scan tolerance where a 9 µm model still reads Paris 4 letters.** "
        f"Tiers: {cnt['1 read']} read, {cnt['2 test']} test, {cnt['3 transfer-limited']} transfer-limited, {cnt['4 scan-limited']} scan-limited"
        + (f"; {n_unm} more had too little valid surface to measure. " if n_unm else ". ") +
        "Wherever a segment got a WEAK verdict the scan is inside the tolerance, so on those segments the gap is model transfer, not scan quality. A WEAK verdict covers the segments measured, not the whole scroll or object: PHerc0343P is a detached fragment, and on the rolled PHerc. 343 the same public 9 µm models read letters (E. Nieuwlaar, First Letters Prize, Oct 2026).")
md = ["# Recoverability triage (CPU only, no GPU)", "", head, "",
      f"Tolerance (node B, Paris 4 dense_native curve): voxel ≤ {UM_EDGE:g} µm (PASS at 9.6, WEAK at 19.2; nothing tested in between), HF spectral ratio ≥ {HF_EDGE}, adjacent-layer high-pass correlation ≥ {CORR_EDGE}. "
      "Applying a Paris 4 tolerance to other scrolls assumes the proxies mean the same thing across scrolls and beam energies; this is not validated.", "",
      RULES, "",
      "| tier | scroll | segment | µm | area mm² | HF ratio | layer corr | node A | in Reader V3 training | ink map on the bucket |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for d in rows:
    md.append(f"| {d['tier']} | {d['scroll']} | {d['segment']} | {d['um']:g} | {d['valid_mm2']} | "
              f"{'n/a' if d['hf_ratio'] is None else format(d['hf_ratio'], '.4f')}{' (relaxed)' if d['hf_note'] else ''} | {d['layer_hp_corr']:.3f} | "
              f"{d['node_a']} | {'yes' if d['in_reader_v3_training'] else 'no'} | {d['team_ink_map']} |")
md += ["", "Proxies are computed on one 2048×2048 crop (or the labelled crop) per segment, centre layer of the model window; "
       "'relaxed' = no fully valid 512 px tile, so tiles ≥ 90% valid were used with the gaps filled (this tends to read slightly high). "
       "Node-A evidence: " + "; ".join(f"{k}: {v[1]}" for k, v in NODE_A.items()) + "."]
open(os.path.join(HERE, "TRIAGE.md"), "w").write("\n".join(md) + "\n")
json.dump(dict(headline=head, counts=cnt, n=n, n_inside=n_in, n_not_measured=n_unm, scrolls=scrolls), open(os.path.join(HERE, "triage_summary.json"), "w"), indent=1)
print(head)

if "--fig" in sys.argv:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    col = {"1 read": "#2a9d4b", "2 test": "#3b75c4", "3 transfer-limited": "#e08a1e", "4 scan-limited": "#c0392b", "5 not measured": "#999999"}
    tol = [l for l in open(os.path.join(ROOT, "results", "tolerance", "tolerance_table.md")) if l.startswith("| ") and "degradation" not in l]
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    for l in tol:
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if c[0] == "binning" or set(c[0]) <= set("-"): continue
        hf, lc = float(c[-2]), float(c[-1]); v = c[2]
        ax.scatter(hf, lc, marker="x", s=30, c={"PASS": "#2a9d4b", "WEAK": "#e08a1e", "FAIL": "#c0392b"}[v], alpha=.8, zorder=2)
    ax.scatter([], [], marker="x", c="grey", label="Paris 4 degraded on purpose (colour = verdict)")
    for t, cc in col.items():
        pts = [d for d in rows if d["tier"] == t and d["hf_ratio"] is not None]
        if pts: ax.scatter([d["hf_ratio"] for d in pts], [d["layer_hp_corr"] for d in pts], s=55, c=cc, edgecolor="k", lw=.5, label=f"tier {t} ({len(pts)})", zorder=3)
    ax.axvline(HF_EDGE, c="k", ls="--", lw=.8); ax.axhline(CORR_EDGE, c="k", ls="--", lw=.8)
    ax.axvspan(HF_EDGE, 0.25, ymin=CORR_EDGE, ymax=1, color="#2a9d4b", alpha=.07, zorder=0)
    ax.text(HF_EDGE * 1.04, 0.96, "blur edge (Paris 4)", fontsize=8, va="top"); ax.text(0.0005, CORR_EDGE + .015, "noise edge (Paris 4)", fontsize=8)
    ax.text(0.2, 0.36, "tolerated", fontsize=9, ha="right", color="#2a9d4b")
    for d in rows:
        if d["tier"].startswith("1") and d["hf_ratio"] is not None:
            ax.annotate(d["scroll"].replace("PHerc", ""), (d["hf_ratio"], d["layer_hp_corr"]), xytext=(6, -10), textcoords="offset points", fontsize=8)
    ax.set_xscale("symlog", linthresh=0.01); ax.set_xlim(-0.0005, 0.25); ax.set_ylim(0, 1)
    ax.set_xlabel("HF spectral ratio (10–25 / 2–10 cycles/mm), sharpness"); ax.set_ylabel("adjacent-layer high-pass correlation, signal vs noise")
    ax.set_title(f"{n_in} of {n} measurable public segments are inside the scan tolerance (upper right)\nWEAK segments are model-transfer-limited, not scan-limited", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0.0, 0.92), framealpha=.95); fig.tight_layout(); fig.savefig(os.path.join(ROOT, "figures", "triage.png"), dpi=150)
