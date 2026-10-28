#!/usr/bin/env python
"""Render score rows (bench/score.py output) as Markdown. Numbers are re-read from each row's inkcheck JSON.
usage: python bench/table.py [--rel BASE] LEADERBOARD.jsonl [...]"""
import json, os, sys

ORDER = {"PASS": 0, "WEAK": 1, "FAIL": 2}


def f(v, d=2):
    return "–" if v is None else f"{v:.{d}f}"


def load(paths, rel):
    rows = {}
    for p in paths:
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            j = r["json"] if os.path.isabs(r["json"]) or os.path.exists(r["json"]) else os.path.join(rel, r["json"])
            if os.path.exists(j):
                n = json.load(open(j))["numbers"]
                r.update(r_bp=n["r_bandpass"], r_bp_z=n["r_bandpass_z"], auc=n["auc_raw"], auc_p=n["metric_nulls"]["auc_raw"]["p"],
                         f1=n.get("breakeven_f1"), stroke_recall=n["stroke_recall"],
                         stroke_recall_chance=n["metric_nulls"]["stroke_recall"]["null_mean"], n_strokes=n.get("n_ref_strokes"),
                         area_cm2=n.get("overlap_cm2"))
            rows[(r["segment"], r["checkpoint"])] = r
    return sorted(rows.values(), key=lambda r: (r["scroll"], r["segment"], -(r.get("auc") or 0)))


def main(argv):
    rel = "."
    if argv[:1] == ["--rel"]:
        rel, argv = argv[1], argv[2:]
    rs = load(argv or ["results/scores/scores.jsonl"], rel)
    print("| scroll | segment (scored area) | checkpoint | AUC | band-pass r (z vs shift null) | breakeven F1 | strokes recalled (chance, n) | inkcheck verdict | note |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        v = f"**{r['verdict']}**" if r["verdict"] == "PASS" else r["verdict"]
        print(f"| {r['scroll']} | {r['segment']} ({f(r.get('area_cm2'))} cm², {r['held_out']}) | {r['checkpoint']} | {f(r['auc'],3)} | "
              f"{f(r['r_bp'])} ({f(r.get('r_bp_z'),1)}) | {f(r['f1'])} | {f(r['stroke_recall'])} ({f(r['stroke_recall_chance'])}, {r.get('n_strokes','–')}) | "
              f"{v} | {r['note']} |")


if __name__ == "__main__":
    main(sys.argv[1:])
