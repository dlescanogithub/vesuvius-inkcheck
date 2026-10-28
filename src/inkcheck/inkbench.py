"""Adapter for inkbench (github.com/inksweep/inkbench) outputs.

inkbench ranks 9 um readers on fixed benchmarks (AUC with block-bootstrap intervals, leakage flags). IRP decides what to
do with one segment. This module turns an inkbench results folder into IRP inputs, without importing inkbench:

  read_scores(results)            -> one row per (benchmark, reader, protocol, segment): value, mean, trained_on flag
  find_pred(preds, sample, seg, reader)
                                  -> the reader's raw reading-side map that inkbench/inksweep wrote for that segment
  case_from_inkbench(...)         -> an IRP case dict whose node-A checks are inkcheck runs on those maps (run lazily by
                                     `inkcheck report`), held_out taken from inkbench's trained_on flag
                                     ("yes" -> excluded, "unknown"/"n/a" -> excluded and flagged, "no" -> held out)

Layout read (inkbench/paths.py, score.py):
  RESULTS/scores/<benchmark>/<reader>.json  {protocol: {per_segment: {tag: value}, mean, trained_on: {tag: flag}, ...}}
  RESULTS/preds/<sample>/<segment folder>[/crop_y_x]/ink/<reader>/raw/<side>/<depth tag>.tif
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def read_scores(results: str | Path) -> list[dict]:
    rows = []
    sdir = Path(results) / "scores"
    for f in sorted(sdir.glob("*/*.json")):
        if f.name.startswith("_"):
            continue
        bench, reader = f.parent.name, f.stem
        for proto, r in json.loads(f.read_text()).items():
            if not isinstance(r, dict) or "per_segment" not in r:
                continue
            flags = r.get("trained_on", {}) or {}
            for seg, val in (r.get("per_segment") or {}).items():
                rows.append(dict(benchmark=bench, reader=reader, protocol=proto, segment=seg,
                                 value=None if val is None or val != val else float(val), mean=r.get("mean"),
                                 trained_on=flags.get(seg, "n/a")))
    return rows


def ranking(rows: list[dict], benchmark: str, protocol: Optional[str] = None) -> list[dict]:
    """Readers on one benchmark/protocol sorted by inkbench's benchmark mean (what inkbench is for)."""
    sel = [r for r in rows if r["benchmark"] == benchmark and (protocol is None or r["protocol"] == protocol)]
    if protocol is None and sel:
        protocol = sel[0]["protocol"]
        sel = [r for r in sel if r["protocol"] == protocol]
    by = {}
    for r in sel:
        d = by.setdefault(r["reader"], dict(reader=r["reader"], protocol=protocol, mean=r["mean"], segments={}, leaked=[]))
        d["segments"][r["segment"]] = r["value"]
        if r["trained_on"] != "no":
            d["leaked"].append(f"{r['segment']}:{r['trained_on']}")
    return sorted(by.values(), key=lambda d: -(d["mean"] if d["mean"] is not None else -1))


def find_pred(preds: str | Path, sample: str, segment: str, reader: str, side: str = "reading") -> Optional[Path]:
    """First raw map of ``reader`` for the segment folder that starts with ``segment`` (an id or folder name), else the
    one that contains it (inkbench tags such as ``w00`` sit inside the folder name)."""
    base = Path(preds) / sample
    for pat in (f"{segment}*", f"*{segment}*"):
        hits = sorted(base.glob(f"{pat}/ink/{reader}/raw/{side}/*.tif")) + \
            sorted(base.glob(f"{pat}/crop_*/ink/{reader}/raw/{side}/*.tif"))
        if hits:
            return hits[0]
    return None


def held_out_from_flag(flag: str) -> tuple[bool, str]:
    if flag == "no":
        return True, ""
    if flag == "yes":
        return False, "inkbench: segment in this reader's published training list"
    return False, f"inkbench: training data {flag} (treated as not held out)"


def case_from_inkbench(results: str | Path, benchmark: str, segment: str, sample: str, ref: str, pred_um: float,
                       ref_um: float, out_dir: str | Path, readers: Optional[list[str]] = None,
                       protocol: Optional[str] = None, segment_folder: Optional[str] = None, mask: Optional[str] = None,
                       ref_origin: Optional[str] = None, preds: Optional[str | Path] = None, name: str = "") -> dict:
    """Build an IRP case (node A) for one inkbench segment: one inkcheck run per reader that has a map."""
    rows = [r for r in read_scores(results) if r["benchmark"] == benchmark and r["segment"] == segment
            and (protocol is None or r["protocol"] == protocol)]
    if protocol is None and rows:
        protocol = rows[0]["protocol"]
        rows = [r for r in rows if r["protocol"] == protocol]
    preds = Path(preds) if preds else Path(results) / "preds"
    out_dir = Path(out_dir)
    checks, missing = [], []
    for r in rows:
        if readers and r["reader"] not in readers:
            continue
        p = find_pred(preds, sample, segment_folder or segment, r["reader"])
        if p is None:
            missing.append(r["reader"])
            continue
        ho, note = held_out_from_flag(r["trained_on"])
        e = dict(label=r["reader"], json=str(out_dir / f"{benchmark}_{segment}__{r['reader']}.json"), pred=str(p), ref=ref,
                 pred_um=pred_um, ref_um=ref_um, held_out=ho, note=note, published_auc=r["value"])
        if mask:
            e["mask"] = mask
        if ref_origin:
            e["ref_origin"] = ref_origin
        checks.append(e)
    case = dict(name=name or f"{sample} {segment} (inkbench {benchmark})", scroll=sample, segment=segment,
                summary=(f"Node A from inkbench outputs: benchmark {benchmark}, protocol {protocol}. 'AUC (published)' is "
                         f"inkbench's value for this segment under its own protocol and region, so it need not equal "
                         f"inkcheck's AUC. Leakage flags come from inkbench's trained_on records."),
                checks=checks, inkbench=dict(results=str(results), benchmark=benchmark, protocol=protocol,
                                             missing_maps=missing))
    return case
