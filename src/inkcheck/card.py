"""Ink card: the versioned per-segment report (schema `inkcheck-report-v1.json`).

    card = build_card(check_json_dict, segment=..., model=..., scan=..., controls=[...], saturation=...)
    validate(card)                 # raises CardError listing every problem
    md = render_markdown(card)

`check_json_dict` is what `inkcheck` writes to PREFIX.json (verdict, summary, warnings, numbers, config, ...).
Validation uses `jsonschema` when it is installed and a small built-in validator (the subset of JSON Schema the
v1 schema uses) otherwise, so the core install stays dependency-light.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from importlib import resources
from pathlib import Path

from . import __version__

SCHEMA_NAME = "inkcheck-report-v1.json"
SCHEMA_VERSION = "1.0"
SCHEMA_ID = ("https://raw.githubusercontent.com/dlescanogithub/vesuvius-inkcheck/main/schemas/" + SCHEMA_NAME)
SATURATION_RULE = "8-bit map: saturated if >= 50% of valid pixels are above 128 (node_d_v2.saturation_check)"


class CardError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("invalid ink card:\n  " + "\n  ".join(self.errors))


def load_schema() -> dict:
    return json.loads(resources.files("inkcheck").joinpath("schemas", SCHEMA_NAME).read_text())


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _clean(o):
    """JSON-safe copy: numpy scalars -> python, NaN/inf -> None, tuples -> lists."""
    try:
        import numpy as np
        if isinstance(o, np.generic):
            o = o.item()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


METRIC_KEYS = ("r_bandpass", "r_bandpass_p", "r_bandpass_z", "r_bandpass_null_mean", "r_bandpass_null_sd",
               "r_bandpass_null_max", "n_shift_nulls", "n_shift_nulls_requested", "r_raw", "auc_raw", "breakeven_f1", "stroke_recall",
               "stroke_precision", "n_ref_strokes", "overlap_cm2", "analysis_um", "shift_um")


def saturation_block(pred=None, valid=None, sat: dict | None = None) -> dict:
    """Saturation block from a prediction array (8-bit only) or from a precomputed saturation_check dict."""
    if sat is None and pred is not None:
        import numpy as np
        a = np.asarray(pred)
        if a.size and float(np.nanmax(a)) <= 255 and float(np.nanmin(a)) >= 0 and np.allclose(a, np.round(a)):
            from .node_d_v2 import saturation_check
            sat = saturation_check(a, (a > 0) if valid is None else valid)
    if not sat:
        return {"checked": False, "saturated": None, "rule": SATURATION_RULE}
    out = {"checked": True, "rule": SATURATION_RULE}
    for k in ("saturated", "median", "frac_high", "threshold", "n"):
        if k in sat:
            out[k] = sat[k]
    out["saturated"] = bool(out.get("saturated"))
    return _clean(out)


def build_card(check: dict, *, segment: dict | None = None, model: dict | None = None, scan: dict | None = None,
               prediction: dict | None = None, reference: dict | None = None, controls: list | None = None,
               saturation: dict | None = None, prereg_sha256: str | None = None, extra: dict | None = None,
               created_utc: str | None = None) -> dict:
    """Assemble a v1 ink card from an inkcheck check JSON (dict) plus provenance. `saturation` may be a
    saturation_check() dict or an already-built block ({"checked": ...})."""
    n = check.get("numbers", {}) or {}
    cfg = check.get("config", {}) or {}
    node_a = check["verdict"]
    controls = [dict(c) for c in (controls or [])]
    for c in controls:
        c.setdefault("expected", "FAIL")
        c.setdefault("kind", c.get("name"))
    if controls:
        bad = [c for c in controls if c["verdict"] == "PASS" and c["expected"] == "FAIL"]
        node_n = "CONTROL_PASSED" if bad else "NO_CONTROL_PASSES"
    else:
        node_n = None
    final = "INVALID" if node_n == "CONTROL_PASSED" else node_a
    summary = check.get("summary", "")
    if final == "INVALID":
        summary = "a negative control passed, so the check cannot discriminate; " + summary
    metrics = {k: n.get(k) for k in METRIC_KEYS if k in n}
    chance = ((n.get("metric_nulls") or {}).get("stroke_recall") or {}).get("null_mean")
    metrics["stroke_recall_chance"] = chance
    b = n.get("bootstrap") or {}
    if b.get("r_ci"):
        metrics["r_bandpass_ci95"] = list(b["r_ci"])
    if saturation is None:
        sat_block = {"checked": False, "saturated": None, "rule": SATURATION_RULE}
    elif "checked" in saturation:
        sat_block = dict(saturation)
    else:
        sat_block = saturation_block(sat=saturation)
    warnings = list(check.get("warnings") or [])
    if sat_block.get("saturated"):
        warnings.append("prediction map looks saturated (most valid pixels are high): correlation/AUC can pass on an "
                        "uninformative map; inspect it before trusting a PASS")
    card = {
        "$schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "kind": "inkcheck.ink-card",
        "created_utc": created_utc or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "segment": {"scroll": None, "segment_id": None, **(segment or {})},
        "verdict": {"final": final, "node_A": node_a, "node_N": node_n, "summary": summary},
        "metrics": metrics,
        "thresholds": {k: cfg[k] for k in ("alpha_r", "min_r_bp", "min_stroke_recall") if k in cfg},
        "controls": controls,
        "saturation": sat_block,
        "warnings": warnings,
        "provenance": {
            "inkcheck_version": __version__,
            "prereg_sha256": prereg_sha256,
            "model": {"name": None, **(model or {})},
            "scan": dict(scan or {}),
            "prediction": dict(prediction or {}),
            "reference": dict(reference or {}),
            "config": cfg,
        },
    }
    if extra:
        card["extra"] = dict(extra)
    return _clean(card)


# --------------------------------------------------------------------------------------------- validation
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is_type(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def _resolve(ref, root):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def _check(v, s, root, path, errs):
    """Built-in validator for the JSON Schema subset used by the v1 schema."""
    if "$ref" in s:
        s = _resolve(s["$ref"], root)
    if "anyOf" in s:
        sub = []
        for alt in s["anyOf"]:
            e = []
            _check(v, alt, root, path, e)
            if not e:
                break
            sub += e
        else:
            errs.append(f"{path}: matches none of anyOf ({'; '.join(sub)})")
        return
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: must be {s['const']!r}, got {v!r}")
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: {v!r} not one of {s['enum']}")
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is_type(v, t) for t in ts):
            errs.append(f"{path}: expected {'/'.join(ts)}, got {type(v).__name__}")
            return
    if isinstance(v, str) and "pattern" in s and not re.search(s["pattern"], v):
        errs.append(f"{path}: {v!r} does not match {s['pattern']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: {v} < minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: {v} > maximum {s['maximum']}")
        if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
            errs.append(f"{path}: {v} <= exclusiveMinimum {s['exclusiveMinimum']}")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                errs.append(f"{path}: missing required '{k}'")
        props = s.get("properties", {})
        for k, x in v.items():
            if k in props:
                _check(x, props[k], root, f"{path}.{k}", errs)
            elif s.get("additionalProperties", True) is False:
                errs.append(f"{path}: unexpected property '{k}'")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            _check(x, s["items"], root, f"{path}[{i}]", errs)


def validation_errors(card: dict, use_jsonschema: bool | None = None) -> list[str]:
    """All problems with `card` (empty list = valid). jsonschema is used when installed (or when
    use_jsonschema=True), else the built-in subset validator (use_jsonschema=False forces it)."""
    schema = load_schema()
    errs: list[str] = []
    js = None
    if use_jsonschema is not False:
        try:
            import jsonschema as js
        except ImportError:
            if use_jsonschema:
                raise
    if js is not None:
        v = js.Draft202012Validator(schema)
        errs = [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in
                sorted(v.iter_errors(card), key=lambda e: list(map(str, e.absolute_path)))]
    else:
        _check(card, schema, schema, "$", errs)
    # semantic rules the schema does not express
    vd = card.get("verdict") if isinstance(card, dict) else None
    if isinstance(vd, dict):
        if vd.get("node_N") == "CONTROL_PASSED" and vd.get("final") != "INVALID":
            errs.append("$.verdict: a control passed, so final must be INVALID")
        if vd.get("node_N") != "CONTROL_PASSED" and vd.get("final") not in (vd.get("node_A"), None):
            errs.append("$.verdict: final must equal node_A unless a control passed")
    return errs


def validate(card: dict, use_jsonschema: bool | None = None) -> dict:
    """Return `card` if valid, else raise CardError with every problem."""
    errs = validation_errors(card, use_jsonschema)
    if errs:
        raise CardError(errs)
    return card


# ----------------------------------------------------------------------------------------------- markdown
def _f(x, fmt="{:.3f}"):
    if x is None:
        return "–"
    if isinstance(x, float):
        return fmt.format(x)
    return str(x)


def render_markdown(card: dict) -> str:
    """One-page Markdown ink card."""
    v, m, pv, seg, sat = card["verdict"], card["metrics"], card["provenance"], card["segment"], card["saturation"]
    title = " / ".join(str(x) for x in (seg.get("scroll"), seg.get("label") or seg.get("segment_id")) if x) or "segment"
    mdl = pv.get("model") or {}
    L = [f"# Ink card: {title}", "",
         f"**Verdict: {v['final']}** — {v['summary']}", "",
         f"| node | result |", "|---|---|",
         f"| A — known ink reproduced beyond search-matched nulls? | {v['node_A']} |",
         f"| N — negative controls fail? | {v['node_N'] or 'not run'} |",
         f"| saturation | {'not checked (map not 8-bit)' if not sat.get('checked') else ('**SATURATED**' if sat.get('saturated') else 'ok')} |",
         "", "## Metrics", "", "| metric | value |", "|---|---|"]
    rows = [("band-pass r", _f(m.get("r_bandpass"))),
            ("p (shift nulls)", _f(m.get("r_bandpass_p"), "{:.3g}")),
            ("null mean / max", f"{_f(m.get('r_bandpass_null_mean'))} / {_f(m.get('r_bandpass_null_max'))}"),
            ("shift nulls", _f(m.get("n_shift_nulls"))),
            ("r 95% CI (tile bootstrap)", "–" if not m.get("r_bandpass_ci95") else
             f"[{m['r_bandpass_ci95'][0]:.3f}, {m['r_bandpass_ci95'][1]:.3f}]"),
            ("raw r", _f(m.get("r_raw"))), ("AUC", _f(m.get("auc_raw"))), ("break-even F1", _f(m.get("breakeven_f1"))),
            ("stroke recall (chance)", f"{_f(m.get('stroke_recall'), '{:.2f}')} ({_f(m.get('stroke_recall_chance'), '{:.2f}')})"),
            ("stroke precision", _f(m.get("stroke_precision"), "{:.2f}")),
            ("reference strokes", _f(m.get("n_ref_strokes"))),
            ("overlap", f"{_f(m.get('overlap_cm2'), '{:.2f}')} cm²"),
            ("analysis grid", f"{_f(m.get('analysis_um'), '{:.2f}')} µm")]
    L += [f"| {a} | {b} |" for a, b in rows]
    th = card.get("thresholds") or {}
    if th:
        L += ["", "Thresholds: " + ", ".join(f"{k} = {th[k]}" for k in th)]
    L += ["", "## Controls", ""]
    if card["controls"]:
        L += ["| control | expected | verdict | band-pass r |", "|---|---|---|---|"]
        L += [f"| {c['name']} | {c['expected']} | {c['verdict']} | {_f(c.get('r_bandpass'))} |" for c in card["controls"]]
    else:
        L += ["No negative control was run (add one: `inkcheck quick` runs a wrong-place control)."]
    if sat.get("checked"):
        L += ["", f"Saturation: median {_f(sat.get('median'), '{:.0f}')}, fraction above {_f(sat.get('threshold'), '{:.0f}')}: "
                  f"{_f(sat.get('frac_high'), '{:.2f}')} → {'SATURATED' if sat.get('saturated') else 'ok'} ({sat.get('rule', '')})."]
    if card["warnings"]:
        L += ["", "## Warnings", ""] + [f"- {w}" for w in card["warnings"]]
    sc, pr, rf = pv.get("scan") or {}, pv.get("prediction") or {}, pv.get("reference") or {}
    L += ["", "## Provenance", "", "| field | value |", "|---|---|",
          f"| model | {mdl.get('name') or '–'}{' (run ' + str(mdl['run']) + ')' if mdl.get('run') else ''} |",
          f"| scan | {sc.get('volume') or '–'}{' · ' + _f(sc.get('pixel_um'), '{:g}') + ' µm' if sc.get('pixel_um') else ''}"
          f"{' · ' + _f(sc.get('energy_kev'), '{:g}') + ' keV' if sc.get('energy_kev') else ''} |",
          f"| prediction | {pr.get('source') or '–'} |", f"| reference | {rf.get('source') or '–'} |",
          f"| pre-registration sha256 | {pv.get('prereg_sha256') or 'none (not pre-registered)'} |",
          f"| inkcheck | {pv.get('inkcheck_version')} · card schema {card['schema_version']} · {card['created_utc']} |", ""]
    return "\n".join(L)


def write_card(card: dict, prefix) -> list[str]:
    """Validate, then write PREFIX.card.json and PREFIX.card.md. Returns the paths."""
    validate(card)
    p = Path(str(prefix))
    p.parent.mkdir(parents=True, exist_ok=True)
    j, md = Path(str(p) + ".card.json"), Path(str(p) + ".card.md")
    j.write_text(json.dumps(card, indent=2))
    md.write_text(render_markdown(card))
    return [str(j), str(md)]


def card_from_check_file(path, **kw) -> dict:
    d = json.loads(Path(path).read_text())
    if d.get("kind") == "inkcheck.ink-card":
        return d
    return build_card(d, **kw)
