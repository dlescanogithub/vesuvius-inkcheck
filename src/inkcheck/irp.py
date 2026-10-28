"""Ink Recoverability Protocol (IRP): a per-segment decision tree on top of inkcheck.

Nodes (each returns a NodeResult with a verdict, the evidence, and the next step):

  A  labelled segment   -> does the model see KNOWN ink?   (inkcheck PASS/WEAK/FAIL vs search-matched nulls)
  B  scan quality       -> do blur/noise proxies of this scan fall outside the tolerance measured on a PASS segment?
  C  scan vs scroll     -> same segment rendered from two scans: does either scan turn a non-PASS into PASS?
  D  unlabelled segment -> pre-registered candidate rule (reverse-depth null, components >= 2x null,
                           cross-checkpoint agreement r >= 0.3, stroke width 0.1-0.5 mm, visual check),
                           and a check that the pre-registration was written before the results.

A case is a JSON file (see examples/irp/*.case.json). Everything here is pure Python on numbers that were
already computed (inkcheck JSON outputs, proxy values, zone metrics), so a card takes well under a second.
Optionally a node-A entry can carry pred/ref paths and inkcheck is run on it first (CPU).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

VERDICT_RANK = {"PASS": 2, "WEAK": 1, "FAIL": 0}
LOW_POWER_STROKES = 10      # fewer reference strokes than this: the stroke test has (almost) no power
AUC_AGREE = 0.02            # |inkcheck AUC - published AUC| within this counts as "reproduces"


@dataclass
class NodeResult:
    node: str
    question: str
    verdict: str            # short machine-readable outcome
    answer: str             # one-line human answer
    evidence: list = field(default_factory=list)   # markdown bullet lines / table rows
    next_step: str = ""
    table: list = field(default_factory=list)      # optional rows (list of lists), first row = header
    automated: str = "automatic"

    def to_dict(self):
        return dict(node=self.node, question=self.question, verdict=self.verdict, answer=self.answer,
                    evidence=self.evidence, next_step=self.next_step, table=self.table, automated=self.automated)


# ----------------------------------------------------------------------------------------------- helpers
def _load_json(path: Path):
    return json.loads(Path(path).read_text())


def _resolve(base: Path, p):
    if p is None:
        return None
    p = Path(p)
    return p if p.is_absolute() else (base / p)


def _f(x, nd=2):
    return "–" if x is None else f"{x:.{nd}f}"


def _check_numbers(d: dict) -> dict:
    n = d.get("numbers", {})
    mn = n.get("metric_nulls", {})
    b = n.get("bootstrap") or {}
    return dict(r_ci=b.get("r_ci"), recall_ci=b.get("stroke_recall_ci"), rmc=b.get("recall_minus_chance"),
                rmc_ci=b.get("recall_minus_chance_ci"), boot_tiles=b.get("n_tiles"),
                verdict=d.get("verdict"), r_bp=n.get("r_bandpass"), r_bp_z=n.get("r_bandpass_z"),
                r_bp_p=n.get("r_bandpass_p"), r_bp_null=n.get("r_bandpass_null_mean"),
                auc=n.get("auc_raw"), stroke_recall=n.get("stroke_recall"),
                stroke_null=(mn.get("stroke_recall") or {}).get("null_mean"),
                n_strokes=n.get("n_ref_strokes"), area_cm2=n.get("overlap_cm2"), analysis_um=n.get("analysis_um"))


def _withheld_check(entry: dict, base: Path) -> dict:
    """Verdict-only check: the numbers are not published (e.g. a data-terms reservation). The case file carries the
    verdict; if the inkcheck JSON is present locally (private copy), its verdict must match the case file."""
    jp = _resolve(base, entry.get("json"))
    verdict = entry.get("verdict")
    if jp is not None and jp.exists():
        v = _load_json(jp).get("verdict")
        if verdict is not None and v != verdict:
            raise ValueError(f"{jp}: verdict {v} does not match the withheld verdict {verdict} in the case file")
        verdict = v
    if verdict is None:
        raise FileNotFoundError(f"withheld check '{entry.get('label')}' has no verdict and no inkcheck JSON ({jp})")
    out = _check_numbers({})
    out.update(verdict=verdict, withheld=str(entry["withhold"]), label=entry.get("label", "check"),
               held_out=entry.get("held_out", True), note=entry.get("note", ""), published_auc=None,
               json=str(entry.get("json")), expect=entry.get("expect"))
    return out


def load_check(entry: dict, base: Path, run_missing: bool = True) -> dict:
    """Load one inkcheck result. entry: {label, json, [pred, ref, pred_um, ref_um, mask, ref_origin, args]}.
    With "withhold": "<reason>" (and "verdict"), only the verdict is used and every number is left out of the card."""
    if entry.get("withhold"):
        return _withheld_check(entry, base)
    jp = _resolve(base, entry.get("json"))
    if jp is not None and not jp.exists() and run_missing and entry.get("pred"):
        from .cli import main as _ic_main
        argv = [str(_resolve(base, entry["pred"])), str(_resolve(base, entry["ref"])),
                "--pred-um", str(entry["pred_um"]), "--ref-um", str(entry["ref_um"]),
                "--out", str(jp.with_suffix(""))]
        if entry.get("mask"):
            argv += ["--mask", str(_resolve(base, entry["mask"]))]
        if entry.get("ref_origin"):
            argv += ["--ref-origin", entry["ref_origin"]]
        argv += [str(a) for a in entry.get("args", [])]
        _ic_main(argv)
    if jp is None or not jp.exists():
        raise FileNotFoundError(f"inkcheck JSON not found: {jp}")
    out = _check_numbers(_load_json(jp))
    out.update(label=entry.get("label", jp.stem), held_out=entry.get("held_out", True),
               note=entry.get("note", ""), published_auc=entry.get("published_auc"), json=str(entry.get("json")),
               expect=entry.get("expect"))
    return out


# ----------------------------------------------------------------------------------------------- node A
def node_a(checks: list[dict]) -> NodeResult:
    q = "Does the model see known ink on this labelled segment?"
    rows = [["checkpoint", "verdict", "r_bp [95% CI] (z)", "AUC (published)", "stroke recall [95% CI] (chance)", "strokes", "note"]]
    ev = []
    for c in checks:
        note = c["note"] or ""
        if not c["held_out"]:
            note = ("NOT held out; " + note).strip("; ")
        if c.get("expect"):
            ok = c["verdict"] == c["expect"]
            note = (f"expected {c['expect']}: {'reproduced' if ok else 'NOT reproduced'}; " + note).strip("; ")
        pub = f" ({c['published_auc']:.3f})" if c.get("published_auc") is not None else ""
        rci = f" [{_f(c['r_ci'][0])}, {_f(c['r_ci'][1])}]" if c.get("r_ci") else ""
        sci = f" [{_f(c['recall_ci'][0])}, {_f(c['recall_ci'][1])}]" if c.get("recall_ci") else ""
        if c.get("withheld"):
            rows.append([c["label"], c["verdict"], "withheld", "withheld", "withheld", "withheld", note])
            continue
        rows.append([c["label"], c["verdict"], f"{_f(c['r_bp'], 3)}{rci} ({_f(c['r_bp_z'], 1)})", f"{_f(c['auc'], 3)}{pub}",
                     f"{_f(c['stroke_recall'])}{sci} ({_f(c['stroke_null'])})", str(c["n_strokes"]), note])
    if any(c.get("r_ci") for c in checks):
        ev.append("Brackets: 95% CIs from a 2 mm tile bootstrap that keeps the registration fixed. They give precision, "
                  "not significance; significance is the shift-null p-value.")
    withheld = [c for c in checks if c.get("withheld")]
    if withheld:
        reasons = sorted({c["withheld"] for c in withheld})
        ev.append(f"Numbers withheld for {len(withheld)} of {len(checks)} checkpoint(s); verdicts only: " + "; ".join(reasons))
    clean = [c for c in checks if c["held_out"]]
    if not clean:
        return NodeResult("A", q, "NO_HELD_OUT", "No held-out checkpoint result: cannot answer.", ev,
                          "Score at least one checkpoint whose training data excludes this segment.", rows)
    measured = [c for c in clean if not c.get("withheld")]
    low_power = bool(measured) and len(measured) == len(clean) and all((c["n_strokes"] or 0) < LOW_POWER_STROKES for c in measured)
    auc_rep = [c for c in clean if c.get("published_auc") is not None]
    if low_power:
        agree = [c for c in auc_rep if abs(c["auc"] - c["published_auc"]) <= AUC_AGREE]
        ev.append(f"Only {max(c['n_strokes'] or 0 for c in clean)} reference strokes (< {LOW_POWER_STROKES}): "
                  "the stroke test has almost no power, so PASS is out of reach by design; AUC is the number to compare.")
        if auc_rep:
            ev.append(f"AUC reproduces the published value (|Δ| ≤ {AUC_AGREE}) for {len(agree)} of {len(auc_rep)} checkpoints with a published AUC: "
                      + ", ".join(f"{c['label']} {c['auc']:.3f} vs {c['published_auc']:.3f}" for c in auc_rep) + ".")
        if auc_rep and len(agree) == len(auc_rep):
            return NodeResult("A", q, "CONTROL_REPRODUCED", "Low-power control: inkcheck reproduces the official AUC, so the scoring matches the official evaluation.",
                              ev, "Use this as the pipeline control; run the full decision tree on a full labelled segment.", rows)
        return NodeResult("A", q, "LOW_POWER", "Too few reference strokes for a letter-level verdict.", ev,
                          "Use a larger labelled region (≥ 10 strokes) or compare AUC with a published value.", rows)
    best = max(clean, key=lambda c: (VERDICT_RANK.get(c["verdict"], -1), c["r_bp"] or 0))
    counts = {v: sum(c["verdict"] == v for c in clean) for v in ("PASS", "WEAK", "FAIL")}
    if best.get("withheld"):
        ev.append(f"Held-out checkpoints: {counts['PASS']} PASS, {counts['WEAK']} WEAK, {counts['FAIL']} FAIL (numbers withheld).")
    else:
        ev.append(f"Held-out checkpoints: {counts['PASS']} PASS, {counts['WEAK']} WEAK, {counts['FAIL']} FAIL "
                  f"(best: {best['label']}, r_bp {_f(best['r_bp'])}, stroke recall {_f(best['stroke_recall'])} vs chance {_f(best['stroke_null'])}"
                  + (f"; recall − chance {best['rmc']:+.2f}, 95% CI [{best['rmc_ci'][0]:+.2f}, {best['rmc_ci'][1]:+.2f}]" if best.get("rmc_ci") else "")
                  + ").")
    leaked = [c["label"] for c in checks if not c["held_out"]]
    if leaked:
        ev.append("Excluded from the verdict (segment in their training data): " + ", ".join(leaked) + ".")
    if counts["PASS"]:
        return NodeResult("A", q, "PASS", (f"YES: {counts['PASS']} of {len(clean)} held-out checkpoints recover letters (PASS)." if len(clean) > 1
                           else "YES: the held-out checkpoint recovers letters (PASS)."), ev,
                          "Ink is recoverable at this resolution with these models. Stop here, or move to unlabelled segments of the same scroll (node D).", rows)
    if counts["WEAK"]:
        return NodeResult("A", q, "WEAK", "PARTLY: significant agreement but not letter-level for every held-out checkpoint (WEAK).", ev,
                          "Ask whether the scan explains the loss (node B), then whether it is the scan or the scroll (node C).", rows)
    return NodeResult("A", q, "FAIL", "NO: no held-out checkpoint beats the search-matched null (FAIL).", ev,
                      "Check placement/orientation/render first (run a known-PASS control through the same pipeline), then nodes B/C.", rows)


# ----------------------------------------------------------------------------------------------- node B
def tolerance_edge(points: list[dict], higher_is_better: bool = True):
    """Worst proxy value still giving PASS on the tolerance curve (None if no PASS point)."""
    ok = [p["value"] for p in points if p.get("verdict") == "PASS"]
    if not ok:
        return None
    return min(ok) if higher_is_better else max(ok)


def node_b(spec: dict) -> NodeResult:
    q = "Do this scan's quality proxies fall outside what a ~9 µm model tolerates?"
    rows = [["proxy", "this scan", "tolerance edge (worst PASS)", "control (undegraded)", "inside tolerance?"]]
    ev = []
    if spec.get("source"):
        ev.append(f"Tolerance curve: {spec['source']}.")
    inside_all, n = True, 0
    for cur in spec.get("curves", []):
        hib = cur.get("higher_is_better", True)
        edge = tolerance_edge(cur["points"], hib)
        tgt = spec.get("target", {}).get(cur["proxy"])
        if edge is None or tgt is None:
            rows.append([cur["proxy"], _f(tgt, 3), _f(edge, 3), "–", "n/a"])
            continue
        inside = tgt >= edge if hib else tgt <= edge
        inside_all &= inside
        n += 1
        ctrl = next((p["value"] for p in cur["points"] if p.get("control")), None)
        rows.append([cur["proxy"] + (" (higher = better)" if hib else " (lower = better)"), _f(tgt, 3), _f(edge, 3),
                     _f(ctrl, 3), "yes" if inside else "**no**"])
        if cur.get("meaning"):
            ev.append(f"{cur['proxy']}: {cur['meaning']}")
    for t in spec.get("tolerances_text", []):
        ev.append(t)
    if not n:
        return NodeResult("B", q, "NOT_RUN", "No proxy/tolerance pair available.", ev,
                          "Measure the proxies (study/psd_compare.py, study/layer_snr.py) on this scan and on a degraded PASS control.", rows)
    if inside_all:
        return NodeResult("B", q, "SCAN_OK", "NO: every proxy is inside the tolerated range, so scan blur/noise alone does not explain the loss.",
                          ev, "Test scan vs scroll directly (node C): same segment, second scan.", rows)
    return NodeResult("B", q, "SCAN_SUSPECT", "POSSIBLY: at least one proxy is outside the tolerated range.", ev,
                      "Re-scan or render from a sharper / less noisy scan, then re-run node A (node C does exactly this if a second scan exists).", rows)


# ----------------------------------------------------------------------------------------------- node C
def node_c(scan_a: dict, scan_b: dict) -> NodeResult:
    q = "Same segment, two scans: is it the scan or the scroll?"
    by_a = {c["label"]: c for c in scan_a["checks"]}
    by_b = {c["label"]: c for c in scan_b["checks"]}
    common = [k for k in by_a if k in by_b]
    rows = [["checkpoint", f"{scan_a['name']}: verdict, r_bp, strokes", f"{scan_b['name']}: verdict, r_bp, strokes", "Δ r_bp", "Δ strokes"]]
    flips, d_r, d_s = [], [], []
    for k in common:
        a, b = by_a[k], by_b[k]
        rows.append([k, f"{a['verdict']}, {_f(a['r_bp'])}, {_f(a['stroke_recall'])}", f"{b['verdict']}, {_f(b['r_bp'])}, {_f(b['stroke_recall'])}",
                     f"{b['r_bp'] - a['r_bp']:+.2f}", f"{b['stroke_recall'] - a['stroke_recall']:+.2f}"])
        d_r.append(b["r_bp"] - a["r_bp"]); d_s.append(b["stroke_recall"] - a["stroke_recall"])
        if (a["verdict"] == "PASS") != (b["verdict"] == "PASS"):
            flips.append(k)
    if not common:
        return NodeResult("C", q, "NOT_RUN", "No checkpoint scored on both scans.", [], "Render the segment from the second scan and score the same checkpoints.", rows)
    import statistics as st
    ev = [f"{len(common)} checkpoints scored on both scans; median Δ r_bp {st.median(d_r):+.2f}, median Δ stroke recall {st.median(d_s):+.2f}."]
    if flips:
        return NodeResult("C", q, "SCAN_LIMITED", f"SCAN: {len(flips)} checkpoint(s) reach PASS on only one of the scans ({', '.join(flips)}).", ev,
                          "Prefer the better scan protocol for this scroll; re-run node A on more segments from it.", rows)
    anypass = any(by_a[k]["verdict"] == "PASS" for k in common)
    if anypass:
        return NodeResult("C", q, "BOTH_PASS", "Neither: letters are recovered from both scans.", ev, "No scan-driven loss to explain.", rows)
    return NodeResult("C", q, "SCROLL_SPECIFIC", "SCROLL/INK: no checkpoint reaches letter level on either scan, so the gap is not voxel size or scan protocol.",
                      ev, "Change the model or the labels, not the scan: a finer or cleaner scan of this scroll is not the bottleneck. Re-test any new model on held-out segments with node A.", rows)


# ----------------------------------------------------------------------------------------------- node D
DEFAULT_RULE = dict(min_ratio=2.0, min_components=5, min_r_other=0.3, width_mm=(0.1, 0.5), require_visual=True)


def candidate_rule(zone: dict, rule: dict | None = None) -> tuple[bool | None, list[str]]:
    """Pre-registered candidate rule for one (zone, model). Returns (passes, reasons).
    passes is None when only the (manual) visual criterion is missing."""
    r = dict(DEFAULT_RULE, **(rule or {}))
    why = []
    c, cn = zone.get("comps"), zone.get("comps_null")
    ok = True
    ratio = (float("inf") if c and not cn else (c / cn if cn else 0.0))
    if ratio < r["min_ratio"]:
        ok = False; why.append(f"components {c} vs reverse-depth null {cn} (ratio {ratio:.2f} < {r['min_ratio']})")
    nc = zone.get("n_components")
    if nc is not None and nc < r["min_components"]:
        ok = False; why.append(f"only {nc:.0f} components (< {r['min_components']})")
    ro = zone.get("r_other")
    if ro is None or ro < r["min_r_other"]:
        ok = False; why.append(f"agreement with a different checkpoint r = {_f(ro)} (< {r['min_r_other']})")
    w = zone.get("stroke_width_mm")
    if w is not None and not (r["width_mm"][0] <= w <= r["width_mm"][1]):
        ok = False; why.append(f"median stroke width {w:.2f} mm outside {r['width_mm'][0]}–{r['width_mm'][1]} mm")
    if not ok:
        return False, why
    vis = zone.get("visual_strokes")
    if r["require_visual"] and vis is None:
        return None, ["numeric criteria pass; visual check (strokes 0.1–0.5 mm) still to do"]
    if r["require_visual"] and not vis:
        return False, ["numeric criteria pass but no stroke-like shapes on visual check"]
    return True, ["all pre-registered criteria pass"]


def _parse_time(s):
    return _dt.datetime.fromisoformat(s) if s else None


def prereg_check(spec: dict, base: Path) -> tuple[bool, list[str]]:
    ev, ok = [], True
    p = _resolve(base, spec.get("prereg"))
    if p is None or not p.exists():
        return False, [f"pre-registration file not found: {spec.get('prereg')}"]
    ev.append(f"Pre-registration: `{spec.get('prereg')}` (sha256 {hashlib.sha256(p.read_bytes()).hexdigest()[:12]}…).")
    w, fr = _parse_time(spec.get("prereg_written")), _parse_time(spec.get("first_result"))
    if w is None or fr is None:
        ok = False; ev.append("Missing `prereg_written` / `first_result` timestamps: cannot show the rule came first.")
    elif w >= fr:
        ok = False; ev.append(f"Rule written {w.isoformat()} is NOT before the first result {fr.isoformat()}: treat as exploratory.")
    else:
        ev.append(f"Rule written {w.isoformat()}, first result viewed {fr.isoformat()}: rule came first.")
    return ok, ev


def node_d(spec: dict, base: Path) -> NodeResult:
    q = "Unlabelled segment: does any zone meet the pre-registered candidate rule?"
    pre_ok, ev = prereg_check(spec, base)
    rows = [["zone", "model", "comps/cm² (null)", "n comps", "r vs other ckpt", "width mm", "outcome", "why"]]
    cands, pending, n = [], [], 0
    zones = list(spec.get("zones", []))
    if spec.get("zones_file"):
        zones += _load_json(_resolve(base, spec["zones_file"]))["zones"]
    for z in zones:
        ok, why = candidate_rule(z, spec.get("rule"))
        n += 1
        out = "CANDIDATE" if ok else ("visual pending" if ok is None else "nothing")
        rows.append([z["zone"], z["model"], f"{_f(z.get('comps'), 1)} ({_f(z.get('comps_null'), 1)})",
                     _f(z.get("n_components"), 0), _f(z.get("r_other")), _f(z.get("stroke_width_mm")), out, "; ".join(why)])
        (cands if ok else pending if ok is None else []).append(f"{z['zone']}/{z['model']}")
    for t in spec.get("notes", []):
        ev.append(t)
    gpu = spec.get("compute")
    if not pre_ok:
        verdict, ans = "EXPLORATORY", "Rule not shown to be pre-registered: any hit is exploratory, not a candidate."
        nxt = "Write the rule in a PREREG file (PREREG_TEMPLATE.md) and re-run on fresh zones."
    elif cands:
        verdict, ans = "CANDIDATE", f"{len(cands)} zone/model pair(s) meet the pre-registered rule: {', '.join(cands)} (candidate, never 'ink')."
        nxt = "Spend compute here: denser/overlapped inference, the teacher model, both directions; seek a reference read."
    elif pending:
        verdict, ans = "VISUAL_PENDING", f"Numeric rule met by {', '.join(pending)}; visual check outstanding."
        nxt = "Do the visual check (strokes 0.1–0.5 mm) and record it in the case file."
    else:
        verdict, ans = "NO_CANDIDATE", f"No candidate in {n} zone/model pairs under the pre-registered rule."
        nxt = "Extra compute (e.g. GPU) is not justified by this evidence; only an exhaustive pass would change it."
    if gpu:
        ev.append(f"Compute: {gpu}")
    return NodeResult("D", q, verdict, ans, ev, nxt, rows, automated="automatic rule + pre-registration check; visual criterion manual")


# ----------------------------------------------------------------------------------------------- node R
def _spearman(a, b):
    """Spearman rho and exact one-sided permutation p (n <= 8)."""
    from itertools import permutations
    n = len(a)
    ra = [sorted(a).index(x) for x in a]
    rb = [sorted(b).index(x) for x in b]
    def rho(x, y):
        return 1 - 6 * sum((i - j) ** 2 for i, j in zip(x, y)) / (n * (n * n - 1))
    r0 = rho(ra, rb)
    if n > 8:
        return r0, None
    perms = list(permutations(range(n)))
    p = sum(rho(ra, q) >= r0 - 1e-12 for q in perms) / len(perms)
    return r0, p


def node_r(spec: dict, base: Path) -> NodeResult:
    """Do two independent references agree?  spec keys:
    references: [{name, kind}] ; ref_vs_ref: [{label, metric, value, null_mean, null_max, p, source}]
    same_pred: [{label, a: check-entry, b: check-entry}]  (one prediction scored against reference a and b)
    ranking: {metric_a, metric_b, models: [{label, a, b}], note}"""
    q = "Do independent references agree with each other and on the model verdicts?"
    refs = spec.get("references", [])
    names = [r["name"] for r in refs]
    ev = ["References: " + "; ".join(f"**{r['name']}** ({r.get('kind', '')})" for r in refs) + "."]
    rows = [["comparison", "reference A", "reference B", "agreement"]]
    ok, n = 0, 0
    for c in spec.get("ref_vs_ref", []):
        sig = c.get("p") is not None and c["p"] <= 0.01
        n += 1; ok += sig
        nm = f", null mean {c['null_mean']:.3f}" if c.get("null_mean") is not None else ""
        nx = f", null max {c['null_max']:.3f}" if c.get("null_max") is not None else ""
        rows.append([c["label"], c.get("a", names[0] if names else ""), c.get("b", names[1] if len(names) > 1 else ""),
                     f"{c['metric']} {c['value']:.3f}{nm}{nx}, p {c['p']:.4f} → {'agree' if sig else 'not shown'}"])
        if c.get("source"):
            ev.append(f"{c['label']}: {c['source']}.")
    for c in spec.get("same_pred", []):
        a, b = load_check(c["a"], base), load_check(c["b"], base)
        same = (a["verdict"] == "PASS") == (b["verdict"] == "PASS")   # the decision that matters: letter level or not
        n += 1; ok += same
        rows.append([c["label"], f"{a['verdict']} (r {_f(a['r_bp'])}, recall {_f(a['stroke_recall'])}, {a['n_strokes']} strokes)",
                     f"{b['verdict']} (r {_f(b['r_bp'])}, recall {_f(b['stroke_recall'])}, {b['n_strokes']} strokes)",
                     ("same decision" + ("" if a["verdict"] == b["verdict"] else " (PASS vs not-PASS agree; WEAK/FAIL differ)")) if same else "decisions differ"])
    rk = spec.get("ranking")
    if rk:
        ms = rk["models"]
        rho, p = _spearman([m["a"] for m in ms], [m["b"] for m in ms])
        sig = p is not None and p <= 0.05
        n += 1; ok += sig
        rows.append([f"model ranking ({len(ms)} models)", rk["metric_a"], rk["metric_b"],
                     f"Spearman ρ {rho:.2f}" + (f", exact p {p:.3f}" if p is not None else "") + f" → {'agree' if sig else 'not shown'}"])
        ev.append(f"Ranking: " + ", ".join(f"{m['label']} {m['a']:.3f}/{m['b']:.3f}" for m in ms) + "."
                  + (f" {rk['note']}" if rk.get("note") else ""))
    if spec.get("same_pred"):
        ev.append("Same prediction scored against each reference; 'same decision' = both PASS or both not PASS.")
    if n == 0:
        return NodeResult("R", q, "NO_SECOND_REF", "Only one reference: agreement not tested.", ev,
                          "Add a second, independent reference (another annotator, another modality).", rows)
    if ok == n:
        v, ans = "REFS_AGREE", (f"YES: all {n} agreement tests pass" if n > 1 else "YES: the agreement test passes") + ", so the verdict does not hinge on one reference."
    elif ok:
        v, ans = "REFS_PARTIAL", f"PARTLY: {ok} of {n} agreement tests pass."
    else:
        v, ans = "REFS_DISAGREE", (f"NO: none of {n} agreement tests pass" if n > 1 else "NO: the agreement test fails") + "; treat node A as reference-dependent."
    return NodeResult("R", q, v, ans, ev, spec.get("next_step", "Read node A together with this agreement."), rows)


# ----------------------------------------------------------------------------------------------- node N
def node_n(checks: list[dict]) -> NodeResult:
    """Negative controls: inputs built to have no letter-level agreement (wrong region, phase-randomised, shuffled
    tiles). The protocol is sound only if none of them PASSes."""
    q = "Do inputs built to contain no readable ink fail?"
    a = node_a([dict(c, held_out=True) for c in checks])
    rows = a.table
    passed = [c["label"] for c in checks if c["verdict"] == "PASS"]
    miss = [c["label"] for c in checks if c.get("expect") and c["verdict"] != c["expect"]]
    ev = [e for e in a.evidence if e.startswith("Brackets")]
    ev.append(f"{len(checks) - len(miss)} of {len(checks)} controls give the expected verdict; {len(passed)} PASS.")
    if passed:
        return NodeResult("N", q, "CONTROL_PASSED", f"NO: {', '.join(passed)} PASSed although it has no readable ink; the thresholds are too loose.",
                          ev, "Do not use the verdicts until the thresholds are recalibrated.", rows)
    if miss:
        return NodeResult("N", q, "NO_CONTROL_PASSES", f"YES for PASS: no control reaches PASS; {', '.join(miss)} did not give the expected verdict.",
                          ev, "PASS is safe; read WEAK as 'significant agreement, not letters' (see the note on each control).", rows)
    return NodeResult("N", q, "CONTROLS_OK", "YES: every control gives its expected verdict and none PASSes.", ev,
                      "The thresholds separate readable from unreadable inputs on these controls.", rows)


# ----------------------------------------------------------------------------------------------- run a case
def run_case(case: dict, base: Path) -> dict:
    nodes = []
    path = []
    if case.get("labeled", True) and case.get("checks"):
        a = node_a([load_check(e, base) for e in case["checks"]])
        nodes.append(a); path.append("A")
        if case.get("references"):
            r = node_r(case["references"], base); nodes.append(r); path.append("R")
        go_on = a.verdict in ("WEAK", "FAIL")
        if case.get("tolerance") and go_on:
            b = node_b(case["tolerance"]); nodes.append(b); path.append("B")
        if case.get("two_scan") and go_on:
            ts = case["two_scan"]
            sa = dict(name=ts["scan_a"]["name"], checks=[load_check(e, base) for e in ts["scan_a"]["checks"]])
            sb = dict(name=ts["scan_b"]["name"], checks=[load_check(e, base) for e in ts["scan_b"]["checks"]])
            c = node_c(sa, sb); nodes.append(c); path.append("C")
    if case.get("negative_controls"):
        nodes.append(node_n([load_check(e, base) for e in case["negative_controls"]])); path.append("N")
    if case.get("unlabeled"):
        d = node_d(case["unlabeled"], base); nodes.append(d); path.append("D")
    main = [n for n in nodes if n.node != "R"] or nodes
    final = main[-1] if main else None
    return dict(name=case.get("name", "case"), segment=case.get("segment", ""), scroll=case.get("scroll", ""),
                summary=case.get("summary", ""), path=path, nodes=[n.to_dict() for n in nodes],
                recommendation=(final.next_step if final else "Nothing to evaluate."),
                headline=case.get("headline") or (final.answer if final else ""))


def _md_table(rows):
    if not rows or len(rows) < 2:
        return ""
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    out += ["| " + " | ".join(str(x).replace("|", "/") for x in r) + " |" for r in rows[1:]]
    return "\n".join(out)


def card_markdown(res: dict, png_name: str | None = None) -> str:
    L = [f"# Readability card: {res['name']}", ""]
    if res["scroll"] or res["segment"]:
        L.append(f"**Scroll / segment:** {res['scroll']} {res['segment']}".rstrip())
    L.append(f"**Verdict path:** {' → '.join(res['path'])}  ")
    L.append(f"**Bottom line:** {res['headline']}  ")
    L.append(f"**Recommended next step:** {res['recommendation']}")
    if res["summary"]:
        L += ["", res["summary"]]
    if png_name:
        L += ["", f"![decision tree]({png_name})"]
    for n in res["nodes"]:
        L += ["", f"## Node {n['node']}: {n['question']}", "", f"**{n['verdict']}**: {n['answer']}", ""]
        L += [f"- {e}" for e in n["evidence"]]
        t = _md_table(n["table"])
        if t:
            L += ["", t]
        L += ["", f"*Next:* {n['next_step']}  ", f"*Automation:* {n['automated']}."]
    L += ["", "---", "Generated by `inkcheck report` (Ink Recoverability Protocol, CPU-only). Verdict rules: README → 'The protocol'."]
    return "\n".join(L) + "\n"


_COL = {"PASS": (46, 160, 67), "SCAN_OK": (46, 160, 67), "CONTROL_REPRODUCED": (46, 160, 67), "BOTH_PASS": (46, 160, 67),
        "WEAK": (230, 160, 30), "VISUAL_PENDING": (230, 160, 30), "LOW_POWER": (230, 160, 30), "SCROLL_SPECIFIC": (200, 90, 40),
        "SCAN_SUSPECT": (200, 90, 40), "SCAN_LIMITED": (200, 90, 40), "CANDIDATE": (40, 110, 200),
        "REFS_AGREE": (46, 160, 67), "REFS_PARTIAL": (230, 160, 30), "REFS_DISAGREE": (200, 50, 50),
        "NO_SECOND_REF": (110, 110, 110), "CONTROLS_OK": (46, 160, 67), "NO_CONTROL_PASSES": (46, 160, 67),
        "CONTROL_PASSED": (200, 50, 50), "FAIL": (200, 50, 50), "NO_CANDIDATE": (110, 110, 110), "EXPLORATORY": (200, 50, 50)}


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def card_png(res: dict, path: str):
    from PIL import Image, ImageDraw
    from .report import _font
    W = 1400
    f_t, f_h, f_b = _font(30), _font(22), _font(18)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    blocks = []
    for n in res["nodes"]:
        key = [e for e in n["evidence"] if not e.startswith(("Tolerance curve", "Pre-registration"))][:1]
        body = _wrap(tmp, n["answer"], f_b, W - 320)
        for e in key:
            body += _wrap(tmp, "• " + e.replace("`", "").replace("**", ""), f_b, W - 320)
        body += [""] + _wrap(tmp, "Next: " + n["next_step"], f_b, W - 320)
        blocks.append((n, body))
    H = 150 + sum(70 + 24 * len(b) for _, b in blocks) + 40 * len(blocks) + 130
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((30, 20), f"Readability card: {res['name']}", fill="black", font=f_t)
    y = 62
    for line in _wrap(d, f"{res['scroll']} {res['segment']}  |  path {' → '.join(res['path'])}", f_b, W - 60)[:2]:
        d.text((30, y), line, fill=(80, 80, 80), font=f_b); y += 24
    y += 20
    for i, (n, body) in enumerate(blocks):
        h = 60 + 24 * len(body)
        col = _COL.get(n["verdict"], (120, 120, 120))
        d.rounded_rectangle([30, y, W - 30, y + h], radius=14, outline=col, width=4)
        d.rounded_rectangle([30, y, 260, y + h], radius=14, fill=col)
        d.text((48, y + 12), f"Node {n['node']}", fill="white", font=f_h)
        for j, line in enumerate(_wrap(d, n["verdict"].replace("_", " "), f_b, 200)):
            d.text((48, y + 44 + 22 * j), line, fill="white", font=f_b)
        d.text((280, y + 10), n["question"], fill="black", font=f_h)
        for j, line in enumerate(body):
            d.text((280, y + 44 + 24 * j), line, fill=(30, 30, 30), font=f_b)
        y += h
        if i < len(blocks) - 1:
            d.line([120, y, 120, y + 40], fill=(90, 90, 90), width=4)
            d.polygon([(110, y + 28), (130, y + 28), (120, y + 40)], fill=(90, 90, 90))
            y += 40
    y += 20
    d.text((30, y), "Recommended next step:", fill="black", font=f_h); y += 30
    for line in _wrap(d, res["recommendation"], f_b, W - 60):
        d.text((30, y), line, fill="black", font=f_b); y += 24
    im.crop((0, 0, W, min(H, y + 20))).save(path)


def write_card(case_path: str, out_prefix: str) -> dict:
    cp = Path(case_path)
    case = _load_json(cp)
    res = run_case(case, cp.parent)
    out = Path(out_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    png = out.with_suffix(".png") if out.suffix else Path(str(out) + ".png")
    md = Path(str(png)[:-4] + ".md")
    js = Path(str(png)[:-4] + ".json")
    card_png(res, str(png))
    md.write_text(card_markdown(res, png.name))
    js.write_text(json.dumps(res, indent=1))
    res["_files"] = [str(md), str(png), str(js)]
    return res
