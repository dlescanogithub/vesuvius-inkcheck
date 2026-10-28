"""Node-B tolerance curve: Paris 4 dense_native inkcheck verdict vs controlled degradation of the model INPUT.

Public outputs (verdicts and scan proxies only; the Paris 4 scores are withheld while the PHercParis4 publication
reservation applies, until 2027-06-25):
  figures/tolerance_curve.png, results/tolerance/tolerance_table.md, results/tolerance/tolerance_verdicts.json
With the private inkcheck JSONs (INKCHECK_PRIVATE_RESULTS=<dir containing results/tolerance/paris4_<variant>_dn.json>)
it re-derives the verdicts from them and also writes the full score figure/table into that private directory.
Without them it redraws the public figure from results/tolerance/tolerance_verdicts.json."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
T = os.path.join(ROOT, "results", "tolerance"); PX = 9.6; VOL_SD = 32.0   # SD of the undegraded volume (make_degraded_p4_c.py)
PRIV = os.environ.get("INKCHECK_PRIVATE_RESULTS")
PT = os.path.join(PRIV, "results", "tolerance") if PRIV else None
prox = json.load(open(os.path.join(ROOT, "results", "study", "proxies_all.json")))
series = {
    "Gaussian blur (FWHM, µm)": [("original", 0)] + [(f"blur{s:g}", 2.3548 * s * PX) for s in (0.5, 1, 1.5, 2, 3, 4)],
    "binning (effective voxel, µm)": [("original", PX)] + [(f"bin{k}", k * PX) for k in (2, 3, 4)],
    "added noise (σ / volume SD)": [("original", 0)] + [(f"noise_sd{s}", s / VOL_SD) for s in (8, 16, 32, 48, 64)],
}
col = dict(PASS="tab:green", WEAK="tab:orange", FAIL="tab:red")
VJ = os.path.join(T, "tolerance_verdicts.json")


def load(v):
    f = os.path.join(PT, f"paris4_{v}_dn.json") if PT else None
    if not f or not os.path.exists(f): return None
    d = json.load(open(f)); n = d["numbers"]; b = n.get("bootstrap", {})
    return dict(verdict=d["verdict"], r=n["r_bandpass"], r_ci=b.get("r_ci"), rec=n["stroke_recall"], rec_ci=b.get("stroke_recall_ci"))


full = {v: load(v) for pts in series.values() for v, _ in pts}
have_private = all(full.values())
if have_private:
    verdicts = {v: d["verdict"] for v, d in full.items()}
    json.dump(dict(note="Paris 4 dense_native verdicts per input degradation; scores withheld (PHercParis4 reservation until 2027-06-25)",
                   verdicts=verdicts), open(VJ, "w"), indent=1)
else:
    print("private Paris 4 tolerance JSONs not found: redrawing the public verdict-only figure from", VJ)
    verdicts = json.load(open(VJ))["verdicts"]

# public: verdict per level + scan proxies, no scores
rows = ["| degradation | level | verdict | HF ratio | layer HP corr |", "|---|---|---|---|---|"]
fig, axes = plt.subplots(1, 3, figsize=(15, 3.0))
for ax, (name, pts) in zip(axes, series.items()):
    for v, x in pts:
        pr = prox.get(v, {})
        rows.append(f"| {name.split(' (')[0]} | {v} ({x:.3g}) | {verdicts[v]} | {pr.get('hf_ratio', float('nan')):.4f} | "
                    f"{pr.get('layer_hp_corr', float('nan')):.3f} |")
        ax.scatter([x], [0], c=col[verdicts[v]], s=160, edgecolor="k", lw=.5, zorder=3)
        ax.annotate(verdicts[v], (x, 0), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=7)
    ax.set_yticks([]); ax.set_ylim(-1, 1.2); ax.set_xlabel(name); ax.set_title(name.split(" (")[0])
for v, c in col.items(): axes[2].scatter([], [], c=c, label=v)
axes[2].legend(fontsize=8, loc="lower right")
fig.suptitle("Node B tolerance: Paris 4, dense_native 9 µm checkpoint, input degraded before inference: IRP verdict per level "
             "(scores withheld: PHercParis4 reservation until 2027-06-25)", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "figures", "tolerance_curve.png"), dpi=130)
open(os.path.join(T, "tolerance_table.md"), "w").write("\n".join(rows) + "\n\nScores withheld (PHercParis4 publication reservation until 2027-06-25); verdicts and scan proxies only.\n")
print("\n".join(rows))

if have_private:   # full score figure and table, private directory only
    prow = ["| degradation | level | verdict | r_bp [95% CI] | stroke recall [95% CI] | HF ratio | layer HP corr |", "|---|---|---|---|---|---|---|"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), sharey=True)
    for ax, (name, pts) in zip(axes, series.items()):
        xs, rs = [], []
        for v, x in pts:
            d = full[v]; xs.append(x); rs.append(d); pr = prox.get(v, {})
            prow.append(f"| {name.split(' (')[0]} | {v} ({x:.3g}) | {d['verdict']} | {d['r']:.2f} [{d['r_ci'][0]:.2f}, {d['r_ci'][1]:.2f}] | "
                        f"{d['rec']:.2f} [{d['rec_ci'][0]:.2f}, {d['rec_ci'][1]:.2f}] | {pr.get('hf_ratio', float('nan')):.4f} | "
                        f"{pr.get('layer_hp_corr', float('nan')):.3f} |")
        o = sorted(range(len(xs)), key=lambda i: xs[i]); xs = [xs[i] for i in o]; rs = [rs[i] for i in o]
        for key, lab, ls in (("r", "band-pass r", "-"), ("rec", "stroke recall", "--")):
            y = [d[key] for d in rs]; lo = [d[key + "_ci"][0] for d in rs]; hi = [d[key + "_ci"][1] for d in rs]
            ax.plot(xs, y, ls, c="k", lw=1, label=lab); ax.fill_between(xs, lo, hi, color="grey", alpha=.2)
            ax.scatter(xs, y, c=[col[d["verdict"]] for d in rs], s=40, zorder=3, edgecolor="k", lw=.4)
        ax.axhline(0.5, c="tab:blue", lw=.7, ls=":"); ax.axhline(0.2, c="tab:blue", lw=.7, ls=":")
        ax.set_xlabel(name); ax.set_title(name.split(" (")[0])
    axes[0].set_ylabel("score (shaded: 2 mm tile-bootstrap 95% CI)"); axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("PRIVATE - Node B tolerance: Paris 4, dense_native (dotted: PASS thresholds r 0.20, recall 0.50)", fontsize=10)
    fig.tight_layout(); os.makedirs(os.path.join(PRIV, "figures"), exist_ok=True)
    fig.savefig(os.path.join(PRIV, "figures", "tolerance_curve.png"), dpi=130)
    open(os.path.join(PT, "tolerance_table.md"), "w").write("\n".join(prow) + "\n")
