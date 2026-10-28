"""Fill the HIRES_1203_RESULTS block of docs/RESOLUTION_STUDY.md (and README.md) from the hires run's summary.json.
usage: python study/fill_hires.py SUMMARY_JSON [FILES...]   (schema-agnostic: renders a flattened key/value table)"""
import json, re, sys


def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from flat(v, f"{p}.{k}" if p else str(k))
    elif isinstance(d, list) and d and all(isinstance(x, dict) for x in d):
        for i, v in enumerate(d):
            yield from flat(v, f"{p}[{i}]")
    else:
        yield p, d


def fmt(v):
    return f"{v:.3g}" if isinstance(v, float) else json.dumps(v) if isinstance(v, (list, dict)) else str(v)


def main(summary, files):
    s = json.load(open(summary))
    rows = "\n".join(f"| `{k}` | {fmt(v)} |" for k, v in flat(s))
    body = f"Source: `{summary}`.\n\n| key | value |\n|---|---|\n{rows}\n"
    pat = re.compile(r"(<!-- HIRES_1203_RESULTS[^>]*-->\n).*?(<!-- /HIRES_1203_RESULTS -->)", re.S)
    for f in files:
        t = open(f).read(); n = pat.sub(lambda m: m.group(1) + body + m.group(2), t)
        if n != t: open(f, "w").write(n); print("filled", f)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["docs/RESOLUTION_STUDY.md", "README.md"])
