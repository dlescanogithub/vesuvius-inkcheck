"""Known training overlap: is a (model, scroll, segment) score in-sample or held out?

A score on a segment the model was trained on measures fit, not generalisation. This module keeps a small registry of
model/segment pairs whose training status has been stated publicly, and answers

  is_in_sample(model, scroll, segment) -> True (in-sample: training overlap), False (stated held out), None (unknown)
  lookup(model, scroll, segment)       -> the same as a dict for reports (status, model, matched id, source, note)

It never changes a score, a verdict or an exit code: reports only carry the flag. Unknown models and unlisted
segments give None (no flag); "not listed" is not evidence of held out.

Segments can be named three ways and all are matched: the public 14-digit segment id (20250108000005), the public
w-number in a segment folder name (20250108000005-w030_2025010818 -> w030), and the case name of the
scrollprize/ink_9um label dataset (pherc0139-w017). The label dataset uses its own w-numbers, which do NOT follow the
public ones (its README says so), so a label case name is only matched as a label case name.

Users can add their own pairs with a JSON file (`--training-overlap FILE`, or `load_registry(path)`), a list of
entries with the same fields as BUILTIN below.

Only model and segment identifiers live here; no scroll data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

JO_TUD_2349 = ("jo-tud on ScrollPrize/villa PR #2349 (https://github.com/ScrollPrize/villa/pull/2349), from "
               "source_surface_volume in each ink_9um label case's .zattrs")

_INK9_0139_TRAIN = [
    # label case pherc0139-w017 sits on public w030; pherc0139-w029 sits on public w045 (.zattrs source_surface_volume)
    {"scroll": "PHerc0139", "segment_id": "20250108000005", "public_w": "w030", "label_case": "pherc0139-w017"},
    {"scroll": "PHerc0139", "segment_id": "20260126000000", "public_w": "w045", "label_case": "pherc0139-w029"},
]
_HELD_OUT_0343P = [{"scroll": "PHerc0343P", "segment_id": "*", "note": "0343P (ir-truth-9um)"}]

# Each entry: model (display name), match (regex on the model name, lower-cased with non-alphanumerics removed),
# in_sample / held_out (lists of segment specs), source, note.
# A segment spec has a scroll and any of: segment_id (public 14-digit id, or "*" = every segment of that scroll),
# public_w (public w-number), label_case (ink_9um label case name), w (a w-number whose naming scheme is not confirmed:
# matched against both public w-numbers and label case w-numbers, i.e. conservatively).
BUILTIN = [
    {"model": "scrollprize ink_9um seed 42", "match": r"ink9um(seed|s)42",
     "in_sample": _INK9_0139_TRAIN, "held_out": _HELD_OUT_0343P, "source": JO_TUD_2349,
     "note": "both 0139 cases are ink_9um training cases"},
    {"model": "scrollprize ink_9um seed 43", "match": r"ink9um(seed|s)43",
     "in_sample": _INK9_0139_TRAIN, "held_out": _HELD_OUT_0343P, "source": JO_TUD_2349,
     "note": "both 0139 cases are ink_9um training cases"},
    {"model": "Nieuwlaar/ink9um-dense-native", "match": r"densenative",
     "in_sample": _INK9_0139_TRAIN, "held_out": _HELD_OUT_0343P, "source": JO_TUD_2349,
     "note": "dense-native trains on both 0139 cases"},
    {"model": "YoussefMoNader/ink-8um-v8in", "match": r"v8in",
     # Recorded exactly as stated ("trained on 0139 w033/w035/w041/w044"). TODO confirm whether these are public
     # w-numbers or ink_9um label case numbers; until then they are matched in both namings (conservative).
     "in_sample": [{"scroll": "PHerc0139", "w": w} for w in ("w033", "w035", "w041", "w044")],
     "held_out": [{"scroll": "PHerc0139", "segment_id": "20250108000005", "public_w": "w030",
                   "label_case": "pherc0139-w017"},
                  {"scroll": "PHerc0139", "segment_id": "20260126000000", "public_w": "w045",
                   "label_case": "pherc0139-w029"}] + _HELD_OUT_0343P,
     "source": JO_TUD_2349,
     "note": "v8-in training cases w033/w035/w041/w044 as stated; their naming scheme is not confirmed"},
]

LABEL = {True: "in-sample (training overlap)", False: "held out (stated)", None: "unknown"}


def _norm_model(name) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def norm_scroll(s) -> str | None:
    """'PHerc0139', 'pherc0139', 'PHerc. 139', '0139' -> '139'; 'PHerc0343P' -> '343p' (fragment != scroll 343)."""
    if not s:
        return None
    t = re.sub(r"[^a-z0-9]", "", str(s).lower()).removeprefix("pherc")
    m = re.fullmatch(r"0*(\d+)([a-z0-9]*)", t)
    return (m.group(1) + m.group(2)) if m else t


def segment_ids(segment, scroll=None) -> dict:
    """Identifiers in a segment name: {'scroll', 'segment_id', 'public_w', 'label_case', 'label_w'} (None if absent)."""
    s = str(segment or "").strip()
    out = dict(scroll=norm_scroll(scroll), segment_id=None, public_w=None, label_case=None, label_w=None)
    m = re.fullmatch(r"(pherc[0-9a-z]+)-(w\d+)", s.lower())
    if m:                                                   # ink_9um label case name
        out.update(label_case=m.group(0), label_w=m.group(2))
        out["scroll"] = out["scroll"] or norm_scroll(m.group(1))
        return out
    m = re.search(r"(?<!\d)(\d{14})(?!\d)", s)
    if m:
        out["segment_id"] = m.group(1)
    m = re.search(r"(?<![a-z0-9])(w\d{2,3})(?![0-9])", s.lower())
    if m:
        out["public_w"] = m.group(1)
    return out


def _spec_matches(spec: dict, ids: dict) -> str | None:
    if norm_scroll(spec.get("scroll")) != ids["scroll"] or ids["scroll"] is None:
        return None
    if spec.get("segment_id") == "*":
        return f"{spec['scroll']} (all segments)"
    if spec.get("segment_id") and spec["segment_id"] == ids["segment_id"]:
        return spec["segment_id"]
    if spec.get("label_case") and spec["label_case"].lower() == ids["label_case"]:
        return spec["label_case"]
    # a public w-number only counts when there is no public id to contradict it
    if spec.get("public_w") and spec["public_w"] == ids["public_w"] and not (spec.get("segment_id") and ids["segment_id"]):
        return spec["public_w"]
    if spec.get("w") and spec["w"].lower() in (ids["public_w"], ids["label_w"]):
        return f"{spec['w']} (naming unconfirmed)"
    return None


def load_registry(path=None, include_builtin: bool = True) -> list[dict]:
    """Built-in entries plus a user JSON file (a list of entries, or {"entries": [...]}). User entries come first, so
    they win when both match."""
    reg = []
    if path:
        d = json.loads(Path(path).read_text())
        d = d.get("entries", []) if isinstance(d, dict) else d
        for e in d:
            if "match" not in e:
                e = {**e, "match": re.escape(_norm_model(e.get("model")))}
            reg.append({"source": f"user file {path}", **e})
    return reg + (list(BUILTIN) if include_builtin else [])


def lookup(model, scroll=None, segment=None, label=None, registry=None) -> dict:
    """Training-overlap status for one (model, scroll, segment). `label` is an optional second name for the segment
    (e.g. the ink_9um label case name next to the public folder); either may match."""
    reg = BUILTIN if registry is None else registry
    nm = _norm_model(model)
    base = dict(status=None, flag=LABEL[None], model=None, matched=None, source=None, note=None)
    if not nm:
        return base
    names = [ids for ids in (segment_ids(segment, scroll), segment_ids(label, scroll) if label else None) if ids]
    for e in reg:
        if not re.search(e["match"], nm):
            continue
        for status, key in ((True, "in_sample"), (False, "held_out")):
            for spec in e.get(key, []):
                for ids in names:
                    hit = _spec_matches(spec, ids)
                    if hit:
                        return dict(status=status, flag=LABEL[status], model=e.get("model"), matched=hit,
                                    source=e.get("source"), note=spec.get("note") or e.get("note"))
        return {**base, "model": e.get("model"), "source": e.get("source"),
                "note": "model known, segment not listed: training status unknown"}
    return base


def is_in_sample(model, scroll=None, segment=None, label=None, registry=None):
    """True = in-sample (the model trained on this segment), False = stated held out, None = unknown."""
    return lookup(model, scroll, segment, label, registry)["status"]
