"""Calibrate and document the PASS / WEAK / FAIL thresholds on labelled cases.

Labels (set by construction, not by the verdict being calibrated):
  readable: held-out segments of scrolls the community already reads from ~9 um maps (Paris 4, PHerc0009B): the
            prediction vs the published reference of the SAME segment, correctly registered. Positives.
  real    : the same kind of pair on scrolls whose ~9 um readability is the open question (343P, 0841, 0172, 0500P2).
            Not labelled either way; shown, not used for the ROC.
  degraded: same as real, but the model input was blurred / binned / noised on purpose (node-B tolerance series)
  control : deliberate negative controls (wrong region, phase-randomised prediction, tile-shuffled reference)
  null    : the 192 shift-null r values stored in every real check (reference moved >= min shift; no alignment)

Outputs (calibration/):
  calibration.png  separation plot (r_bp vs stroke recall, with tile-bootstrap CIs and threshold lines) and ROC of r_bp
  calibration.json numbers quoted in the README: ROC AUC, FPR/TPR at r_bp >= 0.20, threshold sensitivity, borderline cases
Run: python calibration/calibrate.py  (needs matplotlib; reads results/**.json with a 'bootstrap' block)

Paris 4 (PHercParis4) scores are withheld from the public outputs while the PHercParis4 publication reservation applies
(until 2027-06-25). Their inkcheck JSONs live outside the repo; point INKCHECK_PRIVATE_RESULTS at the directory that
holds them (same results/ layout) to reproduce the shipped aggregates. Paris 4 cases then enter the counts, the ROC and
the threshold sensitivity, but calibration.json lists them by name and verdict only and calibration.png does not plot them.
Without the private JSONs the outputs are written as calibration_public_only.{json,png} so the shipped files are not
silently replaced by a smaller sample.
"""
import glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "..", "results")
PRIV = os.environ.get("INKCHECK_PRIVATE_RESULTS")
PRES = os.path.join(PRIV, "results") if PRIV else None


def withheld(name):
    """Paris 4 cases (incl. the degraded Paris 4 series and the Paris 4 positive twin): verdict only in public outputs."""
    return "paris4" in name or name.startswith("tolerance/")
R_MIN, REC_MIN, ALPHA = 0.20, 0.50, 0.01


def group(rel):
    if rel.startswith("negctrl/pos_") or rel.startswith("tolerance/paris4_original"): return "duplicate"
    if rel.startswith("negctrl/ctrl_"): return "control"
    if rel.startswith("tolerance/") and "original" not in rel: return "degraded"
    if "paris4" in rel or "0009B" in rel: return "readable"
    return "real"


def load():
    rows = []; files = {}
    for root in [RES] + ([PRES] if PRES else []):
        for f in (glob.glob(os.path.join(root, "rescore", "**", "*.json"), recursive=True)
                  + glob.glob(os.path.join(root, "negctrl", "*.json"))
                  + glob.glob(os.path.join(root, "tolerance", "*.json"))
                  + glob.glob(os.path.join(root, "newcases", "scores", "*.json"))):
            files.setdefault(os.path.relpath(f, root), f)
    for rel in sorted(files):
        f = files[rel]
        d = json.load(open(f)); n = d.get("numbers", {}); b = n.get("bootstrap")
        if not b or "r_bandpass" not in n:
            continue
        rows.append(dict(name=rel[:-5], group=group(rel), withheld=withheld(rel), verdict=d["verdict"], r=n["r_bandpass"],
                         p=n["r_bandpass_p"], rec=n.get("stroke_recall"),
                         p_s=(n.get("metric_nulls", {}).get("stroke_recall") or {}).get("p", 1.0), n_strokes=n.get("n_ref_strokes"),
                         chance=b.get("chance"), r_ci=b.get("r_ci"), rec_ci=b.get("stroke_recall_ci"),
                         rmc_ci=b.get("recall_minus_chance_ci"), null_mean=n.get("r_bandpass_null_mean"),
                         nulls=d.get("nulls", {}).get("r_bandpass_shift_nulls", [])))
    return rows


def roc(pos, neg):
    s = np.r_[pos, neg]; y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    o = np.argsort(-s); y = y[o]
    tpr = np.r_[0, np.cumsum(y) / max(1, y.sum())]; fpr = np.r_[0, np.cumsum(1 - y) / max(1, (1 - y).sum())]
    return fpr, tpr, float(np.trapezoid(tpr, fpr))


def verdict(x, rmin=R_MIN, recmin=REC_MIN):
    """Same rule as inkcheck.core.run_check, with movable PASS thresholds."""
    if not x["p"] <= ALPHA: return "FAIL"
    big = x["r"] >= rmin and x["rec"] is not None and x["rec"] >= recmin
    return "PASS" if (x["p_s"] is not None and x["p_s"] <= 0.05 and big) else "WEAK"


def main():
    rows = [x for x in load() if x["group"] != "duplicate"]   # same run as rescore/reader_v2/paris4..__dn
    n_wh = sum(x["withheld"] for x in rows)
    tag = "" if n_wh else "_public_only"
    if not n_wh:
        print("WARNING: private Paris 4 JSONs not found (set INKCHECK_PRIVATE_RESULTS); the aggregates below exclude Paris 4 "
              "and are written to calibration_public_only.{json,png}, not over the shipped calibration.{json,png}")
    real = [x for x in rows if x["group"] in ("readable", "real")]; good = [x for x in rows if x["group"] == "readable"]; ctrl = [x for x in rows if x["group"] == "control"]
    deg = [x for x in rows if x["group"] == "degraded"]
    nulls = np.concatenate([x["nulls"] for x in real if x["nulls"]]) if real else np.array([])
    pos = np.array([x["r"] for x in good]); neg = np.r_[nulls, [x["r"] for x in ctrl]]
    fpr, tpr, auc = roc(pos, neg)
    out = dict(n_readable=len(good), n_real_unlabelled=len(real) - len(good),
               readable_pass=sum(x["verdict"] == "PASS" for x in good), readable_r_min=float(pos.min()),
               controls_pass=sum(x["verdict"] == "PASS" for x in ctrl), controls_r_max=float(max(x["r"] for x in ctrl)), n_degraded=len(deg), n_controls=len(ctrl), n_null_draws=int(len(nulls)), roc_auc_r_bp=auc,
               fpr_at_r020=float(np.mean(neg >= R_MIN)), tpr_at_r020=float(np.mean(pos >= R_MIN)),
               null_r_p99=float(np.quantile(nulls, 0.99)) if len(nulls) else None,
               null_r_max=float(nulls.max()) if len(nulls) else None,
               n_withheld_paris4=n_wh,
               withheld_note="Paris 4 cases are counted in every aggregate but listed by name and verdict only, and not plotted "
                             "(PHercParis4 publication reservation until 2027-06-25)",
               controls={x["name"]: dict(verdict=x["verdict"], r=x["r"], p=x["p"], recall=x["rec"], r_ci=x["r_ci"],
                                         recall_minus_chance_ci=x["rmc_ci"]) for x in ctrl})
    # sensitivity: how many recorded verdicts move if the PASS thresholds move (p and WEAK rule unchanged)
    sens = {}
    for rmin in (0.10, 0.15, 0.20, 0.30):
        for recmin in (0.30, 0.40, 0.50, 0.60):
            v = [verdict(x, rmin, recmin) for x in rows]
            sens[f"r>={rmin:.2f},recall>={recmin:.2f}"] = dict(
                PASS=sum(a == "PASS" for a in v),
                changed=sum(a != x["verdict"] for a, x in zip(v, rows)),
                controls_passing=sum(a == "PASS" for a, x in zip(v, rows) if x["group"] == "control"))
    out["threshold_sensitivity"] = sens
    out["rule_reproduces_recorded_verdicts"] = all(verdict(x) == x["verdict"] for x in rows)
    out["borderline"] = [x["name"] for x in rows if not x["withheld"] and x["r_ci"] and x["rec_ci"] and x["p"] <= ALPHA and
                         ((x["r_ci"][0] < R_MIN <= x["r_ci"][1]) or (x["rec_ci"][0] < REC_MIN <= x["rec_ci"][1]))]
    out["cases"] = [dict(name=x["name"], group=x["group"], verdict=x["verdict"], withheld=True) if x["withheld"] else
                    {k: x[k] for k in ("name", "group", "verdict", "r", "p", "rec", "n_strokes", "chance", "r_ci", "rec_ci",
                                       "rmc_ci")} for x in rows]
    json.dump(out, open(os.path.join(HERE, f"calibration{tag}.json"), "w"), indent=1)

    fig, ax = plt.subplots(1, 2, figsize=(13, 5.8), gridspec_kw=dict(width_ratios=[1.25, 1]))
    col = dict(readable="tab:blue", real="tab:purple", degraded="tab:orange", control="tab:red")
    mk = dict(PASS="o", WEAK="s", FAIL="X")
    for x in rows:
        if x["rec"] is None or x["withheld"]: continue
        c = col[x["group"]]
        if x["r_ci"] and x["rec_ci"]:
            ax[0].plot(x["r_ci"], [x["rec"]] * 2, color=c, alpha=.35, lw=1)
            ax[0].plot([x["r"]] * 2, x["rec_ci"], color=c, alpha=.35, lw=1)
        ax[0].scatter(x["r"], x["rec"], c=c, marker=mk[x["verdict"]], s=40, edgecolor="k", lw=.4, zorder=3)
    ax[0].axvline(R_MIN, ls="--", c="k", lw=.8); ax[0].axhline(REC_MIN, ls="--", c="k", lw=.8)
    ax[0].text(R_MIN + .01, .02, "r_bp = 0.20", fontsize=8); ax[0].text(.6, REC_MIN + .02, "recall = 0.50", fontsize=8)
    if len(nulls):
        ax0b = ax[0].twinx(); ax0b.hist(nulls, bins=60, color="grey", alpha=.35, density=True); ax0b.set_yticks([])
    lab = dict(readable="readable (0009B; Paris 4 not plotted)", real="open scroll (343P, 0841, 0172, 0500P2)", degraded="degraded (Paris 4: not plotted)", control="negative control")
    for g, c in col.items(): ax[0].scatter([], [], c=c, label=lab[g])
    for v, m in mk.items(): ax[0].scatter([], [], c="w", edgecolor="k", marker=m, label=v)
    ax[0].scatter([], [], c="grey", alpha=.4, marker="s", label=f"shift nulls (n={len(nulls)})")
    ax[0].legend(fontsize=7, loc="upper left"); ax[0].set_xlabel("band-pass r (bars: 2 mm tile-bootstrap 95% CI)")
    ax[0].set_ylabel("stroke recall"); ax[0].set_title("Every scored pair: band-pass r vs stroke recall", fontsize=11)
    ax[0].set_xlim(-0.1, 0.95); ax[0].set_ylim(-0.02, 1.05)
    rmins, recmins = (0.10, 0.15, 0.20, 0.30), (0.30, 0.40, 0.50, 0.60)
    grid = np.array([[sens[f"r>={r:.2f},recall>={q:.2f}"]["changed"] for r in rmins] for q in recmins])
    ax[1].imshow(grid, cmap="Oranges", vmin=0, vmax=max(4, grid.max() * 2.5), origin="lower")
    for i, q in enumerate(recmins):
        for j, r in enumerate(rmins):
            e = sens[f"r>={r:.2f},recall>={q:.2f}"]
            ax[1].text(j, i, f"{e['PASS']} PASS\n{e['changed']} changed\n{e['controls_passing']} ctrl PASS", ha="center",
                       va="center", fontsize=8, fontweight="bold" if (r, q) == (R_MIN, REC_MIN) else "normal")
    ax[1].set_xticks(range(len(rmins)), [f"{r:.2f}" for r in rmins]); ax[1].set_yticks(range(len(recmins)), [f"{q:.2f}" for q in recmins])
    ax[1].set_xlabel("PASS threshold on band-pass r"); ax[1].set_ylabel("PASS threshold on stroke recall")
    ax[1].set_title(f"Moving the PASS thresholds ({len(rows)} pairs; bold = shipped rule)", fontsize=11)
    fig.text(0.5, 0.035, f"{n_wh} Paris 4 pairs are counted in every number here but not plotted: scores withheld (PHercParis4 publication reservation until 2027-06-25).",
             ha="center", fontsize=8, style="italic")
    fig.text(0.5, 0.01, f"Readable pairs: {out['readable_pass']}/{len(good)} PASS, min r {out['readable_r_min']:.2f}.  "
             f"Negative controls: {out['controls_pass']}/{len(ctrl)} PASS, max r {out['controls_r_max']:.2f}.  "
             f"Shift nulls: max r {out['null_r_max']:.2f} over {len(nulls)} draws.  ROC AUC (readable vs nulls + controls) {auc:.3f}.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(os.path.join(HERE, f"calibration{tag}.png"), dpi=130)
    print(json.dumps({k: v for k, v in out.items() if k not in ("cases", "threshold_sensitivity")}, indent=1))


if __name__ == "__main__":
    main()
